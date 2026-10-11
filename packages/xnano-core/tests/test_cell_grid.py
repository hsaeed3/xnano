"""Validated cell-grid and cell-animation byte interchange."""

from __future__ import annotations

import pytest

from xnano._xnano_core import (
    Buffer,
    CellGridError,
    DecodeLimits,
    Foreground,
    animation_frame_at,
    cell_grid_size,
    cell_grid_to_ansi,
    cell_grid_to_text,
    inspect_cell_animation,
    inspect_cell_grid,
    pack_cell_animation,
    validate_cell_animation,
    validate_cell_grid,
)


def grid(text: str) -> bytes:
    return Buffer(text).to_cell_grid()


def test_grids_inspect_and_convert():
    packed = grid(['ab', 'cd'])
    info = inspect_cell_grid(packed)
    assert (info.format_version, info.columns, info.rows) == (1, 2, 2)
    assert info.has_graphics_protocol_cells is False and info.required_protocol is None
    assert cell_grid_size(packed) == (2, 2)
    assert cell_grid_to_text(packed) == ['ab', 'cd']
    assert '\x1b[' in cell_grid_to_ansi(packed)
    validate_cell_grid(packed)


def test_malformed_bytes_raise_cell_grid_errors_with_guidance():
    with pytest.raises(CellGridError, match='not a cell grid'):
        inspect_cell_grid(b'nope')
    with pytest.raises(CellGridError, match='ends before'):
        validate_cell_grid(grid('abc')[:-3])
    with pytest.raises(CellGridError, match='not a cell animation'):
        validate_cell_animation(grid('a'))
    assert issubclass(CellGridError, ValueError)


def test_decode_limits_are_checked_before_allocating():
    packed = Buffer(width=10, height=10).to_cell_grid()
    with pytest.raises(CellGridError, match='over the limit of 50 cells'):
        validate_cell_grid(packed, limits=DecodeLimits(maximum_cells=50))
    with pytest.raises(CellGridError, match='maximum_payload_bytes'):
        validate_cell_grid(packed, limits=DecodeLimits(maximum_payload_bytes=10))
    assert DecodeLimits().maximum_frames == 10_000
    assert DecodeLimits(maximum_cells=5).maximum_cells == 5


def test_animations_pack_inspect_and_sample():
    red = Buffer('a')
    red.update(Foreground('red'))
    frames = [red.to_cell_grid(), grid('b')]
    packed = pack_cell_animation(
        frames, frame_durations_milliseconds=[100, 50], should_loop=True
    )
    info = inspect_cell_animation(packed)
    assert (info.frame_count, info.duration_milliseconds, info.should_loop) == (
        2,
        150,
        True,
    )
    assert cell_grid_to_text(animation_frame_at(packed, elapsed_milliseconds=120)) == [
        'b'
    ]
    assert cell_grid_to_text(animation_frame_at(packed, elapsed_milliseconds=160)) == [
        'a'
    ]
    with pytest.raises(CellGridError, match='over the limit of 1 frames'):
        validate_cell_animation(packed, limits=DecodeLimits(maximum_frames=1))


def test_animation_inputs_are_checked():
    with pytest.raises(CellGridError, match='2 durations'):
        pack_cell_animation([grid('a')], frame_durations_milliseconds=[1, 2])
    with pytest.raises(CellGridError, match='same size'):
        pack_cell_animation([grid('a'), grid('ab')], frame_durations_milliseconds=[1, 1])
    with pytest.raises(CellGridError, match='positive'):
        pack_cell_animation([grid('a')], frame_durations_milliseconds=[0])
