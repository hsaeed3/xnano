//! `Customization`: a named, typed set of parameters that is an operation.
//!
//! ``Customization('style', bold=True)`` names what to change (a style, a border, a layout,
//! a visual effect, an audio effect) and the parameters of the change. The parameters are read
//! when the customization is used, so a subclass that keeps them as attributes (a dataclass,
//! say) can be edited after it is created. Every kind is resolved here, natively, to the core
//! object that does the work, so a customization needs no Python code of its own to be applied,
//! piped with ``|`` or sequenced with other operations.

use std::sync::Arc;

use pyo3::exceptions::{PyImportError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyTuple};
use xnano_terminal_runtime::operation::Operation;

use crate::expressions::{PyOperation, operation_of};

/// The value a parameter takes when it is not given.
#[derive(Clone, Copy)]
enum Default {
    None,
    Bool(bool),
    Int(i64),
    Float(f64),
    Text(&'static str),
    Pair(i64, i64),
    Bytes,
    Sequence,
}

struct Parameter {
    name: &'static str,
    default: Default,
}

const fn required(name: &'static str) -> Parameter {
    Parameter {
        name,
        default: Default::None,
    }
}

const fn with(name: &'static str, default: Default) -> Parameter {
    Parameter { name, default }
}

/// How a kind turns its parameters into a core object.
enum Build {
    /// Call `Class(positional..., keyword=...)` or `Class.method(...)` of `xnano_core`.
    Call {
        target: &'static str,
        positional: &'static [&'static str],
        keyword: &'static [&'static str],
        /// Whether the result is an effect that takes the `key` parameter.
        keyed: bool,
    },
    Style,
    Border,
    Padding,
    Pixels,
    /// Call `TerminalAudioEffect.method(**parameters)` of `xnano_audio`.
    Audio(&'static str),
}

struct Kind {
    name: &'static str,
    parameters: &'static [Parameter],
    build: Build,
}

macro_rules! parameters {
    ($($parameter:expr),* $(,)?) => { &[$($parameter),*] };
}

macro_rules! timed {
    ($($parameter:expr),* $(,)?) => {
        parameters![
            $($parameter,)*
            required("duration_milliseconds"),
            required("interpolation"),
            required("key"),
        ]
    };
}

macro_rules! effect {
    ($name:literal, $method:literal, [$($positional:literal),*], [$($keyword:literal),*], $parameters:expr) => {
        Kind {
            name: concat!("effect.", $name),
            parameters: $parameters,
            build: Build::Call {
                target: concat!("Effect.", $method),
                positional: &[$($positional),*],
                keyword: &[$($keyword),*],
                keyed: true,
            },
        }
    };
}

macro_rules! audio {
    ($name:literal, $parameters:expr) => {
        Kind {
            name: concat!("audio.", $name),
            parameters: $parameters,
            build: Build::Audio($name),
        }
    };
}

macro_rules! call {
    ($name:literal, $target:literal, [$($positional:literal),*], [$($keyword:literal),*], $parameters:expr) => {
        Kind {
            name: $name,
            parameters: $parameters,
            build: Build::Call {
                target: $target,
                positional: &[$($positional),*],
                keyword: &[$($keyword),*],
                keyed: false,
            },
        }
    };
}

static KINDS: &[Kind] = &[
    Kind {
        name: "style",
        parameters: parameters![
            required("foreground"),
            required("background"),
            with("bold", Default::Bool(false)),
            with("dim", Default::Bool(false)),
            with("italic", Default::Bool(false)),
            with("underline", Default::Bool(false)),
            with("blink", Default::Bool(false)),
            with("reverse", Default::Bool(false)),
            with("hidden", Default::Bool(false)),
            with("crossed_out", Default::Bool(false)),
            with("rapid_blink", Default::Bool(false)),
            required("underline_color"),
        ],
        build: Build::Style,
    },
    Kind {
        name: "border",
        parameters: parameters![
            with("kind", Default::Text("plain")),
            required("border_kind"),
            required("style"),
        ],
        build: Build::Border,
    },
    call!(
        "block",
        "Block",
        ["title"],
        [
            "borders",
            "border_type",
            "border_style",
            "style",
            "title_style",
            "title_alignment",
            "padding",
            "merge",
            "width",
            "height",
            "x",
            "y"
        ],
        parameters![
            required("title"),
            required("borders"),
            required("border_type"),
            required("border_style"),
            required("style"),
            required("title_style"),
            with("title_alignment", Default::Text("left")),
            required("padding"),
            required("merge"),
            required("width"),
            required("height"),
            with("x", Default::Int(0)),
            with("y", Default::Int(0)),
        ]
    ),
    Kind {
        name: "padding",
        parameters: parameters![
            with("left", Default::Int(0)),
            with("right", Default::Int(0)),
            with("top", Default::Int(0)),
            with("bottom", Default::Int(0)),
            required("horizontal"),
            required("vertical"),
            required("uniform"),
        ],
        build: Build::Padding,
    },
    call!(
        "margin",
        "Margin",
        [],
        ["horizontal", "vertical"],
        parameters![
            with("horizontal", Default::Int(0)),
            with("vertical", Default::Int(0)),
        ]
    ),
    call!(
        "fill",
        "Fill",
        ["cell"],
        [],
        parameters![with("cell", Default::Text(" "))]
    ),
    call!(
        "foreground",
        "Foreground",
        ["color"],
        [],
        parameters![with("color", Default::Text("white"))]
    ),
    call!(
        "background",
        "Background",
        ["color"],
        [],
        parameters![with("color", Default::Text("black"))]
    ),
    call!(
        "write",
        "Write",
        ["text"],
        ["x", "y", "style", "mode"],
        parameters![
            with("text", Default::Text("")),
            with("x", Default::Int(0)),
            with("y", Default::Int(0)),
            required("style"),
            with("mode", Default::Text("replace")),
        ]
    ),
    call!(
        "layout",
        "Layout",
        ["arrangement"],
        ["sizes", "spacing", "padding"],
        parameters![
            with("arrangement", Default::Text("column")),
            with("sizes", Default::Sequence),
            with("spacing", Default::Int(0)),
            with("padding", Default::Int(0)),
        ]
    ),
    call!(
        "fuzz",
        "Fuzz",
        ["intensity"],
        ["seed"],
        parameters![with("intensity", Default::Int(10)), required("seed")]
    ),
    Kind {
        name: "pixels",
        parameters: parameters![
            required("shader"),
            required("pixels"),
            with("encoding", Default::Text("half_blocks")),
            with("clip", Default::Bool(true)),
            required("x"),
            required("y"),
        ],
        build: Build::Pixels,
    },
    call!(
        "raster",
        "Raster",
        ["rgba"],
        ["width", "height", "x", "y", "encoding", "mode"],
        parameters![
            with("rgba", Default::Bytes),
            with("width", Default::Int(0)),
            with("height", Default::Int(0)),
            with("x", Default::Int(0)),
            with("y", Default::Int(0)),
            with("encoding", Default::Text("half_blocks")),
            with("mode", Default::Text("over")),
        ]
    ),
    effect!(
        "fade_to",
        "fade_to",
        ["foreground", "background"],
        ["duration_milliseconds", "interpolation"],
        timed![required("foreground"), required("background")]
    ),
    effect!(
        "fade_from",
        "fade_from",
        ["foreground", "background"],
        ["duration_milliseconds", "interpolation"],
        timed![required("foreground"), required("background")]
    ),
    effect!(
        "paint",
        "paint",
        ["foreground", "background"],
        ["duration_milliseconds", "interpolation"],
        timed![required("foreground"), required("background")]
    ),
    effect!(
        "saturate",
        "saturate",
        ["foreground", "background"],
        ["duration_milliseconds", "interpolation"],
        timed![required("foreground"), required("background")]
    ),
    effect!(
        "lighten",
        "lighten",
        ["foreground", "background"],
        ["duration_milliseconds", "interpolation"],
        timed![required("foreground"), required("background")]
    ),
    effect!(
        "darken",
        "darken",
        ["foreground", "background"],
        ["duration_milliseconds", "interpolation"],
        timed![required("foreground"), required("background")]
    ),
    effect!(
        "sweep_in",
        "sweep_in",
        ["direction"],
        [
            "gradient_length",
            "randomness",
            "color",
            "duration_milliseconds",
            "interpolation"
        ],
        timed![
            required("direction"),
            required("gradient_length"),
            required("randomness"),
            required("color"),
        ]
    ),
    effect!(
        "sweep_out",
        "sweep_out",
        ["direction"],
        [
            "gradient_length",
            "randomness",
            "color",
            "duration_milliseconds",
            "interpolation"
        ],
        timed![
            required("direction"),
            required("gradient_length"),
            required("randomness"),
            required("color"),
        ]
    ),
    effect!(
        "slide_in",
        "slide_in",
        ["direction"],
        [
            "gradient_length",
            "randomness",
            "color",
            "duration_milliseconds",
            "interpolation"
        ],
        timed![
            required("direction"),
            required("gradient_length"),
            required("randomness"),
            required("color"),
        ]
    ),
    effect!(
        "slide_out",
        "slide_out",
        ["direction"],
        [
            "gradient_length",
            "randomness",
            "color",
            "duration_milliseconds",
            "interpolation"
        ],
        timed![
            required("direction"),
            required("gradient_length"),
            required("randomness"),
            required("color"),
        ]
    ),
    effect!(
        "hsl_shift",
        "hsl_shift",
        ["foreground", "background"],
        ["duration_milliseconds", "interpolation"],
        timed![required("foreground"), required("background")]
    ),
    effect!(
        "dissolve",
        "dissolve",
        [],
        ["style", "duration_milliseconds", "interpolation"],
        timed![required("style")]
    ),
    effect!(
        "coalesce",
        "coalesce",
        [],
        ["style", "duration_milliseconds", "interpolation"],
        timed![required("style")]
    ),
    effect!(
        "glitch",
        "glitch",
        [],
        [
            "ratio",
            "duration_milliseconds",
            "start_delay_milliseconds",
            "action_milliseconds"
        ],
        parameters![
            required("ratio"),
            required("duration_milliseconds"),
            with("start_delay_milliseconds", Default::Pair(0, 0)),
            with("action_milliseconds", Default::Pair(50, 150)),
            required("key"),
        ]
    ),
    effect!(
        "sleep",
        "sleep",
        ["duration_milliseconds"],
        ["interpolation"],
        parameters![
            with("duration_milliseconds", Default::Int(500)),
            required("interpolation"),
            required("key"),
        ]
    ),
    effect!(
        "evolve",
        "evolve",
        ["symbols"],
        ["style", "duration_milliseconds", "interpolation"],
        timed![required("symbols"), required("style")]
    ),
    effect!(
        "evolve_into",
        "evolve_into",
        ["symbols"],
        ["style", "duration_milliseconds", "interpolation"],
        timed![required("symbols"), required("style")]
    ),
    effect!(
        "evolve_from",
        "evolve_from",
        ["symbols"],
        ["style", "duration_milliseconds", "interpolation"],
        timed![required("symbols"), required("style")]
    ),
    effect!(
        "expand",
        "expand",
        ["direction"],
        ["style", "duration_milliseconds", "interpolation"],
        timed![required("direction"), required("style")]
    ),
    effect!(
        "stretch",
        "stretch",
        ["direction"],
        ["style", "duration_milliseconds", "interpolation"],
        timed![required("direction"), required("style")]
    ),
    effect!(
        "explode",
        "explode",
        [],
        [
            "force",
            "randomness",
            "duration_milliseconds",
            "interpolation"
        ],
        timed![required("force"), required("randomness")]
    ),
    audio!(
        "bit_crush",
        parameters![
            with("bits", Default::Int(8)),
            with("downsample", Default::Int(4)),
        ]
    ),
    audio!(
        "distortion",
        parameters![with("drive", Default::Float(4.0))]
    ),
    audio!(
        "low_pass",
        parameters![
            with("cutoff", Default::Float(1200.0)),
            with("resonance", Default::Float(0.707)),
        ]
    ),
    audio!(
        "high_pass",
        parameters![
            with("cutoff", Default::Float(400.0)),
            with("resonance", Default::Float(0.707)),
        ]
    ),
    audio!(
        "delay",
        parameters![
            with("time_milliseconds", Default::Float(250.0)),
            with("feedback", Default::Float(0.4)),
            with("mix", Default::Float(0.35)),
        ]
    ),
    audio!(
        "reverb",
        parameters![
            with("room", Default::Float(0.5)),
            with("damping", Default::Float(0.5)),
            with("mix", Default::Float(0.25)),
        ]
    ),
    audio!(
        "tremolo",
        parameters![
            with("rate_hertz", Default::Float(5.0)),
            with("depth", Default::Float(0.5)),
        ]
    ),
];

fn find_kind(name: &str) -> PyResult<&'static Kind> {
    KINDS.iter().find(|kind| kind.name == name).ok_or_else(|| {
        let names: Vec<&str> = KINDS.iter().map(|kind| kind.name).collect();
        PyValueError::new_err(format!(
            "\"{name}\" is not a customization kind. Choose one of: {}.",
            names.join(", ")
        ))
    })
}

fn core_module(py: Python<'_>) -> PyResult<Bound<'_, PyModule>> {
    py.import("xnano_core._xnano_core")
}

fn default_value(py: Python<'_>, default: Default) -> PyResult<Bound<'_, PyAny>> {
    Ok(match default {
        Default::None => py.None().into_bound(py),
        Default::Bool(value) => value.into_pyobject(py)?.to_owned().into_any(),
        Default::Int(value) => value.into_pyobject(py)?.into_any(),
        Default::Float(value) => value.into_pyobject(py)?.into_any(),
        Default::Text(value) => value.into_pyobject(py)?.into_any(),
        Default::Pair(first, second) => PyTuple::new(py, [first, second])?.into_any(),
        Default::Bytes => pyo3::types::PyBytes::new(py, &[]).into_any(),
        Default::Sequence => PyTuple::empty(py).into_any(),
    })
}

/// A named, typed set of parameters that is an operation.
#[pyclass(
    name = "Customization",
    module = "xnano_core._xnano_core",
    extends = PyOperation,
    subclass
)]
pub struct PyCustomization {
    /// The kind named when constructed directly, as `Customization('style', ...)`.
    declared: Option<Py<PyAny>>,
    /// The parameters given when constructed directly.
    parameters: Py<PyDict>,
}

impl PyCustomization {
    /// Whether this is a plain `Customization` rather than a subclass that keeps its own fields.
    fn is_direct(slf: &Bound<'_, Self>) -> bool {
        slf.get_type().is(slf.py().get_type::<Self>())
    }

    fn kind_of(slf: &Bound<'_, Self>) -> PyResult<&'static Kind> {
        let py = slf.py();
        if !Self::is_direct(slf) {
            let name: String = slf.getattr("customization_kind")?.extract()?;
            return find_kind(&name);
        }
        let declared = slf
            .borrow()
            .declared
            .as_ref()
            .map(|name| name.clone_ref(py));
        let Some(declared) = declared else {
            return Err(PyTypeError::new_err(
                "Customization needs the kind to fx, such as \
                 Customization('style', bold=True).",
            ));
        };
        let name: String = declared.bind(py).extract().map_err(|_| {
            PyTypeError::new_err("the kind of a Customization must be text such as 'style'.")
        })?;
        let kind = find_kind(&name)?;
        for given in slf.borrow().parameters.bind(py).keys() {
            let given: String = given.extract()?;
            if !kind
                .parameters
                .iter()
                .any(|parameter| parameter.name == given)
            {
                let valid: Vec<&str> = kind.parameters.iter().map(|p| p.name).collect();
                return Err(PyTypeError::new_err(format!(
                    "fx('{}') has no parameter \"{given}\". Its parameters are: {}.",
                    kind.name,
                    valid.join(", ")
                )));
            }
        }
        Ok(kind)
    }

    /// The value of one parameter: given directly, kept as an attribute, or the default.
    fn parameter<'py>(
        slf: &Bound<'py, Self>,
        parameter: &Parameter,
    ) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        if Self::is_direct(slf) {
            if let Some(value) = slf.borrow().parameters.bind(py).get_item(parameter.name)? {
                return Self::resolved(value);
            }
        } else if let Ok(attributes) = slf.getattr("__dict__")
            && let Some(value) = attributes.cast::<PyDict>()?.get_item(parameter.name)?
        {
            return Self::resolved(value);
        }
        default_value(py, parameter.default)
    }

    /// A parameter that is itself a customization (a style for a border) is built first.
    fn resolved(value: Bound<'_, PyAny>) -> PyResult<Bound<'_, PyAny>> {
        match value.cast::<Self>() {
            Ok(inner) => Self::build_object(inner),
            Err(_) => Ok(value),
        }
    }

    fn text_parameter(slf: &Bound<'_, Self>, kind: &Kind, name: &str) -> PyResult<Py<PyAny>> {
        let parameter = kind
            .parameters
            .iter()
            .find(|parameter| parameter.name == name)
            .ok_or_else(|| PyValueError::new_err(format!("{} has no \"{name}\"", kind.name)))?;
        Ok(Self::parameter(slf, parameter)?.unbind())
    }

    /// Build the core object this customization stands for.
    pub fn build_object<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let kind = Self::kind_of(slf)?;
        let core = core_module(py)?;
        match &kind.build {
            Build::Call {
                target,
                positional,
                keyword,
                keyed,
            } => {
                let mut callable = core.clone().into_any();
                for part in target.split('.') {
                    callable = callable.getattr(part)?;
                }
                let mut arguments = Vec::with_capacity(positional.len());
                for name in *positional {
                    arguments.push(Self::named(slf, kind, name)?);
                }
                let options = PyDict::new(py);
                for name in *keyword {
                    options.set_item(name, Self::named(slf, kind, name)?)?;
                }
                let built = callable.call(PyTuple::new(py, arguments)?, Some(&options))?;
                if *keyed {
                    let key = Self::named(slf, kind, "key")?;
                    if !key.is_none() {
                        return built.call_method1("with_key", (key,));
                    }
                }
                Ok(built)
            }
            Build::Style => {
                let options = PyDict::new(py);
                for name in [
                    "bold",
                    "dim",
                    "italic",
                    "underline",
                    "blink",
                    "rapid_blink",
                    "reverse",
                    "hidden",
                    "crossed_out",
                    "underline_color",
                ] {
                    options.set_item(name, Self::named(slf, kind, name)?)?;
                }
                core.getattr("Style")?.call(
                    (
                        Self::named(slf, kind, "foreground")?,
                        Self::named(slf, kind, "background")?,
                    ),
                    Some(&options),
                )
            }
            Build::Border => {
                let chosen = Self::named(slf, kind, "border_kind")?;
                let border_kind = if chosen.is_none() {
                    Self::named(slf, kind, "kind")?
                } else {
                    chosen
                };
                let options = PyDict::new(py);
                options.set_item("style", Self::named(slf, kind, "style")?)?;
                core.getattr("Border")?.call((border_kind,), Some(&options))
            }
            Build::Padding => {
                let number =
                    |name: &str| -> PyResult<Bound<'py, PyAny>> { Self::named(slf, kind, name) };
                let uniform = number("uniform")?;
                if !uniform.is_none() {
                    return Ok(
                        PyTuple::new(py, [&uniform, &uniform, &uniform, &uniform])?.into_any()
                    );
                }
                let horizontal = number("horizontal")?;
                let vertical = number("vertical")?;
                let side = |shared: &Bound<'py, PyAny>, own: &str| -> PyResult<Bound<'py, PyAny>> {
                    if shared.is_none() {
                        number(own)
                    } else {
                        Ok(shared.clone())
                    }
                };
                Ok(PyTuple::new(
                    py,
                    [
                        side(&horizontal, "left")?,
                        side(&horizontal, "right")?,
                        side(&vertical, "top")?,
                        side(&vertical, "bottom")?,
                    ],
                )?
                .into_any())
            }
            Build::Pixels => {
                let pixels = Self::named(slf, kind, "pixels")?;
                if pixels.is_none() || !Self::named(slf, kind, "shader")?.is_none() {
                    return Ok(slf.clone().into_any());
                }
                let options = PyDict::new(py);
                options.set_item("encoding", Self::named(slf, kind, "encoding")?)?;
                options.set_item("clip", Self::named(slf, kind, "clip")?)?;
                for name in ["x", "y"] {
                    options.set_item(name, Self::named(slf, kind, name)?)?;
                }
                core.getattr("Pixels")?.call((pixels,), Some(&options))
            }
            Build::Audio(method) => {
                let audio = py.import("xnano_audio").map_err(|error| {
                    if error.is_instance_of::<pyo3::exceptions::PyModuleNotFoundError>(py) {
                        PyImportError::new_err(format!(
                            "fx('audio.{method}') needs sound synthesis, which is provided \
                             by the optional package xnano-audio. Install it with: pip install \
                             \"xnano[audio]\""
                        ))
                    } else {
                        error
                    }
                })?;
                let options = PyDict::new(py);
                for parameter in kind.parameters {
                    options.set_item(parameter.name, Self::parameter(slf, parameter)?)?;
                }
                audio
                    .getattr("TerminalAudioEffect")?
                    .call_method(*method, (), Some(&options))
            }
        }
    }

    fn named<'py>(slf: &Bound<'py, Self>, kind: &Kind, name: &str) -> PyResult<Bound<'py, PyAny>> {
        Ok(Self::text_parameter(slf, kind, name)?.into_bound(slf.py()))
    }

    /// The native operation this customization applies, or `None` when it needs `apply_to_surface`.
    pub fn native_operation(slf: &Bound<'_, Self>) -> PyResult<Option<Arc<Operation>>> {
        let py = slf.py();
        let built = Self::build_object(slf)?;
        if built.is(slf) {
            return Ok(None);
        }
        let core = core_module(py)?;
        if built.is_instance(&core.getattr("Style")?)? {
            let applied = core.getattr("ApplyStyle")?.call1((built,))?;
            return operation_of(&applied);
        }
        if built.is_instance_of::<PyOperation>() {
            return operation_of(&built);
        }
        Ok(None)
    }
}

#[pymethods]
impl PyCustomization {
    /// ``Customization('style', bold=True)``; subclasses name their kind with a
    /// ``customization_kind`` class attribute and keep their parameters as attributes.
    #[new]
    #[pyo3(signature = (*arguments, **options))]
    fn new(
        arguments: &Bound<'_, PyTuple>,
        options: Option<&Bound<'_, PyDict>>,
    ) -> PyClassInitializer<Self> {
        let py = arguments.py();
        let parameters = options.map_or_else(
            || PyDict::new(py),
            |options| options.copy().unwrap_or_else(|_| PyDict::new(py)),
        );
        PyClassInitializer::from(crate::expressions::PyExpression {
            kind: crate::expressions::ExpressionKind::Operation(None),
        })
        .add_subclass(PyOperation)
        .add_subclass(Self {
            declared: arguments.get_item(0).ok().map(Bound::unbind),
            parameters: parameters.unbind(),
        })
    }

    /// The kind of customization, such as ``'style'`` or ``'effect.fade_to'``.
    #[getter]
    fn customization_kind(slf: &Bound<'_, Self>) -> PyResult<&'static str> {
        Ok(Self::kind_of(slf)?.name)
    }

    /// The parameters of this customization by name, with defaults filled in.
    #[getter]
    fn parameters<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyDict>> {
        let py = slf.py();
        let kind = Self::kind_of(slf)?;
        let result = PyDict::new(py);
        for parameter in kind.parameters {
            result.set_item(parameter.name, Self::parameter(slf, parameter)?)?;
        }
        Ok(result)
    }

    /// The names of every kind of customization.
    #[staticmethod]
    fn kinds() -> Vec<&'static str> {
        KINDS.iter().map(|kind| kind.name).collect()
    }

    /// The parameter names and defaults of a kind, in order.
    #[staticmethod]
    fn defaults<'py>(py: Python<'py>, kind: &str) -> PyResult<Bound<'py, PyDict>> {
        let result = PyDict::new(py);
        for parameter in find_kind(kind)?.parameters {
            result.set_item(parameter.name, default_value(py, parameter.default)?)?;
        }
        Ok(result)
    }

    /// Construct the core object this customization stands for: a ``Style``, ``Border``,
    /// ``Effect``, ``Block``, audio effect and so on.
    fn build<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        Self::build_object(slf)
    }

    /// The core operation that applies this customization.
    ///
    /// Raises ``TypeError`` for a kind that is not applied as an operation.
    fn to_operation<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let built = Self::build_object(slf)?;
        let core = core_module(py)?;
        if built.is_instance(&core.getattr("Style")?)? {
            return core.getattr("ApplyStyle")?.call1((built,));
        }
        if built.is_instance_of::<PyOperation>() {
            return Ok(built);
        }
        Err(PyTypeError::new_err(format!(
            "fx('{}') does not build an operation. Apply it with update() or pipe it \
             onto a surface instead.",
            Self::kind_of(slf)?.name
        )))
    }

    /// The audio effect behind an ``audio.*`` customization.
    fn to_audio_effect<'py>(slf: &Bound<'py, Self>) -> PyResult<Bound<'py, PyAny>> {
        let kind = Self::kind_of(slf)?;
        if !matches!(kind.build, Build::Audio(_)) {
            return Err(PyTypeError::new_err(format!(
                "fx('{}') is not an audio effect. Audio kinds start with \"audio.\".",
                kind.name
            )));
        }
        Self::build_object(slf)
    }

    /// Apply this customization to a buffer, widget or region.
    fn apply_to_surface(slf: &Bound<'_, Self>, surface: &Bound<'_, PyAny>) -> PyResult<()> {
        let py = slf.py();
        let kind = Self::kind_of(slf)?;
        if let Some(native) = Self::native_operation(slf)? {
            let operation = Bound::new(
                py,
                PyClassInitializer::from(crate::expressions::PyExpression {
                    kind: crate::expressions::ExpressionKind::Operation(Some(native)),
                })
                .add_subclass(PyOperation),
            )?;
            return crate::surface::apply_operations(surface, &[operation.into_any()]);
        }
        let core = core_module(py)?;
        match kind.name {
            "block" => {
                if surface.hasattr("block")? {
                    surface.setattr("block", Self::build_object(slf)?)?;
                    return Ok(());
                }
                let border_type = Self::named(slf, kind, "border_type")?;
                let plain = ["plain", "rounded", "double", "thick"];
                let border_kind = match border_type.extract::<String>() {
                    Ok(name) if plain.contains(&name.as_str()) => name,
                    _ => "plain".to_owned(),
                };
                let style = Self::named(slf, kind, "border_style")?;
                let options = PyDict::new(py);
                if style.is_instance(&core.getattr("Style")?)? {
                    options.set_item("style", style)?;
                }
                let border = core
                    .getattr("Border")?
                    .call((border_kind,), Some(&options))?;
                surface.call_method1("update", (border,))?;
                Ok(())
            }
            "padding" => {
                if !surface.hasattr("block")? {
                    return Ok(());
                }
                let padding = Self::build_object(slf)?;
                let current = surface.getattr("block")?;
                if current.is_instance(&core.getattr("Block")?)? {
                    current.setattr("padding", padding)?;
                } else {
                    let options = PyDict::new(py);
                    options.set_item("padding", padding)?;
                    let block = core.getattr("Block")?.call((), Some(&options))?;
                    surface.setattr("block", block)?;
                }
                Ok(())
            }
            "pixels" => Err(PyTypeError::new_err(
                "fx('pixels') draws a shader through xnano.fx, which understands \
                 color names. Pass pixels=[(column, row, (red, green, blue)), ...] to draw \
                 explicit pixels with a core Customization.",
            )),
            _ => Ok(()),
        }
    }

    fn __getattr__(slf: &Bound<'_, Self>, name: &str) -> PyResult<Py<PyAny>> {
        let py = slf.py();
        if Self::is_direct(slf)
            && let Some(value) = slf.borrow().parameters.bind(py).get_item(name)?
        {
            return Ok(value.unbind());
        }
        let kind = Self::kind_of(slf).map_or("customization", |kind| kind.name);
        Err(pyo3::exceptions::PyAttributeError::new_err(format!(
            "this {kind} customization has no \"{name}\""
        )))
    }

    /// Combine with another operation. Native operations become one native sequence; anything
    /// else is kept as a chain that applies each step in order.
    fn __or__<'py>(
        slf: &Bound<'py, Self>,
        other: &Bound<'py, PyAny>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        let core = core_module(py)?;
        let other = if other.is_instance(&core.getattr("Style")?)? {
            core.getattr("ApplyStyle")?.call1((other,))?
        } else {
            other.clone()
        };
        if !other.is_instance_of::<PyOperation>() {
            return Ok(py.NotImplemented().into_bound(py));
        }
        if let (Some(first), Some(second)) = (Self::native_operation(slf)?, operation_of(&other)?) {
            return crate::expressions::sequence_of(py, vec![first, second]);
        }
        let steps = PyTuple::new(py, [slf.clone().into_any(), other])?;
        core.getattr("OperationChain")?.call1(steps)
    }

    fn __repr__(slf: &Bound<'_, Self>) -> PyResult<String> {
        let kind = Self::kind_of(slf)?;
        let parameters = Self::parameters(slf)?;
        let mut shown = Vec::new();
        for parameter in kind.parameters {
            if let Some(value) = parameters.get_item(parameter.name)? {
                let default = default_value(slf.py(), parameter.default)?;
                if !value.eq(&default)? {
                    shown.push(format!("{}={}", parameter.name, value.repr()?));
                }
            }
        }
        Ok(format!("Customization('{}', {})", kind.name, shown.join(", ")).replace(", )", ")"))
    }
}

/// Operations that cannot become one native sequence, applied one after another.
#[pyclass(
    name = "OperationChain",
    module = "xnano_core._xnano_core",
    extends = PyOperation
)]
pub struct PyOperationChain {
    steps: Vec<Py<PyAny>>,
}

#[pymethods]
impl PyOperationChain {
    #[new]
    #[pyo3(signature = (*steps))]
    fn new(steps: &Bound<'_, PyTuple>) -> PyResult<PyClassInitializer<Self>> {
        let mut flattened = Vec::new();
        for step in steps.iter() {
            if !step.is_instance_of::<PyOperation>() {
                return Err(PyTypeError::new_err(format!(
                    "an OperationChain chains operations, but one step is a {}. Pass operations \
                     such as Fill, Border or fx(...).",
                    step.get_type().name()?
                )));
            }
            if let Ok(chain) = step.cast::<Self>() {
                flattened.extend(
                    chain
                        .borrow()
                        .steps
                        .iter()
                        .map(|step| step.clone_ref(steps.py())),
                );
            } else {
                flattened.push(step.unbind());
            }
        }
        Ok(PyClassInitializer::from(crate::expressions::PyExpression {
            kind: crate::expressions::ExpressionKind::Operation(None),
        })
        .add_subclass(PyOperation)
        .add_subclass(Self { steps: flattened }))
    }

    /// The operations applied in order.
    #[getter]
    fn steps<'py>(&self, py: Python<'py>) -> Bound<'py, PyTuple> {
        PyTuple::new(py, self.steps.iter().map(|step| step.bind(py).clone()))
            .unwrap_or_else(|_| PyTuple::empty(py))
    }

    fn apply_to_surface(&self, py: Python<'_>, surface: &Bound<'_, PyAny>) -> PyResult<()> {
        for step in &self.steps {
            surface.call_method1("update", (step.bind(py),))?;
        }
        Ok(())
    }

    fn __or__<'py>(
        slf: &Bound<'py, Self>,
        other: &Bound<'py, PyAny>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let py = slf.py();
        if !other.is_instance_of::<PyOperation>() {
            return Ok(py.NotImplemented().into_bound(py));
        }
        let steps = PyTuple::new(py, [slf.clone().into_any(), other.clone()])?;
        py.import("xnano_core._xnano_core")?
            .getattr("OperationChain")?
            .call1(steps)
    }

    fn __len__(&self) -> usize {
        self.steps.len()
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyCustomization>()?;
    m.add_class::<PyOperationChain>()
}
