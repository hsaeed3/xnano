"""
xnano._schema._axes

The aliases for the numbers that place and size a buffer: cells, percentages, words, ranges
and expressions.
"""

from __future__ import annotations

from typing import Literal, TypeAlias

import xnano_core as _core
from xnano_core import JSONValue

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

FlowPosition: TypeAlias = Literal['next']
"""
The word that places something after what was written before it, where ``write`` puts content
that is given no position.

``y='next'`` starts a line on the first row below the lines written before it, at column ``0``
when ``x`` is ``'next'`` too; content given a ``y`` of its own, such as a status line at
``y='bottom'``, is not one of the lines. ``x='next'`` with a ``y`` that was given continues on
that row, right after the content written just before, when that content is on the row and
there is room after it; otherwise it starts at column ``0``. The position is kept up to date:
when a line grows, shrinks or is removed, the lines after it follow.
"""

RangeBound: TypeAlias = Number | Percentage | str | NumericExpression | None
"""One end of a range as written: cells, a percentage string, an expression, or ``None``."""

Axis: TypeAlias = (
    int
    | float
    | Percentage
    | HorizontalPosition
    | VerticalPosition
    | FlowPosition
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
* ``'next'`` for ``x`` and ``y``: after what was written before it, on the next line by default;
  see [`FlowPosition`][xnano.layout.FlowPosition].
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
