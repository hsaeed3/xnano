use crossterm::terminal::{
    disable_raw_mode as ct_disable_raw_mode,
    enable_raw_mode as ct_enable_raw_mode,
    is_raw_mode_enabled as ct_is_raw_mode_enabled,
    size,
    supports_keyboard_enhancement as ct_supports_keyboard_enhancement,
    window_size, BeginSynchronizedUpdate, Clear, ClearType, DisableLineWrap, EnableLineWrap,
    EndSynchronizedUpdate, EnterAlternateScreen, LeaveAlternateScreen, ScrollDown, ScrollUp,
    SetTitle,
};
use pyo3::prelude::*;

use super::crossterm_exec::{execute_stdout, io_to_py};
use super::layout::PySize;

#[pyclass(name = "ClearType", module = "xnano_core._xnano_core", eq, eq_int)]
#[derive(Clone, Copy, PartialEq, Debug)]
pub enum PyClearType {
    All,
    Purge,
    FromCursorDown,
    FromCursorUp,
    CurrentLine,
    UntilNewLine,
}

impl From<PyClearType> for ClearType {
    fn from(value: PyClearType) -> Self {
        match value {
            PyClearType::All => ClearType::All,
            PyClearType::Purge => ClearType::Purge,
            PyClearType::FromCursorDown => ClearType::FromCursorDown,
            PyClearType::FromCursorUp => ClearType::FromCursorUp,
            PyClearType::CurrentLine => ClearType::CurrentLine,
            PyClearType::UntilNewLine => ClearType::UntilNewLine,
        }
    }
}

#[pyfunction]
fn enable_raw_mode() -> PyResult<()> {
    ct_enable_raw_mode().map_err(io_to_py)
}

#[pyfunction]
fn disable_raw_mode() -> PyResult<()> {
    ct_disable_raw_mode().map_err(io_to_py)
}

#[pyfunction]
fn is_raw_mode_enabled() -> PyResult<bool> {
    ct_is_raw_mode_enabled().map_err(io_to_py)
}

#[pyfunction]
fn terminal_size() -> PyResult<PySize> {
    let (width, height) = size().map_err(io_to_py)?;
    Ok(PySize {
        inner: ratatui::layout::Size::new(width, height),
    })
}

#[pyfunction]
fn terminal_window_size() -> PyResult<PySize> {
    let window = window_size().map_err(io_to_py)?;
    Ok(PySize {
        inner: ratatui::layout::Size::new(window.columns, window.rows),
    })
}

#[pyfunction]
#[pyo3(signature = (count=1))]
fn scroll_up(count: u16) -> PyResult<()> {
    execute_stdout(ScrollUp(count))
}

#[pyfunction]
#[pyo3(signature = (count=1))]
fn scroll_down(count: u16) -> PyResult<()> {
    execute_stdout(ScrollDown(count))
}

#[pyfunction]
fn clear_terminal(clear_type: PyClearType) -> PyResult<()> {
    execute_stdout(Clear(clear_type.into()))
}

#[pyfunction]
fn enter_alternate_screen() -> PyResult<()> {
    execute_stdout(EnterAlternateScreen)
}

#[pyfunction]
fn leave_alternate_screen() -> PyResult<()> {
    execute_stdout(LeaveAlternateScreen)
}

#[pyfunction]
fn set_terminal_title(title: &str) -> PyResult<()> {
    execute_stdout(SetTitle(title))
}

#[pyfunction]
fn enable_line_wrap() -> PyResult<()> {
    execute_stdout(EnableLineWrap)
}

#[pyfunction]
fn disable_line_wrap() -> PyResult<()> {
    execute_stdout(DisableLineWrap)
}

#[pyfunction]
fn begin_synchronized_update() -> PyResult<()> {
    execute_stdout(BeginSynchronizedUpdate)
}

#[pyfunction]
fn end_synchronized_update() -> PyResult<()> {
    execute_stdout(EndSynchronizedUpdate)
}

#[pyfunction]
fn supports_keyboard_enhancement() -> PyResult<bool> {
    ct_supports_keyboard_enhancement().map_err(io_to_py)
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyClearType>()?;
    m.add_function(wrap_pyfunction!(enable_raw_mode, m)?)?;
    m.add_function(wrap_pyfunction!(disable_raw_mode, m)?)?;
    m.add_function(wrap_pyfunction!(is_raw_mode_enabled, m)?)?;
    m.add_function(wrap_pyfunction!(terminal_size, m)?)?;
    m.add_function(wrap_pyfunction!(terminal_window_size, m)?)?;
    m.add_function(wrap_pyfunction!(scroll_up, m)?)?;
    m.add_function(wrap_pyfunction!(scroll_down, m)?)?;
    m.add_function(wrap_pyfunction!(clear_terminal, m)?)?;
    m.add_function(wrap_pyfunction!(enter_alternate_screen, m)?)?;
    m.add_function(wrap_pyfunction!(leave_alternate_screen, m)?)?;
    m.add_function(wrap_pyfunction!(set_terminal_title, m)?)?;
    m.add_function(wrap_pyfunction!(enable_line_wrap, m)?)?;
    m.add_function(wrap_pyfunction!(disable_line_wrap, m)?)?;
    m.add_function(wrap_pyfunction!(begin_synchronized_update, m)?)?;
    m.add_function(wrap_pyfunction!(end_synchronized_update, m)?)?;
    m.add_function(wrap_pyfunction!(supports_keyboard_enhancement, m)?)?;
    Ok(())
}