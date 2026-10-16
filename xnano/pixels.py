"""
xnano.pixels

Pixel drawing on a canvas or a buffer.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import (
    TYPE_CHECKING,
    Literal,
    overload,
)

import xnano_core as _core

if TYPE_CHECKING:
    from xnano_image import TerminalImage

from xnano._axes import to_rgb
from xnano._values import RGB, ColorValue, PixelEncoding


class Pixels:
    """
    The pixels of a canvas, or of any buffer.

    A cell holds more than one pixel: two with ``'half_blocks'`` (one column, two rows) and
    eight with ``'braille'`` (two columns, four rows, but one color for the whole cell).
    Pixels share storage with the cells they are drawn into, so they sit alongside text
    and styles instead of replacing them. Coordinates start at ``(0, 0)`` in the top-left
    corner, and pixels outside the view are skipped.

    A color is a name such as ``'red'`` (in the standard xterm shade), a ``'#rrggbb'`` string
    or an ``(red, green, blue)`` tuple.

    Get one from [`Canvas.pixels`][xnano.canvas.Canvas.pixels] or ``placement.pixels``.

    Attributes:
        width: The width in pixels.
        height: The height in pixels.
        encoding: How pixels are packed into cells.

    Examples:
        ```python
        import xnano

        with xnano.new(width=4, height=2) as canvas:
            pixels = canvas.pixels
            assert (pixels.width, pixels.height) == (4, 4)
            pixels[0, 0] = '#ff0000'
            pixels[0, 1] = (0, 0, 255)
            assert canvas.core_buffer[0, 0].symbol == '▀'
        ```
    """

    __slots__ = ('_view',)

    def __init__(self, view: _core.PixelView) -> None:
        # Created by ``Canvas.pixels`` and ``Placement.pixels``; not constructed directly.
        """
        Wrap a pixel view. Get one from ``canvas.pixels`` instead of calling this.

        Args:
            view: The core pixel view to draw through.
        """
        self._view = view

    @property
    def width(self) -> int:
        """The width in pixels."""
        return self._view.width

    @property
    def height(self) -> int:
        """The height in pixels."""
        return self._view.height

    @property
    def encoding(self) -> PixelEncoding:
        """How pixels are packed into cells."""
        return self._view.encoding

    @property
    def braille(self) -> Pixels:
        """
        The same pixels packed as braille: two columns and four rows per cell, one color per cell.

        Examples:
            ```python
            import xnano

            with xnano.new(width=4, height=2) as canvas:
                dots = canvas.pixels.braille
                assert (dots.width, dots.height) == (8, 8)
            ```
        """
        return Pixels(self._view.surface.pixels(encoding='braille'))

    @overload
    def __setitem__(self, position: tuple[int, int], color: ColorValue) -> None: ...
    @overload
    def __setitem__(
        self, position: tuple[int | slice, int | slice], color: ColorValue
    ) -> None: ...
    def __setitem__(
        self, position: tuple[int | slice, int | slice], color: ColorValue
    ) -> None:
        """
        Draw one pixel or a block of them.

        ``pixels[column, row] = color`` draws one pixel. A slice on either axis draws every
        pixel it covers, so ``pixels[0:10, 2] = 'red'`` is a line and
        ``pixels[:, :] = '#000000'`` clears everything. The color is a name, a
        ``'#rrggbb'`` string, an ``(red, green, blue)`` tuple or a [`Color`][xnano_core.Color]
        with true-color channels.

        Raises:
            TypeError: The position is not a pair of numbers or slices.
            ValueError: The color has no channels, or a slice has a step other than 1.
        """
        if not isinstance(position, tuple) or len(position) != 2:
            raise TypeError(
                f'A pixel position is (column, row), but got {position!r}. Write '
                f'pixels[column, row] = color.'
            )
        columns = self._span(position[0], self.width, 'column')
        rows = self._span(position[1], self.height, 'row')
        channels = to_rgb(color)
        self._view.write((column, row, channels) for row in rows for column in columns)

    @staticmethod
    def _span(index: int | slice, size: int, name: str) -> range:
        if isinstance(index, slice):
            start, stop, step = index.indices(size)
            if step != 1:
                raise ValueError(
                    f'A pixel {name} slice cannot have a step of {index.step}. Use '
                    f'pixels[start:stop, ...] with no step.'
                )
            return range(start, max(start, stop))
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError(
                f'A pixel {name} must be a whole number or a slice, but got {index!r}.'
            )
        return range(index, index + 1)

    def write(self, pixels: Iterable[tuple[int, int, ColorValue]]) -> None:
        """
        Draw many pixels, in order.

        Args:
            pixels: ``(column, row, color)`` tuples.
        """
        self._view.write((column, row, to_rgb(color)) for column, row, color in pixels)

    def shade(self, function: Callable[[int, int], ColorValue | None]) -> None:
        """
        Draw every pixel from a function of its position.

        Args:
            function: Called with ``(column, row)`` for each pixel; return its color, or
                ``None`` to leave the pixel as it is.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=2) as canvas:
                pixels = canvas.pixels
                pixels.shade(lambda column, row: (column * 30, row * 60, 0))
            ```
        """
        view = self._view
        colored: list[tuple[int, int, RGB]] = []
        for row in range(view.height):
            for column in range(view.width):
                color = function(column, row)
                if color is not None:
                    colored.append((column, row, to_rgb(color)))
        view.write(colored)

    def draw_rgba(
        self,
        data: bytes,
        *,
        width: int,
        height: int,
        x: int = 0,
        y: int = 0,
        mode: Literal['over', 'replace'] = 'over',
    ) -> None:
        """
        Draw a row-major RGBA image with its top-left pixel at ``(x, y)``.

        Args:
            data: ``width * height * 4`` bytes of red, green, blue and alpha.
            width: The image width in pixels.
            height: The image height in pixels.
            x: The pixel column of the image's left edge.
            y: The pixel row of the image's top edge.
            mode: ``'over'`` blends by alpha; ``'replace'`` overwrites.
        """
        self._view.draw_rgba(data, width=width, height=height, x=x, y=y, mode=mode)

    def draw_image(
        self,
        image: TerminalImage,
        *,
        x: int = 0,
        y: int = 0,
        mode: Literal['over', 'replace'] = 'over',
        frame_index: int = 0,
    ) -> None:
        """
        Draw a [`TerminalImage`][xnano_image.TerminalImage] with its top-left pixel at ``(x, y)``.

        Pixels outside the view are skipped, so drawing a large image at a negative ``x`` and
        ``y`` scrolls it: that is all a camera over a map needs.

        Args:
            image: The image to draw. It needs the optional ``xnano-image`` package.
            x: The pixel column of the image's left edge. May be negative.
            y: The pixel row of the image's top edge. May be negative.
            mode: ``'over'`` blends by alpha; ``'replace'`` overwrites.
            frame_index: Which frame of an animated image to draw.

        Examples:
            ```python
            import xnano
            from xnano.image import TerminalImage

            with xnano.new(width=4, height=2) as canvas:
                pixels = canvas.pixels
                map_picture = TerminalImage.from_rgba(8, 8, bytes([0, 128, 0, 255]) * 64)
                pixels.draw_image(map_picture, x=-2, y=-2)
            ```
        """
        self.draw_rgba(
            image.to_rgba(frame_index),
            width=image.width,
            height=image.height,
            x=x,
            y=y,
            mode=mode,
        )

    def cell_at(self, column: int, row: int) -> tuple[int, int]:
        """
        Return the ``(column, row)`` of the cell that holds a pixel.

        Args:
            column: The pixel column.
            row: The pixel row.
        """
        return self._view.cell_at(column, row)

    def pixel_at(
        self,
        column: int,
        row: int,
        *,
        anchor: Literal['top_left', 'center', 'bottom_right'] = 'center',
    ) -> tuple[int, int]:
        """
        Return the pixel at an anchor of a cell.

        The mouse reports cells; this picks one pixel of the cell the pointer is over.

        Args:
            column: The cell column.
            row: The cell row.
            anchor: Which pixel of the cell to return.
        """
        return self._view.pixel_at(column, row, anchor=anchor)
