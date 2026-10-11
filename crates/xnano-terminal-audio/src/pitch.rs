//! Note names, MIDI numbers and frequencies.

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyFloat, PyInt, PyString};

/// Frequency of a MIDI note number (A4 = 69 = 440 Hz).
pub fn midi_to_hz(midi: f32) -> f32 {
    440.0 * ((midi - 69.0) / 12.0).exp2()
}

/// Parse a note name such as `C4`, `c#3`, `Db5` or `A` (octave defaults to 4)
/// into a MIDI note number. `C4` is 60.
fn parse_note_name(text: &str) -> Option<i32> {
    let mut chars = text.trim().chars().peekable();
    let semitone = match chars.next()?.to_ascii_uppercase() {
        'C' => 0,
        'D' => 2,
        'E' => 4,
        'F' => 5,
        'G' => 7,
        'A' => 9,
        'B' => 11,
        _ => return None,
    };
    let mut accidental = 0;
    while let Some(&c) = chars.peek() {
        match c {
            '#' | '♯' => accidental += 1,
            'b' | '♭' => accidental -= 1,
            _ => break,
        }
        chars.next();
    }
    let rest: String = chars.collect();
    let octave: i32 = if rest.is_empty() {
        4
    } else {
        rest.parse().ok()?
    };
    if !(-1..=9).contains(&octave) {
        return None;
    }
    Some(12 * (octave + 1) + semitone + accidental)
}

fn midi_pitch_to_hz(midi: i32) -> PyResult<f32> {
    if !(0..=127).contains(&midi) {
        return Err(PyValueError::new_err(format!(
            "MIDI pitch {midi} is outside the supported range (0 to 127)"
        )));
    }
    Ok(midi_to_hz(midi as f32))
}

/// Turn a Python note (`"C#4"`, MIDI `int`, or `float` hertz) into hertz.
///
/// Strings may also be plain numbers (`"69"`, MIDI) or end in `hz` (`"440hz"`).
pub fn note_to_hz(note: &Bound<'_, PyAny>) -> PyResult<f32> {
    let hz = if note.is_instance_of::<PyBool>() {
        return Err(PyTypeError::new_err(
            "note must be a name, MIDI int, or hertz float",
        ));
    } else if note.is_instance_of::<PyInt>() {
        midi_pitch_to_hz(note.extract::<i32>()?)?
    } else if note.is_instance_of::<PyFloat>() {
        note.extract::<f32>()?
    } else if note.is_instance_of::<PyString>() {
        let text: String = note.extract()?;
        let lowered = text.trim().to_lowercase();
        if let Some(number) = lowered.strip_suffix("hz") {
            number.trim().parse::<f32>().map_err(|_| bad_note(&text))?
        } else if let Ok(midi) = lowered.parse::<i32>() {
            midi_pitch_to_hz(midi)?
        } else {
            midi_pitch_to_hz(parse_note_name(&text).ok_or_else(|| bad_note(&text))?)?
        }
    } else {
        return Err(PyTypeError::new_err(
            "note must be a name, MIDI int, or hertz float",
        ));
    };
    if !(8.0..=20_000.0).contains(&hz) {
        return Err(PyValueError::new_err(format!(
            "note frequency {hz:.1} Hz is outside the supported range (8 Hz to 20 kHz)"
        )));
    }
    Ok(hz)
}

fn bad_note(text: &str) -> PyErr {
    PyValueError::new_err(format!(
        "unrecognized note {text:?}: use a name like 'C4' or 'F#3', a MIDI number, or '440hz'"
    ))
}
