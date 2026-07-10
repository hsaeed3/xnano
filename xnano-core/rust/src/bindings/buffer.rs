use std::cell::Cell as StdCell;
use std::rc::Rc;

use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::PyList;
use ratatui::buffer::{Buffer, Cell};
use ratatui::layout::Position;
use ratatui::text::Line;
use ratatui::widgets::{Clear, StatefulWidget, Widget};
use ratatui::style::{Color, Modifier};

use super::layout::PyRect;
use super::style::{PyColor, PyModifier, PyStyle};
use super::text::{PyLine, PySpan, PyText};
use super::widgets_extra::PyPosition;
use super::widgets::{PyBlock, PyClear, PyGauge, PyListState, PyRatList, PyParagraph};
use super::widgets_extra::{
    PyBarChart, PyCanvas, PyChart, PyLineGauge, PyRatTable, PyScrollbar, PyScrollbarState,
    PySparkline, PyTableState, PyTabs,
};

#[pyclass(name = "BufferCell", module = "xnano_core.rust.native", from_py_object)]
#[derive(Clone)]
pub struct PyBufferCell {
    pub inner: Cell,
}

impl From<Cell> for PyBufferCell {
    fn from(value: Cell) -> Self {
        Self { inner: value }
    }
}

#[pymethods]
impl PyBufferCell {
    #[staticmethod]
    fn new(symbol: &str) -> Self {
        let mut inner = Cell::default();
        inner.set_symbol(symbol);
        Self { inner }
    }

    #[classattr]
    const EMPTY: Self = Self {
        inner: Cell::EMPTY,
    };

    #[getter]
    fn symbol(&self) -> String {
        self.inner.symbol().to_string()
    }

    #[getter]
    fn fg(&self) -> PyColor {
        self.inner.fg.into()
    }

    #[getter]
    fn bg(&self) -> PyColor {
        self.inner.bg.into()
    }

    #[getter]
    fn modifier(&self) -> PyModifier {
        PyModifier {
            inner: self.inner.modifier,
        }
    }

    #[getter]
    fn style(&self) -> PyStyle {
        PyStyle {
            inner: self.inner.style(),
        }
    }

    fn reset(&mut self) {
        self.inner.reset();
    }

    fn set_symbol(&mut self, symbol: &str) -> Self {
        self.inner.set_symbol(symbol);
        self.clone()
    }

    fn set_style(&mut self, style: PyStyle) -> Self {
        self.inner.set_style(style.inner);
        self.clone()
    }

    fn __repr__(&self) -> String {
        format!(
            "BufferCell(symbol={:?}, fg={:?}, bg={:?})",
            self.inner.symbol(),
            self.inner.fg,
            self.inner.bg
        )
    }
}

#[pyclass(name = "Buffer", module = "xnano_core.rust.native", from_py_object)]
#[derive(Clone)]
pub struct PyBuffer {
    pub inner: Buffer,
}

fn check_local_coords(buffer: &Buffer, x: u16, y: u16) -> PyResult<()> {
    if x >= buffer.area.width || y >= buffer.area.height {
        return Err(pyo3::exceptions::PyIndexError::new_err(format!(
            "position ({x}, {y}) out of bounds"
        )));
    }
    Ok(())
}

fn local_position(buffer: &Buffer, x: u16, y: u16) -> Position {
    Position {
        x: buffer.area.x + x,
        y: buffer.area.y + y,
    }
}

fn extract_line_value(value: &Bound<'_, PyAny>) -> PyResult<Line<'static>> {
    if let Ok(line) = value.extract::<PyRef<PyLine>>() {
        return Ok(line.inner.clone());
    }
    if let Ok(text) = value.extract::<String>() {
        return Ok(Line::from(text));
    }
    Err(pyo3::exceptions::PyTypeError::new_err(
        "expected str or Line",
    ))
}

pub fn render_widget_inner(
    widget: &Bound<'_, PyAny>,
    area: PyRect,
    buffer: &mut Buffer,
) -> PyResult<()> {
    let mut resolved = widget.clone();
    if let Ok(to_core) = resolved.getattr("_to_core") {
        if let Ok(val) = to_core.call0() {
            resolved = val;
        }
    } else if let Ok(inner) = resolved.getattr("_inner") {
        resolved = inner;
    }

    if let Ok(paragraph) = resolved.extract::<PyRef<PyParagraph>>() {
        paragraph.inner.clone().render(area.inner, buffer);
        return Ok(());
    }
    if let Ok(block) = resolved.extract::<PyRef<PyBlock>>() {
        block.inner.clone().render(area.inner, buffer);
        return Ok(());
    }
    if let Ok(list) = resolved.extract::<PyRef<PyRatList>>() {
        Widget::render(list.inner.clone(), area.inner, buffer);
        return Ok(());
    }
    if let Ok(table) = resolved.extract::<PyRef<PyRatTable>>() {
        Widget::render(table.inner.clone(), area.inner, buffer);
        return Ok(());
    }
    if let Ok(gauge) = resolved.extract::<PyRef<PyGauge>>() {
        gauge.inner.clone().render(area.inner, buffer);
        return Ok(());
    }
    if let Ok(tabs) = resolved.extract::<PyRef<PyTabs>>() {
        tabs.inner.clone().render(area.inner, buffer);
        return Ok(());
    }
    if let Ok(sparkline) = resolved.extract::<PyRef<PySparkline>>() {
        sparkline.inner.clone().render(area.inner, buffer);
        return Ok(());
    }
    if let Ok(line_gauge) = resolved.extract::<PyRef<PyLineGauge>>() {
        line_gauge.inner.clone().render(area.inner, buffer);
        return Ok(());
    }
    if let Ok(bar_chart) = resolved.extract::<PyRef<PyBarChart>>() {
        bar_chart.inner.clone().render(area.inner, buffer);
        return Ok(());
    }
    if let Ok(chart) = resolved.extract::<PyRef<PyChart>>() {
        chart.render_to(area.inner, buffer);
        return Ok(());
    }
    if let Ok(canvas) = resolved.extract::<PyRef<PyCanvas>>() {
        canvas.render_to(area.inner, buffer);
        return Ok(());
    }
    if resolved.is_instance_of::<PyClear>() {
        Clear.render(area.inner, buffer);
        return Ok(());
    }
    if let Ok(span) = resolved.extract::<PyRef<PySpan>>() {
        span.inner.clone().render(area.inner, buffer);
        return Ok(());
    }
    if let Ok(line) = resolved.extract::<PyRef<PyLine>>() {
        line.inner.clone().render(area.inner, buffer);
        return Ok(());
    }
    if let Ok(text) = resolved.extract::<PyRef<PyText>>() {
        text.inner.clone().render(area.inner, buffer);
        return Ok(());
    }

    if let Ok(render_method) = resolved.getattr("render") {
        let py = resolved.py();
        let py_area = Bound::new(py, area)?;
        let rendered = render_method.call1((py_area,))?;
        return render_widget_inner(&rendered, area, buffer);
    }

    Err(pyo3::exceptions::PyTypeError::new_err(format!(
        "unsupported widget type: {}",
        widget.get_type().name()?
    )))
}

pub fn render_stateful_inner(
    widget: &Bound<'_, PyAny>,
    area: PyRect,
    state: &Bound<'_, PyAny>,
    buffer: &mut Buffer,
) -> PyResult<()> {
    if let Ok(list) = widget.extract::<PyRef<PyRatList>>() {
        if let Ok(mut list_state) = state.extract::<PyRefMut<PyListState>>() {
            StatefulWidget::render(list.inner.clone(), area.inner, buffer, &mut list_state.inner);
            return Ok(());
        }
    }
    if let Ok(table) = widget.extract::<PyRef<PyRatTable>>() {
        if let Ok(mut table_state) = state.extract::<PyRefMut<PyTableState>>() {
            StatefulWidget::render(table.inner.clone(), area.inner, buffer, &mut table_state.inner);
            return Ok(());
        }
    }
    if let Ok(scrollbar) = widget.extract::<PyRef<PyScrollbar>>() {
        if let Ok(mut scrollbar_state) = state.extract::<PyRefMut<PyScrollbarState>>() {
            StatefulWidget::render(
                scrollbar.inner.clone(),
                area.inner,
                buffer,
                &mut scrollbar_state.inner,
            );
            return Ok(());
        }
    }

    Err(pyo3::exceptions::PyTypeError::new_err(format!(
        "unsupported stateful widget/state pair: {} / {}",
        widget.get_type().name()?,
        state.get_type().name()?
    )))
}

#[pymethods]
impl PyBuffer {
    #[staticmethod]
    fn empty(area: PyRect) -> Self {
        Self {
            inner: Buffer::empty(area.inner),
        }
    }

    #[staticmethod]
    fn filled(area: PyRect, cell: &PyBufferCell) -> Self {
        Self {
            inner: Buffer::filled(area.inner, cell.inner.clone()),
        }
    }

    #[staticmethod]
    fn with_lines(lines: &Bound<'_, PyList>) -> PyResult<Self> {
        let parsed: Vec<Line<'static>> = lines
            .iter()
            .map(|item| extract_line_value(&item))
            .collect::<PyResult<_>>()?;
        Ok(Self {
            inner: Buffer::with_lines(parsed),
        })
    }

    #[getter]
    fn area(&self) -> PyRect {
        PyRect {
            inner: self.inner.area,
        }
    }

    fn render_widget(&mut self, widget: &Bound<'_, PyAny>, area: PyRect) -> PyResult<()> {
        render_widget_inner(widget, area, &mut self.inner)
    }

    fn render_stateful_widget(
        &mut self,
        widget: &Bound<'_, PyAny>,
        area: PyRect,
        state: &Bound<'_, PyAny>,
    ) -> PyResult<()> {
        render_stateful_inner(widget, area, state, &mut self.inner)
    }

    fn cell(&self, x: u16, y: u16) -> PyResult<Option<PyBufferCell>> {
        check_local_coords(&self.inner, x, y)?;
        let position = local_position(&self.inner, x, y);
        Ok(self
            .inner
            .cell(position)
            .map(|cell| PyBufferCell { inner: cell.clone() }))
    }

    fn set_cell(
        &mut self,
        x: u16,
        y: u16,
        symbol: &str,
        style: PyStyle,
    ) -> PyResult<()> {
        check_local_coords(&self.inner, x, y)?;
        let position = local_position(&self.inner, x, y);
        if let Some(cell) = self.inner.cell_mut(position) {
            cell.set_symbol(symbol).set_style(style.inner);
            Ok(())
        } else {
            Err(pyo3::exceptions::PyIndexError::new_err(format!(
                "position ({x}, {y}) out of bounds"
            )))
        }
    }

    #[pyo3(signature = (y, line, x=0, max_width=None))]
    fn set_line(
        &mut self,
        y: u16,
        line: &Bound<'_, PyAny>,
        x: u16,
        max_width: Option<u16>,
    ) -> PyResult<(u16, u16)> {
        if y >= self.inner.area.height {
            return Err(pyo3::exceptions::PyIndexError::new_err(format!(
                "row {y} out of bounds"
            )));
        }
        let parsed = extract_line_value(line)?;
        let max_width = max_width.unwrap_or(self.inner.area.width.saturating_sub(x));
        Ok(self.inner.set_line(x, y, &parsed, max_width))
    }

    fn set_style(&mut self, area: PyRect, style: PyStyle) {
        self.inner.set_style(area.inner, style.inner);
    }

    #[pyo3(signature = (x, y, span, max_width=None))]
    fn set_span(
        &mut self,
        x: u16,
        y: u16,
        span: &PySpan,
        max_width: Option<u16>,
    ) -> PyResult<(u16, u16)> {
        if x >= self.inner.area.width || y >= self.inner.area.height {
            return Err(pyo3::exceptions::PyIndexError::new_err(format!(
                "position ({x}, {y}) out of bounds"
            )));
        }
        let max_width = max_width.unwrap_or(self.inner.area.width.saturating_sub(x));
        Ok(self.inner.set_span(x, y, &span.inner, max_width))
    }

    fn resize(&mut self, area: PyRect) {
        self.inner.resize(area.inner);
    }

    fn index_of(&self, x: u16, y: u16) -> PyResult<usize> {
        check_local_coords(&self.inner, x, y)?;
        let position = local_position(&self.inner, x, y);
        Ok(self.inner.index_of(position.x, position.y))
    }

    fn pos_of(&self, index: usize) -> PyPosition {
        let (x, y) = self.inner.pos_of(index);
        PyPosition {
            inner: Position { x, y },
        }
    }

    fn content(&self) -> Vec<PyBufferCell> {
        self.inner
            .content()
            .iter()
            .cloned()
            .map(PyBufferCell::from)
            .collect()
    }

    fn cell_symbol(&self, x: u16, y: u16) -> PyResult<String> {
        if x >= self.inner.area.width || y >= self.inner.area.height {
            return Err(pyo3::exceptions::PyIndexError::new_err(format!(
                "position ({x}, {y}) out of bounds"
            )));
        }
        Ok(self.inner[(x, y)].symbol().to_string())
    }

    fn cell_fg(&self, x: u16, y: u16) -> PyResult<PyColor> {
        if x >= self.inner.area.width || y >= self.inner.area.height {
            return Err(pyo3::exceptions::PyIndexError::new_err(format!(
                "position ({x}, {y}) out of bounds"
            )));
        }
        Ok(self.inner[(x, y)].fg.into())
    }

    fn cell_bg(&self, x: u16, y: u16) -> PyResult<PyColor> {
        if x >= self.inner.area.width || y >= self.inner.area.height {
            return Err(pyo3::exceptions::PyIndexError::new_err(format!(
                "position ({x}, {y}) out of bounds"
            )));
        }
        Ok(self.inner[(x, y)].bg.into())
    }

    fn cell_modifier(&self, x: u16, y: u16) -> PyResult<PyModifier> {
        if x >= self.inner.area.width || y >= self.inner.area.height {
            return Err(pyo3::exceptions::PyIndexError::new_err(format!(
                "position ({x}, {y}) out of bounds"
            )));
        }
        Ok(PyModifier {
            inner: self.inner[(x, y)].modifier,
        })
    }

    fn set_string(
        &mut self,
        x: u16,
        y: u16,
        string: &str,
        style: PyStyle,
    ) -> PyResult<()> {
        if x >= self.inner.area.width || y >= self.inner.area.height {
            return Err(pyo3::exceptions::PyIndexError::new_err(format!(
                "position ({x}, {y}) out of bounds"
            )));
        }
        self.inner.set_string(x, y, string, style.inner);
        Ok(())
    }

    fn to_string_lines(&self) -> Vec<String> {
        let width = self.inner.area.width as usize;
        let height = self.inner.area.height as usize;
        let mut lines = Vec::with_capacity(height);
        for row in 0..height {
            let mut line = String::with_capacity(width);
            for col in 0..width {
                let symbol = self.inner[(col as u16, row as u16)].symbol();
                if symbol.is_empty() {
                    line.push(' ');
                } else {
                    line.push_str(symbol);
                }
            }
            lines.push(line.trim_end().to_string());
        }
        lines
    }

    fn __repr__(&self) -> String {
        format!(
            "Buffer(area={}, cells={})",
            self.inner.area,
            self.inner.content.len()
        )
    }

    #[pyo3(signature = (clip_bottom=false))]
    fn to_ansi_lines(&self, clip_bottom: bool) -> Vec<String> {
        let width = self.inner.area.width as usize;
        let height = self.inner.area.height as usize;

        let mut last_non_empty_row = height;
        if clip_bottom {
            for row in (0..height).rev() {
                let mut row_empty = true;
                for col in 0..width {
                    let cell = &self.inner[(col as u16, row as u16)];
                    let symbol = cell.symbol();
                    let is_blank = symbol.is_empty() || symbol == " ";
                    let is_default_style = cell.fg == Color::Reset && cell.bg == Color::Reset && cell.modifier.is_empty();
                    if !is_blank || !is_default_style {
                        row_empty = false;
                        break;
                    }
                }
                if !row_empty {
                    last_non_empty_row = row + 1;
                    break;
                }
            }
            if last_non_empty_row == height {
                let mut all_empty = true;
                for row in 0..height {
                    for col in 0..width {
                        let cell = &self.inner[(col as u16, row as u16)];
                        let symbol = cell.symbol();
                        let is_blank = symbol.is_empty() || symbol == " ";
                        let is_default_style = cell.fg == Color::Reset && cell.bg == Color::Reset && cell.modifier.is_empty();
                        if !is_blank || !is_default_style {
                            all_empty = false;
                            break;
                        }
                    }
                }
                if all_empty {
                    last_non_empty_row = 0;
                }
            }
        }

        let target_height = last_non_empty_row;
        let mut lines = Vec::with_capacity(target_height);

        for row in 0..target_height {
            let mut line = String::new();

            let mut last_active_col = width;
            for col in (0..width).rev() {
                let cell = &self.inner[(col as u16, row as u16)];
                let symbol = cell.symbol();
                let is_blank = symbol.is_empty() || symbol == " ";
                let is_default_style = cell.fg == Color::Reset && cell.bg == Color::Reset && cell.modifier.is_empty();
                if !is_blank || !is_default_style {
                    last_active_col = col + 1;
                    break;
                }
            }
            if last_active_col == width {
                let mut all_empty = true;
                for col in 0..width {
                    let cell = &self.inner[(col as u16, row as u16)];
                    let symbol = cell.symbol();
                    let is_blank = symbol.is_empty() || symbol == " ";
                    let is_default_style = cell.fg == Color::Reset && cell.bg == Color::Reset && cell.modifier.is_empty();
                    if !is_blank || !is_default_style {
                        all_empty = false;
                        break;
                    }
                }
                if all_empty {
                    last_active_col = 0;
                }
            }

            let mut current_fg = Color::Reset;
            let mut current_bg = Color::Reset;
            let mut current_modifier = Modifier::empty();

            for col in 0..last_active_col {
                let cell = &self.inner[(col as u16, row as u16)];

                let fg_changed = cell.fg != current_fg;
                let bg_changed = cell.bg != current_bg;
                let mod_changed = cell.modifier != current_modifier;

                if fg_changed || bg_changed || mod_changed {
                    if mod_changed && !cell.modifier.contains(current_modifier) {
                        line.push_str("\x1b[0m");
                        current_fg = Color::Reset;
                        current_bg = Color::Reset;
                        current_modifier = Modifier::empty();
                    }

                    if cell.fg != current_fg {
                        line.push_str(&color_to_ansi_fg(cell.fg));
                        current_fg = cell.fg;
                    }
                    if cell.bg != current_bg {
                        line.push_str(&color_to_ansi_bg(cell.bg));
                        current_bg = cell.bg;
                    }
                    if cell.modifier != current_modifier {
                        line.push_str(&modifier_to_ansi(cell.modifier));
                        current_modifier = cell.modifier;
                    }
                }

                let symbol = cell.symbol();
                if symbol.is_empty() {
                    line.push(' ');
                } else {
                    line.push_str(symbol);
                }
            }

            line.push_str("\x1b[0m");
            lines.push(line);
        }
        lines
    }
}

fn color_to_ansi_fg(color: Color) -> String {
    match color {
        Color::Reset => "\x1b[39m".to_string(),
        Color::Black => "\x1b[30m".to_string(),
        Color::Red => "\x1b[31m".to_string(),
        Color::Green => "\x1b[32m".to_string(),
        Color::Yellow => "\x1b[33m".to_string(),
        Color::Blue => "\x1b[34m".to_string(),
        Color::Magenta => "\x1b[35m".to_string(),
        Color::Cyan => "\x1b[36m".to_string(),
        Color::Gray => "\x1b[37m".to_string(),
        Color::DarkGray => "\x1b[90m".to_string(),
        Color::LightRed => "\x1b[91m".to_string(),
        Color::LightGreen => "\x1b[92m".to_string(),
        Color::LightYellow => "\x1b[93m".to_string(),
        Color::LightBlue => "\x1b[94m".to_string(),
        Color::LightMagenta => "\x1b[95m".to_string(),
        Color::LightCyan => "\x1b[96m".to_string(),
        Color::White => "\x1b[97m".to_string(),
        Color::Rgb(r, g, b) => format!("\x1b[38;2;{};{};{}m", r, g, b),
        Color::Indexed(i) => format!("\x1b[38;5;{}m", i),
    }
}

fn color_to_ansi_bg(color: Color) -> String {
    match color {
        Color::Reset => "\x1b[49m".to_string(),
        Color::Black => "\x1b[40m".to_string(),
        Color::Red => "\x1b[41m".to_string(),
        Color::Green => "\x1b[42m".to_string(),
        Color::Yellow => "\x1b[43m".to_string(),
        Color::Blue => "\x1b[44m".to_string(),
        Color::Magenta => "\x1b[45m".to_string(),
        Color::Cyan => "\x1b[46m".to_string(),
        Color::Gray => "\x1b[47m".to_string(),
        Color::DarkGray => "\x1b[100m".to_string(),
        Color::LightRed => "\x1b[101m".to_string(),
        Color::LightGreen => "\x1b[102m".to_string(),
        Color::LightYellow => "\x1b[103m".to_string(),
        Color::LightBlue => "\x1b[104m".to_string(),
        Color::LightMagenta => "\x1b[105m".to_string(),
        Color::LightCyan => "\x1b[106m".to_string(),
        Color::White => "\x1b[107m".to_string(),
        Color::Rgb(r, g, b) => format!("\x1b[48;2;{};{};{}m", r, g, b),
        Color::Indexed(i) => format!("\x1b[48;5;{}m", i),
    }
}

fn modifier_to_ansi(modifier: Modifier) -> String {
    let mut parts = Vec::new();
    if modifier.contains(Modifier::BOLD) {
        parts.push("1");
    }
    if modifier.contains(Modifier::DIM) {
        parts.push("2");
    }
    if modifier.contains(Modifier::ITALIC) {
        parts.push("3");
    }
    if modifier.contains(Modifier::UNDERLINED) {
        parts.push("4");
    }
    if modifier.contains(Modifier::REVERSED) {
        parts.push("7");
    }
    if modifier.contains(Modifier::HIDDEN) {
        parts.push("8");
    }
    if modifier.contains(Modifier::CROSSED_OUT) {
        parts.push("9");
    }
    if parts.is_empty() {
        "".to_string()
    } else {
        format!("\x1b[{}m", parts.join(";"))
    }
}

/// Mutable view onto a live buffer, valid only for the duration of a drawable callback.
#[pyclass(name = "BufferMutView", module = "xnano_core.rust.native", unsendable, from_py_object)]
#[derive(Clone)]
pub struct PyBufferMutView {
    ptr: usize,
    alive: Rc<StdCell<bool>>,
}

impl PyBufferMutView {
    pub fn wrap(buffer: &mut Buffer) -> Self {
        Self {
            ptr: buffer as *mut Buffer as usize,
            alive: Rc::new(StdCell::new(true)),
        }
    }

    pub fn invalidate(&self) {
        self.alive.set(false);
    }

    /// Run `f` against the wrapped buffer while the view is still alive.
    ///
    /// The mutable borrow is scoped to the closure rather than returned
    /// from `&self`, so the pointer-backed access stays sound by
    /// construction: the view is `unsendable` and the borrow can never
    /// outlive this call.
    fn with_buffer_mut<R>(
        &self,
        f: impl FnOnce(&mut Buffer) -> PyResult<R>,
    ) -> PyResult<R> {
        if !self.alive.get() {
            return Err(PyRuntimeError::new_err("BufferMutView expired"));
        }
        // SAFETY: `ptr` points at the live buffer for the duration of the
        // drawable callback; `alive` is flipped before it dangles.
        f(unsafe { &mut *(self.ptr as *mut Buffer) })
    }
}

#[pymethods]
impl PyBufferMutView {
    fn get_area(&self) -> PyResult<PyRect> {
        self.with_buffer_mut(|buffer| Ok(PyRect { inner: buffer.area }))
    }

    fn area(&self) -> PyResult<PyRect> {
        self.get_area()
    }

    fn get_cell(&self, x: u16, y: u16) -> PyResult<Option<PyBufferCell>> {
        self.with_buffer_mut(|buffer| {
            check_local_coords(buffer, x, y)?;
            let position = local_position(buffer, x, y);
            Ok(buffer
                .cell(position)
                .map(|cell| PyBufferCell { inner: cell.clone() }))
        })
    }

    fn set_cell(
        &self,
        x: u16,
        y: u16,
        symbol: &str,
        style: PyStyle,
    ) -> PyResult<()> {
        self.with_buffer_mut(|buffer| {
            check_local_coords(buffer, x, y)?;
            let position = local_position(buffer, x, y);
            if let Some(cell) = buffer.cell_mut(position) {
                cell.set_symbol(symbol).set_style(style.inner);
                Ok(())
            } else {
                Err(pyo3::exceptions::PyIndexError::new_err(format!(
                    "position ({x}, {y}) out of bounds"
                )))
            }
        })
    }

    fn set_string(
        &self,
        x: u16,
        y: u16,
        string: &str,
        style: PyStyle,
    ) -> PyResult<()> {
        self.with_buffer_mut(|buffer| {
            if x >= buffer.area.width || y >= buffer.area.height {
                return Err(pyo3::exceptions::PyIndexError::new_err(format!(
                    "position ({x}, {y}) out of bounds"
                )));
            }
            buffer.set_string(x, y, string, style.inner);
            Ok(())
        })
    }

    fn set_style(&self, area: PyRect, style: PyStyle) -> PyResult<()> {
        self.with_buffer_mut(|buffer| {
            buffer.set_style(area.inner, style.inner);
            Ok(())
        })
    }
}

/// Render any supported widget into a buffer region.
#[pyfunction]
pub fn render_widget(
    widget: &Bound<'_, PyAny>,
    area: PyRect,
    buffer: &mut PyBuffer,
) -> PyResult<()> {
    render_widget_inner(widget, area, &mut buffer.inner)
}

/// Render any supported stateful widget into a buffer region.
#[pyfunction]
pub fn render_stateful_widget(
    widget: &Bound<'_, PyAny>,
    area: PyRect,
    state: &Bound<'_, PyAny>,
    buffer: &mut PyBuffer,
) -> PyResult<()> {
    render_stateful_inner(widget, area, state, &mut buffer.inner)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyBufferCell>()?;
    m.add_class::<PyBuffer>()?;
    m.add_class::<PyBufferMutView>()?;
    m.add_function(wrap_pyfunction!(render_widget, m)?)?;
    m.add_function(wrap_pyfunction!(render_stateful_widget, m)?)?;
    Ok(())
}
