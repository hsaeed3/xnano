"""
A canvas: shapes in a coordinate system of your own.

``Canvas`` maps ``x_bounds`` and ``y_bounds`` onto the cells it covers, so shapes are given in
whatever units suit the picture. Here a planet orbits a sun; each frame replaces the shapes.
Press ``q`` to quit.
"""

import math

import xnano
from xnano.context import Frame
from xnano.widgets import Block, Canvas, CanvasCircle, CanvasLabel, CanvasPoints


def main() -> None:
    """Draw an orbit that follows the clock."""
    with xnano.iter(width=50, height=16) as terminal:
        canvas = Canvas(
            x_bounds=(-10, 10),
            y_bounds=(-10, 10),
            marker='braille',
            block=Block('orbit', border_type='rounded'),
        )
        terminal.write(canvas, width=50, height=16)
        orbit = [
            (8 * math.cos(angle / 30 * math.tau), 8 * math.sin(angle / 30 * math.tau))
            for angle in range(30)
        ]

        @terminal.loop.on_frame
        def draw(frame: Frame) -> None:
            angle = frame.elapsed_seconds
            canvas.clear_shapes()
            canvas.extend_shapes(
                [
                    CanvasPoints(orbit, 'gray'),
                    CanvasCircle(0, 0, 2, 'yellow'),
                    CanvasCircle(8 * math.cos(angle), 8 * math.sin(angle), 1, 'cyan'),
                    CanvasLabel(-1, -4, 'sun'),
                ]
            )

        terminal.run(quit_on='q')


if __name__ == '__main__':
    main()
