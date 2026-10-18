"""
xnano

An extremely nano python terminal experience; built on [ratatui](https://ratatui.rs/).
"""

from xnano import symbols as symbols
from xnano._internal._annotation_names import (
    bind_annotation_names as _bind_annotation_names,
)
from xnano.art import Image, Pixel, draw, load_image
from xnano.audio import Note, Sound, load_sound, note, play
from xnano.canvas import Canvas, active, iter, new
from xnano.components import playable, renderable
from xnano.context import Context
from xnano.effects import effect
from xnano.hooks import hook
from xnano.region import box, write
from xnano.terminal import Terminal, open
from xnano_core import Color

__all__ = [
    'Canvas',
    'Color',
    'Context',
    'Image',
    'Note',
    'Pixel',
    'Sound',
    'Terminal',
    'active',
    'box',
    'draw',
    'effect',
    'hook',
    'iter',
    'load_image',
    'load_sound',
    'new',
    'note',
    'open',
    'play',
    'playable',
    'renderable',
    'write',
]

# Every module has loaded by now, so the names that effect annotations need can be added.
_bind_annotation_names()
