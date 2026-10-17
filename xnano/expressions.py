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
    BufferRegion as BufferRegion,
)
from xnano_core import (
    BufferScope,
    KeyboardScope,
    MouseScope,
    ParentScope,
    RootScope,
    ScrollScope,
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
    KeyboardChord as KeyboardChord,
)
from xnano_core import (
    KeyboardExpressionScope as KeyboardExpressionScope,
)
from xnano_core import (
    KeyboardKey as KeyboardKey,
)
from xnano_core import (
    KeyboardKind as KeyboardKind,
)
from xnano_core import (
    MouseButtonValue as MouseButtonValue,
)
from xnano_core import (
    MouseExpressionScope as MouseExpressionScope,
)
from xnano_core import (
    MouseIsDown as MouseIsDown,
)
from xnano_core import (
    MouseKind as MouseKind,
)
from xnano_core import (
    MousePosition as MousePosition,
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
    ScrollExpressionScope as ScrollExpressionScope,
)
from xnano_core import (
    ScrollX as ScrollX,
)
from xnano_core import (
    ScrollY as ScrollY,
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
"""
Symbolic expressions for the current buffer's geometry (``BufferExpressions.width``,
``BufferExpressions.height``) and its rectangle on the screen (``BufferExpressions.region``).
"""

Keyboard: KeyboardExpressionScope = KeyboardScope
"""Symbolic expressions for the latest key event (``Keyboard.key``, ``Keyboard.kind``, ``Keyboard.chord``)."""

Mouse: MouseExpressionScope = MouseScope
"""
Symbolic expressions for the latest mouse button or movement report (``Mouse.position``,
``Mouse.button``, ``Mouse.kind``) and whether a button is held (``Mouse.is_down``).
"""

Scroll: ScrollExpressionScope = ScrollScope
"""Symbolic expressions for the mouse wheel steps of the current step (``Scroll.x``, ``Scroll.y``)."""

__all__ = [
    'BufferExpressionScope',
    'BufferExpressions',
    'BufferRegion',
    'BufferSize',
    'DeviceHeight',
    'DeviceWidth',
    'Expression',
    'FPS',
    'Focused',
    'Height',
    'IsVisible',
    'Keyboard',
    'KeyboardChord',
    'KeyboardExpressionScope',
    'KeyboardKey',
    'KeyboardKind',
    'Mouse',
    'MouseButtonValue',
    'MouseExpressionScope',
    'MouseIsDown',
    'MouseKind',
    'MousePosition',
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
    'Scroll',
    'ScrollExpressionScope',
    'ScrollX',
    'ScrollY',
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
