//! `Scrollbar`: a track with a thumb that shows a scroll position.

use std::sync::Arc;

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use xnano_terminal_runtime::dynamic::Dynamic;
use xnano_terminal_runtime::painter::Spec;
use xnano_terminal_runtime::widgets::Shared;
use xnano_terminal_runtime::widgets::scrollbar::{
    ScrollbarSpec, default_symbols, matching_preset, orientation_from_name, orientation_names,
    symbol_preset_from_name, symbol_preset_names,
};

use crate::widgets::line_gauge::{
    core_of, dynamic_unsigned, frame_of, optional_text_arg, optional_text_to_py, resolve_now,
    text_to_py,
};
use crate::widgets::style::{style_spec_arg, style_spec_to_py};
use crate::widgets::{
    Frame, PyWidget, dynamic_bool, dynamic_string, dynamic_to_py, repaint, widget_initializer,
};

fn orientation_arg(value: &Bound<'_, PyAny>) -> PyResult<Dynamic<String>> {
    let setting = dynamic_string(value)?;
    if let Dynamic::Fixed(name) = &setting
        && orientation_from_name(name).is_none()
    {
        return Err(PyValueError::new_err(format!(
            "\"{name}\" is not a scrollbar orientation; use one of {}",
            orientation_names()
        )));
    }
    Ok(setting)
}

#[pyclass(name = "Scrollbar", module = "xnano_core._xnano_core", extends = PyWidget, subclass)]
pub struct PyScrollbar {
    spec: Shared<ScrollbarSpec>,
}

impl PyScrollbar {
    fn edit<R>(slf: &Bound<'_, Self>, change: impl FnOnce(&mut ScrollbarSpec) -> R) -> R {
        let result = slf.borrow().spec.edit(change);
        repaint(&core_of(slf.as_any()));
        result
    }

    fn duplicate(slf: &Bound<'_, Self>) -> PyResult<Py<Self>> {
        let py = slf.py();
        let spec = Spec::new(slf.borrow().spec.read().clone());
        let initializer = widget_initializer(Arc::clone(&spec), frame_of(slf.as_any()), (1, 10))?;
        Py::new(py, initializer.add_subclass(Self { spec }))
    }

    /// The position and content length now, for the movement helpers.
    fn reading(slf: &Bound<'_, Self>) -> PyResult<(usize, usize)> {
        let (position, length) = {
            let spec = slf.borrow().spec.read().clone();
            (spec.position, spec.content_length)
        };
        let Dynamic::Fixed(position) = position else {
            return Err(PyTypeError::new_err(
                "the position follows an expression, so it cannot be moved; assign a plain number to position first",
            ));
        };
        Ok((position, resolve_now(&core_of(slf.as_any()), &length)?))
    }

    fn move_to(slf: &Bound<'_, Self>, position: usize) {
        Self::edit(slf, |spec| spec.position = Dynamic::Fixed(position));
    }
}

#[pymethods]
impl PyScrollbar {
    #[new]
    #[pyo3(signature = (content_length = None, position = None, *, orientation = None,
        viewport_content_length = None, symbols = None, thumb_symbol = None, track_symbol = None,
        begin_symbol = None, end_symbol = None, has_track = true, has_begin = true, has_end = true,
        style = None, thumb_style = None, track_style = None, begin_style = None, end_style = None,
        is_transparent = None, width = None, height = None, x = 0, y = 0))]
    fn new(
        content_length: Option<&Bound<'_, PyAny>>,
        position: Option<&Bound<'_, PyAny>>,
        orientation: Option<&Bound<'_, PyAny>>,
        viewport_content_length: Option<&Bound<'_, PyAny>>,
        symbols: Option<&str>,
        thumb_symbol: Option<&Bound<'_, PyAny>>,
        track_symbol: Option<&Bound<'_, PyAny>>,
        begin_symbol: Option<&Bound<'_, PyAny>>,
        end_symbol: Option<&Bound<'_, PyAny>>,
        has_track: bool,
        has_begin: bool,
        has_end: bool,
        style: Option<&Bound<'_, PyAny>>,
        thumb_style: Option<&Bound<'_, PyAny>>,
        track_style: Option<&Bound<'_, PyAny>>,
        begin_style: Option<&Bound<'_, PyAny>>,
        end_style: Option<&Bound<'_, PyAny>>,
        is_transparent: Option<&Bound<'_, PyAny>>,
        width: Option<i32>,
        height: Option<i32>,
        x: i32,
        y: i32,
    ) -> PyResult<PyClassInitializer<Self>> {
        let orientation_name = match orientation.filter(|value| !value.is_none()) {
            Some(value) => orientation_arg(value)?,
            None => Dynamic::Fixed("vertical_right".to_owned()),
        };
        let base_name = orientation_name
            .fixed()
            .cloned()
            .unwrap_or_else(|| "vertical_right".to_owned());
        let mut spec = ScrollbarSpec::new(&base_name);
        spec.orientation = orientation_name;
        if let Some(value) = content_length.filter(|value| !value.is_none()) {
            spec.content_length = dynamic_unsigned(value, "the content length")?;
        }
        if let Some(value) = position.filter(|value| !value.is_none()) {
            spec.position = dynamic_unsigned(value, "the position")?;
        }
        spec.viewport_content_length = viewport_content_length
            .filter(|value| !value.is_none())
            .map(|value| dynamic_unsigned(value, "the viewport content length"))
            .transpose()?;
        if let Some(name) = symbols {
            let set = symbol_preset_from_name(name).ok_or_else(|| {
                PyValueError::new_err(format!(
                    "\"{name}\" is not a symbol preset; use one of {}",
                    symbol_preset_names()
                ))
            })?;
            spec.thumb_symbol = Dynamic::Fixed(set.thumb.to_owned());
            spec.track_symbol = Some(Dynamic::Fixed(set.track.to_owned()));
            spec.begin_symbol = Some(Dynamic::Fixed(set.begin.to_owned()));
            spec.end_symbol = Some(Dynamic::Fixed(set.end.to_owned()));
        }
        if let Some(value) = thumb_symbol.filter(|value| !value.is_none()) {
            spec.thumb_symbol = dynamic_string(value)?;
        }
        if let Some(value) = track_symbol.filter(|value| !value.is_none()) {
            spec.track_symbol = optional_text_arg(Some(value))?;
        }
        if let Some(value) = begin_symbol.filter(|value| !value.is_none()) {
            spec.begin_symbol = optional_text_arg(Some(value))?;
        }
        if let Some(value) = end_symbol.filter(|value| !value.is_none()) {
            spec.end_symbol = optional_text_arg(Some(value))?;
        }
        if !has_track {
            spec.track_symbol = None;
        }
        if !has_begin {
            spec.begin_symbol = None;
        }
        if !has_end {
            spec.end_symbol = None;
        }
        spec.style = style_spec_arg(style)?;
        spec.thumb_style = style_spec_arg(thumb_style)?;
        spec.track_style = style_spec_arg(track_style)?;
        spec.begin_style = style_spec_arg(begin_style)?;
        spec.end_style = style_spec_arg(end_style)?;
        if let Some(value) = is_transparent.filter(|value| !value.is_none()) {
            spec.is_transparent = dynamic_bool(value)?;
        }
        let vertical = base_name.starts_with("vertical");
        let shared = Spec::new(spec);
        let initializer = widget_initializer(
            Arc::clone(&shared),
            Frame {
                width,
                height,
                x,
                y,
            },
            if vertical { (1, 10) } else { (20, 1) },
        )?;
        Ok(initializer.add_subclass(Self { spec: shared }))
    }

    #[getter]
    fn orientation<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().orientation.clone();
        text_to_py(slf.py(), &value)
    }

    /// Setting the orientation also switches the default symbols to match, unless customized.
    #[setter]
    fn set_orientation(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let orientation = orientation_arg(value)?;
        Self::edit(slf, |spec| {
            if let (Some(old), Some(new)) = (
                spec.orientation.fixed().cloned(),
                orientation.fixed().cloned(),
            ) {
                let old_set = default_symbols(&old);
                let is_default = spec.thumb_symbol.fixed().map(String::as_str)
                    == Some(old_set.thumb)
                    && spec
                        .track_symbol
                        .as_ref()
                        .and_then(|s| s.fixed())
                        .map(String::as_str)
                        == Some(old_set.track)
                    && spec
                        .begin_symbol
                        .as_ref()
                        .and_then(|s| s.fixed())
                        .map(String::as_str)
                        == Some(old_set.begin)
                    && spec
                        .end_symbol
                        .as_ref()
                        .and_then(|s| s.fixed())
                        .map(String::as_str)
                        == Some(old_set.end);
                if is_default {
                    let set = default_symbols(&new);
                    spec.thumb_symbol = Dynamic::Fixed(set.thumb.to_owned());
                    spec.track_symbol = Some(Dynamic::Fixed(set.track.to_owned()));
                    spec.begin_symbol = Some(Dynamic::Fixed(set.begin.to_owned()));
                    spec.end_symbol = Some(Dynamic::Fixed(set.end.to_owned()));
                }
            }
            spec.orientation = orientation;
        });
        Ok(())
    }

    /// The total number of scrollable items; zero draws nothing.
    #[getter]
    fn content_length<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().content_length.clone();
        dynamic_to_py(slf.py(), &value, |py, number| {
            Ok(number.into_pyobject(py)?.into_any())
        })
    }

    #[setter]
    fn set_content_length(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let setting = dynamic_unsigned(value, "the content length")?;
        Self::edit(slf, |spec| spec.content_length = setting);
        Ok(())
    }

    /// The index of the first visible item.
    #[getter]
    fn content_position<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().position.clone();
        dynamic_to_py(slf.py(), &value, |py, number| {
            Ok(number.into_pyobject(py)?.into_any())
        })
    }

    #[setter]
    fn set_content_position(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let setting = dynamic_unsigned(value, "the position")?;
        Self::edit(slf, |spec| spec.position = setting);
        Ok(())
    }

    #[getter]
    fn viewport_content_length<'py>(slf: &Bound<'py, Self>) -> PyResult<Option<Bound<'py, PyAny>>> {
        let value = slf.borrow().spec.read().viewport_content_length.clone();
        value
            .map(|length| {
                dynamic_to_py(slf.py(), &length, |py, number| {
                    Ok(number.into_pyobject(py)?.into_any())
                })
            })
            .transpose()
    }

    #[setter]
    fn set_viewport_content_length(
        slf: &Bound<'_, Self>,
        value: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<()> {
        let setting = value
            .filter(|value| !value.is_none())
            .map(|value| dynamic_unsigned(value, "the viewport content length"))
            .transpose()?;
        Self::edit(slf, |spec| spec.viewport_content_length = setting);
        Ok(())
    }

    /// The name of the symbol preset the four symbols match, or ``None`` when customized.
    #[getter]
    fn symbols(slf: &Bound<'_, Self>) -> Option<&'static str> {
        let spec = slf.borrow().spec.read().clone();
        let fixed =
            |value: &Option<Dynamic<String>>| value.as_ref().and_then(|v| v.fixed().cloned());
        matching_preset(
            spec.thumb_symbol.fixed()?,
            fixed(&spec.track_symbol).as_deref(),
            fixed(&spec.begin_symbol).as_deref(),
            fixed(&spec.end_symbol).as_deref(),
        )
    }

    #[setter]
    fn set_symbols(slf: &Bound<'_, Self>, name: &str) -> PyResult<()> {
        let set = symbol_preset_from_name(name).ok_or_else(|| {
            PyValueError::new_err(format!(
                "\"{name}\" is not a symbol preset; use one of {}",
                symbol_preset_names()
            ))
        })?;
        Self::edit(slf, |spec| {
            spec.thumb_symbol = Dynamic::Fixed(set.thumb.to_owned());
            if spec.track_symbol.is_some() {
                spec.track_symbol = Some(Dynamic::Fixed(set.track.to_owned()));
            }
            if spec.begin_symbol.is_some() {
                spec.begin_symbol = Some(Dynamic::Fixed(set.begin.to_owned()));
            }
            if spec.end_symbol.is_some() {
                spec.end_symbol = Some(Dynamic::Fixed(set.end.to_owned()));
            }
        });
        Ok(())
    }

    #[getter]
    fn thumb_symbol<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().thumb_symbol.clone();
        text_to_py(slf.py(), &value)
    }

    #[setter]
    fn set_thumb_symbol(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let symbol = dynamic_string(value)?;
        Self::edit(slf, |spec| spec.thumb_symbol = symbol);
        Ok(())
    }

    /// ``None`` hides this part.
    #[getter]
    fn track_symbol<'py>(slf: &Bound<'py, Self>) -> PyResult<Option<Bound<'py, PyAny>>> {
        let value = slf.borrow().spec.read().track_symbol.clone();
        optional_text_to_py(slf.py(), value.as_ref())
    }

    #[setter]
    fn set_track_symbol(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let symbol = optional_text_arg(value)?;
        Self::edit(slf, |spec| spec.track_symbol = symbol);
        Ok(())
    }

    /// ``None`` hides this part.
    #[getter]
    fn begin_symbol<'py>(slf: &Bound<'py, Self>) -> PyResult<Option<Bound<'py, PyAny>>> {
        let value = slf.borrow().spec.read().begin_symbol.clone();
        optional_text_to_py(slf.py(), value.as_ref())
    }

    #[setter]
    fn set_begin_symbol(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let symbol = optional_text_arg(value)?;
        Self::edit(slf, |spec| spec.begin_symbol = symbol);
        Ok(())
    }

    /// ``None`` hides this part.
    #[getter]
    fn end_symbol<'py>(slf: &Bound<'py, Self>) -> PyResult<Option<Bound<'py, PyAny>>> {
        let value = slf.borrow().spec.read().end_symbol.clone();
        optional_text_to_py(slf.py(), value.as_ref())
    }

    #[setter]
    fn set_end_symbol(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let symbol = optional_text_arg(value)?;
        Self::edit(slf, |spec| spec.end_symbol = symbol);
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
    fn thumb_style(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let spec = slf.borrow().spec.read().thumb_style.clone();
        style_spec_to_py(slf.py(), &spec)
    }

    #[setter]
    fn set_thumb_style(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let style = style_spec_arg(value)?;
        Self::edit(slf, |spec| spec.thumb_style = style);
        Ok(())
    }

    #[getter]
    fn track_style(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let spec = slf.borrow().spec.read().track_style.clone();
        style_spec_to_py(slf.py(), &spec)
    }

    #[setter]
    fn set_track_style(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let style = style_spec_arg(value)?;
        Self::edit(slf, |spec| spec.track_style = style);
        Ok(())
    }

    #[getter]
    fn begin_style(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let spec = slf.borrow().spec.read().begin_style.clone();
        style_spec_to_py(slf.py(), &spec)
    }

    #[setter]
    fn set_begin_style(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let style = style_spec_arg(value)?;
        Self::edit(slf, |spec| spec.begin_style = style);
        Ok(())
    }

    #[getter]
    fn end_style(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let spec = slf.borrow().spec.read().end_style.clone();
        style_spec_to_py(slf.py(), &spec)
    }

    #[setter]
    fn set_end_style(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let style = style_spec_arg(value)?;
        Self::edit(slf, |spec| spec.end_style = style);
        Ok(())
    }

    #[getter]
    fn is_transparent<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().is_transparent.clone();
        dynamic_to_py(slf.py(), &value, |py, flag| {
            Ok(pyo3::types::PyBool::new(py, *flag).to_owned().into_any())
        })
    }

    #[setter]
    fn set_is_transparent(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let flag = dynamic_bool(value)?;
        Self::edit(slf, |spec| spec.is_transparent = flag);
        Ok(())
    }

    /// Move to the first item.
    fn first(slf: &Bound<'_, Self>) -> PyResult<()> {
        Self::reading(slf)?;
        Self::move_to(slf, 0);
        Ok(())
    }

    /// Move to the last item.
    fn last(slf: &Bound<'_, Self>) -> PyResult<()> {
        let (_, length) = Self::reading(slf)?;
        Self::move_to(slf, length.saturating_sub(1));
        Ok(())
    }

    /// Move one item forward, stopping at the last item.
    fn next(slf: &Bound<'_, Self>) -> PyResult<()> {
        let (position, length) = Self::reading(slf)?;
        Self::move_to(slf, (position + 1).min(length.saturating_sub(1)));
        Ok(())
    }

    /// Move one item backward, stopping at the first item.
    fn previous(slf: &Bound<'_, Self>) -> PyResult<()> {
        let (position, _) = Self::reading(slf)?;
        Self::move_to(slf, position.saturating_sub(1));
        Ok(())
    }

    /// Move one item in a direction: ``"forward"`` or ``"backward"``.
    fn scroll(slf: &Bound<'_, Self>, direction: &str) -> PyResult<()> {
        match direction {
            "forward" => Self::next(slf),
            "backward" => Self::previous(slf),
            other => Err(PyValueError::new_err(format!(
                "\"{other}\" is not a scroll direction; use \"forward\" or \"backward\""
            ))),
        }
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
            "Scrollbar(width={}, height={})",
            frame.width.unwrap_or(0),
            frame.height.unwrap_or(0)
        )
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyScrollbar>()
}
