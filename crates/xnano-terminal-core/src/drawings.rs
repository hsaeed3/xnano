//! Schema-validated drawings and their animations.

use std::sync::Arc;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict, PyTuple};
use xnano_terminal_runtime::drawing::{
    Drawing, DrawingAnimation, DrawingFrame, DrawingKind, Palette,
};
use xnano_terminal_runtime::operation::Operation;

use crate::convert::json_to_py;
use crate::expressions::PyOperation;
use crate::operations::{encoding_arg, operation_initializer};
use crate::surface::new_buffer;

#[pyclass(
    name = "Drawing",
    module = "xnano._xnano_core",
    frozen,
    eq,
    from_py_object
)]
#[derive(Clone, PartialEq)]
pub struct PyDrawing {
    pub inner: Arc<Drawing>,
}

#[pymethods]
impl PyDrawing {
    #[new]
    #[pyo3(signature = (rows, *, kind = "text", palette = None))]
    fn new(rows: Vec<String>, kind: &str, palette: Option<&Bound<'_, PyDict>>) -> PyResult<Self> {
        let kind = DrawingKind::from_name(kind).ok_or_else(|| {
            PyValueError::new_err(format!(
                "\"{kind}\" is not a drawing kind; use \"text\" or \"palette\""
            ))
        })?;
        let mut colors = Palette::new();
        if let Some(entries) = palette {
            for (symbol, color) in entries.iter() {
                let symbol: String = symbol.extract()?;
                let color = if color.is_none() {
                    None
                } else {
                    let (red, green, blue): (u8, u8, u8) = color.extract().map_err(|_| {
                        PyValueError::new_err(
                            "palette colors are (red, green, blue) from 0 to 255, or None",
                        )
                    })?;
                    Some((red, green, blue))
                };
                colors.insert(symbol, color);
            }
        }
        Drawing::new(kind, rows, colors)
            .map(|inner| Self {
                inner: Arc::new(inner),
            })
            .map_err(PyValueError::new_err)
    }

    #[getter]
    fn kind(&self) -> &'static str {
        self.inner.kind.name()
    }

    #[getter]
    fn rows<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        PyTuple::new(py, self.inner.rows.iter().map(String::as_str))
    }

    #[getter]
    fn width(&self) -> usize {
        self.inner.width()
    }

    #[getter]
    fn height(&self) -> usize {
        self.inner.height()
    }

    #[getter]
    fn palette<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let result = PyDict::new(py);
        for (symbol, color) in &self.inner.palette {
            result.set_item(symbol, color.map(|(red, green, blue)| (red, green, blue)))?;
        }
        Ok(result)
    }

    fn to_value<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        json_to_py(py, &self.inner.to_json())
    }

    fn to_json(&self) -> String {
        self.inner.to_json().to_string()
    }

    #[pyo3(signature = (*, encoding = "half_blocks"))]
    fn to_buffer(&self, py: Python<'_>, encoding: &str) -> PyResult<Py<crate::surface::PyBuffer>> {
        let grid = self.inner.to_grid(encoding_arg(encoding)?);
        new_buffer(py, grid, 0, 0, ratatui_core::buffer::Cell::EMPTY, None)
    }

    #[pyo3(signature = (*, encoding = "half_blocks"))]
    fn to_cell_grid<'py>(&self, py: Python<'py>, encoding: &str) -> PyResult<Bound<'py, PyBytes>> {
        let grid = self.inner.to_grid(encoding_arg(encoding)?);
        let packed = xnano_terminal_cells::pack(grid.buffer())
            .map_err(|error| crate::errors::CellGridError::new_err(error.to_string()))?;
        Ok(PyBytes::new(py, &packed))
    }

    #[classmethod]
    fn from_value(
        _cls: &Bound<'_, pyo3::types::PyType>,
        value: &Bound<'_, PyAny>,
    ) -> PyResult<Self> {
        let node = crate::convert::node_from_py(value)?;
        Drawing::from_json(&node.to_json())
            .map(|inner| Self {
                inner: Arc::new(inner),
            })
            .map_err(PyValueError::new_err)
    }

    fn __repr__(&self) -> String {
        format!(
            "Drawing(kind='{}', width={}, height={})",
            self.inner.kind.name(),
            self.inner.width(),
            self.inner.height()
        )
    }
}

#[pyclass(
    name = "DrawingFrame",
    module = "xnano._xnano_core",
    frozen,
    from_py_object
)]
#[derive(Clone)]
pub struct PyDrawingFrame {
    inner: DrawingFrame,
}

#[pymethods]
impl PyDrawingFrame {
    #[new]
    #[pyo3(signature = (drawing, *, duration_milliseconds = 100))]
    fn new(drawing: &PyDrawing, duration_milliseconds: i64) -> PyResult<Self> {
        let duration = u32::try_from(duration_milliseconds).ok().filter(|duration| *duration > 0).ok_or_else(|| {
            PyValueError::new_err(format!(
                "a frame duration must be a positive number of milliseconds, not {duration_milliseconds}"
            ))
        })?;
        Ok(Self {
            inner: DrawingFrame {
                drawing: (*drawing.inner).clone(),
                duration_milliseconds: duration,
            },
        })
    }

    #[getter]
    fn drawing(&self) -> PyDrawing {
        PyDrawing {
            inner: Arc::new(self.inner.drawing.clone()),
        }
    }

    #[getter]
    fn duration_milliseconds(&self) -> u32 {
        self.inner.duration_milliseconds
    }
}

#[pyclass(
    name = "DrawingAnimation",
    module = "xnano._xnano_core",
    frozen,
    from_py_object
)]
#[derive(Clone)]
pub struct PyDrawingAnimation {
    pub inner: Arc<DrawingAnimation>,
}

#[pymethods]
impl PyDrawingAnimation {
    #[new]
    #[pyo3(signature = (frames, *, should_loop = true))]
    fn new(frames: Vec<PyDrawingFrame>, should_loop: bool) -> PyResult<Self> {
        if frames.is_empty() {
            return Err(PyValueError::new_err(
                "a drawing animation needs at least one frame",
            ));
        }
        Ok(Self {
            inner: Arc::new(DrawingAnimation {
                frames: frames.into_iter().map(|frame| frame.inner).collect(),
                should_loop,
            }),
        })
    }

    #[getter]
    fn frames<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        PyTuple::new(
            py,
            self.inner
                .frames
                .iter()
                .cloned()
                .map(|inner| PyDrawingFrame { inner }),
        )
    }

    #[getter]
    fn should_loop(&self) -> bool {
        self.inner.should_loop
    }

    #[pyo3(signature = (*, encoding = "half_blocks"))]
    fn to_cell_animation<'py>(
        &self,
        py: Python<'py>,
        encoding: &str,
    ) -> PyResult<Bound<'py, PyBytes>> {
        let animation = self.inner.to_cell_animation(encoding_arg(encoding)?);
        let packed = xnano_terminal_cells::pack_animation(&animation)
            .map_err(|error| crate::errors::CellGridError::new_err(error.to_string()))?;
        Ok(PyBytes::new(py, &packed))
    }
}

#[pyclass(name = "Draw", module = "xnano._xnano_core", extends = PyOperation)]
pub struct PyDraw;

#[pymethods]
impl PyDraw {
    #[new]
    #[pyo3(signature = (drawing, *, x = 0, y = 0, encoding = "half_blocks"))]
    fn new(
        drawing: &PyDrawing,
        x: i32,
        y: i32,
        encoding: &str,
    ) -> PyResult<PyClassInitializer<Self>> {
        Ok(operation_initializer(Operation::Draw {
            drawing: Arc::clone(&drawing.inner),
            x,
            y,
            encoding: encoding_arg(encoding)?,
        })
        .add_subclass(Self))
    }
}

#[pyclass(name = "AnimateDrawing", module = "xnano._xnano_core", extends = PyOperation)]
pub struct PyAnimateDrawing;

#[pymethods]
impl PyAnimateDrawing {
    #[new]
    #[pyo3(signature = (animation, *, x = 0, y = 0, encoding = "half_blocks", start_milliseconds = 0))]
    fn new(
        animation: &PyDrawingAnimation,
        x: i32,
        y: i32,
        encoding: &str,
        start_milliseconds: i64,
    ) -> PyResult<PyClassInitializer<Self>> {
        Ok(operation_initializer(Operation::AnimateDrawing {
            animation: Arc::clone(&animation.inner),
            x,
            y,
            encoding: encoding_arg(encoding)?,
            start_milliseconds,
        })
        .add_subclass(Self))
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyDrawing>()?;
    m.add_class::<PyDrawingFrame>()?;
    m.add_class::<PyDrawingAnimation>()?;
    m.add_class::<PyDraw>()?;
    m.add_class::<PyAnimateDrawing>()
}
