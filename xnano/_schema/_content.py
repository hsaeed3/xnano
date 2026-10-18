"""
xnano._schema._content

The protocols and aliases for what a canvas can show or play.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypeAlias, runtime_checkable

from xnano._schema._generics import DepsT_contra, StateT_contra

if TYPE_CHECKING:
    from collections.abc import Sequence

    from xnano_audio import TerminalMelody, TerminalNote, TerminalSound

    from xnano.art._images import Image
    from xnano.art._pixels import Pixel
    from xnano.art._worlds import Art
    from xnano.audio._melodies import Melody
    from xnano.audio._notes import Note
    from xnano.audio._sounds import Sound
    from xnano.context import Context
    from xnano.region import Region
    from xnano_core import Buffer


@runtime_checkable
class SupportsRender(Protocol[DepsT_contra, StateT_contra]):
    """
    Anything that draws itself: an object with a ``__xnano_render__`` method.

    The method receives the [`Context`][xnano.context.Context] and returns what to draw, which
    is any [`Renderable`][xnano.types.Renderable]. No base class is needed; a dataclass or a
    plain class qualifies. The context may be annotated with the dependency and state types
    the component reads, such as ``Context[Services]``. The method runs again, on the next
    frame, only when it read something that changes (the time, the size, state or an input).
    """

    def __xnano_render__(
        self, context: Context[DepsT_contra, StateT_contra]
    ) -> Renderable:
        """Return what to draw."""
        ...


@runtime_checkable
class SupportsPlay(Protocol[DepsT_contra, StateT_contra]):
    """
    Anything that can be played: an object with a ``__xnano_play__`` method.

    The method receives the [`Context`][xnano.context.Context] and returns what to play.
    No base class is needed; a dataclass or a plain class qualifies. The context may be
    annotated with the dependency and state types the component reads, such as
    ``Context[Services]``.
    """

    def __xnano_play__(self, context: Context[DepsT_contra, StateT_contra]) -> Playable:
        """Return what to play."""
        ...


Renderable: TypeAlias = (
    'str | Region | Art | Pixel | Image | Buffer | SupportsRender | Sequence[Renderable]'
)
"""
Anything [`Canvas.write`][xnano.canvas.Canvas.write] accepts: text, a
[`Region`][xnano.region.Region], an [`Art`][xnano.art.Art], a [`Pixel`][xnano.Pixel], an
[`Image`][xnano.Image], a core [`Buffer`][xnano_core.Buffer], an object with
``__xnano_render__``, or a sequence of those, which is stacked from top to bottom.
"""

Playable: TypeAlias = 'str | Note | Melody | Sound | SupportsPlay | Sequence[Playable]'
"""
Anything [`play`][xnano.play] and [`Canvas.play`][xnano.canvas.Canvas.play] accept: a
[`Note`][xnano.Note], a [`Melody`][xnano.audio.Melody], a [`Sound`][xnano.Sound], an object
with ``__xnano_play__``, a sequence of those that plays one after another, or a ``str``: the
name of a registered symbol, a note name such as ``'C#4'``, or melody text such as
``'C4 E4 G4:2'``.
"""

PlaySource: TypeAlias = (
    'Playable | int | float | TerminalSound | TerminalNote | TerminalMelody'
)
"""
Anything [`play`][xnano.play] and [`Canvas.play`][xnano.canvas.Canvas.play] accept: a
[`Playable`][xnano.types.Playable] (a [`Note`][xnano.Note], a [`Melody`][xnano.audio.Melody], a
[`Sound`][xnano.Sound], a symbol name, a note name such as ``'C#4'``, melody text, or a
sequence of those), a MIDI note number such as ``60``, a frequency in hertz, or a rendered
sound, note or melody from ``xnano-audio``.
"""

Content: TypeAlias = 'Renderable | Playable'
"""Anything a canvas can show or play: a ``Renderable`` or a ``Playable``."""
