//! `Paragraph`: styled text that can wrap, align and scroll.

use std::sync::{Arc, Mutex};

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use xnano_terminal_runtime::dynamic::Dynamic;
use xnano_terminal_runtime::painter::Spec;
use xnano_terminal_runtime::widgets::Resolver;
use xnano_terminal_runtime::widgets::Shared;
use xnano_terminal_runtime::widgets::block::alignment_from_name;
use xnano_terminal_runtime::widgets::paragraph::{ParagraphSpec, TextSetting};

use crate::convert::text_lines;
use crate::errors::eval_error;
use crate::expressions::{ExpressionKind, PyExpression};
use crate::shared::lock;
use crate::widgets::block::block_arg;
use crate::widgets::style::{style_spec_arg, style_spec_to_py};
use crate::widgets::{
    Frame, PyWidget, dynamic_bool, dynamic_string, dynamic_to_py, dynamic_u16, environment_of,
    repaint, widget_initializer,
};

#[pyclass(name = "Paragraph", module = "xnano_core._xnano_core", extends = PyWidget, subclass)]
pub struct PyParagraph {
    spec: Shared<ParagraphSpec>,
    /// The text as the user gave it, so the getter returns what was set.
    source: Mutex<Py<PyAny>>,
    block: Mutex<Option<Py<PyAny>>>,
}

fn text_setting(value: &Bound<'_, PyAny>) -> PyResult<TextSetting> {
    if let Ok(expression) = value.extract::<PyRef<'_, PyExpression>>() {
        return match &expression.kind {
            ExpressionKind::Value(expr) => Ok(TextSetting::Bound(Arc::clone(expr))),
            _ => Err(pyo3::exceptions::PyTypeError::new_err(
                "an operation cannot be used as text; bind a value or condition instead",
            )),
        };
    }
    Ok(TextSetting::Fixed(text_lines(value)?))
}

fn alignment_setting(value: &Bound<'_, PyAny>) -> PyResult<Dynamic<String>> {
    let setting = dynamic_string(value)?;
    if let Dynamic::Fixed(name) = &setting
        && alignment_from_name(name).is_none()
    {
        return Err(PyValueError::new_err(format!(
            "\"{name}\" is not an alignment; use \"left\", \"center\" or \"right\""
        )));
    }
    Ok(setting)
}

impl PyParagraph {
    fn edit(slf: &Bound<'_, Self>, change: impl FnOnce(&mut ParagraphSpec)) {
        slf.borrow().spec.edit(change);
        let core = Arc::clone(&slf.as_super().as_super().as_super().borrow().core);
        repaint(&core);
    }
}

#[pymethods]
impl PyParagraph {
    #[new]
    #[pyo3(signature = (text = None, *, style = None, alignment = None, should_wrap = None,
        should_trim = None, scroll = None, block = None, width = None, height = None, x = 0, y = 0))]
    fn new(
        py: Python<'_>,
        text: Option<&Bound<'_, PyAny>>,
        style: Option<&Bound<'_, PyAny>>,
        alignment: Option<&Bound<'_, PyAny>>,
        should_wrap: Option<&Bound<'_, PyAny>>,
        should_trim: Option<&Bound<'_, PyAny>>,
        scroll: Option<(Bound<'_, PyAny>, Bound<'_, PyAny>)>,
        block: Option<&Bound<'_, PyAny>>,
        width: Option<i32>,
        height: Option<i32>,
        x: i32,
        y: i32,
    ) -> PyResult<PyClassInitializer<Self>> {
        let source = match text.filter(|value| !value.is_none()) {
            Some(text) => text.clone().unbind(),
            None => pyo3::types::PyString::new(py, "").into_any().unbind(),
        };
        let mut spec = ParagraphSpec::new(text_setting(source.bind(py))?);
        spec.style = style_spec_arg(style)?;
        if let Some(alignment) = alignment.filter(|value| !value.is_none()) {
            spec.alignment = alignment_setting(alignment)?;
        }
        if let Some(flag) = should_wrap.filter(|value| !value.is_none()) {
            spec.should_wrap = dynamic_bool(flag)?;
        }
        if let Some(flag) = should_trim.filter(|value| !value.is_none()) {
            spec.should_trim = dynamic_bool(flag)?;
        }
        if let Some((row, column)) = scroll {
            spec.scroll_row = dynamic_u16(&row)?;
            spec.scroll_column = dynamic_u16(&column)?;
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
            (20, 3),
        )?;
        Ok(initializer.add_subclass(Self {
            spec: shared,
            source: Mutex::new(source),
            block: Mutex::new(owned_block),
        }))
    }

    /// The text, as it was set: a ``str``, a ``StyledText``, a sequence of those or an expression.
    #[getter]
    fn text(slf: &Bound<'_, Self>) -> Py<PyAny> {
        lock(&slf.borrow().source).clone_ref(slf.py())
    }

    #[setter]
    fn set_text(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let setting = text_setting(value)?;
        *lock(&slf.borrow().source) = value.clone().unbind();
        Self::edit(slf, |spec| spec.text = setting);
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
    fn alignment<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().alignment.clone();
        dynamic_to_py(slf.py(), &value, |py, name| {
            Ok(pyo3::types::PyString::new(py, name).into_any())
        })
    }

    #[setter]
    fn set_alignment(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let alignment = alignment_setting(value)?;
        Self::edit(slf, |spec| spec.alignment = alignment);
        Ok(())
    }

    #[getter]
    fn should_wrap<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().should_wrap.clone();
        dynamic_to_py(slf.py(), &value, |py, flag| {
            Ok(pyo3::types::PyBool::new(py, *flag).to_owned().into_any())
        })
    }

    #[setter]
    fn set_should_wrap(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let flag = dynamic_bool(value)?;
        Self::edit(slf, |spec| spec.should_wrap = flag);
        Ok(())
    }

    #[getter]
    fn should_trim<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().should_trim.clone();
        dynamic_to_py(slf.py(), &value, |py, flag| {
            Ok(pyo3::types::PyBool::new(py, *flag).to_owned().into_any())
        })
    }

    #[setter]
    fn set_should_trim(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let flag = dynamic_bool(value)?;
        Self::edit(slf, |spec| spec.should_trim = flag);
        Ok(())
    }

    /// The first row shown, counted in displayed rows.
    #[getter]
    fn scroll_row<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().scroll_row.clone();
        dynamic_to_py(slf.py(), &value, |py, row| {
            Ok(row.into_pyobject(py)?.into_any())
        })
    }

    #[setter]
    fn set_scroll_row(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let row = dynamic_u16(value)?;
        Self::edit(slf, |spec| spec.scroll_row = row);
        Ok(())
    }

    /// The first column shown.
    #[getter]
    fn scroll_column<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().scroll_column.clone();
        dynamic_to_py(slf.py(), &value, |py, column| {
            Ok(column.into_pyobject(py)?.into_any())
        })
    }

    #[setter]
    fn set_scroll_column(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let column = dynamic_u16(value)?;
        Self::edit(slf, |spec| spec.scroll_column = column);
        Ok(())
    }

    /// The ``Block`` framing the paragraph, or ``None``.
    #[getter]
    fn block(slf: &Bound<'_, Self>) -> Option<Py<PyAny>> {
        lock(&slf.borrow().block)
            .as_ref()
            .map(|block| block.clone_ref(slf.py()))
    }

    #[setter]
    fn set_block(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let shared = block_arg(value)?;
        *lock(&slf.borrow().block) = value
            .filter(|value| !value.is_none())
            .map(|value| value.clone().unbind());
        Self::edit(slf, |spec| spec.block = shared);
        Ok(())
    }

    /// How many rows the text takes when drawn ``width`` columns wide.
    ///
    /// ``width`` defaults to the widget's own width.
    #[pyo3(signature = (width = None))]
    fn line_count(slf: &Bound<'_, Self>, width: Option<u16>) -> PyResult<usize> {
        let core = Arc::clone(&slf.as_super().as_super().as_super().borrow().core);
        let width = width.unwrap_or_else(|| core.lock().grid.width());
        let environment = environment_of(&core);
        let mut resolver = Resolver::new(environment.as_ref());
        let resolved = slf
            .borrow()
            .spec
            .read()
            .resolve_now(&mut resolver)
            .map_err(|error| eval_error(&error))?;
        Ok(resolved.line_count(width))
    }

    /// The width in columns of the widest row of text.
    fn line_width(slf: &Bound<'_, Self>) -> PyResult<usize> {
        let core = Arc::clone(&slf.as_super().as_super().as_super().borrow().core);
        let environment = environment_of(&core);
        let mut resolver = Resolver::new(environment.as_ref());
        let resolved = slf
            .borrow()
            .spec
            .read()
            .resolve_now(&mut resolver)
            .map_err(|error| eval_error(&error))?;
        Ok(resolved.line_width())
    }

    /// A new paragraph with the same settings. A shared ``Block`` stays shared.
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
        let this = slf.borrow();
        let spec = this.spec.read().clone();
        let shared = Spec::new(spec);
        let initializer = widget_initializer(
            Arc::clone(&shared),
            Frame {
                width: Some(bounds.width),
                height: Some(bounds.height),
                x: bounds.x,
                y: bounds.y,
            },
            (20, 3),
        )?;
        Ok(Py::new(
            py,
            initializer.add_subclass(Self {
                spec: shared,
                source: Mutex::new(lock(&this.source).clone_ref(py)),
                block: Mutex::new(lock(&this.block).as_ref().map(|block| block.clone_ref(py))),
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

    fn __repr__(slf: &Bound<'_, Self>) -> String {
        let state = slf
            .as_super()
            .as_super()
            .as_super()
            .borrow()
            .core
            .lock()
            .bounds();
        format!("Paragraph(width={}, height={})", state.width, state.height)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyParagraph>()
}
