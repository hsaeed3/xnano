//! `Trigger`: when an operation or hook runs, and which events count.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use xnano_terminal_runtime::event::{EventKind, KeyBinding, KeyKind, MouseKind};

use crate::events::PyEvent;
use crate::state::PyStateChange;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum TriggerKind {
    Immediate,
    Frame,
    Update,
    Key,
    KeyRelease,
    Click,
    Drag,
    Mouse,
    Paste,
    Resize,
    StateChange,
    Every,
    After,
}

const KINDS: [(&str, TriggerKind); 13] = [
    ("immediate", TriggerKind::Immediate),
    ("frame", TriggerKind::Frame),
    ("update", TriggerKind::Update),
    ("key", TriggerKind::Key),
    ("key_release", TriggerKind::KeyRelease),
    ("click", TriggerKind::Click),
    ("drag", TriggerKind::Drag),
    ("mouse", TriggerKind::Mouse),
    ("paste", TriggerKind::Paste),
    ("resize", TriggerKind::Resize),
    ("state_change", TriggerKind::StateChange),
    ("every", TriggerKind::Every),
    ("after", TriggerKind::After),
];

impl TriggerKind {
    fn name(self) -> &'static str {
        KINDS
            .iter()
            .find(|(_, kind)| *kind == self)
            .map_or("immediate", |(name, _)| name)
    }
}

/// When something runs, and which events count.
///
/// Event triggers (``key``, ``click``, ``drag``, ``mouse``, ``paste``, ``resize`` and
/// ``state_change``) are decided here, in native code; the time triggers (``every`` and
/// ``after``) and the loop triggers (``immediate``, ``frame`` and ``update``) carry the numbers
/// the terminal's clock and loop need.
#[pyclass(
    name = "Trigger",
    module = "xnano_core._xnano_core",
    frozen,
    eq,
    from_py_object
)]
#[derive(Clone, PartialEq)]
pub struct PyTrigger {
    kind: TriggerKind,
    seconds: Option<f64>,
    keys: Vec<String>,
}

fn require_seconds(kind: &str, seconds: f64) -> PyResult<f64> {
    if seconds.is_nan() || seconds < 0.0 {
        return Err(PyValueError::new_err(format!(
            "Trigger.{kind} needs a number of seconds of zero or more, but was given {seconds}. \
             Pass a value such as 0.5."
        )));
    }
    Ok(seconds)
}

fn require_keys(keys: Vec<String>) -> PyResult<Vec<String>> {
    for key in &keys {
        KeyBinding::parse(key).map_err(|reason| {
            PyValueError::new_err(format!(
                "\"{key}\" is not a key binding: {reason}. Use a name such as \"q\", \"enter\" or \"ctrl+s\"."
            ))
        })?;
    }
    Ok(keys)
}

impl PyTrigger {
    fn plain(kind: TriggerKind) -> Self {
        Self {
            kind,
            seconds: None,
            keys: Vec::new(),
        }
    }

    fn matches_event(&self, event: &Bound<'_, PyAny>) -> PyResult<bool> {
        if self.kind == TriggerKind::StateChange {
            return Ok(event.extract::<PyRef<'_, PyStateChange>>().is_ok());
        }
        let Ok(event) = event.extract::<PyRef<'_, PyEvent>>() else {
            return Ok(false);
        };
        let event = &event.inner;
        Ok(match self.kind {
            TriggerKind::Key | TriggerKind::KeyRelease => {
                let Some(key) = event.key() else {
                    return Ok(false);
                };
                let is_release = key.kind == KeyKind::Release;
                if is_release != (self.kind == TriggerKind::KeyRelease) {
                    return Ok(false);
                }
                if self.keys.is_empty() {
                    return Ok(true);
                }
                self.keys
                    .iter()
                    .any(|name| KeyBinding::parse(name).is_ok_and(|binding| binding.matches(key)))
            }
            TriggerKind::Click => event
                .mouse()
                .is_some_and(|mouse| mouse.kind == MouseKind::Press),
            TriggerKind::Drag => event
                .mouse()
                .is_some_and(|mouse| mouse.kind == MouseKind::Drag),
            TriggerKind::Mouse => event.kind == EventKind::Mouse,
            TriggerKind::Paste => event.kind == EventKind::Paste,
            TriggerKind::Resize => event.kind == EventKind::Resize,
            _ => false,
        })
    }
}

#[pymethods]
impl PyTrigger {
    /// Build a trigger from its name, such as ``Trigger.named('click')``.
    #[staticmethod]
    #[pyo3(signature = (kind, *, seconds = None, keys = Vec::new()))]
    fn named(kind: &str, seconds: Option<f64>, keys: Vec<String>) -> PyResult<Self> {
        let Some((_, parsed)) = KINDS.iter().find(|(name, _)| *name == kind) else {
            let names: Vec<&str> = KINDS.iter().map(|(name, _)| *name).collect();
            return Err(PyValueError::new_err(format!(
                "\"{kind}\" is not a trigger. Use one of: {}.",
                names.join(", ")
            )));
        };
        match parsed {
            TriggerKind::Every | TriggerKind::After => {
                let Some(seconds) = seconds else {
                    return Err(PyValueError::new_err(format!(
                        "the \"{kind}\" trigger needs seconds, such as Trigger.{kind}(0.5)."
                    )));
                };
                Ok(Self {
                    kind: *parsed,
                    seconds: Some(require_seconds(kind, seconds)?),
                    keys: Vec::new(),
                })
            }
            TriggerKind::Key | TriggerKind::KeyRelease => Ok(Self {
                kind: *parsed,
                seconds: None,
                keys: require_keys(keys)?,
            }),
            _ => Ok(Self::plain(*parsed)),
        }
    }

    #[staticmethod]
    fn immediate() -> Self {
        Self::plain(TriggerKind::Immediate)
    }

    #[staticmethod]
    fn frame() -> Self {
        Self::plain(TriggerKind::Frame)
    }

    #[staticmethod]
    fn update() -> Self {
        Self::plain(TriggerKind::Update)
    }

    #[staticmethod]
    #[pyo3(signature = (*keys))]
    fn key(keys: Vec<String>) -> PyResult<Self> {
        Ok(Self {
            kind: TriggerKind::Key,
            seconds: None,
            keys: require_keys(keys)?,
        })
    }

    #[staticmethod]
    #[pyo3(signature = (*keys))]
    fn key_release(keys: Vec<String>) -> PyResult<Self> {
        Ok(Self {
            kind: TriggerKind::KeyRelease,
            seconds: None,
            keys: require_keys(keys)?,
        })
    }

    #[staticmethod]
    fn click() -> Self {
        Self::plain(TriggerKind::Click)
    }

    #[staticmethod]
    fn drag() -> Self {
        Self::plain(TriggerKind::Drag)
    }

    #[staticmethod]
    fn mouse() -> Self {
        Self::plain(TriggerKind::Mouse)
    }

    #[staticmethod]
    fn paste() -> Self {
        Self::plain(TriggerKind::Paste)
    }

    #[staticmethod]
    fn resize() -> Self {
        Self::plain(TriggerKind::Resize)
    }

    #[staticmethod]
    fn state_change() -> Self {
        Self::plain(TriggerKind::StateChange)
    }

    #[staticmethod]
    fn every(seconds: f64) -> PyResult<Self> {
        Ok(Self {
            kind: TriggerKind::Every,
            seconds: Some(require_seconds("every", seconds)?),
            keys: Vec::new(),
        })
    }

    #[staticmethod]
    fn after(seconds: f64) -> PyResult<Self> {
        Ok(Self {
            kind: TriggerKind::After,
            seconds: Some(require_seconds("after", seconds)?),
            keys: Vec::new(),
        })
    }

    /// The name of the trigger, such as ``'click'`` or ``'every'``.
    #[getter]
    fn kind(&self) -> &'static str {
        self.kind.name()
    }

    /// The interval or delay in seconds of an ``every`` or ``after`` trigger, else ``None``.
    #[getter]
    fn seconds(&self) -> Option<f64> {
        self.seconds
    }

    /// The key bindings a ``key`` or ``key_release`` trigger reacts to; empty means every key.
    #[getter]
    fn keys(&self) -> Vec<String> {
        self.keys.clone()
    }

    /// Whether the trigger is decided by looking at one event.
    #[getter]
    fn is_event_trigger(&self) -> bool {
        !matches!(
            self.kind,
            TriggerKind::Immediate
                | TriggerKind::Frame
                | TriggerKind::Update
                | TriggerKind::Every
                | TriggerKind::After
        )
    }

    /// Whether ``event`` counts for this trigger.
    fn matches(&self, event: Option<&Bound<'_, PyAny>>) -> PyResult<bool> {
        match event {
            Some(event) if !event.is_none() => self.matches_event(event),
            _ => Ok(false),
        }
    }

    /// Decide for a hook context: true when the context's event counts.
    fn __call__(&self, context: &Bound<'_, PyAny>) -> PyResult<bool> {
        let event = context.getattr("event")?;
        self.matches(Some(&event))
    }

    fn __repr__(&self) -> String {
        match (self.seconds, self.keys.is_empty()) {
            (Some(seconds), _) => format!("Trigger.{}({seconds})", self.kind.name()),
            (None, false) => format!("Trigger.{}({})", self.kind.name(), self.keys.join(", ")),
            (None, true) => format!("Trigger.{}()", self.kind.name()),
        }
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyTrigger>()
}
