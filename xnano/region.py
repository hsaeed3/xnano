"""
xnano.region

A rectangle of cells: standalone, or a live view of a canvas or a placement.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import (
    TYPE_CHECKING,
    Final,
    Literal,
    TypeAlias,
    cast,
    overload,
)

import xnano_core as _core
from xnano._appearance import (
    APPEARANCE_NAMES,
    Appearance,
    Spacing,
    check_border_kind,
)
from xnano._axes import check_point, to_rgb
from xnano._decoration import insets_for, paint_decoration
from xnano._values import RGB, ColorValue
from xnano.appearance import (
    BorderAppearance,
    Colors,
    MarginAppearance,
    PaddingAppearance,
    _Looked,
)
from xnano.errors import TerminalError
from xnano.pixel import Pixel

if TYPE_CHECKING:
    from typing_extensions import Unpack
    from xnano_image import TerminalImage

    from xnano._media import Image
    from xnano._values import Content
    from xnano.canvas import Canvas
    from xnano.context import Context
    from xnano.placement import Placement
    from xnano.types import AppearanceArguments

__all__ = ['Region', 'box', 'write']

Resolution: TypeAlias = Literal['cells', 'half_blocks', 'braille']
PixelAnchor: TypeAlias = Literal['top_left', 'center', 'bottom_right']

_BRAILLE_BITS: Final = ((0x01, 0x08), (0x02, 0x10), (0x04, 0x20), (0x40, 0x80))
_BLANK: Final = _core.Cell(' ')

_VIEW_APPEARANCE_MESSAGE: Final = (
    'Set canvas.{name} (or placement.{name}) instead of region.{name}: a view of a canvas '
    'or a placement has no appearance of its own. Only a region from xnano.write() or '
    'xnano.box() does.'
)


def _is_color(value: object) -> bool:
    if isinstance(value, _core.Color):
        return True
    return (
        isinstance(value, tuple)
        and len(value) == 3
        and all(
            isinstance(channel, int) and not isinstance(channel, bool)
            for channel in value
        )
    )


def _plain(color: _core.Color | None) -> ColorValue | None:
    """A cell color as a pixel color: ``None`` where the terminal's own color shows."""
    return None if color is None or color.is_reset else color


def _snapshot(surface: _core.Surface) -> _core.Buffer:
    return _core.Buffer.from_cell_grid(surface.to_cell_grid())


class Region(_Looked):
    """
    A rectangle of cells that you can read and write, one cell or dot at a time.

    A region is either *standalone*, made by [`write`][xnano.write] or [`box`][xnano.box],
    which owns its cells and can be written into a canvas, or a *live view* of the cells of
    a canvas or a placement, from ``canvas.region`` and ``placement.region``. Coordinates are
    region coordinates, ``(0, 0)`` being the top-left cell. ``(x, y) in region`` and
    ``region.local(point)`` use screen cells, the frame of ``context.mouse.position``.

    The default resolution is one cell. ``region.half_blocks`` addresses two pixels per cell
    (one above the other) and ``region.braille`` eight dots per cell (two by four, one color
    for the whole cell). Reading gives a [`Pixel`][xnano.pixel.Pixel]; assigning accepts a
    pixel, a color (the background of a cell, the color of a pixel or dot), a ``str`` (text)
    or, over a slice, anything ``write`` accepts.

    A standalone region owns ``color``, ``border``, ``padding`` and ``margin`` and draws
    them in its own cells, so its coordinates include them: ``(0, 0)`` of a bordered region
    is the corner of the border. On a live view they belong to the canvas or the placement,
    and the coordinates address the area inside them. A region written into a canvas is a
    snapshot: changing the region afterwards changes nothing on the canvas. A region made by
    ``write`` draws its text again whenever its look changes, so cells you edited are
    replaced; edit the cells of a ``box`` instead.

    Attributes:
        width: The width in cells, or in pixels or dots at the other resolutions.
        height: The height in cells, or in pixels or dots at the other resolutions.
        x: The screen column of the left edge.
        y: The screen row of the top edge.
        resolution: ``'cells'``, ``'half_blocks'`` or ``'braille'``.
        braille: The same cells as braille dots.
        half_blocks: The same cells as half-block pixels.
        color: The colors of a standalone region.
        border: The border of a standalone region.
        padding: The padding of a standalone region.
        margin: The margin of a standalone region.

    Examples:
        ```python
        import xnano

        card = xnano.write('hello', border='rounded')
        assert card.render().splitlines()[0] == '╭─────╮'

        with xnano.new(width=8, height=2) as canvas:
            region = canvas.region
            region[0:4, 0:1] = 'abcd'
            region[5, 0] = xnano.Pixel('diamond', foreground='red')
            region[0, 1] = (0, 0, 255)
            assert region[5, 0].character == '◆'
            assert region[1, 0].character == 'b'
            assert (1, 1) in region
            dots = region.braille
            assert (dots.width, dots.height) == (16, 8)
        ```
    """

    def __init__(
        self,
        buffer: _core.Buffer,
        *,
        owner: Canvas[object, object] | Placement[object, object] | None = None,
        inset: tuple[int, int, int, int] = (0, 0, 0, 0),
        resolution: Resolution = 'cells',
        is_standalone: bool = False,
        look: Appearance | None = None,
        is_text: bool = False,
    ) -> None:
        """
        Wrap a buffer. Get a region from ``write``, ``box`` or ``canvas.region`` instead.

        Args:
            buffer: The core buffer whose cells the region addresses.
            owner: The canvas or placement a live view belongs to.
            inset: Cells left out on the left, top, right and bottom of the buffer.
            resolution: ``'cells'``, ``'half_blocks'`` or ``'braille'``.
            is_standalone: Whether the region owns its buffer and its look.
            look: The look of a standalone region.
            is_text: Whether a standalone region shows the text of its look.
        """
        self._buffer = buffer
        self._owner = owner
        self._inset = inset
        self._resolution: Resolution = resolution
        self._is_standalone = is_standalone
        self._is_text = is_text
        self._appearance = look
        self._canvas: Canvas[object, object] | None = None
        self._insets_applied: tuple[int, int, int, int] | None = None

    @classmethod
    def _from_buffer(cls, buffer: _core.Buffer) -> Region:
        """A standalone region that owns ``buffer`` and has no look."""
        return cls(buffer, is_standalone=True)

    # -- the look (standalone only) ------------------------------------------------------

    def _require_standalone(self, name: str) -> None:
        if not self._is_standalone:
            raise TerminalError(_VIEW_APPEARANCE_MESSAGE.format(name=name))

    @property
    def color(self) -> Colors:  # type: ignore[override]
        """The colors of a standalone region; see [`Colors`][xnano.appearance.Colors]."""
        self._require_standalone('color')
        return Colors(self)

    @property
    def border(self) -> BorderAppearance:  # type: ignore[override]
        """The border of a standalone region; see [`BorderAppearance`][xnano.appearance.BorderAppearance]."""
        self._require_standalone('border')
        return BorderAppearance(self)

    @border.setter
    def border(self, value: _core.BorderKind | bool) -> None:
        self._require_standalone('border')
        BorderAppearance(self)._assign_all(value)

    @property
    def padding(self) -> PaddingAppearance:  # type: ignore[override]
        """The padding of a standalone region; see [`Edges`][xnano.appearance.Edges]."""
        self._require_standalone('padding')
        return PaddingAppearance(self)

    @padding.setter
    def padding(self, value: Spacing) -> None:
        self._require_standalone('padding')
        PaddingAppearance(self)._assign_all(value)

    @property
    def margin(self) -> MarginAppearance:  # type: ignore[override]
        """The margin of a standalone region; see [`Edges`][xnano.appearance.Edges]."""
        self._require_standalone('margin')
        return MarginAppearance(self)

    @margin.setter
    def margin(self, value: Spacing) -> None:
        self._require_standalone('margin')
        MarginAppearance(self)._assign_all(value)

    def _look_text(self) -> str:
        return self._buffer.text

    def _look_canvas(self) -> Canvas[object, object] | None:
        return self._canvas

    def _look_size(self) -> tuple[int, int]:
        return (self._buffer.width, self._buffer.height)

    def _redraw_look(self) -> None:
        """Draw the look into the cells of a standalone region."""
        look = self._appearance
        if look is None:
            return
        buffer = self._buffer
        if self._is_text and not look.sides:
            drawn = look.snapshot()
            buffer.width = drawn.width
            buffer.height = drawn.height
            buffer.update(_core.Fill(_BLANK), _core.Paste(drawn, mode='replace'))
            return
        content: _core.Buffer | None = None
        if self._is_text:
            content = look.text_buffer()
            insets = insets_for(look, content.width, content.height)
            buffer.width = content.width + insets.horizontal
            buffer.height = content.height + insets.vertical
        else:
            # A box keeps its outer size, and its content is whatever is inside the ring.
            previous = self._insets_applied
            if previous is not None:
                left, top, right, bottom = previous
                inner_width = max(0, buffer.width - left - right)
                inner_height = max(0, buffer.height - top - bottom)
                if inner_width and inner_height:
                    content = _snapshot(
                        buffer[left : left + inner_width, top : top + inner_height]
                    )
            insets = insets_for(look, buffer.width, buffer.height)
        paint_decoration(buffer, look, insets)
        if content is not None and content.width and content.height:
            buffer.update(
                _core.Paste(content, x=insets.left, y=insets.top, mode='replace')
            )
        self._insets_applied = insets.as_tuple()

    # -- geometry ------------------------------------------------------------------------

    def _surface(self) -> _core.Surface:
        """The cells this region addresses."""
        self._flush_look()
        buffer = self._buffer
        left, top, right, bottom = self._inset
        if not (left or top or right or bottom):
            return buffer
        return buffer[
            left : max(left, buffer.width - right), top : max(top, buffer.height - bottom)
        ]

    def _cell_size(self) -> tuple[int, int]:
        self._flush_look()
        left, top, right, bottom = self._inset
        return (
            max(0, self._buffer.width - left - right),
            max(0, self._buffer.height - top - bottom),
        )

    @property
    def width(self) -> int:
        """The width in cells, or in pixels or dots at the other resolutions."""
        width = self._cell_size()[0]
        return width * 2 if self._resolution == 'braille' else width

    @property
    def height(self) -> int:
        """The height in cells, or in pixels or dots at the other resolutions."""
        height = self._cell_size()[1]
        if self._resolution == 'half_blocks':
            return height * 2
        return height * 4 if self._resolution == 'braille' else height

    @property
    def resolution(self) -> Resolution:
        """``'cells'``, ``'half_blocks'`` (1 by 2 per cell) or ``'braille'`` (2 by 4)."""
        return self._resolution

    @property
    def x(self) -> int:
        """The screen column of the region's left edge; 0 for a region that is not on screen."""
        try:
            bounds = self._buffer._absolute_bounds
        except Exception:
            return self._inset[0]
        return int(bounds.x) + self._inset[0]

    @property
    def y(self) -> int:
        """The screen row of the region's top edge; 0 for a region that is not on screen."""
        try:
            bounds = self._buffer._absolute_bounds
        except Exception:
            return self._inset[1]
        return int(bounds.y) + self._inset[1]

    def __contains__(self, point: object) -> bool:
        """
        Whether a screen cell is inside the region.

        Args:
            point: A ``(x, y)`` pair or a [`Point`][xnano_core.Point] in screen cells, such
                as ``context.mouse.position``.
        """
        if isinstance(point, _core.Point):
            column, row = point.x, point.y
        elif isinstance(point, tuple) and len(point) == 2:
            column, row = point
        else:
            return False
        width, height = self._cell_size()
        origin_x = self.x
        origin_y = self.y
        return (
            origin_x <= column < origin_x + width and origin_y <= row < origin_y + height
        )

    def local(self, point: _core.Point) -> _core.Point:
        """
        Convert a screen cell into a cell of this region.

        Args:
            point: A cell in screen coordinates, such as ``context.mouse.position``.
        """
        point = check_point(point)
        return _core.Point(point.x - self.x, point.y - self.y)

    def resize(self, width: int, height: int) -> None:
        """
        Change the size of the region, in cells.

        On a view of a placement this resizes the placement. A standalone region made by
        [`box`][xnano.box] keeps its cells where they fit. A region made by
        [`write`][xnano.write] is sized by its text, border, padding and margin, so it
        cannot be resized.

        Args:
            width: The new width in cells.
            height: The new height in cells.

        Raises:
            TerminalError: The region is the view of a canvas, whose size follows its screen,
                or it was made by ``write``, whose size follows its text.
            ValueError: A size is below 1.
        """
        _check_cell_counts('resize', width, height)
        if width < 1 or height < 1:
            raise ValueError(
                f'A region is at least 1 by 1 cells, but resize got {width} by {height}. '
                f'Pass whole numbers of cells, 1 or more.'
            )
        owner = self._owner
        if self._is_standalone and self._is_text:
            raise TerminalError(
                'A region made by write() is sized by its text, border, padding and margin, '
                'so resize() cannot change it. Make a region of a size you choose with '
                'xnano.box(width, height), or change the text or the padding.'
            )
        if self._is_standalone:
            self._buffer.width = width
            self._buffer.height = height
            return
        if owner is None or not hasattr(owner, '_set_axis'):
            raise TerminalError(
                'The size of a canvas follows its screen or its width and height; set '
                'those instead of resizing its region.'
            )
        left, top, right, bottom = self._inset
        placement = cast('Placement[object, object]', owner)
        placement.width = width + left + right
        placement.height = height + top + bottom

    # -- the resolution views ------------------------------------------------------------

    def _view(self, resolution: Resolution) -> Region:
        view = Region(
            self._buffer,
            owner=self._owner,
            inset=self._inset,
            resolution=resolution,
            is_standalone=False,
        )
        view._canvas = self._canvas
        if self._is_standalone:
            view._appearance = None
        return view

    @property
    def braille(self) -> Region:
        """
        The same cells as braille dots: two columns and four rows per cell.

        A dot is drawn in the color of its cell, so the eight dots of a cell share one color.

        Examples:
            ```python
            import xnano

            with xnano.new(width=4, height=2) as canvas:
                dots = canvas.region.braille
                dots[0, 0] = (255, 255, 255)
                assert dots[0, 0].character == '•'
                assert dots[1, 0].character == ' '
            ```
        """
        return self._view('braille')

    @property
    def half_blocks(self) -> Region:
        """The same cells as pixels, two to a cell: one above the other."""
        return self._view('half_blocks')

    def _pixel_view(self) -> _core.PixelView:
        encoding = 'braille' if self._resolution == 'braille' else 'half_blocks'
        return self._surface().pixels(encoding=encoding)

    # -- reading -------------------------------------------------------------------------

    def _check_point(self, key: object) -> None:
        if isinstance(key, _core.Point):
            raise TypeError(
                'region[...] takes region cells, but this is a screen cell. Convert it '
                'first: region[region.local(point).x, region.local(point).y].'
            )
        if not isinstance(key, tuple) or len(key) != 2:
            raise TypeError(
                f'A region is indexed by (x, y), such as region[3, 1] or region[0:5, 0:2], '
                f'but got {key!r}.'
            )

    def _check_bounds(self, x: object, y: object) -> tuple[int, int]:
        if (
            isinstance(x, bool)
            or isinstance(y, bool)
            or not isinstance(x, int)
            or not isinstance(y, int)
        ):
            raise TypeError(
                f'A region coordinate is a whole number or a slice, but got ({x!r}, {y!r}).'
            )
        width = self.width
        height = self.height
        if not (0 <= x < width and 0 <= y < height):
            raise IndexError(
                f'The coordinates ({x}, {y}) are outside this region. Region coordinates '
                f"start at (0, 0) in the region's top-left corner: x runs from 0 to "
                f'{width - 1} and y from 0 to {height - 1}. A screen cell, such as '
                f'context.mouse.position, needs region.local(point) first.'
            )
        return x, y

    @overload
    def __getitem__(self, key: tuple[int, int]) -> Pixel: ...  # pyright: ignore[reportOverlappingOverload]
    @overload
    def __getitem__(self, key: tuple[int | slice, int | slice]) -> Region: ...
    def __getitem__(self, key: tuple[int | slice, int | slice]) -> Pixel | Region:
        """
        Read a cell (a [`Pixel`][xnano.pixel.Pixel]) or take a part of the region.

        Args:
            key: ``(x, y)`` in region coordinates, or two slices without a step.

        Raises:
            IndexError: A coordinate is outside the region; the message names the valid ranges.
            TypeError: The key is a screen [`Point`][xnano_core.Point] or not a pair.
            ValueError: A slice has a step, or a slice is taken from a pixel resolution.
        """
        if type(key) is tuple and len(key) == 2 and self._resolution == 'cells':
            column, row = key
            if type(column) is int and type(row) is int:
                self._flush_look()
                buffer = self._buffer
                if (
                    not any(self._inset)
                    and 0 <= column < buffer.width
                    and 0 <= row < buffer.height
                ):
                    cell = buffer[column, row]
                    foreground = cell.foreground
                    background = cell.background
                    return Pixel._of(
                        cell.symbol,
                        None if foreground is None or foreground.is_reset else foreground,
                        None if background is None or background.is_reset else background,
                    )
        self._check_point(key)
        column, row = key
        if isinstance(column, slice) or isinstance(row, slice):
            if self._resolution != 'cells':
                raise ValueError(
                    f'A slice of a {self._resolution} region would cut cells in two. '
                    f'Take the slice from the cell region (region[0:5, 0:2]) and then '
                    f'use .{self._resolution}.'
                )
            width, height = self._cell_size()
            first_x, last_x = self._span(column, width, 'x')
            first_y, last_y = self._span(row, height, 'y')
            left, top, right, bottom = self._inset
            view = Region(
                self._buffer,
                owner=self._owner,
                inset=(
                    left + first_x,
                    top + first_y,
                    right + (width - last_x),
                    bottom + (height - last_y),
                ),
            )
            view._canvas = self._canvas
            return view
        column, row = self._check_bounds(column, row)
        surface = self._surface()
        if self._resolution == 'cells':
            cell = surface[column, row]
            return Pixel._of(
                cell.symbol, _plain(cell.foreground), _plain(cell.background)
            )
        if self._resolution == 'half_blocks':
            cell = surface[column, row // 2]
            is_top = row % 2 == 0
            symbol = cell.symbol
            if symbol == '▀':
                color = cell.foreground if is_top else cell.background
            elif symbol == '▄':
                color = cell.background if is_top else cell.foreground
            elif symbol == '█':
                color = cell.foreground
            else:
                color = cell.background
            plain = _plain(color)
            return Pixel._of('█', plain) if plain is not None else Pixel._of(' ')
        cell = surface[column // 2, row // 4]
        code = ord(cell.symbol[0]) - 0x2800 if cell.symbol else -1
        is_set = 0 <= code <= 0xFF and bool(code & _BRAILLE_BITS[row % 4][column % 2])
        return Pixel._of('•', _plain(cell.foreground)) if is_set else Pixel._of(' ')

    @staticmethod
    def _span(index: object, size: int, name: str) -> tuple[int, int]:
        if isinstance(index, slice):
            start, stop, step = index.indices(size)
            if step != 1:
                raise ValueError(
                    f'A region is a rectangle, so a slice of {name} cannot have a step '
                    f'(it was {index.step}). Write region[0:5, 0:2] instead of '
                    f'region[0:5:2, 0:2].'
                )
            return start, max(start, stop)
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError(
                f'A region coordinate is a whole number or a slice, but got {index!r}.'
            )
        if not 0 <= index < size:
            raise IndexError(
                f'The {name} coordinate {index} is outside this region, which has {size} '
                f'cells along {name}. Region coordinates start at 0 in the top-left corner.'
            )
        return index, index + 1

    # -- writing -------------------------------------------------------------------------

    def __setitem__(
        self,
        key: tuple[int | slice, int | slice],
        value: Pixel | _core.Color | tuple[int, int, int] | str | object,
    ) -> None:
        """
        Write a pixel, a color, text or content into a cell or a part of the region.

        * A [`Pixel`][xnano.pixel.Pixel] writes its character and colors; over a slice it fills it.
        * A [`Color`][xnano_core.Color] or an ``(red, green, blue)`` tuple sets the background
          of a cell (the color of a pixel or dot at the other resolutions). A ``str`` is never
          a color: make one with ``Color('#336699')``.
        * A ``str`` is text, written from the cell and clipped at the slice.
        * Any other content that ``write`` accepts covers a slice.

        Args:
            key: ``(x, y)`` in region coordinates, or two slices without a step.
            value: What to write.

        Raises:
            IndexError: A coordinate is outside the region.
            TypeError: A single cell was given content that needs a slice, a screen
                [`Point`][xnano_core.Point] was used as the key, or text was written at a
                pixel resolution.
            ValueError: A slice has a step.
        """
        if type(key) is tuple and len(key) == 2 and self._resolution == 'cells':
            column, row = key
            if type(column) is int and type(row) is int and type(value) is Pixel:
                self._flush_look()
                buffer = self._buffer
                if (
                    not any(self._inset)
                    and 0 <= column < buffer.width
                    and 0 <= row < buffer.height
                ):
                    buffer[column, row] = value.cell()
                    return
        self._check_point(key)
        column, row = key
        if isinstance(column, int) and isinstance(row, int):
            x, y = self._check_bounds(column, row)
            self._set_cell(x, y, value)
            return
        width, height = self.width, self.height
        first_x, last_x = self._span(column, width, 'x')
        first_y, last_y = self._span(row, height, 'y')
        if last_x <= first_x or last_y <= first_y:
            return
        self._set_block(first_x, last_x, first_y, last_y, value)

    def _set_cell(self, x: int, y: int, value: object) -> None:
        resolution = self._resolution
        if isinstance(value, Pixel):
            if resolution == 'cells':
                self._surface()[x, y] = value.cell()
                return
            color = value.foreground if value.foreground is not None else value.background
            if color is not None:
                self._pixel_view().write([(x, y, to_rgb(color))])
            return
        if _is_color(value):
            if resolution == 'cells':
                self._surface().set_background_colors(
                    [cast('ColorValue', value)], width=1, x=x, y=y
                )
            else:
                self._pixel_view().write([(x, y, to_rgb(cast('ColorValue', value)))])
            return
        if isinstance(value, str):
            if resolution != 'cells':
                raise TypeError(
                    f'Text is written at cell resolution, but this region is '
                    f'{resolution}. Write the text into the cell region instead.'
                )
            self._surface().write(value, x=x, y=y)
            return
        raise TypeError(
            'A single cell takes a str, a color or a Pixel. To place other content over '
            'an area, index with two slices, such as region[0:5, 0:2].'
        )

    def _set_block(
        self, first_x: int, last_x: int, first_y: int, last_y: int, value: object
    ) -> None:
        resolution = self._resolution
        if resolution != 'cells':
            if isinstance(value, Pixel):
                color = (
                    value.foreground if value.foreground is not None else value.background
                )
                if color is None:
                    return
            elif _is_color(value):
                color = cast('ColorValue', value)
            else:
                raise TypeError(
                    f'A {resolution} region takes a color or a Pixel, but got '
                    f'{type(value).__name__}. Write text and content into the cell region.'
                )
            channels = to_rgb(color)
            self._pixel_view().write(
                (x, y, channels)
                for y in range(first_y, last_y)
                for x in range(first_x, last_x)
            )
            return
        surface = self._surface()
        part = surface[first_x:last_x, first_y:last_y]
        if isinstance(value, Pixel):
            part.fill(value.cell())
        elif _is_color(value):
            part.update(_core.Background(cast('ColorValue', value)))
        elif isinstance(value, str):
            part.update(_core.Write(value))
        else:
            self._cover(first_x, last_x, first_y, last_y, value)

    def _cover(
        self, first_x: int, last_x: int, first_y: int, last_y: int, value: object
    ) -> None:
        owner = self._owner
        if owner is not None and not self._is_standalone:
            left, top, _, _ = self._inset
            cast('Placement[object, object]', owner).write(
                cast('Content', value),
                x=left + first_x,
                y=top + first_y,
                width=last_x - first_x,
                height=last_y - first_y,
            )
            return
        from xnano._media import content_buffer

        content, _ = content_buffer(cast('Content', value))
        copy = content.copy()
        copy.width = last_x - first_x
        copy.height = last_y - first_y
        self._surface().update(_core.Paste(copy, x=first_x, y=first_y, mode='replace'))

    # -- drawing -------------------------------------------------------------------------

    def shade(self, function: Callable[[int, int], ColorValue | None]) -> None:
        """
        Color every cell, pixel or dot from a function of its position, in one write.

        At the default resolution the function is called for each cell and the result is
        the cell's background; ``region.half_blocks.shade`` and ``region.braille.shade`` call
        it for each pixel or dot.

        Args:
            function: Called with ``(x, y)`` in region coordinates; return the color, or
                ``None`` to leave the cell alone.

        Examples:
            ```python
            import xnano

            with xnano.new(width=4, height=2) as canvas:
                canvas.region.shade(lambda x, y: (x * 60, y * 60, 0) if x < 3 else None)
                assert canvas.region[2, 1].background.to_rgb() == (120, 60, 0)
                canvas.region.half_blocks.shade(lambda x, y: (0, y * 30, 0))
                assert canvas.region.half_blocks[0, 3].foreground is not None
            ```
        """
        if self._resolution == 'cells':
            width, height = self._cell_size()
            if width == 0 or height == 0:
                return
            colors = [
                function(column, row) for row in range(height) for column in range(width)
            ]
            self._surface().set_background_colors(colors, width=width)
            return
        view = self._pixel_view()
        colored: list[tuple[int, int, RGB]] = []
        for row in range(view.height):
            for column in range(view.width):
                color = function(column, row)
                if color is not None:
                    colored.append((column, row, to_rgb(color)))
        view.write(colored)

    def _shade_foreground(
        self, function: Callable[[int, int], ColorValue | None]
    ) -> None:
        """Color the text of every cell from a function of its position, in one write."""
        width, height = self._cell_size()
        if width == 0 or height == 0:
            return
        colors = [
            function(column, row) for row in range(height) for column in range(width)
        ]
        self._surface().set_foreground_colors(colors, width=width)

    def draw_color_bytes(
        self,
        data: bytes,
        *,
        width: int,
        height: int,
        x: int = 0,
        y: int = 0,
        mode: _core.RasterMode = 'over',
    ) -> None:
        """
        Draw a row-major RGBA image with its top-left pixel at ``(x, y)``.

        At the default resolution the image is drawn with half-block pixels.

        Args:
            data: ``width * height * 4`` bytes of red, green, blue and alpha.
            width: The image width in pixels.
            height: The image height in pixels.
            x: The pixel column of the image's left edge.
            y: The pixel row of the image's top edge.
            mode: ``'over'`` blends by alpha; ``'replace'`` overwrites.
        """
        self._pixel_view().draw_rgba(
            data, width=width, height=height, x=x, y=y, mode=mode
        )

    def draw_image(
        self,
        image: Image | TerminalImage,
        *,
        x: int = 0,
        y: int = 0,
        mode: _core.RasterMode = 'over',
        frame_index: int = 0,
    ) -> None:
        """
        Draw an image with its top-left pixel at ``(x, y)``.

        Pixels outside the region are skipped, so drawing a large image at a negative ``x``
        and ``y`` scrolls it. At the default resolution the image is drawn with half-block
        pixels.

        Args:
            image: An [`Image`][xnano.Image] or a picture from ``xnano.image``. It needs the
                optional ``xnano-image`` package.
            x: The pixel column of the image's left edge. May be negative.
            y: The pixel row of the image's top edge. May be negative.
            mode: ``'over'`` blends by alpha; ``'replace'`` overwrites.
            frame_index: Which frame of an animated image to draw.
        """
        from xnano._media import Image as MediaImage

        picture = image.image if isinstance(image, MediaImage) else image
        if not hasattr(picture, 'to_rgba'):
            raise TypeError(
                f'draw_image() takes an xnano.Image or a picture from xnano.image, but got '
                f'{image!r}. Load one with xnano.from_image(path) first.'
            )
        self.draw_color_bytes(
            picture.to_rgba(frame_index),
            width=picture.width,
            height=picture.height,
            x=x,
            y=y,
            mode=mode,
        )

    def cell_for_pixel(self, x: int, y: int) -> tuple[int, int]:
        """
        Return the cell that holds a pixel or dot.

        Args:
            x: The pixel or dot column.
            y: The pixel or dot row.
        """
        if self._resolution == 'cells':
            return (x, y)
        return self._pixel_view().cell_at(x, y)

    def pixel_for_cell(
        self, x: int, y: int, *, anchor: PixelAnchor = 'center'
    ) -> tuple[int, int]:
        """
        Return the pixel or dot at an anchor of a cell.

        The mouse reports cells; this picks one pixel of the cell the pointer is over.

        Args:
            x: The cell column.
            y: The cell row.
            anchor: Which pixel of the cell to return.
        """
        if self._resolution == 'cells':
            return (x, y)
        return self._pixel_view().pixel_at(x, y, anchor=anchor)

    def copy(self) -> Region:
        """Return a standalone region with a copy of these cells and, for one, its look."""
        copy = Region(_snapshot(self._surface()), is_standalone=True)
        if self._is_standalone and self._appearance is not None:
            import dataclasses

            copy._appearance = dataclasses.replace(
                self._appearance, sides=dict(self._appearance.sides)
            )
            copy._is_text = self._is_text
            copy._insets_applied = self._insets_applied
        return copy

    def render(self, *, format: Literal['text', 'ansi'] = 'text') -> str:
        """
        Draw the region to a string.

        Args:
            format: ``'text'`` for the characters only, ``'ansi'`` with colors and styles.

        Examples:
            ```python
            import xnano

            assert xnano.write('hi', padding=1).render().splitlines() == ['', ' hi']
            ```
        """
        return _snapshot(self._surface()).render(format=format)

    def __str__(self) -> str:
        """Return the characters of the region, so ``print(region)`` shows it."""
        return self.render()

    def __xnano_render__(self, context: Context | None = None) -> _core.Buffer:
        """Return the buffer that shows the region: its own, or a copy for a view."""
        if self._is_standalone:
            self._flush_look()
            return self._buffer
        return _snapshot(self._surface())

    def __repr__(self) -> str:
        kind = 'standalone' if self._is_standalone else 'view'
        return (
            f'Region({kind}, width={self.width}, height={self.height}, '
            f'resolution={self._resolution!r})'
        )


_PLACEMENT_NAMES: Final = frozenset(
    {'x', 'y', 'width', 'height', 'layer', 'lock', 'effects'}
)


def _check_cell_counts(function_name: str, width: object, height: object) -> None:
    """Raise a ``TypeError`` that says what to pass when a size is not a whole number."""
    for name, value in (('width', width), ('height', height)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(
                f'{function_name}() takes the {name} as a whole number of cells, but got '
                f'{value!r}. Pass a number such as 4.'
            )


def _standalone_look(
    function_name: str, text: str, appearance: dict[str, object], default_border: bool
) -> Appearance:
    unknown = sorted(set(appearance) - APPEARANCE_NAMES)
    if unknown:
        hint = ''
        if unknown[0] in _PLACEMENT_NAMES:
            examples = {
                'lock': 'True',
                'effects': "[{'kind': 'effect.fade_to', 'foreground': 'red'}]",
            }
            hint = (
                f' Position it when you write it on a canvas: '
                f'canvas.write(region, {unknown[0]}={examples.get(unknown[0], "1")}).'
            )
        raise TypeError(
            f'{function_name}() has no setting called {unknown[0]!r}. The look of a region '
            f'is {", ".join(sorted(APPEARANCE_NAMES))}.{hint}'
        )
    settings = dict(appearance)
    check_border_kind(settings.get('border'))
    border = settings.get('border', 'plain' if default_border else None)
    if border is True:
        border = 'plain'
    elif border is False:
        border = None
    settings['border'] = border
    return Appearance(text=text, **cast('dict[str, object]', settings))  # type: ignore[arg-type]


def write(text: str, /, **appearance: Unpack[AppearanceArguments]) -> Region:
    """
    Build a standalone region from text (does not draw).

    The region is sized to the text and is a value that you write into a canvas. It owns its
    cells. Write it into a canvas with ``canvas.write(region)``, print it
    with [`render`][xnano.region.Region.render], or change its look afterwards with
    ``region.border`` and its siblings.

    Args:
        text: The text, line by line.
        appearance: The look of the text: colors, text modifiers, ``border``, ``title``,
            ``padding`` and ``margin``; see [`AppearanceArguments`][xnano.types.AppearanceArguments].

    Raises:
        TypeError: ``text`` is not a string.

    Examples:
        ```python
        import xnano

        card = xnano.write('hello', border='rounded', padding={'horizontal': 1})
        assert card.render().splitlines()[1] == '│ hello │'
        card.border = False
        assert card.render().strip() == 'hello'
        ```
    """
    if not isinstance(text, str):
        raise TypeError(
            f'xnano.write() takes text, but got {text!r}. To show other content, create a '
            f'canvas with xnano.new() and call canvas.write(content).'
        )
    look = _standalone_look('write', text, cast('dict[str, object]', appearance), False)
    region = Region(
        _core.Buffer(width=1, height=1), is_standalone=True, look=look, is_text=True
    )
    region._redraw_look()
    return region


def box(width: int, height: int, /, **appearance: Unpack[AppearanceArguments]) -> Region:
    """
    Build an empty standalone rectangle of cells with a border (does not draw).

    The region is a value that you write into a canvas.

    Args:
        width: The width in cells, border included.
        height: The height in cells, border included.
        appearance: The look of the box. ``border`` is ``'plain'`` unless you pass another
            kind or ``False``.

    Raises:
        ValueError: A size is below 1.

    Examples:
        ```python
        import xnano

        frame = xnano.box(5, 3)
        assert frame.render().splitlines() == ['┌───┐', '│   │', '└───┘']
        ```
    """
    _check_cell_counts('xnano.box', width, height)
    if width < 1 or height < 1:
        raise ValueError(
            f'A box is at least 1 by 1 cells, but got {width} by {height}. Pass whole '
            f'numbers of cells, 1 or more.'
        )
    look = _standalone_look('box', '', cast('dict[str, object]', appearance), True)
    region = Region(
        _core.Buffer(width=width, height=height),
        is_standalone=True,
        look=look,
        is_text=False,
    )
    region._redraw_look()
    return region
