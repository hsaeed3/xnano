"""
xnano.reader._images

The images of a document: where their files are, how large they are, and how to load them.

The size of an image comes from the first bytes of its file, so a document with many large
images is laid out without decoding any of them. An image is decoded when it is shown.
"""

from __future__ import annotations

import functools
import pathlib
import re
import struct

from xnano._internal._optional import is_installed

__all__ = ['cells_for', 'image_file', 'load_image_in_cells', 'pixel_size']

MAXIMUM_ROWS = 24
ADDRESS = re.compile(r'^[A-Za-z][A-Za-z0-9+.-]+:')
"""An address with a scheme of two letters or more, so a Windows drive such as ``C:`` is a path."""


def image_file(source: str, directory: pathlib.Path | None) -> pathlib.Path | None:
    """
    The file of an image that a document names, when xnano can show it.

    Args:
        source: The path or the address of the image, as the document gives it.
        directory: The folder that a relative path starts from, or ``None``.

    Returns:
        The file, or ``None`` when the image is on the network, the file is missing or
        not an image, or ``xnano[image]`` is not installed. The document then shows the
        description of the image in its place.
    """
    if ADDRESS.match(source) or not is_installed('image'):
        return None
    path = pathlib.Path(source.split('#', 1)[0].split('?', 1)[0])
    if not path.is_absolute() and directory is not None:
        path = directory / path
    if not path.is_file() or pixel_size(path) is None:
        return None
    return path


@functools.lru_cache(maxsize=512)
def pixel_size(path: pathlib.Path) -> tuple[int, int] | None:
    """
    The width and the height of an image file in pixels, read from the start of the file.

    Returns:
        The size, or ``None`` when the file is not a PNG, GIF, JPEG, WebP, BMP or XNI1 image.
    """
    try:
        with path.open('rb') as file:
            head = file.read(32)
            if head.startswith(b'\x89PNG\r\n\x1a\n') and len(head) >= 24:
                return _positive(struct.unpack('>II', head[16:24]))
            if head.startswith(b'XNI1') and len(head) >= 8:
                return _positive(struct.unpack('>HH', head[4:8]))
            if head[:6] in (b'GIF87a', b'GIF89a'):
                return _positive(struct.unpack('<HH', head[6:10]))
            if head.startswith(b'BM') and len(head) >= 26:
                width, height = struct.unpack('<ii', head[18:26])
                return _positive((width, abs(height)))
            if head.startswith(b'RIFF') and head[8:12] == b'WEBP':
                return _webp_size(head + file.read(32))
            if head.startswith(b'\xff\xd8'):
                file.seek(2)
                return _jpeg_size(file)
    except (OSError, struct.error):
        return None
    return None


def _positive(size: tuple[int, int]) -> tuple[int, int] | None:
    """The size when both of its sides are more than zero."""
    return size if size[0] > 0 and size[1] > 0 else None


def _webp_size(head: bytes) -> tuple[int, int] | None:
    """The size in the first chunk of a WebP file, in each of its three forms."""
    kind = head[12:16]
    if kind == b'VP8X' and len(head) >= 30:
        width = int.from_bytes(head[24:27], 'little') + 1
        height = int.from_bytes(head[27:30], 'little') + 1
        return width, height
    if kind == b'VP8 ' and len(head) >= 30:
        width, height = struct.unpack('<HH', head[26:30])
        return _positive((width & 0x3FFF, height & 0x3FFF))
    if kind == b'VP8L' and len(head) >= 25:
        bits = int.from_bytes(head[21:25], 'little')
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return None


def _jpeg_size(file: object) -> tuple[int, int] | None:
    """The size in the frame header of a JPEG file."""
    read = file.read  # type: ignore[attr-defined]
    seek = file.seek  # type: ignore[attr-defined]
    while True:
        marker = read(2)
        if len(marker) < 2 or marker[0] != 0xFF:
            return None
        if marker[1] in (0xD8, 0x01) or 0xD0 <= marker[1] <= 0xD7:
            continue
        length = read(2)
        if len(length) < 2:
            return None
        size = struct.unpack('>H', length)[0]
        if 0xC0 <= marker[1] <= 0xCF and marker[1] not in (0xC4, 0xC8, 0xCC):
            frame = read(5)
            if len(frame) < 5:
                return None
            height, width = struct.unpack('>HH', frame[1:5])
            return _positive((width, height))
        seek(size - 2, 1)


def cells_for(
    pixels: tuple[int, int], width: int, height: int = MAXIMUM_ROWS
) -> tuple[int, int]:
    """
    The size in cells of an image of ``pixels`` in a space of ``width`` by ``height`` cells.

    An image is never wider than its own pixels, and it keeps its shape: a cell shows one
    pixel across and two pixels down.

    Returns:
        The width and the height in cells, each one or more.
    """
    columns = max(min(width, pixels[0]), 1)
    rows = max(round(columns * pixels[1] / pixels[0] / 2), 1)
    if rows > height:
        rows = max(height, 1)
        columns = max(min(round(rows * 2 * pixels[0] / pixels[1]), width), 1)
    return columns, rows


def load_image_in_cells(
    path: pathlib.Path, columns: int, rows: int, *, is_still: bool
) -> object | None:
    """
    Load an image file to draw in ``columns`` by ``rows`` cells.

    Args:
        path: The image file.
        columns: The width to draw the image at, in cells.
        rows: The height to draw the image at, in cells.
        is_still: Whether an animated image shows only its first frame, as an image in
            the middle of a document does.

    Returns:
        The [`Image`][xnano.Image], or ``None`` when the file cannot be decoded. The
        document then shows the description of the image in its place.
    """
    from xnano_image import TerminalImage

    from xnano.art import Image

    try:
        decoded = TerminalImage.open(path)
        if is_still and decoded.frame_count > 1:
            decoded = decoded.still_frame(0)
    except (OSError, ValueError):
        return None
    return Image(decoded, width=columns, height=rows, fit='stretch')
