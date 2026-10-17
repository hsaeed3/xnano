"""
Pixel art that fits whatever window it is in.

``terminal.write`` sizes an image by what you give it. A percentage (or no size at all) leaves
the art *unlocked*: it is converted again every time the window is resized, keeping its
proportions and its hard pixel edges. A plain number *locks* it to that many cells. The big
picture below is unlocked, so drag the window's corner and watch it refit; the thumbnail in the
corner is locked at 34 cells and never changes size. Press ``q`` to quit.

The art is "Mountain at Dusk" by Luis Zuno (ansimuz), released under CC0
(https://opengameart.org/content/mountain-at-dusk-background).
"""

import pathlib

import xnano
from xnano.styles import Style

ART = pathlib.Path(__file__).parent / 'assets' / 'mountain-dusk.png'


def main() -> None:
    """Show the picture twice: unlocked, filling the window, and locked, as a thumbnail."""
    with xnano.open(title='dusk') as terminal:
        terminal.write(
            xnano.from_image(ART, x='center', y='center', width='100%', height='100%')
        )
        terminal.write(xnano.from_image(ART, x='right', y='bottom', width=34, layer=1))
        terminal.write(
            ' resize the window: the art follows, the thumbnail stays 34 cells wide ',
            x='center',
            y=0,
            layer=2,
            style=Style('white', 'black', bold=True),
        )
        terminal.run(quit_on='q')


if __name__ == '__main__':
    main()
