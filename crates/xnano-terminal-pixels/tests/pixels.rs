use ratatui_core::buffer::Buffer;
use ratatui_core::layout::Rect;
use ratatui_core::style::{Color, Style};
use xnano_terminal_pixels::{Font, FontKind, measure_text, render_buffer, render_text};

/// A FIGlet font two rows tall: every character is `[]` over `<>`, but `A` is drawn as `/\` over `##`.
fn figlet_font() -> String {
    let mut font = String::from("flf2a$ 2 1 4 0 1\na test font\n");
    for code in 32..=126_u32 {
        if code == u32::from(b'A') {
            font.push_str("/\\@\n##@@\n");
        } else if code == 32 {
            font.push_str("$@\n$@@\n");
        } else {
            font.push_str("[]@\n<>@@\n");
        }
    }
    font.push_str("0x263A smile\n:)@\n..@@\n");
    font
}

/// A BDF font of 3 by 4 pixels with one glyph, `I`: a vertical bar in the middle column.
const BDF_FONT: &str = "STARTFONT 2.1
FONT tiny
SIZE 4 75 75
FONTBOUNDINGBOX 3 4 0 0
STARTPROPERTIES 2
FONT_ASCENT 4
FONT_DESCENT 0
ENDPROPERTIES
CHARS 1
STARTCHAR I
ENCODING 73
SWIDTH 500 0
DWIDTH 3 0
BBX 3 4 0 0
BITMAP
40
40
40
40
ENDCHAR
ENDFONT
";

#[test]
fn figlet_font_writes_its_rows_side_by_side() {
    let font = Font::parse(figlet_font().as_bytes(), "test").unwrap();
    assert_eq!(font.kind(), FontKind::Character);
    assert_eq!(font.rows_per_line(), 2);
    assert_eq!(render_text(&font, "AB"), vec!["/\\[]", "##<>"]);
    assert_eq!(render_text(&font, "A A"), vec!["/\\ /\\", "## ##"]);
    assert!(font.has_character('\u{263A}'));
    assert_eq!(render_text(&font, "\u{263A}"), vec![":)", ".."]);
}

#[test]
fn missing_character_is_written_as_itself() {
    let font = Font::parse(figlet_font().as_bytes(), "test").unwrap();
    assert_eq!(render_text(&font, "é"), vec!["é", " "]);
}

#[test]
fn lines_stack_and_measure_in_cells() {
    let font = Font::parse(figlet_font().as_bytes(), "test").unwrap();
    assert_eq!(render_text(&font, "A\nBB").len(), 4);
    assert_eq!(measure_text(Some(&font), "A\nBB"), (4, 4));
    assert_eq!(measure_text(None, "hello\nhi"), (5, 2));
    assert_eq!(measure_text(None, ""), (0, 1));
}

#[test]
fn bdf_font_is_drawn_with_half_blocks() {
    let font = Font::parse(BDF_FONT.as_bytes(), "tiny.bdf").unwrap();
    assert_eq!(font.kind(), FontKind::Pixel);
    assert_eq!(font.glyph_size(), (3, 4));
    assert_eq!(font.name(), "tiny");
    assert_eq!(render_text(&font, "I"), vec![" █ ", " █ "]);
    // A character the font does not have keeps the glyph's width.
    assert_eq!(render_text(&font, "x"), vec!["x  ", "   "]);
}

#[test]
fn builtin_fonts_have_ascii() {
    for name in xnano_terminal_pixels::BUILTIN_FONT_NAMES {
        let font = Font::builtin(name).unwrap();
        assert_eq!(font.kind(), FontKind::Pixel);
        for character in ' '..='~' {
            assert!(font.has_character(character), "{name} lacks {character:?}");
        }
    }
    assert_eq!(Font::builtin("small").unwrap().glyph_size(), (5, 7));
    assert_eq!(Font::builtin("large").unwrap().glyph_size(), (8, 13));
    assert!(Font::builtin("large").unwrap().has_character('─'));
    let error = Font::builtin("huge").unwrap_err().to_string();
    assert!(error.contains("\"small\" and \"large\""), "{error}");
}

#[test]
fn unknown_data_is_refused_with_the_formats() {
    let error = Font::parse(b"hello", "notes.txt").unwrap_err().to_string();
    assert!(
        error.contains("notes.txt") && error.contains("STARTFONT 2.1"),
        "{error}"
    );
    let error = Font::parse(b"flf2a$ 2 1 4 0 0\n $@\n $@@\n", "short.flf")
        .unwrap_err()
        .to_string();
    assert!(error.contains("ends before the character 33"), "{error}");
}

#[test]
fn buffer_is_drawn_cell_by_cell() {
    let font = Font::builtin("large").unwrap();
    let mut buffer = Buffer::empty(Rect::new(0, 0, 2, 1));
    buffer[(0, 0)]
        .set_symbol("█")
        .set_style(Style::default().fg(Color::Rgb(255, 0, 0)));
    buffer[(1, 0)]
        .set_symbol(" ")
        .set_style(Style::default().bg(Color::Rgb(0, 0, 255)));
    let pixmap = render_buffer(&buffer, &font).unwrap();
    assert_eq!((pixmap.width, pixmap.height), (16, 13));
    let pixel = |x: usize, y: usize| {
        let index = (y * pixmap.width + x) * 3;
        [
            pixmap.data[index],
            pixmap.data[index + 1],
            pixmap.data[index + 2],
        ]
    };
    assert_eq!(pixel(0, 0), [255, 0, 0]);
    assert_eq!(pixel(7, 12), [255, 0, 0]);
    assert_eq!(pixel(8, 0), [0, 0, 255]);
    let png = pixmap.to_png();
    assert_eq!(&png[1..4], b"PNG");
}

#[test]
fn image_needs_a_pixel_font() {
    let font = Font::parse(figlet_font().as_bytes(), "test").unwrap();
    let buffer = Buffer::empty(Rect::new(0, 0, 1, 1));
    let error = render_buffer(&buffer, &font).unwrap_err().to_string();
    assert!(error.contains("character font"), "{error}");
}
