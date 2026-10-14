//! `BarChart`: groups of labelled bars, with `Bar` and `BarGroup` values.

use std::sync::Arc;

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyTuple;
use xnano_terminal_runtime::dynamic::Dynamic;
use xnano_terminal_runtime::painter::Spec;
use xnano_terminal_runtime::widgets::Shared;
use xnano_terminal_runtime::widgets::bar_chart::{BarChartSpec, BarData, BarGroupData};

use crate::style::{PyStyle, style_arg};
use crate::widgets::block::block_arg;
use crate::widgets::line_gauge::{core_of, dynamic_unsigned, frame_of, text_to_py};
use crate::widgets::sparkline::bar_set_arg;
use crate::widgets::style::{style_spec_arg, style_spec_to_py};
use crate::widgets::{Frame, PyWidget, dynamic_string, dynamic_to_py, repaint, widget_initializer};

fn unsigned(value: i64, what: &str) -> PyResult<u64> {
    u64::try_from(value).map_err(|_| {
        PyValueError::new_err(format!(
            "{what} must be zero or more, not {value}; pass a value such as 0 or 10"
        ))
    })
}

/// One bar of a bar chart.
#[pyclass(
    name = "Bar",
    module = "xnano_core._xnano_core",
    frozen,
    eq,
    hash,
    from_py_object
)]
#[derive(Clone, PartialEq, Eq, Hash)]
pub struct PyBar {
    pub data: BarData,
}

#[pymethods]
impl PyBar {
    #[new]
    #[pyo3(signature = (value, label = None, *, text_value = None, style = None, value_style = None))]
    fn new(
        value: i64,
        label: Option<String>,
        text_value: Option<String>,
        style: Option<&Bound<'_, PyAny>>,
        value_style: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Self> {
        Ok(Self {
            data: BarData {
                value: unsigned(value, "a bar value")?,
                label,
                text_value,
                style: style_arg(style)?,
                value_style: style_arg(value_style)?,
            },
        })
    }

    #[getter]
    fn value(&self) -> u64 {
        self.data.value
    }

    #[getter]
    fn label(&self) -> Option<String> {
        self.data.label.clone()
    }

    #[getter]
    fn text_value(&self) -> Option<String> {
        self.data.text_value.clone()
    }

    #[getter]
    fn style(&self) -> PyStyle {
        PyStyle {
            inner: self.data.style,
        }
    }

    #[getter]
    fn value_style(&self) -> PyStyle {
        PyStyle {
            inner: self.data.value_style,
        }
    }

    fn __copy__(&self) -> Self {
        self.clone()
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.clone()
    }

    fn __repr__(&self) -> String {
        match &self.data.label {
            Some(label) => format!("Bar(value={}, label={label:?})", self.data.value),
            None => format!("Bar(value={})", self.data.value),
        }
    }
}

fn bar_arg(item: &Bound<'_, PyAny>) -> PyResult<BarData> {
    if let Ok(bar) = item.extract::<PyBar>() {
        return Ok(bar.data);
    }
    let value: i64 = item
        .extract()
        .map_err(|_| PyTypeError::new_err("bars are Bar objects or whole numbers"))?;
    Ok(BarData {
        value: unsigned(value, "a bar value")?,
        label: None,
        text_value: None,
        style: xnano_terminal_runtime::style::Style::default(),
        value_style: xnano_terminal_runtime::style::Style::default(),
    })
}

fn bars_arg(value: &Bound<'_, PyAny>) -> PyResult<Vec<BarData>> {
    value.try_iter()?.map(|item| bar_arg(&item?)).collect()
}

/// Bars drawn together under one label.
#[pyclass(
    name = "BarGroup",
    module = "xnano_core._xnano_core",
    frozen,
    eq,
    hash,
    from_py_object
)]
#[derive(Clone, PartialEq, Eq, Hash)]
pub struct PyBarGroup {
    pub data: BarGroupData,
}

#[pymethods]
impl PyBarGroup {
    #[new]
    #[pyo3(signature = (bars, label = None))]
    fn new(bars: &Bound<'_, PyAny>, label: Option<String>) -> PyResult<Self> {
        Ok(Self {
            data: BarGroupData {
                label,
                bars: bars_arg(bars)?,
            },
        })
    }

    #[getter]
    fn bars(&self) -> Vec<PyBar> {
        self.data
            .bars
            .iter()
            .map(|data| PyBar { data: data.clone() })
            .collect()
    }

    #[getter]
    fn label(&self) -> Option<String> {
        self.data.label.clone()
    }

    fn __copy__(&self) -> Self {
        self.clone()
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "BarGroup(bars={}, label={:?})",
            self.data.bars.len(),
            self.data.label
        )
    }
}

/// Bars and groups mixed in one sequence are not allowed; bars alone make one group.
fn groups_arg(value: &Bound<'_, PyAny>) -> PyResult<Vec<BarGroupData>> {
    let items = value.try_iter()?.collect::<PyResult<Vec<_>>>()?;
    let groups: Vec<_> = items
        .iter()
        .filter(|item| item.extract::<PyBarGroup>().is_ok())
        .collect();
    if groups.is_empty() {
        let bars = items.iter().map(bar_arg).collect::<PyResult<Vec<_>>>()?;
        return Ok(if bars.is_empty() {
            Vec::new()
        } else {
            vec![BarGroupData { label: None, bars }]
        });
    }
    if groups.len() != items.len() {
        return Err(PyTypeError::new_err(
            "pass either BarGroup objects or bars (Bar objects and numbers), not both; wrap loose bars in a BarGroup",
        ));
    }
    Ok(items
        .iter()
        .filter_map(|item| item.extract::<PyBarGroup>().ok().map(|group| group.data))
        .collect())
}

fn direction_arg(value: &Bound<'_, PyAny>) -> PyResult<Dynamic<String>> {
    let setting = dynamic_string(value)?;
    if let Dynamic::Fixed(name) = &setting
        && name != "vertical"
        && name != "horizontal"
    {
        return Err(PyValueError::new_err(format!(
            "\"{name}\" is not a direction; use \"vertical\" or \"horizontal\""
        )));
    }
    Ok(setting)
}

#[pyclass(name = "BarChart", module = "xnano_core._xnano_core", extends = PyWidget, subclass)]
pub struct PyBarChart {
    spec: Shared<BarChartSpec>,
    block: std::sync::Mutex<Option<Py<PyAny>>>,
}

impl PyBarChart {
    fn edit<R>(slf: &Bound<'_, Self>, change: impl FnOnce(&mut BarChartSpec) -> R) -> R {
        let result = slf.borrow().spec.edit(change);
        repaint(&core_of(slf.as_any()));
        result
    }

    fn duplicate(slf: &Bound<'_, Self>) -> PyResult<Py<Self>> {
        let py = slf.py();
        let spec = Spec::new(slf.borrow().spec.read().clone());
        let block = crate::shared::lock(&slf.borrow().block)
            .as_ref()
            .map(|block| block.clone_ref(py));
        let initializer = widget_initializer(Arc::clone(&spec), frame_of(slf.as_any()), (20, 5))?;
        Py::new(
            py,
            initializer.add_subclass(Self {
                spec,
                block: std::sync::Mutex::new(block),
            }),
        )
    }
}

#[pymethods]
impl PyBarChart {
    #[new]
    #[pyo3(signature = (data = None, *, bar_width = None, bar_gap = None, group_gap = None,
        maximum = None, direction = None, bar_style = None, value_style = None, label_style = None,
        style = None, bar_set = None, block = None, width = None, height = None, x = 0, y = 0))]
    fn new(
        data: Option<&Bound<'_, PyAny>>,
        bar_width: Option<&Bound<'_, PyAny>>,
        bar_gap: Option<&Bound<'_, PyAny>>,
        group_gap: Option<&Bound<'_, PyAny>>,
        maximum: Option<&Bound<'_, PyAny>>,
        direction: Option<&Bound<'_, PyAny>>,
        bar_style: Option<&Bound<'_, PyAny>>,
        value_style: Option<&Bound<'_, PyAny>>,
        label_style: Option<&Bound<'_, PyAny>>,
        style: Option<&Bound<'_, PyAny>>,
        bar_set: Option<&Bound<'_, PyAny>>,
        block: Option<&Bound<'_, PyAny>>,
        width: Option<i32>,
        height: Option<i32>,
        x: i32,
        y: i32,
    ) -> PyResult<PyClassInitializer<Self>> {
        let mut spec = BarChartSpec::default();
        if let Some(data) = data.filter(|value| !value.is_none()) {
            spec.groups = groups_arg(data)?;
        }
        if let Some(value) = bar_width.filter(|value| !value.is_none()) {
            spec.bar_width = dynamic_unsigned(value, "the bar width")?;
        }
        if let Some(value) = bar_gap.filter(|value| !value.is_none()) {
            spec.bar_gap = dynamic_unsigned(value, "the bar gap")?;
        }
        if let Some(value) = group_gap.filter(|value| !value.is_none()) {
            spec.group_gap = dynamic_unsigned(value, "the group gap")?;
        }
        spec.maximum = maximum
            .filter(|value| !value.is_none())
            .map(|value| dynamic_unsigned(value, "the maximum"))
            .transpose()?;
        if let Some(value) = direction.filter(|value| !value.is_none()) {
            spec.direction = direction_arg(value)?;
        }
        spec.bar_style = style_spec_arg(bar_style)?;
        spec.value_style = style_spec_arg(value_style)?;
        spec.label_style = style_spec_arg(label_style)?;
        spec.style = style_spec_arg(style)?;
        if let Some(value) = bar_set.filter(|value| !value.is_none()) {
            spec.bar_set = bar_set_arg(value)?;
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
            (20, 5),
        )?;
        Ok(initializer.add_subclass(Self {
            spec: shared,
            block: std::sync::Mutex::new(owned_block),
        }))
    }

    /// The groups of bars. Setting accepts groups, or bars that form one group.
    #[getter]
    fn groups(slf: &Bound<'_, Self>) -> Vec<PyBarGroup> {
        slf.borrow()
            .spec
            .read()
            .groups
            .iter()
            .map(|data| PyBarGroup { data: data.clone() })
            .collect()
    }

    #[setter]
    fn set_groups(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let groups = groups_arg(value)?;
        Self::edit(slf, |spec| spec.groups = groups);
        Ok(())
    }

    /// Add a bar to the last group, dropping the oldest bars beyond ``maximum_bars``.
    #[pyo3(signature = (bar, *, maximum_bars = None))]
    fn append(
        slf: &Bound<'_, Self>,
        bar: &Bound<'_, PyAny>,
        maximum_bars: Option<usize>,
    ) -> PyResult<()> {
        let bar = bar_arg(bar)?;
        Self::edit(slf, |spec| {
            if spec.groups.is_empty() {
                spec.groups.push(BarGroupData {
                    label: None,
                    bars: Vec::new(),
                });
            }
            if let Some(group) = spec.groups.last_mut() {
                group.bars.push(bar);
                if let Some(maximum) = maximum_bars
                    && group.bars.len() > maximum
                {
                    group.bars.drain(..group.bars.len() - maximum);
                }
            }
        });
        Ok(())
    }

    /// Remove every group.
    fn clear(slf: &Bound<'_, Self>) {
        Self::edit(slf, |spec| spec.groups.clear());
    }

    #[getter]
    fn bar_width<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().bar_width.clone();
        dynamic_to_py(slf.py(), &value, |py, number| {
            Ok(number.into_pyobject(py)?.into_any())
        })
    }

    #[setter]
    fn set_bar_width(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let setting = dynamic_unsigned(value, "the bar width")?;
        Self::edit(slf, |spec| spec.bar_width = setting);
        Ok(())
    }
    #[getter]
    fn bar_gap<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().bar_gap.clone();
        dynamic_to_py(slf.py(), &value, |py, number| {
            Ok(number.into_pyobject(py)?.into_any())
        })
    }

    #[setter]
    fn set_bar_gap(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let setting = dynamic_unsigned(value, "the bar gap")?;
        Self::edit(slf, |spec| spec.bar_gap = setting);
        Ok(())
    }
    #[getter]
    fn group_gap<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().group_gap.clone();
        dynamic_to_py(slf.py(), &value, |py, number| {
            Ok(number.into_pyobject(py)?.into_any())
        })
    }

    #[setter]
    fn set_group_gap(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let setting = dynamic_unsigned(value, "the group gap")?;
        Self::edit(slf, |spec| spec.group_gap = setting);
        Ok(())
    }

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
    fn direction<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().direction.clone();
        text_to_py(slf.py(), &value)
    }

    #[setter]
    fn set_direction(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let direction = direction_arg(value)?;
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

    #[getter]
    fn bar_style(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let spec = slf.borrow().spec.read().bar_style.clone();
        style_spec_to_py(slf.py(), &spec)
    }

    #[setter]
    fn set_bar_style(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let style = style_spec_arg(value)?;
        Self::edit(slf, |spec| spec.bar_style = style);
        Ok(())
    }
    #[getter]
    fn value_style(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let spec = slf.borrow().spec.read().value_style.clone();
        style_spec_to_py(slf.py(), &spec)
    }

    #[setter]
    fn set_value_style(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let style = style_spec_arg(value)?;
        Self::edit(slf, |spec| spec.value_style = style);
        Ok(())
    }
    #[getter]
    fn label_style(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let spec = slf.borrow().spec.read().label_style.clone();
        style_spec_to_py(slf.py(), &spec)
    }

    #[setter]
    fn set_label_style(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let style = style_spec_arg(value)?;
        Self::edit(slf, |spec| spec.label_style = style);
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

    /// The ``Block`` framing the chart, or ``None``.
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
        let _ = PyTuple::empty(slf.py());
        format!(
            "BarChart(groups={}, width={}, height={})",
            slf.borrow().spec.read().groups.len(),
            frame.width.unwrap_or(0),
            frame.height.unwrap_or(0)
        )
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyBar>()?;
    m.add_class::<PyBarGroup>()?;
    m.add_class::<PyBarChart>()
}
