//! The cell store behind every buffer.
//!
//! A [`Grid`] is a ratatui buffer anchored at the origin, plus a mask of cells that were
//! explicitly marked transparent. Using ratatui's cell type means cell grids, widgets and
//! the terminal presenter all share one representation.

use ratatui_core::buffer::{Buffer, Cell, CellDiffOption, CellWidth};
use ratatui_core::layout::Rect;
use ratatui_core::style::Color;
use unicode_segmentation::UnicodeSegmentation;

use crate::style::Style;
use crate::text::{Line, grapheme_width};

/// The most cells a grid may hold.
pub const MAXIMUM_CELLS: usize = 4_000_000;

/// How text written over existing cells treats what is already there.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum WriteMode {
    /// The written cell replaces the old one completely.
    #[default]
    Replace,
    /// The written cell keeps the old background unless it sets its own.
    PreserveBackground,
}

impl WriteMode {
    pub fn from_name(name: &str) -> Option<Self> {
        Some(match name {
            "replace" => Self::Replace,
            "preserve_background" => Self::PreserveBackground,
            _ => return None,
        })
    }
}

/// How one grid is copied onto another.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum BlitMode {
    #[default]
    Replace,
    PreserveBackground,
    /// Skip cells that were explicitly marked transparent (spaces are not transparent).
    Transparent,
}

impl BlitMode {
    pub fn from_name(name: &str) -> Option<Self> {
        Some(match name {
            "replace" => Self::Replace,
            "preserve_background" => Self::PreserveBackground,
            "transparent" => Self::Transparent,
            _ => return None,
        })
    }

    pub fn name(self) -> &'static str {
        match self {
            Self::Replace => "replace",
            Self::PreserveBackground => "preserve_background",
            Self::Transparent => "transparent",
        }
    }
}

/// A rectangle of cells, `[left, right) x [top, bottom)`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Bounds {
    pub left: u16,
    pub top: u16,
    pub right: u16,
    pub bottom: u16,
}

impl Bounds {
    pub fn width(self) -> u16 {
        self.right - self.left
    }

    pub fn height(self) -> u16 {
        self.bottom - self.top
    }
}

/// Cells with an optional transparency mask.
#[derive(Clone, Debug)]
pub struct Grid {
    cells: Buffer,
    transparent: Option<Vec<bool>>,
}

impl PartialEq for Grid {
    fn eq(&self, other: &Self) -> bool {
        self.cells == other.cells
    }
}

/// A cell with no symbol, colors or modifiers.
pub fn blank_cell() -> Cell {
    Cell::EMPTY
}

/// A blank cell carrying `style`.
pub fn styled_blank(style: Style) -> Cell {
    let mut cell = Cell::EMPTY;
    cell.set_style(style);
    cell
}

/// How many columns the symbol of `cell` covers.
pub fn cell_columns(cell: &Cell) -> usize {
    usize::from(cell.cell_width())
}

/// Whether `cell` carries a terminal graphics payload that must not be split.
pub fn is_protocol_cell(cell: &Cell) -> bool {
    cell.diff_option != CellDiffOption::None || cell.symbol().starts_with('\x1b')
}

impl Grid {
    pub fn new(width: u16, height: u16) -> Self {
        Self::filled(width, height, &Cell::EMPTY)
    }

    pub fn filled(width: u16, height: u16, cell: &Cell) -> Self {
        Self {
            cells: Buffer::filled(Rect::new(0, 0, width, height), cell.clone()),
            transparent: None,
        }
    }

    /// Wrap a ratatui buffer. Its area is moved to the origin.
    pub fn from_buffer(mut buffer: Buffer) -> Self {
        buffer.area.x = 0;
        buffer.area.y = 0;
        Self {
            cells: buffer,
            transparent: None,
        }
    }

    pub fn buffer(&self) -> &Buffer {
        &self.cells
    }

    pub fn buffer_mut(&mut self) -> &mut Buffer {
        &mut self.cells
    }

    pub fn into_buffer(self) -> Buffer {
        self.cells
    }

    pub fn width(&self) -> u16 {
        self.cells.area.width
    }

    pub fn height(&self) -> u16 {
        self.cells.area.height
    }

    pub fn bounds(&self) -> Bounds {
        Bounds {
            left: 0,
            top: 0,
            right: self.width(),
            bottom: self.height(),
        }
    }

    fn index(&self, x: u16, y: u16) -> usize {
        usize::from(y) * usize::from(self.width()) + usize::from(x)
    }

    pub fn cell(&self, x: u16, y: u16) -> Option<&Cell> {
        self.cells.cell((x, y))
    }

    pub fn is_transparent(&self, x: u16, y: u16) -> bool {
        self.transparent
            .as_ref()
            .is_some_and(|mask| mask.get(self.index(x, y)).copied().unwrap_or(false))
    }

    fn set_transparent(&mut self, x: u16, y: u16, value: bool) {
        if !value && self.transparent.is_none() {
            return;
        }
        let index = self.index(x, y);
        let length = self.cells.content.len();
        let mask = self.transparent.get_or_insert_with(|| vec![false; length]);
        mask[index] = value;
    }

    /// Mark every cell transparent; cells written later become opaque.
    pub fn mark_all_transparent(&mut self) {
        self.transparent = Some(vec![true; self.cells.content.len()]);
    }

    /// Copy the cells of `region` (as large as `bounds`) back into the grid.
    ///
    /// The region must hold well-formed cells, so no wide-glyph repair is done inside it;
    /// a wide glyph that crosses the left edge is repaired.
    pub fn replace_region(&mut self, bounds: Bounds, region: &Buffer) {
        for y in 0..bounds.height() {
            for x in 0..bounds.width() {
                if let Some(cell) = region.cell((x, y)) {
                    let index = self.index(bounds.left + x, bounds.top + y);
                    self.cells.content[index] = cell.clone();
                    self.set_transparent(bounds.left + x, bounds.top + y, false);
                }
            }
            if bounds.left > 0 && self.is_wide_head(bounds.left - 1, bounds.top + y) {
                let index = self.index(bounds.left - 1, bounds.top + y);
                self.cells.content[index].set_symbol(" ");
            }
        }
    }

    /// A copy of the cells of `bounds` as a standalone buffer.
    pub fn region_buffer(&self, bounds: Bounds) -> Buffer {
        let mut region = Buffer::empty(Rect::new(0, 0, bounds.width(), bounds.height()));
        for y in 0..bounds.height() {
            for x in 0..bounds.width() {
                if let Some(cell) = self.cell(bounds.left + x, bounds.top + y) {
                    let index = usize::from(y) * usize::from(bounds.width()) + usize::from(x);
                    region.content[index] = cell.clone();
                }
            }
        }
        region
    }

    /// Whether any cell is marked transparent.
    pub fn has_transparent_cells(&self) -> bool {
        self.transparent
            .as_ref()
            .is_some_and(|mask| mask.iter().any(|flag| *flag))
    }

    /// A new grid of `width` x `height` keeping the cells that still fit.
    pub fn resize(&mut self, width: u16, height: u16, fill: &Cell) {
        if width == self.width() && height == self.height() {
            return;
        }
        let mut next = Grid::filled(width, height, fill);
        let shared_width = width.min(self.width());
        let shared_height = height.min(self.height());
        for y in 0..shared_height {
            for x in 0..shared_width {
                let source_index = self.index(x, y);
                let target_index = next.index(x, y);
                next.cells.content[target_index] = self.cells.content[source_index].clone();
                if self.is_transparent(x, y) {
                    next.set_transparent(x, y, true);
                }
            }
        }
        // A wide glyph cut by the new right edge cannot keep its head.
        if width < self.width() && width > 0 {
            let edge = width - 1;
            for y in 0..shared_height {
                if cell_columns(&next.cells.content[next.index(edge, y)]) > 1 {
                    let index = next.index(edge, y);
                    next.cells.content[index] = fill.clone();
                }
            }
        }
        *self = next;
    }

    fn is_wide_head(&self, x: u16, y: u16) -> bool {
        self.cell(x, y)
            .is_some_and(|cell| !is_protocol_cell(cell) && cell_columns(cell) > 1)
    }

    /// Store `cell` at `(x, y)`, repairing any wide glyph it cuts. `columns` is how many
    /// cells the symbol covers (the cell after a two-column glyph is cleared).
    pub fn put(&mut self, x: u16, y: u16, cell: Cell, columns: usize, transparent: bool) {
        if x >= self.width() || y >= self.height() {
            return;
        }
        if x > 0 && self.is_wide_head(x - 1, y) {
            let index = self.index(x - 1, y);
            let mut head = self.cells.content[index].clone();
            let fill = Cell::EMPTY;
            head.set_symbol(fill.symbol());
            self.cells.content[index] = head;
        }
        let index = self.index(x, y);
        self.cells.content[index] = cell;
        self.set_transparent(x, y, transparent);
        if columns > 1 && x + 1 < self.width() {
            let next = self.index(x + 1, y);
            self.cells.content[next] = Cell::EMPTY;
            self.set_transparent(x + 1, y, false);
        }
    }

    /// Fill `bounds` with `cell`.
    pub fn fill(&mut self, bounds: Bounds, cell: &Cell, transparent: bool) {
        for y in bounds.top..bounds.bottom {
            for x in bounds.left..bounds.right {
                self.put(x, y, cell.clone(), 1, transparent);
            }
        }
        // A fill with a wide symbol would break rows; the cell is always one column.
    }

    /// Write styled `lines` with their top-left at `(x, y)` relative to `bounds`.
    ///
    /// Text is clipped by display columns; a grapheme that does not fit whole is dropped,
    /// never split.
    pub fn write_lines(
        &mut self,
        bounds: Bounds,
        lines: &[Line],
        x: i32,
        y: i32,
        base: Style,
        mode: WriteMode,
    ) {
        let width = i32::from(bounds.width());
        let height = i32::from(bounds.height());
        for (row_index, line) in lines.iter().enumerate() {
            let row = y.saturating_add(row_index as i32);
            if row < 0 || row >= height {
                continue;
            }
            let mut column = x;
            for span in line {
                let style = base.patch(span.style);
                for grapheme in span.text.graphemes(true) {
                    let columns = grapheme_width(grapheme) as i32;
                    if columns == 0 {
                        continue;
                    }
                    if column + columns <= 0 || column < 0 {
                        column += columns;
                        continue;
                    }
                    if column + columns > width {
                        column = width;
                        break;
                    }
                    let target_x = bounds.left + column as u16;
                    let target_y = bounds.top + row as u16;
                    let old_background = self
                        .cell(target_x, target_y)
                        .map_or(Color::Reset, |old| old.bg);
                    let mut cell = Cell::EMPTY;
                    cell.set_symbol(grapheme);
                    cell.set_style(style);
                    if mode == WriteMode::PreserveBackground && style.bg.is_none() {
                        cell.bg = old_background;
                    }
                    self.put(target_x, target_y, cell, columns as usize, false);
                    column += columns;
                }
                if column >= width {
                    break;
                }
            }
        }
    }

    /// Apply `style` to every cell of `bounds` without changing symbols.
    pub fn apply_style(&mut self, bounds: Bounds, style: Style) {
        for y in bounds.top..bounds.bottom {
            for x in bounds.left..bounds.right {
                if let Some(cell) = self.cells.cell_mut((x, y)) {
                    cell.set_style(style);
                }
            }
        }
    }

    /// Copy `source` so its top-left lands at `(x, y)` relative to `bounds`.
    pub fn blit(&mut self, bounds: Bounds, source: &Grid, x: i32, y: i32, mode: BlitMode) {
        let width = i32::from(bounds.width());
        let height = i32::from(bounds.height());
        let first_row = (-y).max(0);
        let last_row = (height - y).min(i32::from(source.height()));
        let first_column = (-x).max(0);
        let last_column = (width - x).min(i32::from(source.width()));
        for source_row in first_row..last_row {
            let target_y = bounds.top + (y + source_row) as u16;
            let mut source_column = first_column;
            while source_column < last_column {
                let (sx, sy) = (source_column as u16, source_row as u16);
                let Some(cell) = source.cell(sx, sy) else {
                    source_column += 1;
                    continue;
                };
                let target_x = bounds.left + (x + source_column) as u16;
                let is_transparent = source.is_transparent(sx, sy);
                if mode == BlitMode::Transparent && is_transparent {
                    source_column += 1;
                    continue;
                }
                let mut columns = if is_protocol_cell(cell) {
                    1
                } else {
                    cell_columns(cell).max(1)
                };
                // A glyph whose second column is clipped cannot be shown.
                let mut copy = cell.clone();
                if columns > 1 && source_column + 1 >= last_column {
                    copy = Cell::EMPTY;
                    copy.bg = cell.bg;
                    columns = 1;
                }
                if mode == BlitMode::PreserveBackground
                    && copy.bg == Color::Reset
                    && let Some(old) = self.cell(target_x, target_y)
                {
                    copy.bg = old.bg;
                }
                self.put(target_x, target_y, copy, columns, is_transparent);
                source_column += columns as i32;
            }
        }
    }

    /// Plain text rows with trailing blanks removed.
    pub fn text_rows(&self) -> Vec<String> {
        xnano_terminal_cells::text(&self.cells)
    }
}
