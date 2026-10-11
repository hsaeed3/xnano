//! Offline effects that run over a rendered buffer.
//!
//! An [`EffectKind`] is an immutable description; all processing state is
//! created fresh inside [`EffectKind::apply`], so one effect can be reused
//! for any number of sounds.

use std::f32::consts::TAU;

use crate::dsp::{Biquad, limit};

/// A whole chain never extends a sound by more than this.
const MAX_TAIL_SECONDS: f32 = 30.0;

#[derive(Clone, Debug, PartialEq)]
pub enum EffectKind {
    /// Quantize to `bits` and hold every `downsample`-th sample.
    Bitcrush {
        bits: u8,
        downsample: u32,
    },
    /// Tanh soft clipping; `drive` of 1 is nearly clean.
    Distortion {
        drive: f32,
    },
    Lowpass {
        cutoff: f32,
        q: f32,
    },
    Highpass {
        cutoff: f32,
        q: f32,
    },
    /// Echoes: `mix` of the delayed signal is added, `feedback` repeats it.
    Delay {
        time_ms: f32,
        feedback: f32,
        mix: f32,
    },
    /// Freeverb-style room.
    Reverb {
        room: f32,
        damping: f32,
        mix: f32,
    },
    /// Amplitude wobble.
    Tremolo {
        rate_hz: f32,
        depth: f32,
    },
}

impl EffectKind {
    /// Python-facing text: the constructor call that rebuilds the effect.
    pub fn repr(&self) -> String {
        match *self {
            Self::Bitcrush { bits, downsample } => {
                format!("TerminalAudioEffect.bit_crush(bits={bits}, downsample={downsample})")
            }
            Self::Distortion { drive } => {
                format!("TerminalAudioEffect.distortion(drive={drive:?})")
            }
            Self::Lowpass { cutoff, q } => {
                format!("TerminalAudioEffect.low_pass(cutoff={cutoff:?}, resonance={q:?})")
            }
            Self::Highpass { cutoff, q } => {
                format!("TerminalAudioEffect.high_pass(cutoff={cutoff:?}, resonance={q:?})")
            }
            Self::Delay {
                time_ms,
                feedback,
                mix,
            } => {
                format!(
                    "TerminalAudioEffect.delay(time_milliseconds={time_ms:?}, \
                     feedback={feedback:?}, mix={mix:?})"
                )
            }
            Self::Reverb { room, damping, mix } => {
                format!(
                    "TerminalAudioEffect.reverb(room={room:?}, damping={damping:?}, mix={mix:?})"
                )
            }
            Self::Tremolo { rate_hz, depth } => {
                format!("TerminalAudioEffect.tremolo(rate_hertz={rate_hz:?}, depth={depth:?})")
            }
        }
    }

    /// Hash consistent with `PartialEq` (constructors reject NaN, and
    /// `-0.0 == 0.0` hash alike).
    pub fn hash_value(&self) -> u64 {
        use std::hash::{Hash, Hasher};
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        self.name().hash(&mut hasher);
        let bits = |x: f32| (x + 0.0).to_bits();
        match *self {
            Self::Bitcrush { bits, downsample } => (bits, downsample).hash(&mut hasher),
            Self::Distortion { drive } => bits(drive).hash(&mut hasher),
            Self::Lowpass { cutoff, q } | Self::Highpass { cutoff, q } => {
                (bits(cutoff), bits(q)).hash(&mut hasher);
            }
            Self::Delay {
                time_ms,
                feedback,
                mix,
            } => {
                (bits(time_ms), bits(feedback), bits(mix)).hash(&mut hasher);
            }
            Self::Reverb { room, damping, mix } => {
                (bits(room), bits(damping), bits(mix)).hash(&mut hasher);
            }
            Self::Tremolo { rate_hz, depth } => (bits(rate_hz), bits(depth)).hash(&mut hasher),
        }
        hasher.finish()
    }

    pub fn name(&self) -> &'static str {
        match self {
            Self::Bitcrush { .. } => "bit_crush",
            Self::Distortion { .. } => "distortion",
            Self::Lowpass { .. } => "low_pass",
            Self::Highpass { .. } => "high_pass",
            Self::Delay { .. } => "delay",
            Self::Reverb { .. } => "reverb",
            Self::Tremolo { .. } => "tremolo",
        }
    }

    /// Extra seconds of silence this effect needs so its tail is not cut off.
    pub fn tail_seconds(&self) -> f32 {
        match *self {
            Self::Delay {
                time_ms, feedback, ..
            } => {
                let repeats = if feedback < 0.001 {
                    1.0
                } else {
                    (0.001_f32.ln() / feedback.ln()).ceil().max(1.0)
                };
                (time_ms / 1000.0 * repeats).min(6.0)
            }
            Self::Reverb { room, .. } => 1.2 + 3.0 * room,
            _ => 0.0,
        }
    }

    pub fn apply(&self, samples: &mut [f32], sample_rate: f32) {
        match *self {
            Self::Bitcrush { bits, downsample } => {
                let levels = f32::from(1_u16 << (bits.clamp(1, 16) - 1));
                let step = downsample.max(1) as usize;
                let mut held = 0.0;
                for (i, s) in samples.iter_mut().enumerate() {
                    if i % step == 0 {
                        held = (*s * levels).round() / levels;
                    }
                    *s = held;
                }
            }
            Self::Distortion { drive } => {
                let norm = drive.tanh().max(1e-3);
                for s in samples.iter_mut() {
                    *s = (drive * *s).tanh() / norm;
                }
            }
            Self::Lowpass { cutoff, q } => {
                let mut filter = Biquad::lowpass(sample_rate, cutoff, q);
                for s in samples.iter_mut() {
                    *s = filter.process(*s);
                }
            }
            Self::Highpass { cutoff, q } => {
                let mut filter = Biquad::highpass(sample_rate, cutoff, q);
                for s in samples.iter_mut() {
                    *s = filter.process(*s);
                }
            }
            Self::Delay {
                time_ms,
                feedback,
                mix,
            } => {
                let length = ((time_ms / 1000.0 * sample_rate) as usize).max(1);
                let mut line = vec![0.0_f32; length];
                for (i, s) in samples.iter_mut().enumerate() {
                    let slot = i % length;
                    let echo = line[slot];
                    line[slot] = *s + echo * feedback;
                    *s += echo * mix;
                }
            }
            Self::Reverb { room, damping, mix } => {
                Reverb::new(sample_rate, room, damping).process(samples, mix);
            }
            Self::Tremolo { rate_hz, depth } => {
                for (i, s) in samples.iter_mut().enumerate() {
                    let lfo = 0.5 - 0.5 * (TAU * rate_hz * i as f32 / sample_rate).cos();
                    *s *= 1.0 - depth * lfo;
                }
            }
        }
    }
}

/// Run `effects` in order over `samples`, first extending the buffer so tails
/// (echoes, reverb) ring out, then keeping the peak below `0.98`.
pub fn apply_chain(mut samples: Vec<f32>, effects: &[EffectKind], sample_rate: f32) -> Vec<f32> {
    if effects.is_empty() {
        return samples;
    }
    let tail: f32 = effects
        .iter()
        .map(EffectKind::tail_seconds)
        .sum::<f32>()
        .min(MAX_TAIL_SECONDS);
    samples.resize(samples.len() + (tail * sample_rate) as usize, 0.0);
    for effect in effects {
        effect.apply(&mut samples, sample_rate);
    }
    limit(&mut samples, 0.98);
    samples
}

// ------------------------------------------------------------------ reverb

struct Comb {
    line: Vec<f32>,
    index: usize,
    store: f32,
    feedback: f32,
    damp: f32,
}

impl Comb {
    fn process(&mut self, input: f32) -> f32 {
        let out = self.line[self.index];
        self.store = out * (1.0 - self.damp) + self.store * self.damp;
        self.line[self.index] = input + self.store * self.feedback;
        self.index = (self.index + 1) % self.line.len();
        out
    }
}

struct AllPass {
    line: Vec<f32>,
    index: usize,
}

impl AllPass {
    fn process(&mut self, input: f32) -> f32 {
        let buffered = self.line[self.index];
        self.line[self.index] = input + buffered * 0.5;
        self.index = (self.index + 1) % self.line.len();
        buffered - input
    }
}

/// Mono Freeverb: eight damped parallel combs into four series all-passes.
struct Reverb {
    combs: Vec<Comb>,
    allpasses: Vec<AllPass>,
}

impl Reverb {
    const COMBS: [usize; 8] = [1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617];
    const ALLPASSES: [usize; 4] = [556, 441, 341, 225];

    fn new(sample_rate: f32, room: f32, damping: f32) -> Self {
        let scale = sample_rate / 44_100.0;
        let size = |n: usize| ((n as f32 * scale) as usize).max(1);
        Self {
            combs: Self::COMBS
                .iter()
                .map(|&n| Comb {
                    line: vec![0.0; size(n)],
                    index: 0,
                    store: 0.0,
                    feedback: room.clamp(0.0, 1.0) * 0.28 + 0.7,
                    damp: damping.clamp(0.0, 1.0) * 0.4,
                })
                .collect(),
            allpasses: Self::ALLPASSES
                .iter()
                .map(|&n| AllPass {
                    line: vec![0.0; size(n)],
                    index: 0,
                })
                .collect(),
        }
    }

    fn process(&mut self, samples: &mut [f32], mix: f32) {
        for s in samples {
            let input = *s * 0.015;
            let mut wet: f32 = self.combs.iter_mut().map(|c| c.process(input)).sum();
            for allpass in &mut self.allpasses {
                wet = allpass.process(wet);
            }
            *s = *s * (1.0 - mix) + wet * 3.0 * mix;
        }
    }
}
