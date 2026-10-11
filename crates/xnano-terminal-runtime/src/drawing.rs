//! Schema-validated drawings that people and decision models can edit.
//!
//! Text drawings describe terminal glyphs. Palette drawings describe logical pixels:
//! every grapheme of a row is a palette symbol that maps to a color or to transparency.
//! A drawing is plain data; nothing in it is ever evaluated.

use indexmap::IndexMap;
use serde_json::{Value, json};
use unicode_segmentation::UnicodeSegmentation;
use xnano_terminal_cells::{AnimationFrame, CellAnimation};

use crate::grid::{Bounds, Grid, WriteMode};
use crate::pixel::{Pixel, PixelEncoding, PixelSpace, write_pixels};
use crate::style::Style;
use crate::text::{Line, Span, grapheme_width};

/// The largest width or height of a drawing, in columns or pixels.
pub const MAXIMUM_DRAWING_DIMENSION: usize = 4096;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DrawingKind {
    Text,
    Palette,
}

impl DrawingKind {
    pub fn name(self) -> &'static str {
        match self {
            Self::Text => "text",
            Self::Palette => "palette",
        }
    }

    pub fn from_name(name: &str) -> Option<Self> {
        Some(match name {
            "text" => Self::Text,
            "palette" => Self::Palette,
            _ => return None,
        })
    }
}

pub type Palette = IndexMap<String, Option<(u8, u8, u8)>>;

/// An immutable drawing.
#[derive(Debug, Clone, PartialEq)]
pub struct Drawing {
    pub kind: DrawingKind,
    pub rows: Vec<String>,
    pub palette: Palette,
}

fn row_width(kind: DrawingKind, row: &str) -> usize {
    match kind {
        DrawingKind::Text => row.graphemes(true).map(grapheme_width).sum(),
        DrawingKind::Palette => row.graphemes(true).count(),
    }
}

impl Drawing {
    /// Build a drawing, checking that it is well formed.
    pub fn new(kind: DrawingKind, rows: Vec<String>, palette: Palette) -> Result<Self, String> {
        let drawing = Self {
            kind,
            rows,
            palette,
        };
        drawing.check()?;
        Ok(drawing)
    }

    fn check(&self) -> Result<(), String> {
        if self.kind == DrawingKind::Text && !self.palette.is_empty() {
            return Err(
                "a text drawing has no palette; remove the palette or use kind=\"palette\""
                    .to_owned(),
            );
        }
        for symbol in self.palette.keys() {
            if symbol.graphemes(true).count() != 1 {
                return Err(format!(
                    "the palette symbol \"{symbol}\" must be exactly one character; use a \
                     single character such as \"#\" for each color"
                ));
            }
        }
        let width = self.width();
        for (index, row) in self.rows.iter().enumerate() {
            if row_width(self.kind, row) != width {
                return Err(format!(
                    "row {index} is {} wide but the first row is {width} wide; pad every row of \
                     a drawing to the same width",
                    row_width(self.kind, row)
                ));
            }
            if self.kind == DrawingKind::Palette {
                for symbol in row.graphemes(true) {
                    if !self.palette.contains_key(symbol) {
                        return Err(format!(
                            "row {index} uses the symbol \"{symbol}\", which is not in the \
                             palette; add it to the palette or change the row"
                        ));
                    }
                }
            } else if row.chars().any(char::is_control) {
                return Err(format!(
                    "row {index} holds a control character; drawings hold printable text only"
                ));
            }
        }
        if width > MAXIMUM_DRAWING_DIMENSION || self.rows.len() > MAXIMUM_DRAWING_DIMENSION {
            return Err(format!(
                "a drawing can be at most {MAXIMUM_DRAWING_DIMENSION} wide and tall"
            ));
        }
        Ok(())
    }

    /// Display columns for text; palette-symbol columns (pixels) for palette drawings.
    pub fn width(&self) -> usize {
        self.rows.first().map_or(0, |row| row_width(self.kind, row))
    }

    pub fn height(&self) -> usize {
        self.rows.len()
    }

    pub fn to_json(&self) -> Value {
        let mut value = json!({"kind": self.kind.name(), "rows": self.rows});
        if self.kind == DrawingKind::Palette {
            let palette: serde_json::Map<String, Value> = self
                .palette
                .iter()
                .map(|(symbol, color)| {
                    (
                        symbol.clone(),
                        color.map_or(Value::Null, |(red, green, blue)| json!([red, green, blue])),
                    )
                })
                .collect();
            value["palette"] = Value::Object(palette);
        }
        value
    }

    pub fn from_json(value: &Value) -> Result<Self, String> {
        let kind = value
            .get("kind")
            .and_then(Value::as_str)
            .and_then(DrawingKind::from_name)
            .ok_or("a drawing needs a \"kind\" of \"text\" or \"palette\"")?;
        let rows = value
            .get("rows")
            .and_then(Value::as_array)
            .ok_or("a drawing needs a list of \"rows\"")?
            .iter()
            .map(|row| {
                row.as_str()
                    .map(str::to_owned)
                    .ok_or("every row of a drawing must be text")
            })
            .collect::<Result<Vec<_>, _>>()?;
        let mut palette = Palette::new();
        if let Some(entries) = value.get("palette") {
            let entries = entries
                .as_object()
                .ok_or("a drawing's palette must be an object")?;
            for (symbol, color) in entries {
                let parsed = match color {
                    Value::Null => None,
                    Value::Array(channels) if channels.len() == 3 => {
                        let mut parts = [0_u8; 3];
                        for (slot, channel) in parts.iter_mut().zip(channels) {
                            *slot = channel
                                .as_u64()
                                .and_then(|number| u8::try_from(number).ok())
                                .ok_or("palette colors are three numbers from 0 to 255")?;
                        }
                        Some((parts[0], parts[1], parts[2]))
                    }
                    _ => {
                        return Err(
                            "palette colors are three numbers from 0 to 255, or null".to_owned()
                        );
                    }
                };
                palette.insert(symbol.clone(), parsed);
            }
        }
        Self::new(kind, rows, palette)
    }

    /// The pixels of a palette drawing, with transparent symbols skipped.
    pub fn pixels(&self) -> Vec<Pixel> {
        let mut pixels = Vec::new();
        for (row_index, row) in self.rows.iter().enumerate() {
            for (column_index, symbol) in row.graphemes(true).enumerate() {
                if let Some(Some(color)) = self.palette.get(symbol) {
                    pixels.push((column_index as i32, row_index as i32, *color));
                }
            }
        }
        pixels
    }

    /// The cell size of this drawing under `encoding`.
    pub fn cell_size(&self, encoding: PixelEncoding) -> (usize, usize) {
        match self.kind {
            DrawingKind::Text => (self.width(), self.height()),
            DrawingKind::Palette => (
                self.width().div_ceil(encoding.columns_per_cell() as usize),
                self.height().div_ceil(encoding.rows_per_cell() as usize),
            ),
        }
    }

    /// Draw onto `grid` with the top-left at `(x, y)` inside `bounds`.
    pub fn draw(&self, grid: &mut Grid, bounds: Bounds, x: i32, y: i32, encoding: PixelEncoding) {
        match self.kind {
            DrawingKind::Text => {
                let lines: Vec<Line> = self
                    .rows
                    .iter()
                    .map(|row| vec![Span::new(row.clone(), Style::default())])
                    .collect();
                grid.write_lines(bounds, &lines, x, y, Style::default(), WriteMode::Replace);
            }
            DrawingKind::Palette => {
                let space = PixelSpace { bounds, encoding };
                let shift_x = x * encoding.columns_per_cell();
                let shift_y = y * encoding.rows_per_cell();
                let pixels: Vec<Pixel> = self
                    .pixels()
                    .into_iter()
                    .map(|(column, row, color)| (column + shift_x, row + shift_y, color))
                    .collect();
                let _ = write_pixels(grid, space, &pixels, true);
            }
        }
    }

    /// A grid holding just this drawing; cells no pixel touched are transparent.
    pub fn to_grid(&self, encoding: PixelEncoding) -> Grid {
        let (columns, rows) = self.cell_size(encoding);
        let mut grid = Grid::new(
            columns.min(usize::from(u16::MAX)) as u16,
            rows.min(usize::from(u16::MAX)) as u16,
        );
        let bounds = grid.bounds();
        if self.kind == DrawingKind::Palette {
            grid.mark_all_transparent();
        }
        self.draw(&mut grid, bounds, 0, 0, encoding);
        grid
    }
}

/// One frame of a drawing animation.
#[derive(Debug, Clone, PartialEq)]
pub struct DrawingFrame {
    pub drawing: Drawing,
    pub duration_milliseconds: u32,
}

/// Frames shown in sequence.
#[derive(Debug, Clone, PartialEq)]
pub struct DrawingAnimation {
    pub frames: Vec<DrawingFrame>,
    pub should_loop: bool,
}

impl DrawingAnimation {
    /// The frames as equally sized grids, padded to the largest frame.
    pub fn to_cell_animation(&self, encoding: PixelEncoding) -> CellAnimation {
        let grids: Vec<Grid> = self
            .frames
            .iter()
            .map(|frame| frame.drawing.to_grid(encoding))
            .collect();
        let width = grids.iter().map(Grid::width).max().unwrap_or(0);
        let height = grids.iter().map(Grid::height).max().unwrap_or(0);
        CellAnimation {
            frames: grids
                .into_iter()
                .zip(&self.frames)
                .map(|(grid, frame)| {
                    let mut padded = Grid::new(width, height);
                    let bounds = padded.bounds();
                    padded.blit(bounds, &grid, 0, 0, crate::grid::BlitMode::Replace);
                    AnimationFrame {
                        grid: padded.into_buffer(),
                        duration_milliseconds: frame.duration_milliseconds,
                    }
                })
                .collect(),
            should_loop: self.should_loop,
        }
    }
}

/// Check a JSON value against the `x-xnano` `drawing` rule.
///
/// The rule arguments may set `kind`, `width`, `height`, `maximum_width`, `maximum_height`,
/// `allowed_symbols` and a fixed `palette`.
pub fn validate_drawing_rule(
    node: &xnano_terminal_state::Node,
    arguments: &Value,
) -> Vec<(Vec<String>, String)> {
    let value = node.to_json();
    let drawing = match Drawing::from_json(&value) {
        Ok(drawing) => drawing,
        Err(message) => return vec![(Vec::new(), message)],
    };
    let mut problems = Vec::new();
    if let Some(kind) = arguments.get("kind").and_then(Value::as_str)
        && drawing.kind.name() != kind
    {
        problems.push((
            vec!["kind".to_owned()],
            format!("expected a {kind} drawing"),
        ));
    }
    let limit = |key: &str, fallback: usize| {
        arguments
            .get(key)
            .and_then(Value::as_u64)
            .map_or(fallback, |number| number as usize)
    };
    for (key, actual, name) in [
        ("width", drawing.width(), "width"),
        ("height", drawing.height(), "height"),
    ] {
        if let Some(expected) = arguments.get(key).and_then(Value::as_u64)
            && actual != expected as usize
        {
            problems.push((
                Vec::new(),
                format!("the {name} must be {expected} but is {actual}"),
            ));
        }
    }
    let maximum_width = limit("maximum_width", 256);
    let maximum_height = limit("maximum_height", 256);
    if drawing.width() > maximum_width {
        problems.push((
            Vec::new(),
            format!(
                "the width {} is over the maximum of {maximum_width}",
                drawing.width()
            ),
        ));
    }
    if drawing.height() > maximum_height {
        problems.push((
            Vec::new(),
            format!(
                "the height {} is over the maximum of {maximum_height}",
                drawing.height()
            ),
        ));
    }
    if let Some(allowed) = arguments.get("allowed_symbols").and_then(Value::as_array) {
        let allowed: Vec<&str> = allowed.iter().filter_map(Value::as_str).collect();
        for (index, row) in drawing.rows.iter().enumerate() {
            for symbol in row.graphemes(true) {
                if !allowed.contains(&symbol) {
                    problems.push((
                        vec!["rows".to_owned(), index.to_string()],
                        format!("the symbol \"{symbol}\" is not one of the allowed symbols"),
                    ));
                    break;
                }
            }
        }
    }
    if let Some(fixed) = arguments.get("palette").and_then(Value::as_object) {
        for symbol in drawing.palette.keys() {
            if !fixed.contains_key(symbol) {
                problems.push((
                    vec!["palette".to_owned(), symbol.clone()],
                    format!("the symbol \"{symbol}\" is not in the allowed palette"),
                ));
            }
        }
    }
    problems
}
