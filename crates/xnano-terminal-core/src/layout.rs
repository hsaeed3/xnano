//! `SizeRule` and `Layout`.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use xnano_terminal_runtime::layout::{Arrangement, LayoutSpec, SizeRule};
use xnano_terminal_runtime::operation::Operation;

use crate::expressions::PyOperation;
use crate::operations::operation_initializer;

#[pyclass(
    name = "SizeRule",
    module = "xnano._xnano_core",
    frozen,
    eq,
    hash,
    from_py_object
)]
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct PySizeRule {
    kind: u8,
    amount: u16,
}

fn small(value: i64, name: &str) -> PyResult<u16> {
    u16::try_from(value).map_err(|_| {
        PyValueError::new_err(format!(
            "{name} must be a whole number from 0 to 65535, not {value}"
        ))
    })
}

impl PySizeRule {
    pub fn percent_rule(amount: u16) -> Self {
        Self { kind: 1, amount }
    }

    pub fn fill_rule(amount: u16) -> Self {
        Self { kind: 2, amount }
    }

    pub fn minimum_rule(amount: u16) -> Self {
        Self { kind: 4, amount }
    }

    pub fn maximum_rule(amount: u16) -> Self {
        Self { kind: 5, amount }
    }

    pub fn rule(self) -> SizeRule {
        match self.kind {
            0 => SizeRule::Cells(self.amount),
            1 => SizeRule::Percent(self.amount),
            2 => SizeRule::Fill(self.amount),
            3 => SizeRule::Fit,
            4 => SizeRule::Minimum(self.amount),
            _ => SizeRule::Maximum(self.amount),
        }
    }
}

#[pymethods]
impl PySizeRule {
    fn __copy__(&self) -> Self {
        *self
    }
    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        *self
    }

    #[classmethod]
    fn cells(_cls: &Bound<'_, pyo3::types::PyType>, count: i64) -> PyResult<Self> {
        Ok(Self {
            kind: 0,
            amount: small(count, "the cell count")?,
        })
    }

    #[classmethod]
    fn percent(_cls: &Bound<'_, pyo3::types::PyType>, percentage: i64) -> PyResult<Self> {
        if !(0..=100).contains(&percentage) {
            return Err(PyValueError::new_err(format!(
                "a percentage rule needs a value from 0 to 100, not {percentage}"
            )));
        }
        Ok(Self {
            kind: 1,
            amount: percentage as u16,
        })
    }

    #[classmethod]
    #[pyo3(signature = (weight = 1))]
    fn fill(_cls: &Bound<'_, pyo3::types::PyType>, weight: i64) -> PyResult<Self> {
        if weight < 1 {
            return Err(PyValueError::new_err(format!(
                "a fill weight must be at least 1, not {weight}"
            )));
        }
        Ok(Self {
            kind: 2,
            amount: small(weight, "the fill weight")?,
        })
    }

    #[classmethod]
    fn fit(_cls: &Bound<'_, pyo3::types::PyType>) -> Self {
        Self { kind: 3, amount: 0 }
    }

    #[classmethod]
    fn minimum(_cls: &Bound<'_, pyo3::types::PyType>, count: i64) -> PyResult<Self> {
        Ok(Self {
            kind: 4,
            amount: small(count, "the minimum")?,
        })
    }

    #[classmethod]
    fn maximum(_cls: &Bound<'_, pyo3::types::PyType>, count: i64) -> PyResult<Self> {
        Ok(Self {
            kind: 5,
            amount: small(count, "the maximum")?,
        })
    }

    fn __repr__(&self) -> String {
        match self.kind {
            0 => format!("SizeRule.cells({})", self.amount),
            1 => format!("SizeRule.percent({})", self.amount),
            2 => format!("SizeRule.fill({})", self.amount),
            3 => "SizeRule.fit()".to_owned(),
            4 => format!("SizeRule.minimum({})", self.amount),
            _ => format!("SizeRule.maximum({})", self.amount),
        }
    }
}

#[pyclass(name = "Layout", module = "xnano._xnano_core", extends = PyOperation)]
pub struct PyLayout;

#[pymethods]
impl PyLayout {
    /// Split a rectangle through ratatui's constraint solver.
    #[staticmethod]
    #[pyo3(signature = (rectangle, *, arrangement = "column", constraints, spacing = 0))]
    fn split(
        rectangle: &crate::geometry::PyRectangle,
        arrangement: &str,
        constraints: Vec<(String, u16, u16)>,
        spacing: u16,
    ) -> PyResult<Vec<crate::geometry::PyRectangle>> {
        use ratatui_core::layout::{Constraint, Direction, Layout, Rect};
        let direction = match arrangement {
            "row" => Direction::Horizontal,
            "column" => Direction::Vertical,
            _ => {
                return Err(PyValueError::new_err(
                    "split arrangement must be row or column",
                ));
            }
        };
        let constraints = constraints
            .into_iter()
            .map(|(kind, value, denominator)| {
                Ok(match kind.as_str() {
                    "length" => Constraint::Length(value),
                    "percentage" => Constraint::Percentage(value),
                    "ratio" if denominator > 0 => {
                        Constraint::Ratio(u32::from(value), u32::from(denominator))
                    }
                    "minimum" => Constraint::Min(value),
                    "maximum" => Constraint::Max(value),
                    "fill" => Constraint::Fill(value),
                    _ => {
                        return Err(PyValueError::new_err(format!(
                            "invalid layout constraint {kind:?}"
                        )));
                    }
                })
            })
            .collect::<PyResult<Vec<_>>>()?;
        Ok(Layout::default()
            .direction(direction)
            .constraints(constraints)
            .spacing(spacing)
            .split(Rect::new(
                rectangle.inner.x.clamp(0, 65535) as u16,
                rectangle.inner.y.clamp(0, 65535) as u16,
                rectangle.inner.width.clamp(0, 65535) as u16,
                rectangle.inner.height.clamp(0, 65535) as u16,
            ))
            .iter()
            .map(|inner| crate::geometry::PyRectangle {
                inner: xnano_terminal_runtime::geometry::Rectangle::new(
                    i32::from(inner.x),
                    i32::from(inner.y),
                    i32::from(inner.width),
                    i32::from(inner.height),
                ),
            })
            .collect())
    }

    #[new]
    #[pyo3(signature = (arrangement = "column", *, sizes = None, spacing = 0, padding = 0))]
    fn new(
        arrangement: &str,
        sizes: Option<&Bound<'_, PyAny>>,
        spacing: i64,
        padding: i64,
    ) -> PyResult<PyClassInitializer<Self>> {
        let arrangement = Arrangement::from_name(arrangement).ok_or_else(|| {
            PyValueError::new_err(format!(
                "\"{arrangement}\" is not an arrangement; use \"row\", \"column\" or \"overlay\""
            ))
        })?;
        let mut rules = Vec::new();
        if let Some(sizes) = sizes {
            for item in sizes.try_iter()? {
                rules.push(item?.extract::<PySizeRule>()?.rule());
            }
        }
        let spec = LayoutSpec {
            arrangement,
            sizes: rules,
            spacing: small(spacing, "spacing")?,
            padding: small(padding, "padding")?,
        };
        Ok(operation_initializer(Operation::Layout(spec)).add_subclass(Self))
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PySizeRule>()?;
    m.add_class::<PyLayout>()
}
