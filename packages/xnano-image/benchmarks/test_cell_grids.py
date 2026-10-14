"""
Benchmarks for xnano-image: decoding, resizing and converting images and animations into
cell grids and cell animations.

Every benchmark checks what it produced, so a conversion that silently returned something
else would fail instead of looking fast. The 1080p still is the realistic case (a photo
shown in a terminal); the small stills isolate the per-pixel cost of each step.
"""

from __future__ import annotations

import pytest

from xnano_image import (
    TerminalImage,
    cell_grid_size,
    cell_grid_to_ansi,
)


def gradient(width: int, height: int) -> TerminalImage:
    """A smooth color gradient: red grows left to right, green top to bottom."""
    row_pixels = [
        bytes((x * 255 // max(1, width - 1), 0, 128, 255)) for x in range(width)
    ]
    rows = []
    for y in range(height):
        green = y * 255 // max(1, height - 1)
        rows.append(
            b''.join(pixel[:1] + bytes((green,)) + pixel[2:] for pixel in row_pixels)
        )
    return TerminalImage.from_rgba(width, height, b''.join(rows))


def textured(width: int, height: int) -> TerminalImage:
    """A busy image, so decoders and filters cannot take shortcuts on flat areas."""
    row = b''.join(
        bytes(((x * 37) % 256, (x * x // 7) % 256, (x * 11 + 90) % 256, 255))
        for x in range(width)
    )
    rows = [
        row[(y * 4) % (len(row) - 4) :] + row[: (y * 4) % (len(row) - 4)]
        for y in range(height)
    ]
    return TerminalImage.from_rgba(width, height, b''.join(rows))


@pytest.fixture(scope='module')
def still() -> TerminalImage:
    return gradient(160, 120)


@pytest.fixture(scope='module')
def photo() -> TerminalImage:
    return textured(1920, 1080)


@pytest.fixture(scope='module')
def clip() -> TerminalImage:
    frames = [
        gradient(96, 72).fit_to_canvas(96, 72, left=index, top=0) for index in range(30)
    ]
    return TerminalImage.from_frames(frames).with_frames_per_second(30)


@pytest.fixture(scope='module')
def png_photo(photo) -> bytes:
    return photo.encode('png')


@pytest.fixture(scope='module')
def gif_clip(clip) -> bytes:
    return clip.encode('gif')


def test_still_to_cell_grid(benchmark, still):
    grid = benchmark(still.to_cell_grid, 80, 30)
    assert cell_grid_size(grid) == (80, 30)


def test_still_to_cell_grid_nearest(benchmark, still):
    grid = benchmark(lambda: still.to_cell_grid(80, 30, resampling_filter='nearest'))
    assert cell_grid_size(grid) == (80, 30)


@pytest.mark.parametrize(
    'resampling_filter', ['nearest', 'bilinear', 'catmull_rom', 'lanczos3']
)
def test_photo_to_cell_grid(benchmark, photo, resampling_filter):
    grid = benchmark(
        lambda: photo.to_cell_grid(160, 45, resampling_filter=resampling_filter)
    )
    assert cell_grid_size(grid) == (160, 45)


def test_photo_to_ansi(benchmark, photo):
    ansi = benchmark(photo.to_ansi, 160, 45)
    assert len(ansi.splitlines()) == 45


def test_photo_without_size_is_bounded(benchmark, still):
    """Converting at native size, two pixel rows per cell."""
    grid = benchmark(still.to_cell_grid)
    assert cell_grid_size(grid) == (160, 60)


def test_cell_grid_to_ansi(benchmark, photo):
    grid = photo.to_cell_grid(160, 45)
    ansi = benchmark(cell_grid_to_ansi, grid)
    assert len(ansi.splitlines()) == 45


def test_animation_to_cell_grids(benchmark, clip):
    grids = benchmark(clip.to_cell_grids, 48, 18)
    assert len(grids) == 30
    assert all(cell_grid_size(grid) == (48, 18) for grid in grids)


def test_animation_to_cell_animation(benchmark, clip):
    animation = benchmark(clip.to_cell_animation, 48, 18)
    assert animation[:4] == b'XCA1'


def test_quantize(benchmark, still):
    quantized = benchmark(still.quantize, 64)
    assert (quantized.width, quantized.height) == (160, 120)


def test_quantize_with_dithering(benchmark, still):
    quantized = benchmark(lambda: still.quantize(64, should_dither=True))
    assert (quantized.width, quantized.height) == (160, 120)


def test_resize_photo(benchmark, photo):
    smaller = benchmark(lambda: photo.resize(640, 360))
    assert (smaller.width, smaller.height) == (640, 360)


def test_crop_and_fit_to_canvas(benchmark, photo):
    def crop_and_pad() -> TerminalImage:
        return photo.crop(100, 100, 800, 600).fit_to_canvas(900, 700, left=50, top=50)

    padded = benchmark(crop_and_pad)
    assert (padded.width, padded.height) == (900, 700)


def test_decode_png(benchmark, png_photo):
    decoded = benchmark(TerminalImage.from_bytes, png_photo)
    assert (decoded.width, decoded.height) == (1920, 1080)


def test_encode_png(benchmark, photo):
    encoded = benchmark(photo.encode, 'png')
    assert encoded[:8] == b'\x89PNG\r\n\x1a\n'


def test_decode_gif(benchmark, gif_clip):
    decoded = benchmark(TerminalImage.from_bytes, gif_clip)
    assert decoded.frame_count == 30


def test_encode_gif(benchmark, clip):
    encoded = benchmark(clip.encode, 'gif')
    assert encoded[:3] == b'GIF'


def test_to_xni(benchmark, clip):
    encoded = benchmark(clip.to_xni, 64)
    assert encoded[:4] == b'XNI1'


def test_from_xni(benchmark, clip):
    encoded = clip.to_xni(64)
    decoded = benchmark(TerminalImage.from_xni, encoded)
    assert decoded.frame_count == 30
