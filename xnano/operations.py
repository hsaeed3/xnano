"""
xnano.operations

Operations that change a buffer: write text, fill, color, paste, border, place and resize.

Pass operations to ``Buffer.update`` to apply them in order. An operation is a value, so it can
be built once and applied again, or driven by expressions.
"""

from xnano_core import (
    Background as Background,
)
from xnano_core import (
    Border as Border,
)
from xnano_core import (
    Clear as Clear,
)
from xnano_core import (
    Fill as Fill,
)
from xnano_core import (
    Foreground as Foreground,
)
from xnano_core import (
    Layout as Layout,
)
from xnano_core import (
    Move as Move,
)
from xnano_core import (
    Operation as Operation,
)
from xnano_core import (
    Paste as Paste,
)
from xnano_core import (
    Place as Place,
)
from xnano_core import (
    Resize as Resize,
)
from xnano_core import (
    Write as Write,
)

__all__ = [
    'Background',
    'Border',
    'Clear',
    'Fill',
    'Foreground',
    'Layout',
    'Move',
    'Operation',
    'Paste',
    'Place',
    'Resize',
    'Write',
]
