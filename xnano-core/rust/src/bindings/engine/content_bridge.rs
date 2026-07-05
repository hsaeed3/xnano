use pyo3::prelude::*;
use ratatui::buffer::Buffer;
use ratatui::layout::Rect;

use super::super::buffer::{render_stateful_inner, render_widget_inner, PyBufferMutView};
use super::super::layout::PyRect;

pub(crate) enum RenderContentInner {
    Empty,
    Widget(Py<PyAny>),
    Stateful { widget: Py<PyAny>, state: Py<PyAny> },
    Drawable(Py<PyAny>),
}

#[pyclass(name = "CoreRenderContent", module = "xnano_core.rust.engine", unsendable)]
pub struct PyRenderContent {
    pub(crate) inner: RenderContentInner,
}

impl Clone for PyRenderContent {
    fn clone(&self) -> Self {
        Python::with_gil(|py| Self {
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

    fn is_empty(&self) -> bool {
        matches!(self.inner, RenderContentInner::Empty)
    }

    fn is_stateful(&self) -> bool {
        matches!(self.inner, RenderContentInner::Stateful { .. })
    }

    fn is_drawable(&self) -> bool {
        matches!(self.inner, RenderContentInner::Drawable(_))
    }
}

pub(crate) fn render_content(
    content: &PyRenderContent,
    rect: Rect,
    buf: &mut Buffer,
) -> PyResult<()> {
    match &content.inner {
        RenderContentInner::Empty => Ok(()),
        RenderContentInner::Widget(w) => Python::with_gil(|py| {
            render_widget_inner(w.bind(py), PyRect { inner: rect }, buf)
        }),
        RenderContentInner::Stateful { widget, state } => Python::with_gil(|py| {
            render_stateful_inner(
                widget.bind(py),
                PyRect { inner: rect },
                state.bind(py),
                buf,
            )
        }),
        RenderContentInner::Drawable(cb) => Python::with_gil(|py| {
            let buf_view = PyBufferMutView::wrap(buf);
            let rect_arg = PyRect { inner: rect };
            cb.call1(py, (buf_view.clone(), rect_arg))?;
            buf_view.invalidate();
            Ok(())
        }),
    }
}

pub fn register_content(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyRenderContent>()?;
    Ok(())
}