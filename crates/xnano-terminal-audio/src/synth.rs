//! Python surface for rendering instruments and applying effects.
//!
//! Everything here works without an audio device: a note renders to a
//! [`PySound`] that can be inspected, processed further, or handed to the
//! playback engine.

use std::sync::Arc;

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyBytes;

use crate::effects::{EffectKind, apply_chain};
use crate::instruments::{INSTRUMENTS, Note, find};
use crate::pitch;

pub const DEFAULT_SAMPLE_RATE: u32 = 44_100;
/// The longest window `TerminalSound.mix` renders.
const MAXIMUM_MIX_SECONDS: f64 = 3_600.0;
const MAX_NOTE_MS: u32 = 60_000;
/// Most effects one render accepts; every reverb or echo also adds a tail.
pub const MAX_EFFECTS: usize = 32;

fn invalid(message: impl Into<String>) -> PyErr {
    PyValueError::new_err(message.into())
}

/// Unwrap effect objects into descriptions, refusing absurd chain lengths.
pub fn effect_kinds(effects: Vec<PyAudioEffect>) -> PyResult<Vec<EffectKind>> {
    if effects.len() > MAX_EFFECTS {
        return Err(invalid(format!(
            "at most {MAX_EFFECTS} effects can be applied at once, got {}",
            effects.len()
        )));
    }
    Ok(effects.into_iter().map(|e| e.kind).collect())
}

fn unknown_instrument(instrument: &str) -> PyErr {
    let names: Vec<&str> = INSTRUMENTS.iter().map(|i| i.name).collect();
    invalid(format!(
        "unknown instrument {instrument:?}; choose one of: {}",
        names.join(", ")
    ))
}

fn check_range(name: &str, value: f32, low: f32, high: f32) -> PyResult<f32> {
    if (low..=high).contains(&value) {
        Ok(value)
    } else {
        Err(invalid(format!(
            "{name} must be between {low} and {high}, got {value}"
        )))
    }
}

/// An immutable audio effect description. Build one with the static constructors.
#[pyclass(
    name = "TerminalAudioEffect",
    module = "xnano_audio._xnano_audio",
    frozen,
    from_py_object
)]
#[derive(Clone)]
pub struct PyAudioEffect {
    pub(crate) kind: EffectKind,
}

#[pymethods]
impl PyAudioEffect {
    /// Lo-fi: quantize to `bits` and hold every `downsample`-th sample.
    #[staticmethod]
    #[pyo3(signature = (*, bits = 8, downsample = 4))]
    fn bit_crush(bits: u8, downsample: u32) -> PyResult<Self> {
        if !(1..=16).contains(&bits) {
            return Err(invalid(format!(
                "bits must be between 1 and 16, got {bits}"
            )));
        }
        if !(1..=256).contains(&downsample) {
            return Err(invalid(format!(
                "downsample must be between 1 and 256, got {downsample}"
            )));
        }
        Ok(Self {
            kind: EffectKind::Bitcrush { bits, downsample },
        })
    }

    /// Soft-clip distortion; higher `drive` is harsher.
    #[staticmethod]
    #[pyo3(signature = (*, drive = 4.0))]
    fn distortion(drive: f32) -> PyResult<Self> {
        let drive = check_range("drive", drive, 0.1, 100.0)?;
        Ok(Self {
            kind: EffectKind::Distortion { drive },
        })
    }

    /// Remove frequencies above `cutoff` hertz.
    #[staticmethod]
    #[pyo3(signature = (*, cutoff = 1200.0, resonance = 0.707))]
    fn low_pass(cutoff: f32, resonance: f32) -> PyResult<Self> {
        Ok(Self {
            kind: EffectKind::Lowpass {
                cutoff: check_range("cutoff", cutoff, 20.0, 20_000.0)?,
                q: check_range("resonance", resonance, 0.1, 20.0)?,
            },
        })
    }

    /// Remove frequencies below `cutoff` hertz.
    #[staticmethod]
    #[pyo3(signature = (*, cutoff = 400.0, resonance = 0.707))]
    fn high_pass(cutoff: f32, resonance: f32) -> PyResult<Self> {
        Ok(Self {
            kind: EffectKind::Highpass {
                cutoff: check_range("cutoff", cutoff, 20.0, 20_000.0)?,
                q: check_range("resonance", resonance, 0.1, 20.0)?,
            },
        })
    }

    /// Echoes every `time_milliseconds`, each repeat `feedback` as loud as the last.
    #[staticmethod]
    #[pyo3(signature = (*, time_milliseconds = 250.0, feedback = 0.4, mix = 0.35))]
    fn delay(time_milliseconds: f32, feedback: f32, mix: f32) -> PyResult<Self> {
        Ok(Self {
            kind: EffectKind::Delay {
                time_ms: check_range("time_milliseconds", time_milliseconds, 1.0, 2000.0)?,
                feedback: check_range("feedback", feedback, 0.0, 0.95)?,
                mix: check_range("mix", mix, 0.0, 1.0)?,
            },
        })
    }

    /// Room reverb: `room` sets the size, `damping` how quickly highs fade.
    #[staticmethod]
    #[pyo3(signature = (*, room = 0.5, damping = 0.5, mix = 0.25))]
    fn reverb(room: f32, damping: f32, mix: f32) -> PyResult<Self> {
        Ok(Self {
            kind: EffectKind::Reverb {
                room: check_range("room", room, 0.0, 1.0)?,
                damping: check_range("damping", damping, 0.0, 1.0)?,
                mix: check_range("mix", mix, 0.0, 1.0)?,
            },
        })
    }

    /// Amplitude wobble at `rate_hertz`, `depth` from 0 (none) to 1 (full).
    #[staticmethod]
    #[pyo3(signature = (*, rate_hertz = 5.0, depth = 0.5))]
    fn tremolo(rate_hertz: f32, depth: f32) -> PyResult<Self> {
        Ok(Self {
            kind: EffectKind::Tremolo {
                rate_hz: check_range("rate_hertz", rate_hertz, 0.1, 40.0)?,
                depth: check_range("depth", depth, 0.0, 1.0)?,
            },
        })
    }

    /// The effect's kind, such as `"reverb"`.
    #[getter]
    fn name(&self) -> &'static str {
        self.kind.name()
    }

    fn __repr__(&self) -> String {
        self.kind.repr()
    }

    fn __eq__(&self, other: &Self) -> bool {
        self.kind == other.kind
    }

    fn __hash__(&self) -> u64 {
        self.kind.hash_value()
    }

    fn __copy__(&self) -> Self {
        self.clone()
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.clone()
    }

    /// Chain two audio effects (or an effect and a sequence of effects) into an effect list.
    fn __or__<'py>(
        &self,
        py: Python<'py>,
        other: &Bound<'py, PyAny>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let mut chain = vec![self.clone()];
        match effects_of(other)? {
            Some(effects) => {
                chain.extend(effects);
                Ok(chain.into_pyobject(py)?.into_any())
            }
            None => Ok(py.NotImplemented().into_bound(py)),
        }
    }

    fn __ror__<'py>(
        &self,
        py: Python<'py>,
        other: &Bound<'py, PyAny>,
    ) -> PyResult<Bound<'py, PyAny>> {
        if let Some(mut effects) = effects_of(other)? {
            effects.push(self.clone());
            return Ok(effects.into_pyobject(py)?.into_any());
        }
        Ok(py.NotImplemented().into_bound(py))
    }
}

/// The effects behind `item`: an effect, a sequence of effects, or an object (such as an audio
/// customization) that can produce one with `to_audio_effect()`.
fn effects_of(item: &Bound<'_, PyAny>) -> PyResult<Option<Vec<PyAudioEffect>>> {
    if let Ok(effect) = item.extract::<PyAudioEffect>() {
        return Ok(Some(vec![effect]));
    }
    if let Ok(effects) = item.extract::<Vec<PyAudioEffect>>() {
        return Ok(Some(effects));
    }
    if item.hasattr("to_audio_effect")? {
        let effect = item.call_method0("to_audio_effect")?;
        return effects_of(&effect);
    }
    Ok(None)
}

/// A rendered mono sound: raw samples plus their sample rate.
#[pyclass(
    name = "TerminalSound",
    module = "xnano_audio._xnano_audio",
    frozen,
    from_py_object
)]
#[derive(Clone)]
pub struct PySound {
    pub(crate) samples: Arc<[f32]>,
    pub(crate) sample_rate: u32,
}

/// The Python type name of a value, for error messages.
fn type_name(value: &Bound<'_, PyAny>) -> String {
    value
        .get_type()
        .name()
        .map_or_else(|_| "object".to_owned(), |name| name.to_string())
}

/// The `(sound, offset_seconds, gain)` layers given to `TerminalSound.mix`, each checked for its
/// shape so a mistake names the layer and what to pass.
fn mix_layers(layers: &Bound<'_, PyAny>) -> PyResult<Vec<(PySound, f64, f64)>> {
    let shape = "TerminalSound.mix needs layers as a sequence of (sound, offset_seconds, gain) \
                 tuples, for example [(kick, 0.0, 1.0), (snare, 0.5, 0.8)]";
    let items = layers.try_iter().map_err(|_| {
        PyTypeError::new_err(format!(
            "{shape}; got a {} instead of a sequence. Pass a list of layers.",
            type_name(layers)
        ))
    })?;
    let mut parsed = Vec::new();
    for (index, item) in items.enumerate() {
        let item = item?;
        if item.extract::<PySound>().is_ok() {
            return Err(PyTypeError::new_err(format!(
                "{shape}; layer {index} is a TerminalSound on its own. Wrap it as (sound, 0.0, \
                 1.0)."
            )));
        }
        let parts = match item.extract::<Vec<Bound<'_, PyAny>>>() {
            Ok(parts) if !item.is_instance_of::<pyo3::types::PyString>() => parts,
            _ => {
                return Err(PyTypeError::new_err(format!(
                    "{shape}; layer {index} is a {}. Wrap each sound as (sound, offset_seconds, \
                     gain).",
                    type_name(&item)
                )));
            }
        };
        if parts.len() != 3 {
            return Err(PyValueError::new_err(format!(
                "{shape}; layer {index} has {} values. Pass exactly (sound, offset_seconds, gain), \
                 for example (sound, 0.0, 1.0).",
                parts.len()
            )));
        }
        let sound = parts[0].extract::<PySound>().map_err(|_| {
            PyTypeError::new_err(format!(
                "{shape}; the first value of layer {index} is a {}, not a TerminalSound. Render \
                 the sound first and pass it as (sound, offset_seconds, gain).",
                type_name(&parts[0])
            ))
        })?;
        let number = |position: usize, label: &str| {
            parts[position].extract::<f64>().map_err(|_| {
                PyTypeError::new_err(format!(
                    "{shape}; the {label} of layer {index} must be a number, not a {}.",
                    type_name(&parts[position])
                ))
            })
        };
        parsed.push((sound, number(1, "offset_seconds")?, number(2, "gain")?));
    }
    Ok(parsed)
}

#[pymethods]
impl PySound {
    /// Build a sound from your own mono floats (a custom instrument, a
    /// generated waveform, a numpy array converted with `.tolist()`).
    ///
    /// Values should lie in -1.0..1.0; they are not rescaled.
    #[staticmethod]
    #[pyo3(signature = (samples, *, sample_rate = DEFAULT_SAMPLE_RATE))]
    fn from_samples(samples: Vec<f32>, sample_rate: u32) -> PyResult<Self> {
        Self::build(samples, sample_rate)
    }

    /// Build a sound from little-endian 32-bit float bytes, the inverse of
    /// `to_bytes`.
    #[staticmethod]
    #[pyo3(signature = (data, *, sample_rate = DEFAULT_SAMPLE_RATE))]
    fn from_bytes(data: &[u8], sample_rate: u32) -> PyResult<Self> {
        if !data.len().is_multiple_of(4) {
            return Err(invalid(format!(
                "byte length must be a multiple of 4 (32-bit floats), got {}",
                data.len()
            )));
        }
        let samples = data
            .as_chunks::<4>()
            .0
            .iter()
            .map(|c| f32::from_le_bytes(*c))
            .collect();
        Self::build(samples, sample_rate)
    }

    #[getter]
    fn sample_rate(&self) -> u32 {
        self.sample_rate
    }

    /// Length in milliseconds, including any effect tail.
    #[getter]
    fn duration_milliseconds(&self) -> f64 {
        self.samples.len() as f64 * 1000.0 / f64::from(self.sample_rate)
    }

    /// Largest absolute sample value, from 0.0 to 1.0.
    #[getter]
    fn peak(&self) -> f32 {
        self.samples.iter().fold(0.0_f32, |m, &x| m.max(x.abs()))
    }

    /// Root-mean-square level, from 0.0 to 1.0.
    #[getter]
    fn root_mean_square(&self) -> f32 {
        if self.samples.is_empty() {
            return 0.0;
        }
        let sum: f32 = self.samples.iter().map(|x| x * x).sum();
        (sum / self.samples.len() as f32).sqrt()
    }

    /// The samples as little-endian 32-bit floats.
    fn to_bytes<'py>(&self, py: Python<'py>) -> Bound<'py, PyBytes> {
        let bytes: Vec<u8> = self.samples.iter().flat_map(|x| x.to_le_bytes()).collect();
        PyBytes::new(py, &bytes)
    }

    /// The samples as a list of floats.
    fn samples(&self) -> Vec<f32> {
        self.samples.to_vec()
    }

    /// The loudness outline of the sound: `points` peak levels from 0.0 to 1.0.
    ///
    /// Each value is the largest absolute sample in one equal slice of the
    /// sound, which is what a waveform or a sparkline draws.
    fn envelope(&self, points: usize) -> PyResult<Vec<f32>> {
        if !(1..=100_000).contains(&points) {
            return Err(invalid(format!(
                "points must be between 1 and 100000, got {points}"
            )));
        }
        let length = self.samples.len();
        Ok((0..points)
            .map(|index| {
                let start = index * length / points;
                let end = ((index + 1) * length / points).max(start + 1).min(length);
                self.samples[start.min(length - 1)..end]
                    .iter()
                    .fold(0.0_f32, |peak, value| peak.max(value.abs()))
            })
            .collect())
    }

    /// A new sound with `effects` applied in order. Echo and reverb tails
    /// make the result longer than the original.
    fn with_effects(&self, py: Python<'_>, effects: Vec<PyAudioEffect>) -> PyResult<Self> {
        let kinds = effect_kinds(effects)?;
        let (samples, rate) = (Arc::clone(&self.samples), self.sample_rate);
        let processed = py.detach(move || apply_chain(samples.to_vec(), &kinds, rate as f32));
        Ok(Self {
            samples: processed.into(),
            sample_rate: self.sample_rate,
        })
    }

    /// Mix sounds placed on a timeline into one sound.
    ///
    /// Each layer is `(sound, offset_seconds, gain)`: the sound begins `offset_seconds` into the
    /// timeline and is multiplied by `gain`. The result is the part of the timeline from
    /// `start_seconds` for `duration_seconds`, summed and limited to -1.0..1.0.
    #[staticmethod]
    #[pyo3(signature = (layers, *, duration_seconds, start_seconds = 0.0, sample_rate = DEFAULT_SAMPLE_RATE))]
    fn mix(
        py: Python<'_>,
        layers: &Bound<'_, PyAny>,
        duration_seconds: f64,
        start_seconds: f64,
        sample_rate: u32,
    ) -> PyResult<Self> {
        if !(8_000..=192_000).contains(&sample_rate) {
            return Err(invalid(format!(
                "sample_rate must be between 8000 and 192000, got {sample_rate}. Pass the rate the \
                 sounds were rendered at."
            )));
        }
        if !duration_seconds.is_finite()
            || duration_seconds <= 0.0
            || duration_seconds > MAXIMUM_MIX_SECONDS
        {
            return Err(invalid(format!(
                "duration_seconds must be a number above 0 and at most {MAXIMUM_MIX_SECONDS}, got \
                 {duration_seconds}. Pass the length of the window to mix."
            )));
        }
        if !start_seconds.is_finite() {
            return Err(invalid(format!(
                "start_seconds must be a finite number, got {start_seconds}. Pass the time on the \
                 timeline where the mixed sound begins."
            )));
        }
        let length = (duration_seconds * f64::from(sample_rate)).round() as usize;
        if length == 0 {
            return Err(invalid(format!(
                "duration_seconds={duration_seconds} is shorter than one sample at {sample_rate} \
                 Hz. Pass a longer window."
            )));
        }
        let layers = mix_layers(layers)?;
        let rate = f64::from(sample_rate);
        // (samples, index in the output where sample 0 of the layer lands, gain)
        let mut placed: Vec<(Arc<[f32]>, i64, f32)> = Vec::with_capacity(layers.len());
        for (index, (sound, offset_seconds, gain)) in layers.into_iter().enumerate() {
            if sound.sample_rate != sample_rate {
                return Err(invalid(format!(
                    "layer {index} was rendered at {} Hz but the mix is at {sample_rate} Hz. \
                     Render every sound at the same rate and pass it as sample_rate.",
                    sound.sample_rate
                )));
            }
            if !offset_seconds.is_finite() {
                return Err(invalid(format!(
                    "layer {index} has offset_seconds={offset_seconds}. Use a finite number of \
                     seconds on the timeline."
                )));
            }
            if !gain.is_finite() || gain < 0.0 {
                return Err(invalid(format!(
                    "layer {index} has gain={gain}. Use a finite number of 0.0 or more."
                )));
            }
            let landing = ((offset_seconds - start_seconds) * rate).round() as i64;
            placed.push((sound.samples, landing, gain as f32));
        }
        let samples = py.detach(move || {
            let mut mixed = vec![0.0_f32; length];
            for (samples, landing, gain) in &placed {
                let first = (*landing).max(0) as usize;
                if first >= length {
                    continue;
                }
                let skipped = landing.saturating_neg().max(0) as usize;
                if skipped >= samples.len() {
                    continue;
                }
                let count = (length - first).min(samples.len() - skipped);
                for (target, source) in mixed[first..first + count]
                    .iter_mut()
                    .zip(&samples[skipped..skipped + count])
                {
                    *target += source * gain;
                }
            }
            for sample in &mut mixed {
                *sample = sample.clamp(-1.0, 1.0);
            }
            mixed
        });
        Self::build(samples, sample_rate)
    }

    /// Apply one or more audio effects (or sequences of audio effects) and return the new sound.
    #[pyo3(signature = (*effects))]
    fn add(&self, py: Python<'_>, effects: &Bound<'_, pyo3::types::PyTuple>) -> PyResult<Self> {
        let mut collected = Vec::new();
        for item in effects.iter() {
            if let Some(effects) = effects_of(&item)? {
                collected.extend(effects);
            } else {
                return Err(pyo3::exceptions::PyTypeError::new_err(
                    "TerminalSound.add() expects TerminalAudioEffect objects or sequences of them",
                ));
            }
        }
        self.with_effects(py, collected)
    }

    fn __or__<'py>(
        &self,
        py: Python<'py>,
        other: &Bound<'py, PyAny>,
    ) -> PyResult<Bound<'py, PyAny>> {
        match effects_of(other)? {
            Some(effects) => Ok(self
                .with_effects(py, effects)?
                .into_pyobject(py)?
                .into_any()),
            None => Ok(py.NotImplemented().into_bound(py)),
        }
    }

    fn __len__(&self) -> usize {
        self.samples.len()
    }

    fn __eq__(&self, other: &Self) -> bool {
        self.sample_rate == other.sample_rate && self.samples == other.samples
    }

    fn __hash__(&self) -> u64 {
        use std::hash::{Hash, Hasher};
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        self.sample_rate.hash(&mut hasher);
        for sample in self.samples.iter() {
            (sample + 0.0).to_bits().hash(&mut hasher);
        }
        hasher.finish()
    }

    fn __copy__(&self) -> Self {
        self.clone()
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "TerminalSound({:.0} ms @ {} Hz, peak {:.2})",
            self.duration_milliseconds(),
            self.sample_rate,
            self.peak()
        )
    }
}

impl PySound {
    fn build(samples: Vec<f32>, sample_rate: u32) -> PyResult<Self> {
        if samples.is_empty() {
            return Err(invalid(
                "a sound needs at least one sample value; pass a non-empty list of floats",
            ));
        }
        if !(8_000..=192_000).contains(&sample_rate) {
            return Err(invalid(format!(
                "sample_rate must be between 8000 and 192000, got {sample_rate}"
            )));
        }
        if samples.iter().any(|x| !x.is_finite()) {
            return Err(invalid(
                "every sample value must be a finite number (no NaN or infinity); \
                 check the values passed to the sound",
            ));
        }
        Ok(Self {
            samples: samples.into(),
            sample_rate,
        })
    }
}

/// Render `instrument` playing `note` into a sound.
pub fn render(
    py: Python<'_>,
    instrument: &str,
    note: &Bound<'_, PyAny>,
    duration_ms: u32,
    velocity: f32,
    effects: Vec<EffectKind>,
    sample_rate: u32,
) -> PyResult<PySound> {
    let definition = find(instrument).ok_or_else(|| unknown_instrument(instrument))?;
    if !(1..=MAX_NOTE_MS).contains(&duration_ms) {
        return Err(invalid(format!(
            "duration_milliseconds must be between 1 and {MAX_NOTE_MS}, got {duration_ms}"
        )));
    }
    if !(8_000..=192_000).contains(&sample_rate) {
        return Err(invalid(format!(
            "sample_rate must be between 8000 and 192000, got {sample_rate}"
        )));
    }
    if velocity.is_nan() {
        return Err(invalid(
            "velocity must be a number between 0.0 and 1.0, got NaN",
        ));
    }
    let freq = pitch::note_to_hz(note)?;
    let note = Note {
        freq,
        gate: duration_ms as f32 / 1000.0,
        velocity: velocity.clamp(0.0, 1.0),
        sample_rate: sample_rate as f32,
    };
    let samples = py.detach(move || {
        let raw = definition.render(&note);
        apply_chain(raw, &effects, note.sample_rate)
    });
    Ok(PySound {
        samples: samples.into(),
        sample_rate,
    })
}

/// Names of every built-in instrument.
#[pyfunction]
fn instrument_names() -> Vec<&'static str> {
    INSTRUMENTS.iter().map(|i| i.name).collect()
}

/// Whether an instrument rings for its own length and ignores `duration_milliseconds`.
#[pyfunction]
fn is_percussive(instrument: &str) -> PyResult<bool> {
    find(instrument)
        .map(|i| i.percussive)
        .ok_or_else(|| unknown_instrument(instrument))
}

/// Convert a note (`"C#4"`, a MIDI number, or hertz) to hertz.
#[pyfunction]
fn note_to_hertz(note: &Bound<'_, PyAny>) -> PyResult<f32> {
    pitch::note_to_hz(note)
}

/// Render a note with a built-in instrument, without needing an audio device.
///
/// `note` is a name (`"C#4"`), a MIDI number, or hertz as a float.
#[pyfunction]
#[pyo3(signature = (
    instrument,
    note = None,
    *,
    duration_milliseconds = 500,
    velocity = 0.8,
    effects = None,
    sample_rate = DEFAULT_SAMPLE_RATE,
))]
fn render_note(
    py: Python<'_>,
    instrument: &str,
    note: Option<&Bound<'_, PyAny>>,
    duration_milliseconds: u32,
    velocity: f32,
    effects: Option<Vec<PyAudioEffect>>,
    sample_rate: u32,
) -> PyResult<PySound> {
    let default_note = "C4".into_pyobject(py)?.into_any();
    let kinds = effect_kinds(effects.unwrap_or_default())?;
    render(
        py,
        instrument,
        note.unwrap_or(&default_note),
        duration_milliseconds,
        velocity,
        kinds,
        sample_rate,
    )
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyAudioEffect>()?;
    m.add_class::<PySound>()?;
    m.add_function(wrap_pyfunction!(render_note, m)?)?;
    m.add_function(wrap_pyfunction!(instrument_names, m)?)?;
    m.add_function(wrap_pyfunction!(is_percussive, m)?)?;
    m.add_function(wrap_pyfunction!(note_to_hertz, m)?)?;
    Ok(())
}
