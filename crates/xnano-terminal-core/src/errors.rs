//! Exception types raised by the native extension.

use pyo3::exceptions::{PyIndexError, PyRuntimeError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyTuple;
use xnano_terminal_runtime::expression::EvalError;
use xnano_terminal_runtime::operation::OperationError;
use xnano_terminal_state::Error as StateError;

pyo3::create_exception!(
    xnano_core._xnano_core,
    RenderError,
    PyRuntimeError,
    "A recoverable render failure; failed frames are not committed."
);
pyo3::create_exception!(
    xnano_core._xnano_core,
    UnsupportedOperationError,
    PyTypeError,
    "The target registry cannot interpret the supplied operation."
);
pyo3::create_exception!(
    xnano_core._xnano_core,
    RuntimeRequiredError,
    PyRuntimeError,
    "An operation needs a mounted target and an active runtime."
);
pyo3::create_exception!(
    xnano_core._xnano_core,
    InvalidRegionError,
    PyRuntimeError,
    "The original region no longer fits its resized parent buffer."
);
pyo3::create_exception!(
    xnano_core._xnano_core,
    TerminalStateValidationError,
    PyValueError,
    "A value, patch or schema was rejected; nothing was published."
);
pyo3::create_exception!(
    xnano_core._xnano_core,
    TerminalStateConflictError,
    PyRuntimeError,
    "The state changed since it was last observed."
);
pyo3::create_exception!(
    xnano_core._xnano_core,
    TerminalStateAccessError,
    pyo3::exceptions::PyPermissionError,
    "A change reached outside the branches it was granted."
);
pyo3::create_exception!(
    xnano_core._xnano_core,
    CellGridError,
    PyValueError,
    "Packed content is malformed, incompatible, or exceeds resource limits."
);

/// Convert a state error to the exception callers see.
pub fn state_error(py: Python<'_>, error: &StateError) -> PyErr {
    match error {
        StateError::Validation(issues) => {
            let converted = TerminalStateValidationError::new_err(error.to_string());
            let list: Vec<Py<PyAny>> = issues
                .iter()
                .filter_map(|issue| {
                    crate::state::PyStateIssue::from_issue(issue)
                        .into_pyobject(py)
                        .ok()
                        .map(|object| object.into_any().unbind())
                })
                .collect();
            if let Ok(tuple) = PyTuple::new(py, list) {
                let _ = converted.value(py).setattr("issues", tuple);
            }
            converted
        }
        StateError::Conflict { expected, actual } => {
            let converted = TerminalStateConflictError::new_err(error.to_string());
            let _ = converted.value(py).setattr("expected_revision", *expected);
            let _ = converted.value(py).setattr("actual_revision", *actual);
            converted
        }
        StateError::Access(_) => TerminalStateAccessError::new_err(error.to_string()),
    }
}

pub fn eval_error(error: &EvalError) -> PyErr {
    match error {
        EvalError::RuntimeRequired(message) => RuntimeRequiredError::new_err(message.clone()),
        EvalError::Type(message) => PyTypeError::new_err(message.clone()),
        EvalError::State(message) => PyKeyError(message),
        EvalError::DivisionByZero => {
            pyo3::exceptions::PyZeroDivisionError::new_err(error.to_string())
        }
    }
}

#[allow(non_snake_case)]
fn PyKeyError(message: &str) -> PyErr {
    pyo3::exceptions::PyKeyError::new_err(message.to_owned())
}

pub fn operation_error(py: Python<'_>, error: &OperationError) -> PyErr {
    match error {
        OperationError::RuntimeRequired(message) => RuntimeRequiredError::new_err(message.clone()),
        OperationError::Unsupported(message) => UnsupportedOperationError::new_err(message.clone()),
        OperationError::OutOfBounds(message) => PyIndexError::new_err(message.clone()),
        OperationError::Invalid(message) => PyValueError::new_err(message.clone()),
        OperationError::Evaluation(inner) => eval_error(inner),
        OperationError::State(inner) => state_error(py, inner),
    }
}
