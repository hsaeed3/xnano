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
    /// The key of the current key event, or `None` while the current event is not a key.
    KeyboardKey,
    /// `press`, `repeat` or `release`, or `None` while the current event is not a key.
    KeyboardKind,
    /// The current key event as a chord such as `ctrl+s`, or `None`.
    KeyboardChord,
    /// `left`, `right` or `middle` for the current button or motion report, or `None`.
    MouseButton,
    /// `press`, `release`, `drag` or `move` for the current button or motion report, or `None`.
    MouseKind,
    /// The cell of the current button or motion report, or `None`. A wheel report has none.
    MousePosition,
    /// Whether any mouse button is held.
    MouseIsDown,
    /// Signed horizontal wheel steps of the current step (right is positive).
    ScrollX,
    /// Signed vertical wheel steps of the current step (down is positive).
    ScrollY,
    /// The rectangle of the buffer on the screen, in screen cells.
    BufferRegion,
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
            Self::KeyboardKey => "KeyboardKey",
            Self::KeyboardKind => "KeyboardKind",
            Self::KeyboardChord => "KeyboardChord",
            Self::MouseButton => "MouseButtonValue",
            Self::MouseKind => "MouseKind",
            Self::MousePosition => "MousePosition",
            Self::MouseIsDown => "MouseIsDown",
            Self::ScrollX => "ScrollX",
            Self::ScrollY => "ScrollY",
            Self::BufferRegion => "BufferRegion",
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
                | Self::BufferRegion
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
    /// `Contains(rectangle, point)`: whether the rectangle holds the point. False when either
    /// side is `None`.
    Contains,
}

impl Function {
    /// How many arguments the function takes.
    pub fn arity(self) -> usize {
        match self {
            Self::Absolute | Self::Floor | Self::Ceiling | Self::Round => 1,
            Self::Minimum | Self::Maximum | Self::Contains => 2,
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
            Self::Contains => "contains",
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
        if matches!(value, Scalar::Null) {
            // A part of a value that was never seen is not seen either.
            return Ok(Scalar::Null);
        }
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

/// How tightly an expression binds when it is written as Python, from loosest to tightest.
///
/// Python puts comparisons below `|` and `&`, so a comparison inside a combined condition
/// is written in parentheses, as Python needs it to be.
mod binding {
    pub const COMPARISON: u8 = 4;
    pub const OR: u8 = 5;
    pub const AND: u8 = 7;
    pub const SUM: u8 = 9;
    pub const PRODUCT: u8 = 10;
    pub const UNARY: u8 = 11;
    pub const POWER: u8 = 12;
    pub const ATOM: u8 = 14;
}

impl PropertyId {
    /// The name the property has in Python, as `xnano_core` exports it.
    pub fn python_name(self) -> &'static str {
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
            Self::KeyboardKey => "KeyboardKey",
            Self::KeyboardKind => "KeyboardKind",
            Self::KeyboardChord => "KeyboardChord",
            Self::MouseButton => "MouseButtonValue",
            Self::MouseKind => "MouseKind",
            Self::MousePosition => "MousePosition",
            Self::MouseIsDown => "MouseIsDown",
            Self::ScrollX => "ScrollX",
            Self::ScrollY => "ScrollY",
            Self::BufferRegion => "BufferRegion",
        }
    }
}

impl fmt::Display for Scalar {
    /// The value as a Python literal.
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Null => formatter.write_str("None"),
            Self::Bool(true) => formatter.write_str("True"),
            Self::Bool(false) => formatter.write_str("False"),
            Self::Integer(value) => write!(formatter, "{value}"),
            Self::Float(value) if value.is_nan() => formatter.write_str("nan"),
            Self::Float(value) if value.is_infinite() => {
                formatter.write_str(if *value > 0.0 { "inf" } else { "-inf" })
            }
            Self::Float(value) => write!(formatter, "{value:?}"),
            Self::Text(text) => {
                write!(
                    formatter,
                    "'{}'",
                    text.replace('\\', "\\\\").replace('\'', "\\'")
                )
            }
            Self::Point(point) => write!(formatter, "Point({}, {})", point.x, point.y),
            Self::Size(size) => write!(formatter, "Size({}, {})", size.width, size.height),
            Self::Rectangle(rectangle) => write!(
                formatter,
                "Rectangle({}, {}, {}, {})",
                rectangle.x, rectangle.y, rectangle.width, rectangle.height
            ),
            Self::Json(value) => write!(formatter, "{value}"),
        }
    }
}

impl Expr {
    /// How tightly this expression binds when it is written as Python.
    fn binding(&self) -> u8 {
        match self {
            Self::Literal(Scalar::Integer(value)) if *value < 0 => binding::UNARY,
            Self::Literal(Scalar::Float(value)) if *value < 0.0 => binding::UNARY,
            Self::Literal(_)
            | Self::Property(_)
            | Self::State(..)
            | Self::External(_)
            | Self::Function(..)
            | Self::Select(..)
            | Self::Component(..) => binding::ATOM,
            Self::Not(_) | Self::Negate(_) => binding::UNARY,
            Self::Or(..) => binding::OR,
            Self::And(..) => binding::AND,
            Self::Compare(..) => binding::COMPARISON,
            Self::Arithmetic(operation, ..) => match operation {
                ArithmeticOp::Add | ArithmeticOp::Subtract => binding::SUM,
                ArithmeticOp::Power => binding::POWER,
                _ => binding::PRODUCT,
            },
        }
    }

    /// Write `expression`, in parentheses when it binds more loosely than `required`.
    fn write_operand(
        formatter: &mut fmt::Formatter<'_>,
        expression: &Expr,
        required: u8,
    ) -> fmt::Result {
        if expression.binding() < required {
            write!(formatter, "({expression})")
        } else {
            write!(formatter, "{expression}")
        }
    }

    /// Write `left symbol right`, where the right side binds tighter unless `is_right_first`.
    fn write_binary(
        formatter: &mut fmt::Formatter<'_>,
        level: u8,
        symbol: &str,
        left: &Expr,
        right: &Expr,
        is_right_first: bool,
    ) -> fmt::Result {
        let (left_required, right_required) = if is_right_first {
            (level + 1, level)
        } else {
            (level, level + 1)
        };
        Self::write_operand(formatter, left, left_required)?;
        write!(formatter, " {symbol} ")?;
        Self::write_operand(formatter, right, right_required)
    }
}

impl fmt::Display for Expr {
    /// The expression as the Python that builds it, such as `ParentHeight - 1`.
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Literal(value) => write!(formatter, "{value}"),
            Self::Property(property) => formatter.write_str(property.python_name()),
            Self::State(_, path) => write!(formatter, "state.{}", path.join(".")),
            Self::External(name) => formatter.write_str(name),
            Self::Not(inner) => {
                formatter.write_str("~")?;
                Self::write_operand(formatter, inner, binding::UNARY)
            }
            Self::Negate(inner) => {
                formatter.write_str("-")?;
                Self::write_operand(formatter, inner, binding::UNARY)
            }
            Self::And(left, right) => {
                Self::write_binary(formatter, binding::AND, "&", left, right, false)
            }
            Self::Or(left, right) => {
                Self::write_binary(formatter, binding::OR, "|", left, right, false)
            }
            Self::Compare(operation, left, right) => {
                let symbol = match operation {
                    CompareOp::Equal => "==",
                    CompareOp::NotEqual => "!=",
                    CompareOp::Less => "<",
                    CompareOp::LessEqual => "<=",
                    CompareOp::Greater => ">",
                    CompareOp::GreaterEqual => ">=",
                };
                Self::write_binary(formatter, binding::COMPARISON, symbol, left, right, false)
            }
            Self::Arithmetic(operation, left, right) => {
                let symbol = match operation {
                    ArithmeticOp::Add => "+",
                    ArithmeticOp::Subtract => "-",
                    ArithmeticOp::Multiply => "*",
                    ArithmeticOp::Divide => "/",
                    ArithmeticOp::Modulo => "%",
                    ArithmeticOp::FloorDivide => "//",
                    ArithmeticOp::Power => "**",
                };
                let is_right_first = *operation == ArithmeticOp::Power;
                Self::write_binary(
                    formatter,
                    self.binding(),
                    symbol,
                    left,
                    right,
                    is_right_first,
                )
            }
            Self::Function(function, arguments) => {
                let receiver = arguments.first();
                let rest = arguments.get(1..).unwrap_or_default();
                let call = |formatter: &mut fmt::Formatter<'_>, name: &str| -> fmt::Result {
                    write!(formatter, "{name}(")?;
                    for (index, argument) in arguments.iter().enumerate() {
                        if index > 0 {
                            formatter.write_str(", ")?;
                        }
                        write!(formatter, "{argument}")?;
                    }
                    formatter.write_str(")")
                };
                let method = |formatter: &mut fmt::Formatter<'_>, name: &str| -> fmt::Result {
                    if let Some(receiver) = receiver {
                        Self::write_operand(formatter, receiver, binding::ATOM)?;
                    }
                    write!(formatter, ".{name}(")?;
                    for (index, argument) in rest.iter().enumerate() {
                        if index > 0 {
                            formatter.write_str(", ")?;
                        }
                        write!(formatter, "{argument}")?;
                    }
                    formatter.write_str(")")
                };
                match function {
                    Function::Absolute => call(formatter, "abs"),
                    Function::Floor => call(formatter, "math.floor"),
                    Function::Ceiling => call(formatter, "math.ceil"),
                    Function::Round => call(formatter, "round"),
                    Function::Minimum => method(formatter, "minimum"),
                    Function::Maximum => method(formatter, "maximum"),
                    Function::Clamp => method(formatter, "clamp"),
                    Function::Contains => method(formatter, "contains"),
                }
            }
            Self::Select(condition, when_true, when_false) => {
                Self::write_operand(formatter, condition, binding::ATOM)?;
                write!(formatter, ".choose({when_true}, {when_false})")
            }
            Self::Component(component, inner) => {
                Self::write_operand(formatter, inner, binding::ATOM)?;
                let name = match component {
                    Component::X => "x",
                    Component::Y => "y",
                    Component::Width => "width",
                    Component::Height => "height",
                    Component::Right => "right",
                    Component::Bottom => "bottom",
                };
                write!(formatter, ".{name}")
            }
        }
    }
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
    // Something never seen (no key yet, no pointer yet) is neither equal to, different from,
    // nor ordered against anything, so a condition on it is false rather than an error.
    if matches!(left, Scalar::Null) || matches!(right, Scalar::Null) {
        return Ok(false);
    }
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
    if matches!(left, Scalar::Null) || matches!(right, Scalar::Null) {
        return Ok(Scalar::Null);
    }
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

/// A type name with the article that reads right before it ("an int", "a Point").
fn with_article(name: &str) -> String {
    let starts_with_vowel = name.starts_with(['a', 'e', 'i', 'o', 'u']);
    format!("{} {name}", if starts_with_vowel { "an" } else { "a" })
}

fn contains(container: &Scalar, point: &Scalar) -> Result<Scalar, EvalError> {
    match (container, point) {
        (Scalar::Null, _) | (_, Scalar::Null) => Ok(Scalar::Bool(false)),
        (Scalar::Rectangle(rectangle), Scalar::Point(point)) => {
            Ok(Scalar::Bool(rectangle.contains(*point)))
        }
        (container, point) => Err(EvalError::Type(format!(
            "cannot ask whether {} contains {}; ask a Rectangle whether it contains a Point",
            with_article(container.type_name()),
            with_article(point.type_name())
        ))),
    }
}

fn apply_function(function: Function, values: &[Scalar]) -> Result<Scalar, EvalError> {
    debug_assert_eq!(values.len(), function.arity());
    if function == Function::Contains {
        return contains(&values[0], &values[1]);
    }
    if values.iter().any(|value| matches!(value, Scalar::Null)) {
        return Ok(Scalar::Null);
    }
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
        Function::Contains => {
            unreachable!("contains returns before the numeric arguments are read")
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
                Scalar::Null => Ok(Scalar::Null),
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

    fn property(property: PropertyId) -> Arc<Expr> {
        Arc::new(Expr::Property(property))
    }

    fn number(value: i64) -> Arc<Expr> {
        Arc::new(Expr::Literal(Scalar::Integer(value)))
    }

    fn arithmetic(operation: ArithmeticOp, left: Arc<Expr>, right: Arc<Expr>) -> Arc<Expr> {
        Arc::new(Expr::Arithmetic(operation, left, right))
    }

    #[test]
    fn expressions_print_as_the_python_that_builds_them() {
        let height = arithmetic(
            ArithmeticOp::Subtract,
            property(PropertyId::ParentHeight),
            number(1),
        );
        assert_eq!(height.to_string(), "ParentHeight - 1");
        let region = Expr::Component(Component::Height, property(PropertyId::BufferRegion));
        assert_eq!(region.to_string(), "BufferRegion.height");
        let centered = arithmetic(
            ArithmeticOp::FloorDivide,
            arithmetic(
                ArithmeticOp::Subtract,
                property(PropertyId::ParentWidth),
                property(PropertyId::Width),
            ),
            number(2),
        );
        assert_eq!(centered.to_string(), "(ParentWidth - Width) // 2");
        let grouped = arithmetic(
            ArithmeticOp::Subtract,
            number(10),
            arithmetic(ArithmeticOp::Subtract, number(4), number(1)),
        );
        assert_eq!(grouped.to_string(), "10 - (4 - 1)");
    }

    #[test]
    fn conditions_keep_the_parentheses_python_needs() {
        let wide = Arc::new(Expr::Compare(
            CompareOp::Greater,
            property(PropertyId::Width),
            number(4),
        ));
        let short = Arc::new(Expr::Compare(
            CompareOp::Less,
            property(PropertyId::Height),
            number(2),
        ));
        let both = Expr::And(wide.clone(), short);
        assert_eq!(both.to_string(), "(Width > 4) & (Height < 2)");
        assert_eq!(Expr::Not(wide).to_string(), "~(Width > 4)");
        let chosen = Expr::Select(
            property(PropertyId::MouseIsDown),
            Arc::new(Expr::Literal(Scalar::Text("down".into()))),
            Arc::new(Expr::Literal(Scalar::Float(0.5))),
        );
        assert_eq!(chosen.to_string(), "MouseIsDown.choose('down', 0.5)");
        let limited = Expr::Function(
            Function::Clamp,
            vec![property(PropertyId::FramesPerSecond), number(1), number(60)],
        );
        assert_eq!(limited.to_string(), "FPS.clamp(1, 60)");
        let negative = arithmetic(ArithmeticOp::Power, number(-2), number(2));
        assert_eq!(negative.to_string(), "(-2) ** 2");
    }
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

    fn null() -> Arc<Expr> {
        Expr::literal(Scalar::Null)
    }

    #[test]
    fn nothing_seen_is_neither_equal_different_nor_ordered() {
        for operation in [
            CompareOp::Equal,
            CompareOp::NotEqual,
            CompareOp::Less,
            CompareOp::LessEqual,
            CompareOp::Greater,
            CompareOp::GreaterEqual,
        ] {
            for (left, right) in [
                (null(), integer(1)),
                (integer(1), null()),
                (null(), null()),
                (null(), Expr::literal(Scalar::Text("q".to_owned()))),
            ] {
                let expression = Expr::Compare(operation, left, right);
                assert_eq!(
                    evaluate(expression),
                    Ok(Scalar::Bool(false)),
                    "{operation:?}"
                );
            }
        }
    }

    #[test]
    fn parts_and_arithmetic_of_nothing_are_nothing() {
        let part = Expr::Component(Component::X, null());
        assert_eq!(evaluate(part), Ok(Scalar::Null));
        let sum = Expr::Arithmetic(ArithmeticOp::Add, null(), integer(1));
        assert_eq!(evaluate(sum), Ok(Scalar::Null));
        let negated = Expr::Negate(null());
        assert_eq!(evaluate(negated), Ok(Scalar::Null));
        let absolute = Expr::Function(Function::Absolute, vec![null()]);
        assert_eq!(evaluate(absolute), Ok(Scalar::Null));
        let seen_part_compares = Expr::Compare(
            CompareOp::Greater,
            Arc::new(Expr::Component(Component::X, null())),
            integer(0),
        );
        assert_eq!(evaluate(seen_part_compares), Ok(Scalar::Bool(false)));
    }

    #[test]
    fn contains_asks_a_rectangle_about_a_point() {
        let rectangle = Expr::literal(Scalar::Rectangle(Rectangle::new(2, 1, 4, 3)));
        let at = |x: i32, y: i32| Expr::literal(Scalar::Point(Point::new(x, y)));
        let contains = |point: Arc<Expr>| {
            evaluate(Expr::Function(
                Function::Contains,
                vec![rectangle.clone(), point],
            ))
        };
        assert_eq!(contains(at(2, 1)), Ok(Scalar::Bool(true)));
        assert_eq!(contains(at(5, 3)), Ok(Scalar::Bool(true)));
        assert_eq!(contains(at(6, 3)), Ok(Scalar::Bool(false)));
        assert_eq!(contains(at(2, 4)), Ok(Scalar::Bool(false)));
        assert_eq!(contains(null()), Ok(Scalar::Bool(false)));
        let no_rectangle = Expr::Function(Function::Contains, vec![null(), at(2, 1)]);
        assert_eq!(evaluate(no_rectangle), Ok(Scalar::Bool(false)));
        assert!(matches!(contains(integer(1)), Err(EvalError::Type(_))));
    }
}
