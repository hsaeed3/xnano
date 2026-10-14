//! Cells, pixel views, regions and buffers: the surfaces content is written to.

use std::any::Any;
use std::sync::{Arc, Mutex};

use pyo3::exceptions::{PyIndexError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyCFunction, PyDict, PySlice, PyString, PyTuple, PyType};
use pyo3::{PyTraverseError, PyVisit};
use ratatui_core::buffer::Cell;
use unicode_segmentation::UnicodeSegmentation;
use xnano_terminal_runtime::buffer::{
    BufferCore, Geometry, absolute_origin, attach, check_size, compose, detach, relayout,
};
use xnano_terminal_runtime::expression::{Environment, EvalError, PropertyId, Scalar};
use xnano_terminal_runtime::geometry::{Point, Rectangle, Size};
use xnano_terminal_runtime::grid::{
    Bounds, Grid, PasteMode, WriteMode, cell_columns, styled_blank,
};
use xnano_terminal_runtime::operation::{ApplyContext, Deferred, Operation, Target};
use xnano_terminal_runtime::pixel::{
    Anchor, PixelEncoding, PixelSpace, RasterMode, draw_rgba, write_pixels,
};
use xnano_terminal_runtime::style::{Color, Modifier, Style, modifier_names};

use crate::convert::text_lines;
use crate::errors::{InvalidRegionError, eval_error, operation_error};
use crate::expressions::{ExpressionKind, PyExpression, expression_of, operation_of};
use crate::geometry::{PyPoint, PyRectangle, PySize};
use crate::hooks::{HookEntry, HookEvent, PyHook};
use crate::shared::{DrawingAnimationStart, RunningEffect, RuntimeLink, RuntimeShared, lock};
use crate::style::{PyColor, PyStyle, color_arg, modifiers_arg, style_arg};

/// What the Python layer keeps with a buffer.
#[derive(Default)]
pub struct BufferExt {
    pub hooks: Mutex<Vec<Arc<HookEntry>>>,
    pub registry: Mutex<Option<Py<PyAny>>>,
    pub runtime: Mutex<Option<RuntimeLink>>,
    pub children: Mutex<Vec<Py<PyBuffer>>>,
}

impl BufferExt {
    pub fn shared(&self) -> Option<Arc<RuntimeShared>> {
        lock(&self.runtime)
            .as_ref()
            .and_then(std::sync::Weak::upgrade)
    }
}

/// The extension of a buffer core, if it has one.
pub fn ext_of(core: &Arc<BufferCore>) -> Option<Arc<BufferExt>> {
    let extension = core.lock().extension.clone()?;
    let any: Arc<dyn Any + Send + Sync> = extension;
    any.downcast::<BufferExt>().ok()
}

/// One grapheme and how many columns it covers.
pub fn single_symbol(text: &str) -> PyResult<(String, usize)> {
    if text.is_empty() {
        return Ok((" ".to_owned(), 1));
    }
    let mut graphemes = text.graphemes(true);
    let (Some(first), None) = (graphemes.next(), graphemes.next()) else {
        return Err(PyValueError::new_err(format!(
            "a cell holds one character (one grapheme), but {text:?} has more; write longer text \
             with write()"
        )));
    };
    if first.chars().any(char::is_control) {
        return Err(PyValueError::new_err(
            "a cell cannot hold a control character",
        ));
    }
    let columns = xnano_terminal_runtime::text::grapheme_width(first);
    if columns == 0 || columns > 2 {
        return Err(PyValueError::new_err(format!(
            "{first:?} takes {columns} columns; a cell symbol must take one or two columns"
        )));
    }
    Ok((first.to_owned(), columns))
}

#[pyclass(name = "Cell", module = "xnano_core._xnano_core")]
pub struct PyCell {
    pub cell: Cell,
    pub is_transparent: bool,
}

#[pymethods]
impl PyCell {
    #[new]
    #[pyo3(signature = (symbol = " ", *, style = None, foreground = None, background = None,
        modifiers = None, is_transparent = false))]
    fn new(
        symbol: &str,
        style: Option<&Bound<'_, PyAny>>,
        foreground: Option<&Bound<'_, PyAny>>,
        background: Option<&Bound<'_, PyAny>>,
        modifiers: Option<&Bound<'_, PyAny>>,
        is_transparent: bool,
    ) -> PyResult<Self> {
        let (symbol, _) = single_symbol(symbol)?;
        let mut cell = Cell::EMPTY;
        cell.set_symbol(&symbol);
        cell.set_style(style_arg(style)?);
        if let Some(color) = foreground.filter(|value| !value.is_none()) {
            cell.fg = color_arg(color)?;
        }
        if let Some(color) = background.filter(|value| !value.is_none()) {
            cell.bg = color_arg(color)?;
        }
        if let Some(modifiers) = modifiers {
            cell.modifier |= modifiers_arg(modifiers)?;
        }
        Ok(Self {
            cell,
            is_transparent,
        })
    }

    #[getter]
    fn symbol(&self) -> &str {
        self.cell.symbol()
    }

    #[setter]
    fn set_symbol(&mut self, value: &str) -> PyResult<()> {
        let (symbol, _) = single_symbol(value)?;
        self.cell.set_symbol(&symbol);
        Ok(())
    }

    #[getter]
    fn style(&self) -> PyStyle {
        let mut style = Style::default();
        if self.cell.fg != Color::Reset {
            style = style.fg(self.cell.fg);
        }
        if self.cell.bg != Color::Reset {
            style = style.bg(self.cell.bg);
        }
        PyStyle {
            inner: style.add_modifier(self.cell.modifier),
        }
    }

    #[setter]
    fn set_style(&mut self, value: &PyStyle) {
        self.cell.fg = Color::Reset;
        self.cell.bg = Color::Reset;
        self.cell.modifier = Modifier::empty();
        self.cell.set_style(value.inner);
    }

    #[getter]
    fn is_transparent(&self) -> bool {
        self.is_transparent
    }

    #[setter]
    fn set_is_transparent(&mut self, value: bool) {
        self.is_transparent = value;
    }

    #[getter]
    fn foreground(&self) -> PyColor {
        PyColor {
            inner: self.cell.fg,
        }
    }

    #[getter]
    fn background(&self) -> PyColor {
        PyColor {
            inner: self.cell.bg,
        }
    }

    fn copy(&self) -> Self {
        Self {
            cell: self.cell.clone(),
            is_transparent: self.is_transparent,
        }
    }

    fn __eq__(&self, other: &Bound<'_, PyAny>) -> bool {
        other.extract::<PyRef<'_, PyCell>>().is_ok_and(|other| {
            other.cell.symbol() == self.cell.symbol()
                && other.cell.fg == self.cell.fg
                && other.cell.bg == self.cell.bg
                && other.cell.modifier == self.cell.modifier
                && other.is_transparent == self.is_transparent
        })
    }

    fn __repr__(&self) -> String {
        format!(
            "Cell({:?}, foreground='{}', background='{}', modifiers={:?})",
            self.cell.symbol(),
            xnano_terminal_runtime::style::describe_color(self.cell.fg),
            xnano_terminal_runtime::style::describe_color(self.cell.bg),
            modifier_names(self.cell.modifier)
        )
    }
}

fn cell_from(value: &Bound<'_, PyAny>) -> PyResult<(Cell, usize, bool)> {
    if let Ok(cell) = value.extract::<PyRef<'_, PyCell>>() {
        let columns = cell_columns(&cell.cell).max(1);
        return Ok((cell.cell.clone(), columns, cell.is_transparent));
    }
    if let Ok(text) = value.cast::<PyString>() {
        let (symbol, columns) = single_symbol(&text.to_cow()?)?;
        let mut cell = Cell::EMPTY;
        cell.set_symbol(&symbol);
        return Ok((cell, columns, false));
    }
    Err(PyTypeError::new_err(format!(
        "a cell value must be a Cell or a one-character str, not {}",
        value.get_type().name()?
    )))
}

fn pixel_list(value: &Bound<'_, PyAny>) -> PyResult<Vec<(i32, i32, (u8, u8, u8))>> {
    let mut pixels = Vec::new();
    for item in value.try_iter()? {
        let item = item?;
        let (column, row, color): (i32, i32, (i64, i64, i64)) = item.extract().map_err(|_| {
            PyTypeError::new_err("a pixel is (column, row, (red, green, blue)) with whole numbers")
        })?;
        let channel = |value: i64| {
            u8::try_from(value).map_err(|_| {
                PyValueError::new_err(format!(
                    "the color channel {value} is out of range; use 0 to 255"
                ))
            })
        };
        pixels.push((
            column,
            row,
            (channel(color.0)?, channel(color.1)?, channel(color.2)?),
        ));
    }
    Ok(pixels)
}

#[pyclass(name = "PixelView", module = "xnano_core._xnano_core", frozen)]
pub struct PyPixelView {
    surface: Py<PyAny>,
    encoding: PixelEncoding,
}

impl PyPixelView {
    fn space(&self, py: Python<'_>) -> PyResult<(Arc<BufferCore>, PixelSpace)> {
        let surface = self.surface.bind(py).extract::<PyRef<'_, PySurface>>()?;
        let bounds = surface.bounds()?;
        Ok((
            Arc::clone(&surface.core),
            PixelSpace {
                bounds,
                encoding: self.encoding,
            },
        ))
    }
}

#[pymethods]
impl PyPixelView {
    #[getter]
    fn surface(&self, py: Python<'_>) -> Py<PyAny> {
        self.surface.clone_ref(py)
    }

    #[getter]
    fn encoding(&self) -> &'static str {
        self.encoding.name()
    }

    #[getter]
    fn width(&self, py: Python<'_>) -> PyResult<i32> {
        Ok(self.space(py)?.1.width())
    }

    #[getter]
    fn height(&self, py: Python<'_>) -> PyResult<i32> {
        Ok(self.space(py)?.1.height())
    }

    #[pyo3(signature = (pixels, *, clip = true))]
    fn write(&self, py: Python<'_>, pixels: &Bound<'_, PyAny>, clip: bool) -> PyResult<()> {
        let pixels = pixel_list(pixels)?;
        let (core, space) = self.space(py)?;
        let failure = {
            let mut state = core.lock();
            let outcome = write_pixels(&mut state.grid, space, &pixels, clip);
            if outcome.is_ok() {
                state.touch(None);
            }
            outcome.err()
        };
        if let Some((column, row)) = failure {
            return Err(PyIndexError::new_err(format!(
                "the pixel ({column}, {row}) is outside the surface; nothing was changed. Keep \
                 pixels inside the surface or pass clip=True to skip the ones outside"
            )));
        }
        nudge(&core);
        Ok(())
    }

    #[pyo3(signature = (data, *, width, height, x = 0, y = 0, mode = "over", clip = true))]
    fn draw_rgba(
        &self,
        py: Python<'_>,
        data: &[u8],
        width: i32,
        height: i32,
        x: i32,
        y: i32,
        mode: &str,
        clip: bool,
    ) -> PyResult<()> {
        if width < 0 || height < 0 {
            return Err(PyValueError::new_err(
                "the raster width and height must be zero or more",
            ));
        }
        let expected = (width as usize) * (height as usize) * 4;
        if data.len() != expected {
            return Err(PyValueError::new_err(format!(
                "an RGBA raster of {width} x {height} needs {expected} bytes (width * height * 4) \
                 but got {}",
                data.len()
            )));
        }
        let mode = RasterMode::from_name(mode).ok_or_else(|| {
            PyValueError::new_err(format!(
                "\"{mode}\" is not a raster mode; use \"replace\" or \"over\""
            ))
        })?;
        let (core, space) = self.space(py)?;
        let failure = {
            let mut state = core.lock();
            let outcome = draw_rgba(
                &mut state.grid,
                space,
                data,
                width,
                height,
                x,
                y,
                mode,
                clip,
            );
            if outcome.is_ok() {
                state.touch(None);
            }
            outcome.err()
        };
        if let Some((column, row)) = failure {
            return Err(PyIndexError::new_err(format!(
                "the pixel ({column}, {row}) is outside the surface; nothing was changed"
            )));
        }
        nudge(&core);
        Ok(())
    }

    fn cell_at(&self, py: Python<'_>, pixel_column: i32, pixel_row: i32) -> PyResult<(i32, i32)> {
        Ok(self.space(py)?.1.cell_of(pixel_column, pixel_row))
    }

    #[pyo3(signature = (column, row, *, anchor = "center"))]
    fn pixel_at(
        &self,
        py: Python<'_>,
        column: i32,
        row: i32,
        anchor: &str,
    ) -> PyResult<(i32, i32)> {
        let anchor = Anchor::from_name(anchor).ok_or_else(|| {
            PyValueError::new_err(format!(
                "\"{anchor}\" is not an anchor; use \"top_left\", \"center\" or \"bottom_right\""
            ))
        })?;
        Ok(self.space(py)?.1.pixel_of(column, row, anchor))
    }
}

/// Tell the runtime a buffer changed, if it is mounted on one.
pub fn nudge(core: &Arc<BufferCore>) {
    if let Some(shared) = ext_of(core).and_then(|ext| ext.shared()) {
        shared.request_frame();
    }
}

fn as_index(value: &Bound<'_, PyAny>, length: i32, name: &str) -> PyResult<i32> {
    let index: i64 = value.extract().map_err(|_| {
        PyTypeError::new_err(format!(
            "a cell index is (column, row) with whole numbers or slices, not {name}"
        ))
    })?;
    let adjusted = if index < 0 {
        index + i64::from(length)
    } else {
        index
    };
    if adjusted < 0 || adjusted >= i64::from(length) {
        return Err(PyIndexError::new_err(format!(
            "the {name} {index} is outside the surface, which has {length} {name}s"
        )));
    }
    Ok(adjusted as i32)
}

fn slice_range(slice: &Bound<'_, PySlice>, length: i32) -> PyResult<(i32, i32)> {
    let indices = slice.indices(length as isize)?;
    if indices.step != 1 {
        return Err(PyValueError::new_err(
            "a region slice cannot have a step; use region[a:b, c:d]",
        ));
    }
    Ok((indices.start as i32, indices.stop.max(indices.start) as i32))
}

#[pyclass(name = "Surface", module = "xnano_core._xnano_core", subclass)]
pub struct PySurface {
    pub core: Arc<BufferCore>,
    pub ext: Arc<BufferExt>,
    /// The region's bounds inside its buffer, or `None` for a whole buffer.
    pub region: Option<Rectangle>,
}

impl PySurface {
    /// The bounds of this surface inside its grid, or an error if a region no longer fits.
    pub fn bounds(&self) -> PyResult<Bounds> {
        let state = self.core.lock();
        let grid = Rectangle::new(0, 0, state.width(), state.height());
        let area = match self.region {
            None => grid,
            Some(region) => {
                if region.intersection(grid) != region && !region.is_empty() {
                    return Err(InvalidRegionError::new_err(format!(
                        "the region at ({}, {}) sized {} x {} no longer fits its buffer, which is \
                         now {} x {}; take a new region with buffer.region(...)",
                        region.x, region.y, region.width, region.height, grid.width, grid.height
                    )));
                }
                region
            }
        };
        Ok(Bounds {
            left: area.x as u16,
            top: area.y as u16,
            right: area.right() as u16,
            bottom: area.bottom() as u16,
        })
    }

    fn dimensions(&self) -> PyResult<(i32, i32)> {
        let bounds = self.bounds()?;
        Ok((i32::from(bounds.width()), i32::from(bounds.height())))
    }

    fn edit(&self, change: impl FnOnce(&mut Grid, Bounds)) -> PyResult<()> {
        let bounds = self.bounds()?;
        {
            let mut state = self.core.lock();
            change(&mut state.grid, bounds);
            state.touch(Some(crate::shared::full_bounds(bounds)));
        }
        nudge(&self.core);
        Ok(())
    }

    fn target(&self) -> Target {
        Target {
            core: Arc::clone(&self.core),
            region: self.region,
        }
    }

    fn environment(&self) -> SurfaceEnv {
        SurfaceEnv {
            core: Arc::clone(&self.core),
            region: self.region,
            shared: self.ext.shared(),
        }
    }
}

/// Reads for expressions: the target's geometry and, when mounted, its runtime's clock.
pub struct SurfaceEnv {
    pub core: Arc<BufferCore>,
    pub region: Option<Rectangle>,
    pub shared: Option<Arc<RuntimeShared>>,
}

impl SurfaceEnv {
    /// The size of the buffer this target sits in: the parent of a buffer, or the buffer a
    /// region belongs to.
    fn parent_size(&self, id: PropertyId) -> Result<Size, EvalError> {
        if self.region.is_some() {
            let state = self.core.lock();
            return Ok(Size::new(state.width(), state.height()));
        }
        let parent = self.core.parent().ok_or_else(|| {
            EvalError::Type(format!(
                "{} needs a parent buffer, but this buffer has none. Attach it to a parent with \
                 parent.attach(buffer) first",
                id.name()
            ))
        })?;
        let state = parent.lock();
        Ok(Size::new(state.width(), state.height()))
    }

    /// The target's rectangle on the screen.
    fn screen_bounds(&self) -> Rectangle {
        let (origin_x, origin_y) = absolute_origin(&self.core);
        let local = self.core.lock().bounds();
        match self.region {
            // A region is positioned inside its buffer, whose own origin is already included.
            Some(region) => Rectangle::new(
                origin_x.saturating_add(region.x),
                origin_y.saturating_add(region.y),
                region.width,
                region.height,
            ),
            None => Rectangle::new(origin_x, origin_y, local.width, local.height),
        }
    }

    fn runtime(&self, id: PropertyId) -> Result<&Arc<RuntimeShared>, EvalError> {
        self.shared.as_ref().ok_or_else(|| {
            EvalError::RuntimeRequired(format!(
                "{} needs a runtime. Mount the buffer with Runtime.mount(buffer) first, or read \
                 only X, Y, Width, Height, Position, Size and Bounds offline",
                id.name()
            ))
        })
    }
}

impl Environment for SurfaceEnv {
    fn external(&self, name: &str) -> Result<Scalar, EvalError> {
        let shared = self.runtime(PropertyId::TimeElapsed).map_err(|_| {
            EvalError::RuntimeRequired(format!(
                "{name} needs a runtime. Mount the buffer with Runtime.mount(buffer) and install the \
                 extension that provides it"
            ))
        })?;
        Python::attach(|py| {
            let runtime = crate::runtime::runtime_object(py, shared).ok_or_else(|| {
                EvalError::RuntimeRequired(format!("{name} needs a runtime that is still open"))
            })?;
            let value = runtime
                .bind(py)
                .call_method1("_read_external", (name,))
                .map_err(|error| EvalError::State(error.to_string()))?;
            crate::convert::scalar_from_py(&value)
                .map_err(|error| EvalError::Type(error.to_string()))
        })
    }

    fn property(&self, id: PropertyId) -> Result<Scalar, EvalError> {
        let bounds = {
            let state = self.core.lock();
            self.region.unwrap_or_else(|| state.bounds())
        };
        Ok(match id {
            PropertyId::X => Scalar::Integer(i64::from(bounds.x)),
            PropertyId::Y => Scalar::Integer(i64::from(bounds.y)),
            PropertyId::Width => Scalar::Integer(i64::from(bounds.width)),
            PropertyId::Height => Scalar::Integer(i64::from(bounds.height)),
            PropertyId::Position => Scalar::Point(Point::new(bounds.x, bounds.y)),
            PropertyId::Size => Scalar::Size(Size::new(bounds.width, bounds.height)),
            PropertyId::Bounds => Scalar::Rectangle(bounds),
            PropertyId::TimeElapsed => Scalar::Float(self.runtime(id)?.clock.elapsed_seconds()),
            PropertyId::TimeDelta => Scalar::Float(self.runtime(id)?.clock.delta_seconds()),
            PropertyId::TimeElapsedMilliseconds => {
                Scalar::Float(self.runtime(id)?.clock.elapsed_seconds() * 1000.0)
            }
            PropertyId::TimeDeltaMilliseconds => {
                Scalar::Float(self.runtime(id)?.clock.delta_seconds() * 1000.0)
            }
            PropertyId::Frame => {
                Scalar::Integer(i64::try_from(self.runtime(id)?.clock.frame()).unwrap_or(i64::MAX))
            }
            PropertyId::FramesPerSecond => {
                Scalar::Float(self.runtime(id)?.clock.frames_per_second())
            }
            PropertyId::Focused => Scalar::Bool(self.runtime(id)?.is_focused(&self.core)),
            PropertyId::Running => Scalar::Bool(
                self.runtime(id)?
                    .is_running
                    .load(std::sync::atomic::Ordering::SeqCst),
            ),
            PropertyId::DeviceWidth => {
                Scalar::Integer(i64::from(self.runtime(id)?.device_size().width))
            }
            PropertyId::DeviceHeight => {
                Scalar::Integer(i64::from(self.runtime(id)?.device_size().height))
            }
            PropertyId::ParentSize => Scalar::Size(self.parent_size(id)?),
            PropertyId::ParentWidth => Scalar::Integer(i64::from(self.parent_size(id)?.width)),
            PropertyId::ParentHeight => Scalar::Integer(i64::from(self.parent_size(id)?.height)),
            PropertyId::ScreenPosition => {
                let screen = self.screen_bounds();
                Scalar::Point(Point::new(screen.x, screen.y))
            }
            PropertyId::ScreenBounds => Scalar::Rectangle(self.screen_bounds()),
            PropertyId::PointerPosition => {
                let shared = self.runtime(id)?;
                match lock(&shared.input).pointer {
                    Some((column, row)) => Scalar::Point(Point::new(column, row)),
                    None => Scalar::Null,
                }
            }
            PropertyId::Layer => Scalar::Integer(i64::from(self.core.lock().layer)),
            PropertyId::IsVisible => Scalar::Bool(self.core.lock().is_visible),
        })
    }
}

/// The surface behind a context's `target`, as an expression environment.
pub fn environment_from_context(context: &Bound<'_, PyAny>) -> PyResult<SurfaceEnv> {
    let target = context
        .getattr("target")
        .map_err(|_| PyTypeError::new_err("evaluate() needs an EvaluationContext with a target"))?;
    let surface = target
        .extract::<PyRef<'_, PySurface>>()
        .map_err(|_| PyTypeError::new_err("the context's target must be a Buffer or a Region"))?;
    let mut environment = surface.environment();
    if let Ok(runtime) = context.getattr("runtime")
        && !runtime.is_none()
        && let Some(shared) = crate::runtime::shared_of(&runtime)
    {
        environment.shared = Some(shared);
    }
    Ok(environment)
}

/// Apply an operation object to the context's target.
pub fn apply_with_context(
    context: &Bound<'_, PyAny>,
    operation: &Bound<'_, PyAny>,
    native: Option<Arc<Operation>>,
) -> PyResult<()> {
    let target = context.getattr("target")?;
    let _ = native;
    apply_operations(&target, std::slice::from_ref(operation))
}

fn default_registry(py: Python<'_>) -> PyResult<Bound<'_, PyAny>> {
    py.import("xnano_core._xnano_core._core_types")?
        .getattr("default_registry")?
        .call0()
}

/// Apply operations in order to a surface object.
pub fn apply_operations(
    surface: &Bound<'_, PyAny>,
    operations: &[Bound<'_, PyAny>],
) -> PyResult<()> {
    let py = surface.py();
    let (target, environment, ext) = {
        let guard = surface
            .extract::<PyRef<'_, PySurface>>()
            .map_err(|_| PyTypeError::new_err("operations apply to a Buffer or a Region"))?;
        guard.bounds()?;
        (guard.target(), guard.environment(), Arc::clone(&guard.ext))
    };
    for operation in operations {
        match operation_of(operation)? {
            Some(native) => {
                let has_runtime = environment.shared.is_some() && target.core.lock().is_mounted;
                let mut context = ApplyContext {
                    environment: &environment,
                    has_runtime,
                    deferred: Vec::new(),
                };
                native
                    .apply(&target, &mut context)
                    .map_err(|error| operation_error(py, &error))?;
                for deferred in context.deferred {
                    run_deferred(&environment, &target, deferred)?;
                }
            }
            None => {
                if operation.hasattr("apply_to_surface")? {
                    operation.call_method1("apply_to_surface", (surface,))?;
                    continue;
                }
                let explicit = lock(&ext.registry)
                    .as_ref()
                    .map(|registry| registry.bind(py).clone());
                let registry = match explicit {
                    Some(registry) => registry,
                    None => match environment
                        .shared
                        .as_ref()
                        .and_then(|shared| crate::runtime::runtime_object(py, shared))
                    {
                        Some(runtime) => runtime.bind(py).getattr("registry")?,
                        None => default_registry(py)?,
                    },
                };
                let handler = registry.call_method1("resolve", (operation,))?;
                let evaluation = py
                    .import("xnano_core._xnano_core._core_types")?
                    .getattr("EvaluationContext")?;
                let buffer = buffer_of(surface)?;
                let runtime = environment
                    .shared
                    .as_ref()
                    .and_then(|shared| crate::runtime::runtime_object(py, shared));
                let options = PyDict::new(py);
                options.set_item("buffer", buffer)?;
                options.set_item("target", surface)?;
                options.set_item("runtime", runtime)?;
                let context = evaluation.call((), Some(&options))?;
                handler.call1((context, operation))?;
            }
        }
    }
    nudge(&target.core);
    Ok(())
}

fn run_deferred(environment: &SurfaceEnv, target: &Target, deferred: Deferred) -> PyResult<()> {
    let Some(shared) = environment.shared.clone() else {
        return Ok(());
    };
    match deferred {
        Deferred::StartEffect(spec) => {
            let key = spec.read().key.clone();
            shared.start_effect(RunningEffect {
                key,
                run: xnano_terminal_runtime::effects::EffectRun::new(spec),
                placement: xnano_terminal_runtime::effects::Placement::default(),
                target: Arc::clone(&target.core),
                region: target.region,
                is_paused: false,
                is_cancelled: false,
                completed: Vec::new(),
                error: None,
            });
        }
        Deferred::CancelEffect(key) => shared.cancel_effect(&key),
        Deferred::AnimateDrawing {
            animation,
            x,
            y,
            encoding,
            start_milliseconds,
        } => {
            let _ = start_milliseconds;
            shared.start_animation(DrawingAnimationStart {
                animation,
                target: Arc::clone(&target.core),
                region: target.region,
                x,
                y,
                encoding,
                start_milliseconds: (shared.clock.elapsed_seconds() * 1000.0) as i64
                    - start_milliseconds,
            });
        }
    }
    Ok(())
}

/// The Python `Buffer` that owns a surface object.
pub fn buffer_of<'py>(surface: &Bound<'py, PyAny>) -> PyResult<Bound<'py, PyAny>> {
    if let Ok(region) = surface.extract::<PyRef<'_, PyRegion>>() {
        return Ok(region.buffer.bind(surface.py()).clone().into_any());
    }
    Ok(surface.clone())
}

#[pymethods]
impl PySurface {
    fn __traverse__(&self, visit: PyVisit<'_>) -> Result<(), PyTraverseError> {
        if self.region.is_some() {
            return Ok(());
        }
        if let Ok(children) = self.ext.children.try_lock() {
            for child in children.iter() {
                visit.call(child)?;
            }
        }
        if let Ok(registry) = self.ext.registry.try_lock()
            && let Some(registry) = registry.as_ref()
        {
            visit.call(registry)?;
        }
        if let Ok(hooks) = self.ext.hooks.try_lock() {
            for hook in hooks.iter() {
                visit.call(&hook.callback)?;
            }
        }
        Ok(())
    }

    fn __clear__(&self) {
        if self.region.is_some() {
            return;
        }
        if let Ok(mut children) = self.ext.children.try_lock() {
            children.clear();
        }
        if let Ok(mut registry) = self.ext.registry.try_lock() {
            *registry = None;
        }
        if let Ok(mut hooks) = self.ext.hooks.try_lock() {
            hooks.clear();
        }
    }

    #[getter]
    fn width(&self) -> PyResult<i32> {
        Ok(self.dimensions()?.0)
    }

    #[getter]
    fn height(&self) -> PyResult<i32> {
        Ok(self.dimensions()?.1)
    }

    fn __getitem__<'py>(
        slf: &Bound<'py, Self>,
        key: &Bound<'py, PyAny>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let (width, height) = slf.borrow().dimensions()?;
        let Ok(pair) = key.cast::<PyTuple>() else {
            return Err(PyTypeError::new_err(
                "index a surface with (column, row) for a cell or (columns, rows) slices for a region, \
                 for example buffer[0, 0] or buffer[0:4, 0:2]",
            ));
        };
        if pair.len() != 2 {
            return Err(PyTypeError::new_err(
                "a surface index has two parts: (column, row)",
            ));
        }
        let (first, second) = (pair.get_item(0)?, pair.get_item(1)?);
        if let (Ok(columns), Ok(rows)) = (first.cast::<PySlice>(), second.cast::<PySlice>()) {
            let (left, right) = slice_range(columns, width)?;
            let (top, bottom) = slice_range(rows, height)?;
            let surface = slf.borrow();
            let origin = surface.region.unwrap_or_default();
            let bounds =
                Rectangle::new(origin.x + left, origin.y + top, right - left, bottom - top);
            let buffer = buffer_of(slf.as_any())?.cast_into::<PyBuffer>()?;
            return Ok(Bound::new(
                py,
                PyClassInitializer::from(PySurface {
                    core: Arc::clone(&surface.core),
                    ext: Arc::clone(&surface.ext),
                    region: Some(bounds),
                })
                .add_subclass(PyRegion {
                    buffer: buffer.unbind(),
                }),
            )?
            .into_any());
        }
        let column = as_index(&first, width, "column")?;
        let row = as_index(&second, height, "row")?;
        let surface = slf.borrow();
        let bounds = surface.bounds()?;
        let state = surface.core.lock();
        let (x, y) = (bounds.left + column as u16, bounds.top + row as u16);
        let cell = state.grid.cell(x, y).cloned().unwrap_or(Cell::EMPTY);
        let is_transparent = state.grid.is_transparent(x, y);
        drop(state);
        Ok(Bound::new(
            py,
            PyCell {
                cell,
                is_transparent,
            },
        )?
        .into_any())
    }

    fn __setitem__(&self, key: &Bound<'_, PyAny>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let (width, height) = self.dimensions()?;
        let pair = key.cast::<PyTuple>().map_err(|_| {
            PyTypeError::new_err(
                "assign a cell with (column, row), for example buffer[0, 0] = \"x\"",
            )
        })?;
        if pair.len() != 2 {
            return Err(PyTypeError::new_err(
                "a surface index has two parts: (column, row)",
            ));
        }
        let column = as_index(&pair.get_item(0)?, width, "column")?;
        let row = as_index(&pair.get_item(1)?, height, "row")?;
        let (cell, columns, is_transparent) = cell_from(value)?;
        self.edit(|grid, bounds| {
            grid.put(
                bounds.left + column as u16,
                bounds.top + row as u16,
                cell,
                columns,
                is_transparent,
            );
        })
    }

    #[pyo3(signature = (text, *, x = 0, y = 0, style = None, mode = "replace"))]
    fn write(
        &self,
        text: &Bound<'_, PyAny>,
        x: i32,
        y: i32,
        style: Option<&Bound<'_, PyAny>>,
        mode: &str,
    ) -> PyResult<()> {
        let lines = text_lines(text)?;
        let style = style_arg(style)?;
        let mode = WriteMode::from_name(mode).ok_or_else(|| {
            PyValueError::new_err(format!(
                "\"{mode}\" is not a write mode; use \"replace\" or \"preserve_background\""
            ))
        })?;
        self.edit(|grid, bounds| grid.write_lines(bounds, &lines, x, y, style, mode))
    }

    #[pyo3(signature = (cell = None))]
    fn fill(&self, cell: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let (cell, columns, is_transparent) = match cell {
            Some(value) => cell_from(value)?,
            None => (Cell::EMPTY, 1, false),
        };
        if columns != 1 {
            return Err(PyValueError::new_err(
                "fill needs a symbol that takes one column; fill wide characters with write()",
            ));
        }
        self.edit(|grid, bounds| grid.fill(bounds, &cell, is_transparent))
    }

    #[pyo3(signature = (*, encoding = "half_blocks"))]
    fn pixels(slf: &Bound<'_, Self>, encoding: &str) -> PyResult<PyPixelView> {
        let encoding = PixelEncoding::from_name(encoding).ok_or_else(|| {
            PyValueError::new_err(format!(
                "\"{encoding}\" is not a pixel encoding; use \"half_blocks\" or \"braille\""
            ))
        })?;
        slf.borrow().bounds()?;
        Ok(PyPixelView {
            surface: slf.clone().into_any().unbind(),
            encoding,
        })
    }

    #[pyo3(signature = (*operations))]
    fn update(slf: &Bound<'_, Self>, operations: &Bound<'_, PyTuple>) -> PyResult<()> {
        let operations: Vec<Bound<'_, PyAny>> = operations.iter().collect();
        apply_operations(slf.as_any(), &operations)
    }

    fn __or__<'py>(
        slf: &Bound<'py, Self>,
        operation: &Bound<'py, PyAny>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        if operation.hasattr("__xnano_operation__")? {
            return Ok(py.NotImplemented().into_bound(py));
        }
        if operation.is_instance_of::<crate::expressions::PyOperation>() {
            apply_operations(slf.as_any(), std::slice::from_ref(operation))?;
            return Ok(slf.clone().into_any());
        }
        if let Ok(style) = operation.extract::<PyRef<'_, crate::style::PyStyle>>() {
            let step = Operation::ApplyStyle(style.inner);
            let native = Bound::new(
                py,
                PyClassInitializer::from(PyExpression {
                    kind: ExpressionKind::Operation(Some(Arc::new(step))),
                })
                .add_subclass(crate::expressions::PyOperation),
            )?;
            apply_operations(slf.as_any(), std::slice::from_ref(native.as_any()))?;
            return Ok(slf.clone().into_any());
        }
        Ok(py.NotImplemented().into_bound(py))
    }

    fn inspect<'py>(
        &self,
        py: Python<'py>,
        expression: &Bound<'py, PyAny>,
    ) -> PyResult<Bound<'py, PyAny>> {
        self.bounds()?;
        let holder = expression
            .extract::<PyRef<'_, PyExpression>>()
            .map_err(|_| {
                PyTypeError::new_err("inspect() needs an Expression such as Width or TimeElapsed")
            })?;
        if !matches!(holder.kind, ExpressionKind::Value(_)) {
            return Err(PyTypeError::new_err(
                "inspect() reads values; apply operations with update() instead",
            ));
        }
        let expr = expression_of(expression)?;
        let environment = self.environment();
        let scalar = expr
            .evaluate(&environment)
            .map_err(|error| eval_error(&error))?;
        crate::convert::scalar_to_py(py, &scalar)
    }

    fn supports(&self, py: Python<'_>, operation: &Bound<'_, PyType>) -> PyResult<bool> {
        if crate::operations::is_native_operation_type(py, operation)? {
            return Ok(true);
        }
        let registry = match lock(&self.ext.registry).as_ref() {
            Some(registry) => registry.bind(py).clone(),
            None => default_registry(py)?,
        };
        registry.call_method1("supports", (operation,))?.extract()
    }

    #[pyo3(signature = (callback, *, condition = None, events = None, priority = 0, once = false))]
    fn add_hook(
        &self,
        py: Python<'_>,
        callback: Py<PyAny>,
        condition: Option<&Bound<'_, PyAny>>,
        events: Option<&Bound<'_, PyAny>>,
        priority: i32,
        once: bool,
    ) -> PyResult<PyHook> {
        if !callback.bind(py).is_callable() {
            return Err(PyTypeError::new_err("a hook callback must be callable"));
        }
        let events = match events {
            Some(names) => HookEvent::parse_all(names)?,
            None => vec![HookEvent::parse("tick")?],
        };
        let condition = condition
            .filter(|value| !value.is_none())
            .map(expression_of)
            .transpose()?;
        let entry = Arc::new(HookEntry::new(
            callback,
            condition,
            events,
            None,
            priority,
            once,
            self.region,
        ));
        let hook = PyHook::new(Arc::clone(&entry.state));
        {
            let mut hooks = lock(&self.ext.hooks);
            hooks.retain(|existing| {
                !existing
                    .state
                    .is_cancelled
                    .load(std::sync::atomic::Ordering::SeqCst)
            });
            hooks.push(entry);
        }
        Ok(hook)
    }

    #[pyo3(signature = (condition = None, *, events = None, priority = 0, once = false))]
    fn hook<'py>(
        slf: &Bound<'py, Self>,
        condition: Option<Py<PyAny>>,
        events: Option<Py<PyAny>>,
        priority: i32,
        once: bool,
    ) -> PyResult<Bound<'py, PyCFunction>> {
        let py = slf.py();
        let target = slf.clone().unbind();
        PyCFunction::new_closure(
            py,
            None,
            None,
            move |arguments: &Bound<'_, PyTuple>, _| -> PyResult<Py<PyAny>> {
                let py = arguments.py();
                let callback = arguments.get_item(0)?;
                let options = PyDict::new(py);
                options.set_item(
                    "condition",
                    condition.as_ref().map(|value| value.clone_ref(py)),
                )?;
                options.set_item("events", events.as_ref().map(|value| value.clone_ref(py)))?;
                options.set_item("priority", priority)?;
                options.set_item("once", once)?;
                target
                    .bind(py)
                    .call_method("add_hook", (&callback,), Some(&options))?;
                Ok(callback.unbind())
            },
        )
    }

    #[pyo3(signature = (area = None))]
    fn invalidate(&self, area: Option<&PyRectangle>) -> PyResult<()> {
        self.bounds()?;
        {
            let mut state = self.core.lock();
            state.touch(area.map(|area| area.inner));
        }
        nudge(&self.core);
        Ok(())
    }

    fn to_cell_grid<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyBytes>> {
        let bounds = self.bounds()?;
        let packed = {
            let state = self.core.lock();
            // The whole grid is packed in place; only a part needs a copy.
            if bounds == state.grid.bounds() {
                xnano_terminal_cells::pack(state.grid.buffer())
            } else {
                xnano_terminal_cells::pack(&state.grid.region_buffer(bounds))
            }
        }
        .map_err(|error| crate::errors::CellGridError::new_err(error.to_string()))?;
        Ok(PyBytes::new(py, &packed))
    }
}

#[pyclass(name = "Region", module = "xnano_core._xnano_core", extends = PySurface, subclass)]
pub struct PyRegion {
    pub buffer: Py<PyBuffer>,
}

#[pymethods]
impl PyRegion {
    #[getter]
    fn buffer(&self, py: Python<'_>) -> Py<PyBuffer> {
        self.buffer.clone_ref(py)
    }

    #[getter]
    fn bounds(slf: &Bound<'_, Self>) -> PyRectangle {
        PyRectangle {
            inner: slf.as_super().borrow().region.unwrap_or_default(),
        }
    }

    #[getter]
    fn is_valid(slf: &Bound<'_, Self>) -> bool {
        slf.as_super().borrow().bounds().is_ok()
    }

    fn copy(slf: &Bound<'_, Self>) -> PyResult<Py<PyBuffer>> {
        let py = slf.py();
        let surface = slf.as_super().borrow();
        let bounds = surface.bounds()?;
        let (grid, fill) = {
            let state = surface.core.lock();
            (
                Grid::from_buffer(state.grid.region_buffer(bounds)),
                state.fill.clone(),
            )
        };
        new_buffer(py, grid, 0, 0, fill, None)
    }

    fn __repr__(slf: &Bound<'_, Self>) -> String {
        let region = slf.as_super().borrow().region.unwrap_or_default();
        format!(
            "Region(x={}, y={}, width={}, height={})",
            region.x, region.y, region.width, region.height
        )
    }
}

/// Create a Python `Buffer` around a grid.
pub fn new_buffer(
    py: Python<'_>,
    grid: Grid,
    x: i32,
    y: i32,
    fill: Cell,
    registry: Option<Py<PyAny>>,
) -> PyResult<Py<PyBuffer>> {
    let core = BufferCore::new(grid, x, y, fill);
    let ext = Arc::new(BufferExt::default());
    *lock(&ext.registry) = registry;
    core.lock().extension = Some(Arc::clone(&ext) as Arc<dyn Any + Send + Sync>);
    Py::new(
        py,
        PyClassInitializer::from(PySurface {
            core,
            ext,
            region: None,
        })
        .add_subclass(PyBuffer),
    )
}

#[pyclass(name = "Buffer", module = "xnano_core._xnano_core", extends = PySurface, subclass)]
pub struct PyBuffer;

fn grid_for(
    lines: &[xnano_terminal_runtime::text::Line],
    width: i32,
    height: i32,
    style: Style,
) -> PyResult<Grid> {
    let (columns, rows) = check_size(width, height).map_err(PyValueError::new_err)?;
    let mut grid = Grid::filled(columns, rows, &styled_blank(style));
    let bounds = grid.bounds();
    grid.write_lines(bounds, lines, 0, 0, style, WriteMode::Replace);
    Ok(grid)
}

fn paste_mode(mode: &str) -> PyResult<PasteMode> {
    PasteMode::from_name(mode).ok_or_else(|| {
        PyValueError::new_err(format!(
            "\"{mode}\" is not a blend mode; use \"replace\", \"preserve_background\" or \"transparent\""
        ))
    })
}

fn tree_error(error: &xnano_terminal_runtime::buffer::TreeError) -> PyErr {
    PyValueError::new_err(error.to_string())
}

#[pymethods]
impl PyBuffer {
    #[new]
    #[pyo3(signature = (content = None, *, width = None, height = None, x = 0, y = 0, style = None, registry = None))]
    fn new(
        content: Option<&Bound<'_, PyAny>>,
        width: Option<i32>,
        height: Option<i32>,
        x: i32,
        y: i32,
        style: Option<&Bound<'_, PyAny>>,
        registry: Option<Py<PyAny>>,
    ) -> PyResult<PyClassInitializer<Self>> {
        let style = style_arg(style)?;
        let lines = match content.filter(|value| !value.is_none()) {
            Some(content) => text_lines(content)?,
            None => Vec::new(),
        };
        let natural_width = lines
            .iter()
            .map(|line| {
                line.iter()
                    .map(|span| xnano_terminal_runtime::text::display_width(&span.text))
                    .sum::<usize>()
            })
            .max()
            .unwrap_or(0) as i32;
        let grid = grid_for(
            &lines,
            width.unwrap_or(natural_width),
            height.unwrap_or(lines.len() as i32),
            style,
        )?;
        let core = BufferCore::new(grid, x, y, styled_blank(style));
        let ext = Arc::new(BufferExt::default());
        *lock(&ext.registry) = registry;
        core.lock().extension = Some(Arc::clone(&ext) as Arc<dyn Any + Send + Sync>);
        Ok(PyClassInitializer::from(PySurface {
            core,
            ext,
            region: None,
        })
        .add_subclass(Self))
    }

    #[getter]
    fn x(slf: &Bound<'_, Self>) -> i32 {
        slf.as_super().borrow().core.lock().x
    }

    #[setter]
    fn set_x(slf: &Bound<'_, Self>, value: i32) {
        let core = Arc::clone(&slf.as_super().borrow().core);
        let y = core.lock().y;
        core.move_to(value, y);
        nudge(&core);
    }

    #[getter]
    fn y(slf: &Bound<'_, Self>) -> i32 {
        slf.as_super().borrow().core.lock().y
    }

    #[setter]
    fn set_y(slf: &Bound<'_, Self>, value: i32) {
        let core = Arc::clone(&slf.as_super().borrow().core);
        let x = core.lock().x;
        core.move_to(x, value);
        nudge(&core);
    }

    #[getter]
    fn width(slf: &Bound<'_, Self>) -> i32 {
        slf.as_super().borrow().core.lock().width()
    }

    #[getter]
    fn height(slf: &Bound<'_, Self>) -> i32 {
        slf.as_super().borrow().core.lock().height()
    }

    #[setter]
    fn set_width(slf: &Bound<'_, Self>, value: i32) -> PyResult<()> {
        let core = Arc::clone(&slf.as_super().borrow().core);
        let height = core.lock().height();
        core.resize(value, height).map_err(PyValueError::new_err)?;
        nudge(&core);
        Ok(())
    }

    #[setter]
    fn set_height(slf: &Bound<'_, Self>, value: i32) -> PyResult<()> {
        let core = Arc::clone(&slf.as_super().borrow().core);
        let width = core.lock().width();
        core.resize(width, value).map_err(PyValueError::new_err)?;
        nudge(&core);
        Ok(())
    }

    #[getter]
    fn position(slf: &Bound<'_, Self>) -> PyPoint {
        let state = slf.as_super().borrow().core.lock().bounds();
        PyPoint {
            inner: Point::new(state.x, state.y),
        }
    }

    #[setter]
    fn set_position(slf: &Bound<'_, Self>, value: &PyPoint) {
        let core = Arc::clone(&slf.as_super().borrow().core);
        core.move_to(value.inner.x, value.inner.y);
        nudge(&core);
    }

    #[getter]
    fn size(slf: &Bound<'_, Self>) -> PySize {
        let state = slf.as_super().borrow().core.lock().bounds();
        PySize {
            inner: Size::new(state.width, state.height),
        }
    }

    #[setter]
    fn set_size(slf: &Bound<'_, Self>, value: &PySize) -> PyResult<()> {
        let core = Arc::clone(&slf.as_super().borrow().core);
        core.resize(value.inner.width, value.inner.height)
            .map_err(PyValueError::new_err)?;
        nudge(&core);
        Ok(())
    }

    #[getter]
    fn bounds(slf: &Bound<'_, Self>) -> PyRectangle {
        PyRectangle {
            inner: slf.as_super().borrow().core.lock().bounds(),
        }
    }

    /// The buffer's bounds in the coordinates of its root.
    #[getter]
    fn _absolute_bounds(slf: &Bound<'_, Self>) -> PyRectangle {
        let core = Arc::clone(&slf.as_super().borrow().core);
        let origin = xnano_terminal_runtime::buffer::absolute_origin(&core);
        let state = core.lock();
        PyRectangle {
            inner: Rectangle::new(origin.0, origin.1, state.width(), state.height()),
        }
    }

    #[getter]
    fn layer(slf: &Bound<'_, Self>) -> i32 {
        slf.as_super().borrow().core.lock().layer
    }

    #[setter]
    fn set_layer(slf: &Bound<'_, Self>, value: i32) {
        let core = Arc::clone(&slf.as_super().borrow().core);
        {
            let mut state = core.lock();
            state.layer = value;
            state.touch(None);
        }
        if let Some(parent) = core.parent() {
            parent.lock().touch(None);
        }
        nudge(&core);
    }

    #[getter]
    fn is_visible(slf: &Bound<'_, Self>) -> bool {
        slf.as_super().borrow().core.lock().is_visible
    }

    #[setter]
    fn set_is_visible(slf: &Bound<'_, Self>, value: bool) {
        let core = Arc::clone(&slf.as_super().borrow().core);
        {
            let mut state = core.lock();
            state.is_visible = value;
            state.touch(None);
        }
        if let Some(parent) = core.parent() {
            parent.lock().touch(None);
        }
        nudge(&core);
    }

    #[getter]
    fn is_focusable(slf: &Bound<'_, Self>) -> bool {
        slf.as_super().borrow().core.lock().is_focusable
    }

    #[setter]
    fn set_is_focusable(slf: &Bound<'_, Self>, value: bool) {
        slf.as_super().borrow().core.lock().is_focusable = value;
    }

    #[getter]
    fn content(slf: &Bound<'_, Self>) -> PyResult<Py<PyRegion>> {
        whole_region(slf)
    }

    #[setter]
    fn set_content(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let lines = text_lines(value)?;
        let surface = slf.as_super().borrow();
        let fill = surface.core.lock().fill.clone();
        surface.edit(|grid, bounds| {
            grid.fill(bounds, &fill, false);
            grid.write_lines(bounds, &lines, 0, 0, Style::default(), WriteMode::Replace);
        })
    }

    #[getter]
    fn cells(slf: &Bound<'_, Self>) -> PyResult<Py<PyRegion>> {
        whole_region(slf)
    }

    #[getter]
    fn text(slf: &Bound<'_, Self>) -> String {
        slf.as_super()
            .borrow()
            .core
            .lock()
            .grid
            .text_rows()
            .join("\n")
    }

    #[getter]
    fn revision(slf: &Bound<'_, Self>) -> u64 {
        slf.as_super().borrow().core.lock().revision
    }

    #[getter]
    fn registry<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let ext = Arc::clone(&slf.as_super().borrow().ext);
        let stored = lock(&ext.registry)
            .as_ref()
            .map(|registry| registry.bind(py).clone());
        match stored {
            Some(registry) => Ok(registry),
            None => default_registry(py),
        }
    }

    #[getter]
    fn children<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyTuple>> {
        let py = slf.py();
        let ext = Arc::clone(&slf.as_super().borrow().ext);
        let children: Vec<Py<PyBuffer>> = lock(&ext.children)
            .iter()
            .map(|child| child.clone_ref(py))
            .collect();
        PyTuple::new(py, children)
    }

    #[classmethod]
    #[pyo3(signature = (text, *, style = None))]
    fn with_text(
        cls: &Bound<'_, PyType>,
        text: &Bound<'_, PyAny>,
        style: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Py<PyAny>> {
        let options = PyDict::new(cls.py());
        options.set_item("style", style)?;
        Ok(cls.call((text,), Some(&options))?.unbind())
    }

    #[classmethod]
    fn with_size(cls: &Bound<'_, PyType>, width: i32, height: i32) -> PyResult<Py<PyAny>> {
        let options = PyDict::new(cls.py());
        options.set_item("width", width)?;
        options.set_item("height", height)?;
        Ok(cls.call((), Some(&options))?.unbind())
    }

    #[classmethod]
    #[pyo3(signature = (cells, *, width, height))]
    fn with_cells(
        cls: &Bound<'_, PyType>,
        cells: &Bound<'_, PyAny>,
        width: i32,
        height: i32,
    ) -> PyResult<Py<PyAny>> {
        let py = cls.py();
        let (columns, rows) = check_size(width, height).map_err(PyValueError::new_err)?;
        let mut collected = Vec::new();
        for item in cells.try_iter()? {
            collected.push(cell_from(&item?)?);
        }
        if collected.len() != usize::from(columns) * usize::from(rows) {
            return Err(PyValueError::new_err(format!(
                "a {width} x {height} buffer needs {} cells but {} were given; pass width * height \
                 cells in row-major order",
                usize::from(columns) * usize::from(rows),
                collected.len()
            )));
        }
        let mut grid = Grid::new(columns, rows);
        for (index, (cell, columns_covered, transparent)) in collected.into_iter().enumerate() {
            let (x, y) = (
                (index % usize::from(columns)) as u16,
                (index / usize::from(columns)) as u16,
            );
            grid.put(x, y, cell, columns_covered, transparent);
        }
        let buffer = cls.call0().or_else(|_| cls.call1(("",)))?;
        let surface = buffer.extract::<PyRef<'_, PySurface>>()?;
        {
            let mut state = surface.core.lock();
            state.grid = grid;
            state.intrinsic = Size::new(width, height);
            state.touch(None);
        }
        let _ = py;
        drop(surface);
        Ok(buffer.unbind())
    }

    #[classmethod]
    fn from_cell_grid(cls: &Bound<'_, PyType>, packed: &[u8]) -> PyResult<Py<PyAny>> {
        let grid = xnano_terminal_cells::unpack(packed)
            .map_err(|error| crate::errors::CellGridError::new_err(error.to_string()))?;
        buffer_from_grid(cls, Grid::from_buffer(grid))
    }

    #[classmethod]
    #[pyo3(signature = (packed, *, start_milliseconds = 0))]
    fn from_cell_animation(
        cls: &Bound<'_, PyType>,
        packed: &[u8],
        start_milliseconds: i64,
    ) -> PyResult<Py<PyAny>> {
        let animation = xnano_terminal_cells::unpack_animation(packed)
            .map_err(|error| crate::errors::CellGridError::new_err(error.to_string()))?;
        let index = animation.frame_index_at(start_milliseconds);
        let frame = animation.frames[index].grid.clone();
        buffer_from_grid(cls, Grid::from_buffer(frame))
    }

    fn region(slf: &Bound<'_, Self>, bounds: &PyRectangle) -> PyResult<Py<PyRegion>> {
        let py = slf.py();
        let surface = slf.as_super().borrow();
        let (width, height) = {
            let state = surface.core.lock();
            (state.width(), state.height())
        };
        let area = Rectangle::new(0, 0, width, height);
        if bounds.inner.intersection(area) != bounds.inner && !bounds.inner.is_empty() {
            return Err(PyValueError::new_err(format!(
                "the region ({}, {}, {}, {}) does not fit inside the {width} x {height} buffer; \
                 choose bounds within the buffer",
                bounds.inner.x, bounds.inner.y, bounds.inner.width, bounds.inner.height
            )));
        }
        Py::new(
            py,
            PyClassInitializer::from(PySurface {
                core: Arc::clone(&surface.core),
                ext: Arc::clone(&surface.ext),
                region: Some(bounds.inner),
            })
            .add_subclass(PyRegion {
                buffer: slf.clone().unbind(),
            }),
        )
    }

    fn resize(slf: &Bound<'_, Self>, width: i32, height: i32) -> PyResult<()> {
        let core = Arc::clone(&slf.as_super().borrow().core);
        core.resize(width, height).map_err(PyValueError::new_err)?;
        nudge(&core);
        Ok(())
    }

    #[pyo3(signature = (source, *, x = 0, y = 0, mode = "replace"))]
    fn paste(
        slf: &Bound<'_, Self>,
        source: &Bound<'_, PyAny>,
        x: i32,
        y: i32,
        mode: &str,
    ) -> PyResult<()> {
        let mode = paste_mode(mode)?;
        let origin = source
            .extract::<PyRef<'_, PySurface>>()
            .map_err(|_| PyTypeError::new_err("paste needs a Buffer or a Region as its source"))?;
        let bounds = origin.bounds()?;
        let region = Grid::from_buffer(origin.core.lock().grid.region_buffer(bounds));
        drop(origin);
        let surface = slf.as_super().borrow();
        surface.edit(|grid, destination| grid.paste(destination, &region, x, y, mode))
    }

    #[pyo3(signature = (child, *, geometry = "explicit", mode = "replace"))]
    fn attach(
        slf: &Bound<'_, Self>,
        child: &Bound<'_, PyBuffer>,
        geometry: &str,
        mode: &str,
    ) -> PyResult<()> {
        let geometry = Geometry::from_name(geometry).ok_or_else(|| {
            PyValueError::new_err(format!(
                "\"{geometry}\" is not a geometry mode; use \"inherit\" or \"explicit\""
            ))
        })?;
        let mode = paste_mode(mode)?;
        let parent_core = Arc::clone(&slf.as_super().borrow().core);
        let (child_core, ()) = {
            let borrowed = child.as_super().borrow();
            (Arc::clone(&borrowed.core), ())
        };
        attach(&parent_core, &child_core, geometry, mode).map_err(|error| tree_error(&error))?;
        let ext = Arc::clone(&slf.as_super().borrow().ext);
        lock(&ext.children).push(child.clone().unbind());
        if let Some(shared) = ext.shared() {
            let child_ext = child.as_super().borrow().ext.clone();
            *lock(&child_ext.runtime) = Some(Arc::downgrade(&shared));
            xnano_terminal_runtime::buffer::walk(&child_core, &mut |node| {
                node.lock().is_mounted = true;
            });
            shared.request_frame();
        }
        Ok(())
    }

    fn detach(slf: &Bound<'_, Self>, child: &Bound<'_, PyBuffer>) -> PyResult<()> {
        let parent_core = Arc::clone(&slf.as_super().borrow().core);
        let child_core = Arc::clone(&child.as_super().borrow().core);
        detach(&parent_core, &child_core).map_err(|error| tree_error(&error))?;
        let ext = Arc::clone(&slf.as_super().borrow().ext);
        lock(&ext.children).retain(|existing| !existing.is(child));
        if let Some(shared) = ext.shared() {
            let child_ext = child.as_super().borrow().ext.clone();
            *lock(&child_ext.runtime) = None;
            xnano_terminal_runtime::buffer::walk(&child_core, &mut |node| {
                node.lock().is_mounted = false;
            });
            shared.request_frame();
        }
        Ok(())
    }

    fn copy(slf: &Bound<'_, Self>) -> PyResult<Py<PyBuffer>> {
        copy_buffer(slf)
    }

    #[pyo3(signature = (*, format = "ansi"))]
    fn render(slf: &Bound<'_, Self>, format: &str) -> PyResult<String> {
        if format != "ansi" && format != "text" {
            return Err(PyValueError::new_err(format!(
                "\"{format}\" is not a render format; use \"ansi\" or \"text\""
            )));
        }
        let core = Arc::clone(&slf.as_super().borrow().core);
        relayout(&core);
        crate::widgets::refresh_tree(&core)?;
        let (width, height, x, y) = {
            let state = core.lock();
            (state.grid.width(), state.grid.height(), state.x, state.y)
        };
        let mut output = Grid::new(width, height);
        let clip = Rectangle::new(0, 0, i32::from(width), i32::from(height));
        compose(&core, &mut output, (-x, -y), clip, PasteMode::Transparent);
        Ok(if format == "text" {
            output.text_rows().join("\n")
        } else {
            xnano_terminal_cells::ansi(output.buffer())
        })
    }

    #[pyo3(signature = (*, runtime = None))]
    fn __call__(slf: &Bound<'_, Self>, runtime: Option<Py<PyAny>>) -> PyResult<Py<PyAny>> {
        let py = slf.py();
        let rendering = py
            .import("xnano_core._xnano_core._core_types")?
            .getattr("Rendering")?;
        Ok(rendering.call1((slf, runtime))?.unbind())
    }

    fn __repr__(slf: &Bound<'_, Self>) -> String {
        let state = slf.as_super().borrow().core.lock().bounds();
        format!(
            "Buffer(x={}, y={}, width={}, height={})",
            state.x, state.y, state.width, state.height
        )
    }
}

fn whole_region(slf: &Bound<'_, PyBuffer>) -> PyResult<Py<PyRegion>> {
    let py = slf.py();
    let surface = slf.as_super().borrow();
    let (width, height) = {
        let state = surface.core.lock();
        (state.width(), state.height())
    };
    Py::new(
        py,
        PyClassInitializer::from(PySurface {
            core: Arc::clone(&surface.core),
            ext: Arc::clone(&surface.ext),
            region: Some(Rectangle::new(0, 0, width, height)),
        })
        .add_subclass(PyRegion {
            buffer: slf.clone().unbind(),
        }),
    )
}

fn buffer_from_grid(cls: &Bound<'_, PyType>, grid: Grid) -> PyResult<Py<PyAny>> {
    let buffer = cls.call0()?;
    let surface = buffer.extract::<PyRef<'_, PySurface>>()?;
    {
        let mut state = surface.core.lock();
        state.intrinsic = Size::new(i32::from(grid.width()), i32::from(grid.height()));
        state.grid = grid;
        state.touch(None);
    }
    drop(surface);
    Ok(buffer.unbind())
}

fn copy_buffer(slf: &Bound<'_, PyBuffer>) -> PyResult<Py<PyBuffer>> {
    let py = slf.py();
    let (grid, x, y, fill, layer, visible, focusable, layout, intrinsic, registry, children) = {
        let surface = slf.as_super().borrow();
        let state = surface.core.lock();
        let registry = lock(&surface.ext.registry)
            .as_ref()
            .map(|registry| registry.clone_ref(py));
        let children: Vec<(Py<PyBuffer>, Geometry, PasteMode)> = {
            let held = lock(&surface.ext.children);
            state
                .children
                .iter()
                .filter_map(|child| {
                    held.iter()
                        .find(|object| {
                            Arc::ptr_eq(&object.bind(py).as_super().borrow().core, &child.core)
                        })
                        .map(|object| (object.clone_ref(py), child.geometry, child.mode))
                })
                .collect()
        };
        (
            state.grid.clone(),
            state.x,
            state.y,
            state.fill.clone(),
            state.layer,
            state.is_visible,
            state.is_focusable,
            state.layout.clone(),
            state.intrinsic,
            registry,
            children,
        )
    };
    let copy = new_buffer(py, grid, x, y, fill, registry)?;
    {
        let bound = copy.bind(py);
        let surface = bound.as_super().borrow();
        let mut state = surface.core.lock();
        state.layer = layer;
        state.is_visible = visible;
        state.is_focusable = focusable;
        state.layout = layout;
        state.intrinsic = intrinsic;
    }
    for (child, geometry, mode) in children {
        let child_copy = copy_buffer(child.bind(py))?;
        let parent_core = Arc::clone(&copy.bind(py).as_super().borrow().core);
        let child_core = Arc::clone(&child_copy.bind(py).as_super().borrow().core);
        attach(&parent_core, &child_core, geometry, mode).map_err(|error| tree_error(&error))?;
        lock(&copy.bind(py).as_super().borrow().ext.children).push(child_copy);
    }
    Ok(copy)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyCell>()?;
    m.add_class::<PyPixelView>()?;
    m.add_class::<PySurface>()?;
    m.add_class::<PyRegion>()?;
    m.add_class::<PyBuffer>()?;
    Ok(())
}
