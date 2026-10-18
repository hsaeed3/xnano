"""
A terminal that stacks what is written on it, and text that stops at the edges of its area.

``layout='column'`` stacks every piece in the order it is written: the text written first
takes the top of the terminal, and the canvas written after it takes its ``'50%'`` at the
bottom. Positions such as ``y='center'`` are measured in each piece's own slot.
``edges='stop'`` keeps moved content inside its area, so the arrow keys move the text up to
the edges of the canvas and no further.
Press the arrow keys to move the text, any other key to give the top text a new shade of
blue, and ``q`` to quit.
"""

import random

import xnano

random.seed(4)

with xnano.open(height=10, layout='column', edges='stop') as terminal:
    content = terminal.write(
        'Press any key to change the color of this text', x='center', y='center'
    )

    @terminal.hook(on='key')
    def change_color(context: xnano.Context) -> None:
        if context.keyboard.key not in ('up', 'down', 'left', 'right', 'q'):
            content.color.fg.random('blue')

    with xnano.new(height='50%', border='rounded') as canvas:
        movable = canvas.write(
            'Use the arrow keys to move this text', x='center', y='center'
        )
    terminal.write(canvas)

    @canvas.hook(on='key')
    def move_text(context: xnano.Context) -> None:
        match context.keyboard.key:
            case 'up':
                movable.up()
            case 'down':
                movable.down()
            case 'left':
                movable.left()
            case 'right':
                movable.right()
            case _:
                pass

    terminal.run(quit_on='q')
