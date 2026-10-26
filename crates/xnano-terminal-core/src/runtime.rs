//! `Runtime`: scheduling, device ownership, safe frame composition and deterministic testing.

use std::cell::{Cell, RefCell};
use std::collections::{HashMap, VecDeque};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex, Weak};
use std::time::Duration;

use pyo3::exceptions::{PyRuntimeError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict, PyTuple, PyType};
use xnano_terminal_runtime::buffer::{
    BufferCore, Geometry, absolute_origin, buffers_at, compose, latest_modification_stamp,
    listen_for_changes, relayout, tree_modified,
};
use xnano_terminal_runtime::clock::{Clock, ClockSource, SimulationClock};
use xnano_terminal_runtime::device::{DeviceModes, KeyboardInfo, Status, TerminalInfo};
use xnano_terminal_runtime::event::{Event, EventKind, EventPayload, KeyKind, MouseKind};
use xnano_terminal_runtime::geometry::{Rectangle, Size};
use xnano_terminal_runtime::grid::{Bounds, Grid, PasteMode};
use xnano_terminal_state::Store;

use crate::clocks::{PyClock, PySimulationClock};
use crate::errors::RenderError;
use crate::events::PyEvent;
use crate::geometry::{PyPoint, PySize};
use crate::hooks::{HookEntry, HookEvent, HookState, PyHook, PyScheduledCall, ScheduledState};
use crate::input::{
    PyDevice, PyInputRouter, PyInputState, PyTerminalOptions, focus_buffer, hit_areas_at,
};
use crate::shared::{
    Backend, DeviceData, EventQueue, InputData, Metrics, Motion, QueuedCall, RouterData,
    RuntimeShared, lock,
};
use crate::surface::{PyBuffer, PySurface, SurfaceEnv};

/// The shared state behind a Python runtime object.
pub fn shared_of(object: &Bound<'_, PyAny>) -> Option<Arc<RuntimeShared>> {
    object
        .extract::<PyRef<'_, PyRuntime>>()
        .ok()
        .map(|runtime| Arc::clone(&runtime.shared))
}

/// The Python runtime object that owns `shared`, if it is still alive.
pub fn runtime_object(py: Python<'_>, shared: &RuntimeShared) -> Option<Py<PyAny>> {
    let weak = lock(&shared.runtime_object)
        .as_ref()
        .map(|reference| reference.clone_ref(py))?;
    let target = weak.call0(py).ok()?;
    if target.is_none(py) {
        None
    } else {
        Some(target)
    }
}

enum ClockRef {
    Runtime,
    Base(Arc<Clock>),
    Simulation(Arc<SimulationClock>),
}

impl ClockRef {
    fn from_object(object: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let Some(object) = object.filter(|value| !value.is_none()) else {
            return Ok(Self::Runtime);
        };
        if let Ok(clock) = object.extract::<PyRef<'_, PyClock>>() {
            return Ok(Self::Base(Arc::clone(&clock.inner)));
        }
        if let Ok(clock) = object.extract::<PyRef<'_, PySimulationClock>>() {
            return Ok(Self::Simulation(Arc::clone(&clock.inner)));
        }
        Err(PyTypeError::new_err(
            "a clock must be a Clock or a SimulationClock",
        ))
    }

    fn elapsed(&self, shared: &RuntimeShared) -> f64 {
        match self {
            Self::Runtime => shared.clock.elapsed_seconds(),
            Self::Base(clock) => clock.elapsed_seconds(),
            Self::Simulation(clock) => clock.elapsed_seconds(),
        }
    }

    /// Seconds until the clock reaches `target`, in time the runtime clock keeps.
    fn seconds_until(&self, shared: &RuntimeShared, target: f64) -> Option<f64> {
        match self {
            Self::Simulation(clock) => clock.parent_seconds_until(target),
            other => Some((target - other.elapsed(shared)).max(0.0)),
        }
    }
}

struct Scheduled {
    state: Arc<ScheduledState>,
    callback: Py<PyAny>,
    due: f64,
    interval: Option<f64>,
    clock: ClockRef,
}

struct Timer {
    next: f64,
    interval: f64,
    should_repeat: bool,
}

#[derive(Default)]
struct Tick {
    interval: Option<f64>,
    next: f64,
}

struct UpdateRegistration {
    callback: Py<PyAny>,
    state: Arc<HookState>,
    target: Py<PyBuffer>,
    clock: ClockRef,
    fixed_step: Option<f64>,
    maximum_delta: Option<f64>,
    maximum_catch_up_steps: u32,
    should_retain_overflow: bool,
    accumulator: f64,
    last_elapsed: f64,
}

struct FrameRegistration {
    callback: Py<PyAny>,
    state: Arc<HookState>,
    target: Py<PyBuffer>,
}

struct ErrorHandler {
    callback: Py<PyAny>,
    state: Arc<HookState>,
}

struct Mount {
    buffer: Py<PyBuffer>,
    key: Option<String>,
    geometry: Geometry,
}

// The live terminal reads these; WebAssembly builds run offscreen only and never do.
#[cfg_attr(not(feature = "terminal"), allow(dead_code))]
struct Config {
    backend: Backend,
    // A Cell so the frame rate can change while the runtime runs; only its thread reads it.
    frame_interval_milliseconds: Cell<u64>,
    // Cells so an inline region can be resized before its session opens.
    inline_height: Cell<Option<u16>>,
    inline_width: Cell<Option<u16>>,
    should_handle_exit_signals: bool,
    options: Option<PyTerminalOptions>,
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum ContextKind {
    Plain,
    Event,
    Frame,
}

#[derive(Default)]
struct HookRun {
    ran: bool,
    is_consumed: bool,
    should_propagate: bool,
}

#[pyclass(name = "StepResult", module = "xnano_core._xnano_core", frozen)]
pub struct PyStepResult {
    events_processed: usize,
    updates_processed: usize,
    did_render: bool,
    is_running: bool,
}

#[pymethods]
impl PyStepResult {
    fn __richcmp__(
        slf: &Bound<'_, Self>,
        other: &Bound<'_, PyAny>,
        operation: pyo3::basic::CompareOp,
    ) -> PyResult<Py<PyAny>> {
        crate::reprs::compare_by_properties(slf.as_any(), other, operation)
    }

    fn __hash__(slf: &Bound<'_, Self>) -> PyResult<isize> {
        crate::reprs::hash_by_properties(slf.as_any())
    }

    #[getter]
    fn events_processed(&self) -> usize {
        self.events_processed
    }

    #[getter]
    fn updates_processed(&self) -> usize {
        self.updates_processed
    }

    #[getter]
    fn did_render(&self) -> bool {
        self.did_render
    }

    #[getter]
    fn is_running(&self) -> bool {
        self.is_running
    }

    fn __repr__(&self) -> String {
        format!(
            "StepResult(events_processed={}, updates_processed={}, did_render={}, is_running={})",
            self.events_processed,
            self.updates_processed,
            if self.did_render { "True" } else { "False" },
            if self.is_running { "True" } else { "False" }
        )
    }
}

#[pyclass(name = "FrameMetrics", module = "xnano_core._xnano_core", frozen)]
pub struct PyFrameMetrics {
    frames: u64,
    last_microseconds: u64,
    average_microseconds: u64,
}

#[pymethods]
impl PyFrameMetrics {
    fn __richcmp__(
        slf: &Bound<'_, Self>,
        other: &Bound<'_, PyAny>,
        operation: pyo3::basic::CompareOp,
    ) -> PyResult<Py<PyAny>> {
        crate::reprs::compare_by_properties(slf.as_any(), other, operation)
    }

    fn __hash__(slf: &Bound<'_, Self>) -> PyResult<isize> {
        crate::reprs::hash_by_properties(slf.as_any())
    }

    fn __repr__(slf: &Bound<'_, Self>) -> PyResult<String> {
        crate::reprs::described(
            slf.as_any(),
            &[
                "frames",
                "last_frame_microseconds",
                "average_frame_microseconds",
            ],
        )
    }

    #[getter]
    fn frames(&self) -> u64 {
        self.frames
    }

    #[getter]
    fn last_frame_microseconds(&self) -> u64 {
        self.last_microseconds
    }

    #[getter]
    fn average_frame_microseconds(&self) -> u64 {
        self.average_microseconds
    }
}

#[pyclass(name = "FrameSnapshot", module = "xnano_core._xnano_core", frozen)]
pub struct PyFrameSnapshot {
    grid: Arc<Grid>,
    revision: u64,
    cursor: Option<xnano_terminal_runtime::cursor::CursorPlacement>,
}

#[pymethods]
impl PyFrameSnapshot {
    fn __richcmp__(
        slf: &Bound<'_, Self>,
        other: &Bound<'_, PyAny>,
        operation: pyo3::basic::CompareOp,
    ) -> PyResult<Py<PyAny>> {
        crate::reprs::compare_by_properties(slf.as_any(), other, operation)
    }

    fn __hash__(slf: &Bound<'_, Self>) -> PyResult<isize> {
        crate::reprs::hash_by_properties(slf.as_any())
    }

    fn __repr__(slf: &Bound<'_, Self>) -> PyResult<String> {
        crate::reprs::described(slf.as_any(), &["size", "revision", "cursor_position"])
    }

    #[getter]
    fn size(&self) -> PySize {
        PySize {
            inner: Size::new(i32::from(self.grid.width()), i32::from(self.grid.height())),
        }
    }

    #[getter]
    fn revision(&self) -> u64 {
        self.revision
    }

    #[getter]
    fn cursor_position(&self) -> Option<PyPoint> {
        self.cursor.map(|cursor| PyPoint {
            inner: cursor.position,
        })
    }

    #[getter]
    fn is_cursor_visible(&self) -> bool {
        self.cursor.is_some()
    }

    #[getter]
    fn text(&self) -> String {
        self.grid.text_rows().join("\n")
    }

    #[getter]
    fn ansi(&self) -> String {
        xnano_terminal_cells::ansi(self.grid.buffer())
    }

    fn lines(&self) -> Vec<String> {
        self.grid.text_rows()
    }

    fn to_cell_grid<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyBytes>> {
        let packed = xnano_terminal_cells::pack(self.grid.buffer())
            .map_err(|error| crate::errors::CellGridError::new_err(error.to_string()))?;
        Ok(PyBytes::new(py, &packed))
    }
}

/// A runtime's events as a synchronous and asynchronous iterator.
#[pyclass(name = "EventStream", module = "xnano_core._xnano_core", unsendable)]
pub struct PyEventStream {
    runtime: Py<PyRuntime>,
    pending: Arc<Mutex<VecDeque<Event>>>,
}

#[pymethods]
impl PyEventStream {
    fn __repr__(slf: &Bound<'_, Self>) -> PyResult<String> {
        crate::reprs::described(slf.as_any(), &[])
    }

    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(&self, py: Python<'_>) -> PyResult<PyEvent> {
        loop {
            if let Some(event) = lock(&self.pending).pop_front() {
                return Ok(PyEvent::new(event));
            }
            let runtime = self.runtime.bind(py);
            let (is_closed, is_offscreen) = {
                let borrowed = runtime.borrow();
                (
                    borrowed.shared.is_closed.load(Ordering::SeqCst),
                    borrowed.config.backend == Backend::Offscreen,
                )
            };
            if is_closed {
                return Err(pyo3::exceptions::PyStopIteration::new_err(()));
            }
            let timeout = if is_offscreen { Some(0) } else { None };
            let result = PyRuntime::step(runtime, timeout)?;
            if lock(&self.pending).is_empty()
                && (!result.is_running || (is_offscreen && result.events_processed == 0))
            {
                return Err(pyo3::exceptions::PyStopIteration::new_err(()));
            }
        }
    }

    fn __aiter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __anext__<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        py.import("xnano_core._xnano_core._core_types")?
            .getattr("_next_event")?
            .call1((slf,))
    }

    /// Take a waiting event without driving the runtime.
    fn _poll(&self) -> Option<PyEvent> {
        lock(&self.pending).pop_front().map(PyEvent::new)
    }

    #[getter]
    fn _runtime(&self, py: Python<'_>) -> Py<PyRuntime> {
        self.runtime.clone_ref(py)
    }
}

/// A handle that reaches a runtime from any thread.
#[pyclass(name = "Waker", module = "xnano_core._xnano_core", frozen)]
pub struct PyWaker {
    shared: Arc<RuntimeShared>,
}

#[pymethods]
impl PyWaker {
    fn __repr__(slf: &Bound<'_, Self>) -> PyResult<String> {
        crate::reprs::described(slf.as_any(), &[])
    }

    #[pyo3(signature = (callback, *arguments))]
    fn call_soon(&self, callback: Py<PyAny>, arguments: Py<PyTuple>) {
        self.shared.queue.push_call(QueuedCall {
            function: callback,
            arguments,
        });
    }

    fn wake(&self) {
        self.shared.queue.request_wake();
    }
}

#[pyclass(
    name = "Runtime",
    module = "xnano_core._xnano_core",
    subclass,
    unsendable,
    weakref
)]
pub struct PyRuntime {
    shared: Arc<RuntimeShared>,
    config: Config,
    registry: RefCell<Option<Py<PyAny>>>,
    title: RefCell<Option<String>>,
    mounts: RefCell<Vec<Mount>>,
    known: RefCell<HashMap<u64, Py<PyBuffer>>>,
    updates: RefCell<Vec<UpdateRegistration>>,
    frames: RefCell<Vec<FrameRegistration>>,
    error_handlers: RefCell<Vec<ErrorHandler>>,
    scheduled: RefCell<Vec<Scheduled>>,
    timers: RefCell<HashMap<String, Timer>>,
    tick: RefCell<Tick>,
    streams: RefCell<Vec<Weak<Mutex<VecDeque<Event>>>>>,
    stores: RefCell<Vec<Arc<Store>>>,
    /// Functions that provide the values of named external expressions.
    externals: RefCell<HashMap<String, Py<PyAny>>>,
    /// State changes that watched branches published since the last step.
    pending_state_changes: Arc<Mutex<Vec<Arc<xnano_terminal_state::store::Change>>>>,
    #[cfg(feature = "terminal")]
    session: RefCell<Option<xnano_terminal_runtime::terminal::TerminalSession>>,
    is_open: Cell<bool>,
    opened_by_run: Cell<bool>,
    last_frame: RefCell<Option<Arc<Grid>>>,
    last_cursor: Cell<Option<xnano_terminal_runtime::cursor::CursorPlacement>>,
    frame_revision: Cell<u64>,
    last_rendered_stamp: Cell<u64>,
    /// The global modification stamp read just before the last tree walk that found nothing
    /// new, or 0 when the mounts changed since. The global counter also moves for unmounted
    /// buffers and other canvases, so a moved counter only means "maybe": it makes the walk
    /// run, and the walk decides. An unmoved counter means no buffer anywhere changed.
    quiet_global_stamp: Cell<u64>,
    last_present_seconds: Cell<f64>,
    last_effect_seconds: Cell<f64>,
    revisions_seen: RefCell<HashMap<u64, u64>>,
    has_rendered: Cell<bool>,
    interrupt_stops: Cell<bool>,
}

fn closed_error(action: &str) -> PyErr {
    PyRuntimeError::new_err(format!(
        "cannot {action}: the runtime is closed. Create a new one with Runtime.live() or \
         Runtime.offscreen(width=..., height=...)"
    ))
}

fn milliseconds(value: i64, name: &str) -> PyResult<u64> {
    u64::try_from(value)
        .ok()
        .filter(|value| *value > 0)
        .ok_or_else(|| {
            PyValueError::new_err(format!(
                "{name} must be a positive number of milliseconds, not {value}"
            ))
        })
}

fn seconds(value: f64, name: &str) -> PyResult<f64> {
    if !value.is_finite() || value < 0.0 {
        return Err(PyValueError::new_err(format!(
            "{name} must be a finite number of seconds that is zero or more, not {value}"
        )));
    }
    Ok(value)
}

struct Pending {
    callback: Py<PyAny>,
    target: Py<PyBuffer>,
    calls: Vec<(f64, bool)>,
    elapsed: f64,
}

impl PyRuntime {
    fn check_open(&self, action: &str) -> PyResult<()> {
        if self.shared.is_closed.load(Ordering::SeqCst) {
            return Err(closed_error(action));
        }
        Ok(())
    }

    fn now(&self) -> f64 {
        self.shared.clock.elapsed_seconds()
    }

    /// The time frames are paced by: it keeps running while the clock is paused.
    fn pace_now(&self) -> f64 {
        self.shared.clock.real_seconds()
    }

    fn link_object(slf: &Bound<'_, Self>) -> PyResult<()> {
        let py = slf.py();
        let shared = Arc::clone(&slf.borrow().shared);
        let mut slot = lock(&shared.runtime_object);
        if slot.is_none() {
            *slot = Some(
                py.import("weakref")?
                    .getattr("ref")?
                    .call1((slf,))?
                    .unbind(),
            );
        }
        Ok(())
    }

    /// Every mounted buffer, parents before children.
    fn tree(&self, py: Python<'_>) -> Vec<Py<PyBuffer>> {
        fn visit(py: Python<'_>, buffer: &Py<PyBuffer>, output: &mut Vec<Py<PyBuffer>>) {
            output.push(buffer.clone_ref(py));
            let children: Vec<Py<PyBuffer>> = {
                let bound = buffer.bind(py);
                let surface = bound.as_super().borrow();
                lock(&surface.ext.children)
                    .iter()
                    .map(|child| child.clone_ref(py))
                    .collect()
            };
            for child in &children {
                visit(py, child, output);
            }
        }
        let roots: Vec<Py<PyBuffer>> = self
            .mounts
            .borrow()
            .iter()
            .map(|mount| mount.buffer.clone_ref(py))
            .collect();
        let mut output = Vec::new();
        for root in &roots {
            visit(py, root, &mut output);
        }
        output
    }

    fn core_of(py: Python<'_>, buffer: &Py<PyBuffer>) -> Arc<BufferCore> {
        Arc::clone(&buffer.bind(py).as_super().borrow().core)
    }

    fn entries_of(py: Python<'_>, buffer: &Py<PyBuffer>) -> Vec<Arc<HookEntry>> {
        let bound = buffer.bind(py);
        let surface = bound.as_super().borrow();
        let mut entries: Vec<Arc<HookEntry>> = lock(&surface.ext.hooks)
            .iter()
            .filter(|entry| entry.state.is_active())
            .cloned()
            .collect();
        entries.sort_by_key(|entry| (std::cmp::Reverse(entry.priority()), entry.order));
        entries
    }

    fn make_context<'py>(
        &self,
        slf: &Bound<'py, Self>,
        kind: ContextKind,
        buffer: &Py<PyBuffer>,
        target: Option<Bound<'py, PyAny>>,
        event: Option<&Event>,
        extras: &Bound<'py, PyDict>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let module = py.import("xnano_core._xnano_core._core_types")?;
        let class = match (kind, extras.contains("fixed_step")?) {
            (ContextKind::Event, _) => module.getattr("EventContext")?,
            (ContextKind::Frame, _) => module.getattr("FrameContext")?,
            (ContextKind::Plain, true) => module.getattr("UpdateContext")?,
            (ContextKind::Plain, false) => module.getattr("CoreContext")?,
        };
        let options = PyDict::new(py);
        options.set_item("runtime", slf)?;
        options.set_item("buffer", buffer.bind(py))?;
        options.set_item(
            "target",
            target.unwrap_or_else(|| buffer.bind(py).clone().into_any()),
        )?;
        options.set_item("event", event.map(|event| PyEvent::new(event.clone())))?;
        for (key, value) in extras.iter() {
            if key.extract::<String>()? != "fixed_step" {
                options.set_item(key, value)?;
            } else {
                options.set_item("is_fixed_step", value)?;
            }
        }
        class.call((), Some(&options))
    }

    /// Run one hook if its event, binding and condition match.
    #[allow(clippy::too_many_arguments)]
    fn run_entry<'py>(
        &self,
        slf: &Bound<'py, Self>,
        entry: &Arc<HookEntry>,
        buffer: &Py<PyBuffer>,
        wanted: HookEvent,
        kind: ContextKind,
        event: Option<&Event>,
        extras: &Bound<'py, PyDict>,
    ) -> PyResult<HookRun> {
        let py = slf.py();
        let mut run = HookRun::default();
        if !entry.state.is_active() || !entry.listens_to(wanted) {
            return Ok(run);
        }
        if let Some(binding) = &entry.binding {
            let Some(key) = event.and_then(Event::key) else {
                return Ok(run);
            };
            if key.kind == KeyKind::Release || !binding.matches(key) {
                return Ok(run);
            }
        }
        let core = Self::core_of(py, buffer);
        let target = match entry.region {
            Some(region) => {
                let region = crate::geometry::PyRectangle { inner: region };
                match buffer.bind(py).call_method1("region", (region,)) {
                    Ok(region) => Some(region),
                    Err(_) => return Ok(run),
                }
            }
            None => None,
        };
        if let Some(condition) = &entry.condition {
            let environment = SurfaceEnv {
                core: Arc::clone(&core),
                region: entry.region,
                shared: Some(Arc::clone(&self.shared)),
            };
            let passed = condition
                .evaluate(&environment)
                .map_err(|error| crate::errors::eval_error(&error))?
                .is_truthy()
                .ok_or_else(|| {
                    PyTypeError::new_err("a hook condition must be a Predicate such as Width > 40")
                })?;
            if !passed {
                return Ok(run);
            }
        }
        let context = self.make_context(slf, kind, buffer, target, event, extras)?;
        run.ran = true;
        let outcome = entry.callback.bind(py).call1((&context,));
        if entry.once {
            entry.state.cancel(py);
        }
        match outcome {
            Ok(_) => {}
            Err(error) => {
                let signals = py.import("xnano_core._xnano_core._core_types")?;
                let value = error.value(py);
                if value.is_instance(&signals.getattr("Skip")?)? {
                    run.ran = true;
                } else if value.is_instance(&signals.getattr("Invalidate")?)? {
                    self.shared.request_frame();
                } else if value.is_instance(&signals.getattr("Stop")?)? {
                    self.shared.is_running.store(false, Ordering::SeqCst);
                } else if value.is_instance(&signals.getattr("Propagate")?)? {
                    run.should_propagate = true;
                } else {
                    return Err(error);
                }
            }
        }
        run.is_consumed = context
            .getattr("is_consumed")
            .and_then(|value| value.extract())
            .unwrap_or(false);
        Ok(run)
    }

    /// Run the matching hooks of every mounted buffer in priority order.
    fn broadcast<'py>(
        &self,
        slf: &Bound<'py, Self>,
        wanted: HookEvent,
        kind: ContextKind,
        event: Option<&Event>,
        extras: &Bound<'py, PyDict>,
    ) -> PyResult<usize> {
        let py = slf.py();
        let mut work: Vec<(Arc<HookEntry>, Py<PyBuffer>)> = Vec::new();
        for buffer in self.tree(py) {
            for entry in Self::entries_of(py, &buffer) {
                if entry.listens_to(wanted) {
                    work.push((entry, buffer.clone_ref(py)));
                }
            }
        }
        work.sort_by_key(|(entry, _)| (std::cmp::Reverse(entry.priority()), entry.order));
        let mut count = 0;
        for (entry, buffer) in work {
            if self
                .run_entry(slf, &entry, &buffer, wanted, kind, event, extras)?
                .ran
            {
                count += 1;
            }
        }
        Ok(count)
    }

    /// Fire lifecycle hooks of one buffer.
    fn fire_buffer<'py>(
        &self,
        slf: &Bound<'py, Self>,
        buffer: &Py<PyBuffer>,
        wanted: HookEvent,
        extras: &Bound<'py, PyDict>,
    ) -> PyResult<()> {
        let py = slf.py();
        for entry in Self::entries_of(py, buffer) {
            self.run_entry(
                slf,
                &entry,
                buffer,
                wanted,
                ContextKind::Plain,
                None,
                extras,
            )?;
        }
        Ok(())
    }

    /// Deliver an input event along `start` and its ancestors until something handles it.
    fn deliver_chain(
        &self,
        slf: &Bound<'_, Self>,
        start: &Py<PyBuffer>,
        wanted: HookEvent,
        event: &Event,
        by_id: &HashMap<u64, Py<PyBuffer>>,
    ) -> PyResult<bool> {
        let py = slf.py();
        let mut current = Some(start.clone_ref(py));
        while let Some(buffer) = current {
            let core = Self::core_of(py, &buffer);
            let extras = PyDict::new(py);
            if let Some(mouse) = event.mouse() {
                let origin = absolute_origin(&core);
                extras.set_item(
                    "local_pointer",
                    (mouse.column - origin.0, mouse.row - origin.1),
                )?;
            }
            let mut ran_any = false;
            let mut should_propagate = false;
            for entry in Self::entries_of(py, &buffer) {
                let run = self.run_entry(
                    slf,
                    &entry,
                    &buffer,
                    wanted,
                    ContextKind::Event,
                    Some(event),
                    &extras,
                )?;
                ran_any |= run.ran;
                should_propagate |= run.should_propagate;
                if run.is_consumed {
                    return Ok(true);
                }
            }
            if ran_any && !should_propagate {
                return Ok(true);
            }
            current = core
                .parent()
                .and_then(|parent| by_id.get(&parent.id).map(|object| object.clone_ref(py)));
        }
        Ok(false)
    }

    fn modal_root(&self) -> Option<Arc<BufferCore>> {
        lock(&self.shared.router)
            .scopes
            .iter()
            .rev()
            .find(|scope| scope.is_modal && scope.is_active.load(Ordering::SeqCst))
            .map(|scope| Arc::clone(&scope.target))
    }

    fn is_inside(core: &Arc<BufferCore>, root: &Arc<BufferCore>) -> bool {
        let mut current = Some(Arc::clone(core));
        while let Some(node) = current {
            if Arc::ptr_eq(&node, root) {
                return true;
            }
            current = node.parent();
        }
        false
    }

    fn route_input(&self, slf: &Bound<'_, Self>, event: &Event) -> PyResult<()> {
        let py = slf.py();
        let wanted = HookEvent::Event(event.kind);
        let tree = self.tree(py);
        let by_id: HashMap<u64, Py<PyBuffer>> = tree
            .iter()
            .map(|buffer| (Self::core_of(py, buffer).id, buffer.clone_ref(py)))
            .collect();
        let modal = self.modal_root();
        let allowed = |core: &Arc<BufferCore>| {
            modal
                .as_ref()
                .is_none_or(|root| Self::is_inside(core, root))
        };
        match event.kind {
            EventKind::Mouse => {
                let Some(mouse) = event.mouse().copied() else {
                    return Ok(());
                };
                let mut candidates: Vec<Py<PyBuffer>> = Vec::new();
                let captured = lock(&self.shared.router).captured_pointer;
                if let Some(id) = captured
                    && let Some(buffer) = by_id.get(&id)
                {
                    candidates.push(buffer.clone_ref(py));
                } else {
                    for area in hit_areas_at(&self.shared, mouse.column, mouse.row) {
                        let target = Arc::clone(&lock(&area).target);
                        if allowed(&target)
                            && let Some(buffer) = by_id.get(&target.id)
                        {
                            candidates.push(buffer.clone_ref(py));
                        }
                    }
                    let roots: Vec<Py<PyBuffer>> = self
                        .mounts
                        .borrow()
                        .iter()
                        .map(|mount| mount.buffer.clone_ref(py))
                        .collect();
                    for root in roots.iter().rev() {
                        let root_core = Self::core_of(py, root);
                        for core in buffers_at(&root_core, mouse.column, mouse.row) {
                            if allowed(&core)
                                && let Some(buffer) = by_id.get(&core.id)
                            {
                                candidates.push(buffer.clone_ref(py));
                            }
                        }
                    }
                }
                if mouse.kind == MouseKind::Press {
                    for candidate in &candidates {
                        let core = Self::core_of(py, candidate);
                        let mut current = Some(core);
                        let mut focused = false;
                        while let Some(node) = current {
                            if focus_buffer(&self.shared, &node) {
                                focused = true;
                                break;
                            }
                            current = node.parent();
                        }
                        if focused {
                            break;
                        }
                    }
                }
                for candidate in &candidates {
                    if self.deliver_chain(slf, candidate, wanted, event, &by_id)? {
                        break;
                    }
                }
            }
            _ => {
                let focused = lock(&self.shared.router).focused;
                if let Some(id) = focused
                    && let Some(buffer) = by_id.get(&id)
                    && allowed(&Self::core_of(py, buffer))
                {
                    self.deliver_chain(slf, buffer, wanted, event, &by_id)?;
                } else {
                    for buffer in tree.iter().rev() {
                        if allowed(&Self::core_of(py, buffer)) {
                            let extras = PyDict::new(py);
                            let mut consumed = false;
                            for entry in Self::entries_of(py, buffer) {
                                let run = self.run_entry(
                                    slf,
                                    &entry,
                                    buffer,
                                    wanted,
                                    ContextKind::Event,
                                    Some(event),
                                    &extras,
                                )?;
                                if run.is_consumed {
                                    consumed = true;
                                    break;
                                }
                            }
                            if consumed {
                                break;
                            }
                        }
                    }
                }
            }
        }
        Ok(())
    }

    /// Process one event: tap streams, update built-in state, run hooks.
    fn process_event(&self, slf: &Bound<'_, Self>, mut event: Event) -> PyResult<()> {
        let py = slf.py();
        if event.timestamp_seconds == 0.0 {
            event.timestamp_seconds = self.now();
        }
        self.streams
            .borrow_mut()
            .retain(|stream| stream.strong_count() > 0);
        for stream in self.streams.borrow().iter() {
            if let Some(stream) = stream.upgrade() {
                lock(&stream).push_back(event.clone());
            }
        }
        match &event.payload {
            EventPayload::Key(key) => {
                if self.interrupt_stops.get()
                    && key.key == "c"
                    && key
                        .modifiers
                        .contains(xnano_terminal_runtime::event::KeyModifiers::CONTROL)
                    && key.kind != KeyKind::Release
                {
                    self.shared.is_running.store(false, Ordering::SeqCst);
                    return Ok(());
                }
                let now = self.now();
                let mut input = lock(&self.shared.input);
                input.record_key(key);
                match key.kind {
                    KeyKind::Release => {
                        input.pressed.remove(&key.key);
                        input.estimated.remove(&key.key);
                    }
                    _ => {
                        if input.held_keys_available {
                            input.pressed.insert(key.key.clone());
                        } else if let Some(timeout) = input.estimate_timeout {
                            // Only the newest key held repeats, so a different key ends the
                            // estimate of the key before it.
                            input.estimated.clear();
                            input.estimated.insert(key.key.clone(), now + timeout);
                        }
                    }
                }
            }
            EventPayload::Mouse(mouse) => lock(&self.shared.input).record_mouse(mouse),
            EventPayload::Paste(text) => lock(&self.shared.input).record_paste(text),
            EventPayload::Size(size) => {
                #[allow(unused_mut)]
                let mut resolved = *size;
                // An inline region keeps its own height, so a hook that hears the resize sees
                // the size of the region and not the size of the window.
                #[cfg(feature = "terminal")]
                if let Some(session) = self.session.borrow_mut().as_mut()
                    && session.is_inline()
                    && let Ok(viewport) = session.viewport()
                {
                    resolved = viewport;
                }
                lock(&self.shared.device).size = resolved;
                self.shared.request_frame();
            }
            _ => {}
        }
        match event.kind {
            EventKind::FocusGained => lock(&self.shared.device).is_focused = true,
            EventKind::FocusLost => {
                lock(&self.shared.device).is_focused = false;
                let mut input = lock(&self.shared.input);
                input.pressed.clear();
                input.estimated.clear();
                drop(input);
                lock(&self.shared.router).captured_pointer = None;
            }
            _ => {}
        }
        if event.kind.is_input() {
            let routed = self.route_input(slf, &event);
            if event
                .mouse()
                .is_some_and(|mouse| mouse.kind == MouseKind::Release)
            {
                lock(&self.shared.router).captured_pointer = None;
            }
            return routed;
        }
        let extras = PyDict::new(py);
        let handled = self.broadcast(
            slf,
            HookEvent::Event(event.kind),
            ContextKind::Plain,
            Some(&event),
            &extras,
        )?;
        if event.kind == EventKind::ExitRequested && handled == 0 {
            self.shared.is_running.store(false, Ordering::SeqCst);
        }
        Ok(())
    }

    /// Bring the set of mounted buffers in line with the trees: fire mount and unmount hooks.
    fn sync_lifecycle(&self, slf: &Bound<'_, Self>) -> PyResult<()> {
        let py = slf.py();
        let tree = self.tree(py);
        let current: HashMap<u64, Py<PyBuffer>> = tree
            .iter()
            .map(|buffer| (Self::core_of(py, buffer).id, buffer.clone_ref(py)))
            .collect();
        let added: Vec<Py<PyBuffer>> = tree
            .iter()
            .filter(|buffer| {
                !self
                    .known
                    .borrow()
                    .contains_key(&Self::core_of(py, buffer).id)
            })
            .map(|buffer| buffer.clone_ref(py))
            .collect();
        let removed: Vec<(u64, Py<PyBuffer>)> = self
            .known
            .borrow()
            .iter()
            .filter(|(id, _)| !current.contains_key(id))
            .map(|(id, buffer)| (*id, buffer.clone_ref(py)))
            .collect();
        for buffer in &added {
            let core = Self::core_of(py, buffer);
            core.lock().is_mounted = true;
            {
                let bound = buffer.bind(py);
                let ext = Arc::clone(&bound.as_super().borrow().ext);
                *lock(&ext.runtime) = Some(Arc::downgrade(&self.shared));
            }
            self.known
                .borrow_mut()
                .insert(core.id, buffer.clone_ref(py));
            self.revisions_seen
                .borrow_mut()
                .insert(core.id, core.lock().revision);
            self.fire_buffer(slf, buffer, HookEvent::Mount, &PyDict::new(py))?;
        }
        for (id, buffer) in removed {
            self.fire_buffer(slf, &buffer, HookEvent::Unmount, &PyDict::new(py))?;
            self.release_buffer(py, &buffer, id);
        }
        Ok(())
    }

    fn release_buffer(&self, py: Python<'_>, buffer: &Py<PyBuffer>, id: u64) {
        self.known.borrow_mut().remove(&id);
        self.revisions_seen.borrow_mut().remove(&id);
        let bound = buffer.bind(py);
        let surface = bound.as_super().borrow();
        surface.core.lock().is_mounted = false;
        *lock(&surface.ext.runtime) = None;
        {
            let mut router = lock(&self.shared.router);
            if router.focused == Some(id) {
                router.focused = None;
            }
            if router.captured_pointer == Some(id) {
                router.captured_pointer = None;
            }
            router.hit_areas.retain(|area| lock(area).target.id != id);
            router.scopes.retain(|scope| scope.target.id != id);
        }
        let mut motion = lock(&self.shared.motion);
        motion.effects.retain(|effect| lock(effect).target.id != id);
        motion
            .animations
            .retain(|animation| animation.target.id != id);
        drop(motion);
        let adopted: Vec<Arc<HookEntry>> = lock(&surface.ext.hooks).iter().cloned().collect();
        for entry in adopted {
            if entry.events.contains(&HookEvent::Mount) {
                continue;
            }
            // Watches and other adopted registrations end with the mount.
            if entry
                .callback
                .bind(py)
                .hasattr("__xnano_adopted__")
                .unwrap_or(false)
            {
                entry.state.cancel(py);
            }
        }
    }

    fn emit_due(&self) {
        let now = self.now();
        {
            let mut tick = self.tick.borrow_mut();
            if let Some(interval) = tick.interval
                && now >= tick.next
            {
                self.shared
                    .queue
                    .push_event(Event::new(EventKind::Tick, EventPayload::None));
                tick.next = now + interval;
            }
        }
        let mut finished = Vec::new();
        for (key, timer) in self.timers.borrow_mut().iter_mut() {
            if now >= timer.next {
                self.shared.queue.push_event(Event::new(
                    EventKind::Timer,
                    EventPayload::Timer(key.clone()),
                ));
                if timer.should_repeat {
                    timer.next = now + timer.interval;
                } else {
                    finished.push(key.clone());
                }
            }
        }
        for key in finished {
            self.timers.borrow_mut().remove(&key);
        }
    }

    fn run_scheduled(&self, py: Python<'_>) -> PyResult<usize> {
        let mut due: Vec<Py<PyAny>> = Vec::new();
        {
            let mut scheduled = self.scheduled.borrow_mut();
            scheduled.retain(|call| !call.state.is_cancelled.load(Ordering::SeqCst));
            let mut remaining = Vec::new();
            for mut call in scheduled.drain(..) {
                let elapsed = call.clock.elapsed(&self.shared);
                if elapsed >= call.due {
                    due.push(call.callback.clone_ref(py));
                    if let Some(interval) = call.interval {
                        call.due = (call.due + interval).max(elapsed + f64::EPSILON);
                        remaining.push(call);
                    }
                } else {
                    remaining.push(call);
                }
            }
            *scheduled = remaining;
        }
        let count = due.len();
        for callback in due {
            callback.call0(py)?;
        }
        Ok(count)
    }

    fn run_updates(&self, slf: &Bound<'_, Self>) -> PyResult<usize> {
        let py = slf.py();
        let mut pending: Vec<Pending> = Vec::new();
        {
            let mut updates = self.updates.borrow_mut();
            updates.retain(|update| !update.state.is_cancelled.load(Ordering::SeqCst));
            for update in updates.iter_mut() {
                if !update.state.is_active() || !Self::core_of(py, &update.target).lock().is_mounted
                {
                    update.last_elapsed = update.clock.elapsed(&self.shared);
                    continue;
                }
                let elapsed = update.clock.elapsed(&self.shared);
                let delta = (elapsed - update.last_elapsed).max(0.0);
                update.last_elapsed = elapsed;
                if delta <= 0.0 {
                    continue;
                }
                let mut calls = Vec::new();
                match update.fixed_step {
                    None => calls.push((
                        update.maximum_delta.map_or(delta, |limit| delta.min(limit)),
                        false,
                    )),
                    Some(step) => {
                        update.accumulator += delta;
                        let mut steps = 0;
                        while update.accumulator + 1e-9 >= step
                            && steps < update.maximum_catch_up_steps
                        {
                            calls.push((step, true));
                            update.accumulator = (update.accumulator - step).max(0.0);
                            steps += 1;
                        }
                        if update.accumulator + 1e-9 >= step && !update.should_retain_overflow {
                            update.accumulator = 0.0;
                        }
                    }
                }
                pending.push(Pending {
                    callback: update.callback.clone_ref(py),
                    target: update.target.clone_ref(py),
                    calls,
                    elapsed,
                });
            }
        }
        let mut count = 0;
        for entry in pending {
            for (delta, is_fixed) in entry.calls {
                let extras = PyDict::new(py);
                extras.set_item("elapsed_seconds", entry.elapsed)?;
                extras.set_item("delta_seconds", delta)?;
                extras.set_item("fixed_step", is_fixed)?;
                let context =
                    self.make_context(slf, ContextKind::Plain, &entry.target, None, None, &extras)?;
                entry.callback.bind(py).call1((context,))?;
                count += 1;
            }
        }
        Ok(count)
    }

    fn drain_stores(&self) -> PyResult<()> {
        let stores: Vec<Arc<Store>> = self.stores.borrow().clone();
        for store in stores {
            store.drain(1024).map_err(crate::state::listener_failure)?;
        }
        Ok(())
    }

    /// Run the `state_change` hooks once for everything watched state published.
    fn fire_state_changes(&self, slf: &Bound<'_, Self>) -> PyResult<()> {
        let py = slf.py();
        let latest = lock(&self.pending_state_changes).drain(..).next_back();
        let Some(change) = latest else {
            return Ok(());
        };
        let extras = PyDict::new(py);
        extras.set_item(
            "state_change",
            crate::state::PyStateChange { inner: change },
        )?;
        for buffer in self.tree(py) {
            self.fire_buffer(slf, &buffer, HookEvent::StateChange, &extras)?;
        }
        Ok(())
    }

    fn fire_changes(&self, slf: &Bound<'_, Self>) -> PyResult<()> {
        let py = slf.py();
        let tree = self.tree(py);
        let mut changed = Vec::new();
        for buffer in &tree {
            let core = Self::core_of(py, buffer);
            let revision = core.lock().revision;
            let mut seen = self.revisions_seen.borrow_mut();
            let previous = seen.insert(core.id, revision);
            if previous.is_some_and(|previous| previous != revision) {
                changed.push(buffer.clone_ref(py));
            }
        }
        for buffer in changed {
            self.fire_buffer(slf, &buffer, HookEvent::Change, &PyDict::new(py))?;
        }
        Ok(())
    }

    fn needs_frame_now(&self, py: Python<'_>) -> bool {
        if self.shared.is_frame_requested.load(Ordering::SeqCst) || !self.has_rendered.get() {
            return true;
        }
        {
            let motion = lock(&self.shared.motion);
            if motion.effects.iter().any(|effect| !lock(effect).is_paused) {
                return true;
            }
            let now = ((self.now() * 1000.0) as i64).max(0);
            if motion.animations.iter().any(|animation| {
                let elapsed = now - animation.start_milliseconds;
                animation
                    .animation
                    .milliseconds_until_next_frame(elapsed)
                    .is_some()
                    && animation.shown_index != Some(animation.animation.frame_index_at(elapsed))
            }) {
                return true;
            }
        }
        // Read before walking: a change made during the walk moves the counter past this
        // value, so the next check walks again instead of missing it.
        let global = latest_modification_stamp();
        if global == self.quiet_global_stamp.get() {
            return false;
        }
        let mut stamp = 0;
        for mount in self.mounts.borrow().iter() {
            stamp = stamp.max(tree_modified(&Self::core_of(py, &mount.buffer)));
        }
        let is_changed = stamp > self.last_rendered_stamp.get();
        if !is_changed {
            self.quiet_global_stamp.set(global);
        }
        is_changed
    }

    /// Seconds until a frame that is wanted falls due, on a real clock.
    ///
    /// `None` when no frame is wanted, when it is due now, and on a manual clock, where
    /// frames are never paced.
    fn frame_wait(&self, py: Python<'_>) -> Option<f64> {
        if self.shared.clock.source() != ClockSource::Monotonic
            || !self.has_rendered.get()
            || !self.needs_frame_now(py)
        {
            return None;
        }
        let frame = self.config.frame_interval_milliseconds.get() as f64 / 1000.0;
        let since = self.pace_now() - self.last_present_seconds.get();
        (since < frame).then_some(frame - since)
    }

    /// Seconds until the next time-based work, on the runtime clock.
    fn next_deadline(&self, py: Python<'_>) -> Option<f64> {
        let now = self.now();
        let mut best: Option<f64> = None;
        let mut consider = |seconds: f64| {
            best = Some(best.map_or(seconds, |current| current.min(seconds)));
        };
        if let Some(interval) = self.tick.borrow().interval {
            consider((self.tick.borrow().next - now).max(0.0));
            let _ = interval;
        }
        for timer in self.timers.borrow().values() {
            consider((timer.next - now).max(0.0));
        }
        for call in self.scheduled.borrow().iter() {
            if call.state.is_cancelled.load(Ordering::SeqCst) {
                continue;
            }
            if let Some(seconds) = call.clock.seconds_until(&self.shared, call.due) {
                consider(seconds);
            }
        }
        let frame = self.config.frame_interval_milliseconds.get() as f64 / 1000.0;
        {
            let motion = lock(&self.shared.motion);
            if motion.effects.iter().any(|effect| !lock(effect).is_paused) {
                consider(frame);
            }
            let now_ms = ((now * 1000.0) as i64).max(0);
            for animation in &motion.animations {
                let elapsed = now_ms - animation.start_milliseconds;
                if let Some(wait) = animation.animation.milliseconds_until_next_frame(elapsed) {
                    consider(wait as f64 / 1000.0);
                }
            }
        }
        if self
            .updates
            .borrow()
            .iter()
            .any(|update| update.state.is_active())
        {
            consider(frame);
        }
        if self.shared.clock.source() == ClockSource::Monotonic && self.needs_frame_now(py) {
            let since = self.pace_now() - self.last_present_seconds.get();
            consider((frame - since).max(0.0));
        }
        best
    }
}

#[pymethods]
impl PyRuntime {
    #[new]
    #[pyo3(signature = (*, backend = None, width = 80, height = 24, tick_interval_milliseconds = None,
        frame_interval_milliseconds = 16, inline_height = None, inline_width = None,
        should_handle_exit_signals = true, options = None, clock = None, registry = None))]
    fn new(
        backend: Option<&str>,
        width: i32,
        height: i32,
        tick_interval_milliseconds: Option<i64>,
        frame_interval_milliseconds: i64,
        inline_height: Option<u16>,
        inline_width: Option<u16>,
        should_handle_exit_signals: bool,
        options: Option<PyTerminalOptions>,
        clock: Option<&PyClock>,
        registry: Option<Py<PyAny>>,
    ) -> PyResult<Self> {
        let backend = match backend {
            Some("terminal") => Backend::Terminal,
            Some("offscreen") => Backend::Offscreen,
            _ => {
                return Err(PyTypeError::new_err(
                    "create a runtime with Runtime.live() or Runtime.offscreen(width=..., height=...)",
                ));
            }
        };
        #[cfg(not(feature = "terminal"))]
        if backend == Backend::Terminal {
            return Err(PyRuntimeError::new_err(
                "this build of xnano has no live terminal support; use Runtime.offscreen(...) instead",
            ));
        }
        let frame_interval =
            milliseconds(frame_interval_milliseconds, "frame_interval_milliseconds")?;
        let tick = tick_interval_milliseconds
            .map(|value| milliseconds(value, "tick_interval_milliseconds"))
            .transpose()?;
        let (columns, rows) = xnano_terminal_runtime::buffer::check_size(width, height)
            .map_err(PyValueError::new_err)?;
        let clock = match (clock, backend) {
            (Some(clock), _) => Arc::clone(&clock.inner),
            (None, Backend::Offscreen) => Clock::manual(0.0),
            (None, Backend::Terminal) => Clock::monotonic(),
        };
        let shared = Arc::new(RuntimeShared {
            clock,
            device: Mutex::new(DeviceData {
                backend,
                size: Size::new(i32::from(columns), i32::from(rows)),
                window_size_in_pixels: None,
                terminal: if backend == Backend::Terminal {
                    TerminalInfo {
                        is_terminal: false,
                        is_live_terminal_available: true,
                        color_profile: "no_terminal",
                        graphics_protocol: "half_blocks",
                        cell_size_in_pixels: None,
                        synchronized_output: Status::Unknown,
                    }
                } else {
                    TerminalInfo {
                        is_terminal: false,
                        is_live_terminal_available: cfg!(feature = "terminal"),
                        color_profile: "no_terminal",
                        graphics_protocol: "half_blocks",
                        cell_size_in_pixels: None,
                        synchronized_output: Status::Unknown,
                    }
                },
                keyboard: KeyboardInfo {
                    enhancement: Status::Unsupported,
                    unavailable_reason: Some(if backend == Backend::Offscreen {
                        "an offscreen runtime has no keyboard".to_owned()
                    } else {
                        "the terminal has not been queried yet".to_owned()
                    }),
                },
                modes: DeviceModes::default(),
                is_focused: backend == Backend::Offscreen,
                is_inline: inline_height.is_some(),
            }),
            input: Mutex::new(InputData::default()),
            router: Mutex::new(RouterData::default()),
            cursor: Mutex::new(crate::cursor::CursorData::default()),
            queue: EventQueue::default(),
            motion: Mutex::new(Motion::default()),
            metrics: Mutex::new(Metrics::default()),
            is_running: AtomicBool::new(false),
            is_closed: AtomicBool::new(false),
            is_frame_requested: AtomicBool::new(true),
            revision: AtomicU64::new(0),
            runtime_object: Mutex::new(None),
        });
        let interrupt_stops = options
            .as_ref()
            .is_some_and(|options| options.input.interrupt == "stop");
        Ok(Self {
            shared,
            config: Config {
                backend,
                frame_interval_milliseconds: Cell::new(frame_interval),
                inline_height: Cell::new(inline_height),
                inline_width: Cell::new(inline_width),
                should_handle_exit_signals,
                options,
            },
            registry: RefCell::new(registry),
            title: RefCell::default(),
            mounts: RefCell::default(),
            known: RefCell::default(),
            updates: RefCell::default(),
            frames: RefCell::default(),
            error_handlers: RefCell::default(),
            scheduled: RefCell::default(),
            timers: RefCell::default(),
            tick: RefCell::new(Tick {
                interval: tick.map(|value| value as f64 / 1000.0),
                next: tick.map_or(0.0, |value| value as f64 / 1000.0),
            }),
            streams: RefCell::default(),
            stores: RefCell::default(),
            externals: RefCell::default(),
            pending_state_changes: Arc::default(),
            #[cfg(feature = "terminal")]
            session: RefCell::new(None),
            is_open: Cell::new(false),
            opened_by_run: Cell::new(false),
            last_frame: RefCell::new(None),
            last_cursor: Cell::new(None),
            frame_revision: Cell::new(0),
            last_rendered_stamp: Cell::new(0),
            quiet_global_stamp: Cell::new(0),
            last_present_seconds: Cell::new(-1.0),
            last_effect_seconds: Cell::new(0.0),
            revisions_seen: RefCell::default(),
            has_rendered: Cell::new(false),
            interrupt_stops: Cell::new(interrupt_stops),
        })
    }

    #[classmethod]
    #[pyo3(signature = (*, tick_interval_milliseconds = None, frame_interval_milliseconds = 16,
        inline_height = None, inline_width = None, should_handle_exit_signals = true, options = None,
        clock = None, registry = None))]
    fn live(
        cls: &Bound<'_, PyType>,
        tick_interval_milliseconds: Option<i64>,
        frame_interval_milliseconds: i64,
        inline_height: Option<u16>,
        inline_width: Option<u16>,
        should_handle_exit_signals: bool,
        options: Option<PyTerminalOptions>,
        clock: Option<Py<PyClock>>,
        registry: Option<Py<PyAny>>,
    ) -> PyResult<Py<PyAny>> {
        let py = cls.py();
        let keywords = PyDict::new(py);
        keywords.set_item("backend", "terminal")?;
        keywords.set_item("tick_interval_milliseconds", tick_interval_milliseconds)?;
        keywords.set_item("frame_interval_milliseconds", frame_interval_milliseconds)?;
        keywords.set_item("inline_height", inline_height)?;
        keywords.set_item("inline_width", inline_width)?;
        keywords.set_item("should_handle_exit_signals", should_handle_exit_signals)?;
        keywords.set_item(
            "options",
            options.map(|options| Bound::new(py, options)).transpose()?,
        )?;
        keywords.set_item("clock", clock)?;
        keywords.set_item("registry", registry)?;
        Ok(cls.call((), Some(&keywords))?.unbind())
    }

    #[classmethod]
    #[pyo3(signature = (*, width, height, tick_interval_milliseconds = None, frame_interval_milliseconds = 16,
        clock = None, registry = None))]
    fn offscreen(
        cls: &Bound<'_, PyType>,
        width: i32,
        height: i32,
        tick_interval_milliseconds: Option<i64>,
        frame_interval_milliseconds: i64,
        clock: Option<Py<PyClock>>,
        registry: Option<Py<PyAny>>,
    ) -> PyResult<Py<PyAny>> {
        let py = cls.py();
        let keywords = PyDict::new(py);
        keywords.set_item("backend", "offscreen")?;
        keywords.set_item("width", width)?;
        keywords.set_item("height", height)?;
        keywords.set_item("tick_interval_milliseconds", tick_interval_milliseconds)?;
        keywords.set_item("frame_interval_milliseconds", frame_interval_milliseconds)?;
        keywords.set_item("clock", clock)?;
        keywords.set_item("registry", registry)?;
        Ok(cls.call((), Some(&keywords))?.unbind())
    }

    #[getter]
    fn cursor(&self) -> crate::cursor::PyCursor {
        crate::cursor::PyCursor {
            shared: Arc::clone(&self.shared),
        }
    }

    #[getter]
    fn clock(&self) -> PyClock {
        PyClock {
            inner: Arc::clone(&self.shared.clock),
        }
    }

    #[getter]
    fn device(&self) -> PyDevice {
        PyDevice {
            shared: Arc::clone(&self.shared),
        }
    }

    #[getter]
    fn input(&self) -> PyInputState {
        PyInputState {
            shared: Arc::clone(&self.shared),
        }
    }

    #[getter]
    fn router(&self) -> PyInputRouter {
        PyInputRouter {
            shared: Arc::clone(&self.shared),
        }
    }

    #[getter]
    fn registry<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        if let Some(registry) = self.registry.borrow().as_ref() {
            return Ok(registry.bind(py).clone());
        }
        // A runtime owns a private copy, so installing an extension never changes the default.
        let copy = py
            .import("xnano_core._xnano_core._core_types")?
            .getattr("default_registry")?
            .call0()?
            .call_method0("copy")?;
        *self.registry.borrow_mut() = Some(copy.clone().unbind());
        Ok(copy)
    }

    /// The effects running on this runtime.
    #[getter]
    fn effects(&self) -> crate::effects::PyEffectManager {
        crate::effects::PyEffectManager {
            shared: Arc::clone(&self.shared),
        }
    }

    #[getter]
    fn frame_metrics(&self) -> PyFrameMetrics {
        let metrics = lock(&self.shared.metrics);
        PyFrameMetrics {
            frames: metrics.frames,
            last_microseconds: metrics.last_microseconds,
            average_microseconds: if metrics.frames == 0 {
                0
            } else {
                (metrics.total_microseconds / u128::from(metrics.frames)) as u64
            },
        }
    }

    #[getter]
    fn is_running(&self) -> bool {
        self.shared.is_running.load(Ordering::SeqCst)
    }

    #[getter]
    fn is_closed(&self) -> bool {
        self.shared.is_closed.load(Ordering::SeqCst)
    }

    #[getter]
    fn buffers<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        let roots: Vec<Py<PyBuffer>> = self
            .mounts
            .borrow()
            .iter()
            .map(|mount| mount.buffer.clone_ref(py))
            .collect();
        PyTuple::new(py, roots)
    }

    #[getter]
    fn needs_frame(&self, py: Python<'_>) -> bool {
        self.needs_frame_now(py)
    }

    #[pyo3(signature = (buffer, *, key = None, geometry = "explicit"))]
    fn mount<'py>(
        slf: &Bound<'py, Self>,
        buffer: &Bound<'py, PyBuffer>,
        key: Option<String>,
        geometry: &str,
    ) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        Self::link_object(slf)?;
        let runtime = slf.borrow();
        runtime.check_open("mount a buffer")?;
        let geometry = Geometry::from_name(geometry).ok_or_else(|| {
            PyValueError::new_err(format!(
                "\"{geometry}\" is not a geometry mode; use \"inherit\" or \"explicit\""
            ))
        })?;
        let core = Arc::clone(&buffer.as_super().borrow().core);
        {
            let state = core.lock();
            if state.is_mounted
                || runtime
                    .mounts
                    .borrow()
                    .iter()
                    .any(|mount| mount.buffer.is(buffer))
            {
                return Err(PyValueError::new_err(
                    "the buffer is already mounted; unmount it first, or mount a copy with buffer.copy()",
                ));
            }
            if state.parent.upgrade().is_some() {
                return Err(PyValueError::new_err(
                    "the buffer is attached to a parent; mount the parent, or detach the buffer first",
                ));
            }
        }
        if let Some(key) = &key
            && runtime
                .mounts
                .borrow()
                .iter()
                .any(|mount| mount.key.as_ref() == Some(key))
        {
            return Err(PyValueError::new_err(format!(
                "a buffer is already mounted with the key \"{key}\"; choose another key"
            )));
        }
        runtime.quiet_global_stamp.set(0);
        runtime.mounts.borrow_mut().push(Mount {
            buffer: buffer.clone().unbind(),
            key,
            geometry,
        });
        if geometry == Geometry::Inherit {
            let size = runtime.shared.device_size();
            core.move_to(0, 0);
            core.resize(size.width, size.height)
                .map_err(PyValueError::new_err)?;
        }
        runtime.shared.request_frame();
        drop(runtime);
        slf.borrow().sync_lifecycle(slf)?;
        let context = py
            .import("xnano_core._xnano_core._core_types")?
            .getattr("CoreContext")?;
        let options = PyDict::new(py);
        options.set_item("runtime", slf)?;
        options.set_item("buffer", buffer)?;
        options.set_item("target", buffer)?;
        context.call((), Some(&options))
    }

    fn unmount(slf: &Bound<'_, Self>, buffer: &Bound<'_, PyBuffer>) -> PyResult<()> {
        let py = slf.py();
        let runtime = slf.borrow();
        let position = runtime
            .mounts
            .borrow()
            .iter()
            .position(|mount| mount.buffer.is(buffer));
        let Some(position) = position else {
            return Err(PyValueError::new_err(
                "the buffer is not mounted on this runtime",
            ));
        };
        let doomed: Vec<Py<PyBuffer>> = {
            let single = runtime.mounts.borrow()[position].buffer.clone_ref(py);
            let saved = std::mem::take(&mut *runtime.mounts.borrow_mut());
            *runtime.mounts.borrow_mut() = vec![Mount {
                buffer: single,
                key: None,
                geometry: Geometry::Explicit,
            }];
            let tree = runtime.tree(py);
            *runtime.mounts.borrow_mut() = saved;
            runtime.quiet_global_stamp.set(0);
            tree
        };
        for item in &doomed {
            runtime.fire_buffer(slf, item, HookEvent::Unmount, &PyDict::new(py))?;
        }
        runtime.quiet_global_stamp.set(0);
        runtime.mounts.borrow_mut().remove(position);
        for item in &doomed {
            let id = Self::core_of(py, item).id;
            runtime.release_buffer(py, item, id);
        }
        runtime.shared.request_frame();
        Ok(())
    }

    fn dispatch(slf: &Bound<'_, Self>, event: &PyEvent) -> PyResult<()> {
        let runtime = slf.borrow();
        runtime.check_open("dispatch an event")?;
        runtime.process_event(slf, event.inner.clone())
    }

    fn inject(&self, event: &PyEvent) -> PyResult<()> {
        self.check_open("inject an event")?;
        let mut event = event.inner.clone();
        event.timestamp_seconds = self.now();
        self.shared.queue.push_event(event);
        Ok(())
    }

    fn events(slf: &Bound<'_, Self>) -> PyEventStream {
        let pending = Arc::new(Mutex::new(VecDeque::new()));
        slf.borrow()
            .streams
            .borrow_mut()
            .push(Arc::downgrade(&pending));
        PyEventStream {
            runtime: slf.clone().unbind(),
            pending,
        }
    }

    fn waker(&self) -> PyWaker {
        PyWaker {
            shared: Arc::clone(&self.shared),
        }
    }

    #[pyo3(signature = (callback, *, target, clock = None, fixed_step_seconds = None, maximum_delta_seconds = None,
        maximum_catch_up_steps = 4, overflow = "drop"))]
    fn on_update(
        &self,
        py: Python<'_>,
        callback: Py<PyAny>,
        target: &Bound<'_, PyBuffer>,
        clock: Option<&Bound<'_, PyAny>>,
        fixed_step_seconds: Option<f64>,
        maximum_delta_seconds: Option<f64>,
        maximum_catch_up_steps: u32,
        overflow: &str,
    ) -> PyResult<PyHook> {
        if !callback.bind(py).is_callable() {
            return Err(PyTypeError::new_err("an update callback must be callable"));
        }
        if overflow != "drop" && overflow != "retain" {
            return Err(PyValueError::new_err(format!(
                "\"{overflow}\" is not an overflow mode; use \"drop\" or \"retain\""
            )));
        }
        if let Some(step) = fixed_step_seconds
            && (!step.is_finite() || step <= 0.0)
        {
            return Err(PyValueError::new_err(format!(
                "fixed_step_seconds must be a positive number of seconds, not {step}"
            )));
        }
        if let Some(limit) = maximum_delta_seconds {
            seconds(limit, "maximum_delta_seconds")?;
        }
        let clock = ClockRef::from_object(clock)?;
        let state = HookState::new(0);
        let last_elapsed = clock.elapsed(&self.shared);
        self.updates.borrow_mut().push(UpdateRegistration {
            callback,
            state: Arc::clone(&state),
            target: target.clone().unbind(),
            clock,
            fixed_step: fixed_step_seconds,
            maximum_delta: maximum_delta_seconds,
            maximum_catch_up_steps: maximum_catch_up_steps.max(1),
            should_retain_overflow: overflow == "retain",
            accumulator: 0.0,
            last_elapsed,
        });
        Ok(PyHook::new(state))
    }

    #[pyo3(signature = (callback, *, target))]
    fn on_frame(
        &self,
        py: Python<'_>,
        callback: Py<PyAny>,
        target: &Bound<'_, PyBuffer>,
    ) -> PyResult<PyHook> {
        if !callback.bind(py).is_callable() {
            return Err(PyTypeError::new_err("a frame callback must be callable"));
        }
        let state = HookState::new(0);
        self.frames.borrow_mut().push(FrameRegistration {
            callback,
            state: Arc::clone(&state),
            target: target.clone().unbind(),
        });
        Ok(PyHook::new(state))
    }

    fn on_render_error(&self, py: Python<'_>, callback: Py<PyAny>) -> PyResult<PyHook> {
        if !callback.bind(py).is_callable() {
            return Err(PyTypeError::new_err(
                "a render error callback must be callable",
            ));
        }
        let state = HookState::new(0);
        self.error_handlers.borrow_mut().push(ErrorHandler {
            callback,
            state: Arc::clone(&state),
        });
        Ok(PyHook::new(state))
    }

    #[pyo3(signature = (seconds_value, callback, *, clock = None))]
    fn call_later(
        &self,
        seconds_value: f64,
        callback: Py<PyAny>,
        clock: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<PyScheduledCall> {
        self.schedule(seconds(seconds_value, "seconds")?, None, callback, clock)
    }

    #[pyo3(signature = (seconds_value, callback, *, clock = None))]
    fn call_every(
        &self,
        seconds_value: f64,
        callback: Py<PyAny>,
        clock: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<PyScheduledCall> {
        if seconds_value <= 0.0 {
            return Err(PyValueError::new_err(format!(
                "call_every needs a positive interval, not {seconds_value} seconds"
            )));
        }
        self.schedule(
            seconds(seconds_value, "seconds")?,
            Some(seconds_value),
            callback,
            clock,
        )
    }

    fn call_soon_threadsafe(&self, py: Python<'_>, callback: Py<PyAny>) {
        self.shared.queue.push_call(QueuedCall {
            function: callback,
            arguments: PyTuple::empty(py).unbind(),
        });
    }

    #[pyo3(signature = (key, *, interval_milliseconds, should_repeat = true))]
    fn start_timer(
        &self,
        key: String,
        interval_milliseconds: i64,
        should_repeat: bool,
    ) -> PyResult<()> {
        let interval =
            milliseconds(interval_milliseconds, "interval_milliseconds")? as f64 / 1000.0;
        self.timers.borrow_mut().insert(
            key,
            Timer {
                next: self.now() + interval,
                interval,
                should_repeat,
            },
        );
        self.shared.queue.nudge();
        Ok(())
    }

    fn stop_timer(&self, key: &str) -> bool {
        self.timers.borrow_mut().remove(key).is_some()
    }

    fn request_frame(&self) {
        self.shared.request_frame();
    }

    #[pyo3(signature = (*, timeout_milliseconds = Some(0)))]
    fn step(slf: &Bound<'_, Self>, timeout_milliseconds: Option<i64>) -> PyResult<PyStepResult> {
        let py = slf.py();
        Self::link_object(slf)?;
        {
            let runtime = slf.borrow();
            runtime.check_open("step")?;
            runtime.ensure_open(py)?;
            runtime.shared.is_running.store(true, Ordering::SeqCst);
        }
        let timeout = timeout_milliseconds.map(|value| Duration::from_millis(value.max(0) as u64));
        // Wait for work when there is none.
        {
            let runtime = slf.borrow();
            // A buffer changed from another thread (a write right after the screen opens, say)
            // wakes the wait at once instead of when its slice ends. The listener is in place
            // before the check below, so a change between the check and the wait is not missed.
            let is_buffer_changed = Arc::new(AtomicBool::new(false));
            let _change_listener = (timeout != Some(Duration::ZERO)).then(|| {
                let changed = Arc::clone(&is_buffer_changed);
                let shared = Arc::clone(&runtime.shared);
                listen_for_changes(Arc::new(move || {
                    changed.store(true, Ordering::SeqCst);
                    shared.queue.wake_waiters();
                }))
            });
            // A frame that is wanted but not yet due is waited for, not spun on.
            let frame_wait = runtime.frame_wait(py);
            let is_idle = !runtime.shared.queue.has_pending()
                && (frame_wait.is_some() || !runtime.needs_frame_now(py));
            if is_idle && timeout != Some(Duration::ZERO) {
                let deadline = runtime.next_deadline(py).map(Duration::from_secs_f64);
                let manual_without_events =
                    runtime.shared.clock.source() == ClockSource::Manual && timeout.is_none();
                let wait = match (timeout, deadline, runtime.shared.clock.source()) {
                    (_, _, _) if manual_without_events => Some(Duration::from_millis(50)),
                    (Some(limit), Some(next), ClockSource::Monotonic) => Some(limit.min(next)),
                    (Some(limit), _, _) => Some(limit),
                    (None, Some(next), ClockSource::Monotonic) => Some(next),
                    (None, _, _) => None,
                };
                let queue = &runtime.shared;
                let frame_seconds =
                    runtime.config.frame_interval_milliseconds.get() as f64 / 1000.0;
                let mut remaining = wait;
                // Set once a frame is wanted but not yet due, so waiting for it to fall due
                // is not cut short by the request that is already known.
                let mut is_waiting_for_frame = frame_wait.is_some();
                loop {
                    let slice = remaining.map_or(Duration::from_millis(50), |left| {
                        left.min(Duration::from_millis(50))
                    });
                    py.detach(|| {
                        queue.queue.wait(Some(slice), || {
                            !is_waiting_for_frame
                                && (queue.is_frame_requested.load(Ordering::SeqCst)
                                    || is_buffer_changed.load(Ordering::SeqCst))
                        });
                    });
                    is_buffer_changed.store(false, Ordering::SeqCst);
                    py.check_signals()?;
                    if let Some(left) = remaining.as_mut() {
                        *left = left.saturating_sub(slice);
                        if left.is_zero() {
                            break;
                        }
                    }
                    if queue.queue.has_pending() {
                        break;
                    }
                    if runtime.needs_frame_now(py) {
                        // Something asked for a frame, possibly from another thread.
                        if runtime.shared.clock.source() == ClockSource::Manual
                            || !runtime.has_rendered.get()
                        {
                            break;
                        }
                        let since = runtime.pace_now() - runtime.last_present_seconds.get();
                        if since >= frame_seconds {
                            break;
                        }
                        // The frame is wanted but not yet due: wait only until it is.
                        let due = Duration::from_secs_f64(frame_seconds - since);
                        remaining = Some(remaining.map_or(due, |left| left.min(due)));
                        is_waiting_for_frame = true;
                        continue;
                    }
                    if remaining.is_none() && manual_without_events {
                        break;
                    }
                }
            }
        }
        let runtime = slf.borrow();
        runtime.shared.clock.tick();
        // A wheel value lives for the step in which its event is processed.
        lock(&runtime.shared.input).scroll = (0, 0);
        runtime.sync_lifecycle(slf)?;
        // Queued callbacks.
        let mut calls = 0;
        while calls < 256
            && let Some(call) = runtime.shared.queue.pop_call()
        {
            call.function.bind(py).call(call.arguments.bind(py), None)?;
            calls += 1;
        }
        if runtime.shared.queue.take_wake() {
            runtime
                .shared
                .queue
                .push_event(Event::new(EventKind::Wake, EventPayload::None));
        }
        runtime.emit_due();
        let scheduled = runtime.run_scheduled(py)?;
        let mut events = 0;
        while events < 256
            && let Some(event) = runtime.shared.queue.pop_event()
        {
            runtime.process_event(slf, event)?;
            events += 1;
        }
        let updates = runtime.run_updates(slf)?;
        runtime.drain_stores()?;
        runtime.fire_state_changes(slf)?;
        runtime.fire_changes(slf)?;
        runtime.sync_lifecycle(slf)?;
        let mut did_render = false;
        if runtime.shared.is_running.load(Ordering::SeqCst) && runtime.needs_frame_now(py) {
            let is_paced = runtime.shared.clock.source() == ClockSource::Monotonic;
            let frame = runtime.config.frame_interval_milliseconds.get() as f64 / 1000.0;
            let since = runtime.pace_now() - runtime.last_present_seconds.get();
            if !is_paced || !runtime.has_rendered.get() || since >= frame {
                drop(runtime);
                Self::render_frame(slf)?;
                did_render = true;
            }
        }
        let runtime = slf.borrow();
        let _ = scheduled;
        Ok(PyStepResult {
            events_processed: events + calls,
            updates_processed: updates,
            did_render,
            is_running: runtime.shared.is_running.load(Ordering::SeqCst)
                && !runtime.shared.is_closed.load(Ordering::SeqCst),
        })
    }

    fn advance_clock(&self, milliseconds_value: i64) -> PyResult<()> {
        if milliseconds_value < 0 {
            return Err(PyValueError::new_err(format!(
                "a clock cannot move backwards: {milliseconds_value} milliseconds is negative"
            )));
        }
        if !self.shared.clock.advance(milliseconds_value as u64) {
            return Err(PyValueError::new_err(
                "only a manual clock can be advanced; offscreen runtimes use one by default",
            ));
        }
        self.shared.queue.nudge();
        Ok(())
    }

    #[pyo3(signature = (*, width, height))]
    fn resize(&self, width: i32, height: i32) -> PyResult<()> {
        self.check_open("resize")?;
        xnano_terminal_runtime::buffer::check_size(width, height).map_err(PyValueError::new_err)?;
        if self.config.backend != Backend::Offscreen && self.config.inline_height.get().is_none() {
            return Err(PyValueError::new_err(
                "only an offscreen runtime or an inline region can be resized; a live runtime \
                 that takes the whole window follows the window",
            ));
        }
        self.resize_destination(Size::new(width, height), true)?;
        Ok(())
    }

    /// Give every buffer that fits its children the size they cover now, instead of at the
    /// next frame, and return the size of what the runtime draws on.
    ///
    /// A mounted buffer that fits its children decides that size along the axes it fits: an
    /// offscreen runtime takes it, and so does the region of a live runtime that draws inline,
    /// held to the window. Frames do this by themselves before they are drawn; call it to
    /// read sizes that are current between frames.
    fn fit_to_content(slf: &Bound<'_, Self>) -> PyResult<crate::geometry::PySize> {
        let runtime = slf.borrow();
        runtime.check_open("fit_to_content")?;
        runtime.fit_mounted(slf.py())?;
        Ok(crate::geometry::PySize {
            inner: runtime.shared.device_size(),
        })
    }

    fn render(slf: &Bound<'_, Self>) -> PyResult<PyFrameSnapshot> {
        {
            let runtime = slf.borrow();
            runtime.check_open("render")?;
            runtime.ensure_open(slf.py())?;
        }
        Self::link_object(slf)?;
        slf.borrow().sync_lifecycle(slf)?;
        Self::render_frame(slf)
    }

    /// The shortest time between frames, in milliseconds; it may change while the runtime runs.
    #[getter]
    fn frame_interval_milliseconds(&self) -> u64 {
        self.config.frame_interval_milliseconds.get()
    }

    #[setter]
    fn set_frame_interval_milliseconds(&self, value: i64) -> PyResult<()> {
        let interval = milliseconds(value, "frame_interval_milliseconds")?;
        self.config.frame_interval_milliseconds.set(interval);
        Ok(())
    }

    /// The last window title set on this runtime.
    #[getter]
    fn title(&self) -> Option<String> {
        self.title.borrow().clone()
    }

    #[setter]
    fn set_title(&self, title: Option<String>) -> PyResult<()> {
        self.check_open("set the terminal title")?;
        if title
            .as_ref()
            .is_some_and(|title| title.chars().any(char::is_control))
        {
            return Err(PyValueError::new_err(
                "Cannot set the terminal title to text containing control characters. Expected a single line of printable text. Remove the control characters and try again.",
            ));
        }
        #[cfg(feature = "terminal")]
        if let Some(session) = self.session.borrow_mut().as_mut() {
            session.set_title(title.as_deref().unwrap_or("")).map_err(|error| {
                PyRuntimeError::new_err(format!(
                    "Cannot set the terminal title: {error}. Check that the terminal is writable and try again."
                ))
            })?;
        }
        *self.title.borrow_mut() = title;
        Ok(())
    }

    /// Whether standard output and standard error are held back from the screen.
    #[getter]
    fn is_output_captured(&self) -> bool {
        #[cfg(feature = "terminal")]
        if let Some(session) = self.session.borrow().as_ref() {
            return session.is_output_captured();
        }
        false
    }

    /// Text written to standard output and standard error during a live session since the
    /// last call, or an empty string for an offscreen runtime.
    fn take_captured_output(&self) -> String {
        #[cfg(feature = "terminal")]
        if let Some(session) = self.session.borrow().as_ref() {
            return session.take_captured_output();
        }
        String::new()
    }

    fn snapshot(&self) -> PyFrameSnapshot {
        let size = self.shared.device_size();
        let grid = self.last_frame.borrow().clone().unwrap_or_else(|| {
            Arc::new(Grid::new(
                size.width.max(0) as u16,
                size.height.max(0) as u16,
            ))
        });
        PyFrameSnapshot {
            grid,
            revision: self.frame_revision.get(),
            cursor: self.last_cursor.get(),
        }
    }

    fn run(slf: &Bound<'_, Self>) -> PyResult<()> {
        let py = slf.py();
        Self::link_object(slf)?;
        {
            let runtime = slf.borrow();
            runtime.check_open("run")?;
            let was_open = runtime.is_open.get();
            runtime.ensure_open(py)?;
            runtime.opened_by_run.set(!was_open);
            runtime.shared.is_running.store(true, Ordering::SeqCst);
        }
        let outcome = (|| -> PyResult<()> {
            loop {
                {
                    let runtime = slf.borrow();
                    if !runtime.shared.is_running.load(Ordering::SeqCst)
                        || runtime.shared.is_closed.load(Ordering::SeqCst)
                    {
                        return Ok(());
                    }
                }
                Self::step(slf, None)?;
            }
        })();
        if slf.borrow().opened_by_run.get() {
            let _ = slf.call_method0("close");
        }
        outcome
    }

    fn stop(&self) {
        self.shared.is_running.store(false, Ordering::SeqCst);
        self.shared.queue.nudge();
    }

    fn close(slf: &Bound<'_, Self>) -> PyResult<()> {
        let py = slf.py();
        let runtime = slf.borrow();
        if runtime.shared.is_closed.load(Ordering::SeqCst) {
            return Ok(());
        }
        runtime.shared.is_running.store(false, Ordering::SeqCst);
        let doomed = runtime.tree(py);
        let mut first_error = None;
        for buffer in &doomed {
            if let Err(error) =
                runtime.fire_buffer(slf, buffer, HookEvent::Unmount, &PyDict::new(py))
            {
                first_error.get_or_insert(error);
            }
        }
        runtime.quiet_global_stamp.set(0);
        runtime.mounts.borrow_mut().clear();
        for buffer in &doomed {
            let id = Self::core_of(py, buffer).id;
            runtime.release_buffer(py, buffer, id);
        }
        runtime.scheduled.borrow_mut().clear();
        runtime.shared.is_closed.store(true, Ordering::SeqCst);
        #[cfg(feature = "terminal")]
        if let Some(session) = runtime.session.borrow_mut().take() {
            // Python's own buffers go into the capture, and are printed with it, not lost.
            flush_python_streams(py);
            py.detach(|| session.close());
        }
        runtime.shared.queue.nudge();
        match first_error {
            Some(error) => Err(error),
            None => Ok(()),
        }
    }

    fn __enter__(slf: &Bound<'_, Self>) -> PyResult<Py<Self>> {
        Self::link_object(slf)?;
        {
            let runtime = slf.borrow();
            runtime.check_open("enter")?;
            runtime.ensure_open(slf.py())?;
            runtime.shared.is_running.store(true, Ordering::SeqCst);
        }
        Ok(slf.clone().unbind())
    }

    #[pyo3(signature = (exception_type = None, exception_value = None, traceback = None))]
    fn __exit__(
        slf: &Bound<'_, Self>,
        exception_type: Option<&Bound<'_, PyAny>>,
        exception_value: Option<&Bound<'_, PyAny>>,
        traceback: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<bool> {
        let _ = (exception_type, exception_value, traceback);
        slf.call_method0("close")?;
        Ok(false)
    }

    /// Provide the value of a named external expression.
    ///
    /// ``function`` is called with no arguments, on the runtime's own thread, each time an
    /// expression that reads ``name`` is evaluated.
    fn provide(&self, name: String, function: Py<PyAny>) {
        self.externals.borrow_mut().insert(name, function);
    }

    /// Read a named external value. Called by expression evaluation.
    fn _read_external(&self, py: Python<'_>, name: &str) -> PyResult<Py<PyAny>> {
        let function = self
            .externals
            .borrow()
            .get(name)
            .map(|function| function.clone_ref(py));
        match function {
            Some(function) => function.call0(py),
            None => Err(pyo3::exceptions::PyKeyError::new_err(format!(
                "nothing provides the value {name:?}. Call Runtime.provide({name:?}, function) \
                 before an expression reads it"
            ))),
        }
    }

    /// Run `state_change` hooks, once per step, when a watched branch of a store changes.
    ///
    /// `target` is a ``StateReference`` (its branch is watched) or a ``TerminalStateStore``
    /// (the whole store, or the given ``paths``). The hooks see the latest change as
    /// ``context.state_change``.
    #[pyo3(signature = (target, paths = None))]
    fn watch_state(
        &self,
        target: &Bound<'_, PyAny>,
        paths: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<crate::state::PyStateSubscription> {
        let (store, watched) =
            if let Ok(reference) = target.cast::<crate::references::PyStateReference>() {
                let reference = reference.get();
                (Arc::clone(&reference.store), vec![reference.path.clone()])
            } else if let Ok(store) = target.extract::<PyRef<'_, crate::state::PyStateStore>>() {
                let watched = match paths {
                    Some(paths) => crate::convert::paths_from_py(paths)?,
                    None => vec![Vec::new()],
                };
                (Arc::clone(&store.inner), watched)
            } else {
                return Err(pyo3::exceptions::PyTypeError::new_err(
                    "watch_state takes a StateReference or a TerminalStateStore",
                ));
            };
        {
            let mut stores = self.stores.borrow_mut();
            if !stores.iter().any(|existing| Arc::ptr_eq(existing, &store)) {
                stores.push(Arc::clone(&store));
            }
        }
        let listener = Arc::new(QueueListener {
            queue: Arc::clone(&self.pending_state_changes),
            shared: Arc::clone(&self.shared),
        });
        Ok(crate::state::PyStateSubscription::of(
            store.subscribe(watched, true, listener),
        ))
    }

    /// Keep a state store drained on the owner thread each step.
    fn _register_store(&self, store: &crate::state::PyStateStore) {
        let mut stores = self.stores.borrow_mut();
        if !stores
            .iter()
            .any(|existing| Arc::ptr_eq(existing, &store.inner))
        {
            stores.push(Arc::clone(&store.inner));
        }
    }

    /// Call `notifier` from any thread whenever the runtime has work queued.
    fn _add_notifier(&self, py: Python<'_>, notifier: Py<PyAny>) -> u64 {
        let _ = py;
        self.shared.queue.add_notifier(Arc::new(move || {
            Python::attach(|py| {
                if let Err(error) = notifier.call0(py) {
                    error.write_unraisable(py, None);
                }
            });
        }))
    }

    fn _remove_notifier(&self, token: u64) {
        self.shared.queue.remove_notifier(token);
    }

    /// Seconds until the next scheduled work, or `None`.
    fn _next_deadline_seconds(&self, py: Python<'_>) -> Option<f64> {
        self.next_deadline(py)
    }

    /// Start a packed cell animation on a mounted target, replacing one with the same key.
    #[pyo3(signature = (target, packed, *, x = 0, y = 0, start_milliseconds = 0, key = None))]
    fn _animate(
        &self,
        target: &Bound<'_, PyAny>,
        packed: &[u8],
        x: i32,
        y: i32,
        start_milliseconds: i64,
        key: Option<String>,
    ) -> PyResult<()> {
        let surface = target.extract::<PyRef<'_, PySurface>>()?;
        let animation = xnano_terminal_cells::unpack_animation(packed)
            .map_err(|error| crate::errors::CellGridError::new_err(error.to_string()))?;
        let now = ((self.now() * 1000.0) as i64).max(0);
        let mut motion = lock(&self.shared.motion);
        if let Some(key) = &key {
            motion
                .animations
                .retain(|existing| existing.key.as_ref() != Some(key));
        }
        motion.animations.push(crate::shared::RunningAnimation {
            key,
            animation,
            target: Arc::clone(&surface.core),
            region: surface.region,
            x,
            y,
            encoding: xnano_terminal_runtime::pixel::PixelEncoding::HalfBlocks,
            start_milliseconds: now - start_milliseconds,
            shown_index: None,
        });
        drop(motion);
        self.shared.request_frame();
        Ok(())
    }

    /// Stop the animation started with `key`.
    fn _stop_animation(&self, key: &str) {
        lock(&self.shared.motion)
            .animations
            .retain(|existing| existing.key.as_deref() != Some(key));
        self.shared.request_frame();
    }

    /// Wake anything waiting on the runtime without queuing an event.
    fn _nudge(&self) {
        self.shared.queue.nudge();
    }

    fn _has_pending(&self, py: Python<'_>) -> bool {
        self.shared.queue.has_pending() || self.needs_frame_now(py)
    }

    fn _consume_pointer(&self, buffer: &Bound<'_, PyBuffer>, should_capture: bool) {
        let id = buffer.as_super().borrow().core.id;
        let mut router = lock(&self.shared.router);
        if should_capture {
            router.captured_pointer = Some(id);
        } else if router.captured_pointer == Some(id) {
            router.captured_pointer = None;
        }
    }

    fn _focus(&self, buffer: &Bound<'_, PyBuffer>) -> bool {
        let core = Arc::clone(&buffer.as_super().borrow().core);
        focus_buffer(&self.shared, &core)
    }

    fn _fire(
        slf: &Bound<'_, Self>,
        buffer: &Bound<'_, PyBuffer>,
        kind: &str,
        state_change: Option<Py<PyAny>>,
    ) -> PyResult<()> {
        let py = slf.py();
        let runtime = slf.borrow();
        let wanted = HookEvent::parse(kind)?;
        let extras = PyDict::new(py);
        extras.set_item("state_change", state_change)?;
        runtime.fire_buffer(slf, &buffer.clone().unbind(), wanted, &extras)
    }

    fn _is_focused(&self, buffer: &Bound<'_, PyBuffer>) -> bool {
        let id = buffer.as_super().borrow().core.id;
        lock(&self.shared.router).focused == Some(id)
    }

    fn __repr__(&self) -> String {
        format!(
            "Runtime(backend='{}', is_running={}, is_closed={})",
            if self.config.backend == Backend::Terminal {
                "terminal"
            } else {
                "offscreen"
            },
            if self.shared.is_running.load(Ordering::SeqCst) {
                "True"
            } else {
                "False"
            },
            if self.shared.is_closed.load(Ordering::SeqCst) {
                "True"
            } else {
                "False"
            }
        )
    }
}

impl PyRuntime {
    fn schedule(
        &self,
        delay: f64,
        interval: Option<f64>,
        callback: Py<PyAny>,
        clock: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<PyScheduledCall> {
        let clock = ClockRef::from_object(clock)?;
        let state = Arc::new(ScheduledState {
            is_cancelled: AtomicBool::new(false),
        });
        let due = clock.elapsed(&self.shared) + delay;
        self.scheduled.borrow_mut().push(Scheduled {
            state: Arc::clone(&state),
            callback,
            due,
            interval,
            clock,
        });
        self.shared.queue.nudge();
        Ok(PyScheduledCall { state })
    }

    /// Open the device the first time the runtime is entered, run or stepped.
    fn ensure_open(&self, py: Python<'_>) -> PyResult<()> {
        if self.is_open.get() {
            return Ok(());
        }
        self.is_open.set(true);
        #[cfg(feature = "terminal")]
        if self.config.backend == Backend::Terminal {
            use xnano_terminal_runtime::terminal::{
                KeyboardMode, MouseCapture, SessionOptions, TerminalSession,
            };
            let options = self.config.options.clone().map_or_else(
                || PyTerminalOptions::new(None, true, true, true, 250, true, false),
                Ok,
            )?;
            let input = options.input.clone();
            let timeout = Duration::from_millis(input.capability_timeout_milliseconds);
            let probe = py.detach(|| xnano_terminal_runtime::terminal::probe(timeout));
            let session_options = SessionOptions {
                mouse: match input.mouse.as_str() {
                    "buttons" => MouseCapture::Buttons,
                    "motion" => MouseCapture::Motion,
                    _ => MouseCapture::Off,
                },
                scroll: input.scroll,
                keeps_interrupt_chord: input.interrupt == "stop",
                bracketed_paste: input.bracketed_paste,
                focus_reporting: input.focus_reporting,
                keyboard: match input.keyboard.as_str() {
                    "off" => KeyboardMode::Off,
                    "disambiguated" => KeyboardMode::Disambiguated,
                    "release_events" => KeyboardMode::ReleaseEvents,
                    _ => KeyboardMode::Basic,
                },
                capability_timeout: timeout,
                alternate_screen: options.alternate_screen,
                raw_mode: options.raw_mode,
                drain_reports_on_exit: options.drain_reports_on_exit,
                drain_timeout: Duration::from_millis(options.drain_timeout_milliseconds),
                inline_height: self.config.inline_height.get(),
                inline_width: self.config.inline_width.get(),
                should_handle_exit_signals: self.config.should_handle_exit_signals,
                should_clear_on_close: options.should_clear_on_close,
                should_capture_output: options.should_capture_output,
            };
            let shared = Arc::clone(&self.shared);
            let sink: xnano_terminal_runtime::terminal::EventSink =
                Arc::new(move |mut event: Event| {
                    event.timestamp_seconds = shared.clock.elapsed_seconds();
                    shared.queue.push_event(event);
                });
            // Text Python buffered before the session belongs before it, not inside it.
            flush_python_streams(py);
            let woken = Arc::clone(&self.shared);
            let output_notifier: xnano_terminal_runtime::output_capture::OutputNotifier =
                Arc::new(move || woken.queue.nudge());
            let mut session = TerminalSession::open(
                session_options,
                Some(&probe.keyboard),
                sink,
                Some(output_notifier),
            )
            .map_err(|error| PyRuntimeError::new_err(format!(
                    "the terminal could not be opened: {error}. Run the program in a terminal, or use \
                     Runtime.offscreen(...) for tests and output without a terminal"
                )))?;
            if let Some(title) = self.title.borrow().as_ref() {
                session.set_title(title).map_err(|error| {
                    PyRuntimeError::new_err(format!("Cannot set the terminal title: {error}. Check that the terminal is writable and try again."))
                })?;
            }
            let size = session
                .viewport()
                .map_err(|error| PyRuntimeError::new_err(error.to_string()))?;
            {
                let mut device = lock(&self.shared.device);
                device.size = size;
                device.terminal = probe.terminal.clone();
                device.keyboard = probe.keyboard.clone();
                device.modes = session.modes().clone();
                device.is_inline = session.is_inline();
                device.is_focused = true;
                device.window_size_in_pixels = None;
            }
            lock(&self.shared.input).held_keys_available =
                session.modes().keyboard_features.contains(&"event_types");
            *self.session.borrow_mut() = Some(session);
            return Ok(());
        }
        let _ = py;
        Ok(())
    }

    /// Compose, animate and present one frame.
    fn render_frame(slf: &Bound<'_, Self>) -> PyResult<PyFrameSnapshot> {
        let py = slf.py();
        let started = std::time::Instant::now();
        let outcome = Self::build_frame(slf);
        match outcome {
            Ok(snapshot) => {
                let runtime = slf.borrow();
                let microseconds = started.elapsed().as_micros();
                let mut metrics = lock(&runtime.shared.metrics);
                metrics.frames += 1;
                metrics.last_microseconds = microseconds as u64;
                metrics.total_microseconds += microseconds;
                Ok(snapshot)
            }
            Err(error) => {
                let is_ordinary = error.is_instance_of::<pyo3::exceptions::PyException>(py);
                if !is_ordinary {
                    return Err(error);
                }
                let wrapped = if error.is_instance_of::<RenderError>(py) {
                    error
                } else {
                    let wrapped = RenderError::new_err(format!(
                        "a frame could not be rendered: {error}. The previous frame is still shown"
                    ));
                    wrapped.set_cause(py, Some(error));
                    wrapped
                };
                let handlers: Vec<Py<PyAny>> = slf
                    .borrow()
                    .error_handlers
                    .borrow()
                    .iter()
                    .filter(|handler| handler.state.is_active())
                    .map(|handler| handler.callback.clone_ref(py))
                    .collect();
                if handlers.is_empty() {
                    return Err(wrapped);
                }
                let value = wrapped.value(py).clone().into_any();
                for handler in handlers {
                    handler.call1(py, (&value,))?;
                }
                slf.borrow().last_rendered_stamp.set(u64::MAX);
                slf.borrow().quiet_global_stamp.set(0);
                slf.borrow()
                    .shared
                    .is_frame_requested
                    .store(false, Ordering::SeqCst);
                Ok(slf.borrow().snapshot())
            }
        }
    }

    /// Size what the runtime draws on: an offscreen destination takes `size`, and an inline
    /// region of a live terminal takes it as far as the window allows (`inline_width` follows
    /// it only when `is_width_given`). Queues a resize event with the size it got. Returns it.
    fn resize_destination(&self, size: Size, is_width_given: bool) -> PyResult<Size> {
        #[allow(unused_mut)]
        let mut resized = size;
        if self.config.backend != Backend::Offscreen {
            // check_size has held both to the cells a buffer can have.
            let rows = size.height.clamp(1, i32::from(u16::MAX)) as u16;
            let columns = is_width_given.then(|| size.width.clamp(1, i32::from(u16::MAX)) as u16);
            self.config.inline_width.set(columns);
            self.config.inline_height.set(Some(rows));
            #[cfg(feature = "terminal")]
            if let Some(session) = self.session.borrow_mut().as_mut() {
                session.resize_inline(columns, rows).map_err(|error| {
                    PyRuntimeError::new_err(format!(
                        "the inline region could not be resized: {error}. Check that the \
                         terminal is still open"
                    ))
                })?;
                resized = session
                    .viewport()
                    .map_err(|error| PyRuntimeError::new_err(error.to_string()))?;
            }
        }
        lock(&self.shared.device).size = resized;
        self.shared
            .queue
            .push_event(Event::new(EventKind::Resize, EventPayload::Size(resized)));
        self.shared.request_frame();
        Ok(resized)
    }

    /// Fit every mounted tree to its content, and give the runtime the size of a mounted
    /// buffer that fits its children. Returns whether the runtime's size changed.
    fn fit_mounted(&self, py: Python<'_>) -> PyResult<bool> {
        let roots: Vec<(Py<PyBuffer>, Geometry)> = self
            .mounts
            .borrow()
            .iter()
            .map(|mount| (mount.buffer.clone_ref(py), mount.geometry))
            .collect();
        let size = self.shared.device_size();
        for (root, geometry) in &roots {
            let core = Self::core_of(py, root);
            xnano_terminal_runtime::buffer::fit_tree(&core);
            if *geometry != Geometry::Inherit {
                continue;
            }
            let (fit, width, height) = {
                let state = core.lock();
                (state.fit, state.width(), state.height())
            };
            let Some(fit) = fit else {
                continue;
            };
            let is_inline = self.config.inline_height.get().is_some();
            if self.config.backend != Backend::Offscreen && !is_inline {
                // A live runtime that takes the whole window follows the window.
                continue;
            }
            let wanted = Size::new(
                if fit.width { width } else { size.width },
                if fit.height { height } else { size.height },
            );
            if wanted == size {
                return Ok(false);
            }
            let resized = self.resize_destination(wanted, fit.width)?;
            return Ok(resized != size);
        }
        Ok(false)
    }

    fn build_frame(slf: &Bound<'_, Self>) -> PyResult<PyFrameSnapshot> {
        let py = slf.py();
        let runtime = slf.borrow();
        // This frame answers every request made so far. A request made from here on (by
        // a callback, or by another thread changing a buffer) is for the next frame, so it
        // must survive this one.
        runtime
            .shared
            .is_frame_requested
            .store(false, Ordering::SeqCst);
        // The authoritative drawable area for this frame.
        #[cfg(feature = "terminal")]
        if let Some(session) = runtime.session.borrow_mut().as_mut() {
            let size = session
                .viewport()
                .map_err(|error| RenderError::new_err(error.to_string()))?;
            lock(&runtime.shared.device).size = size;
        }
        // Content that fits its children decides the size before anything is measured.
        runtime.fit_mounted(py)?;
        let size = runtime.shared.device_size();
        let (mut columns, mut rows) =
            xnano_terminal_runtime::buffer::check_size(size.width, size.height)
                .map_err(RenderError::new_err)?;
        let mut area = Rectangle::new(0, 0, i32::from(columns), i32::from(rows));
        // Geometry and layout.
        let roots: Vec<(Py<PyBuffer>, Geometry)> = runtime
            .mounts
            .borrow()
            .iter()
            .map(|mount| (mount.buffer.clone_ref(py), mount.geometry))
            .collect();
        for (root, geometry) in &roots {
            let core = Self::core_of(py, root);
            if *geometry == Geometry::Inherit {
                core.move_to(0, 0);
                core.resize(size.width, size.height)
                    .map_err(RenderError::new_err)?;
            }
            relayout(&core);
        }
        let damage = runtime.collect_damage(py);
        let elapsed = runtime.now();
        let delta = (elapsed - runtime.last_effect_seconds.get()).max(0.0);
        runtime.last_effect_seconds.set(elapsed);
        drop(runtime);
        // Frame callbacks and hooks.
        let extras = PyDict::new(py);
        extras.set_item("area", crate::geometry::PyRectangle { inner: area })?;
        extras.set_item("elapsed_seconds", elapsed)?;
        extras.set_item("delta_seconds", delta)?;
        extras.set_item(
            "damaged_areas",
            PyTuple::new(
                py,
                damage
                    .iter()
                    .map(|inner| crate::geometry::PyRectangle { inner: *inner }),
            )?,
        )?;
        let frame_event = Event::new(EventKind::Frame, EventPayload::None);
        {
            let runtime = slf.borrow();
            runtime.broadcast(
                slf,
                HookEvent::BeforeRender,
                ContextKind::Frame,
                None,
                &extras,
            )?;
            let registrations: Vec<(Py<PyAny>, Py<PyBuffer>)> = runtime
                .frames
                .borrow()
                .iter()
                .filter(|registration| registration.state.is_active())
                .map(|registration| {
                    (
                        registration.callback.clone_ref(py),
                        registration.target.clone_ref(py),
                    )
                })
                .collect();
            for (callback, target) in registrations {
                let context =
                    runtime.make_context(slf, ContextKind::Frame, &target, None, None, &extras)?;
                callback.bind(py).call1((context,))?;
            }
            runtime.broadcast(
                slf,
                HookEvent::Event(EventKind::Frame),
                ContextKind::Frame,
                Some(&frame_event),
                &extras,
            )?;
        }
        let runtime = slf.borrow();
        // The frame callbacks may have moved or resized what fits its children (a line of
        // text that follows the one before it), so the size is fitted once more before drawing.
        if runtime.fit_mounted(py)? {
            let size = runtime.shared.device_size();
            (columns, rows) = xnano_terminal_runtime::buffer::check_size(size.width, size.height)
                .map_err(RenderError::new_err)?;
            area = Rectangle::new(0, 0, i32::from(columns), i32::from(rows));
            for mount in runtime.mounts.borrow().iter() {
                if mount.geometry == Geometry::Inherit {
                    let core = Self::core_of(py, &mount.buffer);
                    core.move_to(0, 0);
                    core.resize(size.width, size.height)
                        .map_err(RenderError::new_err)?;
                    relayout(&core);
                }
            }
        }
        // Animations draw into their targets; effects process over the composed frame.
        runtime.update_animations(py);
        let roots: Vec<(Py<PyBuffer>, Geometry)> = runtime
            .mounts
            .borrow()
            .iter()
            .map(|mount| (mount.buffer.clone_ref(py), mount.geometry))
            .collect();
        let mut ordered: Vec<(i32, usize, Arc<BufferCore>)> = roots
            .iter()
            .enumerate()
            .map(|(index, (root, _))| {
                let core = Self::core_of(py, root);
                let layer = core.lock().layer;
                (layer, index, core)
            })
            .collect();
        ordered.sort_by_key(|(layer, index, _)| (*layer, *index));
        let mut frame = Grid::new(columns, rows);
        let mut stamp = 0;
        for (_, _, core) in &ordered {
            crate::widgets::refresh_tree(core)?;
            // Read before composing: a change made while composing (by another thread) is
            // newer than this stamp, so it is drawn by the next frame instead of lost.
            stamp = stamp.max(tree_modified(core));
            compose(core, &mut frame, (0, 0), area, PasteMode::Transparent);
        }
        let (completed, effect_errors) = runtime.apply_effects(&mut frame, delta);
        drop(runtime);
        for callback in completed {
            callback.bind(py).call0()?;
        }
        {
            let runtime = slf.borrow();
            runtime.broadcast(
                slf,
                HookEvent::AfterRender,
                ContextKind::Frame,
                None,
                &extras,
            )?;
        }
        let runtime = slf.borrow();
        let cursor = crate::cursor::resolve(
            &runtime.shared,
            Size::new(i32::from(columns), i32::from(rows)),
        );
        // Whether this frame wrote to the terminal; one identical to the last writes nothing.
        #[cfg_attr(not(feature = "terminal"), allow(unused_mut))]
        let mut was_written = true;
        #[cfg(feature = "terminal")]
        if let Some(session) = runtime.session.borrow_mut().as_mut() {
            was_written = py
                .detach(|| session.present(&frame, cursor))
                .map_err(|error| {
                    RenderError::new_err(format!("the frame could not be shown: {error}"))
                })?;
        }
        runtime.last_rendered_stamp.set(stamp);
        runtime.quiet_global_stamp.set(0);
        // The first frame is drawn as soon as the runtime starts, usually before the program
        // has written anything, so it does not count toward pacing: the next frame, which
        // shows that first write, is drawn at once instead of one frame interval later.
        // A frame that wrote nothing does not count toward pacing either, so the change that
        // follows it is shown at once. The measured frame rate counts the same frames as
        // pacing does, so it never reads above the rate the frame interval allows.
        let interval = runtime.config.frame_interval_milliseconds.get() as f64 / 1000.0;
        if !runtime.has_rendered.get() {
            runtime
                .last_present_seconds
                .set(runtime.pace_now() - interval);
        } else if was_written {
            runtime.last_present_seconds.set(runtime.pace_now());
            runtime.shared.clock.record_drawn_frame();
        }
        runtime.has_rendered.set(true);
        runtime.frame_revision.set(runtime.frame_revision.get() + 1);
        let frame = Arc::new(frame);
        *runtime.last_frame.borrow_mut() = Some(Arc::clone(&frame));
        runtime.last_cursor.set(cursor);
        // The frame is complete, so a mistake in an effect stops nothing half-drawn.
        if let Some(message) = effect_errors.into_iter().next() {
            return Err(RenderError::new_err(message));
        }
        Ok(PyFrameSnapshot {
            grid: frame,
            revision: runtime.frame_revision.get(),
            cursor,
        })
    }

    fn collect_damage(&self, py: Python<'_>) -> Vec<Rectangle> {
        let mut damage = Vec::new();
        for buffer in self.tree(py) {
            let core = Self::core_of(py, &buffer);
            let local: Vec<Rectangle> = std::mem::take(&mut core.lock().damage);
            let origin = absolute_origin(&core);
            for area in local {
                damage.push(area.translate(origin.0, origin.1));
            }
        }
        damage
    }

    fn update_animations(&self, py: Python<'_>) {
        let _ = py;
        let now = ((self.now() * 1000.0) as i64).max(0);
        let mut motion = lock(&self.shared.motion);
        for animation in &mut motion.animations {
            let elapsed = now - animation.start_milliseconds;
            let index = animation.animation.frame_index_at(elapsed);
            if animation.shown_index == Some(index) {
                continue;
            }
            animation.shown_index = Some(index);
            let frame = Grid::from_buffer(animation.animation.frames[index].grid.clone());
            let mut state = animation.target.lock();
            let bounds = region_bounds(&state.grid, animation.region);
            state.grid.paste(
                bounds,
                &frame,
                animation.x,
                animation.y,
                PasteMode::Transparent,
            );
            state.touch(None);
        }
        motion.animations.retain(|animation| {
            animation.animation.should_loop
                || animation
                    .animation
                    .milliseconds_until_next_frame(now - animation.start_milliseconds)
                    .is_some()
                || animation.shown_index.is_none()
        });
    }

    /// Advance and apply the running effects; returns the completion callbacks to call.
    fn apply_effects(&self, frame: &mut Grid, delta: f64) -> (Vec<Py<PyAny>>, Vec<String>) {
        let running: Vec<_> = lock(&self.shared.motion).effects.clone();
        let elapsed_ms = (delta * 1000.0).round() as u32;
        let mut callbacks = Vec::new();
        let mut errors = Vec::new();
        let mut has_effect_ended = false;
        for entry in &running {
            let mut running = lock(entry);
            if running.is_cancelled {
                continue;
            }
            let origin = absolute_origin(&running.target);
            let state = running.target.lock();
            let own = Rectangle::new(origin.0, origin.1, state.width(), state.height());
            drop(state);
            let area = match running.region {
                Some(region) => region.translate(origin.0, origin.1).intersection(own),
                None => own,
            };
            let clipped = area.intersection(Rectangle::new(
                0,
                0,
                i32::from(frame.width()),
                i32::from(frame.height()),
            ));
            if clipped.is_empty() {
                continue;
            }
            let bounds = Bounds {
                left: clipped.x as u16,
                top: clipped.y as u16,
                right: clipped.right() as u16,
                bottom: clipped.bottom() as u16,
            };
            let environment = crate::widgets::environment_of(&running.target);
            let placement = running.placement.clone();
            let step = if running.is_paused { 0 } else { elapsed_ms };
            let result = running.run.advance(
                environment.as_ref(),
                step,
                frame,
                bounds,
                (clipped.x, clipped.y),
                &placement,
            );
            if let Err(error) = result {
                errors.push(format!(
                    "the {} effect could not run: {error}. The effect was cancelled; check the \
                     values it was given",
                    running.run.spec.read().kind.name()
                ));
                running.error = Some(error.to_string());
                running.is_cancelled = true;
            }
            if running.run.is_done() {
                callbacks.append(&mut running.completed);
            }
            // An effect that finished or failed drew into this frame for the last time.
            has_effect_ended |= running.run.is_done() || running.is_cancelled;
        }
        lock(&self.shared.motion).effects.retain(|entry| {
            let entry = lock(entry);
            !entry.is_cancelled && !entry.run.is_done()
        });
        // Nothing else may change after an effect ends, so the frame that shows the content
        // without it is asked for here instead of waiting for an unrelated change.
        if has_effect_ended {
            self.shared.request_frame();
        }
        (callbacks, errors)
    }
}

fn region_bounds(grid: &Grid, region: Option<Rectangle>) -> Bounds {
    let full = Rectangle::new(0, 0, i32::from(grid.width()), i32::from(grid.height()));
    let area = region.map_or(full, |region| region.intersection(full));
    if area.is_empty() {
        return Bounds {
            left: 0,
            top: 0,
            right: 0,
            bottom: 0,
        };
    }
    Bounds {
        left: area.x as u16,
        top: area.y as u16,
        right: area.right() as u16,
        bottom: area.bottom() as u16,
    }
}

impl Drop for PyRuntime {
    fn drop(&mut self) {
        self.shared.is_running.store(false, Ordering::SeqCst);
        self.shared.is_closed.store(true, Ordering::SeqCst);
        self.shared.queue.nudge();
        #[cfg(feature = "terminal")]
        if let Some(session) = self.session.get_mut().take() {
            Python::try_attach(flush_python_streams);
            session.close();
        }
    }
}

/// Write out what Python has buffered for standard output and standard error.
///
/// Called as a live session begins and ends: output written before the capture starts must
/// reach the terminal before it, and output written during the session must reach the
/// capture before it is printed back.
#[cfg(feature = "terminal")]
fn flush_python_streams(py: Python<'_>) {
    let Ok(system) = py.import("sys") else {
        return;
    };
    for name in ["stdout", "stderr"] {
        if let Ok(stream) = system.getattr(name)
            && !stream.is_none()
        {
            let _ = stream.call_method0("flush");
        }
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyStepResult>()?;
    m.add_class::<PyFrameMetrics>()?;
    m.add_class::<PyFrameSnapshot>()?;
    m.add_class::<PyEventStream>()?;
    m.add_class::<PyWaker>()?;
    m.add_class::<PyRuntime>()?;
    Ok(())
}

/// Queues the changes of watched state branches for the runtime's next step.
struct QueueListener {
    queue: Arc<Mutex<Vec<Arc<xnano_terminal_state::store::Change>>>>,
    shared: Arc<RuntimeShared>,
}

impl xnano_terminal_state::store::Listener for QueueListener {
    fn notify(
        &self,
        change: &Arc<xnano_terminal_state::store::Change>,
    ) -> Result<(), xnano_terminal_state::store::ListenerFailure> {
        lock(&self.queue).push(Arc::clone(change));
        self.shared.request_frame();
        Ok(())
    }
}
