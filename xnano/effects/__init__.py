"""
xnano.effects

Effects: how content changes over time, in how it looks or how it sounds.

[`effect`][xnano.effects.effect] builds the parameters of a visual effect (a kind that starts
with ``'effect.'``, such as ``'effect.fade_to'``) or a sound effect (a kind that starts with
``'audio.'``, such as ``'audio.reverb'``). The result is applied with ``|``, ``update``, a
hook that returns it, or an ``effects=[...]`` list, and assigning one of its fields changes
the effect while it runs.

The ``.fx`` properties of placements, canvases, ``canvas.audio`` and ``context`` start an effect
by name instead: ``placement.fx.fade_to(...)``, ``canvas.audio.fx.reverb(...)`` and
``context.fx.fade_to(...)``. An ``effects=[...]`` list takes each effect as a dictionary with
its ``kind``, such as ``{'kind': 'effect.fade_to', 'foreground': 'red'}``.

``Effect.fade_to(...)`` in [`xnano.operations`][xnano.operations] is the operation form of
``effect('effect.fade_to', ...)``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, overload

from xnano._schema._effects import EffectKind as EffectKind
from xnano._schema._effects import PlayableEffectKind as PlayableEffectKind
from xnano._schema._effects import RenderableEffectKind as RenderableEffectKind
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
    RenderableEffectProperties as RenderableEffectProperties,
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
from xnano.effects._registry import build_effect

if TYPE_CHECKING:
    from typing_extensions import Unpack

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
        LightenEffectParametersSchema,
        LowPassAudioEffectParametersSchema,
        PaintEffectParametersSchema,
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

__all__ = [
    'effect',
    'EffectKind',
    'RenderableEffectKind',
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
    'RenderableEffectProperties',
    'PlayableEffectProperties',
    'EffectController',
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
            canvas | fade
        ```
    """
    return build_effect(kind, parameters)
