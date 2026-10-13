"""
Paint with the mouse.

The mouse reports cells, and ``Pixels.pixel_at`` picks the pixel of a cell the pointer is over,
so a drag draws at twice the vertical resolution. Keys ``1`` to ``4`` choose a color, ``c``
clears the canvas and ``q`` quits.
"""

import xnano
from xnano.operations import Fill

COLORS = {'1': '#ff3030', '2': '#ffd000', '3': '#00c800', '4': '#00c8ff'}


class Brush:
    """The color a drag paints with."""

    def __init__(self) -> None:
        self.color = COLORS['1']


def main() -> None:
    """Paint wherever the mouse is dragged."""
    brush = Brush()
    with xnano.open(width=50, height=14, mouse='buttons') as terminal:
        terminal.add('drag to paint, 1-4 colors, c clear, q quit', y=0)
        canvas = terminal.add(' ', y=1, width=50, height=13)
        pixels = canvas.pixels()

        def is_painting(context: xnano.Context) -> bool:
            mouse = context.mouse
            return mouse is not None and mouse.kind in ('press', 'drag')

        @canvas.hook(when=is_painting)
        def paint(context: xnano.Context) -> None:
            if context.mouse is None:
                return
            position = context.mouse.position
            column, row = pixels.pixel_at(position.x, position.y - 1, anchor='center')
            pixels[column, row] = brush.color

        @terminal.on_key(*COLORS)
        def choose_color(context: xnano.Context) -> None:
            if context.keyboard is not None:
                brush.color = COLORS[context.keyboard.key]

        @terminal.on_key('c')
        def clear(context: xnano.Context) -> None:
            canvas.buffer.update(Fill(' '))

        terminal.run(quit_on='q')


if __name__ == '__main__':
    main()
