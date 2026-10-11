//! `Block`: borders, titles and padding, as a widget and as a frame for other widgets.

use std::sync::Arc;

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyTuple;
use xnano_terminal_runtime::dynamic::Dynamic;
use xnano_terminal_runtime::painter::Spec;
use xnano_terminal_runtime::widgets::Shared;
use xnano_terminal_runtime::widgets::block::{
    BORDER_SIDES, BORDER_TYPES, BlockSpec, MERGE_STRATEGIES, TitleSpec, alignment_from_name,
    border_type_from_name,
};

use crate::surface::PySurface;
use crate::widgets::style::{style_spec_arg, style_spec_to_py};
use crate::widgets::{
    Frame, PyWidget, dynamic_string, dynamic_to_py, dynamic_u16, repaint, widget_initializer,
};

/// One title of a block.
#[pyclass(
    name = "BlockTitle",
    module = "xnano._xnano_core",
    frozen,
    from_py_object
)]
#[derive(Clone)]
pub struct PyBlockTitle {
    pub spec: TitleSpec,
}

fn alignment_name(alignment: ratatui_core::layout::Alignment) -> &'static str {
    match alignment {
        ratatui_core::layout::Alignment::Left => "left",
        ratatui_core::layout::Alignment::Center => "center",
        ratatui_core::layout::Alignment::Right => "right",
    }
}

fn alignment_arg(name: &str) -> PyResult<ratatui_core::layout::Alignment> {
    alignment_from_name(name).ok_or_else(|| {
        PyValueError::new_err(format!(
            "\"{name}\" is not an alignment; use \"left\", \"center\" or \"right\""
        ))
    })
}

#[pymethods]
impl PyBlockTitle {
    #[new]
    #[pyo3(signature = (text, *, position = "top", alignment = None, style = None))]
    fn new(
        text: &Bound<'_, PyAny>,
        position: &str,
        alignment: Option<&str>,
        style: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Self> {
        let is_bottom = match position {
            "top" => false,
            "bottom" => true,
            other => {
                return Err(PyValueError::new_err(format!(
                    "\"{other}\" is not a title position; use \"top\" or \"bottom\""
                )));
            }
        };
        Ok(Self {
            spec: TitleSpec {
                text: dynamic_string(text)?,
                is_bottom,
                alignment: alignment.map(alignment_arg).transpose()?,
                style: style_spec_arg(style)?,
            },
        })
    }

    #[getter]
    fn text<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        dynamic_to_py(py, &self.spec.text, |py, text| {
            Ok(pyo3::types::PyString::new(py, text).into_any())
        })
    }

    #[getter]
    fn position(&self) -> &'static str {
        if self.spec.is_bottom { "bottom" } else { "top" }
    }

    #[getter]
    fn alignment(&self) -> Option<&'static str> {
        self.spec.alignment.map(alignment_name)
    }

    #[getter]
    fn style(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        style_spec_to_py(py, &self.spec.style)
    }
}

/// The widget that frames content, and the frame other widgets take as ``block=``.
#[pyclass(name = "Block", module = "xnano._xnano_core", extends = PyWidget, subclass)]
pub struct PyBlock {
    pub spec: Shared<BlockSpec>,
}

/// The settings of a ``Block`` passed as a widget's ``block=`` argument.
pub fn block_arg(value: Option<&Bound<'_, PyAny>>) -> PyResult<Option<Shared<BlockSpec>>> {
    match value {
        None => Ok(None),
        Some(value) if value.is_none() => Ok(None),
        Some(value) => value
            .cast::<PyBlock>()
            .map(|block| Some(Arc::clone(&block.borrow().spec)))
            .map_err(|_| PyTypeError::new_err("block takes a Block or None")),
    }
}

fn sides_arg(value: &Bound<'_, PyAny>) -> PyResult<Vec<String>> {
    if let Ok(text) = value.extract::<String>() {
        return match text.as_str() {
            "all" => Ok(BORDER_SIDES
                .iter()
                .map(|(name, _)| (*name).to_owned())
                .collect()),
            "none" => Ok(Vec::new()),
            name if BORDER_SIDES.iter().any(|(side, _)| *side == name) => Ok(vec![text]),
            other => Err(side_error(other)),
        };
    }
    let mut sides = Vec::new();
    for item in value.try_iter()? {
        let name: String = item?.extract()?;
        if !BORDER_SIDES.iter().any(|(side, _)| *side == name) {
            return Err(side_error(&name));
        }
        if !sides.contains(&name) {
            sides.push(name);
        }
    }
    Ok(sides)
}

fn side_error(name: &str) -> PyErr {
    PyValueError::new_err(format!(
        "\"{name}\" is not a border side; use \"top\", \"right\", \"bottom\", \"left\", \"all\" or \"none\""
    ))
}

fn padding_arg(value: &Bound<'_, PyAny>) -> PyResult<[Dynamic<u16>; 4]> {
    if let Ok(items) = value.cast::<PyTuple>() {
        if items.len() != 4 {
            return Err(PyValueError::new_err(
                "padding takes one number or four: (left, right, top, bottom)",
            ));
        }
        return Ok([
            dynamic_u16(&items.get_item(0)?)?,
            dynamic_u16(&items.get_item(1)?)?,
            dynamic_u16(&items.get_item(2)?)?,
            dynamic_u16(&items.get_item(3)?)?,
        ]);
    }
    let all = dynamic_u16(value)?;
    Ok([all.clone(), all.clone(), all.clone(), all])
}

fn title_arg(value: &Bound<'_, PyAny>) -> PyResult<TitleSpec> {
    if let Ok(title) = value.extract::<PyBlockTitle>() {
        return Ok(title.spec);
    }
    Ok(TitleSpec {
        text: dynamic_string(value)?,
        is_bottom: false,
        alignment: None,
        style: xnano_terminal_runtime::widgets::style::StyleSpec::default(),
    })
}

fn border_type_arg(value: &Bound<'_, PyAny>) -> PyResult<Dynamic<String>> {
    let setting = dynamic_string(value)?;
    if let Dynamic::Fixed(name) = &setting
        && border_type_from_name(name).is_none()
    {
        return Err(PyValueError::new_err(format!(
            "\"{name}\" is not a border type; use one of {}",
            BORDER_TYPES
                .iter()
                .map(|(name, _)| *name)
                .collect::<Vec<_>>()
                .join(", ")
        )));
    }
    Ok(setting)
}

fn merge_arg(value: Option<&str>) -> PyResult<Option<String>> {
    match value {
        None => Ok(None),
        Some(name)
            if MERGE_STRATEGIES
                .iter()
                .any(|(candidate, _)| *candidate == name) =>
        {
            Ok(Some(name.to_owned()))
        }
        Some(name) => Err(PyValueError::new_err(format!(
            "\"{name}\" is not a merge strategy; use \"replace\", \"exact\" or \"fuzzy\""
        ))),
    }
}

impl PyBlock {
    fn edit<R>(slf: &Bound<'_, Self>, change: impl FnOnce(&mut BlockSpec) -> R) -> R {
        let result = slf.borrow().spec.edit(change);
        let core = Arc::clone(&slf.as_super().as_super().as_super().borrow().core);
        repaint(&core);
        result
    }
}

#[pymethods]
impl PyBlock {
    #[new]
    #[pyo3(signature = (title = None, *, borders = None, border_type = None, border_style = None,
        style = None, title_style = None, title_alignment = "left", padding = None, merge = None,
        width = None, height = None, x = 0, y = 0))]
    fn new(
        title: Option<&Bound<'_, PyAny>>,
        borders: Option<&Bound<'_, PyAny>>,
        border_type: Option<&Bound<'_, PyAny>>,
        border_style: Option<&Bound<'_, PyAny>>,
        style: Option<&Bound<'_, PyAny>>,
        title_style: Option<&Bound<'_, PyAny>>,
        title_alignment: &str,
        padding: Option<&Bound<'_, PyAny>>,
        merge: Option<&str>,
        width: Option<i32>,
        height: Option<i32>,
        x: i32,
        y: i32,
    ) -> PyResult<PyClassInitializer<Self>> {
        let mut spec = BlockSpec::default();
        if let Some(borders) = borders.filter(|value| !value.is_none()) {
            spec.sides = sides_arg(borders)?;
        }
        if let Some(kind) = border_type.filter(|value| !value.is_none()) {
            spec.border_type = border_type_arg(kind)?;
        }
        spec.border_style = style_spec_arg(border_style)?;
        spec.style = style_spec_arg(style)?;
        spec.title_style = style_spec_arg(title_style)?;
        spec.title_alignment = alignment_arg(title_alignment)?;
        if let Some(padding) = padding.filter(|value| !value.is_none()) {
            spec.padding = padding_arg(padding)?;
        }
        spec.merge_strategy = merge_arg(merge)?;
        if let Some(title) = title.filter(|value| !value.is_none()) {
            spec.titles.push(title_arg(title)?);
        }
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

    /// The sides that draw a border.
    #[getter]
    fn borders(slf: &Bound<'_, Self>) -> Vec<String> {
        slf.borrow().spec.read().sides.clone()
    }

    #[setter]
    fn set_borders(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let sides = sides_arg(value)?;
        Self::edit(slf, |spec| spec.sides = sides);
        Ok(())
    }

    #[getter]
    fn border_type<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().border_type.clone();
        dynamic_to_py(slf.py(), &value, |py, name| {
            Ok(pyo3::types::PyString::new(py, name).into_any())
        })
    }

    #[setter]
    fn set_border_type(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let setting = border_type_arg(value)?;
        Self::edit(slf, |spec| spec.border_type = setting);
        Ok(())
    }

    #[getter]
    fn border_style(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let spec = slf.borrow().spec.read().border_style.clone();
        style_spec_to_py(slf.py(), &spec)
    }

    #[setter]
    fn set_border_style(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let style = style_spec_arg(value)?;
        Self::edit(slf, |spec| spec.border_style = style);
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
    fn title_style(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let spec = slf.borrow().spec.read().title_style.clone();
        style_spec_to_py(slf.py(), &spec)
    }

    #[setter]
    fn set_title_style(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let style = style_spec_arg(value)?;
        Self::edit(slf, |spec| spec.title_style = style);
        Ok(())
    }

    #[getter]
    fn title_alignment(slf: &Bound<'_, Self>) -> &'static str {
        alignment_name(slf.borrow().spec.read().title_alignment)
    }

    #[setter]
    fn set_title_alignment(slf: &Bound<'_, Self>, value: &str) -> PyResult<()> {
        let alignment = alignment_arg(value)?;
        Self::edit(slf, |spec| spec.title_alignment = alignment);
        Ok(())
    }

    /// The titles, top and bottom.
    #[getter]
    fn titles(slf: &Bound<'_, Self>) -> Vec<PyBlockTitle> {
        slf.borrow()
            .spec
            .read()
            .titles
            .iter()
            .map(|spec| PyBlockTitle { spec: spec.clone() })
            .collect()
    }

    #[setter]
    fn set_titles(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let mut titles = Vec::new();
        for item in value.try_iter()? {
            titles.push(title_arg(&item?)?);
        }
        Self::edit(slf, |spec| spec.titles = titles);
        Ok(())
    }

    #[getter]
    fn padding<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyTuple>> {
        let py = slf.py();
        let padding = slf.borrow().spec.read().padding.clone();
        let items = padding
            .iter()
            .map(|side| {
                dynamic_to_py(py, side, |py, value| {
                    Ok(value.into_pyobject(py)?.into_any())
                })
            })
            .collect::<PyResult<Vec<_>>>()?;
        PyTuple::new(py, items)
    }

    #[setter]
    fn set_padding(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let padding = padding_arg(value)?;
        Self::edit(slf, |spec| spec.padding = padding);
        Ok(())
    }

    #[getter]
    fn merge(slf: &Bound<'_, Self>) -> Option<String> {
        slf.borrow().spec.read().merge_strategy.clone()
    }

    #[setter]
    fn set_merge(slf: &Bound<'_, Self>, value: Option<&str>) -> PyResult<()> {
        let strategy = merge_arg(value)?;
        Self::edit(slf, |spec| spec.merge_strategy = strategy);
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
        format!("Block(width={}, height={})", state.width, state.height)
    }
}

// Keep the surface type reachable for repr helpers above.
#[allow(dead_code)]
type SurfaceMarker = PySurface;

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyBlockTitle>()?;
    m.add_class::<PyBlock>()
}
