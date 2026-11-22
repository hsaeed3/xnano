//! Terminal frames drawn as images: every cell is a box of pixels the size of one glyph.
//!
//! The cell's background fills its box, and its symbol is drawn in its foreground color.
//! Block elements (half blocks, quadrants, shades) and braille are drawn as shapes, so pixel
//! art looks the same with any font. Other symbols come from the font. A symbol the font does
//! not have is drawn as an empty box.

use ratatui_core::buffer::{Buffer, Cell};
use ratatui_core::style::{Color, Modifier};
use unicode_width::UnicodeWidthStr;

use crate::font::{Font, FontError, PixelGlyphs};

/// The color of text that has no color of its own.
pub const DEFAULT_FOREGROUND: [u8; 3] = [229, 229, 229];
/// The color behind cells that have no background of their own.
pub const DEFAULT_BACKGROUND: [u8; 3] = [24, 24, 27];

/// The sixteen named colors, as xterm draws them.
const NAMED_COLORS: [[u8; 3]; 16] = [
    [0, 0, 0],
    [205, 49, 49],
    [13, 188, 121],
    [229, 229, 16],
    [36, 114, 200],
    [188, 63, 188],
    [17, 168, 205],
    [229, 229, 229],
    [102, 102, 102],
    [241, 76, 76],
    [35, 209, 139],
    [245, 245, 67],
    [59, 142, 234],
    [214, 112, 214],
    [41, 184, 219],
    [255, 255, 255],
];

/// An RGB image: three bytes for each pixel, row by row.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Pixmap {
    pub width: usize,
    pub height: usize,
    pub data: Vec<u8>,
}

impl Pixmap {
    fn new(width: usize, height: usize) -> Self {
        Self {
            width,
            height,
            data: vec![0; width * height * 3],
        }
    }

    fn fill(&mut self, left: usize, top: usize, width: usize, height: usize, color: [u8; 3]) {
        let right = (left + width).min(self.width);
        let bottom = (top + height).min(self.height);
        for row in top..bottom {
            for column in left..right {
                let index = (row * self.width + column) * 3;
                self.data[index..index + 3].copy_from_slice(&color);
            }
        }
    }

    /// Encode the image as a PNG file.
    pub fn to_png(&self) -> Vec<u8> {
        let mut bytes = Vec::new();
        {
            let mut encoder = png::Encoder::new(&mut bytes, self.width as u32, self.height as u32);
            encoder.set_color(png::ColorType::Rgb);
            encoder.set_depth(png::BitDepth::Eight);
            // Frames are mostly runs of one color, which fast compression handles well.
            encoder.set_compression(png::Compression::Fast);
            // Writing into a vector cannot fail, and the size always matches the data.
            let mut writer = encoder
                .write_header()
                .expect("a PNG header always writes into memory");
            writer
                .write_image_data(&self.data)
                .expect("the pixel data always matches the image size");
        }
        bytes
    }
}

/// The RGB value of a cell color, with `default` for [`Color::Reset`].
pub fn color_to_rgb(color: Color, default: [u8; 3]) -> [u8; 3] {
    match color {
        Color::Reset => default,
        Color::Black => NAMED_COLORS[0],
        Color::Red => NAMED_COLORS[1],
        Color::Green => NAMED_COLORS[2],
        Color::Yellow => NAMED_COLORS[3],
        Color::Blue => NAMED_COLORS[4],
        Color::Magenta => NAMED_COLORS[5],
        Color::Cyan => NAMED_COLORS[6],
        Color::Gray => NAMED_COLORS[7],
        Color::DarkGray => NAMED_COLORS[8],
        Color::LightRed => NAMED_COLORS[9],
        Color::LightGreen => NAMED_COLORS[10],
        Color::LightYellow => NAMED_COLORS[11],
        Color::LightBlue => NAMED_COLORS[12],
        Color::LightMagenta => NAMED_COLORS[13],
        Color::LightCyan => NAMED_COLORS[14],
        Color::White => NAMED_COLORS[15],
        Color::Rgb(red, green, blue) => [red, green, blue],
        Color::Indexed(index) => indexed_color(index),
    }
}

/// The xterm 256-color palette: sixteen named colors, a 6×6×6 cube and 24 grays.
fn indexed_color(index: u8) -> [u8; 3] {
    match index {
        0..=15 => NAMED_COLORS[index as usize],
        16..=231 => {
            let level = |value: u8| if value == 0 { 0 } else { 55 + value * 40 };
            let cube = index - 16;
            [level(cube / 36), level(cube / 6 % 6), level(cube % 6)]
        }
        _ => {
            let gray = 8 + (index - 232) * 10;
            [gray, gray, gray]
        }
    }
}

/// `color` moved toward `other` by `amount`, from `0.0` (none) to `1.0` (all the way).
fn mix(color: [u8; 3], other: [u8; 3], amount: f32) -> [u8; 3] {
    let channel = |index: usize| {
        let from = f32::from(color[index]);
        let to = f32::from(other[index]);
        (from + (to - from) * amount).round() as u8
    };
    [channel(0), channel(1), channel(2)]
}

/// The foreground and background a cell is drawn with, after its modifiers.
fn cell_colors(cell: &Cell) -> ([u8; 3], [u8; 3]) {
    let mut foreground = color_to_rgb(cell.fg, DEFAULT_FOREGROUND);
    let mut background = color_to_rgb(cell.bg, DEFAULT_BACKGROUND);
    if cell.modifier.contains(Modifier::REVERSED) {
        std::mem::swap(&mut foreground, &mut background);
    }
    if cell.modifier.contains(Modifier::DIM) {
        foreground = mix(foreground, background, 0.5);
    }
    if cell.modifier.contains(Modifier::HIDDEN) {
        foreground = background;
    }
    (foreground, background)
}

/// Draw `buffer` with the cells of `font`, which must be a pixel font.
pub fn render_buffer(buffer: &Buffer, font: &Font) -> Result<Pixmap, FontError> {
    let Some(glyphs) = font.pixel_glyphs() else {
        return Err(FontError::new(format!(
            "An image needs a pixel font to draw its cells, but \"{}\" is a character font. Use \
             a pixel font, such as the built-in \"large\" font or a .bdf file.",
            font.name()
        )));
    };
    let area = buffer.area;
    let (cell_width, cell_height) = (glyphs.width, glyphs.height);
    let mut pixmap = Pixmap::new(
        usize::from(area.width) * cell_width,
        usize::from(area.height) * cell_height,
    );
    pixmap.fill(0, 0, pixmap.width, pixmap.height, DEFAULT_BACKGROUND);
    for row in 0..area.height {
        // A wide symbol covers the cell after it, which the terminal leaves blank.
        let mut covered_until = 0;
        for column in 0..area.width {
            if column < covered_until {
                continue;
            }
            let cell = &buffer[(area.x + column, area.y + row)];
            let left = usize::from(column) * cell_width;
            let top = usize::from(row) * cell_height;
            let (foreground, background) = cell_colors(cell);
            let symbol = cell.symbol();
            let width_in_cells = UnicodeWidthStr::width(symbol)
                .clamp(1, 2)
                .min(usize::from(area.width - column));
            covered_until = column + width_in_cells as u16;
            let box_width = cell_width * width_in_cells;
            pixmap.fill(left, top, box_width, cell_height, background);
            let mut characters = symbol.chars();
            let Some(character) = characters.next() else {
                continue;
            };
            if character != ' ' {
                let box_area = CellBox {
                    left,
                    top,
                    width: box_width,
                    height: cell_height,
                };
                draw_symbol(
                    &mut pixmap,
                    glyphs,
                    character,
                    box_area,
                    foreground,
                    background,
                    cell.modifier.contains(Modifier::BOLD),
                );
            }
            if cell.modifier.contains(Modifier::UNDERLINED) {
                let color = color_to_rgb(cell.underline_color, foreground);
                pixmap.fill(left, top + cell_height - 1, box_width, 1, color);
            }
            if cell.modifier.contains(Modifier::CROSSED_OUT) {
                pixmap.fill(left, top + cell_height / 2, box_width, 1, foreground);
            }
        }
    }
    Ok(pixmap)
}

/// The pixels of one cell, or of two for a wide symbol.
#[derive(Debug, Clone, Copy)]
struct CellBox {
    left: usize,
    top: usize,
    width: usize,
    height: usize,
}

impl CellBox {
    /// The part of the box from `start` to `end`, as fractions of its width and height.
    fn part(
        self,
        (left, top, right, bottom): (f32, f32, f32, f32),
    ) -> (usize, usize, usize, usize) {
        let x = |fraction: f32| (fraction * self.width as f32).round() as usize;
        let y = |fraction: f32| (fraction * self.height as f32).round() as usize;
        (
            self.left + x(left),
            self.top + y(top),
            x(right) - x(left),
            y(bottom) - y(top),
        )
    }
}

fn draw_symbol(
    pixmap: &mut Pixmap,
    glyphs: &PixelGlyphs,
    character: char,
    area: CellBox,
    foreground: [u8; 3],
    background: [u8; 3],
    is_bold: bool,
) {
    if let Some(parts) = block_parts(character) {
        for &part in parts {
            let (left, top, width, height) = area.part(part);
            pixmap.fill(left, top, width, height, foreground);
        }
        return;
    }
    if let Some(amount) = shade_amount(character) {
        let color = mix(background, foreground, amount);
        pixmap.fill(area.left, area.top, area.width, area.height, color);
        return;
    }
    if let Some(dots) = braille_dots(character) {
        draw_braille(pixmap, dots, area, foreground);
        return;
    }
    let Some(glyph) = glyphs.glyphs.get(&character) else {
        draw_missing(pixmap, area, foreground);
        return;
    };
    for row in 0..glyphs.height.min(area.height) {
        for column in 0..glyphs.width.min(area.width) {
            if !PixelGlyphs::is_on(glyph, column, row) {
                continue;
            }
            pixmap.fill(area.left + column, area.top + row, 1, 1, foreground);
            // Bold text is drawn twice, one pixel apart.
            if is_bold && column + 1 < area.width {
                pixmap.fill(area.left + column + 1, area.top + row, 1, 1, foreground);
            }
        }
    }
}

/// An empty box, for a symbol the font does not have.
fn draw_missing(pixmap: &mut Pixmap, area: CellBox, color: [u8; 3]) {
    if area.width < 3 || area.height < 3 {
        return;
    }
    let (left, top) = (area.left + 1, area.top + 1);
    let (width, height) = (area.width - 2, area.height - 2);
    pixmap.fill(left, top, width, 1, color);
    pixmap.fill(left, top + height - 1, width, 1, color);
    pixmap.fill(left, top, 1, height, color);
    pixmap.fill(left + width - 1, top, 1, height, color);
}

const UPPER_LEFT: (f32, f32, f32, f32) = (0.0, 0.0, 0.5, 0.5);
const UPPER_RIGHT: (f32, f32, f32, f32) = (0.5, 0.0, 1.0, 0.5);
const LOWER_LEFT: (f32, f32, f32, f32) = (0.0, 0.5, 0.5, 1.0);
const LOWER_RIGHT: (f32, f32, f32, f32) = (0.5, 0.5, 1.0, 1.0);

/// The filled parts of a block element (U+2580 to U+259F), shades aside.
fn block_parts(character: char) -> Option<&'static [(f32, f32, f32, f32)]> {
    const LOWER: [[(f32, f32, f32, f32); 1]; 8] = [
        [(0.0, 0.875, 1.0, 1.0)],
        [(0.0, 0.75, 1.0, 1.0)],
        [(0.0, 0.625, 1.0, 1.0)],
        [(0.0, 0.5, 1.0, 1.0)],
        [(0.0, 0.375, 1.0, 1.0)],
        [(0.0, 0.25, 1.0, 1.0)],
        [(0.0, 0.125, 1.0, 1.0)],
        [(0.0, 0.0, 1.0, 1.0)],
    ];
    const LEFT: [[(f32, f32, f32, f32); 1]; 7] = [
        [(0.0, 0.0, 0.875, 1.0)],
        [(0.0, 0.0, 0.75, 1.0)],
        [(0.0, 0.0, 0.625, 1.0)],
        [(0.0, 0.0, 0.5, 1.0)],
        [(0.0, 0.0, 0.375, 1.0)],
        [(0.0, 0.0, 0.25, 1.0)],
        [(0.0, 0.0, 0.125, 1.0)],
    ];
    Some(match character {
        '\u{2580}' => &[(0.0, 0.0, 1.0, 0.5)],
        '\u{2581}'..='\u{2588}' => &LOWER[character as usize - 0x2581],
        '\u{2589}'..='\u{258F}' => &LEFT[character as usize - 0x2589],
        '\u{2590}' => &[(0.5, 0.0, 1.0, 1.0)],
        '\u{2594}' => &[(0.0, 0.0, 1.0, 0.125)],
        '\u{2595}' => &[(0.875, 0.0, 1.0, 1.0)],
        '\u{2596}' => &[LOWER_LEFT],
        '\u{2597}' => &[LOWER_RIGHT],
        '\u{2598}' => &[UPPER_LEFT],
        '\u{2599}' => &[UPPER_LEFT, LOWER_LEFT, LOWER_RIGHT],
        '\u{259A}' => &[UPPER_LEFT, LOWER_RIGHT],
        '\u{259B}' => &[UPPER_LEFT, UPPER_RIGHT, LOWER_LEFT],
        '\u{259C}' => &[UPPER_LEFT, UPPER_RIGHT, LOWER_RIGHT],
        '\u{259D}' => &[UPPER_RIGHT],
        '\u{259E}' => &[UPPER_RIGHT, LOWER_LEFT],
        '\u{259F}' => &[UPPER_RIGHT, LOWER_LEFT, LOWER_RIGHT],
        _ => return None,
    })
}

/// How much of the foreground a shade (U+2591 to U+2593) shows.
fn shade_amount(character: char) -> Option<f32> {
    match character {
        '\u{2591}' => Some(0.25),
        '\u{2592}' => Some(0.5),
        '\u{2593}' => Some(0.75),
        _ => None,
    }
}

/// The dots of a braille pattern (U+2800 to U+28FF), as its eight bits.
fn braille_dots(character: char) -> Option<u8> {
    let code = character as u32;
    (0x2800..=0x28FF)
        .contains(&code)
        .then(|| (code - 0x2800) as u8)
}

fn draw_braille(pixmap: &mut Pixmap, dots: u8, area: CellBox, color: [u8; 3]) {
    // Bit order of the braille block: dots 1 to 3 down the left, 4 to 6 down the right,
    // then dot 7 bottom left and dot 8 bottom right.
    const POSITIONS: [(usize, usize); 8] = [
        (0, 0),
        (0, 1),
        (0, 2),
        (1, 0),
        (1, 1),
        (1, 2),
        (0, 3),
        (1, 3),
    ];
    let dot_width = (area.width / 2).max(1);
    let dot_height = (area.height / 4).max(1);
    // Leave a gap between dots when the cell is large enough.
    let size_x = if dot_width >= 3 {
        dot_width - 1
    } else {
        dot_width
    };
    let size_y = if dot_height >= 3 {
        dot_height - 1
    } else {
        dot_height
    };
    for (bit, (column, row)) in POSITIONS.iter().enumerate() {
        if dots >> bit & 1 == 1 {
            pixmap.fill(
                area.left + column * dot_width,
                area.top + row * dot_height,
                size_x,
                size_y,
                color,
            );
        }
    }
}
