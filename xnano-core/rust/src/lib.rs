mod bindings;

use pyo3::prelude::*;

// Native rust bindings for ``ratatui`` & ``tachyonfx`` primitives represented as
// ``xnano_core.rust.native``.
#[pymodule]
fn native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    bindings::register(module)?;
    module.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
