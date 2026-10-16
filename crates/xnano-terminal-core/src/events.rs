//! `Event`, `KeyEvent`, `MouseEvent` and `KeyBinding`.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyFrozenSet;
use xnano_terminal_runtime::event::{
    Event, EventKind, EventPayload, KeyBinding, KeyEvent, KeyKind, MouseButton, MouseEvent,
    MouseKind,
};
use xnano_terminal_runtime::geometry::Size;

use crate::geometry::{PyPoint, PySize};

#[pyclass(
    name = "KeyEvent",
    module = "xnano_core._xnano_core",
    frozen,
    eq,
    from_py_object
)]
#[derive(Clone, PartialEq, Eq)]
pub struct PyKeyEvent {
    pub inner: KeyEvent,
}

#[pymethods]
impl PyKeyEvent {
    #[getter]
    fn key(&self) -> &str {
        &self.inner.key
    }

    #[getter]
    fn text(&self) -> Option<&str> {
        self.inner.text.as_deref()
    }

    #[getter]
    fn modifiers<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyFrozenSet>> {
        PyFrozenSet::new(py, self.inner.modifiers.names())
    }

    #[getter]
    fn kind(&self) -> &'static str {
        self.inner.kind.name()
    }

    fn matches(&self, binding: &Bound<'_, PyAny>) -> PyResult<bool> {
        Ok(binding_arg(binding)?.matches(&self.inner))
    }

    fn __repr__(&self) -> String {
        format!(
            "KeyEvent(key='{}', modifiers={:?}, kind='{}')",
            self.inner.key,
            self.inner.modifiers.names(),
            self.inner.kind.name()
        )
    }
}

#[pyclass(
    name = "MouseEvent",
    module = "xnano_core._xnano_core",
    frozen,
    eq,
    from_py_object
)]
#[derive(Clone, PartialEq, Eq)]
pub struct PyMouseEvent {
    pub inner: MouseEvent,
}

#[pymethods]
impl PyMouseEvent {
    #[getter]
    fn position(&self) -> PyPoint {
        PyPoint {
            inner: self.inner.position(),
        }
    }

    #[getter]
    fn column(&self) -> i32 {
        self.inner.column
    }

    #[getter]
    fn row(&self) -> i32 {
        self.inner.row
    }

    #[getter]
    fn kind(&self) -> &'static str {
        self.inner.kind.name()
    }

    #[getter]
    fn button(&self) -> Option<&'static str> {
        self.inner.button.map(MouseButton::name)
    }

    #[getter]
    fn scroll_x(&self) -> i32 {
        self.inner.scroll_x
    }

    #[getter]
    fn scroll_y(&self) -> i32 {
        self.inner.scroll_y
    }

    fn __repr__(&self) -> String {
        format!(
            "MouseEvent(column={}, row={}, kind='{}', button={:?})",
            self.inner.column,
            self.inner.row,
            self.inner.kind.name(),
            self.inner.button.map(MouseButton::name)
        )
    }
}

#[pyclass(
    name = "Event",
    module = "xnano_core._xnano_core",
    frozen,
    eq,
    from_py_object
)]
#[derive(Clone, PartialEq)]
pub struct PyEvent {
    pub inner: Event,
}

impl PyEvent {
    pub fn new(inner: Event) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyEvent {
    #[getter]
    fn kind(&self) -> &'static str {
        self.inner.kind.name()
    }

    #[getter]
    fn timestamp_seconds(&self) -> f64 {
        self.inner.timestamp_seconds
    }

    #[getter]
    fn key(&self) -> Option<PyKeyEvent> {
        self.inner.key().cloned().map(|inner| PyKeyEvent { inner })
    }

    #[getter]
    fn mouse(&self) -> Option<PyMouseEvent> {
        self.inner
            .mouse()
            .copied()
            .map(|inner| PyMouseEvent { inner })
    }

    #[getter]
    fn pasted_text(&self) -> Option<&str> {
        match &self.inner.payload {
            EventPayload::Paste(text) => Some(text),
            _ => None,
        }
    }

    #[getter]
    fn size(&self) -> Option<PySize> {
        match &self.inner.payload {
            EventPayload::Size(size) => Some(PySize { inner: *size }),
            _ => None,
        }
    }

    #[getter]
    fn timer_key(&self) -> Option<&str> {
        match &self.inner.payload {
            EventPayload::Timer(key) => Some(key),
            _ => None,
        }
    }

    #[classmethod]
    #[pyo3(signature = (binding, *, kind = "press"))]
    fn key_press(
        _cls: &Bound<'_, pyo3::types::PyType>,
        binding: &str,
        kind: &str,
    ) -> PyResult<Self> {
        let kind = KeyKind::from_name(kind).ok_or_else(|| {
            PyValueError::new_err(format!(
                "\"{kind}\" is not a key event kind; use press, repeat or release"
            ))
        })?;
        let key = KeyEvent::from_binding(binding, kind).map_err(PyValueError::new_err)?;
        Ok(Self::new(Event::new(
            EventKind::Key,
            EventPayload::Key(key),
        )))
    }

    #[classmethod]
    fn paste(_cls: &Bound<'_, pyo3::types::PyType>, text: String) -> Self {
        Self::new(Event::new(EventKind::Paste, EventPayload::Paste(text)))
    }

    #[classmethod]
    #[pyo3(signature = (*, width, height))]
    fn resize(_cls: &Bound<'_, pyo3::types::PyType>, width: i32, height: i32) -> PyResult<Self> {
        if width < 0 || height < 0 {
            return Err(PyValueError::new_err(
                "a resize event needs a width and height of zero or more",
            ));
        }
        Ok(Self::new(Event::new(
            EventKind::Resize,
            EventPayload::Size(Size::new(width, height)),
        )))
    }

    #[classmethod]
    #[pyo3(signature = (*, column, row, kind, button = None, scroll_x = 0, scroll_y = 0))]
    fn mouse_event(
        _cls: &Bound<'_, pyo3::types::PyType>,
        column: i32,
        row: i32,
        kind: &str,
        button: Option<&str>,
        scroll_x: i32,
        scroll_y: i32,
    ) -> PyResult<Self> {
        let kind = MouseKind::from_name(kind).ok_or_else(|| {
            PyValueError::new_err(format!(
                "\"{kind}\" is not a mouse event kind; use press, release, drag, move or scroll"
            ))
        })?;
        let button = match button {
            Some(name) => Some(MouseButton::from_name(name).ok_or_else(|| {
                PyValueError::new_err(format!(
                    "\"{name}\" is not a mouse button; use left, right or middle"
                ))
            })?),
            None => None,
        };
        Ok(Self::new(Event::new(
            EventKind::Mouse,
            EventPayload::Mouse(MouseEvent {
                column,
                row,
                kind,
                button,
                scroll_x,
                scroll_y,
            }),
        )))
    }

    #[classmethod]
    fn tick(_cls: &Bound<'_, pyo3::types::PyType>) -> Self {
        Self::new(Event::new(EventKind::Tick, EventPayload::None))
    }

    #[classmethod]
    fn timer(_cls: &Bound<'_, pyo3::types::PyType>, key: String) -> Self {
        Self::new(Event::new(EventKind::Timer, EventPayload::Timer(key)))
    }

    #[classmethod]
    fn wake(_cls: &Bound<'_, pyo3::types::PyType>) -> Self {
        Self::new(Event::new(EventKind::Wake, EventPayload::None))
    }

    #[classmethod]
    fn exit_requested(_cls: &Bound<'_, pyo3::types::PyType>) -> Self {
        Self::new(Event::new(EventKind::ExitRequested, EventPayload::None))
    }

    #[classmethod]
    #[pyo3(signature = (name, *, data = None))]
    fn custom(
        _cls: &Bound<'_, pyo3::types::PyType>,
        name: String,
        data: Option<String>,
    ) -> PyResult<Self> {
        if name.trim().is_empty() {
            return Err(PyValueError::new_err(
                "a custom event needs a name, such as Event.custom(\"volume_changed\")",
            ));
        }
        Ok(Self::new(Event::new(
            EventKind::Custom,
            EventPayload::Custom { name, data },
        )))
    }

    #[getter]
    fn custom_name(&self) -> Option<&str> {
        match &self.inner.payload {
            EventPayload::Custom { name, .. } => Some(name),
            _ => None,
        }
    }

    #[getter]
    fn custom_data(&self) -> Option<&str> {
        match &self.inner.payload {
            EventPayload::Custom { data, .. } => data.as_deref(),
            _ => None,
        }
    }

    #[classmethod]
    fn focus_gained(_cls: &Bound<'_, pyo3::types::PyType>) -> Self {
        Self::new(Event::new(EventKind::FocusGained, EventPayload::None))
    }

    #[classmethod]
    fn focus_lost(_cls: &Bound<'_, pyo3::types::PyType>) -> Self {
        Self::new(Event::new(EventKind::FocusLost, EventPayload::None))
    }

    fn __repr__(&self) -> String {
        format!("Event(kind='{}')", self.inner.kind.name())
    }
}

#[pyclass(
    name = "KeyBinding",
    module = "xnano_core._xnano_core",
    frozen,
    eq,
    hash,
    from_py_object
)]
#[derive(Clone, PartialEq, Eq, Hash)]
pub struct PyKeyBinding {
    pub inner: KeyBinding,
}

/// A `KeyBinding` from a binding string or object.
pub fn binding_arg(value: &Bound<'_, PyAny>) -> PyResult<KeyBinding> {
    if let Ok(binding) = value.extract::<PyKeyBinding>() {
        return Ok(binding.inner);
    }
    let text: String = value.extract().map_err(|_| {
        pyo3::exceptions::PyTypeError::new_err(
            "a key binding must be a string such as \"ctrl+c\" or a KeyBinding",
        )
    })?;
    KeyBinding::parse(&text).map_err(PyValueError::new_err)
}

#[pymethods]
impl PyKeyBinding {
    fn __copy__(&self) -> Self {
        self.clone()
    }
    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.clone()
    }

    #[classmethod]
    fn parse(_cls: &Bound<'_, pyo3::types::PyType>, binding: &str) -> PyResult<Self> {
        Ok(Self {
            inner: KeyBinding::parse(binding).map_err(PyValueError::new_err)?,
        })
    }

    fn matches(&self, event: &Bound<'_, PyAny>) -> PyResult<bool> {
        if let Ok(event) = event.extract::<PyEvent>() {
            return Ok(event.inner.key().is_some_and(|key| self.inner.matches(key)));
        }
        let key = event.extract::<PyKeyEvent>()?;
        Ok(self.inner.matches(&key.inner))
    }

    fn __repr__(&self) -> String {
        let mut parts: Vec<&str> = self.inner.modifiers.names();
        parts.push(&self.inner.key);
        format!("KeyBinding('{}')", parts.join("+"))
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyKeyEvent>()?;
    m.add_class::<PyMouseEvent>()?;
    m.add_class::<PyEvent>()?;
    m.add_class::<PyKeyBinding>()
}
