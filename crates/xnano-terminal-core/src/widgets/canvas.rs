//! `Canvas`: shapes, points and labels drawn on a coordinate plane.
//!
//! Also holds the helpers `Chart` and `Calendar` share: owner tracking for edited sub-objects and
//! conversions between settings and Python values.

use std::any::Any;
use std::sync::{Arc, Mutex, Weak};

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyList, PyString, PyTuple};
use xnano_terminal_runtime::buffer::{BufferCore, check_size};
use xnano_terminal_runtime::dynamic::Dynamic;
use xnano_terminal_runtime::grid::{Grid, blank_cell};
use xnano_terminal_runtime::painter::{Painter, Spec};
use xnano_terminal_runtime::style::Color;
use xnano_terminal_runtime::widgets::block::BlockSpec;
use xnano_terminal_runtime::widgets::canvas::{
    CanvasSpec, CircleShape, LabelShape, LineShape, MapShape, MarkerShape, PointsShape,
    RectangleShape, ShapeHandle, marker_error, marker_from_name,
};
use xnano_terminal_runtime::widgets::{Shared, SpecPainter, WidgetSpec};

use crate::style::PyColor;
use crate::surface::{BufferExt, PyBuffer, PySurface};
use crate::widgets::block::block_arg;
use crate::widgets::style::{style_spec_arg, style_spec_to_py};
use crate::widgets::{
    Frame, PyWidget, dynamic_color, dynamic_f64, dynamic_string, dynamic_to_py, repaint,
};

// ---------------------------------------------------------------------------------------------
// Helpers shared with `chart` and `calendar`
// ---------------------------------------------------------------------------------------------

/// The widgets an edited sub-object (a shape, dataset or axis) belongs to.
///
/// Editing the sub-object repaints those widgets straight away, so reading them afterwards
/// shows the change without waiting for a frame.
#[derive(Clone, Default)]
pub struct Owners(Arc<Mutex<Vec<Weak<BufferCore>>>>);

impl Owners {
    pub fn add(&self, core: &Arc<BufferCore>) {
        let mut owners = crate::shared::lock(&self.0);
        owners.retain(|owner| owner.upgrade().is_some());
        if !owners
            .iter()
            .any(|owner| owner.as_ptr() == Arc::as_ptr(core))
        {
            owners.push(Arc::downgrade(core));
        }
    }

    pub fn repaint(&self) {
        let cores: Vec<Arc<BufferCore>> = crate::shared::lock(&self.0)
            .iter()
            .filter_map(Weak::upgrade)
            .collect();
        for core in cores {
            repaint(&core);
        }
    }
}

/// The initializer of a widget together with the buffer core it owns.
pub fn widget_with_core<S: WidgetSpec>(
    spec: Shared<S>,
    frame: Frame,
    default_size: (i32, i32),
) -> PyResult<(PyClassInitializer<PyWidget>, Arc<BufferCore>)> {
    let (columns, rows) = check_size(
        frame.width.unwrap_or(default_size.0),
        frame.height.unwrap_or(default_size.1),
    )
    .map_err(PyValueError::new_err)?;
    let fill = blank_cell();
    let core = BufferCore::new(Grid::filled(columns, rows, &fill), frame.x, frame.y, fill);
    let ext = Arc::new(BufferExt::default());
    {
        let mut state = core.lock();
        state.extension = Some(Arc::clone(&ext) as Arc<dyn Any + Send + Sync>);
        state.painter = Some(SpecPainter::new(spec) as Arc<dyn Painter>);
    }
    let initializer = PyClassInitializer::from(PySurface {
        core: Arc::clone(&core),
        ext,
        region: None,
    })
    .add_subclass(PyBuffer)
    .add_subclass(PyWidget);
    Ok((initializer, core))
}

pub fn float_out<'py>(py: Python<'py>, value: &Dynamic<f64>) -> PyResult<Bound<'py, PyAny>> {
    dynamic_to_py(py, value, |py, number| {
        Ok(number.into_pyobject(py)?.into_any())
    })
}

pub fn string_out<'py>(py: Python<'py>, value: &Dynamic<String>) -> PyResult<Bound<'py, PyAny>> {
    dynamic_to_py(py, value, |py, text| Ok(PyString::new(py, text).into_any()))
}

pub fn color_out<'py>(py: Python<'py>, value: &Dynamic<Color>) -> PyResult<Bound<'py, PyAny>> {
    dynamic_to_py(py, value, |py, color| {
        Ok(Py::new(py, PyColor { inner: *color })?
            .into_bound(py)
            .into_any())
    })
}

pub fn optional_out<'py, T>(
    py: Python<'py>,
    value: Option<&Dynamic<T>>,
    convert: impl Fn(Python<'py>, &Dynamic<T>) -> PyResult<Bound<'py, PyAny>>,
) -> PyResult<Bound<'py, PyAny>> {
    match value {
        None => Ok(py.None().into_bound(py)),
        Some(inner) => convert(py, inner),
    }
}

pub fn present<'a, 'py>(value: Option<&'a Bound<'py, PyAny>>) -> Option<&'a Bound<'py, PyAny>> {
    value.filter(|value| !value.is_none())
}

/// Two numbers (or expressions) as a pair setting.
pub fn pair_arg(value: &Bound<'_, PyAny>, name: &str) -> PyResult<[Dynamic<f64>; 2]> {
    let items = value
        .try_iter()
        .map_err(|_| PyTypeError::new_err(format!("{name} takes two numbers, such as (0, 100)")))?
        .collect::<PyResult<Vec<_>>>()?;
    if items.len() != 2 {
        return Err(PyValueError::new_err(format!(
            "{name} takes exactly two numbers (lower, upper), not {}",
            items.len()
        )));
    }
    Ok([dynamic_f64(&items[0])?, dynamic_f64(&items[1])?])
}

pub fn pair_out<'py>(py: Python<'py>, pair: &[Dynamic<f64>; 2]) -> PyResult<Bound<'py, PyTuple>> {
    PyTuple::new(py, [float_out(py, &pair[0])?, float_out(py, &pair[1])?])
}

pub fn marker_arg(value: &Bound<'_, PyAny>) -> PyResult<Dynamic<String>> {
    let setting = dynamic_string(value)?;
    if let Dynamic::Fixed(name) = &setting
        && marker_from_name(name).is_none()
    {
        return Err(PyValueError::new_err(marker_error(name)));
    }
    Ok(setting)
}

/// Coordinates from a sequence of `(x, y)` pairs.
pub fn coordinates_arg(value: &Bound<'_, PyAny>) -> PyResult<Vec<(f64, f64)>> {
    let mut points = Vec::new();
    for item in value.try_iter()? {
        let (x, y): (f64, f64) = item?.extract().map_err(|_| {
            PyTypeError::new_err("points are (x, y) pairs of numbers, such as [(0, 1), (2, 3)]")
        })?;
        if !x.is_finite() || !y.is_finite() {
            return Err(PyValueError::new_err(format!(
                "the point ({x}, {y}) is not finite; use ordinary numbers"
            )));
        }
        points.push((x, y));
    }
    Ok(points)
}

pub fn coordinates_out<'py>(
    py: Python<'py>,
    points: &[(f64, f64)],
) -> PyResult<Bound<'py, PyList>> {
    PyList::new(py, points.iter().map(|(x, y)| (*x, *y)))
}

fn color_or_reset(value: Option<&Bound<'_, PyAny>>) -> PyResult<Dynamic<Color>> {
    match present(value) {
        Some(value) => dynamic_color(value),
        None => Ok(Dynamic::Fixed(Color::Reset)),
    }
}

fn same(left: &impl std::fmt::Debug, right: &impl std::fmt::Debug) -> bool {
    format!("{left:?}") == format!("{right:?}")
}

fn unhashable(name: &str) -> PyErr {
    PyTypeError::new_err(format!(
        "{name} can be edited after it is created, so it cannot be hashed; compare it with == instead"
    ))
}

// ---------------------------------------------------------------------------------------------
// Shapes
// ---------------------------------------------------------------------------------------------

macro_rules! shape_common {
    ($class:ident, $data:ty, $label:literal) => {
        impl $class {
            fn edit(&self, change: impl FnOnce(&mut $data)) {
                self.spec.edit(change);
                self.owners.repaint();
            }

            fn duplicate(&self) -> Self {
                Self {
                    spec: Spec::new(self.spec.read().clone()),
                    owners: Owners::default(),
                }
            }
        }
    };
}

/// A straight line, optionally filled down to a baseline.
#[pyclass(name = "CanvasLine", module = "xnano._xnano_core")]
pub struct PyCanvasLine {
    pub spec: Shared<LineShape>,
    pub owners: Owners,
}
shape_common!(PyCanvasLine, LineShape, "CanvasLine");

#[pymethods]
impl PyCanvasLine {
    #[new]
    #[pyo3(signature = (x1, y1, x2, y2, color = None, *, fill_to_y = None))]
    fn new(
        x1: &Bound<'_, PyAny>,
        y1: &Bound<'_, PyAny>,
        x2: &Bound<'_, PyAny>,
        y2: &Bound<'_, PyAny>,
        color: Option<&Bound<'_, PyAny>>,
        fill_to_y: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Self> {
        Ok(Self {
            spec: Spec::new(LineShape {
                x1: dynamic_f64(x1)?,
                y1: dynamic_f64(y1)?,
                x2: dynamic_f64(x2)?,
                y2: dynamic_f64(y2)?,
                color: color_or_reset(color)?,
                fill_to_y: present(fill_to_y).map(dynamic_f64).transpose()?,
            }),
            owners: Owners::default(),
        })
    }

    #[getter]
    fn x1<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        float_out(py, &self.spec.read().x1)
    }

    #[setter]
    fn set_x1(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let number = dynamic_f64(value)?;
        self.edit(|shape| shape.x1 = number);
        Ok(())
    }

    #[getter]
    fn y1<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        float_out(py, &self.spec.read().y1)
    }

    #[setter]
    fn set_y1(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let number = dynamic_f64(value)?;
        self.edit(|shape| shape.y1 = number);
        Ok(())
    }

    #[getter]
    fn x2<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        float_out(py, &self.spec.read().x2)
    }

    #[setter]
    fn set_x2(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let number = dynamic_f64(value)?;
        self.edit(|shape| shape.x2 = number);
        Ok(())
    }

    #[getter]
    fn y2<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        float_out(py, &self.spec.read().y2)
    }

    #[setter]
    fn set_y2(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let number = dynamic_f64(value)?;
        self.edit(|shape| shape.y2 = number);
        Ok(())
    }

    #[getter]
    fn color<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        color_out(py, &self.spec.read().color)
    }

    #[setter]
    fn set_color(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let color = dynamic_color(value)?;
        self.edit(|shape| shape.color = color);
        Ok(())
    }

    /// The baseline the area under the line is filled to, or ``None`` for a plain line.
    #[getter]
    fn fill_to_y<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        optional_out(py, self.spec.read().fill_to_y.as_ref(), |py, value| {
            float_out(py, value)
        })
    }

    #[setter]
    fn set_fill_to_y(&self, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let baseline = present(value).map(dynamic_f64).transpose()?;
        self.edit(|shape| shape.fill_to_y = baseline);
        Ok(())
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let shape = self.spec.read().clone();
        let show = |value: &Dynamic<f64>| -> PyResult<String> {
            float_out(py, value)?.repr().map(|text| text.to_string())
        };
        Ok(format!(
            "CanvasLine({}, {}, {}, {})",
            show(&shape.x1)?,
            show(&shape.y1)?,
            show(&shape.x2)?,
            show(&shape.y2)?
        ))
    }

    fn __eq__(&self, other: &Bound<'_, PyAny>) -> bool {
        other
            .cast::<Self>()
            .is_ok_and(|other| same(&*self.spec.read(), &*other.borrow().spec.read()))
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(unhashable("a CanvasLine"))
    }

    fn __copy__(&self) -> Self {
        self.duplicate()
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.duplicate()
    }
}

/// An axis-aligned rectangle outline.
#[pyclass(name = "CanvasRectangle", module = "xnano._xnano_core")]
pub struct PyCanvasRectangle {
    pub spec: Shared<RectangleShape>,
    pub owners: Owners,
}
shape_common!(PyCanvasRectangle, RectangleShape, "CanvasRectangle");

#[pymethods]
impl PyCanvasRectangle {
    #[new]
    #[pyo3(signature = (x, y, width, height, color = None))]
    fn new(
        x: &Bound<'_, PyAny>,
        y: &Bound<'_, PyAny>,
        width: &Bound<'_, PyAny>,
        height: &Bound<'_, PyAny>,
        color: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Self> {
        Ok(Self {
            spec: Spec::new(RectangleShape {
                x: dynamic_f64(x)?,
                y: dynamic_f64(y)?,
                width: dynamic_f64(width)?,
                height: dynamic_f64(height)?,
                color: color_or_reset(color)?,
            }),
            owners: Owners::default(),
        })
    }

    #[getter]
    fn x<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        float_out(py, &self.spec.read().x)
    }

    #[setter]
    fn set_x(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let number = dynamic_f64(value)?;
        self.edit(|shape| shape.x = number);
        Ok(())
    }

    #[getter]
    fn y<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        float_out(py, &self.spec.read().y)
    }

    #[setter]
    fn set_y(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let number = dynamic_f64(value)?;
        self.edit(|shape| shape.y = number);
        Ok(())
    }

    #[getter]
    fn width<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        float_out(py, &self.spec.read().width)
    }

    #[setter]
    fn set_width(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let number = dynamic_f64(value)?;
        self.edit(|shape| shape.width = number);
        Ok(())
    }

    #[getter]
    fn height<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        float_out(py, &self.spec.read().height)
    }

    #[setter]
    fn set_height(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let number = dynamic_f64(value)?;
        self.edit(|shape| shape.height = number);
        Ok(())
    }

    #[getter]
    fn color<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        color_out(py, &self.spec.read().color)
    }

    #[setter]
    fn set_color(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let color = dynamic_color(value)?;
        self.edit(|shape| shape.color = color);
        Ok(())
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let shape = self.spec.read().clone();
        let show = |value: &Dynamic<f64>| -> PyResult<String> {
            float_out(py, value)?.repr().map(|text| text.to_string())
        };
        Ok(format!(
            "CanvasRectangle({}, {}, {}, {})",
            show(&shape.x)?,
            show(&shape.y)?,
            show(&shape.width)?,
            show(&shape.height)?
        ))
    }

    fn __eq__(&self, other: &Bound<'_, PyAny>) -> bool {
        other
            .cast::<Self>()
            .is_ok_and(|other| same(&*self.spec.read(), &*other.borrow().spec.read()))
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(unhashable("a CanvasRectangle"))
    }

    fn __copy__(&self) -> Self {
        self.duplicate()
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.duplicate()
    }
}

/// A circle outline.
#[pyclass(name = "CanvasCircle", module = "xnano._xnano_core")]
pub struct PyCanvasCircle {
    pub spec: Shared<CircleShape>,
    pub owners: Owners,
}
shape_common!(PyCanvasCircle, CircleShape, "CanvasCircle");

#[pymethods]
impl PyCanvasCircle {
    #[new]
    #[pyo3(signature = (x, y, radius, color = None))]
    fn new(
        x: &Bound<'_, PyAny>,
        y: &Bound<'_, PyAny>,
        radius: &Bound<'_, PyAny>,
        color: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Self> {
        Ok(Self {
            spec: Spec::new(CircleShape {
                x: dynamic_f64(x)?,
                y: dynamic_f64(y)?,
                radius: dynamic_f64(radius)?,
                color: color_or_reset(color)?,
            }),
            owners: Owners::default(),
        })
    }

    #[getter]
    fn x<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        float_out(py, &self.spec.read().x)
    }

    #[setter]
    fn set_x(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let number = dynamic_f64(value)?;
        self.edit(|shape| shape.x = number);
        Ok(())
    }

    #[getter]
    fn y<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        float_out(py, &self.spec.read().y)
    }

    #[setter]
    fn set_y(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let number = dynamic_f64(value)?;
        self.edit(|shape| shape.y = number);
        Ok(())
    }

    #[getter]
    fn radius<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        float_out(py, &self.spec.read().radius)
    }

    #[setter]
    fn set_radius(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let number = dynamic_f64(value)?;
        self.edit(|shape| shape.radius = number);
        Ok(())
    }

    #[getter]
    fn color<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        color_out(py, &self.spec.read().color)
    }

    #[setter]
    fn set_color(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let color = dynamic_color(value)?;
        self.edit(|shape| shape.color = color);
        Ok(())
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let shape = self.spec.read().clone();
        let show = |value: &Dynamic<f64>| -> PyResult<String> {
            float_out(py, value)?.repr().map(|text| text.to_string())
        };
        Ok(format!(
            "CanvasCircle({}, {}, {})",
            show(&shape.x)?,
            show(&shape.y)?,
            show(&shape.radius)?
        ))
    }

    fn __eq__(&self, other: &Bound<'_, PyAny>) -> bool {
        other
            .cast::<Self>()
            .is_ok_and(|other| same(&*self.spec.read(), &*other.borrow().spec.read()))
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(unhashable("a CanvasCircle"))
    }

    fn __copy__(&self) -> Self {
        self.duplicate()
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.duplicate()
    }
}

/// A set of single points.
#[pyclass(name = "CanvasPoints", module = "xnano._xnano_core")]
pub struct PyCanvasPoints {
    pub spec: Shared<PointsShape>,
    pub owners: Owners,
}
shape_common!(PyCanvasPoints, PointsShape, "CanvasPoints");

#[pymethods]
impl PyCanvasPoints {
    #[new]
    #[pyo3(signature = (coordinates, color = None))]
    fn new(coordinates: &Bound<'_, PyAny>, color: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        Ok(Self {
            spec: Spec::new(PointsShape {
                coordinates: coordinates_arg(coordinates)?,
                color: color_or_reset(color)?,
            }),
            owners: Owners::default(),
        })
    }

    /// The ``(x, y)`` points.
    #[getter]
    fn coordinates<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyList>> {
        coordinates_out(py, &self.spec.read().coordinates)
    }

    #[setter]
    fn set_coordinates(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let points = coordinates_arg(value)?;
        self.edit(|shape| shape.coordinates = points);
        Ok(())
    }

    #[getter]
    fn color<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        color_out(py, &self.spec.read().color)
    }

    #[setter]
    fn set_color(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let color = dynamic_color(value)?;
        self.edit(|shape| shape.color = color);
        Ok(())
    }

    fn __len__(&self) -> usize {
        self.spec.read().coordinates.len()
    }

    fn __repr__(&self) -> String {
        format!(
            "CanvasPoints(<{} points>)",
            self.spec.read().coordinates.len()
        )
    }

    fn __eq__(&self, other: &Bound<'_, PyAny>) -> bool {
        other
            .cast::<Self>()
            .is_ok_and(|other| same(&*self.spec.read(), &*other.borrow().spec.read()))
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(unhashable("a CanvasPoints"))
    }

    fn __copy__(&self) -> Self {
        self.duplicate()
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.duplicate()
    }
}

/// The world map.
#[pyclass(name = "CanvasMap", module = "xnano._xnano_core")]
pub struct PyCanvasMap {
    pub spec: Shared<MapShape>,
    pub owners: Owners,
}
shape_common!(PyCanvasMap, MapShape, "CanvasMap");

fn resolution_arg(value: &Bound<'_, PyAny>) -> PyResult<Dynamic<String>> {
    let setting = dynamic_string(value)?;
    if let Dynamic::Fixed(name) = &setting
        && name != "low"
        && name != "high"
    {
        return Err(PyValueError::new_err(format!(
            "\"{name}\" is not a map resolution; use \"low\" or \"high\""
        )));
    }
    Ok(setting)
}

#[pymethods]
impl PyCanvasMap {
    #[new]
    #[pyo3(signature = (resolution = None, color = None))]
    fn new(
        resolution: Option<&Bound<'_, PyAny>>,
        color: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Self> {
        Ok(Self {
            spec: Spec::new(MapShape {
                resolution: match present(resolution) {
                    Some(value) => resolution_arg(value)?,
                    None => Dynamic::Fixed("low".to_owned()),
                },
                color: color_or_reset(color)?,
            }),
            owners: Owners::default(),
        })
    }

    #[getter]
    fn resolution<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        string_out(py, &self.spec.read().resolution)
    }

    #[setter]
    fn set_resolution(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let resolution = resolution_arg(value)?;
        self.edit(|shape| shape.resolution = resolution);
        Ok(())
    }

    #[getter]
    fn color<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        color_out(py, &self.spec.read().color)
    }

    #[setter]
    fn set_color(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let color = dynamic_color(value)?;
        self.edit(|shape| shape.color = color);
        Ok(())
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let resolution = string_out(py, &self.spec.read().resolution)?.repr()?;
        Ok(format!("CanvasMap({resolution})"))
    }

    fn __eq__(&self, other: &Bound<'_, PyAny>) -> bool {
        other
            .cast::<Self>()
            .is_ok_and(|other| same(&*self.spec.read(), &*other.borrow().spec.read()))
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(unhashable("a CanvasMap"))
    }

    fn __copy__(&self) -> Self {
        self.duplicate()
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.duplicate()
    }
}

/// Text printed at a position, always on top of the shapes.
#[pyclass(name = "CanvasLabel", module = "xnano._xnano_core")]
pub struct PyCanvasLabel {
    pub spec: Shared<LabelShape>,
    pub owners: Owners,
}
shape_common!(PyCanvasLabel, LabelShape, "CanvasLabel");

#[pymethods]
impl PyCanvasLabel {
    #[new]
    #[pyo3(signature = (x, y, text, style = None))]
    fn new(
        x: &Bound<'_, PyAny>,
        y: &Bound<'_, PyAny>,
        text: &Bound<'_, PyAny>,
        style: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Self> {
        Ok(Self {
            spec: Spec::new(LabelShape {
                x: dynamic_f64(x)?,
                y: dynamic_f64(y)?,
                text: dynamic_string(text)?,
                style: style_spec_arg(style)?,
            }),
            owners: Owners::default(),
        })
    }

    #[getter]
    fn x<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        float_out(py, &self.spec.read().x)
    }

    #[setter]
    fn set_x(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let number = dynamic_f64(value)?;
        self.edit(|shape| shape.x = number);
        Ok(())
    }

    #[getter]
    fn y<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        float_out(py, &self.spec.read().y)
    }

    #[setter]
    fn set_y(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let number = dynamic_f64(value)?;
        self.edit(|shape| shape.y = number);
        Ok(())
    }

    #[getter]
    fn text<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        string_out(py, &self.spec.read().text)
    }

    #[setter]
    fn set_text(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let text = dynamic_string(value)?;
        self.edit(|shape| shape.text = text);
        Ok(())
    }

    #[getter]
    fn style(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        style_spec_to_py(py, &self.spec.read().style)
    }

    #[setter]
    fn set_style(&self, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let style = style_spec_arg(value)?;
        self.edit(|shape| shape.style = style);
        Ok(())
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let text = string_out(py, &self.spec.read().text)?.repr()?;
        Ok(format!("CanvasLabel(text={text})"))
    }

    fn __eq__(&self, other: &Bound<'_, PyAny>) -> bool {
        other
            .cast::<Self>()
            .is_ok_and(|other| same(&*self.spec.read(), &*other.borrow().spec.read()))
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(unhashable("a CanvasLabel"))
    }

    fn __copy__(&self) -> Self {
        self.duplicate()
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.duplicate()
    }
}

/// Saves what was drawn so far as a layer; the shapes after it draw on top.
#[pyclass(
    name = "CanvasLayer",
    module = "xnano._xnano_core",
    frozen,
    eq,
    hash,
    skip_from_py_object
)]
#[derive(PartialEq, Eq, Hash, Clone, Copy)]
pub struct PyCanvasLayer;

#[pymethods]
impl PyCanvasLayer {
    #[new]
    fn new() -> Self {
        Self
    }

    fn __repr__(&self) -> &'static str {
        "CanvasLayer()"
    }

    fn __copy__(&self) -> Self {
        *self
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        *self
    }
}

/// Switches the marker the following shapes are drawn with.
#[pyclass(name = "CanvasMarker", module = "xnano._xnano_core")]
pub struct PyCanvasMarker {
    pub spec: Shared<MarkerShape>,
    pub owners: Owners,
}
shape_common!(PyCanvasMarker, MarkerShape, "CanvasMarker");

#[pymethods]
impl PyCanvasMarker {
    #[new]
    fn new(marker: &Bound<'_, PyAny>) -> PyResult<Self> {
        Ok(Self {
            spec: Spec::new(MarkerShape {
                marker: marker_arg(marker)?,
            }),
            owners: Owners::default(),
        })
    }

    #[getter]
    fn marker<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        string_out(py, &self.spec.read().marker)
    }

    #[setter]
    fn set_marker(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let marker = marker_arg(value)?;
        self.edit(|shape| shape.marker = marker);
        Ok(())
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let marker = string_out(py, &self.spec.read().marker)?.repr()?;
        Ok(format!("CanvasMarker({marker})"))
    }

    fn __eq__(&self, other: &Bound<'_, PyAny>) -> bool {
        other
            .cast::<Self>()
            .is_ok_and(|other| same(&*self.spec.read(), &*other.borrow().spec.read()))
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(unhashable("a CanvasMarker"))
    }

    fn __copy__(&self) -> Self {
        self.duplicate()
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.duplicate()
    }
}

/// The shape handle of a Python shape object, registering `owner` for repaints.
fn handle_of(value: &Bound<'_, PyAny>, owner: Option<&Arc<BufferCore>>) -> PyResult<ShapeHandle> {
    macro_rules! try_shape {
        ($class:ty, $variant:ident) => {
            if let Ok(shape) = value.cast::<$class>() {
                let shape = shape.borrow();
                if let Some(owner) = owner {
                    shape.owners.add(owner);
                }
                return Ok(ShapeHandle::$variant(Arc::clone(&shape.spec)));
            }
        };
    }
    try_shape!(PyCanvasLine, Line);
    try_shape!(PyCanvasRectangle, Rectangle);
    try_shape!(PyCanvasCircle, Circle);
    try_shape!(PyCanvasPoints, Points);
    try_shape!(PyCanvasMap, Map);
    try_shape!(PyCanvasLabel, Label);
    try_shape!(PyCanvasMarker, Marker);
    if value.cast::<PyCanvasLayer>().is_ok() {
        return Ok(ShapeHandle::Layer);
    }
    Err(PyTypeError::new_err(
        "a canvas draws CanvasLine, CanvasRectangle, CanvasCircle, CanvasPoints, CanvasMap, \
         CanvasLabel, CanvasLayer and CanvasMarker objects",
    ))
}

fn handles_of(
    shapes: &[Py<PyAny>],
    py: Python<'_>,
    owner: Option<&Arc<BufferCore>>,
) -> PyResult<Vec<ShapeHandle>> {
    shapes
        .iter()
        .map(|shape| handle_of(shape.bind(py), owner))
        .collect()
}

// ---------------------------------------------------------------------------------------------
// Canvas
// ---------------------------------------------------------------------------------------------

/// A coordinate plane that shapes, points and labels are drawn on.
#[pyclass(name = "Canvas", module = "xnano._xnano_core", extends = PyWidget, subclass)]
pub struct PyCanvas {
    spec: Shared<CanvasSpec>,
    core: Arc<BufferCore>,
    shapes: Mutex<Vec<Py<PyAny>>>,
    block: Mutex<Option<Py<PyAny>>>,
}

impl PyCanvas {
    fn edit(&self, change: impl FnOnce(&mut CanvasSpec)) {
        self.spec.edit(change);
        repaint(&self.core);
    }

    fn set_shape_objects(&self, py: Python<'_>, shapes: Vec<Py<PyAny>>) -> PyResult<()> {
        let handles = handles_of(&shapes, py, Some(&self.core))?;
        *crate::shared::lock(&self.shapes) = shapes;
        self.edit(|spec| spec.shapes = handles);
        Ok(())
    }
}

#[pymethods]
impl PyCanvas {
    #[new]
    #[pyo3(signature = (x_bounds = None, y_bounds = None, *, marker = None, background_color = None,
        shapes = None, block = None, width = None, height = None, x = 0, y = 0))]
    fn new(
        py: Python<'_>,
        x_bounds: Option<&Bound<'_, PyAny>>,
        y_bounds: Option<&Bound<'_, PyAny>>,
        marker: Option<&Bound<'_, PyAny>>,
        background_color: Option<&Bound<'_, PyAny>>,
        shapes: Option<&Bound<'_, PyAny>>,
        block: Option<&Bound<'_, PyAny>>,
        width: Option<i32>,
        height: Option<i32>,
        x: i32,
        y: i32,
    ) -> PyResult<PyClassInitializer<Self>> {
        let mut spec = CanvasSpec::default();
        if let Some(bounds) = present(x_bounds) {
            spec.x_bounds = pair_arg(bounds, "x_bounds")?;
        }
        if let Some(bounds) = present(y_bounds) {
            spec.y_bounds = pair_arg(bounds, "y_bounds")?;
        }
        if let Some(marker) = present(marker) {
            spec.marker = marker_arg(marker)?;
        }
        spec.background_color = present(background_color).map(dynamic_color).transpose()?;
        spec.block = block_arg(block)?;
        let shape_objects = match present(shapes) {
            Some(shapes) => shapes
                .try_iter()?
                .map(|item| item.map(Bound::unbind))
                .collect::<PyResult<Vec<_>>>()?,
            None => Vec::new(),
        };
        spec.shapes = handles_of(&shape_objects, py, None)?;
        let shared = Spec::new(spec);
        let (initializer, core) = widget_with_core(
            Arc::clone(&shared),
            Frame {
                width,
                height,
                x,
                y,
            },
            (20, 10),
        )?;
        for shape in &shape_objects {
            handle_of(shape.bind(py), Some(&core))?;
        }
        repaint(&core);
        Ok(initializer.add_subclass(Self {
            spec: shared,
            core,
            shapes: Mutex::new(shape_objects),
            block: Mutex::new(present(block).map(|value| value.clone().unbind())),
        }))
    }

    /// The ``(lower, upper)`` range of the horizontal axis.
    #[getter]
    fn x_bounds<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        pair_out(py, &self.spec.read().x_bounds)
    }

    #[setter]
    fn set_x_bounds(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let bounds = pair_arg(value, "x_bounds")?;
        self.edit(|spec| spec.x_bounds = bounds);
        Ok(())
    }

    /// The ``(lower, upper)`` range of the vertical axis.
    #[getter]
    fn y_bounds<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        pair_out(py, &self.spec.read().y_bounds)
    }

    #[setter]
    fn set_y_bounds(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let bounds = pair_arg(value, "y_bounds")?;
        self.edit(|spec| spec.y_bounds = bounds);
        Ok(())
    }

    #[getter]
    fn marker<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        string_out(py, &self.spec.read().marker)
    }

    #[setter]
    fn set_marker(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let marker = marker_arg(value)?;
        self.edit(|spec| spec.marker = marker);
        Ok(())
    }

    #[getter]
    fn background_color<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        optional_out(
            py,
            self.spec.read().background_color.as_ref(),
            |py, color| color_out(py, color),
        )
    }

    #[setter]
    fn set_background_color(&self, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let color = present(value).map(dynamic_color).transpose()?;
        self.edit(|spec| spec.background_color = color);
        Ok(())
    }

    /// The shapes, in drawing order.
    #[getter]
    fn shapes<'py>(&self, py: Python<'py>) -> Bound<'py, PyList> {
        PyList::new(
            py,
            crate::shared::lock(&self.shapes)
                .iter()
                .map(|shape| shape.clone_ref(py)),
        )
        .expect("a list of Python objects can always be built")
    }

    #[setter]
    fn set_shapes(&self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let shapes = value
            .try_iter()?
            .map(|item| item.map(Bound::unbind))
            .collect::<PyResult<Vec<_>>>()?;
        self.set_shape_objects(py, shapes)
    }

    /// Draw `shape` after the shapes already on the canvas.
    fn add_shape(&self, py: Python<'_>, shape: &Bound<'_, PyAny>) -> PyResult<()> {
        let mut shapes: Vec<Py<PyAny>> = crate::shared::lock(&self.shapes)
            .iter()
            .map(|shape| shape.clone_ref(py))
            .collect();
        shapes.push(shape.clone().unbind());
        self.set_shape_objects(py, shapes)
    }

    /// Draw every shape of `shapes` after the shapes already on the canvas.
    fn extend_shapes(&self, py: Python<'_>, shapes: &Bound<'_, PyAny>) -> PyResult<()> {
        let mut all: Vec<Py<PyAny>> = crate::shared::lock(&self.shapes)
            .iter()
            .map(|shape| shape.clone_ref(py))
            .collect();
        for item in shapes.try_iter()? {
            all.push(item?.unbind());
        }
        self.set_shape_objects(py, all)
    }

    /// Remove every shape.
    fn clear_shapes(&self, py: Python<'_>) -> PyResult<()> {
        self.set_shape_objects(py, Vec::new())
    }

    /// The ``Block`` framing the canvas, or ``None``.
    #[getter]
    fn block(&self, py: Python<'_>) -> Option<Py<PyAny>> {
        crate::shared::lock(&self.block)
            .as_ref()
            .map(|block| block.clone_ref(py))
    }

    #[setter]
    fn set_block(&self, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let shared: Option<Shared<BlockSpec>> = block_arg(value)?;
        *crate::shared::lock(&self.block) = present(value).map(|value| value.clone().unbind());
        self.edit(|spec| spec.block = shared);
        Ok(())
    }

    fn __repr__(slf: &Bound<'_, Self>) -> String {
        let state = slf
            .as_super()
            .as_super()
            .as_super()
            .borrow()
            .core
            .lock()
            .bounds();
        format!(
            "Canvas(width={}, height={}, shapes={})",
            state.width,
            state.height,
            crate::shared::lock(&slf.borrow().shapes).len()
        )
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyCanvasLine>()?;
    m.add_class::<PyCanvasRectangle>()?;
    m.add_class::<PyCanvasCircle>()?;
    m.add_class::<PyCanvasPoints>()?;
    m.add_class::<PyCanvasMap>()?;
    m.add_class::<PyCanvasLabel>()?;
    m.add_class::<PyCanvasLayer>()?;
    m.add_class::<PyCanvasMarker>()?;
    m.add_class::<PyCanvas>()
}
