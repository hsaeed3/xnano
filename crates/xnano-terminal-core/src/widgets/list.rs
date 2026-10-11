//! `ItemList`, the scrollable list with a selection, and the helpers the selection widgets share.

use std::hash::{Hash, Hasher};
use std::sync::{Arc, Mutex};

use pyo3::exceptions::{PyIndexError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyString, PyTuple};
use xnano_terminal_runtime::buffer::BufferCore;
use xnano_terminal_runtime::dynamic::Dynamic;
use xnano_terminal_runtime::painter::Spec;
use xnano_terminal_runtime::text::{Line, Span};
use xnano_terminal_runtime::widgets::Shared;
use xnano_terminal_runtime::widgets::list::{
    HIGHLIGHT_SPACINGS, ItemSpec, ListSpec, Selection, TextSource, style_key,
};
use xnano_terminal_runtime::widgets::style::StyleSpec;

use crate::convert::text_lines;
use crate::expressions::{ExpressionKind, PyExpression};
use crate::shared::lock;
use crate::text::PyStyledText;
use crate::widgets::block::block_arg;
use crate::widgets::style::{style_spec_arg, style_spec_to_py};
use crate::widgets::{
    Frame, PyWidget, dynamic_arg, dynamic_bool, dynamic_string, dynamic_to_py, repaint,
    widget_initializer,
};

/// The block object a widget was given, kept so ``widget.block`` returns the same object.
#[derive(Default)]
pub struct BlockHolder(Mutex<Option<Py<PyAny>>>);

impl BlockHolder {
    pub fn new(value: Option<&Bound<'_, PyAny>>) -> Self {
        Self(Mutex::new(
            value
                .filter(|value| !value.is_none())
                .map(|value| value.clone().unbind()),
        ))
    }

    pub fn get(&self, py: Python<'_>) -> Option<Py<PyAny>> {
        lock(&self.0).as_ref().map(|block| block.clone_ref(py))
    }

    pub fn set(&self, value: Option<&Bound<'_, PyAny>>) {
        *lock(&self.0) = value
            .filter(|value| !value.is_none())
            .map(|value| value.clone().unbind());
    }
}

/// Styled text as a Python object: ``str`` when unstyled, ``StyledText`` otherwise.
pub fn lines_to_py(py: Python<'_>, lines: &[Line]) -> PyResult<Py<PyAny>> {
    let is_plain = lines
        .iter()
        .flatten()
        .all(|span| span.style == xnano_terminal_runtime::style::Style::default());
    if is_plain {
        let text = lines
            .iter()
            .map(|line| {
                line.iter()
                    .map(|span| span.text.as_str())
                    .collect::<String>()
            })
            .collect::<Vec<_>>()
            .join("\n");
        return Ok(PyString::new(py, &text).into_any().unbind());
    }
    let mut spans: Vec<Span> = Vec::new();
    for (index, line) in lines.iter().enumerate() {
        if index > 0 {
            spans.push(Span::new(
                "\n",
                xnano_terminal_runtime::style::Style::default(),
            ));
        }
        spans.extend(line.iter().cloned());
    }
    Ok(Py::new(py, PyStyledText { spans })?.into_any())
}

/// A text setting as a Python object: the text, or the expression it follows.
pub fn text_source_to_py(py: Python<'_>, source: &TextSource) -> PyResult<Py<PyAny>> {
    match source {
        TextSource::Fixed(lines) => lines_to_py(py, lines),
        TextSource::Bound(expr) => Ok(crate::widgets::value_object(py, Arc::clone(expr))?.unbind()),
    }
}

/// A text setting given as text, styled text or an expression that produces text.
pub fn text_source_arg(value: &Bound<'_, PyAny>) -> PyResult<TextSource> {
    if let Ok(expression) = value.extract::<PyRef<'_, PyExpression>>() {
        return match &expression.kind {
            ExpressionKind::Value(expr) => Ok(TextSource::Bound(Arc::clone(expr))),
            _ => Err(PyTypeError::new_err(
                "an operation cannot be used as text; bind a value instead",
            )),
        };
    }
    Ok(TextSource::Fixed(text_lines(value)?))
}

/// A selection setting: ``None``, an index or an expression.
pub fn selection_arg(value: Option<&Bound<'_, PyAny>>) -> PyResult<Dynamic<Selection>> {
    let Some(value) = value.filter(|value| !value.is_none()) else {
        return Ok(Dynamic::Fixed(Selection(None)));
    };
    dynamic_arg(value, |value| {
        let index: i64 = value.extract()?;
        usize::try_from(index)
            .map(|index| Selection(Some(index)))
            .map_err(|_| {
                PyValueError::new_err(format!(
                    "a selection is a position of 0 or more, or None for nothing, not {index}"
                ))
            })
    })
}

pub fn selection_to_py<'py>(
    py: Python<'py>,
    value: &Dynamic<Selection>,
) -> PyResult<Bound<'py, PyAny>> {
    dynamic_to_py(py, value, |py, selection| {
        Ok(match selection.0 {
            Some(index) => index.into_pyobject(py)?.into_any(),
            None => py.None().into_bound(py),
        })
    })
}

pub fn dynamic_usize(value: &Bound<'_, PyAny>) -> PyResult<Dynamic<usize>> {
    dynamic_arg(value, |value| {
        let number: i64 = value.extract()?;
        usize::try_from(number).map_err(|_| {
            PyValueError::new_err(format!("expected a number of 0 or more, not {number}"))
        })
    })
}

pub fn usize_to_py<'py>(py: Python<'py>, value: &Dynamic<usize>) -> PyResult<Bound<'py, PyAny>> {
    dynamic_to_py(py, value, |py, number| {
        Ok(number.into_pyobject(py)?.into_any())
    })
}

pub fn string_to_py<'py>(py: Python<'py>, value: &Dynamic<String>) -> PyResult<Bound<'py, PyAny>> {
    dynamic_to_py(py, value, |py, text| Ok(PyString::new(py, text).into_any()))
}

/// A named choice setting, checked immediately when it is a plain string.
pub fn choice_arg(
    value: &Bound<'_, PyAny>,
    kind: &str,
    names: &[&str],
) -> PyResult<Dynamic<String>> {
    let setting = dynamic_string(value)?;
    if let Dynamic::Fixed(name) = &setting
        && !names.contains(&name.as_str())
    {
        return Err(PyValueError::new_err(format!(
            "\"{name}\" is not a {kind}; use {}",
            names
                .iter()
                .map(|name| format!("\"{name}\""))
                .collect::<Vec<_>>()
                .join(", ")
        )));
    }
    Ok(setting)
}

pub fn spacing_names() -> Vec<&'static str> {
    HIGHLIGHT_SPACINGS.iter().map(|(name, _)| *name).collect()
}

/// Copy placement and flags from one widget's buffer to the copy's.
pub fn copy_frame_state(from: &Arc<BufferCore>, to: &Arc<BufferCore>) {
    let (layer, is_visible, is_focusable) = {
        let state = from.lock();
        (state.layer, state.is_visible, state.is_focusable)
    };
    let mut state = to.lock();
    state.layer = layer;
    state.is_visible = is_visible;
    state.is_focusable = is_focusable;
}

/// The size and position a copy of a widget starts with.
pub fn frame_of(core: &Arc<BufferCore>) -> Frame {
    let state = core.lock();
    Frame {
        width: Some(state.width()),
        height: Some(state.height()),
        x: state.x,
        y: state.y,
    }
}

/// One item of an ``ItemList``.
#[pyclass(
    name = "ListItem",
    module = "xnano._xnano_core",
    frozen,
    from_py_object
)]
#[derive(Clone)]
pub struct PyListItem {
    pub spec: ItemSpec,
}

impl PyListItem {
    fn key(&self) -> String {
        format!(
            "{}|{}",
            self.spec.content.key(),
            style_key(&self.spec.style)
        )
    }
}

/// An item given as a ``ListItem``, text, styled text or an expression.
pub fn item_arg(value: &Bound<'_, PyAny>) -> PyResult<ItemSpec> {
    if let Ok(item) = value.extract::<PyListItem>() {
        return Ok(item.spec);
    }
    Ok(ItemSpec {
        content: text_source_arg(value)?,
        style: StyleSpec::default(),
    })
}

#[pymethods]
impl PyListItem {
    #[new]
    #[pyo3(signature = (content, *, style = None))]
    fn new(content: &Bound<'_, PyAny>, style: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        Ok(Self {
            spec: ItemSpec {
                content: text_source_arg(content)?,
                style: style_spec_arg(style)?,
            },
        })
    }

    /// The text, as ``str`` when unstyled and ``StyledText`` otherwise.
    #[getter]
    fn content(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        text_source_to_py(py, &self.spec.content)
    }

    #[getter]
    fn style(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        style_spec_to_py(py, &self.spec.style)
    }

    /// How many rows the item takes.
    #[getter]
    fn height(&self) -> usize {
        match &self.spec.content {
            TextSource::Fixed(lines) => lines.len().max(1),
            TextSource::Bound(_) => 1,
        }
    }

    fn __repr__(&self) -> String {
        match self.spec.content.plain_text() {
            Some(text) => format!("ListItem({text:?})"),
            None => "ListItem(<bound text>)".to_owned(),
        }
    }

    fn __eq__(&self, other: &Bound<'_, PyAny>) -> bool {
        other
            .extract::<PyRef<'_, Self>>()
            .is_ok_and(|other| self.key() == other.key())
    }

    fn __hash__(&self) -> u64 {
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        self.key().hash(&mut hasher);
        hasher.finish()
    }

    fn __copy__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __deepcopy__<'py>(slf: PyRef<'py, Self>, _memo: &Bound<'py, PyAny>) -> PyRef<'py, Self> {
        slf
    }
}

/// A scrollable list of items with a selection.
#[pyclass(name = "ItemList", module = "xnano._xnano_core", extends = PyWidget, subclass)]
pub struct PyItemList {
    spec: Shared<ListSpec>,
    block: BlockHolder,
}

impl PyItemList {
    fn core(slf: &Bound<'_, Self>) -> Arc<BufferCore> {
        Arc::clone(&slf.as_super().as_super().as_super().borrow().core)
    }

    fn edit<R>(slf: &Bound<'_, Self>, change: impl FnOnce(&mut ListSpec) -> R) -> R {
        let result = slf.borrow().spec.edit(change);
        repaint(&Self::core(slf));
        result
    }

    /// Change the selection with a helper; the selection must be a plain value.
    fn move_selection(
        slf: &Bound<'_, Self>,
        change: impl FnOnce(Option<usize>, usize) -> Option<usize>,
    ) -> PyResult<()> {
        let outcome = slf.borrow().spec.edit(|spec| match &spec.selected {
            Dynamic::Fixed(selection) => {
                spec.selected = Dynamic::Fixed(Selection(change(selection.0, spec.items.len())));
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

pub fn clamp_index(index: usize, count: usize) -> Option<usize> {
    if count == 0 {
        None
    } else {
        Some(index.min(count - 1))
    }
}

#[pymethods]
impl PyItemList {
    #[new]
    #[pyo3(signature = (items = None, *, selected = None, offset = None, style = None,
        highlight_style = None, highlight_symbol = None, repeat_highlight_symbol = None,
        highlight_spacing = None, direction = None, scroll_padding = None, block = None,
        width = None, height = None, x = 0, y = 0))]
    fn new(
        items: Option<&Bound<'_, PyAny>>,
        selected: Option<&Bound<'_, PyAny>>,
        offset: Option<&Bound<'_, PyAny>>,
        style: Option<&Bound<'_, PyAny>>,
        highlight_style: Option<&Bound<'_, PyAny>>,
        highlight_symbol: Option<&Bound<'_, PyAny>>,
        repeat_highlight_symbol: Option<&Bound<'_, PyAny>>,
        highlight_spacing: Option<&Bound<'_, PyAny>>,
        direction: Option<&Bound<'_, PyAny>>,
        scroll_padding: Option<&Bound<'_, PyAny>>,
        block: Option<&Bound<'_, PyAny>>,
        width: Option<i32>,
        height: Option<i32>,
        x: i32,
        y: i32,
    ) -> PyResult<PyClassInitializer<Self>> {
        let mut spec = ListSpec::default();
        if let Some(items) = items.filter(|value| !value.is_none()) {
            for item in items.try_iter()? {
                spec.items.push(item_arg(&item?)?);
            }
        }
        spec.selected = selection_arg(selected)?;
        if let Some(offset) = offset.filter(|value| !value.is_none()) {
            spec.offset = dynamic_usize(offset)?;
        }
        spec.style = style_spec_arg(style)?;
        spec.highlight_style = style_spec_arg(highlight_style)?;
        if let Some(symbol) = highlight_symbol.filter(|value| !value.is_none()) {
            spec.highlight_symbol = dynamic_string(symbol)?;
        }
        if let Some(flag) = repeat_highlight_symbol.filter(|value| !value.is_none()) {
            spec.repeat_highlight_symbol = dynamic_bool(flag)?;
        }
        if let Some(spacing) = highlight_spacing.filter(|value| !value.is_none()) {
            spec.highlight_spacing = choice_arg(spacing, "highlight spacing", &spacing_names())?;
        }
        if let Some(direction) = direction.filter(|value| !value.is_none()) {
            spec.direction = choice_arg(
                direction,
                "list direction",
                &["top_to_bottom", "bottom_to_top"],
            )?;
        }
        if let Some(padding) = scroll_padding.filter(|value| !value.is_none()) {
            spec.scroll_padding = dynamic_usize(padding)?;
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
            (20, 5),
        )?;
        Ok(initializer.add_subclass(Self {
            spec: shared,
            block: holder,
        }))
    }

    /// The items, in order.
    #[getter]
    fn items(slf: &Bound<'_, Self>) -> Vec<PyListItem> {
        slf.borrow()
            .spec
            .read()
            .items
            .iter()
            .map(|spec| PyListItem { spec: spec.clone() })
            .collect()
    }

    #[setter]
    fn set_items(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let mut items = Vec::new();
        for item in value.try_iter()? {
            items.push(item_arg(&item?)?);
        }
        Self::edit(slf, |spec| spec.items = items);
        Ok(())
    }

    /// Add one item at the end.
    fn append(slf: &Bound<'_, Self>, item: &Bound<'_, PyAny>) -> PyResult<()> {
        let item = item_arg(item)?;
        Self::edit(slf, |spec| spec.items.push(item));
        Ok(())
    }

    /// Add several items at the end.
    fn extend(slf: &Bound<'_, Self>, items: &Bound<'_, PyAny>) -> PyResult<()> {
        let mut added = Vec::new();
        for item in items.try_iter()? {
            added.push(item_arg(&item?)?);
        }
        Self::edit(slf, |spec| spec.items.extend(added));
        Ok(())
    }

    /// Insert an item before ``index`` (an index past the end appends).
    fn insert(slf: &Bound<'_, Self>, index: usize, item: &Bound<'_, PyAny>) -> PyResult<()> {
        let item = item_arg(item)?;
        Self::edit(slf, |spec| {
            let position = index.min(spec.items.len());
            spec.items.insert(position, item);
        });
        Ok(())
    }

    /// Replace the item at ``index``.
    fn set_item(slf: &Bound<'_, Self>, index: usize, item: &Bound<'_, PyAny>) -> PyResult<()> {
        let item = item_arg(item)?;
        let count = slf.borrow().spec.read().items.len();
        if index >= count {
            return Err(PyIndexError::new_err(format!(
                "there is no item {index}; the list has {count} items"
            )));
        }
        Self::edit(slf, |spec| spec.items[index] = item);
        Ok(())
    }

    /// Remove and return the item at ``index`` (the last one by default).
    #[pyo3(signature = (index = None))]
    fn pop(slf: &Bound<'_, Self>, index: Option<usize>) -> PyResult<PyListItem> {
        let count = slf.borrow().spec.read().items.len();
        let position = index.unwrap_or(count.saturating_sub(1));
        if count == 0 || position >= count {
            return Err(PyIndexError::new_err(format!(
                "there is no item {position} to remove; the list has {count} items"
            )));
        }
        let removed = Self::edit(slf, |spec| spec.items.remove(position));
        Ok(PyListItem { spec: removed })
    }

    /// Remove every item.
    fn clear(slf: &Bound<'_, Self>) {
        Self::edit(slf, |spec| spec.items.clear());
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

    /// The first item the list scrolls from. The list scrolls by itself to keep the
    /// selection visible; assigning a position here moves the view there.
    #[getter]
    fn offset<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().offset.clone();
        usize_to_py(slf.py(), &value)
    }

    #[setter]
    fn set_offset(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let offset = dynamic_usize(value)?;
        Self::edit(slf, |spec| {
            spec.offset = offset;
            spec.offset_epoch += 1;
        });
        Ok(())
    }

    /// The first position shown and one past the last, from the latest paint.
    #[getter]
    fn visible_range(slf: &Bound<'_, Self>) -> Option<(usize, usize)> {
        slf.borrow().spec.read().feedback.read().visible
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
    fn highlight_symbol<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().highlight_symbol.clone();
        string_to_py(slf.py(), &value)
    }

    #[setter]
    fn set_highlight_symbol(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let symbol = dynamic_string(value)?;
        Self::edit(slf, |spec| spec.highlight_symbol = symbol);
        Ok(())
    }

    #[getter]
    fn repeat_highlight_symbol<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().repeat_highlight_symbol.clone();
        dynamic_to_py(slf.py(), &value, |py, flag| {
            Ok(pyo3::types::PyBool::new(py, *flag).to_owned().into_any())
        })
    }

    #[setter]
    fn set_repeat_highlight_symbol(
        slf: &Bound<'_, Self>,
        value: &Bound<'_, PyAny>,
    ) -> PyResult<()> {
        let flag = dynamic_bool(value)?;
        Self::edit(slf, |spec| spec.repeat_highlight_symbol = flag);
        Ok(())
    }

    /// When the symbol column is reserved: ``"always"``, ``"when_selected"`` or ``"never"``.
    #[getter]
    fn highlight_spacing<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().highlight_spacing.clone();
        string_to_py(slf.py(), &value)
    }

    #[setter]
    fn set_highlight_spacing(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let spacing = choice_arg(value, "highlight spacing", &spacing_names())?;
        Self::edit(slf, |spec| spec.highlight_spacing = spacing);
        Ok(())
    }

    /// ``"top_to_bottom"`` or ``"bottom_to_top"``.
    #[getter]
    fn direction<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().direction.clone();
        string_to_py(slf.py(), &value)
    }

    #[setter]
    fn set_direction(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let direction = choice_arg(value, "list direction", &["top_to_bottom", "bottom_to_top"])?;
        Self::edit(slf, |spec| spec.direction = direction);
        Ok(())
    }

    /// How many items stay visible around the selection while scrolling.
    #[getter]
    fn scroll_padding<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().scroll_padding.clone();
        usize_to_py(slf.py(), &value)
    }

    #[setter]
    fn set_scroll_padding(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let padding = dynamic_usize(value)?;
        Self::edit(slf, |spec| spec.scroll_padding = padding);
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

    /// Select the next item, stopping at the last. With nothing selected it selects the first.
    fn select_next(slf: &Bound<'_, Self>) -> PyResult<()> {
        Self::move_selection(slf, |selected, count| {
            clamp_index(selected.map_or(0, |index| index.saturating_add(1)), count)
        })
    }

    /// Select the previous item, stopping at the first. With nothing selected it selects the last.
    fn select_previous(slf: &Bound<'_, Self>) -> PyResult<()> {
        Self::move_selection(slf, |selected, count| {
            clamp_index(
                selected.map_or(usize::MAX, |index| index.saturating_sub(1)),
                count,
            )
        })
    }

    fn select_first(slf: &Bound<'_, Self>) -> PyResult<()> {
        Self::move_selection(slf, |_, count| clamp_index(0, count))
    }

    fn select_last(slf: &Bound<'_, Self>) -> PyResult<()> {
        Self::move_selection(slf, |_, count| clamp_index(usize::MAX, count))
    }

    /// Move the selection down by ``amount`` items, stopping at the last.
    fn scroll_down_by(slf: &Bound<'_, Self>, amount: u16) -> PyResult<()> {
        Self::move_selection(slf, |selected, count| {
            clamp_index(
                selected
                    .unwrap_or_default()
                    .saturating_add(usize::from(amount)),
                count,
            )
        })
    }

    /// Move the selection up by ``amount`` items, stopping at the first.
    fn scroll_up_by(slf: &Bound<'_, Self>, amount: u16) -> PyResult<()> {
        Self::move_selection(slf, |selected, count| {
            clamp_index(
                selected
                    .unwrap_or_default()
                    .saturating_sub(usize::from(amount)),
                count,
            )
        })
    }

    /// A new list with the same settings, geometry and flags (children are not copied).
    fn copy(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let py = slf.py();
        let mut spec = slf.borrow().spec.read().clone();
        spec.feedback = xnano_terminal_runtime::widgets::list::FeedbackHandle::default();
        let source = Self::core(slf);
        let shared = Spec::new(spec);
        let initializer = widget_initializer(Arc::clone(&shared), frame_of(&source), (20, 5))?;
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
        let spec = slf.borrow().spec.read().clone();
        let state = Self::core(slf).lock().bounds();
        format!(
            "ItemList({} items, width={}, height={})",
            spec.items.len(),
            state.width,
            state.height
        )
    }
}

#[allow(dead_code)]
type Unused = PyTuple;

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyListItem>()?;
    m.add_class::<PyItemList>()
}
