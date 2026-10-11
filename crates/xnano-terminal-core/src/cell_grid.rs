//! Validated cell-grid and cell-animation byte interchange.

use pyo3::prelude::*;
use pyo3::types::PyBytes;
use xnano_terminal_cells as format;
use xnano_terminal_cells::{AnimationFrame, CellAnimation, Limits};

use crate::errors::CellGridError;

fn error(error: &format::FormatError) -> PyErr {
    CellGridError::new_err(error.to_string())
}

#[pyclass(
    name = "DecodeLimits",
    skip_from_py_object,
    module = "xnano._xnano_core",
    frozen
)]
#[derive(Clone, Copy)]
pub struct PyDecodeLimits {
    inner: Limits,
}

impl PyDecodeLimits {
    fn resolve(limits: Option<&PyDecodeLimits>) -> Limits {
        limits.map_or_else(Limits::default, |limits| limits.inner)
    }
}

#[pymethods]
impl PyDecodeLimits {
    #[new]
    #[pyo3(signature = (*, maximum_cells = 16_000_000, maximum_frames = 10_000, maximum_payload_bytes = 268_435_456))]
    fn new(maximum_cells: usize, maximum_frames: usize, maximum_payload_bytes: usize) -> Self {
        Self {
            inner: Limits {
                maximum_cells,
                maximum_frames,
                maximum_payload_bytes,
            },
        }
    }

    #[getter]
    fn maximum_cells(&self) -> usize {
        self.inner.maximum_cells
    }

    #[getter]
    fn maximum_frames(&self) -> usize {
        self.inner.maximum_frames
    }

    #[getter]
    fn maximum_payload_bytes(&self) -> usize {
        self.inner.maximum_payload_bytes
    }
}

#[pyclass(name = "CellGridInfo", module = "xnano._xnano_core", frozen)]
pub struct PyCellGridInfo {
    inner: format::GridInfo,
}

#[pymethods]
impl PyCellGridInfo {
    #[getter]
    fn format_version(&self) -> u32 {
        format::FORMAT_VERSION
    }

    #[getter]
    fn columns(&self) -> u16 {
        self.inner.columns
    }

    #[getter]
    fn rows(&self) -> u16 {
        self.inner.rows
    }

    #[getter]
    fn has_graphics_protocol_cells(&self) -> bool {
        self.inner.has_graphics_protocol_cells
    }

    #[getter]
    fn required_protocol(&self) -> Option<&'static str> {
        self.inner.required_protocol
    }
}

#[pyclass(name = "CellAnimationInfo", module = "xnano._xnano_core", frozen)]
pub struct PyCellAnimationInfo {
    inner: format::AnimationInfo,
}

#[pymethods]
impl PyCellAnimationInfo {
    #[getter]
    fn format_version(&self) -> u32 {
        format::FORMAT_VERSION
    }

    #[getter]
    fn columns(&self) -> u16 {
        self.inner.columns
    }

    #[getter]
    fn rows(&self) -> u16 {
        self.inner.rows
    }

    #[getter]
    fn frame_count(&self) -> usize {
        self.inner.frame_count
    }

    #[getter]
    fn duration_milliseconds(&self) -> u64 {
        self.inner.duration_milliseconds
    }

    #[getter]
    fn should_loop(&self) -> bool {
        self.inner.should_loop
    }
}

#[pyfunction]
#[pyo3(signature = (packed, *, limits = None))]
fn inspect_cell_grid(packed: &[u8], limits: Option<&PyDecodeLimits>) -> PyResult<PyCellGridInfo> {
    format::inspect(packed, &PyDecodeLimits::resolve(limits))
        .map(|inner| PyCellGridInfo { inner })
        .map_err(|failure| error(&failure))
}

#[pyfunction]
#[pyo3(signature = (packed, *, limits = None))]
fn inspect_cell_animation(
    packed: &[u8],
    limits: Option<&PyDecodeLimits>,
) -> PyResult<PyCellAnimationInfo> {
    format::inspect_animation(packed, &PyDecodeLimits::resolve(limits))
        .map(|inner| PyCellAnimationInfo { inner })
        .map_err(|failure| error(&failure))
}

#[pyfunction]
#[pyo3(signature = (packed, *, limits = None))]
fn validate_cell_grid(packed: &[u8], limits: Option<&PyDecodeLimits>) -> PyResult<()> {
    format::unpack_limited(packed, &PyDecodeLimits::resolve(limits))
        .map(|_| ())
        .map_err(|failure| error(&failure))
}

#[pyfunction]
#[pyo3(signature = (packed, *, limits = None))]
fn validate_cell_animation(packed: &[u8], limits: Option<&PyDecodeLimits>) -> PyResult<()> {
    format::unpack_animation_limited(packed, &PyDecodeLimits::resolve(limits))
        .map(|_| ())
        .map_err(|failure| error(&failure))
}

#[pyfunction]
fn cell_grid_size(cell_grid: &[u8]) -> PyResult<(u16, u16)> {
    format::grid_size(cell_grid).map_err(|failure| error(&failure))
}

#[pyfunction]
fn cell_grid_to_text(cell_grid: &[u8]) -> PyResult<Vec<String>> {
    format::unpack(cell_grid)
        .map(|grid| format::text(&grid))
        .map_err(|failure| error(&failure))
}

#[pyfunction]
fn cell_grid_to_ansi(cell_grid: &[u8]) -> PyResult<String> {
    format::unpack(cell_grid)
        .map(|grid| format::ansi(&grid))
        .map_err(|failure| error(&failure))
}

#[pyfunction]
#[pyo3(signature = (frames, *, frame_durations_milliseconds, should_loop = true))]
fn pack_cell_animation(
    py: Python<'_>,
    frames: Vec<Vec<u8>>,
    frame_durations_milliseconds: Vec<i64>,
    should_loop: bool,
) -> PyResult<Bound<'_, PyBytes>> {
    if frames.len() != frame_durations_milliseconds.len() {
        return Err(CellGridError::new_err(format!(
            "there are {} frames but {} durations; pass one duration for every frame",
            frames.len(),
            frame_durations_milliseconds.len()
        )));
    }
    let mut unpacked = Vec::with_capacity(frames.len());
    let mut size = None;
    for (index, (frame, duration)) in frames.iter().zip(&frame_durations_milliseconds).enumerate() {
        let grid = format::unpack(frame).map_err(|failure| error(&failure))?;
        match size {
            None => size = Some(grid.area),
            Some(expected) if expected != grid.area => {
                return Err(CellGridError::new_err(format!(
                    "frame {index} is {} x {} cells but the first frame is {} x {}; every frame \
                     of an animation needs the same size",
                    grid.area.width, grid.area.height, expected.width, expected.height
                )));
            }
            Some(_) => {}
        }
        let duration = u32::try_from(*duration).ok().filter(|duration| *duration > 0).ok_or_else(|| {
            CellGridError::new_err(format!(
                "the duration {duration} for frame {index} must be a positive number of milliseconds"
            ))
        })?;
        unpacked.push(AnimationFrame {
            grid,
            duration_milliseconds: duration,
        });
    }
    let packed = format::pack_animation(&CellAnimation {
        frames: unpacked,
        should_loop,
    })
    .map_err(|failure| error(&failure))?;
    Ok(PyBytes::new(py, &packed))
}

#[pyfunction]
#[pyo3(signature = (packed, *, elapsed_milliseconds))]
fn animation_frame_at<'py>(
    py: Python<'py>,
    packed: &[u8],
    elapsed_milliseconds: f64,
) -> PyResult<Bound<'py, PyBytes>> {
    let animation = format::unpack_animation(packed).map_err(|failure| error(&failure))?;
    let index = animation.frame_index_at(elapsed_milliseconds as i64);
    let frame = &animation.frames[index];
    let bytes = format::pack(&frame.grid).map_err(|failure| error(&failure))?;
    Ok(PyBytes::new(py, &bytes))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyDecodeLimits>()?;
    m.add_class::<PyCellGridInfo>()?;
    m.add_class::<PyCellAnimationInfo>()?;
    m.add("CellGridError", m.py().get_type::<CellGridError>())?;
    m.add_function(wrap_pyfunction!(inspect_cell_grid, m)?)?;
    m.add_function(wrap_pyfunction!(inspect_cell_animation, m)?)?;
    m.add_function(wrap_pyfunction!(validate_cell_grid, m)?)?;
    m.add_function(wrap_pyfunction!(validate_cell_animation, m)?)?;
    m.add_function(wrap_pyfunction!(cell_grid_size, m)?)?;
    m.add_function(wrap_pyfunction!(cell_grid_to_text, m)?)?;
    m.add_function(wrap_pyfunction!(cell_grid_to_ansi, m)?)?;
    m.add_function(wrap_pyfunction!(pack_cell_animation, m)?)?;
    m.add_function(wrap_pyfunction!(animation_frame_at, m)?)
}
