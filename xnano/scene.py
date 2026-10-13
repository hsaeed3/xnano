"""
xnano.scene

A pixel world with a camera: sprites placed in world coordinates, drawn only when something
changed, with solid ground to collide against.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import TYPE_CHECKING

from xnano._axes import to_rgb
from xnano._values import ColorValue

if TYPE_CHECKING:
    from xnano_image import TerminalImage

    from xnano.pixels import Pixels
    from xnano.placement import Placement
    from xnano.terminal import Terminal

__all__ = ['Camera', 'Scene', 'Sprite']


class Sprite:
    """
    An image placed in a [`Scene`][xnano.scene.Scene].

    Change any attribute and the scene draws it again on the next frame; nothing else is
    needed. Coordinates are world pixels, measured from the top-left of the world, and
    ``(x, y)`` is the pixel of the image that sits on the ``anchor``: give a character's feet
    as the anchor and ``(x, y)`` is where it stands.

    Attributes:
        image: The picture. Assign another image to change the frame being shown.
        x: The world column of the anchor pixel.
        y: The world row of the anchor pixel.
        layer: Sprites with a higher layer are drawn over lower ones.
        anchor: The ``(column, row)`` inside the image that sits at ``(x, y)``.
        is_visible: Whether the sprite is drawn.

    Examples:
        ```python
        import xnano
        from xnano.image import from_art

        with xnano.open(offscreen=True, width=20, height=5) as terminal:
            scene = terminal.scene(world_width=40, world_height=20)
            hero = scene.add(from_art(['HH', 'HH'], {'H': 'red'}), x=10, y=10, anchor=(1, 1))
            hero.move_by(2, 0)
            assert hero.x == 12
        ```
    """

    __slots__ = (
        '_anchor',
        '_image',
        '_is_visible',
        '_layer',
        '_scene',
        '_x',
        '_y',
    )

    def __init__(
        self,
        scene: Scene,
        image: TerminalImage,
        x: float,
        y: float,
        layer: int,
        anchor: tuple[int, int],
    ) -> None:
        # Created by ``Scene.add``; not constructed directly.
        """
        Create a sprite. Use ``scene.add`` instead of calling this.

        Args:
            scene: The scene the sprite belongs to.
            image: The picture.
            x: The world column of the anchor pixel.
            y: The world row of the anchor pixel.
            layer: The drawing order.
            anchor: The pixel of the image that sits at ``(x, y)``.
        """
        self._scene = scene
        self._image = image
        self._x = float(x)
        self._y = float(y)
        self._layer = layer
        self._anchor = anchor
        self._is_visible = True

    @property
    def image(self) -> TerminalImage:
        """The picture. Assign another image to change the frame being shown."""
        return self._image

    @image.setter
    def image(self, value: TerminalImage) -> None:
        if value is not self._image:
            self._image = value
            self._scene._changed()

    @property
    def x(self) -> float:
        """The world column of the anchor pixel."""
        return self._x

    @x.setter
    def x(self, value: float) -> None:
        if value != self._x:
            self._x = float(value)
            self._scene._changed()

    @property
    def y(self) -> float:
        """The world row of the anchor pixel."""
        return self._y

    @y.setter
    def y(self, value: float) -> None:
        if value != self._y:
            self._y = float(value)
            self._scene._changed()

    @property
    def layer(self) -> int:
        """Sprites with a higher layer are drawn over lower ones."""
        return self._layer

    @layer.setter
    def layer(self, value: int) -> None:
        if value != self._layer:
            self._layer = value
            self._scene._changed()

    @property
    def anchor(self) -> tuple[int, int]:
        """The ``(column, row)`` inside the image that sits at ``(x, y)``."""
        return self._anchor

    @anchor.setter
    def anchor(self, value: tuple[int, int]) -> None:
        if value != self._anchor:
            self._anchor = value
            self._scene._changed()

    @property
    def is_visible(self) -> bool:
        """Whether the sprite is drawn."""
        return self._is_visible

    @is_visible.setter
    def is_visible(self, value: bool) -> None:
        if value != self._is_visible:
            self._is_visible = value
            self._scene._changed()

    def move_by(self, step_x: float, step_y: float) -> float:
        """
        Move the sprite, sliding along solid ground instead of stopping at it.

        The two axes are tried one after the other, so walking diagonally into a wall keeps
        moving along it. Without solid ground (see
        [`Scene.solid`][xnano.scene.Scene.solid]) the sprite moves freely.

        Args:
            step_x: How far to move along ``x``, in world pixels.
            step_y: How far to move along ``y``, in world pixels.

        Returns:
            The distance actually moved, which is ``0`` when the sprite is blocked.
        """
        before = (self._x, self._y)
        self.x = self._advance(self._x, self._y, step_x, True)
        self.y = self._advance(self._x, self._y, step_y, False)
        return math.hypot(self._x - before[0], self._y - before[1])

    def _advance(self, x: float, y: float, distance: float, is_horizontal: bool) -> float:
        """Walk along one axis a pixel at a time, so a thin wall cannot be stepped over."""
        position = x if is_horizontal else y
        remaining = abs(distance)
        sign = 1.0 if distance > 0 else -1.0
        while remaining > 0:
            step = min(1.0, remaining) * sign
            ahead = position + step
            if self._scene.is_solid(*((ahead, y) if is_horizontal else (x, ahead))):
                break
            position = ahead
            remaining -= abs(step)
        return position

    def remove(self) -> None:
        """Take the sprite out of the scene."""
        if self in self._scene._sprites:
            self._scene._sprites.remove(self)
            self._scene._changed()


class Camera:
    """
    Which part of the world is on screen.

    By default the camera stays put. [`follow`][xnano.scene.Camera.follow] a sprite to keep it
    in the middle, or set ``x`` and ``y`` yourself. Either way the camera stays inside the
    world, and a world smaller than the screen is centered.

    Attributes:
        x: The world column at the left edge of the screen, when nothing is followed.
        y: The world row at the top edge of the screen, when nothing is followed.
        target: The sprite the camera follows, or ``None``.
    """

    def __init__(self) -> None:
        """Create a camera. Every scene has one as ``scene.camera``."""
        self.x = 0
        """The world column at the left edge of the screen, when nothing is followed."""
        self.y = 0
        """The world row at the top edge of the screen, when nothing is followed."""
        self.target: Sprite | None = None
        """The sprite the camera follows, or ``None``."""

    def follow(self, sprite: Sprite | None) -> None:
        """
        Keep a sprite in the middle of the screen, or pass ``None`` to stop following.

        Args:
            sprite: The sprite to follow.
        """
        self.target = sprite


def _clamp_axis(wanted: int, world: int, view: int) -> int:
    if world <= view:
        return -((view - world) // 2)  # the world is smaller than the screen: center it
    return max(0, min(world - view, wanted))


class Scene:
    """
    A pixel world: sprites in world coordinates, seen through a camera.

    The scene draws itself. It watches its sprites and the camera and redraws only on a frame
    after something changed, so a standing-still world costs nothing. Get one from
    [`Terminal.scene`][xnano.Terminal.scene] or [`Placement.scene`][xnano.Placement.scene].

    A pixel is half a cell tall, so a terminal of ``80`` by ``24`` cells shows ``80`` by ``48``
    pixels of the world.

    Attributes:
        world_width: The width of the world in pixels. Assign it when the world changes size.
        world_height: The height of the world in pixels.
        camera: What part of the world is on screen.
        origin: The world pixel at the top-left of the screen.
        view_size: The width and height in pixels of what the screen shows.
        solid: Which world pixels cannot be walked on, or ``None`` when everything can.

    Examples:
        ```python
        import xnano
        from xnano.image import from_art

        with xnano.open(offscreen=True, width=20, height=5) as terminal:
            scene = terminal.scene(world_width=100, world_height=60)
            scene.add(from_art(['GGGG'], {'G': 'green'}))
            hero = scene.add(from_art(['H', 'H'], {'H': 'red'}), x=50, y=30, anchor=(0, 1))
            scene.camera.follow(hero)
            terminal.loop.step()
        ```
    """

    def __init__(
        self,
        target: Terminal[object] | Placement[object],
        world_width: int,
        world_height: int,
        background: ColorValue,
    ) -> None:
        # Created by ``Terminal.scene`` and ``Placement.scene``; not constructed directly.
        """
        Create a scene. Use ``terminal.scene(...)`` instead of calling this.

        Args:
            target: The terminal or placement the scene is drawn on.
            world_width: The width of the world in pixels.
            world_height: The height of the world in pixels.
            background: The color shown where no sprite is drawn.
        """
        if world_width < 1 or world_height < 1:
            raise ValueError(
                f'A scene needs a world of at least 1 by 1 pixels, but got {world_width} by '
                f'{world_height}. Give world_width and world_height in pixels.'
            )
        self.world_width = world_width
        """The width of the world in pixels. Assign it when the world changes size."""
        self.world_height = world_height
        """The height of the world in pixels."""
        self.camera = Camera()
        """What part of the world is on screen."""
        self.solid: bytes | bytearray | None = None
        """
        Which world pixels cannot be walked on, or ``None`` when everything can: one byte per
        pixel, row after row, with a non-zero byte for solid ground.
        """
        self._sprites: list[Sprite] = []
        self._pixels: Pixels = target.pixels()
        self._background = to_rgb(background)
        self._version = 0
        self._shown: tuple[int, ...] | None = None
        self._terminal: Terminal[object] = target._terminal
        self._terminal.loop.on_frame(self._draw)

    # -- building the world -------------------------------------------------------------

    def add(
        self,
        image: TerminalImage,
        *,
        x: float = 0,
        y: float = 0,
        layer: int = 0,
        anchor: tuple[int, int] = (0, 0),
    ) -> Sprite:
        """
        Put an image in the world.

        Args:
            image: The picture, such as one made by
                [`from_art`][xnano.image.from_art]. Transparent pixels show what is behind.
            x: The world column of the anchor pixel.
            y: The world row of the anchor pixel.
            layer: Sprites with a higher layer are drawn over lower ones; sprites on the same
                layer are drawn in the order they were added.
            anchor: The ``(column, row)`` inside the image that sits at ``(x, y)``.

        Returns:
            The [`Sprite`][xnano.scene.Sprite], to move, change or remove.
        """
        sprite = Sprite(self, image, x, y, layer, anchor)
        self._sprites.append(sprite)
        self._changed()
        return sprite

    def is_solid(self, x: float, y: float) -> bool:
        """
        Whether a world pixel cannot be walked on.

        Everything outside the world is solid. Inside it, a pixel is solid where
        ``scene.solid`` holds a non-zero byte: one byte per pixel, row after row, so
        ``solid[y * world_width + x]``.

        Args:
            x: The world column.
            y: The world row.
        """
        column, row = round(x), round(y)
        if not (0 <= column < self.world_width and 0 <= row < self.world_height):
            return True
        return self.solid is not None and bool(
            self.solid[row * self.world_width + column]
        )

    # -- looking at it ------------------------------------------------------------------

    def world_at(self, column: int, row: int) -> tuple[int, int]:
        """
        The world pixel under a cell of the screen, such as the one the pointer is over.

        Args:
            column: The cell's column on the screen.
            row: The cell's row on the screen.

        Examples:
            ```python
            # inside a click hook:
            #     target_x, target_y = scene.world_at(*context.mouse.position)
            ```
        """
        left, top = self.origin
        pixel_column, pixel_row = self._pixels.pixel_at(column, row)
        return left + pixel_column, top + pixel_row

    @property
    def view_size(self) -> tuple[int, int]:
        """The ``(width, height)`` in pixels of what the screen shows."""
        return self._pixels.width, self._pixels.height

    @property
    def origin(self) -> tuple[int, int]:
        """
        The world ``(column, row)`` at the top-left of the screen, after the camera has followed
        its sprite and stayed inside the world.
        """
        view_width, view_height = self._pixels.width, self._pixels.height
        target = self.camera.target
        wanted_x = self.camera.x if target is None else round(target.x) - view_width // 2
        wanted_y = self.camera.y if target is None else round(target.y) - view_height // 2
        return (
            _clamp_axis(wanted_x, self.world_width, view_width),
            _clamp_axis(wanted_y, self.world_height, view_height),
        )

    def _changed(self) -> None:
        self._version += 1

    def _draw(self, frame: object) -> None:
        pixels = self._pixels
        left, top = self.origin
        signature = (self._version, left, top, pixels.width, pixels.height)
        if signature == self._shown:
            return  # nothing moved: the screen already shows this
        self._shown = signature
        red, green, blue = self._background
        pixels.draw_rgba(
            bytes((red, green, blue, 255)) * (pixels.width * pixels.height),
            width=pixels.width,
            height=pixels.height,
            mode='replace',
        )
        ordered: Sequence[Sprite] = sorted(
            self._sprites, key=lambda sprite: sprite._layer
        )
        for sprite in ordered:
            if sprite._is_visible:
                pixels.draw_image(
                    sprite._image,
                    x=round(sprite._x) - sprite._anchor[0] - left,
                    y=round(sprite._y) - sprite._anchor[1] - top,
                )
