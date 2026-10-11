//! Styled text, Unicode layout and the text editor, independent of any widget.
//!
//! Offsets are counted in characters (Unicode code points), the same unit Python uses to
//! index a `str`, and always fall on grapheme boundaries. Columns are display columns.

use unicode_segmentation::UnicodeSegmentation;
use unicode_width::UnicodeWidthStr;

use crate::event::{KeyEvent, KeyKind, KeyModifiers};
use crate::style::Style;

/// Display columns of `text`.
pub fn display_width(text: &str) -> usize {
    text.graphemes(true).map(grapheme_width).sum()
}

/// Display columns of one grapheme. Control characters take none.
pub fn grapheme_width(grapheme: &str) -> usize {
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
        let graphemes: Vec<(&str, usize, usize)> = paragraph
            .graphemes(true)
            .map(|grapheme| (grapheme, grapheme_width(grapheme), grapheme.chars().count()))
            .collect();
        let mut start = 0;
        let mut row_width = 0;
        let mut last_break: Option<usize> = None;
        let mut index = 0;
        let paragraph_start = offset;
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
            let prefix: usize = graphemes[..from].iter().map(|entry| entry.2).sum();
            let characters: usize = slice.iter().map(|entry| entry.2).sum();
            lines.push(TextLine {
                text: slice.iter().map(|entry| entry.0).collect(),
                start_offset: paragraph_start + prefix,
                end_offset: paragraph_start + prefix + characters,
                width: column,
            });
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
        for grapheme in self.text.graphemes(true) {
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
        for grapheme in self.text.graphemes(true) {
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
        for grapheme in self.text.graphemes(true) {
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
        for grapheme in row.graphemes(true) {
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
