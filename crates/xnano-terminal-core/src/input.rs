//! Device state, capability negotiation and scoped input routing.

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyFrozenSet, PyTuple};
use xnano_terminal_runtime::buffer::absolute_origin;
use xnano_terminal_runtime::device::Status;
use xnano_terminal_runtime::geometry::{Point, Rectangle, Size};

use crate::events::binding_arg;
use crate::geometry::{PyRectangle, PySize};
use crate::hooks::{HookEntry, HookEvent, PyHook};
use crate::runtime::shared_of;
use crate::shared::{Backend, HitAreaData, RuntimeShared, ScopeData, lock};
use crate::surface::{PySurface, ext_of, nudge};

fn status_name(status: Status) -> &'static str {
    status.name()
}

#[pyclass(
    name = "KeyboardCapabilities",
    module = "xnano_core._xnano_core",
    frozen,
    skip_from_py_object
)]
#[derive(Clone)]
pub struct PyKeyboardCapabilities {
    pub enhancement: Status,
    pub unavailable_reason: Option<String>,
    pub enabled_features: Vec<&'static str>,
}

#[pymethods]
impl PyKeyboardCapabilities {
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
    fn enhancement(&self) -> &'static str {
        status_name(self.enhancement)
    }

    #[getter]
    fn disambiguates_keys(&self) -> bool {
        self.enhancement == Status::Supported
    }

    #[getter]
    fn reports_event_types(&self) -> bool {
        self.enhancement == Status::Supported
    }

    #[getter]
    fn reports_all_keys(&self) -> bool {
        self.enhancement == Status::Supported
    }

    #[getter]
    fn unavailable_reason(&self) -> Option<&str> {
        self.unavailable_reason.as_deref()
    }

    #[getter]
    fn enabled_features<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyFrozenSet>> {
        PyFrozenSet::new(py, self.enabled_features.iter().copied())
    }

    fn __repr__(&self) -> String {
        format!("KeyboardCapabilities(enhancement='{}')", self.enhancement())
    }
}

#[pyfunction]
#[pyo3(signature = (*, timeout_milliseconds = 200))]
pub fn query_keyboard_capabilities(
    py: Python<'_>,
    timeout_milliseconds: u64,
) -> PyKeyboardCapabilities {
    #[cfg(feature = "terminal")]
    {
        let info = py.detach(|| {
            xnano_terminal_runtime::terminal::query_keyboard(Duration::from_millis(
                timeout_milliseconds,
            ))
        });
        PyKeyboardCapabilities {
            enhancement: info.enhancement,
            unavailable_reason: info.unavailable_reason,
            enabled_features: Vec::new(),
        }
    }
    #[cfg(not(feature = "terminal"))]
    {
        let _ = (py, timeout_milliseconds, Duration::ZERO);
        PyKeyboardCapabilities {
            enhancement: Status::Unsupported,
            unavailable_reason: Some("this build has no live terminal".to_owned()),
            enabled_features: Vec::new(),
        }
    }
}

#[pyclass(
    name = "TerminalCapabilities",
    module = "xnano_core._xnano_core",
    frozen,
    skip_from_py_object
)]
#[derive(Clone)]
pub struct PyTerminalCapabilities {
    pub is_terminal: bool,
    pub is_live_terminal_available: bool,
    pub color_profile: &'static str,
    pub graphics_protocol: &'static str,
    pub cell_size_in_pixels: Option<(u16, u16)>,
    pub synchronized_output: Status,
}

impl PyTerminalCapabilities {
    pub fn offscreen() -> Self {
        Self {
            is_terminal: false,
            is_live_terminal_available: cfg!(feature = "terminal"),
            color_profile: "no_terminal",
            graphics_protocol: "half_blocks",
            cell_size_in_pixels: None,
            synchronized_output: Status::Unknown,
        }
    }
}

#[pymethods]
impl PyTerminalCapabilities {
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
    fn is_terminal(&self) -> bool {
        self.is_terminal
    }

    #[getter]
    fn is_live_terminal_available(&self) -> bool {
        self.is_live_terminal_available
    }

    #[getter]
    fn color_profile(&self) -> &'static str {
        self.color_profile
    }

    #[getter]
    fn graphics_protocol(&self) -> &'static str {
        self.graphics_protocol
    }

    #[getter]
    fn cell_size_in_pixels(&self) -> Option<(u16, u16)> {
        self.cell_size_in_pixels
    }

    #[getter]
    fn synchronized_output(&self) -> &'static str {
        status_name(self.synchronized_output)
    }

    fn __repr__(&self) -> String {
        format!(
            "TerminalCapabilities(is_terminal={}, color_profile='{}', graphics_protocol='{}')",
            if self.is_terminal { "True" } else { "False" },
            self.color_profile,
            self.graphics_protocol
        )
    }
}

#[pyfunction]
#[pyo3(signature = (*, timeout_milliseconds = 200))]
pub fn detect_terminal_capabilities(
    py: Python<'_>,
    timeout_milliseconds: u64,
) -> PyTerminalCapabilities {
    #[cfg(feature = "terminal")]
    {
        let info = py.detach(|| {
            xnano_terminal_runtime::terminal::detect_terminal(Duration::from_millis(
                timeout_milliseconds,
            ))
        });
        PyTerminalCapabilities {
            is_terminal: info.is_terminal,
            is_live_terminal_available: info.is_live_terminal_available,
            color_profile: info.color_profile,
            graphics_protocol: info.graphics_protocol,
            cell_size_in_pixels: info.cell_size_in_pixels,
            synchronized_output: info.synchronized_output,
        }
    }
    #[cfg(not(feature = "terminal"))]
    {
        let _ = (py, timeout_milliseconds, Duration::ZERO);
        PyTerminalCapabilities::offscreen()
    }
}

#[pyclass(
    name = "InputOptions",
    module = "xnano_core._xnano_core",
    frozen,
    from_py_object
)]
#[derive(Clone, PartialEq, Eq)]
pub struct PyInputOptions {
    pub mouse: String,
    pub scroll: bool,
    pub bracketed_paste: bool,
    pub focus_reporting: bool,
    pub keyboard: String,
    pub capability_timeout_milliseconds: u64,
    pub interrupt: String,
}

fn choice(value: &str, name: &str, allowed: &[&str]) -> PyResult<()> {
    if allowed.contains(&value) {
        Ok(())
    } else {
        let list: Vec<String> = allowed.iter().map(|item| format!("\"{item}\"")).collect();
        Err(PyValueError::new_err(format!(
            "\"{value}\" is not a {name}; use {}",
            list.join(", ")
        )))
    }
}

#[pymethods]
impl PyInputOptions {
    #[new]
    #[pyo3(signature = (*, mouse = "off", scroll = false, bracketed_paste = true, focus_reporting = true, keyboard = "basic",
        capability_timeout_milliseconds = 200, interrupt = "event"))]
    pub(crate) fn new(
        mouse: &str,
        scroll: bool,
        bracketed_paste: bool,
        focus_reporting: bool,
        keyboard: &str,
        capability_timeout_milliseconds: u64,
        interrupt: &str,
    ) -> PyResult<Self> {
        choice(mouse, "mouse mode", &["off", "buttons", "motion"])?;
        choice(
            keyboard,
            "keyboard mode",
            &["off", "basic", "disambiguated", "release_events"],
        )?;
        choice(interrupt, "interrupt mode", &["event", "stop"])?;
        Ok(Self {
            mouse: mouse.to_owned(),
            scroll,
            bracketed_paste,
            focus_reporting,
            keyboard: keyboard.to_owned(),
            capability_timeout_milliseconds,
            interrupt: interrupt.to_owned(),
        })
    }

    #[getter]
    fn mouse(&self) -> &str {
        &self.mouse
    }

    #[getter]
    fn scroll(&self) -> bool {
        self.scroll
    }

    #[getter]
    fn bracketed_paste(&self) -> bool {
        self.bracketed_paste
    }

    #[getter]
    fn focus_reporting(&self) -> bool {
        self.focus_reporting
    }

    #[getter]
    fn keyboard(&self) -> &str {
        &self.keyboard
    }

    #[getter]
    fn capability_timeout_milliseconds(&self) -> u64 {
        self.capability_timeout_milliseconds
    }

    #[getter]
    fn interrupt(&self) -> &str {
        &self.interrupt
    }

    fn __repr__(&self) -> String {
        format!(
            "InputOptions(mouse='{}', scroll={}, bracketed_paste={}, focus_reporting={}, \
             keyboard='{}', capability_timeout_milliseconds={}, interrupt='{}')",
            self.mouse,
            if self.scroll { "True" } else { "False" },
            if self.bracketed_paste {
                "True"
            } else {
                "False"
            },
            if self.focus_reporting {
                "True"
            } else {
                "False"
            },
            self.keyboard,
            self.capability_timeout_milliseconds,
            self.interrupt
        )
    }

    fn __eq__(&self, other: &Bound<'_, PyAny>) -> bool {
        other
            .extract::<PyInputOptions>()
            .is_ok_and(|other| *self == other)
    }

    #[classattr]
    const __hash__: Option<Py<PyAny>> = None;
}

#[pyclass(
    name = "TerminalOptions",
    module = "xnano_core._xnano_core",
    frozen,
    from_py_object
)]
#[derive(Clone)]
pub struct PyTerminalOptions {
    pub input: PyInputOptions,
    pub alternate_screen: bool,
    pub raw_mode: bool,
    pub drain_reports_on_exit: bool,
    pub drain_timeout_milliseconds: u64,
    pub should_capture_output: bool,
    pub should_clear_on_close: bool,
}

#[pymethods]
impl PyTerminalOptions {
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
                "input",
                "alternate_screen",
                "raw_mode",
                "should_capture_output",
                "should_clear_on_close",
            ],
        )
    }

    #[new]
    #[pyo3(signature = (*, input = None, alternate_screen = true, raw_mode = true, drain_reports_on_exit = true,
        drain_timeout_milliseconds = 250, should_capture_output = true, should_clear_on_close = false))]
    pub(crate) fn new(
        input: Option<PyInputOptions>,
        alternate_screen: bool,
        raw_mode: bool,
        drain_reports_on_exit: bool,
        drain_timeout_milliseconds: u64,
        should_capture_output: bool,
        should_clear_on_close: bool,
    ) -> PyResult<Self> {
        let input = match input {
            Some(input) => input,
            None => PyInputOptions::new("off", false, true, true, "basic", 200, "event")?,
        };
        Ok(Self {
            input,
            alternate_screen,
            raw_mode,
            drain_reports_on_exit,
            drain_timeout_milliseconds,
            should_capture_output,
            should_clear_on_close,
        })
    }

    #[getter]
    fn input(&self) -> PyInputOptions {
        self.input.clone()
    }

    #[getter]
    fn alternate_screen(&self) -> bool {
        self.alternate_screen
    }

    #[getter]
    fn raw_mode(&self) -> bool {
        self.raw_mode
    }

    #[getter]
    fn drain_reports_on_exit(&self) -> bool {
        self.drain_reports_on_exit
    }

    #[getter]
    fn drain_timeout_milliseconds(&self) -> u64 {
        self.drain_timeout_milliseconds
    }

    #[getter]
    fn should_capture_output(&self) -> bool {
        self.should_capture_output
    }

    #[getter]
    fn should_clear_on_close(&self) -> bool {
        self.should_clear_on_close
    }
}

#[pyclass(name = "InputState", module = "xnano_core._xnano_core", frozen)]
pub struct PyInputState {
    pub shared: Arc<RuntimeShared>,
}

#[pymethods]
impl PyInputState {
    fn __repr__(slf: &Bound<'_, Self>) -> PyResult<String> {
        crate::reprs::described(
            slf.as_any(),
            &[
                "last_key",
                "pressed_keys",
                "last_mouse_position",
                "is_mouse_down",
            ],
        )
    }

    #[getter]
    fn held_keys_available(&self) -> bool {
        lock(&self.shared.input).held_keys_available
    }

    #[getter]
    fn pressed_keys<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyFrozenSet>> {
        let keys: Vec<String> = lock(&self.shared.input).pressed.iter().cloned().collect();
        PyFrozenSet::new(py, keys)
    }

    #[getter]
    fn estimated_pressed_keys<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyFrozenSet>> {
        let now = self.shared.clock.elapsed_seconds();
        let keys: Vec<String> = lock(&self.shared.input)
            .estimated
            .iter()
            .filter(|(_, expiry)| **expiry > now)
            .map(|(key, _)| key.clone())
            .collect();
        PyFrozenSet::new(py, keys)
    }

    #[getter]
    fn pointer_cell(&self) -> Option<(i32, i32)> {
        lock(&self.shared.input).pointer
    }

    #[getter]
    fn last_key(&self) -> Option<String> {
        lock(&self.shared.input).last_key.clone()
    }

    #[getter]
    fn last_key_kind(&self) -> Option<&'static str> {
        lock(&self.shared.input).last_key_kind
    }

    #[getter]
    fn last_binding(&self) -> Option<String> {
        lock(&self.shared.input).last_binding.clone()
    }

    #[getter]
    fn last_mouse_button(&self) -> Option<&'static str> {
        lock(&self.shared.input).last_mouse_button
    }

    #[getter]
    fn last_mouse_kind(&self) -> Option<&'static str> {
        lock(&self.shared.input).last_mouse_kind
    }

    #[getter]
    fn last_mouse_position(&self) -> Option<(i32, i32)> {
        lock(&self.shared.input).last_mouse_position
    }

    #[getter]
    fn scroll_x(&self) -> i32 {
        lock(&self.shared.input).scroll.0
    }

    #[getter]
    fn scroll_y(&self) -> i32 {
        lock(&self.shared.input).scroll.1
    }

    #[getter]
    fn is_mouse_down(&self) -> bool {
        lock(&self.shared.input).is_mouse_down()
    }

    #[getter]
    fn last_pasted_text(&self) -> Option<String> {
        lock(&self.shared.input).last_paste.clone()
    }

    #[pyo3(signature = (*, timeout_seconds = None))]
    fn estimate_holds(&self, timeout_seconds: Option<f64>) -> PyResult<()> {
        if let Some(timeout) = timeout_seconds
            && (!timeout.is_finite() || timeout <= 0.0)
        {
            return Err(PyValueError::new_err(format!(
                "the hold timeout must be a positive number of seconds, not {timeout}; pass None to \
                 turn estimates off"
            )));
        }
        let mut input = lock(&self.shared.input);
        input.estimate_timeout = timeout_seconds;
        if timeout_seconds.is_none() {
            input.estimated.clear();
        }
        Ok(())
    }
}

#[pyclass(name = "Device", module = "xnano_core._xnano_core", frozen)]
pub struct PyDevice {
    pub shared: Arc<RuntimeShared>,
}

#[pymethods]
impl PyDevice {
    fn __repr__(slf: &Bound<'_, Self>) -> PyResult<String> {
        crate::reprs::described(
            slf.as_any(),
            &[
                "backend",
                "size",
                "is_inline",
                "is_alternate_screen_enabled",
            ],
        )
    }

    #[getter]
    fn backend(&self) -> &'static str {
        match lock(&self.shared.device).backend {
            Backend::Terminal => "terminal",
            Backend::Offscreen => "offscreen",
        }
    }

    #[getter]
    fn size(&self) -> PySize {
        PySize {
            inner: lock(&self.shared.device).size,
        }
    }

    #[getter]
    fn window_size_in_pixels(&self) -> Option<PySize> {
        let device = lock(&self.shared.device);
        device
            .window_size_in_pixels
            .or_else(|| {
                device.terminal.cell_size_in_pixels.map(|(width, height)| {
                    Size::new(
                        i32::from(width) * device.size.width,
                        i32::from(height) * device.size.height,
                    )
                })
            })
            .map(|inner| PySize { inner })
    }

    #[getter]
    fn capabilities(&self) -> PyTerminalCapabilities {
        let device = lock(&self.shared.device);
        PyTerminalCapabilities {
            is_terminal: device.terminal.is_terminal,
            is_live_terminal_available: device.terminal.is_live_terminal_available,
            color_profile: device.terminal.color_profile,
            graphics_protocol: device.terminal.graphics_protocol,
            cell_size_in_pixels: device.terminal.cell_size_in_pixels,
            synchronized_output: device.terminal.synchronized_output,
        }
    }

    #[getter]
    fn keyboard(&self) -> PyKeyboardCapabilities {
        let device = lock(&self.shared.device);
        PyKeyboardCapabilities {
            enhancement: device.keyboard.enhancement,
            unavailable_reason: device.keyboard.unavailable_reason.clone(),
            enabled_features: device.modes.keyboard_features.clone(),
        }
    }

    #[getter]
    fn is_focused(&self) -> bool {
        lock(&self.shared.device).is_focused
    }

    #[getter]
    fn is_inline(&self) -> bool {
        lock(&self.shared.device).is_inline
    }

    #[getter]
    fn is_raw_mode_enabled(&self) -> bool {
        lock(&self.shared.device).modes.is_raw_mode_enabled
    }

    #[getter]
    fn is_mouse_capture_enabled(&self) -> bool {
        lock(&self.shared.device).modes.is_mouse_capture_enabled
    }

    #[getter]
    fn is_bracketed_paste_enabled(&self) -> bool {
        lock(&self.shared.device).modes.is_bracketed_paste_enabled
    }

    #[getter]
    fn is_focus_reporting_enabled(&self) -> bool {
        lock(&self.shared.device).modes.is_focus_reporting_enabled
    }

    #[getter]
    fn is_alternate_screen_enabled(&self) -> bool {
        lock(&self.shared.device).modes.is_alternate_screen_enabled
    }
}

#[pyclass(name = "HitArea", module = "xnano_core._xnano_core", frozen)]
pub struct PyHitArea {
    data: Arc<Mutex<HitAreaData>>,
    shared: Arc<RuntimeShared>,
}

#[pymethods]
impl PyHitArea {
    #[getter]
    fn key(&self) -> String {
        lock(&self.data).key.clone()
    }

    #[getter]
    fn bounds(&self) -> PyRectangle {
        PyRectangle {
            inner: lock(&self.data).bounds,
        }
    }

    #[setter]
    fn set_bounds(&self, value: &PyRectangle) {
        lock(&self.data).bounds = value.inner;
    }

    fn remove(&self) {
        lock(&self.data).is_removed = true;
        lock(&self.shared.router)
            .hit_areas
            .retain(|area| !Arc::ptr_eq(area, &self.data));
    }

    fn __repr__(&self) -> String {
        format!("HitArea(key={:?})", self.key())
    }
}

#[pyclass(name = "FocusScope", module = "xnano_core._xnano_core", frozen)]
pub struct PyFocusScope {
    id: u64,
    shared: Arc<RuntimeShared>,
    is_active: Arc<AtomicBool>,
}

#[pymethods]
impl PyFocusScope {
    fn __repr__(slf: &Bound<'_, Self>) -> PyResult<String> {
        crate::reprs::described(slf.as_any(), &["is_active"])
    }

    #[getter]
    fn is_active(&self) -> bool {
        self.is_active.load(Ordering::SeqCst)
    }

    fn close(&self) {
        self.is_active.store(false, Ordering::SeqCst);
        lock(&self.shared.router)
            .scopes
            .retain(|scope| scope.id != self.id);
    }

    fn __enter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    #[pyo3(signature = (exception_type = None, exception_value = None, traceback = None))]
    fn __exit__(
        &self,
        exception_type: Option<&Bound<'_, PyAny>>,
        exception_value: Option<&Bound<'_, PyAny>>,
        traceback: Option<&Bound<'_, PyAny>>,
    ) -> bool {
        let _ = (exception_type, exception_value, traceback);
        self.close();
        false
    }
}

#[pyclass(name = "InputRouter", module = "xnano_core._xnano_core", frozen)]
pub struct PyInputRouter {
    pub shared: Arc<RuntimeShared>,
}

fn target_parts(
    target: &Bound<'_, PyAny>,
) -> PyResult<(
    Arc<xnano_terminal_runtime::buffer::BufferCore>,
    Option<Rectangle>,
)> {
    let surface = target
        .extract::<PyRef<'_, PySurface>>()
        .map_err(|_| PyTypeError::new_err("the target must be a Buffer or a Region"))?;
    Ok((Arc::clone(&surface.core), surface.region))
}

#[pymethods]
impl PyInputRouter {
    fn __repr__(slf: &Bound<'_, Self>) -> PyResult<String> {
        crate::reprs::described(slf.as_any(), &[])
    }

    #[pyo3(signature = (callback, *, target, events = None, binding = None, priority = 0))]
    fn on(
        &self,
        py: Python<'_>,
        callback: Py<PyAny>,
        target: &Bound<'_, PyAny>,
        events: Option<&Bound<'_, PyAny>>,
        binding: Option<&Bound<'_, PyAny>>,
        priority: i32,
    ) -> PyResult<PyHook> {
        if !callback.bind(py).is_callable() {
            return Err(PyTypeError::new_err("an input callback must be callable"));
        }
        let (core, region) = target_parts(target)?;
        let kinds = match events {
            Some(names) => HookEvent::parse_all(names)?,
            None => vec![
                HookEvent::parse("key")?,
                HookEvent::parse("mouse")?,
                HookEvent::parse("paste")?,
            ],
        };
        let binding = binding
            .filter(|value| !value.is_none())
            .map(binding_arg)
            .transpose()?;
        let ext =
            ext_of(&core).ok_or_else(|| PyTypeError::new_err("the target is not a buffer"))?;
        let entry = Arc::new(HookEntry::new(
            callback, None, kinds, binding, priority, false, region,
        ));
        let hook = PyHook::new(Arc::clone(&entry.state));
        lock(&ext.hooks).push(entry);
        Ok(hook)
    }

    #[pyo3(signature = (key, *, target, bounds, layer = 0))]
    fn hit_area(
        &self,
        key: String,
        target: &Bound<'_, PyAny>,
        bounds: &PyRectangle,
        layer: i32,
    ) -> PyResult<PyHitArea> {
        let (core, region) = target_parts(target)?;
        let offset = region.unwrap_or_default();
        let mut router = lock(&self.shared.router);
        router.next_id += 1;
        let data = Arc::new(Mutex::new(HitAreaData {
            id: router.next_id,
            key,
            target: core,
            bounds: bounds.inner.translate(offset.x, offset.y),
            layer,
            is_removed: false,
        }));
        router.hit_areas.push(Arc::clone(&data));
        Ok(PyHitArea {
            data,
            shared: Arc::clone(&self.shared),
        })
    }

    fn hit_test<'py>(
        &self,
        py: Python<'py>,
        column: i32,
        row: i32,
    ) -> PyResult<Bound<'py, PyTuple>> {
        let areas = hit_areas_at(&self.shared, column, row);
        let items = areas
            .into_iter()
            .map(|data| PyHitArea {
                data,
                shared: Arc::clone(&self.shared),
            })
            .collect::<Vec<_>>();
        PyTuple::new(py, items)
    }

    #[pyo3(signature = (target, *, modal = false))]
    fn scope(&self, target: &Bound<'_, PyAny>, modal: bool) -> PyResult<PyFocusScope> {
        let (core, _) = target_parts(target)?;
        let mut router = lock(&self.shared.router);
        router.next_id += 1;
        let id = router.next_id;
        let is_active = Arc::new(AtomicBool::new(true));
        router.scopes.push(ScopeData {
            id,
            target: core,
            is_modal: modal,
            is_active: Arc::clone(&is_active),
        });
        Ok(PyFocusScope {
            id,
            shared: Arc::clone(&self.shared),
            is_active,
        })
    }

    fn focus(&self, target: &Bound<'_, PyAny>) -> PyResult<bool> {
        let (core, _) = target_parts(target)?;
        Ok(focus_buffer(&self.shared, &core))
    }

    fn clear_focus(&self) {
        lock(&self.shared.router).focused = None;
        self.shared.request_frame();
    }
}

/// Hit areas under a point, topmost first.
pub fn hit_areas_at(shared: &RuntimeShared, column: i32, row: i32) -> Vec<Arc<Mutex<HitAreaData>>> {
    let areas: Vec<Arc<Mutex<HitAreaData>>> = lock(&shared.router).hit_areas.clone();
    let mut hits: Vec<(i32, usize, Arc<Mutex<HitAreaData>>)> = Vec::new();
    for (order, area) in areas.into_iter().enumerate() {
        let data = lock(&area);
        if data.is_removed || !data.target.lock().is_visible {
            continue;
        }
        let origin = absolute_origin(&data.target);
        let absolute = data.bounds.translate(origin.0, origin.1);
        if absolute.contains(Point::new(column, row)) {
            hits.push((data.layer, order, Arc::clone(&area)));
        }
    }
    hits.sort_by_key(|(layer, order, _)| (std::cmp::Reverse(*layer), std::cmp::Reverse(*order)));
    hits.into_iter().map(|(_, _, area)| area).collect()
}

/// Give `core` the focus when it can take it.
pub fn focus_buffer(
    shared: &RuntimeShared,
    core: &Arc<xnano_terminal_runtime::buffer::BufferCore>,
) -> bool {
    {
        let state = core.lock();
        if !state.is_focusable || !state.is_mounted {
            return false;
        }
    }
    let mut router = lock(&shared.router);
    if let Some(scope) = router
        .scopes
        .iter()
        .rev()
        .find(|scope| scope.is_modal && scope.is_active.load(Ordering::SeqCst))
    {
        let mut inside = false;
        let mut current = Some(Arc::clone(core));
        while let Some(node) = current {
            if Arc::ptr_eq(&node, &scope.target) {
                inside = true;
                break;
            }
            current = node.parent();
        }
        if !inside {
            return false;
        }
    }
    router.focused = Some(core.id);
    drop(router);
    nudge(core);
    true
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyKeyboardCapabilities>()?;
    m.add_class::<PyTerminalCapabilities>()?;
    m.add_class::<PyInputOptions>()?;
    m.add_class::<PyTerminalOptions>()?;
    m.add_class::<PyInputState>()?;
    m.add_class::<PyDevice>()?;
    m.add_class::<PyHitArea>()?;
    m.add_class::<PyFocusScope>()?;
    m.add_class::<PyInputRouter>()?;
    m.add_function(wrap_pyfunction!(query_keyboard_capabilities, m)?)?;
    m.add_function(wrap_pyfunction!(detect_terminal_capabilities, m)?)?;
    let _ = shared_of;
    Ok(())
}
