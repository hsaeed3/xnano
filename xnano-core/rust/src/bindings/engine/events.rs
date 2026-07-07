use crossterm::event::Event as CtEvent;
use pyo3::prelude::*;

use super::super::terminal::{PyKeyEvent, PyMouseEvent};

#[pyclass(name = "CoreTerminalEventKind", module = "xnano_core.rust.engine", eq, eq_int, from_py_object)]
#[derive(Clone, Copy, PartialEq, Debug)]
pub enum PyTerminalEventKind {
    Key,
    Resize,
    Paste,
    Mouse,
    FocusGained,
    FocusLost,
    Tick,
}

#[pyclass(name = "CoreTickEvent", module = "xnano_core.rust.engine", from_py_object)]
#[derive(Clone, Copy)]
pub struct PyTickEvent {
    #[pyo3(get)]
    pub elapsed_ms: u64,
}

#[pyclass(name = "CoreEvent", module = "xnano_core.rust.engine", from_py_object)]
#[derive(Clone)]
pub struct PyEvent {
    #[pyo3(get)]
    pub kind: PyTerminalEventKind,
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
    #[pyo3(get)]
    pub tick: Option<PyTickEvent>,
}

impl PyEvent {
    pub(crate) fn tick(elapsed_ms: u64) -> Self {
        Self {
            kind: PyTerminalEventKind::Tick,
            key: None,
            width: None,
            height: None,
            paste: None,
            mouse: None,
            tick: Some(PyTickEvent { elapsed_ms }),
        }
    }

    pub(crate) fn from_crossterm(ev: CtEvent) -> Self {
        match ev {
            CtEvent::Key(key) => Self {
                kind: PyTerminalEventKind::Key,
                key: Some(key.into()),
                width: None,
                height: None,
                paste: None,
                mouse: None,
                tick: None,
            },
            CtEvent::Resize(width, height) => Self {
                kind: PyTerminalEventKind::Resize,
                key: None,
                width: Some(width),
                height: Some(height),
                paste: None,
                mouse: None,
                tick: None,
            },
            CtEvent::Paste(text) => Self {
                kind: PyTerminalEventKind::Paste,
                key: None,
                width: None,
                height: None,
                paste: Some(text),
                mouse: None,
                tick: None,
            },
            CtEvent::Mouse(mouse) => Self {
                kind: PyTerminalEventKind::Mouse,
                key: None,
                width: None,
                height: None,
                paste: None,
                mouse: Some(mouse.into()),
                tick: None,
            },
            CtEvent::FocusGained => Self {
                kind: PyTerminalEventKind::FocusGained,
                key: None,
                width: None,
                height: None,
                paste: None,
                mouse: None,
                tick: None,
            },
            CtEvent::FocusLost => Self {
                kind: PyTerminalEventKind::FocusLost,
                key: None,
                width: None,
                height: None,
                paste: None,
                mouse: None,
                tick: None,
            },
        }
    }
}

#[pymethods]
impl PyEvent {
    /// Returns the event type as a string without any Python-side comparison.
    /// Values: "key", "resize", "paste", "mouse", "focus_gained", "focus_lost", "tick".
    fn kind_str(&self) -> &'static str {
        match self.kind {
            PyTerminalEventKind::Key => "key",
            PyTerminalEventKind::Resize => "resize",
            PyTerminalEventKind::Paste => "paste",
            PyTerminalEventKind::Mouse => "mouse",
            PyTerminalEventKind::FocusGained => "focus_gained",
            PyTerminalEventKind::FocusLost => "focus_lost",
            PyTerminalEventKind::Tick => "tick",
        }
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyTerminalEventKind>()?;
    m.add_class::<PyTickEvent>()?;
    m.add_class::<PyEvent>()?;
    Ok(())
}
