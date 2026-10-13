"""
xnano._values

Type aliases shared by the terminal, placements and pixels.
"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Literal,
    Protocol,
    TypeAlias,
    TypeVar,
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

if TYPE_CHECKING:
    from xnano_image import TerminalImage

    from xnano._media import ImageBuffer
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

RangeBound: TypeAlias = Number | str | NumericExpression | None
"""One end of a range as written: cells, a percentage string, an expression, or ``None``."""

Axis: TypeAlias = int | float | str | tuple[RangeBound, RangeBound] | NumericExpression
"""
One number of a position or size: ``x``, ``y``, ``width`` or ``height``.

* ``12``: exactly that many cells.
* ``'50%'``: that share of the parent.
* a word that places it inside its parent: ``'left'``, ``'center'`` or ``'right'`` for ``x``, and
  ``'top'``, ``'center'`` or ``'bottom'`` for ``y``.
* an expression such as ``(ParentWidth - Width) // 2`` or ``ParentWidth * (TimeElapsed % 4 / 4)``:
  evaluated again on every frame, with ``TimeElapsed`` and the other clock references moving
  with the terminal's clock.
* a range, a pair ``(low, high)``: not a value but a limit on the values the axis may
  take. For ``x`` and ``y`` it is how far the placement
  may travel, such as the track of a slider; for ``width`` and ``height`` it is the
  smallest and largest size. Whatever is assigned afterwards is held inside the range, and
  the range stays until another one replaces it. Each bound is a number, a percentage
  string or an expression, and ``None`` leaves that side open.
"""

AttributeValue: TypeAlias = 'JSONValue | _core.Color | _core.Style | _core.Buffer | _core.Operation | _core.Expression[int] | _core.Expression[float] | _core.Expression[str] | _core.Expression[bool] | tuple[RangeBound, RangeBound]'  # noqa: E501
"""What a buffer attribute can be set to: plain data, a color, a style, or an expression."""

PixelEncoding: TypeAlias = Literal['half_blocks', 'braille']
"""``'half_blocks'``: one column and two rows of pixels per cell. ``'braille'``: two by four."""

TerminalBackend: TypeAlias = Literal['terminal', 'offscreen']

StateT = TypeVar('StateT')
"""The type of the dataclass a terminal keeps as its state, or ``None`` without one."""

ValueT = TypeVar('ValueT')

StateT_co = TypeVar('StateT_co', covariant=True)


@runtime_checkable
class Renderable(Protocol):
    """
    Anything a terminal can show.

    Implement ``__xnano_buffer__`` on your own class to make it addable to a terminal. A
    [`Buffer`][xnano_core.Buffer] (and so every widget), a string and the bytes
    of a cell grid are renderable without it.
    """

    def __xnano_buffer__(self) -> _core.Buffer:
        """Return the buffer that shows this object."""
        ...


Content: TypeAlias = 'Buffer | Renderable | str | bytes | TerminalImage | ImageBuffer'
"""What [`Terminal.add`][xnano.Terminal.add] accepts."""
