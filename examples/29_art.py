"""
Pixel art, cells and values you can draw with.

``xnano.draw`` turns rows of text and a palette into ``Art``; ``symbol='wall'`` registers it
under a name, so ``xnano.draw('wall')`` makes another copy later. The world is bigger than its
window, the camera follows the knight, and ``knight.move`` slides along the solid walls. On the
right, ``xnano.box`` is a standalone rectangle of cells: ``region[x, y] = xnano.Pixel(...)``
writes single cells from presets (``'diamond'``, ``'star'``, ``'check'``), the registered
``Pixel('gem')`` is found by name, and ``color.bg.shade`` colors every cell from a function.
Helpers can call ``xnano.active()`` to reach the running canvas. Press the arrow keys to walk
and ``q`` to quit.
"""

import xnano
from xnano.context import Context

xnano.draw(['WW', 'WW', 'WW', 'WW'], 'W=#9a7b4f', symbol='wall')
xnano.draw(
    """
    ..SS..
    .SSSS.
    .SKKS.
    ..SS..
    .BBBB.
    .B..B.
    """,
    {'S': '#c0c8d8', 'K': '#202030', 'B': '#4060d0'},
    symbol='knight',
)
xnano.Pixel('diamond', foreground='cyan', symbol='gem')

MESSAGE_ROW = 12


def say(text: str) -> None:
    """Show a message on the running canvas, from anywhere."""
    xnano.active().region[0:58, MESSAGE_ROW : MESSAGE_ROW + 1] = text.ljust(58)


with xnano.open(width=58, height=13) as terminal:
    terminal.write('arrows walk   q quit')

    world = xnano.draw(None, width=64, height=14, background='#14203a')
    for position in (16, 30, 46, 58):
        world.add(xnano.draw('wall'), x=position, y=4, is_solid=True)
    knight = world.add(xnano.draw('knight'), x=2, y=4)
    world.camera.follow(knight)
    terminal.write(world, y=2, width=32, height=7)

    panel = terminal.write(xnano.box(22, 7, border='rounded'), x=35, y=2)
    for index, preset in enumerate(('block', 'diamond', 'star', 'check', 'cross')):
        panel.region[1 + index * 2, 1] = xnano.Pixel(preset, foreground='yellow')
    panel.region[1, 3] = xnano.Pixel('gem')
    panel.region[3:20, 5:6] = 'cells, by value'
    panel.color.bg.shade(lambda x, y: (10 + x * 4, 20 + y * 8, 70))

    def walk(x: int, y: int) -> None:
        moved = knight.move(x, y)
        say('walking' if moved != (0.0, 0.0) else 'blocked: a wall is in the way')

    @terminal.hook(on='key', keys='left')
    def left(context: Context) -> None:
        walk(-2, 0)

    @terminal.hook(on='key', keys='right')
    def right(context: Context) -> None:
        walk(2, 0)

    @terminal.hook(on='key', keys='up')
    def up(context: Context) -> None:
        walk(0, -2)

    @terminal.hook(on='key', keys='down')
    def down(context: Context) -> None:
        walk(0, 2)

    terminal.run(quit_on='q')
