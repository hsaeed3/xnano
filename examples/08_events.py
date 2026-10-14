"""
Every event, in one log.

Keys, the mouse, pastes and your own events all arrive the same way, as a context given to a
hook. Press keys, click, drag, paste, resize the window, or press ``c`` to send an event of
your own with ``terminal.inject``.

A custom ``when`` can also span time. ``taps`` below is a generator: it waits for the next event with
``yield``, counts key presses, starts over when too much time passes, and returns the event
that completed it. Tap ``t`` three times quickly to see it fire. Press ``q`` to quit.
"""

import collections

import xnano
from xnano.context import Context
from xnano.events import Event


def taps(key: str, count: int, within_seconds: float = 0.6):
    """A trigger for ``count`` presses of ``key``, each within ``within_seconds`` of the last."""

    def trigger(context: Context):
        seen = 0
        event = None
        while seen < count:
            event = yield within_seconds  # the next event, or None if time ran out
            if event is None:
                seen = 0
            elif event.kind == 'key' and event.key.kind == 'press':
                seen = seen + 1 if event.key.key == key else 0
        return event  # noqa: B901

    return trigger


with xnano.open(width=60, height=10, mouse='motion') as terminal:
    log: collections.deque[str] = collections.deque(maxlen=8)
    terminal.write('events (c: custom event, t t t: triple tap, q: quit)', y=0)

    rows = [terminal.write('', y=row + 2) for row in range(8)]

    def show() -> None:
        for row, placement in enumerate(rows):
            placement.text = log[row] if row < len(log) else ''

    @terminal.hook
    def record(context: Context) -> None:
        event = context.event
        if event is None:
            return
        if context.keyboard is not None:
            description = f'key {context.keyboard.key!r} ({context.keyboard.kind})'
        elif context.mouse is not None:
            mouse = context.mouse
            if mouse.kind == 'move':
                return
            description = f'mouse {mouse.kind} at {mouse.position.x},{mouse.position.y}'
        elif context.pasted is not None:
            description = f'paste {context.pasted!r}'
        elif context.size_changed is not None:
            description = (
                f'resize {context.size_changed.width}x{context.size_changed.height}'
            )
        elif isinstance(event, Event) and event.kind == 'custom':
            description = f'custom {event.custom_name} {event.custom_data}'
        else:
            description = event.kind if isinstance(event, Event) else 'state change'
        log.append(description)
        show()

    @terminal.hook(when=taps('t', 3))
    def triple_tap(context: Context) -> None:
        log.append('triple tap of t')
        show()

    @terminal.on_key('c')
    def send(context: Context) -> None:
        context.terminal.inject(Event.custom('hello', data='from the example'))

    terminal.run(quit_on='q')
