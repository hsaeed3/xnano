//! `Clear`: blank cells that hide whatever is behind them.

use std::sync::Arc;

use pyo3::prelude::*;
use xnano_terminal_runtime::painter::Spec;
use xnano_terminal_runtime::widgets::Shared;
use xnano_terminal_runtime::widgets::clear::ClearSpec;

use crate::widgets::style::{style_spec_arg, style_spec_to_py};
use crate::widgets::{Frame, PyWidget, dynamic_string, dynamic_to_py, repaint, widget_initializer};

fn symbol_setting(
    value: &Bound<'_, PyAny>,
) -> PyResult<xnano_terminal_runtime::dynamic::Dynamic<String>> {
    let setting = dynamic_string(value)?;
    if let xnano_terminal_runtime::dynamic::Dynamic::Fixed(symbol) = &setting
        && xnano_terminal_runtime::text::display_width(symbol) != 1
    {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "a clear symbol must be a single character one column wide, not \"{symbol}\"; use a space or a glyph such as \"·\""
        )));
    }
    Ok(setting)
}

#[pyclass(name = "Clear", module = "xnano._xnano_core", extends = PyWidget, subclass)]
pub struct PyClear {
    pub spec: Shared<ClearSpec>,
}

impl PyClear {
    fn edit(slf: &Bound<'_, Self>, change: impl FnOnce(&mut ClearSpec)) {
        slf.borrow().spec.edit(change);
        let core = Arc::clone(&slf.as_super().as_super().as_super().borrow().core);
        repaint(&core);
    }
}

#[pymethods]
impl PyClear {
    #[new]
    #[pyo3(signature = (*, symbol = None, style = None, width = None, height = None, x = 0, y = 0))]
    fn new(
        symbol: Option<&Bound<'_, PyAny>>,
        style: Option<&Bound<'_, PyAny>>,
        width: Option<i32>,
        height: Option<i32>,
        x: i32,
        y: i32,
    ) -> PyResult<PyClassInitializer<Self>> {
        let mut spec = ClearSpec::default();
        if let Some(symbol) = symbol.filter(|value| !value.is_none()) {
            spec.symbol = symbol_setting(symbol)?;
        }
        spec.style = style_spec_arg(style)?;
        let shared = Spec::new(spec);
        let initializer = widget_initializer(
            Arc::clone(&shared),
            Frame {
                width,
                height,
                x,
                y,
            },
            (10, 3),
        )?;
        Ok(initializer.add_subclass(Self { spec: shared }))
    }

    /// The one-column symbol every cell shows, a space by default.
    #[getter]
    fn symbol<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().symbol.clone();
        dynamic_to_py(slf.py(), &value, |py, symbol| {
            Ok(pyo3::types::PyString::new(py, symbol).into_any())
        })
    }

    #[setter]
    fn set_symbol(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let symbol = symbol_setting(value)?;
        Self::edit(slf, |spec| spec.symbol = symbol);
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

    /// A new clear widget with the same settings.
    fn copy(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let py = slf.py();
        let bounds = slf
            .as_super()
            .as_super()
            .as_super()
            .borrow()
            .core
            .lock()
            .bounds();
        let shared = Spec::new(slf.borrow().spec.read().clone());
        let initializer = widget_initializer(
            Arc::clone(&shared),
            Frame {
                width: Some(bounds.width),
                height: Some(bounds.height),
                x: bounds.x,
                y: bounds.y,
            },
            (10, 3),
        )?;
        Ok(Py::new(py, initializer.add_subclass(Self { spec: shared }))?.into_any())
    }

    fn __copy__(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        Self::copy(slf)
    }

    fn __deepcopy__(slf: &Bound<'_, Self>, _memo: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        Self::copy(slf)
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
        format!("Clear(width={}, height={})", state.width, state.height)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyClear>()
}
