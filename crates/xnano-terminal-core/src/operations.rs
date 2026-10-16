//! Surface operations: geometry, text, style, pixels, state and editor changes.

use std::sync::{Arc, OnceLock};

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyType;
use xnano_terminal_runtime::grid::WriteMode;
use xnano_terminal_runtime::operation::{EditorPainting, Operation};
use xnano_terminal_runtime::pixel::PixelEncoding;

use crate::convert::{node_from_py, path_from_py};
use crate::dynamic_operations::{
    TextSetting, dynamic_i32, dynamic_name, dynamic_scalar, finish, parse_border_kind,
    parse_encoding, parse_paste_mode, parse_raster_mode, parse_write_mode, scalar_to_node,
};
use crate::errors::operation_error;
use crate::expressions::{ExpressionKind, PyExpression, PyOperation};
use crate::geometry::PyRectangle;
use crate::state::{PyStatePatch, PyStateStore};
use crate::style::style_arg;
use crate::surface::{PyCell, PySurface, single_symbol};
use crate::text::PyTextEditor;
use crate::widgets::dynamic_color;
use crate::widgets::style::style_spec_arg;
use xnano_terminal_runtime::dynamic::Dynamic;
use xnano_terminal_runtime::operation::OperationError;
use xnano_terminal_runtime::widgets::style::StyleSpec;

static NATIVE_TYPES: OnceLock<Vec<Py<PyType>>> = OnceLock::new();

/// Whether `operation_type` is one of the operations implemented natively.
pub fn is_native_operation_type(
    py: Python<'_>,
    operation_type: &Bound<'_, PyType>,
) -> PyResult<bool> {
    let Some(natives) = NATIVE_TYPES.get() else {
        return Ok(false);
    };
    for native in natives {
        if operation_type.is_subclass(native.bind(py))? {
            return Ok(true);
        }
    }
    Ok(false)
}

/// Remember the native operation classes, which `supports` answers for.
pub fn remember_native_types(types: Vec<Py<PyType>>) {
    let _ = NATIVE_TYPES.set(types);
}

pub fn operation_initializer(operation: Operation) -> PyClassInitializer<PyOperation> {
    PyClassInitializer::from(PyExpression {
        kind: ExpressionKind::Operation(Some(Arc::new(operation))),
    })
    .add_subclass(PyOperation)
}

pub fn write_mode(mode: &str) -> PyResult<WriteMode> {
    WriteMode::from_name(mode).ok_or_else(|| {
        PyValueError::new_err(format!(
            "\"{mode}\" is not a write mode; use \"replace\" or \"preserve_background\""
        ))
    })
}

pub fn encoding_arg(encoding: &str) -> PyResult<PixelEncoding> {
    PixelEncoding::from_name(encoding).ok_or_else(|| {
        PyValueError::new_err(format!(
            "\"{encoding}\" is not a pixel encoding; use \"half_blocks\" or \"braille\""
        ))
    })
}

macro_rules! simple_operation {
    ($class:ident, $name:literal, $module:literal) => {
        #[pyclass(name = $name, module = $module, extends = PyOperation, subclass)]
        pub struct $class;
    };
}

simple_operation!(PyResize, "Resize", "xnano_core._xnano_core");
simple_operation!(PyMove, "Move", "xnano_core._xnano_core");
simple_operation!(PyPlace, "Place", "xnano_core._xnano_core");
simple_operation!(PyFill, "Fill", "xnano_core._xnano_core");
simple_operation!(PyClear, "Clear", "xnano_core._xnano_core");
simple_operation!(PyForeground, "Foreground", "xnano_core._xnano_core");
simple_operation!(PyBackground, "Background", "xnano_core._xnano_core");
simple_operation!(PyApplyStyle, "ApplyStyle", "xnano_core._xnano_core");
simple_operation!(PyBorder, "Border", "xnano_core._xnano_core");
simple_operation!(PyPaste, "Paste", "xnano_core._xnano_core");
simple_operation!(PyPixels, "Pixels", "xnano_core._xnano_core");
simple_operation!(PyRaster, "Raster", "xnano_core._xnano_core");
simple_operation!(PySetState, "SetState", "xnano_core._xnano_core");
simple_operation!(
    PyApplyStatePatch,
    "ApplyStatePatch",
    "xnano_core._xnano_core"
);
simple_operation!(PyWrite, "Write", "xnano_core._xnano_core");
simple_operation!(PyEditor, "Editor", "xnano_core._xnano_core");

fn optional_i32(value: Option<&Bound<'_, PyAny>>) -> PyResult<Dynamic<i32>> {
    match value.filter(|value| !value.is_none()) {
        Some(value) => dynamic_i32(value),
        None => Ok(Dynamic::Fixed(0)),
    }
}

fn optional_name(value: Option<&Bound<'_, PyAny>>, default: &str) -> PyResult<Dynamic<String>> {
    match value.filter(|value| !value.is_none()) {
        Some(value) => dynamic_name(value),
        None => Ok(Dynamic::Fixed(default.to_owned())),
    }
}

/// Reject a fixed name right away, so a typo fails where it was written.
fn check_fixed<T>(
    py: Python<'_>,
    setting: &Dynamic<String>,
    parse: fn(&str) -> Result<T, OperationError>,
) -> PyResult<()> {
    if let Dynamic::Fixed(name) = setting {
        parse(name).map_err(|error| operation_error(py, &error))?;
    }
    Ok(())
}

fn style_is_bound(style: &StyleSpec) -> bool {
    [&style.foreground, &style.background, &style.underline_color]
        .iter()
        .any(|color| color.as_ref().is_some_and(Dynamic::is_bound))
}

fn write_operation(
    py: Python<'_>,
    text: &Bound<'_, PyAny>,
    x: Dynamic<i32>,
    y: Dynamic<i32>,
    style: Option<&Bound<'_, PyAny>>,
    mode: Dynamic<String>,
) -> PyResult<PyClassInitializer<PyOperation>> {
    let text = TextSetting::from_py(text)?;
    let style = style_spec_arg(style)?;
    check_fixed(py, &mode, parse_write_mode)?;
    let bound = text.is_bound()
        || x.is_bound()
        || y.is_bound()
        || mode.is_bound()
        || style_is_bound(&style);
    finish(py, "Write", bound, move |resolver| {
        Ok(Operation::Write {
            lines: text.resolve(resolver)?,
            x: resolver.get(&x)?,
            y: resolver.get(&y)?,
            style: style.resolve(resolver)?,
            mode: parse_write_mode(&resolver.get(&mode)?)?,
        })
    })
}

#[pymethods]
impl PyResize {
    #[new]
    fn new(
        py: Python<'_>,
        width: &Bound<'_, PyAny>,
        height: &Bound<'_, PyAny>,
    ) -> PyResult<PyClassInitializer<Self>> {
        let (width, height) = (dynamic_i32(width)?, dynamic_i32(height)?);
        let bound = width.is_bound() || height.is_bound();
        Ok(finish(py, "Resize", bound, move |resolver| {
            let (width, height) = (resolver.get(&width)?, resolver.get(&height)?);
            xnano_terminal_runtime::buffer::check_size(width, height)
                .map_err(OperationError::Invalid)?;
            Ok(Operation::Resize { width, height })
        })?
        .add_subclass(Self))
    }
}

#[pymethods]
impl PyMove {
    #[new]
    #[pyo3(signature = (x = None, y = None))]
    fn new(
        py: Python<'_>,
        x: Option<&Bound<'_, PyAny>>,
        y: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<PyClassInitializer<Self>> {
        let x = optional_i32(x)?;
        let y = optional_i32(y)?;
        let bound = x.is_bound() || y.is_bound();
        Ok(finish(py, "Move", bound, move |resolver| {
            Ok(Operation::Move {
                x: resolver.get(&x)?,
                y: resolver.get(&y)?,
            })
        })?
        .add_subclass(Self))
    }
}

#[pymethods]
impl PyPlace {
    #[new]
    fn new(
        py: Python<'_>,
        x: &Bound<'_, PyAny>,
        y: &Bound<'_, PyAny>,
    ) -> PyResult<PyClassInitializer<Self>> {
        let (x, y) = (dynamic_i32(x)?, dynamic_i32(y)?);
        let bound = x.is_bound() || y.is_bound();
        Ok(finish(py, "Place", bound, move |resolver| {
            Ok(Operation::Place {
                x: resolver.get(&x)?,
                y: resolver.get(&y)?,
            })
        })?
        .add_subclass(Self))
    }
}

#[pymethods]
impl PyWrite {
    #[new]
    #[pyo3(signature = (text, *, x = None, y = None, style = None, mode = None))]
    fn new(
        py: Python<'_>,
        text: &Bound<'_, PyAny>,
        x: Option<&Bound<'_, PyAny>>,
        y: Option<&Bound<'_, PyAny>>,
        style: Option<&Bound<'_, PyAny>>,
        mode: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<PyClassInitializer<Self>> {
        Ok(write_operation(
            py,
            text,
            optional_i32(x)?,
            optional_i32(y)?,
            style,
            optional_name(mode, "replace")?,
        )?
        .add_subclass(Self))
    }
}

#[pyclass(name = "WriteCellText", module = "xnano_core._xnano_core", extends = PyWrite)]
pub struct PyWriteCellText;

#[pymethods]
impl PyWriteCellText {
    #[new]
    #[pyo3(signature = (text, *, column = None, row = None, style = None, mode = None))]
    fn new(
        py: Python<'_>,
        text: &Bound<'_, PyAny>,
        column: Option<&Bound<'_, PyAny>>,
        row: Option<&Bound<'_, PyAny>>,
        style: Option<&Bound<'_, PyAny>>,
        mode: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<PyClassInitializer<Self>> {
        Ok(write_operation(
            py,
            text,
            optional_i32(column)?,
            optional_i32(row)?,
            style,
            optional_name(mode, "replace")?,
        )?
        .add_subclass(PyWrite)
        .add_subclass(Self))
    }
}

/// A fill cell: a ready cell, or a symbol read from an expression.
#[derive(Clone)]
enum FillSetting {
    Cell(ratatui_core::buffer::Cell),
    Symbol(Dynamic<String>),
}

fn fill_cell(symbol: &str) -> PyResult<ratatui_core::buffer::Cell> {
    let (symbol, columns) = single_symbol(symbol)?;
    if columns != 1 {
        return Err(PyValueError::new_err(
            "Fill needs a symbol that takes one column",
        ));
    }
    let mut cell = ratatui_core::buffer::Cell::EMPTY;
    cell.set_symbol(&symbol);
    Ok(cell)
}

#[pymethods]
impl PyFill {
    #[new]
    #[pyo3(signature = (cell = None))]
    fn new(py: Python<'_>, cell: Option<&Bound<'_, PyAny>>) -> PyResult<PyClassInitializer<Self>> {
        let setting = match cell.filter(|value| !value.is_none()) {
            None => FillSetting::Cell(ratatui_core::buffer::Cell::EMPTY),
            Some(value) => {
                if let Ok(cell) = value.extract::<PyRef<'_, PyCell>>() {
                    FillSetting::Cell(cell.cell.clone())
                } else if value.extract::<PyRef<'_, PyExpression>>().is_ok() {
                    FillSetting::Symbol(dynamic_name(value)?)
                } else {
                    let text: String = value.extract().map_err(|_| {
                        PyTypeError::new_err("Fill needs a Cell or a one-character str")
                    })?;
                    FillSetting::Cell(fill_cell(&text)?)
                }
            }
        };
        let bound = matches!(&setting, FillSetting::Symbol(symbol) if symbol.is_bound());
        Ok(finish(py, "Fill", bound, move |resolver| {
            let cell = match &setting {
                FillSetting::Cell(cell) => cell.clone(),
                FillSetting::Symbol(symbol) => fill_cell(&resolver.get(symbol)?)
                    .map_err(|error| OperationError::Invalid(error.to_string()))?,
            };
            Ok(Operation::Fill(cell))
        })?
        .add_subclass(Self))
    }
}

#[pymethods]
impl PyClear {
    #[new]
    fn new() -> PyClassInitializer<Self> {
        operation_initializer(Operation::Clear).add_subclass(Self)
    }
}

#[pymethods]
impl PyForeground {
    #[new]
    fn new(py: Python<'_>, color: &Bound<'_, PyAny>) -> PyResult<PyClassInitializer<Self>> {
        let color = dynamic_color(color)?;
        Ok(finish(py, "Foreground", color.is_bound(), move |resolver| {
            Ok(Operation::Foreground(resolver.get(&color)?))
        })?
        .add_subclass(Self))
    }
}

#[pymethods]
impl PyBackground {
    #[new]
    fn new(py: Python<'_>, color: &Bound<'_, PyAny>) -> PyResult<PyClassInitializer<Self>> {
        let color = dynamic_color(color)?;
        Ok(finish(py, "Background", color.is_bound(), move |resolver| {
            Ok(Operation::Background(resolver.get(&color)?))
        })?
        .add_subclass(Self))
    }
}

#[pymethods]
impl PyApplyStyle {
    #[new]
    fn new(py: Python<'_>, style: &Bound<'_, PyAny>) -> PyResult<PyClassInitializer<Self>> {
        let style = style_spec_arg(Some(style))?;
        let bound = style_is_bound(&style);
        Ok(finish(py, "ApplyStyle", bound, move |resolver| {
            Ok(Operation::ApplyStyle(style.resolve(resolver)?))
        })?
        .add_subclass(Self))
    }
}

#[pymethods]
impl PyBorder {
    #[new]
    #[pyo3(signature = (kind = None, *, style = None))]
    fn new(
        py: Python<'_>,
        kind: Option<&Bound<'_, PyAny>>,
        style: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<PyClassInitializer<Self>> {
        let kind = optional_name(kind, "plain")?;
        check_fixed(py, &kind, parse_border_kind)?;
        let style = style_spec_arg(style)?;
        let bound = kind.is_bound() || style_is_bound(&style);
        Ok(finish(py, "Border", bound, move |resolver| {
            Ok(Operation::Border {
                kind: parse_border_kind(&resolver.get(&kind)?)?,
                style: style.resolve(resolver)?,
            })
        })?
        .add_subclass(Self))
    }
}

#[pymethods]
impl PyPaste {
    #[new]
    #[pyo3(signature = (source, *, x = None, y = None, mode = None))]
    fn new(
        py: Python<'_>,
        source: &Bound<'_, PyAny>,
        x: Option<&Bound<'_, PyAny>>,
        y: Option<&Bound<'_, PyAny>>,
        mode: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<PyClassInitializer<Self>> {
        let origin = source
            .extract::<PyRef<'_, PySurface>>()
            .map_err(|_| PyTypeError::new_err("Paste needs a Buffer or a Region as its source"))?;
        let bounds = origin.bounds()?;
        let snapshot = Arc::new(xnano_terminal_runtime::grid::Grid::from_buffer(
            origin.core.lock().grid.region_buffer(bounds),
        ));
        let (x, y) = (optional_i32(x)?, optional_i32(y)?);
        let mode = optional_name(mode, "replace")?;
        check_fixed(py, &mode, parse_paste_mode)?;
        let bound = x.is_bound() || y.is_bound() || mode.is_bound();
        Ok(finish(py, "Paste", bound, move |resolver| {
            Ok(Operation::Paste {
                source: Arc::clone(&snapshot),
                x: resolver.get(&x)?,
                y: resolver.get(&y)?,
                mode: parse_paste_mode(&resolver.get(&mode)?)?,
            })
        })?
        .add_subclass(Self))
    }
}

fn channel(value: i64) -> PyResult<u8> {
    u8::try_from(value).map_err(|_| {
        PyValueError::new_err(format!(
            "the color channel {value} is out of range; use 0 to 255"
        ))
    })
}

#[pymethods]
impl PyPixels {
    #[new]
    #[pyo3(signature = (pixels, *, encoding = None, clip = true, x = None, y = None))]
    fn new(
        py: Python<'_>,
        pixels: &Bound<'_, PyAny>,
        encoding: Option<&Bound<'_, PyAny>>,
        clip: bool,
        x: Option<&Bound<'_, PyAny>>,
        y: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<PyClassInitializer<Self>> {
        let mut collected = Vec::new();
        for item in pixels.try_iter()? {
            let (column, row, color): (i32, i32, (i64, i64, i64)) =
                item?.extract().map_err(|_| {
                    PyTypeError::new_err(
                        "a pixel is (column, row, (red, green, blue)) with whole numbers",
                    )
                })?;
            collected.push((
                column,
                row,
                (channel(color.0)?, channel(color.1)?, channel(color.2)?),
            ));
        }
        let collected = Arc::new(collected);
        let (x, y) = (optional_i32(x)?, optional_i32(y)?);
        let encoding = optional_name(encoding, "half_blocks")?;
        check_fixed(py, &encoding, parse_encoding)?;
        let bound = x.is_bound() || y.is_bound() || encoding.is_bound();
        Ok(finish(py, "Pixels", bound, move |resolver| {
            let (dx, dy) = (resolver.get(&x)?, resolver.get(&y)?);
            let pixels = if dx == 0 && dy == 0 {
                Arc::clone(&collected)
            } else {
                Arc::new(
                    collected
                        .iter()
                        .map(|&(column, row, color)| {
                            (column.saturating_add(dx), row.saturating_add(dy), color)
                        })
                        .collect::<Vec<_>>(),
                )
            };
            Ok(Operation::Pixels {
                pixels,
                encoding: parse_encoding(&resolver.get(&encoding)?)?,
                clip,
            })
        })?
        .add_subclass(Self))
    }
}

#[pymethods]
impl PyRaster {
    #[new]
    #[pyo3(signature = (rgba, *, width, height, x = None, y = None, encoding = None, mode = None))]
    fn new(
        py: Python<'_>,
        rgba: Vec<u8>,
        width: i32,
        height: i32,
        x: Option<&Bound<'_, PyAny>>,
        y: Option<&Bound<'_, PyAny>>,
        encoding: Option<&Bound<'_, PyAny>>,
        mode: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<PyClassInitializer<Self>> {
        if width < 0 || height < 0 {
            return Err(PyValueError::new_err(
                "the raster width and height must be zero or more",
            ));
        }
        let expected = (width as usize) * (height as usize) * 4;
        if rgba.len() != expected {
            return Err(PyValueError::new_err(format!(
                "an RGBA raster of {width} x {height} needs {expected} bytes (width * height * 4) \
                 but got {}",
                rgba.len()
            )));
        }
        let rgba = Arc::new(rgba);
        let (x, y) = (optional_i32(x)?, optional_i32(y)?);
        let encoding = optional_name(encoding, "half_blocks")?;
        let mode = optional_name(mode, "over")?;
        check_fixed(py, &encoding, parse_encoding)?;
        check_fixed(py, &mode, parse_raster_mode)?;
        let bound = x.is_bound() || y.is_bound() || encoding.is_bound() || mode.is_bound();
        Ok(finish(py, "Raster", bound, move |resolver| {
            Ok(Operation::Raster {
                rgba: Arc::clone(&rgba),
                width,
                height,
                x: resolver.get(&x)?,
                y: resolver.get(&y)?,
                encoding: parse_encoding(&resolver.get(&encoding)?)?,
                mode: parse_raster_mode(&resolver.get(&mode)?)?,
            })
        })?
        .add_subclass(Self))
    }
}

fn reference_parts(
    reference: &Bound<'_, PyAny>,
) -> PyResult<(Arc<xnano_terminal_state::Store>, Vec<String>)> {
    if let Ok(native) = reference.cast::<crate::references::PyStateReference>() {
        let native = native.get();
        return Ok((Arc::clone(&native.store), native.path.clone()));
    }
    let not_reference = || {
        PyTypeError::new_err(
            "expected a state reference with `path`, `native_store` and `schema` attributes",
        )
    };
    let native = reference
        .getattr("native_store")
        .map_err(|_| not_reference())?;
    let store = native
        .extract::<PyRef<'_, PyStateStore>>()
        .map(|store| Arc::clone(&store.inner))
        .map_err(|_| not_reference())?;
    let path = path_from_py(&reference.getattr("path")?)?;
    Ok((store, path))
}

#[pymethods]
impl PySetState {
    #[new]
    #[pyo3(signature = (reference, value, *, expected_revision = None))]
    fn new(
        py: Python<'_>,
        reference: &Bound<'_, PyAny>,
        value: &Bound<'_, PyAny>,
        expected_revision: Option<u64>,
    ) -> PyResult<PyClassInitializer<Self>> {
        let (store, path) = reference_parts(reference)?;
        if value.extract::<PyRef<'_, PyExpression>>().is_ok() {
            let setting = dynamic_scalar(value)?;
            return Ok(finish(py, "SetState", true, move |resolver| {
                Ok(Operation::SetState {
                    store: Arc::clone(&store),
                    path: path.clone(),
                    value: scalar_to_node(&resolver.get(&setting)?)?,
                    expected_revision,
                })
            })?
            .add_subclass(Self));
        }
        let encoded = if reference
            .cast::<crate::references::PyStateReference>()
            .is_ok()
        {
            value.clone()
        } else {
            reference
                .getattr("schema")?
                .call_method1("to_value", (value,))?
        };
        Ok(operation_initializer(Operation::SetState {
            store,
            path,
            value: node_from_py(&encoded)?,
            expected_revision,
        })
        .add_subclass(Self))
    }
}

#[pymethods]
impl PyApplyStatePatch {
    #[new]
    #[pyo3(signature = (reference, patch, *, expected_revision = None))]
    fn new(
        reference: &Bound<'_, PyAny>,
        patch: &Bound<'_, PyAny>,
        expected_revision: Option<u64>,
    ) -> PyResult<PyClassInitializer<Self>> {
        let (store, path) = reference_parts(reference)?;
        let native = match patch.getattr("native") {
            Ok(native) => native,
            Err(_) => patch.clone(),
        };
        let patch = native
            .extract::<PyRef<'_, PyStatePatch>>()
            .map_err(|_| PyTypeError::new_err("ApplyStatePatch needs a TerminalStatePatch"))?
            .inner
            .clone();
        Ok(operation_initializer(Operation::ApplyStatePatch {
            store,
            path,
            patch,
            expected_revision,
        })
        .add_subclass(Self))
    }
}

#[pymethods]
impl PyEditor {
    #[new]
    #[pyo3(signature = (editor, *, area = None, style = None, first_row = 0, should_wrap = true,
        should_show_cursor = true, mode = "preserve_background"))]
    fn new(
        editor: &PyTextEditor,
        area: Option<&PyRectangle>,
        style: Option<&Bound<'_, PyAny>>,
        first_row: usize,
        should_wrap: bool,
        should_show_cursor: bool,
        mode: &str,
    ) -> PyResult<PyClassInitializer<Self>> {
        Ok(operation_initializer(Operation::Editor(EditorPainting {
            editor: Arc::clone(&editor.inner),
            area: area.map(|area| area.inner),
            style: style_arg(style)?,
            first_row,
            should_wrap,
            should_show_cursor,
            mode: write_mode(mode)?,
        }))
        .add_subclass(Self))
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyResize>()?;
    m.add_class::<PyMove>()?;
    m.add_class::<PyPlace>()?;
    m.add_class::<PyWrite>()?;
    m.add_class::<PyWriteCellText>()?;
    m.add_class::<PyFill>()?;
    m.add_class::<PyClear>()?;
    m.add_class::<PyForeground>()?;
    m.add_class::<PyBackground>()?;
    m.add_class::<PyApplyStyle>()?;
    m.add_class::<PyBorder>()?;
    m.add_class::<PyPaste>()?;
    m.add_class::<PyPixels>()?;
    m.add_class::<PyRaster>()?;
    m.add_class::<PySetState>()?;
    m.add_class::<PyApplyStatePatch>()?;
    m.add_class::<PyEditor>()?;
    Ok(())
}
