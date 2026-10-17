"""
xnano._effect_controller

The effects a hook applies through ``context.fx``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, final, get_args, overload

from xnano._customize import (
    Customization,
    PlayableEffectKind,
    RenderableEffectKind,
    fx,
)

if TYPE_CHECKING:
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
    from xnano.context import Context

__all__ = ['EffectController']

_RENDERABLE_KINDS = frozenset(get_args(RenderableEffectKind))
_PLAYABLE_KINDS = frozenset(get_args(PlayableEffectKind))


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


@final
class EffectController:
    """
    Applies effects for the hook that is running.

    Get one from ``context.fx``. Call it with the kind of an effect and that effect's keywords:
    a visual kind (``'effect.fade_to'``) starts on the hook's buffer, and a sound kind
    (``'audio.reverb'``) is added to every sound the hook plays. The effects last while the
    hook does; ``clear()`` ends them sooner, and removing the hook or its placement ends them
    too. Setting a kind again replaces the earlier effect of that kind.

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
            def tint(context: xnano.context.Context) -> None:
                if not context.fx.active:
                    context.fx('effect.fade_to', foreground='red', duration_milliseconds=100)
                counts.append(len(context.fx.active))

            canvas.step(delta_seconds=0.05)
            assert counts and set(counts) == {1}
        ```
    """

    __slots__ = ('_context',)

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

    @overload
    def __call__(
        self,
        kind: Literal['effect.fade_to'],
        /,
        **parameters: Unpack[FadeToEffectArguments],
    ) -> FadeToEffectCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['effect.fade_from'],
        /,
        **parameters: Unpack[FadeFromEffectArguments],
    ) -> FadeFromEffectCustomization: ...
    @overload
    def __call__(
        self, kind: Literal['effect.paint'], /, **parameters: Unpack[PaintEffectArguments]
    ) -> PaintEffectCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['effect.saturate'],
        /,
        **parameters: Unpack[SaturateEffectArguments],
    ) -> SaturateEffectCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['effect.lighten'],
        /,
        **parameters: Unpack[LightenEffectArguments],
    ) -> LightenEffectCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['effect.darken'],
        /,
        **parameters: Unpack[DarkenEffectArguments],
    ) -> DarkenEffectCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['effect.sweep_in'],
        /,
        **parameters: Unpack[SweepInEffectArguments],
    ) -> SweepInEffectCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['effect.sweep_out'],
        /,
        **parameters: Unpack[SweepOutEffectArguments],
    ) -> SweepOutEffectCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['effect.slide_in'],
        /,
        **parameters: Unpack[SlideInEffectArguments],
    ) -> SlideInEffectCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['effect.slide_out'],
        /,
        **parameters: Unpack[SlideOutEffectArguments],
    ) -> SlideOutEffectCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['effect.hsl_shift'],
        /,
        **parameters: Unpack[HslShiftEffectArguments],
    ) -> HslShiftEffectCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['effect.dissolve'],
        /,
        **parameters: Unpack[DissolveEffectArguments],
    ) -> DissolveEffectCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['effect.coalesce'],
        /,
        **parameters: Unpack[CoalesceEffectArguments],
    ) -> CoalesceEffectCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['effect.glitch'],
        /,
        **parameters: Unpack[GlitchEffectArguments],
    ) -> GlitchEffectCustomization: ...
    @overload
    def __call__(
        self, kind: Literal['effect.sleep'], /, **parameters: Unpack[SleepEffectArguments]
    ) -> SleepEffectCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['effect.evolve'],
        /,
        **parameters: Unpack[EvolveEffectArguments],
    ) -> EvolveEffectCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['effect.evolve_into'],
        /,
        **parameters: Unpack[EvolveIntoEffectArguments],
    ) -> EvolveIntoEffectCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['effect.evolve_from'],
        /,
        **parameters: Unpack[EvolveFromEffectArguments],
    ) -> EvolveFromEffectCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['effect.expand'],
        /,
        **parameters: Unpack[ExpandEffectArguments],
    ) -> ExpandEffectCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['effect.stretch'],
        /,
        **parameters: Unpack[StretchEffectArguments],
    ) -> StretchEffectCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['effect.explode'],
        /,
        **parameters: Unpack[ExplodeEffectArguments],
    ) -> ExplodeEffectCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['audio.bit_crush'],
        /,
        **parameters: Unpack[BitCrushAudioArguments],
    ) -> BitCrushAudioCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['audio.distortion'],
        /,
        **parameters: Unpack[DistortionAudioArguments],
    ) -> DistortionAudioCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['audio.low_pass'],
        /,
        **parameters: Unpack[LowPassAudioArguments],
    ) -> LowPassAudioCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['audio.high_pass'],
        /,
        **parameters: Unpack[HighPassAudioArguments],
    ) -> HighPassAudioCustomization: ...
    @overload
    def __call__(
        self, kind: Literal['audio.delay'], /, **parameters: Unpack[DelayAudioArguments]
    ) -> DelayAudioCustomization: ...
    @overload
    def __call__(
        self, kind: Literal['audio.reverb'], /, **parameters: Unpack[ReverbAudioArguments]
    ) -> ReverbAudioCustomization: ...
    @overload
    def __call__(
        self,
        kind: Literal['audio.tremolo'],
        /,
        **parameters: Unpack[TremoloAudioArguments],
    ) -> TremoloAudioCustomization: ...
    def __call__(self, kind: str, /, **parameters: object) -> EffectCustomization:
        """
        Apply an effect for as long as the hook is active.

        Args:
            kind: A visual kind such as ``'effect.fade_to'`` or a sound kind such as
                ``'audio.reverb'``.
            parameters: The keywords of that kind of effect.

        Returns:
            The effect, which can be edited while it runs.

        Raises:
            ValueError: ``kind`` is not an effect. The message lists the kinds.
        """
        is_visual = kind in _RENDERABLE_KINDS
        if not is_visual and kind not in _PLAYABLE_KINDS:
            valid = ', '.join(sorted((*_RENDERABLE_KINDS, *_PLAYABLE_KINDS)))
            raise ValueError(
                f'{kind!r} is not an effect, so context.fx cannot apply it. Use one of: '
                f'{valid}.'
            )
        effect = fx(kind, **parameters)  # type: ignore[call-overload]
        handle = self._context.hook
        if handle.is_removed:
            return effect  # type: ignore[return-value]
        state = handle._effect_state
        if state is None:
            state = handle._effect_state = EffectState()
        if is_visual:
            earlier = state.visual.pop(kind, None)
            if earlier is not None:
                earlier.cancel()
            effect.apply_to(self._context.buffer)
            state.visual[kind] = effect
        else:
            state.audio[kind] = effect  # type: ignore[assignment]
        return effect  # type: ignore[return-value]

    def clear(self) -> None:
        """
        End the effects this hook has set.

        Visual effects stop on the buffer and sound effects are no longer added to what the
        hook plays. Does nothing when the hook has set none.
        """
        state = self._context.hook._effect_state
        if state is not None:
            state.clear()
