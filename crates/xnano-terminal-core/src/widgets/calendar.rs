//! A retained monthly calendar with editable dates and event styles.
use crate::widgets::block::block_arg;
use crate::widgets::canvas::present;
use crate::widgets::style::{style_spec_arg, style_spec_to_py};
use crate::widgets::{Frame, PyWidget, dynamic_arg, dynamic_to_py, repaint, widget_initializer};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyTuple};
use std::sync::Arc;
use xnano_terminal_runtime::dynamic::Dynamic;
use xnano_terminal_runtime::painter::Spec;
use xnano_terminal_runtime::widgets::Shared;
use xnano_terminal_runtime::widgets::calendar::{CalendarSpec, make_date};

#[pyclass(name = "Calendar", module = "xnano_core._xnano_core", extends = PyWidget, subclass)]
pub struct PyCalendar {
    spec: Shared<CalendarSpec>,
    block: Option<Py<PyAny>>,
}
impl PyCalendar {
    fn edit(slf: &Bound<'_, Self>, change: impl FnOnce(&mut CalendarSpec)) {
        slf.borrow().spec.edit(change);
        repaint(&slf.as_super().as_super().as_super().borrow().core);
    }
}
#[pymethods]
impl PyCalendar {
    #[new]
    #[pyo3(signature = (year, month, day = None, *, events = None, style = None, surrounding_style = None, weekdays_header_style = None, month_header_style = None, block = None, width = None, height = None, x = 0, y = 0))]
    fn new(
        year: &Bound<'_, PyAny>,
        month: &Bound<'_, PyAny>,
        day: Option<&Bound<'_, PyAny>>,
        events: Option<&Bound<'_, PyDict>>,
        style: Option<&Bound<'_, PyAny>>,
        surrounding_style: Option<&Bound<'_, PyAny>>,
        weekdays_header_style: Option<&Bound<'_, PyAny>>,
        month_header_style: Option<&Bound<'_, PyAny>>,
        block: Option<&Bound<'_, PyAny>>,
        width: Option<i32>,
        height: Option<i32>,
        x: i32,
        y: i32,
    ) -> PyResult<PyClassInitializer<Self>> {
        let spec = CalendarSpec {
            year: dynamic_arg(year, |value| value.extract())?,
            month: dynamic_arg(month, |value| value.extract())?,
            day: present(day)
                .map(|value| dynamic_arg(value, |value| value.extract()))
                .transpose()?
                .unwrap_or(Dynamic::Fixed(1)),
            events: events.map(event_styles).transpose()?.unwrap_or_default(),
            default_style: style_spec_arg(style)?,
            surrounding_style: present(surrounding_style)
                .map(|value| style_spec_arg(Some(value)))
                .transpose()?,
            weekdays_header_style: present(weekdays_header_style)
                .map(|value| style_spec_arg(Some(value)))
                .transpose()?,
            month_header_style: present(month_header_style)
                .map(|value| style_spec_arg(Some(value)))
                .transpose()?,
            block: block_arg(block)?,
        };
        if let (Dynamic::Fixed(year), Dynamic::Fixed(month), Dynamic::Fixed(day)) =
            (&spec.year, &spec.month, &spec.day)
        {
            make_date(*year, *month, *day).map_err(pyo3::exceptions::PyValueError::new_err)?;
        }
        let spec = Spec::new(spec);
        let initializer = widget_initializer(
            Arc::clone(&spec),
            Frame {
                width,
                height,
                x,
                y,
            },
            (22, 8),
        )?;
        Ok(initializer.add_subclass(Self {
            spec,
            block: present(block).map(|value| value.clone().unbind()),
        }))
    }
    #[getter]
    fn year<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        dynamic_to_py(py, &self.spec.read().year, |py, value| {
            Ok(value.into_pyobject(py)?.into_any())
        })
    }
    #[setter]
    fn set_year(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let setting: Dynamic<i32> = dynamic_arg(value, |value| value.extract())?;
        Self::edit(slf, |spec| spec.year = setting);
        Ok(())
    }
    #[getter]
    fn month<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        dynamic_to_py(py, &self.spec.read().month, |py, value| {
            Ok(value.into_pyobject(py)?.into_any())
        })
    }
    #[setter]
    fn set_month(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let setting: Dynamic<u8> = dynamic_arg(value, |value| value.extract())?;
        Self::edit(slf, |spec| spec.month = setting);
        Ok(())
    }
    #[getter]
    fn day<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        dynamic_to_py(py, &self.spec.read().day, |py, value| {
            Ok(value.into_pyobject(py)?.into_any())
        })
    }
    #[setter]
    fn set_day(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let setting: Dynamic<u8> = dynamic_arg(value, |value| value.extract())?;
        Self::edit(slf, |spec| spec.day = setting);
        Ok(())
    }
    #[getter]
    fn style(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        style_spec_to_py(py, &self.spec.read().default_style)
    }
    #[setter]
    fn set_style(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let setting = style_spec_arg(value)?;
        Self::edit(slf, |spec| spec.default_style = setting);
        Ok(())
    }
    #[getter]
    fn surrounding_style(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        self.spec
            .read()
            .surrounding_style
            .as_ref()
            .map(|style| style_spec_to_py(py, style))
            .transpose()
            .map(|style| style.unwrap_or_else(|| py.None()))
    }
    #[setter]
    fn set_surrounding_style(
        slf: &Bound<'_, Self>,
        value: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<()> {
        let setting = present(value)
            .map(|value| style_spec_arg(Some(value)))
            .transpose()?;
        Self::edit(slf, |spec| spec.surrounding_style = setting);
        Ok(())
    }
    #[getter]
    fn weekdays_header_style(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        self.spec
            .read()
            .weekdays_header_style
            .as_ref()
            .map(|style| style_spec_to_py(py, style))
            .transpose()
            .map(|style| style.unwrap_or_else(|| py.None()))
    }
    #[setter]
    fn set_weekdays_header_style(
        slf: &Bound<'_, Self>,
        value: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<()> {
        let setting = present(value)
            .map(|value| style_spec_arg(Some(value)))
            .transpose()?;
        Self::edit(slf, |spec| spec.weekdays_header_style = setting);
        Ok(())
    }
    #[getter]
    fn month_header_style(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        self.spec
            .read()
            .month_header_style
            .as_ref()
            .map(|style| style_spec_to_py(py, style))
            .transpose()
            .map(|style| style.unwrap_or_else(|| py.None()))
    }
    #[setter]
    fn set_month_header_style(
        slf: &Bound<'_, Self>,
        value: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<()> {
        let setting = present(value)
            .map(|value| style_spec_arg(Some(value)))
            .transpose()?;
        Self::edit(slf, |spec| spec.month_header_style = setting);
        Ok(())
    }
    #[getter]
    fn events<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let result = PyDict::new(py);
        for (date, style) in &self.spec.read().events {
            result.set_item(date, style_spec_to_py(py, style)?)?;
        }
        Ok(result)
    }
    #[setter]
    fn set_events(slf: &Bound<'_, Self>, value: &Bound<'_, PyDict>) -> PyResult<()> {
        let events = event_styles(value)?;
        Self::edit(slf, |spec| spec.events = events);
        Ok(())
    }
    #[getter]
    fn block(&self, py: Python<'_>) -> Option<Py<PyAny>> {
        self.block.as_ref().map(|block| block.clone_ref(py))
    }
    #[setter]
    fn set_block(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let block = block_arg(value)?;
        slf.borrow().spec.edit(|spec| spec.block = block);
        slf.borrow_mut().block = present(value).map(|value| value.clone().unbind());
        repaint(&slf.as_super().as_super().as_super().borrow().core);
        Ok(())
    }
    fn copy(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let core = Arc::clone(&slf.as_super().as_super().as_super().borrow().core);
        let bounds = core.lock().bounds();
        let spec = Spec::new(slf.borrow().spec.read().clone());
        let initializer = widget_initializer(
            Arc::clone(&spec),
            Frame {
                width: Some(bounds.width),
                height: Some(bounds.height),
                x: bounds.x,
                y: bounds.y,
            },
            (22, 8),
        )?;
        Ok(Py::new(
            slf.py(),
            initializer.add_subclass(Self {
                spec,
                block: slf
                    .borrow()
                    .block
                    .as_ref()
                    .map(|block| block.clone_ref(slf.py())),
            }),
        )?
        .into_any())
    }
    fn __copy__(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        Self::copy(slf)
    }
    fn __deepcopy__(slf: &Bound<'_, Self>, _memo: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        Self::copy(slf)
    }
    fn __repr__(&self) -> String {
        {
            let spec = self.spec.read();
            format!(
                "Calendar(year={:?}, month={:?}, day={:?})",
                spec.year, spec.month, spec.day
            )
        }
    }
}
fn event_styles(
    value: &Bound<'_, PyDict>,
) -> PyResult<
    Vec<(
        xnano_terminal_runtime::widgets::calendar::DateParts,
        xnano_terminal_runtime::widgets::style::StyleSpec,
    )>,
> {
    value
        .iter()
        .map(|(date, style)| {
            let parts: (i32, u8, u8) = date.cast::<PyTuple>()?.extract()?;
            make_date(parts.0, parts.1, parts.2)
                .map_err(pyo3::exceptions::PyValueError::new_err)?;
            Ok((parts, style_spec_arg(Some(&style))?))
        })
        .collect()
}
pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<PyCalendar>()
}
