//! Monotonic time, manual time for tests, and independently scaled simulation time.

use std::sync::{Arc, Mutex, MutexGuard};
use std::time::Instant;

fn lock<T>(mutex: &Mutex<T>) -> MutexGuard<'_, T> {
    mutex
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner)
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ClockSource {
    Monotonic,
    Manual,
}

impl ClockSource {
    pub fn name(self) -> &'static str {
        match self {
            Self::Monotonic => "monotonic",
            Self::Manual => "manual",
        }
    }
}

struct ClockState {
    manual_seconds: f64,
    /// Time spent paused so far (monotonic clocks).
    paused_total: f64,
    paused_since: Option<f64>,
    last_elapsed: f64,
    delta: f64,
    frame: u64,
    frames_per_second: f64,
}

/// The time source a runtime schedules against.
///
/// Wall-clock adjustments never affect it.
pub struct Clock {
    source: ClockSource,
    start: Instant,
    state: Mutex<ClockState>,
}

impl std::fmt::Debug for Clock {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            formatter,
            "Clock({}, {:.3}s)",
            self.source.name(),
            self.elapsed_seconds()
        )
    }
}

impl Clock {
    pub fn monotonic() -> Arc<Self> {
        Self::create(ClockSource::Monotonic, 0.0)
    }

    pub fn manual(elapsed_seconds: f64) -> Arc<Self> {
        Self::create(ClockSource::Manual, elapsed_seconds)
    }

    fn create(source: ClockSource, elapsed: f64) -> Arc<Self> {
        Arc::new(Self {
            source,
            start: Instant::now(),
            state: Mutex::new(ClockState {
                manual_seconds: elapsed,
                paused_total: 0.0,
                paused_since: None,
                last_elapsed: elapsed,
                delta: 0.0,
                frame: 0,
                frames_per_second: 0.0,
            }),
        })
    }

    pub fn source(&self) -> ClockSource {
        self.source
    }

    fn raw_seconds(&self, state: &ClockState) -> f64 {
        match self.source {
            ClockSource::Monotonic => self.start.elapsed().as_secs_f64(),
            ClockSource::Manual => state.manual_seconds,
        }
    }

    fn elapsed_locked(&self, state: &ClockState) -> f64 {
        match state.paused_since {
            Some(frozen) => frozen - state.paused_total,
            None => self.raw_seconds(state) - state.paused_total,
        }
    }

    pub fn elapsed_seconds(&self) -> f64 {
        self.elapsed_locked(&lock(&self.state))
    }

    pub fn delta_seconds(&self) -> f64 {
        lock(&self.state).delta
    }

    pub fn frame(&self) -> u64 {
        lock(&self.state).frame
    }

    pub fn frames_per_second(&self) -> f64 {
        lock(&self.state).frames_per_second
    }

    pub fn is_paused(&self) -> bool {
        lock(&self.state).paused_since.is_some()
    }

    /// Start a new frame: the delta is the time since the previous call.
    pub fn tick(&self) {
        let mut state = lock(&self.state);
        let elapsed = self.elapsed_locked(&state);
        state.delta = (elapsed - state.last_elapsed).max(0.0);
        state.last_elapsed = elapsed;
        state.frame += 1;
        if state.delta > 0.0 {
            let instant = 1.0 / state.delta;
            state.frames_per_second = if state.frames_per_second == 0.0 {
                instant
            } else {
                state.frames_per_second * 0.9 + instant * 0.1
            };
        }
    }

    pub fn pause(&self) {
        let mut state = lock(&self.state);
        if state.paused_since.is_none() {
            let raw = self.raw_seconds(&state);
            state.paused_since = Some(raw);
        }
    }

    pub fn resume(&self) {
        let mut state = lock(&self.state);
        if let Some(frozen) = state.paused_since.take() {
            let raw = self.raw_seconds(&state);
            state.paused_total += raw - frozen;
        }
    }

    /// Move a manual clock forward. Returns `false` for a monotonic clock.
    pub fn advance(&self, milliseconds: u64) -> bool {
        if self.source != ClockSource::Manual {
            return false;
        }
        let mut state = lock(&self.state);
        state.manual_seconds += milliseconds as f64 / 1000.0;
        true
    }

    pub fn derive(self: &Arc<Self>, rate: f64, is_paused: bool) -> Arc<SimulationClock> {
        let parent_elapsed = self.elapsed_seconds();
        Arc::new(SimulationClock {
            parent: Arc::clone(self),
            state: Mutex::new(SimulationState {
                rate,
                is_paused,
                base_simulation: 0.0,
                base_parent: parent_elapsed,
                last_elapsed: 0.0,
                delta: 0.0,
            }),
        })
    }
}

struct SimulationState {
    rate: f64,
    is_paused: bool,
    base_simulation: f64,
    base_parent: f64,
    last_elapsed: f64,
    delta: f64,
}

/// A clock scaled from its parent. Changing the rate keeps elapsed time continuous.
pub struct SimulationClock {
    parent: Arc<Clock>,
    state: Mutex<SimulationState>,
}

impl SimulationClock {
    pub fn parent(&self) -> &Arc<Clock> {
        &self.parent
    }

    fn elapsed_locked(&self, state: &SimulationState) -> f64 {
        if state.is_paused {
            state.base_simulation
        } else {
            state.base_simulation + (self.parent.elapsed_seconds() - state.base_parent) * state.rate
        }
    }

    pub fn elapsed_seconds(&self) -> f64 {
        self.elapsed_locked(&lock(&self.state))
    }

    /// Time since the previous sample, in simulation seconds.
    pub fn delta_seconds(&self) -> f64 {
        lock(&self.state).delta
    }

    /// Record the current time; later `delta_seconds` calls report the change since this one.
    pub fn sample(&self) {
        let mut state = lock(&self.state);
        let elapsed = self.elapsed_locked(&state);
        state.delta = (elapsed - state.last_elapsed).max(0.0);
        state.last_elapsed = elapsed;
    }

    pub fn rate(&self) -> f64 {
        lock(&self.state).rate
    }

    pub fn set_rate(&self, rate: f64) {
        let mut state = lock(&self.state);
        let elapsed = self.elapsed_locked(&state);
        state.base_simulation = elapsed;
        state.base_parent = self.parent.elapsed_seconds();
        state.rate = rate;
    }

    pub fn is_paused(&self) -> bool {
        lock(&self.state).is_paused
    }

    pub fn set_paused(&self, is_paused: bool) {
        let mut state = lock(&self.state);
        if state.is_paused == is_paused {
            return;
        }
        let elapsed = self.elapsed_locked(&state);
        state.base_simulation = elapsed;
        state.base_parent = self.parent.elapsed_seconds();
        state.is_paused = is_paused;
    }

    /// Parent seconds until this clock reaches `target` simulation seconds, or `None` when
    /// it never will (paused or stopped).
    pub fn parent_seconds_until(&self, target: f64) -> Option<f64> {
        let state = lock(&self.state);
        if state.is_paused || state.rate <= 0.0 {
            return None;
        }
        let remaining = target - self.elapsed_locked(&state);
        Some((remaining / state.rate).max(0.0))
    }
}
