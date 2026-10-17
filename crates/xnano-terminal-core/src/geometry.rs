//! `Point`, `Size` and `Rectangle`.

use pyo3::exceptions::{PyIndexError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyTuple;
use xnano_terminal_runtime::geometry::{Point, Rectangle, Size};

/// Resolve a Python sequence index against `length`, allowing negative positions.
fn sequence_index(index: isize, length: usize) -> PyResult<usize> {
    let resolved = if index < 0 {
        index + length as isize
    } else {
        index
    };
    if resolved < 0 || resolved >= length as isize {
        return Err(PyIndexError::new_err(format!(
            "the index {index} is outside the {length} fields; use 0 to {}",
            length - 1
        )));
    }
    Ok(resolved as usize)
}

fn non_negative(name: &str, value: i32) -> PyResult<i32> {
    if value < 0 {
        return Err(PyValueError::new_err(format!(
            "{name} cannot be {value}: it must be zero or more"
        )));
    }
    Ok(value)
}

#[pyclass(
    name = "Point",
    module = "xnano_core._xnano_core",
    frozen,
    eq,
    hash,
    from_py_object
)]
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct PyPoint {
    pub inner: Point,
}

#[pymethods]
impl PyPoint {
    #[new]
    #[pyo3(signature = (x = 0, y = 0))]
    fn new(x: i32, y: i32) -> Self {
        Self {
            inner: Point::new(x, y),
        }
    }

    #[getter]
    fn x(&self) -> i32 {
        self.inner.x
    }

    #[getter]
    fn y(&self) -> i32 {
        self.inner.y
    }

    /// Add a point or an offset.
    fn __add__(&self, other: &Bound<'_, PyAny>) -> PyResult<Self> {
        let (x, y) = pair_of(other, "a Point or an Offset")?;
        Ok(Self {
            inner: Point::new(
                self.inner.x.saturating_add(x),
                self.inner.y.saturating_add(y),
            ),
        })
    }

    fn __sub__(&self, other: &Bound<'_, PyAny>) -> PyResult<Self> {
        let (x, y) = pair_of(other, "a Point or an Offset")?;
        Ok(Self {
            inner: Point::new(
                self.inner.x.saturating_sub(x),
                self.inner.y.saturating_sub(y),
            ),
        })
    }

    fn __neg__(&self) -> Self {
        Self {
            inner: Point::new(self.inner.x.saturating_neg(), self.inner.y.saturating_neg()),
        }
    }

    fn __mul__(&self, factor: i32) -> Self {
        Self {
            inner: Point::new(
                self.inner.x.saturating_mul(factor),
                self.inner.y.saturating_mul(factor),
            ),
        }
    }

    fn __rmul__(&self, factor: i32) -> Self {
        self.__mul__(factor)
    }

    fn __bool__(&self) -> bool {
        self.inner != Point::default()
    }

    fn __len__(&self) -> usize {
        2
    }

    fn __getitem__(&self, index: isize) -> PyResult<i32> {
        Ok([self.inner.x, self.inner.y][sequence_index(index, 2)?])
    }

    /// The distance to another point as an offset.
    fn offset_to(&self, other: &Self) -> PyOffset {
        PyOffset {
            x: other.inner.x.saturating_sub(self.inner.x),
            y: other.inner.y.saturating_sub(self.inner.y),
        }
    }

    fn __copy__(&self) -> Self {
        *self
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        *self
    }

    fn __iter__<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        PyTuple::new(py, [self.inner.x, self.inner.y])?
            .try_iter()
            .map(Bound::into_any)
    }

    fn __repr__(&self) -> String {
        format!("Point(x={}, y={})", self.inner.x, self.inner.y)
    }
}

#[pyclass(
    name = "Size",
    module = "xnano_core._xnano_core",
    frozen,
    eq,
    hash,
    from_py_object
)]
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct PySize {
    pub inner: Size,
}

#[pymethods]
impl PySize {
    #[new]
    #[pyo3(signature = (width = 0, height = 0))]
    fn new(width: i32, height: i32) -> PyResult<Self> {
        if width < 0 || height < 0 {
            return Err(PyValueError::new_err(format!(
                "a size cannot be {width} x {height}: the width and height must be zero or more"
            )));
        }
        Ok(Self {
            inner: Size::new(width, height),
        })
    }

    #[getter]
    fn width(&self) -> i32 {
        self.inner.width
    }

    #[getter]
    fn height(&self) -> i32 {
        self.inner.height
    }

    #[getter]
    fn area(&self) -> i64 {
        i64::from(self.inner.width) * i64::from(self.inner.height)
    }

    #[getter]
    fn is_empty(&self) -> bool {
        self.inner.width == 0 || self.inner.height == 0
    }

    /// Add sizes; the result never exceeds the largest addressable terminal.
    fn __add__(&self, other: &Self) -> Self {
        Self {
            inner: Size::new(
                self.inner.width.saturating_add(other.inner.width),
                self.inner.height.saturating_add(other.inner.height),
            ),
        }
    }

    /// Subtract sizes; a dimension never goes below zero.
    fn __sub__(&self, other: &Self) -> Self {
        Self {
            inner: Size::new(
                (self.inner.width - other.inner.width).max(0),
                (self.inner.height - other.inner.height).max(0),
            ),
        }
    }

    fn __mul__(&self, factor: i32) -> PyResult<Self> {
        let factor = non_negative("a size multiplier", factor)?;
        Ok(Self {
            inner: Size::new(
                self.inner.width.saturating_mul(factor),
                self.inner.height.saturating_mul(factor),
            ),
        })
    }

    fn __rmul__(&self, factor: i32) -> PyResult<Self> {
        self.__mul__(factor)
    }

    fn __bool__(&self) -> bool {
        self.inner.width > 0 && self.inner.height > 0
    }

    fn __len__(&self) -> usize {
        2
    }

    fn __getitem__(&self, index: isize) -> PyResult<i32> {
        Ok([self.inner.width, self.inner.height][sequence_index(index, 2)?])
    }

    fn __iter__<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        PyTuple::new(py, [self.inner.width, self.inner.height])?
            .try_iter()
            .map(Bound::into_any)
    }

    fn __copy__(&self) -> Self {
        *self
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        *self
    }

    fn __repr__(&self) -> String {
        format!(
            "Size(width={}, height={})",
            self.inner.width, self.inner.height
        )
    }
}

#[pyclass(
    name = "Rectangle",
    module = "xnano_core._xnano_core",
    frozen,
    eq,
    hash,
    from_py_object
)]
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct PyRectangle {
    pub inner: Rectangle,
}

#[pymethods]
impl PyRectangle {
    #[new]
    #[pyo3(signature = (x = 0, y = 0, width = 0, height = 0))]
    fn new(x: i32, y: i32, width: i32, height: i32) -> PyResult<Self> {
        if width < 0 || height < 0 {
            return Err(PyValueError::new_err(format!(
                "a rectangle cannot be {width} x {height}: the width and height must be zero or more"
            )));
        }
        Ok(Self {
            inner: Rectangle::new(x, y, width, height),
        })
    }

    #[getter]
    fn x(&self) -> i32 {
        self.inner.x
    }

    #[getter]
    fn y(&self) -> i32 {
        self.inner.y
    }

    #[getter]
    fn width(&self) -> i32 {
        self.inner.width
    }

    #[getter]
    fn height(&self) -> i32 {
        self.inner.height
    }

    #[getter]
    fn position(&self) -> PyPoint {
        PyPoint {
            inner: self.inner.position(),
        }
    }

    #[getter]
    fn size(&self) -> PySize {
        PySize {
            inner: self.inner.size(),
        }
    }

    #[getter]
    fn area(&self) -> i64 {
        self.inner.area()
    }

    #[getter]
    fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    fn contains(&self, point: &PyPoint) -> bool {
        self.inner.contains(point.inner)
    }

    fn intersects(&self, other: &Self) -> bool {
        self.inner.intersects(other.inner)
    }

    fn intersection(&self, other: &Self) -> Self {
        Self {
            inner: self.inner.intersection(other.inner),
        }
    }

    fn union(&self, other: &Self) -> Self {
        Self {
            inner: self.inner.union(other.inner),
        }
    }

    #[pyo3(signature = (x = 0, y = 0))]
    fn translate(&self, x: i32, y: i32) -> Self {
        Self {
            inner: self.inner.translate(x, y),
        }
    }

    #[pyo3(signature = (horizontal = 0, vertical = 0))]
    fn inset(&self, horizontal: i32, vertical: i32) -> Self {
        Self {
            inner: self.inner.inset(horizontal, vertical),
        }
    }

    #[getter]
    fn left(&self) -> i32 {
        self.inner.x
    }

    #[getter]
    fn top(&self) -> i32 {
        self.inner.y
    }

    #[getter]
    fn right(&self) -> i32 {
        self.inner.right()
    }

    #[getter]
    fn bottom(&self) -> i32 {
        self.inner.bottom()
    }

    /// Move by an offset.
    fn offset(&self, offset: &PyOffset) -> Self {
        Self {
            inner: self.inner.translate(offset.x, offset.y),
        }
    }

    /// Resize, keeping the corner.
    fn resize(&self, size: &PySize) -> Self {
        Self {
            inner: Rectangle::new(
                self.inner.x,
                self.inner.y,
                size.inner.width,
                size.inner.height,
            ),
        }
    }

    /// Shrink to fit inside `other`, moving as little as needed.
    fn clamp(&self, other: &Self) -> Self {
        let width = self.inner.width.min(other.inner.width);
        let height = self.inner.height.min(other.inner.height);
        let x = self
            .inner
            .x
            .clamp(other.inner.x, other.inner.right() - width);
        let y = self
            .inner
            .y
            .clamp(other.inner.y, other.inner.bottom() - height);
        Self {
            inner: Rectangle::new(x, y, width, height),
        }
    }

    /// Shrink by a margin on every side.
    fn inner_area(&self, margin: &PyMargin) -> Self {
        Self {
            inner: self.inner.inset(margin.horizontal, margin.vertical),
        }
    }

    /// Grow by a margin on every side.
    fn outer(&self, margin: &PyMargin) -> Self {
        Self {
            inner: self.inner.inset(-margin.horizontal, -margin.vertical),
        }
    }

    /// One-row rectangles from top to bottom.
    fn rows(&self) -> Vec<Self> {
        (0..self.inner.height.max(0))
            .map(|row| Self {
                inner: Rectangle::new(self.inner.x, self.inner.y + row, self.inner.width, 1),
            })
            .collect()
    }

    /// One-column rectangles from left to right.
    fn columns(&self) -> Vec<Self> {
        (0..self.inner.width.max(0))
            .map(|column| Self {
                inner: Rectangle::new(self.inner.x + column, self.inner.y, 1, self.inner.height),
            })
            .collect()
    }

    /// A rectangle of the given size centered in this one.
    #[pyo3(signature = (width, height))]
    fn centered(&self, width: i32, height: i32) -> PyResult<Self> {
        let width = non_negative("a width", width)?.min(self.inner.width);
        let height = non_negative("a height", height)?.min(self.inner.height);
        Ok(Self {
            inner: Rectangle::new(
                self.inner.x + (self.inner.width - width) / 2,
                self.inner.y + (self.inner.height - height) / 2,
                width,
                height,
            ),
        })
    }

    /// A rectangle of the given width centered horizontally, keeping this height.
    fn centered_horizontally(&self, width: i32) -> PyResult<Self> {
        self.centered(width, self.inner.height)
    }

    /// A rectangle of the given height centered vertically, keeping this width.
    fn centered_vertically(&self, height: i32) -> PyResult<Self> {
        self.centered(self.inner.width, height)
    }

    fn __and__(&self, other: &Self) -> Self {
        self.intersection(other)
    }

    fn __or__(&self, other: &Self) -> Self {
        self.union(other)
    }

    fn __contains__(&self, point: &PyPoint) -> bool {
        self.inner.contains(point.inner)
    }

    fn __bool__(&self) -> bool {
        !self.inner.is_empty()
    }

    fn __len__(&self) -> usize {
        4
    }

    fn __getitem__(&self, index: isize) -> PyResult<i32> {
        Ok([
            self.inner.x,
            self.inner.y,
            self.inner.width,
            self.inner.height,
        ][sequence_index(index, 4)?])
    }

    fn __copy__(&self) -> Self {
        *self
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        *self
    }

    fn __iter__<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        PyTuple::new(
            py,
            [
                self.inner.x,
                self.inner.y,
                self.inner.width,
                self.inner.height,
            ],
        )?
        .try_iter()
        .map(Bound::into_any)
    }

    fn __repr__(&self) -> String {
        format!(
            "Rectangle(x={}, y={}, width={}, height={})",
            self.inner.x, self.inner.y, self.inner.width, self.inner.height
        )
    }
}

/// Read an `(x, y)` pair from a Point or an Offset.
fn pair_of(value: &Bound<'_, PyAny>, expected: &str) -> PyResult<(i32, i32)> {
    if let Ok(point) = value.extract::<PyPoint>() {
        return Ok((point.inner.x, point.inner.y));
    }
    if let Ok(offset) = value.extract::<PyOffset>() {
        return Ok((offset.x, offset.y));
    }
    Err(PyTypeError::new_err(format!(
        "expected {expected} but got {}; build one with Point(x, y) or Offset(x, y)",
        value.get_type().name()?
    )))
}

/// A signed distance in columns and rows.
#[pyclass(
    name = "Offset",
    module = "xnano_core._xnano_core",
    frozen,
    eq,
    hash,
    from_py_object
)]
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct PyOffset {
    pub x: i32,
    pub y: i32,
}

#[pymethods]
impl PyOffset {
    #[new]
    #[pyo3(signature = (x = 0, y = 0))]
    fn new(x: i32, y: i32) -> Self {
        Self { x, y }
    }

    #[getter]
    fn x(&self) -> i32 {
        self.x
    }

    #[getter]
    fn y(&self) -> i32 {
        self.y
    }

    fn __add__(&self, other: &Self) -> Self {
        Self {
            x: self.x.saturating_add(other.x),
            y: self.y.saturating_add(other.y),
        }
    }

    fn __sub__(&self, other: &Self) -> Self {
        Self {
            x: self.x.saturating_sub(other.x),
            y: self.y.saturating_sub(other.y),
        }
    }

    fn __neg__(&self) -> Self {
        Self {
            x: self.x.saturating_neg(),
            y: self.y.saturating_neg(),
        }
    }

    fn __mul__(&self, factor: i32) -> Self {
        Self {
            x: self.x.saturating_mul(factor),
            y: self.y.saturating_mul(factor),
        }
    }

    fn __rmul__(&self, factor: i32) -> Self {
        self.__mul__(factor)
    }

    fn __bool__(&self) -> bool {
        self.x != 0 || self.y != 0
    }

    fn __len__(&self) -> usize {
        2
    }

    fn __getitem__(&self, index: isize) -> PyResult<i32> {
        Ok([self.x, self.y][sequence_index(index, 2)?])
    }

    fn __iter__<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        PyTuple::new(py, [self.x, self.y])?
            .try_iter()
            .map(Bound::into_any)
    }

    fn __copy__(&self) -> Self {
        *self
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        *self
    }

    fn __repr__(&self) -> String {
        format!("Offset(x={}, y={})", self.x, self.y)
    }
}

/// Empty space around a rectangle: columns on the left and right, rows above and below.
#[pyclass(
    name = "Margin",
    module = "xnano_core._xnano_core",
    frozen,
    eq,
    hash,
    from_py_object
)]
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct PyMargin {
    pub horizontal: i32,
    pub vertical: i32,
}

#[pymethods]
impl PyMargin {
    #[new]
    #[pyo3(signature = (horizontal = 0, vertical = 0))]
    fn new(horizontal: i32, vertical: i32) -> PyResult<Self> {
        Ok(Self {
            horizontal: non_negative("a horizontal margin", horizontal)?,
            vertical: non_negative("a vertical margin", vertical)?,
        })
    }

    #[getter]
    fn horizontal(&self) -> i32 {
        self.horizontal
    }

    #[getter]
    fn vertical(&self) -> i32 {
        self.vertical
    }

    fn __bool__(&self) -> bool {
        self.horizontal != 0 || self.vertical != 0
    }

    fn __len__(&self) -> usize {
        2
    }

    fn __getitem__(&self, index: isize) -> PyResult<i32> {
        Ok([self.horizontal, self.vertical][sequence_index(index, 2)?])
    }

    fn __iter__<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        PyTuple::new(py, [self.horizontal, self.vertical])?
            .try_iter()
            .map(Bound::into_any)
    }

    fn __copy__(&self) -> Self {
        *self
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        *self
    }

    fn __repr__(&self) -> String {
        format!(
            "Margin(horizontal={}, vertical={})",
            self.horizontal, self.vertical
        )
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyPoint>()?;
    m.add_class::<PySize>()?;
    m.add_class::<PyRectangle>()?;
    m.add_class::<PyOffset>()?;
    m.add_class::<PyMargin>()
}
