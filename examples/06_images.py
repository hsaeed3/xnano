"""
Images become cells: pan and zoom over real pixel art.

``assets/punyworld-overworld-tileset.png`` is the Puny World overworld tileset, pixel art
released under CC0 by its author on https://opengameart.org/content/16x16-puny-world-tileset.
It is far larger than the screen, so the example draws it with ``xnano.draw`` as a world and
moves the camera: the arrow keys pan, ``+`` and ``-`` zoom, and ``q`` quits. Zooming enlarges the picture
by whole numbers with nearest-neighbour resampling, which keeps the hard edges of pixel art.

Pass the path of any other image (PNG, JPEG, GIF, WebP) to look around in that instead:
``python examples/06_images.py photo.png``. A string is always text, so a file is given as a
``pathlib.Path``.
"""

import pathlib
import sys

import xnano
from xnano.art import Art
from xnano.context import Context
from xnano.image import TerminalImage
from xnano.placement import Placement

ZOOMS = (1, 2, 4)
STEP = 8  # screen pixels moved by one key press
MAXIMUM_SIDE = 16_384  # the largest side an image can be resized to
DEFAULT_START = (64, 410)  # the village in the tileset
DEFAULT_IMAGE = (
    pathlib.Path(__file__).parent / 'assets' / 'punyworld-overworld-tileset.png'
)


class Viewer:
    """A picture drawn as a world, and how far it is enlarged."""

    def __init__(
        self, view: Placement, world: Art, picture: TerminalImage, left: int, top: int
    ) -> None:
        self.view = view
        self.world = world
        self.picture = picture
        self.zoom_index = 0
        self.left = self.top = 0
        self.look_at(left, top)

    @property
    def zoom(self) -> int:
        """How many screen pixels one picture pixel covers."""
        return ZOOMS[self.zoom_index]

    @property
    def view_size(self) -> tuple[int, int]:
        """The width and height in pixels of what the screen shows."""
        return self.view.width, self.view.height * 2

    def look_at(self, left: int, top: int) -> None:
        """Put the camera at a pixel of the world, staying inside the picture."""
        view_width, view_height = self.view_size
        self.left = max(0, min(self.world.width - view_width, left))
        self.top = max(0, min(self.world.height - view_height, top))
        self.world.camera.x, self.world.camera.y = self.left, self.top

    def pan(self, columns: int, rows: int) -> None:
        """Move the camera by a number of steps."""
        self.look_at(self.left + columns * STEP, self.top + rows * STEP)

    def zoom_by(self, change: int) -> None:
        """Zoom in (``1``) or out (``-1``), keeping the middle of the screen where it is."""
        index = max(0, min(len(ZOOMS) - 1, self.zoom_index + change))
        largest_side = max(self.picture.width, self.picture.height)
        if index == self.zoom_index or largest_side * ZOOMS[index] > MAXIMUM_SIDE:
            return  # an image larger than the limit cannot be enlarged again
        view_width, view_height = self.view_size
        ratio = ZOOMS[index] / self.zoom
        center = (
            (self.left + view_width / 2) * ratio,
            (self.top + view_height / 2) * ratio,
        )
        self.zoom_index = index
        zoom = self.zoom
        self.world.replace(
            self.picture
            if zoom == 1
            else self.picture.resize(
                self.picture.width * zoom,
                self.picture.height * zoom,
                resampling_filter='nearest',
            )
        )
        self.look_at(
            round(center[0] - view_width / 2), round(center[1] - view_height / 2)
        )


def main() -> None:
    """Open the picture and move around in it."""
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_IMAGE
    left, top = DEFAULT_START if len(sys.argv) == 1 else (0, 0)
    picture = TerminalImage.open(path)
    with xnano.open(width=64, height=21) as terminal:
        world = xnano.draw(picture, background='black')
        view = terminal.write(world, width='100%', height=20)
        viewer = Viewer(view, world, picture, left, top)

        status_line = terminal.write('', y=20)

        def show_status() -> None:
            status_line.text = f'x {viewer.left} y {viewer.top} zoom {viewer.zoom}x'

        @terminal.hook(on='key', keys='left')
        def pan_left(context: Context) -> None:
            viewer.pan(-1, 0)
            show_status()

        @terminal.hook(on='key', keys='right')
        def pan_right(context: Context) -> None:
            viewer.pan(1, 0)
            show_status()

        @terminal.hook(on='key', keys='up')
        def pan_up(context: Context) -> None:
            viewer.pan(0, -1)
            show_status()

        @terminal.hook(on='key', keys='down')
        def pan_down(context: Context) -> None:
            viewer.pan(0, 1)
            show_status()

        @terminal.hook(on='key', keys=['+', '='])
        def zoom_in(context: Context) -> None:
            viewer.zoom_by(1)
            show_status()

        @terminal.hook(on='key', keys='-')
        def zoom_out(context: Context) -> None:
            viewer.zoom_by(-1)
            show_status()

        show_status()
        terminal.run(quit_on='q')


if __name__ == '__main__':
    main()
