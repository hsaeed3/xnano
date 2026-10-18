//! The native extension behind the `xnano_core` Python package.

mod cell_grid;
mod clocks;
mod convert;
mod cursor;
mod customization;
mod drawings;
mod dynamic_operations;
mod effects;
mod error_reports;
mod errors;
mod events;
mod expressions;
mod geometry;
mod hooks;
mod input;
mod layout;
mod operation_reprs;
mod operations;
mod references;
mod reprs;
mod runtime;
mod scopes;
mod shared;
mod state;
mod style;
mod surface;
mod text;
mod trigger;
mod widgets;

use pyo3::prelude::*;
use pyo3::types::PyType;

/// The operation classes `Surface.supports` answers for.
const OPERATION_CLASSES: &[&str] = &[
    "Resize",
    "Move",
    "Place",
    "Write",
    "WriteCellText",
    "Fill",
    "Clear",
    "Foreground",
    "Background",
    "ApplyStyle",
    "Border",
    "Paste",
    "Pixels",
    "Raster",
    "SetState",
    "ApplyStatePatch",
    "Editor",
    "SetValue",
    "SequenceOperation",
    "Conditional",
    "Effect",
    "CancelEffect",
    "Fuzz",
    "Layout",
    "Draw",
    "AnimateDrawing",
];

/// Make the extension module act as the package `xnano_core._xnano_core`.
///
/// The compiled module is the package's `__init__`; setting `__path__` to the directory of
/// the same name lets Python import the pure-Python `xnano_core._xnano_core._core_types` next to it.
fn mark_as_package(module: &Bound<'_, PyModule>) -> PyResult<()> {
    let py = module.py();
    let parent_directory = py.import("xnano_core")?.getattr("__path__")?.get_item(0)?;
    let directory = py
        .import("os")?
        .getattr("path")?
        .call_method1("join", (parent_directory, "_xnano_core"))?;
    module.setattr("__path__", vec![directory])
}

#[pymodule(gil_used = false)]
fn _xnano_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add(
        "is_optimized_build",
        option_env!("XNANO_OPTIMIZATION_LEVEL") != Some("0"),
    )?;
    mark_as_package(m)?;
    geometry::register(m)?;
    style::register(m)?;
    clocks::register(m)?;
    events::register(m)?;
    text::register(m)?;
    cell_grid::register(m)?;
    state::register(m)?;
    references::register(m)?;
    hooks::register(m)?;
    expressions::register(m)?;
    customization::register(m)?;
    scopes::register(m)?;
    trigger::register(m)?;
    surface::register(m)?;
    operations::register(m)?;
    effects::register(m)?;
    layout::register(m)?;
    widgets::register(m)?;
    drawings::register(m)?;
    input::register(m)?;
    cursor::register(m)?;
    runtime::register(m)?;
    error_reports::register(m)?;
    let py = m.py();
    m.add("RenderError", py.get_type::<errors::RenderError>())?;
    m.add(
        "UnsupportedOperationError",
        py.get_type::<errors::UnsupportedOperationError>(),
    )?;
    m.add(
        "RuntimeRequiredError",
        py.get_type::<errors::RuntimeRequiredError>(),
    )?;
    m.add(
        "InvalidRegionError",
        py.get_type::<errors::InvalidRegionError>(),
    )?;
    let make_reference = m.getattr("_reference")?;
    for (name, kind) in [
        ("X", "numeric_property"),
        ("Y", "numeric_property"),
        ("Width", "numeric_property"),
        ("Height", "numeric_property"),
        ("Position", "property"),
        ("Bounds", "value"),
        ("TimeElapsed", "numeric"),
        ("TimeDelta", "numeric"),
        ("TimeElapsedMilliseconds", "numeric"),
        ("TimeDeltaMilliseconds", "numeric"),
        ("Frame", "numeric"),
        ("FPS", "numeric"),
        ("Focused", "value"),
        ("Running", "value"),
        ("DeviceWidth", "numeric"),
        ("DeviceHeight", "numeric"),
        ("ParentWidth", "numeric"),
        ("ParentHeight", "numeric"),
        ("ParentSize", "value"),
        ("ScreenPosition", "value"),
        ("ScreenBounds", "value"),
        ("PointerPosition", "value"),
        ("Layer", "numeric_property"),
        ("IsVisible", "property"),
        ("KeyboardKey", "value"),
        ("KeyboardKind", "value"),
        ("KeyboardChord", "value"),
        ("MouseButtonValue", "value"),
        ("MouseKind", "value"),
        ("MousePosition", "value"),
        ("MouseIsDown", "predicate"),
        ("ScrollX", "numeric"),
        ("ScrollY", "numeric"),
        ("BufferRegion", "value"),
    ] {
        m.add(name, make_reference.call1((name, kind))?)?;
    }
    // `Size` is the geometry class, so the buffer-size reference is `BufferSize`.
    m.add("BufferSize", make_reference.call1(("Size", "property"))?)?;
    scopes::add_scopes(m)?;
    let mut natives = Vec::new();
    for name in OPERATION_CLASSES {
        natives.push(m.getattr(*name)?.cast_into::<PyType>()?.unbind());
    }
    operations::remember_native_types(natives);
    Ok(())
}
