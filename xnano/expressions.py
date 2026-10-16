"""
xnano.expressions

The expression language: values that are evaluated again on every frame.

An [`Expression`][xnano.expressions.Expression] stands for a number, a position or a state that
changes, such as the elapsed time, the width of the parent or the pointer position. Combine
them with arithmetic and give them to anything that takes a number, or read them from the
``parent``, ``root`` and ``time`` attributes on a [`Canvas`][xnano.canvas.Canvas] or a
[`Placement`][xnano.placement.Placement].
"""

from __future__ import annotations

from xnano_core import (
    FPS as FPS,
)
from xnano_core import (
    BufferExpressionScope as BufferExpressionScope,
)
from xnano_core import (
    BufferScope,
    ParentScope,
    RootScope,
)
from xnano_core import (
    BufferSize as BufferSize,
)
from xnano_core import (
    DeviceHeight as DeviceHeight,
)
from xnano_core import (
    DeviceWidth as DeviceWidth,
)
from xnano_core import (
    Expression as Expression,
)
from xnano_core import (
    Focused as Focused,
)
from xnano_core import (
    Height as Height,
)
from xnano_core import (
    IsVisible as IsVisible,
)
from xnano_core import (
    NumericValue as NumericValue,
)
from xnano_core import (
    ParentExpressionScope as ParentExpressionScope,
)
from xnano_core import (
    ParentHeight as ParentHeight,
)
from xnano_core import (
    ParentSize as ParentSize,
)
from xnano_core import (
    ParentWidth as ParentWidth,
)
from xnano_core import (
    PointerPosition as PointerPosition,
)
from xnano_core import (
    Position as Position,
)
from xnano_core import (
    RootExpressionScope as RootExpressionScope,
)
from xnano_core import (
    ScreenBounds as ScreenBounds,
)
from xnano_core import (
    ScreenPosition as ScreenPosition,
)
from xnano_core import (
    Size as Size,
)
from xnano_core import (
    TimeDelta as TimeDelta,
)
from xnano_core import (
    TimeDeltaMilliseconds as TimeDeltaMilliseconds,
)
from xnano_core import (
    TimeElapsed as TimeElapsed,
)
from xnano_core import (
    TimeElapsedMilliseconds as TimeElapsedMilliseconds,
)
from xnano_core import (
    Value as Value,
)
from xnano_core import (
    Width as Width,
)
from xnano_core import (
    X as X,
)
from xnano_core import (
    Y as Y,
)

Parent: ParentExpressionScope = ParentScope
"""Symbolic expressions for the parent buffer's geometry (``Parent.width``, ``Parent.height``)."""

Root: RootExpressionScope = RootScope
"""Symbolic expressions for the root canvas's geometry and clock (``Root.width``, ``Root.time``)."""

BufferExpressions: BufferExpressionScope = BufferScope
"""Symbolic expressions for the current buffer's geometry (``BufferExpressions.width``, ``BufferExpressions.height``)."""

__all__ = [
    'BufferExpressionScope',
    'BufferExpressions',
    'BufferSize',
    'DeviceHeight',
    'DeviceWidth',
    'Expression',
    'FPS',
    'Focused',
    'Height',
    'IsVisible',
    'NumericValue',
    'Parent',
    'ParentExpressionScope',
    'ParentHeight',
    'ParentSize',
    'ParentWidth',
    'PointerPosition',
    'Position',
    'Root',
    'RootExpressionScope',
    'ScreenBounds',
    'ScreenPosition',
    'Size',
    'TimeDelta',
    'TimeDeltaMilliseconds',
    'TimeElapsed',
    'TimeElapsedMilliseconds',
    'Value',
    'Width',
    'X',
    'Y',
]
