"""
Image output must be accepted by xnano-core unchanged.

The two packages share no types: they exchange cell grids (``XCG1``) and cell
animations (``XCA1``) as plain bytes, both defined by the shared
``xnano-terminal-cells`` crate. The first group of tests pins that byte contract
from the image side using only the documented layouts, so a format change
fails here rather than at the first user. The second group hands image output
to xnano-core itself and runs once ``xnano_core.engine.TerminalWidget`` exists.
"""

from __future__ import annotations

import struct
from typing import Any, cast

import pytest
from helpers import animation, gradient, read_cell_animation, solid

from xnano_image import (
    TerminalGraphics,
    TerminalImageError,
    cell_grid_size,
    cell_grid_to_text,
)

FITS = ('crop', 'contain', 'cover', 'stretch', 'smart')
PROTOCOLS = ('half_blocks', 'sixel', 'kitty', 'iterm2')


def graphics_for(protocol: str) -> TerminalGraphics:
    return TerminalGraphics.half_blocks().with_protocol(cast(Any, protocol))


def read_cell_grid_header(cell_grid: bytes) -> tuple[int, int]:
    assert cell_grid[:4] == b'XCG1', cell_grid[:8]
    return struct.unpack_from('<HH', cell_grid, 4)


# ------------------------------------------------------- the byte contract


@pytest.mark.parametrize('protocol', PROTOCOLS)
def test_cell_grids_follow_the_documented_header(protocol):
    grid = gradient(13, 9).to_cell_grid(
        7, 4, fit='stretch', graphics=graphics_for(protocol)
    )
    assert read_cell_grid_header(grid) == cell_grid_size(grid) == (7, 4)


@pytest.mark.parametrize('protocol', PROTOCOLS)
def test_cell_animations_follow_the_documented_layout(protocol):
    clip = animation(3, 10, 10, duration_milliseconds=60)
    data = clip.to_cell_animation(5, 3, graphics=graphics_for(protocol))
    should_loop, frames = read_cell_animation(data)
    assert should_loop is True
    assert [duration for duration, _ in frames] == clip.frame_durations()
    for _, grid in frames:
        assert read_cell_grid_header(grid) == cell_grid_size(grid) == (5, 3)
        assert all('\x1b' not in line for line in cell_grid_to_text(grid))


def test_every_fit_mode_produces_valid_cell_grids():
    image = gradient(21, 5)
    for fit in FITS:
        for pixels in (1, 2):
            grid = image.to_cell_grid(9, 4, fit=fit, horizontal_pixels_per_cell=pixels)
            assert cell_grid_size(grid) == (9, 4)
            assert len(cell_grid_to_text(grid)) == 4


def test_cell_animation_frames_are_the_cell_grids_of_each_frame():
    clip = animation(4, 8, 6)
    _, frames = read_cell_animation(clip.to_cell_animation(8, 3))
    assert [grid for _, grid in frames] == clip.to_cell_grids(8, 3)


def test_cell_animations_are_not_cell_grids():
    data = solid(4, 4).to_cell_animation(4, 2)
    assert data[:4] == b'XCA1'
    with pytest.raises(TerminalImageError):
        cell_grid_size(data)


# ------------------------------------------------- acceptance by xnano-core


@pytest.fixture(scope='module')
def core_widget():
    engine = pytest.importorskip('xnano_core.engine')
    widget = getattr(engine, 'TerminalWidget', None)
    if widget is None or not hasattr(widget, 'cell_grid'):
        pytest.skip('xnano_core.engine.TerminalWidget.cell_grid is not available')
    return widget


@pytest.mark.parametrize('protocol', PROTOCOLS)
def test_core_accepts_image_cell_grids(core_widget, protocol):
    for image in (gradient(9, 7), animation(2, 5, 5), solid(1, 1)):
        grid = image.to_cell_grid(6, 3, graphics=graphics_for(protocol))
        assert core_widget.cell_grid(grid) is not None


@pytest.mark.parametrize('protocol', PROTOCOLS)
def test_core_accepts_image_cell_animations(core_widget, protocol):
    if not hasattr(core_widget, 'cell_animation'):
        pytest.skip('xnano_core.engine.TerminalWidget.cell_animation is not available')
    data = animation(3, 10, 10).to_cell_animation(5, 3, graphics=graphics_for(protocol))
    assert core_widget.cell_animation(data) is not None


def test_core_rejects_what_the_image_package_rejects(core_widget):
    grid = gradient(4, 4).to_cell_grid(4, 2)
    for bad in (grid[:-1], b'XCG1', b'', grid[:8] + b'\xff' * 20):
        with pytest.raises(TerminalImageError):
            cell_grid_size(bad)
        with pytest.raises(Exception) as caught:
            core_widget.cell_grid(bad)
        assert '\x1b' not in str(caught.value)
