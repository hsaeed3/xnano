"""
Draw pixel by pixel.

Every cell holds two pixels (one on top of the other), so a 60 by 12 region is 60 by 24
pixels. ``shade`` calls a function for each pixel with its position and uses the color it
returns, here a ``Color`` made from a hue. ``pixels[x, y] = color`` (a ``Color`` or a
``(red, green, blue)`` tuple) draws one pixel and ``pixels[0:10, 2] = color`` a line. Press
``q`` to quit.
"""

import math

import xnano
from xnano.context import Context

with xnano.open(width=60, height=12) as terminal:
    pixels = terminal.region.half_blocks

    @terminal.hook(on='frame')
    def draw(context: Context) -> None:
        time = context.time.elapsed

        def color(x: int, y: int) -> xnano.Color:
            wave = math.sin(x / 7 + time) + math.sin(y / 5 - time * 1.3)
            wave += math.sin((x + y) / 9 + time * 0.7)
            return xnano.Color.from_hsl(120 + (wave + 3) / 6 * 200, 75, 55)

        pixels.shade(color)

    terminal.run(quit_on='q')
