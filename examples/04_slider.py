"""
A slider made of two ideas: a range and a drag hook.

The thumb lives inside the track and its ``x`` is given a range, which is how far it may
travel. A generator hook on ``'drag'`` moves it with the mouse: the loop runs while the
button is down, and ``context = yield`` waits for the next movement. ``left()`` and
``right()`` move it from the keyboard, and the range holds it inside the track. Press ``q`` to
quit.
"""

import xnano
from xnano.context import Context
from xnano.types import HookGenerator

with xnano.open(width=40, height=3, mouse=True) as terminal:
    track = terminal.write('─' * 40, y=1)
    thumb = track.write('█', x=(0, track.width - 1), y=0)
    heading = terminal.write('volume   0%   (drag the block, or press left and right)')

    @thumb.hook(on='drag')
    def slide(context: Context) -> HookGenerator:
        while context.mouse.is_down:
            pointer = context.mouse.position
            if pointer is not None:
                thumb.x = context.parent.local(pointer).x
            context = yield

    @terminal.hook(on='frame')
    def show_value(context: Context) -> None:
        percent = round(thumb.x / 39 * 100)
        heading.text = f'volume {percent:>3}%   (drag the block, or press left and right)'

    @terminal.hook(on='key', keys='left')
    def lower(context: Context) -> None:
        thumb.left(2)

    @terminal.hook(on='key', keys='right')
    def raise_volume(context: Context) -> None:
        thumb.right(2)

    terminal.run(quit_on='q')
