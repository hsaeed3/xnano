use std::panic::{self, PanicHookInfo};
use std::sync::{Arc, Mutex};

use ratatui::restore;

use super::super::crossterm_exec::flush_stdout;
use super::super::event_setup::{
    disable_bracketed_paste_impl, disable_focus_change_impl, disable_mouse_capture_impl,
};
use super::super::terminal_device::end_synchronized_update_impl;

pub(crate) struct PanicHookGuard {
    previous: Arc<Mutex<Option<Box<dyn Fn(&PanicHookInfo<'_>) + Sync + Send>>>>,
}

pub(crate) fn install_restore_panic_hook() -> PanicHookGuard {
    let previous = panic::take_hook();
    let shared = Arc::new(Mutex::new(Some(previous)));
    let hook_shared = Arc::clone(&shared);
    panic::set_hook(Box::new(move |info| {
        let _ = disable_mouse_capture_impl();
        let _ = disable_bracketed_paste_impl();
        let _ = disable_focus_change_impl();
        let _ = end_synchronized_update_impl();
        let _ = flush_stdout();
        restore();
        if let Ok(guard) = hook_shared.lock() {
            if let Some(ref hook) = *guard {
                hook(info);
            }
        }
    }));
    PanicHookGuard { previous: shared }
}

impl Drop for PanicHookGuard {
    fn drop(&mut self) {
        let _ = panic::take_hook();
        if let Ok(mut guard) = self.previous.lock() {
            if let Some(hook) = guard.take() {
                panic::set_hook(hook);
            }
        }
    }
}