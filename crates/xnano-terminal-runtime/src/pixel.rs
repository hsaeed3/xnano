//! Logical pixels drawn into cells.
//!
//! Half blocks give one pixel column and two pixel rows per cell. Braille gives two
//! columns and four rows per cell, with one color per cell. Writing a pixel decodes the
//! cell that holds it, changes the pixel, and encodes the result back into that cell, so
//! pixels share storage with text and styles.

use ratatui_core::buffer::Cell;
use ratatui_core::style::Color;

use crate::grid::{Bounds, Grid};

/// How pixels are packed into cells.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum PixelEncoding {
    #[default]
    HalfBlocks,
    Braille,
}

impl PixelEncoding {
    pub fn from_name(name: &str) -> Option<Self> {
        Some(match name {
            "half_blocks" => Self::HalfBlocks,
            "braille" => Self::Braille,
            _ => return None,
        })
    }

    pub fn name(self) -> &'static str {
        match self {
            Self::HalfBlocks => "half_blocks",
            Self::Braille => "braille",
        }
    }

    /// Pixel columns per cell.
    pub fn columns_per_cell(self) -> i32 {
        match self {
            Self::HalfBlocks => 1,
            Self::Braille => 2,
        }
    }

    /// Pixel rows per cell.
    pub fn rows_per_cell(self) -> i32 {
        match self {
            Self::HalfBlocks => 2,
            Self::Braille => 4,
        }
    }
}

/// One pixel: column, row and color.
pub type Pixel = (i32, i32, (u8, u8, u8));

const UPPER_HALF: &str = "\u{2580}";
const LOWER_HALF: &str = "\u{2584}";
const BRAILLE_BASE: u32 = 0x2800;

const fn braille_bit(column: i32, row: i32) -> u32 {
    match (column, row) {
        (0, 0) => 0x01,
        (0, 1) => 0x02,
        (0, 2) => 0x04,
        (1, 0) => 0x08,
        (1, 1) => 0x10,
        (1, 2) => 0x20,
        (0, 3) => 0x40,
        _ => 0x80,
    }
}

/// A raster view over a rectangle of a grid.
#[derive(Debug, Clone, Copy)]
pub struct PixelSpace {
    pub bounds: Bounds,
    pub encoding: PixelEncoding,
}

impl PixelSpace {
    pub fn width(self) -> i32 {
        i32::from(self.bounds.width()) * self.encoding.columns_per_cell()
    }

    pub fn height(self) -> i32 {
        i32::from(self.bounds.height()) * self.encoding.rows_per_cell()
    }

    pub fn contains(self, column: i32, row: i32) -> bool {
        column >= 0 && row >= 0 && column < self.width() && row < self.height()
    }

    /// The cell `(column, row)` holding the pixel.
    pub fn cell_of(self, pixel_column: i32, pixel_row: i32) -> (i32, i32) {
        (
            pixel_column.div_euclid(self.encoding.columns_per_cell()),
            pixel_row.div_euclid(self.encoding.rows_per_cell()),
        )
    }

    /// The pixel at an anchor of a cell.
    pub fn pixel_of(self, column: i32, row: i32, anchor: Anchor) -> (i32, i32) {
        let columns = self.encoding.columns_per_cell();
        let rows = self.encoding.rows_per_cell();
        let (horizontal, vertical) = match anchor {
            Anchor::TopLeft => (0, 0),
            Anchor::Center => (columns / 2, rows / 2),
            Anchor::BottomRight => (columns - 1, rows - 1),
        };
        (column * columns + horizontal, row * rows + vertical)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Anchor {
    TopLeft,
    Center,
    BottomRight,
}

impl Anchor {
    pub fn from_name(name: &str) -> Option<Self> {
        Some(match name {
            "top_left" => Self::TopLeft,
            "center" => Self::Center,
            "bottom_right" => Self::BottomRight,
            _ => return None,
        })
    }
}

fn rgb(color: (u8, u8, u8)) -> Color {
    Color::Rgb(color.0, color.1, color.2)
}

/// Pixels whose cells are not already in the pixel format are treated as background.
fn decode_half_blocks(cell: &Cell) -> (Color, Color) {
    match cell.symbol() {
        UPPER_HALF => (cell.fg, cell.bg),
        LOWER_HALF => (cell.bg, cell.fg),
        _ => (cell.bg, cell.bg),
    }
}

fn encode_half_blocks(existing: &Cell, top: Color, bottom: Color) -> Cell {
    let mut cell = Cell::EMPTY;
    cell.modifier = existing.modifier;
    if top == bottom {
        cell.set_symbol(" ");
        cell.bg = top;
    } else if top == Color::Reset {
        // Only the bottom pixel is set: draw it as a lower half block, so the empty top half
        // shows the background instead of the terminal's default foreground color.
        cell.set_symbol(LOWER_HALF);
        cell.fg = bottom;
    } else {
        cell.set_symbol(UPPER_HALF);
        cell.fg = top;
        cell.bg = bottom;
    }
    cell
}

fn braille_bits(cell: &Cell) -> u32 {
    let mut characters = cell.symbol().chars();
    match (characters.next(), characters.next()) {
        (Some(character), None)
            if (BRAILLE_BASE..BRAILLE_BASE + 256).contains(&(character as u32)) =>
        {
            character as u32 - BRAILLE_BASE
        }
        _ => 0,
    }
}

fn colors_of(grid: &Grid, space: PixelSpace, column: i32, row: i32) -> Option<(Color, Color)> {
    let (cell_column, cell_row) = space.cell_of(column, row);
    let cell = grid.cell(
        space.bounds.left + cell_column as u16,
        space.bounds.top + cell_row as u16,
    )?;
    Some(decode_half_blocks(cell))
}

/// Write `pixels` in order. Pixels outside the space are skipped when `clip` is true.
///
/// With `clip` false, a pixel outside the space is an error and nothing is written.
pub fn write_pixels(
    grid: &mut Grid,
    space: PixelSpace,
    pixels: &[Pixel],
    clip: bool,
) -> Result<(), (i32, i32)> {
    if !clip
        && let Some((column, row, _)) = pixels
            .iter()
            .find(|(column, row, _)| !space.contains(*column, *row))
    {
        return Err((*column, *row));
    }
    for &(column, row, color) in pixels {
        if !space.contains(column, row) {
            continue;
        }
        let (cell_column, cell_row) = space.cell_of(column, row);
        let x = space.bounds.left + cell_column as u16;
        let y = space.bounds.top + cell_row as u16;
        let Some(existing) = grid.cell(x, y).cloned() else {
            continue;
        };
        match space.encoding {
            PixelEncoding::HalfBlocks => {
                let (mut top, mut bottom) = decode_half_blocks(&existing);
                if row.rem_euclid(2) == 0 {
                    top = rgb(color);
                } else {
                    bottom = rgb(color);
                }
                grid.put(x, y, encode_half_blocks(&existing, top, bottom), 1, false);
            }
            PixelEncoding::Braille => {
                let bits =
                    braille_bits(&existing) | braille_bit(column.rem_euclid(2), row.rem_euclid(4));
                let mut cell = existing.clone();
                cell.set_symbol(
                    &char::from_u32(BRAILLE_BASE + bits)
                        .unwrap_or(' ')
                        .to_string(),
                );
                cell.fg = rgb(color);
                grid.put(x, y, cell, 1, false);
            }
        }
    }
    Ok(())
}

/// How RGBA pixels combine with what is already there.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RasterMode {
    /// The source pixel replaces the destination; fully transparent pixels erase it.
    Replace,
    /// Source-over alpha blending against the destination pixel.
    Over,
}

impl RasterMode {
    pub fn from_name(name: &str) -> Option<Self> {
        Some(match name {
            "replace" => Self::Replace,
            "over" => Self::Over,
            _ => return None,
        })
    }
}

fn blend(source: (u8, u8, u8), alpha: u8, destination: (u8, u8, u8)) -> (u8, u8, u8) {
    let weight = u32::from(alpha);
    let mix = |above: u8, below: u8| {
        ((u32::from(above) * weight + u32::from(below) * (255 - weight) + 127) / 255) as u8
    };
    (
        mix(source.0, destination.0),
        mix(source.1, destination.1),
        mix(source.2, destination.2),
    )
}

/// Draw a row-major RGBA8 image with its top-left pixel at `(x, y)`.
#[allow(clippy::too_many_arguments)]
pub fn draw_rgba(
    grid: &mut Grid,
    space: PixelSpace,
    data: &[u8],
    width: i32,
    height: i32,
    left: i32,
    top: i32,
    mode: RasterMode,
    clip: bool,
) -> Result<(), (i32, i32)> {
    if !clip {
        for (column, row) in [(left, top), (left + width - 1, top + height - 1)] {
            if width > 0 && height > 0 && !space.contains(column, row) {
                return Err((column, row));
            }
        }
    }
    let mut pixels: Vec<Pixel> = Vec::new();
    for row in 0..height {
        for column in 0..width {
            let target = (left + column, top + row);
            if !space.contains(target.0, target.1) {
                continue;
            }
            let offset = ((row * width + column) * 4) as usize;
            let (red, green, blue, alpha) = (
                data[offset],
                data[offset + 1],
                data[offset + 2],
                data[offset + 3],
            );
            match mode {
                RasterMode::Replace => {
                    if alpha == 0 {
                        let _ = write_erase(grid, space, target);
                        continue;
                    }
                    pixels.push((target.0, target.1, (red, green, blue)));
                }
                RasterMode::Over => {
                    if alpha == 0 {
                        continue;
                    }
                    let below = colors_of(grid, space, target.0, target.1).map_or(
                        (0, 0, 0),
                        |(top, bottom)| {
                            let chosen = if target.1.rem_euclid(2) == 0 {
                                top
                            } else {
                                bottom
                            };
                            match chosen {
                                Color::Rgb(red, green, blue) => (red, green, blue),
                                _ => (0, 0, 0),
                            }
                        },
                    );
                    let color = if alpha == 255 {
                        (red, green, blue)
                    } else {
                        blend((red, green, blue), alpha, below)
                    };
                    pixels.push((target.0, target.1, color));
                }
            }
            // Flush as we go so that blending reads earlier pixels of the same image.
            if !pixels.is_empty() {
                let _ = write_pixels(grid, space, &pixels, true);
                pixels.clear();
            }
        }
    }
    Ok(())
}

/// Clear one pixel back to the background (half blocks only; braille dots are cleared).
fn write_erase(grid: &mut Grid, space: PixelSpace, pixel: (i32, i32)) -> Result<(), ()> {
    let (cell_column, cell_row) = space.cell_of(pixel.0, pixel.1);
    let x = space.bounds.left + cell_column as u16;
    let y = space.bounds.top + cell_row as u16;
    let Some(existing) = grid.cell(x, y).cloned() else {
        return Err(());
    };
    match space.encoding {
        PixelEncoding::HalfBlocks => {
            let (mut top, mut bottom) = decode_half_blocks(&existing);
            if pixel.1.rem_euclid(2) == 0 {
                top = Color::Reset;
            } else {
                bottom = Color::Reset;
            }
            grid.put(x, y, encode_half_blocks(&existing, top, bottom), 1, false);
        }
        PixelEncoding::Braille => {
            let bits = braille_bits(&existing)
                & !braille_bit(pixel.0.rem_euclid(2), pixel.1.rem_euclid(4));
            let mut cell = existing;
            cell.set_symbol(
                &char::from_u32(BRAILLE_BASE + bits)
                    .unwrap_or(' ')
                    .to_string(),
            );
            grid.put(x, y, cell, 1, false);
        }
    }
    Ok(())
}
