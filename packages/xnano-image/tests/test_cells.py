"""
Cell conversion output: ANSI correctness, grid geometry and cell animations.

The failure class here is "valid-looking output that breaks a terminal":
malformed or unterminated escapes, stray control characters, rows of the
wrong width, text where a grid belongs.
"""

from __future__ import annotations

import itertools
import re
from typing import Any, cast

import pytest
from helpers import animation, ansi_problems, gradient, read_cell_animation, solid

from xnano_image import (
    TerminalGraphics,
    TerminalImage,
    TerminalImageError,
    cell_grid_size,
    cell_grid_to_ansi,
    cell_grid_to_text,
)

FITS = ('crop', 'contain', 'cover', 'stretch', 'smart')
GRID_HELPERS = (cell_grid_size, cell_grid_to_text, cell_grid_to_ansi)


def graphics_for(protocol: str) -> TerminalGraphics:
    return TerminalGraphics.from_capabilities(
        protocol=cast(Any, protocol), cell_size_in_pixels=(10, 20)
    )


# ------------------------------------------------------------ ANSI output


@pytest.mark.parametrize('fit', FITS)
@pytest.mark.parametrize('pixels', [1, 2])
def test_ansi_output_is_well_formed(fit, pixels):
    image = gradient(13, 9)
    text = image.to_ansi(7, 4, fit=fit, horizontal_pixels_per_cell=pixels)
    assert ansi_problems(text) == []
    assert text.endswith('\x1b[0m\n')


def test_ansi_has_one_line_per_row_and_text_has_exact_columns():
    for columns, rows in ((1, 1), (5, 3), (20, 2), (3, 17)):
        grid = gradient(11, 7).to_cell_grid(columns, rows, fit='stretch')
        assert cell_grid_size(grid) == (columns, rows)
        text = cell_grid_to_text(grid)
        assert len(text) == rows
        assert all(len(line) == columns for line in text), text
        assert cell_grid_to_ansi(grid).count('\n') == rows


def test_every_cell_is_a_half_block_glyph():
    grid = gradient(9, 9).to_cell_grid(9, 5, fit='stretch')
    glyphs = set(''.join(cell_grid_to_text(grid)))
    assert glyphs <= {'▀', ' ', '▄', '█'}


def test_ansi_and_grid_agree_on_content():
    grid = gradient(8, 6).to_cell_grid(8, 3)
    assert gradient(8, 6).to_ansi(8, 3) == cell_grid_to_ansi(grid)


def test_ansi_survives_every_color_extreme():
    for color in itertools.product((0, 255), repeat=3):
        text = solid(2, 2, color).to_ansi(2, 1)
        assert ansi_problems(text) == []
        assert f'38;2;{color[0]};{color[1]};{color[2]}' in text


def test_no_control_characters_other_than_escape_and_newline():
    text = gradient(16, 16).to_ansi(16, 8)
    allowed = {'\x1b', '\n'}
    assert not [
        character
        for character in text
        if ord(character) < 0x20 and character not in allowed
    ]


def test_transparent_pixels_never_produce_alpha_in_ansi():
    text = solid(4, 4, (200, 100, 50), alpha=0).to_ansi(4, 2, background=(10, 20, 30))
    assert '10;20;30' in text and '200' not in text
    assert ansi_problems(text) == []


def test_semi_transparency_blends_over_the_background():
    text = solid(2, 2, (255, 255, 255), alpha=128).to_ansi(2, 1, background=(0, 0, 0))
    assert '38;2;128;128;128' in text or '38;2;127;127;127' in text


# --------------------------------------------------------------- geometry


def test_native_size_uses_two_pixel_rows_per_cell():
    assert cell_grid_size(solid(10, 8).to_cell_grid()) == (10, 4)
    assert cell_grid_size(solid(10, 7).to_cell_grid()) == (10, 4)


def test_one_dimension_derives_the_other_from_the_aspect_ratio():
    image = solid(40, 20)
    assert cell_grid_size(image.to_cell_grid(columns=20)) == (20, 5)
    assert cell_grid_size(image.to_cell_grid(rows=10)) == (40, 10)


@pytest.mark.parametrize('fit', FITS)
@pytest.mark.parametrize('size', [(1, 1), (3, 2), (10, 5), (2, 30)])
def test_box_fits_fill_the_requested_grid(fit, size):
    assert cell_grid_size(gradient(17, 11).to_cell_grid(*size, fit=fit)) == size


def test_contain_letterboxes_with_the_background():
    grid = solid(20, 4, (255, 0, 0)).to_cell_grid(
        10, 6, fit='contain', background=(0, 0, 255)
    )
    lines = cell_grid_to_ansi(grid).split('\n')
    assert '48;2;0;0;255' in lines[0] and '48;2;0;0;255' in lines[-2]
    middle = len(lines) // 2
    assert '255;0;0' in lines[middle - 1] or '255;0;0' in lines[middle]


def test_cover_has_no_background_showing():
    grid = solid(20, 4, (255, 0, 0)).to_cell_grid(
        10, 6, fit='cover', background=(0, 0, 255)
    )
    assert '0;0;255' not in cell_grid_to_ansi(grid)


def test_grids_match_single_conversions():
    image = animation(4)
    grids = image.to_cell_grids(5, 2)
    assert len(grids) == 4 == image.frame_count
    assert grids == [image.to_cell_grid(5, 2, frame_index=index) for index in range(4)]
    assert len(set(grids)) == 4, 'frames must actually differ'


def test_conversion_is_deterministic_and_does_not_mutate():
    image = gradient(15, 15)
    before = image.to_rgba()
    assert image.to_cell_grid(6, 3) == image.to_cell_grid(6, 3)
    assert image.to_rgba() == before


def test_aspect_ratio_correction_widens_two_pixel_cells():
    image = solid(20, 20)
    plain = cell_grid_size(image.to_cell_grid(rows=5, horizontal_pixels_per_cell=2))
    corrected = cell_grid_size(
        image.to_cell_grid(
            rows=5, horizontal_pixels_per_cell=2, should_correct_aspect_ratio=True
        )
    )
    assert corrected[0] >= plain[0]


# ------------------------------------------------------------ size limits


def test_unsized_conversion_of_a_huge_image_raises_a_clear_error():
    image = solid(16384, 1024)
    with pytest.raises(TerminalImageError) as caught:
        image.to_cell_grid()
    message = str(caught.value)
    assert 'TerminalImage.to_cell_grid' in message
    assert '16384x512 cells' in message and '4000000' in message
    assert 'columns or rows' in message
    assert cell_grid_size(image.to_cell_grid(80)) == (80, 3)


def test_huge_cell_animations_are_refused_before_rendering():
    clip = TerminalImage.from_frames([solid(8, 8)] * 70)
    with pytest.raises(TerminalImageError, match='64000000'):
        clip.to_cell_animation(1000, 1000)
    with pytest.raises(TerminalImageError, match='4000000'):
        solid(16384, 1024).to_cell_animation()


# ------------------------------------------------------- cell animations


def test_cell_animation_carries_every_frame_with_its_duration():
    clip = animation(3, 6, 4, duration_milliseconds=70).with_speed(0.5)
    should_loop, frames = read_cell_animation(clip.to_cell_animation(6, 2))
    assert should_loop is True
    assert [duration for duration, _ in frames] == clip.frame_durations() == [140] * 3
    assert [grid for _, grid in frames] == clip.to_cell_grids(6, 2)


def test_cell_animation_loop_flag_and_still_images():
    should_loop, frames = read_cell_animation(
        solid(4, 4, duration_milliseconds=250).to_cell_animation(4, 2, should_loop=False)
    )
    assert should_loop is False
    assert len(frames) == 1 and frames[0][0] == 250
    assert cell_grid_size(frames[0][1]) == (4, 2)


def test_cell_animation_options_match_cell_grid_options():
    clip = animation(2, 9, 7)
    options = {
        'fit': 'cover',
        'horizontal_pixels_per_cell': 2,
        'should_correct_aspect_ratio': True,
        'background': (9, 8, 7),
        'resampling_filter': 'nearest',
    }
    _, frames = read_cell_animation(clip.to_cell_animation(5, 3, **options))
    assert [grid for _, grid in frames] == clip.to_cell_grids(5, 3, **options)


@pytest.mark.parametrize('protocol', ['sixel', 'kitty', 'iterm2'])
def test_cell_animation_with_graphics_protocols(protocol):
    clip = animation(3, 20, 20)
    _, frames = read_cell_animation(
        clip.to_cell_animation(4, 2, graphics=graphics_for(protocol))
    )
    assert len(frames) == 3
    for _, grid in frames:
        assert cell_grid_size(grid) == (4, 2)
        assert '\x1b' in cell_grid_to_ansi(grid)
        assert all('\x1b' not in line for line in cell_grid_to_text(grid))


def test_kitty_animation_frames_share_one_image_id():
    clip = animation(4, 20, 20)
    graphics = graphics_for('kitty')
    _, frames = read_cell_animation(clip.to_cell_animation(4, 2, graphics=graphics))
    identifiers = {
        tuple(re.findall(r'\x1b_G[^\x1b]*?i=(\d+)', cell_grid_to_ansi(grid)))
        for _, grid in frames
    }
    assert len(identifiers) == 1 and all(identifiers.pop()), 'one id for every frame'
    first = read_cell_animation(clip.to_cell_animation(4, 2, graphics=graphics))[1][0][1]
    second = read_cell_animation(clip.to_cell_animation(4, 2, graphics=graphics))[1][0][1]
    assert first != second, 'separate animations use separate ids'


# ------------------------------------------------------ graphics protocols


@pytest.mark.parametrize(
    'protocol, introducer',
    [('sixel', '\x1bP'), ('kitty', '\x1b_G'), ('iterm2', '\x1b]1337;File=')],
)
def test_graphics_cells_carry_one_complete_terminated_payload(protocol, introducer):
    grid = gradient(10, 20).to_cell_grid(4, 2, graphics=graphics_for(protocol))
    payload = cell_grid_to_ansi(grid)
    assert introducer in payload
    terminator = {'sixel': '\x1b\\', 'kitty': '\x1b\\', 'iterm2': '\x07'}[protocol]
    assert terminator in payload.split(introducer, 1)[1], 'payload is not terminated'
    assert cell_grid_size(grid) == (4, 2)


@pytest.mark.parametrize('protocol', ['sixel', 'kitty', 'iterm2'])
def test_cell_grid_text_never_contains_escape_sequences(protocol):
    grid = gradient(10, 20).to_cell_grid(4, 2, graphics=graphics_for(protocol))
    for line in cell_grid_to_text(grid):
        assert '\x1b' not in line and '\x07' not in line


def test_to_ansi_always_draws_half_blocks():
    text = gradient(10, 20).to_ansi(4, 2)
    assert '\x1bP' not in text and ansi_problems(text) == []


def test_half_block_graphics_draw_half_blocks():
    graphics = TerminalGraphics.half_blocks()
    image = gradient(6, 6)
    assert image.to_cell_grid(3, 2, graphics=graphics) == image.to_cell_grid(3, 2)


# ---------------------------------------------------- grid helper hygiene


def test_grid_helpers_reject_non_grids_without_returning_garbage():
    good = gradient(4, 4).to_cell_grid(4, 2)
    for bad in (
        b'',
        b'XCG1',
        b'XCG2' + good[4:],
        good[:-1],
        good[: len(good) // 2],
        b'\x00' * 64,
        gradient(4, 4).to_cell_animation(4, 2),
    ):
        for helper in GRID_HELPERS:
            with pytest.raises(TerminalImageError):
                cast(Any, helper)(bad)


def test_cell_grid_size_validates_the_whole_grid_not_just_the_header():
    with pytest.raises(TerminalImageError):
        cell_grid_size(b'XCG1\xff\xff\xff\xff')


def test_grid_helper_errors_name_the_helper():
    for helper in GRID_HELPERS:
        with pytest.raises(TerminalImageError, match=helper.__name__):
            helper(b'nope')


def test_grid_helpers_only_accept_bytes():
    for bad in (
        'XCG1',
        5,
        None,
        [1, 2],
        bytearray(gradient(2, 2).to_cell_grid(2, 1)),
    ):
        for helper in GRID_HELPERS:
            with pytest.raises(TypeError):
                cast(Any, helper)(bad)
