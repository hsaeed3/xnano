use pyo3::prelude::*;
use ratatui::buffer::Buffer;
use ratatui::widgets::{Clear, StatefulWidget, Widget};

use super::layout::PyRect;
use super::style::{PyColor, PyModifier, PyStyle};
use super::text::{PyLine, PySpan, PyText};
use super::widgets::{PyBlock, PyClear, PyGauge, PyListState, PyRatList, PyParagraph};
use super::widgets_extra::{
    PyBarChart, PyLineGauge, PyRatTable, PyScrollbar, PyScrollbarState, PySparkline, PyTableState,
    PyTabs,
};

#[pyclass(name = "Buffer", module = "xnano_core._xnano_core")]
pub struct PyBuffer {
    pub inner: Buffer,
}

pub fn render_widget_inner(
    widget: &Bound<'_, PyAny>,
    area: PyRect,
    buffer: &mut Buffer,
) -> PyResult<()> {
    if let Ok(paragraph) = widget.extract::<PyRef<PyParagraph>>() {
        paragraph.inner.clone().render(area.inner, buffer);
        return Ok(());
    }
    if let Ok(block) = widget.extract::<PyRef<PyBlock>>() {
        block.inner.clone().render(area.inner, buffer);
        return Ok(());
    }
    if let Ok(list) = widget.extract::<PyRef<PyRatList>>() {
        Widget::render(list.inner.clone(), area.inner, buffer);
        return Ok(());
    }
    if let Ok(table) = widget.extract::<PyRef<PyRatTable>>() {
        Widget::render(table.inner.clone(), area.inner, buffer);
        return Ok(());
    }
    if let Ok(gauge) = widget.extract::<PyRef<PyGauge>>() {
        gauge.inner.clone().render(area.inner, buffer);
        return Ok(());
    }
    if let Ok(tabs) = widget.extract::<PyRef<PyTabs>>() {
        tabs.inner.clone().render(area.inner, buffer);
        return Ok(());
    }
    if let Ok(sparkline) = widget.extract::<PyRef<PySparkline>>() {
        sparkline.inner.clone().render(area.inner, buffer);
        return Ok(());
    }
    if let Ok(line_gauge) = widget.extract::<PyRef<PyLineGauge>>() {
        line_gauge.inner.clone().render(area.inner, buffer);
        return Ok(());
    }
    if let Ok(bar_chart) = widget.extract::<PyRef<PyBarChart>>() {
        bar_chart.inner.clone().render(area.inner, buffer);
        return Ok(());
    }
    if widget.is_instance_of::<PyClear>() {
        Clear.render(area.inner, buffer);
        return Ok(());
    }
    if let Ok(span) = widget.extract::<PyRef<PySpan>>() {
        span.inner.clone().render(area.inner, buffer);
        return Ok(());
    }
    if let Ok(line) = widget.extract::<PyRef<PyLine>>() {
        line.inner.clone().render(area.inner, buffer);
        return Ok(());
    }
    if let Ok(text) = widget.extract::<PyRef<PyText>>() {
        text.inner.clone().render(area.inner, buffer);
        return Ok(());
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
    m.add_class::<PyBuffer>()?;
    m.add_function(wrap_pyfunction!(render_widget, m)?)?;
    m.add_function(wrap_pyfunction!(render_stateful_widget, m)?)?;
    Ok(())
}