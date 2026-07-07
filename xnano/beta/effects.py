"""xnano.beta.effect"""

from __future__ import annotations

import abc
import dataclasses
from typing import Literal, Sequence, TypeAlias, overload

from xnano.beta.color import ColorLike
from xnano.beta.utils.native_types import get_native_color_from_color_like
from xnano_core.rust import native


EffectMotion: TypeAlias = Literal[
    "up_to_down",
    "down_to_up",
    "left_to_right",
    "right_to_left",
]
"""Directional motion for slide and sweep effects.

Values:
    ``"up_to_down"``: Motion travels from the top edge downward.
    ``"down_to_up"``: Motion travels from the bottom edge upward.
    ``"left_to_right"``: Motion travels from the left edge rightward.
    ``"right_to_left"``: Motion travels from the right edge leftward.
"""


EffectInterpolation: TypeAlias = Literal[
    "linear",
    "smooth_step",
    "sine_in",
    "sine_out",
    "sine_in_out",
    "quad_in",
    "quad_out",
    "quad_in_out",
    "cubic_in",
    "cubic_out",
    "cubic_in_out",
    "expo_in",
    "expo_out",
    "expo_in_out",
    "bounce_in",
    "bounce_out",
    "bounce_in_out",
    "elastic_in",
    "elastic_out",
    "elastic_in_out",
    "back_in",
    "back_out",
    "back_in_out",
    "spring",
]
"""Interpolation curve applied over an effect's duration.

Values:
    ``"linear"``: Constant-rate progression.
    ``"smooth_step"``: Eased start and end with a smooth midpoint.
    ``"sine_in"`` / ``"sine_out"`` / ``"sine_in_out"``: Sinusoidal easing.
    ``"quad_in"`` / ``"quad_out"`` / ``"quad_in_out"``: Quadratic easing.
    ``"cubic_in"`` / ``"cubic_out"`` / ``"cubic_in_out"``: Cubic easing.
    ``"expo_in"`` / ``"expo_out"`` / ``"expo_in_out"``: Exponential easing.
    ``"bounce_in"`` / ``"bounce_out"`` / ``"bounce_in_out"``: Bounce easing.
    ``"elastic_in"`` / ``"elastic_out"`` / ``"elastic_in_out"``: Elastic easing.
    ``"back_in"`` / ``"back_out"`` / ``"back_in_out"``: Overshoot easing.
    ``"spring"``: Spring-like easing.
"""


EffectColorSpace: TypeAlias = Literal["rgb", "hsl", "hsv"]
"""Color interpolation space for color-driven effects.

Values:
    ``"rgb"``: Interpolate in RGB space.
    ``"hsl"``: Interpolate in HSL space.
    ``"hsv"``: Interpolate in HSV space.
"""


KnownEffectKind: TypeAlias = Literal[
    "fade",
    "fade_from",
    "fade_to",
    "fade_from_both",
    "dissolve",
    "coalesce",
    "sweep_in",
    "sweep_out",
    "slide_in",
    "slide_out",
    "paint",
    "paint_fg",
    "paint_bg",
    "sleep",
    "sequence",
    "parallel",
    "repeat",
    "delay",
]
"""Built-in effect kinds that can be composed through :func:`Effect` or
:meth:`~xnano.beta.grid.Grid.grid_play_effect`.

Values:
    ``"fade"``: Fade foreground color to a target.
    ``"fade_from"``: Fade foreground color from a source.
    ``"fade_to"``: Fade foreground and background to targets.
    ``"fade_from_both"``: Fade foreground and background from sources.
    ``"dissolve"``: Random pixel dissolve transition.
    ``"coalesce"``: Typewriter-style cell assembly.
    ``"sweep_in"``: Directional sweep revealing content.
    ``"sweep_out"``: Directional sweep hiding content.
    ``"slide_in"``: Directional slide revealing content.
    ``"slide_out"``: Directional slide hiding content.
    ``"paint"``: Paint foreground and background to targets.
    ``"paint_fg"``: Paint foreground to a target color.
    ``"paint_bg"``: Paint background to a target color.
    ``"sleep"``: No-op delay for sequencing.
    ``"sequence"``: Run child effects one after another.
    ``"parallel"``: Run child effects simultaneously.
    ``"repeat"``: Repeat a child effect.
    ``"delay"``: Delay before starting a child effect.
"""


_MOTION_TO_NATIVE: dict[EffectMotion, native.Motion] = {
    "up_to_down": native.Motion.UpToDown,
    "down_to_up": native.Motion.DownToUp,
    "left_to_right": native.Motion.LeftToRight,
    "right_to_left": native.Motion.RightToLeft,
}

_INTERPOLATION_TO_NATIVE: dict[EffectInterpolation, native.Interpolation] = {
    "linear": native.Interpolation.Linear,
    "smooth_step": native.Interpolation.SmoothStep,
    "sine_in": native.Interpolation.SineIn,
    "sine_out": native.Interpolation.SineOut,
    "sine_in_out": native.Interpolation.SineInOut,
    "quad_in": native.Interpolation.QuadIn,
    "quad_out": native.Interpolation.QuadOut,
    "quad_in_out": native.Interpolation.QuadInOut,
    "cubic_in": native.Interpolation.CubicIn,
    "cubic_out": native.Interpolation.CubicOut,
    "cubic_in_out": native.Interpolation.CubicInOut,
    "expo_in": native.Interpolation.ExpoIn,
    "expo_out": native.Interpolation.ExpoOut,
    "expo_in_out": native.Interpolation.ExpoInOut,
    "bounce_in": native.Interpolation.BounceIn,
    "bounce_out": native.Interpolation.BounceOut,
    "bounce_in_out": native.Interpolation.BounceInOut,
    "elastic_in": native.Interpolation.ElasticIn,
    "elastic_out": native.Interpolation.ElasticOut,
    "elastic_in_out": native.Interpolation.ElasticInOut,
    "back_in": native.Interpolation.BackIn,
    "back_out": native.Interpolation.BackOut,
    "back_in_out": native.Interpolation.BackInOut,
    "spring": native.Interpolation.Spring,
}

_COLOR_SPACE_TO_NATIVE: dict[EffectColorSpace, native.ColorSpace] = {
    "rgb": native.ColorSpace.Rgb,
    "hsl": native.ColorSpace.Hsl,
    "hsv": native.ColorSpace.Hsv,
}


def _resolve_native_motion(motion: EffectMotion) -> native.Motion:
    return _MOTION_TO_NATIVE[motion]


def _resolve_native_interpolation(
    interpolation: EffectInterpolation | None,
) -> native.Interpolation | None:
    if interpolation is None:
        return None
    return _INTERPOLATION_TO_NATIVE[interpolation]


def _resolve_native_color_space(
    color_space: EffectColorSpace | None,
) -> native.ColorSpace | None:
    if color_space is None:
        return None
    return _COLOR_SPACE_TO_NATIVE[color_space]


def _require_native_color(color: ColorLike, *, label: str) -> native.Color:
    resolved = get_native_color_from_color_like(color)
    if resolved is None:
        raise ValueError(f"{label} must resolve to a color, got {color!r}")
    return resolved


@dataclasses.dataclass
class AbstractEffect(abc.ABC):
    """Abstract base for user-composed terminal visual effects.

    Subclasses describe effect intent with ``xnano`` types and literals.
    The framework lowers them to native tachyonfx effects through
    :meth:`build_native_effect`.
    """

    duration_ms: int = dataclasses.field(default=300, kw_only=True)
    """Duration of the effect in milliseconds."""
    interpolation: EffectInterpolation | None = dataclasses.field(
        default=None,
        kw_only=True,
    )
    """Optional interpolation curve for the effect."""

    @abc.abstractmethod
    def build_native_effect(self) -> native.Effect:
        """Lower this effect description to a native effect instance.

        Returns:
            A native :class:`~xnano_core.rust.native.Effect` ready to run.
        """


@dataclasses.dataclass
class FadeEffect(AbstractEffect):
    """Fade foreground color to a target color."""

    color: ColorLike = "white"
    """Target foreground color."""

    def build_native_effect(self) -> native.Effect:
        return native.fade_to_fg(
            _require_native_color(self.color, label="color"),
            self.duration_ms,
            _resolve_native_interpolation(self.interpolation),
        )


@dataclasses.dataclass
class FadeFromEffect(AbstractEffect):
    """Fade foreground color from a source color."""

    color: ColorLike = "white"
    """Source foreground color."""

    def build_native_effect(self) -> native.Effect:
        return native.fade_from_fg(
            _require_native_color(self.color, label="color"),
            self.duration_ms,
            _resolve_native_interpolation(self.interpolation),
        )


@dataclasses.dataclass
class FadeToEffect(AbstractEffect):
    """Fade foreground and background to target colors."""

    color: ColorLike = "white"
    """Target foreground color."""
    background: ColorLike = "black"
    """Target background color."""

    def build_native_effect(self) -> native.Effect:
        return native.fade_to(
            _require_native_color(self.color, label="color"),
            _require_native_color(self.background, label="background"),
            self.duration_ms,
            _resolve_native_interpolation(self.interpolation),
        )


@dataclasses.dataclass
class FadeFromBothEffect(AbstractEffect):
    """Fade foreground and background from source colors."""

    color: ColorLike = "white"
    """Source foreground color."""
    background: ColorLike = "black"
    """Source background color."""

    def build_native_effect(self) -> native.Effect:
        return native.fade_from(
            _require_native_color(self.color, label="color"),
            _require_native_color(self.background, label="background"),
            self.duration_ms,
            _resolve_native_interpolation(self.interpolation),
        )


@dataclasses.dataclass
class DissolveEffect(AbstractEffect):
    """Random pixel dissolve transition."""

    def build_native_effect(self) -> native.Effect:
        return native.dissolve(
            self.duration_ms,
            _resolve_native_interpolation(self.interpolation),
        )


@dataclasses.dataclass
class CoalesceEffect(AbstractEffect):
    """Typewriter-style cell assembly."""

    def build_native_effect(self) -> native.Effect:
        return native.coalesce(
            self.duration_ms,
            _resolve_native_interpolation(self.interpolation),
        )


@dataclasses.dataclass
class DirectionalEffect(AbstractEffect):
    """Shared parameters for slide and sweep effects."""

    direction: EffectMotion = "left_to_right"
    """Direction the effect travels across the target area."""
    gradient_length: int = 14
    """Length of the motion gradient in cells."""
    randomness: int = 2
    """Randomness applied along the gradient."""
    color: ColorLike = "white"
    """Accent color used by the motion gradient."""


@dataclasses.dataclass
class SweepInEffect(DirectionalEffect):
    """Directional sweep revealing content."""

    def build_native_effect(self) -> native.Effect:
        return native.sweep_in(
            _resolve_native_motion(self.direction),
            self.gradient_length,
            self.randomness,
            _require_native_color(self.color, label="color"),
            self.duration_ms,
            _resolve_native_interpolation(self.interpolation),
        )


@dataclasses.dataclass
class SweepOutEffect(DirectionalEffect):
    """Directional sweep hiding content."""

    def build_native_effect(self) -> native.Effect:
        return native.sweep_out(
            _resolve_native_motion(self.direction),
            self.gradient_length,
            self.randomness,
            _require_native_color(self.color, label="color"),
            self.duration_ms,
            _resolve_native_interpolation(self.interpolation),
        )


@dataclasses.dataclass
class SlideInEffect(DirectionalEffect):
    """Directional slide revealing content."""

    def build_native_effect(self) -> native.Effect:
        return native.slide_in(
            _resolve_native_motion(self.direction),
            self.gradient_length,
            self.randomness,
            _require_native_color(self.color, label="color"),
            self.duration_ms,
            _resolve_native_interpolation(self.interpolation),
        )


@dataclasses.dataclass
class SlideOutEffect(DirectionalEffect):
    """Directional slide hiding content."""

    def build_native_effect(self) -> native.Effect:
        return native.slide_out(
            _resolve_native_motion(self.direction),
            self.gradient_length,
            self.randomness,
            _require_native_color(self.color, label="color"),
            self.duration_ms,
            _resolve_native_interpolation(self.interpolation),
        )


@dataclasses.dataclass
class PaintEffect(AbstractEffect):
    """Paint foreground and background to target colors."""

    color: ColorLike = "white"
    """Target foreground color."""
    background: ColorLike = "black"
    """Target background color."""

    def build_native_effect(self) -> native.Effect:
        return native.paint(
            _require_native_color(self.color, label="color"),
            _require_native_color(self.background, label="background"),
            self.duration_ms,
            _resolve_native_interpolation(self.interpolation),
        )


@dataclasses.dataclass
class PaintForegroundEffect(AbstractEffect):
    """Paint foreground to a target color."""

    color: ColorLike = "white"
    """Target foreground color."""

    def build_native_effect(self) -> native.Effect:
        return native.paint_fg(
            _require_native_color(self.color, label="color"),
            self.duration_ms,
            _resolve_native_interpolation(self.interpolation),
        )


@dataclasses.dataclass
class PaintBackgroundEffect(AbstractEffect):
    """Paint background to a target color."""

    background: ColorLike = "black"
    """Target background color."""

    def build_native_effect(self) -> native.Effect:
        return native.paint_bg(
            _require_native_color(self.background, label="background"),
            self.duration_ms,
            _resolve_native_interpolation(self.interpolation),
        )


@dataclasses.dataclass
class SleepEffect(AbstractEffect):
    """No-op delay used when composing effect sequences."""

    def build_native_effect(self) -> native.Effect:
        return native.sleep_effect(self.duration_ms)


@dataclasses.dataclass
class SequenceEffect(AbstractEffect):
    """Run child effects one after another."""

    effects: tuple[AbstractEffect, ...] = ()
    """Child effects to run in order."""

    def build_native_effect(self) -> native.Effect:
        if not self.effects:
            raise ValueError("sequence effects require at least one child")
        return native.sequence_effects(
            [effect.build_native_effect() for effect in self.effects]
        )


@dataclasses.dataclass
class ParallelEffect(AbstractEffect):
    """Run child effects simultaneously."""

    effects: tuple[AbstractEffect, ...] = ()
    """Child effects to run in parallel."""

    def build_native_effect(self) -> native.Effect:
        if not self.effects:
            raise ValueError("parallel effects require at least one child")
        return native.parallel_effects(
            [effect.build_native_effect() for effect in self.effects]
        )


@dataclasses.dataclass
class RepeatEffect(AbstractEffect):
    """Repeat a child effect."""

    child: AbstractEffect | None = None
    """Effect to repeat."""
    times: int | None = None
    """Number of times to repeat the child effect."""

    def build_native_effect(self) -> native.Effect:
        if self.child is None:
            raise ValueError("repeat effects require a child effect")
        child = self.child.build_native_effect()
        if self.times is not None:
            return native.repeat_effect(child, times=self.times)
        if self.duration_ms != 300:
            return native.repeat_effect(child, duration_ms=self.duration_ms)
        return native.repeat_effect(child)


@dataclasses.dataclass
class DelayEffect(AbstractEffect):
    """Delay before starting a child effect."""

    child: AbstractEffect | None = None
    """Effect to start after the delay."""

    def build_native_effect(self) -> native.Effect:
        if self.child is None:
            raise ValueError("delay effects require a child effect")
        return native.delay_effect(
            self.duration_ms,
            self.child.build_native_effect(),
        )


def _normalize_child_effects(
    effects: Sequence[AbstractEffect] | None,
) -> tuple[AbstractEffect, ...]:
    if not effects:
        return ()
    return tuple(effects)


def _build_effect_from_kind(
    kind: KnownEffectKind,
    *,
    duration_ms: int = 300,
    color: ColorLike | None = None,
    background: ColorLike | None = None,
    direction: EffectMotion | None = None,
    gradient_length: int | None = None,
    randomness: int | None = None,
    interpolation: EffectInterpolation | None = None,
    effects: Sequence[AbstractEffect] | None = None,
    child: AbstractEffect | None = None,
    times: int | None = None,
) -> AbstractEffect:
    resolved_direction: EffectMotion = (
        direction if direction is not None else "left_to_right"
    )
    resolved_gradient_length = (
        gradient_length if gradient_length is not None else 14
    )
    resolved_randomness = randomness if randomness is not None else 2
    resolved_color: ColorLike = color if color is not None else "white"
    resolved_background: ColorLike = (
        background if background is not None else "black"
    )

    if kind == "fade":
        return FadeEffect(
            color=resolved_color,
            duration_ms=duration_ms,
            interpolation=interpolation,
        )
    if kind == "fade_from":
        return FadeFromEffect(
            color=resolved_color,
            duration_ms=duration_ms,
            interpolation=interpolation,
        )
    if kind == "fade_to":
        return FadeToEffect(
            color=resolved_color,
            background=resolved_background,
            duration_ms=duration_ms,
            interpolation=interpolation,
        )
    if kind == "fade_from_both":
        return FadeFromBothEffect(
            color=resolved_color,
            background=resolved_background,
            duration_ms=duration_ms,
            interpolation=interpolation,
        )
    if kind == "dissolve":
        return DissolveEffect(
            duration_ms=duration_ms,
            interpolation=interpolation,
        )
    if kind == "coalesce":
        return CoalesceEffect(
            duration_ms=duration_ms,
            interpolation=interpolation,
        )
    if kind == "sweep_in":
        return SweepInEffect(
            direction=resolved_direction,
            gradient_length=resolved_gradient_length,
            randomness=resolved_randomness,
            color=resolved_color,
            duration_ms=duration_ms,
            interpolation=interpolation,
        )
    if kind == "sweep_out":
        return SweepOutEffect(
            direction=resolved_direction,
            gradient_length=resolved_gradient_length,
            randomness=resolved_randomness,
            color=resolved_color,
            duration_ms=duration_ms,
            interpolation=interpolation,
        )
    if kind == "slide_in":
        return SlideInEffect(
            direction=resolved_direction,
            gradient_length=resolved_gradient_length,
            randomness=resolved_randomness,
            color=resolved_color,
            duration_ms=duration_ms,
            interpolation=interpolation,
        )
    if kind == "slide_out":
        return SlideOutEffect(
            direction=resolved_direction,
            gradient_length=resolved_gradient_length,
            randomness=resolved_randomness,
            color=resolved_color,
            duration_ms=duration_ms,
            interpolation=interpolation,
        )
    if kind == "paint":
        return PaintEffect(
            color=resolved_color,
            background=resolved_background,
            duration_ms=duration_ms,
            interpolation=interpolation,
        )
    if kind == "paint_fg":
        return PaintForegroundEffect(
            color=resolved_color,
            duration_ms=duration_ms,
            interpolation=interpolation,
        )
    if kind == "paint_bg":
        return PaintBackgroundEffect(
            background=resolved_background,
            duration_ms=duration_ms,
            interpolation=interpolation,
        )
    if kind == "sleep":
        return SleepEffect(
            duration_ms=duration_ms,
            interpolation=interpolation,
        )
    if kind == "sequence":
        return SequenceEffect(
            effects=_normalize_child_effects(effects),
            duration_ms=duration_ms,
            interpolation=interpolation,
        )
    if kind == "parallel":
        return ParallelEffect(
            effects=_normalize_child_effects(effects),
            duration_ms=duration_ms,
            interpolation=interpolation,
        )
    if kind == "repeat":
        return RepeatEffect(
            child=child,
            times=times,
            duration_ms=duration_ms,
            interpolation=interpolation,
        )
    if kind == "delay":
        return DelayEffect(
            child=child,
            duration_ms=duration_ms,
            interpolation=interpolation,
        )

    raise ValueError(f"unsupported effect kind: {kind!r}")


def resolve_effect(
    effect: AbstractEffect | KnownEffectKind,
    *,
    duration_ms: int = 300,
    color: ColorLike | None = None,
    background: ColorLike | None = None,
    direction: EffectMotion | None = None,
    gradient_length: int | None = None,
    randomness: int | None = None,
    interpolation: EffectInterpolation | None = None,
    effects: Sequence[AbstractEffect] | None = None,
    child: AbstractEffect | None = None,
    times: int | None = None,
) -> AbstractEffect:
    """Resolve an effect description into an :class:`AbstractEffect`.

    Args:
        effect: A built effect instance or a known effect kind string.
        duration_ms: Duration of the effect in milliseconds.
        color: Foreground or accent color for color-driven effects.
        background: Background color for two-color effects.
        direction: Motion direction for slide and sweep effects.
        gradient_length: Gradient length for slide and sweep effects.
        randomness: Randomness for slide and sweep effects.
        interpolation: Interpolation curve for the effect.
        effects: Child effects for sequence and parallel composition.
        child: Child effect for repeat and delay composition.
        times: Repeat count for repeat effects.

    Returns:
        A resolved :class:`AbstractEffect` instance.
    """
    if isinstance(effect, AbstractEffect):
        return effect
    return _build_effect_from_kind(
        effect,
        duration_ms=duration_ms,
        color=color,
        background=background,
        direction=direction,
        gradient_length=gradient_length,
        randomness=randomness,
        interpolation=interpolation,
        effects=effects,
        child=child,
        times=times,
    )


def resolve_native_effect(
    effect: AbstractEffect | KnownEffectKind,
    *,
    duration_ms: int = 300,
    color: ColorLike | None = None,
    background: ColorLike | None = None,
    direction: EffectMotion | None = None,
    gradient_length: int | None = None,
    randomness: int | None = None,
    interpolation: EffectInterpolation | None = None,
    effects: Sequence[AbstractEffect] | None = None,
    child: AbstractEffect | None = None,
    times: int | None = None,
) -> native.Effect:
    """Resolve and lower an effect description to a native effect.

    Args:
        effect: A built effect instance or a known effect kind string.
        duration_ms: Duration of the effect in milliseconds.
        color: Foreground or accent color for color-driven effects.
        background: Background color for two-color effects.
        direction: Motion direction for slide and sweep effects.
        gradient_length: Gradient length for slide and sweep effects.
        randomness: Randomness for slide and sweep effects.
        interpolation: Interpolation curve for the effect.
        effects: Child effects for sequence and parallel composition.
        child: Child effect for repeat and delay composition.
        times: Repeat count for repeat effects.

    Returns:
        A native :class:`~xnano_core.rust.native.Effect` instance.
    """
    return resolve_effect(
        effect,
        duration_ms=duration_ms,
        color=color,
        background=background,
        direction=direction,
        gradient_length=gradient_length,
        randomness=randomness,
        interpolation=interpolation,
        effects=effects,
        child=child,
        times=times,
    ).build_native_effect()


@overload
def Effect(
    effect: KnownEffectKind,
    *,
    duration_ms: int = 300,
    color: ColorLike | None = None,
    background: ColorLike | None = None,
    direction: EffectMotion | None = None,
    gradient_length: int | None = None,
    randomness: int | None = None,
    interpolation: EffectInterpolation | None = None,
    effects: Sequence[AbstractEffect] | None = None,
    child: AbstractEffect | None = None,
    times: int | None = None,
) -> AbstractEffect: ...


@overload
def Effect(
    effect: AbstractEffect,
    *,
    duration_ms: int = 300,
    color: ColorLike | None = None,
    background: ColorLike | None = None,
    direction: EffectMotion | None = None,
    gradient_length: int | None = None,
    randomness: int | None = None,
    interpolation: EffectInterpolation | None = None,
    effects: Sequence[AbstractEffect] | None = None,
    child: AbstractEffect | None = None,
    times: int | None = None,
) -> AbstractEffect: ...


def Effect(
    effect: KnownEffectKind | AbstractEffect,
    *,
    duration_ms: int = 300,
    color: ColorLike | None = None,
    background: ColorLike | None = None,
    direction: EffectMotion | None = None,
    gradient_length: int | None = None,
    randomness: int | None = None,
    interpolation: EffectInterpolation | None = None,
    effects: Sequence[AbstractEffect] | None = None,
    child: AbstractEffect | None = None,
    times: int | None = None,
) -> AbstractEffect:
    """Create a user-facing effect description.

    Args:
        effect: A known effect kind or an existing effect instance.
        duration_ms: Duration of the effect in milliseconds.
        color: Foreground or accent color for color-driven effects.
        background: Background color for two-color effects.
        direction: Motion direction for slide and sweep effects.
        gradient_length: Gradient length for slide and sweep effects.
        randomness: Randomness for slide and sweep effects.
        interpolation: Interpolation curve for the effect.
        effects: Child effects for sequence and parallel composition.
        child: Child effect for repeat and delay composition.
        times: Repeat count for repeat effects.

    Returns:
        A resolved :class:`AbstractEffect` instance.
    """
    return resolve_effect(
        effect,
        duration_ms=duration_ms,
        color=color,
        background=background,
        direction=direction,
        gradient_length=gradient_length,
        randomness=randomness,
        interpolation=interpolation,
        effects=effects,
        child=child,
        times=times,
    )


__all__ = (
    "AbstractEffect",
    "CoalesceEffect",
    "DelayEffect",
    "DirectionalEffect",
    "DissolveEffect",
    "Effect",
    "EffectColorSpace",
    "EffectInterpolation",
    "EffectMotion",
    "FadeEffect",
    "FadeFromBothEffect",
    "FadeFromEffect",
    "FadeToEffect",
    "KnownEffectKind",
    "PaintBackgroundEffect",
    "PaintEffect",
    "PaintForegroundEffect",
    "ParallelEffect",
    "RepeatEffect",
    "SequenceEffect",
    "SleepEffect",
    "SlideInEffect",
    "SlideOutEffect",
    "SweepInEffect",
    "SweepOutEffect",
    "resolve_effect",
    "resolve_native_effect",
)
