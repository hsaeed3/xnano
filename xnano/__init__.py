"""
xnano

Terminal interfaces that you describe in a few lines. Create a canvas with ``new()`` to draw
off the screen, or with ``open()`` to draw in your terminal, write text, widgets, art, images
and other canvases onto it, and react to the keyboard, the mouse, time and state with hooks.
"""

from xnano import symbols as symbols
from xnano._media import Audio, Image, from_audio, from_image
from xnano.art import draw
from xnano.canvas import Canvas, active, iter, new
from xnano.components import playable, renderable
from xnano.context import Context
from xnano.music import Note, note, play
from xnano.operations import hook
from xnano.pixel import Pixel
from xnano.region import box, write
from xnano.terminal import Terminal, open
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
    'from_audio',
    'from_image',
    'hook',
    'iter',
    'new',
    'note',
    'open',
    'play',
    'playable',
    'renderable',
    'write',
]
