"""
xnano.art._worlds

Pixel art written as text, and pixel worlds: art that holds other art, seen through a camera,
with solid ground to collide against.
"""

from __future__ import annotations

import math
import textwrap
import weakref
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Literal, cast

import xnano_core as _core
from xnano import symbols
from xnano._internal._axes import to_rgb
from xnano._internal._optional import is_image
from xnano._schema._appearance import ColorValue
from xnano._schema._layout import Anchor
from xnano.appearance._look import MOST_CELLS
from xnano.art._images import Image
from xnano.effects._registry import apply_effects, effect_sequence, normalize_effect

if TYPE_CHECKING:
    from xnano_image import TerminalImage

    from xnano.context import Context
    from xnano.placement import Placement
    from xnano.types import RenderableEffectSpecification

__all__ = ['Art', 'Camera', 'draw']

_RGBA = 4
_PIXELS_PER_CELL_ROW = 2


class Camera:
    """
    Which part of a world is on screen.

    By default the camera stays put. [`follow`][xnano.art.Camera.follow] an art to keep it in
    the middle, or set ``x`` and ``y`` yourself. Either way the camera stays inside the world,
    and a world smaller than the screen is centered.

    Attributes:
        x: The world column at the left edge of the screen, when nothing is followed.
        y: The world row at the top edge of the screen, when nothing is followed.
        target: The art the camera follows, or ``None``.

    Examples:
        ```python
        import xnano

        world = xnano.draw(None, width=100, height=60, background='black')
        hero = world.add(xnano.draw(['H', 'H'], {'H': 'red'}), x=50, y=30)
        world.camera.follow(hero)
        assert world.camera.target is hero
        ```
    """

    def __init__(self) -> None:
        """Create a camera. Every art has one as ``art.camera``."""
        self.x = 0
        """The world column at the left edge of the screen, when nothing is followed."""
        self.y = 0
        """The world row at the top edge of the screen, when nothing is followed."""
        self.target: Art | None = None
        """The art the camera follows, or ``None``."""

    def follow(self, art: Art | None) -> None:
        """
        Keep an art in the middle of the screen, or pass ``None`` to stop following.

        Args:
            art: The art to follow.
        """
        self.target = art


def _clamp_axis(wanted: int, world: int, view: int) -> int:
    if world <= view:
        return -((view - world) // 2)  # the world is smaller than the screen: center it
    return max(0, min(world - view, wanted))


def _check_pixels(
    value: object, *, name: str, verb: str, opposite: str | None = None
) -> None:
    """Refuse a distance that is not a finite number of pixels."""
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise TypeError(
            f'{verb}() takes {name} as a finite number of pixels, but got {value!r}. Pass a '
            f'number such as {name}=1 to move by one pixel.'
        )
    if opposite is not None and value < 0:
        raise ValueError(
            f'{name} must be zero or more, but got {value}. To move the other way, call '
            f'{opposite}() instead of {verb}().'
        )


class Art:
    """
    Pixel art, and a world that holds other art.

    Make one with [`draw`][xnano.draw]. A pixel is half a cell tall, so art that is ``8`` pixels
    tall takes ``4`` rows of a canvas. Write it with ``canvas.write(art)``, or print it on its
    own with [`render`][xnano.art.Art.render].

    An art can hold other art: [`add`][xnano.art.Art.add] puts a child at a position in the
    world, and the world is drawn through its [`camera`][xnano.art.Art.camera]. Change any
    attribute of an art or of a child and the canvas draws it again on the next frame; nothing
    else is needed, and a world that stands still costs nothing. Positions and sizes of art are
    in pixels and may be fractional; a child is drawn at its rounded position. A child's
    ``x`` and ``y`` place it inside its parent in pixels, while ``placement.x`` and
    ``placement.y`` place the whole art on the canvas in cells: ``art.up()`` moves one pixel,
    half a cell, and ``placement.up()`` moves one cell.

    Attributes:
        width: The width in pixels.
        height: The height in pixels (two pixel rows make one cell row).
        x: The pixel column of the anchor inside the parent art.
        y: The pixel row of the anchor inside the parent art.
        layer: Children with a higher layer are drawn over lower ones.
        is_visible: Whether the art is drawn.
        anchor: The ``(x, y)`` pixel inside the art that sits at ``(x, y)``.
        background: The color behind the art and its children, or ``None`` for none.
        solid_map: Which pixels of the art's world cannot be walked on, or ``None``.
        camera: What part of the world is on screen.
        symbol: The name the art is registered under in [`symbols`][xnano.symbols], or ``None``.

    Examples:
        ```python
        import xnano

        world = xnano.draw(None, width=40, height=20, background='black')
        hero = world.add(xnano.draw(['HH', 'HH'], {'H': 'red'}), x=10, y=10, anchor=(1, 1))
        hero.move(2, 0)
        assert hero.x == 12

        with xnano.new(width=20, height=5) as canvas:
            canvas.write(world, width='100%', height='100%')
            canvas.step()
        ```
    """

    __slots__ = (
        '__weakref__',
        '_anchor',
        '_background',
        '_blocks_movement',
        '_cache_buffer',
        '_cache_key',
        '_children',
        '_effects',
        '_height',
        '_is_visible',
        '_last_view',
        '_layer',
        '_observers',
        '_parent',
        '_rgba',
        '_solid_map',
        '_symbol',
        '_version',
        '_width',
        '_x',
        '_y',
        'camera',
    )

    def __init__(
        self,
        rgba: bytes | bytearray | None,
        width: int,
        height: int,
        *,
        background: ColorValue | None = None,
        symbol: str | None = None,
        effects: Sequence[RenderableEffectSpecification] = (),
    ) -> None:
        """
        Create art from pixels. Use [`draw`][xnano.draw] instead of calling this.

        Args:
            rgba: ``width * height * 4`` bytes of red, green, blue and alpha, or ``None`` for
                a world with no pixels of its own.
            width: The width in pixels.
            height: The height in pixels.
            background: The color behind the art.
            symbol: The name to register the art under.
            effects: Effects to start on the placement when the art is written.
        """
        if width < 1 or height < 1:
            raise ValueError(
                f'Art needs at least 1 by 1 pixels, but got {width} by {height}. Give '
                f'draw(...) rows of text, or width= and height= in pixels.'
            )
        if rgba is not None and len(rgba) != width * height * _RGBA:
            raise ValueError(
                f'{width} by {height} pixels need {width * height * _RGBA} bytes of red, '
                f'green, blue and alpha, but got {len(rgba)}.'
            )
        self._rgba: bytes | None = None if rgba is None else bytes(rgba)
        self._width = width
        self._height = height
        self._x = 0.0
        self._y = 0.0
        self._layer = 0
        self._is_visible = True
        self._anchor: Anchor = (0, 0)
        self._background: tuple[int, int, int] | None = (
            None if background is None else to_rgb(background)
        )
        self._solid_map: bytes | bytearray | None = None
        self._blocks_movement = False
        self._children: list[Art] = []
        self._parent: Art | None = None
        self._symbol: str | None = None
        effects = cast(
            'tuple[RenderableEffectSpecification, ...]',
            effect_sequence(effects, 'renderable'),
        )
        for effect in effects:
            normalize_effect(effect, 'renderable')
        self._effects: tuple[RenderableEffectSpecification, ...] = effects
        self._version = 0
        self._cache_key: tuple[int, ...] | None = None
        self._cache_buffer: _core.Buffer | None = None
        self._last_view: tuple[int, int] | None = None
        self._observers: weakref.WeakSet[Placement[object, object]] = weakref.WeakSet()
        self.camera = Camera()
        """What part of the world is on screen."""
        if symbol is not None:
            symbols.register(symbol, self)
            self._symbol = symbol

    # -- attributes ----------------------------------------------------------------------

    @property
    def width(self) -> int:
        """The width in pixels."""
        return self._width

    @property
    def height(self) -> int:
        """The height in pixels."""
        return self._height

    @property
    def symbol(self) -> str | None:
        """The name the art is registered under in [`symbols`][xnano.symbols], or ``None``."""
        return self._symbol

    @property
    def x(self) -> float:
        """The pixel column of the anchor inside the parent art."""
        return self._x

    @x.setter
    def x(self, value: float) -> None:
        if value != self._x:
            self._x = float(value)
            self._changed()

    @property
    def y(self) -> float:
        """The pixel row of the anchor inside the parent art."""
        return self._y

    @y.setter
    def y(self, value: float) -> None:
        if value != self._y:
            self._y = float(value)
            self._changed()

    @property
    def layer(self) -> int:
        """Children with a higher layer are drawn over lower ones."""
        return self._layer

    @layer.setter
    def layer(self, value: int) -> None:
        if value != self._layer:
            self._layer = value
            self._changed()

    @property
    def is_visible(self) -> bool:
        """Whether the art is drawn."""
        return self._is_visible

    @is_visible.setter
    def is_visible(self, value: bool) -> None:
        if value != self._is_visible:
            self._is_visible = value
            self._changed()

    @property
    def anchor(self) -> Anchor:
        """The ``(x, y)`` pixel inside the art that sits at ``(x, y)``."""
        return self._anchor

    @anchor.setter
    def anchor(self, value: Anchor) -> None:
        if value != self._anchor:
            self._anchor = value
            self._changed()

    @property
    def background(self) -> _core.Color | None:
        """The color behind the art and its children, or ``None`` for none."""
        return None if self._background is None else _core.Color(self._background)

    @background.setter
    def background(self, value: ColorValue | None) -> None:
        color = None if value is None else to_rgb(value)
        if color != self._background:
            self._background = color
            self._changed()

    @property
    def solid_map(self) -> bytes | bytearray | None:
        """
        Which pixels of the art's world cannot be walked on, or ``None`` when all can: one byte
        per pixel, row after row (``width * height`` bytes), with a non-zero byte for solid
        ground.
        """
        return self._solid_map

    @solid_map.setter
    def solid_map(self, value: bytes | bytearray | None) -> None:
        if value is not None and len(value) != self._width * self._height:
            raise ValueError(
                f'solid_map needs one byte for each of the {self._width * self._height} '
                f'pixels ({self._width} by {self._height}), but got {len(value)} bytes. '
                f'Write the rows one after another, with a non-zero byte for solid ground.'
            )
        self._solid_map = value
        self._changed()

    # -- building the world --------------------------------------------------------------

    def add(
        self,
        art: Art,
        /,
        *,
        x: float = 0,
        y: float = 0,
        layer: int = 0,
        anchor: Anchor = (0, 0),
        is_solid: bool = False,
    ) -> Art:
        """
        Put another art in this one, at a position in pixels.

        Args:
            art: The art to add. It may be added to one art only.
            x: The pixel column of the child's anchor inside this art.
            y: The pixel row of the child's anchor inside this art.
            layer: Children with a higher layer are drawn over lower ones; children on the
                same layer are drawn in the order they were added.
            anchor: The ``(x, y)`` pixel of the child that sits at ``(x, y)``.
            is_solid: Whether the child's opaque pixels block the movement of other children.

        Returns:
            The child, to move, change or remove.

        Raises:
            ValueError: The art already belongs to an art, or is this art or one that holds
                it.

        Examples:
            ```python
            import xnano

            world = xnano.draw(None, width=8, height=8)
            hero = world.add(xnano.draw(['R', 'R'], {'R': 'red'}), x=3, y=2, anchor=(0, 1))
            assert (hero.x, hero.y) == (3, 2)
            ```
        """
        if not isinstance(art, Art):
            raise TypeError(
                f'add() takes an Art made with xnano.draw(...), but got '
                f'{type(art).__name__}. Wrap a picture with xnano.draw(image) first.'
            )
        ancestor: Art | None = self
        while ancestor is not None:
            if ancestor is art:
                raise ValueError(
                    'An art cannot be added to itself or to an art it holds. Add it to '
                    'another world.'
                )
            ancestor = ancestor._parent
        if art._parent is not None:
            raise ValueError(
                'This art already belongs to another art. Call art.remove() first, or draw '
                'a second one.'
            )
        art._parent = self
        art._x = float(x)
        art._y = float(y)
        art._layer = layer
        art._anchor = anchor
        art._blocks_movement = is_solid
        self._children.append(art)
        self._changed()
        return art

    def replace(
        self,
        source: str | Sequence[str] | Image | TerminalImage | bytes | bytearray | None,
        palette: Mapping[str, ColorValue] | str | None = None,
        *,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """
        Swap the pixels for others, keeping the position, layer and parent.

        The solid ground is kept when the new pixels have the same size and cleared when the
        size changes.

        This is how a walk cycle or a zoom is made: draw every frame once, and replace the
        pixels of the art that is on screen. The sources are the ones
        [`draw`][xnano.draw] takes, except a symbol name.

        Args:
            source: Text rows, an image, RGBA bytes or ``None``.
            palette: What each character of text rows means.
            width: The width in pixels of RGBA bytes or of a blank world.
            height: The height in pixels.

        Examples:
            ```python
            import xnano

            frame_one = ['AB']
            hero = xnano.draw(frame_one, {'A': 'red', 'B': 'blue'})
            hero.replace(['BA'], {'A': 'red', 'B': 'blue'})
            assert hero.width == 2
            ```
        """
        rgba, pixel_width, pixel_height = _pixels_of(source, palette, width, height)
        previous_width, previous_height = self._width, self._height
        self._rgba = None if rgba is None else bytes(rgba)
        self._width = pixel_width
        self._height = pixel_height
        if (pixel_width, pixel_height) != (previous_width, previous_height):
            self._solid_map = None
        self._changed()

    def remove(self) -> None:
        """Take the art out of the art that holds it. Removing a loose art does nothing."""
        parent = self._parent
        if parent is None:
            return
        self._parent = None
        if self in parent._children:
            parent._children.remove(self)
        if parent.camera.target is self:
            parent.camera.target = None
        parent._changed()

    # -- moving --------------------------------------------------------------------------

    def move(self, x: float = 0, y: float = 0) -> tuple[float, float]:
        """
        Move the art by a number of pixels, sliding along solid ground instead of stopping.

        The two axes are tried one after the other, a pixel at a time, so walking diagonally
        into a wall keeps moving along it and a thin wall cannot be stepped over. The anchor
        pixel is what collides. An art without a parent art, or whose parent has no solid
        ground, moves freely. Positive ``x`` moves right and positive ``y`` moves down.

        Pixels are half a cell: ``art.move(y=-1)`` moves one pixel up, where
        ``placement.move(y=-1)`` moves the whole art one cell up.

        Args:
            x: How far to move along ``x``, in pixels.
            y: How far to move along ``y``, in pixels.

        Returns:
            The distance moved along each axis, ``(0.0, 0.0)`` when blocked.

        Examples:
            ```python
            import xnano

            world = xnano.draw(None, width=8, height=8)
            solid = bytearray(64)
            for row in range(8):
                solid[row * 8 + 5] = 1
            world.solid_map = solid
            hero = world.add(xnano.draw(['R'], {'R': 'red'}), x=4, y=2)
            assert hero.move(2, 1) == (0.0, 1.0)
            assert (hero.x, hero.y) == (4, 3)
            ```
        """
        _check_pixels(x, name='x', verb='move')
        _check_pixels(y, name='y', verb='move')
        before_x, before_y = self._x, self._y
        self.x = self._advance(self._x, self._y, x, is_horizontal=True)
        self.y = self._advance(self._x, self._y, y, is_horizontal=False)
        return (self._x - before_x, self._y - before_y)

    def up(self, count: float = 1) -> float:
        """
        Move up by ``count`` pixels, sliding along solid ground, and say how far it got.

        Unlike [`Placement.up`][xnano.placement.Placement.up], which returns the placement
        so calls chain, this returns the distance moved, so a game can tell when the art was
        blocked.

        Args:
            count: How many pixels to move; pixels are half a cell.

        Returns:
            The distance moved in pixels, ``0.0`` when blocked.
        """
        _check_pixels(count, name='count', verb='up', opposite='down')
        return abs(self.move(y=-count)[1])

    def down(self, count: float = 1) -> float:
        """
        Move down by ``count`` pixels, sliding along solid ground, and say how far it got.

        Unlike [`Placement.down`][xnano.placement.Placement.down], which returns the placement
        so calls chain, this returns the distance moved, so a game can tell when the art was
        blocked.

        Args:
            count: How many pixels to move; pixels are half a cell.

        Returns:
            The distance moved in pixels, ``0.0`` when blocked.
        """
        _check_pixels(count, name='count', verb='down', opposite='up')
        return abs(self.move(y=count)[1])

    def left(self, count: float = 1) -> float:
        """
        Move left by ``count`` pixels, sliding along solid ground, and say how far it got.

        Unlike [`Placement.left`][xnano.placement.Placement.left], which returns the placement
        so calls chain, this returns the distance moved, so a game can tell when the art was
        blocked.

        Args:
            count: How many pixels to move; pixels are half a cell.

        Returns:
            The distance moved in pixels, ``0.0`` when blocked.
        """
        _check_pixels(count, name='count', verb='left', opposite='right')
        return abs(self.move(x=-count)[0])

    def right(self, count: float = 1) -> float:
        """
        Move right by ``count`` pixels, sliding along solid ground, and say how far it got.

        Unlike [`Placement.right`][xnano.placement.Placement.right], which returns the placement
        so calls chain, this returns the distance moved, so a game can tell when the art was
        blocked.

        Args:
            count: How many pixels to move; pixels are half a cell.

        Returns:
            The distance moved in pixels, ``0.0`` when blocked.
        """
        _check_pixels(count, name='count', verb='right', opposite='left')
        return abs(self.move(x=count)[0])

    def _advance(
        self, x: float, y: float, distance: float, *, is_horizontal: bool
    ) -> float:
        """Walk along one axis a pixel at a time, so a thin wall cannot be stepped over."""
        position = x if is_horizontal else y
        sign = 1.0 if distance > 0 else -1.0
        parent = self._parent
        if parent is None:
            return position + distance
        # Everything outside the world is solid, so walking further than the world is wide
        # and tall cannot get anywhere a shorter walk would not.
        remaining = min(abs(distance), float(parent._width + parent._height))
        while remaining > 0:
            step = min(1.0, remaining) * sign
            ahead = position + step
            if parent is not None and parent._is_solid_for(
                *((ahead, y) if is_horizontal else (x, ahead)), mover=self
            ):
                break
            position = ahead
            remaining -= abs(step)
        return position

    def is_solid(self, x: float, y: float) -> bool:
        """
        Whether a pixel of this art's world cannot be walked on.

        Everything outside the world is solid. Inside it, a pixel is solid where
        [`solid_map`][xnano.art.Art.solid_map] holds a non-zero byte, or where an opaque pixel
        of a child added with ``is_solid=True`` is.

        Args:
            x: The world column.
            y: The world row.

        Examples:
            ```python
            import xnano

            world = xnano.draw(None, width=4, height=4)
            assert world.is_solid(-1, 0)
            assert not world.is_solid(2, 2)
            ```
        """
        return self._is_solid_for(x, y, mover=None)

    def _is_solid_for(self, x: float, y: float, *, mover: Art | None) -> bool:
        column, row = round(x), round(y)
        if not (0 <= column < self._width and 0 <= row < self._height):
            return True
        solid_map = self._solid_map
        if solid_map is not None and solid_map[row * self._width + column]:
            return True
        for child in self._children:
            if child is mover or not child._blocks_movement or not child._is_visible:
                continue
            if child._has_opaque_pixel(
                column - round(child._x) + child._anchor[0],
                row - round(child._y) + child._anchor[1],
            ):
                return True
        return False

    def _has_opaque_pixel(self, x: int, y: int) -> bool:
        if not (0 <= x < self._width and 0 <= y < self._height):
            return False
        rgba = self._rgba
        return rgba is None or rgba[(y * self._width + x) * _RGBA + 3] > 0

    # -- looking at it -------------------------------------------------------------------

    def world_for_cell(self, x: int, y: int) -> tuple[int, int]:
        """
        The world pixel under a cell of the screen, such as the one the pointer is over.

        The cell must be one of the cells the art was last drawn in; a cell is two pixels
        tall, and the pixel returned is the lower one.

        Args:
            x: The cell's column in the placement of the art.
            y: The cell's row in the placement of the art.

        Examples:
            ```python
            import xnano

            world = xnano.draw(None, width=40, height=40)
            world.camera.x, world.camera.y = 16, 16
            with xnano.new(width=8, height=4) as canvas:
                canvas.write(world, width='100%', height='100%')
                canvas.step()
            assert world.world_for_cell(0, 0) == (16, 17)
            ```
        """
        left, top = self._origin()
        return left + x, top + _PIXELS_PER_CELL_ROW * y + 1

    def _view_size(self) -> tuple[int, int]:
        """The ``(width, height)`` in pixels that the art was last drawn in."""
        view = self._last_view
        if view is None:
            return self._width, self._height
        return view

    def _world_position(self, art: Art) -> tuple[float, float]:
        x, y = art._x, art._y
        parent = art._parent
        while parent is not None and parent is not self:
            x += parent._x
            y += parent._y
            parent = parent._parent
        return x, y

    def _origin(self, view: tuple[int, int] | None = None) -> tuple[int, int]:
        """The world pixel at the top-left of the screen, after the camera has followed."""
        view_width, view_height = self._view_size() if view is None else view
        target = self.camera.target
        if target is None:
            wanted_x, wanted_y = self.camera.x, self.camera.y
        else:
            target_x, target_y = self._world_position(target)
            wanted_x = round(target_x) - view_width // 2
            wanted_y = round(target_y) - view_height // 2
        return (
            _clamp_axis(wanted_x, self._width, view_width),
            _clamp_axis(wanted_y, self._height, view_height),
        )

    def _changed(self) -> None:
        self._version += 1
        parent = self._parent
        if parent is not None:
            parent._changed()
            return
        for observer in list(self._observers):
            observer.refresh()

    def _compose(self, columns: int, rows: int) -> _core.Buffer:
        """The cells that show the world, ``columns`` by ``rows``, drawn again only if needed."""
        view = (columns, rows * _PIXELS_PER_CELL_ROW)
        self._last_view = view
        left, top = self._origin(view)
        key = (self._version, columns, rows, left, top)
        if key == self._cache_key and self._cache_buffer is not None:
            return self._cache_buffer
        buffer = _core.Buffer(width=columns, height=rows)
        pixels = buffer.pixels(encoding='half_blocks')
        if self._background is not None:
            red, green, blue = self._background
            pixels.draw_rgba(
                bytes((red, green, blue, 255)) * (view[0] * view[1]),
                width=view[0],
                height=view[1],
                mode='replace',
            )
        self._draw_onto(pixels, -left, -top)
        self._cache_key = key
        self._cache_buffer = buffer
        return buffer

    def _draw_onto(self, pixels: _core.PixelView, left: int, top: int) -> None:
        if self._rgba is not None:
            pixels.draw_rgba(
                self._rgba,
                width=self._width,
                height=self._height,
                x=left,
                y=top,
                mode='over',
            )
        for child in sorted(self._children, key=lambda item: item._layer):
            if child._is_visible:
                child._draw_onto(
                    pixels,
                    left + round(child._x) - child._anchor[0],
                    top + round(child._y) - child._anchor[1],
                )

    def render(
        self,
        *,
        width: int | None = None,
        height: int | None = None,
        format: Literal['text', 'ansi'] = 'text',
    ) -> str:
        """
        Draw the art to a string, without a canvas.

        Args:
            width: The width in cells. The art's own width by default.
            height: The height in cells. The art's own height in cells by default.
            format: ``'text'`` for the characters only, ``'ansi'`` with colors.

        Examples:
            ```python
            import xnano

            heart = xnano.draw(['R.R', 'RRR'], {'R': 'red'})
            assert heart.render() == ' ▄'
            ```
        """
        columns = self._width if width is None else width
        rows = (
            math.ceil(self._height / _PIXELS_PER_CELL_ROW) if height is None else height
        )
        return self._compose(columns, rows).render(format=format)

    def __xnano_render__(self, context: Context) -> _core.Buffer:
        """Return the cells that show the art, as large as the area it is written in."""
        owner = context.buffer
        area = owner.region
        if hasattr(owner, 'refresh'):
            self._observers.add(cast('Placement[object, object]', owner))
        area_columns, area_rows = area._grid_size()
        columns = area_columns or self._width
        rows = area_rows or math.ceil(self._height / _PIXELS_PER_CELL_ROW)
        return self._compose(columns, rows)

    def _placed(self, target: object, component: object) -> None:
        """Start the effects of ``draw(effects=...)`` on a placement that shows this art."""
        if self._effects:
            apply_effects(cast('Placement[object, object]', target), self._effects)

    def _copy(self) -> Art:
        """A new art with the same pixels, background and solid ground, and no parent."""
        copy = Art(
            self._rgba,
            self._width,
            self._height,
            effects=self._effects,
        )
        copy._background = self._background
        copy._solid_map = self._solid_map
        copy._anchor = self._anchor
        copy._x, copy._y = self._x, self._y
        copy._layer = self._layer
        for child in self._children:
            copy.add(
                child._copy(),
                x=child._x,
                y=child._y,
                layer=child._layer,
                anchor=child._anchor,
                is_solid=child._blocks_movement,
            )
        return copy

    def __repr__(self) -> str:
        return (
            f'Art(width={self._width}, height={self._height}, x={self._x:g}, y={self._y:g}, '
            f'children={len(self._children)})'
        )


def draw(
    source: str | Sequence[str] | Image | TerminalImage | bytes | bytearray | None = None,
    palette: Mapping[str, ColorValue] | str | None = None,
    *,
    width: int | None = None,
    height: int | None = None,
    background: ColorValue | None = None,
    symbol: str | None = None,
    effects: Sequence[RenderableEffectSpecification] = (),
) -> Art:
    """
    Build pixel art from text, a picture, bytes or nothing (does not draw).

    This is how pixel-art sprites are written in code, one character per pixel. Nothing is
    drawn: the art is a value that you write into a canvas. Text rows (a multi-line string, which
    may be indented, or a list of rows) are painted with a palette that says what each
    character means; any character the palette does not name, such as ``'.'``, is a
    transparent pixel. The palette is a mapping, or one string of ``character=color`` pairs.

    What ``source`` is decides what is made:

    * Text with a newline, or a list of rows: pixel art painted with ``palette``.
    * Text without a newline: the name of a registered art or image (see
      [`symbols`][xnano.symbols]); you get a copy of the art, or the pixels of the image.
      A one-row picture is a list, ``draw(['GG'], palette)``, so that a call never changes
      meaning because a symbol was registered later.
    * An [`Image`][xnano.Image] or a ``TerminalImage`` from ``xnano_image``: its pixels are copied
      (the first frame of an animation).
    * ``bytes`` of red, green, blue and alpha, with ``width`` and ``height``.
    * ``None``: a blank world of ``width`` by ``height`` pixels filled with ``background``.

    Args:
        source: What to draw.
        palette: The color of each character of text rows, as a mapping to names,
            ``'#rrggbb'`` strings or ``(red, green, blue)`` tuples, or as a string such as
            ``'R=#e03040 G=green'``.
        width: The width in pixels of ``bytes`` or of a blank world.
        height: The height in pixels.
        background: The color behind the art. Transparent pixels show it.
        symbol: A name to register the art under, so ``draw('name')`` returns a copy of it.
        effects: Effects to start on the placement when the art is written, as dictionaries
            with a ``kind`` key.

    Raises:
        ValueError: The rows are empty or differ in length, the palette or a color in it is
            not valid, a text without a newline is not a known symbol, or the sizes do not
            match the bytes.
        TypeError: ``source`` is not one of the kinds above.

    Examples:
        ```python
        import xnano

        heart = xnano.draw(
            '''
            .RR.RR.
            RRRRRRR
            .RRRRR.
            ..RRR..
            ...R...
            ''',
            'R=#e03040',
        )
        assert (heart.width, heart.height) == (7, 5)
        print(heart.render())

        xnano.draw(['G'], {'G': 'green'}, symbol='grass')
        assert xnano.draw('grass').width == 1
        ```
    """
    if isinstance(source, str) and '\n' not in source:
        if source in symbols.names(kind=Image):
            # The name of a registered image draws that image.
            source = symbols.lookup(source, kind=Image)
    if isinstance(source, str) and '\n' not in source:
        try:
            registered = symbols.lookup(source, kind=Art)
        except ValueError as error:
            raise ValueError(
                f'{error} To draw a one-row picture, pass a list: draw([{source!r}], '
                f'palette).'
            ) from None
        art = registered._copy()
        if background is not None:
            art.background = background
        effects = cast(
            'tuple[RenderableEffectSpecification, ...]',
            effect_sequence(effects, 'renderable'),
        )
        if effects:
            for effect in effects:
                normalize_effect(effect, 'renderable')
            art._effects = effects
        if symbol is not None:
            symbols.register(symbol, art)
            art._symbol = symbol
        return art
    rgba, pixel_width, pixel_height = _pixels_of(source, palette, width, height)
    return Art(
        rgba,
        pixel_width,
        pixel_height,
        background=background,
        symbol=symbol,
        effects=effects,
    )


def _pixels_of(
    source: object,
    palette: Mapping[str, ColorValue] | str | None,
    width: int | None,
    height: int | None,
) -> tuple[bytes | None, int, int]:
    """The RGBA bytes, width and height that a source of ``draw`` stands for."""
    if isinstance(source, str):
        if '\n' not in source:
            raise ValueError(
                f'{source!r} has no newline, so it would be the name of a registered art. '
                f'For a one-row picture pass a list: [{source!r}].'
            )
        return _rows_to_pixels(source, palette)
    if isinstance(source, Sequence) and not isinstance(source, (bytes, bytearray)):
        return _rows_to_pixels(source, palette)
    if source is None:
        if width is None or height is None:
            raise ValueError(
                'A blank world needs a size in pixels: draw(None, width=40, height=20).'
            )
        return None, width, height
    if isinstance(source, (bytes, bytearray)):
        if width is None or height is None:
            raise ValueError(
                'Pixel bytes need the size of the picture: draw(data, width=..., height=...).'
            )
        if len(source) != width * height * _RGBA:
            raise ValueError(
                f'{width} by {height} pixels need {width * height * _RGBA} bytes of red, '
                f'green, blue and alpha, but got {len(source)}.'
            )
        return bytes(source), width, height
    picture = source.decoded if isinstance(source, Image) else source
    if is_image(picture):
        return (
            bytes(picture.to_rgba(0)),  # type: ignore[attr-defined]
            picture.width,  # type: ignore[attr-defined]
            picture.height,  # type: ignore[attr-defined]
        )
    raise TypeError(
        f'draw() cannot make art from a {type(source).__name__}. Pass text rows with a '
        f'palette, an Image, bytes with width= and height=, a symbol name, or None with a '
        f'size.'
    )


def _rows_to_pixels(
    art: str | Sequence[str], palette: Mapping[str, ColorValue] | str | None
) -> tuple[bytes, int, int]:
    if palette is None:
        raise ValueError(
            'Text rows need a palette that says what each character means: draw(rows, '
            "{'#': 'white'}), or draw(rows, '#=white .=black'). A character the palette "
            'does not name is transparent.'
        )
    rows = _art_rows(art)
    colors = _palette_colors(palette)
    if not rows or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError(
            'draw needs at least one row, and every row the same length, but got '
            f'row lengths {[len(row) for row in rows]}. Pad the short rows with ".".'
        )
    if len(rows[0]) > MOST_CELLS:
        raise ValueError(
            f'draw() takes rows of at most {MOST_CELLS} characters, but the rows have '
            f'{len(rows[0])}. Pass shorter rows, or split the picture in several.'
        )
    channels = {character: (*to_rgb(color), 255) for character, color in colors.items()}
    transparent = bytes(_RGBA)
    pixels = b''.join(
        bytes(channels[character]) if character in channels else transparent
        for row in rows
        for character in row
    )
    return pixels, len(rows[0]), len(rows)


def _art_rows(art: str | Sequence[str]) -> list[str]:
    if not isinstance(art, str):
        return list(art)
    lines = textwrap.dedent(art).splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def _palette_colors(palette: Mapping[str, ColorValue] | str) -> Mapping[str, ColorValue]:
    if not isinstance(palette, str):
        if not isinstance(palette, Mapping):
            raise TypeError(
                f'The palette is a mapping from a character to a color, or a string of '
                f"character=color pairs, but got {palette!r}. Pass {{'#': 'white'}} or "
                f"'#=white .=black'."
            )
        return palette
    colors: dict[str, ColorValue] = {}
    for pair in palette.split():
        character, separator, color = pair.partition('=')
        if not separator or len(character) != 1 or not color:
            raise ValueError(
                f'{pair!r} is not a palette entry. Write one character, an equals sign and a '
                f"color, such as 'R=#e03040 G=green', and separate entries with spaces."
            )
        colors[character] = color
    return colors
