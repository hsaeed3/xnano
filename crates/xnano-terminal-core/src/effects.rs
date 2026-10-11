//! Animated effects: constructors for tachyonfx effects, cell filters and the effect manager.

use std::sync::Arc;

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::PyTuple;
use xnano_terminal_runtime::dynamic::Dynamic;
use xnano_terminal_runtime::effects::{
    EffectNode, EffectRun, FilterSpec, Kind, Placement, RepeatSpec, Timer, interpolation_from_name,
    interpolation_names,
};
use xnano_terminal_runtime::operation::Operation;
use xnano_terminal_runtime::painter::Spec;
use xnano_terminal_runtime::widgets::Shared;
use xnano_terminal_runtime::widgets::style::StyleSpec;

use crate::expressions::PyOperation;
use crate::geometry::PyRectangle;
use crate::operations::operation_initializer;
use crate::shared::{RunningEffect, SharedRunningEffect, lock};
use crate::surface::PySurface;
use crate::widgets::style::style_spec_arg;
use crate::widgets::{dynamic_arg, dynamic_color, dynamic_string, value_object};

fn dynamic_u32(value: &Bound<'_, PyAny>) -> PyResult<Dynamic<u32>> {
    dynamic_arg(value, |value| {
        value.extract::<u32>().map_err(|_| {
            PyValueError::new_err(format!(
                "expected a whole number of milliseconds or steps, zero or more, not {}",
                value
                    .repr()
                    .map_or_else(|_| "?".to_owned(), |text| text.to_string())
            ))
        })
    })
}

fn dynamic_f32(value: &Bound<'_, PyAny>) -> PyResult<Dynamic<f32>> {
    dynamic_arg(value, |value| value.extract::<f32>())
}

fn interpolation_arg(name: Option<&Bound<'_, PyAny>>) -> PyResult<Dynamic<String>> {
    let Some(name) = name.filter(|value| !value.is_none()) else {
        return Ok(Dynamic::Fixed("linear".to_owned()));
    };
    let setting = dynamic_string(name)?;
    if let Dynamic::Fixed(text) = &setting
        && interpolation_from_name(text).is_none()
    {
        return Err(PyValueError::new_err(format!(
            "\"{text}\" is not an interpolation; use one of {}",
            interpolation_names()
        )));
    }
    Ok(setting)
}

fn timer_arg(
    duration_milliseconds: &Bound<'_, PyAny>,
    interpolation: Option<&Bound<'_, PyAny>>,
) -> PyResult<Timer> {
    let duration = dynamic_u32(duration_milliseconds)?;
    if let Dynamic::Fixed(0) = duration {
        return Err(PyValueError::new_err(
            "an effect duration must be a positive number of milliseconds, not 0",
        ));
    }
    Ok(Timer::new(duration, interpolation_arg(interpolation)?))
}

fn optional<T>(
    value: Option<&Bound<'_, PyAny>>,
    convert: impl Fn(&Bound<'_, PyAny>) -> PyResult<T>,
) -> PyResult<Option<T>> {
    value
        .filter(|value| !value.is_none())
        .map(convert)
        .transpose()
}

/// An effect: what it does, how long it takes and how it is restricted.
#[pyclass(name = "Effect", module = "xnano._xnano_core", extends = PyOperation, subclass)]
pub struct PyEffect {
    pub spec: Shared<EffectNode>,
}

fn new_effect(py: Python<'_>, node: EffectNode) -> PyResult<Py<PyEffect>> {
    effect_around(py, Spec::new(node))
}

fn effect_around(py: Python<'_>, spec: Shared<EffectNode>) -> PyResult<Py<PyEffect>> {
    Py::new(
        py,
        operation_initializer(Operation::Effect(Arc::clone(&spec))).add_subclass(PyEffect { spec }),
    )
}

fn spec_of(value: &Bound<'_, PyAny>) -> PyResult<Shared<EffectNode>> {
    value
        .extract::<PyRef<'_, PyEffect>>()
        .map(|effect| Arc::clone(&effect.spec))
        .map_err(|_| {
            PyTypeError::new_err(
                "expected an Effect; build one with Effect.fade_to(...) and its siblings",
            )
        })
}

fn specs_of(values: &Bound<'_, PyAny>) -> PyResult<Vec<Shared<EffectNode>>> {
    let mut specs = Vec::new();
    for item in values.try_iter()? {
        specs.push(spec_of(&item?)?);
    }
    if specs.is_empty() {
        return Err(PyValueError::new_err(
            "a sequence or parallel effect needs at least one effect",
        ));
    }
    Ok(specs)
}

fn with_node(
    slf: &Bound<'_, PyEffect>,
    change: impl FnOnce(&mut EffectNode),
) -> PyResult<Py<PyEffect>> {
    let mut node = slf.borrow().spec.read().clone();
    change(&mut node);
    new_effect(slf.py(), node)
}

fn wrap(
    slf: &Bound<'_, PyEffect>,
    kind: impl FnOnce(Shared<EffectNode>) -> Kind,
) -> PyResult<Py<PyEffect>> {
    new_effect(
        slf.py(),
        EffectNode::new(kind(Arc::clone(&slf.borrow().spec))),
    )
}

fn triple(value: &Bound<'_, PyAny>) -> PyResult<[Dynamic<f32>; 3]> {
    let items = value.cast::<PyTuple>().map_err(|_| {
        PyTypeError::new_err("an hsl shift is a (hue, saturation, lightness) tuple")
    })?;
    if items.len() != 3 {
        return Err(PyValueError::new_err(
            "an hsl shift is three numbers: (hue degrees, saturation percent, lightness percent)",
        ));
    }
    Ok([
        dynamic_f32(&items.get_item(0)?)?,
        dynamic_f32(&items.get_item(1)?)?,
        dynamic_f32(&items.get_item(2)?)?,
    ])
}

#[pymethods]
impl PyEffect {
    #[staticmethod]
    #[pyo3(signature = (direction = None, *, gradient_length = None, randomness = None, color = None, duration_milliseconds = None, interpolation = None))]
    fn sweep_in(
        py: Python<'_>,
        direction: Option<&Bound<'_, PyAny>>,
        gradient_length: Option<&Bound<'_, PyAny>>,
        randomness: Option<&Bound<'_, PyAny>>,
        color: Option<&Bound<'_, PyAny>>,
        duration_milliseconds: Option<&Bound<'_, PyAny>>,
        interpolation: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Py<PyEffect>> {
        let default = 500_u32.into_pyobject(py)?.into_any();
        new_effect(
            py,
            EffectNode::new(Kind::Spatial {
                name: "sweep_in".to_owned(),
                direction: optional(direction, dynamic_string)?
                    .unwrap_or(Dynamic::Fixed("left_to_right".to_owned())),
                gradient_length: optional(gradient_length, crate::widgets::dynamic_u16)?
                    .unwrap_or(Dynamic::Fixed(10)),
                randomness: optional(randomness, crate::widgets::dynamic_u16)?
                    .unwrap_or(Dynamic::Fixed(0)),
                color: optional(color, dynamic_color)?
                    .unwrap_or(Dynamic::Fixed(ratatui_core::style::Color::Black)),
                timer: timer_arg(duration_milliseconds.unwrap_or(&default), interpolation)?,
            }),
        )
    }
    #[staticmethod]
    #[pyo3(signature = (direction = None, *, gradient_length = None, randomness = None, color = None, duration_milliseconds = None, interpolation = None))]
    fn sweep_out(
        py: Python<'_>,
        direction: Option<&Bound<'_, PyAny>>,
        gradient_length: Option<&Bound<'_, PyAny>>,
        randomness: Option<&Bound<'_, PyAny>>,
        color: Option<&Bound<'_, PyAny>>,
        duration_milliseconds: Option<&Bound<'_, PyAny>>,
        interpolation: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Py<PyEffect>> {
        let default = 500_u32.into_pyobject(py)?.into_any();
        new_effect(
            py,
            EffectNode::new(Kind::Spatial {
                name: "sweep_out".to_owned(),
                direction: optional(direction, dynamic_string)?
                    .unwrap_or(Dynamic::Fixed("left_to_right".to_owned())),
                gradient_length: optional(gradient_length, crate::widgets::dynamic_u16)?
                    .unwrap_or(Dynamic::Fixed(10)),
                randomness: optional(randomness, crate::widgets::dynamic_u16)?
                    .unwrap_or(Dynamic::Fixed(0)),
                color: optional(color, dynamic_color)?
                    .unwrap_or(Dynamic::Fixed(ratatui_core::style::Color::Black)),
                timer: timer_arg(duration_milliseconds.unwrap_or(&default), interpolation)?,
            }),
        )
    }
    #[staticmethod]
    #[pyo3(signature = (direction = None, *, gradient_length = None, randomness = None, color = None, duration_milliseconds = None, interpolation = None))]
    fn slide_in(
        py: Python<'_>,
        direction: Option<&Bound<'_, PyAny>>,
        gradient_length: Option<&Bound<'_, PyAny>>,
        randomness: Option<&Bound<'_, PyAny>>,
        color: Option<&Bound<'_, PyAny>>,
        duration_milliseconds: Option<&Bound<'_, PyAny>>,
        interpolation: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Py<PyEffect>> {
        let default = 500_u32.into_pyobject(py)?.into_any();
        new_effect(
            py,
            EffectNode::new(Kind::Spatial {
                name: "slide_in".to_owned(),
                direction: optional(direction, dynamic_string)?
                    .unwrap_or(Dynamic::Fixed("left_to_right".to_owned())),
                gradient_length: optional(gradient_length, crate::widgets::dynamic_u16)?
                    .unwrap_or(Dynamic::Fixed(10)),
                randomness: optional(randomness, crate::widgets::dynamic_u16)?
                    .unwrap_or(Dynamic::Fixed(0)),
                color: optional(color, dynamic_color)?
                    .unwrap_or(Dynamic::Fixed(ratatui_core::style::Color::Black)),
                timer: timer_arg(duration_milliseconds.unwrap_or(&default), interpolation)?,
            }),
        )
    }
    #[staticmethod]
    #[pyo3(signature = (direction = None, *, gradient_length = None, randomness = None, color = None, duration_milliseconds = None, interpolation = None))]
    fn slide_out(
        py: Python<'_>,
        direction: Option<&Bound<'_, PyAny>>,
        gradient_length: Option<&Bound<'_, PyAny>>,
        randomness: Option<&Bound<'_, PyAny>>,
        color: Option<&Bound<'_, PyAny>>,
        duration_milliseconds: Option<&Bound<'_, PyAny>>,
        interpolation: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Py<PyEffect>> {
        let default = 500_u32.into_pyobject(py)?.into_any();
        new_effect(
            py,
            EffectNode::new(Kind::Spatial {
                name: "slide_out".to_owned(),
                direction: optional(direction, dynamic_string)?
                    .unwrap_or(Dynamic::Fixed("left_to_right".to_owned())),
                gradient_length: optional(gradient_length, crate::widgets::dynamic_u16)?
                    .unwrap_or(Dynamic::Fixed(10)),
                randomness: optional(randomness, crate::widgets::dynamic_u16)?
                    .unwrap_or(Dynamic::Fixed(0)),
                color: optional(color, dynamic_color)?
                    .unwrap_or(Dynamic::Fixed(ratatui_core::style::Color::Black)),
                timer: timer_arg(duration_milliseconds.unwrap_or(&default), interpolation)?,
            }),
        )
    }
    #[getter]
    fn direction<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let value: Dynamic<String> = match &self.spec.read().kind {
            Kind::Spatial { direction, .. } => direction.clone(),
            _ => {
                return Err(PyValueError::new_err(
                    "direction is a setting of sweep and slide effects",
                ));
            }
        };
        setting(py, &value, |py, value| {
            Ok(value.into_pyobject(py)?.into_any())
        })
    }
    #[setter]
    fn set_direction(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let setting = dynamic_string(value)?;
        self.spec.edit(|node| match &mut node.kind {
            Kind::Spatial { direction, .. } => {
                *direction = setting;
                Ok(())
            }
            _ => Err(PyValueError::new_err(
                "direction is a setting of sweep and slide effects",
            )),
        })
    }
    #[getter]
    fn gradient_length<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let value: Dynamic<u16> = match &self.spec.read().kind {
            Kind::Spatial {
                gradient_length, ..
            } => gradient_length.clone(),
            _ => {
                return Err(PyValueError::new_err(
                    "gradient_length is a setting of sweep and slide effects",
                ));
            }
        };
        setting(py, &value, |py, value| {
            Ok(value.into_pyobject(py)?.into_any())
        })
    }
    #[setter]
    fn set_gradient_length(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let setting = crate::widgets::dynamic_u16(value)?;
        self.spec.edit(|node| match &mut node.kind {
            Kind::Spatial {
                gradient_length, ..
            } => {
                *gradient_length = setting;
                Ok(())
            }
            _ => Err(PyValueError::new_err(
                "gradient_length is a setting of sweep and slide effects",
            )),
        })
    }
    #[getter]
    fn randomness<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let value: Dynamic<u16> = match &self.spec.read().kind {
            Kind::Spatial { randomness, .. } => randomness.clone(),
            _ => {
                return Err(PyValueError::new_err(
                    "randomness is a setting of sweep and slide effects",
                ));
            }
        };
        setting(py, &value, |py, value| {
            Ok(value.into_pyobject(py)?.into_any())
        })
    }
    #[setter]
    fn set_randomness(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let setting = crate::widgets::dynamic_u16(value)?;
        self.spec.edit(|node| match &mut node.kind {
            Kind::Spatial { randomness, .. } => {
                *randomness = setting;
                Ok(())
            }
            _ => Err(PyValueError::new_err(
                "randomness is a setting of sweep and slide effects",
            )),
        })
    }
    #[getter]
    fn color<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let value: Dynamic<ratatui_core::style::Color> = match &self.spec.read().kind {
            Kind::Spatial { color, .. } => color.clone(),
            _ => {
                return Err(PyValueError::new_err(
                    "color is a setting of sweep and slide effects",
                ));
            }
        };
        setting(py, &value, |py, value| {
            Ok(Py::new(py, crate::style::PyColor { inner: *value })?
                .into_bound(py)
                .into_any())
        })
    }
    #[setter]
    fn set_color(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let setting = dynamic_color(value)?;
        self.spec.edit(|node| match &mut node.kind {
            Kind::Spatial { color, .. } => {
                *color = setting;
                Ok(())
            }
            _ => Err(PyValueError::new_err(
                "color is a setting of sweep and slide effects",
            )),
        })
    }
    #[new]
    #[pyo3(signature = (*, duration_milliseconds = None, interpolation = None, key = None))]
    fn new(
        py: Python<'_>,
        duration_milliseconds: Option<&Bound<'_, PyAny>>,
        interpolation: Option<&Bound<'_, PyAny>>,
        key: Option<String>,
    ) -> PyResult<PyClassInitializer<Self>> {
        let default = 500_u32.into_pyobject(py)?.into_any();
        let mut node = EffectNode::new(Kind::Fade {
            foreground: None,
            background: None,
            is_from: false,
            timer: timer_arg(duration_milliseconds.unwrap_or(&default), interpolation)?,
        });
        node.key = key;
        Ok(effect_initializer(node))
    }
    #[pyo3(signature = (*, times = None))]
    fn repeat(slf: &Bound<'_, Self>, times: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyEffect>> {
        Self::repeated(slf, times, None)
    }

    #[staticmethod]
    #[pyo3(signature = (foreground = None, background = None, *, duration_milliseconds = None, interpolation = None))]
    fn fade_to(
        py: Python<'_>,
        foreground: Option<&Bound<'_, PyAny>>,
        background: Option<&Bound<'_, PyAny>>,
        duration_milliseconds: Option<&Bound<'_, PyAny>>,
        interpolation: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Py<PyEffect>> {
        let default = 500_u32.into_pyobject(py)?.into_any();
        let timer = timer_arg(duration_milliseconds.unwrap_or(&default), interpolation)?;
        let kind = Kind::Fade {
            foreground: optional(foreground, dynamic_color)?,
            background: optional(background, dynamic_color)?,
            is_from: false,
            timer,
        };
        new_effect(py, EffectNode::new(kind))
    }
    #[staticmethod]
    #[pyo3(signature = (foreground = None, background = None, *, duration_milliseconds = None, interpolation = None))]
    fn fade_from(
        py: Python<'_>,
        foreground: Option<&Bound<'_, PyAny>>,
        background: Option<&Bound<'_, PyAny>>,
        duration_milliseconds: Option<&Bound<'_, PyAny>>,
        interpolation: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Py<PyEffect>> {
        let default = 500_u32.into_pyobject(py)?.into_any();
        let timer = timer_arg(duration_milliseconds.unwrap_or(&default), interpolation)?;
        let kind = Kind::Fade {
            foreground: optional(foreground, dynamic_color)?,
            background: optional(background, dynamic_color)?,
            is_from: true,
            timer,
        };
        new_effect(py, EffectNode::new(kind))
    }
    #[staticmethod]
    #[pyo3(signature = (foreground = None, background = None, *, duration_milliseconds = None, interpolation = None))]
    fn paint(
        py: Python<'_>,
        foreground: Option<&Bound<'_, PyAny>>,
        background: Option<&Bound<'_, PyAny>>,
        duration_milliseconds: Option<&Bound<'_, PyAny>>,
        interpolation: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Py<PyEffect>> {
        let default = 500_u32.into_pyobject(py)?.into_any();
        let timer = timer_arg(duration_milliseconds.unwrap_or(&default), interpolation)?;
        let kind = Kind::Paint {
            foreground: optional(foreground, dynamic_color)?,
            background: optional(background, dynamic_color)?,

            timer,
        };
        new_effect(py, EffectNode::new(kind))
    }
    #[staticmethod]
    #[pyo3(signature = (foreground = None, background = None, *, duration_milliseconds = None, interpolation = None))]
    fn saturate(
        py: Python<'_>,
        foreground: Option<&Bound<'_, PyAny>>,
        background: Option<&Bound<'_, PyAny>>,
        duration_milliseconds: Option<&Bound<'_, PyAny>>,
        interpolation: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Py<PyEffect>> {
        let default = 500_u32.into_pyobject(py)?.into_any();
        new_effect(
            py,
            EffectNode::new(Kind::Adjust {
                adjustment: xnano_terminal_runtime::effects::Adjustment::Saturate,
                foreground: optional(foreground, dynamic_f32)?,
                background: optional(background, dynamic_f32)?,
                timer: timer_arg(duration_milliseconds.unwrap_or(&default), interpolation)?,
            }),
        )
    }
    #[staticmethod]
    #[pyo3(signature = (foreground = None, background = None, *, duration_milliseconds = None, interpolation = None))]
    fn lighten(
        py: Python<'_>,
        foreground: Option<&Bound<'_, PyAny>>,
        background: Option<&Bound<'_, PyAny>>,
        duration_milliseconds: Option<&Bound<'_, PyAny>>,
        interpolation: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Py<PyEffect>> {
        let default = 500_u32.into_pyobject(py)?.into_any();
        new_effect(
            py,
            EffectNode::new(Kind::Adjust {
                adjustment: xnano_terminal_runtime::effects::Adjustment::Lighten,
                foreground: optional(foreground, dynamic_f32)?,
                background: optional(background, dynamic_f32)?,
                timer: timer_arg(duration_milliseconds.unwrap_or(&default), interpolation)?,
            }),
        )
    }
    #[staticmethod]
    #[pyo3(signature = (foreground = None, background = None, *, duration_milliseconds = None, interpolation = None))]
    fn darken(
        py: Python<'_>,
        foreground: Option<&Bound<'_, PyAny>>,
        background: Option<&Bound<'_, PyAny>>,
        duration_milliseconds: Option<&Bound<'_, PyAny>>,
        interpolation: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Py<PyEffect>> {
        let default = 500_u32.into_pyobject(py)?.into_any();
        new_effect(
            py,
            EffectNode::new(Kind::Adjust {
                adjustment: xnano_terminal_runtime::effects::Adjustment::Darken,
                foreground: optional(foreground, dynamic_f32)?,
                background: optional(background, dynamic_f32)?,
                timer: timer_arg(duration_milliseconds.unwrap_or(&default), interpolation)?,
            }),
        )
    }

    #[staticmethod]
    #[pyo3(signature = (foreground = None, background = None, *, duration_milliseconds = None, interpolation = None))]
    fn hsl_shift(
        py: Python<'_>,
        foreground: Option<&Bound<'_, PyAny>>,
        background: Option<&Bound<'_, PyAny>>,
        duration_milliseconds: Option<&Bound<'_, PyAny>>,
        interpolation: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Py<PyEffect>> {
        let default = 500_u32.into_pyobject(py)?.into_any();
        new_effect(
            py,
            EffectNode::new(Kind::HslShift {
                foreground: optional(foreground, triple)?,
                background: optional(background, triple)?,
                timer: timer_arg(duration_milliseconds.unwrap_or(&default), interpolation)?,
            }),
        )
    }

    #[staticmethod]
    #[pyo3(signature = (*, style = None, duration_milliseconds = None, interpolation = None))]
    fn dissolve(
        py: Python<'_>,
        style: Option<&Bound<'_, PyAny>>,
        duration_milliseconds: Option<&Bound<'_, PyAny>>,
        interpolation: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Py<PyEffect>> {
        dissolve_effect(py, false, style, duration_milliseconds, interpolation)
    }

    #[staticmethod]
    #[pyo3(signature = (*, style = None, duration_milliseconds = None, interpolation = None))]
    fn coalesce(
        py: Python<'_>,
        style: Option<&Bound<'_, PyAny>>,
        duration_milliseconds: Option<&Bound<'_, PyAny>>,
        interpolation: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Py<PyEffect>> {
        dissolve_effect(py, true, style, duration_milliseconds, interpolation)
    }

    #[staticmethod]
    #[pyo3(signature = (*, ratio = None, duration_milliseconds = None, start_delay_milliseconds = (0, 100),
        action_milliseconds = (40, 250)))]
    fn glitch(
        py: Python<'_>,
        ratio: Option<&Bound<'_, PyAny>>,
        duration_milliseconds: Option<&Bound<'_, PyAny>>,
        start_delay_milliseconds: (u32, u32),
        action_milliseconds: (u32, u32),
    ) -> PyResult<Py<PyEffect>> {
        let ratio = match ratio.filter(|value| !value.is_none()) {
            Some(value) => dynamic_f32(value)?,
            None => Dynamic::Fixed(0.1),
        };
        if let Dynamic::Fixed(fixed) = ratio
            && !(0.0..=1.0).contains(&fixed)
        {
            return Err(PyValueError::new_err(format!(
                "a glitch ratio is a fraction from 0.0 to 1.0, not {fixed}"
            )));
        }
        let duration = match duration_milliseconds.filter(|value| !value.is_none()) {
            Some(value) => dynamic_u32(value)?,
            None => Dynamic::Fixed(500),
        };
        new_effect(
            py,
            EffectNode::new(Kind::Glitch {
                cell_ratio: ratio,
                start_delay_milliseconds: [
                    Dynamic::Fixed(start_delay_milliseconds.0),
                    Dynamic::Fixed(start_delay_milliseconds.1),
                ],
                action_milliseconds: [
                    Dynamic::Fixed(action_milliseconds.0),
                    Dynamic::Fixed(action_milliseconds.1),
                ],
                duration_milliseconds: duration,
            }),
        )
    }

    #[staticmethod]
    #[pyo3(signature = (duration_milliseconds, *, interpolation = None))]
    fn sleep(
        py: Python<'_>,
        duration_milliseconds: &Bound<'_, PyAny>,
        interpolation: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Py<PyEffect>> {
        new_effect(
            py,
            EffectNode::new(Kind::Sleep {
                timer: timer_arg(duration_milliseconds, interpolation)?,
            }),
        )
    }

    #[staticmethod]
    fn term256_colors(py: Python<'_>) -> PyResult<Py<PyEffect>> {
        new_effect(py, EffectNode::new(Kind::Term256Colors))
    }

    #[staticmethod]
    fn consume_tick(py: Python<'_>) -> PyResult<Py<PyEffect>> {
        new_effect(py, EffectNode::new(Kind::ConsumeTick))
    }

    #[staticmethod]
    fn sequence(py: Python<'_>, effects: &Bound<'_, PyAny>) -> PyResult<Py<PyEffect>> {
        new_effect(py, EffectNode::new(Kind::Sequence(specs_of(effects)?)))
    }

    #[staticmethod]
    fn parallel(py: Python<'_>, effects: &Bound<'_, PyAny>) -> PyResult<Py<PyEffect>> {
        new_effect(py, EffectNode::new(Kind::Parallel(specs_of(effects)?)))
    }

    /// Run after `other` in a sequence.
    fn then(slf: &Bound<'_, Self>, other: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        if let Ok(spec) = spec_of(other) {
            let children = vec![Arc::clone(&slf.borrow().spec), spec];
            return new_effect(slf.py(), EffectNode::new(Kind::Sequence(children)))
                .map(Py::into_any);
        }
        crate::expressions::PyOperation::then(slf.as_super(), other).map(Py::into_any)
    }

    /// Run at the same time as `other`.
    fn alongside(slf: &Bound<'_, Self>, other: &Bound<'_, PyAny>) -> PyResult<Py<PyEffect>> {
        let children = vec![Arc::clone(&slf.borrow().spec), spec_of(other)?];
        new_effect(slf.py(), EffectNode::new(Kind::Parallel(children)))
    }

    /// Repeat `times` times, or forever, or for `milliseconds`.
    #[pyo3(signature = (times = None, *, milliseconds = None))]
    fn repeated(
        slf: &Bound<'_, Self>,
        times: Option<&Bound<'_, PyAny>>,
        milliseconds: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Py<PyEffect>> {
        let repeat = match (
            optional(times, dynamic_u32)?,
            optional(milliseconds, dynamic_u32)?,
        ) {
            (Some(_), Some(_)) => {
                return Err(PyValueError::new_err(
                    "give either times or milliseconds to repeated(), not both",
                ));
            }
            (Some(times), None) => RepeatSpec::Times(times),
            (None, Some(milliseconds)) => RepeatSpec::Milliseconds(milliseconds),
            (None, None) => RepeatSpec::Forever,
        };
        wrap(slf, |child| Kind::Repeat { child, repeat })
    }

    fn ping_pong(slf: &Bound<'_, Self>) -> PyResult<Py<PyEffect>> {
        wrap(slf, Kind::PingPong)
    }

    fn delayed(slf: &Bound<'_, Self>, milliseconds: &Bound<'_, PyAny>) -> PyResult<Py<PyEffect>> {
        let milliseconds = dynamic_u32(milliseconds)?;
        wrap(slf, |child| Kind::Delay {
            child,
            milliseconds,
        })
    }

    fn prolong_start(
        slf: &Bound<'_, Self>,
        milliseconds: &Bound<'_, PyAny>,
    ) -> PyResult<Py<PyEffect>> {
        let milliseconds = dynamic_u32(milliseconds)?;
        wrap(slf, |child| Kind::ProlongStart {
            child,
            milliseconds,
        })
    }

    fn prolong_end(
        slf: &Bound<'_, Self>,
        milliseconds: &Bound<'_, PyAny>,
    ) -> PyResult<Py<PyEffect>> {
        let milliseconds = dynamic_u32(milliseconds)?;
        wrap(slf, |child| Kind::ProlongEnd {
            child,
            milliseconds,
        })
    }

    #[pyo3(signature = (alpha, *, should_set_raw_alpha = false))]
    fn freeze_at(
        slf: &Bound<'_, Self>,
        alpha: &Bound<'_, PyAny>,
        should_set_raw_alpha: bool,
    ) -> PyResult<Py<PyEffect>> {
        let alpha = dynamic_f32(alpha)?;
        wrap(slf, |child| Kind::FreezeAt {
            child,
            alpha,
            should_set_raw_alpha,
        })
    }

    fn remap_alpha(
        slf: &Bound<'_, Self>,
        start: &Bound<'_, PyAny>,
        end: &Bound<'_, PyAny>,
    ) -> PyResult<Py<PyEffect>> {
        let (start, end) = (dynamic_f32(start)?, dynamic_f32(end)?);
        wrap(slf, |child| Kind::RemapAlpha { child, start, end })
    }

    fn with_duration(
        slf: &Bound<'_, Self>,
        milliseconds: &Bound<'_, PyAny>,
    ) -> PyResult<Py<PyEffect>> {
        let milliseconds = dynamic_u32(milliseconds)?;
        wrap(slf, |child| Kind::WithDuration {
            child,
            milliseconds,
        })
    }

    fn timed_never_complete(
        slf: &Bound<'_, Self>,
        milliseconds: &Bound<'_, PyAny>,
    ) -> PyResult<Py<PyEffect>> {
        let milliseconds = dynamic_u32(milliseconds)?;
        wrap(slf, |child| Kind::TimedNeverComplete {
            child,
            milliseconds,
        })
    }

    fn run_once(slf: &Bound<'_, Self>) -> PyResult<Py<PyEffect>> {
        wrap(slf, Kind::RunOnce)
    }

    fn never_complete(slf: &Bound<'_, Self>) -> PyResult<Py<PyEffect>> {
        wrap(slf, Kind::NeverComplete)
    }

    /// A copy that only touches the cells `filter` selects.
    fn with_filter(slf: &Bound<'_, Self>, filter: &PyCellFilter) -> PyResult<Py<PyEffect>> {
        let filter = filter.spec.clone();
        with_node(slf, |node| node.filter = Some(filter))
    }

    /// A copy limited to a rectangle relative to its target.
    fn with_area(slf: &Bound<'_, Self>, area: &PyRectangle) -> PyResult<Py<PyEffect>> {
        let area = area.inner;
        with_node(slf, |node| node.area = Some(area))
    }

    /// A copy that runs backwards.
    #[pyo3(signature = (is_reversed = None))]
    fn reversed(
        slf: &Bound<'_, Self>,
        is_reversed: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Py<PyEffect>> {
        let flag = match is_reversed.filter(|value| !value.is_none()) {
            Some(value) => crate::widgets::dynamic_bool(value)?,
            None => Dynamic::Fixed(true),
        };
        with_node(slf, |node| node.is_reversed = flag)
    }

    fn with_interpolation(
        slf: &Bound<'_, Self>,
        interpolation: &Bound<'_, PyAny>,
    ) -> PyResult<Py<PyEffect>> {
        let interpolation = interpolation_arg(Some(interpolation))?;
        if slf.borrow().spec.read().kind.timer().is_none() {
            return Err(PyValueError::new_err(
                "this effect has no timer of its own; set the interpolation on the effects inside it",
            ));
        }
        with_node(slf, |node| {
            if let Some(timer) = node.kind.timer_mut() {
                timer.interpolation = interpolation;
            }
        })
    }

    fn with_seed(slf: &Bound<'_, Self>, seed: u32) -> PyResult<Py<PyEffect>> {
        with_node(slf, |node| node.seed = Some(seed))
    }

    fn with_color_space(slf: &Bound<'_, Self>, color_space: &str) -> PyResult<Py<PyEffect>> {
        if xnano_terminal_runtime::effects::color_space_from_name(color_space).is_none() {
            return Err(PyValueError::new_err(format!(
                "\"{color_space}\" is not a color space; use \"rgb\", \"hsl\" or \"hsv\""
            )));
        }
        let color_space = color_space.to_owned();
        with_node(slf, |node| node.color_space = Some(color_space))
    }

    /// A copy that runs under `key`, replacing any running effect with the same key.
    fn with_key(slf: &Bound<'_, Self>, key: String) -> PyResult<Py<PyEffect>> {
        with_node(slf, |node| node.key = Some(key))
    }

    #[getter]
    fn kind(&self) -> &'static str {
        self.spec.read().kind.name()
    }

    #[getter]
    fn key(&self) -> Option<String> {
        self.spec.read().key.clone()
    }

    #[setter]
    fn set_key(&self, key: Option<String>) {
        self.spec.edit(|node| node.key = key);
    }

    #[getter]
    fn duration_milliseconds<'py>(&self, py: Python<'py>) -> PyResult<Option<Bound<'py, PyAny>>> {
        let duration = self
            .spec
            .read()
            .kind
            .timer()
            .map(|timer| timer.duration_milliseconds.clone());
        duration
            .map(|duration| setting(py, &duration, |py, ms| Ok(ms.into_pyobject(py)?.into_any())))
            .transpose()
    }

    #[setter]
    fn set_duration_milliseconds(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let duration = dynamic_u32(value)?;
        let mut applied = false;
        self.spec.edit(|node| {
            if let Some(timer) = node.kind.timer_mut() {
                timer.duration_milliseconds = duration;
                applied = true;
            }
        });
        applied.then_some(()).ok_or_else(|| {
            PyValueError::new_err(
                "this effect has no duration of its own; set it on the effects inside it",
            )
        })
    }

    #[getter]
    fn interpolation<'py>(&self, py: Python<'py>) -> PyResult<Option<Bound<'py, PyAny>>> {
        let value = self
            .spec
            .read()
            .kind
            .timer()
            .map(|timer| timer.interpolation.clone());
        value
            .map(|value| {
                setting(py, &value, |py, name| {
                    Ok(pyo3::types::PyString::new(py, name).into_any())
                })
            })
            .transpose()
    }

    #[setter]
    fn set_interpolation(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let interpolation = interpolation_arg(Some(value))?;
        let mut applied = false;
        self.spec.edit(|node| {
            if let Some(timer) = node.kind.timer_mut() {
                timer.interpolation = interpolation;
                applied = true;
            }
        });
        applied.then_some(()).ok_or_else(|| {
            PyValueError::new_err(
                "this effect has no interpolation of its own; set it on the effects inside it",
            )
        })
    }

    #[getter]
    fn foreground<'py>(&self, py: Python<'py>) -> PyResult<Option<Bound<'py, PyAny>>> {
        color_of(py, &self.spec.read().kind, true)
    }

    #[setter]
    fn set_foreground(&self, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        set_color(&self.spec, true, value)
    }

    #[getter]
    fn background<'py>(&self, py: Python<'py>) -> PyResult<Option<Bound<'py, PyAny>>> {
        color_of(py, &self.spec.read().kind, false)
    }

    #[setter]
    fn set_background(&self, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        set_color(&self.spec, false, value)
    }

    #[getter]
    fn children(&self, py: Python<'_>) -> PyResult<Vec<Py<PyEffect>>> {
        let children = self.spec.read().kind.children();
        children
            .into_iter()
            .map(|child| effect_around(py, child))
            .collect()
    }

    fn copy(&self, py: Python<'_>) -> PyResult<Py<PyEffect>> {
        new_effect(py, self.spec.read().clone())
    }

    fn __copy__(&self, py: Python<'_>) -> PyResult<Py<PyEffect>> {
        self.copy(py)
    }

    fn __deepcopy__(&self, py: Python<'_>, _memo: &Bound<'_, PyAny>) -> PyResult<Py<PyEffect>> {
        self.copy(py)
    }

    fn __eq__(&self, other: &Bound<'_, PyAny>) -> bool {
        other.extract::<PyRef<'_, PyEffect>>().is_ok_and(|other| {
            format!("{:?}", other.spec.read()) == format!("{:?}", self.spec.read())
        })
    }

    #[classattr]
    const __hash__: Option<Py<PyAny>> = None;

    fn __repr__(&self) -> String {
        let node = self.spec.read();
        match node
            .kind
            .timer()
            .map(|timer| timer.duration_milliseconds.clone())
        {
            Some(Dynamic::Fixed(ms)) => format!("Effect({}, {ms} ms)", node.kind.name()),
            _ => format!("Effect({})", node.kind.name()),
        }
    }
}

fn setting<'py, T: Clone>(
    py: Python<'py>,
    value: &Dynamic<T>,
    convert: impl Fn(Python<'py>, &T) -> PyResult<Bound<'py, PyAny>>,
) -> PyResult<Bound<'py, PyAny>> {
    match value {
        Dynamic::Fixed(fixed) => convert(py, fixed),
        Dynamic::Bound(expr) => value_object(py, Arc::clone(expr)),
    }
}

fn color_of<'py>(
    py: Python<'py>,
    kind: &Kind,
    is_foreground: bool,
) -> PyResult<Option<Bound<'py, PyAny>>> {
    let color = match kind {
        Kind::Fade {
            foreground,
            background,
            ..
        }
        | Kind::Paint {
            foreground,
            background,
            ..
        } => if is_foreground {
            foreground
        } else {
            background
        }
        .clone(),
        _ => None,
    };
    color
        .map(|color| {
            setting(py, &color, |py, color| {
                Ok(Py::new(py, crate::style::PyColor { inner: *color })?
                    .into_bound(py)
                    .into_any())
            })
        })
        .transpose()
}

fn set_color(
    spec: &Shared<EffectNode>,
    is_foreground: bool,
    value: Option<&Bound<'_, PyAny>>,
) -> PyResult<()> {
    let color = optional(value, dynamic_color)?;
    let mut applied = false;
    spec.edit(|node| {
        if let Kind::Fade {
            foreground,
            background,
            ..
        }
        | Kind::Paint {
            foreground,
            background,
            ..
        } = &mut node.kind
        {
            if is_foreground {
                *foreground = color;
            } else {
                *background = color;
            }
            applied = true;
        }
    });
    applied.then_some(()).ok_or_else(|| {
        PyValueError::new_err("only fade and paint effects have a foreground and background color")
    })
}

fn dissolve_effect(
    py: Python<'_>,
    is_coalesce: bool,
    style: Option<&Bound<'_, PyAny>>,
    duration_milliseconds: Option<&Bound<'_, PyAny>>,
    interpolation: Option<&Bound<'_, PyAny>>,
) -> PyResult<Py<PyEffect>> {
    let default = 500_u32.into_pyobject(py)?.into_any();
    let style: Option<StyleSpec> = style
        .filter(|value| !value.is_none())
        .map(|value| style_spec_arg(Some(value)))
        .transpose()?;
    new_effect(
        py,
        EffectNode::new(Kind::Dissolve {
            is_coalesce,
            style,
            timer: timer_arg(duration_milliseconds.unwrap_or(&default), interpolation)?,
        }),
    )
}

// ---------------------------------------------------------------------------------------
// Cell filters

/// Which cells of an effect's area it touches.
#[pyclass(
    name = "CellFilter",
    module = "xnano._xnano_core",
    frozen,
    from_py_object
)]
#[derive(Clone)]
pub struct PyCellFilter {
    pub spec: FilterSpec,
}

fn filters_of(items: &Bound<'_, PyTuple>) -> PyResult<Vec<FilterSpec>> {
    items
        .iter()
        .map(|item| {
            item.extract::<PyCellFilter>()
                .map(|filter| filter.spec)
                .map_err(|_| PyTypeError::new_err("expected CellFilter values"))
        })
        .collect()
}

#[pymethods]
impl PyCellFilter {
    #[staticmethod]
    fn all() -> Self {
        Self {
            spec: FilterSpec::All,
        }
    }

    #[staticmethod]
    fn text() -> Self {
        Self {
            spec: FilterSpec::Text,
        }
    }

    #[staticmethod]
    fn non_empty() -> Self {
        Self {
            spec: FilterSpec::NonEmpty,
        }
    }

    #[staticmethod]
    fn background() -> Self {
        Self {
            spec: FilterSpec::Background,
        }
    }
    #[staticmethod]
    fn background_only() -> Self {
        Self {
            spec: FilterSpec::BackgroundOnly,
        }
    }

    #[staticmethod]
    fn foreground_color(color: &Bound<'_, PyAny>) -> PyResult<Self> {
        Ok(Self {
            spec: FilterSpec::ForegroundColor(crate::style::color_arg(color)?),
        })
    }

    #[staticmethod]
    fn background_color(color: &Bound<'_, PyAny>) -> PyResult<Self> {
        Ok(Self {
            spec: FilterSpec::BackgroundColor(crate::style::color_arg(color)?),
        })
    }

    #[staticmethod]
    fn area(area: &PyRectangle) -> Self {
        Self {
            spec: FilterSpec::Area(area.inner),
        }
    }

    #[staticmethod]
    #[pyo3(signature = (horizontal = 1, vertical = 1))]
    fn inner(horizontal: u16, vertical: u16) -> Self {
        Self {
            spec: FilterSpec::Inner {
                horizontal,
                vertical,
            },
        }
    }

    #[staticmethod]
    #[pyo3(signature = (horizontal = 1, vertical = 1))]
    fn outer(horizontal: u16, vertical: u16) -> Self {
        Self {
            spec: FilterSpec::Outer {
                horizontal,
                vertical,
            },
        }
    }

    #[staticmethod]
    #[pyo3(signature = (*filters))]
    fn all_of(filters: &Bound<'_, PyTuple>) -> PyResult<Self> {
        Ok(Self {
            spec: FilterSpec::AllOf(filters_of(filters)?),
        })
    }

    #[staticmethod]
    #[pyo3(signature = (*filters))]
    fn any_of(filters: &Bound<'_, PyTuple>) -> PyResult<Self> {
        Ok(Self {
            spec: FilterSpec::AnyOf(filters_of(filters)?),
        })
    }

    #[staticmethod]
    #[pyo3(signature = (*filters))]
    fn none_of(filters: &Bound<'_, PyTuple>) -> PyResult<Self> {
        Ok(Self {
            spec: FilterSpec::NoneOf(filters_of(filters)?),
        })
    }

    #[staticmethod]
    fn not_(filter: &Self) -> Self {
        Self {
            spec: FilterSpec::Not(Box::new(filter.spec.clone())),
        }
    }

    fn __and__(&self, other: &Self) -> Self {
        Self {
            spec: FilterSpec::AllOf(vec![self.spec.clone(), other.spec.clone()]),
        }
    }

    fn __or__(&self, other: &Self) -> Self {
        Self {
            spec: FilterSpec::AnyOf(vec![self.spec.clone(), other.spec.clone()]),
        }
    }

    fn __invert__(&self) -> Self {
        Self {
            spec: FilterSpec::Not(Box::new(self.spec.clone())),
        }
    }

    fn __eq__(&self, other: &Bound<'_, PyAny>) -> bool {
        other
            .extract::<PyCellFilter>()
            .is_ok_and(|other| other.spec == self.spec)
    }

    fn __hash__(&self) -> u64 {
        use std::hash::{Hash, Hasher};
        let mut hasher = std::collections::hash_map::DefaultHasher::new();
        format!("{:?}", self.spec).hash(&mut hasher);
        hasher.finish()
    }

    fn __copy__(&self) -> Self {
        self.clone()
    }

    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.clone()
    }

    fn __repr__(&self) -> String {
        format!("CellFilter({:?})", self.spec)
    }
}

// ---------------------------------------------------------------------------------------
// Running effects

/// A started effect.
#[pyclass(name = "RunningEffect", module = "xnano._xnano_core", frozen)]
pub struct PyRunningEffect {
    inner: SharedRunningEffect,
}

#[pymethods]
impl PyRunningEffect {
    #[getter]
    fn key(&self) -> Option<String> {
        lock(&self.inner).key.clone()
    }

    #[getter]
    fn effect(&self, py: Python<'_>) -> PyResult<Py<PyEffect>> {
        effect_around(py, Arc::clone(&lock(&self.inner).run.spec))
    }

    /// How far the effect has progressed, from 0.0 to 1.0, when it has a timer of its own.
    #[getter]
    fn progress(&self) -> Option<f32> {
        lock(&self.inner).run.progress()
    }

    #[getter]
    fn elapsed_milliseconds(&self) -> u64 {
        lock(&self.inner).run.elapsed_milliseconds()
    }

    #[getter]
    fn is_done(&self) -> bool {
        let running = lock(&self.inner);
        running.is_cancelled || running.run.is_done()
    }

    #[getter]
    fn is_paused(&self) -> bool {
        lock(&self.inner).is_paused
    }

    /// The reason the effect stopped early, if its settings could not be read.
    #[getter]
    fn error(&self) -> Option<String> {
        lock(&self.inner).error.clone()
    }

    fn pause(&self) {
        lock(&self.inner).is_paused = true;
    }

    fn resume(&self) {
        lock(&self.inner).is_paused = false;
    }

    fn cancel(&self) {
        lock(&self.inner).is_cancelled = true;
    }

    fn restart(&self) {
        lock(&self.inner).run.restart();
    }

    fn reverse(&self) {
        lock(&self.inner).run.reverse();
    }

    /// Call `callback` with no arguments once the effect finishes.
    fn on_complete(&self, callback: Py<PyAny>) {
        lock(&self.inner).completed.push(callback);
    }

    fn __repr__(&self) -> String {
        let running = lock(&self.inner);
        format!(
            "RunningEffect(key={:?}, elapsed_milliseconds={}, is_done={})",
            running.key,
            running.run.elapsed_milliseconds(),
            running.is_cancelled || running.run.is_done()
        )
    }
}

/// The effects running on a runtime.
#[pyclass(name = "EffectManager", module = "xnano._xnano_core", frozen)]
pub struct PyEffectManager {
    pub shared: Arc<crate::shared::RuntimeShared>,
}

#[pymethods]
impl PyEffectManager {
    /// Start `effect` on a buffer or region; a running effect with the same key is replaced.
    #[pyo3(signature = (effect, target, *, key = None, area = None, filter = None))]
    fn start(
        &self,
        effect: &Bound<'_, PyAny>,
        target: &Bound<'_, PyAny>,
        key: Option<String>,
        area: Option<&PyRectangle>,
        filter: Option<&PyCellFilter>,
    ) -> PyResult<PyRunningEffect> {
        let spec = spec_of(effect)?;
        let surface = target
            .extract::<PyRef<'_, PySurface>>()
            .map_err(|_| PyTypeError::new_err("start() runs an effect on a Buffer or a Region"))?;
        let key = key.or_else(|| spec.read().key.clone());
        let inner = self.shared.start_effect(RunningEffect {
            key,
            run: EffectRun::new(spec),
            placement: Placement {
                area: area.map(|area| area.inner),
                filter: filter.map(|filter| filter.spec.clone()),
            },
            target: Arc::clone(&surface.core),
            region: surface.region,
            is_paused: false,
            is_cancelled: false,
            completed: Vec::new(),
            error: None,
        });
        Ok(PyRunningEffect { inner })
    }

    fn cancel(&self, key: &str) {
        self.shared.cancel_effect(key);
    }

    fn cancel_all(&self) {
        let mut motion = lock(&self.shared.motion);
        for entry in motion.effects.drain(..) {
            lock(&entry).is_cancelled = true;
        }
        drop(motion);
        self.shared.request_frame();
    }

    fn is_running(&self, key: &str) -> bool {
        lock(&self.shared.motion)
            .effects
            .iter()
            .any(|entry| lock(entry).key.as_deref() == Some(key))
    }

    fn get(&self, key: &str) -> Option<PyRunningEffect> {
        lock(&self.shared.motion)
            .effects
            .iter()
            .find(|entry| lock(entry).key.as_deref() == Some(key))
            .map(|entry| PyRunningEffect {
                inner: Arc::clone(entry),
            })
    }

    fn running(&self) -> Vec<PyRunningEffect> {
        lock(&self.shared.motion)
            .effects
            .iter()
            .map(|entry| PyRunningEffect {
                inner: Arc::clone(entry),
            })
            .collect()
    }

    fn __len__(&self) -> usize {
        lock(&self.shared.motion).effects.len()
    }

    fn __repr__(&self) -> String {
        format!("EffectManager({} running)", self.__len__())
    }
}

#[pyclass(name = "CancelEffect", module = "xnano._xnano_core", extends = PyOperation)]
pub struct PyCancelEffect;

#[pymethods]
impl PyCancelEffect {
    #[new]
    fn new(key: String) -> PyClassInitializer<Self> {
        operation_initializer(Operation::CancelEffect(key)).add_subclass(Self)
    }
}

fn effect_initializer(node: EffectNode) -> PyClassInitializer<PyEffect> {
    let spec = Spec::new(node);
    operation_initializer(Operation::Effect(Arc::clone(&spec))).add_subclass(PyEffect { spec })
}

#[pyclass(name = "Fade", module = "xnano._xnano_core", extends = PyEffect)]
pub struct PyFade;
#[pymethods]
impl PyFade {
    #[new]
    #[pyo3(signature = (*, foreground = None, background = None, duration_milliseconds = None, interpolation = None, key = None))]
    fn new(
        py: Python<'_>,
        foreground: Option<&Bound<'_, PyAny>>,
        background: Option<&Bound<'_, PyAny>>,
        duration_milliseconds: Option<&Bound<'_, PyAny>>,
        interpolation: Option<&Bound<'_, PyAny>>,
        key: Option<String>,
    ) -> PyResult<PyClassInitializer<Self>> {
        let default = 500_u32.into_pyobject(py)?.into_any();
        let timer = timer_arg(duration_milliseconds.unwrap_or(&default), interpolation)?;
        let mut node = EffectNode::new(Kind::Fade {
            foreground: optional(foreground, dynamic_color)?,
            background: optional(background, dynamic_color)?,
            is_from: false,
            timer,
        });
        node.key = key;

        Ok(effect_initializer(node).add_subclass(Self))
    }
}

#[pyclass(name = "Dissolve", module = "xnano._xnano_core", extends = PyEffect)]
pub struct PyDissolve;
#[pymethods]
impl PyDissolve {
    #[new]
    #[pyo3(signature = (*, should_reverse = false, seed = None, duration_milliseconds = None, interpolation = None, key = None))]
    fn new(
        py: Python<'_>,
        should_reverse: bool,
        seed: Option<u32>,
        duration_milliseconds: Option<&Bound<'_, PyAny>>,
        interpolation: Option<&Bound<'_, PyAny>>,
        key: Option<String>,
    ) -> PyResult<PyClassInitializer<Self>> {
        let default = 500_u32.into_pyobject(py)?.into_any();
        let timer = timer_arg(duration_milliseconds.unwrap_or(&default), interpolation)?;
        let mut node = EffectNode::new(Kind::Dissolve {
            is_coalesce: should_reverse,
            style: None,
            timer,
        });
        node.key = key;
        node.seed = seed;
        Ok(effect_initializer(node).add_subclass(Self))
    }
}

#[pyclass(name = "Glitch", module = "xnano._xnano_core", extends = PyEffect)]
pub struct PyGlitch;
#[pymethods]
impl PyGlitch {
    #[new]
    #[pyo3(signature = (*, intensity = 0.1, seed = None, duration_milliseconds = None, interpolation = None, key = None))]
    fn new(
        py: Python<'_>,
        intensity: f32,
        seed: Option<u32>,
        duration_milliseconds: Option<&Bound<'_, PyAny>>,
        interpolation: Option<&Bound<'_, PyAny>>,
        key: Option<String>,
    ) -> PyResult<PyClassInitializer<Self>> {
        if !(0.0..=1.0).contains(&intensity) {
            return Err(PyValueError::new_err(
                "a glitch intensity must be from 0.0 to 1.0",
            ));
        }
        let default = 500_u32.into_pyobject(py)?.into_any();
        let timer = timer_arg(duration_milliseconds.unwrap_or(&default), interpolation)?;
        let mut node = EffectNode::new(Kind::Glitch {
            cell_ratio: Dynamic::Fixed(intensity),
            start_delay_milliseconds: [Dynamic::Fixed(0), Dynamic::Fixed(100)],
            action_milliseconds: [Dynamic::Fixed(40), Dynamic::Fixed(250)],
            duration_milliseconds: timer.duration_milliseconds,
        });
        node.key = key;
        node.seed = seed;
        Ok(effect_initializer(node).add_subclass(Self))
    }
}
#[pyclass(name = "Fuzz", module = "xnano._xnano_core", extends = PyOperation)]
pub struct PyFuzz;

#[pymethods]
impl PyFuzz {
    #[new]
    #[pyo3(signature = (intensity, *, seed = None))]
    fn new(intensity: i64, seed: Option<u64>) -> PyResult<PyClassInitializer<Self>> {
        if !(0..=100).contains(&intensity) {
            return Err(PyValueError::new_err(format!(
                "a fuzz intensity is a percentage from 0 to 100, not {intensity}"
            )));
        }
        Ok(operation_initializer(Operation::Fuzz {
            intensity: intensity as u32,
            seed,
        })
        .add_subclass(Self))
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyEffect>()?;
    m.add_class::<PyFade>()?;
    m.add_class::<PyDissolve>()?;
    m.add_class::<PyGlitch>()?;
    m.add_class::<PyFuzz>()?;
    m.add_class::<PyCellFilter>()?;
    m.add_class::<PyRunningEffect>()?;
    m.add_class::<PyEffectManager>()?;
    m.add_class::<PyCancelEffect>()
}
