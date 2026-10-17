"""
Paint with the mouse.

The mouse reports cells, and ``Region.pixel_for_cell`` picks the pixel of a cell the pointer is over,
so a drag draws at twice the vertical resolution. Keys ``1`` to ``4`` choose a color, ``c``
clears the canvas and ``q`` quits.
"""

import xnano
from xnano.context import Context
from xnano.operations import Fill

COLORS = {
    '1': xnano.Color('#ff3030'),
    '2': xnano.Color('#ffd000'),
    '3': xnano.Color('#00c800'),
    '4': xnano.Color('#00c8ff'),
}


class Brush:
    """The color a drag paints with."""

    def __init__(self) -> None:
        self.color = COLORS['1']


def main() -> None:
    """Paint wherever the mouse is dragged."""
    brush = Brush()
    with xnano.open(width=50, height=14, mouse=True) as terminal:
        terminal.write('drag to paint, 1-4 colors, c clear, q quit', y=0)
        canvas = terminal.write(' ', y=1, width=50, height=13)
        pixels = canvas.region.half_blocks

        def is_painting(context: Context) -> bool:
            mouse = context.mouse
            return mouse is not None and mouse.kind in ('press', 'drag')

        @canvas.hook(when=is_painting)
        def paint(context: Context) -> None:
            if context.mouse.position is None:
                return
            position = context.mouse.position
            column, row = pixels.pixel_for_cell(
                position.x, position.y - 1, anchor='center'
            )
            pixels[column, row] = brush.color

        @terminal.hook(on='key', keys=list(COLORS))
        def choose_color(context: Context) -> None:
            if context.keyboard.key is not None:
                brush.color = COLORS[context.keyboard.key]

        @terminal.hook(on='key', keys='c')
        def clear(context: Context) -> None:
            canvas.core_buffer.update(Fill(' '))

        terminal.run(quit_on='q')


if __name__ == '__main__':
    main()
