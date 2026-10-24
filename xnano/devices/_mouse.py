"""
xnano.devices._mouse

The mouse of a terminal: the pointer event being handled, the buttons held, the wheel, and the
program's own presses, clicks, drags and turns of the wheel.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Literal, cast

import xnano_core as _core
from xnano.devices._input import _cell_pair, _random_cell
from xnano.errors import TerminalClosedError

if TYPE_CHECKING:
    from types import TracebackType

    from typing_extensions import Self

    from xnano.canvas import Canvas
    from xnano.hooks._context import Context
    from xnano.layout._placement import Placement

__all__ = ['HeldButton', 'Mouse', 'Scroll']

_HELD_NAMES: dict[str, _core.MouseButton] = {
    'mouse_left': 'left',
    'mouse_right': 'right',
    'mouse_middle': 'middle',
}


def _check_button(button: object) -> _core.MouseButton:
    if button not in ('left', 'right', 'middle'):
        raise ValueError(
            f"A mouse button is 'left', 'right' or 'middle', but got {button!r}."
        )
    return cast('_core.MouseButton', button)


class Scroll:
    """
    The mouse wheel: the steps of the wheel report being handled, and the program's own turns.

    Get it from ``mouse.scroll``. ``x`` and ``y`` are signed steps that grow right and down,
    so scrolling up is ``y == -1``; both are ``0`` unless the event being handled is a wheel
    report.

    Attributes:
        x: Horizontal steps, positive to the right.
        y: Vertical steps, positive downward.
        event: The wheel [`MouseEvent`][xnano_core.MouseEvent] being handled, or ``None``.
    """

    __slots__ = ('_canvas', '_event', '_owner')

    def __init__(
        self,
        canvas: Canvas[object, object],
        event: _core.Event | None,
        owner: Placement[object, object] | Canvas[object, object] | None,
    ) -> None:
        """Create a view of the wheel. Use ``mouse.scroll`` instead of calling this."""
        self._canvas = canvas
        self._event = event
        self._owner = owner

    @property
    def event(self) -> _core.MouseEvent | None:
        """The wheel event being handled, or ``None`` for any other event."""
        event = self._event
        if event is None:
            return None
        mouse = event.mouse
        if mouse is None or mouse.kind != 'scroll':
            return None
        return mouse

    @property
    def x(self) -> int:
        """Horizontal steps, positive to the right; ``0`` unless the event is a wheel report."""
        mouse = self.event
        return 0 if mouse is None else mouse.scroll_x

    @property
    def y(self) -> int:
        """Vertical steps, positive downward; ``0`` unless the event is a wheel report."""
        mouse = self.event
        return 0 if mouse is None else mouse.scroll_y

    def turn(self, *, x: int = 0, y: int = 0) -> None:
        """
        Turn the mouse wheel on the canvas, as if the person had.

        The wheel turns at the cell the pointer was last seen at; a pointer the program moved
        counts as seen there at once.

        Args:
            x: Horizontal steps, positive to the right.
            y: Vertical steps, positive downward: ``y=-1`` scrolls up one step.

        Raises:
            TypeError: A number of steps is not a whole number.
            ValueError: A number of steps is outside the range a wheel report carries.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=4) as canvas:
                turned = []

                @canvas.hook(on='scroll')
                def listen(context: xnano.Context) -> None:
                    turned.append(context.mouse.scroll.y)

                canvas.mouse.scroll.turn(y=-2)
                canvas.deliver_events()
                assert turned == [-2]
            ```
        """
        steps_x, steps_y = _cell_pair(
            (x, y), 'scroll.turn', description='steps of the wheel, such as y=1'
        )
        canvas = self._canvas
        state = canvas._input_state
        cell = None if state is None else state.pointer_cell
        pushed = canvas._pushed_pointer
        if (
            pushed is not None
            and pushed[1] == cell
            and pushed[2] == canvas._time_source.frame
        ):
            cell = pushed[0]
        column, row = cell if cell is not None else (0, 0)
        canvas.push(
            _core.Event.mouse_event(
                column=column, row=row, kind='scroll', scroll_x=steps_x, scroll_y=steps_y
            )
        )

    def random(self) -> tuple[int, int]:
        """
        Turn the mouse wheel a random way at a random cell of this hook's canvas or placement.

        The wheel turns one to three steps up, down, left or right, at a screen cell inside the
        cells the hook's target covers on the screen (the whole canvas outside a hook).
        ``random.seed(...)`` repeats the turns.

        Returns:
            The ``(x, y)`` steps that were turned, such as ``(0, -2)`` for two steps up.

        Raises:
            TerminalError: The canvas or placement covers no cell on the screen.
        """
        column, row = _random_cell(self._canvas, self._owner)
        amount = random.randint(1, 3)
        steps_x, steps_y = random.choice(
            ((0, -amount), (0, amount), (-amount, 0), (amount, 0))
        )
        self._canvas.push(
            _core.Event.mouse_event(
                column=column, row=row, kind='scroll', scroll_x=steps_x, scroll_y=steps_y
            )
        )
        return steps_x, steps_y


class HeldButton:
    """
    A mouse button the program holds down: move it to drag, and let go with ``release``.

    [`Mouse.press`][xnano.devices.Mouse.press] returns one. In a ``with`` block the button is
    released when the block ends, so the block is a drag. It moves like a placement and the
    cursor do: ``move`` by cells along each axis, or ``up``, ``down``, ``left`` and ``right``.

    Attributes:
        button: ``'left'``, ``'right'`` or ``'middle'``.
        is_released: Whether the button was let go.

    Examples:
        ```python
        import xnano

        with xnano.new(width=20, height=4) as canvas:
            seen = []
            canvas.hook(lambda context: seen.append(context.mouse.kind), on='mouse')
            with canvas.mouse.press('left', x=2, y=1) as button:
                button.right(3)
            canvas.deliver_events()
            assert seen == ['press', 'drag', 'release']
            assert canvas.mouse.pointer == (5, 1)
        ```
    """

    __slots__ = ('_mouse', 'button', 'is_released')

    def __init__(self, mouse: Mouse, button: _core.MouseButton) -> None:
        """Hold a button. Use ``mouse.press`` instead of calling this."""
        self._mouse = mouse
        self.button: _core.MouseButton = button
        self.is_released = False

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.release()

    def move(self, x: int = 0, y: int = 0) -> Self:
        """
        Drag the held button by a number of cells along each axis.

        Args:
            x: Cells to the right; negative moves left.
            y: Cells down; negative moves up.

        Returns:
            The held button, so moves can be chained.
        """
        self._mouse.move(x, y)
        return self

    def up(self, count: int = 1) -> Self:
        """Drag the held button up by ``count`` rows."""
        return self.move(0, -count)

    def down(self, count: int = 1) -> Self:
        """Drag the held button down by ``count`` rows."""
        return self.move(0, count)

    def left(self, count: int = 1) -> Self:
        """Drag the held button left by ``count`` columns."""
        return self.move(-count, 0)

    def right(self, count: int = 1) -> Self:
        """Drag the held button right by ``count`` columns."""
        return self.move(count, 0)

    def release(self) -> None:
        """Let go of the button where the pointer is. Releasing twice does nothing."""
        if self.is_released:
            return
        self.is_released = True
        self._mouse.release(self.button)


class Mouse:
    """
    The mouse of a terminal: the pointer event being handled, the buttons held, and the wheel.

    Get it from [`Canvas.mouse`][xnano.canvas.Canvas.mouse], or from ``context.mouse`` inside
    a hook. In a hook, ``position`` and ``kind`` describe the pointer event being handled, and
    are ``None`` for any other event (a wheel report is ``scroll``'s). ``button`` is the button
    of that event, and otherwise the button held right now, so it stays ``'left'`` from the
    press of the left button until its release. ``pointer`` and ``held_buttons`` answer for
    right now, from any thread. ``press``, ``click``, ``move``
    and ``scroll.turn`` are the program's own hands, at screen cells: the canvas hears them like
    a person's mouse.

    The pointer moves like the cursor and a placement: assign ``pointer`` to put it at a cell,
    or ``move`` it by cells; with a button held, a move is a drag.

    Attributes:
        position: The cell of the event being handled, or ``None``.
        button: The button of the event being handled, else the button held right now:
            ``'left'``, ``'right'`` or ``'middle'``, or ``None``.
        kind: ``'press'``, ``'release'``, ``'drag'`` or ``'move'``, or ``None``.
        event: The [`MouseEvent`][xnano_core.MouseEvent] being handled, or ``None`` for any
            other event and for the wheel.
        is_down: Whether any mouse button is held right now.
        held_buttons: The buttons held right now.
        pointer: The ``(x, y)`` cell the pointer was last seen at, or ``None`` before it moved.
        scroll: The mouse wheel; see [`Scroll`][xnano.devices.Scroll].

    Examples:
        ```python
        import xnano

        with xnano.new(width=20, height=6) as canvas:
            button = canvas.screen.write('Go', x=5, y=2, border='plain')
            clicked = []

            @button.hook(on='mouse')
            def listen(context: xnano.Context) -> None:
                if context.mouse.kind == 'press':
                    clicked.append(tuple(context.mouse.position))

            canvas.mouse.click(x=6, y=3)
            canvas.deliver_events()
            assert clicked == [(6, 3)]
        ```
    """

    __slots__ = ('_canvas', '_context', '_event', '_owner')

    def __init__(
        self,
        canvas: Canvas[object, object],
        event: _core.Event | None = None,
        owner: Placement[object, object] | Canvas[object, object] | None = None,
        context: Context[object, object] | None = None,
    ) -> None:
        """
        Create a view of the mouse. Use ``canvas.mouse`` or ``context.mouse`` instead.

        Args:
            canvas: The root canvas the mouse belongs to.
            event: The event being handled, or ``None`` outside a hook.
            owner: The placement or canvas a hook is attached to, whose cells ``random`` stays
                inside; ``None`` for the whole canvas.
            context: The hook's context, which notes what a component reads; ``None`` outside
                a hook.
        """
        self._canvas = canvas
        self._event = event
        self._owner = owner
        self._context = context

    def __repr__(self) -> str:
        kind = self.kind
        return (
            'Mouse()'
            if kind is None
            else f'Mouse(kind={kind!r}, position={self.position!r})'
        )

    # -- the pointer event being handled -------------------------------------------------

    @property
    def event(self) -> _core.MouseEvent | None:
        """The mouse event being handled, or ``None`` for any other event and for the wheel."""
        event = self._event
        if event is None:
            return None
        mouse = event.mouse
        if mouse is None or mouse.kind == 'scroll':
            return None
        return mouse

    @property
    def position(self) -> _core.Point | None:
        """The cell of the event, or ``None``."""
        mouse = self.event
        return None if mouse is None else mouse.position

    @property
    def button(self) -> _core.MouseButton | None:
        """
        The button of the pointer event being handled, else the button held right now.

        A press, a release and a drag name their own button. For any other event, and outside
        a hook, it is the button held down: ``'left'``, ``'right'`` or ``'middle'``, the first
        of them in that order when several are held, or ``None`` when none is.
        """
        mouse = self.event
        if mouse is not None and mouse.button is not None:
            return mouse.button
        held = self.held_buttons
        return next((button for button in _HELD_NAMES.values() if button in held), None)

    @property
    def kind(self) -> Literal['press', 'release', 'drag', 'move'] | None:
        """``'press'``, ``'release'``, ``'drag'`` or ``'move'``, or ``None``."""
        mouse = self.event
        return (
            None
            if mouse is None
            else cast("Literal['press', 'release', 'drag', 'move']", mouse.kind)
        )

    @property
    def scroll(self) -> Scroll:
        """The mouse wheel: the steps of the wheel report being handled, and turning it."""
        context = self._context
        if context is not None:
            context._read('scroll')
        return Scroll(self._canvas, self._event, self._owner)

    # -- what is held down right now -----------------------------------------------------

    def _state(self) -> _core.InputState | None:
        context = self._context
        if context is not None:
            context._read_time()
        return self._canvas._input_state

    @property
    def is_down(self) -> bool:
        """Whether any mouse button is held right now."""
        state = self._state()
        return False if state is None else state.is_mouse_down

    @property
    def held_buttons(self) -> frozenset[_core.MouseButton]:
        """The buttons held right now: ``'left'``, ``'right'`` and ``'middle'``."""
        state = self._state()
        if state is None:
            return frozenset()
        return frozenset(
            _HELD_NAMES[name] for name in state.pressed_keys if name in _HELD_NAMES
        )

    @property
    def pointer(self) -> tuple[int, int] | None:
        """
        The ``(x, y)`` cell the pointer was last seen at, or ``None`` before it moved.

        ``x`` grows to the right and ``y`` down. Assign a cell to move the pointer there, as if
        the person had; with a button held it drags there.
        """
        state = self._state()
        if state is None:
            raise TerminalClosedError(
                'The canvas has no input yet, because it is not attached to a running loop.'
            )
        pushed = self._canvas._pushed_pointer
        cell = state.pointer_cell
        if pushed is not None and pushed[1] == cell:
            return pushed[0]
        return cell

    @pointer.setter
    def pointer(self, cell: tuple[int, int]) -> None:
        column, row = _cell_pair(tuple(cell), 'mouse.pointer')
        self._send('move', column, row)

    # -- the program's own mouse ---------------------------------------------------------

    def _here(self, x: int | None, y: int | None, name: str) -> tuple[int, int]:
        """The cell an action happens at: the one given, or where the pointer is."""
        if x is None or y is None:
            state = self._canvas._input_state
            seen = None if state is None else self.pointer
            here = seen if seen is not None else (0, 0)
            x = here[0] if x is None else x
            y = here[1] if y is None else y
        return _cell_pair((x, y), name)

    def _send(
        self,
        kind: _core.MouseEventKind,
        column: int,
        row: int,
        button: _core.MouseButton | None = None,
    ) -> None:
        canvas = self._canvas
        held = canvas._program_held_buttons
        if kind == 'move':
            # The program's own presses count before they are delivered.
            down = self.held_buttons | held
            if down:
                # A pointer that moves with a button down is dragging it.
                kind = 'drag'
                button = sorted(down)[0]
        elif kind == 'press' and button is not None:
            held.add(button)
        elif kind == 'release' and button is not None:
            held.discard(button)
        state = canvas._input_state
        seen = None if state is None else state.pointer_cell
        canvas._pushed_pointer = ((column, row), seen, canvas._time_source.frame)
        if button is None:
            canvas.push(_core.Event.mouse_event(column=column, row=row, kind=kind))
        else:
            canvas.push(
                _core.Event.mouse_event(column=column, row=row, kind=kind, button=button)
            )

    def press(
        self,
        button: _core.MouseButton = 'left',
        *,
        x: int | None = None,
        y: int | None = None,
    ) -> HeldButton:
        """
        Press a mouse button and hold it, as if the person had.

        The button stays down until it is released: call ``release`` on what this returns, or
        press in a ``with`` block, which releases it when the block ends. Moving the pointer
        meanwhile drags the button. For a press and a release at once, use
        [`click`][xnano.devices.Mouse.click].

        Args:
            button: ``'left'``, ``'right'`` or ``'middle'``.
            x: The column to press at; where the pointer is when left out.
            y: The row to press at; where the pointer is when left out.

        Returns:
            The [`HeldButton`][xnano.devices.HeldButton].

        Raises:
            ValueError: ``button`` is not a mouse button, or a cell number is out of range.
            TypeError: A cell number is not a whole number.
        """
        name = _check_button(button)
        column, row = self._here(x, y, 'mouse.press')
        self._send('press', column, row, name)
        return HeldButton(self, name)

    def release(
        self,
        button: _core.MouseButton = 'left',
        *,
        x: int | None = None,
        y: int | None = None,
    ) -> None:
        """
        Let go of a mouse button, as if the person had.

        Args:
            button: ``'left'``, ``'right'`` or ``'middle'``.
            x: The column to release at; where the pointer is when left out.
            y: The row to release at; where the pointer is when left out.

        Raises:
            ValueError: ``button`` is not a mouse button, or a cell number is out of range.
        """
        name = _check_button(button)
        column, row = self._here(x, y, 'mouse.release')
        self._send('release', column, row, name)

    def click(
        self,
        button: _core.MouseButton = 'left',
        *,
        x: int | None = None,
        y: int | None = None,
    ) -> None:
        """
        Press and release a mouse button at one cell, as if the person had clicked.

        Args:
            button: ``'left'``, ``'right'`` or ``'middle'``.
            x: The column to click; where the pointer is when left out.
            y: The row to click; where the pointer is when left out.

        Raises:
            ValueError: ``button`` is not a mouse button, or a cell number is out of range.
        """
        self.press(button, x=x, y=y).release()

    def move(self, x: int = 0, y: int = 0) -> None:
        """
        Move the pointer by a number of cells along each axis; with a button held, a drag.

        Args:
            x: Cells to the right; negative moves left.
            y: Cells down; negative moves up.
        """
        column, row = self._here(None, None, 'mouse.move')
        target = _cell_pair((column + x, row + y), 'mouse.move')
        self._send('move', *target)

    def random(self, kind: Literal['click', 'drag', 'move'] = 'click') -> tuple[int, int]:
        """
        Click, drag or move at a random cell of this hook's canvas or placement.

        Cells are screen cells inside the cells the hook's target covers on the screen (the
        whole canvas outside a hook). The left button is used. ``random.seed(...)`` repeats the
        cells.

        Args:
            kind: ``'click'`` presses and releases at one cell, ``'drag'`` presses at one cell,
                drags to another and releases there, and ``'move'`` moves the pointer to one.

        Returns:
            The ``(x, y)`` cell where it ended: the clicked cell, the cell a drag was released
            at, or the cell the pointer moved to.

        Raises:
            ValueError: ``kind`` is not ``'click'``, ``'drag'`` or ``'move'``.
            TerminalError: The canvas or placement covers no cell on the screen.

        Examples:
            ```python
            import random

            import xnano

            with xnano.new(width=20, height=6) as canvas:
                button = canvas.screen.write('Go', x=5, y=2, border='plain')
                clicked = []
                chosen = []

                @button.hook(on='mouse')
                def listen(context: xnano.Context) -> None:
                    if context.mouse.kind == 'press':
                        clicked.append(tuple(context.mouse.position))

                @button.hook(on='tick', after=0.1)
                def click_somewhere(context: xnano.Context) -> None:
                    chosen.append(context.mouse.random())

                random.seed(3)
                canvas.clock.step(delta_seconds=0.2)
                canvas.deliver_events()
                assert clicked == chosen
                assert 5 <= chosen[0][0] < 5 + button.width
            ```
        """
        if kind not in ('click', 'drag', 'move'):
            raise ValueError(
                f"mouse.random takes the kind 'click', 'drag' or 'move', but got {kind!r}. "
                f"Use mouse.random() for a click, or mouse.random('drag')."
            )
        column, row = _random_cell(self._canvas, self._owner)
        if kind == 'move':
            self._send('move', column, row)
            return column, row
        start_column, start_row = column, row
        if kind == 'drag':
            column, row = _random_cell(self._canvas, self._owner)
        steps: list[tuple[_core.MouseEventKind, int, int]] = [
            ('press', start_column, start_row)
        ]
        if kind == 'drag':
            steps.append(('drag', column, row))
        steps.append(('release', column, row))
        for event_kind, event_column, event_row in steps:
            self._canvas.push(
                _core.Event.mouse_event(
                    column=event_column, row=event_row, kind=event_kind, button='left'
                )
            )
        return column, row
