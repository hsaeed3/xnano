"""
xnano.events

The events a canvas delivers to its hooks: keys, the mouse and everything else.

A hook receives them as ``context.event``; see [`Context`][xnano.context.Context]. Build one
with the class methods of [`Event`][xnano.events.Event] and deliver it with
[`Canvas.push`][xnano.canvas.Canvas.push] to try a hook without a terminal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from xnano_core import Event as _CoreEvent
    from xnano_core import KeyEvent as _CoreKeyEvent
    from xnano_core import MouseEvent as _CoreMouseEvent

    Event = _CoreEvent
    """
    Something that happened: a key, the mouse, a paste, a resize, a timer or an event of
    your own.

    Build one with its class methods to test a hook without a terminal, and read it as
    ``context.event`` inside the hook.

    ```python
    import xnano
    from xnano.events import Event

    with xnano.new(width=20, height=1) as canvas:
        pressed: list[str] = []

        @canvas.hook(on='key')
        def remember(context: xnano.Context) -> None:
            pressed.append(context.event.key.key)

        canvas.push(Event.key_press('a'))
        canvas.step(delta_seconds=0.1)
        assert pressed == ['a']
    ```
    """

    KeyEvent = _CoreKeyEvent
    """
    The details of a key press, repeat or release: the key, the text it types and the
    modifiers held.

    Read it from ``Event.key`` when a hook needs to know which key was pressed.

    ```python
    import xnano
    from xnano.events import Event, KeyEvent

    with xnano.new(width=20, height=1) as canvas:
        heard: list[KeyEvent] = []

        @canvas.hook(on='key')
        def remember(context: xnano.Context) -> None:
            heard.append(context.event.key)

        canvas.push(Event.key_press('ctrl+s'))
        canvas.step(delta_seconds=0.1)
        assert heard[0].key == 's'
        assert heard[0].matches('ctrl+s')
    ```
    """

    MouseEvent = _CoreMouseEvent
    """
    The details of a mouse press, release, drag, move or scroll: the cell, the button and
    the wheel steps.

    Read it from ``Event.mouse`` when a hook needs to know where the pointer is.

    ```python
    import xnano
    from xnano.events import Event, MouseEvent

    with xnano.new(width=20, height=4) as canvas:
        heard: list[MouseEvent] = []

        @canvas.hook(on='mouse')
        def remember(context: xnano.Context) -> None:
            heard.append(context.event.mouse)

        canvas.push(Event.mouse_event(column=4, row=2, kind='press', button='left'))
        canvas.step(delta_seconds=0.1)
        assert (heard[0].column, heard[0].row) == (4, 2)
        assert heard[0].button == 'left'
    ```
    """

_CORE_NAMES: Final[dict[str, str]] = {
    'Event': 'Event',
    'KeyEvent': 'KeyEvent',
    'MouseEvent': 'MouseEvent',
}
"""The name each events object has in ``xnano_core``, by the name it has here."""

__all__ = [
    'Event',
    'KeyEvent',
    'MouseEvent',
]


def __getattr__(name: str) -> object:
    """Import an object from ``xnano_core`` the first time it is read, then keep it."""
    core_name = _CORE_NAMES.get(name)
    if core_name is None:
        raise AttributeError(
            f'xnano.events has no name {name!r}. Its names are {", ".join(__all__)}.'
        )
    import xnano_core

    value = getattr(xnano_core, core_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """The public names of the module, including the ones that are imported when first read."""
    return sorted(__all__)
