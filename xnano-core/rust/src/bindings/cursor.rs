use crossterm::cursor::{
    position, DisableBlinking, EnableBlinking, Hide, MoveDown, MoveLeft, MoveRight, MoveTo,
    MoveToColumn, MoveToNextLine, MoveToPreviousLine, MoveToRow, MoveUp, RestorePosition,
    SavePosition, SetCursorStyle, Show,
};
use pyo3::prelude::*;

use super::crossterm_exec::{execute_stdout, io_to_py};
use super::widgets_extra::PyPosition;

#[pyclass(name = "CursorStyle", module = "xnano_core.rust.native", eq, eq_int, from_py_object)]
#[derive(Clone, Copy, PartialEq, Debug)]
pub enum PyCursorStyle {
    DefaultUserShape,
    BlinkingBlock,
    SteadyBlock,
    BlinkingUnderline,
    SteadyUnderline,
    BlinkingBar,
    SteadyBar,
}

impl From<PyCursorStyle> for SetCursorStyle {
    fn from(value: PyCursorStyle) -> Self {
        match value {
            PyCursorStyle::DefaultUserShape => SetCursorStyle::DefaultUserShape,
            PyCursorStyle::BlinkingBlock => SetCursorStyle::BlinkingBlock,
            PyCursorStyle::SteadyBlock => SetCursorStyle::SteadyBlock,
            PyCursorStyle::BlinkingUnderline => SetCursorStyle::BlinkingUnderScore,
            PyCursorStyle::SteadyUnderline => SetCursorStyle::SteadyUnderScore,
            PyCursorStyle::BlinkingBar => SetCursorStyle::BlinkingBar,
            PyCursorStyle::SteadyBar => SetCursorStyle::SteadyBar,
        }
    }
}

pub(crate) fn show_cursor_impl() -> PyResult<()> {
    execute_stdout(Show)
}

pub(crate) fn hide_cursor_impl() -> PyResult<()> {
    execute_stdout(Hide)
}

pub(crate) fn save_cursor_position_impl() -> PyResult<()> {
    execute_stdout(SavePosition)
}

pub(crate) fn restore_cursor_position_impl() -> PyResult<()> {
    execute_stdout(RestorePosition)
}

pub(crate) fn move_cursor_to_impl(x: u16, y: u16) -> PyResult<()> {
    execute_stdout(MoveTo(x, y))
}

pub(crate) fn move_cursor_to_column_impl(x: u16) -> PyResult<()> {
    execute_stdout(MoveToColumn(x))
}

pub(crate) fn move_cursor_to_row_impl(y: u16) -> PyResult<()> {
    execute_stdout(MoveToRow(y))
}

pub(crate) fn move_cursor_up_impl(count: u16) -> PyResult<()> {
    execute_stdout(MoveUp(count))
}

pub(crate) fn move_cursor_down_impl(count: u16) -> PyResult<()> {
    execute_stdout(MoveDown(count))
}

pub(crate) fn move_cursor_left_impl(count: u16) -> PyResult<()> {
    execute_stdout(MoveLeft(count))
}

pub(crate) fn move_cursor_right_impl(count: u16) -> PyResult<()> {
    execute_stdout(MoveRight(count))
}

pub(crate) fn move_cursor_to_next_line_impl(count: u16) -> PyResult<()> {
    execute_stdout(MoveToNextLine(count))
}

pub(crate) fn move_cursor_to_previous_line_impl(count: u16) -> PyResult<()> {
    execute_stdout(MoveToPreviousLine(count))
}

pub(crate) fn enable_cursor_blinking_impl() -> PyResult<()> {
    execute_stdout(EnableBlinking)
}

pub(crate) fn disable_cursor_blinking_impl() -> PyResult<()> {
    execute_stdout(DisableBlinking)
}

pub(crate) fn set_cursor_style_impl(style: PyCursorStyle) -> PyResult<()> {
    execute_stdout(SetCursorStyle::from(style))
}

pub(crate) fn get_cursor_position_impl() -> PyResult<PyPosition> {
    let (x, y) = position().map_err(io_to_py)?;
    Ok(PyPosition {
        inner: ratatui::layout::Position { x, y },
    })
}

#[pyfunction]
fn show_cursor() -> PyResult<()> {
    show_cursor_impl()
}

#[pyfunction]
fn hide_cursor() -> PyResult<()> {
    hide_cursor_impl()
}

#[pyfunction]
fn save_cursor_position() -> PyResult<()> {
    save_cursor_position_impl()
}

#[pyfunction]
fn restore_cursor_position() -> PyResult<()> {
    restore_cursor_position_impl()
}

#[pyfunction]
fn move_cursor_to(x: u16, y: u16) -> PyResult<()> {
    move_cursor_to_impl(x, y)
}

#[pyfunction]
fn move_cursor_to_column(x: u16) -> PyResult<()> {
    move_cursor_to_column_impl(x)
}

#[pyfunction]
fn move_cursor_to_row(y: u16) -> PyResult<()> {
    move_cursor_to_row_impl(y)
}

#[pyfunction]
#[pyo3(signature = (count=1))]
fn move_cursor_up(count: u16) -> PyResult<()> {
    move_cursor_up_impl(count)
}

#[pyfunction]
#[pyo3(signature = (count=1))]
fn move_cursor_down(count: u16) -> PyResult<()> {
    move_cursor_down_impl(count)
}

#[pyfunction]
#[pyo3(signature = (count=1))]
fn move_cursor_left(count: u16) -> PyResult<()> {
    move_cursor_left_impl(count)
}

#[pyfunction]
#[pyo3(signature = (count=1))]
fn move_cursor_right(count: u16) -> PyResult<()> {
    move_cursor_right_impl(count)
}

#[pyfunction]
#[pyo3(signature = (count=1))]
fn move_cursor_to_next_line(count: u16) -> PyResult<()> {
    move_cursor_to_next_line_impl(count)
}

#[pyfunction]
#[pyo3(signature = (count=1))]
fn move_cursor_to_previous_line(count: u16) -> PyResult<()> {
    move_cursor_to_previous_line_impl(count)
}

#[pyfunction]
fn enable_cursor_blinking() -> PyResult<()> {
    enable_cursor_blinking_impl()
}

#[pyfunction]
fn disable_cursor_blinking() -> PyResult<()> {
    disable_cursor_blinking_impl()
}

#[pyfunction]
fn set_cursor_style(style: PyCursorStyle) -> PyResult<()> {
    set_cursor_style_impl(style)
}

#[pyfunction]
fn get_cursor_position() -> PyResult<PyPosition> {
    get_cursor_position_impl()
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyCursorStyle>()?;
    m.add_function(wrap_pyfunction!(show_cursor, m)?)?;
    m.add_function(wrap_pyfunction!(hide_cursor, m)?)?;
    m.add_function(wrap_pyfunction!(save_cursor_position, m)?)?;
    m.add_function(wrap_pyfunction!(restore_cursor_position, m)?)?;
    m.add_function(wrap_pyfunction!(move_cursor_to, m)?)?;
    m.add_function(wrap_pyfunction!(move_cursor_to_column, m)?)?;
    m.add_function(wrap_pyfunction!(move_cursor_to_row, m)?)?;
    m.add_function(wrap_pyfunction!(move_cursor_up, m)?)?;
    m.add_function(wrap_pyfunction!(move_cursor_down, m)?)?;
    m.add_function(wrap_pyfunction!(move_cursor_left, m)?)?;
    m.add_function(wrap_pyfunction!(move_cursor_right, m)?)?;
    m.add_function(wrap_pyfunction!(move_cursor_to_next_line, m)?)?;
    m.add_function(wrap_pyfunction!(move_cursor_to_previous_line, m)?)?;
    m.add_function(wrap_pyfunction!(enable_cursor_blinking, m)?)?;
    m.add_function(wrap_pyfunction!(disable_cursor_blinking, m)?)?;
    m.add_function(wrap_pyfunction!(set_cursor_style, m)?)?;
    m.add_function(wrap_pyfunction!(get_cursor_position, m)?)?;
    Ok(())
}
