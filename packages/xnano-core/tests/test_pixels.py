"""Logical pixels over cells: half blocks, braille and RGBA rasters."""

from __future__ import annotations

import pytest

from xnano_core._xnano_core import Buffer, Pixels, Raster


def test_half_blocks_pack_two_pixels_per_cell():
    buffer = Buffer(width=2, height=1)
    view = buffer.pixels()
    assert (view.width, view.height) == (2, 2)
    view.write([(0, 0, (255, 0, 0)), (0, 1, (0, 0, 255))])
    cell = buffer[0, 0]
    assert cell.symbol == '▀'
    assert cell.foreground.to_rgb() == (255, 0, 0) and cell.background.to_rgb() == (
        0,
        0,
        255,
    )
    view.write([(0, 1, (255, 0, 0))])
    assert buffer[0, 0].symbol == ' ' and buffer[0, 0].background.to_rgb() == (255, 0, 0)


def test_braille_packs_eight_dots_per_cell():
    buffer = Buffer(width=1, height=1)
    view = buffer.pixels(encoding='braille')
    assert (view.width, view.height) == (2, 4)
    view.write([(0, 0, (1, 2, 3)), (1, 3, (1, 2, 3))])
    assert buffer[0, 0].symbol == '⢁'
    assert buffer[0, 0].foreground.to_rgb() == (1, 2, 3)


def test_out_of_bounds_pixels_clip_or_fail_atomically():
    buffer = Buffer(width=1, height=1)
    view = buffer.pixels()
    view.write([(5, 5, (1, 1, 1)), (0, 0, (9, 9, 9))])
    assert buffer[0, 0].background.to_rgb() == (9, 9, 9) or buffer[
        0, 0
    ].foreground.to_rgb() == (9, 9, 9)
    fresh = Buffer(width=1, height=1)
    with pytest.raises(IndexError, match='nothing was changed'):
        fresh.pixels().write([(0, 0, (1, 1, 1)), (5, 5, (1, 1, 1))], clip=False)
    assert fresh[0, 0].symbol == ' ' and fresh[0, 0].background.to_rgb() is None


def test_pixel_coordinates_convert_to_cells_and_back():
    view = Buffer(width=4, height=3).pixels()
    assert view.cell_at(3, 5) == (3, 2)
    assert view.pixel_at(1, 1, anchor='top_left') == (1, 2)
    assert view.pixel_at(1, 1, anchor='bottom_right') == (1, 3)
    assert view.pixel_at(1, 1) == (1, 3)
    with pytest.raises(ValueError, match='anchor'):
        view.pixel_at(0, 0, anchor='middle')
    braille = Buffer(width=4, height=3).pixels(encoding='braille')
    assert braille.cell_at(3, 5) == (1, 1)
    assert braille.pixel_at(1, 1, anchor='top_left') == (2, 4)


def test_rgba_rasters_blend_over_what_is_there():
    buffer = Buffer(width=1, height=1)
    view = buffer.pixels()
    view.write([(0, 0, (0, 0, 0)), (0, 1, (0, 0, 0))])
    half_white = bytes([255, 255, 255, 128, 0, 0, 0, 0])
    view.draw_rgba(half_white, width=1, height=2, mode='over')
    cell = buffer[0, 0]
    assert 120 <= cell.foreground.to_rgb()[0] <= 135
    replaced = Buffer(width=1, height=1)
    replaced.pixels().write([(0, 0, (7, 7, 7))])
    replaced.pixels().draw_rgba(bytes([1, 2, 3, 0]), width=1, height=1, mode='replace')
    assert (
        replaced[0, 0].background.to_rgb() is None
        and replaced[0, 0].foreground.to_rgb() is None
    )


def test_raster_arguments_are_checked():
    view = Buffer(width=2, height=1).pixels()
    with pytest.raises(ValueError, match='needs 8 bytes'):
        view.draw_rgba(b'\x00' * 7, width=2, height=1)
    with pytest.raises(ValueError, match='raster mode'):
        view.draw_rgba(b'\x00' * 8, width=2, height=1, mode='multiply')
    with pytest.raises(ValueError, match='pixel encoding'):
        Buffer().pixels(encoding='sixel')


def test_pixel_operations_snapshot_their_input():
    buffer = Buffer(width=1, height=1)
    pixels = [(0, 0, (5, 6, 7))]
    operation = Pixels(pixels)
    pixels.clear()
    buffer.update(operation)
    assert buffer[0, 0].foreground.to_rgb() == (5, 6, 7)
    buffer.update(
        Raster(bytes([9, 9, 9, 255, 9, 9, 9, 255]), width=1, height=2, mode='replace')
    )
    assert buffer[0, 0].background.to_rgb() == (9, 9, 9)


def test_regions_have_their_own_pixel_space():
    buffer = Buffer(width=4, height=2)
    region = buffer[2:4, 0:1]
    view = region.pixels()
    assert (view.width, view.height) == (2, 2)
    view.write([(0, 0, (3, 3, 3)), (0, 1, (3, 3, 3))])
    assert buffer[2, 0].background.to_rgb() == (3, 3, 3)
    assert buffer[0, 0].background.to_rgb() is None


def test_a_lone_bottom_pixel_leaves_the_top_half_empty():
    buffer = Buffer(width=2, height=1)
    buffer.pixels().write([(0, 1, (255, 48, 48))])
    cell = buffer[0, 0]
    assert cell.symbol == '▄', 'the set pixel is drawn as a lower half block'
    assert cell.foreground.to_rgb() == (255, 48, 48)
    assert cell.background.to_rgb() is None, 'the empty top half keeps the background'
    buffer.pixels().write([(0, 0, (0, 200, 0))])
    assert buffer[0, 0].symbol == '▀', 'a second pixel makes it a normal two-color cell'
