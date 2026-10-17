"""
xnano.input

What a hook reads from the keyboard, the mouse, the scroll wheel and the clipboard, and which
keys and mouse buttons are held down right now, for programs that poll instead of listening.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal, cast

import xnano_core as _core
from xnano.errors import TerminalClosedError

if TYPE_CHECKING:
    from xnano.canvas import Canvas

__all__ = [
    'ClipboardInput',
    'Input',
    'KeyboardInput',
    'MouseInput',
    'ScrollInput',
]

# How long after the last key repeat a key still counts as held, on a terminal that does not
# report key releases. It has to outlast the operating system's pause before a held key repeats.
_ESTIMATED_HOLD_SECONDS = 0.45

KeyNames = str | Sequence[str]
"""
One key or mouse button name, or several that count the same, such as ``('a', 'left')``.

The mouse buttons are called ``'mouse_left'``, ``'mouse_right'`` and ``'mouse_middle'``; see
[`HeldMouseButtonName`][xnano.types.HeldMouseButtonName].
"""


# The range of a cell number or a number of wheel steps that an event can carry.
_MINIMUM_CELL_NUMBER = -(2**31)
_MAXIMUM_CELL_NUMBER = 2**31 - 1

_MOUSE_BUTTON_NAMES = ('mouse_left', 'mouse_right', 'mouse_middle')


_MODIFIER_NAMES = ('shift', 'ctrl', 'control', 'alt', 'super', 'meta', 'hyper')


def _names(keys: KeyNames) -> tuple[str, ...]:
    """The names in ``keys`` as the runtime spells them, each checked to be one key or button."""
    import difflib

    from xnano._when import _KEY_NAMES, normalize_chord

    if isinstance(keys, str):
        names: tuple[object, ...] = (keys,)
    elif isinstance(keys, Sequence):
        names = tuple(keys)
    else:
        names = (keys,)
    spelled: list[str] = []
    for name in names:
        if not isinstance(name, str):
            raise TypeError(
                f"Held input takes a key name such as 'space', or several such as "
                f"('a', 'left'), but got {keys!r}. Pass the names as text."
            )
        if name in _MOUSE_BUTTON_NAMES:
            spelled.append(name)
            continue
        if name.lower() in _MODIFIER_NAMES or (name != '+' and '+' in name):
            raise ValueError(
                f'{name!r} is a modifier or a chord, but held input is checked one key or '
                f"mouse button at a time, such as is_down('s'). A chord belongs in "
                f"hook(keys='ctrl+s')."
            )
        try:
            normalize_chord(name)
        except ValueError:
            close = difflib.get_close_matches(
                name.lower(), (*_KEY_NAMES, *_MOUSE_BUTTON_NAMES), n=3
            )
            hint = (
                f' Did you mean {" or ".join(repr(match) for match in close)}?'
                if close
                else ''
            )
            raise ValueError(
                f'{name!r} is not a key or a mouse button.{hint} Use one key name from '
                f"xnano.types.KeyName such as 'q', 'space' or 'page_up', or one of "
                f'{", ".join(repr(button) for button in _MOUSE_BUTTON_NAMES)}.'
            ) from None
        key = _core.Event.key_press(name).key
        assert key is not None
        spelled.append(key.key)
    return tuple(spelled)


class Input:
    """
    The keys held down right now.

    A hook hears each key press once. A game wants the opposite: ask every step which keys
    are down. Get one from [`Canvas.input`][xnano.canvas.Canvas.input] and read it anywhere,
    from any thread: inside a hook, in a ``hook(on='tick')`` update, or in your own loop.

    A terminal that reports key releases (kitty, ghostty and wezterm, when the canvas is
    opened with ``keyboard='release_events'``) tells exactly when a key is let go. Any other
    terminal only sends repeats while a key is held, so a key counts as held for a short time
    after its last repeat.

    The held mouse buttons are in the same vocabulary, named ``'mouse_left'``,
    ``'mouse_right'`` and ``'mouse_middle'``, so ``canvas.input.is_down('mouse_left')`` asks
    whether the left button is held.

    Attributes:
        held_keys: The names of the keys and mouse buttons held down right now.
        pointer: The ``(x, y)`` cell the pointer was last seen at, with ``x`` growing to the
            right and ``y`` down, or ``None`` before it has moved. It is the cell that
            ``context.mouse.position`` gives as a point.

    Examples:
        ```python
        import xnano

        with xnano.new(width=20, height=3) as canvas:
            hero = canvas.write('@')

            @canvas.hook(on='tick', every=1 / 30)
            def walk(context: xnano.Context) -> None:
                step_x, step_y = canvas.input.direction()
                hero.x += step_x
                hero.y += step_y

            canvas.step()
        ```
    """

    def __init__(self, canvas: Canvas[object, object]) -> None:
        """
        Create the canvas's input. Use ``canvas.input`` instead of calling this.

        Args:
            canvas: The canvas the input belongs to.
        """
        self._canvas = canvas
        self._state.estimate_holds(timeout_seconds=_ESTIMATED_HOLD_SECONDS)

    @property
    def _state(self) -> _core.InputState:
        """The input of the canvas's current runtime, which any thread may read."""
        state = self._canvas._input_state
        if state is None:
            raise TerminalClosedError(
                'The canvas has no input yet, because it is not attached to a running loop.'
            )
        return state

    @property
    def held_keys(self) -> frozenset[str]:
        """The names of the keys and mouse buttons held down right now."""
        return self._state.pressed_keys | self._state.estimated_pressed_keys

    def is_down(self, keys: KeyNames) -> bool:
        """
        Whether any of the keys or mouse buttons is held down.

        Args:
            keys: One key name such as ``'space'``, or several such as ``('a', 'left')``. A
                mouse button is ``'mouse_left'``, ``'mouse_right'`` or ``'mouse_middle'``.
                A key is spelled as in [`KeyName`][xnano.types.KeyName]; a chord such as
                ``'ctrl+s'`` or a modifier alone is not held input.

        Raises:
            TypeError: A name is not text.
            ValueError: A name is not a key or a mouse button, or is a chord or a modifier.
        """
        held = self.held_keys
        return any(name in held for name in _names(keys))

    def axis(self, negative: KeyNames, positive: KeyNames) -> int:
        """
        ``-1``, ``0`` or ``1`` from a pair of keys: the negative one, neither or both, the
        positive one.

        Args:
            negative: The key or keys that push toward ``-1``.
            positive: The key or keys that push toward ``1``.

        Raises:
            TypeError: A name is not text.
            ValueError: A name is not a key or a mouse button, or is a chord or a modifier.
        """
        return int(self.is_down(positive)) - int(self.is_down(negative))

    def direction(
        self,
        *,
        left: KeyNames = ('a', 'left'),
        right: KeyNames = ('d', 'right'),
        up: KeyNames = ('w', 'up'),
        down: KeyNames = ('s', 'down'),
    ) -> tuple[int, int]:
        """
        The way the arrow keys or ``wasd`` point, as ``(step_x, step_y)``.

        Each step is ``-1``, ``0`` or ``1``; ``y`` grows downward, like the screen.

        Args:
            left: The key or keys that mean left.
            right: The key or keys that mean right.
            up: The key or keys that mean up.
            down: The key or keys that mean down.

        Raises:
            TypeError: A name is not text.
            ValueError: A name is not a key or a mouse button, or is a chord or a modifier.
        """
        return self.axis(left, right), self.axis(up, down)

    @property
    def pointer(self) -> tuple[int, int] | None:
        """
        The ``(x, y)`` cell the pointer was last seen at, or ``None`` before it moved.

        ``x`` grows to the right and ``y`` down. ``context.mouse.position`` gives the same cell
        as a point.
        """
        return self._state.pointer_cell


def _modifier_text(key: _core.KeyEvent) -> str:
    order = (
        ('control', 'ctrl'),
        ('alt', 'alt'),
        ('shift', 'shift'),
        ('super', 'super'),
        ('meta', 'meta'),
        ('hyper', 'hyper'),
    )
    parts = [text for name, text in order if name in key.modifiers]
    parts.append(key.key)
    return '+'.join(parts)


class KeyboardInput:
    """
    The key of the current event, as properties of a hook's context.

    Get one from ``context.keyboard``. It is always there: ``key`` is ``None`` unless the event
    the hook is handling is a key. ``push`` delivers a key to the canvas, so a hook can press a
    key for the program.

    Attributes:
        key: The name of the key, such as ``'q'`` or ``'enter'``, or ``None``.
        kind: ``'press'``, ``'repeat'`` or ``'release'``, or ``None``.
        modifiers: The modifier keys held with it.
        text: The text the key types, or ``None`` for control keys and chords.
        chord: The key with its modifiers as one text such as ``'ctrl+s'``, or ``None``.

    Examples:
        ```python
        import xnano

        with xnano.new(width=8, height=1) as canvas:
            heard = []

            @canvas.hook(on='key')
            def listen(context: xnano.Context) -> None:
                heard.append(context.keyboard.key)

            @canvas.hook(on='tick', after=0.1)
            def press_for_the_program(context: xnano.Context) -> None:
                context.keyboard.push('q')

            canvas.step(delta_seconds=0.2)
            canvas.deliver_events()
            assert heard == ['q']
        ```
    """

    __slots__ = ('_canvas', '_event')

    def __init__(self, canvas: Canvas[object, object], event: _core.Event | None) -> None:
        """
        Create the key view of an event. Use ``context.keyboard`` instead of calling this.

        Args:
            canvas: The canvas the event happened in.
            event: The event being handled, or ``None``.
        """
        self._canvas = canvas
        self._event = event

    def get(self) -> _core.KeyEvent | None:
        """The key event being handled, or ``None`` when the event is not a key."""
        event = self._event
        return event.key if event is not None else None

    @property
    def key(self) -> str | None:
        """The name of the key, such as ``'q'`` or ``'enter'``, or ``None``."""
        key = self.get()
        return None if key is None else key.key

    @property
    def kind(self) -> Literal['press', 'repeat', 'release'] | None:
        """``'press'``, ``'repeat'`` or ``'release'``, or ``None`` for any other event."""
        key = self.get()
        return None if key is None else key.kind

    @property
    def modifiers(self) -> frozenset[str]:
        """The modifier keys held with the key; empty for any other event."""
        key = self.get()
        return frozenset() if key is None else frozenset(key.modifiers)

    @property
    def text(self) -> str | None:
        """The text the key types, or ``None`` for control keys, chords and other events."""
        key = self.get()
        return None if key is None else key.text

    @property
    def chord(self) -> str | None:
        """The key with its modifiers as one text such as ``'ctrl+s'``, or ``None``."""
        key = self.get()
        return None if key is None else _modifier_text(key)

    def push(self, value: str | _core.KeyEvent) -> None:
        """
        Press a key on the canvas, as if it had been typed.

        The canvas's hooks hear it at its next step, whatever the input gates say.

        Args:
            value: A key name or chord such as ``'q'`` or ``'ctrl+s'``, or a
                [`KeyEvent`][xnano_core.KeyEvent].

        Raises:
            TypeError: ``value`` is neither text nor a key event.
            ValueError: ``value`` is text that does not name a key. The message suggests the
                closest key names.
        """
        if isinstance(value, _core.KeyEvent):
            self._canvas.push(
                _core.Event.key_press(_modifier_text(value), kind=value.kind)
            )
        else:
            if not isinstance(value, str):
                raise TypeError(
                    f"keyboard.push takes a key name such as 'q' or 'ctrl+s', or a KeyEvent, "
                    f'but got {value!r}. Pass the key as text: keyboard.push("q").'
                )
            from xnano._when import normalize_chord

            normalize_chord(value)
            self._canvas.push(_core.Event.key_press(value))


def _cell_pair(
    value: tuple[object, ...],
    name: str,
    *,
    description: str = 'a cell on the screen, such as (3, 1)',
) -> tuple[int, int]:
    """Return ``value`` when it is a pair of whole numbers in the supported range."""
    if len(value) != 2 or any(
        isinstance(item, bool) or not isinstance(item, int) for item in value
    ):
        raise TypeError(
            f'{name} takes a pair of whole numbers, {description}, but got {value!r}.'
        )
    pair = cast('tuple[int, int]', value)
    if any(not _MINIMUM_CELL_NUMBER <= item <= _MAXIMUM_CELL_NUMBER for item in pair):
        raise ValueError(
            f'{name} takes whole numbers from {_MINIMUM_CELL_NUMBER} to '
            f'{_MAXIMUM_CELL_NUMBER}, but got {value!r}. Pass {description}.'
        )
    return pair


class MouseInput:
    """
    The mouse button or movement of the current event, as properties of a hook's context.

    Get one from ``context.mouse``. It is always there: ``position`` is ``None`` unless the
    event the hook is handling is a mouse press, release, drag or move. A mouse wheel report is
    not a mouse event here; [`ScrollInput`][xnano.input.ScrollInput] owns it.

    Attributes:
        position: The cell of the event, or ``None``.
        button: ``'left'``, ``'right'`` or ``'middle'``, or ``None``.
        kind: ``'press'``, ``'release'``, ``'drag'`` or ``'move'``, or ``None``.
        is_down: Whether any mouse button is held right now.
    """

    __slots__ = ('_canvas', '_event')

    def __init__(self, canvas: Canvas[object, object], event: _core.Event | None) -> None:
        """
        Create the mouse view of an event. Use ``context.mouse`` instead of calling this.

        Args:
            canvas: The canvas the event happened in.
            event: The event being handled, or ``None``.
        """
        self._canvas = canvas
        self._event = event

    def get(self) -> _core.MouseEvent | None:
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
        mouse = self.get()
        return None if mouse is None else mouse.position

    @property
    def button(self) -> _core.MouseButton | None:
        """``'left'``, ``'right'`` or ``'middle'``, or ``None``."""
        mouse = self.get()
        return None if mouse is None else mouse.button

    @property
    def kind(self) -> Literal['press', 'release', 'drag', 'move'] | None:
        """``'press'``, ``'release'``, ``'drag'`` or ``'move'``, or ``None``."""
        mouse = self.get()
        return (
            None
            if mouse is None
            else cast("Literal['press', 'release', 'drag', 'move']", mouse.kind)
        )

    @property
    def is_down(self) -> bool:
        """Whether any mouse button is held right now."""
        state = self._canvas._input_state
        return False if state is None else state.is_mouse_down

    def push(self, value: _core.MouseEvent | tuple[int, int]) -> None:
        """
        Move or click the mouse on the canvas, as if the person had.

        Args:
            value: A [`MouseEvent`][xnano_core.MouseEvent] of kind press, release, drag or
                move (or an [`Event`][xnano_core.Event] that holds one), or an ``(x, y)``
                pair, which moves the pointer to that cell. A ``context.scroll.push((x, y))``
                that follows turns the wheel at that cell.

        Raises:
            TypeError: The value is a mouse wheel event, which belongs to
                ``context.scroll.push``, or a pair that is not two whole numbers.
            ValueError: A number of the pair is outside the range of a cell number.
        """
        if isinstance(value, tuple):
            column, row = _cell_pair(value, 'mouse.push')
            state = self._canvas._input_state
            seen = None if state is None else state.pointer_cell
            event = _core.Event.mouse_event(column=column, row=row, kind='move')
            self._canvas._pushed_pointer = (
                (column, row),
                seen,
                self._canvas._time_source.frame,
            )
            self._canvas.push(event)
            return
        if isinstance(value, _core.Event):
            if value.mouse is None:
                raise TypeError(
                    f'mouse.push takes a mouse event, but got a {value.kind!r} event. Push '
                    f'it with canvas.push(event), or build a mouse event with '
                    f'Event.mouse_event(...).'
                )
            value = value.mouse
        if not isinstance(value, _core.MouseEvent):
            raise TypeError(
                f'mouse.push takes a MouseEvent or an (x, y) pair, but got {value!r}.'
            )
        if value.kind == 'scroll':
            raise TypeError(
                'mouse.push cannot send a mouse wheel event, because the wheel belongs to '
                'scroll. Use context.scroll.push((x, y)) to scroll by that many steps.'
            )
        self._canvas.push(
            _core.Event.mouse_event(
                column=value.column, row=value.row, kind=value.kind, button=value.button
            )
        )


class ScrollInput:
    """
    The mouse wheel steps of the current event, as properties of a hook's context.

    Get one from ``context.scroll``. ``x`` and ``y`` are signed steps that grow right and down,
    so scrolling up is ``y == -1``; both are ``0`` unless the event is a wheel report.

    Attributes:
        x: Horizontal steps, positive to the right.
        y: Vertical steps, positive downward.
    """

    __slots__ = ('_canvas', '_event')

    def __init__(self, canvas: Canvas[object, object], event: _core.Event | None) -> None:
        """
        Create the wheel view of an event. Use ``context.scroll`` instead of calling this.

        Args:
            canvas: The canvas the event happened in.
            event: The event being handled, or ``None``.
        """
        self._canvas = canvas
        self._event = event

    def get(self) -> _core.MouseEvent | None:
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
        mouse = self.get()
        return 0 if mouse is None else mouse.scroll_x

    @property
    def y(self) -> int:
        """Vertical steps, positive downward; ``0`` unless the event is a wheel report."""
        mouse = self.get()
        return 0 if mouse is None else mouse.scroll_y

    def push(self, value: tuple[int, int] | _core.MouseEvent) -> None:
        """
        Turn the mouse wheel on the canvas, as if the person had.

        Args:
            value: The ``(x, y)`` steps to scroll by, at the cell the pointer was last seen
                at (a pointer moved with ``context.mouse.push`` counts as seen there at
                once), or a [`MouseEvent`][xnano_core.MouseEvent] of kind scroll.

        Raises:
            TypeError: The value is a mouse event that is not a wheel report, which belongs
                to ``context.mouse.push``, or a pair that is not two whole numbers.
            ValueError: A number of the pair is outside the range of a step count.
        """
        if isinstance(value, tuple):
            steps_x, steps_y = _cell_pair(
                value, 'scroll.push', description='steps of the wheel, such as (0, 1)'
            )
            state = self._canvas._input_state
            cell = None if state is None else state.pointer_cell
            pushed = self._canvas._pushed_pointer
            if (
                pushed is not None
                and pushed[1] == cell
                and pushed[2] == self._canvas._time_source.frame
            ):
                cell = pushed[0]
            column, row = cell if cell is not None else (0, 0)
        else:
            if not isinstance(value, _core.MouseEvent):
                raise TypeError(
                    f'scroll.push takes a MouseEvent of kind scroll or an (x, y) pair of '
                    f'steps, but got {value!r}.'
                )
            if value.kind != 'scroll':
                raise TypeError(
                    f'scroll.push takes a mouse wheel event, but this is a {value.kind} '
                    f'event. Use context.mouse.push(event) for presses, releases, drags and '
                    f'moves.'
                )
            column, row = value.column, value.row
            steps_x, steps_y = value.scroll_x, value.scroll_y
        self._canvas.push(
            _core.Event.mouse_event(
                column=column, row=row, kind='scroll', scroll_x=steps_x, scroll_y=steps_y
            )
        )


class ClipboardInput:
    """
    The pasted text of the current event, as a property of a hook's context.

    Get one from ``context.clipboard``. ``text`` is ``None`` unless the event is a paste.

    Attributes:
        text: The text that was pasted, or ``None``.
    """

    __slots__ = ('_canvas', '_event')

    def __init__(self, canvas: Canvas[object, object], event: _core.Event | None) -> None:
        """
        Create the paste view of an event. Use ``context.clipboard`` instead of calling this.

        Args:
            canvas: The canvas the event happened in.
            event: The event being handled, or ``None``.
        """
        self._canvas = canvas
        self._event = event

    def get(self) -> str | None:
        """The text that was pasted, or ``None`` when the event is not a paste."""
        event = self._event
        return event.pasted_text if event is not None else None

    @property
    def text(self) -> str | None:
        """The text that was pasted, or ``None``."""
        return self.get()

    def push(self, value: str) -> None:
        """
        Paste text on the canvas, as if the person had.

        Args:
            value: The text to paste.

        Raises:
            TypeError: The value is not text.
        """
        if not isinstance(value, str):
            raise TypeError(
                f'clipboard.push takes the text to paste, but received {value!r}. Pass a str, '
                f"such as context.clipboard.push('hello')."
            )
        self._canvas.push(_core.Event.paste(value))
