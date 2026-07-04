mod clock;
mod content_bridge;
pub(crate) mod events;
mod panic_hook;
mod render_tree;
mod session;

use pyo3::prelude::*;

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    events::register(m)?;
    content_bridge::register_content(m)?;
    render_tree::register_render_tree(m)?;
    m.add_class::<session::PySession>()?;
    m.add_class::<session::PyTerminalRef>()?;
    Ok(())
}