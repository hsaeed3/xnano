use std::time::Duration;

use crossterm::event::{
    self, Event, KeyCode, KeyEvent, KeyEventKind, KeyModifiers, MouseButton, MouseEvent,
    MouseEventKind,
};
use pyo3::prelude::*;
use ratatui::Frame;
use ratatui::{init, restore, DefaultTerminal};

use super::buffer::{render_stateful_inner, render_widget_inner};
use super::convert_core::{sync_from_core_buffer, sync_to_core_buffer, to_core_rect};
use super::fx::PyEffectManager;
use super::layout::{PyRect, PySize};
use super::widgets_extra::PyPosition;

/// Frame context valid only for the duration of a `Terminal.draw` callback.
#[pyclass(name = "Frame", module = "xnano_core._xnano_core", unsendable)]
pub struct PyFrame {
    ptr: usize,
}

impl PyFrame {
    fn frame(&self) -> &Frame<'_> {
        unsafe { &*(self.ptr as *const Frame<'_>) }
    }

    fn frame_mut(&mut self) -> &mut Frame<'_> {
        unsafe { &mut *(self.ptr as *mut Frame<'_>) }
    }

    fn from_frame(frame: &mut Frame<'_>) -> Self {
        Self {
            ptr: (frame as *mut Frame<'_>) as usize,
        }
    }
}

#[pymethods]
impl PyFrame {
    fn area(&self) -> PyRect {
        PyRect {
            inner: self.frame().area(),
        }
    }

    fn render_widget(&mut self, widget: &Bound<'_, PyAny>, area: PyRect) -> PyResult<()> {
        render_widget_inner(widget, area, self.frame_mut().buffer_mut())
    }

    fn render_stateful_widget(
        &mut self,
        widget: &Bound<'_, PyAny>,
        area: PyRect,
        state: &Bound<'_, PyAny>,
    ) -> PyResult<()> {
        render_stateful_inner(widget, area, state, self.frame_mut().buffer_mut())
    }

    fn set_cursor_position(&mut self, position: PyPosition) {
        self.frame_mut().set_cursor_position(position.inner);
    }

    fn hide_cursor(&mut self) {
        // Ratatui only shows the cursor when `set_cursor_position` is called.
    }

    fn process_effects(
        &mut self,
        manager: &mut PyEffectManager,
        duration_ms: u32,
        area: PyRect,
    ) {
        let buffer = self.frame_mut().buffer_mut();
        let mut core = sync_to_core_buffer(buffer);
        manager.inner_mut().process_effects(
            tachyonfx::Duration::from_millis(duration_ms),
            &mut core,
            to_core_rect(area.inner),
        );
        sync_from_core_buffer(&core, buffer);
    }

    fn count(&self) -> usize {
        self.frame().count()
    }
}

#[pyclass(name = "KeyEventKind", module = "xnano_core._xnano_core", eq, eq_int)]
#[derive(Clone, Copy, PartialEq, Debug)]
pub enum PyKeyEventKind {
    Press,
    Repeat,
    Release,
}

impl From<KeyEventKind> for PyKeyEventKind {
    fn from(kind: KeyEventKind) -> Self {
        match kind {
            KeyEventKind::Press => PyKeyEventKind::Press,
            KeyEventKind::Repeat => PyKeyEventKind::Repeat,
            KeyEventKind::Release => PyKeyEventKind::Release,
        }
    }
}

#[pyclass(name = "KeyModifiers", module = "xnano_core._xnano_core")]
#[derive(Clone, Copy)]
pub struct PyKeyModifiers {
    #[pyo3(get)]
    pub bits: u8,
}

#[pymethods]
impl PyKeyModifiers {
    fn contains(&self, other: Self) -> bool {
        KeyModifiers::from_bits_truncate(self.bits).contains(KeyModifiers::from_bits_truncate(other.bits))
    }

    fn control(&self) -> bool {
        KeyModifiers::from_bits_truncate(self.bits).contains(KeyModifiers::CONTROL)
    }

    fn shift(&self) -> bool {
        KeyModifiers::from_bits_truncate(self.bits).contains(KeyModifiers::SHIFT)
    }

    fn alt(&self) -> bool {
        KeyModifiers::from_bits_truncate(self.bits).contains(KeyModifiers::ALT)
    }
}

impl From<KeyModifiers> for PyKeyModifiers {
    fn from(value: KeyModifiers) -> Self {
        Self {
            bits: value.bits(),
        }
    }
}

#[pyclass(name = "KeyCode", module = "xnano_core._xnano_core", eq, eq_int)]
#[derive(Clone, Copy, PartialEq, Debug)]
pub enum PyKeyCode {
    Char,
    Enter,
    Esc,
    Backspace,
    Tab,
    BackTab,
    Up,
    Down,
    Left,
    Right,
    Home,
    End,
    PageUp,
    PageDown,
    Insert,
    Delete,
    F,
    Null,
    Other,
}

fn key_code_name(code: &KeyCode) -> PyKeyCode {
    match code {
        KeyCode::Char(_) => PyKeyCode::Char,
        KeyCode::Enter => PyKeyCode::Enter,
        KeyCode::Esc => PyKeyCode::Esc,
        KeyCode::Backspace => PyKeyCode::Backspace,
        KeyCode::Tab => PyKeyCode::Tab,
        KeyCode::BackTab => PyKeyCode::BackTab,
        KeyCode::Up => PyKeyCode::Up,
        KeyCode::Down => PyKeyCode::Down,
        KeyCode::Left => PyKeyCode::Left,
        KeyCode::Right => PyKeyCode::Right,
        KeyCode::Home => PyKeyCode::Home,
        KeyCode::End => PyKeyCode::End,
        KeyCode::PageUp => PyKeyCode::PageUp,
        KeyCode::PageDown => PyKeyCode::PageDown,
        KeyCode::Insert => PyKeyCode::Insert,
        KeyCode::Delete => PyKeyCode::Delete,
        KeyCode::F(_) => PyKeyCode::F,
        KeyCode::Null => PyKeyCode::Null,
        _ => PyKeyCode::Other,
    }
}

#[pyclass(name = "MouseEvent", module = "xnano_core._xnano_core")]
#[derive(Clone)]
pub struct PyMouseEvent {
    #[pyo3(get)]
    pub kind: String,
    #[pyo3(get)]
    pub x: u16,
    #[pyo3(get)]
    pub y: u16,
    #[pyo3(get)]
    pub button: String,
}

impl From<MouseEvent> for PyMouseEvent {
    fn from(event: MouseEvent) -> Self {
        let (kind, button) = match event.kind {
            MouseEventKind::Down(btn) => ("down", mouse_button_name(btn)),
            MouseEventKind::Up(btn) => ("up", mouse_button_name(btn)),
            MouseEventKind::Drag(btn) => ("drag", mouse_button_name(btn)),
            MouseEventKind::Moved => ("moved", "none"),
            MouseEventKind::ScrollDown => ("scroll_down", "none"),
            MouseEventKind::ScrollUp => ("scroll_up", "none"),
            MouseEventKind::ScrollLeft => ("scroll_left", "none"),
            MouseEventKind::ScrollRight => ("scroll_right", "none"),
        };
        Self {
            kind: kind.into(),
            x: event.column,
            y: event.row,
            button: button.into(),
        }
    }
}

fn mouse_button_name(button: MouseButton) -> &'static str {
    match button {
        MouseButton::Left => "left",
        MouseButton::Right => "right",
        MouseButton::Middle => "middle",
    }
}

#[pyclass(name = "KeyEvent", module = "xnano_core._xnano_core")]
#[derive(Clone)]
pub struct PyKeyEvent {
    code: KeyCode,
    #[pyo3(get)]
    pub kind: PyKeyEventKind,
    #[pyo3(get)]
    pub modifiers: PyKeyModifiers,
    #[pyo3(get)]
    pub code_name: PyKeyCode,
}

#[pymethods]
impl PyKeyEvent {
    fn is_char(&self, ch: char) -> bool {
        matches!(self.code, KeyCode::Char(c) if c == ch)
    }

    fn char(&self) -> Option<char> {
        match self.code {
            KeyCode::Char(c) => Some(c),
            _ => None,
        }
    }

    fn is_up(&self) -> bool {
        self.code == KeyCode::Up
    }

    fn is_down(&self) -> bool {
        self.code == KeyCode::Down
    }

    fn is_left(&self) -> bool {
        self.code == KeyCode::Left
    }

    fn is_right(&self) -> bool {
        self.code == KeyCode::Right
    }

    fn is_enter(&self) -> bool {
        self.code == KeyCode::Enter
    }

    fn is_esc(&self) -> bool {
        self.code == KeyCode::Esc
    }

    fn is_backspace(&self) -> bool {
        self.code == KeyCode::Backspace
    }

    fn is_tab(&self) -> bool {
        matches!(self.code, KeyCode::Tab | KeyCode::BackTab)
    }

    fn is_page_up(&self) -> bool {
        self.code == KeyCode::PageUp
    }

    fn is_page_down(&self) -> bool {
        self.code == KeyCode::PageDown
    }

    fn __repr__(&self) -> String {
        format!("KeyEvent({:?}, {:?})", self.code, self.kind)
    }
}

impl From<KeyEvent> for PyKeyEvent {
    fn from(event: KeyEvent) -> Self {
        Self {
            code: event.code,
            kind: event.kind.into(),
            modifiers: event.modifiers.into(),
            code_name: key_code_name(&event.code),
        }
    }
}

#[pyclass(name = "Event", module = "xnano_core._xnano_core")]
#[derive(Clone)]
pub struct PyEvent {
    #[pyo3(get)]
    pub kind: String,
    #[pyo3(get)]
    pub key: Option<PyKeyEvent>,
    #[pyo3(get)]
    pub width: Option<u16>,
    #[pyo3(get)]
    pub height: Option<u16>,
    #[pyo3(get)]
    pub paste: Option<String>,
    #[pyo3(get)]
    pub mouse: Option<PyMouseEvent>,
}

#[pyclass(name = "Terminal", module = "xnano_core._xnano_core", unsendable)]
pub struct PyTerminal {
    inner: DefaultTerminal,
}

#[pymethods]
impl PyTerminal {
    #[staticmethod]
    fn init() -> Self {
        Self { inner: init() }
    }

    fn draw(&mut self, callback: PyObject) -> PyResult<()> {
        self.inner
            .draw(|frame| {
                if let Err(err) = Python::with_gil(|py| {
                    let py_frame = PyFrame::from_frame(frame);
                    callback.call1(py, (py_frame,))
                }) {
                    Python::with_gil(|py| err.print(py));
                }
            })
            .map_err(|err| pyo3::exceptions::PyIOError::new_err(err.to_string()))?;
        Ok(())
    }

    fn clear(&mut self) -> PyResult<()> {
        self.inner
            .clear()
            .map_err(|err| pyo3::exceptions::PyIOError::new_err(err.to_string()))
    }

    fn size(&self) -> PyResult<PySize> {
        self.inner
            .size()
            .map(|size| PySize { inner: size })
            .map_err(|err| pyo3::exceptions::PyIOError::new_err(err.to_string()))
    }

    fn __enter__(slf: PyRefMut<'_, Self>) -> PyRefMut<'_, Self> {
        slf
    }

    fn __exit__(
        &mut self,
        _exc_type: &Bound<'_, PyAny>,
        _exc_value: &Bound<'_, PyAny>,
        _traceback: &Bound<'_, PyAny>,
    ) -> PyResult<()> {
        restore();
        Ok(())
    }
}

#[pyfunction]
fn restore_terminal() {
    restore();
}

#[pyfunction]
fn poll_event(timeout_ms: u64) -> PyResult<Option<PyEvent>> {
    if !event::poll(Duration::from_millis(timeout_ms))
        .map_err(|err| pyo3::exceptions::PyIOError::new_err(err.to_string()))?
    {
        return Ok(None);
    }
    read_event().map(Some)
}

#[pyfunction]
fn read_event() -> PyResult<PyEvent> {
    let event =
        event::read().map_err(|err| pyo3::exceptions::PyIOError::new_err(err.to_string()))?;
    Ok(match event {
        Event::Key(key) => PyEvent {
            kind: "key".into(),
            key: Some(key.into()),
            width: None,
            height: None,
            paste: None,
            mouse: None,
        },
        Event::Resize(width, height) => PyEvent {
            kind: "resize".into(),
            key: None,
            width: Some(width),
            height: Some(height),
            paste: None,
            mouse: None,
        },
        Event::Paste(text) => PyEvent {
            kind: "paste".into(),
            key: None,
            width: None,
            height: None,
            paste: Some(text),
            mouse: None,
        },
        Event::Mouse(mouse) => PyEvent {
            kind: "mouse".into(),
            key: None,
            width: None,
            height: None,
            paste: None,
            mouse: Some(mouse.into()),
        },
        _ => PyEvent {
            kind: "other".into(),
            key: None,
            width: None,
            height: None,
            paste: None,
            mouse: None,
        },
    })
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyFrame>()?;
    m.add_class::<PyTerminal>()?;
    m.add_class::<PyKeyEventKind>()?;
    m.add_class::<PyKeyModifiers>()?;
    m.add_class::<PyKeyCode>()?;
    m.add_class::<PyMouseEvent>()?;
    m.add_class::<PyKeyEvent>()?;
    m.add_class::<PyEvent>()?;
    m.add_function(wrap_pyfunction!(restore_terminal, m)?)?;
    m.add_function(wrap_pyfunction!(poll_event, m)?)?;
    m.add_function(wrap_pyfunction!(read_event, m)?)?;
    Ok(())
}