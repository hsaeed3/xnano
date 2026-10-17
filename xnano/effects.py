"""
xnano.effects

Animated effects that change how a buffer looks over time, such as fading or dissolving.

An effect is applied to a buffer like any operation and runs on the canvas's clock until it
finishes or is cancelled.
"""

from xnano_core import (
    CancelEffect as CancelEffect,
)
from xnano_core import (
    Dissolve as Dissolve,
)
from xnano_core import (
    Effect as Effect,
)
from xnano_core import (
    Fade as Fade,
)
from xnano_core import (
    Fuzz as Fuzz,
)
from xnano_core import (
    Glitch as Glitch,
)

__all__ = [
    'CancelEffect',
    'Dissolve',
    'Effect',
    'Fade',
    'Fuzz',
    'Glitch',
]
