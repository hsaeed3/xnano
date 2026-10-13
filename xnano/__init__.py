"""
xnano

Draw on a terminal with numbers and formulas, and everything `xnano-core`, `xnano-audio`
and `xnano-image` can do, from one small API.

[`open`][xnano.open] gives you a [`Terminal`][xnano.Terminal]: one surface of cells with a
clock, a cursor, event hooks, sound and optional typed state. Put anything on it with
[`Terminal.add`][xnano.Terminal.add]: text, buffers and widgets, images (a
[`TerminalImage`][xnano_image.TerminalImage] or the path of an image file) and
compositions. Every number you give it, a position, a size, a color channel, can be an
expression of time, of the terminal's size or of any other buffer, so a layout is a formula
that is evaluated again on every frame. Play notes, melodies and sounds with
[`Terminal.audio`][xnano.Terminal.audio], and let the microphone level or the musical beat
drive what is on screen.

The rest lives in modules named for what they hold: ``xnano.widgets``, ``xnano.operations``,
``xnano.effects``, ``xnano.expressions``, ``xnano.styles``, ``xnano.events``, ``xnano.geometry``,
``xnano.buffers``, ``xnano.scene``, ``xnano.types`` and ``xnano.errors``, and the optional
``xnano.audio`` and ``xnano.image``.

Examples:
    A formula for a position, drawn on three frames of a 30 frames per second clock::

        import xnano
        from xnano.buffers import Buffer
        from xnano.expressions import TimeElapsed, ParentWidth, Width

        with xnano.open(offscreen=True, width=20, height=3, fps=30) as terminal:
            ball = terminal.add(Buffer.with_text('o'))
            ball.x = (ParentWidth - Width) * (TimeElapsed % 1.0)
            for frame in terminal.loop.frames(count=3):
                pass
"""

import importlib
from typing import TYPE_CHECKING

from xnano import (
    buffers,
    effects,
    errors,
    events,
    expressions,
    geometry,
    operations,
    scene,
    styles,
    types,
    widgets,
)
from xnano.composition import Composition, make
from xnano.context import Context, Frame, Update
from xnano.loop import Loop
from xnano.output import Output
from xnano.pixels import Pixels
from xnano.placement import Placement
from xnano.terminal import Terminal, active, open

if TYPE_CHECKING:
    from xnano import audio, image

__all__ = [
    'Composition',
    'Context',
    'Frame',
    'Loop',
    'Output',
    'Pixels',
    'Placement',
    'Terminal',
    'Update',
    'active',
    'buffers',
    'effects',
    'errors',
    'events',
    'expressions',
    'geometry',
    'make',
    'open',
    'operations',
    'scene',
    'styles',
    'types',
    'widgets',
    'audio',
    'image',
]

_OPTIONAL_SUBMODULES = ('audio', 'image')


def __getattr__(name: str) -> object:
    """Import ``xnano.audio`` or ``xnano.image`` the first time it is used."""
    if name in _OPTIONAL_SUBMODULES:
        return importlib.import_module(f'xnano.{name}')
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


def __dir__() -> list[str]:
    return sorted([*__all__, *_OPTIONAL_SUBMODULES])
