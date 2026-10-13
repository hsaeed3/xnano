"""
xnano._media

Turn images into buffers, and keep animated images moving.
"""

from __future__ import annotations

import dataclasses
import math
import os
import pathlib
from typing import TYPE_CHECKING, Literal, cast

import xnano_core as _core
from xnano._optional import is_image, require
from xnano._values import Axis, Content, Renderable

if TYPE_CHECKING:
    from xnano_image import TerminalImage

__all__ = ['ImageAnimation', 'ImageSource', 'content_buffer', 'image_buffer']

_PIXELS_PER_CELL_ROW = 2


@dataclasses.dataclass(slots=True)
class ImageAnimation:
    """
    The frames of an animated image shown in one buffer, and which one is showing.

    Attributes:
        image: The animated image.
        buffer: The buffer the frames are shown in.
        frames: One buffer per frame.
        started_milliseconds: The clock time the animation started at.
        shown_index: The index of the frame that is showing.
    """

    image: TerminalImage
    buffer: _core.Buffer
    frames: list[_core.Buffer]
    started_milliseconds: float
    shown_index: int = 0

    def advance(self, elapsed_seconds: float) -> None:
        """Show the frame that belongs at ``elapsed_seconds``."""
        elapsed = elapsed_seconds * 1000.0 - self.started_milliseconds
        index = self.image.frame_index_at(elapsed)
        if index == self.shown_index:
            return
        self.shown_index = index
        self.buffer.update(_core.Paste(self.frames[index], mode='replace'))


def image_buffer(
    image: TerminalImage,
    *,
    columns: int | None = None,
    rows: int | None = None,
    limit: _core.Size | None = None,
    elapsed_seconds: float = 0.0,
) -> tuple[_core.Buffer, ImageAnimation | None]:
    """
    Return a buffer showing an image, and the animation that moves it if it has frames.

    Args:
        image: The image to show.
        columns: The width in cells. Derived from ``rows`` and the aspect ratio when
            omitted; the image's own width when both are omitted.
        rows: The height in cells, in the same way.
        limit: The largest area the image may take when neither size is given.
        elapsed_seconds: The clock time at which an animation starts.
    """
    if columns is None and rows is None:
        columns, rows = _fitted_size(image, limit)
        fit = 'stretch'
    else:
        fit = 'contain'
    resampling_filter = _resampling_filter(image, columns, rows)
    if not image.is_animated:
        grid = image.to_cell_grid(
            columns, rows, fit=fit, resampling_filter=resampling_filter
        )
        return _core.Buffer.from_cell_grid(grid), None
    grids = image.to_cell_grids(
        columns, rows, fit=fit, resampling_filter=resampling_filter
    )
    frames = [_core.Buffer.from_cell_grid(grid) for grid in grids]
    buffer = _core.Buffer.from_cell_grid(grids[0])
    animation = ImageAnimation(
        image=image,
        buffer=buffer,
        frames=frames,
        started_milliseconds=elapsed_seconds * 1000.0,
    )
    return buffer, animation


# Pictures up to this many pixels on a side are treated as pixel art when they are enlarged.
_PIXEL_ART_LIMIT = 512


def _resampling_filter(
    image: TerminalImage, columns: int | None, rows: int | None
) -> Literal['nearest', 'lanczos3']:
    """
    ``'nearest'`` when a small picture is enlarged, so pixel art keeps its hard edges, and
    ``'lanczos3'`` when a picture is shrunk, so photographs stay smooth.
    """
    scales = []
    if columns is not None:
        scales.append(columns / image.width)
    if rows is not None:
        scales.append(rows * _PIXELS_PER_CELL_ROW / image.height)
    is_small = max(image.width, image.height) <= _PIXEL_ART_LIMIT
    is_enlarged = bool(scales) and min(scales) >= 1.0
    return 'nearest' if is_small and is_enlarged else 'lanczos3'


def _fitted_size(image: TerminalImage, limit: _core.Size | None) -> tuple[int, int]:
    """The image's own size in cells, shrunk to fit ``limit`` with its proportions."""
    columns = image.width
    rows = math.ceil(image.height / _PIXELS_PER_CELL_ROW)
    if limit is not None and limit.width > 0 and limit.height > 0:
        scale = min(1.0, limit.width / columns, limit.height / rows)
        columns = max(1, int(columns * scale))
        rows = max(1, int(rows * scale))
    return columns, rows


def content_buffer(
    content: Content,
    *,
    columns: int | None = None,
    rows: int | None = None,
    limit: _core.Size | None = None,
    elapsed_seconds: float = 0.0,
) -> tuple[_core.Buffer, ImageAnimation | None]:
    """
    Return the buffer that shows any content, and the animation that moves it, if any.

    Args:
        content: A buffer or widget, text, the bytes of a cell grid, an image or the path
            of an image file, or an object with an ``__xnano_buffer__`` method.
        columns: The width in cells of an image.
        rows: The height in cells of an image.
        limit: The largest area an image may take when neither size is given.
        elapsed_seconds: The clock time at which an animated image starts.

    Raises:
        TypeError: The content is not something that can be shown.
    """
    if isinstance(content, _core.Buffer):
        return content, None
    if isinstance(content, str):
        return _core.Buffer.with_text(content), None
    if isinstance(content, bytes):
        return _core.Buffer.from_cell_grid(content), None
    if isinstance(content, os.PathLike) or is_image(content):
        image = load_image(cast('TerminalImage | os.PathLike[str]', content))
        return image_buffer(
            image,
            columns=columns,
            rows=rows,
            limit=limit,
            elapsed_seconds=elapsed_seconds,
        )
    if isinstance(content, Renderable):
        buffer = content.__xnano_buffer__()
        if not isinstance(buffer, _core.Buffer):
            raise TypeError(
                f'{type(content).__name__}.__xnano_buffer__ returned '
                f'{type(buffer).__name__}, but it must return a Buffer.'
            )
        return buffer, None
    raise TypeError(
        f'Cannot show a {type(content).__name__}. Use a Buffer or a widget, a string, the '
        f'bytes of a cell grid, an image or the path of an image file, or an object with '
        f'an __xnano_buffer__ method that returns a Buffer.'
    )


def load_image(content: TerminalImage | os.PathLike[str]) -> TerminalImage:
    """An image as it is, or the image file at a path."""
    if is_image(content):
        return cast('TerminalImage', content)
    module = require('image', needed_for='Showing an image file')
    return module.TerminalImage.open(pathlib.Path(cast('os.PathLike[str]', content)))


def cells(value: Axis | None, available: int) -> int | None:
    """A size in whole cells, when ``value`` is a number or a percentage; otherwise ``None``."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return max(1, round(value))
    if isinstance(value, str) and value.strip().endswith('%'):
        try:
            share = float(value.strip()[:-1]) / 100.0
        except ValueError:
            return None
        return max(1, round(available * share))
    return None


@dataclasses.dataclass(slots=True)
class ImageSource:
    """
    An image shown in a buffer, converted again when the terminal's size changes it.

    Attributes:
        image: The image.
        width: The requested width, as an [`Axis`][xnano.types.Axis], or ``None``.
        height: The requested height, or ``None``.
        size: The terminal size the buffer was converted for.
        buffer: The buffer that shows the image.
        animation: The animation that moves it, for an animated image.
    """

    image: TerminalImage
    width: Axis | None
    height: Axis | None
    size: _core.Size
    buffer: _core.Buffer
    animation: ImageAnimation | None

    @classmethod
    def create(
        cls,
        content: TerminalImage | os.PathLike[str],
        *,
        width: Axis | None,
        height: Axis | None,
        size: _core.Size,
        elapsed_seconds: float,
    ) -> ImageSource:
        """Convert an image (or the image file at a path) for a terminal of this ``size``."""
        image = load_image(content)
        buffer, animation = image_buffer(
            image,
            columns=cells(width, size.width),
            rows=cells(height, size.height),
            limit=size,
            elapsed_seconds=elapsed_seconds,
        )
        return cls(image, width, height, size, buffer, animation)

    def refresh(self, size: _core.Size, elapsed_seconds: float) -> None:
        """Convert the image again for a terminal of a new ``size``, if its size matters."""
        if size == self.size:
            return
        self.size = size
        depends_on_size = (
            (self.width is None and self.height is None)
            or isinstance(self.width, str)
            or isinstance(self.height, str)
        )
        if not depends_on_size:
            return
        buffer, animation = image_buffer(
            self.image,
            columns=cells(self.width, size.width),
            rows=cells(self.height, size.height),
            limit=size,
            elapsed_seconds=elapsed_seconds,
        )
        self.buffer.resize(buffer.width, buffer.height)
        self.buffer.update(_core.Paste(buffer, mode='replace'))
        if self.animation is not None and animation is not None:
            animation.started_milliseconds = self.animation.started_milliseconds
            animation.buffer = self.buffer
            self.animation = animation
            animation.shown_index = -1
