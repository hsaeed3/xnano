mod buffer;
mod command;
mod frame_ext;
mod convert;
mod convert_core;
mod crossterm_exec;
mod cursor;
mod event_setup;
mod fx;
mod layout;
mod palette;
mod style;
mod terminal;
mod terminal_device;
mod text;
mod widgets;
mod widgets_extra;

use pyo3::prelude::*;

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    layout::register(m)?;
    style::register(m)?;
    palette::register(m)?;
    text::register(m)?;
    widgets::register(m)?;
    widgets_extra::register(m)?;
    buffer::register(m)?;
    terminal::register(m)?;
    cursor::register(m)?;
    terminal_device::register(m)?;
    event_setup::register(m)?;
    command::register(m)?;
    fx::register(m)?;
    Ok(())
}