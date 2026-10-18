"""
xnano._values

Type aliases shared by the canvas, placements and pixels.
"""

from __future__ import annotations

import sys
from typing import (
    TYPE_CHECKING,
    Literal,
    Protocol,
    TypeAlias,
    runtime_checkable,
)

import xnano_core as _core
from xnano_core import (
    ColorName as ColorName,
)
from xnano_core import ColorValue as ColorValue
from xnano_core import JSONValue
from xnano_core import (
    TailwindColorBinding as TailwindColorBinding,
)
from xnano_core import (
    TailwindColorName as TailwindColorName,
)
from xnano_core import (
    TailwindColorShade as TailwindColorShade,
)

if sys.version_info >= (3, 13):
    from typing import Never, TypeVar
else:
    from typing_extensions import Never, TypeVar

if TYPE_CHECKING:
    from collections.abc import Sequence

    from xnano_audio import TerminalMelody, TerminalNote, TerminalSound

    from xnano._media import Audio, Image
    from xnano.art import Art
    from xnano.context import Context
    from xnano.music import Note
    from xnano.pixel import Pixel
    from xnano.region import Region
    from xnano_core import Buffer

# --------------------------------------------------------------------------------------

RGB: TypeAlias = tuple[int, int, int]
"""A color as red, green and blue channels, each from 0 to 255."""

Number: TypeAlias = int | float

NumericExpression: TypeAlias = _core.NumericValue[int] | _core.NumericValue[float]
"""An expression that evaluates to a number, such as ``ParentWidth // 2`` or ``TimeElapsed * 3``."""

AxisName: TypeAlias = Literal['x', 'y', 'width', 'height']
"""The four numbers that place and size a buffer."""

Bound: TypeAlias = Number | NumericExpression
"""One end of a range, once a percentage has become an expression."""

Percentage: TypeAlias = Literal[
    '5%',
    '10%',
    '15%',
    '20%',
    '25%',
    '30%',
    '35%',
    '40%',
    '45%',
    '50%',
    '55%',
    '60%',
    '65%',
    '70%',
    '75%',
    '80%',
    '85%',
    '90%',
    '95%',
    '100%',
]
"""
A share of the space a size or position is measured against, such as ``'50%'``.

Editors suggest the steps of 5% listed here, and every other percentage, such as ``'33%'`` or
``'12.5%'``, works the same way; a parameter that takes a percentage also takes any ``str``.
"""

HorizontalPosition: TypeAlias = Literal['left', 'center', 'right']
"""A word that places something inside its parent along ``x``."""

VerticalPosition: TypeAlias = Literal['top', 'center', 'bottom']
"""A word that places something inside its parent along ``y``."""

CanvasLayout: TypeAlias = Literal['overlay', 'column', 'row']
"""
How a canvas places what is written on it.

``'overlay'`` places every piece on its own, over the whole canvas. ``'column'`` stacks the
pieces from top to bottom in the order they are written, and ``'row'`` from left to right.
"""

EdgeBehavior: TypeAlias = Literal['clip', 'stop', 'wrap']
"""
What content does at the edges of its area.

``'clip'`` lets it go past the edge, where it is not drawn. ``'stop'`` holds it inside the
area when it moves. ``'wrap'`` continues text on the next rows of the area.
"""

RangeBound: TypeAlias = Number | Percentage | str | NumericExpression | None
"""One end of a range as written: cells, a percentage string, an expression, or ``None``."""

Axis: TypeAlias = (
    int
    | float
    | Percentage
    | HorizontalPosition
    | VerticalPosition
    | str
    | tuple[RangeBound, RangeBound]
    | NumericExpression
)
"""
One number of a position or size: ``x``, ``y``, ``width`` or ``height``.

* ``12``: exactly that many cells.
* ``'50%'``: that share of the parent.
* a word that places it inside its parent: ``'left'``, ``'center'`` or ``'right'`` for ``x``, and
  ``'top'``, ``'center'`` or ``'bottom'`` for ``y``.
* an expression such as ``(ParentWidth - Width) // 2`` or ``ParentWidth * (TimeElapsed % 4 / 4)``:
  evaluated again on every frame, with ``TimeElapsed`` and the other clock references moving
  with the canvas's clock.
* a range, a pair ``(low, high)``: not a value but a limit on the values the axis may
  take. For ``x`` and ``y`` it is how far the placement
  may travel, such as the track of a slider; for ``width`` and ``height`` it is the
  smallest and largest size. Whatever is assigned afterwards is held inside the range, and
  the range stays until another one replaces it. Each bound is a number, a percentage
  string or an expression, and ``None`` leaves that side open.
"""

AttributeValue: TypeAlias = 'JSONValue | _core.Color | _core.Style | _core.Buffer | _core.Operation | _core.Expression[int] | _core.Expression[float] | _core.Expression[str] | _core.Expression[bool] | tuple[RangeBound, RangeBound]'  # noqa: E501
"""What a buffer attribute can be set to: plain data, a color, a style, or an expression."""

Interpolation: TypeAlias = Literal[
    'linear',
    'back_in',
    'back_out',
    'back_in_out',
    'bounce_in',
    'bounce_out',
    'bounce_in_out',
    'circ_in',
    'circ_out',
    'circ_in_out',
    'cubic_in',
    'cubic_out',
    'cubic_in_out',
    'elastic_in',
    'elastic_out',
    'elastic_in_out',
    'expo_in',
    'expo_out',
    'expo_in_out',
    'quad_in',
    'quad_out',
    'quad_in_out',
    'quart_in',
    'quart_out',
    'quart_in_out',
    'quint_in',
    'quint_out',
    'quint_in_out',
    'sine_in',
    'sine_out',
    'sine_in_out',
    'smooth_step',
    'spring',
    'reverse',
    'ease_in',
]
"""
How an effect eases between its start and end: ``'linear'``, or a curve such as
``'quad_in_out'`` or ``'bounce_out'``. ``'ease_in'`` is ``'quad_in'``.
"""

MotionDirection: TypeAlias = Literal[
    'left_to_right', 'right_to_left', 'up_to_down', 'down_to_up'
]
"""The direction a sweep, slide or stretch effect moves in."""

PixelEncoding: TypeAlias = Literal['half_blocks', 'braille']
"""``'half_blocks'``: one column and two rows of pixels per cell. ``'braille'``: two by four."""

DepsT = TypeVar('DepsT', default=None)
"""The type of the dependencies a canvas was given with ``new(deps=...)``, or ``None``."""

StateT = TypeVar('StateT', default=None)
"""The type of the dataclass a canvas keeps as its state, or ``None`` without one."""

ValueT = TypeVar('ValueT')

WrittenDepsT = TypeVar('WrittenDepsT')
"""The dependencies type of a canvas that is written into another, whatever it is."""

WrittenStateT = TypeVar('WrittenStateT')
"""The state type of a canvas that is written into another, whatever it is."""

DepsT_co = TypeVar('DepsT_co', covariant=True, default=None)

StateT_co = TypeVar('StateT_co', covariant=True, default=None)

DepsT_contra = TypeVar('DepsT_contra', contravariant=True, default=Never)

StateT_contra = TypeVar('StateT_contra', contravariant=True, default=Never)


KeyName: TypeAlias = Literal[
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
    'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    'space', 'enter', 'escape', 'tab', 'backspace', 'delete', 'insert',
    'home', 'end', 'page_up', 'page_down', 'up', 'down', 'left', 'right',
    'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
] | str  # fmt: skip
"""
The name of a key such as ``'q'``, ``'enter'`` or ``'page_up'``.

A key with modifiers is written as a chord joined with ``+``, such as ``'ctrl+s'`` or
``'shift+tab'``; the trailing ``str`` lets a chord and punctuation keys type-check while editors
still suggest the names listed here.
"""

HeldMouseButtonName: TypeAlias = Literal['mouse_left', 'mouse_right', 'mouse_middle']
"""
The name of a mouse button in the held-input vocabulary of [`Input`][xnano.input.Input].

``Input.is_down('mouse_left')`` asks whether the left button is held. The button of a mouse
event keeps the names ``'left'``, ``'right'`` and ``'middle'``.
"""


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

Playable: TypeAlias = 'str | Note | Audio | SupportsPlay | Sequence[Playable]'
"""
Anything [`play`][xnano.play] and [`Canvas.play`][xnano.canvas.Canvas.play] accept: a
[`Note`][xnano.Note], an [`Audio`][xnano.Audio], an object with ``__xnano_play__``, a
sequence of those that plays one after another, or a ``str``: the name of a registered
symbol, a note name such as ``'C#4'``, or melody text such as ``'C4 E4 G4:2'``.
"""

PlaySource: TypeAlias = (
    'Playable | int | float | TerminalSound | TerminalNote | TerminalMelody'
)
"""
Anything [`play`][xnano.play] and [`Canvas.play`][xnano.canvas.Canvas.play] accept: a
[`Playable`][xnano.types.Playable] (a [`Note`][xnano.Note], an [`Audio`][xnano.Audio], a symbol
name, a note name such as ``'C#4'``, melody text, or a sequence of those), a MIDI note number
such as ``60``, a frequency in hertz, or a rendered sound, note or melody from ``xnano-audio``.
"""

Content: TypeAlias = 'Renderable | Playable'
"""Anything a canvas can show or play: a ``Renderable`` or a ``Playable``."""

Anchor: TypeAlias = tuple[int, int]
"""
The ``(x, y)`` pixel inside an [`Art`][xnano.art.Art] that sits at the art's ``(x, y)``.

``anchor=(3, 8)`` makes ``(x, y)`` the place a character's feet touch; ``(0, 0)`` is the top-left
pixel.
"""
