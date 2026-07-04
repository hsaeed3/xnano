use std::time::{Duration, Instant};

pub(crate) struct TickClock {
    interval: Duration,
    last_tick: Instant,
}

impl TickClock {
    pub fn new(interval_ms: u64) -> Self {
        Self {
            interval: Duration::from_millis(interval_ms),
            last_tick: Instant::now(),
        }
    }

    pub fn time_until_tick(&self) -> Duration {
        if self.interval.is_zero() {
            return Duration::from_secs(3600);
        }
        self.interval.saturating_sub(self.last_tick.elapsed())
    }

    pub fn due(&self) -> bool {
        !self.interval.is_zero() && self.last_tick.elapsed() >= self.interval
    }

    pub fn elapsed_since_last_tick_ms(&self) -> u64 {
        self.last_tick.elapsed().as_millis() as u64
    }

    pub fn reset(&mut self) {
        self.last_tick = Instant::now();
    }

    pub fn interval_ms(&self) -> u64 {
        self.interval.as_millis() as u64
    }
}