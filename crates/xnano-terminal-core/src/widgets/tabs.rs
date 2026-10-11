//! `Tabs`: a row of titles with one selected.

use std::sync::Arc;

use pyo3::exceptions::{PyIndexError, PyValueError};
use pyo3::prelude::*;
use xnano_terminal_runtime::buffer::BufferCore;
use xnano_terminal_runtime::dynamic::Dynamic;
use xnano_terminal_runtime::painter::Spec;
use xnano_terminal_runtime::widgets::Shared;
use xnano_terminal_runtime::widgets::list::{Selection, TextSource};
use xnano_terminal_runtime::widgets::tabs::TabsSpec;

use crate::widgets::block::block_arg;
use crate::widgets::list::{
    BlockHolder, copy_frame_state, frame_of, selection_arg, selection_to_py, text_source_arg,
    text_source_to_py,
};
use crate::widgets::style::{style_spec_arg, style_spec_to_py};
use crate::widgets::{Frame, PyWidget, repaint, widget_initializer};

/// A row of titles with one selected.
#[pyclass(name = "Tabs", module = "xnano._xnano_core", extends = PyWidget, subclass)]
pub struct PyTabs {
    spec: Shared<TabsSpec>,
    block: BlockHolder,
}

impl PyTabs {
    fn core(slf: &Bound<'_, Self>) -> Arc<BufferCore> {
        Arc::clone(&slf.as_super().as_super().as_super().borrow().core)
    }

    fn edit<R>(slf: &Bound<'_, Self>, change: impl FnOnce(&mut TabsSpec) -> R) -> R {
        let result = slf.borrow().spec.edit(change);
        repaint(&Self::core(slf));
        result
    }

    fn move_selection(
        slf: &Bound<'_, Self>,
        change: impl FnOnce(Option<usize>, usize) -> Option<usize>,
    ) -> PyResult<()> {
        let outcome = slf.borrow().spec.edit(|spec| match &spec.selected {
            Dynamic::Fixed(selection) => {
                spec.selected = Dynamic::Fixed(Selection(change(selection.0, spec.titles.len())));
                Ok(())
            }
            Dynamic::Bound(_) => Err(PyValueError::new_err(
                "the selection follows an expression, so it cannot be moved by hand. Assign a plain \
                 position to `selected` first, or change the state the expression reads.",
            )),
        });
        repaint(&Self::core(slf));
        outcome
    }
}

#[pymethods]
impl PyTabs {
    #[new]
    #[pyo3(signature = (titles = None, *, selected = None, style = None, highlight_style = None,
        divider = None, padding_left = None, padding_right = None, block = None,
        width = None, height = None, x = 0, y = 0))]
    fn new(
        titles: Option<&Bound<'_, PyAny>>,
        selected: Option<&Bound<'_, PyAny>>,
        style: Option<&Bound<'_, PyAny>>,
        highlight_style: Option<&Bound<'_, PyAny>>,
        divider: Option<&Bound<'_, PyAny>>,
        padding_left: Option<&Bound<'_, PyAny>>,
        padding_right: Option<&Bound<'_, PyAny>>,
        block: Option<&Bound<'_, PyAny>>,
        width: Option<i32>,
        height: Option<i32>,
        x: i32,
        y: i32,
    ) -> PyResult<PyClassInitializer<Self>> {
        let mut spec = TabsSpec::default();
        if let Some(titles) = titles.filter(|value| !value.is_none()) {
            for title in titles.try_iter()? {
                spec.titles.push(text_source_arg(&title?)?);
            }
        }
        // Tabs select the first title unless told otherwise; `selected=None` keeps that.
        if let Some(selected) = selected {
            spec.selected = selection_arg(Some(selected))?;
        }
        spec.style = style_spec_arg(style)?;
        spec.highlight_style = style_spec_arg(highlight_style)?;
        if let Some(divider) = divider.filter(|value| !value.is_none()) {
            spec.divider = text_source_arg(divider)?;
        }
        if let Some(padding) = padding_left.filter(|value| !value.is_none()) {
            spec.padding_left = text_source_arg(padding)?;
        }
        if let Some(padding) = padding_right.filter(|value| !value.is_none()) {
            spec.padding_right = text_source_arg(padding)?;
        }
        spec.block = block_arg(block)?;
        let holder = BlockHolder::new(block);
        let shared = Spec::new(spec);
        let initializer = widget_initializer(
            Arc::clone(&shared),
            Frame {
                width,
                height,
                x,
                y,
            },
            (30, 1),
        )?;
        Ok(initializer.add_subclass(Self {
            spec: shared,
            block: holder,
        }))
    }

    #[getter]
    fn titles(slf: &Bound<'_, Self>) -> PyResult<Vec<Py<PyAny>>> {
        let titles = slf.borrow().spec.read().titles.clone();
        titles
            .iter()
            .map(|title| text_source_to_py(slf.py(), title))
            .collect()
    }

    #[setter]
    fn set_titles(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let mut titles = Vec::new();
        for title in value.try_iter()? {
            titles.push(text_source_arg(&title?)?);
        }
        Self::edit(slf, |spec| spec.titles = titles);
        Ok(())
    }

    /// Add one title at the end.
    fn append(slf: &Bound<'_, Self>, title: &Bound<'_, PyAny>) -> PyResult<()> {
        let title = text_source_arg(title)?;
        Self::edit(slf, |spec| spec.titles.push(title));
        Ok(())
    }

    /// Remove and return the title at ``index`` (the last by default).
    #[pyo3(signature = (index = None))]
    fn pop(slf: &Bound<'_, Self>, index: Option<usize>) -> PyResult<Py<PyAny>> {
        let count = slf.borrow().spec.read().titles.len();
        let position = index.unwrap_or(count.saturating_sub(1));
        if count == 0 || position >= count {
            return Err(PyIndexError::new_err(format!(
                "there is no title {position} to remove; there are {count} titles"
            )));
        }
        let removed: TextSource = Self::edit(slf, |spec| spec.titles.remove(position));
        text_source_to_py(slf.py(), &removed)
    }

    fn clear(slf: &Bound<'_, Self>) {
        Self::edit(slf, |spec| spec.titles.clear());
    }

    /// The selected position, ``None`` for nothing, or the expression it follows.
    #[getter]
    fn selected<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().selected.clone();
        selection_to_py(slf.py(), &value)
    }

    #[setter]
    fn set_selected(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let selection = selection_arg(value)?;
        Self::edit(slf, |spec| spec.selected = selection);
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
    fn highlight_style(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let spec = slf.borrow().spec.read().highlight_style.clone();
        style_spec_to_py(slf.py(), &spec)
    }

    #[setter]
    fn set_highlight_style(
        slf: &Bound<'_, Self>,
        value: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<()> {
        let style = style_spec_arg(value)?;
        Self::edit(slf, |spec| spec.highlight_style = style);
        Ok(())
    }

    #[getter]
    fn divider(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let value = slf.borrow().spec.read().divider.clone();
        text_source_to_py(slf.py(), &value)
    }

    #[setter]
    fn set_divider(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let divider = text_source_arg(value)?;
        Self::edit(slf, |spec| spec.divider = divider);
        Ok(())
    }

    #[getter]
    fn padding_left(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let value = slf.borrow().spec.read().padding_left.clone();
        text_source_to_py(slf.py(), &value)
    }

    #[setter]
    fn set_padding_left(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let padding = text_source_arg(value)?;
        Self::edit(slf, |spec| spec.padding_left = padding);
        Ok(())
    }

    #[getter]
    fn padding_right(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let value = slf.borrow().spec.read().padding_right.clone();
        text_source_to_py(slf.py(), &value)
    }

    #[setter]
    fn set_padding_right(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let padding = text_source_arg(value)?;
        Self::edit(slf, |spec| spec.padding_right = padding);
        Ok(())
    }

    #[getter]
    fn block(slf: &Bound<'_, Self>) -> Option<Py<PyAny>> {
        slf.borrow().block.get(slf.py())
    }

    #[setter]
    fn set_block(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let shared = block_arg(value)?;
        slf.borrow().block.set(value);
        Self::edit(slf, |spec| spec.block = shared);
        Ok(())
    }

    /// Select the next title. With ``should_wrap`` the last title is followed by the first.
    #[pyo3(signature = (*, should_wrap = true))]
    fn select_next(slf: &Bound<'_, Self>, should_wrap: bool) -> PyResult<()> {
        Self::move_selection(slf, |selected, count| {
            if count == 0 {
                return None;
            }
            let next = selected.map_or(0, |index| index.saturating_add(1));
            Some(if next >= count {
                if should_wrap { 0 } else { count - 1 }
            } else {
                next
            })
        })
    }

    /// Select the previous title. With ``should_wrap`` the first title is followed by the last.
    #[pyo3(signature = (*, should_wrap = true))]
    fn select_previous(slf: &Bound<'_, Self>, should_wrap: bool) -> PyResult<()> {
        Self::move_selection(slf, |selected, count| {
            if count == 0 {
                return None;
            }
            Some(match selected {
                None => count - 1,
                Some(0) => {
                    if should_wrap {
                        count - 1
                    } else {
                        0
                    }
                }
                Some(index) => (index - 1).min(count - 1),
            })
        })
    }

    fn select_first(slf: &Bound<'_, Self>) -> PyResult<()> {
        Self::move_selection(slf, |_, count| (count > 0).then_some(0))
    }

    fn select_last(slf: &Bound<'_, Self>) -> PyResult<()> {
        Self::move_selection(slf, |_, count| count.checked_sub(1))
    }

    /// A new tabs widget with the same settings, geometry and flags (children are not copied).
    fn copy(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let py = slf.py();
        let spec = slf.borrow().spec.read().clone();
        let source = Self::core(slf);
        let shared = Spec::new(spec);
        let initializer = widget_initializer(Arc::clone(&shared), frame_of(&source), (30, 1))?;
        let block = slf.borrow().block.get(py);
        let object = Py::new(
            py,
            initializer.add_subclass(Self {
                spec: shared,
                block: BlockHolder::new(block.as_ref().map(|block| block.bind(py))),
            }),
        )?;
        copy_frame_state(&source, &Self::core(object.bind(py)));
        Ok(object.into_any())
    }

    fn __copy__(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        Self::copy(slf)
    }

    fn __deepcopy__(slf: &Bound<'_, Self>, _memo: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        Self::copy(slf)
    }

    fn __repr__(slf: &Bound<'_, Self>) -> String {
        let count = slf.borrow().spec.read().titles.len();
        let state = Self::core(slf).lock().bounds();
        format!(
            "Tabs({count} titles, width={}, height={})",
            state.width, state.height
        )
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyTabs>()
}
