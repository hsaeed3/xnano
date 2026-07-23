//! Native multi-line text editor (`CoreTextEditor`).
//!
//! Wraps `tui_textarea::TextArea` behind the `editor` cargo feature.
//! Key events convert from `PyKeyEvent` inside the crate (no crossterm
//! coupling), so the editor compiles without the `terminal` feature.

#[cfg(feature = "terminal")]
use crossterm::event::{KeyCode, KeyModifiers};
use pyo3::prelude::*;
use tui_textarea::{CursorMove, Input, Key, TextArea};

#[cfg(not(feature = "terminal"))]
use super::super::crossterm_types::{KeyCode, KeyModifiers};
use super::super::terminal::{PyKeyEvent, PyKeyEventKind};

/// Map a key code onto tui-textarea's backend-neutral `Key`.
fn key_from_code(code: &KeyCode) -> Key {
    match *code {
        KeyCode::Char(c) => Key::Char(c),
        KeyCode::Backspace => Key::Backspace,
        KeyCode::Enter => Key::Enter,
        KeyCode::Left => Key::Left,
        KeyCode::Right => Key::Right,
        KeyCode::Up => Key::Up,
        KeyCode::Down => Key::Down,
        KeyCode::Home => Key::Home,
        KeyCode::End => Key::End,
        KeyCode::PageUp => Key::PageUp,
        KeyCode::PageDown => Key::PageDown,
        KeyCode::Tab => Key::Tab,
        KeyCode::Delete => Key::Delete,
        KeyCode::Esc => Key::Esc,
        KeyCode::F(n) => Key::F(n),
        _ => Key::Null,
    }
}

/// Stateful text editor engine backing multi-line `Text` input fields.
#[pyclass(name = "CoreTextEditor", module = "xnano_core.rust.engine", unsendable)]
pub struct PyTextEditor {
    pub(crate) inner: TextArea<'static>,
    single_line: bool,
}

#[pymethods]
impl PyTextEditor {
    #[new]
    #[pyo3(signature = (text = "", *, single_line = false))]
    fn new(text: &str, single_line: bool) -> Self {
        let mut inner = TextArea::from(text.lines());
        inner.move_cursor(CursorMove::Bottom);
        inner.move_cursor(CursorMove::End);
        Self { inner, single_line }
    }

    /// Apply a key event. Returns whether the editor consumed it.
    ///
    /// Tab, BackTab, and Esc always fall through (focus navigation and
    /// hooks own them); Enter falls through in single-line mode.
    fn input(&mut self, key: &PyKeyEvent) -> bool {
        if matches!(key.kind, PyKeyEventKind::Release) {
            return false;
        }
        let code = key_from_code(key.raw_code());
        match code {
            Key::Tab | Key::Esc | Key::Null => return false,
            Key::Enter if self.single_line => return false,
            _ => {}
        }
        let modifiers = key.raw_modifiers();
        self.inner.input(Input {
            key: code,
            ctrl: modifiers.contains(KeyModifiers::CONTROL),
            alt: modifiers.contains(KeyModifiers::ALT),
            shift: modifiers.contains(KeyModifiers::SHIFT),
        })
    }

    /// Insert text at the cursor (paste path). Newlines collapse to
    /// spaces in single-line mode.
    fn insert_text(&mut self, text: &str) {
        if self.single_line {
            self.inner.insert_str(text.replace(['\n', '\r'], " "));
        } else {
            self.inner.insert_str(text);
        }
    }

    /// Full content as a single newline-joined string.
    fn text(&self) -> String {
        self.inner.lines().join("\n")
    }

    /// Replace the full content, keeping the cursor at the end.
    fn set_text(&mut self, text: &str) {
        self.inner.select_all();
        self.inner.cut();
        self.insert_text(text);
    }

    /// Content as one string per line.
    fn lines(&self) -> Vec<String> {
        self.inner.lines().to_vec()
    }

    /// Cursor position as ``(row, column)``.
    fn cursor(&self) -> (usize, usize) {
        self.inner.cursor()
    }

    fn undo(&mut self) -> bool {
        self.inner.undo()
    }

    fn redo(&mut self) -> bool {
        self.inner.redo()
    }

    fn set_placeholder_text(&mut self, text: &str) {
        self.inner.set_placeholder_text(text);
    }

    fn __repr__(&self) -> String {
        let (row, column) = self.inner.cursor();
        format!(
            "CoreTextEditor(lines={}, cursor=({row}, {column}))",
            self.inner.lines().len()
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn key_mapping_covers_editing_keys() {
        assert_eq!(key_from_code(&KeyCode::Char('a')), Key::Char('a'));
        assert_eq!(key_from_code(&KeyCode::Backspace), Key::Backspace);
        assert_eq!(key_from_code(&KeyCode::Enter), Key::Enter);
        assert_eq!(key_from_code(&KeyCode::Left), Key::Left);
        assert_eq!(key_from_code(&KeyCode::Right), Key::Right);
        assert_eq!(key_from_code(&KeyCode::Up), Key::Up);
        assert_eq!(key_from_code(&KeyCode::Down), Key::Down);
        assert_eq!(key_from_code(&KeyCode::Home), Key::Home);
        assert_eq!(key_from_code(&KeyCode::End), Key::End);
        assert_eq!(key_from_code(&KeyCode::PageUp), Key::PageUp);
        assert_eq!(key_from_code(&KeyCode::PageDown), Key::PageDown);
        assert_eq!(key_from_code(&KeyCode::Delete), Key::Delete);
        assert_eq!(key_from_code(&KeyCode::F(5)), Key::F(5));
        // Focus-navigation and unknown keys collapse to Null (unconsumed).
        assert_eq!(key_from_code(&KeyCode::BackTab), Key::Null);
        assert_eq!(key_from_code(&KeyCode::Menu), Key::Null);
    }

    #[test]
    fn single_line_strips_newlines_on_insert() {
        let mut editor = PyTextEditor::new("", true);
        editor.insert_text("one\ntwo\r\nthree");
        assert_eq!(editor.text(), "one two  three");
    }
}
