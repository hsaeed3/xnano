use pyo3::prelude::*;
use pyo3::types::PyList;
use ratatui::style::Style;
use ratatui::text::{Line, Span, Text};

use super::convert::{extract_line, extract_span};
use super::layout::PyAlignment;
use super::style::{PyColor, PyModifier, PyStyle};

#[pyclass(name = "Span", module = "xnano_core.rust.native")]
#[derive(Clone)]
pub struct PySpan {
    pub inner: Span<'static>,
}

#[pymethods]
impl PySpan {
    #[staticmethod]
    fn default() -> Self {
        Self {
            inner: Span::raw(""),
        }
    }

    #[staticmethod]
    fn raw(content: &str) -> Self {
        Self {
            inner: Span::raw(content.to_string()),
        }
    }

    #[staticmethod]
    fn styled(content: &str, style: PyStyle) -> Self {
        Self {
            inner: Span::styled(content.to_string(), style.inner),
        }
    }

    #[staticmethod]
    #[pyo3(name = "from")]
    fn from_value(content: &Bound<'_, PyAny>) -> PyResult<Self> {
        if let Ok(span) = content.extract::<PyRef<PySpan>>() {
            return Ok(Self {
                inner: span.inner.clone(),
            });
        }
        if let Ok(text) = content.extract::<&str>() {
            return Ok(Self {
                inner: Span::from(text.to_string()),
            });
        }
        Err(pyo3::exceptions::PyTypeError::new_err(
            "expected str or Span",
        ))
    }

    fn content(&self, value: &str) -> Self {
        Self {
            inner: self.inner.clone().content(value.to_string()),
        }
    }

    fn style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().style(style.inner),
        }
    }

    fn patch_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().patch_style(style.inner),
        }
    }

    fn reset_style(&self) -> Self {
        Self {
            inner: self.inner.clone().reset_style(),
        }
    }

    fn width(&self) -> usize {
        self.inner.width()
    }

    #[getter]
    fn text(&self) -> String {
        self.inner.content.to_string()
    }

    fn __repr__(&self) -> String {
        format!("{self:?}", self = self.inner)
    }
}

#[pyclass(name = "Line", module = "xnano_core.rust.native")]
#[derive(Clone)]
pub struct PyLine {
    pub inner: Line<'static>,
}

#[pymethods]
impl PyLine {
    #[staticmethod]
    fn raw(content: &str) -> Self {
        Self {
            inner: Line::from(content.to_string()),
        }
    }

    #[staticmethod]
    fn styled(content: &str, style: PyStyle) -> Self {
        Self {
            inner: Line::styled(content.to_string(), style.inner),
        }
    }

    #[staticmethod]
    fn from_spans(spans: &Bound<'_, PyList>) -> PyResult<Self> {
        let spans: Vec<Span<'static>> = spans
            .iter()
            .map(|item| extract_span(&item))
            .collect::<PyResult<_>>()?;
        Ok(Self {
            inner: Line::from(spans),
        })
    }

    fn style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().style(style.inner),
        }
    }

    fn patch_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().patch_style(style.inner),
        }
    }

    fn reset_style(&self) -> Self {
        Self {
            inner: self.inner.clone().reset_style(),
        }
    }

    fn width(&self) -> usize {
        self.inner.width()
    }

    fn alignment(&self, alignment: PyAlignment) -> Self {
        Self {
            inner: self.inner.clone().alignment(alignment.into()),
        }
    }

    fn left_aligned(&self) -> Self {
        Self {
            inner: self.inner.clone().left_aligned(),
        }
    }

    fn centered(&self) -> Self {
        Self {
            inner: self.inner.clone().centered(),
        }
    }

    fn right_aligned(&self) -> Self {
        Self {
            inner: self.inner.clone().right_aligned(),
        }
    }

    fn spans(&self, spans: &Bound<'_, PyList>) -> PyResult<Self> {
        let items: Vec<Span<'static>> = spans
            .iter()
            .map(|item| extract_span(&item))
            .collect::<PyResult<_>>()?;
        Ok(Self {
            inner: self.inner.clone().spans(items),
        })
    }

    fn push_span(&self, span: &Bound<'_, PyAny>) -> PyResult<Self> {
        let mut inner = self.inner.clone();
        inner.push_span(extract_span(span)?);
        Ok(Self { inner })
    }

    fn __repr__(&self) -> String {
        format!("{self:?}", self = self.inner)
    }
}

#[pyclass(name = "Text", module = "xnano_core.rust.native")]
#[derive(Clone)]
pub struct PyText {
    pub inner: Text<'static>,
}

#[pymethods]
impl PyText {
    #[staticmethod]
    fn raw(content: &str) -> Self {
        Self {
            inner: Text::from(content.to_string()),
        }
    }

    #[staticmethod]
    fn styled(content: &str, style: PyStyle) -> Self {
        Self {
            inner: Text::styled(content.to_string(), style.inner),
        }
    }

    #[staticmethod]
    fn from_lines(lines: &Bound<'_, PyList>) -> PyResult<Self> {
        let lines: Vec<Line<'static>> = lines
            .iter()
            .map(|item| extract_line(&item))
            .collect::<PyResult<_>>()?;
        Ok(Self {
            inner: Text::from(lines),
        })
    }

    fn style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().style(style.inner),
        }
    }

    fn patch_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().patch_style(style.inner),
        }
    }

    fn reset_style(&self) -> Self {
        Self {
            inner: self.inner.clone().reset_style(),
        }
    }

    fn width(&self) -> usize {
        self.inner.width()
    }

    fn height(&self) -> usize {
        self.inner.height()
    }

    fn alignment(&self, alignment: PyAlignment) -> Self {
        Self {
            inner: self.inner.clone().alignment(alignment.into()),
        }
    }

    fn left_aligned(&self) -> Self {
        Self {
            inner: self.inner.clone().left_aligned(),
        }
    }

    fn centered(&self) -> Self {
        Self {
            inner: self.inner.clone().centered(),
        }
    }

    fn right_aligned(&self) -> Self {
        Self {
            inner: self.inner.clone().right_aligned(),
        }
    }

    fn push_line(&self, line: &Bound<'_, PyAny>) -> PyResult<Self> {
        let mut inner = self.inner.clone();
        inner.push_line(extract_line(line)?);
        Ok(Self { inner })
    }

    fn __repr__(&self) -> String {
        format!("{self:?}", self = self.inner)
    }
}

/// Create a styled span from a string and style shorthand methods.
#[pyfunction]
#[pyo3(signature = (content, fg=None, bg=None, modifiers=None))]
fn styled_span(
    content: &str,
    fg: Option<PyColor>,
    bg: Option<PyColor>,
    modifiers: Option<PyModifier>,
) -> PySpan {
    let mut style = Style::default();
    if let Some(color) = fg {
        style = style.fg(color.inner);
    }
    if let Some(color) = bg {
        style = style.bg(color.inner);
    }
    if let Some(modifier) = modifiers {
        style = style.add_modifier(modifier.inner);
    }
    PySpan {
        inner: Span::styled(content.to_string(), style),
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PySpan>()?;
    m.add_class::<PyLine>()?;
    m.add_class::<PyText>()?;
    m.add_function(wrap_pyfunction!(styled_span, m)?)?;
    Ok(())
}
