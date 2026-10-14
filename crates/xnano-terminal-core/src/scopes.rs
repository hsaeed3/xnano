//! Expression scopes: `parent`, `root` and the buffer's own geometry as named formulas.

use pyo3::exceptions::PyAttributeError;
use pyo3::prelude::*;

/// The reference object `name` that the extension module exports, such as `ParentWidth`.
fn reference(py: Python<'_>, name: &str) -> PyResult<Py<PyAny>> {
    Ok(py.import("xnano_core._xnano_core")?.getattr(name)?.unbind())
}

/// A named group of expressions, such as the parent's size or the terminal's clock.
#[pyclass(
    name = "ExpressionScope",
    module = "xnano_core._xnano_core",
    frozen,
    subclass
)]
pub struct PyExpressionScope {
    name: &'static str,
    members: &'static [&'static str],
}

#[pymethods]
impl PyExpressionScope {
    /// The attribute names this scope provides.
    fn __dir__(&self) -> Vec<&'static str> {
        self.members.to_vec()
    }

    fn __getattr__(&self, name: &str) -> PyResult<Py<PyAny>> {
        Err(PyAttributeError::new_err(format!(
            "the {} scope has no \"{name}\". It provides: {}.",
            self.name,
            self.members.join(", ")
        )))
    }

    fn __repr__(&self) -> String {
        format!("{}({})", self.name, self.members.join(", "))
    }
}

macro_rules! scope {
    ($class:ident, $python_name:literal, $members:expr, { $($getter:ident => $reference:literal),+ $(,)? }) => {
        #[pyclass(
            name = $python_name,
            module = "xnano_core._xnano_core",
            frozen,
            extends = PyExpressionScope
        )]
        pub struct $class;

        #[pymethods]
        impl $class {
            $(
                #[getter]
                fn $getter(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
                    reference(py, $reference)
                }
            )+
        }

        impl $class {
            fn instance(py: Python<'_>) -> PyResult<Py<$class>> {
                Py::new(
                    py,
                    PyClassInitializer::from(PyExpressionScope {
                        name: $python_name,
                        members: $members,
                    })
                    .add_subclass($class),
                )
            }
        }
    };
}

scope!(PyParentScope, "ParentExpressionScope", &["width", "height", "size"], {
    width => "ParentWidth",
    height => "ParentHeight",
    size => "ParentSize",
});

scope!(
    PyRootScope,
    "RootExpressionScope",
    &["width", "height", "time", "delta", "fps"],
    {
        width => "DeviceWidth",
        height => "DeviceHeight",
        time => "TimeElapsed",
        delta => "TimeDelta",
        fps => "FPS",
    }
);

scope!(
    PyBufferScope,
    "BufferExpressionScope",
    &["x", "y", "position", "width", "height", "size"],
    {
        x => "X",
        y => "Y",
        position => "Position",
        width => "Width",
        height => "Height",
        size => "BufferSize",
    }
);

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyExpressionScope>()?;
    m.add_class::<PyParentScope>()?;
    m.add_class::<PyRootScope>()?;
    m.add_class::<PyBufferScope>()?;
    Ok(())
}

/// Add the `ParentScope`, `RootScope` and `BufferScope` objects to the module.
pub fn add_scopes(m: &Bound<'_, PyModule>) -> PyResult<()> {
    let py = m.py();
    m.add("ParentScope", PyParentScope::instance(py)?)?;
    m.add("RootScope", PyRootScope::instance(py)?)?;
    m.add("BufferScope", PyBufferScope::instance(py)?)?;
    Ok(())
}
