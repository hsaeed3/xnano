use pyo3::exceptions::PyTypeError;
use pyo3::prelude::*;
use pyo3::types::{PyList, PyString};
use ratatui::text::{Line, Span, Text};

use super::style::PyStyle;
use super::text::{PyLine, PySpan, PyText};

pub fn extract_span(value: &Bound<'_, PyAny>) -> PyResult<Span<'static>> {
    if let Ok(span) = value.extract::<PyRef<PySpan>>() {
        return Ok(span.inner.clone());
    }
    if let Ok(style) = value.extract::<PyRef<PyStyle>>() {
        return Ok(Span::styled(String::new(), style.inner));
    }
    if let Ok(text) = value.cast::<PyString>() {
        return Ok(Span::raw(text.to_string()));
    }
    Err(PyTypeError::new_err(format!(
        "expected str or Span, got {}",
        value.get_type().name()?
    )))
}

pub fn extract_line(value: &Bound<'_, PyAny>) -> PyResult<Line<'static>> {
    if let Ok(line) = value.extract::<PyRef<PyLine>>() {
        return Ok(line.inner.clone());
    }
    if let Ok(span) = value.extract::<PyRef<PySpan>>() {
        return Ok(Line::from(span.inner.clone()));
    }
    if let Ok(text) = value.cast::<PyString>() {
        return Ok(Line::from(text.to_string()));
    }
    if let Ok(list) = value.cast::<PyList>() {
        let spans: PyResult<Vec<Span<'static>>> =
            list.iter().map(|item| extract_span(&item)).collect();
        return Ok(Line::from(spans?));
    }
    Err(PyTypeError::new_err(format!(
        "expected str, Span, or sequence of Span, got {}",
        value.get_type().name()?
    )))
}

pub fn extract_text(value: &Bound<'_, PyAny>) -> PyResult<Text<'static>> {
    if let Ok(text) = value.extract::<PyRef<PyText>>() {
        return Ok(text.inner.clone());
    }
    if let Ok(line) = value.extract::<PyRef<PyLine>>() {
        return Ok(Text::from(line.inner.clone()));
    }
    if let Ok(span) = value.extract::<PyRef<PySpan>>() {
        return Ok(Text::from(Line::from(span.inner.clone())));
    }
    if let Ok(s) = value.cast::<PyString>() {
        return Ok(Text::from(s.to_string()));
    }
    if let Ok(list) = value.cast::<PyList>() {
        if list.is_empty() {
            return Ok(Text::default());
        }
        let first = list.get_item(0)?;
        if first.is_instance_of::<PySpan>() || first.is_instance_of::<PyString>() {
            let lines = list
                .iter()
                .map(|item| extract_line(&item))
                .collect::<PyResult<Vec<_>>>()?;
            return Ok(Text::from(lines));
        }
        let lines: PyResult<Vec<Line<'static>>> =
            list.iter().map(|item| extract_line(&item)).collect();
        return Ok(Text::from(lines?));
    }
    Err(PyTypeError::new_err(format!(
        "expected str, Line, Span, Text, or sequence, got {}",
        value.get_type().name()?
    )))
}
