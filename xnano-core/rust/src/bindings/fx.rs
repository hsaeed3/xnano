use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;

use ratatui_core::buffer::Cell as CoreCell;
use ratatui_core::layout::{Offset as CoreOffset, Position as CorePosition};
use ratatui_core::style::Color as CoreColor;
use tachyonfx::{
    fx::{self, EvolveSymbolSet, ExpandDirection, RepeatMode},
    pattern::RadialPattern,
    ref_count, CellFilter, ColorSpace, Duration, Effect, EffectManager, EffectTimer,
    Interpolation, IntoEffect, Motion, RefRect, SimpleRng,
};

use super::buffer::PyBuffer;
use super::convert_core::{
    from_core_color, sync_from_core_buffer, sync_to_core_buffer, to_core_color,
    to_core_margin, to_core_rect, to_core_style,
};
use super::layout::{PyLayout, PyMargin, PyOffset, PyRect, PySize};
use super::style::{PyColor, PyStyle};

fn make_timer(duration_ms: u32, interpolation: Option<PyInterpolation>) -> EffectTimer {
    match interpolation {
        Some(i) => EffectTimer::from_ms(duration_ms, i.into()),
        None => EffectTimer::from_ms(duration_ms, Interpolation::Linear),
    }
}

#[pyclass(name = "Motion", module = "xnano_core.rust.native", eq, eq_int, from_py_object)]
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

#[pyclass(name = "Interpolation", module = "xnano_core.rust.native", eq, eq_int, from_py_object)]
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

#[pyclass(name = "ColorSpace", module = "xnano_core.rust.native", eq, eq_int, from_py_object)]
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

#[pyclass(name = "Duration", module = "xnano_core.rust.native", eq, from_py_object)]
#[derive(Clone, Copy, PartialEq)]
pub struct PyDuration {
    inner: Duration,
}

#[pymethods]
impl PyDuration {
    #[classattr]
    const ZERO: Self = Self {
        inner: Duration::ZERO,
    };

    #[staticmethod]
    fn from_millis(milliseconds: u32) -> Self {
        Self {
            inner: Duration::from_millis(milliseconds),
        }
    }

    #[staticmethod]
    fn from_secs(seconds: u32) -> Self {
        Self {
            inner: Duration::from_secs(seconds),
        }
    }

    fn as_millis(&self) -> u32 {
        self.inner.as_millis()
    }

    fn is_zero(&self) -> bool {
        self.inner.is_zero()
    }

    fn __repr__(&self) -> String {
        format!("Duration({}ms)", self.inner.as_millis())
    }
}

#[pyclass(name = "EffectTimer", module = "xnano_core.rust.native", from_py_object)]
#[derive(Clone, Copy)]
pub struct PyEffectTimer {
    inner: EffectTimer,
}

#[pymethods]
impl PyEffectTimer {
    #[staticmethod]
    fn from_ms(duration_ms: u32, interpolation: PyInterpolation) -> Self {
        Self {
            inner: EffectTimer::from_ms(duration_ms, interpolation.into()),
        }
    }

    fn remaining_ms(&self) -> u32 {
        self.inner.remaining().as_millis()
    }

    fn duration_ms(&self) -> u32 {
        self.inner.duration().as_millis()
    }

    fn alpha(&self) -> f32 {
        self.inner.alpha()
    }

    fn is_reversed(&self) -> bool {
        self.inner.is_reversed()
    }

    fn started(&self) -> bool {
        self.inner.started()
    }

    fn is_done(&self) -> bool {
        self.inner.done()
    }

    fn reset(&mut self) {
        self.inner.reset();
    }

    fn __repr__(&self) -> String {
        format!(
            "EffectTimer(remaining={}ms, duration={}ms)",
            self.remaining_ms(),
            self.duration_ms()
        )
    }
}

#[pyclass(name = "RepeatMode", module = "xnano_core.rust.native", eq, eq_int, from_py_object)]
#[derive(Clone, Copy, PartialEq)]
pub enum PyRepeatMode {
    Forever,
    Times,
    Duration,
}

#[pyclass(name = "RefRect", module = "xnano_core.rust.native", unsendable, from_py_object)]
#[derive(Clone)]
pub struct PyRefRect {
    inner: RefRect,
}

#[pymethods]
impl PyRefRect {
    #[staticmethod]
    fn new(rect: PyRect) -> Self {
        Self {
            inner: RefRect::new(to_core_rect(rect.inner)),
        }
    }

    #[staticmethod]
    fn default() -> Self {
        Self {
            inner: RefRect::default(),
        }
    }

    fn get(&self) -> PyRect {
        let rect = self.inner.get();
        PyRect {
            inner: ratatui::layout::Rect::new(rect.x, rect.y, rect.width, rect.height),
        }
    }

    fn set(&self, rect: PyRect) {
        self.inner.set(to_core_rect(rect.inner));
    }

    fn contains(&self, x: u16, y: u16) -> bool {
        self.inner.contains(CorePosition::new(x, y))
    }

    fn __repr__(&self) -> String {
        let rect = self.inner.get();
        format!(
            "RefRect(x={}, y={}, width={}, height={})",
            rect.x, rect.y, rect.width, rect.height
        )
    }
}

#[pyclass(name = "RadialPattern", module = "xnano_core.rust.native", from_py_object)]
#[derive(Clone, Copy)]
pub struct PyRadialPattern {
    inner: RadialPattern,
}

#[pymethods]
impl PyRadialPattern {
    #[staticmethod]
    fn center() -> Self {
        Self {
            inner: RadialPattern::center(),
        }
    }

    #[staticmethod]
    fn new(center_x: f32, center_y: f32) -> Self {
        Self {
            inner: RadialPattern::new(center_x, center_y),
        }
    }

    #[staticmethod]
    fn with_transition(center_x: f32, center_y: f32, transition_width: f32) -> Self {
        Self {
            inner: RadialPattern::with_transition((center_x, center_y), transition_width),
        }
    }

    fn with_transition_width(&self, width: f32) -> Self {
        Self {
            inner: self.inner.with_transition_width(width),
        }
    }

    fn with_center(&self, center_x: f32, center_y: f32) -> Self {
        Self {
            inner: self.inner.with_center((center_x, center_y)),
        }
    }
}

#[pyclass(name = "ExpandDirection", module = "xnano_core.rust.native", eq, eq_int, from_py_object)]
#[derive(Clone, Copy, PartialEq)]
pub enum PyExpandDirection {
    Horizontal,
    Vertical,
}

impl From<PyExpandDirection> for ExpandDirection {
    fn from(value: PyExpandDirection) -> Self {
        match value {
            PyExpandDirection::Horizontal => ExpandDirection::Horizontal,
            PyExpandDirection::Vertical => ExpandDirection::Vertical,
        }
    }
}

#[pyclass(name = "EvolveSymbolSet", module = "xnano_core.rust.native", eq, eq_int, from_py_object)]
#[derive(Clone, Copy, PartialEq)]
pub enum PyEvolveSymbolSet {
    BlocksHorizontal,
    BlocksVertical,
    CircleFill,
    Circles,
    Quadrants,
    Shaded,
    Squares,
}

impl From<PyEvolveSymbolSet> for EvolveSymbolSet {
    fn from(value: PyEvolveSymbolSet) -> Self {
        match value {
            PyEvolveSymbolSet::BlocksHorizontal => EvolveSymbolSet::BlocksHorizontal,
            PyEvolveSymbolSet::BlocksVertical => EvolveSymbolSet::BlocksVertical,
            PyEvolveSymbolSet::CircleFill => EvolveSymbolSet::CircleFill,
            PyEvolveSymbolSet::Circles => EvolveSymbolSet::Circles,
            PyEvolveSymbolSet::Quadrants => EvolveSymbolSet::Quadrants,
            PyEvolveSymbolSet::Shaded => EvolveSymbolSet::Shaded,
            PyEvolveSymbolSet::Squares => EvolveSymbolSet::Squares,
        }
    }
}

#[pyclass(name = "CellFilter", module = "xnano_core.rust.native", unsendable, from_py_object)]
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

    #[classattr]
    fn BACKGROUND() -> Self {
        Self {
            inner: CellFilter::eval_cell(|cell: &CoreCell| {
                cell.bg != CoreColor::Reset
            }),
        }
    }

    #[classattr]
    fn BACKGROUND_ONLY() -> Self {
        Self {
            inner: CellFilter::eval_cell(|cell: &CoreCell| {
                cell.bg != CoreColor::Reset && cell.symbol() == " "
            }),
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

    #[staticmethod]
    fn none_of(filters: Vec<PyCellFilter>) -> Self {
        Self {
            inner: CellFilter::NoneOf(filters.into_iter().map(|f| f.inner).collect()),
        }
    }

    #[staticmethod]
    fn ref_area(ref_rect: PyRefRect) -> Self {
        Self {
            inner: CellFilter::RefArea(ref_rect.inner.clone()),
        }
    }

    #[staticmethod]
    fn layout(layout: PyLayout, index: u16) -> Self {
        Self {
            inner: CellFilter::Layout(layout.core_layout(), index),
        }
    }

    #[staticmethod]
    fn position_fn(callback: Py<PyAny>) -> Self {
        let cb = callback;
        Self {
            inner: CellFilter::PositionFn(ref_count(move |pos: CorePosition| {
                Python::attach(|py| {
                    cb.call1(py, (pos.x, pos.y))
                        .and_then(|value| value.extract::<bool>(py))
                        .unwrap_or(false)
                })
            })),
        }
    }

    #[staticmethod]
    fn eval_cell(callback: Py<PyAny>) -> Self {
        let cb = callback;
        Self {
            inner: CellFilter::eval_cell(move |cell: &CoreCell| {
                Python::attach(|py| {
                    let fg = PyColor::from(from_core_color(cell.fg));
                    let bg = PyColor::from(from_core_color(cell.bg));
                    let args = (cell.symbol(), fg, bg);
                    cb.call1(py, args)
                        .and_then(|value| value.extract::<bool>(py))
                        .unwrap_or(false)
                })
            }),
        }
    }

    fn negated(&self) -> Self {
        Self {
            inner: self.inner.clone().negated(),
        }
    }

    fn into_static(&self) -> Self {
        Self {
            inner: self.inner.clone().into_static(),
        }
    }
}

#[pyclass(name = "Effect", module = "xnano_core.rust.native", unsendable, from_py_object)]
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

    fn get_area(&self) -> Option<PyRect> {
        self.inner.area().map(|rect| PyRect {
            inner: ratatui::layout::Rect::new(rect.x, rect.y, rect.width, rect.height),
        })
    }

    fn set_area(&mut self, area: PyRect) {
        self.inner.set_area(to_core_rect(area.inner));
    }

    fn get_filter(&self) -> Option<PyCellFilter> {
        self.inner.cell_filter().cloned().map(|filter| PyCellFilter { inner: filter })
    }

    fn set_filter(&mut self, filter: PyCellFilter) {
        self.inner.filter(filter.inner);
    }

    fn reverse(&mut self) {
        self.inner.reverse();
    }

    fn get_timer(&self) -> Option<PyEffectTimer> {
        self.inner.timer().map(|timer| PyEffectTimer { inner: timer })
    }

    fn timer(&self) -> Option<PyEffectTimer> {
        self.get_timer()
    }

    fn reset_timer(&mut self) {
        if let Some(timer) = self.inner.timer_mut() {
            timer.reset();
        }
    }

    fn set_color_space(&mut self, color_space: PyColorSpace) {
        self.inner.set_color_space(color_space.into());
    }

    fn with_pattern(&self, pattern: PyRadialPattern) -> Self {
        Self {
            inner: self.inner.clone().with_pattern(pattern.inner),
        }
    }

    fn to_dsl(&self) -> PyResult<String> {
        self.inner
            .to_dsl()
            .map(|expr| expr.to_string())
            .map_err(|err| PyRuntimeError::new_err(format!("{err:?}")))
    }

    fn process(&mut self, duration_ms: u32, buffer: &mut PyBuffer, area: PyRect) -> Option<u32> {
        let mut core = sync_to_core_buffer(&buffer.inner);
        let overflow = self.inner.process(
            Duration::from_millis(duration_ms),
            &mut core,
            to_core_rect(area.inner),
        );
        sync_from_core_buffer(&core, &mut buffer.inner);
        overflow.map(|d| d.as_millis())
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
        // ``fx::coalesce`` clears symbols but deliberately preserves styles,
        // making background-only cells appear immediately. xnano's effect
        // operates on complete terminal cells, so reform from the default
        // style and let foreground/background participate in the reveal.
        inner: fx::coalesce_from(
            ratatui_core::style::Style::reset(),
            make_timer(duration_ms, interpolation),
        ),
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
#[pyo3(signature = (bg, duration_ms, interpolation=None))]
fn saturate_bg(bg: f32, duration_ms: u32, interpolation: Option<PyInterpolation>) -> PyEffect {
    PyEffect {
        inner: fx::saturate(None, Some(bg), make_timer(duration_ms, interpolation)),
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
#[pyo3(signature = (bg, duration_ms, interpolation=None))]
fn lighten_bg(bg: f32, duration_ms: u32, interpolation: Option<PyInterpolation>) -> PyEffect {
    PyEffect {
        inner: fx::lighten(None, Some(bg), make_timer(duration_ms, interpolation)),
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
#[pyo3(signature = (bg, duration_ms, interpolation=None))]
fn darken_bg(bg: f32, duration_ms: u32, interpolation: Option<PyInterpolation>) -> PyEffect {
    PyEffect {
        inner: fx::darken(None, Some(bg), make_timer(duration_ms, interpolation)),
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

#[pyfunction]
#[pyo3(signature = (h, s, l, duration_ms, interpolation=None))]
fn hsl_shift_bg(
    h: f32,
    s: f32,
    l: f32,
    duration_ms: u32,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::hsl_shift(
            None,
            Some([h, s, l]),
            make_timer(duration_ms, interpolation),
        ),
    }
}

#[pyfunction]
#[pyo3(signature = (symbols, duration_ms, style=None, interpolation=None))]
fn evolve_effect(
    symbols: PyEvolveSymbolSet,
    duration_ms: u32,
    style: Option<PyStyle>,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    let timer = make_timer(duration_ms, interpolation);
    let set: EvolveSymbolSet = symbols.into();
    PyEffect {
        inner: if let Some(style) = style {
            fx::evolve((set, to_core_style(style.inner)), timer)
        } else {
            fx::evolve(set, timer)
        },
    }
}

#[pyfunction]
#[pyo3(signature = (symbols, duration_ms, style=None, interpolation=None))]
fn evolve_into_effect(
    symbols: PyEvolveSymbolSet,
    duration_ms: u32,
    style: Option<PyStyle>,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    let timer = make_timer(duration_ms, interpolation);
    let set: EvolveSymbolSet = symbols.into();
    PyEffect {
        inner: if let Some(style) = style {
            fx::evolve_into((set, to_core_style(style.inner)), timer)
        } else {
            fx::evolve_into(set, timer)
        },
    }
}

#[pyfunction]
#[pyo3(signature = (symbols, duration_ms, style=None, interpolation=None))]
fn evolve_from_effect(
    symbols: PyEvolveSymbolSet,
    duration_ms: u32,
    style: Option<PyStyle>,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    let timer = make_timer(duration_ms, interpolation);
    let set: EvolveSymbolSet = symbols.into();
    PyEffect {
        inner: if let Some(style) = style {
            fx::evolve_from((set, to_core_style(style.inner)), timer)
        } else {
            fx::evolve_from(set, timer)
        },
    }
}

#[pyfunction]
#[pyo3(signature = (force, force_rng_factor, duration_ms, interpolation=None))]
fn explode_effect(
    force: f32,
    force_rng_factor: f32,
    duration_ms: u32,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::explode(force, force_rng_factor, make_timer(duration_ms, interpolation)),
    }
}

#[pyfunction]
#[pyo3(signature = (
    cell_glitch_ratio,
    action_start_delay_min_ms,
    action_start_delay_max_ms,
    action_min_ms,
    action_max_ms,
    filter=None,
    seed=None
))]
fn glitch_effect(
    cell_glitch_ratio: f32,
    action_start_delay_min_ms: u32,
    action_start_delay_max_ms: u32,
    action_min_ms: u32,
    action_max_ms: u32,
    filter: Option<PyCellFilter>,
    seed: Option<u32>,
) -> PyEffect {
    let base = fx::Glitch::builder()
        .cell_glitch_ratio(cell_glitch_ratio)
        .action_start_delay_ms(action_start_delay_min_ms..action_start_delay_max_ms)
        .action_ms(action_min_ms..action_max_ms);
    let glitch = match (filter, seed) {
        (Some(filter), Some(seed)) => base
            .selection(filter.inner)
            .rng(SimpleRng::new(seed))
            .build(),
        (Some(filter), None) => base.selection(filter.inner).build(),
        (None, Some(seed)) => base.rng(SimpleRng::new(seed)).build(),
        (None, None) => base.build(),
    };
    PyEffect {
        inner: glitch.into_effect(),
    }
}

#[pyfunction]
#[pyo3(signature = (effect, translate_by, duration_ms, interpolation=None))]
fn translate_effect(
    effect: PyEffect,
    translate_by: PyOffset,
    duration_ms: u32,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::translate(
            effect.inner,
            CoreOffset {
                x: translate_by.inner.x,
                y: translate_by.inner.y,
            },
            make_timer(duration_ms, interpolation),
        ),
    }
}

#[pyfunction]
#[pyo3(signature = (direction, style, duration_ms, interpolation=None))]
fn expand_effect(
    direction: PyExpandDirection,
    style: PyStyle,
    duration_ms: u32,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::expand(direction.into(), to_core_style(style.inner), make_timer(duration_ms, interpolation)),
    }
}

#[pyfunction]
#[pyo3(signature = (direction, style, duration_ms, interpolation=None))]
fn stretch_effect(
    direction: PyMotion,
    style: PyStyle,
    duration_ms: u32,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    PyEffect {
        inner: fx::stretch(direction.into(), to_core_style(style.inner), make_timer(duration_ms, interpolation)),
    }
}

#[pyfunction]
#[pyo3(signature = (initial_size, duration_ms, effect=None, interpolation=None))]
#[allow(deprecated)]
fn resize_area_effect(
    initial_size: PySize,
    duration_ms: u32,
    effect: Option<PyEffect>,
    interpolation: Option<PyInterpolation>,
) -> PyEffect {
    let size = ratatui_core::layout::Size::new(initial_size.inner.width, initial_size.inner.height);
    PyEffect {
        inner: fx::resize_area(effect.map(|e| e.inner), size, make_timer(duration_ms, interpolation)),
    }
}

#[pyfunction]
fn freeze_at_effect(alpha: f32, set_raw_alpha: bool, effect: PyEffect) -> PyEffect {
    PyEffect {
        inner: fx::freeze_at(alpha, set_raw_alpha, effect.inner),
    }
}

#[pyfunction]
fn remap_alpha_effect(alpha_start: f32, alpha_end: f32, effect: PyEffect) -> PyEffect {
    PyEffect {
        inner: fx::remap_alpha(alpha_start, alpha_end, effect.inner),
    }
}

#[pyfunction]
fn never_complete_effect(effect: PyEffect) -> PyEffect {
    PyEffect {
        inner: fx::never_complete(effect.inner),
    }
}

#[pyfunction]
fn run_once_effect(effect: PyEffect) -> PyEffect {
    PyEffect {
        inner: fx::run_once(effect.inner),
    }
}

#[pyfunction]
fn consume_tick_effect() -> PyEffect {
    PyEffect {
        inner: fx::consume_tick(),
    }
}

#[pyfunction]
fn with_duration_effect(duration_ms: u32, effect: PyEffect) -> PyEffect {
    PyEffect {
        inner: fx::with_duration(Duration::from_millis(duration_ms), effect.inner),
    }
}

#[pyfunction]
fn timed_never_complete_effect(duration_ms: u32, effect: PyEffect) -> PyEffect {
    PyEffect {
        inner: fx::timed_never_complete(Duration::from_millis(duration_ms), effect.inner),
    }
}

#[pyclass(name = "EffectManager", module = "xnano_core.rust.native", unsendable)]
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
    m.add_class::<PyDuration>()?;
    m.add_class::<PyEffectTimer>()?;
    m.add_class::<PyRepeatMode>()?;
    m.add_class::<PyRefRect>()?;
    m.add_class::<PyRadialPattern>()?;
    m.add_class::<PyExpandDirection>()?;
    m.add_class::<PyEvolveSymbolSet>()?;
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
    m.add_function(wrap_pyfunction!(saturate_bg, m)?)?;
    m.add_function(wrap_pyfunction!(lighten, m)?)?;
    m.add_function(wrap_pyfunction!(lighten_fg, m)?)?;
    m.add_function(wrap_pyfunction!(lighten_bg, m)?)?;
    m.add_function(wrap_pyfunction!(darken, m)?)?;
    m.add_function(wrap_pyfunction!(darken_fg, m)?)?;
    m.add_function(wrap_pyfunction!(darken_bg, m)?)?;
    m.add_function(wrap_pyfunction!(hsl_shift, m)?)?;
    m.add_function(wrap_pyfunction!(hsl_shift_fg, m)?)?;
    m.add_function(wrap_pyfunction!(hsl_shift_bg, m)?)?;
    m.add_function(wrap_pyfunction!(evolve_effect, m)?)?;
    m.add_function(wrap_pyfunction!(evolve_into_effect, m)?)?;
    m.add_function(wrap_pyfunction!(evolve_from_effect, m)?)?;
    m.add_function(wrap_pyfunction!(explode_effect, m)?)?;
    m.add_function(wrap_pyfunction!(glitch_effect, m)?)?;
    m.add_function(wrap_pyfunction!(translate_effect, m)?)?;
    m.add_function(wrap_pyfunction!(expand_effect, m)?)?;
    m.add_function(wrap_pyfunction!(stretch_effect, m)?)?;
    m.add_function(wrap_pyfunction!(resize_area_effect, m)?)?;
    m.add_function(wrap_pyfunction!(freeze_at_effect, m)?)?;
    m.add_function(wrap_pyfunction!(remap_alpha_effect, m)?)?;
    m.add_function(wrap_pyfunction!(never_complete_effect, m)?)?;
    m.add_function(wrap_pyfunction!(run_once_effect, m)?)?;
    m.add_function(wrap_pyfunction!(consume_tick_effect, m)?)?;
    m.add_function(wrap_pyfunction!(with_duration_effect, m)?)?;
    m.add_function(wrap_pyfunction!(timed_never_complete_effect, m)?)?;
    Ok(())
}
