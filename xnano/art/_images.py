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


_TRANSPARENT_CELL = _core.Cell(' ', is_transparent=True)

ImageFrame = _core.Buffer | _core.Raster
"""One frame of a picture: cells to paste, or the pixels to draw over transparent cells."""


def show_frame(buffer: _core.Buffer, frame: ImageFrame) -> None:
    """Make ``buffer`` show ``frame``, keeping the transparency of cells the picture leaves bare."""
    if isinstance(frame, _core.Raster):
        buffer.fill(_TRANSPARENT_CELL)
        buffer.update(frame)
    else:
        buffer.update(_core.Paste(frame, mode='replace'))


@dataclasses.dataclass(slots=True)
class ImageAnimation:
    """
    The frames of an animated image shown in one buffer, and which one is showing.

    Attributes:
        decoded: The animated picture, a [`TerminalImage`][xnano_image.TerminalImage].
        buffer: The buffer the frames are shown in.
        frames: One entry per frame: the cells to paste, or, for a picture with transparent
            pixels, the pixels to draw over transparent cells.
        started_milliseconds: The clock time the animation started at.
        shown_index: The index of the frame that is showing.
    """

    decoded: TerminalImage
    """The animated picture, a [`TerminalImage`][xnano_image.TerminalImage]."""
    buffer: _core.Buffer
    """The buffer the frames are shown in."""
    frames: list[ImageFrame]
    """One entry per frame: cells to paste, or pixels to draw over transparent cells."""
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
        show_frame(self.buffer, self.frames[index])


@dataclasses.dataclass(slots=True)
class FittedImage:
    """
    An image fitted into a box of cells.

    Attributes:
        columns: The width in cells.
        rows: The height in cells.
        frames: One entry per frame: the cells to paste, or, when the picture has transparent
            pixels, the pixels to draw over transparent cells.
    """

    columns: int
    """The width in cells."""
    rows: int
    """The height in cells."""
    frames: list[ImageFrame]
    """One entry per frame: cells to paste, or pixels to draw over transparent cells."""

    def new_buffer(self) -> _core.Buffer:
        """A buffer of the fitted size showing the first frame."""
        first = self.frames[0]
        if isinstance(first, _core.Buffer):
            return _core.Buffer.from_cell_grid(first.to_cell_grid())
        buffer = _core.Buffer(width=self.columns, height=self.rows)
        show_frame(buffer, first)
        return buffer


def fit_image(
    image: TerminalImage,
    *,
    columns: int | None = None,
    rows: int | None = None,
    limit: _core.Size | None = None,
    fit: Literal['contain', 'cover', 'stretch', 'crop', 'smart'] | None = None,
    resampling_filter: Literal['nearest', 'bilinear', 'catmull_rom', 'lanczos3']
    | None = None,
    background: tuple[int, int, int] = (0, 0, 0),
) -> FittedImage:
    """
    Fit an image into cells, with the arguments of [`image_buffer`][xnano.art._images.image_buffer].

    An image with no transparent pixel becomes opaque cells, padded with ``background``. An
    image with transparent pixels is drawn as pixels over transparent cells, so fully
    transparent pixels and the margins around the picture let what is below show through.
    """
    if columns is None and rows is None:
        columns, rows = _fitted_size(image, limit)
        chosen_fit = fit or 'stretch'
    else:
        chosen_fit = fit or 'contain'
    chosen_filter = resampling_filter or _resampling_filter(image, columns, rows)
    if not image.is_opaque:
        return _fit_transparent(
            image, columns, rows, chosen_fit, chosen_filter, background
        )
    if image.is_animated:
        grids = image.to_cell_grids(
            columns,
            rows,
            fit=chosen_fit,
            resampling_filter=chosen_filter,
            background=background,
        )
    else:
        grids = [
            image.to_cell_grid(
                columns,
                rows,
                fit=chosen_fit,
                resampling_filter=chosen_filter,
                background=background,
            )
        ]
    frames: list[ImageFrame] = [_core.Buffer.from_cell_grid(grid) for grid in grids]
    first = cast('_core.Buffer', frames[0])
    return FittedImage(first.width, first.height, frames)


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
        background: The color of the margins around an image with no transparent pixel, and
            the color partly transparent pixels are blended with. Fully transparent pixels
            and the margins of an image with transparency show the cells below.
    """
    fitted = fit_image(
        image,
        columns=columns,
        rows=rows,
        limit=limit,
        fit=fit,
        resampling_filter=resampling_filter,
        background=background,
    )
    if not image.is_animated and isinstance(fitted.frames[0], _core.Buffer):
        return fitted.frames[0], None
    buffer = fitted.new_buffer()
    if not image.is_animated:
        return buffer, None
    animation = ImageAnimation(
        decoded=image,
        buffer=buffer,
        frames=fitted.frames,
        started_milliseconds=elapsed_seconds * 1000.0,
    )
    return buffer, animation


_VISIBILITY = bytes([0] + [255] * 255)
"""Maps an alpha of 0 to 0 and every other alpha to 255."""


def _visible_pixels(flattened: bytes, original: bytes) -> bytes:
    """
    RGBA bytes whose colors are blended onto the background and whose alpha is 0 only where
    the original pixel was fully transparent.
    """
    pixels = bytearray(flattened)
    pixels[3::4] = original[3::4].translate(_VISIBILITY)
    return bytes(pixels)


def _fit_transparent(
    image: TerminalImage,
    columns: int | None,
    rows: int | None,
    fit: str,
    resampling_filter: str,
    background: tuple[int, int, int],
) -> FittedImage:
    """
    Fit an image that has transparent pixels, as pixels to draw over transparent cells.

    The picture is sized and placed exactly as it would be for an opaque image, but it is not
    flattened onto a background first.
    """
    plan = _pixel_plan(image.width, image.height, columns, rows, fit)
    fitted = image
    if plan.scaled is not None and plan.scaled != (image.width, image.height):
        fitted = fitted.resize(*plan.scaled, resampling_filter=resampling_filter)  # type: ignore[arg-type]
    canvas_width, canvas_height = plan.canvas
    source_left = max(0, (fitted.width - canvas_width) // 2)
    source_top = max(0, (fitted.height - canvas_height) // 2)
    source_top -= source_top % _PIXELS_PER_CELL_ROW
    copy_width = min(fitted.width, canvas_width)
    copy_height = min(fitted.height, canvas_height)
    if (source_left, source_top, copy_width, copy_height) != (
        0,
        0,
        fitted.width,
        fitted.height,
    ):
        fitted = fitted.crop(source_left, source_top, copy_width, copy_height)
    left = max(0, (canvas_width - fitted.width) // 2)
    top = max(0, (canvas_height - fitted.height) // 2)
    top -= top % _PIXELS_PER_CELL_ROW
    flattened = fitted.flatten(background)
    frames: list[ImageFrame] = [
        _core.Raster(
            _visible_pixels(flattened.to_rgba(frame_index), fitted.to_rgba(frame_index)),
            width=fitted.width,
            height=fitted.height,
            x=left,
            y=top,
            mode='over',
        )
        for frame_index in range(fitted.frame_count)
    ]
    return FittedImage(plan.columns, plan.rows, frames)


@dataclasses.dataclass(frozen=True, slots=True)
class _PixelPlan:
    """Where a picture lands on a grid of half-block pixels."""

    columns: int
    rows: int
    scaled: tuple[int, int] | None
    canvas: tuple[int, int]


def _pixel_plan(
    width: int, height: int, columns: int | None, rows: int | None, fit: str
) -> _PixelPlan:
    """The size in cells, the size to resize to and the pixel canvas, for one image."""

    def rounded(value: float) -> int:
        return max(1, round(value))

    natural = (width, height)
    if rows is None:
        if columns is None:
            return _PixelPlan(
                width, math.ceil(height / _PIXELS_PER_CELL_ROW), None, natural
            )
        scale = 1.0 if fit == 'crop' else columns / width
        scaled = (rounded(width * scale), rounded(height * scale))
        return _PixelPlan(
            columns,
            math.ceil(scaled[1] / _PIXELS_PER_CELL_ROW),
            scaled,
            (columns, scaled[1]),
        )
    if columns is None:
        scale = 1.0 if fit == 'crop' else rows * _PIXELS_PER_CELL_ROW / height
        scaled = (rounded(width * scale), rounded(height * scale))
        return _PixelPlan(
            scaled[0], rows, scaled, (scaled[0], rows * _PIXELS_PER_CELL_ROW)
        )
    target_width, target_height = columns, rows * _PIXELS_PER_CELL_ROW
    if fit == 'smart':
        ratio = (width / height) / (target_width / target_height)
        fit = 'cover' if max(ratio, 1 / ratio) <= 1.2 else 'contain'
    scaled: tuple[int, int] | None
    if fit == 'crop':
        scaled = None
    elif fit == 'stretch':
        scaled = (target_width, target_height)
    else:
        horizontal, vertical = target_width / width, target_height / height
        scale = max(horizontal, vertical) if fit == 'cover' else min(horizontal, vertical)
        scaled = (rounded(width * scale), rounded(height * scale))
    return _PixelPlan(columns, rows, scaled, (target_width, target_height))


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
    An image and how it is shown: what [`Screen.write`][xnano.devices.Screen.write] takes
    to put a picture on the canvas.

    Make one from the path of an image file, its bytes, or a
    [`TerminalImage`][xnano_image.TerminalImage]. A file is read once, here, where you can
    see it; ``write`` never takes a path. The placement values are what ``write`` uses when it
    is not given its own. An image sized by a percentage (or not sized at all) is converted
    again whenever the canvas is resized, so it always fits; give it a number, or
    ``lock=True``, and it keeps its size.

    A picture with transparent pixels (a PNG with an alpha channel, for example) lets what is
    below it on the canvas show through them. Pixels that are only partly transparent blend
    with ``background``, and a cell with one transparent half and one drawn half shows the terminal's
    default color in the transparent half.

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
        background: The color of the margins around a picture with no transparent pixel, and
            the color its partly transparent pixels are blended with. Fully transparent
            pixels let the canvas show through.
        symbol: The name the image is registered under in [`symbols`][xnano.symbols], or
            ``None``.

    Examples:
        ```python
        import xnano
        from xnano_image import TerminalImage

        picture = xnano.Image(TerminalImage.from_rgba(2, 2, bytes([255, 0, 0, 255]) * 4), width=8)
        with xnano.new(width=20, height=6) as canvas:
            canvas.screen.write(picture, x='center')
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
    """The color of margins and partly transparent pixels, as ``(red, green, blue)``."""
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
                expression or a range. See [`Axis`][xnano.layout.Axis].
            y: The row of the top edge, in the same forms.
            width: The width, in the same forms; the picture's own when ``None``.
            height: The height, in the same forms.
            layer: Content with a higher layer is drawn over content with a lower one.
            lock: Keep the size the image has when it is added, whatever the canvas does.
            fit: How the picture sits in a box of ``width`` by ``height``.
            resampling_filter: How pixels are blended when it is resized.
            background: The color of the margins around a picture with no transparent pixel
                and the color partly transparent pixels are blended with, as a color name, a
                hex string, an ``(r, g, b)`` tuple or a [`Color`][xnano_core.Color]. Fully
                transparent pixels let the canvas show through.
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
    ``canvas.screen.write(picture)``.

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
        background: The color of the margins around a picture with no transparent pixel, and
            the color partly transparent pixels are blended with.
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
    picture: Image, width: Axis | None, height: Axis | None, size: _core.Size
) -> FittedImage:
    return fit_image(
        picture.decoded,
        columns=cells(width, size.width),
        rows=cells(height, size.height),
        limit=size,
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
        width: The requested width, as an [`Axis`][xnano.layout.Axis], or ``None``.
        height: The requested height, or ``None``.
        size: The canvas size the buffer was converted for.
        buffer: The buffer that shows the image.
        animation: The animation that moves it, for an animated image.
        picture: The [`Image`][xnano.Image] that is shown.
    """

    decoded: TerminalImage
    """The decoded picture, a [`TerminalImage`][xnano_image.TerminalImage]."""
    width: Axis | None
    """The requested width, as an [`Axis`][xnano.layout.Axis], or ``None``."""
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
        fitted = _convert(picture, width, height, size)
        buffer = fitted.new_buffer()
        animation = None
        if picture.decoded.is_animated:
            animation = ImageAnimation(
                decoded=picture.decoded,
                buffer=buffer,
                frames=fitted.frames,
                started_milliseconds=elapsed_seconds * 1000.0,
            )
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
        fitted = _convert(self.picture, self.width, self.height, size)
        self.buffer.resize(fitted.columns, fitted.rows)
        show_frame(self.buffer, fitted.frames[0])
        if self.animation is not None:
            self.animation.frames = fitted.frames
            self.animation.shown_index = -1
