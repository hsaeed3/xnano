//! Fonts: the shapes of characters, made of characters (FIGlet) or of pixels (BDF).
//!
//! A pixel font keeps one bitmap per character, all of the same size. A character font keeps
//! the rows of characters that draw each character, all of the same height. Both are plain
//! data once they are read, so a font can be shared between threads.

use std::collections::HashMap;
use std::fmt;
use std::sync::{Arc, OnceLock};

use embedded_graphics::geometry::{OriginDimensions, Point};
use embedded_graphics::image::GetPixel;
use embedded_graphics::mono_font::MonoFont;
use embedded_graphics::pixelcolor::BinaryColor;
use unicode_width::UnicodeWidthStr;

/// The widest pixel glyph a font can have, in pixels: one row of a glyph is one `u64`.
pub const MAXIMUM_GLYPH_WIDTH: usize = 64;

/// The names of the fonts built into xnano.
pub const BUILTIN_FONT_NAMES: [&str; 2] = ["small", "large"];

/// What a font draws characters with.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FontKind {
    /// Each character is drawn with several rows of other characters (a FIGlet font).
    Character,
    /// Each character is drawn with pixels (a BDF font).
    Pixel,
}

impl FontKind {
    pub fn name(self) -> &'static str {
        match self {
            Self::Character => "character",
            Self::Pixel => "pixel",
        }
    }
}

/// Why a font could not be read.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FontError {
    message: String,
}

impl FontError {
    pub fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
        }
    }
}

impl fmt::Display for FontError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.message)
    }
}

impl std::error::Error for FontError {}

/// The pixels of one glyph: one `u64` for each row, where bit `x` is the pixel in column `x`.
pub type GlyphRows = Box<[u64]>;

/// The glyphs of a pixel font, all `width` by `height` pixels.
#[derive(Debug, Clone)]
pub struct PixelGlyphs {
    pub width: usize,
    pub height: usize,
    pub glyphs: HashMap<char, GlyphRows>,
}

impl PixelGlyphs {
    /// Whether the pixel at `column` and `row` of `glyph` is on.
    pub fn is_on(glyph: &[u64], column: usize, row: usize) -> bool {
        glyph
            .get(row)
            .is_some_and(|bits| column < MAXIMUM_GLYPH_WIDTH && bits >> column & 1 == 1)
    }
}

/// The glyphs of a character font, all `height` rows tall.
#[derive(Debug, Clone)]
pub struct CharacterGlyphs {
    pub height: usize,
    /// The rows of each character, padded with spaces to the same display width.
    pub glyphs: HashMap<char, Vec<String>>,
}

#[derive(Debug, Clone)]
enum Shapes {
    Pixel(PixelGlyphs),
    Character(CharacterGlyphs),
}

/// A font: its name and the shapes of its characters.
#[derive(Debug, Clone)]
pub struct Font {
    name: String,
    shapes: Shapes,
}

impl Font {
    /// The built-in font called `name`: `"small"` (5 by 7 pixels) or `"large"` (8 by 13).
    pub fn builtin(name: &str) -> Result<Arc<Font>, FontError> {
        static SMALL: OnceLock<Arc<Font>> = OnceLock::new();
        static LARGE: OnceLock<Arc<Font>> = OnceLock::new();
        match name {
            "small" => Ok(Arc::clone(SMALL.get_or_init(|| {
                Arc::new(Font::from_mono_font(
                    "small",
                    &embedded_graphics_unicodefonts::mono_5x7_atlas(),
                ))
            }))),
            "large" => Ok(Arc::clone(LARGE.get_or_init(|| {
                Arc::new(Font::from_mono_font(
                    "large",
                    &embedded_graphics_unicodefonts::mono_8x13_atlas(),
                ))
            }))),
            _ => Err(FontError::new(format!(
                "There is no built-in font called \"{name}\". The built-in fonts are {}. Load \
                 another font from a .flf or .bdf file.",
                BUILTIN_FONT_NAMES
                    .iter()
                    .map(|name| format!("\"{name}\""))
                    .collect::<Vec<_>>()
                    .join(" and ")
            ))),
        }
    }

    /// Read a font from the bytes of a FIGlet (`.flf`) or BDF (`.bdf`) file.
    ///
    /// `name` names the font when the file does not, and in error messages.
    pub fn parse(data: &[u8], name: &str) -> Result<Font, FontError> {
        let text = String::from_utf8_lossy(data);
        let start = text.trim_start_matches('\u{feff}').trim_start();
        if start.starts_with("flf2") {
            parse_figlet(start, name)
        } else if start.starts_with("STARTFONT") {
            parse_bdf(start, name)
        } else {
            Err(FontError::new(format!(
                "\"{name}\" is not a font that xnano can read. Use a FIGlet font, whose first \
                 line starts with \"flf2a\", or a BDF font, whose first line is \"STARTFONT 2.1\"."
            )))
        }
    }

    pub fn name(&self) -> &str {
        &self.name
    }

    pub fn kind(&self) -> FontKind {
        match self.shapes {
            Shapes::Pixel(_) => FontKind::Pixel,
            Shapes::Character(_) => FontKind::Character,
        }
    }

    /// The size of one glyph: pixels for a pixel font, characters for a character font.
    ///
    /// The width of a character font is its widest glyph.
    pub fn glyph_size(&self) -> (usize, usize) {
        match &self.shapes {
            Shapes::Pixel(glyphs) => (glyphs.width, glyphs.height),
            Shapes::Character(glyphs) => (
                glyphs
                    .glyphs
                    .values()
                    .filter_map(|rows| rows.first())
                    .map(|row| UnicodeWidthStr::width(row.as_str()))
                    .max()
                    .unwrap_or(0),
                glyphs.height,
            ),
        }
    }

    /// The rows of cells one line of text takes in this font.
    ///
    /// A pixel font is drawn with half blocks, two pixel rows in each cell row.
    pub fn rows_per_line(&self) -> usize {
        match &self.shapes {
            Shapes::Pixel(glyphs) => glyphs.height.div_ceil(2),
            Shapes::Character(glyphs) => glyphs.height,
        }
    }

    pub fn has_character(&self, character: char) -> bool {
        match &self.shapes {
            Shapes::Pixel(glyphs) => glyphs.glyphs.contains_key(&character),
            Shapes::Character(glyphs) => glyphs.glyphs.contains_key(&character),
        }
    }

    pub fn pixel_glyphs(&self) -> Option<&PixelGlyphs> {
        match &self.shapes {
            Shapes::Pixel(glyphs) => Some(glyphs),
            Shapes::Character(_) => None,
        }
    }

    pub fn character_glyphs(&self) -> Option<&CharacterGlyphs> {
        match &self.shapes {
            Shapes::Character(glyphs) => Some(glyphs),
            Shapes::Pixel(_) => None,
        }
    }

    /// Copy the glyphs of an embedded-graphics mono font, for every character it has.
    fn from_mono_font(name: &str, font: &MonoFont<'static>) -> Font {
        let width = font.character_size.width as usize;
        let height = font.character_size.height as usize;
        let glyphs_per_row = (font.image.size().width as usize / width.max(1)).max(1);
        let space_index = font.glyph_mapping.index(' ');
        let mut glyphs = HashMap::new();
        for code in 0x20..=0xFFFF_u32 {
            let Some(character) = char::from_u32(code) else {
                continue;
            };
            let index = font.glyph_mapping.index(character);
            // A character the font does not have maps to the space glyph.
            if index == space_index && character != ' ' {
                continue;
            }
            let left = (index % glyphs_per_row) * width;
            let top = (index / glyphs_per_row) * height;
            let rows = (0..height)
                .map(|row| {
                    (0..width).fold(0_u64, |bits, column| {
                        let point = Point::new((left + column) as i32, (top + row) as i32);
                        match font.image.pixel(point) {
                            Some(BinaryColor::On) => bits | 1 << column,
                            _ => bits,
                        }
                    })
                })
                .collect();
            glyphs.insert(character, rows);
        }
        Font {
            name: name.to_owned(),
            shapes: Shapes::Pixel(PixelGlyphs {
                width,
                height,
                glyphs,
            }),
        }
    }
}

/// Read a BDF font: every glyph is placed on the font's bounding box, so all have one size.
fn parse_bdf(text: &str, name: &str) -> Result<Font, FontError> {
    let font = copper_bdf_parser::Font::parse(text).map_err(|error| {
        FontError::new(format!(
            "\"{name}\" could not be read as a BDF font: {error}. Check that the file is a \
             complete BDF 2.1 font."
        ))
    })?;
    let bounds = font.metadata.bounding_box;
    // The cell is as wide as most glyphs advance: a few wide glyphs (emoji, for example)
    // would otherwise make every character wide. Wider glyphs are cut at the cell's edge.
    let mut advance_counts: HashMap<i32, usize> = HashMap::new();
    for glyph in font.glyphs.iter() {
        if let Some(advance) = glyph.width_horizontal {
            *advance_counts.entry(advance.device.x).or_default() += 1;
        }
    }
    let advance = advance_counts
        .into_iter()
        .filter(|(advance, _)| *advance > 0)
        .max_by_key(|(advance, count)| (*count, -advance))
        .map_or(bounds.size.x, |(advance, _)| advance);
    let (Ok(width), Ok(height)) = (usize::try_from(advance), usize::try_from(bounds.size.y)) else {
        return Err(FontError::new(format!(
            "\"{name}\" has a bounding box of negative size, so its glyphs have no place. Check \
             the FONTBOUNDINGBOX line of the file."
        )));
    };
    if width == 0 || height == 0 || width > MAXIMUM_GLYPH_WIDTH {
        return Err(FontError::new(format!(
            "\"{name}\" has glyphs {width} by {height} pixels. xnano reads pixel fonts from 1 to \
             {MAXIMUM_GLYPH_WIDTH} pixels wide."
        )));
    }
    let top_of_font = bounds.offset.y + bounds.size.y;
    let mut glyphs = HashMap::new();
    for glyph in font.glyphs.iter() {
        let code = match glyph.encoding {
            copper_bdf_parser::Encoding::Standard(code)
            | copper_bdf_parser::Encoding::NonStandard(code) => code,
            copper_bdf_parser::Encoding::Unspecified => continue,
        };
        let Some(character) = char::from_u32(code) else {
            continue;
        };
        let glyph_box = glyph.bounding_box;
        let left = glyph_box.offset.x;
        let top = top_of_font - (glyph_box.offset.y + glyph_box.size.y);
        let mut rows = vec![0_u64; height];
        for row in 0..glyph_box.size.y.max(0) {
            for column in 0..glyph_box.size.x.max(0) {
                if glyph.pixel(column as usize, row as usize) != Some(true) {
                    continue;
                }
                let (x, y) = (left + column, top + row);
                if (0..width as i32).contains(&x) && (0..height as i32).contains(&y) {
                    rows[y as usize] |= 1 << x;
                }
            }
        }
        glyphs.insert(character, rows.into_boxed_slice());
    }
    let font_name = if font.metadata.name.trim().is_empty() {
        name.to_owned()
    } else {
        font.metadata.name.trim().to_owned()
    };
    Ok(Font {
        name: font_name,
        shapes: Shapes::Pixel(PixelGlyphs {
            width,
            height,
            glyphs,
        }),
    })
}

/// The characters every FIGlet font has, in order: ASCII 32 to 126.
const FIGLET_REQUIRED: std::ops::RangeInclusive<u32> = 32..=126;
/// The German characters that may follow the required ones, in order.
const FIGLET_GERMAN: [u32; 7] = [196, 214, 220, 228, 246, 252, 223];

/// Read a FIGlet font. Characters are placed side by side, at their full width.
fn parse_figlet(text: &str, name: &str) -> Result<Font, FontError> {
    let mut lines = text.lines();
    let header = lines.next().unwrap_or_default();
    let invalid_header = || {
        FontError::new(format!(
            "\"{name}\" has a FIGlet header that xnano cannot read: \"{header}\". The first line \
             must be \"flf2a\" followed by the hard blank character, the height, the baseline, \
             the maximum length, the layout and the number of comment lines."
        ))
    };
    let signature = header
        .split_whitespace()
        .next()
        .ok_or_else(invalid_header)?;
    let hard_blank = signature
        .strip_prefix("flf2a")
        .and_then(|rest| rest.chars().next())
        .ok_or_else(invalid_header)?;
    let numbers: Vec<i64> = header
        .split_whitespace()
        .skip(1)
        .map_while(|value| value.parse().ok())
        .collect();
    let (Some(&height), Some(&comment_lines)) = (numbers.first(), numbers.get(4)) else {
        return Err(invalid_header());
    };
    let (Ok(height), Ok(comment_lines)) = (usize::try_from(height), usize::try_from(comment_lines))
    else {
        return Err(invalid_header());
    };
    if height == 0 {
        return Err(invalid_header());
    }
    for _ in 0..comment_lines {
        lines.next();
    }

    let mut glyphs = HashMap::new();
    let read_glyph = |lines: &mut std::str::Lines<'_>| -> Option<Vec<String>> {
        let mut rows = Vec::with_capacity(height);
        for _ in 0..height {
            let line = lines.next()?.trim_end();
            let end_mark = line.chars().last()?;
            let row = line.trim_end_matches(end_mark).replace(hard_blank, " ");
            rows.push(row);
        }
        let width = rows
            .iter()
            .map(|row| UnicodeWidthStr::width(row.as_str()))
            .max()
            .unwrap_or(0);
        for row in &mut rows {
            let padding = width - UnicodeWidthStr::width(row.as_str());
            row.extend(std::iter::repeat_n(' ', padding));
        }
        Some(rows)
    };

    for code in FIGLET_REQUIRED {
        let rows = read_glyph(&mut lines).ok_or_else(|| {
            FontError::new(format!(
                "\"{name}\" ends before the character {code} (\"{}\"). A FIGlet font has every \
                 character from 32 (space) to 126 (\"~\"), each {height} lines tall.",
                char::from_u32(code).unwrap_or(' ')
            ))
        })?;
        if let Some(character) = char::from_u32(code) {
            glyphs.insert(character, rows);
        }
    }
    for code in FIGLET_GERMAN {
        // The German characters are left out of some fonts: a code tag comes next instead.
        let next_is_tag = lines
            .clone()
            .next()
            .and_then(|line| line.split_whitespace().next())
            .and_then(parse_figlet_code)
            .is_some();
        if next_is_tag {
            break;
        }
        let Some(rows) = read_glyph(&mut lines) else {
            break;
        };
        if let Some(character) = char::from_u32(code) {
            glyphs.insert(character, rows);
        }
    }
    // Code-tagged characters: a line with the character's code, then its rows.
    while let Some(tag) = lines.next() {
        let Some(code) = tag.split_whitespace().next().and_then(parse_figlet_code) else {
            break;
        };
        let Some(rows) = read_glyph(&mut lines) else {
            break;
        };
        if let Some(character) = u32::try_from(code).ok().and_then(char::from_u32) {
            glyphs.insert(character, rows);
        }
    }
    Ok(Font {
        name: name.to_owned(),
        shapes: Shapes::Character(CharacterGlyphs { height, glyphs }),
    })
}

/// A FIGlet character code: decimal, `0x` hexadecimal or `0` octal, maybe negative.
fn parse_figlet_code(text: &str) -> Option<i64> {
    let (sign, digits) = match text.strip_prefix('-') {
        Some(rest) => (-1, rest),
        None => (1, text),
    };
    let value = if let Some(hexadecimal) = digits
        .strip_prefix("0x")
        .or_else(|| digits.strip_prefix("0X"))
    {
        i64::from_str_radix(hexadecimal, 16).ok()?
    } else if digits.len() > 1 && digits.starts_with('0') {
        i64::from_str_radix(&digits[1..], 8).ok()?
    } else {
        digits.parse().ok()?
    };
    Some(sign * value)
}
