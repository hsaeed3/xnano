"""
xnano.effects._properties

The dataclasses that hold the parameters of every effect, and the properties that start effects
by name.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast, final, get_args

import xnano_core as _core
from xnano._internal._dynamic_operations import DynamicOperation
from xnano._schema._appearance import ColorValue

# The schemas are read when the module runs, not under `TYPE_CHECKING`, so that
# `typing.get_type_hints` resolves the keyword annotations of the effect methods.
from xnano._schema._effects import (
    BitCrushAudioEffectParametersSchema,
    CoalesceEffectParametersSchema,
    DarkenEffectParametersSchema,
    DelayAudioEffectParametersSchema,
    DissolveEffectParametersSchema,
    DistortionAudioEffectParametersSchema,
    EvolveEffectParametersSchema,
    EvolveFromEffectParametersSchema,
    EvolveIntoEffectParametersSchema,
    ExpandEffectParametersSchema,
    ExplodeEffectParametersSchema,
    FadeFromEffectParametersSchema,
    FadeToEffectParametersSchema,
    GlitchEffectParametersSchema,
    HighPassAudioEffectParametersSchema,
    HslShiftEffectParametersSchema,
    HslShiftTuple,
    LightenEffectParametersSchema,
    LowPassAudioEffectParametersSchema,
    PaintEffectParametersSchema,
    PlayableEffectKind,
    RenderableEffectKind,
    ReverbAudioEffectParametersSchema,
    SaturateEffectParametersSchema,
    SleepEffectParametersSchema,
    SlideInEffectParametersSchema,
    SlideOutEffectParametersSchema,
    StretchEffectParametersSchema,
    SweepInEffectParametersSchema,
    SweepOutEffectParametersSchema,
    TremoloAudioEffectParametersSchema,
)
from xnano._schema._layout import Interpolation, MotionDirection

if sys.version_info >= (3, 11):
    from typing import Unpack
else:
    from typing_extensions import Unpack

if TYPE_CHECKING:
    from collections.abc import Mapping

    from xnano_audio import TerminalAudioEffect

    from xnano._schema._effects import (
        EffectSpecification,
        PlayableEffect,
        RenderableEffect,
    )
    from xnano.audio._player import AudioDevice
    from xnano.canvas import Canvas
    from xnano.placement import Placement


class EffectParameters(DynamicOperation):
    """
    The base of the parameters of every effect that [`effect`][xnano.effects.effect] returns.

    An effect is both a dataclass holding its typed parameters and a native
    [`Customization`][xnano_core.Customization] operation. It can be applied with ``|``,
    passed to ``add`` and ``update``, returned from a [`hook`][xnano.hooks.hook] or listed in
    ``effects=``. The parameters are read when it is applied, so editing a field changes what
    it does.

    Attributes:
        customization_kind: Identifier of the effect kind, such as ``'effect.dissolve'`` or ``'audio.reverb'``.
    """

    def cancel(self) -> None:
        """
        Stop this effect on the target it was applied to.

        Does nothing for an effect that was never applied or has already finished, and for a
        sound effect.

        Examples:
            ```python
            import xnano

            with xnano.new('hi', width=4, height=1) as canvas:
                fade = xnano.effect('effect.fade_to', foreground='red', duration_milliseconds=5000)
                fade.apply_to(canvas)
                fade.cancel()
                fade.cancel()
            ```
        """
        target = self.__dict__.get('_target')
        key = getattr(self, 'key', None)
        if target is None or not isinstance(key, str):
            return
        if not self.customization_kind.startswith('effect.'):
            return
        surface = target._buffer if hasattr(target, '_buffer') else target
        surface.update(_core.CancelEffect(key))


class AudioEffectParameters(EffectParameters):
    """
    The base of the parameters of every sound effect (``'audio.<name>'``).

    Attributes:
        customization_kind: Identifier of the sound effect kind, such as ``'audio.reverb'``.
    """

    if TYPE_CHECKING:

        def to_audio_effect(self) -> TerminalAudioEffect:
            """The [`TerminalAudioEffect`][xnano_audio.TerminalAudioEffect] this effect builds."""
            ...


@dataclass
class FadeToEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.fade_to'`` visual effect (``Effect.fade_to``).

    Attributes:
        foreground: Target foreground color, or ``None``.
        background: Target background color, or ``None``.
        duration_milliseconds: Duration of the fade in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.fade_to'

    foreground: ColorValue | _core.Expression[ColorValue] | None = None
    """Target foreground color, or ``None``."""

    background: ColorValue | _core.Expression[ColorValue] | None = None
    """Target background color, or ``None``."""

    duration_milliseconds: int | _core.Expression[int | float] | None = None
    """Duration of the fade in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None = None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class FadeFromEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.fade_from'`` visual effect (``Effect.fade_from``).

    Attributes:
        foreground: Starting foreground color, or ``None``.
        background: Starting background color, or ``None``.
        duration_milliseconds: Duration of the fade in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.fade_from'

    foreground: ColorValue | _core.Expression[ColorValue] | None = None
    """Starting foreground color, or ``None``."""

    background: ColorValue | _core.Expression[ColorValue] | None = None
    """Starting background color, or ``None``."""

    duration_milliseconds: int | _core.Expression[int | float] | None = None
    """Duration of the fade in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None = None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class PaintEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.paint'`` visual effect (``Effect.paint``).

    Attributes:
        foreground: Foreground color to paint, or ``None``.
        background: Background color to paint, or ``None``.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.paint'

    foreground: ColorValue | _core.Expression[ColorValue] | None = None
    """Foreground color to paint, or ``None``."""

    background: ColorValue | _core.Expression[ColorValue] | None = None
    """Background color to paint, or ``None``."""

    duration_milliseconds: int | _core.Expression[int | float] | None = None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None = None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class SaturateEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.saturate'`` visual effect (``Effect.saturate``).

    Attributes:
        foreground: Foreground saturation change, or ``None``.
        background: Background saturation change, or ``None``.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.saturate'

    foreground: float | _core.Expression[int | float] | None = None
    """Foreground saturation change, or ``None``."""

    background: float | _core.Expression[int | float] | None = None
    """Background saturation change, or ``None``."""

    duration_milliseconds: int | _core.Expression[int | float] | None = None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None = None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class LightenEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.lighten'`` visual effect (``Effect.lighten``).

    Attributes:
        foreground: Foreground lightness increase, or ``None``.
        background: Background lightness increase, or ``None``.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.lighten'

    foreground: float | _core.Expression[int | float] | None = None
    """Foreground lightness increase, or ``None``."""

    background: float | _core.Expression[int | float] | None = None
    """Background lightness increase, or ``None``."""

    duration_milliseconds: int | _core.Expression[int | float] | None = None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None = None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class DarkenEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.darken'`` visual effect (``Effect.darken``).

    Attributes:
        foreground: Foreground darkness increase, or ``None``.
        background: Background darkness increase, or ``None``.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.darken'

    foreground: float | _core.Expression[int | float] | None = None
    """Foreground darkness increase, or ``None``."""

    background: float | _core.Expression[int | float] | None = None
    """Background darkness increase, or ``None``."""

    duration_milliseconds: int | _core.Expression[int | float] | None = None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None = None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class SweepInEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.sweep_in'`` visual effect (``Effect.sweep_in``).

    Attributes:
        direction: Sweep direction (such as ``'left_to_right'``).
        gradient_length: Length of the sweep gradient in cells.
        randomness: Random offset across rows or columns.
        color: Starting sweep color.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.sweep_in'

    direction: MotionDirection | _core.Expression[str] | None = None
    """Sweep direction (such as ``'left_to_right'``)."""

    gradient_length: int | _core.Expression[int | float] | None = None
    """Length of the sweep gradient in cells."""

    randomness: int | _core.Expression[int | float] | None = None
    """Random offset across rows or columns."""

    color: ColorValue | _core.Expression[ColorValue] | None = None
    """Starting sweep color."""

    duration_milliseconds: int | _core.Expression[int | float] | None = None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None = None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class SweepOutEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.sweep_out'`` visual effect (``Effect.sweep_out``).

    Attributes:
        direction: Sweep direction (such as ``'left_to_right'``).
        gradient_length: Length of the sweep gradient in cells.
        randomness: Random offset across rows or columns.
        color: Ending sweep color.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.sweep_out'

    direction: MotionDirection | _core.Expression[str] | None = None
    """Sweep direction (such as ``'left_to_right'``)."""

    gradient_length: int | _core.Expression[int | float] | None = None
    """Length of the sweep gradient in cells."""

    randomness: int | _core.Expression[int | float] | None = None
    """Random offset across rows or columns."""

    color: ColorValue | _core.Expression[ColorValue] | None = None
    """Ending sweep color."""

    duration_milliseconds: int | _core.Expression[int | float] | None = None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None = None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class SlideInEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.slide_in'`` visual effect (``Effect.slide_in``).

    Attributes:
        direction: Slide direction (such as ``'left_to_right'``).
        gradient_length: Length of the gradient trail in cells.
        randomness: Random offset across rows or columns.
        color: Color behind the sliding cells.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.slide_in'

    direction: MotionDirection | _core.Expression[str] | None = None
    """Slide direction (such as ``'left_to_right'``)."""

    gradient_length: int | _core.Expression[int | float] | None = None
    """Length of the gradient trail in cells."""

    randomness: int | _core.Expression[int | float] | None = None
    """Random offset across rows or columns."""

    color: ColorValue | _core.Expression[ColorValue] | None = None
    """Color behind the sliding cells."""

    duration_milliseconds: int | _core.Expression[int | float] | None = None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None = None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class SlideOutEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.slide_out'`` visual effect (``Effect.slide_out``).

    Attributes:
        direction: Slide direction (such as ``'left_to_right'``).
        gradient_length: Length of the gradient trail in cells.
        randomness: Random offset across rows or columns.
        color: Color left behind the sliding cells.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.slide_out'

    direction: MotionDirection | _core.Expression[str] | None = None
    """Slide direction (such as ``'left_to_right'``)."""

    gradient_length: int | _core.Expression[int | float] | None = None
    """Length of the gradient trail in cells."""

    randomness: int | _core.Expression[int | float] | None = None
    """Random offset across rows or columns."""

    color: ColorValue | _core.Expression[ColorValue] | None = None
    """Color left behind the sliding cells."""

    duration_milliseconds: int | _core.Expression[int | float] | None = None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None = None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class HslShiftEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.hsl_shift'`` visual effect (``Effect.hsl_shift``).

    Attributes:
        foreground: ``(hue, saturation, lightness)`` shift for foreground colors.
        background: ``(hue, saturation, lightness)`` shift for background colors.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.hsl_shift'

    foreground: HslShiftTuple | None = None
    """``(hue, saturation, lightness)`` shift for foreground colors."""

    background: HslShiftTuple | None = None
    """``(hue, saturation, lightness)`` shift for background colors."""

    duration_milliseconds: int | _core.Expression[int | float] | None = None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None = None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class DissolveEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.dissolve'`` visual effect (``Effect.dissolve``).

    Attributes:
        style: Style dissolved into.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.dissolve'

    style: _core.Style | _core.DynamicStyle | None = None
    """Style dissolved into."""

    duration_milliseconds: int | _core.Expression[int | float] | None = None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None = None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class CoalesceEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.coalesce'`` visual effect (``Effect.coalesce``).

    Attributes:
        style: Style coalesced from.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.coalesce'

    style: _core.Style | _core.DynamicStyle | None = None
    """Style coalesced from."""

    duration_milliseconds: int | _core.Expression[int | float] | None = None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None = None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class GlitchEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.glitch'`` visual effect (``Effect.glitch``).

    Attributes:
        ratio: Fraction of cells affected by the glitch.
        duration_milliseconds: Duration in milliseconds.
        start_delay_milliseconds: ``(minimum, maximum)`` delay before a cell glitches.
        action_milliseconds: ``(minimum, maximum)`` duration of each cell glitch.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.glitch'

    ratio: float | _core.Expression[int | float] | None = None
    """Fraction of cells affected by the glitch."""

    duration_milliseconds: int | _core.Expression[int | float] | None = None
    """Duration in milliseconds."""

    start_delay_milliseconds: tuple[int, int] = (0, 0)
    """``(minimum, maximum)`` delay before a cell glitches."""

    action_milliseconds: tuple[int, int] = (50, 150)
    """``(minimum, maximum)`` duration of each cell glitch."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class SleepEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.sleep'`` visual effect (``Effect.sleep``).

    Attributes:
        duration_milliseconds: Pause duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.sleep'

    duration_milliseconds: int | _core.Expression[int | float] = 500
    """Pause duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None = None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class EvolveEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.evolve'`` visual effect (``Effect.evolve``).

    Attributes:
        symbols: The symbols stepped through, such as ``'circles'``, ``'squares'`` or ``'shaded'``.
        style: Optional style applied to the evolving symbols.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.evolve'

    symbols: _core.EvolveSymbolSet | _core.Expression[str] | None = None
    """The symbols stepped through, such as ``'circles'``, ``'squares'`` or ``'shaded'``."""

    style: _core.Style | _core.DynamicStyle | None = None
    """Optional style applied to the evolving symbols."""

    duration_milliseconds: int | _core.Expression[int | float] | None = None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None = None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class EvolveIntoEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.evolve_into'`` visual effect (``Effect.evolve_into``).

    Attributes:
        symbols: The symbols stepped through, such as ``'circles'``, ``'squares'`` or ``'shaded'``.
        style: Optional style applied to the evolving symbols.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.evolve_into'

    symbols: _core.EvolveSymbolSet | _core.Expression[str] | None = None
    """The symbols stepped through, such as ``'circles'``, ``'squares'`` or ``'shaded'``."""

    style: _core.Style | _core.DynamicStyle | None = None
    """Optional style applied to the evolving symbols."""

    duration_milliseconds: int | _core.Expression[int | float] | None = None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None = None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class EvolveFromEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.evolve_from'`` visual effect (``Effect.evolve_from``).

    Attributes:
        symbols: The symbols stepped through, such as ``'circles'``, ``'squares'`` or ``'shaded'``.
        style: Optional style applied to the evolving symbols.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.evolve_from'

    symbols: _core.EvolveSymbolSet | _core.Expression[str] | None = None
    """The symbols stepped through, such as ``'circles'``, ``'squares'`` or ``'shaded'``."""

    style: _core.Style | _core.DynamicStyle | None = None
    """Optional style applied to the evolving symbols."""

    duration_milliseconds: int | _core.Expression[int | float] | None = None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None = None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class ExpandEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.expand'`` visual effect (``Effect.expand``).

    Attributes:
        direction: ``'horizontal'`` or ``'vertical'``.
        style: Style expanded outward from the center.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.expand'

    direction: Literal['horizontal', 'vertical'] | _core.Expression[str] | None = None
    """``'horizontal'`` or ``'vertical'``."""

    style: _core.Style | _core.DynamicStyle | None = None
    """Style expanded outward from the center."""

    duration_milliseconds: int | _core.Expression[int | float] | None = None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None = None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class StretchEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.stretch'`` visual effect (``Effect.stretch``).

    Attributes:
        direction: ``'left_to_right'``, ``'right_to_left'``, ``'up_to_down'`` or ``'down_to_up'``.
        style: Style stretched across the area.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.stretch'

    direction: MotionDirection | _core.Expression[str] | None = None
    """``'left_to_right'``, ``'right_to_left'``, ``'up_to_down'`` or ``'down_to_up'``."""

    style: _core.Style | _core.DynamicStyle | None = None
    """Style stretched across the area."""

    duration_milliseconds: int | _core.Expression[int | float] | None = None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None = None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class ExplodeEffectParameters(EffectParameters):
    """
    The parameters of the ``'effect.explode'`` visual effect (``Effect.explode``).

    Attributes:
        force: Outward force throwing the cells.
        randomness: Variation in force from cell to cell.
        duration_milliseconds: Duration in milliseconds.
        interpolation: The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.explode'

    force: float | _core.Expression[int | float] | None = None
    """Outward force throwing the cells."""

    randomness: float | _core.Expression[int | float] | None = None
    """Variation in force from cell to cell."""

    duration_milliseconds: int | _core.Expression[int | float] | None = None
    """Duration in milliseconds."""

    interpolation: Interpolation | _core.Expression[str] | None = None
    """The easing curve, such as ``'linear'`` or ``'quad_in_out'``."""

    key: str | _core.Expression[str] | None = None
    """Optional effect key for replacement or cancellation."""


@dataclass
class BitCrushAudioEffectParameters(AudioEffectParameters):
    """
    The parameters of the ``'audio.bit_crush'`` sound effect.

    Attributes:
        bits: Quantization resolution in bits (``1`` to ``16``).
        downsample: Sample-hold factor (``1`` to ``256``).
    """

    customization_kind = 'audio.bit_crush'

    bits: int = 8
    """Quantization resolution in bits (``1`` to ``16``)."""

    downsample: int = 4
    """Sample-hold factor (``1`` to ``256``)."""


@dataclass
class DistortionAudioEffectParameters(AudioEffectParameters):
    """
    The parameters of the ``'audio.distortion'`` sound effect.

    Attributes:
        drive: Input gain before soft-clipping (``0.1`` to ``100.0``).
    """

    customization_kind = 'audio.distortion'

    drive: float = 4.0
    """Input gain before soft-clipping (``0.1`` to ``100.0``)."""


@dataclass
class LowPassAudioEffectParameters(AudioEffectParameters):
    """
    The parameters of the ``'audio.low_pass'`` sound effect.

    Attributes:
        cutoff: Corner frequency in hertz (``20.0`` to ``20000.0``).
        resonance: Filter resonance Q (``0.1`` to ``20.0``).
    """

    customization_kind = 'audio.low_pass'

    cutoff: float = 1200.0
    """Corner frequency in hertz (``20.0`` to ``20000.0``)."""

    resonance: float = 0.707
    """Filter resonance Q (``0.1`` to ``20.0``)."""


@dataclass
class HighPassAudioEffectParameters(AudioEffectParameters):
    """
    The parameters of the ``'audio.high_pass'`` sound effect.

    Attributes:
        cutoff: Corner frequency in hertz (``20.0`` to ``20000.0``).
        resonance: Filter resonance Q (``0.1`` to ``20.0``).
    """

    customization_kind = 'audio.high_pass'

    cutoff: float = 400.0
    """Corner frequency in hertz (``20.0`` to ``20000.0``)."""

    resonance: float = 0.707
    """Filter resonance Q (``0.1`` to ``20.0``)."""


@dataclass
class DelayAudioEffectParameters(AudioEffectParameters):
    """
    The parameters of the ``'audio.delay'`` sound effect.

    Attributes:
        time_milliseconds: Delay time between echoes in milliseconds (``1.0`` to ``2000.0``).
        feedback: Echo feedback ratio (``0.0`` to ``0.95``).
        mix: Wet/dry mix ratio (``0.0`` to ``1.0``).
    """

    customization_kind = 'audio.delay'

    time_milliseconds: float = 250.0
    """Delay time between echoes in milliseconds (``1.0`` to ``2000.0``)."""

    feedback: float = 0.4
    """Echo feedback ratio (``0.0`` to ``0.95``)."""

    mix: float = 0.35
    """Wet/dry mix ratio (``0.0`` to ``1.0``)."""


@dataclass
class ReverbAudioEffectParameters(AudioEffectParameters):
    """
    The parameters of the ``'audio.reverb'`` sound effect.

    Attributes:
        room: Room size (``0.0`` to ``1.0``).
        damping: High-frequency damping (``0.0`` to ``1.0``).
        mix: Wet/dry mix ratio (``0.0`` to ``1.0``).
    """

    customization_kind = 'audio.reverb'

    room: float = 0.5
    """Room size (``0.0`` to ``1.0``)."""

    damping: float = 0.5
    """High-frequency damping (``0.0`` to ``1.0``)."""

    mix: float = 0.25
    """Wet/dry mix ratio (``0.0`` to ``1.0``)."""


@dataclass
class TremoloAudioEffectParameters(AudioEffectParameters):
    """
    The parameters of the ``'audio.tremolo'`` sound effect.

    Attributes:
        rate_hertz: Modulation rate in hertz (``0.1`` to ``40.0``).
        depth: Modulation depth (``0.0`` to ``1.0``).
    """

    customization_kind = 'audio.tremolo'

    rate_hertz: float = 5.0
    """Modulation rate in hertz (``0.1`` to ``40.0``)."""

    depth: float = 0.5
    """Modulation depth (``0.0`` to ``1.0``)."""


_RENDERABLE_NAMES = tuple(
    sorted(kind.partition('.')[2] for kind in get_args(RenderableEffectKind))
)
_PLAYABLE_NAMES = tuple(
    sorted(kind.partition('.')[2] for kind in get_args(PlayableEffectKind))
)


def _unknown_effect(
    owner: str, name: str, *, has_visual: bool, has_sound: bool
) -> AttributeError:
    """The error for ``owner.name`` when ``name`` is not one of its effects."""
    if not has_sound and name in _PLAYABLE_NAMES:
        return AttributeError(
            f'{name} is a sound effect, and {owner} has the visual effects only. Add it to '
            f'what the canvas plays with canvas.audio.fx.{name}(...), or to what one hook '
            f'plays with context.fx.{name}(...).'
        )
    if not has_visual and name in _RENDERABLE_NAMES:
        return AttributeError(
            f'{name} is a visual effect, and {owner} has the sound effects only. Start it on '
            f'a placement with placement.fx.{name}(...), on the canvas with '
            f"canvas.fx.{name}(...), or on a hook's buffer with context.fx.{name}(...)."
        )
    names = (_RENDERABLE_NAMES if has_visual else ()) + (
        _PLAYABLE_NAMES if has_sound else ()
    )
    return AttributeError(
        f'{owner} has no effect named {name!r}. Use one of: {", ".join(names)}, or '
        f'active and clear().'
    )


class _RenderableEffectMethods:
    """One method for each visual effect, which starts it on a buffer."""

    __slots__ = ()

    def _start(self, kind: str, parameters: Mapping[str, object]) -> EffectSpecification:
        raise NotImplementedError

    def fade_to(
        self, **parameters: Unpack[FadeToEffectParametersSchema]
    ) -> FadeToEffectParameters:
        """
        Fade the colors to ``foreground`` and ``background``.

        Keyword Args:
            foreground (ColorValue | Expression[ColorValue] | None): Target foreground color, or ``None``.
            background (ColorValue | Expression[ColorValue] | None): Target background color, or ``None``.
            duration_milliseconds (int | Expression[int | float] | None): Duration of the fade in milliseconds.
            interpolation (Interpolation | Expression[str] | None): The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast('FadeToEffectParameters', self._start('effect.fade_to', parameters))

    def fade_from(
        self, **parameters: Unpack[FadeFromEffectParametersSchema]
    ) -> FadeFromEffectParameters:
        """
        Fade the colors in from ``foreground`` and ``background``.

        Keyword Args:
            foreground (ColorValue | Expression[ColorValue] | None): Starting foreground color, or ``None``.
            background (ColorValue | Expression[ColorValue] | None): Starting background color, or ``None``.
            duration_milliseconds (int | Expression[int | float] | None): Duration of the fade in milliseconds.
            interpolation (Interpolation | Expression[str] | None): The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast(
            'FadeFromEffectParameters', self._start('effect.fade_from', parameters)
        )

    def paint(
        self, **parameters: Unpack[PaintEffectParametersSchema]
    ) -> PaintEffectParameters:
        """
        Paint ``foreground`` and ``background`` over the colors.

        Keyword Args:
            foreground (ColorValue | Expression[ColorValue] | None): Foreground color to paint, or ``None``.
            background (ColorValue | Expression[ColorValue] | None): Background color to paint, or ``None``.
            duration_milliseconds (int | Expression[int | float] | None): Duration in milliseconds.
            interpolation (Interpolation | Expression[str] | None): The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast('PaintEffectParameters', self._start('effect.paint', parameters))

    def saturate(
        self, **parameters: Unpack[SaturateEffectParametersSchema]
    ) -> SaturateEffectParameters:
        """
        Make the colors more or less saturated.

        Keyword Args:
            foreground (float | Expression[int | float] | None): Foreground saturation change, or ``None``.
            background (float | Expression[int | float] | None): Background saturation change, or ``None``.
            duration_milliseconds (int | Expression[int | float] | None): Duration in milliseconds.
            interpolation (Interpolation | Expression[str] | None): The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast(
            'SaturateEffectParameters', self._start('effect.saturate', parameters)
        )

    def lighten(
        self, **parameters: Unpack[LightenEffectParametersSchema]
    ) -> LightenEffectParameters:
        """
        Lighten the colors.

        Keyword Args:
            foreground (float | Expression[int | float] | None): Foreground lightness increase, or ``None``.
            background (float | Expression[int | float] | None): Background lightness increase, or ``None``.
            duration_milliseconds (int | Expression[int | float] | None): Duration in milliseconds.
            interpolation (Interpolation | Expression[str] | None): The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast('LightenEffectParameters', self._start('effect.lighten', parameters))

    def darken(
        self, **parameters: Unpack[DarkenEffectParametersSchema]
    ) -> DarkenEffectParameters:
        """
        Darken the colors.

        Keyword Args:
            foreground (float | Expression[int | float] | None): Foreground darkness increase, or ``None``.
            background (float | Expression[int | float] | None): Background darkness increase, or ``None``.
            duration_milliseconds (int | Expression[int | float] | None): Duration in milliseconds.
            interpolation (Interpolation | Expression[str] | None): The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast('DarkenEffectParameters', self._start('effect.darken', parameters))

    def sweep_in(
        self, **parameters: Unpack[SweepInEffectParametersSchema]
    ) -> SweepInEffectParameters:
        """
        Reveal the content behind a sweep of ``color`` in ``direction``.

        Keyword Args:
            direction (MotionDirection | Expression[str] | None): Sweep direction (such as ``'left_to_right'``).
            gradient_length (int | Expression[int | float] | None): Length of the sweep gradient in cells.
            randomness (int | Expression[int | float] | None): Random offset across rows or columns.
            color (ColorValue | Expression[ColorValue] | None): Starting sweep color.
            duration_milliseconds (int | Expression[int | float] | None): Duration in milliseconds.
            interpolation (Interpolation | Expression[str] | None): The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast('SweepInEffectParameters', self._start('effect.sweep_in', parameters))

    def sweep_out(
        self, **parameters: Unpack[SweepOutEffectParametersSchema]
    ) -> SweepOutEffectParameters:
        """
        Hide the content behind a sweep of ``color`` in ``direction``.

        Keyword Args:
            direction (MotionDirection | Expression[str] | None): Sweep direction (such as ``'left_to_right'``).
            gradient_length (int | Expression[int | float] | None): Length of the sweep gradient in cells.
            randomness (int | Expression[int | float] | None): Random offset across rows or columns.
            color (ColorValue | Expression[ColorValue] | None): Ending sweep color.
            duration_milliseconds (int | Expression[int | float] | None): Duration in milliseconds.
            interpolation (Interpolation | Expression[str] | None): The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast(
            'SweepOutEffectParameters', self._start('effect.sweep_out', parameters)
        )

    def slide_in(
        self, **parameters: Unpack[SlideInEffectParametersSchema]
    ) -> SlideInEffectParameters:
        """
        Slide the content in, in ``direction``.

        Keyword Args:
            direction (MotionDirection | Expression[str] | None): Slide direction (such as ``'left_to_right'``).
            gradient_length (int | Expression[int | float] | None): Length of the gradient trail in cells.
            randomness (int | Expression[int | float] | None): Random offset across rows or columns.
            color (ColorValue | Expression[ColorValue] | None): Color behind the sliding cells.
            duration_milliseconds (int | Expression[int | float] | None): Duration in milliseconds.
            interpolation (Interpolation | Expression[str] | None): The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast('SlideInEffectParameters', self._start('effect.slide_in', parameters))

    def slide_out(
        self, **parameters: Unpack[SlideOutEffectParametersSchema]
    ) -> SlideOutEffectParameters:
        """
        Slide the content out, in ``direction``.

        Keyword Args:
            direction (MotionDirection | Expression[str] | None): Slide direction (such as ``'left_to_right'``).
            gradient_length (int | Expression[int | float] | None): Length of the gradient trail in cells.
            randomness (int | Expression[int | float] | None): Random offset across rows or columns.
            color (ColorValue | Expression[ColorValue] | None): Color left behind the sliding cells.
            duration_milliseconds (int | Expression[int | float] | None): Duration in milliseconds.
            interpolation (Interpolation | Expression[str] | None): The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast(
            'SlideOutEffectParameters', self._start('effect.slide_out', parameters)
        )

    def hsl_shift(
        self, **parameters: Unpack[HslShiftEffectParametersSchema]
    ) -> HslShiftEffectParameters:
        """
        Shift the hue, saturation and lightness of the colors.

        Keyword Args:
            foreground (HslShiftTuple | None): ``(hue, saturation, lightness)`` shift for foreground colors.
            background (HslShiftTuple | None): ``(hue, saturation, lightness)`` shift for background colors.
            duration_milliseconds (int | Expression[int | float] | None): Duration in milliseconds.
            interpolation (Interpolation | Expression[str] | None): The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast(
            'HslShiftEffectParameters', self._start('effect.hsl_shift', parameters)
        )

    def dissolve(
        self, **parameters: Unpack[DissolveEffectParametersSchema]
    ) -> DissolveEffectParameters:
        """
        Dissolve the content into ``style``, cell by cell.

        Keyword Args:
            style (Style | DynamicStyle | None): Style dissolved into.
            duration_milliseconds (int | Expression[int | float] | None): Duration in milliseconds.
            interpolation (Interpolation | Expression[str] | None): The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast(
            'DissolveEffectParameters', self._start('effect.dissolve', parameters)
        )

    def coalesce(
        self, **parameters: Unpack[CoalesceEffectParametersSchema]
    ) -> CoalesceEffectParameters:
        """
        Bring the content together out of ``style``, cell by cell.

        Keyword Args:
            style (Style | DynamicStyle | None): Style coalesced from.
            duration_milliseconds (int | Expression[int | float] | None): Duration in milliseconds.
            interpolation (Interpolation | Expression[str] | None): The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast(
            'CoalesceEffectParameters', self._start('effect.coalesce', parameters)
        )

    def glitch(
        self, **parameters: Unpack[GlitchEffectParametersSchema]
    ) -> GlitchEffectParameters:
        """
        Make a share of the cells glitch for a moment.

        Keyword Args:
            ratio (float | Expression[int | float] | None): Fraction of cells affected by the glitch.
            duration_milliseconds (int | Expression[int | float] | None): Duration in milliseconds.
            start_delay_milliseconds (tuple[int, int]): ``(minimum, maximum)`` delay before a cell glitches.
            action_milliseconds (tuple[int, int]): ``(minimum, maximum)`` duration of each cell glitch.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast('GlitchEffectParameters', self._start('effect.glitch', parameters))

    def sleep(
        self, **parameters: Unpack[SleepEffectParametersSchema]
    ) -> SleepEffectParameters:
        """
        Wait for ``duration_milliseconds`` without changing anything.

        Keyword Args:
            duration_milliseconds (int | Expression[int | float]): Pause duration in milliseconds.
            interpolation (Interpolation | Expression[str] | None): The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast('SleepEffectParameters', self._start('effect.sleep', parameters))

    def evolve(
        self, **parameters: Unpack[EvolveEffectParametersSchema]
    ) -> EvolveEffectParameters:
        """
        Cycle the cells through a progression of ``symbols``.

        Keyword Args:
            symbols (EvolveSymbolSet | Expression[str] | None): The symbols stepped through, such as ``'circles'``, ``'squares'`` or ``'shaded'``.
            style (Style | DynamicStyle | None): Optional style applied to the evolving symbols.
            duration_milliseconds (int | Expression[int | float] | None): Duration in milliseconds.
            interpolation (Interpolation | Expression[str] | None): The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast('EvolveEffectParameters', self._start('effect.evolve', parameters))

    def evolve_into(
        self, **parameters: Unpack[EvolveIntoEffectParametersSchema]
    ) -> EvolveIntoEffectParameters:
        """
        Turn the content into a progression of ``symbols``.

        Keyword Args:
            symbols (EvolveSymbolSet | Expression[str] | None): The symbols stepped through, such as ``'circles'``, ``'squares'`` or ``'shaded'``.
            style (Style | DynamicStyle | None): Optional style applied to the evolving symbols.
            duration_milliseconds (int | Expression[int | float] | None): Duration in milliseconds.
            interpolation (Interpolation | Expression[str] | None): The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast(
            'EvolveIntoEffectParameters', self._start('effect.evolve_into', parameters)
        )

    def evolve_from(
        self, **parameters: Unpack[EvolveFromEffectParametersSchema]
    ) -> EvolveFromEffectParameters:
        """
        Grow the content out of a progression of ``symbols``.

        Keyword Args:
            symbols (EvolveSymbolSet | Expression[str] | None): The symbols stepped through, such as ``'circles'``, ``'squares'`` or ``'shaded'``.
            style (Style | DynamicStyle | None): Optional style applied to the evolving symbols.
            duration_milliseconds (int | Expression[int | float] | None): Duration in milliseconds.
            interpolation (Interpolation | Expression[str] | None): The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast(
            'EvolveFromEffectParameters', self._start('effect.evolve_from', parameters)
        )

    def expand(
        self, **parameters: Unpack[ExpandEffectParametersSchema]
    ) -> ExpandEffectParameters:
        """
        Expand ``style`` outward from the center.

        Keyword Args:
            direction (Literal['horizontal', 'vertical'] | Expression[str] | None): ``'horizontal'`` or ``'vertical'``.
            style (Style | DynamicStyle | None): Style expanded outward from the center.
            duration_milliseconds (int | Expression[int | float] | None): Duration in milliseconds.
            interpolation (Interpolation | Expression[str] | None): The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast('ExpandEffectParameters', self._start('effect.expand', parameters))

    def stretch(
        self, **parameters: Unpack[StretchEffectParametersSchema]
    ) -> StretchEffectParameters:
        """
        Stretch ``style`` across the area in ``direction``.

        Keyword Args:
            direction (MotionDirection | Expression[str] | None): ``'left_to_right'``, ``'right_to_left'``, ``'up_to_down'`` or ``'down_to_up'``.
            style (Style | DynamicStyle | None): Style stretched across the area.
            duration_milliseconds (int | Expression[int | float] | None): Duration in milliseconds.
            interpolation (Interpolation | Expression[str] | None): The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast('StretchEffectParameters', self._start('effect.stretch', parameters))

    def explode(
        self, **parameters: Unpack[ExplodeEffectParametersSchema]
    ) -> ExplodeEffectParameters:
        """
        Throw the cells outward.

        Keyword Args:
            force (float | Expression[int | float] | None): Outward force throwing the cells.
            randomness (float | Expression[int | float] | None): Variation in force from cell to cell.
            duration_milliseconds (int | Expression[int | float] | None): Duration in milliseconds.
            interpolation (Interpolation | Expression[str] | None): The easing curve, such as ``'linear'`` or ``'quad_in_out'``.
            key (str | Expression[str] | None): Optional effect key for replacement or cancellation.

        Returns:
            The running effect. Assigning one of its fields starts it again with the new
            values, and ``cancel()`` stops it.
        """
        return cast('ExplodeEffectParameters', self._start('effect.explode', parameters))


class _PlayableEffectMethods:
    """One method for each sound effect, which adds it to the sounds that are played."""

    __slots__ = ()

    def _start(self, kind: str, parameters: Mapping[str, object]) -> EffectSpecification:
        raise NotImplementedError

    def bit_crush(
        self, **parameters: Unpack[BitCrushAudioEffectParametersSchema]
    ) -> BitCrushAudioEffectParameters:
        """
        Lower the resolution of the sound, for a gritty, retro tone.

        Keyword Args:
            bits (int): Quantization resolution in bits (``1`` to ``16``).
            downsample (int): Sample-hold factor (``1`` to ``256``).

        Returns:
            The effect. Assigning one of its fields changes the sounds played after that.
        """
        return cast(
            'BitCrushAudioEffectParameters', self._start('audio.bit_crush', parameters)
        )

    def distortion(
        self, **parameters: Unpack[DistortionAudioEffectParametersSchema]
    ) -> DistortionAudioEffectParameters:
        """
        Distort the sound by driving it into soft clipping.

        Keyword Args:
            drive (float): Input gain before soft-clipping (``0.1`` to ``100.0``).

        Returns:
            The effect. Assigning one of its fields changes the sounds played after that.
        """
        return cast(
            'DistortionAudioEffectParameters', self._start('audio.distortion', parameters)
        )

    def low_pass(
        self, **parameters: Unpack[LowPassAudioEffectParametersSchema]
    ) -> LowPassAudioEffectParameters:
        """
        Keep the frequencies below ``cutoff`` and soften those above it.

        Keyword Args:
            cutoff (float): Corner frequency in hertz (``20.0`` to ``20000.0``).
            resonance (float): Filter resonance Q (``0.1`` to ``20.0``).

        Returns:
            The effect. Assigning one of its fields changes the sounds played after that.
        """
        return cast(
            'LowPassAudioEffectParameters', self._start('audio.low_pass', parameters)
        )

    def high_pass(
        self, **parameters: Unpack[HighPassAudioEffectParametersSchema]
    ) -> HighPassAudioEffectParameters:
        """
        Keep the frequencies above ``cutoff`` and soften those below it.

        Keyword Args:
            cutoff (float): Corner frequency in hertz (``20.0`` to ``20000.0``).
            resonance (float): Filter resonance Q (``0.1`` to ``20.0``).

        Returns:
            The effect. Assigning one of its fields changes the sounds played after that.
        """
        return cast(
            'HighPassAudioEffectParameters', self._start('audio.high_pass', parameters)
        )

    def delay(
        self, **parameters: Unpack[DelayAudioEffectParametersSchema]
    ) -> DelayAudioEffectParameters:
        """
        Repeat the sound as fading echoes.

        Keyword Args:
            time_milliseconds (float): Delay time between echoes in milliseconds (``1.0`` to ``2000.0``).
            feedback (float): Echo feedback ratio (``0.0`` to ``0.95``).
            mix (float): Wet/dry mix ratio (``0.0`` to ``1.0``).

        Returns:
            The effect. Assigning one of its fields changes the sounds played after that.
        """
        return cast('DelayAudioEffectParameters', self._start('audio.delay', parameters))

    def reverb(
        self, **parameters: Unpack[ReverbAudioEffectParametersSchema]
    ) -> ReverbAudioEffectParameters:
        """
        Add the reverberation of a room.

        Keyword Args:
            room (float): Room size (``0.0`` to ``1.0``).
            damping (float): High-frequency damping (``0.0`` to ``1.0``).
            mix (float): Wet/dry mix ratio (``0.0`` to ``1.0``).

        Returns:
            The effect. Assigning one of its fields changes the sounds played after that.
        """
        return cast(
            'ReverbAudioEffectParameters', self._start('audio.reverb', parameters)
        )

    def tremolo(
        self, **parameters: Unpack[TremoloAudioEffectParametersSchema]
    ) -> TremoloAudioEffectParameters:
        """
        Pulse the volume up and down.

        Keyword Args:
            rate_hertz (float): Modulation rate in hertz (``0.1`` to ``40.0``).
            depth (float): Modulation depth (``0.0`` to ``1.0``).

        Returns:
            The effect. Assigning one of its fields changes the sounds played after that.
        """
        return cast(
            'TremoloAudioEffectParameters', self._start('audio.tremolo', parameters)
        )


@final
class RenderableEffectProperties(_RenderableEffectMethods):
    """
    The visual effects of a placement or a canvas, one method for each effect.

    Get it from [`Placement.fx`][xnano.placement.Placement.fx] or
    [`Canvas.fx`][xnano.canvas.Canvas.fx]. Each method starts its effect on that placement or
    canvas at once and returns it while it runs. Starting an effect of a kind that is already
    running replaces the earlier one, ``clear()`` stops them all, and removing the placement
    stops its effects too.

    Attributes:
        active: The effects started here and not cleared or replaced.

    Examples:
        ```python
        import xnano

        with xnano.new(width=8, height=1) as canvas:
            label = canvas.write('hi')
            fade = label.fx.fade_to(foreground='red', duration_milliseconds=100)
            assert label.fx.active == (fade,)
            label.fx.clear()
            assert label.fx.active == ()
        ```
    """

    __slots__ = ('_running', '_target')

    def __getattr__(self, name: str) -> object:
        if name.startswith('_'):
            raise AttributeError(name)
        raise _unknown_effect('placement.fx', name, has_visual=True, has_sound=False)

    def __init__(
        self, target: Canvas[object, object] | Placement[object, object]
    ) -> None:
        """
        Create the effects of a placement or canvas. Use ``placement.fx`` instead.

        Args:
            target: The placement or canvas the effects run on.
        """
        self._target = target
        self._running: dict[str, EffectParameters] = {}

    @property
    def active(self) -> tuple[RenderableEffect, ...]:
        """The effects started here and not cleared or replaced."""
        return cast('tuple[RenderableEffect, ...]', tuple(self._running.values()))

    def clear(self) -> None:
        """Stop every effect started here. Does nothing when none was started."""
        running = tuple(self._running.values())
        self._running.clear()
        for effect in running:
            effect.cancel()

    def _start(self, kind: str, parameters: Mapping[str, object]) -> EffectSpecification:
        from xnano.effects._registry import build_effect

        effect = build_effect(kind, parameters)
        earlier = self._running.get(kind)
        if earlier is not None:
            earlier.cancel()
        self._target.update(effect)
        self._running[kind] = effect
        return cast('EffectSpecification', effect)


@final
class PlayableEffectProperties(_PlayableEffectMethods):
    """
    The sound effects of a canvas's audio, one method for each effect.

    Get it from [`AudioDevice.fx`][xnano.audio.AudioDevice.fx]. Each method adds its effect to
    every sound the canvas plays from then on, after the sound's own effects. A sound that is
    already playing keeps the effects it started with. Adding an effect of a kind that is
    already there replaces the earlier one, and ``clear()`` removes them all.

    Attributes:
        active: The effects added here and not cleared or replaced.

    Examples:
        ```python
        import xnano

        with xnano.new(width=8, height=1) as canvas:
            echo = canvas.audio.fx.delay(time_milliseconds=120.0, feedback=0.4)
            assert canvas.audio.fx.active == (echo,)
            canvas.play('C4')
            canvas.audio.fx.clear()
            assert canvas.audio.fx.active == ()
        ```
    """

    __slots__ = ('_device', '_running')

    def __getattr__(self, name: str) -> object:
        if name.startswith('_'):
            raise AttributeError(name)
        raise _unknown_effect('canvas.audio.fx', name, has_visual=False, has_sound=True)

    def __init__(self, device: AudioDevice) -> None:
        """
        Create the sound effects of a canvas's audio. Use ``canvas.audio.fx`` instead.

        Args:
            device: The audio the effects are added to.
        """
        self._device = device
        self._running: dict[str, AudioEffectParameters] = {}

    @property
    def active(self) -> tuple[PlayableEffect, ...]:
        """The effects added here and not cleared or replaced."""
        return cast('tuple[PlayableEffect, ...]', tuple(self._running.values()))

    def clear(self) -> None:
        """Remove every effect added here, for the sounds played after this."""
        self._running.clear()

    def _audio_effects(self) -> tuple[TerminalAudioEffect, ...]:
        return tuple(effect.to_audio_effect() for effect in self._running.values())

    def _start(self, kind: str, parameters: Mapping[str, object]) -> EffectSpecification:
        from xnano.effects._registry import build_effect

        self._device._canvas._require_open()
        effect = cast('AudioEffectParameters', build_effect(kind, parameters))
        self._running[kind] = effect
        return cast('EffectSpecification', effect)
