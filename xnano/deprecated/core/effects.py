"""
xnano.deprecated.core.effects

---

Turn effect descriptions into native ``tachyonfx`` effects.
"""

from __future__ import annotations

from collections.abc import Sequence

from xnano.deprecated import _effects as tachyonfx
from xnano.deprecated import _ratatui as ratatui
from xnano.deprecated.colors import Color, ColorLike
from xnano.deprecated.effects import (
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

_MOTION_TO_NATIVE: dict[EffectMotion, tachyonfx.TachyonFxMotion] = {
    'up_to_down': tachyonfx.TachyonFxMotion.UpToDown,
    'down_to_up': tachyonfx.TachyonFxMotion.DownToUp,
    'left_to_right': tachyonfx.TachyonFxMotion.LeftToRight,
    'right_to_left': tachyonfx.TachyonFxMotion.RightToLeft,
}

_INTERPOLATION_TO_NATIVE: dict[EffectInterpolation, tachyonfx.TachyonFxInterpolation] = {
    'linear': tachyonfx.TachyonFxInterpolation.Linear,
    'smooth_step': tachyonfx.TachyonFxInterpolation.SmoothStep,
    'sine_in': tachyonfx.TachyonFxInterpolation.SineIn,
    'sine_out': tachyonfx.TachyonFxInterpolation.SineOut,
    'sine_in_out': tachyonfx.TachyonFxInterpolation.SineInOut,
    'quad_in': tachyonfx.TachyonFxInterpolation.QuadraticIn,
    'quad_out': tachyonfx.TachyonFxInterpolation.QuadraticOut,
    'quad_in_out': tachyonfx.TachyonFxInterpolation.QuadraticInOut,
    'cubic_in': tachyonfx.TachyonFxInterpolation.CubicIn,
    'cubic_out': tachyonfx.TachyonFxInterpolation.CubicOut,
    'cubic_in_out': tachyonfx.TachyonFxInterpolation.CubicInOut,
    'expo_in': tachyonfx.TachyonFxInterpolation.ExponentialIn,
    'expo_out': tachyonfx.TachyonFxInterpolation.ExponentialOut,
    'expo_in_out': tachyonfx.TachyonFxInterpolation.ExponentialInOut,
    'bounce_in': tachyonfx.TachyonFxInterpolation.BounceIn,
    'bounce_out': tachyonfx.TachyonFxInterpolation.BounceOut,
    'bounce_in_out': tachyonfx.TachyonFxInterpolation.BounceInOut,
    'elastic_in': tachyonfx.TachyonFxInterpolation.ElasticIn,
    'elastic_out': tachyonfx.TachyonFxInterpolation.ElasticOut,
    'elastic_in_out': tachyonfx.TachyonFxInterpolation.ElasticInOut,
    'back_in': tachyonfx.TachyonFxInterpolation.BackIn,
    'back_out': tachyonfx.TachyonFxInterpolation.BackOut,
    'back_in_out': tachyonfx.TachyonFxInterpolation.BackInOut,
    'spring': tachyonfx.TachyonFxInterpolation.Spring,
}

_COLOR_SPACE_TO_NATIVE: dict[EffectColorSpace, tachyonfx.TachyonFxColorSpace] = {
    'rgb': tachyonfx.TachyonFxColorSpace.Rgb,
    'hsl': tachyonfx.TachyonFxColorSpace.Hsl,
    'hsv': tachyonfx.TachyonFxColorSpace.Hsv,
}


def _resolve_native_motion(motion: EffectMotion) -> tachyonfx.TachyonFxMotion:
    return _MOTION_TO_NATIVE[motion]


def _resolve_native_interpolation(
    interpolation: EffectInterpolation | None,
) -> tachyonfx.TachyonFxInterpolation | None:
    if interpolation is None:
        return None
    return _INTERPOLATION_TO_NATIVE[interpolation]


def _resolve_native_color_space(
    color_space: EffectColorSpace | None,
) -> tachyonfx.TachyonFxColorSpace | None:
    if color_space is None:
        return None
    return _COLOR_SPACE_TO_NATIVE[color_space]


_NATIVE_COLOR_CACHE: dict[tuple[int, int, int, float], ratatui.RatatuiColor] = {}


def _require_native_color(color: ColorLike, *, label: str) -> ratatui.RatatuiColor:
    try:
        parsed = Color.parse(color)
    except Exception as e:
        raise ValueError(f'{label} must resolve to a color, got {color!r}') from e

    key = (parsed.r, parsed.g, parsed.b, parsed.a)
    cached = _NATIVE_COLOR_CACHE.get(key)
    if cached is not None:
        return cached

    resolved = ratatui.RatatuiColor.rgb(parsed.r, parsed.g, parsed.b)
    _NATIVE_COLOR_CACHE[key] = resolved
    return resolved


def build_native_effect(effect: AbstractEffect) -> tachyonfx.TachyonFxEffect:
    """
    Lower an effect description to a native effect instance.

    Args:
        effect: The neutral effect description to lower.

    Returns:
        A native ``Effect`` ready to run.
    """
    if isinstance(effect, FadeEffect):
        return tachyonfx.tachyonfx_fade_to_foreground(
            _require_native_color(effect.color, label='color'),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, FadeFromEffect):
        return tachyonfx.tachyonfx_fade_from_foreground(
            _require_native_color(effect.color, label='color'),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, FadeToEffect):
        return tachyonfx.tachyonfx_fade_to(
            _require_native_color(effect.color, label='color'),
            _require_native_color(effect.background, label='background'),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, FadeFromBothEffect):
        return tachyonfx.tachyonfx_fade_from(
            _require_native_color(effect.color, label='color'),
            _require_native_color(effect.background, label='background'),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, DissolveEffect):
        return tachyonfx.tachyonfx_dissolve(
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, CoalesceEffect):
        return tachyonfx.tachyonfx_coalesce(
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, SweepInEffect):
        return tachyonfx.tachyonfx_sweep_in(
            _resolve_native_motion(effect.direction),
            effect.gradient_length,
            effect.randomness,
            _require_native_color(effect.color, label='color'),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, SweepOutEffect):
        return tachyonfx.tachyonfx_sweep_out(
            _resolve_native_motion(effect.direction),
            effect.gradient_length,
            effect.randomness,
            _require_native_color(effect.color, label='color'),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, SlideInEffect):
        return tachyonfx.tachyonfx_slide_in(
            _resolve_native_motion(effect.direction),
            effect.gradient_length,
            effect.randomness,
            _require_native_color(effect.color, label='color'),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, SlideOutEffect):
        return tachyonfx.tachyonfx_slide_out(
            _resolve_native_motion(effect.direction),
            effect.gradient_length,
            effect.randomness,
            _require_native_color(effect.color, label='color'),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, PaintEffect):
        return tachyonfx.tachyonfx_paint(
            _require_native_color(effect.color, label='color'),
            _require_native_color(effect.background, label='background'),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, PaintForegroundEffect):
        return tachyonfx.tachyonfx_paint_foreground(
            _require_native_color(effect.color, label='color'),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, PaintBackgroundEffect):
        return tachyonfx.tachyonfx_paint_background(
            _require_native_color(effect.background, label='background'),
            effect.duration_ms,
            _resolve_native_interpolation(effect.interpolation),
        )
    if isinstance(effect, SleepEffect):
        return tachyonfx.tachyonfx_sleep(effect.duration_ms)
    if isinstance(effect, SequenceEffect):
        if not effect.effects:
            raise ValueError('sequence effects require at least one child')
        return tachyonfx.tachyonfx_sequence(
            [build_native_effect(child) for child in effect.effects]
        )
    if isinstance(effect, ParallelEffect):
        if not effect.effects:
            raise ValueError('parallel effects require at least one child')
        return tachyonfx.tachyonfx_parallel(
            [build_native_effect(child) for child in effect.effects]
        )
    if isinstance(effect, RepeatEffect):
        if effect.child is None:
            raise ValueError('repeat effects require a child effect')
        child = build_native_effect(effect.child)
        if effect.times is not None:
            return tachyonfx.tachyonfx_repeat(child, times=effect.times)
        if effect.duration_ms != 300:
            return tachyonfx.tachyonfx_repeat(
                child, duration_milliseconds=effect.duration_ms
            )
        return tachyonfx.tachyonfx_repeat(child)
    if isinstance(effect, DelayEffect):
        if effect.child is None:
            raise ValueError('delay effects require a child effect')
        return tachyonfx.tachyonfx_delay(
            effect.duration_ms,
            build_native_effect(effect.child),
        )

    raise ValueError(f'unsupported effect type: {type(effect)!r}')


def apply_native_cell_filter(
    effect_description: AbstractEffect,
    native_effect: tachyonfx.TachyonFxEffect,
) -> tachyonfx.TachyonFxEffect:
    """Apply an effect description's terminal cell filter to an effect."""
    if effect_description.cell_filter is None:
        return native_effect
    filters = {
        'all': tachyonfx.TachyonFxCellFilter.All,
        'text': tachyonfx.TachyonFxCellFilter.Text,
        'non_empty': tachyonfx.TachyonFxCellFilter.NonEmpty,
        'background': tachyonfx.TachyonFxCellFilter.Background,
        'background_only': tachyonfx.TachyonFxCellFilter.BackgroundOnly,
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
) -> tachyonfx.TachyonFxEffect:
    """
    Resolve and lower an effect description to a native effect.

    Terminal-only: lowers through ``build_native_effect``. See the
    ``xnano.deprecated.effects`` module docstring for why this lowering step lives
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
