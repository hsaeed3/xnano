//! Hooks and cancellable scheduling registrations.

use std::sync::Arc;
use std::sync::Mutex;
use std::sync::atomic::{AtomicBool, AtomicI32, AtomicU64, Ordering};

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use xnano_terminal_runtime::event::{EventKind, KeyBinding};
use xnano_terminal_runtime::expression::Expr;
use xnano_terminal_runtime::geometry::Rectangle;

use crate::shared::lock;

/// What a hook listens for.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HookEvent {
    Event(EventKind),
    Mount,
    Unmount,
    Change,
    StateChange,
    BeforeRender,
    AfterRender,
}

impl HookEvent {
    pub fn parse(name: &str) -> PyResult<Self> {
        if let Some(kind) = EventKind::from_name(name) {
            return Ok(Self::Event(kind));
        }
        Ok(match name {
            "mount" => Self::Mount,
            "unmount" => Self::Unmount,
            "change" => Self::Change,
            "state_change" => Self::StateChange,
            "before_render" => Self::BeforeRender,
            "after_render" => Self::AfterRender,
            other => {
                return Err(PyValueError::new_err(format!(
                    "\"{other}\" is not an event a hook can listen for; use key, mouse, paste, \
                     resize, focus_gained, focus_lost, tick, timer, frame, wake, exit_requested, \
                     mount, unmount, change, state_change, before_render or after_render"
                )));
            }
        })
    }

    pub fn parse_all(names: &Bound<'_, PyAny>) -> PyResult<Vec<Self>> {
        if let Ok(single) = names.extract::<String>() {
            return Ok(vec![Self::parse(&single)?]);
        }
        let mut events = Vec::new();
        for name in names.try_iter()? {
            events.push(Self::parse(&name?.extract::<String>()?)?);
        }
        Ok(events)
    }
}

static NEXT_HOOK_ID: AtomicU64 = AtomicU64::new(1);

/// The switches of a hook, shared between the hook object and its registration.
pub struct HookState {
    pub is_enabled: AtomicBool,
    pub is_cancelled: AtomicBool,
    pub priority: AtomicI32,
    on_cancel: Mutex<Option<Py<PyAny>>>,
}

impl HookState {
    pub fn new(priority: i32) -> Arc<Self> {
        Arc::new(Self {
            is_enabled: AtomicBool::new(true),
            is_cancelled: AtomicBool::new(false),
            priority: AtomicI32::new(priority),
            on_cancel: Mutex::new(None),
        })
    }

    pub fn is_active(&self) -> bool {
        self.is_enabled.load(Ordering::SeqCst) && !self.is_cancelled.load(Ordering::SeqCst)
    }

    /// Cancel the hook, running its cancel callback once.
    pub fn cancel(&self, py: Python<'_>) {
        if self.is_cancelled.swap(true, Ordering::SeqCst) {
            return;
        }
        let callback = lock(&self.on_cancel).take();
        if let Some(callback) = callback
            && let Err(error) = callback.call0(py)
        {
            error.write_unraisable(py, None);
        }
    }
}

/// One registered hook.
pub struct HookEntry {
    pub id: u64,
    pub order: u64,
    pub callback: Py<PyAny>,
    pub condition: Option<Arc<Expr>>,
    pub events: Vec<HookEvent>,
    pub binding: Option<KeyBinding>,
    pub once: bool,
    pub region: Option<Rectangle>,
    pub state: Arc<HookState>,
}

impl HookEntry {
    pub fn new(
        callback: Py<PyAny>,
        condition: Option<Arc<Expr>>,
        events: Vec<HookEvent>,
        binding: Option<KeyBinding>,
        priority: i32,
        once: bool,
        region: Option<Rectangle>,
    ) -> Self {
        let id = NEXT_HOOK_ID.fetch_add(1, Ordering::SeqCst);
        Self {
            id,
            order: id,
            callback,
            condition,
            events,
            binding,
            once,
            region,
            state: HookState::new(priority),
        }
    }

    pub fn priority(&self) -> i32 {
        self.state.priority.load(Ordering::SeqCst)
    }

    pub fn listens_to(&self, event: HookEvent) -> bool {
        self.events.contains(&event)
    }
}

#[pyclass(name = "Hook", module = "xnano._xnano_core", frozen)]
pub struct PyHook {
    pub state: Arc<HookState>,
}

impl PyHook {
    pub fn new(state: Arc<HookState>) -> Self {
        Self { state }
    }

    pub fn on_cancel(&self, callback: Py<PyAny>) {
        *lock(&self.state.on_cancel) = Some(callback);
    }
}

#[pymethods]
impl PyHook {
    /// A hook that is not tied to any buffer, such as one that wraps a subscription.
    #[classmethod]
    #[pyo3(signature = (cancel = None))]
    fn _detached(_cls: &Bound<'_, pyo3::types::PyType>, cancel: Option<Py<PyAny>>) -> Self {
        let hook = Self {
            state: HookState::new(0),
        };
        if let Some(cancel) = cancel {
            hook.on_cancel(cancel);
        }
        hook
    }

    #[getter]
    fn enabled(&self) -> bool {
        self.state.is_enabled.load(Ordering::SeqCst)
    }

    #[setter]
    fn set_enabled(&self, value: bool) {
        self.state.is_enabled.store(value, Ordering::SeqCst);
    }

    #[getter]
    fn priority(&self) -> i32 {
        self.state.priority.load(Ordering::SeqCst)
    }

    #[getter]
    fn is_cancelled(&self) -> bool {
        self.state.is_cancelled.load(Ordering::SeqCst)
    }

    fn cancel(&self, py: Python<'_>) {
        self.state.cancel(py);
    }

    fn __repr__(&self) -> String {
        format!(
            "Hook(priority={}, enabled={}, is_cancelled={})",
            self.priority(),
            if self.enabled() { "True" } else { "False" },
            if self.is_cancelled() { "True" } else { "False" }
        )
    }
}

/// The cancel switch of a scheduled call.
pub struct ScheduledState {
    pub is_cancelled: AtomicBool,
}

#[pyclass(name = "ScheduledCall", module = "xnano._xnano_core", frozen)]
pub struct PyScheduledCall {
    pub state: Arc<ScheduledState>,
}

#[pymethods]
impl PyScheduledCall {
    #[getter]
    fn is_cancelled(&self) -> bool {
        self.state.is_cancelled.load(Ordering::SeqCst)
    }

    fn cancel(&self) {
        self.state.is_cancelled.store(true, Ordering::SeqCst);
    }

    fn __repr__(&self) -> String {
        format!(
            "ScheduledCall(is_cancelled={})",
            if self.is_cancelled() { "True" } else { "False" }
        )
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyHook>()?;
    m.add_class::<PyScheduledCall>()
}
