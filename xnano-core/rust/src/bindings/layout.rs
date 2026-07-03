use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyList;
use ratatui::layout::{
    Alignment, Constraint, Direction, Flex, Layout, Margin, Offset, Position, Rect, Size,
    Spacing,
};

#[pyclass(name = "Rect", module = "xnano_core._xnano_core")]
#[derive(Clone, Copy)]
pub struct PyRect {
    pub inner: Rect,
}

#[pymethods]
impl PyRect {
    #[new]
    #[pyo3(signature = (x=0, y=0, width=0, height=0))]
    fn new(x: u16, y: u16, width: u16, height: u16) -> Self {
        Self {
            inner: Rect::new(x, y, width, height),
        }
    }

    #[classattr]
    const ZERO: Self = Self {
        inner: Rect::ZERO,
    };

    #[staticmethod]
    fn zero() -> Self {
        Self::ZERO
    }

    #[getter]
    fn x(&self) -> u16 {
        self.inner.x
    }

    #[getter]
    fn y(&self) -> u16 {
        self.inner.y
    }

    #[getter]
    fn width(&self) -> u16 {
        self.inner.width
    }

    #[getter]
    fn height(&self) -> u16 {
        self.inner.height
    }

    fn area(&self) -> u32 {
        self.inner.area()
    }

    fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    fn inner(&self, margin: PyMargin) -> Self {
        Self {
            inner: self.inner.inner(margin.inner),
        }
    }

    fn left(&self) -> u16 {
        self.inner.left()
    }

    fn right(&self) -> u16 {
        self.inner.right()
    }

    fn top(&self) -> u16 {
        self.inner.top()
    }

    fn bottom(&self) -> u16 {
        self.inner.bottom()
    }

    fn offset(&self, offset: PyOffset) -> Self {
        Self {
            inner: self.inner.offset(offset.inner),
        }
    }

    fn union(&self, other: Self) -> Self {
        Self {
            inner: self.inner.union(other.inner),
        }
    }

    fn intersection(&self, other: Self) -> Self {
        Self {
            inner: self.inner.intersection(other.inner),
        }
    }

    fn intersects(&self, other: Self) -> bool {
        self.inner.intersects(other.inner)
    }

    fn contains(&self, x: u16, y: u16) -> bool {
        self.inner.contains(Position { x, y })
    }

    fn rows(&self) -> Vec<Self> {
        self.inner
            .rows()
            .map(|rect| Self { inner: rect })
            .collect()
    }

    fn columns(&self) -> Vec<Self> {
        self.inner
            .columns()
            .map(|rect| Self { inner: rect })
            .collect()
    }

    fn split(&self, layout: &PyLayout) -> Vec<Self> {
        layout
            .spec
            .to_ratatui()
            .split(self.inner)
            .iter()
            .map(|rect| Self { inner: *rect })
            .collect()
    }

    fn __repr__(&self) -> String {
        format!(
            "Rect(x={}, y={}, width={}, height={})",
            self.inner.x, self.inner.y, self.inner.width, self.inner.height
        )
    }

    fn __str__(&self) -> String {
        self.inner.to_string()
    }
}

#[pyclass(name = "Margin", module = "xnano_core._xnano_core")]
#[derive(Clone, Copy)]
pub struct PyMargin {
    pub inner: Margin,
}

#[pymethods]
impl PyMargin {
    #[new]
    #[pyo3(signature = (horizontal=0, vertical=0))]
    fn new(horizontal: u16, vertical: u16) -> Self {
        Self {
            inner: Margin::new(horizontal, vertical),
        }
    }

    #[getter]
    fn horizontal(&self) -> u16 {
        self.inner.horizontal
    }

    #[getter]
    fn vertical(&self) -> u16 {
        self.inner.vertical
    }

    fn __repr__(&self) -> String {
        format!(
            "Margin(horizontal={}, vertical={})",
            self.inner.horizontal, self.inner.vertical
        )
    }
}

#[pyclass(name = "Direction", module = "xnano_core._xnano_core", eq, eq_int)]
#[derive(Clone, Copy, PartialEq)]
pub enum PyDirection {
    Horizontal,
    Vertical,
}

impl From<PyDirection> for Direction {
    fn from(value: PyDirection) -> Self {
        match value {
            PyDirection::Horizontal => Direction::Horizontal,
            PyDirection::Vertical => Direction::Vertical,
        }
    }
}

#[pyclass(name = "Alignment", module = "xnano_core._xnano_core", eq, eq_int)]
#[derive(Clone, Copy, PartialEq)]
pub enum PyAlignment {
    Left,
    Center,
    Right,
}

impl From<PyAlignment> for Alignment {
    fn from(value: PyAlignment) -> Self {
        match value {
            PyAlignment::Left => Alignment::Left,
            PyAlignment::Center => Alignment::Center,
            PyAlignment::Right => Alignment::Right,
        }
    }
}

#[pyclass(name = "Flex", module = "xnano_core._xnano_core", eq, eq_int)]
#[derive(Clone, Copy, PartialEq)]
pub enum PyFlex {
    Legacy,
    Start,
    End,
    Center,
    SpaceBetween,
    SpaceAround,
}

impl From<PyFlex> for Flex {
    fn from(value: PyFlex) -> Self {
        match value {
            PyFlex::Legacy => Flex::Legacy,
            PyFlex::Start => Flex::Start,
            PyFlex::End => Flex::End,
            PyFlex::Center => Flex::Center,
            PyFlex::SpaceBetween => Flex::SpaceBetween,
            PyFlex::SpaceAround => Flex::SpaceAround,
        }
    }
}

#[pyclass(name = "Constraint", module = "xnano_core._xnano_core")]
#[derive(Clone, Copy)]
pub struct PyConstraint {
    pub inner: Constraint,
}

#[pymethods]
impl PyConstraint {
    #[staticmethod]
    fn min(value: u16) -> Self {
        Self {
            inner: Constraint::Min(value),
        }
    }

    #[staticmethod]
    fn max(value: u16) -> Self {
        Self {
            inner: Constraint::Max(value),
        }
    }

    #[staticmethod]
    fn length(value: u16) -> Self {
        Self {
            inner: Constraint::Length(value),
        }
    }

    #[staticmethod]
    fn percentage(value: u16) -> Self {
        Self {
            inner: Constraint::Percentage(value),
        }
    }

    #[staticmethod]
    fn ratio(numerator: u32, denominator: u32) -> Self {
        Self {
            inner: Constraint::Ratio(numerator, denominator),
        }
    }

    #[staticmethod]
    fn fill(value: u16) -> Self {
        Self {
            inner: Constraint::Fill(value),
        }
    }

    #[staticmethod]
    fn from_lengths(values: Vec<u16>) -> Vec<Self> {
        Constraint::from_lengths(values)
            .into_iter()
            .map(|inner| Self { inner })
            .collect()
    }

    #[staticmethod]
    fn from_percentages(values: Vec<u16>) -> Vec<Self> {
        Constraint::from_percentages(values)
            .into_iter()
            .map(|inner| Self { inner })
            .collect()
    }

    #[staticmethod]
    fn from_ratios(values: Vec<(u32, u32)>) -> Vec<Self> {
        Constraint::from_ratios(values)
            .into_iter()
            .map(|inner| Self { inner })
            .collect()
    }

    #[staticmethod]
    fn from_mins(values: Vec<u16>) -> Vec<Self> {
        Constraint::from_mins(values)
            .into_iter()
            .map(|inner| Self { inner })
            .collect()
    }

    #[staticmethod]
    fn from_maxes(values: Vec<u16>) -> Vec<Self> {
        Constraint::from_maxes(values)
            .into_iter()
            .map(|inner| Self { inner })
            .collect()
    }

    #[staticmethod]
    fn from_fills(values: Vec<u16>) -> Vec<Self> {
        Constraint::from_fills(values)
            .into_iter()
            .map(|inner| Self { inner })
            .collect()
    }

    #[allow(deprecated)]
    fn apply(&self, length: u16) -> u16 {
        self.inner.apply(length)
    }

    fn __repr__(&self) -> String {
        format!("{self:?}", self = self.inner)
    }
}

#[pyclass(name = "Offset", module = "xnano_core._xnano_core")]
#[derive(Clone, Copy)]
pub struct PyOffset {
    pub inner: Offset,
}

#[pymethods]
impl PyOffset {
    #[new]
    #[pyo3(signature = (x=0, y=0))]
    fn new(x: i32, y: i32) -> Self {
        Self {
            inner: Offset { x, y },
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
}

#[pyclass(name = "Size", module = "xnano_core._xnano_core")]
#[derive(Clone, Copy)]
pub struct PySize {
    pub inner: Size,
}

#[pymethods]
impl PySize {
    #[new]
    fn new(width: u16, height: u16) -> Self {
        Self {
            inner: Size::new(width, height),
        }
    }

    #[getter]
    fn width(&self) -> u16 {
        self.inner.width
    }

    #[getter]
    fn height(&self) -> u16 {
        self.inner.height
    }

    fn __repr__(&self) -> String {
        format!(
            "Size(width={}, height={})",
            self.inner.width, self.inner.height
        )
    }
}

#[pyclass(name = "LayoutSpacing", module = "xnano_core._xnano_core")]
#[derive(Clone)]
pub enum PyLayoutSpacing {
    Space(u16),
    Overlap(u16),
}

impl From<PyLayoutSpacing> for Spacing {
    fn from(value: PyLayoutSpacing) -> Self {
        match value {
            PyLayoutSpacing::Space(value) => Spacing::Space(value),
            PyLayoutSpacing::Overlap(value) => Spacing::Overlap(value),
        }
    }
}

#[derive(Clone)]
struct LayoutSpec {
    direction: Direction,
    constraints: Vec<Constraint>,
    horizontal_margin: u16,
    vertical_margin: u16,
    flex: Flex,
    spacing: Spacing,
}

impl LayoutSpec {
    fn default() -> Self {
        Self {
            direction: Direction::Vertical,
            constraints: Vec::new(),
            horizontal_margin: 0,
            vertical_margin: 0,
            flex: Flex::Start,
            spacing: Spacing::Space(0),
        }
    }

    fn to_ratatui(&self) -> Layout {
        let mut layout = Layout::default()
            .direction(self.direction)
            .horizontal_margin(self.horizontal_margin)
            .vertical_margin(self.vertical_margin)
            .flex(self.flex)
            .spacing(self.spacing.clone());
        if !self.constraints.is_empty() {
            layout = layout.constraints(self.constraints.clone());
        }
        layout
    }

    pub(crate) fn to_core(&self) -> ratatui_core::layout::Layout {
        use ratatui_core::layout::{Constraint as CoreConstraint, Flex as CoreFlex, Layout as CoreLayout, Spacing as CoreSpacing};

        let constraints: Vec<CoreConstraint> = self
            .constraints
            .iter()
            .copied()
            .map(|c| match c {
                Constraint::Min(v) => CoreConstraint::Min(v),
                Constraint::Max(v) => CoreConstraint::Max(v),
                Constraint::Length(v) => CoreConstraint::Length(v),
                Constraint::Percentage(v) => CoreConstraint::Percentage(v),
                Constraint::Ratio(n, d) => CoreConstraint::Ratio(n, d),
                Constraint::Fill(v) => CoreConstraint::Fill(v),
            })
            .collect();

        let spacing = match self.spacing {
            Spacing::Space(v) => CoreSpacing::Space(v),
            Spacing::Overlap(v) => CoreSpacing::Overlap(v),
        };

        let flex = match self.flex {
            Flex::Legacy => CoreFlex::Legacy,
            Flex::Start => CoreFlex::Start,
            Flex::End => CoreFlex::End,
            Flex::Center => CoreFlex::Center,
            Flex::SpaceBetween => CoreFlex::SpaceBetween,
            Flex::SpaceAround => CoreFlex::SpaceAround,
        };

        let mut layout = CoreLayout::default()
            .direction(match self.direction {
                Direction::Horizontal => ratatui_core::layout::Direction::Horizontal,
                Direction::Vertical => ratatui_core::layout::Direction::Vertical,
            })
            .horizontal_margin(self.horizontal_margin)
            .vertical_margin(self.vertical_margin)
            .flex(flex)
            .spacing(spacing);
        if !constraints.is_empty() {
            layout = layout.constraints(constraints);
        }
        layout
    }
}

#[pyclass(name = "Layout", module = "xnano_core._xnano_core")]
#[derive(Clone)]
pub struct PyLayout {
    spec: LayoutSpec,
}

impl PyLayout {
    pub(crate) fn core_layout(&self) -> ratatui_core::layout::Layout {
        self.spec.to_core()
    }
}

fn extract_constraints(values: &Bound<'_, PyList>) -> PyResult<Vec<Constraint>> {
    values
        .iter()
        .map(|item| {
            item.extract::<PyRef<PyConstraint>>()
                .map(|c| c.inner)
                .map_err(|_| {
                    PyValueError::new_err("constraints must be a sequence of Constraint")
                })
        })
        .collect()
}

#[pymethods]
impl PyLayout {
    #[staticmethod]
    fn default() -> Self {
        Self {
            spec: LayoutSpec::default(),
        }
    }

    #[staticmethod]
    fn new(direction: PyDirection, constraints: &Bound<'_, PyList>) -> PyResult<Self> {
        Ok(Self {
            spec: LayoutSpec {
                direction: direction.into(),
                constraints: extract_constraints(constraints)?,
                ..LayoutSpec::default()
            },
        })
    }

    #[staticmethod]
    fn vertical(constraints: &Bound<'_, PyList>) -> PyResult<Self> {
        Ok(Self {
            spec: LayoutSpec {
                direction: Direction::Vertical,
                constraints: extract_constraints(constraints)?,
                ..LayoutSpec::default()
            },
        })
    }

    #[staticmethod]
    fn horizontal(constraints: &Bound<'_, PyList>) -> PyResult<Self> {
        Ok(Self {
            spec: LayoutSpec {
                direction: Direction::Horizontal,
                constraints: extract_constraints(constraints)?,
                ..LayoutSpec::default()
            },
        })
    }

    fn direction(&self, direction: PyDirection) -> Self {
        let mut spec = self.spec.clone();
        spec.direction = direction.into();
        Self { spec }
    }

    fn constraints(&self, constraints: &Bound<'_, PyList>) -> PyResult<Self> {
        let mut spec = self.spec.clone();
        spec.constraints = extract_constraints(constraints)?;
        Ok(Self { spec })
    }

    fn margin(&self, value: u16) -> Self {
        let mut spec = self.spec.clone();
        spec.horizontal_margin = value;
        spec.vertical_margin = value;
        Self { spec }
    }

    fn margin_xy(&self, margin: PyMargin) -> Self {
        let mut spec = self.spec.clone();
        spec.horizontal_margin = margin.inner.horizontal;
        spec.vertical_margin = margin.inner.vertical;
        Self { spec }
    }

    fn horizontal_margin(&self, value: u16) -> Self {
        let mut spec = self.spec.clone();
        spec.horizontal_margin = value;
        Self { spec }
    }

    fn vertical_margin(&self, value: u16) -> Self {
        let mut spec = self.spec.clone();
        spec.vertical_margin = value;
        Self { spec }
    }

    fn flex(&self, flex: PyFlex) -> Self {
        let mut spec = self.spec.clone();
        spec.flex = flex.into();
        Self { spec }
    }

    fn spacing(&self, value: i32) -> Self {
        let mut spec = self.spec.clone();
        spec.spacing = Spacing::from(value);
        Self { spec }
    }

    fn spacing_layout(&self, spacing: PyLayoutSpacing) -> Self {
        let mut spec = self.spec.clone();
        spec.spacing = spacing.into();
        Self { spec }
    }

    fn split(&self, area: PyRect) -> Vec<PyRect> {
        self.spec
            .to_ratatui()
            .split(area.inner)
            .iter()
            .map(|rect| PyRect { inner: *rect })
            .collect()
    }

    fn split_with_spacers(&self, area: PyRect) -> (Vec<PyRect>, Vec<PyRect>) {
        let (areas, spacers) = self.spec.to_ratatui().split_with_spacers(area.inner);
        let to_py = |rects: &[_]| rects.iter().map(|rect| PyRect { inner: *rect }).collect();
        (to_py(areas.as_ref()), to_py(spacers.as_ref()))
    }

    fn __repr__(&self) -> String {
        format!("{self:?}", self = self.spec.to_ratatui())
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyRect>()?;
    m.add_class::<PyMargin>()?;
    m.add_class::<PyDirection>()?;
    m.add_class::<PyAlignment>()?;
    m.add_class::<PyFlex>()?;
    m.add_class::<PyConstraint>()?;
    m.add_class::<PyOffset>()?;
    m.add_class::<PySize>()?;
    m.add_class::<PyLayoutSpacing>()?;
    m.add_class::<PyLayout>()?;
    Ok(())
}