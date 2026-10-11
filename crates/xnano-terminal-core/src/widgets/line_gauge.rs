//! `LineGauge`: a one-line progress bar, plus helpers shared by the data widgets.

use std::sync::Arc;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyString;
use xnano_terminal_runtime::buffer::BufferCore;
use xnano_terminal_runtime::dynamic::{Dynamic, FromScalar};
use xnano_terminal_runtime::expression::Evaluation;
use xnano_terminal_runtime::painter::Spec;
use xnano_terminal_runtime::widgets::Shared;
use xnano_terminal_runtime::widgets::line_gauge::{
    LineGaugeSpec, line_set_from_name, line_set_names,
};

use crate::errors::eval_error;
use crate::surface::PySurface;
use crate::widgets::block::block_arg;
use crate::widgets::style::{style_spec_arg, style_spec_to_py};
use crate::widgets::{
    Frame, PyWidget, dynamic_arg, dynamic_f64, dynamic_string, dynamic_to_py, environment_of,
    repaint, widget_initializer,
};

/// The buffer core behind any widget object.
pub(super) fn core_of(widget: &Bound<'_, PyAny>) -> Arc<BufferCore> {
    Arc::clone(
        &widget
            .cast::<PySurface>()
            .expect("a widget is a surface")
            .borrow()
            .core,
    )
}

/// Where a widget currently sits and how big it is.
pub(super) fn frame_of(widget: &Bound<'_, PyAny>) -> Frame {
    let bounds = core_of(widget).lock().bounds();
    Frame {
        width: Some(bounds.width),
        height: Some(bounds.height),
        x: bounds.x,
        y: bounds.y,
    }
}

/// A text setting as a Python object.
pub(super) fn text_to_py<'py>(
    py: Python<'py>,
    value: &Dynamic<String>,
) -> PyResult<Bound<'py, PyAny>> {
    dynamic_to_py(py, value, |py, text| Ok(PyString::new(py, text).into_any()))
}

/// An optional text setting as a Python object.
pub(super) fn optional_text_to_py<'py>(
    py: Python<'py>,
    value: Option<&Dynamic<String>>,
) -> PyResult<Option<Bound<'py, PyAny>>> {
    value.map(|text| text_to_py(py, text)).transpose()
}

/// An optional text setting from a Python value, where ``None`` clears it.
pub(super) fn optional_text_arg(
    value: Option<&Bound<'_, PyAny>>,
) -> PyResult<Option<Dynamic<String>>> {
    value
        .filter(|value| !value.is_none())
        .map(dynamic_string)
        .transpose()
}

/// A whole-number setting that must be zero or more.
pub(super) fn dynamic_unsigned<T>(
    value: &Bound<'_, PyAny>,
    name: &'static str,
) -> PyResult<Dynamic<T>>
where
    T: FromScalar + Clone + TryFrom<i64>,
{
    dynamic_arg(value, move |value| {
        let number: i64 = value.extract()?;
        T::try_from(number).map_err(|_| {
            PyValueError::new_err(format!(
                "{name} must be a whole number of zero or more, not {number}; pass a value such as 0 or 10"
            ))
        })
    })
}

/// Read a bound setting once, now, using the widget's environment.
pub(super) fn resolve_now<T: FromScalar + Clone>(
    core: &Arc<BufferCore>,
    value: &Dynamic<T>,
) -> PyResult<T> {
    let environment = environment_of(core);
    value
        .resolve(environment.as_ref(), &mut Evaluation::default())
        .map_err(|error| eval_error(&error))
}

fn line_set_arg(value: &Bound<'_, PyAny>) -> PyResult<Dynamic<String>> {
    let setting = dynamic_string(value)?;
    if let Dynamic::Fixed(name) = &setting
        && line_set_from_name(name).is_none()
    {
        return Err(PyValueError::new_err(format!(
            "\"{name}\" is not a line set; use one of {}",
            line_set_names()
        )));
    }
    Ok(setting)
}

#[pyclass(name = "LineGauge", module = "xnano._xnano_core", extends = PyWidget, subclass)]
pub struct PyLineGauge {
    spec: Shared<LineGaugeSpec>,
    block: std::sync::Mutex<Option<Py<PyAny>>>,
}

impl PyLineGauge {
    fn edit(slf: &Bound<'_, Self>, change: impl FnOnce(&mut LineGaugeSpec)) {
        slf.borrow().spec.edit(change);
        repaint(&core_of(slf.as_any()));
    }

    fn create(
        py: Python<'_>,
        spec: LineGaugeSpec,
        frame: Frame,
        block: Option<Py<PyAny>>,
    ) -> PyResult<Py<Self>> {
        let shared = Spec::new(spec);
        let initializer = widget_initializer(Arc::clone(&shared), frame, (20, 1))?;
        Py::new(
            py,
            initializer.add_subclass(Self {
                spec: shared,
                block: std::sync::Mutex::new(block),
            }),
        )
    }

    fn duplicate(slf: &Bound<'_, Self>) -> PyResult<Py<Self>> {
        let py = slf.py();
        let spec = slf.borrow().spec.read().clone();
        let block = crate::shared::lock(&slf.borrow().block)
            .as_ref()
            .map(|block| block.clone_ref(py));
        Self::create(py, spec, frame_of(slf.as_any()), block)
    }
}

#[pymethods]
impl PyLineGauge {
    #[new]
    #[pyo3(signature = (ratio = None, *, label = None, line_set = None, filled_symbol = None,
        unfilled_symbol = None, style = None, filled_style = None, unfilled_style = None,
        block = None, width = None, height = None, x = 0, y = 0))]
    fn new(
        ratio: Option<&Bound<'_, PyAny>>,
        label: Option<&Bound<'_, PyAny>>,
        line_set: Option<&Bound<'_, PyAny>>,
        filled_symbol: Option<&Bound<'_, PyAny>>,
        unfilled_symbol: Option<&Bound<'_, PyAny>>,
        style: Option<&Bound<'_, PyAny>>,
        filled_style: Option<&Bound<'_, PyAny>>,
        unfilled_style: Option<&Bound<'_, PyAny>>,
        block: Option<&Bound<'_, PyAny>>,
        width: Option<i32>,
        height: Option<i32>,
        x: i32,
        y: i32,
    ) -> PyResult<PyClassInitializer<Self>> {
        let mut spec = LineGaugeSpec::new(match ratio.filter(|value| !value.is_none()) {
            Some(ratio) => dynamic_f64(ratio)?,
            None => Dynamic::Fixed(0.0),
        });
        spec.label = optional_text_arg(label)?;
        if let Some(line_set) = line_set.filter(|value| !value.is_none()) {
            spec.line_set = line_set_arg(line_set)?;
        }
        spec.filled_symbol = optional_text_arg(filled_symbol)?;
        spec.unfilled_symbol = optional_text_arg(unfilled_symbol)?;
        spec.style = style_spec_arg(style)?;
        spec.filled_style = style_spec_arg(filled_style)?;
        spec.unfilled_style = style_spec_arg(unfilled_style)?;
        spec.block = block_arg(block)?;
        let owned_block = block
            .filter(|value| !value.is_none())
            .map(|value| value.clone().unbind());
        let shared = Spec::new(spec);
        let initializer = widget_initializer(
            Arc::clone(&shared),
            Frame {
                width,
                height,
                x,
                y,
            },
            (20, 1),
        )?;
        Ok(initializer.add_subclass(Self {
            spec: shared,
            block: std::sync::Mutex::new(owned_block),
        }))
    }

    /// The filled fraction, from 0.0 to 1.0.
    #[getter]
    fn ratio<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().ratio.clone();
        dynamic_to_py(slf.py(), &value, |py, ratio| {
            Ok(ratio.into_pyobject(py)?.into_any())
        })
    }

    #[setter]
    fn set_ratio(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let ratio = dynamic_f64(value)?;
        Self::edit(slf, |spec| spec.ratio = ratio);
        Ok(())
    }

    #[getter]
    fn label<'py>(slf: &Bound<'py, Self>) -> PyResult<Option<Bound<'py, PyAny>>> {
        let value = slf.borrow().spec.read().label.clone();
        optional_text_to_py(slf.py(), value.as_ref())
    }

    #[setter]
    fn set_label(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let label = optional_text_arg(value)?;
        Self::edit(slf, |spec| spec.label = label);
        Ok(())
    }

    #[getter]
    fn line_set<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().line_set.clone();
        text_to_py(slf.py(), &value)
    }

    #[setter]
    fn set_line_set(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let line_set = line_set_arg(value)?;
        Self::edit(slf, |spec| spec.line_set = line_set);
        Ok(())
    }

    #[getter]
    fn filled_symbol<'py>(slf: &Bound<'py, Self>) -> PyResult<Option<Bound<'py, PyAny>>> {
        let value = slf.borrow().spec.read().filled_symbol.clone();
        optional_text_to_py(slf.py(), value.as_ref())
    }

    #[setter]
    fn set_filled_symbol(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let symbol = optional_text_arg(value)?;
        Self::edit(slf, |spec| spec.filled_symbol = symbol);
        Ok(())
    }

    #[getter]
    fn unfilled_symbol<'py>(slf: &Bound<'py, Self>) -> PyResult<Option<Bound<'py, PyAny>>> {
        let value = slf.borrow().spec.read().unfilled_symbol.clone();
        optional_text_to_py(slf.py(), value.as_ref())
    }

    #[setter]
    fn set_unfilled_symbol(
        slf: &Bound<'_, Self>,
        value: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<()> {
        let symbol = optional_text_arg(value)?;
        Self::edit(slf, |spec| spec.unfilled_symbol = symbol);
        Ok(())
    }

    #[getter]
    fn style(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let spec = slf.borrow().spec.read().style.clone();
        style_spec_to_py(slf.py(), &spec)
    }

    #[setter]
    fn set_style(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let style = style_spec_arg(value)?;
        Self::edit(slf, |spec| spec.style = style);
        Ok(())
    }

    #[getter]
    fn filled_style(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let spec = slf.borrow().spec.read().filled_style.clone();
        style_spec_to_py(slf.py(), &spec)
    }

    #[setter]
    fn set_filled_style(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let style = style_spec_arg(value)?;
        Self::edit(slf, |spec| spec.filled_style = style);
        Ok(())
    }

    #[getter]
    fn unfilled_style(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let spec = slf.borrow().spec.read().unfilled_style.clone();
        style_spec_to_py(slf.py(), &spec)
    }

    #[setter]
    fn set_unfilled_style(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let style = style_spec_arg(value)?;
        Self::edit(slf, |spec| spec.unfilled_style = style);
        Ok(())
    }

    /// The ``Block`` framing the gauge, or ``None``.
    #[getter]
    fn block(slf: &Bound<'_, Self>) -> Option<Py<PyAny>> {
        crate::shared::lock(&slf.borrow().block)
            .as_ref()
            .map(|block| block.clone_ref(slf.py()))
    }

    #[setter]
    fn set_block(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let shared = block_arg(value)?;
        *crate::shared::lock(&slf.borrow().block) = value
            .filter(|value| !value.is_none())
            .map(|value| value.clone().unbind());
        Self::edit(slf, |spec| spec.block = shared);
        Ok(())
    }

    fn copy(slf: &Bound<'_, Self>) -> PyResult<Py<Self>> {
        Self::duplicate(slf)
    }

    fn __copy__(slf: &Bound<'_, Self>) -> PyResult<Py<Self>> {
        Self::duplicate(slf)
    }

    fn __deepcopy__(slf: &Bound<'_, Self>, _memo: &Bound<'_, PyAny>) -> PyResult<Py<Self>> {
        Self::duplicate(slf)
    }

    fn __repr__(slf: &Bound<'_, Self>) -> String {
        let frame = frame_of(slf.as_any());
        let ratio = match &slf.borrow().spec.read().ratio {
            Dynamic::Fixed(ratio) => format!("{ratio}"),
            Dynamic::Bound(_) => "<bound>".to_owned(),
        };
        format!(
            "LineGauge(ratio={ratio}, width={}, height={})",
            frame.width.unwrap_or(0),
            frame.height.unwrap_or(0)
        )
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyLineGauge>()
}
