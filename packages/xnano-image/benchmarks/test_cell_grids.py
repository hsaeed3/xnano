"""
Benchmarks for xnano-image: converting images and animations into cell
grids and cell animations.
"""

from __future__ import annotations

import pytest

from xnano_image import TerminalImage


def gradient(width: int, height: int) -> TerminalImage:
    pixels = bytearray()
    for y in range(height):
        for x in range(width):
            pixels += bytes(
                (x * 255 // max(1, width - 1), y * 255 // max(1, height - 1), 128, 255)
            )
    return TerminalImage.from_rgba(width, height, bytes(pixels))


@pytest.fixture(scope='module')
def still() -> TerminalImage:
    return gradient(160, 120)


@pytest.fixture(scope='module')
def clip() -> TerminalImage:
    frames = [
        gradient(96, 72).fit_to_canvas(96, 72, left=index, top=0) for index in range(30)
    ]
    return TerminalImage.from_frames(frames).with_frames_per_second(30)


def test_still_to_cell_grid(benchmark, still):
    benchmark(still.to_cell_grid, 80, 30)


def test_still_to_cell_grid_nearest(benchmark, still):
    benchmark(lambda: still.to_cell_grid(80, 30, resampling_filter='nearest'))


def test_animation_to_cell_grids(benchmark, clip):
    benchmark(clip.to_cell_grids, 48, 18)


def test_animation_to_cell_animation(benchmark, clip):
    benchmark(clip.to_cell_animation, 48, 18)


def test_quantize(benchmark, still):
    benchmark(still.quantize, 64)
