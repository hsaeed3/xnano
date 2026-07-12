// Tick clock is shared by live and buffer-backed sessions (wasm).
mod clock;
mod content_bridge;
pub(crate) mod events;
mod key_binding;
#[cfg(feature = "terminal")]
mod panic_hook;
mod render_ir;
mod render_tree;
#[cfg(feature = "terminal")]
mod session;
// Buffer-backed CoreSession for --no-default-features (wasm / Pyodide).
// Exposes the same type names as the live session module so the Python
// import surface is identical; only live crossterm I/O is missing.
#[cfg(not(feature = "terminal"))]
mod session_stub;
#[cfg(not(feature = "terminal"))]
use session_stub as session;
#[cfg(feature = "terminal")]
pub(crate) mod terminal_reset;

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
