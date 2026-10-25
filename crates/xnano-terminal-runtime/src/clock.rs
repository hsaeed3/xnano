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
    /// When the previous drawn frame was recorded, on the time the frame rate is measured in.
    last_drawn_seconds: Option<f64>,
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
        Self::monotonic_from(0.0, 0)
    }

    /// A monotonic clock that starts at `elapsed_seconds` and has already counted `frame` frames.
    pub fn monotonic_from(elapsed_seconds: f64, frame: u64) -> Arc<Self> {
        Arc::new(Self {
            source: ClockSource::Monotonic,
            start: Instant::now(),
            state: Mutex::new(ClockState {
                manual_seconds: 0.0,
                paused_total: -elapsed_seconds,
                paused_since: None,
                last_elapsed: elapsed_seconds,
                delta: 0.0,
                frame,
                last_drawn_seconds: None,
                frames_per_second: 0.0,
            }),
        })
    }

    pub fn manual(elapsed_seconds: f64) -> Arc<Self> {
        Arc::new(Self {
            source: ClockSource::Manual,
            start: Instant::now(),
            state: Mutex::new(ClockState {
                manual_seconds: elapsed_seconds,
                paused_total: 0.0,
                paused_since: None,
                last_elapsed: elapsed_seconds,
                delta: 0.0,
                frame: 0,
                last_drawn_seconds: None,
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

    /// Time that keeps passing while the clock is paused. Frame pacing uses it, so a paused
    /// terminal still draws what changed.
    pub fn real_seconds(&self) -> f64 {
        self.raw_seconds(&lock(&self.state))
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

    /// Start a new step: the delta is the time since the previous call, and the frame count
    /// grows by one. A runtime steps far more often than it draws, so the frame rate is
    /// measured by `record_drawn_frame` instead.
    pub fn tick(&self) {
        let mut state = lock(&self.state);
        let elapsed = self.elapsed_locked(&state);
        state.delta = (elapsed - state.last_elapsed).max(0.0);
        state.last_elapsed = elapsed;
        state.frame += 1;
    }

    /// Record that a frame was drawn: the frame rate follows the time between drawn frames.
    ///
    /// A monotonic clock measures that time in real seconds, which keep passing while the
    /// clock is paused, so it is the rate frames reach the screen. A manual clock measures it
    /// in its own seconds, so it is the rate its steps imply. Frames drawn without time
    /// passing leave the rate as it was.
    pub fn record_drawn_frame(&self) {
        let mut state = lock(&self.state);
        let now = match self.source {
            ClockSource::Monotonic => self.raw_seconds(&state),
            ClockSource::Manual => self.elapsed_locked(&state),
        };
        let Some(previous) = state.last_drawn_seconds.replace(now) else {
            return;
        };
        let delta = now - previous;
        if delta <= 0.0 {
            return;
        }
        let instant = 1.0 / delta;
        state.frames_per_second = if state.frames_per_second == 0.0 {
            instant
        } else {
            state.frames_per_second * 0.9 + instant * 0.1
        };
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

    /// Move time forward by exactly `milliseconds`. A manual clock always moves; a monotonic
    /// clock moves only while it is paused. Returns `false` for a running monotonic clock.
    pub fn step(&self, milliseconds: u64) -> bool {
        let mut state = lock(&self.state);
        let seconds = milliseconds as f64 / 1000.0;
        if state.paused_since.is_some() {
            state.paused_total -= seconds;
            return true;
        }
        match self.source {
            ClockSource::Manual => {
                state.manual_seconds += seconds;
                true
            }
            ClockSource::Monotonic => false,
        }
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_manual_clock_steps_whether_or_not_it_is_stopped() {
        let clock = Clock::manual(0.0);
        assert!(clock.step(250));
        assert!((clock.elapsed_seconds() - 0.25).abs() < 1e-9);
        clock.pause();
        assert!(clock.step(750));
        assert!((clock.elapsed_seconds() - 1.0).abs() < 1e-9);
        clock.resume();
        assert!((clock.elapsed_seconds() - 1.0).abs() < 1e-9);
    }

    #[test]
    fn a_monotonic_clock_steps_only_while_it_is_stopped() {
        let clock = Clock::monotonic();
        assert!(!clock.step(10));
        clock.pause();
        let before = clock.elapsed_seconds();
        assert!(clock.step(2000));
        assert!((clock.elapsed_seconds() - (before + 2.0)).abs() < 1e-9);
        clock.resume();
        assert!(clock.elapsed_seconds() >= before + 2.0);
    }

    #[test]
    fn a_step_is_the_delta_of_the_next_frame() {
        let clock = Clock::manual(0.0);
        clock.tick();
        clock.step(40);
        clock.tick();
        assert!((clock.delta_seconds() - 0.04).abs() < 1e-9);
        assert_eq!(clock.frame(), 2);
    }

    #[test]
    fn steps_without_drawn_frames_leave_the_frame_rate_alone() {
        let clock = Clock::manual(0.0);
        for _ in 0..100 {
            clock.step(1);
            clock.tick();
        }
        assert_eq!(clock.frame(), 100);
        assert_eq!(clock.frames_per_second(), 0.0);
    }

    #[test]
    fn the_frame_rate_follows_drawn_frames_and_not_steps() {
        let clock = Clock::manual(0.0);
        clock.record_drawn_frame();
        for _ in 0..20 {
            // Four steps for every frame drawn, as input and queued calls make.
            for _ in 0..4 {
                clock.step(5);
                clock.tick();
            }
            clock.record_drawn_frame();
        }
        assert!((clock.frames_per_second() - 50.0).abs() < 1e-9);
    }

    #[test]
    fn frames_drawn_without_time_passing_leave_the_frame_rate_alone() {
        let clock = Clock::manual(0.0);
        clock.record_drawn_frame();
        clock.step(100);
        clock.record_drawn_frame();
        assert!((clock.frames_per_second() - 10.0).abs() < 1e-9);
        clock.record_drawn_frame();
        clock.record_drawn_frame();
        assert!((clock.frames_per_second() - 10.0).abs() < 1e-9);
    }

    #[test]
    fn a_monotonic_clock_measures_drawn_frames_in_real_time_while_paused() {
        let clock = Clock::monotonic();
        clock.pause();
        clock.record_drawn_frame();
        std::thread::sleep(std::time::Duration::from_millis(20));
        clock.record_drawn_frame();
        let frames_per_second = clock.frames_per_second();
        assert!(frames_per_second > 0.0 && frames_per_second <= 50.0);
    }

    #[test]
    fn a_monotonic_clock_can_start_at_an_elapsed_time_and_frame() {
        let clock = Clock::monotonic_from(2.0, 120);
        assert!(clock.elapsed_seconds() >= 2.0);
        assert!(clock.elapsed_seconds() < 3.0);
        assert_eq!(clock.frame(), 120);
        clock.tick();
        assert_eq!(clock.frame(), 121);
        assert!(clock.delta_seconds() < 1.0);
    }
}
