//! The cell store behind every buffer.
//!
//! A [`Grid`] is a ratatui buffer anchored at the origin, plus a mask of cells that were
//! explicitly marked transparent. Using ratatui's cell type means cell grids, widgets and
//! the terminal presenter all share one representation.

use ratatui_core::buffer::{Buffer, Cell, CellDiffOption, CellWidth};
use ratatui_core::layout::Rect;
use ratatui_core::style::Color;

use crate::style::Style;
use crate::text::{Line, grapheme_width, split_graphemes};

/// The one-character string of every printable ASCII byte, so writing ASCII text needs no
/// string slicing per cell.
const ASCII_SYMBOLS: [&str; 95] = [
    " ", "!", "\"", "#", "$", "%", "&", "'", "(", ")", "*", "+", ",", "-", ".", "/", "0", "1", "2",
    "3", "4", "5", "6", "7", "8", "9", ":", ";", "<", "=", ">", "?", "@", "A", "B", "C", "D", "E",
    "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X",
    "Y", "Z", "[", "\\", "]", "^", "_", "`", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k",
    "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "{", "|", "}", "~",
];

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
pub enum PasteMode {
    #[default]
    Replace,
    PreserveBackground,
    /// Skip cells that were explicitly marked transparent (spaces are not transparent).
    Transparent,
}

impl PasteMode {
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
    if cell.diff_option == CellDiffOption::None {
        let symbol = cell.symbol();
        // A one-byte symbol is one column; most cells never reach the width tables.
        if symbol.len() == 1 {
            return 1;
        }
        return usize::from(symbol.cell_width());
    }
    usize::from(cell.cell_width())
}

/// Whether `cell` carries a terminal graphics payload that must not be split.
pub fn is_protocol_cell(cell: &Cell) -> bool {
    cell.diff_option != CellDiffOption::None || cell.symbol().starts_with('\x1b')
}

/// Whether `cell` is the head of a glyph that covers more than one column.
///
/// Protocol cells are never wide heads. Only a symbol longer than one byte can be wide.
fn is_wide(cell: &Cell) -> bool {
    if cell.diff_option != CellDiffOption::None {
        return false;
    }
    let symbol = cell.symbol();
    symbol.len() > 1 && !symbol.starts_with('\x1b') && symbol.cell_width() > 1
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

    fn set_transparent_range(&mut self, start: usize, end: usize, value: bool) {
        if !value && self.transparent.is_none() {
            return;
        }
        let length = self.cells.content.len();
        let mask = self.transparent.get_or_insert_with(|| vec![false; length]);
        mask[start..end].fill(value);
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
        let width = usize::from(bounds.width());
        // Cells outside the grid stay blank.
        let copied = width.min(usize::from(self.width().saturating_sub(bounds.left)));
        for y in 0..bounds.height() {
            if bounds.top + y >= self.height() {
                break;
            }
            let source_start = self.index(bounds.left, bounds.top + y);
            let target_start = usize::from(y) * width;
            region.content[target_start..target_start + copied]
                .clone_from_slice(&self.cells.content[source_start..source_start + copied]);
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
        let shared = usize::from(shared_width);
        for y in 0..shared_height {
            let source_start = self.index(0, y);
            let target_start = next.index(0, y);
            next.cells.content[target_start..target_start + shared]
                .clone_from_slice(&self.cells.content[source_start..source_start + shared]);
        }
        if let Some(mask) = &self.transparent {
            for y in 0..shared_height {
                for x in 0..shared_width {
                    if mask[self.index(x, y)] {
                        next.set_transparent(x, y, true);
                    }
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
        self.cell(x, y).is_some_and(is_wide)
    }

    /// Store `cell` at `(x, y)`, repairing any wide glyph it cuts. `columns` is how many
    /// cells the symbol covers (the cell after a two-column glyph is cleared).
    pub fn put(&mut self, x: u16, y: u16, cell: Cell, columns: usize, transparent: bool) {
        if x >= self.width() || y >= self.height() {
            return;
        }
        let index = self.index(x, y);
        if x > 0 && is_wide(&self.cells.content[index - 1]) {
            self.cells.content[index - 1].set_symbol(Cell::EMPTY.symbol());
        }
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
        // A fill with a wide symbol would break rows; the cell is always one column.
        if bounds.left >= bounds.right || bounds.top >= bounds.bottom {
            return;
        }
        for y in bounds.top..bounds.bottom {
            // Only the first cell of a row can cut a wide glyph that starts to its left.
            self.put(bounds.left, y, cell.clone(), 1, transparent);
            if bounds.left + 1 >= bounds.right {
                continue;
            }
            let (start, end) = (
                self.index(bounds.left + 1, y),
                self.index(bounds.right - 1, y) + 1,
            );
            self.cells.content[start..end].fill(cell.clone());
            self.set_transparent_range(start, end, transparent);
        }
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
                if span.text.is_ascii() {
                    column = self.write_ascii(bounds, &span.text, column, row, style, mode, width);
                } else {
                    column =
                        self.write_graphemes(bounds, &span.text, column, row, style, mode, width);
                }
                if column >= width {
                    break;
                }
            }
        }
    }

    /// Write one ASCII run. Every printable byte is one grapheme of one column and control
    /// bytes take none, so no grapheme segmentation is needed.
    #[allow(clippy::too_many_arguments)]
    fn write_ascii(
        &mut self,
        bounds: Bounds,
        text: &str,
        mut column: i32,
        row: i32,
        style: Style,
        mode: WriteMode,
        width: i32,
    ) -> i32 {
        let target_y = bounds.top + row as u16;
        let mut template = Cell::EMPTY;
        template.set_style(style);
        let keeps_background = mode == WriteMode::PreserveBackground && style.bg.is_none();
        for byte in text.bytes() {
            if byte.is_ascii_control() {
                continue;
            }
            if column < 0 {
                column += 1;
                continue;
            }
            if column + 1 > width {
                return width;
            }
            let target_x = bounds.left + column as u16;
            let mut cell = template.clone();
            cell.set_symbol(ASCII_SYMBOLS[usize::from(byte - 0x20)]);
            if keeps_background && let Some(old) = self.cell(target_x, target_y) {
                cell.bg = old.bg;
            }
            self.put(target_x, target_y, cell, 1, false);
            column += 1;
        }
        column
    }

    #[allow(clippy::too_many_arguments)]
    fn write_graphemes(
        &mut self,
        bounds: Bounds,
        text: &str,
        mut column: i32,
        row: i32,
        style: Style,
        mode: WriteMode,
        width: i32,
    ) -> i32 {
        for grapheme in split_graphemes(text) {
            let columns = grapheme_width(grapheme) as i32;
            if columns == 0 {
                continue;
            }
            if column + columns <= 0 || column < 0 {
                column += columns;
                continue;
            }
            if column + columns > width {
                return width;
            }
            let target_x = bounds.left + column as u16;
            let target_y = bounds.top + row as u16;
            let mut cell = Cell::EMPTY;
            cell.set_symbol(grapheme);
            cell.set_style(style);
            if mode == WriteMode::PreserveBackground && style.bg.is_none() {
                cell.bg = self
                    .cell(target_x, target_y)
                    .map_or(Color::Reset, |old| old.bg);
            }
            self.put(target_x, target_y, cell, columns as usize, false);
            column += columns;
        }
        column
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
    pub fn paste(&mut self, bounds: Bounds, source: &Grid, x: i32, y: i32, mode: PasteMode) {
        let width = i32::from(bounds.width());
        let height = i32::from(bounds.height());
        let first_row = (-y).max(0);
        let last_row = (height - y).min(i32::from(source.height()));
        let first_column = (-x).max(0);
        let last_column = (width - x).min(i32::from(source.width()));
        let source_width = usize::from(source.width());
        for source_row in first_row..last_row {
            let target_y = bounds.top + (y + source_row) as u16;
            let row_start = source_row as usize * source_width;
            let mut source_column = first_column;
            while source_column < last_column {
                let (sx, sy) = (source_column as u16, source_row as u16);
                let Some(cell) = source.cells.content.get(row_start + source_column as usize)
                else {
                    source_column += 1;
                    continue;
                };
                let target_x = bounds.left + (x + source_column) as u16;
                let is_transparent = source.is_transparent(sx, sy);
                if mode == PasteMode::Transparent && is_transparent {
                    source_column += 1;
                    continue;
                }
                let mut columns = if cell.diff_option != CellDiffOption::None {
                    1
                } else {
                    let symbol = cell.symbol();
                    if symbol.len() == 1 || symbol.starts_with('\x1b') {
                        1
                    } else {
                        usize::from(symbol.cell_width()).max(1)
                    }
                };
                // A glyph whose second column is clipped cannot be shown.
                let mut copy = cell.clone();
                if columns > 1 && source_column + 1 >= last_column {
                    copy = Cell::EMPTY;
                    copy.bg = cell.bg;
                    columns = 1;
                }
                if mode == PasteMode::PreserveBackground
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
