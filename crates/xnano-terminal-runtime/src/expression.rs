//! Symbolic reads and conditions, evaluated on demand against an [`Environment`].

use std::collections::HashMap;
use std::fmt;
use std::sync::Arc;

use serde_json::Value;
use xnano_terminal_state::{Node, Snapshot, Store};

use crate::geometry::{Point, Rectangle, Size};

/// A value an expression can produce.
#[derive(Debug, Clone, PartialEq)]
pub enum Scalar {
    Null,
    Bool(bool),
    Integer(i64),
    Float(f64),
    Text(String),
    Point(Point),
    Size(Size),
    Rectangle(Rectangle),
    /// A state branch that is a list or an object.
    Json(Value),
}

impl Scalar {
    pub fn type_name(&self) -> &'static str {
        match self {
            Self::Null => "None",
            Self::Bool(_) => "bool",
            Self::Integer(_) => "int",
            Self::Float(_) => "float",
            Self::Text(_) => "str",
            Self::Point(_) => "Point",
            Self::Size(_) => "Size",
            Self::Rectangle(_) => "Rectangle",
            Self::Json(_) => "state value",
        }
    }

    pub fn as_number(&self) -> Option<f64> {
        match self {
            Self::Integer(integer) => Some(*integer as f64),
            Self::Float(float) => Some(*float),
            _ => None,
        }
    }

    pub fn is_truthy(&self) -> Option<bool> {
        match self {
            Self::Bool(flag) => Some(*flag),
            _ => None,
        }
    }

    pub fn from_node(node: &Node) -> Self {
        match node {
            Node::Null => Self::Null,
            Node::Bool(flag) => Self::Bool(*flag),
            Node::Integer(integer) => Self::Integer(*integer),
            Node::Float(float) => Self::Float(*float),
            Node::String(text) => Self::Text(text.to_string()),
            other => Self::Json(other.to_json()),
        }
    }
}

/// The readable (and, for some, writable) facts about a target and its runtime.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum PropertyId {
    X,
    Y,
    Width,
    Height,
    Position,
    Size,
    Bounds,
    Elapsed,
    Delta,
    ElapsedMilliseconds,
    DeltaMilliseconds,
    Frame,
    FramesPerSecond,
    Focused,
    Running,
    DeviceWidth,
    DeviceHeight,
}

impl PropertyId {
    pub fn name(self) -> &'static str {
        match self {
            Self::X => "X",
            Self::Y => "Y",
            Self::Width => "Width",
            Self::Height => "Height",
            Self::Position => "Position",
            Self::Size => "Size",
            Self::Bounds => "Bounds",
            Self::Elapsed => "Elapsed",
            Self::Delta => "Delta",
            Self::ElapsedMilliseconds => "ElapsedMilliseconds",
            Self::DeltaMilliseconds => "DeltaMilliseconds",
            Self::Frame => "Frame",
            Self::FramesPerSecond => "FPS",
            Self::Focused => "Focused",
            Self::Running => "Running",
            Self::DeviceWidth => "DeviceWidth",
            Self::DeviceHeight => "DeviceHeight",
        }
    }

    /// Whether an assignment such as `Width(40)` is meaningful.
    pub fn is_settable(self) -> bool {
        matches!(
            self,
            Self::X | Self::Y | Self::Width | Self::Height | Self::Position | Self::Size
        )
    }

    /// Whether reading it needs a running or mounted runtime.
    pub fn needs_runtime(self) -> bool {
        !matches!(
            self,
            Self::X
                | Self::Y
                | Self::Width
                | Self::Height
                | Self::Position
                | Self::Size
                | Self::Bounds
        )
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CompareOp {
    Equal,
    NotEqual,
    Less,
    LessEqual,
    Greater,
    GreaterEqual,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ArithmeticOp {
    Add,
    Subtract,
    Multiply,
    Divide,
    Modulo,
}

/// A symbolic expression.
#[derive(Debug, Clone)]
pub enum Expr {
    Literal(Scalar),
    Property(PropertyId),
    State(Arc<Store>, Vec<String>),
    /// A value an extension provides by name, such as the current musical beat.
    External(String),
    Not(Arc<Expr>),
    And(Arc<Expr>, Arc<Expr>),
    Or(Arc<Expr>, Arc<Expr>),
    Compare(CompareOp, Arc<Expr>, Arc<Expr>),
    Arithmetic(ArithmeticOp, Arc<Expr>, Arc<Expr>),
    Negate(Arc<Expr>),
}

/// Why an expression could not be evaluated.
#[derive(Debug, Clone, PartialEq)]
pub enum EvalError {
    /// The expression reads something only a running or mounted runtime has.
    RuntimeRequired(String),
    Type(String),
    State(String),
    DivisionByZero,
}

impl fmt::Display for EvalError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::RuntimeRequired(message) | Self::Type(message) | Self::State(message) => {
                formatter.write_str(message)
            }
            Self::DivisionByZero => formatter.write_str(
                "the expression divides or takes a remainder by zero; check the divisor first",
            ),
        }
    }
}

impl std::error::Error for EvalError {}

/// Where property reads come from.
pub trait Environment {
    fn property(&self, id: PropertyId) -> Result<Scalar, EvalError>;

    /// A value provided by name by an installed extension.
    fn external(&self, name: &str) -> Result<Scalar, EvalError> {
        Err(EvalError::RuntimeRequired(format!(
            "{name} needs a runtime with its extension installed; mount the buffer on a Runtime and \
             install the extension first"
        )))
    }
}

/// Evaluation state: one consistent snapshot per referenced state store.
#[derive(Default)]
pub struct Evaluation {
    snapshots: HashMap<u64, Snapshot>,
}

fn compare(operation: CompareOp, left: &Scalar, right: &Scalar) -> Result<bool, EvalError> {
    if let (Some(a), Some(b)) = (left.as_number(), right.as_number()) {
        let exact = match (left, right) {
            (Scalar::Integer(a), Scalar::Integer(b)) => Some(a.cmp(b)),
            _ => a.partial_cmp(&b),
        };
        return Ok(match (operation, exact) {
            (CompareOp::Equal, ordering) => ordering == Some(std::cmp::Ordering::Equal),
            (CompareOp::NotEqual, ordering) => ordering != Some(std::cmp::Ordering::Equal),
            (_, None) => false,
            (CompareOp::Less, Some(ordering)) => ordering.is_lt(),
            (CompareOp::LessEqual, Some(ordering)) => ordering.is_le(),
            (CompareOp::Greater, Some(ordering)) => ordering.is_gt(),
            (CompareOp::GreaterEqual, Some(ordering)) => ordering.is_ge(),
        });
    }
    match operation {
        CompareOp::Equal => Ok(left == right),
        CompareOp::NotEqual => Ok(left != right),
        _ => {
            if let (Scalar::Text(a), Scalar::Text(b)) = (left, right) {
                return Ok(match operation {
                    CompareOp::Less => a < b,
                    CompareOp::LessEqual => a <= b,
                    CompareOp::Greater => a > b,
                    _ => a >= b,
                });
            }
            Err(EvalError::Type(format!(
                "cannot order a {} against a {}; compare numbers with numbers or text with text",
                left.type_name(),
                right.type_name()
            )))
        }
    }
}

fn arithmetic(operation: ArithmeticOp, left: &Scalar, right: &Scalar) -> Result<Scalar, EvalError> {
    if let (Scalar::Integer(a), Scalar::Integer(b)) = (left, right) {
        let result = match operation {
            ArithmeticOp::Add => a.checked_add(*b),
            ArithmeticOp::Subtract => a.checked_sub(*b),
            ArithmeticOp::Multiply => a.checked_mul(*b),
            ArithmeticOp::Modulo => {
                if *b == 0 {
                    return Err(EvalError::DivisionByZero);
                }
                Some(a.rem_euclid(*b))
            }
            ArithmeticOp::Divide => None,
        };
        if let Some(value) = result {
            return Ok(Scalar::Integer(value));
        }
    }
    let (Some(a), Some(b)) = (left.as_number(), right.as_number()) else {
        return Err(EvalError::Type(format!(
            "cannot do arithmetic on a {} and a {}; both sides must be numbers",
            left.type_name(),
            right.type_name()
        )));
    };
    Ok(Scalar::Float(match operation {
        ArithmeticOp::Add => a + b,
        ArithmeticOp::Subtract => a - b,
        ArithmeticOp::Multiply => a * b,
        ArithmeticOp::Divide => {
            if b == 0.0 {
                return Err(EvalError::DivisionByZero);
            }
            a / b
        }
        ArithmeticOp::Modulo => {
            if b == 0.0 {
                return Err(EvalError::DivisionByZero);
            }
            a.rem_euclid(b)
        }
    }))
}

impl Expr {
    pub fn literal(value: Scalar) -> Arc<Self> {
        Arc::new(Self::Literal(value))
    }

    pub fn evaluate(&self, environment: &dyn Environment) -> Result<Scalar, EvalError> {
        self.evaluate_with(environment, &mut Evaluation::default())
    }

    pub fn evaluate_with(
        &self,
        environment: &dyn Environment,
        evaluation: &mut Evaluation,
    ) -> Result<Scalar, EvalError> {
        match self {
            Self::Literal(value) => Ok(value.clone()),
            Self::Property(id) => environment.property(*id),
            Self::External(name) => environment.external(name),
            Self::State(store, path) => {
                let snapshot = match evaluation.snapshots.get(&store.id()) {
                    Some(snapshot) => snapshot.clone(),
                    None => {
                        let snapshot = store
                            .snapshot(&[])
                            .map_err(|error| EvalError::State(error.to_string()))?;
                        evaluation.snapshots.insert(store.id(), snapshot.clone());
                        snapshot
                    }
                };
                snapshot
                    .node
                    .get(path)
                    .map(Scalar::from_node)
                    .ok_or_else(|| {
                        EvalError::State(format!(
                            "the state branch {} no longer exists; check that it is still part \
                             of the state before reading it",
                            xnano_terminal_state::to_pointer(path)
                        ))
                    })
            }
            Self::Not(inner) => match inner.evaluate_with(environment, evaluation)?.is_truthy() {
                Some(flag) => Ok(Scalar::Bool(!flag)),
                None => Err(EvalError::Type(
                    "only a condition can be inverted with ~".to_owned(),
                )),
            },
            Self::And(left, right) | Self::Or(left, right) => {
                let is_and = matches!(self, Self::And(..));
                let first = left
                    .evaluate_with(environment, evaluation)?
                    .is_truthy()
                    .ok_or_else(|| EvalError::Type("& and | combine conditions only".to_owned()))?;
                if first != is_and {
                    return Ok(Scalar::Bool(first));
                }
                right
                    .evaluate_with(environment, evaluation)?
                    .is_truthy()
                    .map(Scalar::Bool)
                    .ok_or_else(|| EvalError::Type("& and | combine conditions only".to_owned()))
            }
            Self::Compare(operation, left, right) => {
                let a = left.evaluate_with(environment, evaluation)?;
                let b = right.evaluate_with(environment, evaluation)?;
                compare(*operation, &a, &b).map(Scalar::Bool)
            }
            Self::Arithmetic(operation, left, right) => {
                let a = left.evaluate_with(environment, evaluation)?;
                let b = right.evaluate_with(environment, evaluation)?;
                arithmetic(*operation, &a, &b)
            }
            Self::Negate(inner) => match inner.evaluate_with(environment, evaluation)? {
                Scalar::Integer(integer) => Ok(Scalar::Integer(-integer)),
                Scalar::Float(float) => Ok(Scalar::Float(-float)),
                other => Err(EvalError::Type(format!(
                    "cannot negate a {}; only numbers can be negated",
                    other.type_name()
                ))),
            },
        }
    }
}
