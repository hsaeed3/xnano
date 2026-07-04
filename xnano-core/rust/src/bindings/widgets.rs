use pyo3::prelude::*;
use pyo3::types::PyList;
use ratatui::widgets::block::Position as TitlePosition;
use ratatui::symbols::border;
use ratatui::widgets::{
    Block, BorderType, Borders, Gauge, HighlightSpacing, List, ListDirection, ListItem, ListState,
    Paragraph, Wrap,
};

use super::convert::{extract_line, extract_span, extract_text};
use super::layout::{PyAlignment, PyRect};
use super::style::PyStyle;

#[pyclass(name = "Borders", module = "xnano_core.rust.native")]
#[derive(Clone, Copy)]
pub struct PyBorders {
    pub inner: Borders,
}

#[pymethods]
impl PyBorders {
    #[classattr]
    const NONE: Self = Self {
        inner: Borders::NONE,
    };
    #[classattr]
    const TOP: Self = Self {
        inner: Borders::TOP,
    };
    #[classattr]
    const RIGHT: Self = Self {
        inner: Borders::RIGHT,
    };
    #[classattr]
    const BOTTOM: Self = Self {
        inner: Borders::BOTTOM,
    };
    #[classattr]
    const LEFT: Self = Self {
        inner: Borders::LEFT,
    };
    #[classattr]
    const ALL: Self = Self {
        inner: Borders::ALL,
    };

    fn __or__(&self, other: Self) -> Self {
        Self {
            inner: self.inner | other.inner,
        }
    }

    fn __repr__(&self) -> String {
        format!("{self:?}", self = self.inner)
    }
}

#[pyclass(name = "BorderSet", module = "xnano_core.rust.native")]
#[derive(Clone, Copy)]
pub struct PyBorderSet {
    pub inner: border::Set,
}

#[pymethods]
impl PyBorderSet {
    #[classattr]
    const PLAIN: Self = Self { inner: border::PLAIN };
    #[classattr]
    const ROUNDED: Self = Self {
        inner: border::ROUNDED,
    };
    #[classattr]
    const DOUBLE: Self = Self {
        inner: border::DOUBLE,
    };
    #[classattr]
    const THICK: Self = Self { inner: border::THICK };

    #[staticmethod]
    #[pyo3(signature = (
        top_left,
        top_right,
        bottom_left,
        bottom_right,
        vertical_left,
        vertical_right,
        horizontal_top,
        horizontal_bottom
    ))]
    fn new(
        top_left: &str,
        top_right: &str,
        bottom_left: &str,
        bottom_right: &str,
        vertical_left: &str,
        vertical_right: &str,
        horizontal_top: &str,
        horizontal_bottom: &str,
    ) -> Self {
        let leak = |value: &str| Box::leak(value.to_string().into_boxed_str());
        Self {
            inner: border::Set {
                top_left: leak(top_left),
                top_right: leak(top_right),
                bottom_left: leak(bottom_left),
                bottom_right: leak(bottom_right),
                vertical_left: leak(vertical_left),
                vertical_right: leak(vertical_right),
                horizontal_top: leak(horizontal_top),
                horizontal_bottom: leak(horizontal_bottom),
            },
        }
    }

    fn __repr__(&self) -> String {
        format!("BorderSet({:?})", self.inner)
    }
}

#[pyclass(name = "BorderType", module = "xnano_core.rust.native", eq, eq_int)]
#[derive(Clone, Copy, PartialEq)]
pub enum PyBorderType {
    Plain,
    Rounded,
    Double,
    Thick,
    QuadrantInside,
    QuadrantOutside,
}

impl From<PyBorderType> for BorderType {
    fn from(value: PyBorderType) -> Self {
        match value {
            PyBorderType::Plain => BorderType::Plain,
            PyBorderType::Rounded => BorderType::Rounded,
            PyBorderType::Double => BorderType::Double,
            PyBorderType::Thick => BorderType::Thick,
            PyBorderType::QuadrantInside => BorderType::QuadrantInside,
            PyBorderType::QuadrantOutside => BorderType::QuadrantOutside,
        }
    }
}

#[pyclass(name = "TitlePosition", module = "xnano_core.rust.native", eq, eq_int)]
#[derive(Clone, Copy, PartialEq)]
pub enum PyTitlePosition {
    Top,
    Bottom,
}

impl From<PyTitlePosition> for TitlePosition {
    fn from(value: PyTitlePosition) -> Self {
        match value {
            PyTitlePosition::Top => TitlePosition::Top,
            PyTitlePosition::Bottom => TitlePosition::Bottom,
        }
    }
}

#[pyclass(name = "HighlightSpacing", module = "xnano_core.rust.native", eq, eq_int)]
#[derive(Clone, Copy, PartialEq)]
pub enum PyHighlightSpacing {
    Always,
    WhenSelected,
    Never,
}

impl From<PyHighlightSpacing> for HighlightSpacing {
    fn from(value: PyHighlightSpacing) -> Self {
        match value {
            PyHighlightSpacing::Always => HighlightSpacing::Always,
            PyHighlightSpacing::WhenSelected => HighlightSpacing::WhenSelected,
            PyHighlightSpacing::Never => HighlightSpacing::Never,
        }
    }
}

#[pyclass(name = "Wrap", module = "xnano_core.rust.native")]
#[derive(Clone, Copy)]
pub struct PyWrap {
    pub inner: Wrap,
}

#[pymethods]
impl PyWrap {
    #[new]
    #[pyo3(signature = (trim=false))]
    fn new(trim: bool) -> Self {
        Self {
            inner: Wrap { trim },
        }
    }
}

#[pyclass(name = "Block", module = "xnano_core.rust.native")]
#[derive(Clone)]
pub struct PyBlock {
    pub inner: Block<'static>,
}

#[pymethods]
impl PyBlock {
    #[staticmethod]
    fn new() -> Self {
        Self {
            inner: Block::new(),
        }
    }

    #[staticmethod]
    fn default() -> Self {
        Self {
            inner: Block::default(),
        }
    }

    #[staticmethod]
    fn bordered() -> Self {
        Self {
            inner: Block::bordered(),
        }
    }

    fn borders(&self, borders: PyBorders) -> Self {
        Self {
            inner: self.inner.clone().borders(borders.inner),
        }
    }

    fn border_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().border_style(style.inner),
        }
    }

    fn border_type(&self, border_type: PyBorderType) -> Self {
        Self {
            inner: self.inner.clone().border_type(border_type.into()),
        }
    }

    fn border_set(&self, border_set: PyBorderSet) -> Self {
        Self {
            inner: self.inner.clone().border_set(border_set.inner),
        }
    }

    fn style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().style(style.inner),
        }
    }

    fn title(&self, title: &Bound<'_, PyAny>) -> PyResult<Self> {
        let line = extract_line(title)?;
        Ok(Self {
            inner: self.inner.clone().title(line),
        })
    }

    fn title_alignment(&self, alignment: PyAlignment) -> Self {
        Self {
            inner: self
                .inner
                .clone()
                .title_alignment(alignment.into()),
        }
    }

    fn title_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().title_style(style.inner),
        }
    }

    fn title_top(&self, title: &Bound<'_, PyAny>) -> PyResult<Self> {
        let line = extract_line(title)?;
        Ok(Self {
            inner: self.inner.clone().title_top(line),
        })
    }

    fn title_bottom(&self, title: &Bound<'_, PyAny>) -> PyResult<Self> {
        let line = extract_line(title)?;
        Ok(Self {
            inner: self.inner.clone().title_bottom(line),
        })
    }

    fn title_position(&self, position: PyTitlePosition) -> Self {
        Self {
            inner: self.inner.clone().title_position(position.into()),
        }
    }

    fn title_at(&self, title: &Bound<'_, PyAny>, position: PyTitlePosition) -> PyResult<Self> {
        let line = extract_line(title)?;
        let inner = match position {
            PyTitlePosition::Top => self.inner.clone().title_top(line),
            PyTitlePosition::Bottom => self.inner.clone().title_bottom(line),
        };
        Ok(Self { inner })
    }

    fn inner(&self, area: PyRect) -> PyRect {
        PyRect {
            inner: self.inner.inner(area.inner),
        }
    }

    fn padding(&self, padding: super::widgets_extra::PyPadding) -> Self {
        Self {
            inner: self.inner.clone().padding(padding.inner),
        }
    }

    fn __repr__(&self) -> String {
        format!("{self:?}", self = self.inner)
    }
}

#[pyclass(name = "Paragraph", module = "xnano_core.rust.native")]
#[derive(Clone)]
pub struct PyParagraph {
    pub inner: Paragraph<'static>,
}

#[pymethods]
impl PyParagraph {
    #[staticmethod]
    fn new(content: &Bound<'_, PyAny>) -> PyResult<Self> {
        Ok(Self {
            inner: Paragraph::new(extract_text(content)?),
        })
    }

    fn block(&self, block: PyBlock) -> Self {
        Self {
            inner: self.inner.clone().block(block.inner),
        }
    }

    fn style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().style(style.inner),
        }
    }

    fn wrap(&self, wrap: PyWrap) -> Self {
        Self {
            inner: self.inner.clone().wrap(wrap.inner),
        }
    }

    fn alignment(&self, alignment: PyAlignment) -> Self {
        Self {
            inner: self.inner.clone().alignment(alignment.into()),
        }
    }

    fn left_aligned(&self) -> Self {
        Self {
            inner: self.inner.clone().left_aligned(),
        }
    }

    fn centered(&self) -> Self {
        Self {
            inner: self.inner.clone().centered(),
        }
    }

    fn right_aligned(&self) -> Self {
        Self {
            inner: self.inner.clone().right_aligned(),
        }
    }

    fn scroll(&self, x: u16, y: u16) -> Self {
        Self {
            inner: self.inner.clone().scroll((x, y).into()),
        }
    }

    fn __repr__(&self) -> String {
        format!("{self:?}", self = self.inner)
    }
}

#[pyclass(name = "ListItem", module = "xnano_core.rust.native")]
#[derive(Clone)]
pub struct PyListItem {
    pub inner: ListItem<'static>,
}

#[pymethods]
impl PyListItem {
    #[staticmethod]
    fn new(content: &Bound<'_, PyAny>) -> PyResult<Self> {
        let line = extract_line(content)?;
        Ok(Self {
            inner: ListItem::new(line),
        })
    }

    fn style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().style(style.inner),
        }
    }

    fn __repr__(&self) -> String {
        format!("{self:?}", self = self.inner)
    }
}

#[pyclass(name = "ListDirection", module = "xnano_core.rust.native", eq, eq_int)]
#[derive(Clone, Copy, PartialEq)]
pub enum PyListDirection {
    TopToBottom,
    BottomToTop,
}

impl From<PyListDirection> for ListDirection {
    fn from(value: PyListDirection) -> Self {
        match value {
            PyListDirection::TopToBottom => ListDirection::TopToBottom,
            PyListDirection::BottomToTop => ListDirection::BottomToTop,
        }
    }
}

#[pyclass(name = "RatList", module = "xnano_core.rust.native")]
#[derive(Clone)]
pub struct PyRatList {
    pub inner: List<'static>,
}

#[pymethods]
impl PyRatList {
    #[staticmethod]
    fn new(items: &Bound<'_, PyList>) -> PyResult<Self> {
        let list_items: Vec<ListItem<'static>> = items
            .iter()
            .map(|item| {
                if let Ok(list_item) = item.extract::<PyRef<PyListItem>>() {
                    Ok(list_item.inner.clone())
                } else {
                    let line = extract_line(&item)?;
                    Ok(ListItem::new(line))
                }
            })
            .collect::<PyResult<_>>()?;
        Ok(Self {
            inner: List::new(list_items),
        })
    }

    fn block(&self, block: PyBlock) -> Self {
        Self {
            inner: self.inner.clone().block(block.inner),
        }
    }

    fn style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().style(style.inner),
        }
    }

    fn highlight_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().highlight_style(style.inner),
        }
    }

    fn direction(&self, direction: PyListDirection) -> Self {
        Self {
            inner: self.inner.clone().direction(direction.into()),
        }
    }

    fn highlight_symbol(&self, symbol: &str) -> Self {
        let leaked: &'static str = Box::leak(symbol.to_string().into_boxed_str());
        Self {
            inner: self.inner.clone().highlight_symbol(leaked),
        }
    }

    fn items(&self, items: &Bound<'_, PyList>) -> PyResult<Self> {
        let list_items: Vec<ListItem<'static>> = items
            .iter()
            .map(|item| {
                if let Ok(list_item) = item.extract::<PyRef<PyListItem>>() {
                    Ok(list_item.inner.clone())
                } else {
                    let line = extract_line(&item)?;
                    Ok(ListItem::new(line))
                }
            })
            .collect::<PyResult<_>>()?;
        Ok(Self {
            inner: self.inner.clone().items(list_items),
        })
    }

    fn repeat_highlight_symbol(&self, repeat: bool) -> Self {
        Self {
            inner: self.inner.clone().repeat_highlight_symbol(repeat),
        }
    }

    fn highlight_spacing(&self, spacing: PyHighlightSpacing) -> Self {
        Self {
            inner: self.inner.clone().highlight_spacing(spacing.into()),
        }
    }

    fn scroll_padding(&self, padding: usize) -> Self {
        Self {
            inner: self.inner.clone().scroll_padding(padding),
        }
    }

    fn len(&self) -> usize {
        self.inner.len()
    }

    fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    fn __repr__(&self) -> String {
        format!("{self:?}", self = self.inner)
    }
}

#[pyclass(name = "ListState", module = "xnano_core.rust.native")]
pub struct PyListState {
    pub inner: ListState,
}

#[pymethods]
impl PyListState {
    #[new]
    fn new() -> Self {
        Self {
            inner: ListState::default(),
        }
    }

    #[pyo3(signature = (index=None))]
    fn select(&mut self, index: Option<usize>) {
        self.inner.select(index);
    }

    #[getter]
    fn selected(&self) -> Option<usize> {
        self.inner.selected()
    }

    fn select_next(&mut self) {
        self.inner.select_next();
    }

    fn select_previous(&mut self) {
        self.inner.select_previous();
    }

    fn select_first(&mut self) {
        self.inner.select_first();
    }

    fn select_last(&mut self) {
        self.inner.select_last();
    }

    #[getter]
    fn offset(&self) -> usize {
        self.inner.offset()
    }

    fn set_offset(&mut self, value: usize) {
        *self.inner.offset_mut() = value;
    }

    fn scroll_down_by(&mut self, amount: u16) {
        self.inner.scroll_down_by(amount);
    }

    fn scroll_up_by(&mut self, amount: u16) {
        self.inner.scroll_up_by(amount);
    }

    fn __repr__(&self) -> String {
        format!(
            "ListState(selected={:?}, offset={})",
            self.inner.selected(),
            self.inner.offset()
        )
    }
}

#[pyclass(name = "Gauge", module = "xnano_core.rust.native")]
#[derive(Clone)]
pub struct PyGauge {
    pub inner: Gauge<'static>,
}

#[pymethods]
impl PyGauge {
    #[staticmethod]
    fn new() -> Self {
        Self {
            inner: Gauge::default(),
        }
    }

    #[staticmethod]
    fn default() -> Self {
        Self {
            inner: Gauge::default(),
        }
    }

    fn block(&self, block: PyBlock) -> Self {
        Self {
            inner: self.inner.clone().block(block.inner),
        }
    }

    fn style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().style(style.inner),
        }
    }

    fn gauge_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().gauge_style(style.inner),
        }
    }

    fn percent(&self, value: u16) -> Self {
        Self {
            inner: self.inner.clone().percent(value),
        }
    }

    fn ratio(&self, value: f64) -> Self {
        Self {
            inner: self.inner.clone().ratio(value),
        }
    }

    fn label(&self, label: &Bound<'_, PyAny>) -> PyResult<Self> {
        let span = extract_span(label)?;
        Ok(Self {
            inner: self.inner.clone().label(span),
        })
    }

    fn use_unicode(&self, value: bool) -> Self {
        Self {
            inner: self.inner.clone().use_unicode(value),
        }
    }

    fn __repr__(&self) -> String {
        format!("{self:?}", self = self.inner)
    }
}

#[pyclass(name = "Clear", module = "xnano_core.rust.native")]
#[derive(Clone, Copy)]
pub struct PyClear;

#[pymethods]
impl PyClear {
    #[staticmethod]
    fn new() -> Self {
        Self
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyBorders>()?;
    m.add_class::<PyBorderSet>()?;
    m.add_class::<PyBorderType>()?;
    m.add_class::<PyTitlePosition>()?;
    m.add_class::<PyHighlightSpacing>()?;
    m.add_class::<PyWrap>()?;
    m.add_class::<PyBlock>()?;
    m.add_class::<PyParagraph>()?;
    m.add_class::<PyListItem>()?;
    m.add_class::<PyListDirection>()?;
    m.add_class::<PyRatList>()?;
    m.add_class::<PyListState>()?;
    m.add_class::<PyGauge>()?;
    m.add_class::<PyClear>()?;
    Ok(())
}