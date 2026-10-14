//! Styled text, Unicode layout and the text editor, independent of any widget.
//!
//! Offsets are counted in characters (Unicode code points), the same unit Python uses to
//! index a `str`, and always fall on grapheme boundaries. Columns are display columns.

use unicode_segmentation::UnicodeSegmentation;
use unicode_width::UnicodeWidthStr;

use crate::event::{KeyEvent, KeyKind, KeyModifiers};
use crate::style::Style;

/// The extended grapheme clusters of `text`, the same as `UnicodeSegmentation::graphemes`.
///
/// An ASCII character followed by another ASCII character is always a cluster of its own
/// (no ASCII character extends or joins a neighbour, except the carriage return and line
/// feed pair), so those skip the Unicode tables. Everything else is segmented by
/// `unicode-segmentation`, starting from a known boundary.
pub fn split_graphemes(text: &str) -> impl Iterator<Item = &str> {
    let mut position = 0;
    std::iter::from_fn(move || {
        let rest = &text[position..];
        let bytes = rest.as_bytes();
        let first = *bytes.first()?;
        let second = bytes.get(1).copied();
        let length = if first < 0x80
            && second.is_none_or(|next| next < 0x80)
            && !(first == b'\r' && second == Some(b'\n'))
        {
            1
        } else {
            rest.graphemes(true).next()?.len()
        };
        position += length;
        Some(&rest[..length])
    })
}

/// Display columns of `text`.
pub fn display_width(text: &str) -> usize {
    split_graphemes(text).map(grapheme_width).sum()
}

/// Display columns of one grapheme. Control characters take none.
pub fn grapheme_width(grapheme: &str) -> usize {
    if let [byte] = grapheme.as_bytes() {
        // One byte is one ASCII character.
        return usize::from(!byte.is_ascii_control());
    }
    if grapheme.chars().any(char::is_control) {
        return 0;
    }
    UnicodeWidthStr::width(grapheme)
}

/// A run of text in one style.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Span {
    pub text: String,
    pub style: Style,
}

impl Span {
    pub fn new(text: impl Into<String>, style: Style) -> Self {
        Self {
            text: text.into(),
            style,
        }
    }
}

/// One row of styled text.
pub type Line = Vec<Span>;

/// Whether any glyph of `lines` takes more than one column.
pub fn has_wide_glyphs(lines: &[Line]) -> bool {
    lines
        .iter()
        .flatten()
        .any(|span| split_graphemes(&span.text).any(|grapheme| grapheme_width(grapheme) > 1))
}

/// One grapheme with its style and width, while a row is being wrapped.
struct Piece<'a> {
    text: &'a str,
    style: Style,
    width: usize,
    is_space: bool,
}

/// Word-wrap `lines` into rows of at most `width` columns.
///
/// Words break at spaces, and a word longer than a row is folded across rows. Wide glyphs
/// count their real width, so a row never holds more than `width` columns and a glyph that
/// does not fit moves to the next row whole. With `should_trim`, the spaces at a break are
/// dropped; without it they are kept, and the ones that do not fit begin the next row.
pub fn wrap_lines(lines: &[Line], width: usize, should_trim: bool) -> Vec<Line> {
    let width = width.max(1);
    let mut rows: Vec<Line> = Vec::new();
    for line in lines {
        let pieces: Vec<Piece<'_>> = line
            .iter()
            .flat_map(|span| {
                split_graphemes(&span.text).map(move |grapheme| Piece {
                    text: grapheme,
                    style: span.style,
                    width: grapheme_width(grapheme),
                    is_space: grapheme.chars().all(char::is_whitespace),
                })
            })
            .collect();
        let mut current: Vec<&Piece<'_>> = Vec::new();
        let mut used = 0_usize;
        let mut index = 0;
        while index < pieces.len() {
            let token_end = pieces[index..]
                .iter()
                .position(|piece| piece.is_space != pieces[index].is_space)
                .map_or(pieces.len(), |offset| index + offset);
            let token = &pieces[index..token_end];
            let token_width: usize = token.iter().map(|piece| piece.width).sum();
            index = token_end;
            if token[0].is_space {
                if used + token_width <= width {
                    current.extend(token);
                    used += token_width;
                } else if should_trim {
                    // The spaces at a break are dropped.
                    flush_row(&mut rows, &mut current, true);
                    used = 0;
                } else {
                    flush_row(&mut rows, &mut current, false);
                    current.extend(token);
                    used = token_width.min(width);
                }
                continue;
            }
            if used + token_width <= width {
                current.extend(token);
                used += token_width;
                continue;
            }
            if token_width <= width {
                flush_row(&mut rows, &mut current, should_trim);
                current.extend(token);
                used = token_width;
                continue;
            }
            // A word longer than a row is folded.
            if used > 0 {
                flush_row(&mut rows, &mut current, should_trim);
                used = 0;
            }
            for piece in token {
                if used > 0 && used + piece.width > width {
                    flush_row(&mut rows, &mut current, should_trim);
                    used = 0;
                }
                current.push(piece);
                used += piece.width;
                if used >= width {
                    flush_row(&mut rows, &mut current, should_trim);
                    used = 0;
                }
            }
        }
        flush_row(&mut rows, &mut current, should_trim);
    }
    rows
}

/// End the row being built: trailing spaces are dropped when trimming, and equal styles are merged.
fn flush_row(rows: &mut Vec<Line>, current: &mut Vec<&Piece<'_>>, should_trim: bool) {
    while should_trim && current.last().is_some_and(|piece| piece.is_space) {
        current.pop();
    }
    let mut row: Line = Vec::new();
    for piece in current.drain(..) {
        match row.last_mut() {
            Some(span) if span.style == piece.style => span.text.push_str(piece.text),
            _ => row.push(Span::new(piece.text, piece.style)),
        }
    }
    rows.push(row);
}

/// Split spans into rows at every `\n` (and `\r\n`).
pub fn split_lines(spans: &[Span]) -> Vec<Line> {
    let mut lines = vec![Vec::new()];
    for span in spans {
        let mut parts = span.text.split('\n').peekable();
        while let Some(part) = parts.next() {
            let part = part.strip_suffix('\r').unwrap_or(part);
            if !part.is_empty() {
                lines
                    .last_mut()
                    .expect("there is always a current line")
                    .push(Span::new(part, span.style));
            }
            if parts.peek().is_some() {
                lines.push(Vec::new());
            }
        }
    }
    lines
}

/// The widest row, in display columns.
pub fn lines_width(lines: &[Line]) -> usize {
    lines
        .iter()
        .map(|line| {
            line.iter()
                .map(|span| display_width(&span.text))
                .sum::<usize>()
        })
        .max()
        .unwrap_or(0)
}

/// One displayed row of laid-out text.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct TextLine {
    pub text: String,
    pub start_offset: usize,
    pub end_offset: usize,
    pub width: usize,
}

/// Text broken into displayed rows.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct TextLayout {
    pub lines: Vec<TextLine>,
    pub cursor_cell: Option<(usize, usize)>,
    graphemes: Vec<Vec<(usize, usize)>>,
}

fn is_break_opportunity(grapheme: &str) -> bool {
    grapheme.chars().all(char::is_whitespace)
}

/// Lay out `text` in rows at most `width` columns wide.
///
/// With `should_wrap` false, only line breaks in the text start a new row.
pub fn layout_text(
    text: &str,
    width: usize,
    cursor_offset: Option<usize>,
    should_wrap: bool,
) -> TextLayout {
    let width = width.max(1);
    let mut lines: Vec<TextLine> = Vec::new();
    let mut grapheme_columns: Vec<Vec<(usize, usize)>> = Vec::new();
    let mut offset = 0_usize;
    for paragraph in text.split('\n') {
        let graphemes: Vec<(&str, usize, usize)> = split_graphemes(paragraph)
            .map(|grapheme| (grapheme, grapheme_width(grapheme), grapheme.chars().count()))
            .collect();
        let mut start = 0;
        let mut row_width = 0;
        let mut last_break: Option<usize> = None;
        let mut index = 0;
        let paragraph_start = offset;
        // Rows are flushed in order and end where the next begins, so the characters before
        // a row are a running total instead of a sum over every earlier grapheme.
        let mut prefix = 0_usize;
        let mut flush = |from: usize, to: usize, lines: &mut Vec<TextLine>| {
            let slice = &graphemes[from..to];
            let mut columns = Vec::with_capacity(slice.len());
            let mut column = 0;
            let mut chars_before = 0;
            for (_, grapheme_columns_width, characters) in slice {
                columns.push((column, chars_before));
                column += grapheme_columns_width;
                chars_before += characters;
            }
            debug_assert!(from <= to);
            let characters = chars_before;
            let mut row_text = String::with_capacity(slice.iter().map(|entry| entry.0.len()).sum());
            for (grapheme, _, _) in slice {
                row_text.push_str(grapheme);
            }
            lines.push(TextLine {
                text: row_text,
                start_offset: paragraph_start + prefix,
                end_offset: paragraph_start + prefix + characters,
                width: column,
            });
            prefix += characters;
            grapheme_columns.push(columns);
        };
        while index < graphemes.len() {
            let (grapheme, columns, _) = graphemes[index];
            // Trailing whitespace may hang past the edge instead of forcing a wrap.
            if should_wrap
                && row_width + columns > width
                && index > start
                && !is_break_opportunity(grapheme)
            {
                let break_at = match last_break {
                    Some(position) if position > start => position,
                    _ => index,
                };
                flush(start, break_at, &mut lines);
                start = break_at;
                row_width = graphemes[start..index].iter().map(|entry| entry.1).sum();
                last_break = None;
                continue;
            }
            row_width += columns;
            index += 1;
            if is_break_opportunity(grapheme) {
                last_break = Some(index);
            }
        }
        flush(start, graphemes.len(), &mut lines);
        offset = paragraph_start + paragraph.chars().count() + 1;
    }
    let mut layout = TextLayout {
        lines,
        cursor_cell: None,
        graphemes: grapheme_columns,
    };
    if let Some(cursor) = cursor_offset {
        layout.cursor_cell = Some(layout.cell_at_text_offset(cursor));
    }
    layout
}

impl TextLayout {
    /// The `(column, row)` where the character at `offset` is drawn.
    pub fn cell_at_text_offset(&self, offset: usize) -> (usize, usize) {
        for (row, line) in self.lines.iter().enumerate() {
            let is_last = row + 1 == self.lines.len();
            let next_start = self.lines.get(row + 1).map(|next| next.start_offset);
            let is_inside = offset >= line.start_offset
                && (offset < line.end_offset
                    || (offset == line.end_offset && (is_last || next_start != Some(offset))));
            if is_inside {
                let local = offset - line.start_offset;
                let column = if offset == line.end_offset {
                    line.width
                } else {
                    self.graphemes[row]
                        .iter()
                        .rev()
                        .find(|(_, characters)| *characters <= local)
                        .map_or(0, |(column, _)| *column)
                };
                return (column, row);
            }
        }
        let last = self.lines.len().saturating_sub(1);
        (self.lines.get(last).map_or(0, |line| line.width), last)
    }

    /// The offset of the grapheme drawn at `(column, row)`; positions past the end of a
    /// row give that row's end.
    pub fn text_offset_at(&self, column: usize, row: usize) -> usize {
        let Some(line) = self.lines.get(row.min(self.lines.len().saturating_sub(1))) else {
            return 0;
        };
        let row = row.min(self.lines.len() - 1);
        if column >= line.width {
            return line.end_offset;
        }
        let entries = &self.graphemes[row];
        let position = entries.partition_point(|(start, _)| *start <= column);
        entries
            .get(position.saturating_sub(1))
            .map_or(line.start_offset, |(_, characters)| {
                line.start_offset + characters
            })
    }
}

fn char_to_byte(text: &str, offset: usize) -> usize {
    text.char_indices()
        .nth(offset)
        .map_or(text.len(), |(byte, _)| byte)
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum EditKind {
    Insert,
    Delete,
    Other,
}

/// Editable text with a cursor, undo and redo.
#[derive(Debug, Clone)]
pub struct TextEditor {
    text: String,
    cursor: usize,
    pub is_single_line: bool,
    pub placeholder_text: String,
    /// How the cursor cell is drawn.
    pub cursor_style: Style,
    /// How selected text is drawn.
    pub selection_style: Style,
    anchor: Option<usize>,
    undo: Vec<(String, usize)>,
    redo: Vec<(String, usize)>,
    last_edit: Option<EditKind>,
}

impl std::fmt::Debug for EditKind {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(match self {
            Self::Insert => "insert",
            Self::Delete => "delete",
            Self::Other => "other",
        })
    }
}

impl TextEditor {
    pub fn new(text: &str, is_single_line: bool) -> Self {
        let mut editor = Self {
            text: String::new(),
            cursor: 0,
            is_single_line,
            placeholder_text: String::new(),
            cursor_style: Style::default().add_modifier(crate::style::Modifier::REVERSED),
            selection_style: Style::default().add_modifier(crate::style::Modifier::REVERSED),
            anchor: None,
            undo: Vec::new(),
            redo: Vec::new(),
            last_edit: None,
        };
        editor.text = editor.sanitize(text);
        editor.cursor = editor.text.chars().count();
        editor
    }

    fn sanitize(&self, text: &str) -> String {
        let unified = text.replace("\r\n", "\n").replace('\r', "\n");
        if self.is_single_line {
            unified.replace('\n', " ")
        } else {
            unified
        }
    }

    pub fn text(&self) -> &str {
        &self.text
    }

    pub fn cursor_offset(&self) -> usize {
        self.cursor
    }

    pub fn length(&self) -> usize {
        self.text.chars().count()
    }

    fn checkpoint(&mut self, kind: EditKind) {
        let continues_run =
            matches!(kind, EditKind::Insert | EditKind::Delete) && self.last_edit == Some(kind);
        if !continues_run {
            self.undo.push((self.text.clone(), self.cursor));
            if self.undo.len() > 500 {
                self.undo.remove(0);
            }
        }
        self.redo.clear();
        self.last_edit = Some(kind);
    }

    /// Replace the text, keeping the cursor at the end; the change can be undone.
    pub fn set_text(&mut self, text: &str) {
        self.checkpoint(EditKind::Other);
        self.anchor = None;
        self.text = self.sanitize(text);
        self.cursor = self.length();
    }

    /// Insert `text` at the cursor.
    pub fn insert_text(&mut self, text: &str) {
        let text = self.sanitize(text);
        if text.is_empty() {
            return;
        }
        let is_word_break = text.chars().any(char::is_whitespace);
        self.checkpoint(if is_word_break {
            EditKind::Other
        } else {
            EditKind::Insert
        });
        let byte = char_to_byte(&self.text, self.cursor);
        self.text.insert_str(byte, &text);
        self.cursor += text.chars().count();
    }

    /// Move the cursor to `offset`, snapped back to a grapheme boundary.
    pub fn move_cursor(&mut self, offset: usize) {
        self.anchor = None;
        self.place_cursor(offset);
    }

    fn place_cursor(&mut self, offset: usize) {
        self.last_edit = None;
        let target = offset.min(self.length());
        let mut position = 0;
        for grapheme in split_graphemes(&self.text) {
            let next = position + grapheme.chars().count();
            if next > target {
                break;
            }
            position = next;
        }
        self.cursor = if target == self.length() {
            target
        } else {
            position
        };
    }

    fn previous_boundary(&self, offset: usize) -> usize {
        let mut position = 0;
        for grapheme in split_graphemes(&self.text) {
            let next = position + grapheme.chars().count();
            if next >= offset {
                break;
            }
            position = next;
        }
        if offset == 0 { 0 } else { position }
    }

    fn next_boundary(&self, offset: usize) -> usize {
        let mut position = 0;
        for grapheme in split_graphemes(&self.text) {
            position += grapheme.chars().count();
            if position > offset {
                return position;
            }
        }
        self.length()
    }

    fn word_start(&self, offset: usize) -> usize {
        let characters: Vec<char> = self.text.chars().collect();
        let mut position = offset.min(characters.len());
        while position > 0 && characters[position - 1].is_whitespace() {
            position -= 1;
        }
        while position > 0 && !characters[position - 1].is_whitespace() {
            position -= 1;
        }
        position
    }

    fn word_end(&self, offset: usize) -> usize {
        let characters: Vec<char> = self.text.chars().collect();
        let mut position = offset.min(characters.len());
        while position < characters.len() && characters[position].is_whitespace() {
            position += 1;
        }
        while position < characters.len() && !characters[position].is_whitespace() {
            position += 1;
        }
        position
    }

    fn line_bounds(&self, offset: usize) -> (usize, usize) {
        let characters: Vec<char> = self.text.chars().collect();
        let mut start = offset.min(characters.len());
        while start > 0 && characters[start - 1] != '\n' {
            start -= 1;
        }
        let mut end = offset.min(characters.len());
        while end < characters.len() && characters[end] != '\n' {
            end += 1;
        }
        (start, end)
    }

    fn delete_range(&mut self, start: usize, end: usize) {
        if start >= end {
            return;
        }
        self.checkpoint(EditKind::Delete);
        let from = char_to_byte(&self.text, start);
        let to = char_to_byte(&self.text, end);
        self.text.replace_range(from..to, "");
        self.anchor = None;
        self.cursor = start;
    }

    fn move_vertically(&mut self, direction: i32) {
        let (start, end) = self.line_bounds(self.cursor);
        let column = display_width(
            &self
                .text
                .chars()
                .skip(start)
                .take(self.cursor - start)
                .collect::<String>(),
        );
        let target = if direction < 0 {
            if start == 0 {
                self.cursor = 0;
                return;
            }
            self.line_bounds(start - 1)
        } else {
            if end >= self.length() {
                self.cursor = self.length();
                return;
            }
            self.line_bounds(end + 1)
        };
        let row: String = self
            .text
            .chars()
            .skip(target.0)
            .take(target.1 - target.0)
            .collect();
        let mut accumulated = 0;
        let mut characters = 0;
        for grapheme in split_graphemes(&row) {
            let width = grapheme_width(grapheme);
            if accumulated + width > column {
                break;
            }
            accumulated += width;
            characters += grapheme.chars().count();
        }
        self.cursor = target.0 + characters;
    }

    /// Edit with a key event. Returns whether the editor used the key.
    pub fn handle_key(&mut self, key: &KeyEvent) -> bool {
        if key.kind == KeyKind::Release {
            return false;
        }
        let control = key.modifiers.contains(KeyModifiers::CONTROL);
        let alt = key.modifiers.contains(KeyModifiers::ALT);
        let shift = key.modifiers.contains(KeyModifiers::SHIFT);
        let is_movement = matches!(
            key.key.as_str(),
            "left" | "right" | "up" | "down" | "home" | "end"
        );
        if is_movement {
            if shift {
                self.anchor.get_or_insert(self.cursor);
            } else {
                self.anchor = None;
            }
        } else if self.selection().is_some() {
            let is_typing = !control
                && !alt
                && key
                    .text
                    .as_ref()
                    .is_some_and(|text| !text.chars().any(char::is_control));
            match key.key.as_str() {
                "backspace" | "delete" if !control && !alt => {
                    self.delete_selection();
                    return true;
                }
                "enter" if !self.is_single_line => {
                    self.delete_selection();
                }
                _ if is_typing => {
                    self.delete_selection();
                }
                _ => {}
            }
        }
        let (line_start, line_end) = self.line_bounds(self.cursor);
        match (key.key.as_str(), control, alt) {
            ("left", false, false) => self.place_cursor(self.previous_boundary(self.cursor)),
            ("right", false, false) => self.place_cursor(self.next_boundary(self.cursor)),
            ("left", _, _) => self.place_cursor(self.word_start(self.cursor)),
            ("right", _, _) => self.place_cursor(self.word_end(self.cursor)),
            ("up", _, _) if !self.is_single_line => {
                self.last_edit = None;
                self.move_vertically(-1);
            }
            ("down", _, _) if !self.is_single_line => {
                self.last_edit = None;
                self.move_vertically(1);
            }
            ("home", false, _) | ("a", true, false) => self.place_cursor(line_start),
            ("end", false, _) | ("e", true, false) => self.place_cursor(line_end),
            ("home", true, _) => self.place_cursor(0),
            ("end", true, _) => self.place_cursor(self.length()),
            ("backspace", false, false) => {
                let start = self.previous_boundary(self.cursor);
                self.delete_range(start, self.cursor);
            }
            ("backspace", _, _) | ("w", true, false) => {
                let start = self.word_start(self.cursor);
                self.delete_range(start, self.cursor);
            }
            ("delete", false, false) | ("d", true, false) => {
                let end = self.next_boundary(self.cursor);
                self.delete_range(self.cursor, end);
            }
            ("delete", _, _) => {
                let end = self.word_end(self.cursor);
                self.delete_range(self.cursor, end);
            }
            ("u", true, false) => self.delete_range(line_start, self.cursor),
            ("k", true, false) => self.delete_range(self.cursor, line_end),
            ("z", true, false) if !shift => return self.undo(),
            ("y" | "z", true, false) => return self.redo(),
            ("enter", _, _) if !self.is_single_line => self.insert_text("\n"),
            _ => {
                if control || alt {
                    return false;
                }
                match &key.text {
                    Some(text) if !text.chars().any(char::is_control) => self.insert_text(text),
                    _ => return false,
                }
            }
        }
        true
    }

    /// The selected range as `(start, end)` character offsets, if any text is selected.
    pub fn selection(&self) -> Option<(usize, usize)> {
        let anchor = self.anchor?;
        (anchor != self.cursor).then(|| (anchor.min(self.cursor), anchor.max(self.cursor)))
    }

    /// The selected text, or an empty string.
    pub fn selected_text(&self) -> String {
        self.selection()
            .map(|(start, end)| self.text.chars().skip(start).take(end - start).collect())
            .unwrap_or_default()
    }

    /// Select from `start` to `end` and put the cursor at `end`.
    pub fn select(&mut self, start: usize, end: usize) {
        self.last_edit = None;
        self.anchor = Some(start.min(self.length()));
        self.cursor = end.min(self.length());
    }

    pub fn select_all(&mut self) {
        self.select(0, self.length());
    }

    pub fn clear_selection(&mut self) {
        self.anchor = None;
    }

    /// Delete the selected text. Returns whether anything was selected.
    pub fn delete_selection(&mut self) -> bool {
        let Some((start, end)) = self.selection() else {
            return false;
        };
        self.delete_range(start, end);
        true
    }

    /// Replace the selection (or insert at the cursor) with `text`.
    pub fn replace_selection(&mut self, text: &str) {
        self.delete_selection();
        self.insert_text(text);
    }

    pub fn move_word_left(&mut self) {
        self.anchor = None;
        self.place_cursor(self.word_start(self.cursor));
    }

    pub fn move_word_right(&mut self) {
        self.anchor = None;
        self.place_cursor(self.word_end(self.cursor));
    }

    pub fn move_to_line_start(&mut self) {
        let (start, _) = self.line_bounds(self.cursor);
        self.move_cursor(start);
    }

    pub fn move_to_line_end(&mut self) {
        let (_, end) = self.line_bounds(self.cursor);
        self.move_cursor(end);
    }

    pub fn move_to_start(&mut self) {
        self.move_cursor(0);
    }

    pub fn move_to_end(&mut self) {
        self.move_cursor(self.length());
    }

    /// Undo the last edit. Returns whether there was one.
    pub fn undo(&mut self) -> bool {
        let Some((text, cursor)) = self.undo.pop() else {
            return false;
        };
        self.redo
            .push((std::mem::replace(&mut self.text, text), self.cursor));
        self.cursor = cursor;
        self.anchor = None;
        self.last_edit = None;
        true
    }

    /// Redo the last undone edit. Returns whether there was one.
    pub fn redo(&mut self) -> bool {
        let Some((text, cursor)) = self.redo.pop() else {
            return false;
        };
        self.undo
            .push((std::mem::replace(&mut self.text, text), self.cursor));
        self.cursor = cursor;
        self.anchor = None;
        self.last_edit = None;
        true
    }

    pub fn layout(&self, width: usize, should_wrap: bool) -> TextLayout {
        layout_text(&self.text, width, Some(self.cursor), should_wrap)
    }
}

#[cfg(test)]
mod grapheme_tests {
    use super::*;

    #[test]
    fn split_graphemes_matches_unicode_segmentation() {
        let samples = [
            "",
            "plain ascii text with spaces",
            "line one\r\nline two\r\n",
            "\r\r\n\n\r",
            "e\u{301}a\u{301}bc",
            "a\u{200d}b",
            "\u{600}abc",
            "\u{1f469}\u{200d}\u{1f4bb}x\u{1f1fa}\u{1f1f8}y",
            "界面abc界",
            "ünïcödé wörds",
            "ab\u{308}cd",
            "한국어 and ASCII",
            "tab\there\u{7f}del",
            "9\u{fe0f}\u{20e3}#\u{fe0f}\u{20e3}",
        ];
        for sample in samples {
            let expected: Vec<&str> = sample.graphemes(true).collect();
            let actual: Vec<&str> = split_graphemes(sample).collect();
            assert_eq!(actual, expected, "segmenting {sample:?}");
        }
    }

    fn rows(text: &str, width: usize) -> Vec<String> {
        wrap_lines(
            &split_lines(&[Span::new(text, Style::default())]),
            width,
            true,
        )
        .iter()
        .map(|row| row.iter().map(|span| span.text.as_str()).collect())
        .collect()
    }

    #[test]
    fn wrapping_counts_wide_glyphs_by_their_columns() {
        assert_eq!(rows("わさび", 3), ["わ", "さ", "び"]);
        assert_eq!(rows("わさび", 4), ["わさ", "び"]);
        assert_eq!(rows("😽😽😽😽", 7), ["😽😽😽", "😽"]);
        assert_eq!(
            rows("123ありがとうございました", 8),
            ["123あり", "がとうご", "ざいまし", "た"]
        );
    }

    #[test]
    fn wrapping_breaks_words_and_folds_long_ones() {
        assert_eq!(rows("foo bar baz", 3), ["foo", "bar", "baz"]);
        assert_eq!(rows("1234 12345678", 7), ["1234", "1234567", "8"]);
        assert_eq!(rows("abracadabra", 4), ["abra", "cada", "bra"]);
        assert_eq!(rows("Some more words", 4), ["Some", "more", "word", "s"]);
        assert_eq!(rows("a\n\nb", 3), ["a", "", "b"]);
    }

    #[test]
    fn wrapping_without_trimming_keeps_the_spaces_at_a_break() {
        let lines = split_lines(&[Span::new("ab cd", Style::default())]);
        let text = |rows: Vec<Line>| -> Vec<String> {
            rows.iter()
                .map(|row| row.iter().map(|span| span.text.as_str()).collect())
                .collect()
        };
        assert_eq!(text(wrap_lines(&lines, 3, true)), ["ab", "cd"]);
        assert_eq!(text(wrap_lines(&lines, 3, false)), ["ab ", "cd"]);
    }

    #[test]
    fn wrapping_keeps_styles_with_their_text() {
        let red = Style::default().fg(ratatui_core::style::Color::Red);
        let lines = vec![vec![
            Span::new("ab ", Style::default()),
            Span::new("cd", red),
        ]];
        let wrapped = wrap_lines(&lines, 3, true);
        assert_eq!(wrapped.len(), 2);
        assert_eq!(wrapped[1][0].style, red);
    }

    #[test]
    fn grapheme_width_shortcut_matches_the_general_rule() {
        for byte in 0..0x80_u8 {
            let text = char::from(byte).to_string();
            let general = if text.chars().any(char::is_control) {
                0
            } else {
                UnicodeWidthStr::width(text.as_str())
            };
            assert_eq!(grapheme_width(&text), general, "byte {byte}");
        }
    }
}
