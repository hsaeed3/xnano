//! `Cursor`: the one cursor a terminal has, settable from any thread.

use std::sync::Arc;

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyTuple;
use xnano_terminal_runtime::buffer::{BufferCore, absolute_origin};
use xnano_terminal_runtime::cursor::{CursorPlacement, CursorShape};
use xnano_terminal_runtime::geometry::{Point, Size};

use crate::geometry::PyPoint;
use crate::shared::{RuntimeShared, lock};
use crate::surface::PyBuffer;

/// A cursor that stays at a place inside a buffer.
pub struct CursorAnchor {
    pub core: Arc<BufferCore>,
    pub x: i32,
    pub y: i32,
}

/// What the runtime knows about its cursor between frames.
pub struct CursorData {
    pub position: Option<Point>,
    pub anchor: Option<CursorAnchor>,
    /// `None` leaves the user's own cursor shape alone.
    pub shape: Option<CursorShape>,
    pub is_blinking: bool,
    pub is_visible: bool,
}

impl Default for CursorData {
    fn default() -> Self {
        Self {
            position: None,
            anchor: None,
            shape: None,
            is_blinking: false,
            is_visible: true,
        }
    }
}

/// Whether a buffer and every buffer above it is shown.
fn is_shown(core: &Arc<BufferCore>) -> bool {
    let mut current = Some(Arc::clone(core));
    while let Some(node) = current {
        if !node.lock().is_visible {
            return false;
        }
        current = node.parent();
    }
    true
}

fn anchored_position(anchor: &CursorAnchor) -> Option<Point> {
    if !is_shown(&anchor.core) {
        return None;
    }
    let (origin_x, origin_y) = absolute_origin(&anchor.core);
    Some(Point::new(
        origin_x.saturating_add(anchor.x),
        origin_y.saturating_add(anchor.y),
    ))
}

/// Where the cursor is shown in a frame of `size`, if it is shown at all.
pub fn resolve(shared: &RuntimeShared, size: Size) -> Option<CursorPlacement> {
    let data = lock(&shared.cursor);
    if !data.is_visible {
        return None;
    }
    let position = match &data.anchor {
        Some(anchor) => anchored_position(anchor)?,
        None => data.position?,
    };
    if position.x < 0 || position.y < 0 || position.x >= size.width || position.y >= size.height {
        return None;
    }
    let style = (data.shape.is_some() || data.is_blinking)
        .then(|| (data.shape.unwrap_or_default(), data.is_blinking));
    Some(CursorPlacement { position, style })
}

/// The terminal's cursor.
#[pyclass(name = "Cursor", module = "xnano_core._xnano_core", frozen)]
pub struct PyCursor {
    pub shared: Arc<RuntimeShared>,
}

fn point_arg(value: &Bound<'_, PyAny>) -> PyResult<Point> {
    if let Ok(point) = value.extract::<PyPoint>() {
        return Ok(point.inner);
    }
    if let Ok(pair) = value.cast::<PyTuple>()
        && pair.len() == 2
        && let (Ok(x), Ok(y)) = (pair.get_item(0)?.extract(), pair.get_item(1)?.extract())
    {
        return Ok(Point::new(x, y));
    }
    Err(PyTypeError::new_err(format!(
        "a cursor position is a Point or a (column, row) pair of whole numbers, or None to \
         hide the cursor, but got {}",
        value.repr()?
    )))
}

#[pymethods]
impl PyCursor {
    #[getter]
    fn position(&self) -> Option<PyPoint> {
        let data = lock(&self.shared.cursor);
        match &data.anchor {
            Some(anchor) => anchored_position(anchor),
            None => data.position,
        }
        .map(|inner| PyPoint { inner })
    }

    #[setter]
    fn set_position(&self, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let position = match value {
            Some(value) if !value.is_none() => Some(point_arg(value)?),
            _ => None,
        };
        {
            let mut data = lock(&self.shared.cursor);
            data.position = position;
            data.anchor = None;
        }
        self.shared.request_frame();
        Ok(())
    }

    #[getter]
    fn shape(&self) -> Option<&'static str> {
        lock(&self.shared.cursor).shape.map(CursorShape::name)
    }

    #[setter]
    fn set_shape(&self, value: Option<&str>) -> PyResult<()> {
        let shape = match value {
            None => None,
            Some(name) => Some(CursorShape::from_name(name).ok_or_else(|| {
                PyValueError::new_err(format!(
                    "\"{name}\" is not a cursor shape; use \"block\", \"bar\" or \"underline\", \
                     or None to keep the user's own shape"
                ))
            })?),
        };
        lock(&self.shared.cursor).shape = shape;
        self.shared.request_frame();
        Ok(())
    }

    #[getter]
    fn is_blinking(&self) -> bool {
        lock(&self.shared.cursor).is_blinking
    }

    #[setter]
    fn set_is_blinking(&self, value: bool) {
        lock(&self.shared.cursor).is_blinking = value;
        self.shared.request_frame();
    }

    #[getter]
    fn is_visible(&self) -> bool {
        lock(&self.shared.cursor).is_visible
    }

    #[setter]
    fn set_is_visible(&self, value: bool) {
        lock(&self.shared.cursor).is_visible = value;
        self.shared.request_frame();
    }

    /// Keep the cursor at a place inside a buffer, wherever the buffer is, or stop doing
    /// so when ``buffer`` is ``None``.
    #[pyo3(signature = (buffer, *, x = 0, y = 0))]
    fn follow(&self, buffer: Option<&Bound<'_, PyBuffer>>, x: i32, y: i32) {
        let anchor = buffer.map(|buffer| CursorAnchor {
            core: Arc::clone(&buffer.as_super().borrow().core),
            x,
            y,
        });
        lock(&self.shared.cursor).anchor = anchor;
        self.shared.request_frame();
    }

    fn __repr__(&self) -> String {
        let data = lock(&self.shared.cursor);
        format!(
            "Cursor(shape={}, is_blinking={}, is_visible={})",
            data.shape.map_or("None", CursorShape::name),
            if data.is_blinking { "True" } else { "False" },
            if data.is_visible { "True" } else { "False" },
        )
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyCursor>()
}
