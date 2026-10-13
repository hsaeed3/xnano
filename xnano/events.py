"""
xnano.events

The events a terminal delivers to its hooks: keys, the mouse and everything else.

A hook receives them as ``context.event``; see [`Context`][xnano.Context].
"""

from xnano_core import (
    Event as Event,
)
from xnano_core import (
    KeyEvent as KeyEvent,
)
from xnano_core import (
    MouseEvent as MouseEvent,
)

__all__ = [
    'Event',
    'KeyEvent',
    'MouseEvent',
]
