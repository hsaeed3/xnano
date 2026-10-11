//! Procedural instruments: every sound is computed, nothing is recorded.
//!
//! | Family        | Technique                                              |
//! |---------------|--------------------------------------------------------|
//! | piano, organ  | additive partials (piano is slightly inharmonic)       |
//! | e-piano, bell | FM synthesis                                           |
//! | marimba       | sine plus a fast-decaying overtone                     |
//! | guitars       | Karplus-Strong plucked-string physical model           |
//! | synths, bass  | detuned band-limited saws through a swept low-pass     |
//! | drums         | pitch-swept sines, filtered noise, metallic squares    |
//!
//! Every instrument is a pure function of a [`Note`] and returns mono samples
//! (including its natural tail), so output is deterministic and needs no
//! audio device.

use std::f32::consts::TAU;

use crate::dsp::{Biquad, Osc, Rng, adsr, cents, decay_per_sample, gate_release, limit};

/// What to play.
pub struct Note {
    /// Pitch in hertz.
    pub freq: f32,
    /// Seconds the key is held; the release/tail is added on top.
    pub gate: f32,
    /// Strength from `0.0` to `1.0`.
    pub velocity: f32,
    pub sample_rate: f32,
}

pub struct Instrument {
    pub name: &'static str,
    /// Percussive instruments ring for their own natural length and ignore the
    /// note duration.
    pub percussive: bool,
    /// Loudness-matching gain: scales each instrument to the same RMS at a
    /// reference note (A3, velocity 0.8), capped so velocity 1.0 stays under
    /// the ceiling. Checked by `test_instruments_are_loudness_matched`.
    gain: f32,
    render: fn(&Note) -> Vec<f32>,
}

/// Highest sample value an instrument may produce.
const CEILING: f32 = 0.95;

impl Instrument {
    /// Render the note at matched loudness, keeping the peak at or below the
    /// ceiling.
    pub fn render(&self, note: &Note) -> Vec<f32> {
        let mut samples = (self.render)(note);
        for sample in &mut samples {
            *sample *= self.gain;
        }
        limit(&mut samples, CEILING);
        samples
    }
}

macro_rules! instrument {
    ($name:literal, $render:ident, $gain:expr) => {
        Instrument {
            name: $name,
            percussive: false,
            gain: $gain,
            render: $render,
        }
    };
    ($name:literal, $render:ident, $gain:expr, percussive) => {
        Instrument {
            name: $name,
            percussive: true,
            gain: $gain,
            render: $render,
        }
    };
}

pub const INSTRUMENTS: &[Instrument] = &[
    instrument!("piano", piano, 0.884),
    instrument!("electric_piano", electric_piano, 0.701),
    instrument!("organ", organ, 0.635),
    instrument!("bell", bell, 0.756),
    instrument!("marimba", marimba, 0.607),
    instrument!("guitar", guitar, 1.317),
    instrument!("electric_guitar", electric_guitar, 1.247),
    instrument!("pluck", pluck, 1.0),
    instrument!("bass", bass, 1.398),
    instrument!("synth", synth, 0.974),
    instrument!("pad", pad, 1.596),
    instrument!("strings", strings, 2.532),
    instrument!("sine", sine, 0.408),
    instrument!("square", square, 0.579),
    instrument!("saw", saw, 1.005),
    instrument!("triangle", triangle, 0.499),
    instrument!("kick", kick, 0.527, percussive),
    instrument!("snare", snare, 0.656, percussive),
    instrument!("hihat", hihat, 1.205, percussive),
    instrument!("open_hat", open_hat, 1.204, percussive),
    instrument!("clap", clap, 0.845, percussive),
    instrument!("tom", tom, 0.453, percussive),
    instrument!("cowbell", cowbell, 0.547, percussive),
];

pub fn find(name: &str) -> Option<&'static Instrument> {
    let wanted = name.trim().to_lowercase().replace([' ', '-'], "_");
    INSTRUMENTS.iter().find(|i| i.name == wanted)
}

// ---------------------------------------------------------------- helpers

/// Render `gate + tail` seconds, calling `f(t)` for every sample.
fn render_with(n: &Note, tail: f32, f: impl FnMut(f32) -> f32) -> Vec<f32> {
    render_for(n, n.gate + tail, f)
}

/// Render exactly `seconds`, calling `f(t)` for every sample.
fn render_for(n: &Note, seconds: f32, mut f: impl FnMut(f32) -> f32) -> Vec<f32> {
    let len = (seconds * n.sample_rate).ceil().max(1.0) as usize;
    let dt = 1.0 / n.sample_rate;
    (0..len).map(|i| f(i as f32 * dt)).collect()
}

fn rng(n: &Note, salt: u32) -> Rng {
    Rng::new(n.freq.to_bits() ^ salt)
}

/// Short fade so percussive sounds end without a click.
fn end_fade(t: f32, total: f32) -> f32 {
    ((total - t) / 0.03).clamp(0.0, 1.0)
}

fn advance(phase: &mut f32, hz: f32, sample_rate: f32) {
    *phase = (*phase + TAU * hz / sample_rate) % TAU;
}

struct Partial {
    phase: f32,
    inc: f32,
    amp: f32,
    decay: f32,
}

impl Partial {
    fn next(&mut self) -> f32 {
        let value = self.amp * self.phase.sin();
        self.phase = (self.phase + self.inc) % TAU;
        self.amp *= self.decay;
        value
    }
}

// ----------------------------------------------------------------- pitched

/// Additive piano: stiff-string inharmonic partials that decay faster the
/// higher they are, plus a short hammer-noise thump. Velocity brightens it.
fn piano(n: &Note) -> Vec<f32> {
    let sr = n.sample_rate;
    let inharmonicity = 0.000_35_f32;
    let tau = (3.5 * (261.6 / n.freq).powf(0.45)).clamp(0.5, 7.0);
    let bright = 0.55 + 0.45 * n.velocity;
    let mut partials: Vec<Partial> = (1..=14)
        .filter_map(|k| {
            let kf = k as f32;
            let hz = kf * n.freq * (1.0 + inharmonicity * kf * kf).sqrt();
            (hz < sr * 0.45).then(|| Partial {
                phase: 0.0,
                inc: TAU * hz / sr,
                amp: bright.powf(kf - 1.0) / kf.powf(1.15),
                decay: decay_per_sample(tau / (1.0 + 0.7 * (kf - 1.0)), sr),
            })
        })
        .collect();
    let mut noise = rng(n, 0x91A0);
    let (mut hammer, mut hammer_env) = (0.0, n.velocity * 0.5);
    let hammer_decay = decay_per_sample(0.012, sr);
    render_with(n, 0.3, |t| {
        let mut s: f32 = partials.iter_mut().map(Partial::next).sum();
        hammer += 0.25 * (noise.next() - hammer);
        s += hammer * hammer_env;
        hammer_env *= hammer_decay;
        s * gate_release(t, n.gate, 0.25) * 0.28 * n.velocity
    })
}

/// Rhodes-style FM: a 1:1 modulator whose index decays, plus a bright "tine".
fn electric_piano(n: &Note) -> Vec<f32> {
    let sr = n.sample_rate;
    let index0 = 1.2 + 2.4 * n.velocity;
    let tine_hz = n.freq * 14.0;
    let (mut carrier, mut modulator, mut tine) = (0.0_f32, 0.0_f32, 0.0_f32);
    render_with(n, 0.4, |t| {
        let index = index0 * (-t / 0.45).exp() + 0.25;
        let m = modulator.sin();
        advance(&mut modulator, n.freq, sr);
        let c = (carrier + index * m).sin();
        advance(&mut carrier, n.freq, sr);
        let tine_level = if tine_hz < sr * 0.45 {
            let v = tine.sin() * (-t / 0.03).exp() * 0.12 * n.velocity;
            advance(&mut tine, tine_hz, sr);
            v
        } else {
            0.0
        };
        (c * (-t / 1.6).exp() + tine_level) * gate_release(t, n.gate, 0.35) * 0.5 * n.velocity
    })
}

/// Drawbar organ: sine partials at the classic drawbar ratios.
fn organ(n: &Note) -> Vec<f32> {
    const DRAWBARS: [(f32, f32); 8] = [
        (0.5, 0.6),
        (1.0, 1.0),
        (1.5, 0.4),
        (2.0, 0.8),
        (3.0, 0.4),
        (4.0, 0.5),
        (6.0, 0.2),
        (8.0, 0.15),
    ];
    let sr = n.sample_rate;
    let mut bars: Vec<(Osc, f32, f32)> = DRAWBARS
        .iter()
        .filter(|(ratio, _)| n.freq * ratio < sr * 0.45)
        .map(|&(ratio, level)| (Osc::default(), n.freq * ratio, level))
        .collect();
    render_with(n, 0.08, |t| {
        let s: f32 = bars
            .iter_mut()
            .map(|(o, hz, lvl)| o.sine(*hz, sr) * *lvl)
            .sum();
        s * (t / 0.008).min(1.0) * gate_release(t, n.gate, 0.06) * 0.22 * n.velocity
    })
}

/// Bell: FM with an inharmonic 3.5:1 ratio whose index decays, ringing on
/// after the key is released.
fn bell(n: &Note) -> Vec<f32> {
    let sr = n.sample_rate;
    let index0 = 5.0 * (0.6 + 0.4 * n.velocity);
    let (mut carrier, mut modulator) = (0.0_f32, 0.0_f32);
    render_with(n, 1.6, |t| {
        let index = index0 * (-t / 0.7).exp() + 0.2;
        let m = modulator.sin();
        advance(&mut modulator, n.freq * 3.51, sr);
        let c = (carrier + index * m).sin();
        advance(&mut carrier, n.freq, sr);
        c * (-t / 1.4).exp() * gate_release(t, n.gate, 1.4) * 0.6 * n.velocity
    })
}

/// Marimba: a sine body plus a fast-decaying overtone near 4x.
fn marimba(n: &Note) -> Vec<f32> {
    let sr = n.sample_rate;
    let (mut body, mut over, mut high) = (0.0_f32, 0.0_f32, 0.0_f32);
    render_with(n, 0.4, |t| {
        let mut s = body.sin() * (-t / 0.5).exp();
        advance(&mut body, n.freq, sr);
        if n.freq * 4.0 < sr * 0.45 {
            s += 0.35 * over.sin() * (-t / 0.05).exp();
            advance(&mut over, n.freq * 4.0, sr);
        }
        if n.freq * 10.0 < sr * 0.45 {
            s += 0.1 * high.sin() * (-t / 0.02).exp();
            advance(&mut high, n.freq * 10.0, sr);
        }
        s * gate_release(t, n.gate, 0.2) * 0.7 * n.velocity
    })
}

/// Karplus-Strong plucked string: a noise burst circulating in a filtered
/// delay line. `t60` is the ring time, `brightness` (0..1) the pick tone.
fn karplus_strong(n: &Note, t60: f32, brightness: f32, tail: f32, salt: u32) -> Vec<f32> {
    let sr = n.sample_rate;
    // The loop low-pass adds half a sample of delay; an all-pass supplies the
    // fractional remainder so pitch stays in tune.
    let loop_delay = sr / n.freq - 0.5;
    let length = (loop_delay.floor() as usize).max(2);
    let frac = (loop_delay - length as f32).clamp(0.0, 0.999);
    let coeff = (1.0 - frac) / (1.0 + frac);
    let gain = 10.0_f32.powf(-3.0 / (n.freq * t60));

    let mut noise = rng(n, salt);
    let mut smooth = 0.0;
    let mut line: Vec<f32> = (0..length)
        .map(|_| {
            smooth += brightness.clamp(0.05, 1.0) * (noise.next() - smooth);
            smooth
        })
        .collect();
    // Pick position: a comb that removes harmonics around the pick point.
    let pick = (length as f32 * 0.18) as usize;
    if pick > 0 {
        let source = line.clone();
        for (i, v) in line.iter_mut().enumerate() {
            *v -= source[(i + length - pick) % length];
        }
    }
    let peak = line.iter().fold(1e-6_f32, |m, &x| m.max(x.abs()));
    for v in &mut line {
        *v /= peak;
    }

    let (mut index, mut previous) = (0, 0.0);
    let (mut ap_x, mut ap_y) = (0.0, 0.0);
    render_with(n, tail, |t| {
        let out = line[index];
        let averaged = f32::midpoint(out, previous);
        previous = out;
        let tuned = coeff * averaged + ap_x - coeff * ap_y;
        ap_x = averaged;
        ap_y = tuned;
        line[index] = tuned * gain;
        index = (index + 1) % length;
        out * gate_release(t, n.gate, 0.4) * n.velocity * 0.9
    })
}

/// Acoustic guitar: a warm string softened by a body-like low-pass.
fn guitar(n: &Note) -> Vec<f32> {
    let mut body = Biquad::lowpass(n.sample_rate, 3500.0, 0.7);
    let mut out = karplus_strong(n, 2.5, 0.45, 0.4, 0x6017);
    for s in &mut out {
        *s = body.process(*s);
    }
    out
}

/// Electric guitar: a brighter string pushed through soft-clip drive and a
/// cabinet-like low-pass.
fn electric_guitar(n: &Note) -> Vec<f32> {
    let mut cabinet = Biquad::lowpass(n.sample_rate, 3800.0, 0.8);
    let mut out = karplus_strong(n, 3.5, 0.7, 0.4, 0xE6A7);
    for s in &mut out {
        *s = cabinet.process((*s * 5.0).tanh()) * 0.5;
    }
    out
}

/// Bright, short plucked string.
fn pluck(n: &Note) -> Vec<f32> {
    karplus_strong(n, 1.0, 1.0, 0.2, 0x91CC)
}

/// Saw plus sub sine through a low-pass that snaps closed.
fn bass(n: &Note) -> Vec<f32> {
    let sr = n.sample_rate;
    let (mut saw, mut sub) = (Osc::default(), Osc::default());
    let mut filter = Biquad::lowpass(sr, 400.0, 1.0);
    let mut counter = 0_u32;
    render_with(n, 0.1, |t| {
        if counter.trailing_zeros() >= 5 {
            let cutoff = 180.0 + 1400.0 * n.velocity * (-t / 0.1).exp();
            filter.retune_lowpass(sr, cutoff, 1.0);
        }
        counter += 1;
        let raw = 0.6 * saw.saw(n.freq, sr) + 0.7 * sub.sine(n.freq, sr);
        filter.process(raw) * adsr(t, n.gate, 0.004, 0.2, 0.65, 0.08) * 0.6 * n.velocity
    })
}

/// Voices shared by the sustained synths: detuned saws, an optional vibrato
/// and a low-pass whose cutoff follows `cutoff(t)`.
struct SawStack {
    oscs: Vec<(Osc, f32)>,
    filter: Biquad,
    counter: u32,
}

impl SawStack {
    fn new(sample_rate: f32, detune: &[f32]) -> Self {
        Self {
            oscs: detune
                .iter()
                .enumerate()
                .map(|(i, &c)| (Osc::with_phase(i as f32 * 0.29), cents(c)))
                .collect(),
            filter: Biquad::lowpass(sample_rate, 1500.0, 1.0),
            counter: 0,
        }
    }

    fn next(&mut self, n: &Note, bend: f32, cutoff: f32, q: f32) -> f32 {
        if self.counter.trailing_zeros() >= 5 {
            self.filter.retune_lowpass(n.sample_rate, cutoff, q);
        }
        self.counter += 1;
        let hz = n.freq * bend;
        let count = self.oscs.len() as f32;
        let raw: f32 = self
            .oscs
            .iter_mut()
            .map(|(osc, ratio)| osc.saw(hz * *ratio, n.sample_rate))
            .sum();
        self.filter.process(raw / count)
    }
}

fn vibrato(phase: &mut f32, t: f32, rate: f32, depth_cents: f32, delay: f32, sr: f32) -> f32 {
    advance(phase, rate, sr);
    cents(depth_cents * phase.sin() * ((t - delay) / 0.4).clamp(0.0, 1.0))
}

/// Lead synth: two detuned saws and a sub square, resonant filter envelope,
/// delayed vibrato.
fn synth(n: &Note) -> Vec<f32> {
    let sr = n.sample_rate;
    let mut stack = SawStack::new(sr, &[7.0, -7.0]);
    let mut sub = Osc::with_phase(0.11);
    let mut vib = 0.0;
    render_with(n, 0.25, |t| {
        let bend = vibrato(&mut vib, t, 5.5, 6.0, 0.15, sr);
        let cutoff = (n.freq * 2.5).clamp(300.0, 8000.0) + 2800.0 * n.velocity * (-t / 0.18).exp();
        let body = stack.next(n, bend, cutoff.min(sr * 0.45), 1.4);
        let low = 0.25 * sub.square(n.freq * 0.5 * bend, sr);
        (body * 0.9 + low) * adsr(t, n.gate, 0.006, 0.15, 0.75, 0.2) * 0.5 * n.velocity
    })
}

/// Slow, wide pad of three detuned saws.
fn pad(n: &Note) -> Vec<f32> {
    let mut stack = SawStack::new(n.sample_rate, &[-12.0, 0.0, 12.0]);
    render_with(n, 0.8, |t| {
        let cutoff = (n.freq * 3.0).clamp(400.0, 1800.0);
        stack.next(n, 1.0, cutoff, 0.8) * adsr(t, n.gate, 0.4, 0.5, 0.8, 0.7) * 0.5 * n.velocity
    })
}

/// Ensemble strings: four detuned saws with gentle vibrato.
fn strings(n: &Note) -> Vec<f32> {
    let sr = n.sample_rate;
    let mut stack = SawStack::new(sr, &[-9.0, -3.0, 4.0, 10.0]);
    let mut vib = 0.0;
    render_with(n, 0.5, |t| {
        let bend = vibrato(&mut vib, t, 5.0, 5.0, 0.25, sr);
        let cutoff = (n.freq * 4.0).clamp(800.0, 3200.0);
        stack.next(n, bend, cutoff, 0.7)
            * adsr(t, n.gate, 0.22, 0.3, 0.85, 0.45)
            * 0.55
            * n.velocity
    })
}

fn basic(n: &Note, gain: f32, shape: fn(&mut Osc, f32, f32) -> f32) -> Vec<f32> {
    let mut osc = Osc::default();
    render_with(n, 0.05, |t| {
        shape(&mut osc, n.freq, n.sample_rate)
            * adsr(t, n.gate, 0.005, 0.05, 0.9, 0.04)
            * gain
            * n.velocity
    })
}

fn sine(n: &Note) -> Vec<f32> {
    basic(n, 0.6, Osc::sine)
}

fn square(n: &Note) -> Vec<f32> {
    basic(n, 0.3, Osc::square)
}

fn saw(n: &Note) -> Vec<f32> {
    basic(n, 0.3, Osc::saw)
}

fn triangle(n: &Note) -> Vec<f32> {
    basic(n, 0.6, Osc::triangle)
}

// ------------------------------------------------------------------- drums

/// Kick: a sine that sweeps down fast, plus a click.
fn kick(n: &Note) -> Vec<f32> {
    let sr = n.sample_rate;
    let mut phase = 0.0;
    let mut noise = rng(n, 0xB1C4);
    render_for(n, 0.5, |t| {
        advance(&mut phase, 48.0 + 170.0 * (-t / 0.028).exp(), sr);
        let body = phase.sin() * (-t / 0.18).exp();
        let click = noise.next() * (-t / 0.003).exp() * 0.25;
        (body * 0.95 + click) * n.velocity * end_fade(t, 0.5)
    })
}

/// Snare: a short tone plus high-passed noise.
fn snare(n: &Note) -> Vec<f32> {
    let sr = n.sample_rate;
    let mut noise = rng(n, 0x5A4E);
    let mut high = Biquad::highpass(sr, 1200.0, 0.7);
    let mut phase = 0.0;
    render_for(n, 0.3, |t| {
        advance(&mut phase, 185.0, sr);
        let tone = phase.sin() * (-t / 0.07).exp() * 0.5;
        let hiss = high.process(noise.next()) * (-t / 0.11).exp() * 0.8;
        (tone + hiss) * n.velocity * end_fade(t, 0.3)
    })
}

/// Six metallic square waves (the classic 808 ratios) through a high-pass.
fn hat(n: &Note, tau: f32, total: f32) -> Vec<f32> {
    const METAL: [f32; 6] = [205.3, 304.4, 369.6, 522.7, 540.0, 800.0];
    let sr = n.sample_rate;
    let mut oscs = [Osc::default(); 6];
    let mut high = Biquad::highpass(sr, 6500.0, 0.8);
    render_for(n, total, |t| {
        let raw: f32 = oscs
            .iter_mut()
            .zip(METAL)
            .map(|(osc, hz)| osc.square(hz, sr))
            .sum();
        high.process(raw / 6.0) * (-t / tau).exp() * n.velocity * 1.4 * end_fade(t, total)
    })
}

fn hihat(n: &Note) -> Vec<f32> {
    hat(n, 0.025, 0.12)
}

fn open_hat(n: &Note) -> Vec<f32> {
    hat(n, 0.22, 0.6)
}

/// Clap: four quick noise bursts and a longer tail through a band-pass.
fn clap(n: &Note) -> Vec<f32> {
    let sr = n.sample_rate;
    let mut noise = rng(n, 0xC1A9);
    let mut band = Biquad::bandpass(sr, 1400.0, 1.2);
    render_for(n, 0.35, |t| {
        let bursts = [0.0, 0.011, 0.022]
            .iter()
            .filter(|&&start| t >= start)
            .map(|&start| (-(t - start) / 0.006).exp())
            .fold(0.0_f32, f32::max);
        let tail = if t >= 0.033 {
            (-(t - 0.033) / 0.09).exp()
        } else {
            0.0
        };
        band.process(noise.next()) * bursts.max(tail) * n.velocity * 2.2 * end_fade(t, 0.35)
    })
}

/// Tom: a sine that sweeps down onto the note pitch.
fn tom(n: &Note) -> Vec<f32> {
    let sr = n.sample_rate;
    let mut phase = 0.0;
    render_for(n, 0.5, |t| {
        advance(&mut phase, n.freq * (1.0 + 0.6 * (-t / 0.05).exp()), sr);
        phase.sin() * (-t / 0.28).exp() * n.velocity * 0.9 * end_fade(t, 0.5)
    })
}

/// Cowbell: two detuned squares through a band-pass.
fn cowbell(n: &Note) -> Vec<f32> {
    let sr = n.sample_rate;
    let (mut a, mut b) = (Osc::default(), Osc::with_phase(0.3));
    let mut band = Biquad::bandpass(sr, 2400.0, 2.0);
    render_for(n, 0.4, |t| {
        let raw = a.square(540.0, sr) + b.square(800.0, sr);
        band.process(raw) * (-t / 0.1).exp() * n.velocity * 1.2 * end_fade(t, 0.4)
    })
}
