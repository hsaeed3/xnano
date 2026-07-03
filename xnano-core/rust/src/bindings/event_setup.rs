use crossterm::event::{
    DisableBracketedPaste, DisableFocusChange, DisableMouseCapture, EnableBracketedPaste,
    EnableFocusChange, EnableMouseCapture, KeyboardEnhancementFlags, PopKeyboardEnhancementFlags,
    PushKeyboardEnhancementFlags,
};
use pyo3::prelude::*;

use super::crossterm_exec::execute_stdout;

#[pyclass(name = "KeyboardEnhancementFlags", module = "xnano_core._xnano_core")]
#[derive(Clone, Copy)]
pub struct PyKeyboardEnhancementFlags {
    #[pyo3(get)]
    pub bits: u8,
}

#[pymethods]
impl PyKeyboardEnhancementFlags {
    #[classattr]
    const DISAMBIGUATE_ESCAPE_CODES: Self = Self {
        bits: KeyboardEnhancementFlags::DISAMBIGUATE_ESCAPE_CODES.bits(),
    };

    #[classattr]
    const REPORT_EVENT_TYPES: Self = Self {
        bits: KeyboardEnhancementFlags::REPORT_EVENT_TYPES.bits(),
    };

    #[classattr]
    const REPORT_ALTERNATE_KEYS: Self = Self {
        bits: KeyboardEnhancementFlags::REPORT_ALTERNATE_KEYS.bits(),
    };

    #[classattr]
    const REPORT_ALL_KEYS_AS_ESCAPE_CODES: Self = Self {
        bits: KeyboardEnhancementFlags::REPORT_ALL_KEYS_AS_ESCAPE_CODES.bits(),
    };

    fn __or__(&self, other: Self) -> Self {
        Self {
            bits: self.bits | other.bits,
        }
    }

    fn __repr__(&self) -> String {
        format!("KeyboardEnhancementFlags(bits={})", self.bits)
    }
}

impl From<PyKeyboardEnhancementFlags> for KeyboardEnhancementFlags {
    fn from(value: PyKeyboardEnhancementFlags) -> Self {
        KeyboardEnhancementFlags::from_bits_truncate(value.bits)
    }
}

#[pyfunction]
fn enable_mouse_capture() -> PyResult<()> {
    execute_stdout(EnableMouseCapture)
}

#[pyfunction]
fn disable_mouse_capture() -> PyResult<()> {
    execute_stdout(DisableMouseCapture)
}

#[pyfunction]
fn enable_bracketed_paste() -> PyResult<()> {
    execute_stdout(EnableBracketedPaste)
}

#[pyfunction]
fn disable_bracketed_paste() -> PyResult<()> {
    execute_stdout(DisableBracketedPaste)
}

#[pyfunction]
fn enable_focus_change() -> PyResult<()> {
    execute_stdout(EnableFocusChange)
}

#[pyfunction]
fn disable_focus_change() -> PyResult<()> {
    execute_stdout(DisableFocusChange)
}

#[pyfunction]
fn push_keyboard_enhancement_flags(flags: PyKeyboardEnhancementFlags) -> PyResult<()> {
    execute_stdout(PushKeyboardEnhancementFlags(flags.into()))
}

#[pyfunction]
fn pop_keyboard_enhancement_flags() -> PyResult<()> {
    execute_stdout(PopKeyboardEnhancementFlags)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyKeyboardEnhancementFlags>()?;
    m.add_function(wrap_pyfunction!(enable_mouse_capture, m)?)?;
    m.add_function(wrap_pyfunction!(disable_mouse_capture, m)?)?;
    m.add_function(wrap_pyfunction!(enable_bracketed_paste, m)?)?;
    m.add_function(wrap_pyfunction!(disable_bracketed_paste, m)?)?;
    m.add_function(wrap_pyfunction!(enable_focus_change, m)?)?;
    m.add_function(wrap_pyfunction!(disable_focus_change, m)?)?;
    m.add_function(wrap_pyfunction!(push_keyboard_enhancement_flags, m)?)?;
    m.add_function(wrap_pyfunction!(pop_keyboard_enhancement_flags, m)?)?;
    Ok(())
}