"""
xnano._schema._effects

The TypedDicts of the keywords of every visual and sound effect, the dictionary form of each
for ``effects=[...]``, the aliases of the effect kinds, and the aliases of the parameters classes
that ``effect(...)`` returns.

The aliases of the parameters classes are unions of classes that import this module, so they are
declared for type checkers and built on first read by this module's ``__getattr__``.
"""

from __future__ import annotations

import functools
import operator
from typing import TYPE_CHECKING, Final, Literal, TypeAlias, TypedDict

import xnano_core as _core
from xnano._schema._appearance import ColorValue
from xnano._schema._layout import Interpolation, MotionDirection

if TYPE_CHECKING:
    # `xnano.effects._properties` imports this module, so it cannot be imported here while the
    # module runs: type checkers see the unions of its classes below, and `__getattr__` builds
    # them the first time they are read.
    from typing_extensions import Required

    from xnano.effects._properties import (
        BitCrushAudioEffectParameters,
        CoalesceEffectParameters,
        DarkenEffectParameters,
        DelayAudioEffectParameters,
        DissolveEffectParameters,
        DistortionAudioEffectParameters,
        EvolveEffectParameters,
        EvolveFromEffectParameters,
        EvolveIntoEffectParameters,
        ExpandEffectParameters,
        ExplodeEffectParameters,
        FadeFromEffectParameters,
        FadeToEffectParameters,
        GlitchEffectParameters,
        HighPassAudioEffectParameters,
        HslShiftEffectParameters,
        LightenEffectParameters,
        LowPassAudioEffectParameters,
        PaintEffectParameters,
        ReverbAudioEffectParameters,
        SaturateEffectParameters,
        SleepEffectParameters,
        SlideInEffectParameters,
        SlideOutEffectParameters,
        StretchEffectParameters,
        SweepInEffectParameters,
        SweepOutEffectParameters,
        TremoloAudioEffectParameters,
    )

HslShiftChannel: TypeAlias = float | _core.Expression[int | float]
"""
One change of an HSL shift, to the hue, the saturation or the lightness.

It is a number, or an expression that gives one.
"""

HslShiftTuple: TypeAlias = tuple[HslShiftChannel, HslShiftChannel, HslShiftChannel]
"""The ``(hue, saturation, lightness)`` change of an HSL shift."""


class FadeToEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.fade_to', ...)``.

    Attributes:
        foreground: Target foreground color, or ``None``.
        background: Target background color, or ``None``.
        duration_milliseconds: Duration of the fade in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    foreground: ColorValue | _core.Expression[ColorValue] | None
    """Target foreground color, or ``None``."""

    background: ColorValue | _core.Expression[ColorValue] | None
    """Target background color, or ``None``."""

    duration_milliseconds: int | _core.Expression[int | float] | None
    """Duration of the fade in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class FadeFromEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.fade_from', ...)``.

    Attributes:
        foreground: Starting foreground color, or ``None``.
        background: Starting background color, or ``None``.
        duration_milliseconds: Duration of the fade in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    foreground: ColorValue | _core.Expression[ColorValue] | None
    """Starting foreground color, or ``None``."""

    background: ColorValue | _core.Expression[ColorValue] | None
    """Starting background color, or ``None``."""

    duration_milliseconds: int | _core.Expression[int | float] | None
    """Duration of the fade in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class PaintEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.paint', ...)``.

    Attributes:
        foreground: Foreground color to paint, or ``None``.
        background: Background color to paint, or ``None``.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    foreground: ColorValue | _core.Expression[ColorValue] | None
    """Foreground color to paint, or ``None``."""

    background: ColorValue | _core.Expression[ColorValue] | None
    """Background color to paint, or ``None``."""

    duration_milliseconds: int | _core.Expression[int | float] | None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class SaturateEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.saturate', ...)``.

    Attributes:
        foreground: Foreground saturation change, or ``None``.
        background: Background saturation change, or ``None``.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    foreground: float | _core.Expression[int | float] | None
    """Foreground saturation change, or ``None``."""

    background: float | _core.Expression[int | float] | None
    """Background saturation change, or ``None``."""

    duration_milliseconds: int | _core.Expression[int | float] | None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class LightenEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.lighten', ...)``.

    Attributes:
        foreground: Foreground lightness increase, or ``None``.
        background: Background lightness increase, or ``None``.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    foreground: float | _core.Expression[int | float] | None
    """Foreground lightness increase, or ``None``."""

    background: float | _core.Expression[int | float] | None
    """Background lightness increase, or ``None``."""

    duration_milliseconds: int | _core.Expression[int | float] | None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class DarkenEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.darken', ...)``.

    Attributes:
        foreground: Foreground darkness increase, or ``None``.
        background: Background darkness increase, or ``None``.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    foreground: float | _core.Expression[int | float] | None
    """Foreground darkness increase, or ``None``."""

    background: float | _core.Expression[int | float] | None
    """Background darkness increase, or ``None``."""

    duration_milliseconds: int | _core.Expression[int | float] | None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class SweepInEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.sweep_in', ...)``.

    Attributes:
        direction: Sweep direction (such as ``'left_to_right'``).
        gradient_length: Length of the sweep gradient in cells.
        randomness: Random offset across rows or columns.
        color: Starting sweep color.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    direction: MotionDirection | _core.Expression[str] | None
    """Sweep direction (such as ``'left_to_right'``)."""

    gradient_length: int | _core.Expression[int | float] | None
    """Length of the sweep gradient in cells."""

    randomness: int | _core.Expression[int | float] | None
    """Random offset across rows or columns."""

    color: ColorValue | _core.Expression[ColorValue] | None
    """Starting sweep color."""

    duration_milliseconds: int | _core.Expression[int | float] | None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class SweepOutEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.sweep_out', ...)``.

    Attributes:
        direction: Sweep direction (such as ``'left_to_right'``).
        gradient_length: Length of the sweep gradient in cells.
        randomness: Random offset across rows or columns.
        color: Ending sweep color.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    direction: MotionDirection | _core.Expression[str] | None
    """Sweep direction (such as ``'left_to_right'``)."""

    gradient_length: int | _core.Expression[int | float] | None
    """Length of the sweep gradient in cells."""

    randomness: int | _core.Expression[int | float] | None
    """Random offset across rows or columns."""

    color: ColorValue | _core.Expression[ColorValue] | None
    """Ending sweep color."""

    duration_milliseconds: int | _core.Expression[int | float] | None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class SlideInEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.slide_in', ...)``.

    Attributes:
        direction: Slide direction (such as ``'left_to_right'``).
        gradient_length: Length of the gradient trail in cells.
        randomness: Random offset across rows or columns.
        color: Color behind the sliding cells.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    direction: MotionDirection | _core.Expression[str] | None
    """Slide direction (such as ``'left_to_right'``)."""

    gradient_length: int | _core.Expression[int | float] | None
    """Length of the gradient trail in cells."""

    randomness: int | _core.Expression[int | float] | None
    """Random offset across rows or columns."""

    color: ColorValue | _core.Expression[ColorValue] | None
    """Color behind the sliding cells."""

    duration_milliseconds: int | _core.Expression[int | float] | None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class SlideOutEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.slide_out', ...)``.

    Attributes:
        direction: Slide direction (such as ``'left_to_right'``).
        gradient_length: Length of the gradient trail in cells.
        randomness: Random offset across rows or columns.
        color: Color left behind the sliding cells.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    direction: MotionDirection | _core.Expression[str] | None
    """Slide direction (such as ``'left_to_right'``)."""

    gradient_length: int | _core.Expression[int | float] | None
    """Length of the gradient trail in cells."""

    randomness: int | _core.Expression[int | float] | None
    """Random offset across rows or columns."""

    color: ColorValue | _core.Expression[ColorValue] | None
    """Color left behind the sliding cells."""

    duration_milliseconds: int | _core.Expression[int | float] | None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class HslShiftEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.hsl_shift', ...)``.

    Attributes:
        foreground: ``(hue, saturation, lightness)`` shift for foreground colors.
        background: ``(hue, saturation, lightness)`` shift for background colors.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    foreground: HslShiftTuple | None
    """``(hue, saturation, lightness)`` shift for foreground colors."""

    background: HslShiftTuple | None
    """``(hue, saturation, lightness)`` shift for background colors."""

    duration_milliseconds: int | _core.Expression[int | float] | None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class DissolveEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.dissolve', ...)``.

    Attributes:
        style: Style dissolved into.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    style: _core.Style | _core.DynamicStyle | None
    """Style dissolved into."""

    duration_milliseconds: int | _core.Expression[int | float] | None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class CoalesceEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.coalesce', ...)``.

    Attributes:
        style: Style coalesced from.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    style: _core.Style | _core.DynamicStyle | None
    """Style coalesced from."""

    duration_milliseconds: int | _core.Expression[int | float] | None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class GlitchEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.glitch', ...)``.

    Attributes:
        ratio: Fraction of cells affected by the glitch.
        duration_milliseconds: Duration in milliseconds.
        start_delay_milliseconds: ``(minimum, maximum)`` delay before a cell glitches.
        action_milliseconds: ``(minimum, maximum)`` duration of each cell glitch.
        key: Optional effect key for replacement or cancellation.
    """

    ratio: float | _core.Expression[int | float] | None
    """Fraction of cells affected by the glitch."""

    duration_milliseconds: int | _core.Expression[int | float] | None
    """Duration in milliseconds."""

    start_delay_milliseconds: tuple[int, int]
    """``(minimum, maximum)`` delay before a cell glitches."""

    action_milliseconds: tuple[int, int]
    """``(minimum, maximum)`` duration of each cell glitch."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class SleepEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.sleep', ...)``.

    Attributes:
        duration_milliseconds: Pause duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    duration_milliseconds: int | _core.Expression[int | float]
    """Pause duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class EvolveEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.evolve', ...)``.

    Attributes:
        symbols: The symbols stepped through, such as ``'circles'``, ``'squares'`` or ``'shaded'``.
        style: Optional style applied to the evolving symbols.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    symbols: _core.EvolveSymbolSet | _core.Expression[str] | None
    """The symbols stepped through, such as ``'circles'``, ``'squares'`` or ``'shaded'``."""

    style: _core.Style | _core.DynamicStyle | None
    """Optional style applied to the evolving symbols."""

    duration_milliseconds: int | _core.Expression[int | float] | None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class EvolveIntoEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.evolve_into', ...)``.

    Attributes:
        symbols: The symbols stepped through, such as ``'circles'``, ``'squares'`` or ``'shaded'``.
        style: Optional style applied to the evolving symbols.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    symbols: _core.EvolveSymbolSet | _core.Expression[str] | None
    """The symbols stepped through, such as ``'circles'``, ``'squares'`` or ``'shaded'``."""

    style: _core.Style | _core.DynamicStyle | None
    """Optional style applied to the evolving symbols."""

    duration_milliseconds: int | _core.Expression[int | float] | None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class EvolveFromEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.evolve_from', ...)``.

    Attributes:
        symbols: The symbols stepped through, such as ``'circles'``, ``'squares'`` or ``'shaded'``.
        style: Optional style applied to the evolving symbols.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    symbols: _core.EvolveSymbolSet | _core.Expression[str] | None
    """The symbols stepped through, such as ``'circles'``, ``'squares'`` or ``'shaded'``."""

    style: _core.Style | _core.DynamicStyle | None
    """Optional style applied to the evolving symbols."""

    duration_milliseconds: int | _core.Expression[int | float] | None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class ExpandEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.expand', ...)``.

    Attributes:
        direction: ``'horizontal'`` or ``'vertical'``.
        style: Style expanded outward from the center.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    direction: Literal['horizontal', 'vertical'] | _core.Expression[str] | None
    """``'horizontal'`` or ``'vertical'``."""

    style: _core.Style | _core.DynamicStyle | None
    """Style expanded outward from the center."""

    duration_milliseconds: int | _core.Expression[int | float] | None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class StretchEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.stretch', ...)``.

    Attributes:
        direction: ``'left_to_right'``, ``'right_to_left'``, ``'up_to_down'`` or ``'down_to_up'``.
        style: Style stretched across the area.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    direction: MotionDirection | _core.Expression[str] | None
    """``'left_to_right'``, ``'right_to_left'``, ``'up_to_down'`` or ``'down_to_up'``."""

    style: _core.Style | _core.DynamicStyle | None
    """Style stretched across the area."""

    duration_milliseconds: int | _core.Expression[int | float] | None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class ExplodeEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('effect.explode', ...)``.

    Attributes:
        force: Outward force throwing the cells.
        randomness: Variation in force from cell to cell.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    force: float | _core.Expression[int | float] | None
    """Outward force throwing the cells."""

    randomness: float | _core.Expression[int | float] | None
    """Variation in force from cell to cell."""

    duration_milliseconds: int | _core.Expression[int | float] | None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None
    """Optional effect key for replacement or cancellation."""


class BitCrushAudioEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('audio.bit_crush', ...)``.

    Attributes:
        bits: Quantization resolution in bits (``1`` to ``16``).
        downsample: Sample-hold factor (``1`` to ``256``).
    """

    bits: int
    """Quantization resolution in bits (``1`` to ``16``)."""

    downsample: int
    """Sample-hold factor (``1`` to ``256``)."""


class DistortionAudioEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('audio.distortion', ...)``.

    Attributes:
        drive: Input gain before soft-clipping (``0.1`` to ``100.0``).
    """

    drive: float
    """Input gain before soft-clipping (``0.1`` to ``100.0``)."""


class LowPassAudioEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('audio.low_pass', ...)``.

    Attributes:
        cutoff: Corner frequency in hertz (``20.0`` to ``20000.0``).
        resonance: Filter resonance Q (``0.1`` to ``20.0``).
    """

    cutoff: float
    """Corner frequency in hertz (``20.0`` to ``20000.0``)."""

    resonance: float
    """Filter resonance Q (``0.1`` to ``20.0``)."""


class HighPassAudioEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('audio.high_pass', ...)``.

    Attributes:
        cutoff: Corner frequency in hertz (``20.0`` to ``20000.0``).
        resonance: Filter resonance Q (``0.1`` to ``20.0``).
    """

    cutoff: float
    """Corner frequency in hertz (``20.0`` to ``20000.0``)."""

    resonance: float
    """Filter resonance Q (``0.1`` to ``20.0``)."""


class DelayAudioEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('audio.delay', ...)``.

    Attributes:
        time_milliseconds: Delay time between echoes in milliseconds (``1.0`` to ``2000.0``).
        feedback: Echo feedback ratio (``0.0`` to ``0.95``).
        mix: Wet/dry mix ratio (``0.0`` to ``1.0``).
    """

    time_milliseconds: float
    """Delay time between echoes in milliseconds (``1.0`` to ``2000.0``)."""

    feedback: float
    """Echo feedback ratio (``0.0`` to ``0.95``)."""

    mix: float
    """Wet/dry mix ratio (``0.0`` to ``1.0``)."""


class ReverbAudioEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('audio.reverb', ...)``.

    Attributes:
        room: Room size (``0.0`` to ``1.0``).
        damping: High-frequency damping (``0.0`` to ``1.0``).
        mix: Wet/dry mix ratio (``0.0`` to ``1.0``).
    """

    room: float
    """Room size (``0.0`` to ``1.0``)."""

    damping: float
    """High-frequency damping (``0.0`` to ``1.0``)."""

    mix: float
    """Wet/dry mix ratio (``0.0`` to ``1.0``)."""


class TremoloAudioEffectParametersSchema(TypedDict, total=False):
    """
    The keyword arguments of ``effect('audio.tremolo', ...)``.

    Attributes:
        rate_hertz: Modulation rate in hertz (``0.1`` to ``40.0``).
        depth: Modulation depth (``0.0`` to ``1.0``).
    """

    rate_hertz: float
    """Modulation rate in hertz (``0.1`` to ``40.0``)."""

    depth: float
    """Modulation depth (``0.0`` to ``1.0``)."""


RenderableEffectKind: TypeAlias = Literal[
    'effect.fade_to',
    'effect.fade_from',
    'effect.paint',
    'effect.saturate',
    'effect.lighten',
    'effect.darken',
    'effect.sweep_in',
    'effect.sweep_out',
    'effect.slide_in',
    'effect.slide_out',
    'effect.hsl_shift',
    'effect.dissolve',
    'effect.coalesce',
    'effect.glitch',
    'effect.sleep',
    'effect.evolve',
    'effect.evolve_into',
    'effect.evolve_from',
    'effect.expand',
    'effect.stretch',
    'effect.explode',
]
"""
The kinds of effect that change how a buffer looks.

They are the kinds of ``effect`` that start with ``'effect.'``, such as ``'effect.fade_to'``.
"""

PlayableEffectKind: TypeAlias = Literal[
    'audio.bit_crush',
    'audio.distortion',
    'audio.low_pass',
    'audio.high_pass',
    'audio.delay',
    'audio.reverb',
    'audio.tremolo',
]
"""
The kinds of effect that change how a sound plays.

They are the kinds of ``effect`` that start with ``'audio.'``, such as ``'audio.reverb'``.
"""

EffectKind: TypeAlias = Literal[RenderableEffectKind, PlayableEffectKind]
"""Every kind of effect that ``effect(kind, ...)`` accepts: the visual kinds and the sound kinds."""


class FadeToEffectSpecification(FadeToEffectParametersSchema):
    """
    The dictionary form of the ``'effect.fade_to'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.fade_to'``.
    """

    kind: Required[Literal['effect.fade_to']]
    """Always ``'effect.fade_to'``."""


class FadeFromEffectSpecification(FadeFromEffectParametersSchema):
    """
    The dictionary form of the ``'effect.fade_from'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.fade_from'``.
    """

    kind: Required[Literal['effect.fade_from']]
    """Always ``'effect.fade_from'``."""


class PaintEffectSpecification(PaintEffectParametersSchema):
    """
    The dictionary form of the ``'effect.paint'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.paint'``.
    """

    kind: Required[Literal['effect.paint']]
    """Always ``'effect.paint'``."""


class SaturateEffectSpecification(SaturateEffectParametersSchema):
    """
    The dictionary form of the ``'effect.saturate'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.saturate'``.
    """

    kind: Required[Literal['effect.saturate']]
    """Always ``'effect.saturate'``."""


class LightenEffectSpecification(LightenEffectParametersSchema):
    """
    The dictionary form of the ``'effect.lighten'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.lighten'``.
    """

    kind: Required[Literal['effect.lighten']]
    """Always ``'effect.lighten'``."""


class DarkenEffectSpecification(DarkenEffectParametersSchema):
    """
    The dictionary form of the ``'effect.darken'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.darken'``.
    """

    kind: Required[Literal['effect.darken']]
    """Always ``'effect.darken'``."""


class SweepInEffectSpecification(SweepInEffectParametersSchema):
    """
    The dictionary form of the ``'effect.sweep_in'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.sweep_in'``.
    """

    kind: Required[Literal['effect.sweep_in']]
    """Always ``'effect.sweep_in'``."""


class SweepOutEffectSpecification(SweepOutEffectParametersSchema):
    """
    The dictionary form of the ``'effect.sweep_out'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.sweep_out'``.
    """

    kind: Required[Literal['effect.sweep_out']]
    """Always ``'effect.sweep_out'``."""


class SlideInEffectSpecification(SlideInEffectParametersSchema):
    """
    The dictionary form of the ``'effect.slide_in'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.slide_in'``.
    """

    kind: Required[Literal['effect.slide_in']]
    """Always ``'effect.slide_in'``."""


class SlideOutEffectSpecification(SlideOutEffectParametersSchema):
    """
    The dictionary form of the ``'effect.slide_out'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.slide_out'``.
    """

    kind: Required[Literal['effect.slide_out']]
    """Always ``'effect.slide_out'``."""


class HslShiftEffectSpecification(HslShiftEffectParametersSchema):
    """
    The dictionary form of the ``'effect.hsl_shift'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.hsl_shift'``.
    """

    kind: Required[Literal['effect.hsl_shift']]
    """Always ``'effect.hsl_shift'``."""


class DissolveEffectSpecification(DissolveEffectParametersSchema):
    """
    The dictionary form of the ``'effect.dissolve'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.dissolve'``.
    """

    kind: Required[Literal['effect.dissolve']]
    """Always ``'effect.dissolve'``."""


class CoalesceEffectSpecification(CoalesceEffectParametersSchema):
    """
    The dictionary form of the ``'effect.coalesce'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.coalesce'``.
    """

    kind: Required[Literal['effect.coalesce']]
    """Always ``'effect.coalesce'``."""


class GlitchEffectSpecification(GlitchEffectParametersSchema):
    """
    The dictionary form of the ``'effect.glitch'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.glitch'``.
    """

    kind: Required[Literal['effect.glitch']]
    """Always ``'effect.glitch'``."""


class SleepEffectSpecification(SleepEffectParametersSchema):
    """
    The dictionary form of the ``'effect.sleep'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.sleep'``.
    """

    kind: Required[Literal['effect.sleep']]
    """Always ``'effect.sleep'``."""


class EvolveEffectSpecification(EvolveEffectParametersSchema):
    """
    The dictionary form of the ``'effect.evolve'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.evolve'``.
    """

    kind: Required[Literal['effect.evolve']]
    """Always ``'effect.evolve'``."""


class EvolveIntoEffectSpecification(EvolveIntoEffectParametersSchema):
    """
    The dictionary form of the ``'effect.evolve_into'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.evolve_into'``.
    """

    kind: Required[Literal['effect.evolve_into']]
    """Always ``'effect.evolve_into'``."""


class EvolveFromEffectSpecification(EvolveFromEffectParametersSchema):
    """
    The dictionary form of the ``'effect.evolve_from'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.evolve_from'``.
    """

    kind: Required[Literal['effect.evolve_from']]
    """Always ``'effect.evolve_from'``."""


class ExpandEffectSpecification(ExpandEffectParametersSchema):
    """
    The dictionary form of the ``'effect.expand'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.expand'``.
    """

    kind: Required[Literal['effect.expand']]
    """Always ``'effect.expand'``."""


class StretchEffectSpecification(StretchEffectParametersSchema):
    """
    The dictionary form of the ``'effect.stretch'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.stretch'``.
    """

    kind: Required[Literal['effect.stretch']]
    """Always ``'effect.stretch'``."""


class ExplodeEffectSpecification(ExplodeEffectParametersSchema):
    """
    The dictionary form of the ``'effect.explode'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.explode'``.
    """

    kind: Required[Literal['effect.explode']]
    """Always ``'effect.explode'``."""


class BitCrushAudioEffectSpecification(BitCrushAudioEffectParametersSchema):
    """
    The dictionary form of the ``'audio.bit_crush'`` sound effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'audio.bit_crush'``.
    """

    kind: Required[Literal['audio.bit_crush']]
    """Always ``'audio.bit_crush'``."""


class DistortionAudioEffectSpecification(DistortionAudioEffectParametersSchema):
    """
    The dictionary form of the ``'audio.distortion'`` sound effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'audio.distortion'``.
    """

    kind: Required[Literal['audio.distortion']]
    """Always ``'audio.distortion'``."""


class LowPassAudioEffectSpecification(LowPassAudioEffectParametersSchema):
    """
    The dictionary form of the ``'audio.low_pass'`` sound effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'audio.low_pass'``.
    """

    kind: Required[Literal['audio.low_pass']]
    """Always ``'audio.low_pass'``."""


class HighPassAudioEffectSpecification(HighPassAudioEffectParametersSchema):
    """
    The dictionary form of the ``'audio.high_pass'`` sound effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'audio.high_pass'``.
    """

    kind: Required[Literal['audio.high_pass']]
    """Always ``'audio.high_pass'``."""


class DelayAudioEffectSpecification(DelayAudioEffectParametersSchema):
    """
    The dictionary form of the ``'audio.delay'`` sound effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'audio.delay'``.
    """

    kind: Required[Literal['audio.delay']]
    """Always ``'audio.delay'``."""


class ReverbAudioEffectSpecification(ReverbAudioEffectParametersSchema):
    """
    The dictionary form of the ``'audio.reverb'`` sound effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'audio.reverb'``.
    """

    kind: Required[Literal['audio.reverb']]
    """Always ``'audio.reverb'``."""


class TremoloAudioEffectSpecification(TremoloAudioEffectParametersSchema):
    """
    The dictionary form of the ``'audio.tremolo'`` sound effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'audio.tremolo'``.
    """

    kind: Required[Literal['audio.tremolo']]
    """Always ``'audio.tremolo'``."""


RenderableEffectSpecification: TypeAlias = (
    FadeToEffectSpecification
    | FadeFromEffectSpecification
    | PaintEffectSpecification
    | SaturateEffectSpecification
    | LightenEffectSpecification
    | DarkenEffectSpecification
    | SweepInEffectSpecification
    | SweepOutEffectSpecification
    | SlideInEffectSpecification
    | SlideOutEffectSpecification
    | HslShiftEffectSpecification
    | DissolveEffectSpecification
    | CoalesceEffectSpecification
    | GlitchEffectSpecification
    | SleepEffectSpecification
    | EvolveEffectSpecification
    | EvolveIntoEffectSpecification
    | EvolveFromEffectSpecification
    | ExpandEffectSpecification
    | StretchEffectSpecification
    | ExplodeEffectSpecification
)
"""One visual effect as a dictionary for ``effects=[...]``: its ``kind`` and its keywords."""

PlayableEffectSpecification: TypeAlias = (
    BitCrushAudioEffectSpecification
    | DistortionAudioEffectSpecification
    | LowPassAudioEffectSpecification
    | HighPassAudioEffectSpecification
    | DelayAudioEffectSpecification
    | ReverbAudioEffectSpecification
    | TremoloAudioEffectSpecification
)
"""One sound effect as a dictionary for ``effects=[...]``: its ``kind`` and its keywords."""

if TYPE_CHECKING:
    RenderableEffect: TypeAlias = (
        FadeToEffectParameters
        | FadeFromEffectParameters
        | PaintEffectParameters
        | SaturateEffectParameters
        | LightenEffectParameters
        | DarkenEffectParameters
        | SweepInEffectParameters
        | SweepOutEffectParameters
        | SlideInEffectParameters
        | SlideOutEffectParameters
        | HslShiftEffectParameters
        | DissolveEffectParameters
        | CoalesceEffectParameters
        | GlitchEffectParameters
        | SleepEffectParameters
        | EvolveEffectParameters
        | EvolveIntoEffectParameters
        | EvolveFromEffectParameters
        | ExpandEffectParameters
        | StretchEffectParameters
        | ExplodeEffectParameters
    )
    """A visual effect as ``effect(...)`` and the methods of ``placement.fx`` and ``context.fx`` return it."""

    PlayableEffect: TypeAlias = (
        BitCrushAudioEffectParameters
        | DistortionAudioEffectParameters
        | LowPassAudioEffectParameters
        | HighPassAudioEffectParameters
        | DelayAudioEffectParameters
        | ReverbAudioEffectParameters
        | TremoloAudioEffectParameters
    )
    """A sound effect as ``effect(...)`` and the methods of ``canvas.audio.fx`` and ``context.fx`` return it."""

    EffectSpecification: TypeAlias = RenderableEffect | PlayableEffect
    """
    Any visual or sound effect, as [`effect`][xnano.effects.effect] returns it.

    This is not [`Effect`][xnano.operations.Effect], the class whose methods build a visual effect
    for ``update``, and it is not the dictionary form that ``effects=[...]`` takes.
    """

_LAZY_UNION_NAMES: Final = ('EffectSpecification', 'PlayableEffect', 'RenderableEffect')
"""
The unions of the parameters classes.

They are built the first time one is read, which happens when ``import xnano`` finishes at
the latest.
"""


def __getattr__(name: str) -> object:
    """Build the unions of the parameters classes the first time one is read, then keep them."""
    if name not in _LAZY_UNION_NAMES:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
    from xnano.effects._registry import EFFECT_PARAMETERS_BY_KIND

    renderable_classes = [
        parameters_class
        for kind, parameters_class in EFFECT_PARAMETERS_BY_KIND.items()
        if kind.startswith('effect.')
    ]
    playable_classes = [
        parameters_class
        for kind, parameters_class in EFFECT_PARAMETERS_BY_KIND.items()
        if kind.startswith('audio.')
    ]
    globals().update(
        RenderableEffect=functools.reduce(operator.or_, renderable_classes),
        PlayableEffect=functools.reduce(operator.or_, playable_classes),
        EffectSpecification=functools.reduce(
            operator.or_, [*renderable_classes, *playable_classes]
        ),
    )
    return globals()[name]


def __dir__() -> list[str]:
    """The names of the module, including the unions that are built when first read."""
    return sorted({*globals(), *_LAZY_UNION_NAMES})
