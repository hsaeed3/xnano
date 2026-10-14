"""
A slider made of two ideas: a range and a hook.

The thumb lives inside the track and its ``x`` is given a range, which is how far it may
travel. Piping ``draggable()`` onto it lets the mouse set ``x``, and the range holds it
inside the track. Press
``q`` to quit.
"""

import xnano
from xnano.context import Frame
from xnano.operations import draggable

with xnano.open(width=40, height=3, mouse=True) as terminal:
    track = terminal.write('─' * 40, y=1)
    thumb = track.write('█', x=(0, track.width - 1), y=0) | draggable()
    heading = terminal.write('volume   0%   (drag the block)')

    @terminal.loop.on_frame
    def show_value(frame: Frame) -> None:
        percent = round(thumb.x / 39 * 100)
        heading.text = f'volume {percent:>3}%   (drag the block)'

    terminal.run(quit_on='q')
