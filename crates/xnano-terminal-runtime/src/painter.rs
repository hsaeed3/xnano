//! Retained painting: buffers whose cells are produced from live inputs.
//!
//! A [`Painter`] fills a buffer's grid from values that can change after construction or
//! follow expressions. [`refresh`] asks every painter in a tree for a fingerprint of its
//! inputs and repaints only the ones whose fingerprint changed, so an unchanged widget
//! costs one comparison per frame.

use std::ops::Deref;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex, MutexGuard};

use crate::buffer::{BufferCore, walk};
use crate::expression::{Environment, EvalError};
use crate::grid::Grid;

/// Produces the cells of a retained buffer.
pub trait Painter: Send + Sync {
    /// A value that changes whenever the painted output would change.
    ///
    /// Bound inputs are read here, so an unreadable binding is reported as an error.
    fn fingerprint(&self, environment: &dyn Environment) -> Result<u64, EvalError>;

    /// Paint the whole grid. The grid is cleared by the caller.
    fn paint(&self, grid: &mut Grid, environment: &dyn Environment) -> Result<(), EvalError>;
}

/// A widget's settings with a version that changes whenever they are edited.
pub struct Spec<T> {
    version: AtomicU64,
    data: Mutex<T>,
}

impl<T: std::fmt::Debug> std::fmt::Debug for Spec<T> {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "Spec(v{}, {:?})", self.version(), *self.read())
    }
}

/// An immutable view of a widget's settings while its lock is held.
pub struct SpecReadGuard<'a, T> {
    guard: MutexGuard<'a, T>,
}

impl<T> Deref for SpecReadGuard<'_, T> {
    type Target = T;

    fn deref(&self) -> &Self::Target {
        &self.guard
    }
}

impl<T: std::fmt::Debug> std::fmt::Debug for SpecReadGuard<'_, T> {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        std::fmt::Debug::fmt(&*self.guard, formatter)
    }
}

impl<T> Spec<T> {
    pub fn new(data: T) -> Arc<Self> {
        Arc::new(Self {
            version: AtomicU64::new(1),
            data: Mutex::new(data),
        })
    }

    pub fn version(&self) -> u64 {
        self.version.load(Ordering::SeqCst)
    }

    /// Read the settings without allowing changes that bypass the version counter.
    pub fn read(&self) -> SpecReadGuard<'_, T> {
        SpecReadGuard {
            guard: self
                .data
                .lock()
                .unwrap_or_else(std::sync::PoisonError::into_inner),
        }
    }

    /// Edit the settings and mark them changed.
    pub fn edit<R>(&self, change: impl FnOnce(&mut T) -> R) -> R {
        let mut settings = self
            .data
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let result = change(&mut settings);
        drop(settings);
        self.version.fetch_add(1, Ordering::SeqCst);
        result
    }
}

/// A retained buffer that could not be repainted, and why.
#[derive(Debug, Clone, PartialEq)]
pub struct PaintFailure {
    pub buffer_id: u64,
    pub error: EvalError,
}

/// Repaint every painter in the tree below `root` whose inputs changed.
///
/// Returns the buffers that failed. A failing buffer keeps its previous cells.
pub fn refresh(
    root: &Arc<BufferCore>,
    environment_for: &dyn Fn(&Arc<BufferCore>) -> Box<dyn Environment>,
) -> Vec<PaintFailure> {
    let mut cores = Vec::new();
    walk(root, &mut |core| cores.push(Arc::clone(core)));
    let mut failures = Vec::new();
    for core in cores {
        let (painter, painted) = {
            let state = core.lock();
            match &state.painter {
                Some(painter) => (Arc::clone(painter), state.painted),
                None => continue,
            }
        };
        let environment = environment_for(&core);
        let result = painter
            .fingerprint(environment.as_ref())
            .and_then(|content| {
                let (columns, rows, fill) = {
                    let state = core.lock();
                    (state.grid.width(), state.grid.height(), state.fill.clone())
                };
                // A resized widget has to repaint even when its settings did not change.
                let fingerprint = content
                    ^ (u64::from(columns) << 48)
                    ^ (u64::from(rows) << 32)
                    ^ 0x9e37_79b9_7f4a_7c15;
                if painted == Some(fingerprint) {
                    return Ok(());
                }
                let mut grid = Grid::filled(columns, rows, &fill);
                painter.paint(&mut grid, environment.as_ref())?;
                let mut state = core.lock();
                if state.grid.width() == columns && state.grid.height() == rows {
                    state.grid = grid;
                    state.painted = Some(fingerprint);
                    state.touch(None);
                }
                Ok(())
            });
        if let Err(error) = result {
            failures.push(PaintFailure {
                buffer_id: core.id,
                error,
            });
        }
    }
    failures
}
