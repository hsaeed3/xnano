//! Styled text, layout and the text editor.

use std::sync::{Arc, Mutex};

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyTuple;
use xnano_terminal_runtime::style::Style;
use xnano_terminal_runtime::text::{self, Span, TextEditor, TextLayout};

use crate::events::PyKeyEvent;
use crate::style::{PyStyle, style_arg};

#[pyclass(
    name = "TextSpan",
    module = "xnano_core._xnano_core",
    frozen,
    eq,
    hash,
    from_py_object
)]
#[derive(Clone, PartialEq, Eq, Hash)]
pub struct PyTextSpan {
    pub inner: Span,
}

#[pymethods]
impl PyTextSpan {
    #[new]
    #[pyo3(signature = (text, *, style = None))]
    fn new(text: String, style: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        Ok(Self {
            inner: Span::new(text, style_arg(style)?),
        })
    }

    #[getter]
    fn text(&self) -> &str {
        &self.inner.text
    }

    #[getter]
    fn style(&self) -> PyStyle {
        PyStyle {
            inner: self.inner.style,
        }
    }

    fn __copy__(&self) -> Self {
        self.clone()
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.clone()
    }

    fn __repr__(&self) -> String {
        if self.inner.style == Style::default() {
            format!("TextSpan({:?})", self.inner.text)
        } else {
            format!(
                "TextSpan({:?}, style={})",
                self.inner.text,
                crate::style::style_repr(&self.inner.style)
            )
        }
    }
}

#[pyclass(
    name = "StyledText",
    module = "xnano_core._xnano_core",
    frozen,
    eq,
    hash
)]
#[derive(PartialEq, Eq, Hash)]
pub struct PyStyledText {
    pub spans: Vec<Span>,
}

#[pymethods]
impl PyStyledText {
    #[new]
    fn new(spans: Vec<PyTextSpan>) -> Self {
        Self {
            spans: spans.into_iter().map(|span| span.inner).collect(),
        }
    }

    #[getter]
    fn spans<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        PyTuple::new(
            py,
            self.spans.iter().cloned().map(|inner| PyTextSpan { inner }),
        )
    }

    /// Add more text: another ``StyledText``, a ``TextSpan`` or a plain string.
    fn __add__(&self, other: &Bound<'_, PyAny>) -> PyResult<Self> {
        let mut spans = self.spans.clone();
        if let Ok(styled) = other.extract::<PyRef<'_, PyStyledText>>() {
            spans.extend(styled.spans.iter().cloned());
        } else if let Ok(span) = other.extract::<PyTextSpan>() {
            spans.push(span.inner);
        } else if let Ok(text) = other.extract::<String>() {
            spans.push(Span::new(text, Style::default()));
        } else {
            return Err(pyo3::exceptions::PyTypeError::new_err(format!(
                "cannot add {} to a StyledText; add a StyledText, a TextSpan or a str",
                other.get_type().name()?
            )));
        }
        Ok(Self { spans })
    }

    fn __bool__(&self) -> bool {
        self.spans.iter().any(|span| !span.text.is_empty())
    }

    /// The text without styles.
    #[getter]
    fn text(&self) -> String {
        self.__str__()
    }

    /// The number of rows (lines separated by newlines).
    #[getter]
    fn height(&self) -> usize {
        self.__str__().split('\n').count()
    }

    /// The display width in columns of the widest row.
    #[getter]
    fn width(&self) -> usize {
        self.__str__()
            .split('\n')
            .map(text::display_width)
            .max()
            .unwrap_or(0)
    }

    /// A copy with ``style`` applied on top of every span's own style.
    fn patch_style(&self, style: &PyStyle) -> Self {
        Self {
            spans: self
                .spans
                .iter()
                .map(|span| Span::new(span.text.clone(), span.style.patch(style.inner)))
                .collect(),
        }
    }

    fn __copy__(&self) -> Self {
        Self {
            spans: self.spans.clone(),
        }
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.__copy__()
    }

    fn __str__(&self) -> String {
        self.spans.iter().map(|span| span.text.as_str()).collect()
    }

    fn __repr__(&self) -> String {
        let spans: Vec<String> = self
            .spans
            .iter()
            .map(|span| {
                PyTextSpan {
                    inner: span.clone(),
                }
                .__repr__()
            })
            .collect();
        format!("StyledText([{}])", spans.join(", "))
    }
}

#[pyclass(
    name = "TextLine",
    skip_from_py_object,
    module = "xnano_core._xnano_core",
    frozen,
    eq,
    hash
)]
#[derive(Clone, PartialEq, Eq, Hash)]
pub struct PyTextLine {
    inner: text::TextLine,
}

#[pymethods]
impl PyTextLine {
    #[getter]
    fn text(&self) -> &str {
        &self.inner.text
    }

    #[getter]
    fn start_offset(&self) -> usize {
        self.inner.start_offset
    }

    #[getter]
    fn end_offset(&self) -> usize {
        self.inner.end_offset
    }

    #[getter]
    fn width(&self) -> usize {
        self.inner.width
    }

    fn __repr__(&self) -> String {
        format!(
            "TextLine({:?}, start_offset={}, end_offset={}, width={})",
            self.inner.text, self.inner.start_offset, self.inner.end_offset, self.inner.width
        )
    }
}

#[pyclass(
    name = "TextLayout",
    module = "xnano_core._xnano_core",
    frozen,
    eq,
    hash
)]
#[derive(PartialEq, Eq, Hash)]
pub struct PyTextLayout {
    inner: TextLayout,
}

#[pymethods]
impl PyTextLayout {
    #[getter]
    fn lines<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        PyTuple::new(
            py,
            self.inner
                .lines
                .iter()
                .cloned()
                .map(|inner| PyTextLine { inner }),
        )
    }

    #[getter]
    fn cursor_cell(&self) -> Option<(usize, usize)> {
        self.inner.cursor_cell
    }

    fn text_offset_at(&self, column: usize, row: usize) -> usize {
        self.inner.text_offset_at(column, row)
    }

    fn cell_at_text_offset(&self, offset: usize) -> (usize, usize) {
        self.inner.cell_at_text_offset(offset)
    }

    fn __repr__(&self) -> String {
        format!("TextLayout({} lines)", self.inner.lines.len())
    }
}

fn check_width(width: i64) -> PyResult<usize> {
    usize::try_from(width)
        .ok()
        .filter(|width| *width > 0)
        .ok_or_else(|| {
            PyValueError::new_err(format!(
                "the layout width must be at least 1 column, not {width}"
            ))
        })
}

#[pyfunction]
#[pyo3(signature = (text, *, width, cursor_offset = None, should_wrap = true))]
fn layout_text(
    text: &str,
    width: i64,
    cursor_offset: Option<usize>,
    should_wrap: bool,
) -> PyResult<PyTextLayout> {
    Ok(PyTextLayout {
        inner: text::layout_text(text, check_width(width)?, cursor_offset, should_wrap),
    })
}

#[pyfunction]
fn display_width(text: &str) -> usize {
    text::display_width(text)
}

#[pyclass(name = "TextEditor", module = "xnano_core._xnano_core", frozen)]
pub struct PyTextEditor {
    pub inner: Arc<Mutex<TextEditor>>,
}

impl PyTextEditor {
    fn lock(&self) -> std::sync::MutexGuard<'_, TextEditor> {
        self.inner
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
    }
}

#[pymethods]
impl PyTextEditor {
    #[new]
    #[pyo3(signature = (text = "", *, is_single_line = false))]
    fn new(text: &str, is_single_line: bool) -> Self {
        Self {
            inner: Arc::new(Mutex::new(TextEditor::new(text, is_single_line))),
        }
    }

    #[getter]
    fn text(&self) -> String {
        self.lock().text().to_owned()
    }

    #[getter]
    fn is_single_line(&self) -> bool {
        self.lock().is_single_line
    }

    #[getter]
    fn cursor_offset(&self) -> usize {
        self.lock().cursor_offset()
    }

    #[getter]
    fn placeholder_text(&self) -> String {
        self.lock().placeholder_text.clone()
    }

    #[setter]
    fn set_placeholder_text(&self, value: String) {
        self.lock().placeholder_text = value;
    }

    fn set_text(&self, text: &str) {
        self.lock().set_text(text);
    }

    fn insert_text(&self, text: &str) {
        self.lock().insert_text(text);
    }

    fn handle_key(&self, key: &PyKeyEvent) -> bool {
        self.lock().handle_key(&key.inner)
    }

    fn move_cursor(&self, offset: usize) {
        self.lock().move_cursor(offset);
    }

    fn undo(&self) -> bool {
        self.lock().undo()
    }

    fn redo(&self) -> bool {
        self.lock().redo()
    }

    #[pyo3(signature = (*, width, should_wrap = true))]
    fn layout(&self, width: i64, should_wrap: bool) -> PyResult<PyTextLayout> {
        Ok(PyTextLayout {
            inner: self.lock().layout(check_width(width)?, should_wrap),
        })
    }

    /// The selected range as ``(start, end)`` character offsets, or ``None``.
    #[getter]
    fn selection(&self) -> Option<(usize, usize)> {
        self.lock().selection()
    }

    #[getter]
    fn selected_text(&self) -> String {
        self.lock().selected_text()
    }

    #[pyo3(signature = (start, end))]
    fn select(&self, start: usize, end: usize) {
        self.lock().select(start, end);
    }

    fn select_all(&self) {
        self.lock().select_all();
    }

    fn clear_selection(&self) {
        self.lock().clear_selection();
    }

    /// Delete the selected text. Returns whether anything was selected.
    fn delete_selection(&self) -> bool {
        self.lock().delete_selection()
    }

    /// Replace the selection, or insert at the cursor when nothing is selected.
    fn replace_selection(&self, text: &str) {
        self.lock().replace_selection(text);
    }

    fn move_word_left(&self) {
        self.lock().move_word_left();
    }

    fn move_word_right(&self) {
        self.lock().move_word_right();
    }

    fn move_to_line_start(&self) {
        self.lock().move_to_line_start();
    }

    fn move_to_line_end(&self) {
        self.lock().move_to_line_end();
    }

    fn move_to_start(&self) {
        self.lock().move_to_start();
    }

    fn move_to_end(&self) {
        self.lock().move_to_end();
    }

    #[getter]
    fn cursor_style(&self) -> PyStyle {
        PyStyle {
            inner: self.lock().cursor_style,
        }
    }

    #[setter]
    fn set_cursor_style(&self, style: &PyStyle) {
        self.lock().cursor_style = style.inner;
    }

    #[getter]
    fn selection_style(&self) -> PyStyle {
        PyStyle {
            inner: self.lock().selection_style,
        }
    }

    #[setter]
    fn set_selection_style(&self, style: &PyStyle) {
        self.lock().selection_style = style.inner;
    }

    /// An independent editor with the same text, cursor and selection.
    fn __copy__(&self) -> Self {
        Self {
            inner: Arc::new(Mutex::new(self.lock().clone())),
        }
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.__copy__()
    }

    fn __eq__(&self, other: &Bound<'_, PyAny>) -> bool {
        let Ok(other) = other.extract::<PyRef<'_, PyTextEditor>>() else {
            return false;
        };
        if Arc::ptr_eq(&self.inner, &other.inner) {
            return true;
        }
        let (mine, theirs) = (self.lock(), other.lock());
        mine.text() == theirs.text()
            && mine.cursor_offset() == theirs.cursor_offset()
            && mine.selection() == theirs.selection()
            && mine.is_single_line == theirs.is_single_line
            && mine.placeholder_text == theirs.placeholder_text
    }

    fn __repr__(&self) -> String {
        let editor = self.lock();
        format!(
            "TextEditor({:?}, is_single_line={})",
            editor.text(),
            if editor.is_single_line {
                "True"
            } else {
                "False"
            }
        )
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyTextSpan>()?;
    m.add_class::<PyStyledText>()?;
    m.add_class::<PyTextLine>()?;
    m.add_class::<PyTextLayout>()?;
    m.add_class::<PyTextEditor>()?;
    m.add_function(wrap_pyfunction!(layout_text, m)?)?;
    m.add_function(wrap_pyfunction!(display_width, m)?)?;
    let _ = Style::default();
    Ok(())
}
