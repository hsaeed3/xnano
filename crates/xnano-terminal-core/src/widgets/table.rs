//! `Table`, `TableRow` and `TableCell`: rows and columns with a selection.

use xnano_terminal_runtime::layout::SizeRule;

use std::hash::{Hash, Hasher};
use std::sync::Arc;

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use xnano_terminal_runtime::buffer::BufferCore;
use xnano_terminal_runtime::dynamic::Dynamic;
use xnano_terminal_runtime::painter::Spec;
use xnano_terminal_runtime::widgets::Shared;
use xnano_terminal_runtime::widgets::list::{Selection, TextSource};
use xnano_terminal_runtime::widgets::style::StyleSpec;
use xnano_terminal_runtime::widgets::table::{CellSpec, FLEXES, RowSpec, TableSpec, WidthRule};

use crate::widgets::block::block_arg;
use crate::widgets::list::{
    BlockHolder, choice_arg, clamp_index, copy_frame_state, dynamic_usize, frame_of, selection_arg,
    selection_to_py, spacing_names, string_to_py, text_source_arg, text_source_to_py, usize_to_py,
};
use crate::widgets::style::{style_spec_arg, style_spec_to_py};
use crate::widgets::{
    Frame, PyWidget, dynamic_string, dynamic_to_py, dynamic_u16, repaint, widget_initializer,
};

fn hash_of(key: &str) -> u64 {
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    key.hash(&mut hasher);
    hasher.finish()
}

/// One cell of a table row.
#[pyclass(
    name = "TableCell",
    module = "xnano._xnano_core",
    frozen,
    from_py_object
)]
#[derive(Clone)]
pub struct PyTableCell {
    pub spec: CellSpec,
}

fn cell_arg(value: &Bound<'_, PyAny>) -> PyResult<CellSpec> {
    if let Ok(cell) = value.extract::<PyTableCell>() {
        return Ok(cell.spec);
    }
    Ok(CellSpec {
        content: text_source_arg(value)?,
        style: StyleSpec::default(),
        column_span: 1,
    })
}

#[pymethods]
impl PyTableCell {
    #[new]
    #[pyo3(signature = (content, *, style = None, column_span = 1))]
    fn new(
        content: &Bound<'_, PyAny>,
        style: Option<&Bound<'_, PyAny>>,
        column_span: u16,
    ) -> PyResult<Self> {
        if column_span == 0 {
            return Err(PyValueError::new_err(
                "a cell spans at least one column; use column_span=1 or more",
            ));
        }
        Ok(Self {
            spec: CellSpec {
                content: text_source_arg(content)?,
                style: style_spec_arg(style)?,
                column_span,
            },
        })
    }

    #[getter]
    fn content(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        text_source_to_py(py, &self.spec.content)
    }

    #[getter]
    fn style(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        style_spec_to_py(py, &self.spec.style)
    }

    #[getter]
    fn column_span(&self) -> u16 {
        self.spec.column_span
    }

    fn __repr__(&self) -> String {
        match self.spec.content.plain_text() {
            Some(text) => format!("TableCell({text:?})"),
            None => "TableCell(<bound text>)".to_owned(),
        }
    }

    fn __eq__(&self, other: &Bound<'_, PyAny>) -> bool {
        other
            .extract::<PyRef<'_, Self>>()
            .is_ok_and(|other| self.spec.key() == other.spec.key())
    }

    fn __hash__(&self) -> u64 {
        hash_of(&self.spec.key())
    }

    fn __copy__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __deepcopy__<'py>(slf: PyRef<'py, Self>, _memo: &Bound<'py, PyAny>) -> PyRef<'py, Self> {
        slf
    }
}

/// One row of a table.
#[pyclass(
    name = "TableRow",
    module = "xnano._xnano_core",
    frozen,
    from_py_object
)]
#[derive(Clone)]
pub struct PyTableRow {
    pub spec: RowSpec,
}

fn row_arg(value: &Bound<'_, PyAny>) -> PyResult<RowSpec> {
    if let Ok(row) = value.extract::<PyTableRow>() {
        return Ok(row.spec);
    }
    let mut cells = Vec::new();
    for cell in value.try_iter().map_err(|_| {
        PyTypeError::new_err("a row is a TableRow or a sequence of cells (text or TableCell)")
    })? {
        cells.push(cell_arg(&cell?)?);
    }
    Ok(RowSpec {
        cells,
        height: 1,
        top_margin: 0,
        bottom_margin: 0,
        style: StyleSpec::default(),
    })
}

#[pymethods]
impl PyTableRow {
    #[new]
    #[pyo3(signature = (cells, *, height = 1, top_margin = 0, bottom_margin = 0, style = None))]
    fn new(
        cells: &Bound<'_, PyAny>,
        height: u16,
        top_margin: u16,
        bottom_margin: u16,
        style: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Self> {
        let mut spec = row_arg(cells)?;
        spec.height = height;
        spec.top_margin = top_margin;
        spec.bottom_margin = bottom_margin;
        spec.style = style_spec_arg(style)?;
        Ok(Self { spec })
    }

    #[getter]
    fn cells(&self) -> Vec<PyTableCell> {
        self.spec
            .cells
            .iter()
            .map(|spec| PyTableCell { spec: spec.clone() })
            .collect()
    }

    #[getter]
    fn height(&self) -> u16 {
        self.spec.height
    }

    #[getter]
    fn top_margin(&self) -> u16 {
        self.spec.top_margin
    }

    #[getter]
    fn bottom_margin(&self) -> u16 {
        self.spec.bottom_margin
    }

    #[getter]
    fn style(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        style_spec_to_py(py, &self.spec.style)
    }

    fn __repr__(&self) -> String {
        format!(
            "TableRow({} cells, height={})",
            self.spec.cells.len(),
            self.spec.height
        )
    }

    fn __eq__(&self, other: &Bound<'_, PyAny>) -> bool {
        other
            .extract::<PyRef<'_, Self>>()
            .is_ok_and(|other| self.spec.key() == other.spec.key())
    }

    fn __hash__(&self) -> u64 {
        hash_of(&self.spec.key())
    }

    fn __copy__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __deepcopy__<'py>(slf: PyRef<'py, Self>, _memo: &Bound<'py, PyAny>) -> PyRef<'py, Self> {
        slf
    }
}

fn width_arg(value: &Bound<'_, PyAny>) -> PyResult<WidthRule> {
    if let Ok(length) = value.extract::<u16>() {
        return Ok(WidthRule::Length(length));
    }
    if let Ok((numerator, denominator)) = value.extract::<(u32, u32)>() {
        if denominator == 0 {
            return Err(PyValueError::new_err(
                "a ratio needs a denominator above zero, for example (1, 3)",
            ));
        }
        return Ok(WidthRule::Ratio(numerator, denominator));
    }
    let rule = value.extract::<crate::layout::PySizeRule>().map_err(|_| {
        PyTypeError::new_err(
            "a column width is a whole number of cells, a (numerator, denominator) ratio or a SizeRule",
        )
    })?;
    match rule.rule() {
        SizeRule::Cells(amount) => Ok(WidthRule::Length(amount)),
        SizeRule::Percent(amount) => Ok(WidthRule::Percentage(amount)),
        SizeRule::Fill(weight) => Ok(WidthRule::Fill(weight)),
        SizeRule::Minimum(amount) => Ok(WidthRule::Minimum(amount)),
        SizeRule::Maximum(amount) => Ok(WidthRule::Maximum(amount)),
        SizeRule::Fit => Err(PyValueError::new_err(
            "SizeRule.fit() has no meaning for a table column; use cells, percent, fill, minimum or maximum",
        )),
    }
}

fn width_to_py(py: Python<'_>, rule: WidthRule) -> PyResult<Py<PyAny>> {
    use pyo3::IntoPyObjectExt;
    match rule {
        WidthRule::Length(amount) => amount.into_py_any(py),
        WidthRule::Ratio(numerator, denominator) => (numerator, denominator).into_py_any(py),
        WidthRule::Percentage(amount) => {
            Py::new(py, crate::layout::PySizeRule::percent_rule(amount))?.into_py_any(py)
        }
        WidthRule::Fill(amount) => {
            Py::new(py, crate::layout::PySizeRule::fill_rule(amount))?.into_py_any(py)
        }
        WidthRule::Minimum(amount) => {
            Py::new(py, crate::layout::PySizeRule::minimum_rule(amount))?.into_py_any(py)
        }
        WidthRule::Maximum(amount) => {
            Py::new(py, crate::layout::PySizeRule::maximum_rule(amount))?.into_py_any(py)
        }
    }
}

/// A table of rows with a header, a footer and a selection.
#[pyclass(name = "Table", module = "xnano._xnano_core", extends = PyWidget, subclass)]
pub struct PyTable {
    spec: Shared<TableSpec>,
    block: BlockHolder,
}

impl PyTable {
    fn core(slf: &Bound<'_, Self>) -> Arc<BufferCore> {
        Arc::clone(&slf.as_super().as_super().as_super().borrow().core)
    }

    fn edit<R>(slf: &Bound<'_, Self>, change: impl FnOnce(&mut TableSpec) -> R) -> R {
        let result = slf.borrow().spec.edit(change);
        repaint(&Self::core(slf));
        result
    }

    fn move_selection(
        slf: &Bound<'_, Self>,
        is_column: bool,
        change: impl FnOnce(Option<usize>, usize) -> Option<usize>,
    ) -> PyResult<()> {
        let outcome = slf.borrow().spec.edit(|spec| {
            let count = if is_column {
                spec.column_count()
            } else {
                spec.rows.len()
            };
            let slot = if is_column {
                &mut spec.selected_column
            } else {
                &mut spec.selected_row
            };
            match slot {
                Dynamic::Fixed(selection) => {
                    *slot = Dynamic::Fixed(Selection(change(selection.0, count)));
                    Ok(())
                }
                Dynamic::Bound(_) => Err(PyValueError::new_err(
                    "the selection follows an expression, so it cannot be moved by hand. Assign a \
                     plain position first, or change the state the expression reads.",
                )),
            }
        });
        repaint(&Self::core(slf));
        outcome
    }
}

#[pymethods]
impl PyTable {
    #[new]
    #[pyo3(signature = (rows = None, *, header = None, footer = None, widths = None,
        column_spacing = None, flex = None, selected_row = None, selected_column = None,
        offset = None, style = None, row_highlight_style = None, column_highlight_style = None,
        cell_highlight_style = None, highlight_symbol = None, highlight_spacing = None,
        block = None, width = None, height = None, x = 0, y = 0))]
    fn new(
        rows: Option<&Bound<'_, PyAny>>,
        header: Option<&Bound<'_, PyAny>>,
        footer: Option<&Bound<'_, PyAny>>,
        widths: Option<&Bound<'_, PyAny>>,
        column_spacing: Option<&Bound<'_, PyAny>>,
        flex: Option<&Bound<'_, PyAny>>,
        selected_row: Option<&Bound<'_, PyAny>>,
        selected_column: Option<&Bound<'_, PyAny>>,
        offset: Option<&Bound<'_, PyAny>>,
        style: Option<&Bound<'_, PyAny>>,
        row_highlight_style: Option<&Bound<'_, PyAny>>,
        column_highlight_style: Option<&Bound<'_, PyAny>>,
        cell_highlight_style: Option<&Bound<'_, PyAny>>,
        highlight_symbol: Option<&Bound<'_, PyAny>>,
        highlight_spacing: Option<&Bound<'_, PyAny>>,
        block: Option<&Bound<'_, PyAny>>,
        width: Option<i32>,
        height: Option<i32>,
        x: i32,
        y: i32,
    ) -> PyResult<PyClassInitializer<Self>> {
        let mut spec = TableSpec::default();
        if let Some(rows) = rows.filter(|value| !value.is_none()) {
            for row in rows.try_iter()? {
                spec.rows.push(row_arg(&row?)?);
            }
        }
        spec.header = header
            .filter(|value| !value.is_none())
            .map(row_arg)
            .transpose()?;
        spec.footer = footer
            .filter(|value| !value.is_none())
            .map(row_arg)
            .transpose()?;
        if let Some(widths) = widths.filter(|value| !value.is_none()) {
            for item in widths.try_iter()? {
                spec.widths.push(width_arg(&item?)?);
            }
        }
        if let Some(spacing) = column_spacing.filter(|value| !value.is_none()) {
            spec.column_spacing = dynamic_u16(spacing)?;
        }
        if let Some(flex) = flex.filter(|value| !value.is_none()) {
            let names: Vec<&str> = FLEXES.iter().map(|(name, _)| *name).collect();
            spec.flex = choice_arg(flex, "flex mode", &names)?;
        }
        spec.selected_row = selection_arg(selected_row)?;
        spec.selected_column = selection_arg(selected_column)?;
        if let Some(offset) = offset.filter(|value| !value.is_none()) {
            spec.offset = dynamic_usize(offset)?;
        }
        spec.style = style_spec_arg(style)?;
        spec.row_highlight_style = style_spec_arg(row_highlight_style)?;
        spec.column_highlight_style = style_spec_arg(column_highlight_style)?;
        spec.cell_highlight_style = style_spec_arg(cell_highlight_style)?;
        if let Some(symbol) = highlight_symbol.filter(|value| !value.is_none()) {
            spec.highlight_symbol = dynamic_string(symbol)?;
        }
        if let Some(spacing) = highlight_spacing.filter(|value| !value.is_none()) {
            spec.highlight_spacing = choice_arg(spacing, "highlight spacing", &spacing_names())?;
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
            (30, 6),
        )?;
        Ok(initializer.add_subclass(Self {
            spec: shared,
            block: holder,
        }))
    }

    #[getter]
    fn rows(slf: &Bound<'_, Self>) -> Vec<PyTableRow> {
        slf.borrow()
            .spec
            .read()
            .rows
            .iter()
            .map(|spec| PyTableRow { spec: spec.clone() })
            .collect()
    }

    #[setter]
    fn set_rows(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let mut rows = Vec::new();
        for row in value.try_iter()? {
            rows.push(row_arg(&row?)?);
        }
        Self::edit(slf, |spec| spec.rows = rows);
        Ok(())
    }

    /// Add one row at the end.
    fn append_row(slf: &Bound<'_, Self>, row: &Bound<'_, PyAny>) -> PyResult<()> {
        let row = row_arg(row)?;
        Self::edit(slf, |spec| spec.rows.push(row));
        Ok(())
    }

    /// Remove every row (the header and footer stay).
    fn clear_rows(slf: &Bound<'_, Self>) {
        Self::edit(slf, |spec| spec.rows.clear());
    }

    #[getter]
    fn header(slf: &Bound<'_, Self>) -> Option<PyTableRow> {
        slf.borrow()
            .spec
            .read()
            .header
            .clone()
            .map(|spec| PyTableRow { spec })
    }

    #[setter]
    fn set_header(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let header = value
            .filter(|value| !value.is_none())
            .map(row_arg)
            .transpose()?;
        Self::edit(slf, |spec| spec.header = header);
        Ok(())
    }

    #[getter]
    fn footer(slf: &Bound<'_, Self>) -> Option<PyTableRow> {
        slf.borrow()
            .spec
            .read()
            .footer
            .clone()
            .map(|spec| PyTableRow { spec })
    }

    #[setter]
    fn set_footer(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let footer = value
            .filter(|value| !value.is_none())
            .map(row_arg)
            .transpose()?;
        Self::edit(slf, |spec| spec.footer = footer);
        Ok(())
    }

    /// Column widths: whole cells, a ``(numerator, denominator)`` ratio or a ``SizeRule``.
    #[getter]
    fn widths(slf: &Bound<'_, Self>) -> PyResult<Vec<Py<PyAny>>> {
        let widths = slf.borrow().spec.read().widths.clone();
        widths
            .into_iter()
            .map(|rule| width_to_py(slf.py(), rule))
            .collect()
    }

    #[setter]
    fn set_widths(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let mut widths = Vec::new();
        for item in value.try_iter()? {
            widths.push(width_arg(&item?)?);
        }
        Self::edit(slf, |spec| spec.widths = widths);
        Ok(())
    }

    #[getter]
    fn column_spacing<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().column_spacing.clone();
        dynamic_to_py(slf.py(), &value, |py, number| {
            Ok(number.into_pyobject(py)?.into_any())
        })
    }

    #[setter]
    fn set_column_spacing(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let spacing = dynamic_u16(value)?;
        Self::edit(slf, |spec| spec.column_spacing = spacing);
        Ok(())
    }

    #[getter]
    fn flex<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().flex.clone();
        string_to_py(slf.py(), &value)
    }

    #[setter]
    fn set_flex(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let names: Vec<&str> = FLEXES.iter().map(|(name, _)| *name).collect();
        let flex = choice_arg(value, "flex mode", &names)?;
        Self::edit(slf, |spec| spec.flex = flex);
        Ok(())
    }

    #[getter]
    fn selected_row<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().selected_row.clone();
        selection_to_py(slf.py(), &value)
    }

    #[setter]
    fn set_selected_row(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let selection = selection_arg(value)?;
        Self::edit(slf, |spec| spec.selected_row = selection);
        Ok(())
    }

    #[getter]
    fn selected_column<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let value = slf.borrow().spec.read().selected_column.clone();
        selection_to_py(slf.py(), &value)
    }

    #[setter]
    fn set_selected_column(
        slf: &Bound<'_, Self>,
        value: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<()> {
        let selection = selection_arg(value)?;
        Self::edit(slf, |spec| spec.selected_column = selection);
        Ok(())
    }

    /// The selected ``(row, column)``, or ``None`` unless both are selected plainly.
    #[getter]
    fn selected_cell(slf: &Bound<'_, Self>) -> Option<(usize, usize)> {
        let spec = slf.borrow().spec.read().clone();
        match (spec.selected_row.fixed(), spec.selected_column.fixed()) {
            (Some(Selection(Some(row))), Some(Selection(Some(column)))) => Some((*row, *column)),
            _ => None,
        }
    }

    #[setter]
    fn set_selected_cell(slf: &Bound<'_, Self>, value: Option<(usize, usize)>) {
        Self::edit(slf, |spec| {
            spec.selected_row = Dynamic::Fixed(Selection(value.map(|cell| cell.0)));
            spec.selected_column = Dynamic::Fixed(Selection(value.map(|cell| cell.1)));
        });
    }

    /// The first row the table scrolls from; assigning moves the view there.
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

    /// The first row shown and one past the last, from the latest paint.
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
    fn row_highlight_style(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let spec = slf.borrow().spec.read().row_highlight_style.clone();
        style_spec_to_py(slf.py(), &spec)
    }

    #[setter]
    fn set_row_highlight_style(
        slf: &Bound<'_, Self>,
        value: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<()> {
        let style = style_spec_arg(value)?;
        Self::edit(slf, |spec| spec.row_highlight_style = style);
        Ok(())
    }

    #[getter]
    fn column_highlight_style(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let spec = slf.borrow().spec.read().column_highlight_style.clone();
        style_spec_to_py(slf.py(), &spec)
    }

    #[setter]
    fn set_column_highlight_style(
        slf: &Bound<'_, Self>,
        value: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<()> {
        let style = style_spec_arg(value)?;
        Self::edit(slf, |spec| spec.column_highlight_style = style);
        Ok(())
    }

    #[getter]
    fn cell_highlight_style(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let spec = slf.borrow().spec.read().cell_highlight_style.clone();
        style_spec_to_py(slf.py(), &spec)
    }

    #[setter]
    fn set_cell_highlight_style(
        slf: &Bound<'_, Self>,
        value: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<()> {
        let style = style_spec_arg(value)?;
        Self::edit(slf, |spec| spec.cell_highlight_style = style);
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

    /// Select the next row, stopping at the last.
    fn select_next(slf: &Bound<'_, Self>) -> PyResult<()> {
        Self::move_selection(slf, false, |selected, count| {
            clamp_index(selected.map_or(0, |index| index.saturating_add(1)), count)
        })
    }

    /// Select the previous row, stopping at the first.
    fn select_previous(slf: &Bound<'_, Self>) -> PyResult<()> {
        Self::move_selection(slf, false, |selected, count| {
            clamp_index(
                selected.map_or(usize::MAX, |index| index.saturating_sub(1)),
                count,
            )
        })
    }

    fn select_first(slf: &Bound<'_, Self>) -> PyResult<()> {
        Self::move_selection(slf, false, |_, count| clamp_index(0, count))
    }

    fn select_last(slf: &Bound<'_, Self>) -> PyResult<()> {
        Self::move_selection(slf, false, |_, count| clamp_index(usize::MAX, count))
    }

    fn select_next_column(slf: &Bound<'_, Self>) -> PyResult<()> {
        Self::move_selection(slf, true, |selected, count| {
            clamp_index(selected.map_or(0, |index| index.saturating_add(1)), count)
        })
    }

    fn select_previous_column(slf: &Bound<'_, Self>) -> PyResult<()> {
        Self::move_selection(slf, true, |selected, count| {
            clamp_index(
                selected.map_or(usize::MAX, |index| index.saturating_sub(1)),
                count,
            )
        })
    }

    fn select_first_column(slf: &Bound<'_, Self>) -> PyResult<()> {
        Self::move_selection(slf, true, |_, count| clamp_index(0, count))
    }

    fn select_last_column(slf: &Bound<'_, Self>) -> PyResult<()> {
        Self::move_selection(slf, true, |_, count| clamp_index(usize::MAX, count))
    }

    fn scroll_down_by(slf: &Bound<'_, Self>, amount: u16) -> PyResult<()> {
        Self::move_selection(slf, false, |selected, count| {
            clamp_index(
                selected
                    .unwrap_or_default()
                    .saturating_add(usize::from(amount)),
                count,
            )
        })
    }

    fn scroll_up_by(slf: &Bound<'_, Self>, amount: u16) -> PyResult<()> {
        Self::move_selection(slf, false, |selected, count| {
            clamp_index(
                selected
                    .unwrap_or_default()
                    .saturating_sub(usize::from(amount)),
                count,
            )
        })
    }

    fn scroll_right_by(slf: &Bound<'_, Self>, amount: u16) -> PyResult<()> {
        Self::move_selection(slf, true, |selected, count| {
            clamp_index(
                selected
                    .unwrap_or_default()
                    .saturating_add(usize::from(amount)),
                count,
            )
        })
    }

    fn scroll_left_by(slf: &Bound<'_, Self>, amount: u16) -> PyResult<()> {
        Self::move_selection(slf, true, |selected, count| {
            clamp_index(
                selected
                    .unwrap_or_default()
                    .saturating_sub(usize::from(amount)),
                count,
            )
        })
    }

    /// A new table with the same settings, geometry and flags (children are not copied).
    fn copy(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let py = slf.py();
        let mut spec = slf.borrow().spec.read().clone();
        spec.feedback = xnano_terminal_runtime::widgets::list::FeedbackHandle::default();
        let source = Self::core(slf);
        let shared = Spec::new(spec);
        let initializer = widget_initializer(Arc::clone(&shared), frame_of(&source), (30, 6))?;
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
        let count = slf.borrow().spec.read().rows.len();
        let state = Self::core(slf).lock().bounds();
        format!(
            "Table({count} rows, width={}, height={})",
            state.width, state.height
        )
    }
}

#[allow(dead_code)]
type UnusedText = TextSource;

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyTableCell>()?;
    m.add_class::<PyTableRow>()?;
    m.add_class::<PyTable>()
}
