"""
xnano.art._images

Decoded images and how they are fitted into cells and animated.
"""

from __future__ import annotations

import dataclasses
import math
import os
import pathlib
from typing import TYPE_CHECKING, Literal, cast

import xnano_core as _core
from xnano import symbols
from xnano._internal._axes import to_rgb
from xnano._internal._optional import is_image, require
from xnano._schema._appearance import ColorValue
from xnano._schema._axes import Axis
from xnano._schema._media import ImageFit, ResamplingFilter

if TYPE_CHECKING:
    from xnano_image import TerminalImage

__all__ = [
    'Image',
    'ImageAnimation',
    'ImageSource',
    'cells',
    'image_buffer',
    'load_image',
]

_PIXELS_PER_CELL_ROW = 2


@dataclasses.dataclass(slots=True)
class ImageAnimation:
    """
    The frames of an animated image shown in one buffer, and which one is showing.

    Attributes:
        decoded: The animated picture, a [`TerminalImage`][xnano_image.TerminalImage].
        buffer: The buffer the frames are shown in.
        frames: One buffer per frame.
        started_milliseconds: The clock time the animation started at.
        shown_index: The index of the frame that is showing.
    """

    decoded: TerminalImage
    """The animated picture, a [`TerminalImage`][xnano_image.TerminalImage]."""
    buffer: _core.Buffer
    """The buffer the frames are shown in."""
    frames: list[_core.Buffer]
    """One buffer per frame."""
    started_milliseconds: float
    """The clock time the animation started at."""
    shown_index: int = 0
    """The index of the frame that is showing."""

    def advance(self, elapsed_seconds: float) -> None:
        """Show the frame that belongs at ``elapsed_seconds``."""
        elapsed = elapsed_seconds * 1000.0 - self.started_milliseconds
        index = self.decoded.frame_index_at(elapsed)
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
    fit: Literal['contain', 'cover', 'stretch', 'crop', 'smart'] | None = None,
    resampling_filter: Literal['nearest', 'bilinear', 'catmull_rom', 'lanczos3']
    | None = None,
    background: tuple[int, int, int] = (0, 0, 0),
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
        fit: How the picture sits in the box; ``None`` stretches an unsized image to its
            own size and contains a sized one.
        resampling_filter: How pixels are blended; ``None`` chooses by whether it is enlarged.
        background: The color behind transparent pixels and padding.
    """
    if columns is None and rows is None:
        columns, rows = _fitted_size(image, limit)
        chosen_fit = fit or 'stretch'
    else:
        chosen_fit = fit or 'contain'
    chosen_filter = resampling_filter or _resampling_filter(image, columns, rows)
    if not image.is_animated:
        grid = image.to_cell_grid(
            columns,
            rows,
            fit=chosen_fit,
            resampling_filter=chosen_filter,
            background=background,
        )
        return _core.Buffer.from_cell_grid(grid), None
    grids = image.to_cell_grids(
        columns,
        rows,
        fit=chosen_fit,
        resampling_filter=chosen_filter,
        background=background,
    )
    frames = [_core.Buffer.from_cell_grid(grid) for grid in grids]
    buffer = _core.Buffer.from_cell_grid(grids[0])
    animation = ImageAnimation(
        decoded=image,
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


@dataclasses.dataclass(frozen=True, slots=True, init=False)
class Image:
    """
    An image and how it is shown: what [`Canvas.write`][xnano.canvas.Canvas.write] takes
    to put a picture on the canvas.

    Make one from the path of an image file, its bytes, or a
    [`TerminalImage`][xnano_image.TerminalImage]. A file is read once, here, where you can
    see it; ``write`` never takes a path. The placement values are what ``write`` uses when it
    is not given its own. An image sized by a percentage (or not sized at all) is converted
    again whenever the canvas is resized, so it always fits; give it a number, or
    ``lock=True``, and it keeps its size.

    Maps to [`xnano_image.TerminalImage`][xnano_image.TerminalImage].

    Attributes:
        decoded: The decoded picture, a [`TerminalImage`][xnano_image.TerminalImage].
        x: The column of the left edge, or ``None`` for the top-left corner.
        y: The row of the top edge, or ``None``.
        width: The width: cells, a percentage, an expression, or ``None`` for the picture's own.
        height: The height, in the same forms.
        layer: Content with a higher layer is drawn over content with a lower one.
        lock: Whether the image keeps the size it was shown at when the canvas is resized.
        fit: How the picture sits in a box of ``width`` by ``height``: ``'contain'`` (the
            default), ``'cover'``, ``'stretch'``, ``'crop'`` or ``'smart'``.
        resampling_filter: How pixels are blended when it is resized. By default a small
            picture that is enlarged keeps hard pixel edges (``'nearest'``) and any other is
            smoothed (``'lanczos3'``).
        background: The color behind transparent pixels and padding.
        symbol: The name the image is registered under in [`symbols`][xnano.symbols], or
            ``None``.

    Examples:
        ```python
        import xnano
        from xnano_image import TerminalImage

        picture = xnano.Image(TerminalImage.from_rgba(2, 2, bytes([255, 0, 0, 255]) * 4), width=8)
        with xnano.new(width=20, height=6) as canvas:
            canvas.write(picture, x='center')
        # xnano.Image('photo.png', width='100%') loads a file, and refits when the window resizes.
        ```
    """

    decoded: TerminalImage
    """The decoded picture, a [`TerminalImage`][xnano_image.TerminalImage]."""
    x: Axis | None
    """The column of the left edge, or ``None`` for the top-left corner."""
    y: Axis | None
    """The row of the top edge, or ``None``."""
    width: Axis | None
    """The width: cells, a percentage, an expression, or ``None`` for the picture's own."""
    height: Axis | None
    """The height, in the same forms."""
    layer: int
    """Content with a higher layer is drawn over content with a lower one."""
    lock: bool
    """Whether the image keeps the size it was shown at when the canvas is resized."""
    fit: ImageFit | None
    """How the picture sits in a box of ``width`` by ``height``, or ``None`` for the default."""
    resampling_filter: ResamplingFilter | None
    """How pixels are blended when it is resized, or ``None`` to choose by scale."""
    background: tuple[int, int, int]
    """The color behind transparent pixels and padding, as ``(red, green, blue)``."""
    symbol: str | None
    """The name the image is registered under in [`symbols`][xnano.symbols], or ``None``."""

    def __init__(
        self,
        source: TerminalImage | os.PathLike[str] | str | bytes,
        *,
        x: Axis | None = None,
        y: Axis | None = None,
        width: Axis | None = None,
        height: Axis | None = None,
        layer: int = 0,
        lock: bool = False,
        fit: ImageFit | None = None,
        resampling_filter: ResamplingFilter | None = None,
        background: ColorValue = (0, 0, 0),
        speed: float = 1.0,
        symbol: str | None = None,
    ) -> None:
        """
        Load an image and set how it is shown.

        Args:
            source: The path of an image file (PNG, JPEG, GIF, WebP or XNI), the bytes of one,
                or an image. An animated file plays on the canvas's clock.
            x: The column of the left edge: cells, a percentage, a word such as ``'center'``, an
                expression or a range. See [`Axis`][xnano.types.Axis].
            y: The row of the top edge, in the same forms.
            width: The width, in the same forms; the picture's own when ``None``.
            height: The height, in the same forms.
            layer: Content with a higher layer is drawn over content with a lower one.
            lock: Keep the size the image has when it is added, whatever the canvas does.
            fit: How the picture sits in a box of ``width`` by ``height``.
            resampling_filter: How pixels are blended when it is resized.
            background: The color behind transparent pixels and padding, as a color name, a
                hex string, an ``(r, g, b)`` tuple or a [`Color`][xnano_core.Color].
            speed: How fast an animated image plays: ``2.0`` is twice as fast.
            symbol: A name to register the image under in [`symbols`][xnano.symbols].

        Raises:
            ImportError: ``xnano-image`` is not installed. Install it with
                ``pip install "xnano[image]"``.
            TypeError: ``source`` is not a path, bytes or an image.
            FileNotFoundError: ``source`` is a path with no file at it.
            ValueError: ``symbol`` cannot be a symbol name, or another kind of value
                already has it.
        """
        if is_image(source):
            image = cast('TerminalImage', source)
        else:
            module = require('image', needed_for='xnano.Image')
            if isinstance(source, bytes):
                image = module.TerminalImage.from_bytes(source)
            elif isinstance(source, (str, os.PathLike)):
                path = pathlib.Path(source)
                if not path.is_file():
                    raise FileNotFoundError(
                        f'Image could not load {str(path)!r}, because no image file exists '
                        f'there. Check the path, or pass the bytes of the image.'
                    )
                image = module.TerminalImage.open(path)
            else:
                raise TypeError(
                    f'Image needs the path of an image file, the bytes of an image or an '
                    f'image, but got {type(source).__name__}. Pass Image("picture.png").'
                )
        if speed != 1.0:
            image = image.with_speed(speed)
        for name, value in (
            ('decoded', image),
            ('x', x),
            ('y', y),
            ('width', width),
            ('height', height),
            ('layer', layer),
            ('lock', lock),
            ('fit', fit),
            ('resampling_filter', resampling_filter),
            ('background', to_rgb(background)),
            ('symbol', symbol),
        ):
            object.__setattr__(self, name, value)
        if symbol is not None:
            symbols.register(symbol, self)


def load_image(
    source: TerminalImage | os.PathLike[str] | str | bytes,
    /,
    *,
    x: Axis | None = None,
    y: Axis | None = None,
    width: Axis | None = None,
    height: Axis | None = None,
    layer: int = 0,
    lock: bool = False,
    fit: ImageFit | None = None,
    resampling_filter: ResamplingFilter | None = None,
    background: ColorValue = (0, 0, 0),
    speed: float = 1.0,
    symbol: str | None = None,
) -> Image:
    """
    Load an image or an animation from a file path or from bytes.

    This is [`Image`][xnano.Image] with the same arguments: PNG, JPEG, GIF, WebP and XNI files
    are read, and an animated one plays on the canvas's clock. Write the result with
    ``canvas.write(picture)``.

    Args:
        source: The path of an image file, the bytes of one, or a
            [`TerminalImage`][xnano_image.TerminalImage].
        x: The column of the left edge; see [`Image`][xnano.Image].
        y: The row of the top edge.
        width: The width: cells, a percentage, an expression, or ``None`` for the picture's own.
        height: The height, in the same forms.
        layer: Content with a higher layer is drawn over content with a lower one.
        lock: Keep the size the image has when it is added, whatever the canvas does.
        fit: How the picture sits in a box of ``width`` by ``height``.
        resampling_filter: How pixels are blended when it is resized.
        background: The color behind transparent pixels and padding.
        speed: How fast an animated image plays: ``2.0`` is twice as fast.
        symbol: A name to register the image under in [`symbols`][xnano.symbols].

    Returns:
        The [`Image`][xnano.Image].

    Raises:
        ImportError: ``xnano-image`` is not installed. Install it with
            ``pip install "xnano[image]"``.
        TypeError: ``source`` is not a path, bytes or an image.
        FileNotFoundError: The path does not exist.

    Examples:
        ```python
        import xnano
        from xnano_image import TerminalImage

        picture = xnano.load_image(
            TerminalImage.from_rgba(1, 1, bytes([255, 0, 0, 255])), width=4, symbol='red_dot'
        )
        assert isinstance(picture, xnano.Image)
        assert xnano.symbols.lookup('red_dot') is picture
        ```
    """
    require('image', needed_for='xnano.load_image')
    return Image(
        source,
        x=x,
        y=y,
        width=width,
        height=height,
        layer=layer,
        lock=lock,
        fit=fit,
        resampling_filter=resampling_filter,
        background=background,
        speed=speed,
        symbol=symbol,
    )


def _convert(
    picture: Image,
    width: Axis | None,
    height: Axis | None,
    size: _core.Size,
    elapsed_seconds: float,
) -> tuple[_core.Buffer, ImageAnimation | None]:
    return image_buffer(
        picture.decoded,
        columns=cells(width, size.width),
        rows=cells(height, size.height),
        limit=size,
        elapsed_seconds=elapsed_seconds,
        fit=picture.fit,
        resampling_filter=picture.resampling_filter,
        background=picture.background,
    )


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
    An image shown in a buffer, converted again when the canvas's size changes it.

    Attributes:
        decoded: The decoded picture, a [`TerminalImage`][xnano_image.TerminalImage].
        width: The requested width, as an [`Axis`][xnano.types.Axis], or ``None``.
        height: The requested height, or ``None``.
        size: The canvas size the buffer was converted for.
        buffer: The buffer that shows the image.
        animation: The animation that moves it, for an animated image.
        picture: The [`Image`][xnano.Image] that is shown.
    """

    decoded: TerminalImage
    """The decoded picture, a [`TerminalImage`][xnano_image.TerminalImage]."""
    width: Axis | None
    """The requested width, as an [`Axis`][xnano.types.Axis], or ``None``."""
    height: Axis | None
    """The requested height, or ``None``."""
    size: _core.Size
    """The canvas size the buffer was converted for."""
    buffer: _core.Buffer
    """The buffer that shows the image."""
    animation: ImageAnimation | None
    """The animation that moves it, for an animated image."""
    picture: Image
    """The [`Image`][xnano.Image] that is shown."""

    @classmethod
    def create(
        cls,
        picture: Image,
        *,
        width: Axis | None,
        height: Axis | None,
        size: _core.Size,
        elapsed_seconds: float,
    ) -> ImageSource:
        """Convert an image for a canvas of this ``size``."""
        buffer, animation = _convert(picture, width, height, size, elapsed_seconds)
        return cls(picture.decoded, width, height, size, buffer, animation, picture)

    @property
    def depends_on_size(self) -> bool:
        """Whether the canvas's size decides how large the image is drawn."""
        return not self.picture.lock and (
            (self.width is None and self.height is None)
            or isinstance(self.width, str)
            or isinstance(self.height, str)
        )

    @property
    def needs_frames(self) -> bool:
        """Whether the image must be looked at before every frame: it animates or resizes."""
        return self.animation is not None or self.depends_on_size

    def refresh(self, size: _core.Size, elapsed_seconds: float) -> None:
        """Convert the image again for a canvas of a new ``size``, if its size matters."""
        if size == self.size:
            return
        self.size = size
        if not self.depends_on_size:
            return
        buffer, animation = _convert(
            self.picture, self.width, self.height, size, elapsed_seconds
        )
        self.buffer.resize(buffer.width, buffer.height)
        self.buffer.update(_core.Paste(buffer, mode='replace'))
        if self.animation is not None and animation is not None:
            animation.started_milliseconds = self.animation.started_milliseconds
            animation.buffer = self.buffer
            self.animation = animation
            animation.shown_index = -1
