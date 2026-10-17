"""
Motion without a loop.

The balls move because their ``x`` is a formula of the canvas's clock: nothing in this
program draws a frame. The frame counter is the only thing that runs code every frame.
Press ``q`` to quit.
"""

import xnano
from xnano.context import Context

with xnano.open(width=60, height=6) as terminal:
    for row, seconds in enumerate((1.5, 2.5, 4.0), start=1):
        ball = terminal.write('●', y=row)
        ball.x = (ball.parent.width - ball.width) * ((ball.root.time / seconds) % 1.0)

    counter = terminal.write('frame 0', y=5)

    @terminal.hook(on='frame')
    def count(context: Context) -> None:
        counter.text = f'frame {context.time.frame:<6} {context.time.elapsed:5.1f}s'

    terminal.run(quit_on='q')
