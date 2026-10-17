"""
Every event, in one log.

Keys, the mouse, pastes and your own events all arrive the same way, as a context given to a
hook. Press keys, click, drag, scroll, paste, resize the window, or press ``c`` to send an event of
your own with ``terminal.push``.

A hook can also span several events. ``triple_tap`` below is a generator hook: it receives the
next context at each ``yield``, counts presses of ``t``, starts over when too much time passes
or another key comes, and logs when the third arrives. Tap ``t`` three times quickly to see
it fire. Press ``q`` to quit.
"""

import collections

import xnano
from xnano.context import Context
from xnano.events import Event
from xnano.types import HookGenerator

with xnano.open(width=60, height=10, mouse='motion', scroll=True) as terminal:
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
        if context.keyboard.key is not None:
            description = f'key {context.keyboard.key!r} ({context.keyboard.kind})'
        elif (position := context.mouse.position) is not None:
            if context.mouse.kind == 'move':
                return
            description = f'mouse {context.mouse.kind} at {position.x},{position.y}'
        elif context.scroll.x or context.scroll.y:
            description = f'scroll {context.scroll.x},{context.scroll.y}'
        elif context.clipboard.text is not None:
            description = f'paste {context.clipboard.text!r}'
        elif isinstance(event, Event) and event.size is not None:
            description = f'resize {event.size.width}x{event.size.height}'
        elif isinstance(event, Event) and event.kind == 'custom':
            description = f'custom {event.custom_name} {event.custom_data}'
        else:
            description = event.kind if isinstance(event, Event) else 'state change'
        log.append(description)
        show()

    @terminal.hook(on='key', when="keyboard.kind == 'press'")
    def triple_tap(context: Context) -> HookGenerator:
        taps = 0
        last_seconds = context.time.elapsed
        while taps < 3:
            now_seconds = context.time.elapsed
            is_t = context.keyboard.key == 't'
            is_in_time = taps == 0 or now_seconds - last_seconds <= 0.6
            taps = taps + 1 if is_t and is_in_time else int(is_t)
            last_seconds = now_seconds
            if taps < 3:
                context = yield
        log.append('triple tap of t')
        show()

    @terminal.hook(on='key', keys='c')
    def send(context: Context) -> None:
        context.canvas.push(Event.custom('hello', data='from the example'))

    terminal.run(quit_on='q')
