//! Styled text from ANSI text: what a program prints for a terminal, read as styled spans.
//!
//! The SGR sequences (`ESC [ … m`) set the colors and the text modifiers. A newline starts a
//! new line, a tab moves to the next column that is a multiple of eight, and a carriage return
//! moves back to the start of the line, so the text after it writes over the line as it does
//! on a terminal. Every other control character and escape sequence (cursor movement, erasing,
//! titles, modes, and OSC, DCS and APC strings) is removed.

use crate::style::{Color, Modifier, Style};
use crate::text::{Span, grapheme_width, split_graphemes};

/// The columns between two tab stops.
const TAB_STOP: usize = 8;

/// Read `text` as the output of a program, as spans with a `\n` between two lines.
///
/// A final newline does not start an empty line, as with Python's `str.splitlines`.
#[must_use]
pub fn spans_from_ansi(text: &str) -> Vec<Span> {
    let mut reader = AnsiReader::default();
    let mut parser = vte::Parser::new();
    parser.advance(&mut reader, text.as_bytes());
    reader.finish()
}

/// One column of a line.
#[derive(Debug, Clone, Copy)]
enum Column {
    /// A column that nothing was written to, such as one that a tab skipped.
    Blank,
    /// A grapheme: where its text is in the line's text, and its style. A wide grapheme also
    /// takes the next column.
    Grapheme {
        start: usize,
        end: usize,
        style: Style,
    },
    /// The second column of a wide grapheme.
    Continuation,
}

/// A line of the terminal: the text of the graphemes written to it, and its columns.
///
/// All graphemes share one string, so writing a line allocates as it grows, not once for
/// each grapheme. Text that a carriage return writes over stays in the string, unused.
#[derive(Default)]
struct Line {
    text: String,
    columns: Vec<Column>,
}

/// The state of a terminal line while the text is read.
#[derive(Default)]
struct AnsiReader {
    /// The style of the text printed next.
    style: Style,
    /// Text that was printed in `style` and is not in the line yet.
    printed: String,
    /// The finished lines.
    lines: Vec<Line>,
    /// The line that the text is written to.
    line: Line,
    /// The column that the next grapheme is written to.
    cursor: usize,
}

impl AnsiReader {
    /// Write the printed text into the line, one grapheme at a time, measured as cells are.
    fn place_printed(&mut self) {
        if self.printed.is_empty() {
            return;
        }
        let printed = std::mem::take(&mut self.printed);
        for grapheme in split_graphemes(&printed) {
            if grapheme.chars().any(char::is_control) {
                continue;
            }
            match grapheme_width(grapheme) {
                0 => self.extend_previous(grapheme),
                width => self.place(grapheme, width),
            }
        }
    }

    /// Join a zero-width grapheme, such as a combining mark, to the grapheme before the cursor.
    fn extend_previous(&mut self, grapheme: &str) {
        let line = &mut self.line;
        let mut index = self.cursor.min(line.columns.len());
        while index > 0 {
            index -= 1;
            match line.columns[index] {
                Column::Continuation => {}
                Column::Grapheme { start, end, style } => {
                    // The grapheme's text moves to the end of the line's text to grow there.
                    let start = if end == line.text.len() {
                        start
                    } else {
                        let moved = line.text.len();
                        line.text.extend_from_within(start..end);
                        moved
                    };
                    line.text.push_str(grapheme);
                    line.columns[index] = Column::Grapheme {
                        start,
                        end: line.text.len(),
                        style,
                    };
                    return;
                }
                Column::Blank => return,
            }
        }
    }

    /// Write a grapheme of `width` columns at the cursor, over what the line held there.
    fn place(&mut self, grapheme: &str, width: usize) {
        let columns = &mut self.line.columns;
        let start = self.cursor;
        let end = start + width;
        if columns.len() < end {
            columns.resize(end, Column::Blank);
        }
        // A wide grapheme that this one covers half of loses its other half.
        if start > 0 && matches!(columns[start], Column::Continuation) {
            columns[start - 1] = Column::Blank;
        }
        if matches!(columns.get(end), Some(Column::Continuation)) {
            columns[end] = Column::Blank;
        }
        let text_start = self.line.text.len();
        self.line.text.push_str(grapheme);
        columns[start] = Column::Grapheme {
            start: text_start,
            end: self.line.text.len(),
            style: self.style,
        };
        for column in &mut columns[start + 1..end] {
            *column = Column::Continuation;
        }
        self.cursor = end;
    }

    /// Apply the parameters of an SGR sequence to the style of the text printed next.
    fn select_graphic_rendition(&mut self, parameters: &vte::Params) {
        if parameters.is_empty() {
            self.style = Style::default();
            return;
        }
        let mut parameters = parameters.iter();
        while let Some(parameter) = parameters.next() {
            let code = parameter.first().copied().unwrap_or(0);
            match code {
                0 => self.style = Style::default(),
                1 => self.add(Modifier::BOLD),
                2 => self.add(Modifier::DIM),
                3 => self.add(Modifier::ITALIC),
                // `4:0` turns the underline off; `4:1` to `4:5` are kinds of underline.
                4 if parameter.get(1) == Some(&0) => self.remove(Modifier::UNDERLINED),
                4 | 21 => self.add(Modifier::UNDERLINED),
                5 => self.add(Modifier::SLOW_BLINK),
                6 => self.add(Modifier::RAPID_BLINK),
                7 => self.add(Modifier::REVERSED),
                8 => self.add(Modifier::HIDDEN),
                9 => self.add(Modifier::CROSSED_OUT),
                22 => self.remove(Modifier::BOLD | Modifier::DIM),
                23 => self.remove(Modifier::ITALIC),
                24 => self.remove(Modifier::UNDERLINED),
                25 => self.remove(Modifier::SLOW_BLINK | Modifier::RAPID_BLINK),
                27 => self.remove(Modifier::REVERSED),
                28 => self.remove(Modifier::HIDDEN),
                29 => self.remove(Modifier::CROSSED_OUT),
                30..=37 => self.style.fg = Some(standard_color(code - 30)),
                38 => {
                    if let Some(color) = extended_color(parameter, &mut parameters) {
                        self.style.fg = Some(color);
                    }
                }
                39 => self.style.fg = None,
                40..=47 => self.style.bg = Some(standard_color(code - 40)),
                48 => {
                    if let Some(color) = extended_color(parameter, &mut parameters) {
                        self.style.bg = Some(color);
                    }
                }
                49 => self.style.bg = None,
                58 => {
                    if let Some(color) = extended_color(parameter, &mut parameters) {
                        self.style.underline_color = Some(color);
                    }
                }
                59 => self.style.underline_color = None,
                90..=97 => self.style.fg = Some(standard_color(code - 90 + 8)),
                100..=107 => self.style.bg = Some(standard_color(code - 100 + 8)),
                _ => {}
            }
        }
    }

    fn add(&mut self, modifier: Modifier) {
        self.style.add_modifier.insert(modifier);
    }

    fn remove(&mut self, modifier: Modifier) {
        self.style.add_modifier.remove(modifier);
    }

    /// The spans of every line, with a `\n` between two lines.
    fn finish(mut self) -> Vec<Span> {
        self.place_printed();
        if !self.line.columns.is_empty() {
            self.lines.push(std::mem::take(&mut self.line));
        }
        let mut spans: Vec<Span> = Vec::new();
        for (index, line) in self.lines.iter().enumerate() {
            if index > 0 {
                push_text(&mut spans, "\n", Style::default());
            }
            for column in &line.columns {
                match *column {
                    Column::Blank => push_text(&mut spans, " ", Style::default()),
                    Column::Grapheme { start, end, style } => {
                        push_text(&mut spans, &line.text[start..end], style);
                    }
                    Column::Continuation => {}
                }
            }
        }
        spans
    }
}

impl vte::Perform for AnsiReader {
    fn print(&mut self, character: char) {
        self.printed.push(character);
    }

    fn execute(&mut self, byte: u8) {
        self.place_printed();
        match byte {
            b'\n' => {
                self.lines.push(std::mem::take(&mut self.line));
                self.cursor = 0;
            }
            b'\r' => self.cursor = 0,
            b'\t' => self.cursor = (self.cursor / TAB_STOP + 1) * TAB_STOP,
            _ => {}
        }
    }

    fn csi_dispatch(
        &mut self,
        parameters: &vte::Params,
        intermediates: &[u8],
        ignore: bool,
        action: char,
    ) {
        if action == 'm' && intermediates.is_empty() && !ignore {
            self.place_printed();
            self.select_graphic_rendition(parameters);
        }
    }
}

/// Add text to the last span when it has the same style, or start a new span.
fn push_text(spans: &mut Vec<Span>, text: &str, style: Style) {
    match spans.last_mut() {
        Some(last) if last.style == style => last.text.push_str(text),
        _ => spans.push(Span::new(text, style)),
    }
}

/// One of the 16 colors that every terminal has, by its SGR number (0 to 15).
fn standard_color(index: u16) -> Color {
    match index {
        0 => Color::Black,
        1 => Color::Red,
        2 => Color::Green,
        3 => Color::Yellow,
        4 => Color::Blue,
        5 => Color::Magenta,
        6 => Color::Cyan,
        7 => Color::Gray,
        8 => Color::DarkGray,
        9 => Color::LightRed,
        10 => Color::LightGreen,
        11 => Color::LightYellow,
        12 => Color::LightBlue,
        13 => Color::LightMagenta,
        14 => Color::LightCyan,
        _ => Color::White,
    }
}

/// The color of `38`, `48` or `58`: a palette index (`5;n`) or a true color (`2;r;g;b`).
///
/// Both the common form with semicolons and the ITU T.416 form with colons are read. The
/// colon form may name a color space before the channels (`38:2:0:r:g:b`), which is skipped.
fn extended_color<'parameters>(
    parameter: &[u16],
    rest: &mut impl Iterator<Item = &'parameters [u16]>,
) -> Option<Color> {
    if parameter.len() > 1 {
        return match parameter[1] {
            5 => parameter
                .get(2)
                .map(|&index| Color::Indexed(channel(index))),
            2 => {
                let values = &parameter[2..];
                let channels = if values.len() >= 4 {
                    &values[1..]
                } else {
                    values
                };
                match channels {
                    [red, green, blue, ..] => {
                        Some(Color::Rgb(channel(*red), channel(*green), channel(*blue)))
                    }
                    _ => None,
                }
            }
            _ => None,
        };
    }
    match *rest.next()?.first()? {
        5 => rest
            .next()
            .and_then(<[u16]>::first)
            .map(|&index| Color::Indexed(channel(index))),
        2 => {
            let red = *rest.next()?.first()?;
            let green = *rest.next()?.first()?;
            let blue = *rest.next()?.first()?;
            Some(Color::Rgb(channel(red), channel(green), channel(blue)))
        }
        _ => None,
    }
}

/// A color channel or palette index, with values past 255 held at 255.
fn channel(value: u16) -> u8 {
    u8::try_from(value).unwrap_or(u8::MAX)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn read(text: &str) -> Vec<(String, Style)> {
        spans_from_ansi(text)
            .into_iter()
            .map(|span| (span.text, span.style))
            .collect()
    }

    fn plain(text: &str) -> String {
        spans_from_ansi(text)
            .into_iter()
            .map(|span| span.text)
            .collect()
    }

    #[test]
    fn colors_and_modifiers_style_the_text_until_a_reset() {
        let bold_red = Style::default().fg(Color::Red).add_modifier(Modifier::BOLD);
        assert_eq!(
            read("\x1b[1;31merror:\x1b[0m disk full"),
            vec![
                ("error:".to_owned(), bold_red),
                (" disk full".to_owned(), Style::default()),
            ]
        );
    }

    #[test]
    fn palette_and_true_colors_read_in_both_forms() {
        let expected = [
            ("\x1b[38;5;208mx", Color::Indexed(208)),
            ("\x1b[38:5:208mx", Color::Indexed(208)),
            ("\x1b[38;2;255;136;0mx", Color::Rgb(255, 136, 0)),
            ("\x1b[38:2::255:136:0mx", Color::Rgb(255, 136, 0)),
            ("\x1b[38:2:255:136:0mx", Color::Rgb(255, 136, 0)),
            ("\x1b[94mx", Color::LightBlue),
        ];
        for (text, color) in expected {
            assert_eq!(
                read(text),
                vec![("x".to_owned(), Style::default().fg(color))],
                "{text:?}"
            );
        }
        assert_eq!(
            read("\x1b[4;58;2;255;0;0mx")[0].1,
            Style::default()
                .add_modifier(Modifier::UNDERLINED)
                .underline_color(Color::Rgb(255, 0, 0))
        );
        assert_eq!(
            read("\x1b[48;5;4;1mx")[0].1,
            Style::default()
                .bg(Color::Indexed(4))
                .add_modifier(Modifier::BOLD)
        );
    }

    #[test]
    fn turning_a_modifier_off_leaves_the_others() {
        let spans = read("\x1b[1;3mA\x1b[22mB\x1b[39;23mC");
        assert_eq!(
            spans[1],
            (
                "B".to_owned(),
                Style::default().add_modifier(Modifier::ITALIC)
            )
        );
        assert_eq!(spans[2], ("C".to_owned(), Style::default()));
    }

    #[test]
    fn lines_tabs_and_carriage_returns_lay_out_as_on_a_terminal() {
        assert_eq!(plain("one\ntwo\n"), "one\ntwo");
        assert_eq!(plain("a\n\nb"), "a\n\nb");
        assert_eq!(plain("a\tb"), "a       b");
        assert_eq!(plain("12345678\tx"), "12345678        x");
        assert_eq!(
            plain("downloading 10%\rdownloading 100%\n"),
            "downloading 100%"
        );
        assert_eq!(plain("abcdef\rXY"), "XYcdef");
        assert_eq!(plain("one\r\ntwo"), "one\ntwo");
        assert_eq!(plain(""), "");
    }

    #[test]
    fn other_sequences_and_control_characters_are_removed() {
        let text = "\x1b[2J\x1b[H\x1b]0;title\x07\x1b[?25lshown\x1b[5A\x07\x08\x1bP1$r\x1b\\!";
        assert_eq!(plain(text), "shown!");
    }

    #[test]
    fn wide_graphemes_and_combining_marks_keep_their_cells() {
        assert_eq!(plain("日本\rx"), "x 本");
        assert_eq!(plain("e\u{301}!"), "e\u{301}!");
        assert_eq!(plain("\x1b[31me\x1b[0m\u{301}"), "e\u{301}");
    }
}
