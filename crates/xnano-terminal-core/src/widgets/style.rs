//! Styles whose colors can follow expressions.

use std::sync::Mutex;

use pyo3::prelude::*;
use xnano_terminal_runtime::dynamic::Dynamic;
use xnano_terminal_runtime::widgets::style::StyleSpec;

use crate::style::{PyColor, PyStyle, modifiers_arg};
use crate::widgets::{dynamic_color, dynamic_to_py};

/// A style whose colors may be plain values or expressions.
///
/// Anything that accepts a ``Style`` in a widget setting accepts a ``DynamicStyle`` too.
#[pyclass(name = "DynamicStyle", module = "xnano._xnano_core")]
pub struct PyDynamicStyle {
    pub spec: Mutex<StyleSpec>,
}

/// A widget style setting: a plain ``Style``, a ``DynamicStyle`` or nothing.
pub fn style_spec_arg(value: Option<&Bound<'_, PyAny>>) -> PyResult<StyleSpec> {
    match value {
        None => Ok(StyleSpec::default()),
        Some(value) if value.is_none() => Ok(StyleSpec::default()),
        Some(value) => {
            if let Ok(style) = value.extract::<PyStyle>() {
                return Ok(StyleSpec::fixed(style.inner));
            }
            if let Ok(dynamic) = value.cast::<PyDynamicStyle>() {
                return Ok(crate::shared::lock(&dynamic.borrow().spec).clone());
            }
            Err(pyo3::exceptions::PyTypeError::new_err(
                "a style setting takes a Style or a DynamicStyle",
            ))
        }
    }
}

/// A widget style setting as a Python object.
pub fn style_spec_to_py(py: Python<'_>, spec: &StyleSpec) -> PyResult<Py<PyAny>> {
    let is_fixed = [&spec.foreground, &spec.background, &spec.underline_color]
        .iter()
        .all(|color| color.as_ref().is_none_or(|color| !color.is_bound()));
    if is_fixed {
        let mut style = xnano_terminal_runtime::style::Style::default()
            .add_modifier(spec.add_modifier)
            .remove_modifier(spec.remove_modifier);
        if let Some(Dynamic::Fixed(color)) = &spec.foreground {
            style = style.fg(*color);
        }
        if let Some(Dynamic::Fixed(color)) = &spec.background {
            style = style.bg(*color);
        }
        if let Some(Dynamic::Fixed(color)) = &spec.underline_color {
            style = style.underline_color(*color);
        }
        return Ok(Py::new(py, PyStyle { inner: style })?.into_any());
    }
    Ok(Py::new(
        py,
        PyDynamicStyle {
            spec: Mutex::new(spec.clone()),
        },
    )?
    .into_any())
}

fn color_setting(
    py: Python<'_>,
    color: Option<&Dynamic<xnano_terminal_runtime::style::Color>>,
) -> PyResult<Py<PyAny>> {
    match color {
        None => Ok(py.None()),
        Some(color) => Ok(dynamic_to_py(py, color, |py, color| {
            Ok(Py::new(py, PyColor { inner: *color })?
                .into_bound(py)
                .into_any())
        })?
        .unbind()),
    }
}

#[pymethods]
impl PyDynamicStyle {
    #[new]
    #[pyo3(signature = (foreground = None, background = None, *, underline_color = None, modifiers = None))]
    fn new(
        foreground: Option<&Bound<'_, PyAny>>,
        background: Option<&Bound<'_, PyAny>>,
        underline_color: Option<&Bound<'_, PyAny>>,
        modifiers: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Self> {
        let optional = |value: Option<&Bound<'_, PyAny>>| {
            value
                .filter(|value| !value.is_none())
                .map(dynamic_color)
                .transpose()
        };
        let mut spec = StyleSpec {
            foreground: optional(foreground)?,
            background: optional(background)?,
            underline_color: optional(underline_color)?,
            ..StyleSpec::default()
        };
        if let Some(modifiers) = modifiers.filter(|value| !value.is_none()) {
            spec.add_modifier = modifiers_arg(modifiers)?;
        }
        Ok(Self {
            spec: Mutex::new(spec),
        })
    }

    #[getter]
    fn foreground(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        color_setting(py, crate::shared::lock(&self.spec).foreground.as_ref())
    }

    #[setter]
    fn set_foreground(&self, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let color = value
            .filter(|value| !value.is_none())
            .map(dynamic_color)
            .transpose()?;
        crate::shared::lock(&self.spec).foreground = color;
        Ok(())
    }

    #[getter]
    fn background(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        color_setting(py, crate::shared::lock(&self.spec).background.as_ref())
    }

    #[setter]
    fn set_background(&self, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let color = value
            .filter(|value| !value.is_none())
            .map(dynamic_color)
            .transpose()?;
        crate::shared::lock(&self.spec).background = color;
        Ok(())
    }

    fn __repr__(&self) -> String {
        let spec = crate::shared::lock(&self.spec);
        format!(
            "DynamicStyle(foreground={}, background={})",
            if spec.foreground.is_some() {
                "set"
            } else {
                "None"
            },
            if spec.background.is_some() {
                "set"
            } else {
                "None"
            },
        )
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyDynamicStyle>()
}
