mod clock;
mod content_bridge;
pub(crate) mod events;
mod key_binding;
mod panic_hook;
mod render_ir;
mod render_tree;
mod session;

use pyo3::prelude::*;

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    events::register(m)?;
    content_bridge::register_content(m)?;
    render_tree::register_render_tree(m)?;
    render_ir::register_render_ir(m)?;
    key_binding::register_key_binding(m)?;
    m.add_class::<session::PySession>()?;
    m.add_class::<session::PyTerminalRef>()?;
    Ok(())
}
