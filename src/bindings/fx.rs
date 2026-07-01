use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use tachyonfx::{
    fx::{self, RepeatMode},
    CellFilter, ColorSpace, Effect, EffectManager, EffectTimer, Interpolation, Motion, SimpleRng,
};

use super::buffer::PyBuffer;
use super::convert_core::{
    sync_from_core_buffer, sync_to_core_buffer, to_core_color, to_core_margin, to_core_rect,
    to_core_style,
};
use super::layout::{PyMargin, PyRect};
use super::style::{PyColor, PyStyle};

fn make_timer(duration_ms: u32, interpolation: Option<PyInterpolation>) -> EffectTimer {
    match interpolation {
        Some(i) => EffectTimer::from_ms(duration_ms, i.into()),
        None => EffectTimer::from_ms(duration_ms, Interpolation::Linear),
    }
}

#[pyclass(name = "Motion", module = "xnano_core._xnano_core", eq, eq_int)]
#[derive(Clone, Copy, PartialEq)]
pub enum PyMotion {
    UpToDown,
    DownToUp,
    LeftToRight,
    RightToLeft,
}

impl From<PyMotion> for Motion {
    fn from(value: PyMotion) -> Self {
        match value {
            PyMotion::UpToDown => Motion::UpToDown,
            PyMotion::DownToUp => Motion::DownToUp,
            PyMotion::LeftToRight => Motion::LeftToRight,
            PyMotion::RightToLeft => Motion::RightToLeft,
        }
    }
}

#[pyclass(name = "Interpolation", module = "xnano_core._xnano_core", eq, eq_int)]
#[derive(Clone, Copy, PartialEq)]
pub enum PyInterpolation {
    BackIn,
    BackOut,
    BackInOut,
    BounceIn,
    BounceOut,
    BounceInOut,
    CircIn,
    CircOut,
    CircInOut,
    CubicIn,
    CubicOut,
    CubicInOut,
    ElasticIn,
    ElasticOut,
    ElasticInOut,
    ExpoIn,
    ExpoOut,
    ExpoInOut,
    Linear,
    QuadIn,
    QuadOut,
    QuadInOut,
    QuartIn,
    QuartOut,
    QuartInOut,
    QuintIn,
    QuintOut,
    QuintInOut,
    Reverse,
    SmoothStep,
    Spring,
    SineIn,
    SineOut,
    SineInOut,
}

impl From<PyInterpolation> for Interpolation {
    fn from(value: PyInterpolation) -> Self {
        match value {
            PyInterpolation::BackIn => Interpolation::BackIn,
            PyInterpolation::BackOut => Interpolation::BackOut,
            PyInterpolation::BackInOut => Interpolation::BackInOut,
            PyInterpolation::BounceIn => Interpolation::BounceIn,
            PyInterpolation::BounceOut => Interpolation::BounceOut,
            PyInterpolation::BounceInOut => Interpolation::BounceInOut,
            PyInterpolation::CircIn => Interpolation::CircIn,
            PyInterpolation::CircOut => Interpolation::CircOut,
            PyInterpolation::CircInOut => Interpolation::CircInOut,
            PyInterpolation::CubicIn => Interpolation::CubicIn,
            PyInterpolation::CubicOut => Interpolation::CubicOut,
            PyInterpolation::CubicInOut => Interpolation::CubicInOut,
            PyInterpolation::ElasticIn => Interpolation::ElasticIn,
            PyInterpolation::ElasticOut => Interpolation::ElasticOut,
            PyInterpolation::ElasticInOut => Interpolation::ElasticInOut,
            PyInterpolation::ExpoIn => Interpolation::ExpoIn,
            PyInterpolation::ExpoOut => Interpolation::ExpoOut,
            PyInterpolation::ExpoInOut => Interpolation::ExpoInOut,
            PyInterpolation::Linear => Interpolation::Linear,
            PyInterpolation::QuadIn => Interpolation::QuadIn,
            PyInterpolation::QuadOut => Interpolation::QuadOut,
            PyInterpolation::QuadInOut => Interpolation::QuadInOut,
            PyInterpolation::QuartIn => Interpolation::QuartIn,
            PyInterpolation::QuartOut => Interpolation::QuartOut,
            PyInterpolation::QuartInOut => Interpolation::QuartInOut,
            PyInterpolation::QuintIn => Interpolation::QuintIn,
            PyInterpolation::QuintOut => Interpolation::QuintOut,
            PyInterpolation::QuintInOut => Interpolation::QuintInOut,
            PyInterpolation::Reverse => Interpolation::Reverse,
            PyInterpolation::SmoothStep => Interpolation::SmoothStep,
            PyInterpolation::Spring => Interpolation::Spring,
            PyInterpolation::SineIn => Interpolation::SineIn,
            PyInterpolation::SineOut => Interpolation::SineOut,
            PyInterpolation::SineInOut => Interpolation::SineInOut,
        }
    }
}

#[pyclass(name = "ColorSpace", module = "xnano_core._xnano_core", eq, eq_int)]
#[derive(Clone, Copy, PartialEq)]
pub enum PyColorSpace {
    Rgb,
    Hsl,
    Hsv,
}

impl From<PyColorSpace> for ColorSpace {
    fn from(value: PyColorSpace) -> Self {
        match value {
            PyColorSpace::Rgb => ColorSpace::Rgb,
            PyColorSpace::Hsl => ColorSpace::Hsl,
            PyColorSpace::Hsv => ColorSpace::Hsv,
        }
    }
}

#[pyclass(name = "CellFilter", module = "xnano_core._xnano_core", unsendable)]
#[derive(Clone)]
pub struct PyCellFilter {
    pub inner: CellFilter,
}

#[pymethods]
#[allow(non_snake_case)]
impl PyCellFilter {
    #[classattr]
    fn ALL() -> Self {
        Self {
            inner: CellFilter::All,
        }
    }

    #[classattr]
    fn TEXT() -> Self {
        Self {
            inner: CellFilter::Text,
        }
    }

    #[classattr]
    fn NON_EMPTY() -> Self {
        Self {
            inner: CellFilter::NonEmpty,
        }
    }

    #[staticmethod]
    fn fg_color(color: PyColor) -> Self {
        Self {
            inner: CellFilter::FgColor(to_core_color(color.inner)),
        }
    }

    #[staticmethod]
    fn bg_color(color: PyColor) -> Self {
        Self {
            inner: CellFilter::BgColor(to_core_color(color.inner)),
        }
    }

    #[staticmethod]
    fn inner(margin: PyMargin) -> Self {
        Self {
            inner: CellFilter::Inner(to_core_margin(margin.inner)),
        }
    }

    #[staticmethod]
    fn outer(margin: PyMargin) -> Self {
        Self {
            inner: CellFilter::Outer(to_core_margin(margin.inner)),
        }
    }

    #[staticmethod]
    fn area(rect: PyRect) -> Self {
        Self {
            inner: CellFilter::Area(to_core_rect(rect.inner)),
        }
    }

    #[staticmethod]
    fn all_of(filters: Vec<PyCellFilter>) -> Self {
        Self {
            inner: CellFilter::AllOf(filters.into_iter().map(|f| f.inner).collect()),
        }
    }

    #[staticmethod]
    fn any_of(filters: Vec<PyCellFilter>) -> Self {
        Self {
            inner: CellFilter::AnyOf(filters.into_iter().map(|f| f.inner).collect()),
        }
    }

    #[staticmethod]
    fn not_(filter: PyCellFilter) -> Self {
        Self {
            inner: CellFilter::Not(Box::new(filter.inner)),
        }
    }
}

#[pyclass(name = "Effect", module = "xnano_core._xnano_core", unsendable)]
#[derive(Clone)]
pub struct PyEffect {
    pub inner: Effect,
}

#[pymethods]
impl PyEffect {
    fn with_area(&self, area: PyRect) -> Self {
        Self {
            inner: self.inner.clone().with_area(to_core_rect(area.inner)),
        }
    }

    fn with_filter(&self, filter: PyCellFilter) -> Self {
        Self {
            inner: self.inner.clone().with_filter(filter.inner),
        }
    }

    fn with_color_space(&self, color_space: PyColorSpace) -> Self {
        Self {
            inner: self.inner.clone().with_color_space(color_space.into()),
        }
    }

    fn with_rng(&self, seed: u32) -> Self {
        Self {
            inner: self.inner.clone().with_rng(SimpleRng::new(seed)),
        }
    }

    fn reversed(&self) -> Self {
        Self {
            inner: self.inner.clone().reversed(),
        }
    }

    fn name(&self) -> &'static str {
        self.inner.name()
    }

    fn is_done(&self) -> bool {
        self.inner.done()
    }

    fn is_running(&self) -> bool {
        self.inner.running()
    }

    fn reset(&mut self) {
        self.inner.reset();
    }
}

#[pyfunction]
#[pyo3(signature = (color, duration_ms, interpolation=None))]
fn fade_to_fg(color: PyColor, duration_ms: u32, interpolation: Option<PyInterpolation>) -> PyEffect {
    PyEffect {
        inner: fx::fade_to_fg(
            to_core_color(color.inner),
            make_timer(duration_ms, interpolation),
        ),
    }
}

#[pyfunction]
#[pyo3(signature = (color, duration_ms, interpolation=None))]
fn fade_from_fg(
    color: PyColor,
    duration_ms: u32,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::fade_from_fg(
            to_core_color(color.inner),
            make_timer(duration_ms, interpolation),
        ),
    }
}

#[pyfunction]
#[pyo3(signature = (fg, bg, duration_ms, interpolation=None))]
fn fade_to(
    fg: PyColor,
    bg: PyColor,
    duration_ms: u32,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::fade_to(
            to_core_color(fg.inner),
            to_core_color(bg.inner),
            make_timer(duration_ms, interpolation),
        ),
    }
}

#[pyfunction]
#[pyo3(signature = (fg, bg, duration_ms, interpolation=None))]
fn fade_from(
    fg: PyColor,
    bg: PyColor,
    duration_ms: u32,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::fade_from(
            to_core_color(fg.inner),
            to_core_color(bg.inner),
            make_timer(duration_ms, interpolation),
        ),
    }
}

#[pyfunction]
#[pyo3(signature = (fg, bg, duration_ms, interpolation=None))]
fn paint(
    fg: PyColor,
    bg: PyColor,
    duration_ms: u32,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::paint(
            to_core_color(fg.inner),
            to_core_color(bg.inner),
            make_timer(duration_ms, interpolation),
        ),
    }
}

#[pyfunction]
#[pyo3(signature = (fg, duration_ms, interpolation=None))]
fn paint_fg(
    fg: PyColor,
    duration_ms: u32,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::paint_fg(to_core_color(fg.inner), make_timer(duration_ms, interpolation)),
    }
}

#[pyfunction]
#[pyo3(signature = (bg, duration_ms, interpolation=None))]
fn paint_bg(
    bg: PyColor,
    duration_ms: u32,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::paint_bg(to_core_color(bg.inner), make_timer(duration_ms, interpolation)),
    }
}

#[pyfunction]
#[pyo3(signature = (direction, gradient_length, randomness, color, duration_ms, interpolation=None))]
fn slide_in(
    direction: PyMotion,
    gradient_length: u16,
    randomness: u16,
    color: PyColor,
    duration_ms: u32,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::slide_in(
            direction.into(),
            gradient_length,
            randomness,
            to_core_color(color.inner),
            make_timer(duration_ms, interpolation),
        ),
    }
}

#[pyfunction]
#[pyo3(signature = (direction, gradient_length, randomness, color, duration_ms, interpolation=None))]
fn slide_out(
    direction: PyMotion,
    gradient_length: u16,
    randomness: u16,
    color: PyColor,
    duration_ms: u32,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::slide_out(
            direction.into(),
            gradient_length,
            randomness,
            to_core_color(color.inner),
            make_timer(duration_ms, interpolation),
        ),
    }
}

#[pyfunction]
#[pyo3(signature = (direction, gradient_length, randomness, color, duration_ms, interpolation=None))]
fn sweep_in(
    direction: PyMotion,
    gradient_length: u16,
    randomness: u16,
    color: PyColor,
    duration_ms: u32,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::sweep_in(
            direction.into(),
            gradient_length,
            randomness,
            to_core_color(color.inner),
            make_timer(duration_ms, interpolation),
        ),
    }
}

#[pyfunction]
#[pyo3(signature = (direction, gradient_length, randomness, color, duration_ms, interpolation=None))]
fn sweep_out(
    direction: PyMotion,
    gradient_length: u16,
    randomness: u16,
    color: PyColor,
    duration_ms: u32,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::sweep_out(
            direction.into(),
            gradient_length,
            randomness,
            to_core_color(color.inner),
            make_timer(duration_ms, interpolation),
        ),
    }
}

#[pyfunction]
#[pyo3(signature = (duration_ms, interpolation=None))]
fn dissolve(duration_ms: u32, interpolation: Option<PyInterpolation>) -> PyEffect {
    PyEffect {
        inner: fx::dissolve(make_timer(duration_ms, interpolation)),
    }
}

#[pyfunction]
#[pyo3(signature = (style, duration_ms, interpolation=None))]
fn dissolve_to(
    style: PyStyle,
    duration_ms: u32,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::dissolve_to(to_core_style(style.inner), make_timer(duration_ms, interpolation)),
    }
}

#[pyfunction]
#[pyo3(signature = (duration_ms, interpolation=None))]
fn coalesce(duration_ms: u32, interpolation: Option<PyInterpolation>) -> PyEffect {
    PyEffect {
        inner: fx::coalesce(make_timer(duration_ms, interpolation)),
    }
}

#[pyfunction]
#[pyo3(signature = (style, duration_ms, interpolation=None))]
fn coalesce_from(
    style: PyStyle,
    duration_ms: u32,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::coalesce_from(
            to_core_style(style.inner),
            make_timer(duration_ms, interpolation),
        ),
    }
}

#[pyfunction]
fn sleep_effect(duration_ms: u32) -> PyEffect {
    PyEffect {
        inner: fx::sleep(tachyonfx::Duration::from_millis(duration_ms)),
    }
}

#[pyfunction]
fn sequence_effects(effects: Vec<PyEffect>) -> PyEffect {
    let items: Vec<Effect> = effects.into_iter().map(|e| e.inner).collect();
    PyEffect {
        inner: fx::sequence(&items),
    }
}

#[pyfunction]
fn parallel_effects(effects: Vec<PyEffect>) -> PyEffect {
    let items: Vec<Effect> = effects.into_iter().map(|e| e.inner).collect();
    PyEffect {
        inner: fx::parallel(&items),
    }
}

#[pyfunction]
fn repeating_effect(effect: &PyEffect) -> PyEffect {
    PyEffect {
        inner: fx::repeating(effect.inner.clone()),
    }
}

#[pyfunction]
fn ping_pong_effect(effect: &PyEffect) -> PyEffect {
    PyEffect {
        inner: fx::ping_pong(effect.inner.clone()),
    }
}

#[pyfunction]
#[pyo3(signature = (effect, times=None, duration_ms=None))]
fn repeat_effect(
    effect: &PyEffect,
    times: Option<u32>,
    duration_ms: Option<u32>,
) -> PyResult<PyEffect> {
    let mode = match (times, duration_ms) {
        (Some(n), None) => RepeatMode::Times(n),
        (None, Some(ms)) => RepeatMode::Duration(tachyonfx::Duration::from_millis(ms)),
        (None, None) => RepeatMode::Forever,
        _ => {
            return Err(PyValueError::new_err(
                "specify either times or duration_ms, not both",
            ));
        }
    };
    Ok(PyEffect {
        inner: fx::repeat(effect.inner.clone(), mode),
    })
}

#[pyfunction]
fn delay_effect(duration_ms: u32, effect: &PyEffect) -> PyEffect {
    PyEffect {
        inner: fx::delay(
            tachyonfx::Duration::from_millis(duration_ms),
            effect.inner.clone(),
        ),
    }
}

#[pyfunction]
fn prolong_start_effect(duration_ms: u32, effect: &PyEffect) -> PyEffect {
    PyEffect {
        inner: fx::prolong_start(
            tachyonfx::Duration::from_millis(duration_ms),
            effect.inner.clone(),
        ),
    }
}

#[pyfunction]
fn prolong_end_effect(duration_ms: u32, effect: &PyEffect) -> PyEffect {
    PyEffect {
        inner: fx::prolong_end(
            tachyonfx::Duration::from_millis(duration_ms),
            effect.inner.clone(),
        ),
    }
}

#[pyfunction]
#[pyo3(signature = (duration_ms, fg=None, bg=None, interpolation=None))]
fn saturate(
    duration_ms: u32,
    fg: Option<f32>,
    bg: Option<f32>,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::saturate(fg, bg, make_timer(duration_ms, interpolation)),
    }
}

#[pyfunction]
#[pyo3(signature = (fg, duration_ms, interpolation=None))]
fn saturate_fg(fg: f32, duration_ms: u32, interpolation: Option<PyInterpolation>) -> PyEffect {
    PyEffect {
        inner: fx::saturate_fg(fg, make_timer(duration_ms, interpolation)),
    }
}

#[pyfunction]
#[pyo3(signature = (duration_ms, fg=None, bg=None, interpolation=None))]
fn lighten(
    duration_ms: u32,
    fg: Option<f32>,
    bg: Option<f32>,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::lighten(fg, bg, make_timer(duration_ms, interpolation)),
    }
}

#[pyfunction]
#[pyo3(signature = (fg, duration_ms, interpolation=None))]
fn lighten_fg(fg: f32, duration_ms: u32, interpolation: Option<PyInterpolation>) -> PyEffect {
    PyEffect {
        inner: fx::lighten_fg(fg, make_timer(duration_ms, interpolation)),
    }
}

#[pyfunction]
#[pyo3(signature = (duration_ms, fg=None, bg=None, interpolation=None))]
fn darken(
    duration_ms: u32,
    fg: Option<f32>,
    bg: Option<f32>,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::darken(fg, bg, make_timer(duration_ms, interpolation)),
    }
}

#[pyfunction]
#[pyo3(signature = (fg, duration_ms, interpolation=None))]
fn darken_fg(fg: f32, duration_ms: u32, interpolation: Option<PyInterpolation>) -> PyEffect {
    PyEffect {
        inner: fx::darken_fg(fg, make_timer(duration_ms, interpolation)),
    }
}

#[pyfunction]
#[pyo3(signature = (duration_ms, fg_h=None, fg_s=None, fg_l=None, bg_h=None, bg_s=None, bg_l=None, interpolation=None))]
fn hsl_shift(
    duration_ms: u32,
    fg_h: Option<f32>,
    fg_s: Option<f32>,
    fg_l: Option<f32>,
    bg_h: Option<f32>,
    bg_s: Option<f32>,
    bg_l: Option<f32>,
    interpolation: Option<PyInterpolation>,
) -> PyResult<PyEffect> {
    let fg_shift = match (fg_h, fg_s, fg_l) {
        (Some(h), Some(s), Some(l)) => Some([h, s, l]),
        (None, None, None) => None,
        _ => {
            return Err(PyValueError::new_err(
                "fg_h, fg_s, and fg_l must all be provided together",
            ));
        }
    };
    let bg_shift = match (bg_h, bg_s, bg_l) {
        (Some(h), Some(s), Some(l)) => Some([h, s, l]),
        (None, None, None) => None,
        _ => {
            return Err(PyValueError::new_err(
                "bg_h, bg_s, and bg_l must all be provided together",
            ));
        }
    };
    if fg_shift.is_none() && bg_shift.is_none() {
        return Err(PyValueError::new_err(
            "at least one of foreground or background HSL shift must be provided",
        ));
    }
    Ok(PyEffect {
        inner: fx::hsl_shift(fg_shift, bg_shift, make_timer(duration_ms, interpolation)),
    })
}

#[pyfunction]
#[pyo3(signature = (h, s, l, duration_ms, interpolation=None))]
fn hsl_shift_fg(
    h: f32,
    s: f32,
    l: f32,
    duration_ms: u32,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::hsl_shift_fg(
            [h, s, l],
            make_timer(duration_ms, interpolation),
        ),
    }
}

#[pyclass(name = "EffectManager", module = "xnano_core._xnano_core", unsendable)]
pub struct PyEffectManager {
    inner: EffectManager<String>,
}

impl PyEffectManager {
    pub fn inner_mut(&mut self) -> &mut EffectManager<String> {
        &mut self.inner
    }
}

#[pymethods]
impl PyEffectManager {
    #[new]
    fn new() -> Self {
        Self {
            inner: EffectManager::default(),
        }
    }

    fn add(&mut self, effect: PyEffect) {
        self.inner.add_effect(effect.inner);
    }

    fn add_unique(&mut self, key: String, effect: PyEffect) {
        self.inner.add_unique_effect(key, effect.inner);
    }

    fn unique(&mut self, key: String, effect: PyEffect) -> PyEffect {
        PyEffect {
            inner: self.inner.unique(key, effect.inner),
        }
    }

    fn cancel(&mut self, key: String) {
        self.inner.cancel_unique_effect(key);
    }

    fn is_running(&self) -> bool {
        self.inner.is_running()
    }

    fn process(&mut self, duration_ms: u32, buffer: &mut PyBuffer, area: PyRect) {
        let mut core = sync_to_core_buffer(&buffer.inner);
        self.inner.process_effects(
            tachyonfx::Duration::from_millis(duration_ms),
            &mut core,
            to_core_rect(area.inner),
        );
        sync_from_core_buffer(&core, &mut buffer.inner);
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyEffect>()?;
    m.add_class::<PyMotion>()?;
    m.add_class::<PyInterpolation>()?;
    m.add_class::<PyColorSpace>()?;
    m.add_class::<PyCellFilter>()?;
    m.add_class::<PyEffectManager>()?;
    m.add_function(wrap_pyfunction!(fade_to_fg, m)?)?;
    m.add_function(wrap_pyfunction!(fade_from_fg, m)?)?;
    m.add_function(wrap_pyfunction!(fade_to, m)?)?;
    m.add_function(wrap_pyfunction!(fade_from, m)?)?;
    m.add_function(wrap_pyfunction!(paint, m)?)?;
    m.add_function(wrap_pyfunction!(paint_fg, m)?)?;
    m.add_function(wrap_pyfunction!(paint_bg, m)?)?;
    m.add_function(wrap_pyfunction!(slide_in, m)?)?;
    m.add_function(wrap_pyfunction!(slide_out, m)?)?;
    m.add_function(wrap_pyfunction!(sweep_in, m)?)?;
    m.add_function(wrap_pyfunction!(sweep_out, m)?)?;
    m.add_function(wrap_pyfunction!(dissolve, m)?)?;
    m.add_function(wrap_pyfunction!(dissolve_to, m)?)?;
    m.add_function(wrap_pyfunction!(coalesce, m)?)?;
    m.add_function(wrap_pyfunction!(coalesce_from, m)?)?;
    m.add_function(wrap_pyfunction!(sleep_effect, m)?)?;
    m.add_function(wrap_pyfunction!(sequence_effects, m)?)?;
    m.add_function(wrap_pyfunction!(parallel_effects, m)?)?;
    m.add_function(wrap_pyfunction!(repeating_effect, m)?)?;
    m.add_function(wrap_pyfunction!(ping_pong_effect, m)?)?;
    m.add_function(wrap_pyfunction!(repeat_effect, m)?)?;
    m.add_function(wrap_pyfunction!(delay_effect, m)?)?;
    m.add_function(wrap_pyfunction!(prolong_start_effect, m)?)?;
    m.add_function(wrap_pyfunction!(prolong_end_effect, m)?)?;
    m.add_function(wrap_pyfunction!(saturate, m)?)?;
    m.add_function(wrap_pyfunction!(saturate_fg, m)?)?;
    m.add_function(wrap_pyfunction!(lighten, m)?)?;
    m.add_function(wrap_pyfunction!(lighten_fg, m)?)?;
    m.add_function(wrap_pyfunction!(darken, m)?)?;
    m.add_function(wrap_pyfunction!(darken_fg, m)?)?;
    m.add_function(wrap_pyfunction!(hsl_shift, m)?)?;
    m.add_function(wrap_pyfunction!(hsl_shift_fg, m)?)?;
    Ok(())
}