//! Native persistent state storage and compiled schema validation.

use std::sync::{Arc, Mutex};

use pyo3::exceptions::{PyRuntimeError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict, PyList, PyString, PyTuple};
use xnano_terminal_state::store::{Change, Listener, ListenerFailure};
use xnano_terminal_state::{
    Error, Issue, Node, Observation, Patch, Schema, Selection, Snapshot, Store, SubscriptionHandle,
    Transaction, to_pointer,
};

use crate::convert::{
    json_to_py, node_from_py, node_to_py, path_from_py, paths_from_py, segments_to_py, tokens_to_py,
};
use crate::errors::{
    TerminalStateAccessError, TerminalStateConflictError, TerminalStateValidationError, state_error,
};

fn json_arg(value: &Bound<'_, PyAny>) -> PyResult<serde_json::Value> {
    Ok(node_from_py(value)?.to_json())
}

fn parse_document(data: &Bound<'_, PyAny>) -> PyResult<serde_json::Value> {
    let text = if let Ok(bytes) = data.cast::<PyBytes>() {
        String::from_utf8(bytes.as_bytes().to_vec())
            .map_err(|_| PyValueError::new_err("the JSON data is not valid UTF-8"))?
    } else if let Ok(text) = data.cast::<PyString>() {
        text.to_cow()?.into_owned()
    } else {
        return Err(PyTypeError::new_err("JSON data must be a str or bytes"));
    };
    serde_json::from_str(&text)
        .map_err(|failure| PyValueError::new_err(format!("the JSON data is invalid: {failure}")))
}

#[pyclass(
    name = "TerminalStateIssue",
    skip_from_py_object,
    module = "xnano_core._xnano_core",
    frozen
)]
#[derive(Clone)]
pub struct PyStateIssue {
    path: Vec<String>,
    message: String,
    constraint: String,
}

impl PyStateIssue {
    pub fn from_issue(issue: &Issue) -> Self {
        Self {
            path: issue.path.clone(),
            message: issue.message.clone(),
            constraint: issue.constraint.clone(),
        }
    }
}

#[pymethods]
impl PyStateIssue {
    fn __richcmp__(
        slf: &Bound<'_, Self>,
        other: &Bound<'_, PyAny>,
        operation: pyo3::basic::CompareOp,
    ) -> PyResult<Py<PyAny>> {
        crate::reprs::compare_by_properties(slf.as_any(), other, operation)
    }

    fn __hash__(slf: &Bound<'_, Self>) -> PyResult<isize> {
        crate::reprs::hash_by_properties(slf.as_any())
    }

    #[getter]
    fn path<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        tokens_to_py(py, &self.path)
    }

    #[getter]
    fn message(&self) -> &str {
        &self.message
    }

    #[getter]
    fn constraint(&self) -> &str {
        &self.constraint
    }

    fn __repr__(&self) -> String {
        format!(
            "TerminalStateIssue(path={:?}, constraint={:?})",
            to_pointer(&self.path),
            self.constraint
        )
    }
}

#[pyclass(
    name = "TerminalStateSchema",
    skip_from_py_object,
    module = "xnano_core._xnano_core",
    frozen
)]
#[derive(Clone)]
pub struct PyStateSchema {
    pub inner: Schema,
}

#[pymethods]
impl PyStateSchema {
    fn __repr__(slf: &Bound<'_, Self>) -> PyResult<String> {
        crate::reprs::described(slf.as_any(), &[])
    }

    #[classmethod]
    #[pyo3(signature = (schema, *, maximum_depth = 256))]
    fn compile(
        _cls: &Bound<'_, pyo3::types::PyType>,
        schema: &Bound<'_, PyAny>,
        maximum_depth: usize,
    ) -> PyResult<Self> {
        let py = schema.py();
        let document = json_arg(schema)?;
        Schema::compile(&document, maximum_depth)
            .map(|inner| Self { inner })
            .map_err(|error| state_error(py, &error))
    }

    fn to_json_schema<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        json_to_py(py, &self.inner.to_json())
    }

    fn validate(&self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let node = node_from_py(value)?;
        self.inner
            .validate(&node)
            .map_err(|error| state_error(py, &error))
    }

    fn validate_json(&self, py: Python<'_>, data: &Bound<'_, PyAny>) -> PyResult<()> {
        let node =
            Node::from_json(&parse_document(data)?).map_err(|error| state_error(py, &error))?;
        self.inner
            .validate(&node)
            .map_err(|error| state_error(py, &error))
    }

    fn at(&self, py: Python<'_>, path: &Bound<'_, PyAny>) -> PyResult<Self> {
        self.inner
            .at(&path_from_py(path)?)
            .map(|inner| Self { inner })
            .map_err(|error| state_error(py, &error))
    }
}

#[pyclass(
    name = "TerminalStateSnapshot",
    skip_from_py_object,
    module = "xnano_core._xnano_core",
    frozen
)]
#[derive(Clone)]
pub struct PyStateSnapshot {
    inner: Snapshot,
}

#[pymethods]
impl PyStateSnapshot {
    fn __repr__(slf: &Bound<'_, Self>) -> PyResult<String> {
        crate::reprs::described(slf.as_any(), &["revision"])
    }

    #[getter]
    fn revision(&self) -> u64 {
        self.inner.revision
    }

    #[getter]
    fn schema(&self) -> PyStateSchema {
        PyStateSchema {
            inner: self.inner.schema.clone(),
        }
    }

    fn at(&self, py: Python<'_>, path: &Bound<'_, PyAny>) -> PyResult<Self> {
        self.inner
            .at(&path_from_py(path)?)
            .map(|inner| Self { inner })
            .map_err(|error| state_error(py, &error))
    }

    fn exists(&self, path: &Bound<'_, PyAny>) -> PyResult<bool> {
        Ok(self.inner.exists(&path_from_py(path)?))
    }

    fn to_value<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        node_to_py(py, &self.inner.node)
    }

    fn to_json(&self) -> String {
        self.inner.node.to_json().to_string()
    }

    fn select(&self, paths: &Bound<'_, PyAny>) -> PyResult<PyStateSelection> {
        Ok(PyStateSelection {
            inner: self.inner.select(&paths_from_py(paths)?),
        })
    }
}

#[pyclass(
    name = "TerminalStateSelection",
    skip_from_py_object,
    module = "xnano_core._xnano_core",
    frozen
)]
#[derive(Clone)]
pub struct PyStateSelection {
    inner: Selection,
}

#[pymethods]
impl PyStateSelection {
    fn __richcmp__(
        slf: &Bound<'_, Self>,
        other: &Bound<'_, PyAny>,
        operation: pyo3::basic::CompareOp,
    ) -> PyResult<Py<PyAny>> {
        crate::reprs::compare_by_properties(slf.as_any(), other, operation)
    }

    fn __hash__(slf: &Bound<'_, Self>) -> PyResult<isize> {
        crate::reprs::hash_by_properties(slf.as_any())
    }

    fn __repr__(slf: &Bound<'_, Self>) -> PyResult<String> {
        crate::reprs::described(slf.as_any(), &["revision", "paths"])
    }

    #[getter]
    fn revision(&self) -> u64 {
        self.inner.revision
    }

    #[getter]
    fn paths<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        let items = self
            .inner
            .entries
            .iter()
            .map(|(path, _)| tokens_to_py(py, path))
            .collect::<PyResult<Vec<_>>>()?;
        PyTuple::new(py, items)
    }

    fn to_value<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let dictionary = PyDict::new(py);
        for (path, node) in &self.inner.entries {
            dictionary.set_item(to_pointer(path), node_to_py(py, node)?)?;
        }
        Ok(dictionary)
    }

    fn to_json(&self) -> String {
        let entries: serde_json::Map<String, serde_json::Value> = self
            .inner
            .entries
            .iter()
            .map(|(path, node)| (to_pointer(path), node.to_json()))
            .collect();
        serde_json::Value::Object(entries).to_string()
    }
}

#[pyclass(
    name = "TerminalStatePatch",
    skip_from_py_object,
    module = "xnano_core._xnano_core",
    frozen
)]
#[derive(Clone)]
pub struct PyStatePatch {
    pub inner: Patch,
}

#[pymethods]
impl PyStatePatch {
    fn __repr__(slf: &Bound<'_, Self>) -> PyResult<String> {
        crate::reprs::described(slf.as_any(), &[])
    }

    #[classmethod]
    fn from_json(_cls: &Bound<'_, pyo3::types::PyType>, data: &Bound<'_, PyAny>) -> PyResult<Self> {
        let py = data.py();
        Patch::from_json(&parse_document(data)?)
            .map(|inner| Self { inner })
            .map_err(|error| state_error(py, &error))
    }

    #[classmethod]
    fn from_value(
        _cls: &Bound<'_, pyo3::types::PyType>,
        operations: &Bound<'_, PyAny>,
    ) -> PyResult<Self> {
        let py = operations.py();
        Patch::from_json(&json_arg(operations)?)
            .map(|inner| Self { inner })
            .map_err(|error| state_error(py, &error))
    }

    fn to_value<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        json_to_py(py, &self.inner.to_json())
    }

    fn to_json(&self) -> String {
        self.inner.to_json().to_string()
    }

    fn __len__(&self) -> usize {
        self.inner.operations.len()
    }
}

#[pyclass(
    name = "TerminalStateChange",
    skip_from_py_object,
    module = "xnano_core._xnano_core",
    frozen
)]
#[derive(Clone)]
pub struct PyStateChange {
    pub inner: Arc<Change>,
}

#[pymethods]
impl PyStateChange {
    fn __richcmp__(
        slf: &Bound<'_, Self>,
        other: &Bound<'_, PyAny>,
        operation: pyo3::basic::CompareOp,
    ) -> PyResult<Py<PyAny>> {
        crate::reprs::compare_by_properties(slf.as_any(), other, operation)
    }

    fn __hash__(slf: &Bound<'_, Self>) -> PyResult<isize> {
        crate::reprs::hash_by_properties(slf.as_any())
    }

    fn __repr__(slf: &Bound<'_, Self>) -> PyResult<String> {
        crate::reprs::described(slf.as_any(), &["revision", "before_revision", "paths"])
    }

    #[getter]
    fn before_revision(&self) -> u64 {
        self.inner.before_revision
    }

    #[getter]
    fn revision(&self) -> u64 {
        self.inner.revision
    }

    #[getter]
    fn paths<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        let items = self
            .inner
            .paths
            .iter()
            .map(|segments| segments_to_py(py, segments))
            .collect::<PyResult<Vec<_>>>()?;
        PyTuple::new(py, items)
    }

    #[getter]
    fn patch(&self) -> PyStatePatch {
        PyStatePatch {
            inner: self.inner.patch.clone(),
        }
    }

    #[getter]
    fn before(&self) -> PyStateSnapshot {
        PyStateSnapshot {
            inner: self.inner.before.clone(),
        }
    }

    #[getter]
    fn after(&self) -> PyStateSnapshot {
        PyStateSnapshot {
            inner: self.inner.after.clone(),
        }
    }
}

#[pyclass(
    name = "TerminalStateSubscription",
    module = "xnano_core._xnano_core",
    frozen
)]
pub struct PyStateSubscription {
    inner: SubscriptionHandle,
}

impl PyStateSubscription {
    pub fn of(inner: SubscriptionHandle) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyStateSubscription {
    fn __repr__(slf: &Bound<'_, Self>) -> PyResult<String> {
        crate::reprs::described(slf.as_any(), &["is_cancelled"])
    }

    #[getter]
    fn is_cancelled(&self) -> bool {
        self.inner.is_cancelled()
    }

    fn cancel(&self) {
        self.inner.cancel();
    }
}

struct PythonListener {
    callback: Py<PyAny>,
}

impl Listener for PythonListener {
    fn notify(&self, change: &Arc<Change>) -> Result<(), ListenerFailure> {
        Python::attach(|py| {
            let argument = PyStateChange {
                inner: Arc::clone(change),
            };
            self.callback
                .call1(py, (argument,))
                .map(|_| ())
                .map_err(|error| ListenerFailure(Box::new(error)))
        })
    }
}

/// Turn a listener failure back into the Python exception that caused it.
pub fn listener_failure(failure: ListenerFailure) -> PyErr {
    match failure.0.downcast::<PyErr>() {
        Ok(error) => *error,
        Err(_) => PyRuntimeError::new_err("a state notification callback failed"),
    }
}

#[pyclass(
    name = "TerminalStateTransaction",
    module = "xnano_core._xnano_core",
    frozen
)]
pub struct PyStateTransaction {
    inner: Mutex<Transaction>,
}

impl PyStateTransaction {
    fn lock(&self) -> std::sync::MutexGuard<'_, Transaction> {
        self.inner
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
    }
}

#[pymethods]
impl PyStateTransaction {
    fn __repr__(slf: &Bound<'_, Self>) -> PyResult<String> {
        crate::reprs::described(slf.as_any(), &["base_revision"])
    }

    #[getter]
    fn base_revision(&self) -> u64 {
        self.lock().base_revision
    }

    fn snapshot(&self) -> PyStateSnapshot {
        PyStateSnapshot {
            inner: self.lock().snapshot(),
        }
    }

    fn set(
        &self,
        py: Python<'_>,
        path: &Bound<'_, PyAny>,
        value: &Bound<'_, PyAny>,
    ) -> PyResult<()> {
        let path = path_from_py(path)?;
        let node = node_from_py(value)?;
        self.lock()
            .set(&path, node)
            .map_err(|error| state_error(py, &error))
    }

    fn remove(&self, py: Python<'_>, path: &Bound<'_, PyAny>) -> PyResult<()> {
        let path = path_from_py(path)?;
        self.lock()
            .remove(&path)
            .map_err(|error| state_error(py, &error))
    }

    fn apply(&self, py: Python<'_>, patch: &PyStatePatch) -> PyResult<()> {
        self.lock()
            .apply(&patch.inner)
            .map_err(|error| state_error(py, &error))
    }

    fn commit(&self, py: Python<'_>) -> PyResult<Option<PyStateChange>> {
        self.lock()
            .commit()
            .map(|change| change.map(|inner| PyStateChange { inner }))
            .map_err(|error| state_error(py, &error))
    }

    fn rollback(&self) {
        self.lock().rollback();
    }

    fn __enter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    #[pyo3(signature = (exception_type = None, exception_value = None, traceback = None))]
    fn __exit__(
        &self,
        py: Python<'_>,
        exception_type: Option<&Bound<'_, PyAny>>,
        exception_value: Option<&Bound<'_, PyAny>>,
        traceback: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<bool> {
        let _ = (exception_value, traceback);
        let mut transaction = self.lock();
        if transaction.is_finished() {
            return Ok(false);
        }
        if exception_type.is_some_and(|kind| !kind.is_none()) {
            transaction.rollback();
        } else {
            transaction
                .commit()
                .map_err(|error| state_error(py, &error))?;
        }
        Ok(false)
    }
}

#[pyclass(
    name = "TerminalStateObservation",
    skip_from_py_object,
    module = "xnano_core._xnano_core",
    frozen
)]
#[derive(Clone)]
pub struct PyStateObservation {
    inner: Observation,
}

#[pymethods]
impl PyStateObservation {
    fn __repr__(slf: &Bound<'_, Self>) -> PyResult<String> {
        crate::reprs::described(slf.as_any(), &["revision", "read", "write"])
    }

    #[getter]
    fn revision(&self) -> u64 {
        self.inner.revision
    }

    #[getter]
    fn selection(&self) -> PyStateSelection {
        PyStateSelection {
            inner: self.inner.selection.clone(),
        }
    }

    #[getter]
    fn schemas<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let dictionary = PyDict::new(py);
        for (pointer, schema) in &self.inner.schemas {
            dictionary.set_item(pointer, json_to_py(py, schema)?)?;
        }
        Ok(dictionary)
    }

    #[getter]
    fn read<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        let items = self
            .inner
            .read
            .iter()
            .map(|path| tokens_to_py(py, path))
            .collect::<PyResult<Vec<_>>>()?;
        PyTuple::new(py, items)
    }

    #[getter]
    fn write<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        let items = self
            .inner
            .write
            .iter()
            .map(|path| tokens_to_py(py, path))
            .collect::<PyResult<Vec<_>>>()?;
        PyTuple::new(py, items)
    }
}

#[pyclass(name = "TerminalStateStore", module = "xnano_core._xnano_core", frozen)]
pub struct PyStateStore {
    pub inner: Arc<Store>,
}

#[pymethods]
impl PyStateStore {
    #[new]
    #[pyo3(signature = (value, *, schema))]
    fn new(py: Python<'_>, value: &Bound<'_, PyAny>, schema: &PyStateSchema) -> PyResult<Self> {
        let node = node_from_py(value)?;
        Store::new(node, schema.inner.clone())
            .map(|inner| Self { inner })
            .map_err(|error| state_error(py, &error))
    }

    #[getter]
    fn revision(&self) -> u64 {
        self.inner.revision()
    }

    #[getter]
    fn schema(&self) -> PyStateSchema {
        PyStateSchema {
            inner: self.inner.schema().clone(),
        }
    }

    #[getter]
    fn identity(&self) -> u64 {
        self.inner.id()
    }

    #[pyo3(signature = (path = None))]
    fn snapshot(
        &self,
        py: Python<'_>,
        path: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<PyStateSnapshot> {
        let path = path.map(path_from_py).transpose()?.unwrap_or_default();
        self.inner
            .snapshot(&path)
            .map(|inner| PyStateSnapshot { inner })
            .map_err(|error| state_error(py, &error))
    }

    /// The reference to a branch of this store.
    #[pyo3(signature = (path = None))]
    fn reference(
        &self,
        path: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<crate::references::PyStateReference> {
        Ok(crate::references::PyStateReference::of(
            Arc::clone(&self.inner),
            path.map(path_from_py).transpose()?.unwrap_or_default(),
        ))
    }

    fn revision_at(&self, path: &Bound<'_, PyAny>) -> PyResult<u64> {
        Ok(self.inner.revision_at(&path_from_py(path)?))
    }

    #[pyo3(signature = (patch, *, expected_revision = None))]
    fn apply(
        &self,
        py: Python<'_>,
        patch: &PyStatePatch,
        expected_revision: Option<u64>,
    ) -> PyResult<Option<PyStateChange>> {
        self.inner
            .apply(&patch.inner, expected_revision)
            .map(|change| change.map(|inner| PyStateChange { inner }))
            .map_err(|error| state_error(py, &error))
    }

    #[pyo3(signature = (*, expected_revision = None))]
    fn transaction(&self, expected_revision: Option<u64>) -> PyStateTransaction {
        PyStateTransaction {
            inner: Mutex::new(self.inner.transaction(expected_revision)),
        }
    }

    #[pyo3(signature = (paths, callback, *, include_descendants = true))]
    fn subscribe(
        &self,
        paths: &Bound<'_, PyAny>,
        callback: Py<PyAny>,
        include_descendants: bool,
    ) -> PyResult<PyStateSubscription> {
        let listener = Arc::new(PythonListener { callback });
        Ok(PyStateSubscription {
            inner: self
                .inner
                .subscribe(paths_from_py(paths)?, include_descendants, listener),
        })
    }

    fn attach_waker(&self, wake: Py<PyAny>) -> PyStateSubscription {
        let notify: Arc<dyn Fn() + Send + Sync> = Arc::new(move || {
            Python::attach(|py| {
                if let Err(error) = wake.call0(py) {
                    error.write_unraisable(py, None);
                }
            });
        });
        PyStateSubscription {
            inner: self.inner.attach_waker(notify),
        }
    }

    #[pyo3(signature = (*, read, write = None))]
    fn observe(
        &self,
        py: Python<'_>,
        read: &Bound<'_, PyAny>,
        write: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<PyStateObservation> {
        let read = paths_from_py(read)?;
        let write = write.map(paths_from_py).transpose()?.unwrap_or_default();
        self.inner
            .observe(read, write)
            .map(|inner| PyStateObservation { inner })
            .map_err(|error| state_error(py, &error))
    }

    fn validate_observed(
        &self,
        py: Python<'_>,
        patch: &PyStatePatch,
        observation: &PyStateObservation,
    ) -> PyResult<()> {
        self.inner
            .validate_observed(&patch.inner, &observation.inner)
            .map_err(|error| state_error(py, &error))
    }

    fn apply_observed(
        &self,
        py: Python<'_>,
        patch: &PyStatePatch,
        observation: &PyStateObservation,
    ) -> PyResult<Option<PyStateChange>> {
        self.inner
            .apply_observed(&patch.inner, &observation.inner)
            .map(|change| change.map(|inner| PyStateChange { inner }))
            .map_err(|error| state_error(py, &error))
    }

    #[pyo3(signature = (*, maximum_changes = 1024))]
    fn drain_notifications(&self, maximum_changes: usize) -> PyResult<usize> {
        self.inner.drain(maximum_changes).map_err(listener_failure)
    }

    fn __repr__(&self) -> String {
        format!("TerminalStateStore(revision={})", self.inner.revision())
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    xnano_terminal_state::register_semantic_rule(
        "drawing",
        Arc::new(xnano_terminal_runtime::drawing::validate_drawing_rule),
    );
    m.add_class::<PyStateIssue>()?;
    m.add_class::<PyStateSchema>()?;
    m.add_class::<PyStateSnapshot>()?;
    m.add_class::<PyStateSelection>()?;
    m.add_class::<PyStatePatch>()?;
    m.add_class::<PyStateChange>()?;
    m.add_class::<PyStateSubscription>()?;
    m.add_class::<PyStateTransaction>()?;
    m.add_class::<PyStateObservation>()?;
    m.add_class::<PyStateStore>()?;
    let py = m.py();
    m.add(
        "TerminalStateValidationError",
        py.get_type::<TerminalStateValidationError>(),
    )?;
    m.add(
        "TerminalStateConflictError",
        py.get_type::<TerminalStateConflictError>(),
    )?;
    m.add(
        "TerminalStateAccessError",
        py.get_type::<TerminalStateAccessError>(),
    )?;
    let _ = (PyList::empty(py), Error::Access(String::new()));
    Ok(())
}
