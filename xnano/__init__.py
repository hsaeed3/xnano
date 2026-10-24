"""
xnano

An extremely nano python terminal experience; built on [ratatui](https://ratatui.rs/).
"""

from xnano import symbols as symbols
from xnano._internal._annotation_names import (
    bind_annotation_names as _bind_annotation_names,
)
from xnano.art import Image, Pixel, draw, load_image
from xnano.audio import Audio, Note, load_audio, note, play
from xnano.canvas import Canvas, active, new
from xnano.components import playable, renderable, writable
from xnano.effects import effect
from xnano.hooks import hook
from xnano.hooks._context import Context
from xnano.layout._region import box, write
from xnano.terminal import Terminal, iter, iter_async, open, open_async
from xnano_core import Color

__all__ = [
    'Audio',
    'Canvas',
    'Color',
    'Context',
    'Image',
    'Note',
    'Pixel',
    'Terminal',
    'active',
    'box',
    'draw',
    'effect',
    'hook',
    'iter',
    'iter_async',
    'load_audio',
    'load_image',
    'new',
    'note',
    'open',
    'open_async',
    'play',
    'playable',
    'renderable',
    'writable',
    'write',
]

# Every module has loaded by now, so the names that effect annotations need can be added.
_bind_annotation_names()
