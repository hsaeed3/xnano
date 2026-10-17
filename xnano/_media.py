"""
xnano._media

Turn images into buffers, and keep animated images moving.
"""

from __future__ import annotations

import array
import dataclasses
import io
import math
import os
import pathlib
import sys
import wave
from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal, cast

import xnano_core as _core
from xnano import symbols
from xnano._optional import is_image, require
from xnano._values import Axis, Content
from xnano.errors import TerminalError

if TYPE_CHECKING:
    from types import ModuleType

    from xnano_audio import TerminalSound
    from xnano_image import TerminalImage

    from xnano.context import Context

__all__ = [
    'Audio',
    'Image',
    'ImageAnimation',
    'ImageSource',
    'content_buffer',
    'from_audio',
    'from_image',
    'image_buffer',
]

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


class _NotRenderable(TypeError):
    """Raised for content that cannot be shown; remembers the offending object."""

    def __init__(self, message: str, content: object) -> None:
        """Remember the message and the content that cannot be shown."""
        super().__init__(message)
        self.content = content


_MAXIMUM_RENDER_DEPTH = 8
"""How many times a result may itself be something that renders, before it is a cycle."""


def content_buffer(
    content: Content,
    *,
    columns: int | None = None,
    rows: int | None = None,
    limit: _core.Size | None = None,
    elapsed_seconds: float = 0.0,
    context: Context[object, object] | None = None,
) -> tuple[_core.Buffer, ImageAnimation | None]:
    """
    Return the buffer that shows any content, and the animation that moves it, if any.

    Args:
        content: A buffer or widget, text, a region, art, a pixel, an image, an object with an
            ``__xnano_render__`` method, or a sequence of those.
        columns: The width in cells of an image.
        rows: The height in cells of an image.
        limit: The largest area an image may take when neither size is given.
        elapsed_seconds: The clock time at which an animated image starts.
        context: What ``__xnano_render__`` methods are called with.

    Raises:
        TypeError: The content is not something that can be shown.
        TerminalError: A render method returns itself again and again.
    """
    try:
        return _content_buffer(
            content,
            columns=columns,
            rows=rows,
            limit=limit,
            elapsed_seconds=elapsed_seconds,
            context=context,
            _chain=(),
        )
    except _NotRenderable as error:
        raise TypeError(str(error)) from None


def _content_buffer(
    content: Content,
    *,
    columns: int | None,
    rows: int | None,
    limit: _core.Size | None,
    elapsed_seconds: float,
    context: Context[object, object] | None,
    _chain: tuple[type, ...],
) -> tuple[_core.Buffer, ImageAnimation | None]:
    """Do the work of [`content_buffer`][xnano._media.content_buffer], tracking the chain."""
    if isinstance(content, _core.Buffer):
        return content, None
    if isinstance(content, str):
        return _core.Buffer.with_text(content), None
    if isinstance(content, (bytes, bytearray)):
        raise TypeError(
            'write() does not accept raw bytes. Write the cell buffer instead: '
            'canvas.write(Buffer.from_cell_grid(data)), or for picture bytes use '
            'xnano.from_image(data) or xnano.draw(data, width=..., height=...).'
        )
    if isinstance(content, os.PathLike):
        raise TypeError(
            f'{content!r} is a path, and write shows images, not paths. Load it first with '
            f'xnano.from_image(path) and write the result.'
        )
    if isinstance(content, Image):
        return image_buffer(
            content.image,
            columns=columns,
            rows=rows,
            limit=limit,
            elapsed_seconds=elapsed_seconds,
        )
    if is_image(content):
        raise TypeError(
            'write() does not accept a TerminalImage directly. Wrap it: '
            'canvas.write(Image(terminal_image)), or load a file with xnano.from_image(path).'
        )
    from xnano.canvas import Canvas

    if isinstance(content, Canvas):
        raise TypeError(
            'A canvas is written with canvas.write(child) directly; a component or a '
            'sequence cannot contain one.'
        )
    if not isinstance(content, type) and hasattr(content, '__xnano_render__'):
        kind = type(content)
        if kind in _chain or len(_chain) >= _MAXIMUM_RENDER_DEPTH:
            names = ' -> '.join(item.__name__ for item in (*_chain, kind))
            raise TerminalError(
                f'{kind.__name__}.__xnano_render__ keeps returning something that renders '
                f'again ({names}). Return text, a Region, an Art, a Buffer or another '
                f'finished value instead of an object that renders itself.'
            )
        result = content.__xnano_render__(context)  # type: ignore[arg-type]
        try:
            return _content_buffer(
                result,
                columns=columns,
                rows=rows,
                limit=limit,
                elapsed_seconds=elapsed_seconds,
                context=context,
                _chain=(*_chain, kind),
            )
        except _NotRenderable as error:
            if error.content is not result:
                raise
            raise TypeError(
                f'{kind.__name__}.__xnano_render__ returned {type(result).__name__}, but it '
                f'must return something write() accepts: text, a Region, an Art, a Pixel, an '
                f'Image, a Buffer, an object with __xnano_render__, or a sequence of those.'
            ) from None
    if isinstance(content, Sequence):
        return _stack(
            content,
            columns=columns,
            rows=rows,
            limit=limit,
            elapsed_seconds=elapsed_seconds,
            context=context,
            chain=_chain,
        ), None
    missing = (
        ' It has an __xnano_play__ method but no __xnano_render__ method, so it can be '
        'played with canvas.play() but not written.'
        if hasattr(content, '__xnano_play__')
        else ' It has no __xnano_render__ method.'
    )
    raise _NotRenderable(
        f'Cannot show a {type(content).__name__}.{missing} Use a string, a Region, an Art, '
        f'a Pixel, an xnano.Image (made with xnano.from_image(path)), a Buffer or widget, '
        f'an object with an __xnano_render__ method, or a sequence of those.',
        content,
    )


def _stack(
    items: Sequence[object],
    *,
    columns: int | None,
    rows: int | None,
    limit: _core.Size | None,
    elapsed_seconds: float,
    context: Context[object, object] | None,
    chain: tuple[type, ...],
) -> _core.Buffer:
    """Draw the items one below the other, as wide as the widest."""
    buffers = [
        _content_buffer(
            cast('Content', item),
            columns=columns,
            rows=rows,
            limit=limit,
            elapsed_seconds=elapsed_seconds,
            context=context,
            _chain=chain,
        )[0]
        for item in items
    ]
    stacked = _core.Buffer(
        width=max((buffer.width for buffer in buffers), default=0),
        height=sum(buffer.height for buffer in buffers),
    )
    offset = 0
    for buffer in buffers:
        stacked.update(_core.Paste(buffer, y=offset, mode='replace'))
        offset += buffer.height
    return stacked


ImageFit = Literal['contain', 'cover', 'stretch', 'crop', 'smart']
ResamplingFilter = Literal['nearest', 'bilinear', 'catmull_rom', 'lanczos3']


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

    Attributes:
        image: The picture.
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
        from xnano.image import TerminalImage

        picture = xnano.Image(TerminalImage.from_rgba(2, 2, bytes([255, 0, 0, 255]) * 4), width=8)
        with xnano.new(width=20, height=6) as canvas:
            canvas.write(picture, x='center')
        # xnano.Image('photo.png', width='100%') loads a file, and refits when the window resizes.
        ```
    """

    image: TerminalImage
    x: Axis | None
    y: Axis | None
    width: Axis | None
    height: Axis | None
    layer: int
    lock: bool
    fit: ImageFit | None
    resampling_filter: ResamplingFilter | None
    background: tuple[int, int, int]
    symbol: str | None

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
        background: tuple[int, int, int] = (0, 0, 0),
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
            background: The color behind transparent pixels and padding.
            speed: How fast an animated image plays: ``2.0`` is twice as fast.
            symbol: A name to register the image under in [`symbols`][xnano.symbols].

        Raises:
            ImportError: ``xnano-image`` is not installed. Install it with
                ``pip install "xnano[image]"``.
            TypeError: ``source`` is not a path, bytes or an image.
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
                image = module.TerminalImage.open(pathlib.Path(source))
            else:
                raise TypeError(
                    f'Image needs the path of an image file, the bytes of an image or an '
                    f'image, but got {type(source).__name__}. Pass Image("picture.png").'
                )
        if speed != 1.0:
            image = image.with_speed(speed)
        for name, value in (
            ('image', image),
            ('x', x),
            ('y', y),
            ('width', width),
            ('height', height),
            ('layer', layer),
            ('lock', lock),
            ('fit', fit),
            ('resampling_filter', resampling_filter),
            ('background', background),
            ('symbol', symbol),
        ):
            object.__setattr__(self, name, value)
        if symbol is not None:
            symbols.register(symbol, self)


@dataclasses.dataclass(frozen=True, slots=True, init=False)
class Audio:
    """
    A sound you can play with [`Canvas.play`][xnano.canvas.Canvas.play] or
    [`AudioDevice.play`][xnano.audio.AudioDevice.play].

    Make one from the path of a WAV file, the bytes of one, or a
    [`TerminalSound`][xnano_audio.TerminalSound].

    Attributes:
        sound: The rendered sound.
        symbol: The name the sound is registered under in [`symbols`][xnano.symbols], or
            ``None``. ``play('kick')`` plays the sound registered as ``'kick'``.

    Examples:
        ```python
        import xnano
        from xnano_audio import TerminalSound

        audio = xnano.Audio(TerminalSound.from_samples([0.0, 0.5, -0.5, 0.0]))
        assert audio.sound.sample_rate == 44100
        ```
    """

    sound: TerminalSound
    symbol: str | None

    def __init__(
        self,
        source: TerminalSound | os.PathLike[str] | str | bytes,
        *,
        symbol: str | None = None,
    ) -> None:
        """
        Load a sound.

        Args:
            source: The path of a WAV file, the bytes of one, or a sound.
            symbol: A name to register the sound under in [`symbols`][xnano.symbols], so
                ``play(name)`` plays it.

        Raises:
            ImportError: ``xnano-audio`` is not installed. Install it with
                ``pip install "xnano[audio]"``.
            TypeError: ``source`` is not a path, bytes or a sound.
            ValueError: The file is not a PCM WAV file that xnano can read, or ``symbol`` cannot
                be a symbol name, or another kind of value already has it.
        """
        module = require('audio', needed_for='xnano.Audio')
        if isinstance(source, module.TerminalSound):
            sound = source
        elif isinstance(source, bytes):
            sound = _decode_wave(module, source)
        elif isinstance(source, (str, os.PathLike)):
            sound = _decode_wave(module, pathlib.Path(source).read_bytes())
        else:
            raise TypeError(
                f'Audio needs the path of a WAV file, the bytes of one or a sound, but got '
                f'{type(source).__name__}. Pass Audio("sound.wav").'
            )
        object.__setattr__(self, 'sound', sound)
        object.__setattr__(self, 'symbol', symbol)
        if symbol is not None:
            symbols.register(symbol, self)


def _decode_wave(module: ModuleType, data: bytes) -> TerminalSound:
    """Decode the bytes of a PCM WAV file into a mono sound."""
    try:
        with wave.open(io.BytesIO(data), 'rb') as reader:
            channels = reader.getnchannels()
            sample_width = reader.getsampwidth()
            sample_rate = reader.getframerate()
            frames = reader.readframes(reader.getnframes())
    except (wave.Error, EOFError) as error:
        raise ValueError(
            f'This is not a PCM WAV file that xnano can read ({error}). Convert the sound '
            f'to a 16-bit PCM WAV file, or build a sound with xnano_audio.TerminalSound.'
        ) from None
    if sample_width == 1:
        values = [(byte - 128) / 128.0 for byte in frames]
    elif sample_width == 3:
        values = [
            int.from_bytes(frames[index : index + 3], 'little', signed=True) / 8388608.0
            for index in range(0, len(frames) - 2, 3)
        ]
    else:
        kind = {2: 'h', 4: 'i'}[sample_width]
        decoded = array.array(kind)
        decoded.frombytes(frames[: len(frames) - len(frames) % sample_width])
        if sys.byteorder == 'big':
            decoded.byteswap()
        scale = float(1 << (8 * sample_width - 1))
        values = [value / scale for value in decoded]
    if channels > 1:
        usable = len(values) - len(values) % channels
        values = [
            sum(values[index : index + channels]) / channels
            for index in range(0, usable, channels)
        ]
    if not values:
        raise ValueError(
            'This WAV file holds no samples. Pass a recording that is not empty.'
        )
    return module.TerminalSound.from_samples(values, sample_rate=sample_rate)


def from_image(
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
    background: tuple[int, int, int] = (0, 0, 0),
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
        from xnano.image import TerminalImage

        picture = xnano.from_image(
            TerminalImage.from_rgba(1, 1, bytes([255, 0, 0, 255])), width=4, symbol='red_dot'
        )
        assert isinstance(picture, xnano.Image)
        assert xnano.symbols.lookup('red_dot') is picture
        ```
    """
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


def from_audio(
    source: TerminalSound | os.PathLike[str] | str | bytes,
    /,
    *,
    symbol: str | None = None,
) -> Audio:
    """
    Load a sound from a WAV file path or from bytes.

    This is [`Audio`][xnano.Audio] with the same arguments. Play the result with
    ``canvas.play(sound)``, or give it a ``symbol`` and play it by name.

    Args:
        source: The path of a PCM WAV file, the bytes of one, or a
            [`TerminalSound`][xnano_audio.TerminalSound].
        symbol: A name to register the sound under in [`symbols`][xnano.symbols], so
            ``play(name)`` plays it.

    Returns:
        The [`Audio`][xnano.Audio].

    Raises:
        ImportError: ``xnano-audio`` is not installed. Install it with
            ``pip install "xnano[audio]"``.
        TypeError: ``source`` is not a path, bytes or a sound.
        ValueError: The file is not a PCM WAV file that xnano can read.
        FileNotFoundError: The path does not exist.

    Examples:
        ```python
        import xnano
        from xnano_audio import TerminalSound

        beep = xnano.from_audio(TerminalSound.from_samples([0.0, 0.5, -0.5, 0.0]), symbol='beep')
        with xnano.new(width=8, height=1) as canvas:
            canvas.play('beep')
            canvas.step(delta_seconds=0.1)
            assert canvas.audio.render_sound().peak > 0.0
        ```
    """
    return Audio(source, symbol=symbol)


def _convert(
    picture: Image,
    width: Axis | None,
    height: Axis | None,
    size: _core.Size,
    elapsed_seconds: float,
) -> tuple[_core.Buffer, ImageAnimation | None]:
    return image_buffer(
        picture.image,
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
        image: The image.
        width: The requested width, as an [`Axis`][xnano.types.Axis], or ``None``.
        height: The requested height, or ``None``.
        size: The canvas size the buffer was converted for.
        buffer: The buffer that shows the image.
        animation: The animation that moves it, for an animated image.
    """

    image: TerminalImage
    width: Axis | None
    height: Axis | None
    size: _core.Size
    buffer: _core.Buffer
    animation: ImageAnimation | None
    picture: Image

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
        return cls(picture.image, width, height, size, buffer, animation, picture)

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
