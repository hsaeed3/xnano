//! Buffer-backed ``CoreSession`` for builds without the ``terminal`` feature.
//!
//! Emscripten / Pyodide wheels ship with ``--no-default-features`` because
//! crossterm cannot compile to wasm. The full layout / render engine
//! (``CoreRenderNode``, ``CoreRenderIR``, constraints, widgets, buffer)
//! still ships; only the live crossterm ``DefaultTerminal`` path is
//! unavailable.
//!
//! This module exposes a real ``CoreSession`` that paints into an
//! in-memory ratatui ``Buffer`` — the same path the native
//! :meth:`CoreSession.offscreen` factory uses. That gives correct layout,
//! borders, gaps, and alignment for single-frame rendering. There is no
//! OS terminal, so keyboard / mouse / resize events and the interactive
//! run loop remain unavailable.

use std::collections::HashMap;
use std::time::Instant;

use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyTuple};
use ratatui::buffer::Buffer;
use ratatui::layout::{Rect, Size};
use tachyonfx::EffectManager;

use super::super::buffer::PyBuffer;
use super::super::convert_core::{sync_from_core_buffer, sync_to_core_buffer, to_core_rect};
use super::super::fx::PyEffect;
use super::super::layout::{PyRect, PySize};
use super::super::widgets_extra::PyPosition;
use super::clock::TickClock;
use super::events::PyEvent;
use super::render_tree::{render_node_to_buffer, PyRenderNode, RenderContext};

const LIVE_UNSUPPORTED: &str = "the xnano-core live terminal engine is not \
     available on Emscripten/WebAssembly builds; use CoreSession.offscreen() \
     for buffer-backed single-frame rendering";

const NO_LIVE_TERMINAL: &str = "session has no live terminal \
     (buffer-backed / wasm session)";

#[pyclass(name = "CoreSession", module = "xnano_core.rust.engine", unsendable)]
pub struct PySession {
    offscreen_buffer: Option<Buffer>,
    effect_manager: EffectManager<String>,
    tick_clock: TickClock,
    raw_mode: bool,
    mouse_capture: bool,
    bracketed_paste: bool,
    focus_change: bool,
    alternate_screen: bool,
    synchronized_updates: bool,
    cursor_visible: bool,
    cursor_x: u16,
    cursor_y: u16,
    title: Option<String>,
    last_frame_at: Instant,
    last_frame_area: Option<Rect>,
    effect_areas: HashMap<String, Rect>,
    inline_height: Option<u16>,
}

impl PySession {
    fn require_buffer(&mut self) -> PyResult<&mut Buffer> {
        self.offscreen_buffer
            .as_mut()
            .ok_or_else(|| PyRuntimeError::new_err("session closed"))
    }

    fn buffer_area(&self) -> PyResult<Rect> {
        self.offscreen_buffer
            .as_ref()
            .map(|b| b.area)
            .ok_or_else(|| PyRuntimeError::new_err("session closed"))
    }
}

#[pymethods]
impl PySession {
    /// Whether this build can claim a live crossterm terminal.
    ///
    /// Always ``False`` for ``--no-default-features`` (wasm) builds.
    #[staticmethod]
    fn supports_live_terminal() -> bool {
        false
    }

    /// Whether this session paints into an in-memory buffer (always true here).
    fn is_buffer_backed(&self) -> bool {
        true
    }

    #[staticmethod]
    #[pyo3(signature = (*, tick_rate_ms = None, inline_height = None))]
    fn init(tick_rate_ms: Option<u64>, inline_height: Option<u16>) -> PyResult<Self> {
        let _ = (tick_rate_ms, inline_height);
        Err(PyRuntimeError::new_err(LIVE_UNSUPPORTED))
    }

    #[staticmethod]
    fn offscreen(width: u16, height: u16) -> PyResult<Self> {
        let width = width.max(1);
        let height = height.max(1);
        Ok(Self {
            offscreen_buffer: Some(Buffer::empty(Rect::new(0, 0, width, height))),
            effect_manager: EffectManager::default(),
            tick_clock: TickClock::new(0),
            raw_mode: false,
            mouse_capture: false,
            bracketed_paste: false,
            focus_change: false,
            alternate_screen: false,
            synchronized_updates: false,
            cursor_visible: false,
            cursor_x: 0,
            cursor_y: 0,
            title: None,
            last_frame_at: Instant::now(),
            last_frame_area: Some(Rect::new(0, 0, width, height)),
            effect_areas: HashMap::new(),
            inline_height: None,
        })
    }

    /// Render one frame into the in-memory buffer.
    ///
    /// Uses the full layout/constraint solver and widget paint path —
    /// identical to the native offscreen backend. No crossterm I/O occurs.
    fn render(&mut self, node: &PyRenderNode) -> PyResult<()> {
        let now = Instant::now();
        let elapsed_ms = now.duration_since(self.last_frame_at).as_millis() as u32;
        self.last_frame_at = now;

        let mut ctx = RenderContext::default();

        // Partial field borrows (same pattern as the native offscreen path)
        // so ``effect_manager`` can be used alongside the buffer.
        let Some(buffer) = self.offscreen_buffer.as_mut() else {
            return Err(PyRuntimeError::new_err("session closed"));
        };
        let area = buffer.area;
        self.last_frame_area = Some(area);

        render_node_to_buffer(buffer, area, node, &mut ctx)?;

        if self.effect_manager.is_running() {
            let mut core = sync_to_core_buffer(buffer);
            self.effect_manager.process_effects(
                tachyonfx::Duration::from_millis(elapsed_ms),
                &mut core,
                to_core_rect(area),
            );
            sync_from_core_buffer(&core, buffer);
        }

        if let Some(err) = ctx.error.take() {
            return Err(err);
        }
        self.effect_areas = ctx.effect_areas;
        Ok(())
    }

    #[pyo3(signature = (timeout_ms = 16))]
    fn poll_event(&mut self, py: Python<'_>, timeout_ms: u64) -> PyResult<Option<PyEvent>> {
        let _ = timeout_ms;
        py.check_signals()?;
        if self.tick_clock.due() {
            let elapsed = self.tick_clock.elapsed_since_last_tick_ms();
            self.tick_clock.reset();
            return Ok(Some(PyEvent::tick(elapsed)));
        }
        Ok(None)
    }

    fn read_event(&mut self, py: Python<'_>) -> PyResult<PyEvent> {
        // No OS input stream exists on wasm. Spinning forever would hang the
        // browser's Python runtime; fail loudly instead.
        let _ = py;
        Err(PyRuntimeError::new_err(
            "CoreSession.read_event is not available on buffer-backed \
             (wasm) sessions; there is no OS terminal input stream",
        ))
    }

    fn add_effect(&mut self, effect: PyEffect) {
        self.effect_manager.add_effect(effect.inner);
    }

    fn add_unique_effect(&mut self, key: String, effect: PyEffect) {
        self.effect_manager.add_unique_effect(key, effect.inner);
    }

    fn cancel_effect(&mut self, key: String) {
        self.effect_manager.cancel_unique_effect(key);
    }

    fn is_animating(&self) -> bool {
        self.effect_manager.is_running()
    }

    fn effect_area_for(&self, key: &str) -> Option<PyRect> {
        self.effect_areas.get(key).map(|r| PyRect { inner: *r })
    }

    fn buffer_snapshot(&mut self) -> PyResult<PyBuffer> {
        let buffer = self.require_buffer()?;
        Ok(PyBuffer {
            inner: buffer.clone(),
        })
    }

    fn get_terminal(&mut self) -> PyResult<PyTerminalRef> {
        Err(PyRuntimeError::new_err(NO_LIVE_TERMINAL))
    }

    fn enable_raw_mode(&mut self) -> PyResult<()> {
        self.raw_mode = true;
        Ok(())
    }

    fn disable_raw_mode(&mut self) -> PyResult<()> {
        self.raw_mode = false;
        Ok(())
    }

    fn enable_mouse_capture(&mut self) -> PyResult<()> {
        self.mouse_capture = true;
        Ok(())
    }

    fn disable_mouse_capture(&mut self) -> PyResult<()> {
        self.mouse_capture = false;
        Ok(())
    }

    fn enable_bracketed_paste(&mut self) -> PyResult<()> {
        self.bracketed_paste = true;
        Ok(())
    }

    fn disable_bracketed_paste(&mut self) -> PyResult<()> {
        self.bracketed_paste = false;
        Ok(())
    }

    fn enable_focus_change(&mut self) -> PyResult<()> {
        self.focus_change = true;
        Ok(())
    }

    fn disable_focus_change(&mut self) -> PyResult<()> {
        self.focus_change = false;
        Ok(())
    }

    fn enter_alternate_screen(&mut self) -> PyResult<()> {
        self.alternate_screen = true;
        Ok(())
    }

    fn leave_alternate_screen(&mut self) -> PyResult<()> {
        self.alternate_screen = false;
        Ok(())
    }

    fn push_keyboard_enhancement_flags(
        &mut self,
        flags: Bound<'_, PyAny>,
    ) -> PyResult<()> {
        let _ = flags;
        Ok(())
    }

    fn pop_keyboard_enhancement_flags(&mut self) -> PyResult<()> {
        Ok(())
    }

    fn show_cursor(&mut self) -> PyResult<()> {
        self.cursor_visible = true;
        Ok(())
    }

    fn hide_cursor(&mut self) -> PyResult<()> {
        self.cursor_visible = false;
        Ok(())
    }

    fn set_cursor_style(&mut self, style: Bound<'_, PyAny>) -> PyResult<()> {
        let _ = style;
        Ok(())
    }

    fn get_cursor_style(&self) -> String {
        // CursorStyle is a terminal-feature native enum; return the default
        // style name so Python can still query the mirror without importing
        // the missing type.
        "default".to_string()
    }

    fn move_cursor_to(&mut self, x: u16, y: u16) -> PyResult<()> {
        self.cursor_x = x;
        self.cursor_y = y;
        Ok(())
    }

    fn save_cursor_position(&mut self) -> PyResult<()> {
        Ok(())
    }

    fn restore_cursor_position(&mut self) -> PyResult<()> {
        Ok(())
    }

    fn get_cursor_position(&self) -> PyResult<PyPosition> {
        Ok(PyPosition {
            inner: ratatui::layout::Position::new(self.cursor_x, self.cursor_y),
        })
    }

    fn get_size(&self) -> PyResult<PySize> {
        let area = self.buffer_area()?;
        Ok(PySize {
            inner: Size::new(area.width, area.height),
        })
    }

    fn get_window_size(&self) -> PyResult<PySize> {
        self.get_size()
    }

    fn get_last_frame_area(&self) -> Option<PyRect> {
        self.last_frame_area.map(|r| PyRect { inner: r })
    }

    fn get_viewport_area(&mut self) -> PyResult<PyRect> {
        let area = self.buffer_area()?;
        Ok(PyRect { inner: area })
    }

    fn is_raw_mode_enabled(&self) -> bool {
        self.raw_mode
    }

    fn is_mouse_capture_enabled(&self) -> bool {
        self.mouse_capture
    }

    fn is_bracketed_paste_enabled(&self) -> bool {
        self.bracketed_paste
    }

    fn is_focus_change_enabled(&self) -> bool {
        self.focus_change
    }

    fn is_alternate_screen_enabled(&self) -> bool {
        self.alternate_screen
    }

    fn is_inline(&self) -> bool {
        self.inline_height.is_some()
    }

    fn get_inline_height(&self) -> Option<u16> {
        self.inline_height
    }

    fn is_cursor_visible(&self) -> bool {
        self.cursor_visible
    }

    fn clear(&mut self, clear_type: Bound<'_, PyAny>) -> PyResult<()> {
        let _ = clear_type;
        if let Some(buffer) = self.offscreen_buffer.as_mut() {
            let area = buffer.area;
            *buffer = Buffer::empty(area);
        }
        Ok(())
    }

    fn set_title(&mut self, title: &str) -> PyResult<()> {
        self.title = Some(title.to_owned());
        Ok(())
    }

    fn get_title(&self) -> Option<String> {
        self.title.clone()
    }

    fn scroll_up(&mut self, count: u16) -> PyResult<()> {
        let _ = count;
        Ok(())
    }

    fn scroll_down(&mut self, count: u16) -> PyResult<()> {
        let _ = count;
        Ok(())
    }

    fn begin_synchronized_update(&mut self) -> PyResult<()> {
        self.synchronized_updates = true;
        Ok(())
    }

    fn end_synchronized_update(&mut self) -> PyResult<()> {
        self.synchronized_updates = false;
        Ok(())
    }

    fn teardown_device_state(&mut self) {
        self.synchronized_updates = false;
        self.mouse_capture = false;
        self.bracketed_paste = false;
        self.focus_change = false;
        self.cursor_visible = false;
    }

    fn restore(&mut self) -> PyResult<()> {
        self.teardown_device_state();
        self.offscreen_buffer = None;
        Ok(())
    }

    fn __enter__(slf: Py<Self>) -> Py<Self> {
        slf
    }

    #[pyo3(signature = (exc_type = None, exc_value = None, traceback = None))]
    fn __exit__(
        &mut self,
        exc_type: Option<Py<PyAny>>,
        exc_value: Option<Py<PyAny>>,
        traceback: Option<Py<PyAny>>,
    ) -> PyResult<bool> {
        let _ = (exc_type, exc_value, traceback);
        self.restore()?;
        Ok(false)
    }
}

/// Scope-guarded live-terminal handle — always unavailable on wasm.
#[pyclass(
    name = "CoreTerminalRef",
    module = "xnano_core.rust.engine",
    unsendable
)]
pub struct PyTerminalRef;

#[pymethods]
impl PyTerminalRef {
    #[new]
    #[pyo3(signature = (*args, **kwargs))]
    fn new(
        args: &Bound<'_, PyTuple>,
        kwargs: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Self> {
        let _ = (args, kwargs);
        Err(PyRuntimeError::new_err(LIVE_UNSUPPORTED))
    }

    fn draw(&mut self, callback: Py<PyAny>) -> PyResult<()> {
        let _ = callback;
        Err(PyRuntimeError::new_err(NO_LIVE_TERMINAL))
    }

    fn try_draw(&mut self, callback: Py<PyAny>) -> PyResult<()> {
        let _ = callback;
        Err(PyRuntimeError::new_err(NO_LIVE_TERMINAL))
    }

    fn flush(&mut self) -> PyResult<()> {
        Err(PyRuntimeError::new_err(NO_LIVE_TERMINAL))
    }

    fn clear(&mut self) -> PyResult<()> {
        Err(PyRuntimeError::new_err(NO_LIVE_TERMINAL))
    }

    fn size(&self) -> PyResult<PySize> {
        Err(PyRuntimeError::new_err(NO_LIVE_TERMINAL))
    }
}
