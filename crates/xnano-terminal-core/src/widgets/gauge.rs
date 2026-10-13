//! `Gauge`: a filled bar with a percentage or label.

use std::sync::Arc;

use pyo3::prelude::*;
use xnano_terminal_runtime::dynamic::Dynamic;
use xnano_terminal_runtime::painter::Spec;
use xnano_terminal_runtime::widgets::Shared;
use xnano_terminal_runtime::widgets::gauge::GaugeSpec;

use crate::widgets::block::block_arg;
use crate::widgets::style::{style_spec_arg, style_spec_to_py};
use crate::widgets::{
    Frame, PyWidget, dynamic_bool, dynamic_f64, dynamic_string, dynamic_to_py, repaint,
    widget_initializer,
};

#[pyclass(name = "Gauge", module = "xnano_core._xnano_core", extends = PyWidget, subclass)]
pub struct PyGauge {
    spec: Shared<GaugeSpec>,
    block: std::sync::Mutex<Option<Py<PyAny>>>,
}

impl PyGauge {
    fn edit(slf: &Bound<'_, Self>, change: impl FnOnce(&mut GaugeSpec)) {
        slf.borrow().spec.edit(change);
        let core = Arc::clone(&slf.as_super().as_super().as_super().borrow().core);
        repaint(&core);
    }
}

#[pymethods]
impl PyGauge {
    #[new]
    #[pyo3(signature = (ratio = None, *, label = None, style = None, gauge_style = None,
        use_unicode = None, block = None, width = None, height = None, x = 0, y = 0))]
    fn new(
        ratio: Option<&Bound<'_, PyAny>>,
        label: Option<&Bound<'_, PyAny>>,
        style: Option<&Bound<'_, PyAny>>,
        gauge_style: Option<&Bound<'_, PyAny>>,
        use_unicode: Option<&Bound<'_, PyAny>>,
        block: Option<&Bound<'_, PyAny>>,
        width: Option<i32>,
        height: Option<i32>,
        x: i32,
        y: i32,
    ) -> PyResult<PyClassInitializer<Self>> {
        let mut spec = GaugeSpec::new(match ratio.filter(|value| !value.is_none()) {
            Some(ratio) => dynamic_f64(ratio)?,
            None => Dynamic::Fixed(0.0),
        });
        if let Some(label) = label.filter(|value| !value.is_none()) {
            spec.label = Some(dynamic_string(label)?);
        }
        spec.style = style_spec_arg(style)?;
        spec.gauge_style = style_spec_arg(gauge_style)?;
        if let Some(flag) = use_unicode.filter(|value| !value.is_none()) {
            spec.use_unicode = dynamic_bool(flag)?;
        }
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
        value
            .map(|label| {
                dynamic_to_py(slf.py(), &label, |py, text| {
                    Ok(pyo3::types::PyString::new(py, text).into_any())
                })
            })
            .transpose()
    }

    #[setter]
    fn set_label(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let label = value
            .filter(|value| !value.is_none())
            .map(dynamic_string)
            .transpose()?;
        Self::edit(slf, |spec| spec.label = label);
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
    fn gauge_style(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let spec = slf.borrow().spec.read().gauge_style.clone();
        style_spec_to_py(slf.py(), &spec)
    }

    #[setter]
    fn set_gauge_style(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let style = style_spec_arg(value)?;
        Self::edit(slf, |spec| spec.gauge_style = style);
        Ok(())
    }

    #[getter]
    fn use_unicode<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().use_unicode.clone();
        dynamic_to_py(slf.py(), &value, |py, flag| {
            Ok(pyo3::types::PyBool::new(py, *flag).to_owned().into_any())
        })
    }

    #[setter]
    fn set_use_unicode(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let flag = dynamic_bool(value)?;
        Self::edit(slf, |spec| spec.use_unicode = flag);
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

    fn __repr__(slf: &Bound<'_, Self>) -> String {
        let state = slf
            .as_super()
            .as_super()
            .as_super()
            .borrow()
            .core
            .lock()
            .bounds();
        format!("Gauge(width={}, height={})", state.width, state.height)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyGauge>()
}
