//! Notes and melodies on a beat timeline.
//!
//! A [`Melody`] is a list of [`Note`] values positioned in beats, plus a [`TempoMap`] that
//! turns beats into seconds and a [`TimeSignature`]. Nothing here depends on Python or on an
//! audio device: the same model can be queried for the notes that start inside a window of
//! seconds on any external clock, or rendered to samples with a built-in instrument.

use std::fmt;

use crate::instruments::{Note as InstrumentNote, find};
use crate::pitch::midi_to_hz;

/// Highest MIDI pitch.
pub const MAXIMUM_PITCH: u8 = 127;
/// Slowest accepted tempo.
pub const MINIMUM_BEATS_PER_MINUTE: f64 = 1.0;
/// Fastest accepted tempo.
pub const MAXIMUM_BEATS_PER_MINUTE: f64 = 1000.0;
/// Most notes one melody holds.
pub const MAXIMUM_NOTES: usize = 100_000;
/// Longest span, in seconds, one render produces.
pub const MAXIMUM_RENDER_SECONDS: f64 = 600.0;
/// Most tempo changes one tempo map holds.
pub const MAXIMUM_TEMPO_CHANGES: usize = 10_000;

const NAMES: [&str; 12] = [
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B",
];
const EPSILON: f64 = 1e-9;
const CEILING: f32 = 0.95;

/// A message that explains what was wrong and what to do next.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MelodyError(pub String);

impl fmt::Display for MelodyError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl std::error::Error for MelodyError {}

fn error<T>(message: String) -> Result<T, MelodyError> {
    Err(MelodyError(message))
}

fn finite(name: &str, value: f64) -> Result<f64, MelodyError> {
    if value.is_finite() {
        Ok(value)
    } else {
        error(format!("{name} must be a finite number, got {value}"))
    }
}

/// The MIDI pitch named by `text`: a name such as `C4`, `c#3` or `Db5`, or a number such as `60`.
///
/// `C4` is 60 and a name without an octave means octave 4.
pub fn parse_pitch(text: &str) -> Result<u8, MelodyError> {
    let trimmed = text.trim();
    if let Ok(number) = trimmed.parse::<i64>() {
        return pitch_from_number(number);
    }
    let mut characters = trimmed.chars().peekable();
    let semitone: i64 = match characters.next().map(|c| c.to_ascii_uppercase()) {
        Some('C') => 0,
        Some('D') => 2,
        Some('E') => 4,
        Some('F') => 5,
        Some('G') => 7,
        Some('A') => 9,
        Some('B') => 11,
        _ => return unknown_pitch(text),
    };
    let mut accidental = 0;
    while let Some(&character) = characters.peek() {
        match character {
            '#' | '♯' => accidental += 1,
            'b' | '♭' => accidental -= 1,
            _ => break,
        }
        characters.next();
    }
    let rest: String = characters.collect();
    let octave: i64 = if rest.is_empty() {
        4
    } else if let Ok(octave) = rest.parse() {
        octave
    } else {
        return unknown_pitch(text);
    };
    pitch_from_number(12 * (octave + 1) + semitone + accidental)
}

fn unknown_pitch<T>(text: &str) -> Result<T, MelodyError> {
    error(format!(
        "unrecognized pitch {text:?}: use a note name such as 'C4' or 'F#3', or a MIDI number from 0 to 127"
    ))
}

/// Check that `number` is a MIDI pitch.
pub fn pitch_from_number(number: i64) -> Result<u8, MelodyError> {
    u8::try_from(number)
        .ok()
        .filter(|pitch| *pitch <= MAXIMUM_PITCH)
        .map_or_else(
            || {
                error(format!(
                    "pitch must be a MIDI number from 0 to {MAXIMUM_PITCH}, got {number}; \
                     transpose by fewer semitones or choose another octave"
                ))
            },
            Ok,
        )
}

/// The sharp-spelled name of a MIDI pitch, such as `C#4`.
pub fn pitch_name(pitch: u8) -> String {
    let octave = i32::from(pitch / 12) - 1;
    format!("{}{octave}", NAMES[usize::from(pitch % 12)])
}

/// Check a velocity between `0.0` and `1.0`.
pub fn check_velocity(velocity: f32) -> Result<f32, MelodyError> {
    if (0.0..=1.0).contains(&velocity) {
        Ok(velocity)
    } else {
        error(format!(
            "velocity must be between 0.0 and 1.0, got {velocity}"
        ))
    }
}

/// Check a tempo in beats per minute.
pub fn check_beats_per_minute(beats_per_minute: f64) -> Result<f64, MelodyError> {
    if (MINIMUM_BEATS_PER_MINUTE..=MAXIMUM_BEATS_PER_MINUTE).contains(&beats_per_minute) {
        Ok(beats_per_minute)
    } else {
        error(format!(
            "beats_per_minute must be between {MINIMUM_BEATS_PER_MINUTE} and \
             {MAXIMUM_BEATS_PER_MINUTE}, got {beats_per_minute}"
        ))
    }
}

/// One note on a beat timeline.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Note {
    /// MIDI pitch from 0 to 127.
    pub pitch: u8,
    /// Strength from `0.0` to `1.0`.
    pub velocity: f32,
    /// Where the note starts, in beats from the start of the melody.
    pub start_beats: f64,
    /// How long the key is held, in beats.
    pub duration_beats: f64,
}

impl Note {
    /// Build a note, checking every value.
    pub fn new(
        pitch: u8,
        velocity: f32,
        start_beats: f64,
        duration_beats: f64,
    ) -> Result<Self, MelodyError> {
        pitch_from_number(i64::from(pitch))?;
        check_velocity(velocity)?;
        if finite("start_beats", start_beats)? < 0.0 {
            return error(format!(
                "start_beats must be zero or more, got {start_beats}"
            ));
        }
        if finite("duration_beats", duration_beats)? <= 0.0 {
            return error(format!(
                "duration_beats must be greater than zero, got {duration_beats}; \
                 use a rest to leave silence"
            ));
        }
        Ok(Self {
            pitch,
            velocity,
            start_beats,
            duration_beats,
        })
    }

    /// Where the note ends, in beats.
    pub fn end_beats(&self) -> f64 {
        self.start_beats + self.duration_beats
    }

    /// Frequency of the pitch in hertz.
    pub fn frequency_hertz(&self) -> f32 {
        midi_to_hz(f32::from(self.pitch))
    }

    /// The note moved by `semitones`.
    pub fn transposed(&self, semitones: i32) -> Result<Self, MelodyError> {
        let pitch = pitch_from_number(i64::from(self.pitch) + i64::from(semitones))?;
        Ok(Self { pitch, ..*self })
    }
}

/// How many beats make a bar.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct TimeSignature {
    /// Beat units per bar, 1 to 64.
    pub numerator: u8,
    /// The note value of one beat unit: 1, 2, 4, 8, 16 or 32.
    pub denominator: u8,
}

impl Default for TimeSignature {
    fn default() -> Self {
        Self {
            numerator: 4,
            denominator: 4,
        }
    }
}

impl TimeSignature {
    /// Build a time signature, checking the numerator and denominator.
    pub fn new(numerator: u8, denominator: u8) -> Result<Self, MelodyError> {
        if !(1..=64).contains(&numerator) {
            return error(format!(
                "numerator must be between 1 and 64, got {numerator}"
            ));
        }
        if ![1, 2, 4, 8, 16, 32].contains(&denominator) {
            return error(format!(
                "denominator must be 1, 2, 4, 8, 16 or 32, got {denominator}"
            ));
        }
        Ok(Self {
            numerator,
            denominator,
        })
    }

    /// Length of one bar in quarter-note beats, the unit melodies are measured in.
    pub fn bar_length_beats(&self) -> f64 {
        f64::from(self.numerator) * 4.0 / f64::from(self.denominator)
    }

    /// The zero-based bar and the beat inside that bar that `beats` falls on.
    pub fn bar_and_beat(&self, beats: f64) -> (u64, f64) {
        let length = self.bar_length_beats();
        let bar = (beats / length + EPSILON).floor().max(0.0);
        (bar as u64, (beats - bar * length).max(0.0))
    }
}

/// Maps beats to seconds. The tempo is constant between changes.
#[derive(Debug, Clone, PartialEq)]
pub struct TempoMap {
    initial_beats_per_minute: f64,
    /// `(beat, beats_per_minute)` pairs with strictly increasing beats above zero.
    changes: Vec<(f64, f64)>,
}

impl Default for TempoMap {
    fn default() -> Self {
        Self {
            initial_beats_per_minute: 120.0,
            changes: Vec::new(),
        }
    }
}

impl TempoMap {
    /// A constant tempo.
    pub fn new(beats_per_minute: f64) -> Result<Self, MelodyError> {
        Ok(Self {
            initial_beats_per_minute: check_beats_per_minute(beats_per_minute)?,
            changes: Vec::new(),
        })
    }

    /// The tempo before any change.
    pub fn initial_beats_per_minute(&self) -> f64 {
        self.initial_beats_per_minute
    }

    /// The tempo changes in beat order.
    pub fn changes(&self) -> &[(f64, f64)] {
        &self.changes
    }

    /// The map with a change to `beats_per_minute` at `beat`; a change at the same beat is replaced.
    ///
    /// A change at beat `0` replaces the initial tempo.
    pub fn with_change(&self, beat: f64, beats_per_minute: f64) -> Result<Self, MelodyError> {
        check_beats_per_minute(beats_per_minute)?;
        if finite("beat", beat)? < 0.0 {
            return error(format!("beat must be zero or more, got {beat}"));
        }
        let mut map = self.clone();
        if beat <= EPSILON {
            map.initial_beats_per_minute = beats_per_minute;
            return Ok(map);
        }
        match map
            .changes
            .iter()
            .position(|(existing, _)| (existing - beat).abs() <= EPSILON)
        {
            Some(index) => map.changes[index].1 = beats_per_minute,
            None => {
                if map.changes.len() >= MAXIMUM_TEMPO_CHANGES {
                    return error(format!(
                        "a tempo map holds at most {MAXIMUM_TEMPO_CHANGES} changes"
                    ));
                }
                map.changes.push((beat, beats_per_minute));
                map.changes
                    .sort_by(|left, right| left.0.total_cmp(&right.0));
            }
        }
        Ok(map)
    }

    /// The tempo in effect at `beat`.
    pub fn beats_per_minute_at(&self, beat: f64) -> f64 {
        self.changes
            .iter()
            .take_while(|(start, _)| *start <= beat + EPSILON)
            .last()
            .map_or(self.initial_beats_per_minute, |(_, tempo)| *tempo)
    }

    /// Seconds from beat zero to `beat`.
    pub fn beats_to_seconds(&self, beat: f64) -> f64 {
        let mut seconds = 0.0;
        let mut position = 0.0;
        let mut tempo = self.initial_beats_per_minute;
        for &(start, next) in &self.changes {
            if start >= beat {
                break;
            }
            seconds += (start - position) * 60.0 / tempo;
            position = start;
            tempo = next;
        }
        seconds + (beat - position) * 60.0 / tempo
    }

    /// The beat reached after `seconds`.
    pub fn seconds_to_beats(&self, seconds: f64) -> f64 {
        let mut elapsed = 0.0;
        let mut position = 0.0;
        let mut tempo = self.initial_beats_per_minute;
        for &(start, next) in &self.changes {
            let segment = (start - position) * 60.0 / tempo;
            if elapsed + segment >= seconds {
                break;
            }
            elapsed += segment;
            position = start;
            tempo = next;
        }
        position + (seconds - elapsed) * tempo / 60.0
    }

    /// The map with every tempo multiplied by `factor` (`2.0` plays twice as fast).
    pub fn scaled(&self, factor: f64) -> Result<Self, MelodyError> {
        if finite("factor", factor)? <= 0.0 {
            return error(format!("factor must be greater than zero, got {factor}"));
        }
        let mut map = Self::new(check_beats_per_minute(
            self.initial_beats_per_minute * factor,
        )?)?;
        for &(beat, tempo) in &self.changes {
            map = map.with_change(beat, tempo * factor)?;
        }
        Ok(map)
    }
}

/// A note placed on an external clock.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ScheduledNote {
    /// The note, in melody beats.
    pub note: Note,
    /// When the note starts, in seconds on the external clock.
    pub start_seconds: f64,
    /// How long the key is held, in seconds.
    pub duration_seconds: f64,
    /// How many times the melody has looped before this note, starting at zero.
    pub iteration: u64,
}

/// Notes on a beat timeline with a tempo map and a time signature.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct Melody {
    notes: Vec<Note>,
    tempo_map: TempoMap,
    time_signature: TimeSignature,
    minimum_length_beats: f64,
}

impl Melody {
    /// A melody of `notes`, kept in start order.
    pub fn new(
        notes: Vec<Note>,
        tempo_map: TempoMap,
        time_signature: TimeSignature,
        minimum_length_beats: f64,
    ) -> Result<Self, MelodyError> {
        if notes.len() > MAXIMUM_NOTES {
            return error(format!(
                "a melody holds at most {MAXIMUM_NOTES} notes, got {}",
                notes.len()
            ));
        }
        if finite("length_beats", minimum_length_beats)? < 0.0 {
            return error(format!(
                "length_beats must be zero or more, got {minimum_length_beats}"
            ));
        }
        let mut notes = notes;
        notes.sort_by(|left, right| left.start_beats.total_cmp(&right.start_beats));
        Ok(Self {
            notes,
            tempo_map,
            time_signature,
            minimum_length_beats,
        })
    }

    /// The notes in start order.
    pub fn notes(&self) -> &[Note] {
        &self.notes
    }

    /// The tempo map.
    pub fn tempo_map(&self) -> &TempoMap {
        &self.tempo_map
    }

    /// The time signature.
    pub fn time_signature(&self) -> TimeSignature {
        self.time_signature
    }

    /// The end of the last note, or the explicit length when that is longer, in beats.
    pub fn length_beats(&self) -> f64 {
        self.notes
            .iter()
            .map(Note::end_beats)
            .fold(self.minimum_length_beats, f64::max)
    }

    /// The melody's length in seconds.
    pub fn duration_seconds(&self) -> f64 {
        self.tempo_map.beats_to_seconds(self.length_beats())
    }

    /// The same melody with a different tempo map.
    pub fn with_tempo_map(&self, tempo_map: TempoMap) -> Self {
        Self {
            tempo_map,
            ..self.clone()
        }
    }

    /// The same melody with a different time signature.
    pub fn with_time_signature(&self, time_signature: TimeSignature) -> Self {
        Self {
            time_signature,
            ..self.clone()
        }
    }

    /// The same melody with a length of at least `length_beats`, which adds trailing silence.
    pub fn with_length_beats(&self, length_beats: f64) -> Result<Self, MelodyError> {
        Self::new(
            self.notes.clone(),
            self.tempo_map.clone(),
            self.time_signature,
            length_beats,
        )
    }

    /// The melody with `added` notes included.
    pub fn with_notes(&self, added: &[Note]) -> Result<Self, MelodyError> {
        let mut notes = self.notes.clone();
        notes.extend_from_slice(added);
        Self::new(
            notes,
            self.tempo_map.clone(),
            self.time_signature,
            self.minimum_length_beats,
        )
    }

    /// The melody with a chord of `pitches` appended at its current end.
    ///
    /// All pitches start together; the end moves by `duration_beats`.
    pub fn appended_chord(
        &self,
        pitches: &[u8],
        duration_beats: f64,
        velocity: f32,
    ) -> Result<Self, MelodyError> {
        let start = self.length_beats();
        let added = pitches
            .iter()
            .map(|pitch| Note::new(*pitch, velocity, start, duration_beats))
            .collect::<Result<Vec<_>, _>>()?;
        let mut melody = self.with_notes(&added)?;
        melody.minimum_length_beats = start + duration_beats;
        Ok(melody)
    }

    /// The melody with silence of `duration_beats` appended at its end.
    pub fn appended_rest(&self, duration_beats: f64) -> Result<Self, MelodyError> {
        if finite("duration_beats", duration_beats)? <= 0.0 {
            return error(format!(
                "duration_beats must be greater than zero, got {duration_beats}"
            ));
        }
        self.with_length_beats(self.length_beats() + duration_beats)
    }

    /// The melody with every pitch moved by `semitones`.
    pub fn transposed(&self, semitones: i32) -> Result<Self, MelodyError> {
        let notes = self
            .notes
            .iter()
            .map(|note| note.transposed(semitones))
            .collect::<Result<Vec<_>, _>>()?;
        Self::new(
            notes,
            self.tempo_map.clone(),
            self.time_signature,
            self.minimum_length_beats,
        )
    }

    /// The melody moved later by `beats` (earlier when negative).
    pub fn shifted(&self, beats: f64) -> Result<Self, MelodyError> {
        finite("beats", beats)?;
        let mut notes = Vec::with_capacity(self.notes.len());
        for note in &self.notes {
            notes.push(Note::new(
                note.pitch,
                note.velocity,
                note.start_beats + beats,
                note.duration_beats,
            )?);
        }
        Self::new(
            notes,
            self.tempo_map.clone(),
            self.time_signature,
            (self.minimum_length_beats + beats).max(0.0),
        )
    }

    /// The melody with every start, duration and tempo change stretched in beats by `factor`.
    ///
    /// The tempo map is left alone, so `2.0` makes the melody twice as long in time.
    pub fn stretched(&self, factor: f64) -> Result<Self, MelodyError> {
        if finite("factor", factor)? <= 0.0 {
            return error(format!("factor must be greater than zero, got {factor}"));
        }
        let notes = self
            .notes
            .iter()
            .map(|note| {
                Note::new(
                    note.pitch,
                    note.velocity,
                    note.start_beats * factor,
                    note.duration_beats * factor,
                )
            })
            .collect::<Result<Vec<_>, _>>()?;
        let mut tempo_map = TempoMap::new(self.tempo_map.initial_beats_per_minute)?;
        for &(beat, tempo) in self.tempo_map.changes() {
            tempo_map = tempo_map.with_change(beat * factor, tempo)?;
        }
        Self::new(
            notes,
            tempo_map,
            self.time_signature,
            self.minimum_length_beats * factor,
        )
    }

    /// The melody played `count` times in a row.
    pub fn repeated(&self, count: usize) -> Result<Self, MelodyError> {
        if count == 0 || count.saturating_mul(self.notes.len()) > MAXIMUM_NOTES {
            return error(format!(
                "count must be at least 1 and the repeated melody can hold at most \
                 {MAXIMUM_NOTES} notes, got count {count} for {} notes",
                self.notes.len()
            ));
        }
        let length = self.length_beats();
        let mut notes = Vec::with_capacity(self.notes.len() * count);
        for iteration in 0..count {
            for note in &self.notes {
                notes.push(Note {
                    start_beats: note.start_beats + length * iteration as f64,
                    ..*note
                });
            }
        }
        Self::new(
            notes,
            self.tempo_map.clone(),
            self.time_signature,
            length * count as f64,
        )
    }

    /// The melody followed by `other`, which keeps this melody's tempo map and time signature.
    pub fn followed_by(&self, other: &Self) -> Result<Self, MelodyError> {
        let offset = self.length_beats();
        let mut notes = self.notes.clone();
        notes.extend(other.notes.iter().map(|note| Note {
            start_beats: note.start_beats + offset,
            ..*note
        }));
        Self::new(
            notes,
            self.tempo_map.clone(),
            self.time_signature,
            offset + other.length_beats(),
        )
    }

    /// The notes of both melodies played together, using this melody's tempo map.
    pub fn layered_with(&self, other: &Self) -> Result<Self, MelodyError> {
        let mut notes = self.notes.clone();
        notes.extend_from_slice(&other.notes);
        Self::new(
            notes,
            self.tempo_map.clone(),
            self.time_signature,
            self.minimum_length_beats.max(other.minimum_length_beats),
        )
    }

    /// The notes that start in `[from_beats, to_beats)`.
    pub fn notes_between_beats(&self, from_beats: f64, to_beats: f64) -> &[Note] {
        let first = self
            .notes
            .partition_point(|note| note.start_beats < from_beats - EPSILON);
        let last = self
            .notes
            .partition_point(|note| note.start_beats < to_beats - EPSILON);
        &self.notes[first..last.max(first)]
    }

    /// The notes that start in `[from_seconds, to_seconds)` of melody time.
    pub fn notes_between_seconds(&self, from_seconds: f64, to_seconds: f64) -> &[Note] {
        self.notes_between_beats(
            self.tempo_map.seconds_to_beats(from_seconds),
            self.tempo_map.seconds_to_beats(to_seconds),
        )
    }

    /// The notes due on an external clock between two readings.
    ///
    /// The melody begins when the external clock reads `start_seconds`. Notes that start in
    /// `[from_elapsed_seconds, to_elapsed_seconds)` are returned with their start measured in
    /// seconds on that same clock. With `should_loop` the melody restarts every time it
    /// reaches its length. Windows that follow each other never repeat or skip a note.
    pub fn scheduled_between(
        &self,
        from_elapsed_seconds: f64,
        to_elapsed_seconds: f64,
        start_seconds: f64,
        should_loop: bool,
    ) -> Result<Vec<ScheduledNote>, MelodyError> {
        finite("from_elapsed_seconds", from_elapsed_seconds)?;
        finite("to_elapsed_seconds", to_elapsed_seconds)?;
        finite("start_seconds", start_seconds)?;
        if to_elapsed_seconds < from_elapsed_seconds {
            return error(format!(
                "to_elapsed_seconds ({to_elapsed_seconds}) must not be earlier than \
                 from_elapsed_seconds ({from_elapsed_seconds})"
            ));
        }
        let from = (from_elapsed_seconds - start_seconds).max(0.0);
        let to = to_elapsed_seconds - start_seconds;
        let mut scheduled = Vec::new();
        if to <= 0.0 || self.notes.is_empty() {
            return Ok(scheduled);
        }
        let period = self.duration_seconds();
        let (first_iteration, last_iteration) = if should_loop && period > 0.0 {
            ((from / period).floor() as u64, (to / period).ceil() as u64)
        } else {
            (0, 0)
        };
        for iteration in first_iteration..=last_iteration {
            let offset = period * iteration as f64;
            for note in self.notes_between_seconds(from - offset, to - offset) {
                let start = offset + self.tempo_map.beats_to_seconds(note.start_beats);
                if start < from - EPSILON || start >= to - EPSILON {
                    continue;
                }
                scheduled.push(ScheduledNote {
                    note: *note,
                    start_seconds: start_seconds + start,
                    duration_seconds: self.tempo_map.beats_to_seconds(note.end_beats())
                        - self.tempo_map.beats_to_seconds(note.start_beats),
                    iteration,
                });
            }
        }
        Ok(scheduled)
    }

    /// Render the notes that start in `[from_seconds, to_seconds)` of melody time to mono samples.
    ///
    /// The first sample is the instant `from_seconds`. `to_seconds` of `None` means the end of
    /// the melody. Notes ring past the window with their natural tail, so the result can be
    /// longer than the window. Overlapping notes add up and the result is limited to stay
    /// below clipping.
    pub fn render(
        &self,
        instrument: &str,
        sample_rate: u32,
        from_seconds: f64,
        to_seconds: Option<f64>,
    ) -> Result<Vec<f32>, MelodyError> {
        let definition = find(instrument).ok_or_else(|| {
            MelodyError(format!(
                "unknown instrument {instrument:?}; call instrument_names() for the choices"
            ))
        })?;
        if !(8_000..=192_000).contains(&sample_rate) {
            return error(format!(
                "sample_rate must be between 8000 and 192000, got {sample_rate}"
            ));
        }
        let from = finite("from_seconds", from_seconds)?.max(0.0);
        let to = to_seconds.map_or(Ok(self.duration_seconds()), |to| finite("to_seconds", to))?;
        if to - from > MAXIMUM_RENDER_SECONDS {
            return error(format!(
                "a render covers at most {MAXIMUM_RENDER_SECONDS} seconds, got {}; \
                 render shorter windows",
                to - from
            ));
        }
        let rate = f64::from(sample_rate);
        let mut output: Vec<f32> = Vec::new();
        for note in self.notes_between_seconds(from, to) {
            let start = self.tempo_map.beats_to_seconds(note.start_beats) - from;
            let gate = self.tempo_map.beats_to_seconds(note.end_beats())
                - self.tempo_map.beats_to_seconds(note.start_beats);
            let samples = definition.render(&InstrumentNote {
                freq: note.frequency_hertz(),
                gate: gate as f32,
                velocity: note.velocity,
                sample_rate: sample_rate as f32,
            });
            let offset = (start * rate).round().max(0.0) as usize;
            if output.len() < offset + samples.len() {
                output.resize(offset + samples.len(), 0.0);
            }
            for (slot, sample) in output[offset..].iter_mut().zip(&samples) {
                *slot += sample;
            }
        }
        let window = ((to - from) * rate).ceil().max(0.0) as usize;
        if output.len() < window {
            output.resize(window, 0.0);
        }
        crate::dsp::limit(&mut output, CEILING);
        Ok(output)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn note(pitch: u8, start: f64, duration: f64) -> Note {
        Note::new(pitch, 0.8, start, duration).unwrap()
    }

    fn scale() -> Melody {
        Melody::new(
            (0..4)
                .map(|index| note(60 + index, f64::from(index), 1.0))
                .collect(),
            TempoMap::new(120.0).unwrap(),
            TimeSignature::default(),
            0.0,
        )
        .unwrap()
    }

    #[test]
    fn pitches_parse_and_print() {
        assert_eq!(parse_pitch("C4").unwrap(), 60);
        assert_eq!(parse_pitch("c#3").unwrap(), 49);
        assert_eq!(parse_pitch("Db5").unwrap(), 73);
        assert_eq!(parse_pitch("A").unwrap(), 69);
        assert_eq!(parse_pitch("72").unwrap(), 72);
        assert_eq!(pitch_name(61), "C#4");
        assert!(parse_pitch("H4").is_err());
        assert!(parse_pitch("200").is_err());
        assert!(parse_pitch("C#10").is_err());
    }

    #[test]
    fn tempo_maps_convert_both_ways() {
        let map = TempoMap::new(120.0)
            .unwrap()
            .with_change(4.0, 60.0)
            .unwrap();
        assert!((map.beats_to_seconds(4.0) - 2.0).abs() < 1e-9);
        assert!((map.beats_to_seconds(6.0) - 4.0).abs() < 1e-9);
        assert!((map.seconds_to_beats(4.0) - 6.0).abs() < 1e-9);
        assert!((map.seconds_to_beats(1.0) - 2.0).abs() < 1e-9);
        assert_eq!(map.beats_per_minute_at(3.9), 120.0);
        assert_eq!(map.beats_per_minute_at(4.0), 60.0);
    }

    #[test]
    fn windows_never_repeat_or_skip_notes() {
        let melody = scale();
        let mut heard = Vec::new();
        for step in 0..8 {
            let from = f64::from(step) * 0.3;
            for item in melody
                .scheduled_between(from, from + 0.3, 0.0, false)
                .unwrap()
            {
                heard.push(item.note.pitch);
            }
        }
        assert_eq!(heard, vec![60, 61, 62, 63]);
    }

    #[test]
    fn looping_wraps_after_the_length() {
        let melody = scale();
        let items = melody.scheduled_between(1.9, 2.6, 0.0, true).unwrap();
        let starts: Vec<(u8, u64)> = items
            .iter()
            .map(|item| (item.note.pitch, item.iteration))
            .collect();
        assert_eq!(starts, vec![(60, 1), (61, 1)]);
        assert!((items[0].start_seconds - 2.0).abs() < 1e-9);
    }

    #[test]
    fn start_offset_shifts_the_clock() {
        let items = scale().scheduled_between(10.0, 11.0, 10.0, false).unwrap();
        assert_eq!(items.len(), 2);
        assert!((items[1].start_seconds - 10.5).abs() < 1e-9);
    }

    #[test]
    fn chords_rests_and_transforms() {
        let melody = Melody::default()
            .appended_chord(&[60, 64, 67], 2.0, 0.7)
            .unwrap()
            .appended_rest(1.0)
            .unwrap();
        assert_eq!(melody.notes().len(), 3);
        assert_eq!(melody.length_beats(), 3.0);
        assert_eq!(melody.transposed(12).unwrap().notes()[0].pitch, 72);
        assert!(melody.transposed(100).is_err());
        assert_eq!(melody.repeated(2).unwrap().length_beats(), 6.0);
        assert_eq!(melody.stretched(0.5).unwrap().length_beats(), 1.5);
        assert_eq!(melody.shifted(1.0).unwrap().notes()[0].start_beats, 1.0);
        assert!(melody.shifted(-1.0).is_err());
    }

    #[test]
    fn rendering_places_notes_at_their_start() {
        let melody = Melody::new(
            vec![note(69, 1.0, 0.5)],
            TempoMap::new(120.0).unwrap(),
            TimeSignature::default(),
            0.0,
        )
        .unwrap();
        let samples = melody.render("sine", 8_000, 0.0, None).unwrap();
        assert!(samples[..4_000].iter().all(|sample| *sample == 0.0));
        assert!(samples[4_000..].iter().any(|sample| sample.abs() > 0.01));
        assert!(samples.iter().all(|sample| sample.abs() <= CEILING + 1e-6));
    }

    #[test]
    fn time_signatures_count_bars() {
        let waltz = TimeSignature::new(3, 4).unwrap();
        assert_eq!(waltz.bar_length_beats(), 3.0);
        assert_eq!(waltz.bar_and_beat(7.5), (2, 1.5));
        assert_eq!(TimeSignature::new(6, 8).unwrap().bar_length_beats(), 3.0);
        assert!(TimeSignature::new(4, 3).is_err());
    }
}
