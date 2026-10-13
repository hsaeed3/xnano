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
        // Taking the lock first orders this after a waiter has either seen the new state or
        // started waiting, so the wake-up cannot fall between its check and its wait.
        drop(lock(&self.state));
        self.ready.notify_all();
        let notifiers: Vec<Notifier> = lock(&self.notifiers)
            .iter()
            .map(|(_, notifier)| Arc::clone(notifier))
            .collect();
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
        let state = lock(&self.state);
        if !state.events.is_empty()
            || !state.calls.is_empty()
            || state.is_wake_requested
            || should_return()
        {
            return;
        }
        match timeout {
            Some(timeout) => {
                drop(self.ready.wait_timeout(state, timeout));
            }
            None => {
                drop(self.ready.wait(state));
            }
        }
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
