#[cfg(feature = "terminal")]
use crossterm::event::{KeyCode, KeyModifiers};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

#[cfg(not(feature = "terminal"))]
use super::super::crossterm_types::{KeyCode, KeyModifiers};

use super::super::terminal::PyKeyEvent;

/// Parsed form of an xnano keyboard binding string such as `"ctrl+q"`.
/// Matching is done entirely in Rust — no Python string manipulation needed.
#[pyclass(name = "CoreKeyBinding", module = "xnano_core.rust.engine", from_py_object)]
#[derive(Clone, Debug)]
pub struct CoreKeyBinding {
    ctrl: bool,
    shift: bool,
    alt: bool,
    code: KeyCode,
}

impl CoreKeyBinding {
    fn from_str_inner(binding: &str) -> PyResult<Self> {
        let parts: Vec<&str> = binding.split('+').map(str::trim).collect();
        if parts.is_empty() {
            return Err(PyValueError::new_err(format!("empty binding: {binding:?}")));
        }

        let mut ctrl = false;
        let mut shift = false;
        let mut alt = false;
        let key_part = parts[parts.len() - 1].to_lowercase();

        for modifier in &parts[..parts.len() - 1] {
            match modifier.to_lowercase().as_str() {
                "ctrl" | "control" => ctrl = true,
                "shift" | "shft" => shift = true,
                "alt" => alt = true,
                other => {
                    return Err(PyValueError::new_err(format!(
                        "unknown modifier {other:?} in binding {binding:?}"
                    )))
                }
            }
        }

        let code = Self::parse_key_part(&key_part, binding)?;
        Ok(Self { ctrl, shift, alt, code })
    }

    fn parse_key_part(key_part: &str, binding: &str) -> PyResult<KeyCode> {
        match key_part {
            "enter" => Ok(KeyCode::Enter),
            "esc" | "escape" => Ok(KeyCode::Esc),
            "backspace" => Ok(KeyCode::Backspace),
            "tab" => Ok(KeyCode::Tab),
            "backtab" => Ok(KeyCode::BackTab),
            "up" => Ok(KeyCode::Up),
            "down" => Ok(KeyCode::Down),
            "left" => Ok(KeyCode::Left),
            "right" => Ok(KeyCode::Right),
            "home" => Ok(KeyCode::Home),
            "end" => Ok(KeyCode::End),
            "pageup" | "page_up" => Ok(KeyCode::PageUp),
            "pagedown" | "page_down" => Ok(KeyCode::PageDown),
            "insert" => Ok(KeyCode::Insert),
            "delete" | "del" => Ok(KeyCode::Delete),
            "space" => Ok(KeyCode::Char(' ')),
            "null" => Ok(KeyCode::Null),
            "capslock" => Ok(KeyCode::CapsLock),
            "scrolllock" => Ok(KeyCode::ScrollLock),
            "numlock" => Ok(KeyCode::NumLock),
            "printscreen" => Ok(KeyCode::PrintScreen),
            "pause" => Ok(KeyCode::Pause),
            "menu" => Ok(KeyCode::Menu),
            "keypadbegin" => Ok(KeyCode::KeypadBegin),
            key if key.starts_with('f') && key.len() <= 3 => {
                if let Ok(n) = key[1..].parse::<u8>() {
                    if (1..=12).contains(&n) {
                        return Ok(KeyCode::F(n));
                    }
                }
                Err(PyValueError::new_err(format!("invalid function key: {key:?}")))
            }
            key if key.len() == 1 => Ok(KeyCode::Char(key.chars().next().unwrap())),
            _ => Err(PyValueError::new_err(format!(
                "unknown key in binding: {key_part:?} (binding: {binding:?})"
            ))),
        }
    }

    fn matches_event(&self, event: &PyKeyEvent) -> bool {
        let code_matches = match self.code {
            KeyCode::Char(expected) => {
                if let Some(ch) = event.char_value() {
                    ch.to_lowercase().next() == expected.to_lowercase().next()
                } else {
                    false
                }
            }
            KeyCode::F(n) => event.function_number() == Some(n),
            ref other => other == event.raw_code(),
        };
        if !code_matches {
            return false;
        }

        let mods = event.raw_modifiers();
        let has_ctrl = mods.contains(KeyModifiers::CONTROL);
        let has_shift = mods.contains(KeyModifiers::SHIFT);
        let has_alt = mods.contains(KeyModifiers::ALT);

        self.ctrl == has_ctrl && self.shift == has_shift && self.alt == has_alt
    }
}

#[pymethods]
impl CoreKeyBinding {
    /// Parse a binding string like `"ctrl+q"` or `"shift+up"`.
    #[staticmethod]
    fn parse(binding: &str) -> PyResult<Self> {
        Self::from_str_inner(binding)
    }

    /// Return `True` if this binding matches the given native `KeyEvent`.
    fn matches(&self, event: &PyKeyEvent) -> bool {
        self.matches_event(event)
    }

    fn __repr__(&self) -> String {
        let mut parts: Vec<String> = Vec::new();
        if self.ctrl { parts.push("ctrl".into()); }
        if self.shift { parts.push("shift".into()); }
        if self.alt { parts.push("alt".into()); }
        let key = match &self.code {
            KeyCode::Char(c) if *c == ' ' => "space".to_string(),
            KeyCode::Char(c) => c.to_string(),
            KeyCode::Enter => "enter".to_string(),
            KeyCode::Esc => "esc".to_string(),
            KeyCode::Backspace => "backspace".to_string(),
            KeyCode::Tab => "tab".to_string(),
            KeyCode::BackTab => "backtab".to_string(),
            KeyCode::Up => "up".to_string(),
            KeyCode::Down => "down".to_string(),
            KeyCode::Left => "left".to_string(),
            KeyCode::Right => "right".to_string(),
            KeyCode::Home => "home".to_string(),
            KeyCode::End => "end".to_string(),
            KeyCode::PageUp => "pageup".to_string(),
            KeyCode::PageDown => "pagedown".to_string(),
            KeyCode::Insert => "insert".to_string(),
            KeyCode::Delete => "delete".to_string(),
            KeyCode::F(n) => format!("f{n}"),
            other => format!("{other:?}"),
        };
        parts.push(key);
        format!("CoreKeyBinding({})", parts.join("+"))
    }
}

pub fn register_key_binding(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<CoreKeyBinding>()?;
    Ok(())
}
