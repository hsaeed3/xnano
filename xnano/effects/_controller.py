"""
xnano.effects._controller

The effects of the hook that is running: ``context.fx``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast, final

# Read when the module runs, not under `TYPE_CHECKING`, so that `typing.get_type_hints` resolves
# the annotations of `EffectController`.
from xnano._schema._effects import EffectSpecification
from xnano.effects._properties import (
    AudioEffectParameters,
    EffectParameters,
    _PlayableEffectMethods,
    _unknown_effect,
    _WritableEffectMethods,
)
from xnano.effects._registry import build_effect

if TYPE_CHECKING:
    from collections.abc import Mapping

    from xnano_audio import TerminalAudioEffect

    from xnano.hooks._context import Context


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
        self.visual: dict[str, EffectParameters] = {}
        self.audio: dict[str, AudioEffectParameters] = {}

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
class EffectController(_WritableEffectMethods, _PlayableEffectMethods):
    """
    The effects of the hook that is running, one method for each effect.

    Get it from ``context.fx``. A visual effect (``context.fx.fade_to(...)``) starts on the
    hook's target, and a sound effect (``context.fx.reverb(...)``) is added to every sound the
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
            label = canvas.screen.write('hi')
            counts = []

            @label.hook(on='frame')
            def tint(context: xnano.Context) -> None:
                if not context.fx.active:
                    context.fx.fade_to(foreground='red', duration_milliseconds=100)
                counts.append(len(context.fx.active))

            canvas.clock.step(delta_seconds=0.05)
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
    def active(self) -> tuple[EffectSpecification, ...]:
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

    def _start(self, kind: str, parameters: Mapping[str, object]) -> EffectSpecification:
        effect = build_effect(kind, parameters)
        handle = self._context.hook
        if handle.is_removed:
            return cast('EffectSpecification', effect)
        state = handle._effect_state
        if state is None:
            state = handle._effect_state = EffectState()
        if kind.startswith('effect.'):
            earlier = state.visual.pop(kind, None)
            if earlier is not None:
                earlier.cancel()
            effect.apply_to(self._context.target)
            state.visual[kind] = effect
        else:
            state.audio[kind] = cast('AudioEffectParameters', effect)
        return cast('EffectSpecification', effect)
