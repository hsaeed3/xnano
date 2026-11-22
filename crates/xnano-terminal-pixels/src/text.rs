//! Text written in a font: rows of characters that a terminal can show.
//!
//! A character font gives its own rows. A pixel font is drawn with half blocks, so each cell
//! holds two pixels, one above the other, and the text keeps the color of the cells it is in.
//! A character the font does not have is written as itself, in the top row of its place.

use unicode_width::{UnicodeWidthChar, UnicodeWidthStr};

use crate::font::{Font, PixelGlyphs};

/// The rows that draw `text` in `font`. Each line of `text` becomes
/// [`Font::rows_per_line`] rows, and the rows of one line have the same display width.
pub fn render_text(font: &Font, text: &str) -> Vec<String> {
    let rows_per_line = font.rows_per_line();
    let mut rows = Vec::new();
    for line in text.split('\n') {
        let mut line_rows = vec![String::new(); rows_per_line];
        for character in line.chars() {
            write_character(font, character, &mut line_rows);
        }
        rows.extend(line_rows);
    }
    rows
}

/// The width and height in cells of `text` written in `font`, or in the terminal font when
/// `font` is `None`.
pub fn measure_text(font: Option<&Font>, text: &str) -> (usize, usize) {
    match font {
        None => {
            let lines: Vec<&str> = text.split('\n').collect();
            let width = lines
                .iter()
                .map(|line| UnicodeWidthStr::width(*line))
                .max()
                .unwrap_or(0);
            (width, lines.len())
        }
        Some(font) => {
            let rows = render_text(font, text);
            let width = rows
                .iter()
                .map(|row| UnicodeWidthStr::width(row.as_str()))
                .max()
                .unwrap_or(0);
            (width, rows.len())
        }
    }
}

/// The half block that shows the pixels `top` and `bottom` of one cell.
fn half_block(top: bool, bottom: bool) -> char {
    match (top, bottom) {
        (false, false) => ' ',
        (true, false) => '\u{2580}',
        (false, true) => '\u{2584}',
        (true, true) => '\u{2588}',
    }
}

fn write_character(font: &Font, character: char, rows: &mut [String]) {
    let character = if character == '\t' { ' ' } else { character };
    let Some(character_width) = UnicodeWidthChar::width(character) else {
        // Control characters take no place.
        return;
    };
    if let Some(glyphs) = font.pixel_glyphs() {
        if let Some(glyph) = glyphs.glyphs.get(&character) {
            for (cell_row, row) in rows.iter_mut().enumerate() {
                for column in 0..glyphs.width {
                    row.push(half_block(
                        PixelGlyphs::is_on(glyph, column, cell_row * 2),
                        PixelGlyphs::is_on(glyph, column, cell_row * 2 + 1),
                    ));
                }
            }
            return;
        }
        write_missing(character, character_width.max(glyphs.width), rows);
        return;
    }
    if let Some(glyphs) = font.character_glyphs() {
        if let Some(glyph) = glyphs.glyphs.get(&character) {
            for (row, glyph_row) in rows.iter_mut().zip(glyph) {
                row.push_str(glyph_row);
            }
            return;
        }
        write_missing(character, character_width, rows);
    }
}

/// Write a character the font does not have as itself, padded to `width` cells.
fn write_missing(character: char, width: usize, rows: &mut [String]) {
    let character_width = UnicodeWidthChar::width(character).unwrap_or(0);
    for (index, row) in rows.iter_mut().enumerate() {
        if index == 0 && character_width > 0 {
            row.push(character);
            row.extend(std::iter::repeat_n(' ', width - character_width));
        } else {
            row.extend(std::iter::repeat_n(' ', width));
        }
    }
}
