"""
xnano.expressions

Dynamic properties and values that can be used for mathematical operations.

An [`Expression`][xnano.expressions.Expression] stands for a positional, stateful or other
runtime value that changes over time or is otherwise not possible to express in a static
context, such as the width of the parent, the elapsed time or the pointer position.

You can use expressions along with all of Python's standard arithmetic operators, and give
them to anything that takes a number: a position, a size or a range. Comparing one builds a
condition, which hooks take as ``when=``. Read the current value of one with
[`Canvas.inspect`][xnano.canvas.Canvas.inspect].

```python
import xnano
from xnano.expressions import ParentWidth, TimeElapsed, Width

with xnano.open(width=40, height=3) as terminal:
    # A formula keeps the text centered, whatever the width of the window.
    terminal.write('centered', x=(ParentWidth - Width) // 2)

    # A formula that reads the time moves the ball on every frame.
    ball = terminal.write('o', y=2)
    ball.x = (ParentWidth - Width) * (TimeElapsed % 2 / 2)

    terminal.run(quit_on='q')
```
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from xnano_core import FPS as _CoreFPS
    from xnano_core import BufferExpressionScope as _CoreBufferExpressionScope
    from xnano_core import BufferRegion as _CoreBufferRegion
    from xnano_core import BufferScope as _CoreBufferScope
    from xnano_core import BufferSize as _CoreBufferSize
    from xnano_core import DeviceHeight as _CoreDeviceHeight
    from xnano_core import DeviceWidth as _CoreDeviceWidth
    from xnano_core import Expression as _CoreExpression
    from xnano_core import Focused as _CoreFocused
    from xnano_core import Height as _CoreHeight
    from xnano_core import IsVisible as _CoreIsVisible
    from xnano_core import KeyboardChord as _CoreKeyboardChord
    from xnano_core import KeyboardExpressionScope as _CoreKeyboardExpressionScope
    from xnano_core import KeyboardKey as _CoreKeyboardKey
    from xnano_core import KeyboardKind as _CoreKeyboardKind
    from xnano_core import KeyboardScope as _CoreKeyboardScope
    from xnano_core import MouseButtonValue as _CoreMouseButtonValue
    from xnano_core import MouseExpressionScope as _CoreMouseExpressionScope
    from xnano_core import MouseIsDown as _CoreMouseIsDown
    from xnano_core import MouseKind as _CoreMouseKind
    from xnano_core import MousePosition as _CoreMousePosition
    from xnano_core import MouseScope as _CoreMouseScope
    from xnano_core import NumericValue as _CoreNumericValue
    from xnano_core import ParentExpressionScope as _CoreParentExpressionScope
    from xnano_core import ParentHeight as _CoreParentHeight
    from xnano_core import ParentScope as _CoreParentScope
    from xnano_core import ParentSize as _CoreParentSize
    from xnano_core import ParentWidth as _CoreParentWidth
    from xnano_core import PointerPosition as _CorePointerPosition
    from xnano_core import Position as _CorePosition
    from xnano_core import RootExpressionScope as _CoreRootExpressionScope
    from xnano_core import RootScope as _CoreRootScope
    from xnano_core import ScreenBounds as _CoreScreenBounds
    from xnano_core import ScreenPosition as _CoreScreenPosition
    from xnano_core import ScrollExpressionScope as _CoreScrollExpressionScope
    from xnano_core import ScrollScope as _CoreScrollScope
    from xnano_core import ScrollX as _CoreScrollX
    from xnano_core import ScrollY as _CoreScrollY
    from xnano_core import Size as _CoreSize
    from xnano_core import TimeDelta as _CoreTimeDelta
    from xnano_core import TimeDeltaMilliseconds as _CoreTimeDeltaMilliseconds
    from xnano_core import TimeElapsed as _CoreTimeElapsed
    from xnano_core import TimeElapsedMilliseconds as _CoreTimeElapsedMilliseconds
    from xnano_core import Value as _CoreValue
    from xnano_core import Width as _CoreWidth
    from xnano_core import X as _CoreX
    from xnano_core import Y as _CoreY

    Expression = _CoreExpression
    """
    The base of every expression: a value, a condition or a change that is worked out again on every frame.

    ```python
    import xnano
    from xnano.expressions import Expression, ParentWidth, Width

    centered = (ParentWidth - Width) // 2
    assert isinstance(centered, Expression)
    with xnano.new(width=20, height=2) as canvas:
        text = canvas.write('centered', x=centered)
        assert text.x == 6
    ```
    """

    Value = _CoreValue
    """
    An expression with a value that is not a number, such as a key name or a rectangle. ``==`` and ``!=`` on it build conditions.

    ```python
    import xnano
    from xnano.expressions import BufferSize, Value
    from xnano.geometry import Size

    assert isinstance(BufferSize, Value)
    with xnano.new(width=20, height=2) as canvas:
        assert canvas.inspect(BufferSize) == Size(20, 2)
        assert canvas.inspect(BufferSize == Size(20, 2)) is True
    ```
    """

    NumericValue = _CoreNumericValue
    """
    An expression with a number for a value. Arithmetic on it builds new expressions, and ``<``, ``>`` and their relatives build conditions.

    ```python
    import xnano
    from xnano.expressions import NumericValue, Width

    assert isinstance(Width, NumericValue)
    with xnano.new(width=20, height=2) as canvas:
        assert canvas.inspect(Width * 2) == 40
        assert canvas.inspect(Width > 10) is True
    ```
    """

    BufferExpressionScope = _CoreBufferExpressionScope
    """
    The type of [`BufferExpressions`][xnano.expressions.BufferExpressions].

    ```python
    import xnano
    from xnano.expressions import BufferExpressions, BufferExpressionScope

    assert isinstance(BufferExpressions, BufferExpressionScope)
    with xnano.new(width=20, height=2) as canvas:
        assert canvas.inspect(BufferExpressions.width) == 20
    ```
    """

    KeyboardExpressionScope = _CoreKeyboardExpressionScope
    """
    The type of [`Keyboard`][xnano.expressions.Keyboard].

    ```python
    import xnano
    from xnano.events import Event
    from xnano.expressions import Keyboard, KeyboardExpressionScope

    assert isinstance(Keyboard, KeyboardExpressionScope)
    with xnano.new(width=20, height=2) as canvas:
        canvas.push(Event.key_press('a'))
        canvas.step(delta_seconds=0.1)
        assert canvas.inspect(Keyboard.key) == 'a'
    ```
    """

    MouseExpressionScope = _CoreMouseExpressionScope
    """
    The type of [`Mouse`][xnano.expressions.Mouse].

    ```python
    import xnano
    from xnano.events import Event
    from xnano.expressions import Mouse, MouseExpressionScope
    from xnano.geometry import Point

    assert isinstance(Mouse, MouseExpressionScope)
    with xnano.new(width=20, height=2) as canvas:
        canvas.push(Event.mouse_event(column=4, row=1, kind='press', button='left'))
        canvas.step(delta_seconds=0.1)
        assert canvas.inspect(Mouse.position) == Point(4, 1)
    ```
    """

    ParentExpressionScope = _CoreParentExpressionScope
    """
    The type of [`Parent`][xnano.expressions.Parent].

    ```python
    import xnano
    from xnano.expressions import Parent, ParentExpressionScope

    assert isinstance(Parent, ParentExpressionScope)
    with xnano.new(width=20, height=2) as canvas:
        text = canvas.write('right', x=Parent.width - 5)
        assert text.x == 15
    ```
    """

    RootExpressionScope = _CoreRootExpressionScope
    """
    The type of [`Root`][xnano.expressions.Root].

    ```python
    import xnano
    from xnano.expressions import Root, RootExpressionScope

    assert isinstance(Root, RootExpressionScope)
    with xnano.new(width=20, height=2) as canvas:
        assert canvas.inspect(Root.width) == 20
    ```
    """

    ScrollExpressionScope = _CoreScrollExpressionScope
    """
    The type of [`Scroll`][xnano.expressions.Scroll].

    ```python
    import xnano
    from xnano.events import Event
    from xnano.expressions import Scroll, ScrollExpressionScope

    assert isinstance(Scroll, ScrollExpressionScope)
    with xnano.new(width=20, height=2) as canvas:
        canvas.push(Event.mouse_event(column=0, row=0, kind='scroll', scroll_y=3))
        canvas.step(delta_seconds=0.1)
        assert canvas.inspect(Scroll.y) == 3
    ```
    """

    X = _CoreX
    """
    The column of the buffer inside its parent, in cells.

    ```python
    import xnano
    from xnano.expressions import X

    with xnano.open(width=60, height=6) as terminal:
        terminal.write('placed by a formula', y=X % 3)
        terminal.run(quit_on='q')
    ```
    """

    Y = _CoreY
    """
    The row of the buffer inside its parent, in cells.

    ```python
    import xnano
    from xnano.expressions import Y

    with xnano.open(width=60, height=6) as terminal:
        terminal.write('placed by a formula', x=Y * 2)
        terminal.run(quit_on='q')
    ```
    """

    Width = _CoreWidth
    """
    The width of the buffer, in cells.

    ```python
    import xnano
    from xnano.expressions import ParentWidth, Width

    with xnano.open(width=60, height=6) as terminal:
        terminal.write('placed by a formula', x=(ParentWidth - Width) // 2)
        terminal.run(quit_on='q')
    ```
    """

    Height = _CoreHeight
    """
    The height of the buffer, in cells.

    ```python
    import xnano
    from xnano.expressions import Height, ParentHeight

    with xnano.open(width=60, height=6) as terminal:
        terminal.write('placed by a formula', y=ParentHeight - Height)
        terminal.run(quit_on='q')
    ```
    """

    Position = _CorePosition
    """
    The column and row of the buffer inside its parent, as a ``Point``.

    ```python
    import xnano
    from xnano.expressions import Position

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('')

        @terminal.hook(on='tick', every=0.5)
        def show(context: xnano.Context) -> None:
            label.text = f'position: {context.canvas.inspect(Position)}'

        terminal.run(quit_on='q')
    ```
    """

    Size = _CoreSize
    """
    The width and height of the buffer, as a ``Size``.

    ```python
    import xnano
    from xnano.expressions import Size

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('')

        @terminal.hook(on='tick', every=0.5)
        def show(context: xnano.Context) -> None:
            label.text = f'size: {context.canvas.inspect(Size)}'

        terminal.run(quit_on='q')
    ```
    """

    IsVisible = _CoreIsVisible
    """
    Whether the buffer is drawn.

    ```python
    import xnano
    from xnano.expressions import IsVisible

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('')

        @terminal.hook(on='tick', every=0.5)
        def show(context: xnano.Context) -> None:
            label.text = f'visible: {context.canvas.inspect(IsVisible)}'

        terminal.run(quit_on='q')
    ```
    """

    Focused = _CoreFocused
    """
    Whether the buffer has the keyboard focus.

    ```python
    import xnano
    from xnano.expressions import Focused

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('')

        @terminal.hook(on='tick', every=0.5)
        def show(context: xnano.Context) -> None:
            label.text = f'focused: {context.canvas.inspect(Focused)}'

        terminal.run(quit_on='q')
    ```
    """

    ParentWidth = _CoreParentWidth
    """
    The width of the parent the buffer is written in, in cells.

    ```python
    import xnano
    from xnano.expressions import ParentWidth, Width

    with xnano.open(width=60, height=6) as terminal:
        terminal.write('placed by a formula', x=ParentWidth - Width)
        terminal.run(quit_on='q')
    ```
    """

    ParentHeight = _CoreParentHeight
    """
    The height of the parent the buffer is written in, in cells.

    ```python
    import xnano
    from xnano.expressions import ParentHeight

    with xnano.open(width=60, height=6) as terminal:
        terminal.write('placed by a formula', y=ParentHeight - 1)
        terminal.run(quit_on='q')
    ```
    """

    ParentSize = _CoreParentSize
    """
    The width and height of the parent the buffer is written in, as a ``Size``.

    ```python
    import xnano
    from xnano.expressions import ParentSize

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('')

        @terminal.hook(on='tick', every=0.5)
        def show(context: xnano.Context) -> None:
            label.text = f'parent size: {context.canvas.inspect(ParentSize)}'

        terminal.run(quit_on='q')
    ```
    """

    TerminalWidth = _CoreDeviceWidth
    """
    The width of the terminal area the program draws on, in cells.

    It is the whole window for a canvas that takes the whole window, the region below the
    prompt for a canvas opened with a ``height``, and the size of the canvas itself when the
    canvas is not on the screen. [`Terminal.window`][xnano.terminal.Terminal.window] is the
    size of the whole window, whatever the canvas takes of it.

    Maps to [`xnano_core.DeviceWidth`][xnano_core.DeviceWidth].

    ```python
    import xnano
    from xnano.expressions import TerminalWidth

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('')

        @terminal.hook(on='tick', every=0.5)
        def show(context: xnano.Context) -> None:
            label.text = f'terminal width: {context.canvas.inspect(TerminalWidth)}'

        terminal.run(quit_on='q')
    ```
    """

    TerminalHeight = _CoreDeviceHeight
    """
    The height of the terminal area the program draws on, in cells.

    It is the whole window for a canvas that takes the whole window, the region below the
    prompt for a canvas opened with a ``height``, and the size of the canvas itself when the
    canvas is not on the screen. [`Terminal.window`][xnano.terminal.Terminal.window] is the
    size of the whole window, whatever the canvas takes of it.

    Maps to [`xnano_core.DeviceHeight`][xnano_core.DeviceHeight].

    ```python
    import xnano
    from xnano.expressions import TerminalHeight

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('')

        @terminal.hook(on='tick', every=0.5)
        def show(context: xnano.Context) -> None:
            label.text = f'terminal height: {context.canvas.inspect(TerminalHeight)}'

        terminal.run(quit_on='q')
    ```
    """

    BufferRegion = _CoreBufferRegion
    """
    The rectangle of the screen the buffer covers, as a ``Rectangle``: where it is drawn after every parent is placed.

    ```python
    import xnano
    from xnano.expressions import BufferRegion

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('')

        @terminal.hook(on='tick', every=0.5)
        def show(context: xnano.Context) -> None:
            label.text = f'region: {context.canvas.inspect(BufferRegion)}'

        terminal.run(quit_on='q')
    ```
    """

    BufferSize = _CoreBufferSize
    """
    The width and height of the canvas or renderable area at runtime, as a ``Size``.

    ```python
    import xnano
    from xnano.expressions import BufferSize

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('')

        @terminal.hook(on='tick', every=0.5)
        def show(context: xnano.Context) -> None:
            label.text = f'size: {context.canvas.inspect(BufferSize)}'

        terminal.run(quit_on='q')
    ```
    """

    ScreenPosition = _CoreScreenPosition
    """
    The column and row of the buffer on the screen, as a ``Point``.

    ```python
    import xnano
    from xnano.expressions import ScreenPosition

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('')

        @terminal.hook(on='tick', every=0.5)
        def show(context: xnano.Context) -> None:
            label.text = f'on screen at: {context.canvas.inspect(ScreenPosition)}'

        terminal.run(quit_on='q')
    ```
    """

    ScreenBounds = _CoreScreenBounds
    """
    The rectangle of the buffer on the screen, as a ``Rectangle``.

    ```python
    import xnano
    from xnano.expressions import ScreenBounds

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('')

        @terminal.hook(on='tick', every=0.5)
        def show(context: xnano.Context) -> None:
            label.text = f'bounds: {context.canvas.inspect(ScreenBounds)}'

        terminal.run(quit_on='q')
    ```
    """

    TimeElapsed = _CoreTimeElapsed
    """
    The seconds the canvas has run, on its own clock.

    ```python
    import xnano
    from xnano.expressions import ParentWidth, TimeElapsed, Width

    with xnano.open(width=60, height=6) as terminal:
        ball = terminal.write('o', y=2)
        ball.x = (ParentWidth - Width) * (TimeElapsed % 2 / 2)
        terminal.run(quit_on='q')
    ```
    """

    TimeElapsedMilliseconds = _CoreTimeElapsedMilliseconds
    """
    The milliseconds the canvas has run, on its own clock.

    ```python
    import xnano
    from xnano.expressions import TimeElapsedMilliseconds

    with xnano.open(width=60, height=6) as terminal:
        ball = terminal.write('o', y=2)
        ball.x = TimeElapsedMilliseconds // 100 % 40
        terminal.run(quit_on='q')
    ```
    """

    TimeDelta = _CoreTimeDelta
    """
    The seconds between the last frame and the one before it.

    ```python
    import xnano
    from xnano.expressions import TimeDelta

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('')

        @terminal.hook(on='tick', every=0.5)
        def show(context: xnano.Context) -> None:
            label.text = f'last frame took: {context.canvas.inspect(TimeDelta)}'

        terminal.run(quit_on='q')
    ```
    """

    TimeDeltaMilliseconds = _CoreTimeDeltaMilliseconds
    """
    The milliseconds between the last frame and the one before it.

    ```python
    import xnano
    from xnano.expressions import TimeDeltaMilliseconds

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('')

        @terminal.hook(on='tick', every=0.5)
        def show(context: xnano.Context) -> None:
            label.text = f'last frame took: {context.canvas.inspect(TimeDeltaMilliseconds)}'

        terminal.run(quit_on='q')
    ```
    """

    FPS = _CoreFPS
    """
    The current runtime's estimated frames per second, measured over recent frames.

    ```python
    import xnano
    from xnano.expressions import FPS

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('')

        @terminal.hook(on='tick', every=0.5)
        def show(context: xnano.Context) -> None:
            label.text = f'FPS: {context.canvas.inspect(FPS)}'

        terminal.run(quit_on='q')
    ```
    """

    KeyboardKey = _CoreKeyboardKey
    """
    The name of the latest key, such as ``'a'`` or ``'up'``.

    ```python
    import xnano
    from xnano.expressions import KeyboardKey

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('press a key')

        @terminal.hook(on='key')
        def show(context: xnano.Context) -> None:
            label.text = f'key: {context.canvas.inspect(KeyboardKey)}'

        terminal.run(quit_on='q')
    ```
    """

    KeyboardKind = _CoreKeyboardKind
    """
    Whether the latest key was a ``'press'``, a ``'repeat'`` or a ``'release'``.

    ```python
    import xnano
    from xnano.expressions import KeyboardKind

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('press a key')

        @terminal.hook(on='key')
        def show(context: xnano.Context) -> None:
            label.text = f'kind: {context.canvas.inspect(KeyboardKind)}'

        terminal.run(quit_on='q')
    ```
    """

    KeyboardBinding = _CoreKeyboardChord
    """
    The latest key with its modifiers, such as ``'ctrl+c'``.

    ```python
    import xnano
    from xnano.expressions import KeyboardBinding

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('press a key')

        @terminal.hook(on='key')
        def show(context: xnano.Context) -> None:
            label.text = f'binding: {context.canvas.inspect(KeyboardBinding)}'

        terminal.run(quit_on='q')
    ```
    """

    MousePosition = _CoreMousePosition
    """
    The cell of the latest mouse report, as a ``Point``.

    ```python
    import xnano
    from xnano.expressions import MousePosition

    with xnano.open(width=60, height=6, mouse='motion') as terminal:
        label = terminal.write('move or click the mouse')

        @terminal.hook(on='mouse')
        def show(context: xnano.Context) -> None:
            label.text = f'mouse at: {context.canvas.inspect(MousePosition)}'

        terminal.run(quit_on='q')
    ```
    """

    MouseButtonValue = _CoreMouseButtonValue
    """
    The button of the latest mouse report, such as ``'left'``.

    ```python
    import xnano
    from xnano.expressions import MouseButtonValue

    with xnano.open(width=60, height=6, mouse='motion') as terminal:
        label = terminal.write('move or click the mouse')

        @terminal.hook(on='mouse')
        def show(context: xnano.Context) -> None:
            label.text = f'button: {context.canvas.inspect(MouseButtonValue)}'

        terminal.run(quit_on='q')
    ```
    """

    MouseKind = _CoreMouseKind
    """
    What the latest mouse report was, such as ``'press'``, ``'drag'`` or ``'move'``.

    ```python
    import xnano
    from xnano.expressions import MouseKind

    with xnano.open(width=60, height=6, mouse='motion') as terminal:
        label = terminal.write('move or click the mouse')

        @terminal.hook(on='mouse')
        def show(context: xnano.Context) -> None:
            label.text = f'kind: {context.canvas.inspect(MouseKind)}'

        terminal.run(quit_on='q')
    ```
    """

    MouseIsDown = _CoreMouseIsDown
    """
    A condition that holds while a mouse button is held down.

    ```python
    import xnano
    from xnano.expressions import MouseIsDown

    with xnano.open(width=60, height=6, mouse=True) as terminal:
        label = terminal.write('')

        @terminal.hook(on='mouse', when=MouseIsDown)
        def react(context: xnano.Context) -> None:
            label.text = 'a button is down'

        terminal.run(quit_on='q')
    ```
    """

    PointerPosition = _CorePointerPosition
    """
    The cell the pointer was last seen over, as a ``Point``; it has no value before the pointer moves.

    ```python
    import xnano
    from xnano.expressions import PointerPosition

    with xnano.open(width=60, height=6, mouse='motion') as terminal:
        label = terminal.write('move or click the mouse')

        @terminal.hook(on='mouse')
        def show(context: xnano.Context) -> None:
            label.text = f'pointer at: {context.canvas.inspect(PointerPosition)}'

        terminal.run(quit_on='q')
    ```
    """

    ScrollX = _CoreScrollX
    """
    The sideways wheel steps of the current step: negative to the left.

    ```python
    import xnano
    from xnano.expressions import ScrollX

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('')

        @terminal.hook(on='tick', every=0.5)
        def show(context: xnano.Context) -> None:
            label.text = f'sideways steps: {context.canvas.inspect(ScrollX)}'

        terminal.run(quit_on='q')
    ```
    """

    ScrollY = _CoreScrollY
    """
    The wheel steps of the current step: negative upward.

    ```python
    import xnano
    from xnano.expressions import ScrollY

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('')

        @terminal.hook(on='tick', every=0.5)
        def show(context: xnano.Context) -> None:
            label.text = f'steps: {context.canvas.inspect(ScrollY)}'

        terminal.run(quit_on='q')
    ```
    """

    Parent = _CoreParentScope
    """
    Expressions for the parent buffer: ``Parent.width``, ``Parent.height`` and ``Parent.size``.

    ```python
    import xnano
    from xnano.expressions import Parent, Width

    with xnano.open(width=60, height=6) as terminal:
        terminal.write('placed by a formula', x=Parent.width - Width)
        terminal.run(quit_on='q')
    ```
    """

    Root = _CoreRootScope
    """
    Expressions for the root canvas's geometry and clock: ``Root.width``, ``Root.height`` and ``Root.time``.

    ```python
    import xnano
    from xnano.expressions import Root

    with xnano.open(width=60, height=6) as terminal:
        terminal.write('placed by a formula', x=Root.width // 2)
        terminal.run(quit_on='q')
    ```
    """

    BufferExpressions = _CoreBufferScope
    """
    Expressions for the current buffer: ``BufferExpressions.width``, ``BufferExpressions.height`` and its rectangle on the screen, ``BufferExpressions.region``.

    ```python
    import xnano
    from xnano.expressions import BufferExpressions

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('')

        @terminal.hook(on='tick', every=0.5)
        def show(context: xnano.Context) -> None:
            label.text = f'region: {context.canvas.inspect(BufferExpressions.region)}'

        terminal.run(quit_on='q')
    ```
    """

    Keyboard = _CoreKeyboardScope
    """
    Expressions for the latest key: ``Keyboard.key``, ``Keyboard.kind`` and ``Keyboard.chord`` (the key with its modifiers).

    ```python
    import xnano
    from xnano.expressions import Keyboard

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('press a key')

        @terminal.hook(on='key')
        def show(context: xnano.Context) -> None:
            label.text = f'binding: {context.canvas.inspect(Keyboard.chord)}'

        terminal.run(quit_on='q')
    ```
    """

    Mouse = _CoreMouseScope
    """
    Expressions for the latest mouse report: ``Mouse.position``, ``Mouse.button``, ``Mouse.kind`` and ``Mouse.is_down``.

    ```python
    import xnano
    from xnano.expressions import Mouse

    with xnano.open(width=60, height=6, mouse='motion') as terminal:
        label = terminal.write('move or click the mouse')

        @terminal.hook(on='mouse')
        def show(context: xnano.Context) -> None:
            label.text = f'mouse at: {context.canvas.inspect(Mouse.position)}'

        terminal.run(quit_on='q')
    ```
    """

    Scroll = _CoreScrollScope
    """
    Expressions for the wheel steps of the current step: ``Scroll.x`` and ``Scroll.y``.

    ```python
    import xnano
    from xnano.expressions import Scroll

    with xnano.open(width=60, height=6) as terminal:
        label = terminal.write('')

        @terminal.hook(on='tick', every=0.5)
        def show(context: xnano.Context) -> None:
            label.text = f'steps: {context.canvas.inspect(Scroll.y)}'

        terminal.run(quit_on='q')
    ```
    """

_CORE_NAMES: Final[dict[str, str]] = {
    'BufferExpressionScope': 'BufferExpressionScope',
    'BufferExpressions': 'BufferScope',
    'BufferRegion': 'BufferRegion',
    'BufferSize': 'BufferSize',
    'Expression': 'Expression',
    'FPS': 'FPS',
    'Focused': 'Focused',
    'Height': 'Height',
    'IsVisible': 'IsVisible',
    'Keyboard': 'KeyboardScope',
    'KeyboardBinding': 'KeyboardChord',
    'KeyboardExpressionScope': 'KeyboardExpressionScope',
    'KeyboardKey': 'KeyboardKey',
    'KeyboardKind': 'KeyboardKind',
    'Mouse': 'MouseScope',
    'MouseButtonValue': 'MouseButtonValue',
    'MouseExpressionScope': 'MouseExpressionScope',
    'MouseIsDown': 'MouseIsDown',
    'MouseKind': 'MouseKind',
    'MousePosition': 'MousePosition',
    'NumericValue': 'NumericValue',
    'Parent': 'ParentScope',
    'ParentExpressionScope': 'ParentExpressionScope',
    'ParentHeight': 'ParentHeight',
    'ParentSize': 'ParentSize',
    'ParentWidth': 'ParentWidth',
    'PointerPosition': 'PointerPosition',
    'Position': 'Position',
    'Root': 'RootScope',
    'RootExpressionScope': 'RootExpressionScope',
    'ScreenBounds': 'ScreenBounds',
    'ScreenPosition': 'ScreenPosition',
    'Scroll': 'ScrollScope',
    'ScrollExpressionScope': 'ScrollExpressionScope',
    'ScrollX': 'ScrollX',
    'ScrollY': 'ScrollY',
    'Size': 'Size',
    'TerminalHeight': 'DeviceHeight',
    'TerminalWidth': 'DeviceWidth',
    'TimeDelta': 'TimeDelta',
    'TimeDeltaMilliseconds': 'TimeDeltaMilliseconds',
    'TimeElapsed': 'TimeElapsed',
    'TimeElapsedMilliseconds': 'TimeElapsedMilliseconds',
    'Value': 'Value',
    'Width': 'Width',
    'X': 'X',
    'Y': 'Y',
}
"""The name each expression has in ``xnano_core``, by the name it has here."""

__all__ = [
    'BufferExpressionScope',
    'BufferExpressions',
    'BufferRegion',
    'BufferSize',
    'Expression',
    'FPS',
    'Focused',
    'Height',
    'IsVisible',
    'Keyboard',
    'KeyboardBinding',
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
    'ScreenBounds',
    'ScreenPosition',
    'Scroll',
    'ScrollExpressionScope',
    'ScrollX',
    'ScrollY',
    'Size',
    'TerminalHeight',
    'TerminalWidth',
    'TimeDelta',
    'TimeDeltaMilliseconds',
    'TimeElapsed',
    'TimeElapsedMilliseconds',
    'Value',
    'Width',
    'X',
    'Y',
]


def __getattr__(name: str) -> object:
    """Import an expression from ``xnano_core`` the first time it is read, then keep it."""
    if name == 'KeyboardChord':
        import warnings

        warnings.warn(
            'xnano.expressions.KeyboardChord is deprecated and will be removed in xnano '
            '2.1.0. Use xnano.expressions.KeyboardBinding instead.',
            DeprecationWarning,
            stacklevel=2,
        )
        name = 'KeyboardBinding'
    core_name = _CORE_NAMES.get(name)
    if core_name is None:
        raise AttributeError(
            f'xnano.expressions has no expression called {name!r}. The expressions are '
            f'{", ".join(sorted(_CORE_NAMES))}.'
        )
    import xnano_core

    value = getattr(xnano_core, core_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """The public names of the module, including the ones that are imported when first read."""
    return sorted(__all__)
