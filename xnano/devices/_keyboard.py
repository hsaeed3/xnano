"""
xnano.devices._keyboard

The keyboard of a terminal: the key being handled, the keys held down, and the program's own
key presses, pastes, waits and prompts.
"""

from __future__ import annotations

import random
from collections.abc import Coroutine
from typing import TYPE_CHECKING, Any, cast

import xnano_core as _core
from xnano._schema._hooks import KeyName, KeyNames
from xnano.devices._input import (
    _ESTIMATED_HOLD_SECONDS,
    _MOUSE_BUTTON_NAMES,
    _modifier_text,
    _names,
)
from xnano.errors import TerminalClosedError

if TYPE_CHECKING:
    from xnano._schema._axes import Axis
    from xnano.canvas import Canvas
    from xnano.hooks._context import Context
    from xnano.layout._placement import Placement

__all__ = ['Keyboard']


class Keyboard:
    """
    The keyboard of a terminal: what is typed, what is held down, and the program's own keys.

    Get it from [`Canvas.keyboard`][xnano.canvas.Canvas.keyboard], or from
    ``context.keyboard`` inside a hook. In a hook, ``key``, ``binding`` and the rest describe
    the key being handled, and are ``None`` (or empty) for any other event; outside a hook
    there is no key being handled. ``held_keys`` and ``is_down`` answer for right now, from any
    thread, for a program that polls instead of listening. ``press``, ``paste`` and ``random``
    are the program's own hands: the canvas hears them like keys a person typed.

    A terminal that reports key releases (kitty, ghostty and wezterm, when the canvas is
    opened with ``keyboard='release_events'``) tells exactly when a key is let go. Any other
    terminal only sends repeats while a key is held, so a key counts as held for a short time
    after its last repeat.

    Attributes:
        key: The [`KeyName`][xnano.devices.KeyName] of the key being handled, such as ``'q'`` or
            ``'enter'``, or ``None``.
        kind: ``'press'``, ``'repeat'`` or ``'release'``, or ``None``.
        modifiers: The modifier keys held with it, from ``'control'``, ``'shift'``, ``'alt'``,
            ``'super'``, ``'meta'`` and ``'hyper'``.
        text: The text the key types, or ``None`` for control keys and key bindings.
        binding: The key with its modifiers as one text such as ``'ctrl+s'``, or ``None``.
        event: The [`KeyEvent`][xnano_core.KeyEvent] being handled, or ``None``.
        pasted: The text of the paste being handled, or ``None``.
        held_keys: The keys held down right now.

    Examples:
        ```python
        import xnano

        with xnano.new(width=8, height=1) as canvas:
            heard = []

            @canvas.hook(on='key')
            def listen(context: xnano.Context) -> None:
                heard.append(context.keyboard.binding)

            canvas.keyboard.press('ctrl+s')
            canvas.deliver_events()
            assert heard == ['ctrl+s']
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
        Create a view of the keyboard. Use ``canvas.keyboard`` or ``context.keyboard`` instead.

        Args:
            canvas: The root canvas the keyboard belongs to.
            event: The event being handled, or ``None`` outside a hook.
            owner: The placement or canvas a hook is attached to; ``None`` for the canvas.
            context: The hook's context, which notes what a component reads; ``None`` outside
                a hook.
        """
        self._canvas = canvas
        self._event = event
        self._owner = owner
        self._context = context

    def __repr__(self) -> str:
        key = self.binding
        return 'Keyboard()' if key is None else f'Keyboard(binding={key!r})'

    # -- the key being handled -----------------------------------------------------------

    @property
    def event(self) -> _core.KeyEvent | None:
        """The key event being handled, or ``None`` when the event is not a key."""
        event = self._event
        return event.key if event is not None else None

    @property
    def key(self) -> KeyName | None:
        """The name of the key, such as ``'q'`` or ``'enter'``, or ``None``."""
        key = self.event
        return None if key is None else key.key

    @property
    def kind(self) -> _core.KeyEventKind | None:
        """``'press'``, ``'repeat'`` or ``'release'``, or ``None`` for any other event."""
        key = self.event
        return None if key is None else key.kind

    @property
    def modifiers(self) -> frozenset[_core.KeyModifier]:
        """The modifier keys held with the key; empty for any other event."""
        key = self.event
        return frozenset() if key is None else frozenset(key.modifiers)

    @property
    def text(self) -> str | None:
        """The text the key types, or ``None`` for control keys, key bindings and other events."""
        key = self.event
        return None if key is None else key.text

    @property
    def binding(self) -> _core.KeyBindingText | None:
        """The key with its modifiers as one text such as ``'ctrl+s'``, or ``None``."""
        key = self.event
        return None if key is None else _modifier_text(key)

    @property
    def pasted(self) -> str | None:
        """The text of the paste being handled, or ``None`` when the event is not a paste."""
        context = self._context
        if context is not None:
            context._read('paste')
        event = self._event
        return event.pasted_text if event is not None else None

    # -- what is held down ---------------------------------------------------------------

    @property
    def _state(self) -> _core.InputState:
        """The input of the canvas's current runtime, which any thread may read."""
        context = self._context
        if context is not None:
            context._read_time()
        state = self._canvas._input_state
        if state is None:
            raise TerminalClosedError(
                'The canvas has no input yet, because it is not attached to a running loop.'
            )
        canvas = self._canvas
        if canvas._estimated_holds_state is not state:
            # Held keys are estimated from repeats once a program asks for them.
            state.estimate_holds(timeout_seconds=_ESTIMATED_HOLD_SECONDS)
            canvas._estimated_holds_state = state
        return state

    @property
    def held_keys(self) -> frozenset[KeyName]:
        """The keys held down right now."""
        state = self._state
        held = state.pressed_keys | state.estimated_pressed_keys
        return cast(
            'frozenset[KeyName]',
            frozenset(name for name in held if name not in _MOUSE_BUTTON_NAMES),
        )

    def is_down(self, keys: KeyNames) -> bool:
        """
        Whether any of the keys is held down right now.

        Args:
            keys: One key name such as ``'space'``, or several such as ``('a', 'left')``,
                spelled as in [`KeyName`][xnano.devices.KeyName]. A key binding such as
                ``'ctrl+s'`` or a modifier alone is not held input.

        Raises:
            TypeError: A name is not text.
            ValueError: A name is not a key, or is a key binding or a modifier.

        Examples:
            ```python
            import xnano

            with xnano.new(width=20, height=3) as canvas:
                hero = canvas.screen.write('@')

                @canvas.hook(on='tick', every=1 / 30)
                def walk(context: xnano.Context) -> None:
                    step_x, step_y = context.keyboard.direction()
                    hero.x += step_x
                    hero.y += step_y

                canvas.clock.step()
                assert not canvas.keyboard.is_down('space')
            ```
        """
        names = _names(keys)
        held = self.held_keys
        return any(name in held for name in names)

    def axis(self, negative: KeyNames, positive: KeyNames) -> int:
        """
        ``-1``, ``0`` or ``1`` from a pair of keys: the negative one, neither or both, the
        positive one.

        Args:
            negative: The key or keys that push toward ``-1``.
            positive: The key or keys that push toward ``1``.

        Raises:
            TypeError: A name is not text.
            ValueError: A name is not a key, or is a key binding or a modifier.
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
            ValueError: A name is not a key, or is a key binding or a modifier.
        """
        return self.axis(left, right), self.axis(up, down)

    # -- the program's own keys ----------------------------------------------------------

    def press(self, key: _core.KeyBindingText | _core.KeyEvent) -> None:
        """
        Press a key on the canvas, as if it had been typed.

        The canvas's hooks hear it at its next step, whatever the terminal settings say.

        Args:
            key: A key name or key binding such as ``'q'`` or ``'ctrl+s'``, or a
                [`KeyEvent`][xnano_core.KeyEvent].

        Raises:
            TypeError: ``key`` is neither text nor a key event.
            ValueError: ``key`` is text that does not name a key. The message suggests the
                closest key names.

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
                    context.keyboard.press('q')

                canvas.clock.step(delta_seconds=0.2)
                canvas.deliver_events()
                assert heard == ['q']
            ```
        """
        if isinstance(key, _core.KeyEvent):
            self._canvas.push(_core.Event.key_press(_modifier_text(key), kind=key.kind))
            return
        if not isinstance(key, str):
            raise TypeError(
                f"keyboard.press takes a key name such as 'q' or 'ctrl+s', or a KeyEvent, but "
                f'got {key!r}. Pass the key as text: keyboard.press("q").'
            )
        from xnano.hooks._triggers import normalize_binding

        normalize_binding(key)
        self._canvas.push(_core.Event.key_press(key))

    def random(self) -> KeyName:
        """
        Press a random key on the canvas and return its name.

        The key is a letter, a digit, ``'space'``, ``'enter'``, ``'escape'``, ``'tab'``,
        ``'backspace'``, ``'delete'``, ``'insert'``, ``'home'``, ``'end'``, ``'page_up'``,
        ``'page_down'``, an arrow or ``'f1'`` to ``'f12'``, pressed with no modifiers. It is
        delivered like ``press(name)``. ``random.seed(...)`` repeats the keys.

        Returns:
            The [`KeyName`][xnano.devices.KeyName] that was pressed.

        Examples:
            ```python
            import random

            import xnano

            with xnano.new(width=8, height=1) as canvas:
                heard = []

                @canvas.hook(on='key')
                def listen(context: xnano.Context) -> None:
                    heard.append(context.keyboard.key)

                random.seed(7)
                pressed = canvas.keyboard.random()
                canvas.deliver_events()
                assert heard == [pressed]
            ```
        """
        from xnano.hooks._triggers import _KEY_NAMES

        name = cast('KeyName', random.choice(_KEY_NAMES))
        self.press(name)
        return name

    def paste(self, text: str) -> None:
        """
        Paste text on the canvas, as if the person had.

        Args:
            text: The text to paste.

        Raises:
            TypeError: ``text`` is not text.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=1) as canvas:
                pasted = []
                canvas.hook(lambda context: pasted.append(context.keyboard.pasted), on='paste')
                canvas.keyboard.paste('hello')
                canvas.deliver_events()
                assert pasted == ['hello']
            ```
        """
        if not isinstance(text, str):
            raise TypeError(
                f'keyboard.paste takes the text to paste, but received {text!r}. Pass a str, '
                f"such as canvas.keyboard.paste('hello')."
            )
        self._canvas.push(_core.Event.paste(text))

    # -- waiting for keys ----------------------------------------------------------------

    def wait(self, *keys: KeyName) -> KeyName:
        """
        Wait until a key is pressed, and return its name.

        Your program waits here while the canvas goes on drawing and animating. It reads
        like ``input()``: nothing else runs on your thread until the key arrives.

        Args:
            keys: The keys to wait for, such as ``'enter'`` or ``'q'``. Give none to take any key.

        Returns:
            The name of the key that was pressed.

        Raises:
            TerminalError: The canvas ended, or has a manual clock, so no key could arrive.

        Examples:
            In a program: ``terminal.keyboard.wait()`` after writing "Press any key to start".
            Here a timer plays the part of the person pressing the key:

            ```python
            import xnano

            with xnano.new(realtime=True, width=30, height=2) as canvas:
                canvas.screen.write('Press enter to start')

                @canvas.hook(on='tick', after=0.05)
                def press(context: xnano.Context) -> None:
                    context.keyboard.press('enter')

                assert canvas.keyboard.wait('enter') == 'enter'
            ```
        """
        return self._canvas._wait_for_key(keys)

    def wait_async(self, *keys: KeyName) -> Coroutine[Any, Any, KeyName]:
        """
        Wait until a key is pressed, like [`wait`][xnano.devices.Keyboard.wait], with ``await``.

        Your event loop goes on running other tasks while the canvas waits for the key.

        Args:
            keys: The keys to wait for, such as ``'enter'`` or ``'q'``. Give none to take any key.

        Returns:
            A coroutine that gives the name of the key that was pressed.

        Raises:
            TerminalError: The canvas ended, or has a manual clock, so no key could arrive.

        Examples:
            ```python
            import asyncio

            import xnano


            async def main() -> None:
                async with xnano.new(realtime=True, width=30, height=2) as canvas:
                    canvas.screen.write('Press enter to start')

                    @canvas.hook(on='tick', after=0.05)
                    def press(context: xnano.Context) -> None:
                        context.keyboard.press('enter')

                    assert await canvas.keyboard.wait_async('enter') == 'enter'


            asyncio.run(main())
            ```
        """
        return self._canvas._wait_for_key_async(keys)

    def prompt(
        self, text: str, *, x: Axis = 'next', y: Axis = 'next', default: str = ''
    ) -> str:
        """
        Prompt for a line of text on the screen, and return what was typed.

        The prompt and the answer appear on the canvas while your program waits, like
        ``input()``. ``Enter`` submits and ``Backspace`` deletes.

        Args:
            text: What to ask, such as ``'Your name: '``.
            x: The column of the prompt, in the forms ``screen.write`` takes.
            y: The row of the prompt; on the next line by default, like ``screen.write``.
            default: Text already in the answer, which the user can edit.

        Returns:
            What was typed, without the prompt.

        Raises:
            TerminalError: The canvas ended, or has a manual clock, so no answer could arrive.

        Examples:
            In a program: ``name = terminal.keyboard.prompt('Your name: ')``. Here a timer
            plays the part of the person typing:

            ```python
            import xnano

            with xnano.new(realtime=True, width=30, height=2) as canvas:

                @canvas.hook(on='tick', after=0.05)
                def type_answer(context: xnano.Context) -> None:
                    for letter in 'Ada':
                        context.keyboard.press(letter)
                    context.keyboard.press('enter')

                assert canvas.keyboard.prompt('Your name: ') == 'Ada'
            ```
        """
        return self._canvas._prompt(text, x=x, y=y, default=default)

    def prompt_async(
        self, text: str, *, x: Axis = 'next', y: Axis = 'next', default: str = ''
    ) -> Coroutine[Any, Any, str]:
        """
        Prompt for a line of text, like [`prompt`][xnano.devices.Keyboard.prompt], with
        ``await``.

        Your event loop goes on running other tasks while the person types.

        Args:
            text: What to ask, such as ``'Your name: '``.
            x: The column of the prompt, in the forms ``screen.write`` takes.
            y: The row of the prompt; on the next line by default.
            default: Text already in the answer, which the user can edit.

        Returns:
            A coroutine that gives what was typed, without the prompt.

        Raises:
            TerminalError: The canvas ended, or has a manual clock, so no answer could arrive.
        """
        return self._canvas._prompt_async(text, x=x, y=y, default=default)
