"""xnano.effects"""

from __future__ import annotations

import dataclasses
from typing import Any, Literal, Sequence, TypeAlias

from xnano import _core
from xnano._convert import ColorLike, _resolve_color, unwrap
from xnano.color import Color
from xnano.layout import Margin, Rectangle
from xnano.style import Style


Motion: TypeAlias = Literal[
    "up_to_down", "down_to_up", "left_to_right", "right_to_left"
]
"""Visual motion direction for slide and sweep effects."""


Interpolation: TypeAlias = Literal[
    "back_in",
    "back_out",
    "back_in_out",
    "bounce_in",
    "bounce_out",
    "bounce_in_out",
    "circ_in",
    "circ_out",
    "circ_in_out",
    "cubic_in",
    "cubic_out",
    "cubic_in_out",
    "elastic_in",
    "elastic_out",
    "elastic_in_out",
    "expo_in",
    "expo_out",
    "expo_in_out",
    "linear",
    "quad_in",
    "quad_out",
    "quad_in_out",
    "quart_in",
    "quart_out",
    "quart_in_out",
    "quint_in",
    "quint_out",
    "quint_in_out",
    "reverse",
    "smooth_step",
    "spring",
    "sine_in",
    "sine_out",
    "sine_in_out",
]
"""Mathematical curves used to interpolate visual effect progress over time."""


ColorSpace: TypeAlias = Literal["rgb", "hsl", "hsv"]
"""Color space used for color interpolation during transitions."""


_MOTION: dict[Motion, _core.Motion] = {
    "up_to_down": _core.Motion.UpToDown,
    "down_to_up": _core.Motion.DownToUp,
    "left_to_right": _core.Motion.LeftToRight,
    "right_to_left": _core.Motion.RightToLeft,
}


_INTERPOLATION: dict[Interpolation, _core.Interpolation] = {
    "back_in": _core.Interpolation.BackIn,
    "back_out": _core.Interpolation.BackOut,
    "back_in_out": _core.Interpolation.BackInOut,
    "bounce_in": _core.Interpolation.BounceIn,
    "bounce_out": _core.Interpolation.BounceOut,
    "bounce_in_out": _core.Interpolation.BounceInOut,
    "circ_in": _core.Interpolation.CircIn,
    "circ_out": _core.Interpolation.CircOut,
    "circ_in_out": _core.Interpolation.CircInOut,
    "cubic_in": _core.Interpolation.CubicIn,
    "cubic_out": _core.Interpolation.CubicOut,
    "cubic_in_out": _core.Interpolation.CubicInOut,
    "elastic_in": _core.Interpolation.ElasticIn,
    "elastic_out": _core.Interpolation.ElasticOut,
    "elastic_in_out": _core.Interpolation.ElasticInOut,
    "expo_in": _core.Interpolation.ExpoIn,
    "expo_out": _core.Interpolation.ExpoOut,
    "expo_in_out": _core.Interpolation.ExpoInOut,
    "linear": _core.Interpolation.Linear,
    "quad_in": _core.Interpolation.QuadIn,
    "quad_out": _core.Interpolation.QuadOut,
    "quad_in_out": _core.Interpolation.QuadInOut,
    "quart_in": _core.Interpolation.QuartIn,
    "quart_out": _core.Interpolation.QuartOut,
    "quart_in_out": _core.Interpolation.QuartInOut,
    "quint_in": _core.Interpolation.QuintIn,
    "quint_out": _core.Interpolation.QuintOut,
    "quint_in_out": _core.Interpolation.QuintInOut,
    "reverse": _core.Interpolation.Reverse,
    "smooth_step": _core.Interpolation.SmoothStep,
    "spring": _core.Interpolation.Spring,
    "sine_in": _core.Interpolation.SineIn,
    "sine_out": _core.Interpolation.SineOut,
    "sine_in_out": _core.Interpolation.SineInOut,
}


_COLOR_SPACE: dict[ColorSpace, _core.ColorSpace] = {
    "rgb": _core.ColorSpace.Rgb,
    "hsl": _core.ColorSpace.Hsl,
    "hsv": _core.ColorSpace.Hsv,
}


def _core_motion(value: Motion) -> _core.Motion:
    return _MOTION[value]


def _core_interpolation(
    value: Interpolation | None,
) -> _core.Interpolation | None:
    if value is None:
        return None
    return _INTERPOLATION[value]


def _core_color_space(value: ColorSpace) -> _core.ColorSpace:
    return _COLOR_SPACE[value]


class CellFilter:
    """A filter that determines which cells in a render buffer are affected by
    an visual effect.

    Use the factory classmethods to create filters::

        # Apply only to non-empty cells
        filter = CellFilter.non_empty()

        # Apply only to cells with red text
        filter = CellFilter.foreground_color("red")
    """

    __slots__ = ("_inner",)
    _inner: _core.CellFilter

    def __init__(self) -> None:
        raise TypeError(
            "CellFilter instances must be created using factory methods: "
            "CellFilter.all(), CellFilter.text(), CellFilter.foreground_color(), etc."
        )

    @classmethod
    def _from_core(cls, inner: _core.CellFilter) -> CellFilter:
        """Construct from a native ``core.CellFilter``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.CellFilter:
        """Return the native cell filter."""
        return self._inner

    @classmethod
    def all(cls) -> CellFilter:
        """Filter that matches all cells in the area."""
        return cls._from_core(_core.CellFilter.ALL)

    @classmethod
    def text(cls) -> CellFilter:
        """Filter that matches only cells containing text characters."""
        return cls._from_core(_core.CellFilter.TEXT)

    @classmethod
    def non_empty(cls) -> CellFilter:
        """Filter that matches cells containing non-whitespace content."""
        return cls._from_core(_core.CellFilter.NON_EMPTY)

    @classmethod
    def foreground_color(cls, color: ColorLike) -> CellFilter:
        """Filter that matches cells with a specific foreground color."""
        return cls._from_core(_core.CellFilter.fg_color(_resolve_color(color)))

    @classmethod
    def background_color(cls, color: ColorLike) -> CellFilter:
        """Filter that matches cells with a specific background color."""
        return cls._from_core(_core.CellFilter.bg_color(_resolve_color(color)))

    # Deprecated/compatibility aliases
    fg_color = foreground_color
    bg_color = background_color

    @classmethod
    def inner(cls, margin: Margin) -> CellFilter:
        """Filter that matches cells within the inner area defined by the
        margin.
        """
        return cls._from_core(_core.CellFilter.inner(margin._to_core()))

    @classmethod
    def outer(cls, margin: Margin) -> CellFilter:
        """Filter that matches cells outside the inner area defined by the
        margin.
        """
        return cls._from_core(_core.CellFilter.outer(margin._to_core()))

    @classmethod
    def area(cls, rect: Rectangle) -> CellFilter:
        """Filter that matches only cells inside the specified Rectangle."""
        return cls._from_core(_core.CellFilter.area(rect._to_core()))

    @classmethod
    def all_of(cls, filters: Sequence[CellFilter]) -> CellFilter:
        """Filter that matches if all of the sub-filters match."""
        return cls._from_core(
            _core.CellFilter.all_of([f._to_core() for f in filters])
        )

    @classmethod
    def any_of(cls, filters: Sequence[CellFilter]) -> CellFilter:
        """Filter that matches if any of the sub-filters match."""
        return cls._from_core(
            _core.CellFilter.any_of([f._to_core() for f in filters])
        )

    @classmethod
    def not_(cls, filter: CellFilter) -> CellFilter:
        """Filter that matches if the given filter does not match."""
        return cls._from_core(_core.CellFilter.not_(filter._to_core()))

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("CellFilter is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("CellFilter is immutable")


class Effect:
    """A visual animation effect that updates terminal cells over time.

    Effects are created using the visual effect function helpers (e.g.
    ``fade_to_fg``, ``dissolve``, ``slide_in``).
    """

    __slots__ = ("_inner",)
    _inner: _core.Effect

    def __init__(self) -> None:
        raise TypeError(
            "Effect instances must be created using the effect creator functions "
            "like fade_to_fg(), slide_in(), dissolve(), etc."
        )

    @classmethod
    def _from_core(cls, inner: _core.Effect) -> Effect:
        """Construct from a native ``core.Effect``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.Effect:
        """Return the native effect."""
        return self._inner

    def with_area(self, area: Rectangle) -> Effect:
        """Return a new Effect locked to a specific render area."""
        return Effect._from_core(self._inner.with_area(area._to_core()))

    def with_filter(self, filter: CellFilter) -> Effect:
        """Return a new Effect that only applies to cells matching the filter."""
        return Effect._from_core(self._inner.with_filter(filter._to_core()))

    def with_color_space(self, color_space: ColorSpace) -> Effect:
        """Return a new Effect that interpolates colors in the specified space."""
        return Effect._from_core(
            self._inner.with_color_space(_core_color_space(color_space))
        )

    def with_rng(self, seed: int) -> Effect:
        """Return a new Effect with a specific seed for randomized visual elements."""
        return Effect._from_core(self._inner.with_rng(seed))

    def reversed(self) -> Effect:
        """Return a new Effect running in reverse progress."""
        return Effect._from_core(self._inner.reversed())

    def name(self) -> str:
        """Return the name identifier of this effect."""
        return self._inner.name()

    def is_done(self) -> bool:
        """Return ``True`` if the effect has completed running."""
        return self._inner.is_done()

    def is_running(self) -> bool:
        """Return ``True`` if the effect is currently active."""
        return self._inner.is_running()

    def reset(self) -> None:
        """Reset the progress of the effect back to its starting state."""
        self._inner.reset()

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Effect is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Effect is immutable")


class EffectManager:
    """An visual effect scheduler that manages and runs multiple active
    visual animations simultaneously.
    """

    __slots__ = ("_inner",)
    _inner: _core.EffectManager

    def __init__(self) -> None:
        """Create a new visual EffectManager."""
        object.__setattr__(self, "_inner", _core.EffectManager())

    @classmethod
    def _from_core(cls, inner: _core.EffectManager) -> EffectManager:
        """Construct from a native ``core.EffectManager``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.EffectManager:
        """Return the native effect manager."""
        return self._inner

    def add(self, effect: Effect) -> None:
        """Schedule a new visual effect to run."""
        self._inner.add(effect._to_core())

    def add_unique(self, key: str, effect: Effect) -> None:
        """Schedule a visual effect with a key, canceling any previous
        active effect running under the same key.
        """
        self._inner.add_unique(key, effect._to_core())

    def unique(self, key: str, effect: Effect) -> Effect:
        """Ensure a single unique instance of this effect is scheduled,
        returning it.
        """
        return Effect._from_core(self._inner.unique(key, effect._to_core()))

    def cancel(self, key: str) -> None:
        """Cancel the scheduled visual effect associated with the key."""
        self._inner.cancel(key)

    def is_running(self) -> bool:
        """Return ``True`` if there are any active effects currently running."""
        return self._inner.is_running()

    def process(self, duration_ms: int, buffer: Any, area: Rectangle) -> None:
        """Advance the scheduled animations by the given millisecond step duration,
        applying rendering updates to the buffer.
        """
        from xnano.buffer import Buffer

        core_buffer = (
            buffer._to_core() if isinstance(buffer, Buffer) else buffer
        )
        self._inner.process(duration_ms, core_buffer, area._to_core())

    def __repr__(self) -> str:
        return repr(self._inner)


def _wrap(effect: _core.Effect) -> Effect:
    return Effect._from_core(effect)


def fade_to_fg(
    color: ColorLike,
    duration_ms: int,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Fade the text foreground color of matching cells to the target color."""
    return _wrap(
        _core.fade_to_fg(
            _resolve_color(color),
            duration_ms,
            _core_interpolation(interpolation),
        )
    )


def fade_from_fg(
    color: ColorLike,
    duration_ms: int,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Fade the text foreground color of matching cells starting from the source color."""
    return _wrap(
        _core.fade_from_fg(
            _resolve_color(color),
            duration_ms,
            _core_interpolation(interpolation),
        )
    )


def fade_to(
    fg: ColorLike,
    bg: ColorLike,
    duration_ms: int,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Fade both foreground and background colors of cells to target values."""
    return _wrap(
        _core.fade_to(
            _resolve_color(fg),
            _resolve_color(bg),
            duration_ms,
            _core_interpolation(interpolation),
        )
    )


def fade_from(
    fg: ColorLike,
    bg: ColorLike,
    duration_ms: int,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Fade both foreground and background colors of cells starting from source values."""
    return _wrap(
        _core.fade_from(
            _resolve_color(fg),
            _resolve_color(bg),
            duration_ms,
            _core_interpolation(interpolation),
        )
    )


def paint(
    fg: ColorLike,
    bg: ColorLike,
    duration_ms: int,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Paint cells to specific target foreground and background colors over time."""
    return _wrap(
        _core.paint(
            _resolve_color(fg),
            _resolve_color(bg),
            duration_ms,
            _core_interpolation(interpolation),
        )
    )


def paint_fg(
    fg: ColorLike,
    duration_ms: int,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Paint the cell text foreground color over time."""
    return _wrap(
        _core.paint_fg(
            _resolve_color(fg), duration_ms, _core_interpolation(interpolation)
        )
    )


def paint_bg(
    bg: ColorLike,
    duration_ms: int,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Paint the cell background color over time."""
    return _wrap(
        _core.paint_bg(
            _resolve_color(bg), duration_ms, _core_interpolation(interpolation)
        )
    )


def slide_in(
    direction: Motion,
    gradient_length: int,
    randomness: int,
    color: ColorLike,
    duration_ms: int,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Animate content sliding into view from a given direction."""
    return _wrap(
        _core.slide_in(
            _core_motion(direction),
            gradient_length,
            randomness,
            _resolve_color(color),
            duration_ms,
            _core_interpolation(interpolation),
        )
    )


def slide_out(
    direction: Motion,
    gradient_length: int,
    randomness: int,
    color: ColorLike,
    duration_ms: int,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Animate content sliding out of view to a given direction."""
    return _wrap(
        _core.slide_out(
            _core_motion(direction),
            gradient_length,
            randomness,
            _resolve_color(color),
            duration_ms,
            _core_interpolation(interpolation),
        )
    )


def sweep_in(
    direction: Motion,
    gradient_length: int,
    randomness: int,
    color: ColorLike,
    duration_ms: int,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Sweep cell coloring into view across the screen."""
    return _wrap(
        _core.sweep_in(
            _core_motion(direction),
            gradient_length,
            randomness,
            _resolve_color(color),
            duration_ms,
            _core_interpolation(interpolation),
        )
    )


def sweep_out(
    direction: Motion,
    gradient_length: int,
    randomness: int,
    color: ColorLike,
    duration_ms: int,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Sweep cell coloring out of view across the screen."""
    return _wrap(
        _core.sweep_out(
            _core_motion(direction),
            gradient_length,
            randomness,
            _resolve_color(color),
            duration_ms,
            _core_interpolation(interpolation),
        )
    )


def dissolve(
    duration_ms: int,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Animate content dissolving/fading out in a randomized grid pattern."""
    return _wrap(
        _core.dissolve(duration_ms, _core_interpolation(interpolation))
    )


def dissolve_to(
    style: Style,
    duration_ms: int,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Dissolve content styling toward a target style."""
    return _wrap(
        _core.dissolve_to(
            style._to_core(), duration_ms, _core_interpolation(interpolation)
        )
    )


def coalesce(
    duration_ms: int,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Animate content coalescing/fading back in from a dissolved state."""
    return _wrap(
        _core.coalesce(duration_ms, _core_interpolation(interpolation))
    )


def coalesce_from(
    style: Style,
    duration_ms: int,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Coalesce content styling starting from a specific source style."""
    return _wrap(
        _core.coalesce_from(
            style._to_core(), duration_ms, _core_interpolation(interpolation)
        )
    )


def sleep(duration_ms: int) -> Effect:
    """A delay/pause effect that performs no rendering changes for a duration."""
    return _wrap(_core.sleep_effect(duration_ms))


def sequence(effects: list[Effect]) -> Effect:
    """Chain multiple visual effects to run sequentially one after another."""
    return _wrap(
        _core.sequence_effects([effect._to_core() for effect in effects])
    )


def parallel(effects: list[Effect]) -> Effect:
    """Combine multiple visual effects to run concurrently at the same time."""
    return _wrap(
        _core.parallel_effects([effect._to_core() for effect in effects])
    )


def repeating(effect: Effect) -> Effect:
    """Repeat the progress of the given visual effect indefinitely in a loop."""
    return _wrap(_core.repeating_effect(effect._to_core()))


def ping_pong(effect: Effect) -> Effect:
    """Run an effect forward, then run it in reverse, repeating in a loop."""
    return _wrap(_core.ping_pong_effect(effect._to_core()))


def repeat(
    effect: Effect,
    *,
    times: int | None = None,
    duration_ms: int | None = None,
) -> Effect:
    """Repeat a visual effect a specific number of times or for a duration."""
    if times is not None:
        return _wrap(_core.repeat_effect(effect._to_core(), times=times))
    elif duration_ms is not None:
        return _wrap(
            _core.repeat_effect(effect._to_core(), duration_ms=duration_ms)
        )
    else:
        return _wrap(_core.repeat_effect(effect._to_core()))


def delay(duration_ms: int, effect: Effect) -> Effect:
    """Delay the execution start of a visual effect."""
    return _wrap(_core.delay_effect(duration_ms, effect._to_core()))


def prolong_start(duration_ms: int, effect: Effect) -> Effect:
    """Hold the start frame visual state of an effect for a duration before running."""
    return _wrap(_core.prolong_start_effect(duration_ms, effect._to_core()))


def prolong_end(duration_ms: int, effect: Effect) -> Effect:
    """Hold the completed final visual state of an effect for a duration before finishing."""
    return _wrap(_core.prolong_end_effect(duration_ms, effect._to_core()))


def saturate(
    duration_ms: int,
    *,
    fg: float | None = None,
    bg: float | None = None,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Animate saturation shift on cell colors."""
    return _wrap(
        _core.saturate(
            duration_ms,
            fg=fg,
            bg=bg,
            interpolation=_core_interpolation(interpolation),
        )
    )


def saturate_fg(
    fg: float,
    duration_ms: int,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Animate saturation shift on foreground text color."""
    return _wrap(
        _core.saturate_fg(fg, duration_ms, _core_interpolation(interpolation))
    )


def lighten(
    duration_ms: int,
    *,
    fg: float | None = None,
    bg: float | None = None,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Animate lightening transition of cell colors."""
    return _wrap(
        _core.lighten(
            duration_ms,
            fg=fg,
            bg=bg,
            interpolation=_core_interpolation(interpolation),
        )
    )


def lighten_fg(
    fg: float,
    duration_ms: int,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Animate lightening transition of foreground text color."""
    return _wrap(
        _core.lighten_fg(fg, duration_ms, _core_interpolation(interpolation))
    )


def darken(
    duration_ms: int,
    *,
    fg: float | None = None,
    bg: float | None = None,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Animate darkening transition of cell colors."""
    return _wrap(
        _core.darken(
            duration_ms,
            fg=fg,
            bg=bg,
            interpolation=_core_interpolation(interpolation),
        )
    )


def darken_fg(
    fg: float,
    duration_ms: int,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Animate darkening transition of foreground text color."""
    return _wrap(
        _core.darken_fg(fg, duration_ms, _core_interpolation(interpolation))
    )


def hsl_shift(
    duration_ms: int,
    *,
    fg_h: float | None = None,
    fg_s: float | None = None,
    fg_l: float | None = None,
    bg_h: float | None = None,
    bg_s: float | None = None,
    bg_l: float | None = None,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Animate shifting of HSL color components of cell styles."""
    return _wrap(
        _core.hsl_shift(
            duration_ms,
            fg_h=fg_h,
            fg_s=fg_s,
            fg_l=fg_l,
            bg_h=bg_h,
            bg_s=bg_s,
            bg_l=bg_l,
            interpolation=_core_interpolation(interpolation),
        )
    )


def hsl_shift_fg(
    h: float,
    s: float,
    l: float,
    duration_ms: int,
    interpolation: Interpolation | None = None,
) -> Effect:
    """Animate shifting of HSL color components of foreground text color."""
    return _wrap(
        _core.hsl_shift_fg(
            h, s, l, duration_ms, _core_interpolation(interpolation)
        )
    )


__all__ = (
    "CellFilter",
    "ColorSpace",
    "Effect",
    "EffectManager",
    "Interpolation",
    "Motion",
    "coalesce",
    "coalesce_from",
    "darken",
    "darken_fg",
    "delay",
    "dissolve",
    "dissolve_to",
    "fade_from",
    "fade_from_fg",
    "fade_to",
    "fade_to_fg",
    "hsl_shift",
    "hsl_shift_fg",
    "lighten",
    "lighten_fg",
    "paint",
    "paint_bg",
    "paint_fg",
    "parallel",
    "ping_pong",
    "prolong_end",
    "prolong_start",
    "repeat",
    "repeating",
    "saturate",
    "saturate_fg",
    "sequence",
    "sleep",
    "slide_in",
    "slide_out",
    "sweep_in",
    "sweep_out",
)
