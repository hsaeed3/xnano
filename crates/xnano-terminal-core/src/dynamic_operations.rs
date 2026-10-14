//! Operations whose settings may be plain values or expressions.
//!
//! Each constructor reads its arguments as [`Dynamic`] values. When none is bound the
//! operation is built once, exactly as before. When any is bound the operation keeps its
//! settings and builds the concrete operation each time it is applied, reading the
//! expressions against the target's environment.

use pyo3::prelude::*;
use xnano_terminal_runtime::dynamic::Dynamic;
use xnano_terminal_runtime::expression::{Environment, EvalError, PropertyId, Scalar};
use xnano_terminal_runtime::grid::{PasteMode, WriteMode};
use xnano_terminal_runtime::operation::{BorderKind, DynamicOperation, Operation, OperationError};
use xnano_terminal_runtime::pixel::{PixelEncoding, RasterMode};
use xnano_terminal_runtime::text::{Line, Span, split_lines};
use xnano_terminal_runtime::widgets::Resolver;
use xnano_terminal_state::Node;

use crate::errors::operation_error;
use crate::expressions::{ExpressionKind, PyExpression, PyOperation};
use crate::operations::operation_initializer;
use crate::widgets::dynamic_arg;

/// An environment for building operations whose settings are all fixed.
struct Offline;

impl Environment for Offline {
    fn property(&self, id: PropertyId) -> Result<Scalar, EvalError> {
        Err(EvalError::RuntimeRequired(format!(
            "{} needs a runtime",
            id.name()
        )))
    }
}

/// The finished operation: built now when every setting is fixed, else on each apply.
pub fn finish(
    py: Python<'_>,
    name: &'static str,
    has_bound_setting: bool,
    make: impl Fn(&mut Resolver<'_>) -> Result<Operation, OperationError> + Send + Sync + 'static,
) -> PyResult<PyClassInitializer<PyOperation>> {
    if has_bound_setting {
        return Ok(PyClassInitializer::from(PyExpression {
            kind: ExpressionKind::Operation(Some(std::sync::Arc::new(Operation::Dynamic(
                DynamicOperation::new(name, make),
            )))),
        })
        .add_subclass(PyOperation));
    }
    let operation =
        make(&mut Resolver::new(&Offline)).map_err(|error| operation_error(py, &error))?;
    Ok(operation_initializer(operation))
}

pub fn dynamic_i32(value: &Bound<'_, PyAny>) -> PyResult<Dynamic<i32>> {
    dynamic_arg(value, |value| value.extract())
}

pub fn dynamic_name(value: &Bound<'_, PyAny>) -> PyResult<Dynamic<String>> {
    dynamic_arg(value, |value| value.extract())
}

/// A setting that is a plain value of `T`, converted by `convert`, or an expression.
pub fn dynamic_scalar(value: &Bound<'_, PyAny>) -> PyResult<Dynamic<Scalar>> {
    dynamic_arg(value, crate::convert::scalar_from_py)
}

fn unknown(kind: &str, name: &str, choices: &str) -> OperationError {
    OperationError::Invalid(format!("\"{name}\" is not a {kind}; use {choices}"))
}

pub fn parse_write_mode(name: &str) -> Result<WriteMode, OperationError> {
    WriteMode::from_name(name)
        .ok_or_else(|| unknown("write mode", name, "\"replace\" or \"preserve_background\""))
}

pub fn parse_paste_mode(name: &str) -> Result<PasteMode, OperationError> {
    match name {
        "replace" => Ok(PasteMode::Replace),
        "preserve_background" => Ok(PasteMode::PreserveBackground),
        other => Err(unknown(
            "blend mode",
            other,
            "\"replace\" or \"preserve_background\"",
        )),
    }
}

pub fn parse_encoding(name: &str) -> Result<PixelEncoding, OperationError> {
    PixelEncoding::from_name(name)
        .ok_or_else(|| unknown("pixel encoding", name, "\"half_blocks\" or \"braille\""))
}

pub fn parse_raster_mode(name: &str) -> Result<RasterMode, OperationError> {
    RasterMode::from_name(name)
        .ok_or_else(|| unknown("raster mode", name, "\"replace\" or \"over\""))
}

pub fn parse_border_kind(name: &str) -> Result<BorderKind, OperationError> {
    BorderKind::from_name(name).ok_or_else(|| {
        unknown(
            "border kind",
            name,
            "\"plain\", \"rounded\", \"double\" or \"thick\"",
        )
    })
}

/// Text written by an operation: fixed styled lines, or text read from an expression.
#[derive(Clone)]
pub enum TextSetting {
    Lines(Vec<Line>),
    Bound(Dynamic<String>),
}

impl TextSetting {
    pub fn from_py(value: &Bound<'_, PyAny>) -> PyResult<Self> {
        if value.extract::<PyRef<'_, PyExpression>>().is_ok() {
            return Ok(Self::Bound(dynamic_arg(value, |value| value.extract())?));
        }
        Ok(Self::Lines(crate::convert::text_lines(value)?))
    }

    pub fn is_bound(&self) -> bool {
        matches!(self, Self::Bound(_))
    }

    pub fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Vec<Line>, EvalError> {
        match self {
            Self::Lines(lines) => Ok(lines.clone()),
            Self::Bound(text) => Ok(split_lines(&[Span::new(
                resolver.get(text)?,
                xnano_terminal_runtime::style::Style::default(),
            )])),
        }
    }
}

/// A state value an expression produced, as a state node.
pub fn scalar_to_node(scalar: &Scalar) -> Result<Node, OperationError> {
    let json = match scalar {
        Scalar::Null => serde_json::Value::Null,
        Scalar::Bool(flag) => serde_json::Value::Bool(*flag),
        Scalar::Integer(integer) => serde_json::Value::from(*integer),
        Scalar::Float(float) => serde_json::Number::from_f64(*float)
            .map(serde_json::Value::Number)
            .ok_or_else(|| {
                OperationError::Invalid(format!(
                    "the value {float} is not a finite number, so it cannot be stored in state"
                ))
            })?,
        Scalar::Text(text) => serde_json::Value::String(text.clone()),
        Scalar::Json(value) => value.clone(),
        other => {
            return Err(OperationError::Invalid(format!(
                "a {} cannot be stored in state; store numbers, text, booleans, lists or objects",
                other.type_name()
            )));
        }
    };
    Node::from_json(&json).map_err(|error| OperationError::Invalid(error.to_string()))
}
