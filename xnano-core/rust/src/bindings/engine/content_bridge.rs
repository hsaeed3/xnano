use pyo3::prelude::*;
use ratatui::buffer::Buffer;
use ratatui::layout::Rect;

use super::render_ir::CoreRenderIR;
use super::super::buffer::{render_stateful_inner, render_widget_inner, PyBufferMutView};
use super::super::layout::PyRect;

pub(crate) enum RenderContentInner {
    Empty,
    Widget(Py<PyAny>),
    Stateful { widget: Py<PyAny>, state: Py<PyAny> },
    Drawable(Py<PyAny>),
    Ir(Py<CoreRenderIR>),
}

#[pyclass(name = "CoreRenderContent", module = "xnano_core.rust.engine", unsendable, from_py_object)]
pub struct PyRenderContent {
    pub(crate) inner: RenderContentInner,
}

impl Clone for PyRenderContent {
    fn clone(&self) -> Self {
        Python::attach(|py| Self {
            inner: match &self.inner {
                RenderContentInner::Empty => RenderContentInner::Empty,
                RenderContentInner::Widget(widget) => {
                    RenderContentInner::Widget(widget.clone_ref(py))
                }
                RenderContentInner::Stateful { widget, state } => RenderContentInner::Stateful {
                    widget: widget.clone_ref(py),
                    state: state.clone_ref(py),
                },
                RenderContentInner::Drawable(callback) => {
                    RenderContentInner::Drawable(callback.clone_ref(py))
                }
                RenderContentInner::Ir(ir) => RenderContentInner::Ir(ir.clone_ref(py)),
            },
        })
    }
}

#[pymethods]
impl PyRenderContent {
    #[staticmethod]
    pub(crate) fn empty() -> Self {
        Self {
            inner: RenderContentInner::Empty,
        }
    }

    #[staticmethod]
    fn widget(widget: Py<PyAny>) -> Self {
        Self {
            inner: RenderContentInner::Widget(widget),
        }
    }

    #[staticmethod]
    fn stateful(widget: Py<PyAny>, state: Py<PyAny>) -> Self {
        Self {
            inner: RenderContentInner::Stateful { widget, state },
        }
    }

    #[staticmethod]
    fn drawable(callback: Py<PyAny>) -> Self {
        Self {
            inner: RenderContentInner::Drawable(callback),
        }
    }

    #[staticmethod]
    fn ir(ir: Py<CoreRenderIR>) -> Self {
        Self {
            inner: RenderContentInner::Ir(ir),
        }
    }

    fn is_empty(&self) -> bool {
        matches!(self.inner, RenderContentInner::Empty)
    }

    fn is_stateful(&self) -> bool {
        matches!(self.inner, RenderContentInner::Stateful { .. })
    }

    fn is_drawable(&self) -> bool {
        matches!(self.inner, RenderContentInner::Drawable(_))
    }

    fn is_ir(&self) -> bool {
        matches!(self.inner, RenderContentInner::Ir(_))
    }
}

pub(crate) fn render_content(
    content: &PyRenderContent,
    rect: Rect,
    buf: &mut Buffer,
) -> PyResult<()> {
    match &content.inner {
        RenderContentInner::Empty => Ok(()),
        RenderContentInner::Widget(w) => Python::attach(|py| {
            render_widget_inner(w.bind(py), PyRect { inner: rect }, buf)
        }),
        RenderContentInner::Stateful { widget, state } => Python::attach(|py| {
            render_stateful_inner(
                widget.bind(py),
                PyRect { inner: rect },
                state.bind(py),
                buf,
            )
        }),
        RenderContentInner::Drawable(cb) => Python::attach(|py| {
            let buf_view = PyBufferMutView::wrap(buf);
            let rect_arg = PyRect { inner: rect };
            cb.call1(py, (buf_view.clone(), rect_arg))?;
            buf_view.invalidate();
            Ok(())
        }),
        RenderContentInner::Ir(ir) => Python::attach(|py| {
            ir.borrow(py).render_to_buffer(rect, buf)
        }),
    }
}

pub fn register_content(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyRenderContent>()?;
    Ok(())
}
