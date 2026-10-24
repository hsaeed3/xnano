"""
xnano.effects

Effects: how content changes over time, in how it looks or how it sounds.

[`effect`][xnano.effects.effect] builds the parameters of a visual effect (a kind that starts
with ``'effect.'``, such as ``'effect.fade_to'``) or a sound effect (a kind that starts with
``'audio.'``, such as ``'audio.reverb'``). The result is applied with ``|``, ``update``, a
hook that returns it, or an ``effects=[...]`` list, and assigning one of its fields changes
the effect while it runs.

The ``.fx`` properties of placements, canvases, ``canvas.speaker`` and ``context`` start an effect
by name instead: ``placement.fx.fade_to(...)``, ``canvas.speaker.fx.reverb(...)`` and
``context.fx.fade_to(...)``. An ``effects=[...]`` list takes each effect as a dictionary with
its ``kind``, such as ``{'kind': 'effect.fade_to', 'foreground': 'red'}``.

``Effect.fade_to(...)`` in [`xnano.operations`][xnano.operations] is the operation form of
``effect('effect.fade_to', ...)``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, overload

from xnano._schema._effects import (
    BitCrushAudioEffectParametersSchema as BitCrushAudioEffectParametersSchema,
)
from xnano._schema._effects import (
    BitCrushAudioEffectSpecification as BitCrushAudioEffectSpecification,
)
from xnano._schema._effects import (
    CoalesceEffectParametersSchema as CoalesceEffectParametersSchema,
)
from xnano._schema._effects import (
    CoalesceEffectSpecification as CoalesceEffectSpecification,
)
from xnano._schema._effects import (
    DarkenEffectParametersSchema as DarkenEffectParametersSchema,
)
from xnano._schema._effects import DarkenEffectSpecification as DarkenEffectSpecification
from xnano._schema._effects import (
    DelayAudioEffectParametersSchema as DelayAudioEffectParametersSchema,
)
from xnano._schema._effects import (
    DelayAudioEffectSpecification as DelayAudioEffectSpecification,
)
from xnano._schema._effects import (
    DissolveEffectParametersSchema as DissolveEffectParametersSchema,
)
from xnano._schema._effects import (
    DissolveEffectSpecification as DissolveEffectSpecification,
)
from xnano._schema._effects import (
    DistortionAudioEffectParametersSchema as DistortionAudioEffectParametersSchema,
)
from xnano._schema._effects import (
    DistortionAudioEffectSpecification as DistortionAudioEffectSpecification,
)
from xnano._schema._effects import EffectKind as EffectKind
from xnano._schema._effects import EffectSpecification as EffectSpecification
from xnano._schema._effects import (
    EvolveEffectParametersSchema as EvolveEffectParametersSchema,
)
from xnano._schema._effects import EvolveEffectSpecification as EvolveEffectSpecification
from xnano._schema._effects import (
    EvolveFromEffectParametersSchema as EvolveFromEffectParametersSchema,
)
from xnano._schema._effects import (
    EvolveFromEffectSpecification as EvolveFromEffectSpecification,
)
from xnano._schema._effects import (
    EvolveIntoEffectParametersSchema as EvolveIntoEffectParametersSchema,
)
from xnano._schema._effects import (
    EvolveIntoEffectSpecification as EvolveIntoEffectSpecification,
)
from xnano._schema._effects import (
    ExpandEffectParametersSchema as ExpandEffectParametersSchema,
)
from xnano._schema._effects import ExpandEffectSpecification as ExpandEffectSpecification
from xnano._schema._effects import (
    ExplodeEffectParametersSchema as ExplodeEffectParametersSchema,
)
from xnano._schema._effects import (
    ExplodeEffectSpecification as ExplodeEffectSpecification,
)
from xnano._schema._effects import (
    FadeFromEffectParametersSchema as FadeFromEffectParametersSchema,
)
from xnano._schema._effects import (
    FadeFromEffectSpecification as FadeFromEffectSpecification,
)
from xnano._schema._effects import (
    FadeToEffectParametersSchema as FadeToEffectParametersSchema,
)
from xnano._schema._effects import FadeToEffectSpecification as FadeToEffectSpecification
from xnano._schema._effects import (
    GlitchEffectParametersSchema as GlitchEffectParametersSchema,
)
from xnano._schema._effects import GlitchEffectSpecification as GlitchEffectSpecification
from xnano._schema._effects import (
    HighPassAudioEffectParametersSchema as HighPassAudioEffectParametersSchema,
)
from xnano._schema._effects import (
    HighPassAudioEffectSpecification as HighPassAudioEffectSpecification,
)
from xnano._schema._effects import (
    HslShiftEffectParametersSchema as HslShiftEffectParametersSchema,
)
from xnano._schema._effects import (
    HslShiftEffectSpecification as HslShiftEffectSpecification,
)
from xnano._schema._effects import (
    LightenEffectParametersSchema as LightenEffectParametersSchema,
)
from xnano._schema._effects import (
    LightenEffectSpecification as LightenEffectSpecification,
)
from xnano._schema._effects import (
    LowPassAudioEffectParametersSchema as LowPassAudioEffectParametersSchema,
)
from xnano._schema._effects import (
    LowPassAudioEffectSpecification as LowPassAudioEffectSpecification,
)
from xnano._schema._effects import (
    PaintEffectParametersSchema as PaintEffectParametersSchema,
)
from xnano._schema._effects import PaintEffectSpecification as PaintEffectSpecification
from xnano._schema._effects import PlayableEffect as PlayableEffect
from xnano._schema._effects import PlayableEffectKind as PlayableEffectKind
from xnano._schema._effects import (
    PlayableEffectSpecification as PlayableEffectSpecification,
)
from xnano._schema._effects import (
    ReverbAudioEffectParametersSchema as ReverbAudioEffectParametersSchema,
)
from xnano._schema._effects import (
    ReverbAudioEffectSpecification as ReverbAudioEffectSpecification,
)
from xnano._schema._effects import (
    SaturateEffectParametersSchema as SaturateEffectParametersSchema,
)
from xnano._schema._effects import (
    SaturateEffectSpecification as SaturateEffectSpecification,
)
from xnano._schema._effects import (
    SleepEffectParametersSchema as SleepEffectParametersSchema,
)
from xnano._schema._effects import SleepEffectSpecification as SleepEffectSpecification
from xnano._schema._effects import (
    SlideInEffectParametersSchema as SlideInEffectParametersSchema,
)
from xnano._schema._effects import (
    SlideInEffectSpecification as SlideInEffectSpecification,
)
from xnano._schema._effects import (
    SlideOutEffectParametersSchema as SlideOutEffectParametersSchema,
)
from xnano._schema._effects import (
    SlideOutEffectSpecification as SlideOutEffectSpecification,
)
from xnano._schema._effects import (
    StretchEffectParametersSchema as StretchEffectParametersSchema,
)
from xnano._schema._effects import (
    StretchEffectSpecification as StretchEffectSpecification,
)
from xnano._schema._effects import (
    SweepInEffectParametersSchema as SweepInEffectParametersSchema,
)
from xnano._schema._effects import (
    SweepInEffectSpecification as SweepInEffectSpecification,
)
from xnano._schema._effects import (
    SweepOutEffectParametersSchema as SweepOutEffectParametersSchema,
)
from xnano._schema._effects import (
    SweepOutEffectSpecification as SweepOutEffectSpecification,
)
from xnano._schema._effects import (
    TremoloAudioEffectParametersSchema as TremoloAudioEffectParametersSchema,
)
from xnano._schema._effects import (
    TremoloAudioEffectSpecification as TremoloAudioEffectSpecification,
)
from xnano._schema._effects import WritableEffect as WritableEffect
from xnano._schema._effects import WritableEffectKind as WritableEffectKind
from xnano._schema._effects import (
    WritableEffectSpecification as WritableEffectSpecification,
)
from xnano._schema._layout import Interpolation as Interpolation
from xnano._schema._layout import MotionDirection as MotionDirection
from xnano.effects._controller import EffectController as EffectController
from xnano.effects._properties import AudioEffectParameters as AudioEffectParameters
from xnano.effects._properties import (
    BitCrushAudioEffectParameters as BitCrushAudioEffectParameters,
)
from xnano.effects._properties import CoalesceEffectParameters as CoalesceEffectParameters
from xnano.effects._properties import DarkenEffectParameters as DarkenEffectParameters
from xnano.effects._properties import (
    DelayAudioEffectParameters as DelayAudioEffectParameters,
)
from xnano.effects._properties import DissolveEffectParameters as DissolveEffectParameters
from xnano.effects._properties import (
    DistortionAudioEffectParameters as DistortionAudioEffectParameters,
)
from xnano.effects._properties import EffectParameters as EffectParameters
from xnano.effects._properties import EvolveEffectParameters as EvolveEffectParameters
from xnano.effects._properties import (
    EvolveFromEffectParameters as EvolveFromEffectParameters,
)
from xnano.effects._properties import (
    EvolveIntoEffectParameters as EvolveIntoEffectParameters,
)
from xnano.effects._properties import ExpandEffectParameters as ExpandEffectParameters
from xnano.effects._properties import ExplodeEffectParameters as ExplodeEffectParameters
from xnano.effects._properties import FadeFromEffectParameters as FadeFromEffectParameters
from xnano.effects._properties import FadeToEffectParameters as FadeToEffectParameters
from xnano.effects._properties import GlitchEffectParameters as GlitchEffectParameters
from xnano.effects._properties import (
    HighPassAudioEffectParameters as HighPassAudioEffectParameters,
)
from xnano.effects._properties import HslShiftEffectParameters as HslShiftEffectParameters
from xnano.effects._properties import LightenEffectParameters as LightenEffectParameters
from xnano.effects._properties import (
    LowPassAudioEffectParameters as LowPassAudioEffectParameters,
)
from xnano.effects._properties import PaintEffectParameters as PaintEffectParameters
from xnano.effects._properties import (
    PlayableEffectProperties as PlayableEffectProperties,
)
from xnano.effects._properties import (
    ReverbAudioEffectParameters as ReverbAudioEffectParameters,
)
from xnano.effects._properties import SaturateEffectParameters as SaturateEffectParameters
from xnano.effects._properties import SleepEffectParameters as SleepEffectParameters
from xnano.effects._properties import SlideInEffectParameters as SlideInEffectParameters
from xnano.effects._properties import SlideOutEffectParameters as SlideOutEffectParameters
from xnano.effects._properties import StretchEffectParameters as StretchEffectParameters
from xnano.effects._properties import SweepInEffectParameters as SweepInEffectParameters
from xnano.effects._properties import SweepOutEffectParameters as SweepOutEffectParameters
from xnano.effects._properties import (
    TremoloAudioEffectParameters as TremoloAudioEffectParameters,
)
from xnano.effects._properties import (
    WritableEffectProperties as WritableEffectProperties,
)
from xnano.effects._registry import build_effect

if TYPE_CHECKING:
    from typing_extensions import Unpack


__all__ = [
    'effect',
    'EffectKind',
    'WritableEffectKind',
    'PlayableEffectKind',
    'EffectParameters',
    'AudioEffectParameters',
    'FadeToEffectParameters',
    'FadeFromEffectParameters',
    'PaintEffectParameters',
    'SaturateEffectParameters',
    'LightenEffectParameters',
    'DarkenEffectParameters',
    'SweepInEffectParameters',
    'SweepOutEffectParameters',
    'SlideInEffectParameters',
    'SlideOutEffectParameters',
    'HslShiftEffectParameters',
    'DissolveEffectParameters',
    'CoalesceEffectParameters',
    'GlitchEffectParameters',
    'SleepEffectParameters',
    'EvolveEffectParameters',
    'EvolveIntoEffectParameters',
    'EvolveFromEffectParameters',
    'ExpandEffectParameters',
    'StretchEffectParameters',
    'ExplodeEffectParameters',
    'BitCrushAudioEffectParameters',
    'DistortionAudioEffectParameters',
    'LowPassAudioEffectParameters',
    'HighPassAudioEffectParameters',
    'DelayAudioEffectParameters',
    'ReverbAudioEffectParameters',
    'TremoloAudioEffectParameters',
    'WritableEffectProperties',
    'PlayableEffectProperties',
    'EffectController',
    'BitCrushAudioEffectParametersSchema',
    'BitCrushAudioEffectSpecification',
    'CoalesceEffectParametersSchema',
    'CoalesceEffectSpecification',
    'DarkenEffectParametersSchema',
    'DarkenEffectSpecification',
    'DelayAudioEffectParametersSchema',
    'DelayAudioEffectSpecification',
    'DissolveEffectParametersSchema',
    'DissolveEffectSpecification',
    'DistortionAudioEffectParametersSchema',
    'DistortionAudioEffectSpecification',
    'EvolveEffectParametersSchema',
    'EvolveEffectSpecification',
    'EvolveFromEffectParametersSchema',
    'EvolveFromEffectSpecification',
    'EvolveIntoEffectParametersSchema',
    'EvolveIntoEffectSpecification',
    'ExpandEffectParametersSchema',
    'ExpandEffectSpecification',
    'ExplodeEffectParametersSchema',
    'ExplodeEffectSpecification',
    'FadeFromEffectParametersSchema',
    'FadeFromEffectSpecification',
    'FadeToEffectParametersSchema',
    'FadeToEffectSpecification',
    'GlitchEffectParametersSchema',
    'GlitchEffectSpecification',
    'HighPassAudioEffectParametersSchema',
    'HighPassAudioEffectSpecification',
    'HslShiftEffectParametersSchema',
    'HslShiftEffectSpecification',
    'EffectSpecification',
    'PlayableEffect',
    'WritableEffect',
    'Interpolation',
    'LightenEffectParametersSchema',
    'LightenEffectSpecification',
    'LowPassAudioEffectParametersSchema',
    'LowPassAudioEffectSpecification',
    'MotionDirection',
    'PaintEffectParametersSchema',
    'PaintEffectSpecification',
    'PlayableEffectSpecification',
    'ReverbAudioEffectParametersSchema',
    'ReverbAudioEffectSpecification',
    'SaturateEffectParametersSchema',
    'SaturateEffectSpecification',
    'SleepEffectParametersSchema',
    'SleepEffectSpecification',
    'SlideInEffectParametersSchema',
    'SlideInEffectSpecification',
    'SlideOutEffectParametersSchema',
    'SlideOutEffectSpecification',
    'StretchEffectParametersSchema',
    'StretchEffectSpecification',
    'SweepInEffectParametersSchema',
    'SweepInEffectSpecification',
    'SweepOutEffectParametersSchema',
    'SweepOutEffectSpecification',
    'TremoloAudioEffectParametersSchema',
    'TremoloAudioEffectSpecification',
    'WritableEffectSpecification',
]


@overload
def effect(
    kind: Literal['effect.fade_to'], /, **parameters: Unpack[FadeToEffectParametersSchema]
) -> FadeToEffectParameters: ...
@overload
def effect(
    kind: Literal['effect.fade_from'],
    /,
    **parameters: Unpack[FadeFromEffectParametersSchema],
) -> FadeFromEffectParameters: ...
@overload
def effect(
    kind: Literal['effect.paint'], /, **parameters: Unpack[PaintEffectParametersSchema]
) -> PaintEffectParameters: ...
@overload
def effect(
    kind: Literal['effect.saturate'],
    /,
    **parameters: Unpack[SaturateEffectParametersSchema],
) -> SaturateEffectParameters: ...
@overload
def effect(
    kind: Literal['effect.lighten'],
    /,
    **parameters: Unpack[LightenEffectParametersSchema],
) -> LightenEffectParameters: ...
@overload
def effect(
    kind: Literal['effect.darken'], /, **parameters: Unpack[DarkenEffectParametersSchema]
) -> DarkenEffectParameters: ...
@overload
def effect(
    kind: Literal['effect.sweep_in'],
    /,
    **parameters: Unpack[SweepInEffectParametersSchema],
) -> SweepInEffectParameters: ...
@overload
def effect(
    kind: Literal['effect.sweep_out'],
    /,
    **parameters: Unpack[SweepOutEffectParametersSchema],
) -> SweepOutEffectParameters: ...
@overload
def effect(
    kind: Literal['effect.slide_in'],
    /,
    **parameters: Unpack[SlideInEffectParametersSchema],
) -> SlideInEffectParameters: ...
@overload
def effect(
    kind: Literal['effect.slide_out'],
    /,
    **parameters: Unpack[SlideOutEffectParametersSchema],
) -> SlideOutEffectParameters: ...
@overload
def effect(
    kind: Literal['effect.hsl_shift'],
    /,
    **parameters: Unpack[HslShiftEffectParametersSchema],
) -> HslShiftEffectParameters: ...
@overload
def effect(
    kind: Literal['effect.dissolve'],
    /,
    **parameters: Unpack[DissolveEffectParametersSchema],
) -> DissolveEffectParameters: ...
@overload
def effect(
    kind: Literal['effect.coalesce'],
    /,
    **parameters: Unpack[CoalesceEffectParametersSchema],
) -> CoalesceEffectParameters: ...
@overload
def effect(
    kind: Literal['effect.glitch'], /, **parameters: Unpack[GlitchEffectParametersSchema]
) -> GlitchEffectParameters: ...
@overload
def effect(
    kind: Literal['effect.sleep'], /, **parameters: Unpack[SleepEffectParametersSchema]
) -> SleepEffectParameters: ...
@overload
def effect(
    kind: Literal['effect.evolve'], /, **parameters: Unpack[EvolveEffectParametersSchema]
) -> EvolveEffectParameters: ...
@overload
def effect(
    kind: Literal['effect.evolve_into'],
    /,
    **parameters: Unpack[EvolveIntoEffectParametersSchema],
) -> EvolveIntoEffectParameters: ...
@overload
def effect(
    kind: Literal['effect.evolve_from'],
    /,
    **parameters: Unpack[EvolveFromEffectParametersSchema],
) -> EvolveFromEffectParameters: ...
@overload
def effect(
    kind: Literal['effect.expand'], /, **parameters: Unpack[ExpandEffectParametersSchema]
) -> ExpandEffectParameters: ...
@overload
def effect(
    kind: Literal['effect.stretch'],
    /,
    **parameters: Unpack[StretchEffectParametersSchema],
) -> StretchEffectParameters: ...
@overload
def effect(
    kind: Literal['effect.explode'],
    /,
    **parameters: Unpack[ExplodeEffectParametersSchema],
) -> ExplodeEffectParameters: ...
@overload
def effect(
    kind: Literal['audio.bit_crush'],
    /,
    **parameters: Unpack[BitCrushAudioEffectParametersSchema],
) -> BitCrushAudioEffectParameters: ...
@overload
def effect(
    kind: Literal['audio.distortion'],
    /,
    **parameters: Unpack[DistortionAudioEffectParametersSchema],
) -> DistortionAudioEffectParameters: ...
@overload
def effect(
    kind: Literal['audio.low_pass'],
    /,
    **parameters: Unpack[LowPassAudioEffectParametersSchema],
) -> LowPassAudioEffectParameters: ...
@overload
def effect(
    kind: Literal['audio.high_pass'],
    /,
    **parameters: Unpack[HighPassAudioEffectParametersSchema],
) -> HighPassAudioEffectParameters: ...
@overload
def effect(
    kind: Literal['audio.delay'],
    /,
    **parameters: Unpack[DelayAudioEffectParametersSchema],
) -> DelayAudioEffectParameters: ...
@overload
def effect(
    kind: Literal['audio.reverb'],
    /,
    **parameters: Unpack[ReverbAudioEffectParametersSchema],
) -> ReverbAudioEffectParameters: ...
@overload
def effect(
    kind: Literal['audio.tremolo'],
    /,
    **parameters: Unpack[TremoloAudioEffectParametersSchema],
) -> TremoloAudioEffectParameters: ...
def effect(kind: EffectKind, /, **parameters: object) -> EffectParameters:
    """
    Create the parameters of a visual or sound effect.

    Each ``kind`` is an overload whose keyword arguments are typed by the settings of that
    effect and which returns that effect's parameters:
    ``effect('effect.fade_to', ...)`` returns a
    [`FadeToEffectParameters`][xnano.effects.FadeToEffectParameters]. The result can be
    inspected and edited, piped with ``|``, passed to ``add`` and ``update``, returned from a
    [`hook`][xnano.hooks.hook] or listed in ``effects=``.

    Args:
        kind: The effect to create: a visual kind such as ``'effect.fade_to'`` or a sound kind
            such as ``'audio.reverb'``.
        parameters: The keyword arguments of that kind.

    Returns:
        The parameters of the effect, not yet applied to anything.

    Raises:
        ValueError: ``kind`` is not a known effect kind, or is the kind of an operation that
            is not an effect, such as ``'fill'``.
        TypeError: A keyword is not a setting of that kind. The message lists its settings.

    Examples:
        ```python
        import xnano

        fade = xnano.effect('effect.fade_to', foreground='red', duration_milliseconds=200)
        assert fade.duration_milliseconds == 200
        with xnano.new('hi', width=4, height=1) as canvas:
            canvas.screen | fade
        ```
    """
    return build_effect(kind, parameters)
