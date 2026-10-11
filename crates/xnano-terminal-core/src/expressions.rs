//! Symbolic reads, conditions and operations over owned buffer state.

use std::sync::Arc;

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::pyclass::CompareOp;
use pyo3::types::{PyDict, PyTuple, PyType};
use xnano_terminal_runtime::expression::{
    ArithmeticOp, CompareOp as Comparison, Expr, PropertyId, Scalar,
};
use xnano_terminal_runtime::operation::Operation;

use crate::convert::{scalar_from_py, scalar_to_py};
use crate::errors::eval_error;
use crate::surface::{apply_with_context, environment_from_context};

/// What an expression object holds.
pub enum ExpressionKind {
    /// A readable value or condition.
    Value(Arc<Expr>),
    /// A change to apply. `None` for operations defined in Python.
    Operation(Option<Arc<Operation>>),
    /// A bare `Expression` that holds nothing.
    Empty,
}

#[pyclass(name = "Expression", module = "xnano._xnano_core", subclass)]
pub struct PyExpression {
    pub kind: ExpressionKind,
}

/// The expression behind a value object, or a literal for a plain Python value.
pub fn expression_of(value: &Bound<'_, PyAny>) -> PyResult<Arc<Expr>> {
    if let Ok(expression) = value.extract::<PyRef<'_, PyExpression>>() {
        return match &expression.kind {
            ExpressionKind::Value(expr) => Ok(Arc::clone(expr)),
            _ => Err(PyTypeError::new_err(
                "an operation cannot be used as a value; combine operations with then() or when()",
            )),
        };
    }
    Ok(Expr::literal(scalar_from_py(value)?))
}

/// The operation behind an operation object, if it is a native one.
pub fn operation_of(value: &Bound<'_, PyAny>) -> PyResult<Option<Arc<Operation>>> {
    if let Ok(clear) = value.extract::<PyRef<'_, crate::widgets::clear::PyClear>>() {
        let spec = Arc::clone(&clear.spec);
        return Ok(Some(Arc::new(Operation::Dynamic(
            xnano_terminal_runtime::operation::DynamicOperation::new("Clear", move |resolver| {
                let settings = spec.read();
                let symbol = resolver.get(&settings.symbol)?;
                if xnano_terminal_runtime::text::display_width(&symbol) != 1 {
                    return Err(xnano_terminal_runtime::operation::OperationError::Invalid(
                        "a clear symbol must occupy one column".to_owned(),
                    ));
                }
                let mut cell = ratatui_core::buffer::Cell::default();
                cell.set_symbol(&symbol);
                cell.set_style(settings.style.resolve(resolver)?);
                Ok(Operation::Fill(cell))
            }),
        ))));
    }

    let expression = value.extract::<PyRef<'_, PyExpression>>().map_err(|_| {
        PyTypeError::new_err(format!(
            "expected an Operation but got {}; pass an operation such as Write, Fill, Border \
             or Layout",
            value
                .get_type()
                .name()
                .map_or_else(|_| "?".into(), |name| name.to_string())
        ))
    })?;
    match &expression.kind {
        ExpressionKind::Operation(operation) => Ok(operation.clone()),
        _ => Err(PyTypeError::new_err(
            "update accepts operations only; a query expression reads state with inspect()",
        )),
    }
}

fn class_getitem(cls: &Bound<'_, PyType>, item: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
    let py = cls.py();
    Ok(py
        .import("types")?
        .getattr("GenericAlias")?
        .call1((cls, item))?
        .unbind())
}

#[pymethods]
impl PyExpression {
    #[new]
    #[pyo3(signature = (*_arguments, **_options))]
    fn new(_arguments: &Bound<'_, PyTuple>, _options: Option<&Bound<'_, PyDict>>) -> Self {
        Self {
            kind: ExpressionKind::Empty,
        }
    }

    #[classmethod]
    fn __class_getitem__(cls: &Bound<'_, PyType>, item: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        class_getitem(cls, item)
    }

    /// Read the value (or apply the operation) against `context`.
    fn evaluate<'py>(
        slf: &Bound<'py, Self>,
        context: &Bound<'py, PyAny>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let (value, operation) = {
            let expression = slf.borrow();
            match &expression.kind {
                ExpressionKind::Value(expr) => (Some(Arc::clone(expr)), None),
                ExpressionKind::Operation(operation) => (None, Some(operation.clone())),
                ExpressionKind::Empty => {
                    return Err(PyTypeError::new_err(
                        "this Expression holds nothing to evaluate",
                    ));
                }
            }
        };
        if let Some(expr) = value {
            let environment = environment_from_context(context)?;
            let scalar = py
                .detach(|| expr.evaluate(&environment))
                .map_err(|error| eval_error(&error))?;
            return scalar_to_py(py, &scalar);
        }
        apply_with_context(context, slf.as_any(), operation.flatten())?;
        Ok(py.None().into_bound(py))
    }

    fn __bool__(&self) -> PyResult<bool> {
        Err(PyTypeError::new_err(
            "an Expression has no truth value until it is evaluated; call evaluate(context) or \
             combine conditions with & and | instead of `and` and `or`",
        ))
    }
}

fn predicate(py: Python<'_>, expr: Arc<Expr>) -> PyResult<Py<PyPredicate>> {
    Py::new(
        py,
        PyClassInitializer::from(PyExpression {
            kind: ExpressionKind::Value(expr),
        })
        .add_subclass(PyPredicate),
    )
}

fn numeric(py: Python<'_>, expr: Arc<Expr>) -> PyResult<Py<PyNumericValue>> {
    Py::new(
        py,
        PyClassInitializer::from(PyExpression {
            kind: ExpressionKind::Value(expr),
        })
        .add_subclass(PyValue)
        .add_subclass(PyNumericValue),
    )
}

#[pyclass(name = "Predicate", module = "xnano._xnano_core", extends = PyExpression, subclass)]
pub struct PyPredicate;

#[pymethods]
impl PyPredicate {
    fn __and__(slf: &Bound<'_, Self>, other: &Bound<'_, PyAny>) -> PyResult<Py<PyPredicate>> {
        predicate(
            slf.py(),
            Arc::new(Expr::And(
                expression_of(slf.as_any())?,
                expression_of(other)?,
            )),
        )
    }

    fn __or__(slf: &Bound<'_, Self>, other: &Bound<'_, PyAny>) -> PyResult<Py<PyPredicate>> {
        predicate(
            slf.py(),
            Arc::new(Expr::Or(
                expression_of(slf.as_any())?,
                expression_of(other)?,
            )),
        )
    }

    fn __invert__(slf: &Bound<'_, Self>) -> PyResult<Py<PyPredicate>> {
        predicate(slf.py(), Arc::new(Expr::Not(expression_of(slf.as_any())?)))
    }
}

#[pyclass(name = "Value", module = "xnano._xnano_core", extends = PyExpression, subclass)]
pub struct PyValue;

fn comparison(
    slf: &Bound<'_, PyAny>,
    operation: Comparison,
    other: &Bound<'_, PyAny>,
) -> PyResult<Py<PyPredicate>> {
    predicate(
        slf.py(),
        Arc::new(Expr::Compare(
            operation,
            expression_of(slf)?,
            expression_of(other)?,
        )),
    )
}

#[pymethods]
impl PyValue {
    fn eq(slf: &Bound<'_, Self>, other: &Bound<'_, PyAny>) -> PyResult<Py<PyPredicate>> {
        comparison(slf.as_any(), Comparison::Equal, other)
    }

    fn ne(slf: &Bound<'_, Self>, other: &Bound<'_, PyAny>) -> PyResult<Py<PyPredicate>> {
        comparison(slf.as_any(), Comparison::NotEqual, other)
    }
}

#[pyclass(name = "NumericValue", module = "xnano._xnano_core", extends = PyValue, subclass)]
pub struct PyNumericValue;

fn arithmetic(
    slf: &Bound<'_, PyAny>,
    operation: ArithmeticOp,
    other: &Bound<'_, PyAny>,
    is_reversed: bool,
) -> PyResult<Py<PyNumericValue>> {
    let (left, right) = (expression_of(slf)?, expression_of(other)?);
    let (left, right) = if is_reversed {
        (right, left)
    } else {
        (left, right)
    };
    numeric(slf.py(), Arc::new(Expr::Arithmetic(operation, left, right)))
}

#[pymethods]
impl PyNumericValue {
    fn __richcmp__(
        slf: &Bound<'_, Self>,
        other: &Bound<'_, PyAny>,
        operation: CompareOp,
    ) -> PyResult<Py<PyAny>> {
        let py = slf.py();
        let mapped = match operation {
            CompareOp::Lt => Comparison::Less,
            CompareOp::Le => Comparison::LessEqual,
            CompareOp::Gt => Comparison::Greater,
            CompareOp::Ge => Comparison::GreaterEqual,
            CompareOp::Eq | CompareOp::Ne => return Ok(py.NotImplemented()),
        };
        Ok(comparison(slf.as_any(), mapped, other)?.into_any())
    }

    fn __add__(slf: &Bound<'_, Self>, other: &Bound<'_, PyAny>) -> PyResult<Py<PyNumericValue>> {
        arithmetic(slf.as_any(), ArithmeticOp::Add, other, false)
    }

    fn __radd__(slf: &Bound<'_, Self>, other: &Bound<'_, PyAny>) -> PyResult<Py<PyNumericValue>> {
        arithmetic(slf.as_any(), ArithmeticOp::Add, other, true)
    }

    fn __sub__(slf: &Bound<'_, Self>, other: &Bound<'_, PyAny>) -> PyResult<Py<PyNumericValue>> {
        arithmetic(slf.as_any(), ArithmeticOp::Subtract, other, false)
    }

    fn __rsub__(slf: &Bound<'_, Self>, other: &Bound<'_, PyAny>) -> PyResult<Py<PyNumericValue>> {
        arithmetic(slf.as_any(), ArithmeticOp::Subtract, other, true)
    }

    fn __mul__(slf: &Bound<'_, Self>, other: &Bound<'_, PyAny>) -> PyResult<Py<PyNumericValue>> {
        arithmetic(slf.as_any(), ArithmeticOp::Multiply, other, false)
    }

    fn __rmul__(slf: &Bound<'_, Self>, other: &Bound<'_, PyAny>) -> PyResult<Py<PyNumericValue>> {
        arithmetic(slf.as_any(), ArithmeticOp::Multiply, other, true)
    }

    fn __truediv__(
        slf: &Bound<'_, Self>,
        other: &Bound<'_, PyAny>,
    ) -> PyResult<Py<PyNumericValue>> {
        arithmetic(slf.as_any(), ArithmeticOp::Divide, other, false)
    }

    fn __mod__(slf: &Bound<'_, Self>, other: &Bound<'_, PyAny>) -> PyResult<Py<PyNumericValue>> {
        arithmetic(slf.as_any(), ArithmeticOp::Modulo, other, false)
    }

    fn __neg__(slf: &Bound<'_, Self>) -> PyResult<Py<PyNumericValue>> {
        numeric(
            slf.py(),
            Arc::new(Expr::Negate(expression_of(slf.as_any())?)),
        )
    }
}

pub fn property_id(name: &str) -> Option<PropertyId> {
    Some(match name {
        "X" => PropertyId::X,
        "Y" => PropertyId::Y,
        "Width" => PropertyId::Width,
        "Height" => PropertyId::Height,
        "Position" => PropertyId::Position,
        "Size" => PropertyId::Size,
        "Bounds" => PropertyId::Bounds,
        "Elapsed" => PropertyId::Elapsed,
        "Delta" => PropertyId::Delta,
        "ElapsedMilliseconds" => PropertyId::ElapsedMilliseconds,
        "DeltaMilliseconds" => PropertyId::DeltaMilliseconds,
        "Frame" => PropertyId::Frame,
        "FPS" => PropertyId::FramesPerSecond,
        "Focused" => PropertyId::Focused,
        "Running" => PropertyId::Running,
        "DeviceWidth" => PropertyId::DeviceWidth,
        "DeviceHeight" => PropertyId::DeviceHeight,
        _ => return None,
    })
}

fn assignment(
    py: Python<'_>,
    property: PropertyId,
    value: &Bound<'_, PyAny>,
) -> PyResult<Py<PySetValue>> {
    if !property.is_settable() {
        return Err(PyValueError::new_err(format!(
            "{} is read-only; only X, Y, Width, Height, Position and Size can be assigned",
            property.name()
        )));
    }
    let operation = Operation::SetValue {
        property,
        value: expression_of(value)?,
    };
    Py::new(
        py,
        PyClassInitializer::from(PyExpression {
            kind: ExpressionKind::Operation(Some(Arc::new(operation))),
        })
        .add_subclass(PyOperation)
        .add_subclass(PySetValue),
    )
}

#[pyclass(name = "Property", module = "xnano._xnano_core", extends = PyValue, subclass)]
pub struct PyProperty {
    id: PropertyId,
}

#[pymethods]
impl PyProperty {
    #[getter]
    fn name(&self) -> &'static str {
        self.id.name()
    }

    fn __call__(&self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<Py<PySetValue>> {
        assignment(py, self.id, value)
    }

    fn __repr__(&self) -> String {
        format!("Property({})", self.id.name())
    }
}

#[pyclass(name = "NumericProperty", module = "xnano._xnano_core", extends = PyNumericValue, subclass)]
pub struct PyNumericProperty {
    id: PropertyId,
}

#[pymethods]
impl PyNumericProperty {
    #[getter]
    fn name(&self) -> &'static str {
        self.id.name()
    }

    fn __call__(&self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<Py<PySetValue>> {
        assignment(py, self.id, value)
    }

    fn __repr__(&self) -> String {
        format!("NumericProperty({})", self.id.name())
    }
}

#[pyclass(name = "Operation", module = "xnano._xnano_core", extends = PyExpression, subclass)]
pub struct PyOperation;

/// Combine two operation objects into a sequence.
fn sequence(py: Python<'_>, steps: Vec<Arc<Operation>>) -> PyResult<Py<PySequenceOperation>> {
    Py::new(
        py,
        PyClassInitializer::from(PyExpression {
            kind: ExpressionKind::Operation(Some(Arc::new(Operation::Sequence(steps)))),
        })
        .add_subclass(PyOperation)
        .add_subclass(PySequenceOperation),
    )
}

fn native_step(value: &Bound<'_, PyAny>) -> PyResult<Arc<Operation>> {
    operation_of(value)?.ok_or_else(|| {
        PyTypeError::new_err(
            "an operation defined in Python cannot be combined; apply it with update() on its own",
        )
    })
}

#[pymethods]
impl PyOperation {
    /// Operations defined in Python accept any constructor arguments; their handlers give
    /// them meaning.
    #[new]
    #[pyo3(signature = (*_arguments, **_options))]
    fn new(
        _arguments: &Bound<'_, PyTuple>,
        _options: Option<&Bound<'_, PyDict>>,
    ) -> PyClassInitializer<Self> {
        PyClassInitializer::from(PyExpression {
            kind: ExpressionKind::Operation(None),
        })
        .add_subclass(Self)
    }

    pub(crate) fn then(
        slf: &Bound<'_, Self>,
        other: &Bound<'_, PyAny>,
    ) -> PyResult<Py<PySequenceOperation>> {
        sequence(
            slf.py(),
            vec![native_step(slf.as_any())?, native_step(other)?],
        )
    }

    fn when(slf: &Bound<'_, Self>, condition: &Bound<'_, PyAny>) -> PyResult<Py<PyConditional>> {
        conditional(slf.py(), condition, slf.as_any(), None)
    }
}

#[pyclass(name = "SetValue", module = "xnano._xnano_core", extends = PyOperation)]
pub struct PySetValue;

#[pymethods]
impl PySetValue {
    #[new]
    fn new(
        property: &Bound<'_, PyAny>,
        value: &Bound<'_, PyAny>,
    ) -> PyResult<PyClassInitializer<Self>> {
        let name: String = property
            .getattr("name")
            .and_then(|name| name.extract())
            .map_err(|_| PyTypeError::new_err("SetValue needs a Property such as X or Width"))?;
        let id = property_id(&name)
            .ok_or_else(|| PyValueError::new_err(format!("\"{name}\" is not a known property")))?;
        if !id.is_settable() {
            return Err(PyValueError::new_err(format!(
                "{} is read-only; only X, Y, Width, Height, Position and Size can be assigned",
                id.name()
            )));
        }
        Ok(PyClassInitializer::from(PyExpression {
            kind: ExpressionKind::Operation(Some(Arc::new(Operation::SetValue {
                property: id,
                value: expression_of(value)?,
            }))),
        })
        .add_subclass(PyOperation)
        .add_subclass(Self))
    }
}

#[pyclass(name = "SequenceOperation", module = "xnano._xnano_core", extends = PyOperation)]
pub struct PySequenceOperation;

#[pymethods]
impl PySequenceOperation {
    #[new]
    #[pyo3(signature = (*operations))]
    fn new(operations: &Bound<'_, PyTuple>) -> PyResult<PyClassInitializer<Self>> {
        let steps = operations
            .iter()
            .map(|step| native_step(&step))
            .collect::<PyResult<Vec<_>>>()?;
        Ok(PyClassInitializer::from(PyExpression {
            kind: ExpressionKind::Operation(Some(Arc::new(Operation::Sequence(steps)))),
        })
        .add_subclass(PyOperation)
        .add_subclass(Self))
    }
}

fn conditional(
    py: Python<'_>,
    condition: &Bound<'_, PyAny>,
    operation: &Bound<'_, PyAny>,
    otherwise: Option<&Bound<'_, PyAny>>,
) -> PyResult<Py<PyConditional>> {
    let condition_expr = expression_of(condition)?;
    let otherwise = otherwise
        .filter(|value| !value.is_none())
        .map(native_step)
        .transpose()?;
    Py::new(
        py,
        PyClassInitializer::from(PyExpression {
            kind: ExpressionKind::Operation(Some(Arc::new(Operation::Conditional {
                condition: condition_expr,
                then: native_step(operation)?,
                otherwise,
            }))),
        })
        .add_subclass(PyOperation)
        .add_subclass(PyConditional),
    )
}

#[pyclass(name = "Conditional", module = "xnano._xnano_core", extends = PyOperation)]
pub struct PyConditional;

#[pymethods]
impl PyConditional {
    #[new]
    #[pyo3(signature = (condition, operation, *, otherwise = None))]
    fn new(
        condition: &Bound<'_, PyAny>,
        operation: &Bound<'_, PyAny>,
        otherwise: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<PyClassInitializer<Self>> {
        let otherwise = otherwise
            .filter(|value| !value.is_none())
            .map(native_step)
            .transpose()?;
        Ok(PyClassInitializer::from(PyExpression {
            kind: ExpressionKind::Operation(Some(Arc::new(Operation::Conditional {
                condition: expression_of(condition)?,
                then: native_step(operation)?,
                otherwise,
            }))),
        })
        .add_subclass(PyOperation)
        .add_subclass(Self))
    }
}

/// The module-level read-only and assignable references such as `X` and `Elapsed`.
#[pyfunction]
fn _reference(py: Python<'_>, name: &str, kind: &str) -> PyResult<Py<PyAny>> {
    let id = property_id(name)
        .ok_or_else(|| PyValueError::new_err(format!("\"{name}\" is not a known property")))?;
    let base = PyExpression {
        kind: ExpressionKind::Value(Arc::new(Expr::Property(id))),
    };
    Ok(match kind {
        "numeric_property" => Py::new(
            py,
            PyClassInitializer::from(base)
                .add_subclass(PyValue)
                .add_subclass(PyNumericValue)
                .add_subclass(PyNumericProperty { id }),
        )?
        .into_any(),
        "property" => Py::new(
            py,
            PyClassInitializer::from(base)
                .add_subclass(PyValue)
                .add_subclass(PyProperty { id }),
        )?
        .into_any(),
        "numeric" => Py::new(
            py,
            PyClassInitializer::from(base)
                .add_subclass(PyValue)
                .add_subclass(PyNumericValue),
        )?
        .into_any(),
        _ => Py::new(py, PyClassInitializer::from(base).add_subclass(PyValue))?.into_any(),
    })
}

/// A value an installed extension provides by name.
#[pyfunction]
fn _external(py: Python<'_>, name: String, is_numeric: bool) -> PyResult<Py<PyAny>> {
    let base = PyExpression {
        kind: ExpressionKind::Value(Arc::new(Expr::External(name))),
    };
    Ok(if is_numeric {
        Py::new(
            py,
            PyClassInitializer::from(base)
                .add_subclass(PyValue)
                .add_subclass(PyNumericValue),
        )?
        .into_any()
    } else {
        Py::new(py, PyClassInitializer::from(base).add_subclass(PyValue))?.into_any()
    })
}

/// A value expression reading a branch of a state store.
#[pyfunction]
fn _state_expression(
    py: Python<'_>,
    store: &crate::state::PyStateStore,
    path: &Bound<'_, PyAny>,
    is_numeric: bool,
) -> PyResult<Py<PyAny>> {
    state_expression(
        py,
        Arc::clone(&store.inner),
        crate::convert::path_from_py(path)?,
        is_numeric,
    )
}

pub fn state_expression(
    py: Python<'_>,
    store: Arc<xnano_terminal_state::Store>,
    path: Vec<String>,
    is_numeric: bool,
) -> PyResult<Py<PyAny>> {
    let base = PyExpression {
        kind: ExpressionKind::Value(Arc::new(Expr::State(store, path))),
    };
    Ok(if is_numeric {
        Py::new(
            py,
            PyClassInitializer::from(base)
                .add_subclass(PyValue)
                .add_subclass(PyNumericValue),
        )?
        .into_any()
    } else {
        Py::new(py, PyClassInitializer::from(base).add_subclass(PyValue))?.into_any()
    })
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyExpression>()?;
    m.add_class::<PyPredicate>()?;
    m.add_class::<PyValue>()?;
    m.add_class::<PyNumericValue>()?;
    m.add_class::<PyProperty>()?;
    m.add_class::<PyNumericProperty>()?;
    m.add_class::<PyOperation>()?;
    m.add_class::<PySetValue>()?;
    m.add_class::<PySequenceOperation>()?;
    m.add_class::<PyConditional>()?;
    m.add_function(wrap_pyfunction!(_reference, m)?)?;
    m.add_function(wrap_pyfunction!(_external, m)?)?;
    m.add_function(wrap_pyfunction!(_state_expression, m)?)
}

#[allow(dead_code)]
fn unused(_: Scalar) {}
