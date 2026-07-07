use std::time::Duration;

use crossterm::event::{
    self, KeyCode, KeyEvent, KeyEventKind, KeyEventState, KeyModifiers, MouseButton, MouseEvent,
    MouseEventKind,
};
use pyo3::prelude::*;
use ratatui::Frame;
use ratatui::{init, restore, DefaultTerminal};

use super::buffer::{render_stateful_inner, render_widget_inner, PyBuffer};
use super::crossterm_exec::io_to_py;
use super::engine::events::PyEvent;
use super::convert_core::{sync_from_core_buffer, sync_to_core_buffer, to_core_rect};
use super::frame_ext::frame_hide_cursor;
use super::fx::PyEffectManager;
use super::layout::{PyRect, PySize};
use super::widgets_extra::PyPosition;

/// Frame context valid only for the duration of a `Terminal.draw` callback.
#[pyclass(name = "Frame", module = "xnano_core.rust.native", unsendable)]
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

    pub(crate) fn from_frame(frame: &mut Frame<'_>) -> Self {
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
        frame_hide_cursor(self.frame_mut());
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

    fn buffer(&mut self) -> PyBuffer {
        PyBuffer {
            inner: self.frame_mut().buffer_mut().clone(),
        }
    }

    fn get_buffer(&mut self) -> PyBuffer {
        self.buffer()
    }

    fn size(&self) -> PySize {
        let area = self.frame().area();
        PySize {
            inner: ratatui::layout::Size {
                width: area.width,
                height: area.height,
            },
        }
    }

    fn viewport(&self) -> PyRect {
        PyRect {
            inner: self.frame().area(),
        }
    }
}

/// Snapshot of terminal state after a successful draw.
#[pyclass(name = "CompletedFrame", module = "xnano_core.rust.native")]
pub struct PyCompletedFrame {
    #[pyo3(get)]
    pub buffer: PyBuffer,
    #[pyo3(get)]
    pub area: PyRect,
    #[pyo3(get)]
    pub count: usize,
}

#[pyclass(name = "KeyEventKind", module = "xnano_core.rust.native", eq, eq_int, from_py_object)]
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

#[pyclass(name = "KeyEventState", module = "xnano_core.rust.native", from_py_object)]
#[derive(Clone, Copy)]
pub struct PyKeyEventState {
    #[pyo3(get)]
    pub bits: u8,
}

#[pymethods]
impl PyKeyEventState {
    #[classattr]
    const NONE: Self = Self { bits: 0 };

    #[classattr]
    const KEYPAD: Self = Self {
        bits: KeyEventState::KEYPAD.bits(),
    };

    #[classattr]
    const CAPS_LOCK: Self = Self {
        bits: KeyEventState::CAPS_LOCK.bits(),
    };

    #[classattr]
    const NUM_LOCK: Self = Self {
        bits: KeyEventState::NUM_LOCK.bits(),
    };

    fn keypad(&self) -> bool {
        KeyEventState::from_bits_truncate(self.bits).contains(KeyEventState::KEYPAD)
    }

    fn caps_lock(&self) -> bool {
        KeyEventState::from_bits_truncate(self.bits).contains(KeyEventState::CAPS_LOCK)
    }

    fn num_lock(&self) -> bool {
        KeyEventState::from_bits_truncate(self.bits).contains(KeyEventState::NUM_LOCK)
    }

    fn __repr__(&self) -> String {
        format!("KeyEventState(bits={})", self.bits)
    }
}

impl From<KeyEventState> for PyKeyEventState {
    fn from(value: KeyEventState) -> Self {
        Self {
            bits: value.bits(),
        }
    }
}

#[pyclass(name = "KeyModifiers", module = "xnano_core.rust.native", from_py_object)]
#[derive(Clone, Copy)]
pub struct PyKeyModifiers {
    #[pyo3(get)]
    pub bits: u8,
}

#[pymethods]
impl PyKeyModifiers {
    #[classattr]
    const NONE: Self = Self { bits: 0 };

    #[classattr]
    const SHIFT: Self = Self {
        bits: KeyModifiers::SHIFT.bits(),
    };

    #[classattr]
    const CONTROL: Self = Self {
        bits: KeyModifiers::CONTROL.bits(),
    };

    #[classattr]
    const ALT: Self = Self {
        bits: KeyModifiers::ALT.bits(),
    };

    #[classattr]
    const SUPER: Self = Self {
        bits: KeyModifiers::SUPER.bits(),
    };

    #[classattr]
    const HYPER: Self = Self {
        bits: KeyModifiers::HYPER.bits(),
    };

    #[classattr]
    const META: Self = Self {
        bits: KeyModifiers::META.bits(),
    };

    fn contains(&self, other: Self) -> bool {
        KeyModifiers::from_bits_truncate(self.bits)
            .contains(KeyModifiers::from_bits_truncate(other.bits))
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

    fn super_(&self) -> bool {
        KeyModifiers::from_bits_truncate(self.bits).contains(KeyModifiers::SUPER)
    }

    fn meta(&self) -> bool {
        KeyModifiers::from_bits_truncate(self.bits).contains(KeyModifiers::META)
    }

    fn hyper(&self) -> bool {
        KeyModifiers::from_bits_truncate(self.bits).contains(KeyModifiers::HYPER)
    }

    fn __or__(&self, other: Self) -> Self {
        Self {
            bits: self.bits | other.bits,
        }
    }

    fn __repr__(&self) -> String {
        format!("KeyModifiers(bits={})", self.bits)
    }
}

impl From<KeyModifiers> for PyKeyModifiers {
    fn from(value: KeyModifiers) -> Self {
        Self {
            bits: value.bits(),
        }
    }
}

#[pyclass(name = "KeyCode", module = "xnano_core.rust.native", eq, eq_int, from_py_object)]
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
    CapsLock,
    ScrollLock,
    NumLock,
    PrintScreen,
    Pause,
    Menu,
    KeypadBegin,
    Media,
    Modifier,
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
        KeyCode::CapsLock => PyKeyCode::CapsLock,
        KeyCode::ScrollLock => PyKeyCode::ScrollLock,
        KeyCode::NumLock => PyKeyCode::NumLock,
        KeyCode::PrintScreen => PyKeyCode::PrintScreen,
        KeyCode::Pause => PyKeyCode::Pause,
        KeyCode::Menu => PyKeyCode::Menu,
        KeyCode::KeypadBegin => PyKeyCode::KeypadBegin,
        KeyCode::Media(_) => PyKeyCode::Media,
        KeyCode::Modifier(_) => PyKeyCode::Modifier,
    }
}

#[pyclass(name = "MouseButton", module = "xnano_core.rust.native", eq, eq_int, from_py_object)]
#[derive(Clone, Copy, PartialEq, Debug)]
pub enum PyMouseButton {
    Left,
    Right,
    Middle,
    NoButton,
}

impl From<MouseButton> for PyMouseButton {
    fn from(button: MouseButton) -> Self {
        match button {
            MouseButton::Left => PyMouseButton::Left,
            MouseButton::Right => PyMouseButton::Right,
            MouseButton::Middle => PyMouseButton::Middle,
        }
    }
}

#[pyclass(name = "MouseEventKind", module = "xnano_core.rust.native", eq, eq_int, from_py_object)]
#[derive(Clone, Copy, PartialEq, Debug)]
pub enum PyMouseEventKind {
    Down,
    Up,
    Drag,
    Moved,
    ScrollDown,
    ScrollUp,
    ScrollLeft,
    ScrollRight,
}

impl PyMouseEventKind {
    fn as_str(self) -> &'static str {
        match self {
            PyMouseEventKind::Down => "down",
            PyMouseEventKind::Up => "up",
            PyMouseEventKind::Drag => "drag",
            PyMouseEventKind::Moved => "moved",
            PyMouseEventKind::ScrollDown => "scroll_down",
            PyMouseEventKind::ScrollUp => "scroll_up",
            PyMouseEventKind::ScrollLeft => "scroll_left",
            PyMouseEventKind::ScrollRight => "scroll_right",
        }
    }
}

fn mouse_event_kind(value: MouseEventKind) -> (PyMouseEventKind, PyMouseButton) {
    match value {
        MouseEventKind::Down(btn) => (PyMouseEventKind::Down, btn.into()),
        MouseEventKind::Up(btn) => (PyMouseEventKind::Up, btn.into()),
        MouseEventKind::Drag(btn) => (PyMouseEventKind::Drag, btn.into()),
        MouseEventKind::Moved => (PyMouseEventKind::Moved, PyMouseButton::NoButton),
        MouseEventKind::ScrollDown => (PyMouseEventKind::ScrollDown, PyMouseButton::NoButton),
        MouseEventKind::ScrollUp => (PyMouseEventKind::ScrollUp, PyMouseButton::NoButton),
        MouseEventKind::ScrollLeft => (PyMouseEventKind::ScrollLeft, PyMouseButton::NoButton),
        MouseEventKind::ScrollRight => (PyMouseEventKind::ScrollRight, PyMouseButton::NoButton),
    }
}

#[pyclass(name = "MouseEvent", module = "xnano_core.rust.native", from_py_object)]
#[derive(Clone)]
pub struct PyMouseEvent {
    #[pyo3(get)]
    pub event_kind: PyMouseEventKind,
    #[pyo3(get)]
    pub mouse_button: PyMouseButton,
    #[pyo3(get)]
    pub x: u16,
    #[pyo3(get)]
    pub y: u16,
    #[pyo3(get)]
    pub modifiers: PyKeyModifiers,
    kind: String,
    button: String,
}

#[pymethods]
impl PyMouseEvent {
    #[getter]
    fn kind(&self) -> &str {
        &self.kind
    }

    #[getter]
    fn button(&self) -> &str {
        &self.button
    }

    #[getter]
    fn column(&self) -> u16 {
        self.x
    }

    #[getter]
    fn row(&self) -> u16 {
        self.y
    }
}

impl From<MouseEvent> for PyMouseEvent {
    fn from(event: MouseEvent) -> Self {
        let (event_kind, mouse_button) = mouse_event_kind(event.kind);
        let button = match mouse_button {
            PyMouseButton::Left => "left".into(),
            PyMouseButton::Right => "right".into(),
            PyMouseButton::Middle => "middle".into(),
            PyMouseButton::NoButton => "none".into(),
        };
        Self {
            kind: event_kind.as_str().into(),
            button,
            event_kind,
            mouse_button,
            x: event.column,
            y: event.row,
            modifiers: event.modifiers.into(),
        }
    }
}

#[pyclass(name = "KeyEvent", module = "xnano_core.rust.native", from_py_object)]
#[derive(Clone)]
pub struct PyKeyEvent {
    code: KeyCode,
    #[pyo3(get)]
    pub kind: PyKeyEventKind,
    #[pyo3(get)]
    pub modifiers: PyKeyModifiers,
    #[pyo3(get)]
    pub code_name: PyKeyCode,
    #[pyo3(get)]
    pub state: PyKeyEventState,
}

#[pymethods]
impl PyKeyEvent {
    fn char_value(&self) -> Option<char> {
        match self.code {
            KeyCode::Char(c) => Some(c),
            _ => None,
        }
    }

    fn function_number(&self) -> Option<u8> {
        match self.code {
            KeyCode::F(n) => Some(n),
            _ => None,
        }
    }

    fn is_char(&self, ch: char) -> bool {
        matches!(self.code, KeyCode::Char(c) if c == ch)
    }

    fn char(&self) -> Option<char> {
        self.char_value()
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

    fn is_home(&self) -> bool {
        self.code == KeyCode::Home
    }

    fn is_end(&self) -> bool {
        self.code == KeyCode::End
    }

    fn is_insert(&self) -> bool {
        self.code == KeyCode::Insert
    }

    fn is_delete(&self) -> bool {
        self.code == KeyCode::Delete
    }

    fn is_null(&self) -> bool {
        self.code == KeyCode::Null
    }

    fn is_back_tab(&self) -> bool {
        self.code == KeyCode::BackTab
    }

    fn is_function_key(&self) -> bool {
        matches!(self.code, KeyCode::F(_))
    }

    fn is_caps_lock(&self) -> bool {
        self.code == KeyCode::CapsLock
    }

    fn is_scroll_lock(&self) -> bool {
        self.code == KeyCode::ScrollLock
    }

    fn is_num_lock(&self) -> bool {
        self.code == KeyCode::NumLock
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
            state: event.state.into(),
        }
    }
}

#[pyclass(name = "Terminal", module = "xnano_core.rust.native", unsendable)]
pub struct PyTerminal {
    inner: DefaultTerminal,
}

#[pymethods]
impl PyTerminal {
    #[staticmethod]
    fn init() -> Self {
        Self { inner: init() }
    }

    fn draw(&mut self, callback: Py<PyAny>) -> PyResult<()> {
        self.inner
            .draw(|frame| {
                if let Err(err) = Python::attach(|py| {
                    let py_frame = PyFrame::from_frame(frame);
                    callback.call1(py, (py_frame,))
                }) {
                    Python::attach(|py| err.print(py));
                }
            })
            .map_err(|err| pyo3::exceptions::PyIOError::new_err(err.to_string()))?;
        Ok(())
    }

    fn try_draw(&mut self, callback: Py<PyAny>) -> PyResult<PyCompletedFrame> {
        let mut callback_error: Option<PyErr> = None;
        let completed = self
            .inner
            .try_draw(|frame| {
                Python::attach(|py| -> Result<(), std::io::Error> {
                    let py_frame = PyFrame::from_frame(frame);
                    match callback.call1(py, (py_frame,)) {
                        Ok(_) => Ok(()),
                        Err(err) => {
                            callback_error = Some(err);
                            Err(std::io::Error::new(
                                std::io::ErrorKind::Other,
                                "Python draw callback failed",
                            ))
                        }
                    }
                })
            })
            .map_err(|err| pyo3::exceptions::PyIOError::new_err(err.to_string()))?;

        if let Some(err) = callback_error {
            return Err(err);
        }

        Ok(PyCompletedFrame {
            buffer: PyBuffer {
                inner: completed.buffer.clone(),
            },
            area: PyRect {
                inner: completed.area,
            },
            count: completed.count,
        })
    }

    fn flush(&mut self) -> PyResult<()> {
        self.inner
            .flush()
            .map_err(|err| pyo3::exceptions::PyIOError::new_err(err.to_string()))
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
fn poll_event(py: Python<'_>, timeout_ms: u64) -> PyResult<Option<PyEvent>> {
    let ready = py
        .detach(|| event::poll(Duration::from_millis(timeout_ms)))
        .map_err(io_to_py)?;
    py.check_signals()?;
    if !ready {
        return Ok(None);
    }
    let ev = py.detach(event::read).map_err(io_to_py)?;
    Ok(Some(PyEvent::from_crossterm(ev)))
}

#[pyfunction]
fn read_event(py: Python<'_>) -> PyResult<PyEvent> {
    loop {
        if let Some(ev) = poll_event(py, u64::MAX / 2)? {
            return Ok(ev);
        }
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyFrame>()?;
    m.add_class::<PyCompletedFrame>()?;
    m.add_class::<PyTerminal>()?;
    m.add_class::<PyKeyEventKind>()?;
    m.add_class::<PyKeyEventState>()?;
    m.add_class::<PyKeyModifiers>()?;
    m.add_class::<PyKeyCode>()?;
    m.add_class::<PyMouseButton>()?;
    m.add_class::<PyMouseEventKind>()?;
    m.add_class::<PyMouseEvent>()?;
    m.add_class::<PyKeyEvent>()?;
    m.add_function(wrap_pyfunction!(restore_terminal, m)?)?;
    m.add_function(wrap_pyfunction!(poll_event, m)?)?;
    m.add_function(wrap_pyfunction!(read_event, m)?)?;
    Ok(())
}
