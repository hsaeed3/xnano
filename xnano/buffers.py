"""
xnano.buffers

Buffers: grids of cells that hold text and styles.

A [`Buffer`][xnano.buffers.Buffer] is what a terminal draws; each [`Cell`][xnano.buffers.Cell] holds
one symbol with its colors.
"""

from xnano._media import Image as Image
from xnano_core import (
    Buffer as Buffer,
)
from xnano_core import (
    BufferSize as BufferSize,
)
from xnano_core import (
    Cell as Cell,
)

__all__ = [
    'Buffer',
    'BufferSize',
    'Cell',
    'Image',
]
