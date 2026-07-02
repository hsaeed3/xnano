mod bindings;

use pyo3::prelude::*;

// Native rust bindings for ``ratatui`` & ``tachyonfx`` primitives represented as
// ``xnano_core._xnano_core``.
#[pymodule]
fn _xnano_core(module: &Bound<'_, PyModule>) -> PyResult<()> {
    bindings::register(module)
}