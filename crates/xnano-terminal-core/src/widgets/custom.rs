//! `CustomWidget`: a widget drawn by a Python function.

use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex, Weak};

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyTuple;
use xnano_terminal_runtime::buffer::BufferCore;
use xnano_terminal_runtime::dynamic::Fingerprint;
use xnano_terminal_runtime::expression::{Environment, EvalError, Expr};
use xnano_terminal_runtime::grid::Grid;
use xnano_terminal_runtime::painter::{Painter, Spec};
use xnano_terminal_runtime::widgets::Shared;

use crate::shared::lock;
use crate::surface::nudge;
use crate::widgets::{
    Frame, PyWidget, fingerprint_watched, paint_through_python, repaint, shared_in_tree,
    value_object, watch_arg, widget_initializer_with,
};

struct CustomSpec {
    render: Py<PyAny>,
    should_redraw_every_frame: bool,
    watch: Vec<Arc<Expr>>,
}

impl Clone for CustomSpec {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            render: self.render.clone_ref(py),
            should_redraw_every_frame: self.should_redraw_every_frame,
            watch: self.watch.clone(),
        })
    }
}

struct CustomPainter {
    spec: Shared<CustomSpec>,
    owner: Weak<BufferCore>,
    frames: AtomicU64,
}

impl Painter for CustomPainter {
    fn fingerprint(&self, environment: &dyn Environment) -> Result<u64, EvalError> {
        let mut fingerprint = Fingerprint::new();
        fingerprint.add(&self.spec.version());
        let spec = self.spec.read();
        fingerprint_watched(&spec.watch, environment, &mut fingerprint)?;
        if spec.should_redraw_every_frame {
            fingerprint.add(&self.frames.fetch_add(1, Ordering::SeqCst));
        }
        Ok(fingerprint.finish())
    }

    fn paint(&self, grid: &mut Grid, _environment: &dyn Environment) -> Result<(), EvalError> {
        let render = Python::attach(|py| self.spec.read().render.clone_ref(py));
        let owner = self.owner.clone();
        paint_through_python(
            &self.owner,
            grid,
            "custom widget callback",
            move |py, scratch| {
                let runtime = owner
                    .upgrade()
                    .as_ref()
                    .and_then(shared_in_tree)
                    .and_then(|shared| crate::runtime::runtime_object(py, &shared));
                let options = pyo3::types::PyDict::new(py);
                options.set_item("buffer", scratch)?;
                options.set_item("target", scratch)?;
                options.set_item("runtime", runtime)?;
                let context = py
                    .import("xnano._xnano_core._core_types")?
                    .getattr("EvaluationContext")?
                    .call((), Some(&options))?;
                render.bind(py).call1((context, scratch))?;
                Ok(())
            },
        )
    }
}

#[pyclass(name = "CustomWidget", module = "xnano._xnano_core", extends = PyWidget, subclass)]
pub struct PyCustomWidget {
    spec: Shared<CustomSpec>,
    watch: Mutex<Vec<Py<PyAny>>>,
}

fn redraw_arg(name: &str) -> PyResult<bool> {
    match name {
        "on_change" => Ok(false),
        "always" => Ok(true),
        other => Err(PyValueError::new_err(format!(
            "\"{other}\" is not a redraw policy; use \"on_change\" to redraw after invalidate(), a resize or a watched change, or \"always\" to redraw every frame"
        ))),
    }
}

fn check_callable(render: &Bound<'_, PyAny>) -> PyResult<()> {
    if render.is_callable() {
        return Ok(());
    }
    Err(pyo3::exceptions::PyTypeError::new_err(
        "render must be a function called as render(context, region) that draws into the region",
    ))
}

fn create(
    py: Python<'_>,
    spec: CustomSpec,
    watch: Vec<Py<PyAny>>,
    frame: Frame,
) -> PyResult<PyClassInitializer<PyCustomWidget>> {
    let shared = Spec::new(spec);
    let painter_spec = Arc::clone(&shared);
    let initializer = widget_initializer_with(
        move |core| {
            Arc::new(CustomPainter {
                spec: painter_spec,
                owner: Arc::downgrade(core),
                frames: AtomicU64::new(0),
            }) as Arc<dyn Painter>
        },
        frame,
        (10, 3),
    )?;
    let _ = py;
    Ok(initializer.add_subclass(PyCustomWidget {
        spec: shared,
        watch: Mutex::new(watch),
    }))
}

impl PyCustomWidget {
    fn core(slf: &Bound<'_, Self>) -> Arc<BufferCore> {
        Arc::clone(&slf.as_super().as_super().as_super().borrow().core)
    }
}

#[pymethods]
impl PyCustomWidget {
    #[new]
    #[pyo3(signature = (render, *, redraw = "on_change", watch = None, width = None, height = None, x = 0, y = 0))]
    fn new(
        py: Python<'_>,
        render: &Bound<'_, PyAny>,
        redraw: &str,
        watch: Option<&Bound<'_, PyAny>>,
        width: Option<i32>,
        height: Option<i32>,
        x: i32,
        y: i32,
    ) -> PyResult<PyClassInitializer<Self>> {
        check_callable(render)?;
        let expressions = watch_arg(watch)?;
        let originals = match watch.filter(|value| !value.is_none()) {
            Some(watch) => watch
                .try_iter()?
                .map(|item| item.map(Bound::unbind))
                .collect::<PyResult<Vec<_>>>()?,
            None => Vec::new(),
        };
        create(
            py,
            CustomSpec {
                render: render.clone().unbind(),
                should_redraw_every_frame: redraw_arg(redraw)?,
                watch: expressions,
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

    /// The function that draws, called as ``render(context, region)``.
    #[getter]
    fn callback(slf: &Bound<'_, Self>) -> Py<PyAny> {
        slf.borrow().spec.read().render.clone_ref(slf.py())
    }

    #[setter(callback)]
    fn set_callback(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        check_callable(value)?;
        let render = value.clone().unbind();
        slf.borrow().spec.edit(|spec| spec.render = render);
        repaint(&Self::core(slf));
        Ok(())
    }

    /// ``"on_change"`` or ``"always"``.
    #[getter]
    fn redraw(slf: &Bound<'_, Self>) -> &'static str {
        if slf.borrow().spec.read().should_redraw_every_frame {
            "always"
        } else {
            "on_change"
        }
    }

    #[setter]
    fn set_redraw(slf: &Bound<'_, Self>, value: &str) -> PyResult<()> {
        let always = redraw_arg(value)?;
        slf.borrow()
            .spec
            .edit(|spec| spec.should_redraw_every_frame = always);
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

    /// Ask for a redraw on the next frame.
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

    /// A new widget with the same function, policy and watched expressions.
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
            py,
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
        format!(
            "CustomWidget(width={}, height={})",
            state.width, state.height
        )
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyCustomWidget>()
}
