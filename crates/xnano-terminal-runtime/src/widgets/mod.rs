//! Retained widgets: settings that stay editable, repainted when an input changes.
//!
//! Each widget has a *spec* (its settings, shared with the Python object that edits it), a
//! *resolved* form (every bound value read once) and a draw function. [`SpecPainter`]
//! connects them to the buffer tree through [`Painter`](crate::painter::Painter): the
//! fingerprint is the resolved form, so a widget repaints exactly when something it shows
//! changed.

pub mod bar_chart;
pub mod block;
pub mod calendar;
pub mod canvas;
pub mod chart;
pub mod clear;
pub mod custom;
pub mod gauge;
pub mod line_gauge;
pub mod list;
pub mod live;
pub mod paragraph;
pub mod scrollbar;
pub mod sparkline;
pub mod style;
pub mod table;
pub mod tabs;

use std::collections::hash_map::DefaultHasher;
use std::fmt::{self, Write as _};
use std::hash::{Hash, Hasher};
use std::sync::{Arc, Mutex};

use crate::dynamic::{Dynamic, FromScalar};
use crate::expression::{Environment, EvalError, Evaluation};
use crate::grid::Grid;
use crate::painter::{Painter, Spec};

/// A widget's settings, shared between the object that edits them and its painter.
pub type Shared<T> = Arc<Spec<T>>;

/// Reads bound values with one consistent view of state per paint.
pub struct Resolver<'a> {
    pub environment: &'a dyn Environment,
    evaluation: Evaluation,
    size: Option<(u16, u16)>,
}

impl<'a> Resolver<'a> {
    pub fn new(environment: &'a dyn Environment) -> Self {
        Self {
            environment,
            evaluation: Evaluation::default(),
            size: None,
        }
    }

    /// Tell the resolver how large the grid being painted is, so a widget holding far more
    /// items than fit can resolve only the ones it will show.
    #[must_use]
    pub fn with_size(mut self, width: u16, height: u16) -> Self {
        self.size = Some((width, height));
        self
    }

    /// The size of the grid being painted, when known.
    pub fn size(&self) -> Option<(u16, u16)> {
        self.size
    }

    /// Hash the current value of a setting if it is bound (a fixed one is covered by the
    /// settings version).
    pub fn hash_bound<T: FromScalar + Clone + fmt::Debug>(
        &mut self,
        value: &Dynamic<T>,
        hasher: &mut DefaultHasher,
    ) -> Result<(), EvalError> {
        if value.is_bound() {
            hash_debug(&self.get(value)?, hasher);
        }
        Ok(())
    }

    /// The current value of a fixed or bound setting.
    pub fn get<T: FromScalar + Clone>(&mut self, value: &Dynamic<T>) -> Result<T, EvalError> {
        value.resolve(self.environment, &mut self.evaluation)
    }

    /// The current value of an optional setting.
    pub fn get_optional<T: FromScalar + Clone>(
        &mut self,
        value: &Option<Dynamic<T>>,
    ) -> Result<Option<T>, EvalError> {
        value.as_ref().map(|inner| self.get(inner)).transpose()
    }
}

/// What a widget needs to describe itself as a retained, repaintable buffer.
pub trait WidgetSpec: Send + 'static {
    /// Every setting with its bound values read.
    type Resolved: std::fmt::Debug + Send;

    fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Self::Resolved, EvalError>;

    /// Hash the current value of every bound setting, and return `Some`, when the output
    /// depends on nothing else but the settings version.
    ///
    /// A widget that implements this has a cheap fingerprint however many items it holds:
    /// the items it shows are covered by the version, so only the few bound values are
    /// read. Returning `None` (the default) makes the fingerprint resolve and hash every
    /// setting each time it is asked for.
    fn hash_bindings(
        &self,
        _resolver: &mut Resolver<'_>,
        _hasher: &mut DefaultHasher,
    ) -> Option<Result<(), EvalError>> {
        None
    }

    /// Whether resolving reads the size of the grid being painted (see
    /// [`Resolver::size`]). Such a widget is resolved again when it is painted, because the
    /// fingerprint is made before the size is known.
    fn depends_on_size(&self) -> bool {
        false
    }

    /// Paint the resolved widget over the whole grid.
    fn draw(resolved: &Self::Resolved, grid: &mut Grid);
}

/// Paints a [`WidgetSpec`] into a buffer.
pub struct SpecPainter<S: WidgetSpec> {
    spec: Shared<S>,
    cache: Mutex<Option<(u64, S::Resolved)>>,
}

impl<S: WidgetSpec> SpecPainter<S> {
    pub fn new(spec: Shared<S>) -> Arc<Self> {
        Arc::new(Self {
            spec,
            cache: Mutex::new(None),
        })
    }
}

struct DebugHashWriter<'a>(&'a mut DefaultHasher);

impl fmt::Write for DebugHashWriter<'_> {
    fn write_str(&mut self, value: &str) -> fmt::Result {
        self.0.write(value.as_bytes());
        Ok(())
    }
}

/// Feed the debug text of `value` to `hasher`, without building the string.
pub fn hash_debug(value: &impl std::fmt::Debug, hasher: &mut DefaultHasher) {
    let mut writer = DebugHashWriter(hasher);
    let _ = write!(writer, "{value:?}");
    hasher.write_u8(0xff);
}

fn digest(resolved: &impl std::fmt::Debug, grid_size: (u16, u16)) -> u64 {
    let mut hasher = DefaultHasher::new();
    {
        let mut writer = DebugHashWriter(&mut hasher);
        let _ = write!(writer, "{resolved:?}");
    }
    hasher.write_u8(0xff);
    grid_size.hash(&mut hasher);
    hasher.finish()
}

impl<S: WidgetSpec> Painter for SpecPainter<S> {
    fn fingerprint(&self, environment: &dyn Environment) -> Result<u64, EvalError> {
        let mut resolver = Resolver::new(environment);
        {
            let mut hasher = DefaultHasher::new();
            hasher.write_u8(0xfe);
            hasher.write_u64(self.spec.version());
            if let Some(result) = self.spec.read().hash_bindings(&mut resolver, &mut hasher) {
                result?;
                *self
                    .cache
                    .lock()
                    .unwrap_or_else(std::sync::PoisonError::into_inner) = None;
                return Ok(hasher.finish());
            }
        }
        let resolved = self.spec.read().resolve(&mut resolver)?;
        let fingerprint = digest(&resolved, (0, 0));
        *self
            .cache
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner) = Some((fingerprint, resolved));
        Ok(fingerprint)
    }

    fn paint(&self, grid: &mut Grid, environment: &dyn Environment) -> Result<(), EvalError> {
        let cached = self
            .cache
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .take()
            .filter(|_| !self.spec.read().depends_on_size());
        let resolved = match cached {
            Some((_, resolved)) => resolved,
            None => self
                .spec
                .read()
                .resolve(&mut Resolver::new(environment).with_size(grid.width(), grid.height()))?,
        };
        S::draw(&resolved, grid);
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};

    use super::digest;

    #[test]
    fn digest_matches_hashing_the_resolved_debug_text() {
        let resolved = ("example", 12_u16);
        let grid_size = (12, 4);
        let mut expected = DefaultHasher::new();
        format!("{resolved:?}").hash(&mut expected);
        grid_size.hash(&mut expected);

        assert_eq!(digest(&resolved, grid_size), expected.finish());
    }
}
