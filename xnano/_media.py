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
from typing import TYPE_CHECKING, Literal, TypedDict, cast

import xnano_core as _core
from xnano._optional import is_image, require
from xnano._values import Axis, Content, Renderable

if TYPE_CHECKING:
    from types import ModuleType

    from typing_extensions import Unpack
    from xnano_audio import TerminalSound
    from xnano_image import TerminalImage

__all__ = [
    'Audio',
    'Image',
    'ImageAnimation',
    'ImageSource',
    'content_buffer',
    'image_buffer',
    'open',
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
    if isinstance(content, os.PathLike):
        raise TypeError(
            f'{content!r} is a path, and write shows images, not paths. Load it first with '
            f'xnano.Image(path) or xnano.open(path).'
        )
    if is_image(content):
        image = cast('TerminalImage', content)
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


ImageFit = Literal['contain', 'cover', 'stretch', 'crop', 'smart']
ResamplingFilter = Literal['nearest', 'bilinear', 'catmull_rom', 'lanczos3']

_IMAGE_SUFFIXES = frozenset(
    {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.xni', '.bmp', '.tif', '.tiff'}
)
_AUDIO_SUFFIXES = frozenset({'.wav', '.wave'})


@dataclasses.dataclass(frozen=True, slots=True, init=False)
class Image:
    """
    An image and how it is shown: what [`Terminal.write`][xnano.terminal.Terminal.write] takes
    to put a picture on the terminal.

    Make one from the path of an image file, its bytes, or a
    [`TerminalImage`][xnano_image.TerminalImage]. A file is read once, here, where you can
    see it; ``write`` never takes a path. The placement values are what ``write`` uses when it
    is not given its own. An image sized by a percentage (or not sized at all) is converted
    again whenever the terminal is resized, so it always fits; give it a number, or
    ``lock=True``, and it keeps its size.

    Attributes:
        image: The picture.
        x: The column of the left edge, or ``None`` for the top-left corner.
        y: The row of the top edge, or ``None``.
        width: The width: cells, a percentage, an expression, or ``None`` for the picture's own.
        height: The height, in the same forms.
        layer: Content with a higher layer is drawn over content with a lower one.
        lock: Whether the image keeps the size it was shown at when the terminal is resized.
        fit: How the picture sits in a box of ``width`` by ``height``: ``'contain'`` (the
            default), ``'cover'``, ``'stretch'``, ``'crop'`` or ``'smart'``.
        resampling_filter: How pixels are blended when it is resized. By default a small
            picture that is enlarged keeps hard pixel edges (``'nearest'``) and any other is
            smoothed (``'lanczos3'``).
        background: The color behind transparent pixels and padding.

    Examples:
        ```python
        import xnano
        from xnano.image import TerminalImage

        picture = xnano.Image(TerminalImage.from_rgba(2, 2, bytes([255, 0, 0, 255]) * 4), width=8)
        with xnano.iter(offscreen=True, width=20, height=6) as terminal:
            terminal.write(picture, x='center')
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
    ) -> None:
        """
        Load an image and set how it is shown.

        Args:
            source: The path of an image file (PNG, JPEG, GIF, WebP or XNI), the bytes of one,
                or an image. An animated file plays on the terminal's clock.
            x: The column of the left edge: cells, a percentage, a word such as ``'center'``, an
                expression or a range. See [`Axis`][xnano.types.Axis].
            y: The row of the top edge, in the same forms.
            width: The width, in the same forms; the picture's own when ``None``.
            height: The height, in the same forms.
            layer: Content with a higher layer is drawn over content with a lower one.
            lock: Keep the size the image has when it is added, whatever the terminal does.
            fit: How the picture sits in a box of ``width`` by ``height``.
            resampling_filter: How pixels are blended when it is resized.
            background: The color behind transparent pixels and padding.
            speed: How fast an animated image plays: ``2.0`` is twice as fast.

        Raises:
            ImportError: ``xnano-image`` is not installed. Install it with
                ``pip install "xnano[image]"``.
            TypeError: ``source`` is not a path, bytes or an image.
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
        ):
            object.__setattr__(self, name, value)


@dataclasses.dataclass(frozen=True, slots=True, init=False)
class Audio:
    """
    A sound you can play with [`Terminal.play`][xnano.terminal.Terminal.play] or
    [`AudioDevice.play`][xnano.audio.AudioDevice.play].

    Make one from the path of a WAV file, the bytes of one, or a
    [`TerminalSound`][xnano_audio.TerminalSound].

    Attributes:
        sound: The rendered sound.

    Examples:
        ```python
        import xnano
        from xnano_audio import TerminalSound

        audio = xnano.Audio(TerminalSound.from_samples([0.0, 0.5, -0.5, 0.0]))
        assert audio.sound.sample_rate == 44100
        ```
    """

    sound: TerminalSound

    def __init__(self, source: TerminalSound | os.PathLike[str] | str | bytes) -> None:
        """
        Load a sound.

        Args:
            source: The path of a WAV file, the bytes of one, or a sound.

        Raises:
            ImportError: ``xnano-audio`` is not installed. Install it with
                ``pip install "xnano[audio]"``.
            TypeError: ``source`` is not a path, bytes or a sound.
            ValueError: The file is not a PCM WAV file that xnano can read.
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


class _ImageOptions(TypedDict, total=False):
    """The keyword arguments of [`Image`][xnano.Image], for [`open`][xnano.open]."""

    x: Axis | None
    y: Axis | None
    width: Axis | None
    height: Axis | None
    layer: int
    lock: bool
    fit: ImageFit | None
    resampling_filter: ResamplingFilter | None
    background: tuple[int, int, int]
    speed: float


def open(
    source: TerminalImage | TerminalSound | os.PathLike[str] | str | bytes,
    /,
    **options: Unpack[_ImageOptions],
) -> Image | Audio:
    """
    Open an image, an animation or a sound from a file path or from bytes.

    The kind is read from the file's extension, or from its first bytes when it has none or
    when you pass bytes: a WAV file becomes an [`Audio`][xnano.Audio], and PNG, JPEG, GIF,
    WebP and XNI files become an [`Image`][xnano.Image] (an animated one plays on the
    terminal's clock). Use `Image` or `Audio` directly when you already know which you have.

    Args:
        source: A path, the bytes of a file, a
            [`TerminalImage`][xnano_image.TerminalImage] or a
            [`TerminalSound`][xnano_audio.TerminalSound].
        **options: How an image is shown; see [`Image`][xnano.Image]. A sound takes none.

    Returns:
        An [`Image`][xnano.Image] or an [`Audio`][xnano.Audio].

    Raises:
        ImportError: The package for the kind of file is not installed.
        TypeError: ``source`` is not something that can be opened, or options were given for
            a sound.
        ValueError: The file is neither an image nor a WAV file.
        FileNotFoundError: The path does not exist.

    Examples:
        ```python
        import xnano
        from xnano.image import TerminalImage

        picture = xnano.open(TerminalImage.from_rgba(1, 1, bytes([255, 0, 0, 255])), width=4)
        assert isinstance(picture, xnano.Image)
        ```
    """
    kind = _kind_of(source)
    if kind == 'audio':
        if options:
            raise TypeError(
                f'A sound takes no display options, but {", ".join(sorted(options))} '
                f'{"was" if len(options) == 1 else "were"} given. Remove them, or open an '
                f'image instead.'
            )
        return Audio(cast('TerminalSound | os.PathLike[str] | str | bytes', source))
    return Image(
        cast('TerminalImage | os.PathLike[str] | str | bytes', source), **options
    )


def _kind_of(source: object) -> Literal['image', 'audio']:
    if is_image(source):
        return 'image'
    module = sys.modules.get('xnano_audio')
    if module is not None and isinstance(source, module.TerminalSound):
        return 'audio'
    if isinstance(source, (str, os.PathLike)):
        path = pathlib.Path(source)
        suffix = path.suffix.lower()
        if suffix in _AUDIO_SUFFIXES:
            return 'audio'
        if suffix in _IMAGE_SUFFIXES:
            return 'image'
        with path.open('rb') as stream:
            head = stream.read(12)
    elif isinstance(source, bytes):
        head = source[:12]
    else:
        raise TypeError(
            f'open needs the path of a file, the bytes of one, an image or a sound, but got '
            f'{type(source).__name__}. Pass open("picture.png") or open("sound.wav").'
        )
    if head[:4] == b'RIFF' and head[8:12] == b'WAVE':
        return 'audio'
    if (
        head[:4] == b'RIFF'
        and head[8:12] == b'WEBP'
        or head[:4]
        in (
            b'\x89PNG',
            b'GIF8',
            b'\xff\xd8\xff\xe0',
            b'\xff\xd8\xff\xe1',
            b'\xff\xd8\xff\xdb',
        )
    ):
        return 'image'
    raise ValueError(
        'This file is neither an image (PNG, JPEG, GIF, WebP or XNI) nor a WAV sound. '
        'Pass a file of one of those kinds, or use Image(...) or Audio(...) on a file you '
        'know how to read.'
    )


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
        """Convert an image for a terminal of this ``size``."""
        buffer, animation = _convert(picture, width, height, size, elapsed_seconds)
        return cls(picture.image, width, height, size, buffer, animation, picture)

    def refresh(self, size: _core.Size, elapsed_seconds: float) -> None:
        """Convert the image again for a terminal of a new ``size``, if its size matters."""
        if size == self.size:
            return
        self.size = size
        depends_on_size = not self.picture.lock and (
            (self.width is None and self.height is None)
            or isinstance(self.width, str)
            or isinstance(self.height, str)
        )
        if not depends_on_size:
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
