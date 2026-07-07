use std::rc::Rc;

use pyo3::prelude::*;
use pyo3::types::PyList;
use ratatui::buffer::Buffer;
use ratatui::layout::{Constraint, Position, Rect};
use ratatui::symbols::Marker;
use ratatui::text::Line;
use ratatui::widgets::block::Padding;
use ratatui::widgets::canvas::{Canvas, Circle, Line as CanvasLine, Points, Rectangle};
use ratatui::widgets::{
    Axis, Bar, BarChart, BarGroup, Cell, Chart, Dataset, GraphType, LegendPosition, LineGauge, Row,
    Scrollbar, ScrollbarOrientation, ScrollbarState, ScrollDirection, Sparkline, SparklineBar,
    Table, TableState, Tabs, Widget,
};

use super::convert::{extract_line, extract_text};
use super::layout::{PyAlignment, PyConstraint, PyDirection};
use super::style::{PyColor, PyStyle};
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

#[pyclass(name = "Padding", module = "xnano_core.rust.native", from_py_object)]
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

#[pyclass(name = "Position", module = "xnano_core.rust.native", from_py_object)]
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

#[pyclass(name = "Cell", module = "xnano_core.rust.native", from_py_object)]
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

#[pyclass(name = "Row", module = "xnano_core.rust.native", from_py_object)]
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

#[pyclass(name = "RatTable", module = "xnano_core.rust.native", from_py_object)]
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

#[pyclass(name = "TableState", module = "xnano_core.rust.native")]
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

#[pyclass(name = "ScrollbarOrientation", module = "xnano_core.rust.native", eq, eq_int, from_py_object)]
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

#[pyclass(name = "Scrollbar", module = "xnano_core.rust.native", from_py_object)]
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

#[pyclass(name = "ScrollDirection", module = "xnano_core.rust.native", eq, eq_int, from_py_object)]
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

#[pyclass(name = "ScrollbarState", module = "xnano_core.rust.native")]
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

#[pyclass(name = "Tabs", module = "xnano_core.rust.native", from_py_object)]
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

#[pyclass(name = "SparklineBar", module = "xnano_core.rust.native", from_py_object)]
#[derive(Clone)]
pub struct PySparklineBar {
    pub inner: SparklineBar,
}

#[pymethods]
impl PySparklineBar {
    #[staticmethod]
    fn new(value: u64) -> Self {
        Self {
            inner: SparklineBar::from(value),
        }
    }

    fn style(&self, style: PyStyle) -> Self {
        Self {
            inner: self.inner.style(Some(style.inner)),
        }
    }
}

#[pyclass(name = "Sparkline", module = "xnano_core.rust.native", from_py_object)]
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

    #[staticmethod]
    fn from_bars(bars: &Bound<'_, PyList>) -> PyResult<Self> {
        let items: Vec<SparklineBar> = bars
            .iter()
            .map(|item| {
                item.extract::<PyRef<PySparklineBar>>()
                    .map(|bar| bar.inner)
                    .map_err(|_| {
                        pyo3::exceptions::PyTypeError::new_err("expected SparklineBar")
                    })
            })
            .collect::<PyResult<_>>()?;
        Ok(Self {
            inner: Sparkline::default().data(items),
        })
    }

    fn data(&self, data: Vec<u64>) -> Self {
        Self {
            inner: self.inner.clone().data(&data),
        }
    }

    fn bars(&self, bars: &Bound<'_, PyList>) -> PyResult<Self> {
        let items: Vec<SparklineBar> = bars
            .iter()
            .map(|item| {
                item.extract::<PyRef<PySparklineBar>>()
                    .map(|bar| bar.inner)
                    .map_err(|_| {
                        pyo3::exceptions::PyTypeError::new_err("expected SparklineBar")
                    })
            })
            .collect::<PyResult<_>>()?;
        Ok(Self {
            inner: self.inner.clone().data(items),
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

#[pyclass(name = "LineGauge", module = "xnano_core.rust.native", from_py_object)]
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

#[pyclass(name = "Bar", module = "xnano_core.rust.native", from_py_object)]
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

#[pyclass(name = "BarGroup", module = "xnano_core.rust.native", from_py_object)]
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

#[pyclass(name = "BarChart", module = "xnano_core.rust.native", from_py_object)]
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

#[pyclass(name = "GraphType", module = "xnano_core.rust.native", eq, eq_int, from_py_object)]
#[derive(Clone, Copy, PartialEq)]
pub enum PyGraphType {
    Scatter,
    Line,
    Bar,
}

impl From<PyGraphType> for GraphType {
    fn from(value: PyGraphType) -> Self {
        match value {
            PyGraphType::Scatter => GraphType::Scatter,
            PyGraphType::Line => GraphType::Line,
            PyGraphType::Bar => GraphType::Bar,
        }
    }
}

#[pyclass(name = "LegendPosition", module = "xnano_core.rust.native", eq, eq_int, from_py_object)]
#[derive(Clone, Copy, PartialEq)]
pub enum PyLegendPosition {
    Top,
    TopRight,
    TopLeft,
    Left,
    Right,
    Bottom,
    BottomRight,
    BottomLeft,
}

impl From<PyLegendPosition> for LegendPosition {
    fn from(value: PyLegendPosition) -> Self {
        match value {
            PyLegendPosition::Top => LegendPosition::Top,
            PyLegendPosition::TopRight => LegendPosition::TopRight,
            PyLegendPosition::TopLeft => LegendPosition::TopLeft,
            PyLegendPosition::Left => LegendPosition::Left,
            PyLegendPosition::Right => LegendPosition::Right,
            PyLegendPosition::Bottom => LegendPosition::Bottom,
            PyLegendPosition::BottomRight => LegendPosition::BottomRight,
            PyLegendPosition::BottomLeft => LegendPosition::BottomLeft,
        }
    }
}

#[pyclass(name = "Marker", module = "xnano_core.rust.native", eq, eq_int, from_py_object)]
#[derive(Clone, Copy, PartialEq)]
pub enum PyMarker {
    Dot,
    Block,
    Bar,
    Braille,
    HalfBlock,
}

impl From<PyMarker> for Marker {
    fn from(value: PyMarker) -> Self {
        match value {
            PyMarker::Dot => Marker::Dot,
            PyMarker::Block => Marker::Block,
            PyMarker::Bar => Marker::Bar,
            PyMarker::Braille => Marker::Braille,
            PyMarker::HalfBlock => Marker::HalfBlock,
        }
    }
}

#[derive(Clone)]
struct OwnedDataset {
    name: Option<Line<'static>>,
    data: Vec<(f64, f64)>,
    marker: Marker,
    graph_type: GraphType,
    style: ratatui::style::Style,
}

#[pyclass(name = "Dataset", module = "xnano_core.rust.native", from_py_object)]
#[derive(Clone)]
pub struct PyDataset {
    name: Option<Line<'static>>,
    data: Vec<(f64, f64)>,
    marker: Marker,
    graph_type: GraphType,
    style: ratatui::style::Style,
}

#[pymethods]
impl PyDataset {
    #[staticmethod]
    fn default() -> Self {
        Self {
            name: None,
            data: Vec::new(),
            marker: Marker::Dot,
            graph_type: GraphType::Scatter,
            style: ratatui::style::Style::default(),
        }
    }

    fn name(&self, value: &Bound<'_, PyAny>) -> PyResult<Self> {
        let line = extract_line(value)?;
        Ok(Self {
            name: Some(line),
            ..self.clone()
        })
    }

    fn data(&self, values: Vec<(f64, f64)>) -> Self {
        Self {
            data: values,
            ..self.clone()
        }
    }

    fn marker(&self, value: PyMarker) -> Self {
        Self {
            marker: value.into(),
            ..self.clone()
        }
    }

    fn graph_type(&self, value: PyGraphType) -> Self {
        Self {
            graph_type: value.into(),
            ..self.clone()
        }
    }

    fn style(&self, value: PyStyle) -> Self {
        Self {
            style: value.inner,
            ..self.clone()
        }
    }
}

impl From<PyDataset> for OwnedDataset {
    fn from(value: PyDataset) -> Self {
        Self {
            name: value.name,
            data: value.data,
            marker: value.marker,
            graph_type: value.graph_type,
            style: value.style,
        }
    }
}

#[pyclass(name = "Axis", module = "xnano_core.rust.native", from_py_object)]
#[derive(Clone)]
pub struct PyAxis {
    inner: Axis<'static>,
}

#[pymethods]
impl PyAxis {
    #[staticmethod]
    fn default() -> Self {
        Self {
            inner: Axis::default(),
        }
    }

    fn title(&self, value: &Bound<'_, PyAny>) -> PyResult<Self> {
        let line = extract_line(value)?;
        Ok(Self {
            inner: self.inner.clone().title(line),
        })
    }

    fn bounds(&self, bounds: [f64; 2]) -> Self {
        Self {
            inner: self.inner.clone().bounds(bounds),
        }
    }

    fn labels(&self, values: &Bound<'_, PyList>) -> PyResult<Self> {
        let labels: Vec<Line<'static>> = values
            .iter()
            .map(|item| extract_line(&item))
            .collect::<PyResult<_>>()?;
        Ok(Self {
            inner: self.inner.clone().labels(labels),
        })
    }

    fn style(&self, value: PyStyle) -> Self {
        Self {
            inner: self.inner.clone().style(value.inner),
        }
    }

    fn labels_alignment(&self, alignment: PyAlignment) -> Self {
        Self {
            inner: self.inner.clone().labels_alignment(alignment.into()),
        }
    }
}

#[pyclass(name = "Chart", module = "xnano_core.rust.native", from_py_object)]
#[derive(Clone)]
pub struct PyChart {
    block: Option<ratatui::widgets::Block<'static>>,
    x_axis: Axis<'static>,
    y_axis: Axis<'static>,
    datasets: Vec<OwnedDataset>,
    style: ratatui::style::Style,
    hidden_legend_constraints: (Constraint, Constraint),
    legend_position: Option<LegendPosition>,
}

impl PyChart {
    pub fn render_to(&self, area: Rect, buffer: &mut Buffer) {
        let datasets: Vec<Dataset<'_>> = self
            .datasets
            .iter()
            .map(|dataset| {
                let mut built = Dataset::default()
                    .data(dataset.data.as_slice())
                    .marker(dataset.marker)
                    .graph_type(dataset.graph_type)
                    .style(dataset.style);
                if let Some(ref name) = dataset.name {
                    built = built.name(name.clone());
                }
                built
            })
            .collect();

        let mut chart = Chart::new(datasets)
            .x_axis(self.x_axis.clone())
            .y_axis(self.y_axis.clone())
            .style(self.style)
            .hidden_legend_constraints(self.hidden_legend_constraints)
            .legend_position(self.legend_position);
        if let Some(ref block) = self.block {
            chart = chart.block(block.clone());
        }
        chart.render(area, buffer);
    }
}

#[pymethods]
impl PyChart {
    #[staticmethod]
    fn new(datasets: &Bound<'_, PyList>) -> PyResult<Self> {
        let datasets: Vec<OwnedDataset> = datasets
            .iter()
            .map(|item| {
                item.extract::<PyRef<PyDataset>>()
                    .map(|dataset| dataset.clone().into())
                    .map_err(|_| pyo3::exceptions::PyTypeError::new_err("expected Dataset"))
            })
            .collect::<PyResult<_>>()?;
        Ok(Self {
            block: None,
            x_axis: Axis::default(),
            y_axis: Axis::default(),
            datasets,
            style: ratatui::style::Style::default(),
            hidden_legend_constraints: (Constraint::Ratio(1, 4), Constraint::Ratio(1, 4)),
            legend_position: Some(LegendPosition::default()),
        })
    }

    fn block(&self, block: PyBlock) -> Self {
        Self {
            block: Some(block.inner),
            ..self.clone()
        }
    }

    fn style(&self, value: PyStyle) -> Self {
        Self {
            style: value.inner,
            ..self.clone()
        }
    }

    fn x_axis(&self, axis: PyAxis) -> Self {
        Self {
            x_axis: axis.inner,
            ..self.clone()
        }
    }

    fn y_axis(&self, axis: PyAxis) -> Self {
        Self {
            y_axis: axis.inner,
            ..self.clone()
        }
    }

    fn hidden_legend_constraints(&self, width: PyConstraint, height: PyConstraint) -> Self {
        Self {
            hidden_legend_constraints: (width.inner, height.inner),
            ..self.clone()
        }
    }

    #[pyo3(signature = (position=None))]
    fn legend_position(&self, position: Option<PyLegendPosition>) -> Self {
        Self {
            legend_position: position.map(Into::into),
            ..self.clone()
        }
    }
}

#[derive(Clone)]
enum CanvasShape {
    Line {
        x1: f64,
        y1: f64,
        x2: f64,
        y2: f64,
        color: ratatui::style::Color,
    },
    Points {
        coords: Vec<(f64, f64)>,
        color: ratatui::style::Color,
    },
    Rectangle {
        x: f64,
        y: f64,
        width: f64,
        height: f64,
        color: ratatui::style::Color,
    },
    Circle {
        x: f64,
        y: f64,
        radius: f64,
        color: ratatui::style::Color,
    },
}

#[derive(Clone)]
struct CanvasLabel {
    x: f64,
    y: f64,
    line: Line<'static>,
}

#[pyclass(name = "Canvas", module = "xnano_core.rust.native", from_py_object)]
#[derive(Clone)]
pub struct PyCanvas {
    block: Option<ratatui::widgets::Block<'static>>,
    x_bounds: [f64; 2],
    y_bounds: [f64; 2],
    background_color: ratatui::style::Color,
    marker: Marker,
    shapes: Vec<CanvasShape>,
    labels: Vec<CanvasLabel>,
}

impl PyCanvas {
    pub fn render_to(&self, area: Rect, buffer: &mut Buffer) {
        let shapes = Rc::new(self.shapes.clone());
        let labels = Rc::new(self.labels.clone());
        let shapes_draw = Rc::clone(&shapes);
        let labels_draw = Rc::clone(&labels);
        let mut canvas = Canvas::default()
            .x_bounds(self.x_bounds)
            .y_bounds(self.y_bounds)
            .background_color(self.background_color)
            .marker(self.marker);
        if let Some(ref block) = self.block {
            canvas = canvas.block(block.clone());
        }
        canvas
            .paint(move |ctx| {
                for shape in shapes_draw.iter() {
                    match shape {
                        CanvasShape::Line {
                            x1,
                            y1,
                            x2,
                            y2,
                            color,
                        } => ctx.draw(&CanvasLine {
                            x1: *x1,
                            y1: *y1,
                            x2: *x2,
                            y2: *y2,
                            color: *color,
                        }),
                        CanvasShape::Points { coords, color } => ctx.draw(&Points {
                            coords: coords.as_slice(),
                            color: *color,
                        }),
                        CanvasShape::Rectangle {
                            x,
                            y,
                            width,
                            height,
                            color,
                        } => ctx.draw(&Rectangle {
                            x: *x,
                            y: *y,
                            width: *width,
                            height: *height,
                            color: *color,
                        }),
                        CanvasShape::Circle {
                            x,
                            y,
                            radius,
                            color,
                        } => ctx.draw(&Circle {
                            x: *x,
                            y: *y,
                            radius: *radius,
                            color: *color,
                        }),
                    }
                }
                for label in labels_draw.iter() {
                    ctx.print(label.x, label.y, label.line.clone());
                }
            })
            .render(area, buffer);
    }
}

#[pymethods]
impl PyCanvas {
    #[staticmethod]
    fn default() -> Self {
        Self {
            block: None,
            x_bounds: [0.0, 0.0],
            y_bounds: [0.0, 0.0],
            background_color: ratatui::style::Color::Reset,
            marker: Marker::Braille,
            shapes: Vec::new(),
            labels: Vec::new(),
        }
    }

    fn block(&self, block: PyBlock) -> Self {
        Self {
            block: Some(block.inner),
            ..self.clone()
        }
    }

    fn x_bounds(&self, bounds: [f64; 2]) -> Self {
        Self {
            x_bounds: bounds,
            ..self.clone()
        }
    }

    fn y_bounds(&self, bounds: [f64; 2]) -> Self {
        Self {
            y_bounds: bounds,
            ..self.clone()
        }
    }

    fn background_color(&self, color: PyColor) -> Self {
        Self {
            background_color: color.inner,
            ..self.clone()
        }
    }

    fn marker(&self, value: PyMarker) -> Self {
        Self {
            marker: value.into(),
            ..self.clone()
        }
    }

    fn line(&self, x1: f64, y1: f64, x2: f64, y2: f64, color: PyColor) -> Self {
        let mut shapes = self.shapes.clone();
        shapes.push(CanvasShape::Line {
            x1,
            y1,
            x2,
            y2,
            color: color.inner,
        });
        Self { shapes, ..self.clone() }
    }

    fn points(&self, coords: Vec<(f64, f64)>, color: PyColor) -> Self {
        let mut shapes = self.shapes.clone();
        shapes.push(CanvasShape::Points {
            coords,
            color: color.inner,
        });
        Self { shapes, ..self.clone() }
    }

    fn rectangle(&self, x: f64, y: f64, width: f64, height: f64, color: PyColor) -> Self {
        let mut shapes = self.shapes.clone();
        shapes.push(CanvasShape::Rectangle {
            x,
            y,
            width,
            height,
            color: color.inner,
        });
        Self { shapes, ..self.clone() }
    }

    fn circle(&self, x: f64, y: f64, radius: f64, color: PyColor) -> Self {
        let mut shapes = self.shapes.clone();
        shapes.push(CanvasShape::Circle {
            x,
            y,
            radius,
            color: color.inner,
        });
        Self { shapes, ..self.clone() }
    }

    fn print(&self, x: f64, y: f64, content: &Bound<'_, PyAny>) -> PyResult<Self> {
        let line = extract_line(content)?;
        let mut labels = self.labels.clone();
        labels.push(CanvasLabel { x, y, line });
        Ok(Self {
            labels,
            ..self.clone()
        })
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
    m.add_class::<PySparklineBar>()?;
    m.add_class::<PySparkline>()?;
    m.add_class::<PyLineGauge>()?;
    m.add_class::<PyBar>()?;
    m.add_class::<PyBarGroup>()?;
    m.add_class::<PyBarChart>()?;
    m.add_class::<PyGraphType>()?;
    m.add_class::<PyLegendPosition>()?;
    m.add_class::<PyMarker>()?;
    m.add_class::<PyDataset>()?;
    m.add_class::<PyAxis>()?;
    m.add_class::<PyChart>()?;
    m.add_class::<PyCanvas>()?;
    Ok(())
}
