//! Small DSP building blocks shared by instruments and effects.
//!
//! Everything here is plain `f32` math with no allocation in the per-sample
//! path, so rendering a note is a tight loop.

use std::f32::consts::TAU;

/// Deterministic white-noise generator (xorshift32).
///
/// Instruments seed it from the note so that the same note always renders to
/// the exact same samples.
pub struct Rng(u32);

impl Rng {
    pub fn new(seed: u32) -> Self {
        Self(seed | 1)
    }

    /// Next value in `-1.0..1.0`.
    pub fn next(&mut self) -> f32 {
        let mut x = self.0;
        x ^= x << 13;
        x ^= x >> 17;
        x ^= x << 5;
        self.0 = x;
        (x as f32 / u32::MAX as f32) * 2.0 - 1.0
    }
}

/// Two-pole filter (RBJ cookbook), transposed direct form II.
#[derive(Clone, Copy)]
pub struct Biquad {
    b0: f32,
    b1: f32,
    b2: f32,
    a1: f32,
    a2: f32,
    z1: f32,
    z2: f32,
}

impl Biquad {
    fn from_coefficients(b: [f32; 3], a: [f32; 3]) -> Self {
        Self {
            b0: b[0] / a[0],
            b1: b[1] / a[0],
            b2: b[2] / a[0],
            a1: a[1] / a[0],
            a2: a[2] / a[0],
            z1: 0.0,
            z2: 0.0,
        }
    }

    fn terms(sample_rate: f32, cutoff: f32, q: f32) -> (f32, f32) {
        let w0 = TAU * cutoff.clamp(10.0, sample_rate * 0.49) / sample_rate;
        (w0.cos(), w0.sin() / (2.0 * q.max(0.1)))
    }

    pub fn lowpass(sample_rate: f32, cutoff: f32, q: f32) -> Self {
        let (cos, alpha) = Self::terms(sample_rate, cutoff, q);
        Self::from_coefficients(
            [(1.0 - cos) / 2.0, 1.0 - cos, (1.0 - cos) / 2.0],
            [1.0 + alpha, -2.0 * cos, 1.0 - alpha],
        )
    }

    pub fn highpass(sample_rate: f32, cutoff: f32, q: f32) -> Self {
        let (cos, alpha) = Self::terms(sample_rate, cutoff, q);
        let half = f32::midpoint(1.0, cos);
        Self::from_coefficients(
            [half, -(1.0 + cos), half],
            [1.0 + alpha, -2.0 * cos, 1.0 - alpha],
        )
    }

    pub fn bandpass(sample_rate: f32, cutoff: f32, q: f32) -> Self {
        let (cos, alpha) = Self::terms(sample_rate, cutoff, q);
        Self::from_coefficients([alpha, 0.0, -alpha], [1.0 + alpha, -2.0 * cos, 1.0 - alpha])
    }

    /// Retune to a new low-pass cutoff, keeping the filter state (for sweeps).
    pub fn retune_lowpass(&mut self, sample_rate: f32, cutoff: f32, q: f32) {
        let fresh = Self::lowpass(sample_rate, cutoff, q);
        (self.b0, self.b1, self.b2, self.a1, self.a2) =
            (fresh.b0, fresh.b1, fresh.b2, fresh.a1, fresh.a2);
    }

    pub fn process(&mut self, x: f32) -> f32 {
        let y = self.b0 * x + self.z1;
        self.z1 = self.b1 * x - self.a1 * y + self.z2;
        self.z2 = self.b2 * x - self.a2 * y;
        y
    }
}

/// Band-limiting correction for naive saw/square edges (PolyBLEP).
fn poly_blep(t: f32, dt: f32) -> f32 {
    if t < dt {
        let x = t / dt;
        x + x - x * x - 1.0
    } else if t > 1.0 - dt {
        let x = (t - 1.0) / dt;
        x * x + x + x + 1.0
    } else {
        0.0
    }
}

/// Phase-accumulating oscillator with anti-aliased saw and square shapes.
#[derive(Default, Clone, Copy)]
pub struct Osc {
    phase: f32,
}

impl Osc {
    pub fn with_phase(phase: f32) -> Self {
        Self { phase }
    }

    fn advance(&mut self, dt: f32) {
        self.phase += dt;
        if self.phase >= 1.0 {
            self.phase -= 1.0;
        }
    }

    pub fn sine(&mut self, freq: f32, sample_rate: f32) -> f32 {
        let value = (TAU * self.phase).sin();
        self.advance(freq / sample_rate);
        value
    }

    pub fn saw(&mut self, freq: f32, sample_rate: f32) -> f32 {
        let dt = freq / sample_rate;
        let value = 2.0 * self.phase - 1.0 - poly_blep(self.phase, dt);
        self.advance(dt);
        value
    }

    pub fn square(&mut self, freq: f32, sample_rate: f32) -> f32 {
        let dt = freq / sample_rate;
        let t = self.phase;
        let naive = if t < 0.5 { 1.0 } else { -1.0 };
        let value = naive + poly_blep(t, dt) - poly_blep((t + 0.5) % 1.0, dt);
        self.advance(dt);
        value
    }

    pub fn triangle(&mut self, freq: f32, sample_rate: f32) -> f32 {
        let value = 4.0 * (self.phase - 0.5).abs() - 1.0;
        self.advance(freq / sample_rate);
        value
    }
}

/// Multiplier that turns `cents` of detune into a frequency ratio.
pub fn cents(cents: f32) -> f32 {
    (cents / 1200.0).exp2()
}

/// Per-sample multiplier that makes an exponential decay reach 1/e in `tau` s.
pub fn decay_per_sample(tau: f32, sample_rate: f32) -> f32 {
    (-1.0 / (tau.max(1e-4) * sample_rate)).exp()
}

/// Quadratic fade-out after the gate closes: `1.0` while held, `0.0` after
/// `release` seconds.
pub fn gate_release(t: f32, gate: f32, release: f32) -> f32 {
    if t <= gate {
        1.0
    } else {
        let x = ((t - gate) / release.max(1e-3)).min(1.0);
        (1.0 - x) * (1.0 - x)
    }
}

/// Attack / decay / sustain envelope level while the gate is held.
pub fn adsr_held(t: f32, attack: f32, decay: f32, sustain: f32) -> f32 {
    if t < attack {
        t / attack.max(1e-4)
    } else if t < attack + decay {
        1.0 - (1.0 - sustain) * ((t - attack) / decay.max(1e-4))
    } else {
        sustain
    }
}

/// Full ADSR with a quadratic release that starts from the level at the gate.
pub fn adsr(t: f32, gate: f32, attack: f32, decay: f32, sustain: f32, release: f32) -> f32 {
    if t <= gate {
        adsr_held(t, attack, decay, sustain)
    } else {
        adsr_held(gate, attack, decay, sustain) * gate_release(t, gate, release)
    }
}

/// Scale `samples` down so the peak never exceeds `ceiling`.
pub fn limit(samples: &mut [f32], ceiling: f32) {
    let peak = samples.iter().fold(0.0_f32, |m, &x| m.max(x.abs()));
    if peak > ceiling {
        let scale = ceiling / peak;
        for x in samples {
            *x *= scale;
        }
    }
}
