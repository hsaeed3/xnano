"""xnano.tui.effects

---

Lowers neutral ``xnano.effects`` descriptions to native ``tachyonfx``
effects for the terminal controller.
"""

from __future__ import annotations

from typing import Sequence

from xnano.color import Color, ColorLike
from xnano.effects import (
    AbstractEffect,
    CoalesceEffect,
    DelayEffect,
    DissolveEffect,
    EffectColorSpace,
    EffectInterpolation,
    EffectMotion,
    FadeEffect,
    FadeFromBothEffect,
    FadeFromEffect,
    FadeToEffect,
    KnownEffectKind,
    PaintBackgroundEffect,
    PaintEffect,
    PaintForegroundEffect,
    ParallelEffect,
    RepeatEffect,
    SequenceEffect,
    SleepEffect,
    SlideInEffect,
    SlideOutEffect,
    SweepInEffect,
    SweepOutEffect,
    resolve_effect,
)
from xnano_core.rust import native


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


_NATIVE_COLOR_CACHE: dict[tuple[int, int, int, float], native.Color] = {}


def _require_native_color(color: ColorLike, *, label: str) -> native.Color:
    try:
        parsed = Color.parse(color)
    except Exception as e:
        raise ValueError(
            f"{label} must resolve to a color, got {color!r}"
        ) from e

    key = (parsed.r, parsed.g, parsed.b, parsed.a)
    cached = _NATIVE_COLOR_CACHE.get(key)
    if cached is not None:
        return cached

    resolved = native.Color.rgb(parsed.r, parsed.g, parsed.b)
    _NATIVE_COLOR_CACHE[key] = resolved
    return resolved


def build_native_effect(effect: AbstractEffect) -> native.Effect:
    """Lower an effect description to a native effect instance.

    Args:
        effect: The neutral effect description to lower.

    Returns:
        A native ``Effect`` ready to run.
    """
    if isinstance(effect, FadeEffect):
        return native.fade_to_fg(
            _require_native_color(effect.color, label="color"),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, FadeFromEffect):
        return native.fade_from_fg(
            _require_native_color(effect.color, label="color"),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, FadeToEffect):
        return native.fade_to(
            _require_native_color(effect.color, label="color"),
            _require_native_color(effect.background, label="background"),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, FadeFromBothEffect):
        return native.fade_from(
            _require_native_color(effect.color, label="color"),
            _require_native_color(effect.background, label="background"),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, DissolveEffect):
        return native.dissolve(
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, CoalesceEffect):
        return native.coalesce(
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, SweepInEffect):
        return native.sweep_in(
            _resolve_native_motion(effect.direction),
            effect.gradient_length,
            effect.randomness,
            _require_native_color(effect.color, label="color"),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, SweepOutEffect):
        return native.sweep_out(
            _resolve_native_motion(effect.direction),
            effect.gradient_length,
            effect.randomness,
            _require_native_color(effect.color, label="color"),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, SlideInEffect):
        return native.slide_in(
            _resolve_native_motion(effect.direction),
            effect.gradient_length,
            effect.randomness,
            _require_native_color(effect.color, label="color"),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, SlideOutEffect):
        return native.slide_out(
            _resolve_native_motion(effect.direction),
            effect.gradient_length,
            effect.randomness,
            _require_native_color(effect.color, label="color"),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, PaintEffect):
        return native.paint(
            _require_native_color(effect.color, label="color"),
            _require_native_color(effect.background, label="background"),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, PaintForegroundEffect):
        return native.paint_fg(
            _require_native_color(effect.color, label="color"),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, PaintBackgroundEffect):
        return native.paint_bg(
            _require_native_color(effect.background, label="background"),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, SleepEffect):
        return native.sleep_effect(effect.duration_ms)
    if isinstance(effect, SequenceEffect):
        if not effect.effects:
            raise ValueError("sequence effects require at least one child")
        return native.sequence_effects(
            [build_native_effect(child) for child in effect.effects]
        )
    if isinstance(effect, ParallelEffect):
        if not effect.effects:
            raise ValueError("parallel effects require at least one child")
        return native.parallel_effects(
            [build_native_effect(child) for child in effect.effects]
        )
    if isinstance(effect, RepeatEffect):
        if effect.child is None:
            raise ValueError("repeat effects require a child effect")
        child = build_native_effect(effect.child)
        if effect.times is not None:
            return native.repeat_effect(child, times=effect.times)
        if effect.duration_ms != 300:
            return native.repeat_effect(child, duration_ms=effect.duration_ms)
        return native.repeat_effect(child)
    if isinstance(effect, DelayEffect):
        if effect.child is None:
            raise ValueError("delay effects require a child effect")
        return native.delay_effect(
            effect.duration_ms,
            build_native_effect(effect.child),
        )

    raise ValueError(f"unsupported effect type: {type(effect)!r}")


def apply_native_cell_filter(
    effect_description: AbstractEffect,
    native_effect: native.Effect,
) -> native.Effect:
    """Apply an effect description's terminal cell filter to an effect."""
    if effect_description.cell_filter is None:
        return native_effect
    filters = {
        "all": native.CellFilter.ALL,
        "text": native.CellFilter.TEXT,
        "non_empty": native.CellFilter.NON_EMPTY,
        "background": native.CellFilter.BACKGROUND,
        "background_only": native.CellFilter.BACKGROUND_ONLY,
    }
    return native_effect.with_filter(filters[effect_description.cell_filter])


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
    key: str | None = None,
) -> native.Effect:
    """Resolve and lower an effect description to a native effect.

    Terminal-only: lowers through ``build_native_effect``. See the
    ``xnano.effects`` module docstring for why this lowering step lives
    behind the terminal controller rather than growing a second (web)
    lowering path there.

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
            per target field.

    Returns:
        A native ``Effect`` instance.
    """
    resolved = resolve_effect(
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
    return apply_native_cell_filter(resolved, build_native_effect(resolved))
