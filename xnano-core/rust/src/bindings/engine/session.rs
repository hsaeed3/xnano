use std::collections::HashMap;
use std::time::{Duration, Instant};

use crossterm::event;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use ratatui::buffer::Buffer;
use ratatui::layout::{Rect, Size};
use ratatui::{init, restore, DefaultTerminal};
use tachyonfx::EffectManager;

use super::clock::TickClock;
use super::events::PyEvent;
use super::panic_hook::{install_restore_panic_hook, PanicHookGuard};
use super::render_tree::{render_node, render_node_to_buffer, PyRenderNode, RenderContext};
use super::super::convert_core::{sync_from_core_buffer, sync_to_core_buffer, to_core_rect};
use super::super::crossterm_exec::{flush_stdout, io_to_py};
use super::super::cursor::{
    get_cursor_position_impl, hide_cursor_impl, move_cursor_to_impl, restore_cursor_position_impl,
    save_cursor_position_impl, set_cursor_style_impl, show_cursor_impl, PyCursorStyle,
};
use super::super::event_setup::{
    disable_bracketed_paste_impl, disable_focus_change_impl, disable_mouse_capture_impl,
    enable_bracketed_paste_impl, enable_focus_change_impl, enable_mouse_capture_impl,
    pop_keyboard_enhancement_flags_impl, push_keyboard_enhancement_flags_impl,
    PyKeyboardEnhancementFlags,
};
use super::super::frame_ext::frame_hide_cursor;
use super::super::fx::PyEffect;
use super::super::layout::{PyRect, PySize};
use super::super::terminal::{PyCompletedFrame, PyFrame};
use super::super::terminal_device::{
    begin_synchronized_update_impl, clear_terminal_impl, disable_raw_mode_impl,
    enable_raw_mode_impl, end_synchronized_update_impl, enter_alternate_screen_impl,
    leave_alternate_screen_impl, scroll_down_impl, scroll_up_impl, set_terminal_title_impl,
    terminal_size_impl, terminal_window_size_impl, PyClearType,
};
use super::super::buffer::PyBuffer;
use super::super::widgets_extra::PyPosition;

#[pyclass(name = "CoreTerminalRef", module = "xnano_core.rust.engine", unsendable)]
pub struct PyTerminalRef {
    ptr: usize,
}

impl PyTerminalRef {
    fn terminal_mut(&mut self) -> PyResult<&mut DefaultTerminal> {
        if self.ptr == 0 {
            return Err(PyRuntimeError::new_err("terminal reference expired"));
        }
        Ok(unsafe { &mut *(self.ptr as *mut DefaultTerminal) })
    }
}

#[pymethods]
impl PyTerminalRef {
    fn draw(&mut self, callback: PyObject) -> PyResult<()> {
        let terminal = self.terminal_mut()?;
        terminal
            .draw(|frame| {
                if let Err(err) = Python::with_gil(|py| {
                    let py_frame = PyFrame::from_frame(frame);
                    callback.call1(py, (py_frame,))
                }) {
                    Python::with_gil(|py| err.print(py));
                }
            })
            .map_err(io_to_py)?;
        Ok(())
    }

    fn try_draw(&mut self, callback: PyObject) -> PyResult<PyCompletedFrame> {
        let terminal = self.terminal_mut()?;
        let mut callback_error: Option<PyErr> = None;
        let completed = terminal
            .try_draw(|frame| {
                Python::with_gil(|py| -> Result<(), std::io::Error> {
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
            .map_err(io_to_py)?;

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
        self.terminal_mut()?.flush().map_err(io_to_py)
    }

    fn clear(&mut self) -> PyResult<()> {
        self.terminal_mut()?.clear().map_err(io_to_py)
    }

    fn size(&self) -> PyResult<PySize> {
        // SAFETY: read-only access to terminal size.
        let terminal = unsafe { &*(self.ptr as *const DefaultTerminal) };
        terminal
            .size()
            .map(|size| PySize { inner: size })
            .map_err(io_to_py)
    }
}

#[pyclass(name = "CoreSession", module = "xnano_core.rust.engine", unsendable)]
pub struct PySession {
    terminal: Option<DefaultTerminal>,
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
    cursor_style: PyCursorStyle,
    title: Option<String>,
    last_frame_at: Instant,
    last_frame_area: Option<Rect>,
    effect_areas: HashMap<String, Rect>,
    _panic_hook_guard: Option<PanicHookGuard>,
}

#[pymethods]
impl PySession {
    #[staticmethod]
    #[pyo3(signature = (*, tick_rate_ms = None))]
    fn init(tick_rate_ms: Option<u64>) -> PyResult<Self> {
        let panic_guard = install_restore_panic_hook();
        let terminal = init();
        Ok(Self {
            terminal: Some(terminal),
            offscreen_buffer: None,
            effect_manager: EffectManager::default(),
            tick_clock: TickClock::new(tick_rate_ms.unwrap_or(0)),
            raw_mode: true,
            mouse_capture: false,
            bracketed_paste: false,
            focus_change: false,
            alternate_screen: true,
            synchronized_updates: false,
            cursor_visible: true,
            cursor_style: PyCursorStyle::DefaultUserShape,
            title: None,
            last_frame_at: Instant::now(),
            last_frame_area: None,
            effect_areas: HashMap::new(),
            _panic_hook_guard: Some(panic_guard),
        })
    }

    #[staticmethod]
    fn offscreen(width: u16, height: u16) -> PyResult<Self> {
        Ok(Self {
            terminal: None,
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
            cursor_style: PyCursorStyle::DefaultUserShape,
            title: None,
            last_frame_at: Instant::now(),
            last_frame_area: Some(Rect::new(0, 0, width, height)),
            effect_areas: HashMap::new(),
            _panic_hook_guard: None,
        })
    }

    fn render(&mut self, node: &PyRenderNode) -> PyResult<()> {
        let now = Instant::now();
        let elapsed_ms = now.duration_since(self.last_frame_at).as_millis() as u32;
        self.last_frame_at = now;

        let mut ctx = RenderContext::default();

        if let Some(terminal) = self.terminal.as_mut() {
            let area = terminal.get_frame().area();
            self.last_frame_area = Some(area);
            let cursor_visible = self.cursor_visible;
            let effect_manager = &mut self.effect_manager;

            terminal
                .draw(|frame| {
                    let cursor = match render_node(frame, area, node, &mut ctx) {
                        Ok(c) => c,
                        Err(err) => {
                            ctx.error = Some(err);
                            None
                        }
                    };

                    let mut core = sync_to_core_buffer(frame.buffer_mut());
                    effect_manager.process_effects(
                        tachyonfx::Duration::from_millis(elapsed_ms),
                        &mut core,
                        to_core_rect(area),
                    );
                    sync_from_core_buffer(&core, frame.buffer_mut());

                    match cursor {
                        Some(pos) if cursor_visible => frame.set_cursor_position(pos),
                        _ => frame_hide_cursor(frame),
                    }
                })
                .map_err(io_to_py)?;

            if let Some(err) = ctx.error.take() {
                return Err(err);
            }
            self.effect_areas = ctx.effect_areas;
            Ok(())
        } else if let Some(buffer) = self.offscreen_buffer.as_mut() {
            let area = buffer.area;
            self.last_frame_area = Some(area);

            render_node_to_buffer(buffer, area, node, &mut ctx)?;

            let mut core = sync_to_core_buffer(buffer);
            self.effect_manager.process_effects(
                tachyonfx::Duration::from_millis(elapsed_ms),
                &mut core,
                to_core_rect(area),
            );
            sync_from_core_buffer(&core, buffer);

            if let Some(err) = ctx.error.take() {
                return Err(err);
            }
            self.effect_areas = ctx.effect_areas;
            Ok(())
        } else {
            Err(PyRuntimeError::new_err("session closed"))
        }
    }

    #[pyo3(signature = (timeout_ms = 16))]
    fn poll_event(&mut self, py: Python<'_>, timeout_ms: u64) -> PyResult<Option<PyEvent>> {
        if self.terminal.is_none() {
            py.check_signals()?;
            if self.tick_clock.due() {
                let elapsed = self.tick_clock.elapsed_since_last_tick_ms();
                self.tick_clock.reset();
                return Ok(Some(PyEvent::tick(elapsed)));
            }
            return Ok(None);
        }

        let user_budget = Duration::from_millis(timeout_ms);
        let tick_budget = self.tick_clock.time_until_tick();
        let budget = tick_budget.min(user_budget);

        let ready = py
            .allow_threads(|| event::poll(budget))
            .map_err(io_to_py)?;

        py.check_signals()?;

        if ready {
            let ev = py.allow_threads(event::read).map_err(io_to_py)?;
            return Ok(Some(PyEvent::from_crossterm(ev)));
        }
        if self.tick_clock.due() {
            let elapsed = self.tick_clock.elapsed_since_last_tick_ms();
            self.tick_clock.reset();
            return Ok(Some(PyEvent::tick(elapsed)));
        }
        Ok(None)
    }

    fn read_event(&mut self, py: Python<'_>) -> PyResult<PyEvent> {
        loop {
            if let Some(ev) = self.poll_event(py, u64::MAX / 2)? {
                return Ok(ev);
            }
        }
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
        self.effect_areas
            .get(key)
            .map(|r| PyRect { inner: *r })
    }

    fn buffer_snapshot(&mut self) -> PyResult<PyBuffer> {
        if let Some(t) = self.terminal.as_mut() {
            Ok(PyBuffer {
                inner: t.get_frame().buffer_mut().clone(),
            })
        } else if let Some(b) = &self.offscreen_buffer {
            Ok(PyBuffer {
                inner: b.clone(),
            })
        } else {
            Err(PyRuntimeError::new_err("session closed"))
        }
    }

    fn get_terminal(&mut self) -> PyResult<PyTerminalRef> {
        if let Some(terminal) = self.terminal.as_mut() {
            Ok(PyTerminalRef {
                ptr: terminal as *mut DefaultTerminal as usize,
            })
        } else {
            Err(PyRuntimeError::new_err("session has no live terminal"))
        }
    }

    fn enable_raw_mode(&mut self) -> PyResult<()> {
        enable_raw_mode_impl()?;
        self.raw_mode = true;
        Ok(())
    }

    fn disable_raw_mode(&mut self) -> PyResult<()> {
        disable_raw_mode_impl()?;
        self.raw_mode = false;
        Ok(())
    }

    fn enable_mouse_capture(&mut self) -> PyResult<()> {
        enable_mouse_capture_impl()?;
        self.mouse_capture = true;
        Ok(())
    }

    fn disable_mouse_capture(&mut self) -> PyResult<()> {
        disable_mouse_capture_impl()?;
        self.mouse_capture = false;
        Ok(())
    }

    fn enable_bracketed_paste(&mut self) -> PyResult<()> {
        enable_bracketed_paste_impl()?;
        self.bracketed_paste = true;
        Ok(())
    }

    fn disable_bracketed_paste(&mut self) -> PyResult<()> {
        disable_bracketed_paste_impl()?;
        self.bracketed_paste = false;
        Ok(())
    }

    fn enable_focus_change(&mut self) -> PyResult<()> {
        enable_focus_change_impl()?;
        self.focus_change = true;
        Ok(())
    }

    fn disable_focus_change(&mut self) -> PyResult<()> {
        disable_focus_change_impl()?;
        self.focus_change = false;
        Ok(())
    }

    fn enter_alternate_screen(&mut self) -> PyResult<()> {
        enter_alternate_screen_impl()?;
        self.alternate_screen = true;
        Ok(())
    }

    fn leave_alternate_screen(&mut self) -> PyResult<()> {
        leave_alternate_screen_impl()?;
        self.alternate_screen = false;
        Ok(())
    }

    fn push_keyboard_enhancement_flags(
        &mut self,
        flags: PyKeyboardEnhancementFlags,
    ) -> PyResult<()> {
        push_keyboard_enhancement_flags_impl(flags)
    }

    fn pop_keyboard_enhancement_flags(&mut self) -> PyResult<()> {
        pop_keyboard_enhancement_flags_impl()
    }

    fn show_cursor(&mut self) -> PyResult<()> {
        show_cursor_impl()?;
        self.cursor_visible = true;
        Ok(())
    }

    fn hide_cursor(&mut self) -> PyResult<()> {
        hide_cursor_impl()?;
        self.cursor_visible = false;
        Ok(())
    }

    fn set_cursor_style(&mut self, style: PyCursorStyle) -> PyResult<()> {
        set_cursor_style_impl(style)?;
        self.cursor_style = style;
        Ok(())
    }

    fn get_cursor_style(&self) -> PyCursorStyle {
        self.cursor_style
    }

    fn move_cursor_to(&mut self, x: u16, y: u16) -> PyResult<()> {
        move_cursor_to_impl(x, y)
    }

    fn save_cursor_position(&mut self) -> PyResult<()> {
        save_cursor_position_impl()
    }

    fn restore_cursor_position(&mut self) -> PyResult<()> {
        restore_cursor_position_impl()
    }

    fn get_cursor_position(&self) -> PyResult<PyPosition> {
        get_cursor_position_impl()
    }

    fn get_size(&self) -> PyResult<PySize> {
        if let Some(buffer) = &self.offscreen_buffer {
            let area = buffer.area();
            return Ok(PySize {
                inner: Size::new(area.width, area.height),
            });
        }
        terminal_size_impl()
    }

    fn get_window_size(&self) -> PyResult<PySize> {
        if let Some(buffer) = &self.offscreen_buffer {
            let area = buffer.area();
            return Ok(PySize {
                inner: Size::new(area.width, area.height),
            });
        }
        terminal_window_size_impl()
    }

    fn get_last_frame_area(&self) -> Option<PyRect> {
        self.last_frame_area.map(|r| PyRect { inner: r })
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

    fn is_cursor_visible(&self) -> bool {
        self.cursor_visible
    }

    fn clear(&mut self, clear_type: PyClearType) -> PyResult<()> {
        clear_terminal_impl(clear_type)
    }

    fn set_title(&mut self, title: &str) -> PyResult<()> {
        set_terminal_title_impl(title)?;
        self.title = Some(title.to_owned());
        Ok(())
    }

    fn get_title(&self) -> Option<String> {
        self.title.clone()
    }

    fn scroll_up(&mut self, count: u16) -> PyResult<()> {
        scroll_up_impl(count)
    }

    fn scroll_down(&mut self, count: u16) -> PyResult<()> {
        scroll_down_impl(count)
    }

    fn begin_synchronized_update(&mut self) -> PyResult<()> {
        begin_synchronized_update_impl()?;
        self.synchronized_updates = true;
        Ok(())
    }

    fn end_synchronized_update(&mut self) -> PyResult<()> {
        end_synchronized_update_impl()?;
        self.synchronized_updates = false;
        Ok(())
    }

    fn teardown_device_state(&mut self) {
        // Always emit the disable sequences — ratatui::restore() does not
        // turn off mouse capture, and the mirror flags can be wrong after an
        // abnormal exit.  Ignore errors: cleanup must be best-effort.
        let _ = disable_mouse_capture_impl();
        self.mouse_capture = false;
        let _ = disable_bracketed_paste_impl();
        self.bracketed_paste = false;
        let _ = disable_focus_change_impl();
        self.focus_change = false;
        if self.synchronized_updates {
            let _ = end_synchronized_update_impl();
            self.synchronized_updates = false;
        }
        if !self.cursor_visible {
            let _ = show_cursor_impl();
            self.cursor_visible = true;
        }
        let _ = flush_stdout();
    }

    fn restore(&mut self) -> PyResult<()> {
        self.teardown_device_state();
        if self.terminal.is_some() {
            restore();
            self.terminal.take();
        }
        self._panic_hook_guard = None;
        Ok(())
    }

    fn __enter__(slf: Py<Self>) -> Py<Self> {
        slf
    }

    #[pyo3(signature = (exc_type = None, exc_value = None, traceback = None))]
    fn __exit__(
        &mut self,
        exc_type: Option<PyObject>,
        exc_value: Option<PyObject>,
        traceback: Option<PyObject>,
    ) -> PyResult<bool> {
        let _ = (exc_type, exc_value, traceback);
        self.restore()?;
        Ok(false)
    }
}

impl Drop for PySession {
    fn drop(&mut self) {
        if self.terminal.is_some() {
            let _ = self.restore();
        }
    }
}
