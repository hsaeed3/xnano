//! `Live`: operations that are applied again whenever something they show changes.

use std::sync::{Arc, Mutex, Weak};

use pyo3::prelude::*;
use pyo3::types::PyTuple;
use xnano_terminal_runtime::buffer::BufferCore;
use xnano_terminal_runtime::dynamic::Fingerprint;
use xnano_terminal_runtime::expression::{Environment, EvalError, Expr};
use xnano_terminal_runtime::grid::Grid;
use xnano_terminal_runtime::painter::{Painter, Spec};
use xnano_terminal_runtime::widgets::Shared;

use crate::expressions::operation_of;
use crate::shared::lock;
use crate::surface::{apply_operations, nudge};
use crate::widgets::{
    Frame, PyWidget, fingerprint_watched, paint_through_python, repaint, value_object, watch_arg,
    widget_initializer_with,
};

struct LiveSpec {
    operations: Vec<Py<PyAny>>,
    watch: Vec<Arc<Expr>>,
}

impl Clone for LiveSpec {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            operations: self
                .operations
                .iter()
                .map(|item| item.clone_ref(py))
                .collect(),
            watch: self.watch.clone(),
        })
    }
}

struct LivePainter {
    spec: Shared<LiveSpec>,
    owner: Weak<BufferCore>,
}

impl Painter for LivePainter {
    fn fingerprint(&self, environment: &dyn Environment) -> Result<u64, EvalError> {
        let mut fingerprint = Fingerprint::new();
        fingerprint.add(&self.spec.version());
        fingerprint_watched(&self.spec.read().watch, environment, &mut fingerprint)?;
        Ok(fingerprint.finish())
    }

    fn paint(&self, grid: &mut Grid, _environment: &dyn Environment) -> Result<(), EvalError> {
        let operations = Python::attach(|py| {
            self.spec
                .read()
                .operations
                .iter()
                .map(|operation| operation.clone_ref(py))
                .collect::<Vec<_>>()
        });
        paint_through_python(&self.owner, grid, "Live operations", move |py, scratch| {
            let bound = operations
                .iter()
                .map(|operation| operation.bind(py).clone())
                .collect::<Vec<_>>();
            apply_operations(scratch, &bound)
        })
    }
}

#[pyclass(name = "Live", module = "xnano._xnano_core", extends = PyWidget, subclass)]
pub struct PyLive {
    spec: Shared<LiveSpec>,
    watch: Mutex<Vec<Py<PyAny>>>,
}

fn operations_arg(items: &[Bound<'_, PyAny>]) -> PyResult<Vec<Py<PyAny>>> {
    items
        .iter()
        .map(|item| {
            operation_of(item)?;
            Ok(item.clone().unbind())
        })
        .collect()
}

fn create(
    spec: LiveSpec,
    watch: Vec<Py<PyAny>>,
    frame: Frame,
) -> PyResult<PyClassInitializer<PyLive>> {
    let shared = Spec::new(spec);
    let painter_spec = Arc::clone(&shared);
    let initializer = widget_initializer_with(
        move |core| {
            Arc::new(LivePainter {
                spec: painter_spec,
                owner: Arc::downgrade(core),
            }) as Arc<dyn Painter>
        },
        frame,
        (10, 3),
    )?;
    Ok(initializer.add_subclass(PyLive {
        spec: shared,
        watch: Mutex::new(watch),
    }))
}

impl PyLive {
    fn core(slf: &Bound<'_, Self>) -> Arc<BufferCore> {
        Arc::clone(&slf.as_super().as_super().as_super().borrow().core)
    }
}

#[pymethods]
impl PyLive {
    #[new]
    #[pyo3(signature = (*operations, watch = None, width = None, height = None, x = 0, y = 0))]
    fn new(
        operations: &Bound<'_, PyTuple>,
        watch: Option<&Bound<'_, PyAny>>,
        width: Option<i32>,
        height: Option<i32>,
        x: i32,
        y: i32,
    ) -> PyResult<PyClassInitializer<Self>> {
        let items = operations.iter().collect::<Vec<_>>();
        let originals = match watch.filter(|value| !value.is_none()) {
            Some(watch) => watch
                .try_iter()?
                .map(|item| item.map(Bound::unbind))
                .collect::<PyResult<Vec<_>>>()?,
            None => Vec::new(),
        };
        create(
            LiveSpec {
                operations: operations_arg(&items)?,
                watch: watch_arg(watch)?,
            },
            originals,
            Frame {
                width,
                height,
                x,
                y,
            },
        )
    }

    /// The operations applied, in order, to a cleared area on every redraw.
    #[getter]
    fn operations<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyTuple>> {
        let py = slf.py();
        let items = slf
            .borrow()
            .spec
            .read()
            .operations
            .iter()
            .map(|operation| operation.clone_ref(py))
            .collect::<Vec<_>>();
        PyTuple::new(py, items)
    }

    #[setter]
    fn set_operations(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let items = value.try_iter()?.collect::<PyResult<Vec<_>>>()?;
        let operations = operations_arg(&items)?;
        slf.borrow().spec.edit(|spec| spec.operations = operations);
        repaint(&Self::core(slf));
        Ok(())
    }

    /// The expressions whose changes redraw the widget.
    #[getter]
    fn watch<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyTuple>> {
        let py = slf.py();
        let items = slf
            .borrow()
            .spec
            .read()
            .watch
            .iter()
            .map(|expr| value_object(py, Arc::clone(expr)))
            .collect::<PyResult<Vec<_>>>()?;
        PyTuple::new(py, items)
    }

    #[setter]
    fn set_watch(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let expressions = watch_arg(Some(value))?;
        let originals = value
            .try_iter()?
            .map(|item| item.map(Bound::unbind))
            .collect::<PyResult<Vec<_>>>()?;
        *lock(&slf.borrow().watch) = originals;
        slf.borrow().spec.edit(|spec| spec.watch = expressions);
        repaint(&Self::core(slf));
        Ok(())
    }

    /// Apply the operations again on the next frame.
    #[pyo3(signature = (area = None))]
    fn invalidate(
        slf: &Bound<'_, Self>,
        area: Option<&crate::geometry::PyRectangle>,
    ) -> PyResult<()> {
        slf.borrow().spec.edit(|_| ());
        let core = Self::core(slf);
        core.lock().touch(area.map(|area| area.inner));
        nudge(&core);
        Ok(())
    }

    /// A new widget with the same operations and watched expressions.
    fn copy(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        let py = slf.py();
        let bounds = Self::core(slf).lock().bounds();
        let this = slf.borrow();
        let spec = this.spec.read().clone();
        let watch = lock(&this.watch)
            .iter()
            .map(|item| item.clone_ref(py))
            .collect();
        let initializer = create(
            spec,
            watch,
            Frame {
                width: Some(bounds.width),
                height: Some(bounds.height),
                x: bounds.x,
                y: bounds.y,
            },
        )?;
        Ok(Py::new(py, initializer)?.into_any())
    }

    fn __copy__(slf: &Bound<'_, Self>) -> PyResult<Py<PyAny>> {
        Self::copy(slf)
    }

    fn __deepcopy__(slf: &Bound<'_, Self>, _memo: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        Self::copy(slf)
    }

    fn __repr__(slf: &Bound<'_, Self>) -> String {
        let state = Self::core(slf).lock().bounds();
        format!("Live(width={}, height={})", state.width, state.height)
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyLive>()
}
