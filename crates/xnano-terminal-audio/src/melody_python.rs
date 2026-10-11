//! Python surface for notes and melodies.
//!
//! Each class wraps one item of [`crate::melody`] one to one. Values are immutable: every
//! change returns a new object, so Python can build any higher-level API on top.

use std::hash::{Hash, Hasher};

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyInt, PyIterator, PyList, PyString};

use crate::effects::apply_chain;
use crate::melody::{
    Melody, MelodyError, Note, ScheduledNote, TempoMap, TimeSignature, parse_pitch,
    pitch_from_number, pitch_name,
};
use crate::synth::{DEFAULT_SAMPLE_RATE, PyAudioEffect, PySound, effect_kinds};

fn value_error(error: MelodyError) -> PyErr {
    PyValueError::new_err(error.0)
}

fn hash_of(parts: &[u64]) -> u64 {
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    parts.hash(&mut hasher);
    hasher.finish()
}

/// Read a pitch given as a MIDI integer or a note name.
fn pitch_of(value: &Bound<'_, PyAny>) -> PyResult<u8> {
    if value.is_instance_of::<PyBool>() {
        return Err(PyTypeError::new_err(
            "pitch must be a MIDI number or a note name such as 'C4', not a bool",
        ));
    }
    if value.is_instance_of::<PyInt>() {
        return pitch_from_number(value.extract::<i64>()?).map_err(value_error);
    }
    if value.is_instance_of::<PyString>() {
        return parse_pitch(&value.extract::<String>()?).map_err(value_error);
    }
    Err(PyTypeError::new_err(
        "pitch must be a MIDI number or a note name such as 'C4'; use note_to_hertz for frequencies",
    ))
}

/// One note on a beat timeline.
#[pyclass(
    name = "TerminalNote",
    module = "xnano_audio._xnano_audio",
    frozen,
    eq,
    from_py_object
)]
#[derive(Clone, PartialEq)]
pub struct PyNote {
    pub(crate) inner: Note,
}

#[pymethods]
impl PyNote {
    #[new]
    #[pyo3(signature = (pitch, *, start_beats = 0.0, duration_beats = 1.0, velocity = 0.8))]
    fn new(
        pitch: &Bound<'_, PyAny>,
        start_beats: f64,
        duration_beats: f64,
        velocity: f32,
    ) -> PyResult<Self> {
        Note::new(pitch_of(pitch)?, velocity, start_beats, duration_beats)
            .map(|inner| Self { inner })
            .map_err(value_error)
    }

    /// The MIDI pitch, 0 to 127.
    #[getter]
    fn pitch(&self) -> u8 {
        self.inner.pitch
    }

    /// The sharp-spelled note name, such as ``C#4``.
    #[getter]
    fn name(&self) -> String {
        pitch_name(self.inner.pitch)
    }

    /// The pitch in hertz.
    #[getter]
    fn frequency_hertz(&self) -> f32 {
        self.inner.frequency_hertz()
    }

    /// The strength, 0.0 to 1.0.
    #[getter]
    fn velocity(&self) -> f32 {
        self.inner.velocity
    }

    /// Where the note starts, in beats.
    #[getter]
    fn start_beats(&self) -> f64 {
        self.inner.start_beats
    }

    /// How long the key is held, in beats.
    #[getter]
    fn duration_beats(&self) -> f64 {
        self.inner.duration_beats
    }

    /// Where the note ends, in beats.
    #[getter]
    fn end_beats(&self) -> f64 {
        self.inner.end_beats()
    }

    /// The note with another pitch (a MIDI number or a note name).
    fn with_pitch(&self, pitch: &Bound<'_, PyAny>) -> PyResult<Self> {
        Note::new(
            pitch_of(pitch)?,
            self.inner.velocity,
            self.inner.start_beats,
            self.inner.duration_beats,
        )
        .map(|inner| Self { inner })
        .map_err(value_error)
    }

    /// The note starting at another beat.
    fn with_start_beats(&self, start_beats: f64) -> PyResult<Self> {
        Note::new(
            self.inner.pitch,
            self.inner.velocity,
            start_beats,
            self.inner.duration_beats,
        )
        .map(|inner| Self { inner })
        .map_err(value_error)
    }

    /// The note held for another number of beats.
    fn with_duration_beats(&self, duration_beats: f64) -> PyResult<Self> {
        Note::new(
            self.inner.pitch,
            self.inner.velocity,
            self.inner.start_beats,
            duration_beats,
        )
        .map(|inner| Self { inner })
        .map_err(value_error)
    }

    /// The note with another strength.
    fn with_velocity(&self, velocity: f32) -> PyResult<Self> {
        Note::new(
            self.inner.pitch,
            velocity,
            self.inner.start_beats,
            self.inner.duration_beats,
        )
        .map(|inner| Self { inner })
        .map_err(value_error)
    }

    /// The note moved by ``semitones``.
    fn transposed(&self, semitones: i32) -> PyResult<Self> {
        self.inner
            .transposed(semitones)
            .map(|inner| Self { inner })
            .map_err(value_error)
    }

    fn __hash__(&self) -> u64 {
        hash_of(&[
            u64::from(self.inner.pitch),
            u64::from(self.inner.velocity.to_bits()),
            self.inner.start_beats.to_bits(),
            self.inner.duration_beats.to_bits(),
        ])
    }

    fn __copy__(&self) -> Self {
        self.clone()
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "TerminalNote('{}', start_beats={}, duration_beats={}, velocity={})",
            pitch_name(self.inner.pitch),
            self.inner.start_beats,
            self.inner.duration_beats,
            self.inner.velocity
        )
    }
}

/// How many beats make a bar.
#[pyclass(
    name = "TerminalTimeSignature",
    module = "xnano_audio._xnano_audio",
    frozen,
    eq,
    hash,
    from_py_object
)]
#[derive(Clone, PartialEq, Eq, Hash)]
pub struct PyTimeSignature {
    pub(crate) inner: TimeSignature,
}

#[pymethods]
impl PyTimeSignature {
    #[new]
    #[pyo3(signature = (numerator = 4, denominator = 4))]
    fn new(numerator: u8, denominator: u8) -> PyResult<Self> {
        TimeSignature::new(numerator, denominator)
            .map(|inner| Self { inner })
            .map_err(value_error)
    }

    /// Beat units per bar.
    #[getter]
    fn numerator(&self) -> u8 {
        self.inner.numerator
    }

    /// The note value of one beat unit.
    #[getter]
    fn denominator(&self) -> u8 {
        self.inner.denominator
    }

    /// The length of one bar in quarter-note beats.
    #[getter]
    fn bar_length_beats(&self) -> f64 {
        self.inner.bar_length_beats()
    }

    /// The zero-based bar and the beat inside it that ``beats`` falls on.
    fn bar_and_beat(&self, beats: f64) -> PyResult<(u64, f64)> {
        if !beats.is_finite() || beats < 0.0 {
            return Err(PyValueError::new_err(format!(
                "beats must be a finite number of zero or more, got {beats}"
            )));
        }
        Ok(self.inner.bar_and_beat(beats))
    }

    fn __copy__(&self) -> Self {
        self.clone()
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "TerminalTimeSignature({}, {})",
            self.inner.numerator, self.inner.denominator
        )
    }
}

/// Maps beats to seconds. The tempo is constant between changes.
#[pyclass(
    name = "TerminalTempoMap",
    module = "xnano_audio._xnano_audio",
    frozen,
    eq,
    from_py_object
)]
#[derive(Clone, PartialEq)]
pub struct PyTempoMap {
    pub(crate) inner: TempoMap,
}

#[pymethods]
impl PyTempoMap {
    #[new]
    #[pyo3(signature = (beats_per_minute = 120.0))]
    fn new(beats_per_minute: f64) -> PyResult<Self> {
        TempoMap::new(beats_per_minute)
            .map(|inner| Self { inner })
            .map_err(value_error)
    }

    /// The tempo before any change.
    #[getter]
    fn initial_beats_per_minute(&self) -> f64 {
        self.inner.initial_beats_per_minute()
    }

    /// The tempo changes as ``(beat, beats_per_minute)`` pairs in beat order.
    #[getter]
    fn changes(&self) -> Vec<(f64, f64)> {
        self.inner.changes().to_vec()
    }

    /// The map with a change to ``beats_per_minute`` at ``beat``.
    fn with_change(&self, beat: f64, beats_per_minute: f64) -> PyResult<Self> {
        self.inner
            .with_change(beat, beats_per_minute)
            .map(|inner| Self { inner })
            .map_err(value_error)
    }

    /// The map with every tempo multiplied by ``factor``.
    fn scaled(&self, factor: f64) -> PyResult<Self> {
        self.inner
            .scaled(factor)
            .map(|inner| Self { inner })
            .map_err(value_error)
    }

    /// The tempo in effect at ``beat``.
    fn beats_per_minute_at(&self, beat: f64) -> f64 {
        self.inner.beats_per_minute_at(beat)
    }

    /// Seconds from beat zero to ``beat``.
    fn beats_to_seconds(&self, beat: f64) -> PyResult<f64> {
        if !beat.is_finite() || beat < 0.0 {
            return Err(PyValueError::new_err(format!(
                "beat must be a finite number of zero or more, got {beat}"
            )));
        }
        Ok(self.inner.beats_to_seconds(beat))
    }

    /// The beat reached after ``seconds``.
    fn seconds_to_beats(&self, seconds: f64) -> PyResult<f64> {
        if !seconds.is_finite() || seconds < 0.0 {
            return Err(PyValueError::new_err(format!(
                "seconds must be a finite number of zero or more, got {seconds}"
            )));
        }
        Ok(self.inner.seconds_to_beats(seconds))
    }

    fn __hash__(&self) -> u64 {
        let mut parts = vec![self.inner.initial_beats_per_minute().to_bits()];
        for (beat, tempo) in self.inner.changes() {
            parts.push(beat.to_bits());
            parts.push(tempo.to_bits());
        }
        hash_of(&parts)
    }

    fn __copy__(&self) -> Self {
        self.clone()
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "TerminalTempoMap({}, changes={:?})",
            self.inner.initial_beats_per_minute(),
            self.inner.changes()
        )
    }
}

/// A note placed on an external clock.
#[pyclass(
    name = "TerminalScheduledNote",
    module = "xnano_audio._xnano_audio",
    frozen,
    eq,
    from_py_object
)]
#[derive(Clone, PartialEq)]
pub struct PyScheduledNote {
    inner: ScheduledNote,
}

#[pymethods]
impl PyScheduledNote {
    /// The note, in melody beats.
    #[getter]
    fn note(&self) -> PyNote {
        PyNote {
            inner: self.inner.note,
        }
    }

    /// When the note starts, in seconds on the external clock.
    #[getter]
    fn start_seconds(&self) -> f64 {
        self.inner.start_seconds
    }

    /// How long the key is held, in seconds.
    #[getter]
    fn duration_seconds(&self) -> f64 {
        self.inner.duration_seconds
    }

    /// When the key is released, in seconds on the external clock.
    #[getter]
    fn end_seconds(&self) -> f64 {
        self.inner.start_seconds + self.inner.duration_seconds
    }

    /// How many times the melody had looped before this note, starting at zero.
    #[getter]
    fn iteration(&self) -> u64 {
        self.inner.iteration
    }

    fn __copy__(&self) -> Self {
        self.clone()
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "TerminalScheduledNote('{}', start_seconds={}, duration_seconds={}, iteration={})",
            pitch_name(self.inner.note.pitch),
            self.inner.start_seconds,
            self.inner.duration_seconds,
            self.inner.iteration
        )
    }
}

/// Notes on a beat timeline with a tempo map and a time signature.
#[pyclass(
    name = "TerminalMelody",
    module = "xnano_audio._xnano_audio",
    frozen,
    eq,
    from_py_object
)]
#[derive(Clone, PartialEq)]
pub struct PyMelody {
    inner: Melody,
}

impl PyMelody {
    fn wrap(result: Result<Melody, MelodyError>) -> PyResult<Self> {
        result.map(|inner| Self { inner }).map_err(value_error)
    }
}

fn notes_of(notes: &[PyNote]) -> Vec<Note> {
    notes.iter().map(|note| note.inner).collect()
}

fn pitches_of(pitches: &Bound<'_, PyAny>) -> PyResult<Vec<u8>> {
    pitches
        .try_iter()?
        .map(|item| pitch_of(&item?))
        .collect::<PyResult<Vec<_>>>()
}

#[pymethods]
impl PyMelody {
    #[new]
    #[pyo3(signature = (notes = None, *, tempo_map = None, time_signature = None, length_beats = 0.0))]
    fn new(
        notes: Option<Vec<PyNote>>,
        tempo_map: Option<PyTempoMap>,
        time_signature: Option<PyTimeSignature>,
        length_beats: f64,
    ) -> PyResult<Self> {
        Self::wrap(Melody::new(
            notes_of(&notes.unwrap_or_default()),
            tempo_map.map(|map| map.inner).unwrap_or_default(),
            time_signature.map(|value| value.inner).unwrap_or_default(),
            length_beats,
        ))
    }

    /// The notes in start order.
    #[getter]
    fn notes(&self) -> Vec<PyNote> {
        self.inner
            .notes()
            .iter()
            .map(|note| PyNote { inner: *note })
            .collect()
    }

    /// The tempo map.
    #[getter]
    fn tempo_map(&self) -> PyTempoMap {
        PyTempoMap {
            inner: self.inner.tempo_map().clone(),
        }
    }

    /// The time signature.
    #[getter]
    fn time_signature(&self) -> PyTimeSignature {
        PyTimeSignature {
            inner: self.inner.time_signature(),
        }
    }

    /// The end of the last note, or the explicit length when that is longer, in beats.
    #[getter]
    fn length_beats(&self) -> f64 {
        self.inner.length_beats()
    }

    /// The melody's length in seconds.
    #[getter]
    fn duration_seconds(&self) -> f64 {
        self.inner.duration_seconds()
    }

    /// The melody with ``notes`` added.
    fn with_notes(&self, notes: Vec<PyNote>) -> PyResult<Self> {
        Self::wrap(self.inner.with_notes(&notes_of(&notes)))
    }

    /// The melody with another tempo map.
    fn with_tempo_map(&self, tempo_map: &PyTempoMap) -> Self {
        Self {
            inner: self.inner.with_tempo_map(tempo_map.inner.clone()),
        }
    }

    /// The melody with another time signature.
    fn with_time_signature(&self, time_signature: &PyTimeSignature) -> Self {
        Self {
            inner: self.inner.with_time_signature(time_signature.inner),
        }
    }

    /// The melody lasting at least ``length_beats``, which adds trailing silence.
    fn with_length_beats(&self, length_beats: f64) -> PyResult<Self> {
        Self::wrap(self.inner.with_length_beats(length_beats))
    }

    /// The melody with one note appended at its end.
    #[pyo3(signature = (pitch, *, duration_beats = 1.0, velocity = 0.8))]
    fn appended_note(
        &self,
        pitch: &Bound<'_, PyAny>,
        duration_beats: f64,
        velocity: f32,
    ) -> PyResult<Self> {
        Self::wrap(
            self.inner
                .appended_chord(&[pitch_of(pitch)?], duration_beats, velocity),
        )
    }

    /// The melody with notes that sound together appended at its end.
    #[pyo3(signature = (pitches, *, duration_beats = 1.0, velocity = 0.8))]
    fn appended_chord(
        &self,
        pitches: &Bound<'_, PyAny>,
        duration_beats: f64,
        velocity: f32,
    ) -> PyResult<Self> {
        Self::wrap(
            self.inner
                .appended_chord(&pitches_of(pitches)?, duration_beats, velocity),
        )
    }

    /// The melody with silence appended at its end.
    #[pyo3(signature = (duration_beats = 1.0))]
    fn appended_rest(&self, duration_beats: f64) -> PyResult<Self> {
        Self::wrap(self.inner.appended_rest(duration_beats))
    }

    /// The melody with every pitch moved by ``semitones``.
    fn transposed(&self, semitones: i32) -> PyResult<Self> {
        Self::wrap(self.inner.transposed(semitones))
    }

    /// The melody moved later by ``beats``, or earlier when negative.
    fn shifted(&self, beats: f64) -> PyResult<Self> {
        Self::wrap(self.inner.shifted(beats))
    }

    /// The melody with every start and duration multiplied by ``factor``.
    fn stretched(&self, factor: f64) -> PyResult<Self> {
        Self::wrap(self.inner.stretched(factor))
    }

    /// The melody played ``count`` times in a row.
    fn repeated(&self, count: usize) -> PyResult<Self> {
        Self::wrap(self.inner.repeated(count))
    }

    /// The melody followed by ``other``.
    fn followed_by(&self, other: &Self) -> PyResult<Self> {
        Self::wrap(self.inner.followed_by(&other.inner))
    }

    /// The notes of both melodies played together.
    fn layered_with(&self, other: &Self) -> PyResult<Self> {
        Self::wrap(self.inner.layered_with(&other.inner))
    }

    /// The notes that start in ``[from_beats, to_beats)``.
    fn notes_between_beats(&self, from_beats: f64, to_beats: f64) -> Vec<PyNote> {
        self.inner
            .notes_between_beats(from_beats, to_beats)
            .iter()
            .map(|note| PyNote { inner: *note })
            .collect()
    }

    /// The notes that start in ``[from_seconds, to_seconds)`` of melody time.
    fn notes_between_seconds(&self, from_seconds: f64, to_seconds: f64) -> Vec<PyNote> {
        self.inner
            .notes_between_seconds(from_seconds, to_seconds)
            .iter()
            .map(|note| PyNote { inner: *note })
            .collect()
    }

    /// The notes due on an external clock between two readings.
    #[pyo3(signature = (from_elapsed_seconds, to_elapsed_seconds, *, start_seconds = 0.0, should_loop = false))]
    fn scheduled_between(
        &self,
        from_elapsed_seconds: f64,
        to_elapsed_seconds: f64,
        start_seconds: f64,
        should_loop: bool,
    ) -> PyResult<Vec<PyScheduledNote>> {
        self.inner
            .scheduled_between(
                from_elapsed_seconds,
                to_elapsed_seconds,
                start_seconds,
                should_loop,
            )
            .map(|items| {
                items
                    .into_iter()
                    .map(|inner| PyScheduledNote { inner })
                    .collect()
            })
            .map_err(value_error)
    }

    /// Render the melody, or the notes starting inside a window, to a sound.
    #[pyo3(signature = (
        instrument = "piano",
        *,
        sample_rate = DEFAULT_SAMPLE_RATE,
        effects = None,
        from_seconds = 0.0,
        to_seconds = None,
    ))]
    fn render(
        &self,
        py: Python<'_>,
        instrument: &str,
        sample_rate: u32,
        effects: Option<Vec<PyAudioEffect>>,
        from_seconds: f64,
        to_seconds: Option<f64>,
    ) -> PyResult<PySound> {
        let kinds = effect_kinds(effects.unwrap_or_default())?;
        let melody = self.inner.clone();
        let instrument = instrument.to_owned();
        let samples = py
            .detach(move || melody.render(&instrument, sample_rate, from_seconds, to_seconds))
            .map_err(value_error)?;
        let samples = apply_chain(samples, &kinds, sample_rate as f32);
        Ok(PySound {
            samples: samples.into(),
            sample_rate,
        })
    }

    fn __len__(&self) -> usize {
        self.inner.notes().len()
    }

    fn __iter__<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyIterator>> {
        PyList::new(py, self.notes())?.try_iter()
    }

    fn __copy__(&self) -> Self {
        self.clone()
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "TerminalMelody(notes={}, length_beats={}, beats_per_minute={})",
            self.inner.notes().len(),
            self.inner.length_beats(),
            self.inner.tempo_map().initial_beats_per_minute()
        )
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyNote>()?;
    m.add_class::<PyTimeSignature>()?;
    m.add_class::<PyTempoMap>()?;
    m.add_class::<PyScheduledNote>()?;
    m.add_class::<PyMelody>()?;
    Ok(())
}
