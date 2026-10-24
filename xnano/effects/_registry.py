"""
xnano.effects._registry

The effect kinds and the parameter class of each, and how ``effects=[...]`` lists become running
effects.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import fields
from typing import TYPE_CHECKING, Literal, cast

from xnano.effects._properties import (
    BitCrushAudioEffectParameters,
    CoalesceEffectParameters,
    DarkenEffectParameters,
    DelayAudioEffectParameters,
    DissolveEffectParameters,
    DistortionAudioEffectParameters,
    EffectParameters,
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

if TYPE_CHECKING:
    from xnano._schema._effects import WritableEffectSpecification
    from xnano.canvas import Canvas
    from xnano.layout._placement import Placement

EFFECT_PARAMETERS_BY_KIND: dict[str, type[EffectParameters]] = {
    'effect.fade_to': FadeToEffectParameters,
    'effect.fade_from': FadeFromEffectParameters,
    'effect.paint': PaintEffectParameters,
    'effect.saturate': SaturateEffectParameters,
    'effect.lighten': LightenEffectParameters,
    'effect.darken': DarkenEffectParameters,
    'effect.sweep_in': SweepInEffectParameters,
    'effect.sweep_out': SweepOutEffectParameters,
    'effect.slide_in': SlideInEffectParameters,
    'effect.slide_out': SlideOutEffectParameters,
    'effect.hsl_shift': HslShiftEffectParameters,
    'effect.dissolve': DissolveEffectParameters,
    'effect.coalesce': CoalesceEffectParameters,
    'effect.glitch': GlitchEffectParameters,
    'effect.sleep': SleepEffectParameters,
    'effect.evolve': EvolveEffectParameters,
    'effect.evolve_into': EvolveIntoEffectParameters,
    'effect.evolve_from': EvolveFromEffectParameters,
    'effect.expand': ExpandEffectParameters,
    'effect.stretch': StretchEffectParameters,
    'effect.explode': ExplodeEffectParameters,
    'audio.bit_crush': BitCrushAudioEffectParameters,
    'audio.distortion': DistortionAudioEffectParameters,
    'audio.low_pass': LowPassAudioEffectParameters,
    'audio.high_pass': HighPassAudioEffectParameters,
    'audio.delay': DelayAudioEffectParameters,
    'audio.reverb': ReverbAudioEffectParameters,
    'audio.tremolo': TremoloAudioEffectParameters,
}
"""The parameter class of every kind of effect, by kind."""

_DYNAMIC_OPERATION_NAMES = {
    'fill': 'DynamicFill',
    'write': 'DynamicWrite',
    'layout': 'DynamicLayout',
    'fuzz': 'DynamicFuzz',
    'pixels': 'DynamicPixels',
    'raster': 'DynamicRaster',
}


def build_effect(kind: str, parameters: Mapping[str, object]) -> EffectParameters:
    """
    Create the parameters of the effect of one kind.

    Args:
        kind: The kind of effect, such as ``'effect.fade_to'`` or ``'audio.reverb'``.
        parameters: The keyword arguments of that kind.

    Returns:
        The effect, not yet applied to anything.

    Raises:
        ValueError: ``kind`` is the kind of a dynamic operation such as ``'fill'``, or is not a
            known effect kind.
        TypeError: A keyword is not a setting of that kind. The message lists its settings.
    """
    if kind in _DYNAMIC_OPERATION_NAMES:
        name = _DYNAMIC_OPERATION_NAMES[kind]
        raise ValueError(
            f'{kind!r} is not an effect. Build it with xnano.operations.{name}(...) and '
            f'apply it with | or update().'
        )
    parameters_class = EFFECT_PARAMETERS_BY_KIND.get(kind)
    if parameters_class is None:
        valid = ', '.join(sorted(EFFECT_PARAMETERS_BY_KIND))
        raise ValueError(f'{kind!r} is not a known effect kind. Choose one of: {valid}.')
    accepted = [field.name for field in fields(parameters_class) if field.init]  # type: ignore[arg-type]
    unknown = [name for name in parameters if name not in accepted]
    if unknown:
        raise TypeError(
            f'The effect {kind!r} has no setting called {unknown[0]!r}. Its settings are: '
            f'{", ".join(accepted)}.'
        )
    factory = cast('Callable[..., EffectParameters]', parameters_class)
    return factory(**parameters)


def effect_sequence(
    effects: object, expected: Literal['writable', 'playable']
) -> tuple[object, ...]:
    """
    Return the entries of an ``effects=[...]`` argument, refusing a value that is not a list.

    Args:
        effects: The value given as ``effects=``.
        expected: ``'writable'`` for a list that styles a buffer, ``'playable'`` for a list
            that styles a sound.

    Raises:
        TypeError: The value is a string, a single dictionary or anything else that is not a
            list of effects.
    """
    if isinstance(effects, (str, bytes, Mapping, AbstractSet)) or not isinstance(
        effects, Iterable
    ):
        sample = 'effect.fade_to' if expected == 'writable' else 'audio.reverb'
        raise TypeError(
            f"effects= takes a list of dictionaries such as [{{'kind': {sample!r}, ...}}], "
            f'but got {effects!r}. Pass a list, even for one effect.'
        )
    return tuple(effects)


def normalize_effect(
    specification: object, expected: Literal['writable', 'playable']
) -> EffectParameters:
    """
    Turn one entry of an ``effects=[...]`` list into the effect it describes.

    Args:
        specification: A dictionary with a ``kind`` key and that effect's keywords, such as
            ``{'kind': 'effect.fade_to', 'foreground': 'red'}``.
        expected: ``'writable'`` for a list that styles a buffer, ``'playable'`` for a list
            that styles a sound.

    Returns:
        The effect, not yet applied to anything.

    Raises:
        TypeError: The entry is not such a dictionary, or its ``kind`` belongs to the other
            list or is not an effect.
        ValueError: The ``kind`` looks like an effect but is not a known one.
    """
    is_writable = expected == 'writable'
    prefix = 'effect.' if is_writable else 'audio.'
    sample = 'effect.fade_to' if is_writable else 'audio.reverb'
    example = f"{{'kind': {sample!r}, ...}}"
    if not isinstance(specification, Mapping) or 'kind' not in specification:
        if not isinstance(specification, EffectParameters):
            hint = "Write each effect as a dictionary with a 'kind' key."
        elif is_writable:
            hint = (
                'An effect(...) object is applied with placement | effect(...) or '
                'placement.update(effect(...)).'
            )
        else:
            hint = 'An effect(...) object is not accepted here; write the effect as a dictionary.'
        raise TypeError(
            f'effects= takes dictionaries such as {example}, but got {specification!r}. {hint}'
        )
    parameters = dict(specification)
    kind = parameters.pop('kind')
    if not isinstance(kind, str):
        raise TypeError(
            f"The 'kind' of an effect is a string such as {sample!r}, but was {kind!r}."
        )
    if kind.startswith(prefix):
        if kind not in EFFECT_PARAMETERS_BY_KIND:
            known = ', '.join(
                sorted(
                    name for name in EFFECT_PARAMETERS_BY_KIND if name.startswith(prefix)
                )
            )
            raise ValueError(
                f'{kind!r} is not a known {"visual" if is_writable else "sound"} effect. '
                f'Use one of: {known}.'
            )
        return build_effect(kind, parameters)
    if kind.startswith(('effect.', 'audio.')):
        if is_writable:
            raise TypeError(
                f'{kind!r} is a sound effect; pass it to play(effects=...) or '
                f'Note(effects=...), not to a visual list such as write(effects=...). '
                f"Visual effects have kinds that start with 'effect.', such as "
                f"'effect.fade_to'."
            )
        raise TypeError(
            f'{kind!r} is a visual effect; pass it to write(effects=...) or '
            f'draw(effects=...), not to a sound. Sound effects have kinds that start with '
            f"'audio.', such as 'audio.reverb'."
        )
    noun = 'a visual effect' if is_writable else 'a sound effect'
    raise TypeError(
        f'{kind!r} is not {noun}, so it cannot be in effects=. Use a kind that starts with '
        f"'{prefix}', such as {sample!r}."
    )


def apply_effects(
    target: Canvas[object, object] | Placement[object, object],
    effects: Sequence[WritableEffectSpecification],
) -> list[EffectParameters]:
    """
    Start each effect of an ``effects=[...]`` list on ``target`` and return the live handles.

    Args:
        target: The canvas or placement the effects run on.
        effects: Dictionaries with a ``kind`` key naming a visual effect, such as
            ``{'kind': 'effect.fade_to', 'foreground': 'red'}``, and that effect's keywords.

    Returns:
        The running effects, in the order of the list.

    Raises:
        TypeError: An entry is not such a dictionary, or names something that is not a
            visual effect.
    """
    applied: list[EffectParameters] = []
    for specification in effect_sequence(effects, 'writable'):
        effect = normalize_effect(specification, 'writable')
        effect.apply_to(target)
        applied.append(effect)
    return applied
