"""
Steer the terminal's cursor.

A terminal has one cursor. ``terminal.cursor.up()``, ``down()``, ``left()`` and ``right()``
move it by a count of cells and stop at the edges of the terminal; ``home()`` sends it to
the top-left cell and ``shape`` changes how it looks. Press the arrow keys to move it,
``h`` to send it home, ``s`` to change its shape and ``q`` to quit.
"""

import xnano
from xnano.context import Context
from xnano.styles import Style

SHAPES = ('block', 'bar', 'underline')

with xnano.open(width=50, height=8) as terminal:
    cursor = terminal.cursor
    terminal.write(
        'arrows move the cursor   h home   s shape   q quit', style=Style(dim=True)
    )
    status = terminal.write(' ' * 50, y=7)

    def show() -> None:
        position = cursor.position
        assert position is not None
        status.text = f'column {position.x:<3} row {position.y:<3} shape {cursor.shape}'

    cursor.shape = 'block'
    cursor.is_blinking = True
    cursor.home().down(2)
    show()

    @terminal.on_key('up')
    def move_up(context: Context) -> None:
        cursor.up()
        show()

    @terminal.on_key('down')
    def move_down(context: Context) -> None:
        cursor.down()
        show()

    @terminal.on_key('left')
    def move_left(context: Context) -> None:
        cursor.left()
        show()

    @terminal.on_key('right')
    def move_right(context: Context) -> None:
        cursor.right()
        show()

    @terminal.on_key('h')
    def go_home(context: Context) -> None:
        cursor.home()
        show()

    @terminal.on_key('s')
    def change_shape(context: Context) -> None:
        cursor.shape = SHAPES[(SHAPES.index(cursor.shape or 'block') + 1) % len(SHAPES)]
        show()

    terminal.run(quit_on='q')
