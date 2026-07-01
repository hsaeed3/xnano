use pyo3::prelude::*;
use pyo3::types::PyList;
use ratatui::layout::{Constraint, Position};
use ratatui::widgets::block::Padding;
use ratatui::widgets::{
    Bar, BarChart, BarGroup, Cell, LineGauge, Row, Scrollbar,
    ScrollbarOrientation, ScrollbarState, ScrollDirection, Sparkline, Table, TableState, Tabs,
};

use super::convert::{extract_line, extract_text};
use super::layout::{PyConstraint, PyDirection};
use super::style::PyStyle;
use super::widgets::{PyBlock, PyHighlightSpacing};

fn extract_constraints(values: &Bound<'_, PyList>) -> PyResult<Vec<Constraint>> {
    values
        .iter()
        .map(|item| {
            item.extract::<PyRef<PyConstraint>>()
                .map(|c| c.inner)
                .map_err(|_| {
                    pyo3::exceptions::PyValueError::new_err("expected a sequence of Constraint")
                })
        })
        .collect()
}

#[pyclass(name = "Padding", module = "xnano_core._xnano_core")]
#[derive(Clone, Copy)]
pub struct PyPadding {
    pub inner: Padding,
}

#[pymethods]
impl PyPadding {
    #[staticmethod]
    fn zero() -> Self {
        Self {
            inner: Padding::ZERO,
        }
    }

    #[staticmethod]
    fn uniform(value: u16) -> Self {
        Self {
            inner: Padding::uniform(value),
        }
    }

    #[staticmethod]
    fn horizontal(value: u16) -> Self {
        Self {
            inner: Padding::horizontal(value),
        }
    }

    #[staticmethod]
    fn vertical(value: u16) -> Self {
        Self {
            inner: Padding::vertical(value),
        }
    }

    #[staticmethod]
    #[pyo3(signature = (horizontal, vertical))]
    fn symmetric(horizontal: u16, vertical: u16) -> Self {
        Self {
            inner: Padding::symmetric(horizontal, vertical),
        }
    }

    #[staticmethod]
    #[pyo3(signature = (left, right, top, bottom))]
    fn new(left: u16, right: u16, top: u16, bottom: u16) -> Self {
        Self {
            inner: Padding::new(left, right, top, bottom),
        }
    }
}

#[pyclass(name = "Position", module = "xnano_core._xnano_core")]
#[derive(Clone, Copy)]
pub struct PyPosition {
    pub inner: Position,
}

#[pymethods]
impl PyPosition {
    #[new]
    fn new(x: u16, y: u16) -> Self {
        Self {
            inner: Position { x, y },
        }
    }

    #[getter]
    fn x(&self) -> u16 {
        self.inner.x
    }

    #[getter]
    fn y(&self) -> u16 {
        self.inner.y
    }

    #[classattr]
    const ORIGIN: Self = Self {
        inner: Position::ORIGIN,
    };
}

#[pyclass(name = "Cell", module = "xnano_core._xnano_core")]
#[derive(Clone)]
pub struct PyCell {
    pub inner: Cell<'static>,
}

#[pymethods]
impl PyCell {
    #[staticmethod]
    fn new(content: &Bound<'_, PyAny>) -> PyResult<Self> {
        let line = extract_line(content)?;
        Ok(Self {
            inner: Cell::from(line),
        })
    }

    fn style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().style(style.inner),
        }
    }

    fn content(&self, value: &Bound<'_, PyAny>) -> PyResult<Self> {
        let line = extract_line(value)?;
        Ok(Self {
            inner: self.inner.clone().content(line),
        })
    }
}

#[pyclass(name = "Row", module = "xnano_core._xnano_core")]
#[derive(Clone)]
pub struct PyRow {
    pub inner: Row<'static>,
}

#[pymethods]
impl PyRow {
    #[staticmethod]
    fn new(cells: &Bound<'_, PyList>) -> PyResult<Self> {
        let row_cells: Vec<Cell<'static>> = cells
            .iter()
            .map(|item| {
                if let Ok(cell) = item.extract::<PyRef<PyCell>>() {
                    Ok(cell.inner.clone())
                } else {
                    let line = extract_line(&item)?;
                    Ok(Cell::from(line))
                }
            })
            .collect::<PyResult<_>>()?;
        Ok(Self {
            inner: Row::new(row_cells),
        })
    }

    fn style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().style(style.inner),
        }
    }

    fn height(&self, value: u16) -> Self {
        Self {
            inner: self.inner.clone().height(value),
        }
    }

    fn top_margin(&self, value: u16) -> Self {
        Self {
            inner: self.inner.clone().top_margin(value),
        }
    }

    fn bottom_margin(&self, value: u16) -> Self {
        Self {
            inner: self.inner.clone().bottom_margin(value),
        }
    }

    fn cells(&self, cells: &Bound<'_, PyList>) -> PyResult<Self> {
        let row_cells: Vec<Cell<'static>> = cells
            .iter()
            .map(|item| {
                if let Ok(cell) = item.extract::<PyRef<PyCell>>() {
                    Ok(cell.inner.clone())
                } else {
                    let line = extract_line(&item)?;
                    Ok(Cell::from(line))
                }
            })
            .collect::<PyResult<_>>()?;
        Ok(Self {
            inner: self.inner.clone().cells(row_cells),
        })
    }
}

#[pyclass(name = "RatTable", module = "xnano_core._xnano_core")]
#[derive(Clone)]
pub struct PyRatTable {
    pub inner: Table<'static>,
}

#[pymethods]
impl PyRatTable {
    #[staticmethod]
    fn new(rows: &Bound<'_, PyList>, widths: &Bound<'_, PyList>) -> PyResult<Self> {
        let table_rows: Vec<Row<'static>> = rows
            .iter()
            .map(|item| {
                if let Ok(row) = item.extract::<PyRef<PyRow>>() {
                    Ok(row.inner.clone())
                } else {
                    Err(pyo3::exceptions::PyTypeError::new_err("expected Row"))
                }
            })
            .collect::<PyResult<_>>()?;
        Ok(Self {
            inner: Table::new(table_rows, extract_constraints(widths)?),
        })
    }

    fn header(&self, row: PyRow) -> Self {
        Self {
            inner: self.inner.clone().header(row.inner),
        }
    }

    fn footer(&self, row: PyRow) -> Self {
        Self {
            inner: self.inner.clone().footer(row.inner),
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

    fn row_highlight_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().row_highlight_style(style.inner),
        }
    }

    fn column_highlight_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().column_highlight_style(style.inner),
        }
    }

    fn cell_highlight_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().cell_highlight_style(style.inner),
        }
    }

    fn highlight_symbol(&self, symbol: &Bound<'_, PyAny>) -> PyResult<Self> {
        let text = extract_text(symbol)?;
        Ok(Self {
            inner: self.inner.clone().highlight_symbol(text),
        })
    }

    fn highlight_spacing(&self, spacing: PyHighlightSpacing) -> Self {
        Self {
            inner: self.inner.clone().highlight_spacing(spacing.into()),
        }
    }

    fn rows(&self, rows: &Bound<'_, PyList>) -> PyResult<Self> {
        let table_rows: Vec<Row<'static>> = rows
            .iter()
            .map(|item| {
                item.extract::<PyRef<PyRow>>()
                    .map(|row| row.inner.clone())
                    .map_err(|_| pyo3::exceptions::PyTypeError::new_err("expected Row"))
            })
            .collect::<PyResult<_>>()?;
        Ok(Self {
            inner: self.inner.clone().rows(table_rows),
        })
    }

    fn widths(&self, widths: &Bound<'_, PyList>) -> PyResult<Self> {
        Ok(Self {
            inner: self.inner.clone().widths(extract_constraints(widths)?),
        })
    }

    fn column_spacing(&self, value: u16) -> Self {
        Self {
            inner: self.inner.clone().column_spacing(value),
        }
    }
}

#[pyclass(name = "TableState", module = "xnano_core._xnano_core")]
pub struct PyTableState {
    pub inner: TableState,
}

#[pymethods]
impl PyTableState {
    #[new]
    fn new() -> Self {
        Self {
            inner: TableState::default(),
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

    #[getter]
    fn selected_column(&self) -> Option<usize> {
        self.inner.selected_column()
    }

    fn selected_cell(&self) -> Option<(usize, usize)> {
        self.inner.selected_cell()
    }

    #[getter]
    fn offset(&self) -> usize {
        self.inner.offset()
    }

    #[pyo3(signature = (index=None))]
    fn select_column(&mut self, index: Option<usize>) {
        self.inner.select_column(index);
    }

    #[pyo3(signature = (indexes=None))]
    fn select_cell(&mut self, indexes: Option<(usize, usize)>) {
        self.inner.select_cell(indexes);
    }

    fn select_next(&mut self) {
        self.inner.select_next();
    }

    fn select_previous(&mut self) {
        self.inner.select_previous();
    }

    fn select_next_column(&mut self) {
        self.inner.select_next_column();
    }

    fn select_previous_column(&mut self) {
        self.inner.select_previous_column();
    }

    fn select_first(&mut self) {
        self.inner.select_first();
    }

    fn select_last(&mut self) {
        self.inner.select_last();
    }

    fn select_first_column(&mut self) {
        self.inner.select_first_column();
    }

    fn select_last_column(&mut self) {
        self.inner.select_last_column();
    }

    fn scroll_down_by(&mut self, amount: u16) {
        self.inner.scroll_down_by(amount);
    }

    fn scroll_up_by(&mut self, amount: u16) {
        self.inner.scroll_up_by(amount);
    }

    fn scroll_right_by(&mut self, amount: u16) {
        self.inner.scroll_right_by(amount);
    }

    fn scroll_left_by(&mut self, amount: u16) {
        self.inner.scroll_left_by(amount);
    }
}

#[pyclass(name = "ScrollbarOrientation", module = "xnano_core._xnano_core", eq, eq_int)]
#[derive(Clone, Copy, PartialEq)]
pub enum PyScrollbarOrientation {
    VerticalRight,
    VerticalLeft,
    HorizontalBottom,
    HorizontalTop,
}

impl From<PyScrollbarOrientation> for ScrollbarOrientation {
    fn from(value: PyScrollbarOrientation) -> Self {
        match value {
            PyScrollbarOrientation::VerticalRight => ScrollbarOrientation::VerticalRight,
            PyScrollbarOrientation::VerticalLeft => ScrollbarOrientation::VerticalLeft,
            PyScrollbarOrientation::HorizontalBottom => ScrollbarOrientation::HorizontalBottom,
            PyScrollbarOrientation::HorizontalTop => ScrollbarOrientation::HorizontalTop,
        }
    }
}

#[pyclass(name = "Scrollbar", module = "xnano_core._xnano_core")]
#[derive(Clone)]
pub struct PyScrollbar {
    pub inner: Scrollbar<'static>,
}

#[pymethods]
impl PyScrollbar {
    #[staticmethod]
    fn new(orientation: PyScrollbarOrientation) -> Self {
        Self {
            inner: Scrollbar::new(orientation.into()),
        }
    }

    fn style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().style(style.inner),
        }
    }

    fn thumb_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().thumb_style(style.inner),
        }
    }

    fn track_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().track_style(style.inner),
        }
    }

    fn begin_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().begin_style(style.inner),
        }
    }

    fn end_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().end_style(style.inner),
        }
    }

    #[pyo3(signature = (symbol=None))]
    fn begin_symbol(&self, symbol: Option<&str>) -> Self {
        let leaked = symbol.map(|s| Box::leak(s.to_string().into_boxed_str()) as &'static str);
        Self {
            inner: self.inner.clone().begin_symbol(leaked),
        }
    }

    #[pyo3(signature = (symbol=None))]
    fn end_symbol(&self, symbol: Option<&str>) -> Self {
        let leaked = symbol.map(|s| Box::leak(s.to_string().into_boxed_str()) as &'static str);
        Self {
            inner: self.inner.clone().end_symbol(leaked),
        }
    }
}

#[pyclass(name = "ScrollDirection", module = "xnano_core._xnano_core", eq, eq_int)]
#[derive(Clone, Copy, PartialEq)]
pub enum PyScrollDirection {
    Forward,
    Backward,
}

impl From<PyScrollDirection> for ScrollDirection {
    fn from(value: PyScrollDirection) -> Self {
        match value {
            PyScrollDirection::Forward => ScrollDirection::Forward,
            PyScrollDirection::Backward => ScrollDirection::Backward,
        }
    }
}

#[pyclass(name = "ScrollbarState", module = "xnano_core._xnano_core")]
pub struct PyScrollbarState {
    pub inner: ScrollbarState,
}

#[pymethods]
impl PyScrollbarState {
    #[new]
    fn new(content_length: usize) -> Self {
        Self {
            inner: ScrollbarState::new(content_length),
        }
    }

    fn set_position(&mut self, value: usize) {
        self.inner = self.inner.position(value);
    }

    fn set_content_length(&mut self, value: usize) {
        self.inner = self.inner.content_length(value);
    }

    fn viewport_content_length(&self, value: usize) -> Self {
        Self {
            inner: self.inner.viewport_content_length(value),
        }
    }

    fn prev(&mut self) {
        self.inner.prev();
    }

    fn next(&mut self) {
        self.inner.next();
    }

    fn first(&mut self) {
        self.inner.first();
    }

    fn last(&mut self) {
        self.inner.last();
    }

    fn scroll(&mut self, direction: PyScrollDirection) {
        self.inner.scroll(direction.into());
    }
}

#[pyclass(name = "Tabs", module = "xnano_core._xnano_core")]
#[derive(Clone)]
pub struct PyTabs {
    pub inner: Tabs<'static>,
}

#[pymethods]
impl PyTabs {
    #[staticmethod]
    fn new(titles: &Bound<'_, PyList>) -> PyResult<Self> {
        let lines: Vec<ratatui::text::Line<'static>> = titles
            .iter()
            .map(|item| extract_line(&item))
            .collect::<PyResult<_>>()?;
        Ok(Self {
            inner: Tabs::new(lines),
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

    fn titles(&self, titles: &Bound<'_, PyList>) -> PyResult<Self> {
        let lines: Vec<ratatui::text::Line<'static>> = titles
            .iter()
            .map(|item| extract_line(&item))
            .collect::<PyResult<_>>()?;
        Ok(Self {
            inner: self.inner.clone().titles(lines),
        })
    }

    #[pyo3(signature = (index=None))]
    fn select(&self, index: Option<usize>) -> Self {
        Self {
            inner: self.inner.clone().select(index),
        }
    }

    fn padding(&self, left: &str, right: &str) -> Self {
        Self {
            inner: self
                .inner
                .clone()
                .padding(left.to_string(), right.to_string()),
        }
    }

    fn padding_left(&self, value: &str) -> Self {
        Self {
            inner: self.inner.clone().padding_left(value.to_string()),
        }
    }

    fn padding_right(&self, value: &str) -> Self {
        Self {
            inner: self.inner.clone().padding_right(value.to_string()),
        }
    }

    fn divider(&self, symbol: &str) -> Self {
        let leaked: &'static str = Box::leak(symbol.to_string().into_boxed_str());
        Self {
            inner: self.inner.clone().divider(leaked),
        }
    }
}

#[pyclass(name = "Sparkline", module = "xnano_core._xnano_core")]
#[derive(Clone)]
pub struct PySparkline {
    pub inner: Sparkline<'static>,
}

#[pymethods]
impl PySparkline {
    #[staticmethod]
    fn default() -> Self {
        Self {
            inner: Sparkline::default(),
        }
    }

    #[staticmethod]
    fn new(data: Vec<u64>) -> Self {
        Self {
            inner: Sparkline::default().data(&data),
        }
    }

    fn data(&self, data: Vec<u64>) -> Self {
        Self {
            inner: self.inner.clone().data(&data),
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

    fn max(&self, value: u64) -> Self {
        Self {
            inner: self.inner.clone().max(value),
        }
    }

    fn absent_value_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().absent_value_style(style.inner),
        }
    }

    fn absent_value_symbol(&self, symbol: &str) -> Self {
        Self {
            inner: self.inner.clone().absent_value_symbol(symbol.to_string()),
        }
    }
}

#[pyclass(name = "LineGauge", module = "xnano_core._xnano_core")]
#[derive(Clone)]
pub struct PyLineGauge {
    pub inner: LineGauge<'static>,
}

#[pymethods]
impl PyLineGauge {
    #[staticmethod]
    fn new() -> Self {
        Self {
            inner: LineGauge::default(),
        }
    }

    fn ratio(&self, value: f64) -> Self {
        Self {
            inner: self.inner.clone().ratio(value),
        }
    }

    fn label(&self, label: &Bound<'_, PyAny>) -> PyResult<Self> {
        let line = extract_line(label)?;
        Ok(Self {
            inner: self.inner.clone().label(line),
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

    fn filled_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().filled_style(style.inner),
        }
    }

    fn unfilled_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().unfilled_style(style.inner),
        }
    }
}

#[pyclass(name = "Bar", module = "xnano_core._xnano_core")]
#[derive(Clone)]
pub struct PyBar {
    pub inner: Bar<'static>,
}

#[pymethods]
impl PyBar {
    #[staticmethod]
    fn default() -> Self {
        Self {
            inner: Bar::default(),
        }
    }

    #[staticmethod]
    fn new(value: u64, label: &str) -> Self {
        Self {
            inner: Bar::default()
                .value(value)
                .label(ratatui::text::Line::from(label.to_string())),
        }
    }

    fn value(&self, value: u64) -> Self {
        Self {
            inner: self.inner.clone().value(value),
        }
    }

    fn label(&self, label: &Bound<'_, PyAny>) -> PyResult<Self> {
        let line = extract_line(label)?;
        Ok(Self {
            inner: self.inner.clone().label(line),
        })
    }

    fn text_value(&self, value: &str) -> Self {
        Self {
            inner: self.inner.clone().text_value(value.to_string()),
        }
    }

    fn style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().style(style.inner),
        }
    }

    fn value_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().value_style(style.inner),
        }
    }
}

#[pyclass(name = "BarGroup", module = "xnano_core._xnano_core")]
#[derive(Clone)]
pub struct PyBarGroup {
    pub inner: BarGroup<'static>,
}

#[pymethods]
impl PyBarGroup {
    #[staticmethod]
    fn new(bars: &Bound<'_, PyList>) -> PyResult<Self> {
        let items: Vec<Bar<'static>> = bars
            .iter()
            .map(|item| {
                item.extract::<PyRef<PyBar>>()
                    .map(|b| b.inner.clone())
                    .map_err(|_| pyo3::exceptions::PyTypeError::new_err("expected Bar"))
            })
            .collect::<PyResult<_>>()?;
        Ok(Self {
            inner: BarGroup::default().bars(&items),
        })
    }
}

#[pyclass(name = "BarChart", module = "xnano_core._xnano_core")]
#[derive(Clone)]
pub struct PyBarChart {
    pub inner: BarChart<'static>,
}

#[pymethods]
impl PyBarChart {
    #[staticmethod]
    fn new(groups: &Bound<'_, PyList>) -> PyResult<Self> {
        let mut chart = BarChart::default();
        for item in groups.iter() {
            let group = item
                .extract::<PyRef<PyBarGroup>>()
                .map_err(|_| pyo3::exceptions::PyTypeError::new_err("expected BarGroup"))?;
            chart = chart.data(group.inner.clone());
        }
        Ok(Self { inner: chart })
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

    fn bar_width(&self, value: u16) -> Self {
        Self {
            inner: self.inner.clone().bar_width(value),
        }
    }

    fn max(&self, value: u64) -> Self {
        Self {
            inner: self.inner.clone().max(value),
        }
    }

    fn bar_gap(&self, value: u16) -> Self {
        Self {
            inner: self.inner.clone().bar_gap(value),
        }
    }

    fn group_gap(&self, value: u16) -> Self {
        Self {
            inner: self.inner.clone().group_gap(value),
        }
    }

    fn bar_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().bar_style(style.inner),
        }
    }

    fn value_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().value_style(style.inner),
        }
    }

    fn label_style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().label_style(style.inner),
        }
    }

    fn direction(&self, direction: PyDirection) -> Self {
        Self {
            inner: self.inner.clone().direction(direction.into()),
        }
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyPadding>()?;
    m.add_class::<PyPosition>()?;
    m.add_class::<PyCell>()?;
    m.add_class::<PyRow>()?;
    m.add_class::<PyRatTable>()?;
    m.add_class::<PyTableState>()?;
    m.add_class::<PyScrollbar>()?;
    m.add_class::<PyScrollbarOrientation>()?;
    m.add_class::<PyScrollDirection>()?;
    m.add_class::<PyScrollbarState>()?;
    m.add_class::<PyTabs>()?;
    m.add_class::<PySparkline>()?;
    m.add_class::<PyLineGauge>()?;
    m.add_class::<PyBar>()?;
    m.add_class::<PyBarGroup>()?;
    m.add_class::<PyBarChart>()?;
    Ok(())
}