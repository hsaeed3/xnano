use std::panic::{self, PanicHookInfo};
use std::sync::{Arc, Mutex};

use ratatui::restore;

pub(crate) struct PanicHookGuard {
    previous: Arc<Mutex<Option<Box<dyn Fn(&PanicHookInfo<'_>) + Sync + Send>>>>,
}

pub(crate) fn install_restore_panic_hook() -> PanicHookGuard {
    let previous = panic::take_hook();
    let shared = Arc::new(Mutex::new(Some(previous)));
    let hook_shared = Arc::clone(&shared);
    panic::set_hook(Box::new(move |info| {
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