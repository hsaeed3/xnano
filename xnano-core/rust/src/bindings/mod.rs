mod buffer;
mod command;
mod convert;
mod convert_core;
mod crossterm_exec;
mod cursor;
mod engine;
mod event_setup;
mod frame_ext;
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

pub fn register(native: &Bound<'_, PyModule>) -> PyResult<()> {
    layout::register(native)?;
    style::register(native)?;
    palette::register(native)?;
    text::register(native)?;
    widgets::register(native)?;
    widgets_extra::register(native)?;
    buffer::register(native)?;
    terminal::register(native)?;
    cursor::register(native)?;
    terminal_device::register(native)?;
    event_setup::register(native)?;
    command::register(native)?;
    fx::register(native)?;

    let engine = PyModule::new(native.py(), "engine")?;
    engine::register(&engine)?;
    engine.setattr(
        "__name__",
        pyo3::intern!(native.py(), "xnano_core.rust.engine"),
    )?;
    engine.setattr(
        "__package__",
        pyo3::intern!(native.py(), "xnano_core.rust"),
    )?;
    engine.setattr(
        "__doc__",
        "xnano_core.rust.engine\n\n\
         Runtime shim for the Rust-implemented engine submodule. Importing\n\
         :mod:`xnano_core.rust.native` registers the real module object on\n\
         ``sys.modules`` under this name.",
    )?;

    let sys_modules = native.py().import("sys")?.getattr("modules")?;
    sys_modules.set_item("xnano_core.rust.native", native)?;
    sys_modules.set_item("xnano_core.rust.engine", &engine)?;

    native.add("engine", &engine)?;
    native.add("CoreEvent", engine.getattr("CoreEvent")?)?;
    native.add("CoreTickEvent", engine.getattr("CoreTickEvent")?)?;
    native.add(
        "CoreTerminalEventKind",
        engine.getattr("CoreTerminalEventKind")?,
    )?;

    Ok(())
}
