"""
Widgets, composed.

A widget describes something to draw, and every number in it can be a formula, so the
gauge follows the clock with no code that redraws it. A ``Block`` draws a border that fits
its size. Press ``q`` to quit.
"""

import collections
import math

import xnano
from xnano.context import Context
from xnano.expressions import TimeElapsed
from xnano.widgets import Block, Gauge, Sparkline

with xnano.open(width=50, height=9) as terminal:
    gauge = Gauge((TimeElapsed % 4) / 4, label='cpu', width=48, height=1)
    terminal.write(Block('load', border_type='rounded'), width=50, height=3)
    terminal.write(gauge, x=1, y=1)

    samples = collections.deque([0] * 48, maxlen=48)
    history = Sparkline(list(samples), maximum=100, width=48, height=1)
    terminal.write(Block('history', border_type='rounded'), y=4, width=50, height=3)
    terminal.write(history, x=1, y=5)

    @terminal.every(0.1)
    def sample(context: Context) -> None:
        elapsed = context.time.elapsed
        samples.append(round(50 + 50 * math.sin(elapsed * 2)))
        history.values = list(samples)

    terminal.run(quit_on='q')
