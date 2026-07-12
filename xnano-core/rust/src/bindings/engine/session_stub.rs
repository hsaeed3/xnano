//! Emscripten stand-ins for the native terminal session classes.
//!
//! `CoreSession` and `CoreTerminalRef` drive a real terminal through
//! crossterm, which cannot exist under Pyodide/WebAssembly. The stubs
//! keep the `xnano_core.rust.engine` import surface identical across
//! platforms while failing loudly if terminal functionality is used.

use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyTuple};

const UNSUPPORTED_MESSAGE: &str = "the xnano-core terminal engine is not \
     available on Emscripten/WebAssembly builds; only rendering \
     primitives are supported in this environment";

#[pyclass(name = "CoreSession", module = "xnano_core.rust.engine", unsendable)]
pub struct PySession;

#[pymethods]
impl PySession {
    #[new]
    #[pyo3(signature = (*args, **kwargs))]
    fn new(
        args: &Bound<'_, PyTuple>,
        kwargs: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Self> {
        let _ = (args, kwargs);
        Err(PyRuntimeError::new_err(UNSUPPORTED_MESSAGE))
    }
}

#[pyclass(
    name = "CoreTerminalRef",
    module = "xnano_core.rust.engine",
    unsendable
)]
pub struct PyTerminalRef;

#[pymethods]
impl PyTerminalRef {
    #[new]
    #[pyo3(signature = (*args, **kwargs))]
    fn new(
        args: &Bound<'_, PyTuple>,
        kwargs: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Self> {
        let _ = (args, kwargs);
        Err(PyRuntimeError::new_err(UNSUPPORTED_MESSAGE))
    }
}
