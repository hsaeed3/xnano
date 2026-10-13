"""
Draw pixel by pixel.

Every cell holds two pixels (one on top of the other), so a 60 by 12 region is 60 by 24
pixels. ``shade`` calls a function for each pixel with its position and uses the color it
returns. Press ``q`` to quit.
"""

import math

import xnano

with xnano.open(width=60, height=12) as terminal:
    pixels = terminal.pixels()

    @terminal.loop.on_frame
    def draw(frame: xnano.Frame) -> None:
        time = frame.elapsed_seconds

        def color(column: int, row: int) -> tuple[int, int, int]:
            wave = math.sin(column / 7 + time) + math.sin(row / 5 - time * 1.3)
            wave += math.sin((column + row) / 9 + time * 0.7)
            hue = (wave + 3) / 6
            return (
                int(255 * hue),
                int(255 * (1 - abs(hue - 0.5) * 2)),
                int(255 * (1 - hue)),
            )

        pixels.shade(color)

    terminal.run(quit_on='q')
