//! `StateReference`: one branch of a state store, as values and expressions see it.

use std::sync::Arc;

use pyo3::prelude::*;
use pyo3::types::PyTuple;
use xnano_terminal_state::Store;

use crate::convert::{node_from_py, node_to_py, path_from_py};
use crate::errors::state_error;
use crate::expressions::state_expression;
use crate::state::{PyStateChange, PyStatePatch, PyStateSchema, PyStateStore};

/// A branch of a state store: read it, write it, or bind settings to it.
#[pyclass(
    name = "StateReference",
    module = "xnano._xnano_core",
    frozen,
    eq,
    hash,
    skip_from_py_object
)]
#[derive(Clone)]
pub struct PyStateReference {
    pub store: Arc<Store>,
    pub path: Vec<String>,
}

impl PartialEq for PyStateReference {
    fn eq(&self, other: &Self) -> bool {
        self.store.id() == other.store.id() && self.path == other.path
    }
}

impl Eq for PyStateReference {}

impl std::hash::Hash for PyStateReference {
    fn hash<H: std::hash::Hasher>(&self, state: &mut H) {
        self.store.id().hash(state);
        self.path.hash(state);
    }
}

impl PyStateReference {
    pub fn of(store: Arc<Store>, path: Vec<String>) -> Self {
        Self { store, path }
    }
}

#[pymethods]
impl PyStateReference {
    #[classmethod]
    fn __class_getitem__(
        cls: &Bound<'_, pyo3::types::PyType>,
        item: &Bound<'_, PyAny>,
    ) -> PyResult<Py<PyAny>> {
        Ok(cls
            .py()
            .import("types")?
            .getattr("GenericAlias")?
            .call1((cls, item))?
            .unbind())
    }
    fn __copy__(&self) -> Self {
        self.clone()
    }
    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.clone()
    }

    #[new]
    #[pyo3(signature = (store, path = None))]
    fn new(store: &PyStateStore, path: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        Ok(Self {
            store: Arc::clone(&store.inner),
            path: path.map(path_from_py).transpose()?.unwrap_or_default(),
        })
    }

    /// Where the branch is in the tree.
    #[getter]
    fn path<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        PyTuple::new(py, self.path.iter().map(String::as_str))
    }

    /// The store this reference points into.
    #[getter]
    fn store(&self) -> PyStateStore {
        PyStateStore {
            inner: Arc::clone(&self.store),
        }
    }

    /// The same object under the name the operations look for.
    #[getter]
    fn native_store(&self) -> PyStateStore {
        self.store()
    }

    /// The schema of the branch.
    #[getter]
    fn schema(&self, py: Python<'_>) -> PyResult<PyStateSchema> {
        self.store
            .schema()
            .at(&self.path)
            .map(|inner| PyStateSchema { inner })
            .map_err(|error| state_error(py, &error))
    }

    /// The store's current revision.
    #[getter]
    fn revision(&self) -> u64 {
        self.store.revision()
    }

    /// The most recent revision that changed this branch.
    #[getter]
    fn branch_revision(&self) -> u64 {
        self.store.revision_at(&self.path)
    }

    /// Whether the branch exists right now.
    fn exists(&self) -> bool {
        self.store
            .snapshot(&[])
            .is_ok_and(|snapshot| snapshot.exists(&self.path))
    }

    /// The branch's current value as plain Python data.
    fn get<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let snapshot = self
            .store
            .snapshot(&self.path)
            .map_err(|error| state_error(py, &error))?;
        node_to_py(py, &snapshot.node)
    }

    /// Replace the branch's value, validated against the schema.
    #[pyo3(signature = (value, *, expected_revision = None))]
    fn set(
        &self,
        py: Python<'_>,
        value: &Bound<'_, PyAny>,
        expected_revision: Option<u64>,
    ) -> PyResult<Option<PyStateChange>> {
        let node = node_from_py(value)?;
        let mut transaction = self.store.transaction(expected_revision);
        transaction
            .set(&self.path, node)
            .map_err(|error| state_error(py, &error))?;
        transaction
            .commit()
            .map(|change| change.map(|inner| PyStateChange { inner }))
            .map_err(|error| state_error(py, &error))
    }

    /// Apply a patch whose paths are relative to this branch.
    #[pyo3(signature = (patch, *, expected_revision = None))]
    fn update(
        &self,
        py: Python<'_>,
        patch: &PyStatePatch,
        expected_revision: Option<u64>,
    ) -> PyResult<Option<PyStateChange>> {
        self.store
            .apply(&patch.inner.with_prefix(&self.path), expected_revision)
            .map(|change| change.map(|inner| PyStateChange { inner }))
            .map_err(|error| state_error(py, &error))
    }

    /// An expression that follows the branch's value live.
    #[getter]
    fn value(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        state_expression(py, Arc::clone(&self.store), self.path.clone(), false)
    }

    /// An expression that follows the branch's numeric value live, with arithmetic.
    #[getter]
    fn number(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        state_expression(py, Arc::clone(&self.store), self.path.clone(), true)
    }

    /// The reference to a child branch.
    fn __getitem__(&self, key: &Bound<'_, PyAny>) -> PyResult<Self> {
        let mut path = self.path.clone();
        path.extend(path_from_py(&PyTuple::new(key.py(), [key])?.into_any())?);
        Ok(Self {
            store: Arc::clone(&self.store),
            path,
        })
    }

    fn __repr__(&self) -> String {
        format!(
            "StateReference(path={})",
            xnano_terminal_state::to_pointer(&self.path)
        )
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyStateReference>()
}
