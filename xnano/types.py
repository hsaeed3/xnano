"""
xnano.types

The types that describe what `xnano` accepts: positions and sizes as an axis, anything that can
be added to a terminal, space around text, pixel encodings, terminal backends, and the functions that hook into
events.
"""

from xnano._appearance import (
    Spacing as Spacing,
)
from xnano._appearance import (
    SpacingDictionary as SpacingDictionary,
)
from xnano._hooks import (
    Hook as Hook,
)
from xnano._hooks import (
    Trigger as Trigger,
)
from xnano._hooks import (
    TriggerGenerator as TriggerGenerator,
)
from xnano._values import (
    Axis as Axis,
)
from xnano._values import (
    Content as Content,
)
from xnano._values import (
    PixelEncoding as PixelEncoding,
)
from xnano._values import (
    RangeBound as RangeBound,
)
from xnano._values import (
    Renderable as Renderable,
)
from xnano._values import (
    TerminalBackend as TerminalBackend,
)

__all__ = [
    'Axis',
    'Content',
    'Hook',
    'PixelEncoding',
    'RangeBound',
    'Renderable',
    'Spacing',
    'SpacingDictionary',
    'TerminalBackend',
    'Trigger',
    'TriggerGenerator',
]
