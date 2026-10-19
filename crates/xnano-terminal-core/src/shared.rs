//! State shared between a runtime and the objects that look into it.
//!
//! The runtime object lives on its owner thread. Everything another object (a device, an
//! input state, a waker, a buffer's expression environment) needs to see lives here, behind
//! locks, so those objects stay small and safe to hold.

use std::collections::{BTreeMap, BTreeSet, VecDeque};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Condvar, Mutex, MutexGuard, Weak};
use std::time::Duration;

use pyo3::prelude::*;
use pyo3::types::PyTuple;
use xnano_terminal_runtime::buffer::BufferCore;
use xnano_terminal_runtime::clock::Clock;
use xnano_terminal_runtime::device::{DeviceModes, KeyboardInfo, TerminalInfo};
use xnano_terminal_runtime::drawing::DrawingAnimation;
use xnano_terminal_runtime::event::Event;
use xnano_terminal_runtime::geometry::{Rectangle, Size};
use xnano_terminal_runtime::grid::Bounds;
use xnano_terminal_runtime::pixel::PixelEncoding;

pub fn lock<T>(mutex: &Mutex<T>) -> MutexGuard<'_, T> {
    mutex
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner)
}

/// A callback queued from another thread.
pub struct QueuedCall {
    pub function: Py<PyAny>,
    pub arguments: Py<PyTuple>,
}

#[derive(Default)]
struct QueueState {
    events: VecDeque<Event>,
    calls: VecDeque<QueuedCall>,
    is_wake_requested: bool,
    /// Threads blocked in `EventQueue::wait`. Counted under the lock, so a notifier that
    /// reads zero knows no thread can start waiting without first seeing what it queued.
    waiters: usize,
}

type Notifier = Arc<dyn Fn() + Send + Sync>;

/// Everything waiting to be processed by the owner thread.
pub struct EventQueue {
    state: Mutex<QueueState>,
    ready: Condvar,
    notifiers: Mutex<Vec<(u64, Notifier)>>,
    next_notifier: AtomicU64,
}

impl Default for EventQueue {
    fn default() -> Self {
        Self {
            state: Mutex::new(QueueState::default()),
            ready: Condvar::new(),
            notifiers: Mutex::new(Vec::new()),
            next_notifier: AtomicU64::new(1),
        }
    }
}

impl EventQueue {
    fn notify(&self) {
        // Reading the waiters under the lock orders this after a waiter has either seen the
        // new state or started waiting, so the wake-up cannot fall between its check and its
        // wait. Without a waiter there is nothing to wake, and `notify_all` would still cost a
        // system call on every queued event and frame request.
        if lock(&self.state).waiters > 0 {
            self.ready.notify_all();
        }
        let notifiers: Vec<Notifier> = {
            let registered = lock(&self.notifiers);
            if registered.is_empty() {
                return;
            }
            registered
                .iter()
                .map(|(_, notifier)| Arc::clone(notifier))
                .collect()
        };
        for notifier in notifiers {
            notifier();
        }
    }

    pub fn push_event(&self, event: Event) {
        lock(&self.state).events.push_back(event);
        self.notify();
    }

    pub fn push_call(&self, call: QueuedCall) {
        lock(&self.state).calls.push_back(call);
        self.notify();
    }

    /// Wake anything waiting on the queue without queuing a wake event.
    pub fn nudge(&self) {
        self.notify();
    }

    /// Wake the threads blocked in [`EventQueue::wait`], and nothing else.
    ///
    /// Unlike [`EventQueue::nudge`] it calls no registered notifier, so it is safe to call
    /// from code that holds a buffer lock.
    pub fn wake_waiters(&self) {
        if lock(&self.state).waiters > 0 {
            self.ready.notify_all();
        }
    }

    pub fn request_wake(&self) {
        lock(&self.state).is_wake_requested = true;
        self.notify();
    }

    pub fn pop_event(&self) -> Option<Event> {
        lock(&self.state).events.pop_front()
    }

    pub fn pop_call(&self) -> Option<QueuedCall> {
        lock(&self.state).calls.pop_front()
    }

    pub fn take_wake(&self) -> bool {
        std::mem::take(&mut lock(&self.state).is_wake_requested)
    }

    pub fn has_pending(&self) -> bool {
        let state = lock(&self.state);
        !state.events.is_empty() || !state.calls.is_empty() || state.is_wake_requested
    }

    /// Block until something is queued, `should_return` says so, or `timeout` passes.
    /// `None` waits without limit.
    pub fn wait(&self, timeout: Option<Duration>, should_return: impl Fn() -> bool) {
        let mut state = lock(&self.state);
        if !state.events.is_empty()
            || !state.calls.is_empty()
            || state.is_wake_requested
            || should_return()
        {
            return;
        }
        state.waiters += 1;
        let mut state = match timeout {
            Some(timeout) => match self.ready.wait_timeout(state, timeout) {
                Ok((state, _)) => state,
                Err(poisoned) => poisoned.into_inner().0,
            },
            None => match self.ready.wait(state) {
                Ok(state) => state,
                Err(poisoned) => poisoned.into_inner(),
            },
        };
        state.waiters -= 1;
    }

    /// Call `notifier` (from any thread) whenever something is queued.
    pub fn add_notifier(&self, notifier: Notifier) -> u64 {
        let id = self.next_notifier.fetch_add(1, Ordering::SeqCst);
        lock(&self.notifiers).push((id, notifier));
        id
    }

    pub fn remove_notifier(&self, id: u64) {
        lock(&self.notifiers).retain(|(existing, _)| *existing != id);
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Backend {
    Terminal,
    Offscreen,
}

pub struct DeviceData {
    pub backend: Backend,
    pub size: Size,
    pub window_size_in_pixels: Option<Size>,
    pub terminal: TerminalInfo,
    pub keyboard: KeyboardInfo,
    pub modes: DeviceModes,
    pub is_focused: bool,
    pub is_inline: bool,
}

#[derive(Default)]
pub struct InputData {
    pub pressed: BTreeSet<String>,
    pub estimated: BTreeMap<String, f64>,
    pub held_keys_available: bool,
    pub pointer: Option<(i32, i32)>,
    pub estimate_timeout: Option<f64>,
    /// The key of the latest key event, until an event of another kind replaces it.
    pub last_key: Option<String>,
    pub last_key_kind: Option<&'static str>,
    /// The latest key event as a canonical chord such as `ctrl+s`.
    pub last_chord: Option<String>,
    /// The button of the latest button or motion report (`left`, `right`, `middle`).
    pub last_mouse_button: Option<&'static str>,
    /// `press`, `release`, `drag` or `move`; empty for a wheel report.
    pub last_mouse_kind: Option<&'static str>,
    /// The cell of the latest button or motion report.
    pub last_mouse_position: Option<(i32, i32)>,
    /// Signed wheel steps `(x, y)` of the step in which the wheel was reported.
    pub scroll: (i32, i32),
    pub last_paste: Option<String>,
}

/// The held-input names of the mouse buttons.
const HELD_MOUSE_BUTTONS: [&str; 3] = ["mouse_left", "mouse_right", "mouse_middle"];

/// The held-input name of a mouse button.
fn held_mouse_name(button: &str) -> String {
    format!("mouse_{button}")
}

impl InputData {
    fn forget_key(&mut self) {
        self.last_key = None;
        self.last_key_kind = None;
        self.last_chord = None;
    }

    fn forget_mouse(&mut self) {
        self.last_mouse_button = None;
        self.last_mouse_kind = None;
        self.last_mouse_position = None;
    }

    /// Remember a key event; the scalars of the other kinds of event are cleared.
    pub fn record_key(&mut self, key: &xnano_terminal_runtime::event::KeyEvent) {
        use xnano_terminal_runtime::event::KeyModifiers;
        self.forget_mouse();
        self.scroll = (0, 0);
        self.last_paste = None;
        let mut chord = String::new();
        for (name, flag) in [
            ("ctrl", KeyModifiers::CONTROL),
            ("alt", KeyModifiers::ALT),
            ("shift", KeyModifiers::SHIFT),
            ("super", KeyModifiers::SUPER),
            ("meta", KeyModifiers::META),
            ("hyper", KeyModifiers::HYPER),
        ] {
            if key.modifiers.contains(flag) {
                chord.push_str(name);
                chord.push('+');
            }
        }
        chord.push_str(&key.key);
        self.last_key = Some(key.key.clone());
        self.last_key_kind = Some(key.kind.name());
        self.last_chord = Some(chord);
    }

    /// Remember a mouse event and the buttons it leaves held; the scalars of the other kinds
    /// of event are cleared. A wheel report sets only `scroll`.
    pub fn record_mouse(&mut self, mouse: &xnano_terminal_runtime::event::MouseEvent) {
        use xnano_terminal_runtime::event::MouseKind;
        self.forget_key();
        self.last_paste = None;
        self.pointer = Some((mouse.column, mouse.row));
        if mouse.kind == MouseKind::Scroll {
            self.forget_mouse();
            self.scroll = (mouse.scroll_x, mouse.scroll_y);
            return;
        }
        self.scroll = (0, 0);
        self.last_mouse_kind = Some(mouse.kind.name());
        self.last_mouse_button = mouse
            .button
            .map(xnano_terminal_runtime::event::MouseButton::name);
        self.last_mouse_position = Some((mouse.column, mouse.row));
        if let Some(button) = mouse.button {
            let name = held_mouse_name(button.name());
            match mouse.kind {
                MouseKind::Press | MouseKind::Drag => {
                    self.pressed.insert(name);
                }
                MouseKind::Release => {
                    self.pressed.remove(&name);
                }
                _ => {}
            }
        }
    }

    /// Remember pasted text; the scalars of the other kinds of event are cleared.
    pub fn record_paste(&mut self, text: &str) {
        self.forget_key();
        self.forget_mouse();
        self.scroll = (0, 0);
        self.last_paste = Some(text.to_owned());
    }

    /// Whether any mouse button is held.
    pub fn is_mouse_down(&self) -> bool {
        HELD_MOUSE_BUTTONS
            .iter()
            .any(|name| self.pressed.contains(*name))
    }
}

pub struct HitAreaData {
    pub id: u64,
    pub key: String,
    pub target: Arc<BufferCore>,
    pub bounds: Rectangle,
    pub layer: i32,
    pub is_removed: bool,
}

pub struct ScopeData {
    pub id: u64,
    pub target: Arc<BufferCore>,
    pub is_modal: bool,
    pub is_active: Arc<AtomicBool>,
}

#[derive(Default)]
pub struct RouterData {
    pub hit_areas: Vec<Arc<Mutex<HitAreaData>>>,
    pub scopes: Vec<ScopeData>,
    pub focused: Option<u64>,
    pub captured_pointer: Option<u64>,
    pub next_id: u64,
}

/// A started effect, following its target.
pub struct RunningEffect {
    pub key: Option<String>,
    pub run: xnano_terminal_runtime::effects::EffectRun,
    pub placement: xnano_terminal_runtime::effects::Placement,
    pub target: Arc<BufferCore>,
    pub region: Option<Rectangle>,
    pub is_paused: bool,
    pub is_cancelled: bool,
    pub completed: Vec<Py<PyAny>>,
    pub error: Option<String>,
}

/// A running effect shared between the runtime and the handles that control it.
pub type SharedRunningEffect = Arc<Mutex<RunningEffect>>;

/// A started drawing animation, redrawn into its target when its frame changes.
pub struct RunningAnimation {
    pub key: Option<String>,
    pub animation: xnano_terminal_cells::CellAnimation,
    pub target: Arc<BufferCore>,
    pub region: Option<Rectangle>,
    pub x: i32,
    pub y: i32,
    pub encoding: PixelEncoding,
    pub start_milliseconds: i64,
    pub shown_index: Option<usize>,
}

#[derive(Default)]
pub struct Motion {
    pub effects: Vec<SharedRunningEffect>,
    pub animations: Vec<RunningAnimation>,
}

#[derive(Default)]
pub struct Metrics {
    pub frames: u64,
    pub last_microseconds: u64,
    pub total_microseconds: u128,
}

/// What the runtime shares with the objects that look into it.
pub struct RuntimeShared {
    pub clock: Arc<Clock>,
    pub device: Mutex<DeviceData>,
    pub input: Mutex<InputData>,
    pub router: Mutex<RouterData>,
    pub cursor: Mutex<crate::cursor::CursorData>,
    pub queue: EventQueue,
    pub motion: Mutex<Motion>,
    pub metrics: Mutex<Metrics>,
    pub is_running: AtomicBool,
    pub is_closed: AtomicBool,
    pub is_frame_requested: AtomicBool,
    pub revision: AtomicU64,
    /// A weak reference to the Python runtime object that owns this state.
    pub runtime_object: Mutex<Option<Py<PyAny>>>,
}

impl RuntimeShared {
    pub fn device_size(&self) -> Size {
        lock(&self.device).size
    }

    pub fn is_focused(&self, core: &Arc<BufferCore>) -> bool {
        lock(&self.router).focused == Some(core.id)
    }

    pub fn request_frame(&self) {
        self.is_frame_requested.store(true, Ordering::SeqCst);
        self.queue.nudge();
    }

    /// Start `effect` on a target, replacing a running effect with the same key.
    pub fn start_effect(&self, effect: RunningEffect) -> SharedRunningEffect {
        let shared = Arc::new(Mutex::new(effect));
        let mut motion = lock(&self.motion);
        if let Some(key) = lock(&shared).key.clone() {
            motion.effects.retain(|existing| {
                let mut existing = lock(existing);
                let same = existing.key.as_ref() == Some(&key);
                if same {
                    existing.is_cancelled = true;
                }
                !same
            });
        }
        motion.effects.push(Arc::clone(&shared));
        drop(motion);
        self.request_frame();
        shared
    }

    pub fn cancel_effect(&self, key: &str) {
        lock(&self.motion).effects.retain(|existing| {
            let mut existing = lock(existing);
            let same = existing.key.as_deref() == Some(key);
            if same {
                existing.is_cancelled = true;
            }
            !same
        });
        self.request_frame();
    }

    pub fn start_animation(&self, animation: DrawingAnimationStart) {
        let cells = animation.animation.to_cell_animation(animation.encoding);
        lock(&self.motion).animations.push(RunningAnimation {
            key: None,
            animation: cells,
            target: animation.target,
            region: animation.region,
            x: animation.x,
            y: animation.y,
            encoding: animation.encoding,
            start_milliseconds: animation.start_milliseconds,
            shown_index: None,
        });
        self.request_frame();
    }
}

pub struct DrawingAnimationStart {
    pub animation: Arc<DrawingAnimation>,
    pub target: Arc<BufferCore>,
    pub region: Option<Rectangle>,
    pub x: i32,
    pub y: i32,
    pub encoding: PixelEncoding,
    pub start_milliseconds: i64,
}

/// A weak handle a buffer keeps to the runtime it is mounted on.
pub type RuntimeLink = Weak<RuntimeShared>;

pub fn full_bounds(bounds: Bounds) -> Rectangle {
    Rectangle::new(
        i32::from(bounds.left),
        i32::from(bounds.top),
        i32::from(bounds.width()),
        i32::from(bounds.height()),
    )
}
