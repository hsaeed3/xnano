//! Retained widgets: buffers whose cells come from settings that stay editable.
//!
//! A widget is a [`Buffer`](crate::surface::PyBuffer) subclass, so it has geometry, can be
//! attached to a parent, laid out, focused and hooked like any buffer. Its settings are
//! properties; each one accepts either a plain value or an expression, and the widget
//! repaints when anything it shows changes.

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

use std::any::Any;
use std::sync::Arc;

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use xnano_terminal_runtime::buffer::{BufferCore, check_size};
use xnano_terminal_runtime::dynamic::{Dynamic, FromScalar};
use xnano_terminal_runtime::expression::Expr;
use xnano_terminal_runtime::grid::{Grid, blank_cell};
use xnano_terminal_runtime::painter::{Painter, refresh};
use xnano_terminal_runtime::widgets::{Shared, SpecPainter, WidgetSpec};

use crate::errors::{RenderError, eval_error};
use crate::expressions::{ExpressionKind, PyExpression, PyValue};
use crate::surface::{BufferExt, PyBuffer, PySurface, SurfaceEnv, ext_of, nudge};

/// The base class of every retained widget.
#[pyclass(name = "Widget", module = "xnano._xnano_core", extends = PyBuffer, subclass)]
pub struct PyWidget;

/// Where a widget sits and how big it is when it is created.
#[derive(Debug, Clone, Copy)]
pub struct Frame {
    pub width: Option<i32>,
    pub height: Option<i32>,
    pub x: i32,
    pub y: i32,
}

/// Build the Python object parts of a widget whose cells come from `spec`.
pub fn widget_initializer<S: WidgetSpec>(
    spec: Shared<S>,
    frame: Frame,
    default_size: (i32, i32),
) -> PyResult<PyClassInitializer<PyWidget>> {
    widget_initializer_with(
        |_| SpecPainter::new(spec) as Arc<dyn Painter>,
        frame,
        default_size,
    )
}

/// Build the Python object parts of a widget painted by a custom [`Painter`].
///
/// `make_painter` receives the widget's buffer, so a painter can find its runtime later.
pub fn widget_initializer_with(
    make_painter: impl FnOnce(&Arc<BufferCore>) -> Arc<dyn Painter>,
    frame: Frame,
    default_size: (i32, i32),
) -> PyResult<PyClassInitializer<PyWidget>> {
    let (columns, rows) = check_size(
        frame.width.unwrap_or(default_size.0),
        frame.height.unwrap_or(default_size.1),
    )
    .map_err(PyValueError::new_err)?;
    let fill = blank_cell();
    let core = BufferCore::new(Grid::filled(columns, rows, &fill), frame.x, frame.y, fill);
    let ext = Arc::new(BufferExt::default());
    {
        let painter = make_painter(&core);
        let mut state = core.lock();
        state.extension = Some(Arc::clone(&ext) as Arc<dyn Any + Send + Sync>);
        state.painter = Some(painter);
    }
    repaint(&core);
    Ok(PyClassInitializer::from(PySurface {
        core,
        ext,
        region: None,
    })
    .add_subclass(PyBuffer)
    .add_subclass(PyWidget))
}

static PAINT_ERRORS: std::sync::Mutex<Vec<(u64, PyErr)>> = std::sync::Mutex::new(Vec::new());

/// Remember the Python exception a painter hit, so the render error can chain it.
pub fn stash_paint_error(buffer_id: u64, error: PyErr) {
    let mut errors = PAINT_ERRORS
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner);
    errors.retain(|(id, _)| *id != buffer_id);
    errors.push((buffer_id, error));
}

fn take_paint_error(buffer_id: u64) -> Option<PyErr> {
    let mut errors = PAINT_ERRORS
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner);
    let position = errors.iter().position(|(id, _)| *id == buffer_id)?;
    Some(errors.remove(position).1)
}

/// The runtime link of the nearest ancestor (or the buffer itself) that has one.
pub fn shared_in_tree(core: &Arc<BufferCore>) -> Option<Arc<crate::shared::RuntimeShared>> {
    let mut current = Some(Arc::clone(core));
    while let Some(node) = current {
        if let Some(shared) = ext_of(&node).and_then(|ext| ext.shared()) {
            return Some(shared);
        }
        current = node.parent();
    }
    None
}

/// The expression environment of one buffer in a tree.
pub fn environment_of(
    core: &Arc<BufferCore>,
) -> Box<dyn xnano_terminal_runtime::expression::Environment> {
    Box::new(SurfaceEnv {
        core: Arc::clone(core),
        region: None,
        shared: shared_in_tree(core),
    })
}

/// Repaint the widgets at and below `root` whose inputs changed.
///
/// Returns the first failure, if any; a failing widget keeps its previous cells.
pub fn refresh_tree(root: &Arc<BufferCore>) -> PyResult<()> {
    let failures = refresh(root, &|core| environment_of(core));
    match failures.into_iter().next() {
        Some(failure) => {
            if let Some(cause) = take_paint_error(failure.buffer_id) {
                return Err(Python::attach(|py| {
                    let error = RenderError::new_err(format!(
                        "a widget could not be painted because its callback raised {}: {}. \
                         Fix the callback or give the widget values it can draw.",
                        cause
                            .get_type(py)
                            .name()
                            .map_or_else(|_| "an exception".to_owned(), |name| name.to_string()),
                        cause.value(py)
                    ));
                    error.set_cause(py, Some(cause));
                    error
                }));
            }
            Err(match &failure.error {
                xnano_terminal_runtime::expression::EvalError::RuntimeRequired(_) => {
                    eval_error(&failure.error)
                }
                other => RenderError::new_err(format!(
                    "a widget could not be painted: {other}. Check the values bound to its settings."
                )),
            })
        }
        None => Ok(()),
    }
}

/// Repaint after a setting changed: immediately for readers, and on the next frame for a runtime.
pub fn repaint(core: &Arc<BufferCore>) {
    let _ = refresh_tree(core);
    nudge(core);
}

/// A setting given as a plain value or as an expression.
pub fn dynamic_arg<T: FromScalar + Clone>(
    value: &Bound<'_, PyAny>,
    fixed: impl Fn(&Bound<'_, PyAny>) -> PyResult<T>,
) -> PyResult<Dynamic<T>> {
    if let Ok(expression) = value.extract::<PyRef<'_, PyExpression>>() {
        return match &expression.kind {
            ExpressionKind::Value(expr) => Ok(Dynamic::Bound(Arc::clone(expr))),
            _ => Err(PyTypeError::new_err(
                "an operation cannot be used as a setting; bind a value or condition instead",
            )),
        };
    }
    fixed(value).map(Dynamic::Fixed)
}

pub fn dynamic_f64(value: &Bound<'_, PyAny>) -> PyResult<Dynamic<f64>> {
    dynamic_arg(value, |value| value.extract())
}

pub fn dynamic_bool(value: &Bound<'_, PyAny>) -> PyResult<Dynamic<bool>> {
    dynamic_arg(value, |value| value.extract())
}

pub fn dynamic_u16(value: &Bound<'_, PyAny>) -> PyResult<Dynamic<u16>> {
    dynamic_arg(value, |value| value.extract())
}

pub fn dynamic_string(value: &Bound<'_, PyAny>) -> PyResult<Dynamic<String>> {
    dynamic_arg(value, |value| value.extract())
}

pub fn dynamic_color(
    value: &Bound<'_, PyAny>,
) -> PyResult<Dynamic<xnano_terminal_runtime::style::Color>> {
    dynamic_arg(value, crate::style::color_arg)
}

/// A setting as a Python object: the plain value, or the expression it follows.
pub fn dynamic_to_py<'py, T: Clone>(
    py: Python<'py>,
    value: &Dynamic<T>,
    convert: impl Fn(Python<'py>, &T) -> PyResult<Bound<'py, PyAny>>,
) -> PyResult<Bound<'py, PyAny>> {
    match value {
        Dynamic::Fixed(fixed) => convert(py, fixed),
        Dynamic::Bound(expr) => value_object(py, Arc::clone(expr)),
    }
}

/// A `Value` expression object.
pub fn value_object(py: Python<'_>, expr: Arc<Expr>) -> PyResult<Bound<'_, PyAny>> {
    Ok(Py::new(
        py,
        PyClassInitializer::from(PyExpression {
            kind: ExpressionKind::Value(expr),
        })
        .add_subclass(PyValue),
    )?
    .into_bound(py)
    .into_any())
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyWidget>()?;
    style::register(m)?;
    block::register(m)?;
    gauge::register(m)?;
    paragraph::register(m)?;
    clear::register(m)?;
    custom::register(m)?;
    live::register(m)?;
    list::register(m)?;
    table::register(m)?;
    tabs::register(m)?;
    line_gauge::register(m)?;
    sparkline::register(m)?;
    bar_chart::register(m)?;
    scrollbar::register(m)?;
    canvas::register(m)?;
    chart::register(m)?;
    calendar::register(m)?;
    Ok(())
}

/// Paint a widget by letting Python draw into a scratch buffer the size of `grid`.
///
/// `draw` receives the scratch buffer. The buffer lock is not held while Python runs, and
/// the scratch buffer reads the owner's runtime, so operations can use runtime values.
/// A Python exception is kept for [`refresh_tree`] to chain, and reported as an
/// evaluation failure.
pub fn paint_through_python(
    owner: &std::sync::Weak<BufferCore>,
    grid: &mut Grid,
    what: &str,
    draw: impl FnOnce(Python<'_>, &Bound<'_, PyAny>) -> PyResult<()>,
) -> Result<(), xnano_terminal_runtime::expression::EvalError> {
    use xnano_terminal_runtime::expression::EvalError;
    let owner_core = owner.upgrade();
    let owner_id = owner_core.as_ref().map_or(0, |core| core.id);
    let outcome: PyResult<Grid> = Python::attach(|py| {
        let scratch = crate::surface::new_buffer(py, grid.clone(), 0, 0, blank_cell(), None)?;
        let scratch_bound = scratch.bind(py);
        let scratch_core = Arc::clone(&scratch_bound.as_super().borrow().core);
        if let Some(shared) = owner_core.as_ref().and_then(shared_in_tree) {
            let ext = Arc::clone(&scratch_bound.as_super().borrow().ext);
            *crate::shared::lock(&ext.runtime) = Some(Arc::downgrade(&shared));
        }
        draw(py, scratch_bound.as_any())?;
        let painted = scratch_core.lock().grid.clone();
        Ok(painted)
    });
    match outcome {
        Ok(painted) => {
            if painted.width() != grid.width() || painted.height() != grid.height() {
                return Err(EvalError::Type(format!(
                    "the {what} changed the size of the area it draws into; draw inside the area \
                     it is given instead of resizing it"
                )));
            }
            *grid = painted;
            Ok(())
        }
        Err(error) => {
            let message =
                Python::attach(|py| format!("{}: {}", error.get_type(py), error.value(py)));
            stash_paint_error(owner_id, error);
            Err(EvalError::Type(format!("the {what} raised {message}")))
        }
    }
}

/// Read each watched expression once, for fingerprints.
pub fn fingerprint_watched(
    watched: &[Arc<Expr>],
    environment: &dyn xnano_terminal_runtime::expression::Environment,
    fingerprint: &mut xnano_terminal_runtime::dynamic::Fingerprint,
) -> Result<(), xnano_terminal_runtime::expression::EvalError> {
    let mut evaluation = xnano_terminal_runtime::expression::Evaluation::default();
    for expression in watched {
        let value = expression.evaluate_with(environment, &mut evaluation)?;
        fingerprint.add_debug(&value);
    }
    Ok(())
}

/// Expressions from a ``watch`` argument: any sequence of values or conditions.
pub fn watch_arg(value: Option<&Bound<'_, PyAny>>) -> PyResult<Vec<Arc<Expr>>> {
    let Some(value) = value.filter(|value| !value.is_none()) else {
        return Ok(Vec::new());
    };
    let mut expressions = Vec::new();
    for item in value.try_iter()? {
        let item = item?;
        let Ok(expression) = item.extract::<PyRef<'_, PyExpression>>() else {
            return Err(PyTypeError::new_err(
                "watch takes expressions such as a state value or Elapsed, not plain values",
            ));
        };
        match &expression.kind {
            ExpressionKind::Value(expr) => expressions.push(Arc::clone(expr)),
            _ => {
                return Err(PyTypeError::new_err(
                    "watch takes values and conditions; an operation cannot be watched",
                ));
            }
        }
    }
    Ok(expressions)
}
