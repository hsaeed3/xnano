"""
A slider made of two ideas: a range and a hook.

The thumb's ``x`` is given a range, ``(0, 39)``, which is how far it may travel. Dragging it
with the mouse sets ``x`` to the pointer, and the range holds it inside the track. Press
``q`` to quit.
"""

import xnano

with xnano.open(width=40, height=3, mouse='buttons') as terminal:
    terminal.add('─' * 40, y=1)
    thumb = terminal.add('█', x=(0, 39), y=1, layer=1)
    thumb.make_draggable()

    @terminal.loop.on_frame
    def show_value(frame: xnano.Frame) -> None:
        percent = round(thumb.x / 39 * 100)
        terminal.write(f'volume {percent:>3}%   (drag the block)', y=0)

    terminal.run(quit_on='q')
