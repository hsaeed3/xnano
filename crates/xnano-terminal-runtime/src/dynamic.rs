//! Values that are either fixed or follow an expression.
//!
//! Every user-facing parameter of a widget, effect or operation is a [`Dynamic`]. A fixed
//! value never changes; a bound value is an [`Expr`] (a state branch, a runtime property or
//! arithmetic on them) that is read again each time the owner paints or advances.

use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::sync::Arc;

use crate::expression::{Environment, EvalError, Evaluation, Expr, Scalar};
use crate::geometry::{Point, Rectangle, Size};
use crate::style::{Color, parse_color};

/// A type an expression result can be converted to.
pub trait FromScalar: Sized {
    /// Convert, or explain what was expected.
    fn from_scalar(scalar: &Scalar) -> Result<Self, EvalError>;
}

fn mismatch(expected: &str, scalar: &Scalar) -> EvalError {
    EvalError::Type(format!(
        "expected {expected} but the expression produced a {}; bind a value of the right type",
        scalar.type_name()
    ))
}

impl FromScalar for Scalar {
    fn from_scalar(scalar: &Scalar) -> Result<Self, EvalError> {
        Ok(scalar.clone())
    }
}

impl FromScalar for bool {
    fn from_scalar(scalar: &Scalar) -> Result<Self, EvalError> {
        match scalar {
            Scalar::Bool(flag) => Ok(*flag),
            other => Err(mismatch("a bool", other)),
        }
    }
}

macro_rules! integer_from_scalar {
    ($($type:ty),*) => {$(
        #[allow(clippy::cast_lossless)]
        impl FromScalar for $type {
            fn from_scalar(scalar: &Scalar) -> Result<Self, EvalError> {
                let number = match scalar {
                    Scalar::Integer(integer) => *integer as f64,
                    Scalar::Float(float) => float.round(),
                    other => return Err(mismatch("a number", other)),
                };
                if number.is_nan() || number < <$type>::MIN as f64 || number > <$type>::MAX as f64 {
                    return Err(EvalError::Type(format!(
                        "the value {number} is outside the range {} to {} this setting accepts",
                        <$type>::MIN,
                        <$type>::MAX
                    )));
                }
                Ok(number as $type)
            }
        }
    )*};
}
integer_from_scalar!(i32, i64, u8, u16, u32, u64, usize);

impl FromScalar for f64 {
    fn from_scalar(scalar: &Scalar) -> Result<Self, EvalError> {
        scalar
            .as_number()
            .ok_or_else(|| mismatch("a number", scalar))
    }
}

impl FromScalar for f32 {
    fn from_scalar(scalar: &Scalar) -> Result<Self, EvalError> {
        f64::from_scalar(scalar).map(|number| number as f32)
    }
}

impl FromScalar for String {
    fn from_scalar(scalar: &Scalar) -> Result<Self, EvalError> {
        match scalar {
            Scalar::Text(text) => Ok(text.clone()),
            Scalar::Integer(integer) => Ok(integer.to_string()),
            Scalar::Float(float) => Ok(float.to_string()),
            Scalar::Bool(flag) => Ok(flag.to_string()),
            other => Err(mismatch("text", other)),
        }
    }
}

impl FromScalar for Color {
    fn from_scalar(scalar: &Scalar) -> Result<Self, EvalError> {
        match scalar {
            Scalar::Text(text) => parse_color(text).map_err(EvalError::Type),
            Scalar::Integer(index) => u8::try_from(*index).map(Color::Indexed).map_err(|_| {
                EvalError::Type(format!(
                    "the palette index {index} is out of range; use 0 to 255"
                ))
            }),
            other => Err(mismatch("a color name, hex value or palette index", other)),
        }
    }
}

impl FromScalar for Point {
    fn from_scalar(scalar: &Scalar) -> Result<Self, EvalError> {
        match scalar {
            Scalar::Point(point) => Ok(*point),
            other => Err(mismatch("a Point", other)),
        }
    }
}

impl FromScalar for Size {
    fn from_scalar(scalar: &Scalar) -> Result<Self, EvalError> {
        match scalar {
            Scalar::Size(size) => Ok(*size),
            other => Err(mismatch("a Size", other)),
        }
    }
}

impl FromScalar for Rectangle {
    fn from_scalar(scalar: &Scalar) -> Result<Self, EvalError> {
        match scalar {
            Scalar::Rectangle(rectangle) => Ok(*rectangle),
            other => Err(mismatch("a Rectangle", other)),
        }
    }
}

/// A value that is fixed or follows an expression.
#[derive(Debug, Clone)]
pub enum Dynamic<T> {
    Fixed(T),
    Bound(Arc<Expr>),
}

impl<T> From<T> for Dynamic<T> {
    fn from(value: T) -> Self {
        Self::Fixed(value)
    }
}

impl<T: FromScalar + Clone> Dynamic<T> {
    /// The current value.
    pub fn resolve(
        &self,
        environment: &dyn Environment,
        evaluation: &mut Evaluation,
    ) -> Result<T, EvalError> {
        match self {
            Self::Fixed(value) => Ok(value.clone()),
            Self::Bound(expression) => {
                T::from_scalar(&expression.evaluate_with(environment, evaluation)?)
            }
        }
    }

    /// The fixed value, or `None` when the value follows an expression.
    pub fn fixed(&self) -> Option<&T> {
        match self {
            Self::Fixed(value) => Some(value),
            Self::Bound(_) => None,
        }
    }
}

impl<T> Dynamic<T> {
    pub fn is_bound(&self) -> bool {
        matches!(self, Self::Bound(_))
    }
}

/// Builds the fingerprint of a painted output from its inputs.
///
/// Two equal fingerprints mean the output would be identical, so painting can be skipped.
#[derive(Default)]
pub struct Fingerprint(DefaultHasher);

impl Fingerprint {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add(&mut self, value: &impl Hash) -> &mut Self {
        value.hash(&mut self.0);
        self
    }

    /// Add the debug form of a value, for types that do not implement `Hash`.
    pub fn add_debug(&mut self, value: &impl std::fmt::Debug) -> &mut Self {
        format!("{value:?}").hash(&mut self.0);
        self
    }

    pub fn finish(&self) -> u64 {
        self.0.finish()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct Offline;
    impl Environment for Offline {
        fn property(&self, id: crate::expression::PropertyId) -> Result<Scalar, EvalError> {
            Err(EvalError::RuntimeRequired(id.name().to_owned()))
        }
    }

    #[test]
    fn fixed_and_bound_values_resolve() {
        let mut evaluation = Evaluation::default();
        let fixed: Dynamic<u16> = Dynamic::Fixed(4);
        assert_eq!(fixed.resolve(&Offline, &mut evaluation), Ok(4));
        let bound: Dynamic<u16> = Dynamic::Bound(Expr::literal(Scalar::Float(2.6)));
        assert_eq!(bound.resolve(&Offline, &mut evaluation), Ok(3));
        let wrong: Dynamic<bool> = Dynamic::Bound(Expr::literal(Scalar::Integer(1)));
        assert!(wrong.resolve(&Offline, &mut evaluation).is_err());
        let range: Dynamic<u8> = Dynamic::Bound(Expr::literal(Scalar::Integer(300)));
        assert!(range.resolve(&Offline, &mut evaluation).is_err());
    }

    #[test]
    fn colors_resolve_from_names_and_indexes() {
        let mut evaluation = Evaluation::default();
        let named: Dynamic<Color> =
            Dynamic::Bound(Expr::literal(Scalar::Text("light_blue".into())));
        assert_eq!(
            named.resolve(&Offline, &mut evaluation),
            Ok(Color::LightBlue)
        );
    }
}
