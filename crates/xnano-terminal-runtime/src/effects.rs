//! Animated effects: a tree of settings that builds tachyonfx effects and stays editable.
//!
//! # How the pieces fit
//!
//! - An [`EffectNode`] is one node of an effect tree: a [`Kind`] (what it does), plus
//!   modifiers every node shares (area, cell filter, pattern, reversal, seed, color space).
//!   Nodes are held in a [`Shared`] spec, so the Python object that edits a node and the
//!   running effect that reads it see the same settings. Combinators hold their children as
//!   shared nodes too, so editing a child edits every tree it is part of.
//! - Every value a user may want to change is a [`Dynamic`]: fixed, or bound to an expression.
//! - [`EffectNode::resolve`] reads every bound value once and returns a plain [`Plan`].
//!   [`Plan::build`] turns the plan into a `tachyonfx::Effect`.
//! - [`RunningEffect`] owns one built effect. Each frame it resolves the tree again; when the
//!   plan differs from the one that was built it rebuilds the effect and fast-forwards it to
//!   the elapsed time, so a changed parameter keeps the animation's progress.
//!
//! # Adding a leaf effect (about 20 lines)
//!
//! 1. Add a variant to [`Kind`] holding its settings as [`Dynamic`] values (and a [`Timer`]
//!    when it is timed).
//! 2. Add a matching variant to [`PlanKind`] holding the resolved, plain values, and the arm
//!    in [`Kind::resolve`] that reads each [`Dynamic`] with the [`Resolver`].
//! 3. Add the arm in [`PlanKind::build`] that calls the `tachyonfx::fx` constructor.
//! 4. Add a constructor classmethod in the bindings (`crates/xnano-terminal-core/src/effects.rs`)
//!    and the property arms in `Kind` accessors there if the new settings are editable.
//!
//! Nothing else changes: modifiers, the manager, dynamics and progress carry-over apply to
//! every variant.
//!
//! # Which parameters can change mid-flight
//!
//! All of them. A change rebuilds the underlying effect and replays the elapsed time, so
//! timers keep their progress; effects that keep per-cell random state (dissolve, glitch)
//! reshuffle it when rebuilt.

use std::fmt;
use std::hash::{Hash, Hasher};
use std::sync::Arc;

use ratatui_core::buffer::Buffer;
use ratatui_core::layout::{Margin, Rect};
use ratatui_core::style::Color;
use tachyonfx::fx::{self, RepeatMode};
use tachyonfx::{
    CellFilter, ColorSpace, Duration, Effect, EffectTimer, Interpolation, IntoEffect, Shader,
    SimpleRng,
};

use crate::dynamic::Dynamic;
use crate::expression::{Environment, EvalError};
use crate::geometry::Rectangle;
use crate::grid::{Bounds, Grid};
use crate::painter::Spec;
use crate::widgets::style::StyleSpec;
use crate::widgets::{Resolver, Shared};

/// Every easing curve, by its Python name.
pub const INTERPOLATIONS: [(&str, Interpolation); 35] = [
    ("back_in", Interpolation::BackIn),
    ("back_out", Interpolation::BackOut),
    ("back_in_out", Interpolation::BackInOut),
    ("bounce_in", Interpolation::BounceIn),
    ("bounce_out", Interpolation::BounceOut),
    ("bounce_in_out", Interpolation::BounceInOut),
    ("circ_in", Interpolation::CircIn),
    ("circ_out", Interpolation::CircOut),
    ("circ_in_out", Interpolation::CircInOut),
    ("cubic_in", Interpolation::CubicIn),
    ("cubic_out", Interpolation::CubicOut),
    ("cubic_in_out", Interpolation::CubicInOut),
    ("elastic_in", Interpolation::ElasticIn),
    ("elastic_out", Interpolation::ElasticOut),
    ("elastic_in_out", Interpolation::ElasticInOut),
    ("expo_in", Interpolation::ExpoIn),
    ("expo_out", Interpolation::ExpoOut),
    ("expo_in_out", Interpolation::ExpoInOut),
    ("linear", Interpolation::Linear),
    ("quad_in", Interpolation::QuadIn),
    ("quad_out", Interpolation::QuadOut),
    ("quad_in_out", Interpolation::QuadInOut),
    ("quart_in", Interpolation::QuartIn),
    ("quart_out", Interpolation::QuartOut),
    ("quart_in_out", Interpolation::QuartInOut),
    ("quint_in", Interpolation::QuintIn),
    ("quint_out", Interpolation::QuintOut),
    ("quint_in_out", Interpolation::QuintInOut),
    ("reverse", Interpolation::Reverse),
    ("smooth_step", Interpolation::SmoothStep),
    ("spring", Interpolation::Spring),
    ("sine_in", Interpolation::SineIn),
    ("sine_out", Interpolation::SineOut),
    ("sine_in_out", Interpolation::SineInOut),
    // Legacy spellings of the quadratic curves.
    ("ease_in", Interpolation::QuadIn),
];

/// The easing curve called `name`.
pub fn interpolation_from_name(name: &str) -> Option<Interpolation> {
    INTERPOLATIONS
        .iter()
        .find(|(candidate, _)| *candidate == name)
        .map(|(_, interpolation)| *interpolation)
}

/// The name of an easing curve.
pub fn interpolation_name(interpolation: Interpolation) -> &'static str {
    INTERPOLATIONS
        .iter()
        .find(|(_, candidate)| *candidate == interpolation)
        .map_or("linear", |(name, _)| name)
}

/// The names accepted for an easing curve, for error messages.
pub fn interpolation_names() -> String {
    INTERPOLATIONS
        .iter()
        .take(INTERPOLATIONS.len() - 1)
        .map(|(name, _)| *name)
        .collect::<Vec<_>>()
        .join(", ")
}

/// The color space called `name` (`rgb`, `hsl` or `hsv`).
pub fn color_space_from_name(name: &str) -> Option<ColorSpace> {
    Some(match name {
        "rgb" => ColorSpace::Rgb,
        "hsl" => ColorSpace::Hsl,
        "hsv" => ColorSpace::Hsv,
        _ => return None,
    })
}

// ---------------------------------------------------------------------------------------
// Cell filters

/// Which cells of an effect's area it touches. Mirrors `tachyonfx::CellFilter`.
#[derive(Debug, Clone, PartialEq)]
pub enum FilterSpec {
    All,
    Text,
    NonEmpty,
    Background,
    BackgroundOnly,
    ForegroundColor(Color),
    BackgroundColor(Color),
    /// A rectangle relative to the target the effect runs on.
    Area(Rectangle),
    Inner {
        horizontal: u16,
        vertical: u16,
    },
    Outer {
        horizontal: u16,
        vertical: u16,
    },
    AllOf(Vec<FilterSpec>),
    AnyOf(Vec<FilterSpec>),
    NoneOf(Vec<FilterSpec>),
    Not(Box<FilterSpec>),
}

impl FilterSpec {
    /// The tachyonfx filter; `origin` places relative areas on the frame.
    pub fn to_filter(&self, origin: (i32, i32)) -> CellFilter {
        let many = |filters: &[FilterSpec]| filters.iter().map(|f| f.to_filter(origin)).collect();
        match self {
            Self::All => CellFilter::All,
            Self::Text => CellFilter::Text,
            Self::NonEmpty => CellFilter::NonEmpty,
            Self::Background | Self::BackgroundOnly => {
                CellFilter::BgColor(ratatui_core::style::Color::Reset)
            }
            Self::ForegroundColor(color) => CellFilter::FgColor(*color),
            Self::BackgroundColor(color) => CellFilter::BgColor(*color),
            Self::Area(area) => CellFilter::Area(to_rect(area.translate(origin.0, origin.1))),
            Self::Inner {
                horizontal,
                vertical,
            } => CellFilter::Inner(Margin::new(*horizontal, *vertical)),
            Self::Outer {
                horizontal,
                vertical,
            } => CellFilter::Outer(Margin::new(*horizontal, *vertical)),
            Self::AllOf(filters) => CellFilter::AllOf(many(filters)),
            Self::AnyOf(filters) => CellFilter::AnyOf(many(filters)),
            Self::NoneOf(filters) => CellFilter::NoneOf(many(filters)),
            Self::Not(filter) => CellFilter::Not(Box::new(filter.to_filter(origin))),
        }
    }
}

fn to_rect(rectangle: Rectangle) -> Rect {
    let clamp = |value: i32| value.clamp(0, i32::from(u16::MAX)) as u16;
    Rect::new(
        clamp(rectangle.x),
        clamp(rectangle.y),
        clamp(rectangle.width),
        clamp(rectangle.height),
    )
}

// ---------------------------------------------------------------------------------------
// Patterns

/// The shape a pattern-capable effect spreads in. Mirrors `tachyonfx::pattern`.
#[derive(Debug, Clone, PartialEq)]
pub enum PatternSpec {
    Radial {
        center_x: f32,
        center_y: f32,
        transition_width: f32,
    },
    Diamond {
        center_x: f32,
        center_y: f32,
        transition_width: f32,
    },
    Spiral {
        center_x: f32,
        center_y: f32,
        transition_width: f32,
        arms: u16,
    },
    Checkerboard {
        cell_size: u16,
        transition_width: f32,
    },
    /// `direction` is one of `left_to_right`, `right_to_left`, `up_to_down`, `down_to_up`.
    Sweep {
        direction: String,
        gradient_span: u16,
    },
    /// `direction` is one of `top_left_to_bottom_right`, `top_right_to_bottom_left`,
    /// `bottom_left_to_top_right`, `bottom_right_to_top_left`.
    Diagonal {
        direction: String,
        transition_width: f32,
    },
    Coalesce,
    Dissolve,
    Inverted(Box<PatternSpec>),
    Blend(Box<PatternSpec>, Box<PatternSpec>),
}

/// The motion directions, by name.
pub const MOTIONS: [(&str, tachyonfx::Motion); 4] = [
    ("left_to_right", tachyonfx::Motion::LeftToRight),
    ("right_to_left", tachyonfx::Motion::RightToLeft),
    ("up_to_down", tachyonfx::Motion::UpToDown),
    ("down_to_up", tachyonfx::Motion::DownToUp),
];

pub fn motion_from_name(name: &str) -> Option<tachyonfx::Motion> {
    MOTIONS
        .iter()
        .find(|(candidate, _)| *candidate == name)
        .map(|(_, motion)| *motion)
}

impl PatternSpec {
    /// The tachyonfx pattern, or why the settings are invalid.
    pub fn to_pattern(&self) -> Result<tachyonfx::pattern::AnyPattern, String> {
        use tachyonfx::pattern::{
            AnyPattern, BlendPattern, CheckerboardPattern, CoalescePattern, DiagonalDirection,
            DiagonalPattern, DiamondPattern, DissolvePattern, InvertedPattern, RadialPattern,
            SpiralPattern, SweepPattern,
        };
        Ok(match self {
            Self::Radial {
                center_x,
                center_y,
                transition_width,
            } => RadialPattern::with_transition((*center_x, *center_y), *transition_width).into(),
            Self::Diamond {
                center_x,
                center_y,
                transition_width,
            } => DiamondPattern::with_transition((*center_x, *center_y), *transition_width).into(),
            Self::Spiral {
                center_x,
                center_y,
                transition_width,
                arms,
            } => SpiralPattern::with_transition((*center_x, *center_y), *transition_width)
                .with_arms(*arms)
                .into(),
            Self::Checkerboard {
                cell_size,
                transition_width,
            } => CheckerboardPattern::new(*cell_size, *transition_width).into(),
            Self::Sweep {
                direction,
                gradient_span,
            } => {
                let motion = motion_from_name(direction).ok_or_else(|| {
                    format!(
                        "\"{direction}\" is not a sweep direction; use left_to_right, \
                         right_to_left, up_to_down or down_to_up"
                    )
                })?;
                SweepPattern::new(motion, *gradient_span).into()
            }
            Self::Diagonal {
                direction,
                transition_width,
            } => {
                let direction = match direction.as_str() {
                    "top_left_to_bottom_right" => DiagonalDirection::TopLeftToBottomRight,
                    "top_right_to_bottom_left" => DiagonalDirection::TopRightToBottomLeft,
                    "bottom_left_to_top_right" => DiagonalDirection::BottomLeftToTopRight,
                    "bottom_right_to_top_left" => DiagonalDirection::BottomRightToTopLeft,
                    other => {
                        return Err(format!(
                            "\"{other}\" is not a diagonal direction; use top_left_to_bottom_right, \
                             top_right_to_bottom_left, bottom_left_to_top_right or \
                             bottom_right_to_top_left"
                        ));
                    }
                };
                DiagonalPattern::new(direction, *transition_width).into()
            }
            Self::Coalesce => CoalescePattern::new().into(),
            Self::Dissolve => DissolvePattern::new().into(),
            Self::Inverted(inner) => InvertedPattern::new(inner.to_pattern()?).into(),
            Self::Blend(first, second) => {
                BlendPattern::new(first.to_pattern()?, second.to_pattern()?).into()
            }
        })
        .map(|pattern: AnyPattern| pattern)
    }
}

// ---------------------------------------------------------------------------------------
// The editable tree

/// A duration and easing curve.
#[derive(Debug, Clone)]
pub struct Timer {
    pub duration_milliseconds: Dynamic<u32>,
    /// An easing name from [`INTERPOLATIONS`].
    pub interpolation: Dynamic<String>,
}

impl Timer {
    pub fn new(duration_milliseconds: Dynamic<u32>, interpolation: Dynamic<String>) -> Self {
        Self {
            duration_milliseconds,
            interpolation,
        }
    }

    fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<ResolvedTimer, EvalError> {
        let name = resolver.get(&self.interpolation)?;
        let interpolation = interpolation_from_name(&name).ok_or_else(|| {
            EvalError::Type(format!(
                "\"{name}\" is not an interpolation; use one of {}",
                interpolation_names()
            ))
        })?;
        Ok(ResolvedTimer {
            duration_milliseconds: resolver.get(&self.duration_milliseconds)?,
            interpolation,
        })
    }
}

/// How often a repeat runs.
#[derive(Debug, Clone)]
pub enum RepeatSpec {
    Forever,
    Times(Dynamic<u32>),
    Milliseconds(Dynamic<u32>),
}

/// The three brightness adjustments that share one shape.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Adjustment {
    Saturate,
    Lighten,
    Darken,
}

impl Adjustment {
    pub fn name(self) -> &'static str {
        match self {
            Self::Saturate => "saturate",
            Self::Lighten => "lighten",
            Self::Darken => "darken",
        }
    }
}

/// How an evolve effect treats the content underneath.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EvolveMode {
    Full,
    Into,
    From,
}

/// Every symbol set an evolve effect can step through, by its Python name.
pub const EVOLVE_SYMBOL_SETS: [(&str, fx::EvolveSymbolSet); 7] = [
    ("blocks_horizontal", fx::EvolveSymbolSet::BlocksHorizontal),
    ("blocks_vertical", fx::EvolveSymbolSet::BlocksVertical),
    ("circle_fill", fx::EvolveSymbolSet::CircleFill),
    ("circles", fx::EvolveSymbolSet::Circles),
    ("quadrants", fx::EvolveSymbolSet::Quadrants),
    ("shaded", fx::EvolveSymbolSet::Shaded),
    ("squares", fx::EvolveSymbolSet::Squares),
];

fn evolve_symbols(name: &str) -> Result<fx::EvolveSymbolSet, EvalError> {
    EVOLVE_SYMBOL_SETS
        .iter()
        .find(|(candidate, _)| *candidate == name)
        .map(|(_, set)| *set)
        .ok_or_else(|| {
            EvalError::Type(format!(
                "{name} is not a symbol set; use blocks_horizontal, blocks_vertical, \
                 circle_fill, circles, quadrants, shaded or squares"
            ))
        })
}

/// What an effect does. See the module documentation for how to add a variant.
#[derive(Debug, Clone)]
pub enum Kind {
    Spatial {
        name: String,
        direction: Dynamic<String>,
        gradient_length: Dynamic<u16>,
        randomness: Dynamic<u16>,
        color: Dynamic<Color>,
        timer: Timer,
    },
    /// Move colors toward (or, with `is_from`, from) the given ones.
    Fade {
        foreground: Option<Dynamic<Color>>,
        background: Option<Dynamic<Color>>,
        is_from: bool,
        timer: Timer,
    },
    /// Replace colors outright, blending in over the timer.
    Paint {
        foreground: Option<Dynamic<Color>>,
        background: Option<Dynamic<Color>>,
        timer: Timer,
    },
    /// Shift hue, saturation and lightness (degrees, percent, percent).
    HslShift {
        foreground: Option<[Dynamic<f32>; 3]>,
        background: Option<[Dynamic<f32>; 3]>,
        timer: Timer,
    },
    /// Change saturation, lightness or darkness by an amount.
    Adjust {
        adjustment: Adjustment,
        foreground: Option<Dynamic<f32>>,
        background: Option<Dynamic<f32>>,
        timer: Timer,
    },
    /// Remove cells at random (`dissolve`), or bring them back (`coalesce`).
    Dissolve {
        is_coalesce: bool,
        style: Option<StyleSpec>,
        timer: Timer,
    },
    /// Corrupt random cells.
    Glitch {
        cell_ratio: Dynamic<f32>,
        start_delay_milliseconds: [Dynamic<u32>; 2],
        action_milliseconds: [Dynamic<u32>; 2],
        duration_milliseconds: Dynamic<u32>,
    },
    /// Quantize colors to the 256-color palette.
    Term256Colors,
    /// Step cells through a set of symbols: all the way (`full`), or into (`into`) or from
    /// (`from`) the content underneath.
    Evolve {
        mode: String,
        symbols: Dynamic<String>,
        style: Option<StyleSpec>,
        timer: Timer,
    },
    /// Grow a style outward from the center, horizontally or vertically.
    Expand {
        direction: Dynamic<String>,
        style: StyleSpec,
        timer: Timer,
    },
    /// Stretch a style across the area in a direction.
    Stretch {
        direction: Dynamic<String>,
        style: StyleSpec,
        timer: Timer,
    },
    /// Blow cells outward.
    Explode {
        force: Dynamic<f32>,
        randomness: Dynamic<f32>,
        timer: Timer,
    },
    /// Move the cells a child effect draws by an offset.
    Translate {
        child: Shared<EffectNode>,
        x: Dynamic<i32>,
        y: Dynamic<i32>,
        timer: Timer,
    },
    /// Do nothing for a while.
    Sleep {
        timer: Timer,
    },
    Sequence(Vec<Shared<EffectNode>>),
    Parallel(Vec<Shared<EffectNode>>),
    Repeat {
        child: Shared<EffectNode>,
        repeat: RepeatSpec,
    },
    PingPong(Shared<EffectNode>),
    Repeating(Shared<EffectNode>),
    Delay {
        child: Shared<EffectNode>,
        milliseconds: Dynamic<u32>,
    },
    ProlongStart {
        child: Shared<EffectNode>,
        milliseconds: Dynamic<u32>,
    },
    ProlongEnd {
        child: Shared<EffectNode>,
        milliseconds: Dynamic<u32>,
    },
    FreezeAt {
        child: Shared<EffectNode>,
        alpha: Dynamic<f32>,
        should_set_raw_alpha: bool,
    },
    RemapAlpha {
        child: Shared<EffectNode>,
        start: Dynamic<f32>,
        end: Dynamic<f32>,
    },
    WithDuration {
        child: Shared<EffectNode>,
        milliseconds: Dynamic<u32>,
    },
    TimedNeverComplete {
        child: Shared<EffectNode>,
        milliseconds: Dynamic<u32>,
    },
    RunOnce(Shared<EffectNode>),
    NeverComplete(Shared<EffectNode>),
    ConsumeTick,
}

impl Kind {
    /// The name of the constructor that makes this kind.
    pub fn name(&self) -> &'static str {
        match self {
            Self::Spatial { name, .. } => match name.as_str() {
                "sweep_in" => "sweep_in",
                "sweep_out" => "sweep_out",
                "slide_in" => "slide_in",
                _ => "slide_out",
            },
            Self::Fade { is_from: false, .. } => "fade_to",
            Self::Fade { is_from: true, .. } => "fade_from",
            Self::Paint { .. } => "paint",
            Self::HslShift { .. } => "hsl_shift",
            Self::Adjust { adjustment, .. } => adjustment.name(),
            Self::Dissolve {
                is_coalesce: false, ..
            } => "dissolve",
            Self::Dissolve {
                is_coalesce: true, ..
            } => "coalesce",
            Self::Glitch { .. } => "glitch",
            Self::Term256Colors => "term256_colors",
            Self::Evolve { mode, .. } => match mode.as_str() {
                "into" => "evolve_into",
                "from" => "evolve_from",
                _ => "evolve",
            },
            Self::Expand { .. } => "expand",
            Self::Stretch { .. } => "stretch",
            Self::Explode { .. } => "explode",
            Self::Translate { .. } => "translate",
            Self::Sleep { .. } => "sleep",
            Self::Sequence(_) => "sequence",
            Self::Parallel(_) => "parallel",
            Self::Repeat { .. } => "repeat",
            Self::PingPong(_) => "ping_pong",
            Self::Repeating(_) => "repeating",
            Self::Delay { .. } => "delay",
            Self::ProlongStart { .. } => "prolong_start",
            Self::ProlongEnd { .. } => "prolong_end",
            Self::FreezeAt { .. } => "freeze_at",
            Self::RemapAlpha { .. } => "remap_alpha",
            Self::WithDuration { .. } => "with_duration",
            Self::TimedNeverComplete { .. } => "timed_never_complete",
            Self::RunOnce(_) => "run_once",
            Self::NeverComplete(_) => "never_complete",
            Self::ConsumeTick => "consume_tick",
        }
    }

    /// The timer of a timed leaf, if this kind has one.
    pub fn timer(&self) -> Option<&Timer> {
        match self {
            Self::Spatial { timer, .. }
            | Self::Fade { timer, .. }
            | Self::Paint { timer, .. }
            | Self::HslShift { timer, .. }
            | Self::Adjust { timer, .. }
            | Self::Dissolve { timer, .. }
            | Self::Evolve { timer, .. }
            | Self::Expand { timer, .. }
            | Self::Stretch { timer, .. }
            | Self::Explode { timer, .. }
            | Self::Translate { timer, .. }
            | Self::Sleep { timer } => Some(timer),
            _ => None,
        }
    }

    pub fn timer_mut(&mut self) -> Option<&mut Timer> {
        match self {
            Self::Spatial { timer, .. }
            | Self::Fade { timer, .. }
            | Self::Paint { timer, .. }
            | Self::HslShift { timer, .. }
            | Self::Adjust { timer, .. }
            | Self::Dissolve { timer, .. }
            | Self::Evolve { timer, .. }
            | Self::Expand { timer, .. }
            | Self::Stretch { timer, .. }
            | Self::Explode { timer, .. }
            | Self::Translate { timer, .. }
            | Self::Sleep { timer } => Some(timer),
            _ => None,
        }
    }

    /// The children of a combinator, in order.
    pub fn children(&self) -> Vec<Shared<EffectNode>> {
        match self {
            Self::Sequence(children) | Self::Parallel(children) => children.clone(),
            Self::Repeat { child, .. }
            | Self::Delay { child, .. }
            | Self::ProlongStart { child, .. }
            | Self::ProlongEnd { child, .. }
            | Self::FreezeAt { child, .. }
            | Self::RemapAlpha { child, .. }
            | Self::WithDuration { child, .. }
            | Self::Translate { child, .. }
            | Self::TimedNeverComplete { child, .. }
            | Self::PingPong(child)
            | Self::Repeating(child)
            | Self::RunOnce(child)
            | Self::NeverComplete(child) => vec![Arc::clone(child)],
            _ => Vec::new(),
        }
    }

    fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<PlanKind, EvalError> {
        let colors = |resolver: &mut Resolver<'_>,
                      foreground: &Option<Dynamic<Color>>,
                      background: &Option<Dynamic<Color>>,
                      name: &str|
         -> Result<(Option<Color>, Option<Color>), EvalError> {
            let pair = (
                resolver.get_optional(foreground)?,
                resolver.get_optional(background)?,
            );
            if pair.0.is_none() && pair.1.is_none() {
                return Err(EvalError::Type(format!(
                    "{name} needs a foreground color, a background color or both; set at least one"
                )));
            }
            Ok(pair)
        };
        let child = |resolver: &mut Resolver<'_>, node: &Shared<EffectNode>| {
            node.read().resolve(resolver).map(Box::new)
        };
        Ok(match self {
            Self::Spatial {
                name,
                direction,
                gradient_length,
                randomness,
                color,
                timer,
            } => {
                let direction_name = resolver.get(direction)?;
                PlanKind::Spatial { name: name.clone(), direction: motion_from_name(&direction_name).ok_or_else(|| EvalError::Type(format!("{direction_name} is not a motion direction; use up_to_down, down_to_up, left_to_right or right_to_left")))?, gradient_length: resolver.get(gradient_length)?, randomness: resolver.get(randomness)?, color: resolver.get(color)?, timer: timer.resolve(resolver)? }
            }
            Self::Fade {
                foreground,
                background,
                is_from,
                timer,
            } => {
                let (foreground, background) = colors(resolver, foreground, background, "a fade")?;
                PlanKind::Fade {
                    foreground,
                    background,
                    is_from: *is_from,
                    timer: timer.resolve(resolver)?,
                }
            }
            Self::Paint {
                foreground,
                background,
                timer,
            } => {
                let (foreground, background) =
                    colors(resolver, foreground, background, "a paint effect")?;
                PlanKind::Paint {
                    foreground,
                    background,
                    timer: timer.resolve(resolver)?,
                }
            }
            Self::HslShift {
                foreground,
                background,
                timer,
            } => {
                let triple = |resolver: &mut Resolver<'_>,
                              value: &Option<[Dynamic<f32>; 3]>|
                 -> Result<Option<[f32; 3]>, EvalError> {
                    value
                        .as_ref()
                        .map(|[a, b, c]| Ok([resolver.get(a)?, resolver.get(b)?, resolver.get(c)?]))
                        .transpose()
                };
                let foreground = triple(resolver, foreground)?;
                let background = triple(resolver, background)?;
                if foreground.is_none() && background.is_none() {
                    return Err(EvalError::Type(
                        "an hsl_shift needs a foreground shift, a background shift or both"
                            .to_owned(),
                    ));
                }
                PlanKind::HslShift {
                    foreground,
                    background,
                    timer: timer.resolve(resolver)?,
                }
            }
            Self::Adjust {
                adjustment,
                foreground,
                background,
                timer,
            } => {
                let foreground = resolver.get_optional(foreground)?;
                let background = resolver.get_optional(background)?;
                if foreground.is_none() && background.is_none() {
                    return Err(EvalError::Type(format!(
                        "{} needs a foreground amount, a background amount or both",
                        adjustment.name()
                    )));
                }
                PlanKind::Adjust {
                    adjustment: *adjustment,
                    foreground,
                    background,
                    timer: timer.resolve(resolver)?,
                }
            }
            Self::Dissolve {
                is_coalesce,
                style,
                timer,
            } => PlanKind::Dissolve {
                is_coalesce: *is_coalesce,
                style: style
                    .as_ref()
                    .map(|style| style.resolve(resolver))
                    .transpose()?,
                timer: timer.resolve(resolver)?,
            },
            Self::Glitch {
                cell_ratio,
                start_delay_milliseconds,
                action_milliseconds,
                duration_milliseconds,
            } => {
                let ratio = resolver.get(cell_ratio)?;
                if !(0.0..=1.0).contains(&ratio) {
                    return Err(EvalError::Type(format!(
                        "a glitch ratio is a fraction from 0.0 to 1.0, not {ratio}"
                    )));
                }
                let range = |resolver: &mut Resolver<'_>,
                             pair: &[Dynamic<u32>; 2],
                             name: &str|
                 -> Result<(u32, u32), EvalError> {
                    let (low, high) = (resolver.get(&pair[0])?, resolver.get(&pair[1])?);
                    if low > high {
                        return Err(EvalError::Type(format!(
                            "the {name} range starts at {low} but ends at {high}; the end must \
                             not be smaller than the start"
                        )));
                    }
                    Ok((low, high))
                };
                PlanKind::Glitch {
                    cell_ratio: ratio,
                    start_delay: range(resolver, start_delay_milliseconds, "glitch start delay")?,
                    action: range(resolver, action_milliseconds, "glitch action")?,
                    duration_milliseconds: resolver.get(duration_milliseconds)?,
                }
            }
            Self::Term256Colors => PlanKind::Term256Colors,
            Self::Evolve {
                mode,
                symbols,
                style,
                timer,
            } => {
                let name = resolver.get(symbols)?;
                PlanKind::Evolve {
                    mode: match mode.as_str() {
                        "into" => EvolveMode::Into,
                        "from" => EvolveMode::From,
                        _ => EvolveMode::Full,
                    },
                    symbols: evolve_symbols(&name)?,
                    style: style
                        .as_ref()
                        .map(|style| style.resolve(resolver))
                        .transpose()?,
                    timer: timer.resolve(resolver)?,
                }
            }
            Self::Expand {
                direction,
                style,
                timer,
            } => {
                let name = resolver.get(direction)?;
                PlanKind::Expand {
                    direction: match name.as_str() {
                        "horizontal" => fx::ExpandDirection::Horizontal,
                        "vertical" => fx::ExpandDirection::Vertical,
                        other => {
                            return Err(EvalError::Type(format!(
                                "{other} is not an expand direction; use horizontal or vertical"
                            )));
                        }
                    },
                    style: style.resolve(resolver)?,
                    timer: timer.resolve(resolver)?,
                }
            }
            Self::Stretch {
                direction,
                style,
                timer,
            } => {
                let name = resolver.get(direction)?;
                PlanKind::Stretch {
                    direction: motion_from_name(&name).ok_or_else(|| {
                        EvalError::Type(format!(
                            "{name} is not a motion direction; use up_to_down, down_to_up, \
                             left_to_right or right_to_left"
                        ))
                    })?,
                    style: style.resolve(resolver)?,
                    timer: timer.resolve(resolver)?,
                }
            }
            Self::Explode {
                force,
                randomness,
                timer,
            } => PlanKind::Explode {
                force: resolver.get(force)?,
                randomness: resolver.get(randomness)?,
                timer: timer.resolve(resolver)?,
            },
            Self::Translate {
                child: node,
                x,
                y,
                timer,
            } => PlanKind::Translate {
                child: child(resolver, node)?,
                x: resolver.get(x)?,
                y: resolver.get(y)?,
                timer: timer.resolve(resolver)?,
            },
            Self::Sleep { timer } => PlanKind::Sleep {
                timer: timer.resolve(resolver)?,
            },
            Self::Sequence(children) | Self::Parallel(children) => {
                let plans = children
                    .iter()
                    .map(|node| node.read().resolve(resolver))
                    .collect::<Result<Vec<_>, _>>()?;
                if matches!(self, Self::Sequence(_)) {
                    PlanKind::Sequence(plans)
                } else {
                    PlanKind::Parallel(plans)
                }
            }
            Self::Repeat {
                child: node,
                repeat,
            } => PlanKind::Repeat {
                child: child(resolver, node)?,
                mode: match repeat {
                    RepeatSpec::Forever => RepeatMode::Forever,
                    RepeatSpec::Times(times) => RepeatMode::Times(resolver.get(times)?),
                    RepeatSpec::Milliseconds(milliseconds) => {
                        RepeatMode::Duration(Duration::from_millis(resolver.get(milliseconds)?))
                    }
                },
            },
            Self::PingPong(node) => PlanKind::PingPong(child(resolver, node)?),
            Self::Repeating(node) => PlanKind::Repeating(child(resolver, node)?),
            Self::Delay {
                child: node,
                milliseconds,
            } => PlanKind::Delay {
                child: child(resolver, node)?,
                milliseconds: resolver.get(milliseconds)?,
            },
            Self::ProlongStart {
                child: node,
                milliseconds,
            } => PlanKind::ProlongStart {
                child: child(resolver, node)?,
                milliseconds: resolver.get(milliseconds)?,
            },
            Self::ProlongEnd {
                child: node,
                milliseconds,
            } => PlanKind::ProlongEnd {
                child: child(resolver, node)?,
                milliseconds: resolver.get(milliseconds)?,
            },
            Self::FreezeAt {
                child: node,
                alpha,
                should_set_raw_alpha,
            } => PlanKind::FreezeAt {
                child: child(resolver, node)?,
                alpha: resolver.get(alpha)?.clamp(0.0, 1.0),
                should_set_raw_alpha: *should_set_raw_alpha,
            },
            Self::RemapAlpha {
                child: node,
                start,
                end,
            } => PlanKind::RemapAlpha {
                child: child(resolver, node)?,
                start: resolver.get(start)?,
                end: resolver.get(end)?,
            },
            Self::WithDuration {
                child: node,
                milliseconds,
            } => PlanKind::WithDuration {
                child: child(resolver, node)?,
                milliseconds: resolver.get(milliseconds)?,
            },
            Self::TimedNeverComplete {
                child: node,
                milliseconds,
            } => PlanKind::TimedNeverComplete {
                child: child(resolver, node)?,
                milliseconds: resolver.get(milliseconds)?,
            },
            Self::RunOnce(node) => PlanKind::RunOnce(child(resolver, node)?),
            Self::NeverComplete(node) => PlanKind::NeverComplete(child(resolver, node)?),
            Self::ConsumeTick => PlanKind::ConsumeTick,
        })
    }
}

/// One node of an effect tree.
#[derive(Debug, Clone)]
pub struct EffectNode {
    pub kind: Kind,
    /// Restrict the effect to a rectangle relative to its target.
    pub area: Option<Dynamic<Rectangle>>,
    /// Restrict the effect to the cells a filter selects.
    pub filter: Option<FilterSpec>,
    pub pattern: Option<PatternSpec>,
    pub is_reversed: Dynamic<bool>,
    /// Seed for the random choices of dissolve and glitch effects.
    pub seed: Option<u32>,
    /// `rgb`, `hsl` or `hsv`; the effect's default when `None`.
    pub color_space: Option<String>,
    /// The name the effect runs under, so starting another with the same key replaces it.
    pub key: Option<String>,
}

impl EffectNode {
    pub fn new(kind: Kind) -> Self {
        Self {
            kind,
            area: None,
            filter: None,
            pattern: None,
            is_reversed: Dynamic::Fixed(false),
            seed: None,
            color_space: None,
            key: None,
        }
    }

    pub fn shared(kind: Kind) -> Shared<Self> {
        Spec::new(Self::new(kind))
    }

    /// Read every bound value in this node and below.
    pub fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Plan, EvalError> {
        let color_space = match &self.color_space {
            None => None,
            Some(name) => Some(color_space_from_name(name).ok_or_else(|| {
                EvalError::Type(format!(
                    "\"{name}\" is not a color space; use \"rgb\", \"hsl\" or \"hsv\""
                ))
            })?),
        };
        if let Some(pattern) = &self.pattern {
            pattern.to_pattern().map_err(EvalError::Type)?;
        }
        Ok(Plan {
            kind: self.kind.resolve(resolver)?,
            area: self
                .area
                .as_ref()
                .map(|area| resolver.get(area))
                .transpose()?,
            filter: self.filter.clone(),
            pattern: self.pattern.clone(),
            is_reversed: resolver.get(&self.is_reversed)?,
            seed: self.seed,
            color_space,
        })
    }
}

// ---------------------------------------------------------------------------------------
// The resolved plan

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ResolvedTimer {
    pub duration_milliseconds: u32,
    pub interpolation: Interpolation,
}

impl ResolvedTimer {
    fn to_timer(self) -> EffectTimer {
        EffectTimer::from_ms(self.duration_milliseconds, self.interpolation)
    }
}

/// A node with every bound value read.
#[derive(Debug, Clone)]
pub struct Plan {
    pub kind: PlanKind,
    pub area: Option<Rectangle>,
    pub filter: Option<FilterSpec>,
    pub pattern: Option<PatternSpec>,
    pub is_reversed: bool,
    pub seed: Option<u32>,
    pub color_space: Option<ColorSpace>,
}

#[derive(Debug, Clone)]
pub enum PlanKind {
    Spatial {
        name: String,
        direction: tachyonfx::Motion,
        gradient_length: u16,
        randomness: u16,
        color: Color,
        timer: ResolvedTimer,
    },
    Fade {
        foreground: Option<Color>,
        background: Option<Color>,
        is_from: bool,
        timer: ResolvedTimer,
    },
    Paint {
        foreground: Option<Color>,
        background: Option<Color>,
        timer: ResolvedTimer,
    },
    HslShift {
        foreground: Option<[f32; 3]>,
        background: Option<[f32; 3]>,
        timer: ResolvedTimer,
    },
    Adjust {
        adjustment: Adjustment,
        foreground: Option<f32>,
        background: Option<f32>,
        timer: ResolvedTimer,
    },
    Dissolve {
        is_coalesce: bool,
        style: Option<ratatui_core::style::Style>,
        timer: ResolvedTimer,
    },
    Glitch {
        cell_ratio: f32,
        start_delay: (u32, u32),
        action: (u32, u32),
        duration_milliseconds: u32,
    },
    Term256Colors,
    Evolve {
        mode: EvolveMode,
        symbols: fx::EvolveSymbolSet,
        style: Option<ratatui_core::style::Style>,
        timer: ResolvedTimer,
    },
    Expand {
        direction: fx::ExpandDirection,
        style: ratatui_core::style::Style,
        timer: ResolvedTimer,
    },
    Stretch {
        direction: tachyonfx::Motion,
        style: ratatui_core::style::Style,
        timer: ResolvedTimer,
    },
    Explode {
        force: f32,
        randomness: f32,
        timer: ResolvedTimer,
    },
    Translate {
        child: Box<Plan>,
        x: i32,
        y: i32,
        timer: ResolvedTimer,
    },
    Sleep {
        timer: ResolvedTimer,
    },
    Sequence(Vec<Plan>),
    Parallel(Vec<Plan>),
    Repeat {
        child: Box<Plan>,
        mode: RepeatMode,
    },
    PingPong(Box<Plan>),
    Repeating(Box<Plan>),
    Delay {
        child: Box<Plan>,
        milliseconds: u32,
    },
    ProlongStart {
        child: Box<Plan>,
        milliseconds: u32,
    },
    ProlongEnd {
        child: Box<Plan>,
        milliseconds: u32,
    },
    FreezeAt {
        child: Box<Plan>,
        alpha: f32,
        should_set_raw_alpha: bool,
    },
    RemapAlpha {
        child: Box<Plan>,
        start: f32,
        end: f32,
    },
    WithDuration {
        child: Box<Plan>,
        milliseconds: u32,
    },
    TimedNeverComplete {
        child: Box<Plan>,
        milliseconds: u32,
    },
    RunOnce(Box<Plan>),
    NeverComplete(Box<Plan>),
    ConsumeTick,
}

/// Blend colors toward a target on the background only (tachyonfx has no public constructor).
fn fade_background(background: Color, is_from: bool, timer: EffectTimer) -> Effect {
    let timer = if is_from { timer.mirrored() } else { timer };
    fx::effect_fn((), timer, move |(), context, cells| {
        let alpha = context.alpha();
        for (_, cell) in cells {
            let blended = ColorSpace::Hsl.lerp(&cell.bg, &background, alpha);
            cell.set_bg(blended);
        }
    })
}

impl Plan {
    /// Build a fresh tachyonfx effect. `origin` is the frame position of the effect's target.
    pub fn build(&self, origin: (i32, i32)) -> Effect {
        let mut effect = self.kind.build(origin, self.seed);
        if let Some(seed) = self.seed {
            effect = effect.with_rng(SimpleRng::new(seed));
        }
        if let Some(color_space) = self.color_space {
            effect = effect.with_color_space(color_space);
        }
        if let Some(pattern) = &self.pattern
            && let Ok(pattern) = pattern.to_pattern()
        {
            effect = effect.with_pattern(pattern);
        }
        if self.is_reversed {
            effect = effect.reversed();
        }
        if let Some(filter) = &self.filter {
            effect = effect.with_filter(filter.to_filter(origin));
        }
        if let Some(area) = self.area {
            effect = effect.with_area(to_rect(area.translate(origin.0, origin.1)));
        }
        effect
    }
}

impl PlanKind {
    fn build(&self, origin: (i32, i32), seed: Option<u32>) -> Effect {
        let child = |plan: &Plan| plan.build(origin);
        match self {
            Self::Spatial {
                name,
                direction,
                gradient_length,
                randomness,
                color,
                timer,
            } => match name.as_str() {
                "sweep_in" => fx::sweep_in(
                    *direction,
                    *gradient_length,
                    *randomness,
                    *color,
                    timer.to_timer(),
                ),
                "sweep_out" => fx::sweep_out(
                    *direction,
                    *gradient_length,
                    *randomness,
                    *color,
                    timer.to_timer(),
                ),
                "slide_in" => fx::slide_in(
                    *direction,
                    *gradient_length,
                    *randomness,
                    *color,
                    timer.to_timer(),
                ),
                _ => fx::slide_out(
                    *direction,
                    *gradient_length,
                    *randomness,
                    *color,
                    timer.to_timer(),
                ),
            },
            Self::Fade {
                foreground,
                background,
                is_from,
                timer,
            } => {
                let timer = timer.to_timer();
                match (foreground, background, is_from) {
                    (Some(fg), Some(bg), false) => fx::fade_to(*fg, *bg, timer),
                    (Some(fg), Some(bg), true) => fx::fade_from(*fg, *bg, timer),
                    (Some(fg), None, false) => fx::fade_to_fg(*fg, timer),
                    (Some(fg), None, true) => fx::fade_from_fg(*fg, timer),
                    (None, Some(bg), is_from) => fade_background(*bg, *is_from, timer),
                    (None, None, _) => fx::sleep(timer),
                }
            }
            Self::Paint {
                foreground,
                background,
                timer,
            } => {
                let timer = timer.to_timer();
                match (foreground, background) {
                    (Some(fg), Some(bg)) => fx::paint(*fg, *bg, timer),
                    (Some(fg), None) => fx::paint_fg(*fg, timer),
                    (None, Some(bg)) => fx::paint_bg(*bg, timer),
                    (None, None) => fx::sleep(timer),
                }
            }
            Self::HslShift {
                foreground,
                background,
                timer,
            } => fx::hsl_shift(*foreground, *background, timer.to_timer()),
            Self::Adjust {
                adjustment,
                foreground,
                background,
                timer,
            } => {
                let timer = timer.to_timer();
                match adjustment {
                    Adjustment::Saturate => fx::saturate(*foreground, *background, timer),
                    Adjustment::Lighten => fx::lighten(*foreground, *background, timer),
                    Adjustment::Darken => fx::darken(*foreground, *background, timer),
                }
            }
            Self::Dissolve {
                is_coalesce,
                style,
                timer,
            } => {
                let timer = timer.to_timer();
                match (is_coalesce, style) {
                    (false, None) => fx::dissolve(timer),
                    (false, Some(style)) => fx::dissolve_to(*style, timer),
                    (true, None) => fx::coalesce(timer),
                    (true, Some(style)) => fx::coalesce_from(*style, timer),
                }
            }
            Self::Glitch {
                cell_ratio,
                start_delay,
                action,
                duration_milliseconds,
            } => {
                let glitch = fx::Glitch::builder()
                    .cell_glitch_ratio(*cell_ratio)
                    .rng(seed.map(SimpleRng::new).unwrap_or_default())
                    .action_start_delay_ms(start_delay.0..start_delay.1.max(start_delay.0 + 1))
                    .action_ms(action.0..action.1.max(action.0 + 1))
                    .build();
                fx::with_duration(
                    Duration::from_millis(*duration_milliseconds),
                    PrintableGlitch {
                        glitch,
                        largest_cell_count: 0,
                    }
                    .into_effect(),
                )
            }
            #[allow(deprecated)]
            Self::Term256Colors => fx::term256_colors(),
            Self::Evolve {
                mode,
                symbols,
                style,
                timer,
            } => {
                let timer = timer.to_timer();
                match (mode, style) {
                    (EvolveMode::Full, None) => fx::evolve(*symbols, timer),
                    (EvolveMode::Full, Some(style)) => fx::evolve((*symbols, *style), timer),
                    (EvolveMode::Into, None) => fx::evolve_into(*symbols, timer),
                    (EvolveMode::Into, Some(style)) => fx::evolve_into((*symbols, *style), timer),
                    (EvolveMode::From, None) => fx::evolve_from(*symbols, timer),
                    (EvolveMode::From, Some(style)) => fx::evolve_from((*symbols, *style), timer),
                }
            }
            Self::Expand {
                direction,
                style,
                timer,
            } => fx::expand(*direction, *style, timer.to_timer()),
            Self::Stretch {
                direction,
                style,
                timer,
            } => fx::stretch(*direction, *style, timer.to_timer()),
            Self::Explode {
                force,
                randomness,
                timer,
            } => fx::explode(*force, *randomness, timer.to_timer()),
            Self::Translate {
                child: plan,
                x,
                y,
                timer,
            } => fx::translate(
                child(plan),
                ratatui_core::layout::Offset { x: *x, y: *y },
                timer.to_timer(),
            ),
            Self::Sleep { timer } => fx::sleep(timer.to_timer()),
            Self::Sequence(plans) => fx::sequence(
                &plans
                    .iter()
                    .map(|plan| plan.build(origin))
                    .collect::<Vec<_>>(),
            ),
            Self::Parallel(plans) => fx::parallel(
                &plans
                    .iter()
                    .map(|plan| plan.build(origin))
                    .collect::<Vec<_>>(),
            ),
            Self::Repeat { child: plan, mode } => fx::repeat(child(plan), *mode),
            Self::PingPong(plan) => fx::ping_pong(child(plan)),
            Self::Repeating(plan) => fx::repeating(child(plan)),
            Self::Delay {
                child: plan,
                milliseconds,
            } => fx::delay(*milliseconds, child(plan)),
            Self::ProlongStart {
                child: plan,
                milliseconds,
            } => fx::prolong_start(*milliseconds, child(plan)),
            Self::ProlongEnd {
                child: plan,
                milliseconds,
            } => fx::prolong_end(*milliseconds, child(plan)),
            Self::FreezeAt {
                child: plan,
                alpha,
                should_set_raw_alpha,
            } => fx::freeze_at(*alpha, *should_set_raw_alpha, child(plan)),
            Self::RemapAlpha {
                child: plan,
                start,
                end,
            } => fx::remap_alpha(*start, *end, child(plan)),
            Self::WithDuration {
                child: plan,
                milliseconds,
            } => fx::with_duration(Duration::from_millis(*milliseconds), child(plan)),
            Self::TimedNeverComplete {
                child: plan,
                milliseconds,
            } => fx::timed_never_complete(Duration::from_millis(*milliseconds), child(plan)),
            Self::RunOnce(plan) => fx::run_once(child(plan)),
            Self::NeverComplete(plan) => fx::never_complete(child(plan)),
            Self::ConsumeTick => fx::consume_tick(),
        }
    }
}

/// A tachyonfx glitch that leaves only printable symbols in its cells.
///
/// The glitch moves a character's byte value by up to nine and clamps the result to
/// 32..=255, so a character near `~` becomes DEL or a C1 control character. A terminal acts
/// on those instead of drawing them, and ratatui panics on them in debug builds. After each
/// frame of the glitch, every control character it can have written becomes the nearest
/// printable ASCII character. Every other method forwards to the glitch.
#[derive(Clone, Debug)]
struct PrintableGlitch {
    glitch: fx::Glitch,
    /// The most cells the glitch's area has held, which bounds how far below the area its
    /// cells can land.
    largest_cell_count: usize,
}

impl Shader for PrintableGlitch {
    fn name(&self) -> &'static str {
        self.glitch.name()
    }

    fn process(&mut self, duration: Duration, buffer: &mut Buffer, area: Rect) -> Option<Duration> {
        let overflow = self.glitch.process(duration, buffer, area);
        // The glitch keeps the cells it chose before its area shrank. They land below the
        // area in the same columns, within the rows the larger area's cells fill at the
        // current width.
        let width = usize::from(area.width);
        self.largest_cell_count = self
            .largest_cell_count
            .max(width * usize::from(area.height));
        let rows = self.largest_cell_count.div_ceil(width.max(1));
        let written = Rect {
            height: u16::try_from(rows).unwrap_or(u16::MAX),
            ..area
        }
        .intersection(buffer.area);
        let row_length = usize::from(written.width);
        for y in written.top()..written.bottom() {
            let row_start = buffer.index_of(written.x, y);
            for cell in &mut buffer.content[row_start..row_start + row_length] {
                if let Some(replacement) = printable_replacement(cell.symbol()) {
                    cell.set_char(replacement);
                }
            }
        }
        overflow
    }

    fn done(&self) -> bool {
        self.glitch.done()
    }

    fn clone_box(&self) -> Box<dyn Shader> {
        Box::new(self.clone())
    }

    fn area(&self) -> Option<Rect> {
        self.glitch.area()
    }

    fn set_area(&mut self, area: Rect) {
        self.glitch.set_area(area);
    }

    fn filter(&mut self, filter: CellFilter) {
        self.glitch.filter(filter);
    }

    fn timer_mut(&mut self) -> Option<&mut EffectTimer> {
        self.glitch.timer_mut()
    }

    fn cell_filter(&self) -> Option<&CellFilter> {
        self.glitch.cell_filter()
    }

    fn reset(&mut self) {
        self.glitch.reset();
        self.largest_cell_count = 0;
    }

    fn set_rng(&mut self, rng: SimpleRng) {
        self.glitch.set_rng(rng);
    }
}

/// The printable ASCII character nearest to `symbol` when it is a control character:
/// a space for C0 control characters, `~` for DEL and the C1 control characters.
fn printable_replacement(symbol: &str) -> Option<char> {
    match symbol.as_bytes() {
        // DEL, and U+0080..=U+009F in UTF-8.
        [0x7F] | [0xC2, 0x80..=0x9F] => Some('~'),
        [byte] if byte.is_ascii_control() => Some(' '),
        _ => None,
    }
}

// ---------------------------------------------------------------------------------------
// Running

/// Where and how a started effect runs.
#[derive(Debug, Clone, Default)]
pub struct Placement {
    /// A rectangle relative to the target, overriding the effect's own.
    pub area: Option<Rectangle>,
    /// A filter overriding the effect's own.
    pub filter: Option<FilterSpec>,
}

/// One started effect: the tree, the effect built from it and its progress.
pub struct EffectRun {
    pub spec: Shared<EffectNode>,
    effect: Option<Effect>,
    built_from: Option<u64>,
    elapsed_milliseconds: u64,
    is_started: bool,
    /// Whether tachyonfx failed while running the effect, which ends it.
    has_failed: bool,
}

impl fmt::Debug for EffectRun {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "EffectRun({} ms, built={})",
            self.elapsed_milliseconds,
            self.effect.is_some()
        )
    }
}

fn plan_fingerprint(plan: &Plan, placement: &Placement, origin: (i32, i32)) -> u64 {
    let mut hasher = std::collections::hash_map::DefaultHasher::new();
    format!("{plan:?}{placement:?}{origin:?}").hash(&mut hasher);
    hasher.finish()
}

impl EffectRun {
    pub fn new(spec: Shared<EffectNode>) -> Self {
        Self {
            spec,
            effect: None,
            built_from: None,
            elapsed_milliseconds: 0,
            is_started: false,
            has_failed: false,
        }
    }

    /// Time the effect has run, in milliseconds.
    pub fn elapsed_milliseconds(&self) -> u64 {
        self.elapsed_milliseconds
    }

    pub fn is_done(&self) -> bool {
        self.has_failed || self.effect.as_ref().is_some_and(Effect::done)
    }

    /// How far the effect has progressed, from 0.0 to 1.0, when it has a timer of its own.
    pub fn progress(&self) -> Option<f32> {
        self.effect
            .as_ref()
            .and_then(Effect::timer)
            .map(|timer| timer.alpha())
    }

    /// Start over from the first frame.
    pub fn restart(&mut self) {
        self.effect = None;
        self.built_from = None;
        self.elapsed_milliseconds = 0;
        self.is_started = false;
        self.has_failed = false;
    }

    /// Run the effect backwards from where it is.
    pub fn reverse(&mut self) {
        if let Some(effect) = &mut self.effect {
            effect.reverse();
        }
    }

    /// Advance by `elapsed_milliseconds` and apply to `bounds` of `frame`.
    ///
    /// Bound values are read through `environment`; when any changed since the effect was
    /// built, it is rebuilt and replayed to the current time first.
    pub fn advance(
        &mut self,
        environment: &dyn Environment,
        elapsed_milliseconds: u32,
        frame: &mut Grid,
        bounds: Bounds,
        origin: (i32, i32),
        placement: &Placement,
    ) -> Result<(), EvalError> {
        let mut resolver = Resolver::new(environment);
        let mut plan = self.spec.read().resolve(&mut resolver)?;
        if let Some(area) = placement.area {
            plan.area = Some(area);
        }
        if let Some(filter) = &placement.filter {
            plan.filter = Some(filter.clone());
        }
        let fingerprint = plan_fingerprint(&plan, placement, origin);
        let area = Rect::new(bounds.left, bounds.top, bounds.width(), bounds.height());
        let step = if self.is_started {
            elapsed_milliseconds
        } else {
            0
        };
        if self.built_from != Some(fingerprint) {
            let mut effect = plan.build(origin);
            if self.elapsed_milliseconds > 0 {
                let mut scratch = Buffer::empty(Rect::new(
                    0,
                    0,
                    frame.width().max(area.right()),
                    frame.height().max(area.bottom()),
                ));
                effect.process(
                    Duration::from_millis(self.elapsed_milliseconds.min(u64::from(u32::MAX)) as u32),
                    &mut scratch,
                    area,
                );
            }
            self.effect = Some(effect);
            self.built_from = Some(fingerprint);
        }
        self.is_started = true;
        self.elapsed_milliseconds += u64::from(step);
        if let Some(effect) = &mut self.effect {
            // tachyonfx does plain arithmetic on cell positions, which can overflow for some
            // sizes at the very end of an effect; an effect that fails ends instead of
            // taking the whole runtime down.
            let outcome = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                effect.process(Duration::from_millis(step), frame.buffer_mut(), area);
            }));
            if outcome.is_err() {
                self.effect = None;
                self.has_failed = true;
            }
        }
        Ok(())
    }
}

pub fn fuzz(grid: &mut Grid, bounds: Bounds, intensity: u32, seed: Option<u64>) {
    const GLYPHS: [&str; 10] = ["░", "▒", "▓", "#", "%", "&", "*", "+", "~", "?"];
    let mut state = seed.unwrap_or_else(|| {
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_or(0x9e37_79b9_7f4a_7c15, |elapsed| elapsed.as_nanos() as u64)
    }) | 1;
    let mut next = move || {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        state
    };
    let threshold = u64::from(intensity.min(100));
    for y in bounds.top..bounds.bottom {
        for x in bounds.left..bounds.right {
            let Some(cell) = grid.buffer().cell((x, y)) else {
                continue;
            };
            if cell.symbol().trim().is_empty() || crate::grid::cell_columns(cell) != 1 {
                continue;
            }
            if next() % 100 < threshold
                && let Some(cell) = grid.buffer_mut().cell_mut((x, y))
            {
                cell.set_symbol(GLYPHS[(next() % GLYPHS.len() as u64) as usize]);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::expression::{PropertyId, Scalar};

    struct Offline;
    impl Environment for Offline {
        fn property(&self, id: PropertyId) -> Result<Scalar, EvalError> {
            Err(EvalError::RuntimeRequired(id.name().to_owned()))
        }
    }

    fn timer(milliseconds: u32) -> Timer {
        Timer::new(
            Dynamic::Fixed(milliseconds),
            Dynamic::Fixed("linear".to_owned()),
        )
    }

    fn fade() -> Shared<EffectNode> {
        EffectNode::shared(Kind::Fade {
            foreground: Some(Dynamic::Fixed(Color::Rgb(255, 0, 0))),
            background: None,
            is_from: false,
            timer: timer(100),
        })
    }

    #[test]
    fn rectangle_expressions_resolve_and_wrong_types_are_rejected() {
        use crate::expression::Expr;
        let mut node = EffectNode::new(Kind::ConsumeTick);
        let area = Rectangle::new(2, 1, 3, 1);
        node.area = Some(Dynamic::Bound(Expr::literal(Scalar::Rectangle(area))));
        assert_eq!(
            node.resolve(&mut Resolver::new(&Offline)).unwrap().area,
            Some(area)
        );
        node.area = Some(Dynamic::Bound(Expr::literal(Scalar::Integer(3))));
        assert!(node.resolve(&mut Resolver::new(&Offline)).is_err());
    }

    #[test]
    fn a_fade_reaches_its_color() {
        let mut run = EffectRun::new(fade());
        let mut grid = Grid::new(4, 1);
        let bounds = grid.bounds();
        for step in [0, 50, 60] {
            run.advance(
                &Offline,
                step,
                &mut grid,
                bounds,
                (0, 0),
                &Placement::default(),
            )
            .unwrap();
        }
        assert!(run.is_done());
        assert_eq!(grid.cell(0, 0).unwrap().fg, Color::Rgb(255, 0, 0));
    }

    #[test]
    fn editing_the_spec_rebuilds_and_keeps_progress() {
        let node = fade();
        let mut run = EffectRun::new(Arc::clone(&node));
        let mut grid = Grid::new(4, 1);
        let bounds = grid.bounds();
        for step in [0, 50] {
            run.advance(
                &Offline,
                step,
                &mut grid,
                bounds,
                (0, 0),
                &Placement::default(),
            )
            .unwrap();
        }
        node.edit(|node| {
            if let Kind::Fade { timer, .. } = &mut node.kind {
                timer.duration_milliseconds = Dynamic::Fixed(1000);
            }
        });
        run.advance(
            &Offline,
            10,
            &mut grid,
            bounds,
            (0, 0),
            &Placement::default(),
        )
        .unwrap();
        assert!(!run.is_done());
        assert!(run.progress().unwrap() < 0.1);
        assert_eq!(run.elapsed_milliseconds(), 60);
    }

    #[test]
    fn invalid_settings_are_reported() {
        let node = EffectNode::shared(Kind::Fade {
            foreground: None,
            background: None,
            is_from: false,
            timer: timer(100),
        });
        let mut run = EffectRun::new(node);
        let mut grid = Grid::new(1, 1);
        let bounds = grid.bounds();
        let error = run
            .advance(
                &Offline,
                0,
                &mut grid,
                bounds,
                (0, 0),
                &Placement::default(),
            )
            .unwrap_err();
        assert!(error.to_string().contains("foreground"));
    }

    #[test]
    fn a_glitch_writes_only_printable_symbols() {
        // A glitch that moves `~` up by any amount passes the end of printable ASCII.
        let node = EffectNode::shared(Kind::Glitch {
            cell_ratio: Dynamic::Fixed(1.0),
            start_delay_milliseconds: [Dynamic::Fixed(0), Dynamic::Fixed(1)],
            action_milliseconds: [Dynamic::Fixed(40), Dynamic::Fixed(250)],
            duration_milliseconds: Dynamic::Fixed(1000),
        });
        let mut run = EffectRun::new(node);
        let mut tilde = ratatui_core::buffer::Cell::EMPTY;
        tilde.set_char('~');
        let mut changed_cells = 0;
        // The top row, then a shorter one: cells chosen for the long row land below it.
        for (step, width) in [(0, 40), (20, 40), (20, 40), (20, 10), (20, 10)] {
            let mut grid = Grid::filled(40, 4, &tilde);
            let bounds = Bounds {
                left: 0,
                top: 0,
                right: width,
                bottom: 1,
            };
            run.advance(
                &Offline,
                step,
                &mut grid,
                bounds,
                (0, 0),
                &Placement::default(),
            )
            .unwrap();
            for cell in &grid.buffer().content {
                let symbol = cell.symbol();
                assert!(
                    !symbol.chars().any(char::is_control),
                    "the glitch wrote {symbol:?}"
                );
                changed_cells += usize::from(symbol != "~");
            }
        }
        assert!(changed_cells > 0);
    }

    #[test]
    fn every_interpolation_name_round_trips() {
        for (name, interpolation) in INTERPOLATIONS.iter().take(INTERPOLATIONS.len() - 1) {
            assert_eq!(interpolation_from_name(name), Some(*interpolation));
            assert_eq!(interpolation_name(*interpolation), *name);
        }
    }
}
