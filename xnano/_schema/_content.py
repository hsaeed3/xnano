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
    from xnano.audio._audio import Audio
    from xnano.audio._melodies import Melody
    from xnano.audio._notes import Note
    from xnano.hooks._context import Context
    from xnano.layout._region import Region
    from xnano_core import Buffer


@runtime_checkable
class SupportsWrite(Protocol[DepsT_contra, StateT_contra]):
    """
    Anything that draws itself: an object with a ``__xnano_write__`` method.

    The method receives the [`Context`][xnano.hooks.Context] and returns what to draw, which
    is any [`Writable`][xnano.components.Writable]. No base class is needed; a dataclass or a
    plain class qualifies. The context may be annotated with the dependency and state types
    the component reads, such as ``Context[Services]``. The method runs again, on the next
    frame, only when it read something that changes (the time, the size, state or an input).
    """

    def __xnano_write__(self, context: Context[DepsT_contra, StateT_contra]) -> Writable:
        """Return what to draw."""
        ...


@runtime_checkable
class SupportsRender(Protocol[DepsT_contra, StateT_contra]):
    """
    Anything with a screen of its own: an object with a ``__xnano_render__`` method.

    The method receives the [`Context`][xnano.hooks.Context], draws on ``context.screen``
    (its own screen, where it is written) and plays on ``context.speaker``, and returns
    nothing. Each run starts from an empty screen. No base class is needed; a dataclass or a
    plain class qualifies. The method runs again, on the next frame, only when it read
    something that changes (the time, the size, state or an input).
    """

    def __xnano_render__(self, context: Context[DepsT_contra, StateT_contra]) -> None:
        """Draw on ``context.screen`` and play on ``context.speaker``."""
        ...


@runtime_checkable
class SupportsPlay(Protocol[DepsT_contra, StateT_contra]):
    """
    Anything that can be played: an object with a ``__xnano_play__`` method.

    The method receives the [`Context`][xnano.hooks.Context] and returns what to play.
    No base class is needed; a dataclass or a plain class qualifies. The context may be
    annotated with the dependency and state types the component reads, such as
    ``Context[Services]``.
    """

    def __xnano_play__(self, context: Context[DepsT_contra, StateT_contra]) -> Playable:
        """Return what to play."""
        ...


Writable: TypeAlias = 'str | Region | Art | Pixel | Image | Buffer | SupportsWrite | SupportsRender | Sequence[Writable]'  # fmt: skip
"""
Anything [`Screen.write`][xnano.devices.Screen.write] accepts: text, a
[`Region`][xnano.layout.Region], an [`Art`][xnano.art.Art], a [`Pixel`][xnano.Pixel], an
[`Image`][xnano.Image], a core [`Buffer`][xnano_core.Buffer], an object with
``__xnano_write__``, or a sequence of those, which is stacked from top to bottom; or a
renderable, an object with ``__xnano_render__``, which is written on its own.
"""

Playable: TypeAlias = 'str | Note | Melody | Audio | SupportsPlay | Sequence[Playable]'
"""
Anything [`play`][xnano.play] and [`Speaker.play`][xnano.devices.Speaker.play] accept: a
[`Note`][xnano.Note], a [`Melody`][xnano.audio.Melody], an [`Audio`][xnano.Audio], an object
with ``__xnano_play__``, a sequence of those that plays one after another, or a ``str``: the
name of a registered symbol, a note name such as ``'C#4'``, or melody text such as
``'C4 E4 G4:2'``.
"""

PlaySource: TypeAlias = (
    'Playable | int | float | TerminalSound | TerminalNote | TerminalMelody'
)
"""
Anything [`play`][xnano.play] and [`Speaker.play`][xnano.devices.Speaker.play] accept: a
[`Playable`][xnano.components.Playable] (a [`Note`][xnano.Note], a [`Melody`][xnano.audio.Melody], a
[`Audio`][xnano.Audio], a symbol name, a note name such as ``'C#4'``, melody text, or a
sequence of those), a MIDI note number such as ``60``, a frequency in hertz, or a rendered
sound, note or melody from ``xnano-audio``.
"""

Content: TypeAlias = 'Writable | Playable'
"""Anything a canvas can show or play: a ``Writable`` or a ``Playable``."""
