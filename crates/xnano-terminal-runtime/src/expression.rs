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
    TimeElapsed,
    TimeDelta,
    TimeElapsedMilliseconds,
    TimeDeltaMilliseconds,
    Frame,
    FramesPerSecond,
    Focused,
    Running,
    DeviceWidth,
    DeviceHeight,
    /// The size of the parent buffer, or of the buffer a region belongs to.
    ParentSize,
    ParentWidth,
    ParentHeight,
    /// The top-left cell of the target on the screen.
    ScreenPosition,
    /// The target's rectangle on the screen.
    ScreenBounds,
    /// The cell under the pointer, or `None` until the pointer has been seen.
    PointerPosition,
    Layer,
    IsVisible,
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
            Self::TimeElapsed => "TimeElapsed",
            Self::TimeDelta => "TimeDelta",
            Self::TimeElapsedMilliseconds => "TimeElapsedMilliseconds",
            Self::TimeDeltaMilliseconds => "TimeDeltaMilliseconds",
            Self::Frame => "Frame",
            Self::FramesPerSecond => "FPS",
            Self::Focused => "Focused",
            Self::Running => "Running",
            Self::DeviceWidth => "DeviceWidth",
            Self::DeviceHeight => "DeviceHeight",
            Self::ParentSize => "ParentSize",
            Self::ParentWidth => "ParentWidth",
            Self::ParentHeight => "ParentHeight",
            Self::ScreenPosition => "ScreenPosition",
            Self::ScreenBounds => "ScreenBounds",
            Self::PointerPosition => "PointerPosition",
            Self::Layer => "Layer",
            Self::IsVisible => "IsVisible",
        }
    }

    /// Whether an assignment such as `Width(40)` is meaningful.
    pub fn is_settable(self) -> bool {
        matches!(
            self,
            Self::X
                | Self::Y
                | Self::Width
                | Self::Height
                | Self::Position
                | Self::Size
                | Self::Layer
                | Self::IsVisible
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
                | Self::ParentSize
                | Self::ParentWidth
                | Self::ParentHeight
                | Self::ScreenPosition
                | Self::ScreenBounds
                | Self::Layer
                | Self::IsVisible
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
    /// Division rounded toward negative infinity, like Python's `//`.
    FloorDivide,
    Power,
}

/// A function of one to three numbers.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Function {
    Absolute,
    Floor,
    Ceiling,
    Round,
    Minimum,
    Maximum,
    /// `Clamp(value, lowest, highest)`.
    Clamp,
}

impl Function {
    /// How many arguments the function takes.
    pub fn arity(self) -> usize {
        match self {
            Self::Absolute | Self::Floor | Self::Ceiling | Self::Round => 1,
            Self::Minimum | Self::Maximum => 2,
            Self::Clamp => 3,
        }
    }

    pub fn name(self) -> &'static str {
        match self {
            Self::Absolute => "absolute value",
            Self::Floor => "floor",
            Self::Ceiling => "ceiling",
            Self::Round => "round",
            Self::Minimum => "minimum",
            Self::Maximum => "maximum",
            Self::Clamp => "clamp",
        }
    }
}

/// A part of a point, size or rectangle.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Component {
    X,
    Y,
    Width,
    Height,
    Right,
    Bottom,
}

impl Component {
    pub fn name(self) -> &'static str {
        match self {
            Self::X => "x",
            Self::Y => "y",
            Self::Width => "width",
            Self::Height => "height",
            Self::Right => "right",
            Self::Bottom => "bottom",
        }
    }

    fn of(self, value: &Scalar) -> Result<Scalar, EvalError> {
        let part = match (value, self) {
            (Scalar::Point(point), Self::X) => point.x,
            (Scalar::Point(point), Self::Y) => point.y,
            (Scalar::Size(size), Self::Width) => size.width,
            (Scalar::Size(size), Self::Height) => size.height,
            (Scalar::Rectangle(rectangle), Self::X) => rectangle.x,
            (Scalar::Rectangle(rectangle), Self::Y) => rectangle.y,
            (Scalar::Rectangle(rectangle), Self::Width) => rectangle.width,
            (Scalar::Rectangle(rectangle), Self::Height) => rectangle.height,
            (Scalar::Rectangle(rectangle), Self::Right) => rectangle.right(),
            (Scalar::Rectangle(rectangle), Self::Bottom) => rectangle.bottom(),
            (other, component) => {
                return Err(EvalError::Type(format!(
                    "a {} has no {}; read x and y from a Point, width and height from a Size, \
                     and x, y, width, height, right and bottom from a Rectangle",
                    other.type_name(),
                    component.name()
                )));
            }
        };
        Ok(Scalar::Integer(i64::from(part)))
    }
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
    Function(Function, Vec<Arc<Expr>>),
    /// The first value when the condition holds, the second otherwise.
    Select(Arc<Expr>, Arc<Expr>, Arc<Expr>),
    Component(Component, Arc<Expr>),
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
            ArithmeticOp::FloorDivide => {
                if *b == 0 {
                    return Err(EvalError::DivisionByZero);
                }
                let quotient = a.checked_div(*b);
                quotient.map(|quotient| {
                    if a % b != 0 && ((*a < 0) != (*b < 0)) {
                        quotient - 1
                    } else {
                        quotient
                    }
                })
            }
            ArithmeticOp::Power => u32::try_from(*b)
                .ok()
                .and_then(|exponent| a.checked_pow(exponent)),
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
        ArithmeticOp::FloorDivide => {
            if b == 0.0 {
                return Err(EvalError::DivisionByZero);
            }
            (a / b).floor()
        }
        ArithmeticOp::Power => a.powf(b),
    }))
}

/// Round half away from zero, like most people expect and unlike Python's `round`.
fn rounded(value: f64) -> f64 {
    value.round()
}

fn apply_function(function: Function, values: &[Scalar]) -> Result<Scalar, EvalError> {
    debug_assert_eq!(values.len(), function.arity());
    let mut numbers = Vec::with_capacity(values.len());
    for value in values {
        numbers.push(value.as_number().ok_or_else(|| {
            EvalError::Type(format!(
                "cannot take the {} of a {}; the arguments must be numbers",
                function.name(),
                value.type_name()
            ))
        })?);
    }
    let all_integers = values
        .iter()
        .all(|value| matches!(value, Scalar::Integer(_)));
    let number = |value: f64| {
        if all_integers {
            Scalar::Integer(value as i64)
        } else {
            Scalar::Float(value)
        }
    };
    Ok(match function {
        Function::Absolute => number(numbers[0].abs()),
        // Rounding functions always give whole numbers, as integers.
        Function::Floor => Scalar::Integer(numbers[0].floor() as i64),
        Function::Ceiling => Scalar::Integer(numbers[0].ceil() as i64),
        Function::Round => Scalar::Integer(rounded(numbers[0]) as i64),
        Function::Minimum => number(numbers[0].min(numbers[1])),
        Function::Maximum => number(numbers[0].max(numbers[1])),
        Function::Clamp => {
            if numbers[1] > numbers[2] {
                return Err(EvalError::Type(format!(
                    "cannot clamp between {} and {}; the lowest value must not exceed the highest",
                    numbers[1], numbers[2]
                )));
            }
            number(numbers[0].clamp(numbers[1], numbers[2]))
        }
    })
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
            Self::Function(function, arguments) => {
                let mut values = Vec::with_capacity(arguments.len());
                for argument in arguments {
                    values.push(argument.evaluate_with(environment, evaluation)?);
                }
                apply_function(*function, &values)
            }
            Self::Select(condition, when_true, when_false) => {
                let chosen = condition
                    .evaluate_with(environment, evaluation)?
                    .is_truthy()
                    .ok_or_else(|| {
                        EvalError::Type(
                            "choose() needs a condition; build one with a comparison such as \
                             Width > 10"
                                .to_owned(),
                        )
                    })?;
                if chosen { when_true } else { when_false }.evaluate_with(environment, evaluation)
            }
            Self::Component(component, inner) => {
                component.of(&inner.evaluate_with(environment, evaluation)?)
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

#[cfg(test)]
mod tests {
    use super::*;

    struct Offline;

    impl Environment for Offline {
        fn property(&self, id: PropertyId) -> Result<Scalar, EvalError> {
            Err(EvalError::RuntimeRequired(id.name().to_owned()))
        }
    }

    fn integer(value: i64) -> Arc<Expr> {
        Expr::literal(Scalar::Integer(value))
    }

    fn float(value: f64) -> Arc<Expr> {
        Expr::literal(Scalar::Float(value))
    }

    fn evaluate(expression: Expr) -> Result<Scalar, EvalError> {
        expression.evaluate(&Offline)
    }

    #[test]
    fn floor_division_rounds_toward_negative_infinity() {
        for (numerator, divisor) in [(7_i64, 2_i64), (-7, 2), (7, -2), (-7, -2), (0, 3)] {
            let expression = Expr::Arithmetic(
                ArithmeticOp::FloorDivide,
                integer(numerator),
                integer(divisor),
            );
            assert_eq!(
                evaluate(expression),
                Ok(Scalar::Integer(
                    numerator.div_euclid(divisor)
                        - i64::from(divisor < 0 && numerator.rem_euclid(divisor) != 0)
                )),
                "{numerator} // {divisor}"
            );
        }
        let by_zero = Expr::Arithmetic(ArithmeticOp::FloorDivide, integer(1), integer(0));
        assert_eq!(evaluate(by_zero), Err(EvalError::DivisionByZero));
        let floats = Expr::Arithmetic(ArithmeticOp::FloorDivide, float(7.0), float(2.0));
        assert_eq!(evaluate(floats), Ok(Scalar::Float(3.0)));
    }

    #[test]
    fn power_keeps_integers_when_it_can() {
        let square = Expr::Arithmetic(ArithmeticOp::Power, integer(7), integer(2));
        assert_eq!(evaluate(square), Ok(Scalar::Integer(49)));
        let inverse = Expr::Arithmetic(ArithmeticOp::Power, integer(2), integer(-1));
        assert_eq!(evaluate(inverse), Ok(Scalar::Float(0.5)));
        let overflow = Expr::Arithmetic(ArithmeticOp::Power, integer(10), integer(40));
        assert!(matches!(evaluate(overflow), Ok(Scalar::Float(_))));
    }

    #[test]
    fn functions_keep_integers_and_check_their_arguments() {
        let clamp = |value: i64, low: i64, high: i64| {
            evaluate(Expr::Function(
                Function::Clamp,
                vec![integer(value), integer(low), integer(high)],
            ))
        };
        assert_eq!(clamp(50, 0, 10), Ok(Scalar::Integer(10)));
        assert_eq!(clamp(-5, 0, 10), Ok(Scalar::Integer(0)));
        assert!(clamp(5, 10, 0).is_err());
        let rounded = Expr::Function(Function::Round, vec![float(2.5)]);
        assert_eq!(evaluate(rounded), Ok(Scalar::Integer(3)));
        let text = Expr::Function(
            Function::Absolute,
            vec![Expr::literal(Scalar::Text("x".to_owned()))],
        );
        assert!(matches!(evaluate(text), Err(EvalError::Type(_))));
    }

    #[test]
    fn select_and_components() {
        let choice = Expr::Select(Expr::literal(Scalar::Bool(false)), integer(1), integer(2));
        assert_eq!(evaluate(choice), Ok(Scalar::Integer(2)));
        let not_a_condition = Expr::Select(integer(1), integer(1), integer(2));
        assert!(matches!(evaluate(not_a_condition), Err(EvalError::Type(_))));
        let rectangle = Expr::literal(Scalar::Rectangle(Rectangle::new(2, 1, 7, 3)));
        let right = Expr::Component(Component::Right, rectangle.clone());
        assert_eq!(evaluate(right), Ok(Scalar::Integer(9)));
        let wrong = Expr::Component(
            Component::Right,
            Expr::literal(Scalar::Point(Point::new(1, 2))),
        );
        assert!(matches!(evaluate(wrong), Err(EvalError::Type(_))));
    }
}
