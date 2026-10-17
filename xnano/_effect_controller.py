"""
xnano._effect_controller

The named effects of ``placement.fx``, ``canvas.fx``, ``canvas.audio.fx`` and ``context.fx``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast, final, get_args

from xnano._customize import (
    Customization,
    PlayableEffectKind,
    RenderableEffectKind,
    fx,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from typing_extensions import Unpack
    from xnano_audio import TerminalAudioEffect

    from xnano._customize import (
        AudioCustomization,
        BitCrushAudioArguments,
        BitCrushAudioCustomization,
        CoalesceEffectArguments,
        CoalesceEffectCustomization,
        DarkenEffectArguments,
        DarkenEffectCustomization,
        DelayAudioArguments,
        DelayAudioCustomization,
        DissolveEffectArguments,
        DissolveEffectCustomization,
        DistortionAudioArguments,
        DistortionAudioCustomization,
        EffectCustomization,
        EvolveEffectArguments,
        EvolveEffectCustomization,
        EvolveFromEffectArguments,
        EvolveFromEffectCustomization,
        EvolveIntoEffectArguments,
        EvolveIntoEffectCustomization,
        ExpandEffectArguments,
        ExpandEffectCustomization,
        ExplodeEffectArguments,
        ExplodeEffectCustomization,
        FadeFromEffectArguments,
        FadeFromEffectCustomization,
        FadeToEffectArguments,
        FadeToEffectCustomization,
        GlitchEffectArguments,
        GlitchEffectCustomization,
        HighPassAudioArguments,
        HighPassAudioCustomization,
        HslShiftEffectArguments,
        HslShiftEffectCustomization,
        LightenEffectArguments,
        LightenEffectCustomization,
        LowPassAudioArguments,
        LowPassAudioCustomization,
        PaintEffectArguments,
        PaintEffectCustomization,
        PlayableEffect,
        RenderableEffect,
        ReverbAudioArguments,
        ReverbAudioCustomization,
        SaturateEffectArguments,
        SaturateEffectCustomization,
        SleepEffectArguments,
        SleepEffectCustomization,
        SlideInEffectArguments,
        SlideInEffectCustomization,
        SlideOutEffectArguments,
        SlideOutEffectCustomization,
        StretchEffectArguments,
        StretchEffectCustomization,
        SweepInEffectArguments,
        SweepInEffectCustomization,
        SweepOutEffectArguments,
        SweepOutEffectCustomization,
        TremoloAudioArguments,
        TremoloAudioCustomization,
    )
    from xnano.audio import AudioDevice
    from xnano.canvas import Canvas
    from xnano.context import Context
    from xnano.placement import Placement

__all__ = ['EffectController', 'PlayableEffects', 'RenderableEffects']


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


class EffectState:
    """
    The effects one hook has set: visual effects on its buffer and sound effects for what it
    plays. They live as long as the hook does.

    Attributes:
        visual: The visual effects by kind.
        audio: The sound effects by kind.
    """

    __slots__ = ('audio', 'visual')

    def __init__(self) -> None:
        """Start with no effects."""
        self.visual: dict[str, Customization] = {}
        self.audio: dict[str, AudioCustomization] = {}

    def audio_effects(self) -> tuple[TerminalAudioEffect, ...]:
        """The sound effects of the hook, ready to be applied to a sound."""
        return tuple(effect.to_audio_effect() for effect in self.audio.values())

    def clear(self) -> None:
        """Stop the visual effects and forget the sound effects."""
        visual = tuple(self.visual.values())
        self.visual.clear()
        self.audio.clear()
        for effect in visual:
            effect.cancel()


class _RenderableEffectMethods:
    """One method for each visual effect, which starts it on a buffer."""

    __slots__ = ()

    def _start(self, kind: str, parameters: Mapping[str, object]) -> EffectCustomization:
        raise NotImplementedError

    def fade_to(
        self, **parameters: Unpack[FadeToEffectArguments]
    ) -> FadeToEffectCustomization:
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
        return cast(
            'FadeToEffectCustomization', self._start('effect.fade_to', parameters)
        )

    def fade_from(
        self, **parameters: Unpack[FadeFromEffectArguments]
    ) -> FadeFromEffectCustomization:
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
            'FadeFromEffectCustomization', self._start('effect.fade_from', parameters)
        )

    def paint(
        self, **parameters: Unpack[PaintEffectArguments]
    ) -> PaintEffectCustomization:
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
        return cast('PaintEffectCustomization', self._start('effect.paint', parameters))

    def saturate(
        self, **parameters: Unpack[SaturateEffectArguments]
    ) -> SaturateEffectCustomization:
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
            'SaturateEffectCustomization', self._start('effect.saturate', parameters)
        )

    def lighten(
        self, **parameters: Unpack[LightenEffectArguments]
    ) -> LightenEffectCustomization:
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
        return cast(
            'LightenEffectCustomization', self._start('effect.lighten', parameters)
        )

    def darken(
        self, **parameters: Unpack[DarkenEffectArguments]
    ) -> DarkenEffectCustomization:
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
        return cast('DarkenEffectCustomization', self._start('effect.darken', parameters))

    def sweep_in(
        self, **parameters: Unpack[SweepInEffectArguments]
    ) -> SweepInEffectCustomization:
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
        return cast(
            'SweepInEffectCustomization', self._start('effect.sweep_in', parameters)
        )

    def sweep_out(
        self, **parameters: Unpack[SweepOutEffectArguments]
    ) -> SweepOutEffectCustomization:
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
            'SweepOutEffectCustomization', self._start('effect.sweep_out', parameters)
        )

    def slide_in(
        self, **parameters: Unpack[SlideInEffectArguments]
    ) -> SlideInEffectCustomization:
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
        return cast(
            'SlideInEffectCustomization', self._start('effect.slide_in', parameters)
        )

    def slide_out(
        self, **parameters: Unpack[SlideOutEffectArguments]
    ) -> SlideOutEffectCustomization:
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
            'SlideOutEffectCustomization', self._start('effect.slide_out', parameters)
        )

    def hsl_shift(
        self, **parameters: Unpack[HslShiftEffectArguments]
    ) -> HslShiftEffectCustomization:
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
            'HslShiftEffectCustomization', self._start('effect.hsl_shift', parameters)
        )

    def dissolve(
        self, **parameters: Unpack[DissolveEffectArguments]
    ) -> DissolveEffectCustomization:
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
            'DissolveEffectCustomization', self._start('effect.dissolve', parameters)
        )

    def coalesce(
        self, **parameters: Unpack[CoalesceEffectArguments]
    ) -> CoalesceEffectCustomization:
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
            'CoalesceEffectCustomization', self._start('effect.coalesce', parameters)
        )

    def glitch(
        self, **parameters: Unpack[GlitchEffectArguments]
    ) -> GlitchEffectCustomization:
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
        return cast('GlitchEffectCustomization', self._start('effect.glitch', parameters))

    def sleep(
        self, **parameters: Unpack[SleepEffectArguments]
    ) -> SleepEffectCustomization:
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
        return cast('SleepEffectCustomization', self._start('effect.sleep', parameters))

    def evolve(
        self, **parameters: Unpack[EvolveEffectArguments]
    ) -> EvolveEffectCustomization:
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
        return cast('EvolveEffectCustomization', self._start('effect.evolve', parameters))

    def evolve_into(
        self, **parameters: Unpack[EvolveIntoEffectArguments]
    ) -> EvolveIntoEffectCustomization:
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
            'EvolveIntoEffectCustomization', self._start('effect.evolve_into', parameters)
        )

    def evolve_from(
        self, **parameters: Unpack[EvolveFromEffectArguments]
    ) -> EvolveFromEffectCustomization:
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
            'EvolveFromEffectCustomization', self._start('effect.evolve_from', parameters)
        )

    def expand(
        self, **parameters: Unpack[ExpandEffectArguments]
    ) -> ExpandEffectCustomization:
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
        return cast('ExpandEffectCustomization', self._start('effect.expand', parameters))

    def stretch(
        self, **parameters: Unpack[StretchEffectArguments]
    ) -> StretchEffectCustomization:
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
        return cast(
            'StretchEffectCustomization', self._start('effect.stretch', parameters)
        )

    def explode(
        self, **parameters: Unpack[ExplodeEffectArguments]
    ) -> ExplodeEffectCustomization:
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
        return cast(
            'ExplodeEffectCustomization', self._start('effect.explode', parameters)
        )


class _PlayableEffectMethods:
    """One method for each sound effect, which adds it to the sounds that are played."""

    __slots__ = ()

    def _start(self, kind: str, parameters: Mapping[str, object]) -> EffectCustomization:
        raise NotImplementedError

    def bit_crush(
        self, **parameters: Unpack[BitCrushAudioArguments]
    ) -> BitCrushAudioCustomization:
        """
        Lower the resolution of the sound, for a gritty, retro tone.

        Keyword Args:
            bits (int): Quantization resolution in bits (``1`` to ``16``).
            downsample (int): Sample-hold factor (``1`` to ``256``).

        Returns:
            The effect. Assigning one of its fields changes the sounds played after that.
        """
        return cast(
            'BitCrushAudioCustomization', self._start('audio.bit_crush', parameters)
        )

    def distortion(
        self, **parameters: Unpack[DistortionAudioArguments]
    ) -> DistortionAudioCustomization:
        """
        Distort the sound by driving it into soft clipping.

        Keyword Args:
            drive (float): Input gain before soft-clipping (``0.1`` to ``100.0``).

        Returns:
            The effect. Assigning one of its fields changes the sounds played after that.
        """
        return cast(
            'DistortionAudioCustomization', self._start('audio.distortion', parameters)
        )

    def low_pass(
        self, **parameters: Unpack[LowPassAudioArguments]
    ) -> LowPassAudioCustomization:
        """
        Keep the frequencies below ``cutoff`` and soften those above it.

        Keyword Args:
            cutoff (float): Corner frequency in hertz (``20.0`` to ``20000.0``).
            resonance (float): Filter resonance Q (``0.1`` to ``20.0``).

        Returns:
            The effect. Assigning one of its fields changes the sounds played after that.
        """
        return cast(
            'LowPassAudioCustomization', self._start('audio.low_pass', parameters)
        )

    def high_pass(
        self, **parameters: Unpack[HighPassAudioArguments]
    ) -> HighPassAudioCustomization:
        """
        Keep the frequencies above ``cutoff`` and soften those below it.

        Keyword Args:
            cutoff (float): Corner frequency in hertz (``20.0`` to ``20000.0``).
            resonance (float): Filter resonance Q (``0.1`` to ``20.0``).

        Returns:
            The effect. Assigning one of its fields changes the sounds played after that.
        """
        return cast(
            'HighPassAudioCustomization', self._start('audio.high_pass', parameters)
        )

    def delay(self, **parameters: Unpack[DelayAudioArguments]) -> DelayAudioCustomization:
        """
        Repeat the sound as fading echoes.

        Keyword Args:
            time_milliseconds (float): Delay time between echoes in milliseconds (``1.0`` to ``2000.0``).
            feedback (float): Echo feedback ratio (``0.0`` to ``0.95``).
            mix (float): Wet/dry mix ratio (``0.0`` to ``1.0``).

        Returns:
            The effect. Assigning one of its fields changes the sounds played after that.
        """
        return cast('DelayAudioCustomization', self._start('audio.delay', parameters))

    def reverb(
        self, **parameters: Unpack[ReverbAudioArguments]
    ) -> ReverbAudioCustomization:
        """
        Add the reverberation of a room.

        Keyword Args:
            room (float): Room size (``0.0`` to ``1.0``).
            damping (float): High-frequency damping (``0.0`` to ``1.0``).
            mix (float): Wet/dry mix ratio (``0.0`` to ``1.0``).

        Returns:
            The effect. Assigning one of its fields changes the sounds played after that.
        """
        return cast('ReverbAudioCustomization', self._start('audio.reverb', parameters))

    def tremolo(
        self, **parameters: Unpack[TremoloAudioArguments]
    ) -> TremoloAudioCustomization:
        """
        Pulse the volume up and down.

        Keyword Args:
            rate_hertz (float): Modulation rate in hertz (``0.1`` to ``40.0``).
            depth (float): Modulation depth (``0.0`` to ``1.0``).

        Returns:
            The effect. Assigning one of its fields changes the sounds played after that.
        """
        return cast('TremoloAudioCustomization', self._start('audio.tremolo', parameters))


@final
class RenderableEffects(_RenderableEffectMethods):
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
        self._running: dict[str, Customization] = {}

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

    def _start(self, kind: str, parameters: Mapping[str, object]) -> EffectCustomization:
        effect = cast('Customization', fx(kind, **parameters))  # type: ignore[call-overload]
        earlier = self._running.get(kind)
        if earlier is not None:
            earlier.cancel()
        self._target.update(effect)
        self._running[kind] = effect
        return cast('EffectCustomization', effect)


@final
class PlayableEffects(_PlayableEffectMethods):
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
        self._running: dict[str, AudioCustomization] = {}

    @property
    def active(self) -> tuple[PlayableEffect, ...]:
        """The effects added here and not cleared or replaced."""
        return cast('tuple[PlayableEffect, ...]', tuple(self._running.values()))

    def clear(self) -> None:
        """Remove every effect added here, for the sounds played after this."""
        self._running.clear()

    def _audio_effects(self) -> tuple[TerminalAudioEffect, ...]:
        return tuple(effect.to_audio_effect() for effect in self._running.values())

    def _start(self, kind: str, parameters: Mapping[str, object]) -> EffectCustomization:
        self._device._canvas._require_open()
        effect = cast('AudioCustomization', fx(kind, **parameters))  # type: ignore[call-overload]
        self._running[kind] = effect
        return cast('EffectCustomization', effect)


@final
class EffectController(_RenderableEffectMethods, _PlayableEffectMethods):
    """
    The effects of the hook that is running, one method for each effect.

    Get it from ``context.fx``. A visual effect (``context.fx.fade_to(...)``) starts on the
    hook's buffer, and a sound effect (``context.fx.reverb(...)``) is added to every sound the
    hook plays. The effects last while the hook does; ``clear()`` ends them sooner, and
    removing the hook or its placement ends them too. Starting an effect of a kind that is
    already set replaces the earlier one.

    Attributes:
        context: The context of the hook that applies the effects.
        active: The effects the hook has set and not cleared or replaced.

    Examples:
        ```python
        import xnano

        with xnano.new(width=8, height=1) as canvas:
            label = canvas.write('hi')
            counts = []

            @label.hook(on='frame')
            def tint(context: xnano.Context) -> None:
                if not context.fx.active:
                    context.fx.fade_to(foreground='red', duration_milliseconds=100)
                counts.append(len(context.fx.active))

            canvas.step(delta_seconds=0.05)
            assert counts and set(counts) == {1}
        ```
    """

    __slots__ = ('_context',)

    def __getattr__(self, name: str) -> object:
        if name.startswith('_'):
            raise AttributeError(name)
        raise _unknown_effect('context.fx', name, has_visual=True, has_sound=True)

    def __init__(self, context: Context[object, object]) -> None:
        """
        Create the controller of a context. Use ``context.fx`` instead of calling this.

        Args:
            context: The context of the hook that applies the effects.
        """
        self._context = context

    @property
    def context(self) -> Context[object, object]:
        """The context of the hook that applies the effects."""
        return self._context

    @property
    def active(self) -> tuple[EffectCustomization, ...]:
        """The effects the hook has set and not cleared or replaced."""
        state = self._context.hook._effect_state
        if state is None:
            return ()
        return (*state.visual.values(), *state.audio.values())  # type: ignore[return-value]

    def clear(self) -> None:
        """
        End the effects this hook has set.

        Visual effects stop on the buffer, and the hook's sound effects are not applied to what
        it plays. Does nothing when the hook has set none.
        """
        state = self._context.hook._effect_state
        if state is not None:
            state.clear()

    def _start(self, kind: str, parameters: Mapping[str, object]) -> EffectCustomization:
        effect = cast('Customization', fx(kind, **parameters))  # type: ignore[call-overload]
        handle = self._context.hook
        if handle.is_removed:
            return cast('EffectCustomization', effect)
        state = handle._effect_state
        if state is None:
            state = handle._effect_state = EffectState()
        if kind.startswith('effect.'):
            earlier = state.visual.pop(kind, None)
            if earlier is not None:
                earlier.cancel()
            effect.apply_to(self._context.buffer)
            state.visual[kind] = effect
        else:
            state.audio[kind] = cast('AudioCustomization', effect)
        return cast('EffectCustomization', effect)
