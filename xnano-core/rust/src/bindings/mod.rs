mod buffer;
mod convert;
mod convert_core;
mod fx;
mod layout;
mod palette;
mod style;
mod terminal;
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
    fx::register(m)?;
    Ok(())
}