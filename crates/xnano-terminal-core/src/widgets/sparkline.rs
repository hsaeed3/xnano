//! `Sparkline`: a row of bars showing a series of values.

use std::sync::Arc;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyTuple;
use xnano_terminal_runtime::dynamic::Dynamic;
use xnano_terminal_runtime::painter::Spec;
use xnano_terminal_runtime::widgets::Shared;
use xnano_terminal_runtime::widgets::sparkline::{
    BAR_SETS, SparklineBarData, SparklineSpec, bar_set_from_name,
};

use crate::style::{PyStyle, style_arg};
use crate::widgets::block::block_arg;
use crate::widgets::line_gauge::{
    core_of, dynamic_unsigned, frame_of, optional_text_arg, optional_text_to_py, text_to_py,
};
use crate::widgets::style::{style_spec_arg, style_spec_to_py};
use crate::widgets::{Frame, PyWidget, dynamic_string, dynamic_to_py, repaint, widget_initializer};

/// One value of a sparkline, with an optional style of its own.
#[pyclass(
    name = "SparklineBar",
    module = "xnano._xnano_core",
    frozen,
    eq,
    hash,
    from_py_object
)]
#[derive(Clone, PartialEq, Eq, Hash)]
pub struct PySparklineBar {
    pub data: SparklineBarData,
}

#[pymethods]
impl PySparklineBar {
    #[new]
    #[pyo3(signature = (value, style = None))]
    fn new(value: Option<i64>, style: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let value = value
            .map(|number| {
                u64::try_from(number).map_err(|_| {
                    PyValueError::new_err(format!(
                        "a sparkline value must be zero or more, not {number}; use None for an absent value"
                    ))
                })
            })
            .transpose()?;
        let style = style
            .filter(|value| !value.is_none())
            .map(|value| style_arg(Some(value)))
            .transpose()?;
        Ok(Self {
            data: SparklineBarData { value, style },
        })
    }

    /// The value, or ``None`` when the bar is absent.
    #[getter]
    fn value(&self) -> Option<u64> {
        self.data.value
    }

    #[getter]
    fn style(&self) -> Option<PyStyle> {
        self.data.style.map(|inner| PyStyle { inner })
    }

    fn __copy__(&self) -> Self {
        self.clone()
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.clone()
    }

    fn __repr__(&self) -> String {
        let value = self
            .data
            .value
            .map_or_else(|| "None".to_owned(), |value| value.to_string());
        if self.data.style.is_some() {
            format!("SparklineBar(value={value}, style=...)")
        } else {
            format!("SparklineBar(value={value})")
        }
    }
}

fn bars_arg(value: &Bound<'_, PyAny>) -> PyResult<Vec<SparklineBarData>> {
    let mut bars = Vec::new();
    for item in value.try_iter()? {
        let item = item?;
        if let Ok(bar) = item.extract::<PySparklineBar>() {
            bars.push(bar.data);
        } else if item.is_none() {
            bars.push(SparklineBarData {
                value: None,
                style: None,
            });
        } else {
            let number: i64 = item.extract().map_err(|_| {
                PyValueError::new_err(
                    "sparkline values are whole numbers, None for an absent value, or SparklineBar objects",
                )
            })?;
            let value = u64::try_from(number).map_err(|_| {
                PyValueError::new_err(format!(
                    "a sparkline value must be zero or more, not {number}; use None for an absent value"
                ))
            })?;
            bars.push(SparklineBarData {
                value: Some(value),
                style: None,
            });
        }
    }
    Ok(bars)
}

fn choice_arg(value: &Bound<'_, PyAny>, choices: &[&str], what: &str) -> PyResult<Dynamic<String>> {
    let setting = dynamic_string(value)?;
    if let Dynamic::Fixed(name) = &setting
        && !choices.contains(&name.as_str())
    {
        return Err(PyValueError::new_err(format!(
            "\"{name}\" is not a {what}; use one of {}",
            choices
                .iter()
                .map(|choice| format!("\"{choice}\""))
                .collect::<Vec<_>>()
                .join(", ")
        )));
    }
    Ok(setting)
}

pub(super) fn bar_set_arg(value: &Bound<'_, PyAny>) -> PyResult<Dynamic<String>> {
    let names: Vec<&str> = BAR_SETS.iter().map(|(name, _)| *name).collect();
    let setting = choice_arg(value, &names, "bar set")?;
    debug_assert!(
        setting
            .fixed()
            .is_none_or(|name| bar_set_from_name(name).is_some())
    );
    Ok(setting)
}

#[pyclass(name = "Sparkline", module = "xnano._xnano_core", extends = PyWidget, subclass)]
pub struct PySparkline {
    spec: Shared<SparklineSpec>,
    block: std::sync::Mutex<Option<Py<PyAny>>>,
}

impl PySparkline {
    fn edit<R>(slf: &Bound<'_, Self>, change: impl FnOnce(&mut SparklineSpec) -> R) -> R {
        let result = slf.borrow().spec.edit(change);
        repaint(&core_of(slf.as_any()));
        result
    }

    fn create(
        py: Python<'_>,
        spec: SparklineSpec,
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

    fn trim(bars: &mut Vec<SparklineBarData>, maximum_length: Option<usize>) {
        if let Some(maximum) = maximum_length
            && bars.len() > maximum
        {
            bars.drain(..bars.len() - maximum);
        }
    }
}

#[pymethods]
impl PySparkline {
    #[new]
    #[pyo3(signature = (values = None, *, maximum = None, style = None, absent_value_style = None,
        absent_value_symbol = None, direction = None, bar_set = None, block = None,
        width = None, height = None, x = 0, y = 0))]
    fn new(
        values: Option<&Bound<'_, PyAny>>,
        maximum: Option<&Bound<'_, PyAny>>,
        style: Option<&Bound<'_, PyAny>>,
        absent_value_style: Option<&Bound<'_, PyAny>>,
        absent_value_symbol: Option<&Bound<'_, PyAny>>,
        direction: Option<&Bound<'_, PyAny>>,
        bar_set: Option<&Bound<'_, PyAny>>,
        block: Option<&Bound<'_, PyAny>>,
        width: Option<i32>,
        height: Option<i32>,
        x: i32,
        y: i32,
    ) -> PyResult<PyClassInitializer<Self>> {
        let mut spec = SparklineSpec::default();
        if let Some(values) = values.filter(|value| !value.is_none()) {
            spec.bars = bars_arg(values)?;
        }
        spec.maximum = maximum
            .filter(|value| !value.is_none())
            .map(|value| dynamic_unsigned(value, "the maximum"))
            .transpose()?;
        spec.style = style_spec_arg(style)?;
        spec.absent_value_style = style_spec_arg(absent_value_style)?;
        spec.absent_value_symbol = optional_text_arg(absent_value_symbol)?;
        if let Some(direction) = direction.filter(|value| !value.is_none()) {
            spec.direction =
                choice_arg(direction, &["left_to_right", "right_to_left"], "direction")?;
        }
        if let Some(bar_set) = bar_set.filter(|value| !value.is_none()) {
            spec.bar_set = bar_set_arg(bar_set)?;
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

    /// The values shown, with ``None`` for absent values.
    #[getter]
    fn values<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyTuple>> {
        let py = slf.py();
        let values = slf
            .borrow()
            .spec
            .read()
            .bars
            .iter()
            .map(|bar| bar.value)
            .collect::<Vec<_>>();
        PyTuple::new(py, values)
    }

    #[setter]
    fn set_values(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let bars = bars_arg(value)?;
        Self::edit(slf, |spec| spec.bars = bars);
        Ok(())
    }

    /// The values with their individual styles.
    #[getter]
    fn bars(slf: &Bound<'_, Self>) -> Vec<PySparklineBar> {
        slf.borrow()
            .spec
            .read()
            .bars
            .iter()
            .map(|data| PySparklineBar { data: *data })
            .collect()
    }

    /// Add a value at the end, dropping the oldest ones beyond ``maximum_length``.
    #[pyo3(signature = (value, *, maximum_length = None))]
    fn append(
        slf: &Bound<'_, Self>,
        value: &Bound<'_, PyAny>,
        maximum_length: Option<usize>,
    ) -> PyResult<()> {
        let mut added = bars_arg(&PyTuple::new(slf.py(), [value])?.into_any())?;
        Self::edit(slf, |spec| {
            spec.bars.append(&mut added);
            Self::trim(&mut spec.bars, maximum_length);
        });
        Ok(())
    }

    /// Add several values at the end, dropping the oldest ones beyond ``maximum_length``.
    #[pyo3(signature = (values, *, maximum_length = None))]
    fn extend(
        slf: &Bound<'_, Self>,
        values: &Bound<'_, PyAny>,
        maximum_length: Option<usize>,
    ) -> PyResult<()> {
        let mut added = bars_arg(values)?;
        Self::edit(slf, |spec| {
            spec.bars.append(&mut added);
            Self::trim(&mut spec.bars, maximum_length);
        });
        Ok(())
    }

    /// Remove every value.
    fn clear(slf: &Bound<'_, Self>) {
        Self::edit(slf, |spec| spec.bars.clear());
    }

    fn __len__(slf: &Bound<'_, Self>) -> usize {
        slf.borrow().spec.read().bars.len()
    }

    /// The value that fills a bar completely, or ``None`` to use the largest value shown.
    #[getter]
    fn maximum<'py>(slf: &Bound<'py, Self>) -> PyResult<Option<Bound<'py, PyAny>>> {
        let value = slf.borrow().spec.read().maximum.clone();
        value
            .map(|maximum| {
                dynamic_to_py(slf.py(), &maximum, |py, number| {
                    Ok(number.into_pyobject(py)?.into_any())
                })
            })
            .transpose()
    }

    #[setter]
    fn set_maximum(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let maximum = value
            .filter(|value| !value.is_none())
            .map(|value| dynamic_unsigned(value, "the maximum"))
            .transpose()?;
        Self::edit(slf, |spec| spec.maximum = maximum);
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
    fn absent_value_style(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let spec = slf.borrow().spec.read().absent_value_style.clone();
        style_spec_to_py(slf.py(), &spec)
    }

    #[setter]
    fn set_absent_value_style(
        slf: &Bound<'_, Self>,
        value: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<()> {
        let style = style_spec_arg(value)?;
        Self::edit(slf, |spec| spec.absent_value_style = style);
        Ok(())
    }

    #[getter]
    fn absent_value_symbol<'py>(slf: &Bound<'py, Self>) -> PyResult<Option<Bound<'py, PyAny>>> {
        let value = slf.borrow().spec.read().absent_value_symbol.clone();
        optional_text_to_py(slf.py(), value.as_ref())
    }

    #[setter]
    fn set_absent_value_symbol(
        slf: &Bound<'_, Self>,
        value: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<()> {
        let symbol = optional_text_arg(value)?;
        Self::edit(slf, |spec| spec.absent_value_symbol = symbol);
        Ok(())
    }

    #[getter]
    fn direction<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().direction.clone();
        text_to_py(slf.py(), &value)
    }

    #[setter]
    fn set_direction(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let direction = choice_arg(value, &["left_to_right", "right_to_left"], "direction")?;
        Self::edit(slf, |spec| spec.direction = direction);
        Ok(())
    }

    #[getter]
    fn bar_set<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().bar_set.clone();
        text_to_py(slf.py(), &value)
    }

    #[setter]
    fn set_bar_set(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let bar_set = bar_set_arg(value)?;
        Self::edit(slf, |spec| spec.bar_set = bar_set);
        Ok(())
    }

    /// The ``Block`` framing the sparkline, or ``None``.
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
        format!(
            "Sparkline(values={}, width={}, height={})",
            slf.borrow().spec.read().bars.len(),
            frame.width.unwrap_or(0),
            frame.height.unwrap_or(0)
        )
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PySparklineBar>()?;
    m.add_class::<PySparkline>()
}
