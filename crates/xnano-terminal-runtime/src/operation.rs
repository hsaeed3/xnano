//! Operations: composable changes to a buffer or one of its regions.

use std::fmt;
use std::sync::{Arc, Mutex};

use ratatui::widgets::{Block, BorderType, Widget as _};
use ratatui_core::buffer::Cell;
use ratatui_core::layout::Rect;
use ratatui_core::style::{Color, Modifier};
use xnano_terminal_state::{Node, Patch, Store};

use crate::buffer::{BufferCore, relayout};
use crate::components::Component;
use crate::drawing::{Drawing, DrawingAnimation};
use crate::effects::EffectNode;
use crate::expression::{Environment, EvalError, Expr, Scalar};
use crate::geometry::{Point, Rectangle, Size};
use crate::grid::{Bounds, Grid, PasteMode, WriteMode};
use crate::layout::LayoutSpec;
use crate::pixel::{Pixel, PixelEncoding, PixelSpace, RasterMode, draw_rgba, write_pixels};
use crate::style::Style;
use crate::text::{Line, Span, TextEditor, display_width};
use crate::widgets::Resolver;
use crate::widgets::Shared;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BorderKind {
    Plain,
    Rounded,
    Double,
    Thick,
}

impl BorderKind {
    pub fn from_name(name: &str) -> Option<Self> {
        Some(match name {
            "plain" => Self::Plain,
            "rounded" => Self::Rounded,
            "double" => Self::Double,
            "thick" => Self::Thick,
            _ => return None,
        })
    }

    fn border_type(self) -> BorderType {
        match self {
            Self::Plain => BorderType::Plain,
            Self::Rounded => BorderType::Rounded,
            Self::Double => BorderType::Double,
            Self::Thick => BorderType::Thick,
        }
    }
}

/// How a text editor is drawn.
#[derive(Clone)]
pub struct EditorPainting {
    pub editor: Arc<Mutex<TextEditor>>,
    pub area: Option<Rectangle>,
    pub style: Style,
    pub first_row: usize,
    pub should_wrap: bool,
    pub should_show_cursor: bool,
    pub mode: WriteMode,
}

impl fmt::Debug for EditorPainting {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("EditorPainting")
    }
}

/// An operation whose settings are read from expressions each time it is applied.
#[derive(Clone)]
pub struct DynamicOperation {
    name: &'static str,
    builder: Arc<dyn Fn(&mut Resolver<'_>) -> Result<Operation, OperationError> + Send + Sync>,
}

impl DynamicOperation {
    pub fn new(
        name: &'static str,
        builder: impl Fn(&mut Resolver<'_>) -> Result<Operation, OperationError> + Send + Sync + 'static,
    ) -> Self {
        Self {
            name,
            builder: Arc::new(builder),
        }
    }

    /// The operation these settings describe right now.
    pub fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Operation, OperationError> {
        (self.builder)(resolver)
    }
}

impl fmt::Debug for DynamicOperation {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "Dynamic{}", self.name)
    }
}

/// A change to apply.
#[derive(Debug, Clone)]
pub enum Operation {
    Resize {
        width: i32,
        height: i32,
    },
    Move {
        x: i32,
        y: i32,
    },
    Place {
        x: i32,
        y: i32,
    },
    Write {
        lines: Vec<Line>,
        x: i32,
        y: i32,
        style: Style,
        mode: WriteMode,
    },
    Fill(Cell),
    Clear,
    Foreground(Color),
    Background(Color),
    ApplyStyle(Style),
    Border {
        kind: BorderKind,
        style: Style,
    },
    Paste {
        source: Arc<Grid>,
        x: i32,
        y: i32,
        mode: PasteMode,
    },
    Pixels {
        pixels: Arc<Vec<Pixel>>,
        encoding: PixelEncoding,
        clip: bool,
    },
    Raster {
        rgba: Arc<Vec<u8>>,
        width: i32,
        height: i32,
        x: i32,
        y: i32,
        encoding: PixelEncoding,
        mode: RasterMode,
    },
    SetState {
        store: Arc<Store>,
        path: Vec<String>,
        value: Node,
        expected_revision: Option<u64>,
    },
    ApplyStatePatch {
        store: Arc<Store>,
        path: Vec<String>,
        patch: Patch,
        expected_revision: Option<u64>,
    },
    Draw {
        drawing: Arc<Drawing>,
        x: i32,
        y: i32,
        encoding: PixelEncoding,
    },
    AnimateDrawing {
        animation: Arc<DrawingAnimation>,
        x: i32,
        y: i32,
        encoding: PixelEncoding,
        start_milliseconds: i64,
    },
    Effect(Shared<EffectNode>),
    CancelEffect(String),
    Fuzz {
        intensity: u32,
        seed: Option<u64>,
    },
    Layout(LayoutSpec),
    Component(Arc<Component>),
    Editor(EditorPainting),
    Sequence(Vec<Arc<Operation>>),
    Conditional {
        condition: Arc<Expr>,
        then: Arc<Operation>,
        otherwise: Option<Arc<Operation>>,
    },
    SetValue {
        property: crate::expression::PropertyId,
        value: Arc<Expr>,
    },
    /// Settings that follow expressions, read each time it is applied.
    Dynamic(DynamicOperation),
}

impl Operation {
    /// Whether applying it needs a runtime with a mounted target.
    pub fn requires_runtime(&self) -> bool {
        match self {
            Self::AnimateDrawing { .. } | Self::Effect(_) | Self::CancelEffect(_) => true,
            Self::Sequence(steps) => steps.iter().any(|step| step.requires_runtime()),
            Self::Conditional {
                then, otherwise, ..
            } => {
                then.requires_runtime()
                    || otherwise
                        .as_ref()
                        .is_some_and(|step| step.requires_runtime())
            }
            _ => false,
        }
    }
}

/// Work an operation hands to the runtime that owns the target.
#[derive(Debug, Clone)]
pub enum Deferred {
    StartEffect(Shared<EffectNode>),
    CancelEffect(String),
    AnimateDrawing {
        animation: Arc<DrawingAnimation>,
        x: i32,
        y: i32,
        encoding: PixelEncoding,
        start_milliseconds: i64,
    },
}

/// Why an operation failed.
#[derive(Debug)]
pub enum OperationError {
    /// It needs a mounted target and an active runtime.
    RuntimeRequired(String),
    /// This kind of target cannot do it.
    Unsupported(String),
    /// A pixel was outside the surface.
    OutOfBounds(String),
    Invalid(String),
    Evaluation(EvalError),
    State(xnano_terminal_state::Error),
}

impl fmt::Display for OperationError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::RuntimeRequired(message)
            | Self::Unsupported(message)
            | Self::OutOfBounds(message)
            | Self::Invalid(message) => formatter.write_str(message),
            Self::Evaluation(error) => write!(formatter, "{error}"),
            Self::State(error) => write!(formatter, "{error}"),
        }
    }
}

impl std::error::Error for OperationError {}

impl From<EvalError> for OperationError {
    fn from(error: EvalError) -> Self {
        Self::Evaluation(error)
    }
}

impl From<xnano_terminal_state::Error> for OperationError {
    fn from(error: xnano_terminal_state::Error) -> Self {
        Self::State(error)
    }
}

/// The buffer (or region of it) an operation changes.
#[derive(Clone)]
pub struct Target {
    pub core: Arc<BufferCore>,
    /// The region's bounds inside the buffer, or the whole buffer.
    pub region: Option<Rectangle>,
}

/// Everything an operation may consult or hand off while it applies.
pub struct ApplyContext<'a> {
    pub environment: &'a dyn Environment,
    pub has_runtime: bool,
    pub deferred: Vec<Deferred>,
}

fn region_bounds(grid: &Grid, region: Option<Rectangle>) -> Bounds {
    let full = Rectangle::new(0, 0, i32::from(grid.width()), i32::from(grid.height()));
    let area = region.map_or(full, |region| region.intersection(full));
    if area.is_empty() {
        return Bounds {
            left: 0,
            top: 0,
            right: 0,
            bottom: 0,
        };
    }
    Bounds {
        left: area.x as u16,
        top: area.y as u16,
        right: area.right() as u16,
        bottom: area.bottom() as u16,
    }
}

fn scalar_to_integer(value: &Scalar, name: &str) -> Result<i32, OperationError> {
    match value {
        Scalar::Integer(integer) => i32::try_from(*integer).map_err(|_| {
            OperationError::Invalid(format!("{name} is too large; use a smaller whole number"))
        }),
        other => Err(OperationError::Evaluation(EvalError::Type(format!(
            "{name} needs a whole number but got a {}; pass an int",
            other.type_name()
        )))),
    }
}

impl Operation {
    /// Apply to `target`.
    pub fn apply(
        &self,
        target: &Target,
        context: &mut ApplyContext<'_>,
    ) -> Result<(), OperationError> {
        let core = &target.core;
        match self {
            Self::Dynamic(dynamic) => {
                let operation = dynamic.resolve(&mut Resolver::new(context.environment))?;
                operation.apply(target, context)
            }
            Self::Resize { width, height } => {
                require_buffer(target, "resized")?;
                core.resize(*width, *height)
                    .map_err(OperationError::Invalid)
            }
            Self::Move { x, y } => {
                require_buffer(target, "moved")?;
                let (current_x, current_y) = {
                    let state = core.lock();
                    (state.x, state.y)
                };
                core.move_to(current_x.saturating_add(*x), current_y.saturating_add(*y));
                Ok(())
            }
            Self::Place { x, y } => {
                require_buffer(target, "placed")?;
                core.move_to(*x, *y);
                Ok(())
            }
            Self::Write {
                lines,
                x,
                y,
                style,
                mode,
            } => {
                // Writing what is already there changes nothing, so it must not make the
                // terminal draw a frame: a status line rewritten every update stays free.
                let mut state = target.core.lock();
                let bounds = region_bounds(&state.grid, target.region);
                // Only a small write is compared: for a large one the comparison costs more
                // than a frame it could save.
                let rows = rows_written(bounds, lines.len(), *y).filter(|rows| {
                    usize::from(rows.width()) * usize::from(rows.height()) <= MAXIMUM_COMPARED_CELLS
                });
                let before = rows.map(|rows| state.grid.region_buffer(rows));
                state.grid.write_lines(bounds, lines, *x, *y, *style, *mode);
                let is_unchanged = rows
                    .zip(before)
                    .is_some_and(|(rows, before)| state.grid.region_buffer(rows) == before);
                if !is_unchanged {
                    let area = Rectangle::new(
                        i32::from(bounds.left),
                        i32::from(bounds.top),
                        i32::from(bounds.width()),
                        i32::from(bounds.height()),
                    );
                    state.touch(Some(area));
                }
                Ok(())
            }
            Self::Fill(cell) => {
                self.edit(target, |grid, bounds| grid.fill(bounds, cell, false));
                Ok(())
            }
            Self::Clear => {
                let fill = core.lock().fill.clone();
                self.edit(target, |grid, bounds| grid.fill(bounds, &fill, false));
                Ok(())
            }
            Self::Foreground(color) => {
                let style = Style::default().fg(*color);
                self.edit(target, |grid, bounds| grid.apply_style(bounds, style));
                Ok(())
            }
            Self::Background(color) => {
                let style = Style::default().bg(*color);
                self.edit(target, |grid, bounds| grid.apply_style(bounds, style));
                Ok(())
            }
            Self::ApplyStyle(style) => {
                self.edit(target, |grid, bounds| grid.apply_style(bounds, *style));
                Ok(())
            }
            Self::Border { kind, style } => {
                Component::paint_with(target_edit(target), |region, area| {
                    Block::bordered()
                        .border_type(kind.border_type())
                        .border_style(*style)
                        .render(area, region);
                });
                Ok(())
            }
            Self::Paste { source, x, y, mode } => {
                self.edit(target, |grid, bounds| {
                    grid.paste(bounds, source, *x, *y, *mode);
                });
                Ok(())
            }
            Self::Pixels {
                pixels,
                encoding,
                clip,
            } => {
                let mut failure = None;
                self.edit(target, |grid, bounds| {
                    let space = PixelSpace {
                        bounds,
                        encoding: *encoding,
                    };
                    failure = write_pixels(grid, space, pixels, *clip).err();
                });
                match failure {
                    Some((column, row)) => Err(out_of_bounds(column, row)),
                    None => Ok(()),
                }
            }
            Self::Raster {
                rgba,
                width,
                height,
                x,
                y,
                encoding,
                mode,
            } => {
                let expected = (*width as usize)
                    .saturating_mul(*height as usize)
                    .saturating_mul(4);
                if rgba.len() != expected {
                    return Err(OperationError::Invalid(format!(
                        "an RGBA raster of {width} x {height} needs {expected} bytes (width * height * 4) \
                         but got {}; pass exactly four bytes per pixel",
                        rgba.len()
                    )));
                }
                self.edit(target, |grid, bounds| {
                    let space = PixelSpace {
                        bounds,
                        encoding: *encoding,
                    };
                    let _ = draw_rgba(grid, space, rgba, *width, *height, *x, *y, *mode, true);
                });
                Ok(())
            }
            Self::SetState {
                store,
                path,
                value,
                expected_revision,
            } => {
                store.set(path, value.clone(), *expected_revision)?;
                Ok(())
            }
            Self::ApplyStatePatch {
                store,
                path,
                patch,
                expected_revision,
            } => {
                store.apply(&patch.with_prefix(path), *expected_revision)?;
                Ok(())
            }
            Self::Draw {
                drawing,
                x,
                y,
                encoding,
            } => {
                self.edit(target, |grid, bounds| {
                    drawing.draw(grid, bounds, *x, *y, *encoding);
                });
                Ok(())
            }
            Self::AnimateDrawing {
                animation,
                x,
                y,
                encoding,
                start_milliseconds,
            } => {
                require_runtime(context, "AnimateDrawing")?;
                context.deferred.push(Deferred::AnimateDrawing {
                    animation: Arc::clone(animation),
                    x: *x,
                    y: *y,
                    encoding: *encoding,
                    start_milliseconds: *start_milliseconds,
                });
                Ok(())
            }
            Self::Effect(spec) => {
                require_runtime(context, "an animated effect")?;
                context
                    .deferred
                    .push(Deferred::StartEffect(Arc::clone(spec)));
                Ok(())
            }
            Self::CancelEffect(key) => {
                require_runtime(context, "CancelEffect")?;
                context.deferred.push(Deferred::CancelEffect(key.clone()));
                Ok(())
            }
            Self::Fuzz { intensity, seed } => {
                self.edit(target, |grid, bounds| {
                    crate::effects::fuzz(grid, bounds, *intensity, *seed);
                });
                Ok(())
            }
            Self::Layout(spec) => {
                require_buffer(target, "arranged")?;
                {
                    let mut state = core.lock();
                    state.layout = Some(spec.clone());
                    state.touch(None);
                }
                relayout(core);
                Ok(())
            }
            Self::Component(component) => {
                self.edit(target, |grid, bounds| component.paint(grid, bounds));
                Ok(())
            }
            Self::Editor(painting) => {
                self.edit(target, |grid, bounds| paint_editor(painting, grid, bounds));
                Ok(())
            }
            Self::Sequence(steps) => {
                for step in steps {
                    step.apply(target, context)?;
                }
                Ok(())
            }
            Self::Conditional {
                condition,
                then,
                otherwise,
            } => {
                let passed = condition
                    .evaluate(context.environment)?
                    .is_truthy()
                    .ok_or_else(|| {
                        OperationError::Evaluation(EvalError::Type(
                            "a condition must be a comparison or a combination of comparisons"
                                .to_owned(),
                        ))
                    })?;
                if passed {
                    then.apply(target, context)
                } else if let Some(otherwise) = otherwise {
                    otherwise.apply(target, context)
                } else {
                    Ok(())
                }
            }
            Self::SetValue { property, value } => {
                use crate::expression::PropertyId as P;
                require_buffer(target, "assigned a property")?;
                let value = value.evaluate(context.environment)?;
                let (x, y, width, height) = {
                    let state = core.lock();
                    (state.x, state.y, state.width(), state.height())
                };
                match property {
                    P::X => core.move_to(scalar_to_integer(&value, "X")?, y),
                    P::Y => core.move_to(x, scalar_to_integer(&value, "Y")?),
                    P::Width => core
                        .resize(scalar_to_integer(&value, "Width")?, height)
                        .map_err(OperationError::Invalid)?,
                    P::Height => core
                        .resize(width, scalar_to_integer(&value, "Height")?)
                        .map_err(OperationError::Invalid)?,
                    P::Position => match value {
                        Scalar::Point(Point { x, y }) => core.move_to(x, y),
                        other => return Err(type_error("Position", "Point", &other)),
                    },
                    P::Size => match value {
                        Scalar::Size(Size { width, height }) => {
                            core.resize(width, height)
                                .map_err(OperationError::Invalid)?;
                        }
                        other => return Err(type_error("Size", "Size", &other)),
                    },
                    P::Layer => {
                        let layer = scalar_to_integer(&value, "Layer")?;
                        {
                            let mut state = core.lock();
                            state.layer = layer;
                            state.touch(None);
                        }
                        if let Some(parent) = core.parent() {
                            parent.lock().touch(None);
                        }
                    }
                    P::IsVisible => match value {
                        Scalar::Bool(is_visible) => {
                            {
                                let mut state = core.lock();
                                state.is_visible = is_visible;
                                state.touch(None);
                            }
                            if let Some(parent) = core.parent() {
                                parent.lock().touch(None);
                            }
                        }
                        other => return Err(type_error("IsVisible", "bool", &other)),
                    },
                    other => {
                        return Err(OperationError::Invalid(format!(
                            "{} is read-only; only X, Y, Width, Height, Position, Size, Layer and \
                             IsVisible can be assigned",
                            other.name()
                        )));
                    }
                }
                Ok(())
            }
        }
    }

    fn edit(&self, target: &Target, change: impl FnOnce(&mut Grid, Bounds)) {
        let mut state = target.core.lock();
        let bounds = region_bounds(&state.grid, target.region);
        change(&mut state.grid, bounds);
        let area = Rectangle::new(
            i32::from(bounds.left),
            i32::from(bounds.top),
            i32::from(bounds.width()),
            i32::from(bounds.height()),
        );
        state.touch(Some(area));
    }
}

/// The most cells of a write that are compared with what was there before.
const MAXIMUM_COMPARED_CELLS: usize = 4096;

/// The rows of `bounds` that a write of `lines` lines starting at row `y` can reach.
fn rows_written(bounds: Bounds, lines: usize, y: i32) -> Option<Bounds> {
    let height = i32::from(bounds.height());
    let first = y.max(0);
    let last = y.saturating_add(lines as i32).min(height);
    (first < last).then(|| Bounds {
        left: bounds.left,
        right: bounds.right,
        top: bounds.top + first as u16,
        bottom: bounds.top + last as u16,
    })
}

fn target_edit(target: &Target) -> &Target {
    target
}

impl Component {
    /// Run `render` on a copy of the target region and write the result back.
    pub fn paint_with(
        target: &Target,
        render: impl FnOnce(&mut ratatui_core::buffer::Buffer, Rect),
    ) {
        let mut state = target.core.lock();
        let bounds = region_bounds(&state.grid, target.region);
        if bounds.width() == 0 || bounds.height() == 0 {
            return;
        }
        let mut region = state.grid.region_buffer(bounds);
        render(
            &mut region,
            Rect::new(0, 0, bounds.width(), bounds.height()),
        );
        state.grid.replace_region(bounds, &region);
        state.touch(None);
    }
}

fn require_buffer(target: &Target, verb: &str) -> Result<(), OperationError> {
    if target.region.is_some() {
        return Err(OperationError::Unsupported(format!(
            "a region cannot be {verb}; apply this to the region's buffer instead"
        )));
    }
    Ok(())
}

fn require_runtime(context: &ApplyContext<'_>, what: &str) -> Result<(), OperationError> {
    if context.has_runtime {
        return Ok(());
    }
    Err(OperationError::RuntimeRequired(format!(
        "{what} needs a mounted target and an active runtime. Mount the buffer with \
         Runtime.mount(buffer) and apply it through the returned context, or use a static \
         operation instead"
    )))
}

fn out_of_bounds(column: i32, row: i32) -> OperationError {
    OperationError::OutOfBounds(format!(
        "the pixel ({column}, {row}) is outside the surface; nothing was changed. Keep pixels \
         inside the surface or pass clip=True to skip the ones outside"
    ))
}

fn type_error(name: &str, expected: &str, found: &Scalar) -> OperationError {
    OperationError::Evaluation(EvalError::Type(format!(
        "{name} needs a {expected} but got a {}",
        found.type_name()
    )))
}

fn paint_editor(painting: &EditorPainting, grid: &mut Grid, bounds: Bounds) {
    let area = painting.area.unwrap_or(Rectangle::new(
        0,
        0,
        i32::from(bounds.width()),
        i32::from(bounds.height()),
    ));
    let inner = area.intersection(Rectangle::new(
        0,
        0,
        i32::from(bounds.width()),
        i32::from(bounds.height()),
    ));
    if inner.is_empty() {
        return;
    }
    let editor = painting
        .editor
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner);
    let inner_bounds = Bounds {
        left: bounds.left + inner.x as u16,
        top: bounds.top + inner.y as u16,
        right: bounds.left + inner.right() as u16,
        bottom: bounds.top + inner.bottom() as u16,
    };
    let width = inner.width as usize;
    let is_empty = editor.text().is_empty();
    let source = if is_empty {
        editor.placeholder_text.clone()
    } else {
        editor.text().to_owned()
    };
    let layout = crate::text::layout_text(
        &source,
        width,
        Some(editor.cursor_offset()),
        painting.should_wrap,
    );
    let placeholder_style = painting.style.add_modifier(Modifier::DIM);
    let lines: Vec<Line> = layout
        .lines
        .iter()
        .skip(painting.first_row)
        .take(inner.height as usize)
        .map(|line| {
            vec![Span::new(
                line.text.clone(),
                if is_empty {
                    placeholder_style
                } else {
                    painting.style
                },
            )]
        })
        .collect();
    grid.fill(
        inner_bounds,
        &crate::grid::styled_blank(painting.style),
        false,
    );
    grid.write_lines(inner_bounds, &lines, 0, 0, painting.style, painting.mode);
    if painting.should_show_cursor
        && let Some((column, row)) = layout.cursor_cell
        && row >= painting.first_row
        && row - painting.first_row < inner.height as usize
        && column < width
    {
        let x = inner_bounds.left + column as u16;
        let y = inner_bounds.top + (row - painting.first_row) as u16;
        if let Some(cell) = grid.buffer_mut().cell_mut((x, y)) {
            if display_width(cell.symbol()) == 0 {
                cell.set_symbol(" ");
            }
            cell.set_style(editor.cursor_style);
        }
    }
    if let Some((start, end)) = editor.selection() {
        for offset in start..end {
            let (column, row) = layout.cell_at_text_offset(offset);
            if row < painting.first_row
                || row - painting.first_row >= inner.height as usize
                || column >= width
            {
                continue;
            }
            let x = inner_bounds.left + column as u16;
            let y = inner_bounds.top + (row - painting.first_row) as u16;
            if let Some(cell) = grid.buffer_mut().cell_mut((x, y)) {
                cell.set_style(editor.selection_style);
            }
        }
    }
}
