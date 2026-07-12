"""xnano.effects

Declarative, controller-agnostic descriptions of visual effects that can be
played against one or more ``BaseGrid`` layout fields.

Every ``AbstractEffect`` subclass here only describes *intent* — duration,
interpolation, color, motion, composition — using ``xnano`` types and
literals. Nothing in this module assumes a terminal. The terminal-only
lowering of a description to a ``tachyonfx`` native effect lives in
``xnano.tui.effects``, which the terminal controller calls. A future web
controller would instead dispatch over these same dataclasses to a CSS
transition/animation.

``key`` lives on ``AbstractEffect`` (alongside ``duration_ms`` and
``interpolation``) rather than being passed separately wherever an effect
is played, because it is the effect's own dedup/identity — the same
category of thing as its duration, not a per-call detail like which fields
to target this time. A controller's ``play_effect(effect, *, fields=...)``
reads ``effect.key`` itself rather than accepting a redundant ``key``
argument.
"""

from __future__ import annotations

import abc
import dataclasses
from typing import Literal, Sequence, TypeAlias, overload

from xnano.color import ColorLike


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


EffectCellFilter: TypeAlias = Literal[
    "all",
    "text",
    "non_empty",
    "background",
    "background_only",
]
"""Terminal cells selected by an effect.

Values:
    ``"all"``: Every cell in the target field area.
    ``"text"``: Cells containing text-like characters.
    ``"non_empty"``: Cells whose symbol is not a space.
    ``"background"``: Cells carrying a non-reset background color.
    ``"background_only"``: Blank cells carrying a non-reset background;
        styled text cells are excluded.
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
"""Built-in effect kinds that can be composed through ``Effect`` or
a controller's ``play_effect``.

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


@dataclasses.dataclass
class AbstractEffect(abc.ABC):
    """Abstract base for user-composed visual effects.

    Subclasses describe effect intent with ``xnano`` types and literals.
    A controller lowers them to whatever native effect representation it
    understands — today that means ``xnano.tui.effects`` lowering to a
    ``tachyonfx`` effect for the terminal controller; a web controller
    would instead dispatch over the concrete subclass to a CSS
    transition/animation.
    """

    duration_ms: int = dataclasses.field(default=300, kw_only=True)
    """Duration of the effect in milliseconds."""
    interpolation: EffectInterpolation | None = dataclasses.field(
        default=None,
        kw_only=True,
    )
    """Optional interpolation curve for the effect."""
    cell_filter: EffectCellFilter | None = dataclasses.field(
        default=None,
        kw_only=True,
    )
    """Optional terminal-cell selection applied by the controller."""
    key: str | None = dataclasses.field(default=None, kw_only=True)
    """Optional identity for this effect instance.

    Used by a controller to derive a stable, de-duplicating id per target
    field (e.g. ``f"{key}:{field_name}"``) so replaying the same effect
    kind on the same field replaces the running instance instead of
    stacking a new one. Left unset, the controller falls back to the
    field name alone.
    """


@dataclasses.dataclass
class FadeEffect(AbstractEffect):
    """Fade foreground color to a target color."""

    color: ColorLike = "white"
    """Target foreground color."""


@dataclasses.dataclass
class FadeFromEffect(AbstractEffect):
    """Fade foreground color from a source color."""

    color: ColorLike = "white"
    """Source foreground color."""


@dataclasses.dataclass
class FadeToEffect(AbstractEffect):
    """Fade foreground and background to target colors."""

    color: ColorLike = "white"
    """Target foreground color."""
    background: ColorLike = "black"
    """Target background color."""


@dataclasses.dataclass
class FadeFromBothEffect(AbstractEffect):
    """Fade foreground and background from source colors."""

    color: ColorLike = "white"
    """Source foreground color."""
    background: ColorLike = "black"
    """Source background color."""


@dataclasses.dataclass
class DissolveEffect(AbstractEffect):
    """Random pixel dissolve transition."""


@dataclasses.dataclass
class CoalesceEffect(AbstractEffect):
    """Typewriter-style cell assembly."""


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


@dataclasses.dataclass
class SweepOutEffect(DirectionalEffect):
    """Directional sweep hiding content."""


@dataclasses.dataclass
class SlideInEffect(DirectionalEffect):
    """Directional slide revealing content."""


@dataclasses.dataclass
class SlideOutEffect(DirectionalEffect):
    """Directional slide hiding content."""


@dataclasses.dataclass
class PaintEffect(AbstractEffect):
    """Paint foreground and background to target colors."""

    color: ColorLike = "white"
    """Target foreground color."""
    background: ColorLike = "black"
    """Target background color."""


@dataclasses.dataclass
class PaintForegroundEffect(AbstractEffect):
    """Paint foreground to a target color."""

    color: ColorLike = "white"
    """Target foreground color."""


@dataclasses.dataclass
class PaintBackgroundEffect(AbstractEffect):
    """Paint background to a target color."""

    background: ColorLike = "black"
    """Target background color."""


@dataclasses.dataclass
class SleepEffect(AbstractEffect):
    """No-op delay used when composing effect sequences."""


@dataclasses.dataclass
class SequenceEffect(AbstractEffect):
    """Run child effects one after another."""

    effects: tuple[AbstractEffect, ...] = ()
    """Child effects to run in order."""


@dataclasses.dataclass
class ParallelEffect(AbstractEffect):
    """Run child effects simultaneously."""

    effects: tuple[AbstractEffect, ...] = ()
    """Child effects to run in parallel."""


@dataclasses.dataclass
class RepeatEffect(AbstractEffect):
    """Repeat a child effect."""

    child: AbstractEffect | None = None
    """Effect to repeat."""
    times: int | None = None
    """Number of times to repeat the child effect."""


@dataclasses.dataclass
class DelayEffect(AbstractEffect):
    """Delay before starting a child effect."""

    child: AbstractEffect | None = None
    """Effect to start after the delay."""


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
    key: str | None = None,
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
            key=key,
        )
    if kind == "fade_from":
        return FadeFromEffect(
            color=resolved_color,
            duration_ms=duration_ms,
            interpolation=interpolation,
            key=key,
        )
    if kind == "fade_to":
        return FadeToEffect(
            color=resolved_color,
            background=resolved_background,
            duration_ms=duration_ms,
            interpolation=interpolation,
            key=key,
        )
    if kind == "fade_from_both":
        return FadeFromBothEffect(
            color=resolved_color,
            background=resolved_background,
            duration_ms=duration_ms,
            interpolation=interpolation,
            key=key,
        )
    if kind == "dissolve":
        return DissolveEffect(
            duration_ms=duration_ms,
            interpolation=interpolation,
            key=key,
        )
    if kind == "coalesce":
        return CoalesceEffect(
            duration_ms=duration_ms,
            interpolation=interpolation,
            key=key,
        )
    if kind == "sweep_in":
        return SweepInEffect(
            direction=resolved_direction,
            gradient_length=resolved_gradient_length,
            randomness=resolved_randomness,
            color=resolved_color,
            duration_ms=duration_ms,
            interpolation=interpolation,
            key=key,
        )
    if kind == "sweep_out":
        return SweepOutEffect(
            direction=resolved_direction,
            gradient_length=resolved_gradient_length,
            randomness=resolved_randomness,
            color=resolved_color,
            duration_ms=duration_ms,
            interpolation=interpolation,
            key=key,
        )
    if kind == "slide_in":
        return SlideInEffect(
            direction=resolved_direction,
            gradient_length=resolved_gradient_length,
            randomness=resolved_randomness,
            color=resolved_color,
            duration_ms=duration_ms,
            interpolation=interpolation,
            key=key,
        )
    if kind == "slide_out":
        return SlideOutEffect(
            direction=resolved_direction,
            gradient_length=resolved_gradient_length,
            randomness=resolved_randomness,
            color=resolved_color,
            duration_ms=duration_ms,
            interpolation=interpolation,
            key=key,
        )
    if kind == "paint":
        return PaintEffect(
            color=resolved_color,
            background=resolved_background,
            duration_ms=duration_ms,
            interpolation=interpolation,
            key=key,
        )
    if kind == "paint_fg":
        return PaintForegroundEffect(
            color=resolved_color,
            duration_ms=duration_ms,
            interpolation=interpolation,
            key=key,
        )
    if kind == "paint_bg":
        return PaintBackgroundEffect(
            background=resolved_background,
            duration_ms=duration_ms,
            interpolation=interpolation,
            key=key,
        )
    if kind == "sleep":
        return SleepEffect(
            duration_ms=duration_ms,
            interpolation=interpolation,
            key=key,
        )
    if kind == "sequence":
        return SequenceEffect(
            effects=_normalize_child_effects(effects),
            duration_ms=duration_ms,
            interpolation=interpolation,
            key=key,
        )
    if kind == "parallel":
        return ParallelEffect(
            effects=_normalize_child_effects(effects),
            duration_ms=duration_ms,
            interpolation=interpolation,
            key=key,
        )
    if kind == "repeat":
        return RepeatEffect(
            child=child,
            times=times,
            duration_ms=duration_ms,
            interpolation=interpolation,
            key=key,
        )
    if kind == "delay":
        return DelayEffect(
            child=child,
            duration_ms=duration_ms,
            interpolation=interpolation,
            key=key,
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
    key: str | None = None,
) -> AbstractEffect:
    """Resolve an effect description into an ``AbstractEffect``.

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
        key: Identity used by a controller to de-duplicate this effect
            per target field. Ignored when ``effect`` is already an
            ``AbstractEffect`` instance — set ``key`` on the instance
            itself in that case.

    Returns:
        A resolved ``AbstractEffect`` instance.
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
        key=key,
    )


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
    key: str | None = None,
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
    key: str | None = None,
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
    key: str | None = None,
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
        key: Identity used by a controller to de-duplicate this effect
            per target field, e.g. distinguishing two independently
            triggered ``"fade"`` effects on the same grid.

    Returns:
        A resolved ``AbstractEffect`` instance.
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
        key=key,
    )


__all__ = (
    "AbstractEffect",
    "CoalesceEffect",
    "DelayEffect",
    "DirectionalEffect",
    "DissolveEffect",
    "Effect",
    "EffectColorSpace",
    "EffectCellFilter",
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
)
