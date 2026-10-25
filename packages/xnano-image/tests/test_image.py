"""Image tests: decoding, processing, fitting, cell conversion and containers."""

import re
import struct
import zlib
from typing import Any, cast

import pytest

from xnano_image import (
    TerminalGraphics,
    TerminalImage,
    TerminalImageError,
    cell_grid_size,
    cell_grid_to_ansi,
    cell_grid_to_text,
)

RED, GREEN, BLUE, WHITE = (
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (255, 255, 255),
)
CELL = re.compile(r'\x1b\[0(?:;[0-9;]*?)?m')
COLORS = re.compile(r'38;2;(\d+);(\d+);(\d+);48;2;(\d+);(\d+);(\d+)')


def solid(width, height, color, alpha=255, duration_milliseconds=100):
    return TerminalImage.from_rgba(
        width,
        height,
        bytes([*color, alpha]) * (width * height),
        duration_milliseconds=duration_milliseconds,
    )


def from_pixels(rows):
    """An image from rows of RGB tuples."""
    data = b''.join(bytes([*pixel, 255]) for row in rows for pixel in row)
    return TerminalImage.from_rgba(len(rows[0]), len(rows), data)


def pixel_colors(rgba):
    """The RGB bytes of every pixel, row-major."""
    return [rgba[position : position + 3] for position in range(0, len(rgba), 4)]


def cell_colors(grid):
    """``[(foreground, background), ...]`` per cell, row-major."""
    found = COLORS.findall(cell_grid_to_ansi(grid))
    return [
        (tuple(map(int, colors[:3])), tuple(map(int, colors[3:]))) for colors in found
    ]


# ------------------------------------------------------------- construction


def test_from_rgba_properties():
    image = solid(5, 3, RED, duration_milliseconds=250)
    assert (image.width, image.height, image.frame_count) == (5, 3, 1)
    assert not image.is_animated and image.is_opaque
    assert image.frame_durations() == [250] and image.duration_milliseconds == 250
    assert len(image) == 1 and '5x3' in repr(image)
    assert image.to_rgba() == bytes([*RED, 255]) * 15


@pytest.mark.parametrize(
    'build',
    [
        lambda: TerminalImage.from_rgba(0, 4, b''),
        lambda: TerminalImage.from_rgba(2, 2, b'\x00' * 15),
        lambda: TerminalImage.from_rgba(99_999, 1, b''),
        lambda: TerminalImage.from_bytes(b'definitely not an image'),
        lambda: TerminalImage.from_bytes(b''),
        lambda: TerminalImage.from_bytes(b'\x89PNG\r\n\x1a\n' + b'junk'),
        lambda: TerminalImage.from_xni(b'XNI1'),
        lambda: TerminalImage.from_xni(b'NOPE' + b'\x00' * 20),
    ],
)
def test_invalid_input_raises_core_image_error(build):
    with pytest.raises(TerminalImageError):
        build()


def test_core_image_error_is_a_value_error():
    assert issubclass(TerminalImageError, ValueError)


def test_open_missing_file_raises_oserror():
    with pytest.raises(OSError):
        TerminalImage.open('/nonexistent/path/image.png')


# ------------------------------------------------------------------ formats


def test_png_round_trip_is_lossless():
    pixels = [[RED, GREEN], [BLUE, WHITE]]
    image = from_pixels(pixels)
    back = TerminalImage.from_bytes(image.encode('png'))
    assert back.to_rgba() == image.to_rgba()


def test_png_keeps_transparency():
    image = solid(2, 2, RED, alpha=100)
    back = TerminalImage.from_bytes(image.encode('png'))
    assert not back.is_opaque
    assert back.to_rgba()[3] == 100


def test_gif_round_trip_keeps_frames_and_timing(tmp_path):
    frames = [
        solid(8, 6, (level, level, level), duration_milliseconds=milliseconds)
        for level, milliseconds in ((0, 40), (120, 80), (240, 120))
    ]
    # build an animation through XNI1 (lossless palette) then export as GIF
    data = _animation_from(frames)
    gif = data.encode('gif')
    back = TerminalImage.from_bytes(gif)
    assert back.frame_count == 3 and (back.width, back.height) == (8, 6)
    assert back.is_animated
    assert back.frame_durations() == [40, 80, 120]
    path = tmp_path / 'out.gif'
    data.save(path)
    assert TerminalImage.open(path).frame_count == 3


def _animation_from(frames):
    """Combine still images into one animation via hand-built XNI1."""
    width, height = frames[0].width, frames[0].height
    payload = b'XNI1' + struct.pack('>HHH', width, height, len(frames))
    for frame in frames:
        rgba = frame.to_rgba()
        colors = []
        indexes = bytearray()
        for position in range(0, len(rgba), 4):
            color = rgba[position : position + 3]
            if color not in colors:
                colors.append(color)
            indexes.append(colors.index(color))
        compressed = zlib.compress(bytes(indexes), 9)
        payload += struct.pack(
            '>HHI', frame.frame_durations()[0], len(colors), len(compressed)
        )
        payload += b''.join(colors) + compressed
    return TerminalImage.from_xni(payload)


def test_save_picks_format_from_extension(tmp_path):
    image = solid(4, 4, GREEN)
    image.save(tmp_path / 'a.png')
    assert TerminalImage.open(tmp_path / 'a.png').to_rgba() == image.to_rgba()
    with pytest.raises(TerminalImageError):
        image.save(tmp_path / 'a.tiff')
    with pytest.raises(TerminalImageError):
        image.encode('bmp')


# ---------------------------------------------------------------------- XNI1


def test_xni_matches_the_documented_byte_layout():
    """Bytes written by hand from the documented layout decode as expected."""
    width, height = 4, 2
    palette = bytes([255, 0, 0, 0, 0, 255])  # red, blue
    indexes = bytes([0, 0, 1, 1, 1, 1, 0, 0])
    compressed = zlib.compress(indexes, 9)
    data = (
        b'XNI1'
        + struct.pack('>HHH', width, height, 1)
        + struct.pack('>HHI', 80, 2, len(compressed))
        + palette
        + compressed
    )
    image = TerminalImage.from_xni(data)
    assert (image.width, image.height, image.frame_durations()) == (4, 2, [80])
    rgba = image.to_rgba()
    assert rgba[0:3] == bytes(RED) and rgba[8:11] == bytes(BLUE)
    assert TerminalImage.from_bytes(data).to_rgba() == rgba  # sniffed by header


def test_xni_round_trip_preserves_a_small_palette():
    original = _animation_from(
        [
            solid(6, 4, RED, duration_milliseconds=60),
            solid(6, 4, BLUE, duration_milliseconds=90),
        ]
    )
    back = TerminalImage.from_xni(original.to_xni(16))
    assert back.frame_durations() == [60, 90]
    assert back.to_rgba(0) == original.to_rgba(0)
    assert back.to_rgba(1) == original.to_rgba(1)


@pytest.mark.parametrize('cut', [4, 9, 14, 20])
def test_truncated_xni_is_rejected(cut):
    good = solid(6, 4, RED).to_xni(4)
    with pytest.raises(TerminalImageError):
        TerminalImage.from_xni(good[:cut])
    with pytest.raises(TerminalImageError):
        TerminalImage.from_xni(good + b'\x00')


def test_xni_quantizes_to_the_requested_colors():
    gradient = from_pixels(
        [[(column * 8, row * 8, 128) for column in range(32)] for row in range(32)]
    )
    back = TerminalImage.from_xni(gradient.to_xni(8))
    rgba = back.to_rgba()
    assert len(set(pixel_colors(rgba))) <= 8


# ---------------------------------------------------------------- transforms


def test_resize_exact_size_and_solid_color_is_preserved():
    big = solid(10, 10, (30, 140, 200)).resize(4, 7)
    assert (big.width, big.height) == (4, 7)
    rgba = big.to_rgba()
    assert all(color == bytes((30, 140, 200)) for color in pixel_colors(rgba))


def test_resize_has_no_dark_halo_on_transparent_pixels():
    # half-transparent red must stay red when resized (premultiplied math)
    shrunk = solid(8, 8, RED, alpha=128).resize(3, 3)
    pixel = shrunk.to_rgba()[:4]
    assert pixel[0] >= 250 and pixel[1] <= 2 and 120 <= pixel[3] <= 136


@pytest.mark.parametrize('name', ['nearest', 'bilinear', 'catmull_rom', 'lanczos3'])
def test_every_resampling_filter_works(name):
    assert solid(6, 6, RED).resize(3, 3, resampling_filter=name).width == 3


def test_nearest_keeps_hard_edges():
    checker = from_pixels([[RED, BLUE], [BLUE, RED]])
    resized = checker.resize(4, 4, resampling_filter='nearest').to_rgba()
    colors = set(pixel_colors(resized))
    assert colors == {bytes(RED), bytes(BLUE)}


def test_scale_and_crop():
    image = from_pixels([[RED, GREEN, BLUE], [WHITE, RED, GREEN]])
    assert image.scale(2.0).width == 6
    cropped = image.crop(1, 0, 2, 2)
    assert (cropped.width, cropped.height) == (2, 2)
    assert cropped.to_rgba()[:3] == bytes(GREEN)
    for bad in ((2, 0, 2, 2), (0, 0, 4, 1), (0, 0, 0, 1)):
        with pytest.raises(TerminalImageError):
            image.crop(*bad)
    with pytest.raises(TerminalImageError):
        image.scale(0.0)


def test_fit_to_canvas_pads_centers_and_crops():
    padded = solid(2, 2, RED).fit_to_canvas(6, 4, background=BLUE)
    rgba = padded.to_rgba()
    pixel = lambda column, row: pixel_colors(rgba)[row * 6 + column]
    assert (
        pixel(0, 0) == bytes(BLUE)
        and pixel(2, 1) == bytes(RED)
        and pixel(5, 3) == bytes(BLUE)
    )
    wide = from_pixels([[RED, GREEN, BLUE, WHITE]])
    assert wide.fit_to_canvas(2, 1).to_rgba()[:3] == bytes(GREEN)  # centered window
    assert wide.fit_to_canvas(2, 1, left=2).to_rgba()[:3] == bytes(
        BLUE
    )  # explicit window


def test_flatten_composites_over_the_background():
    flat = solid(2, 2, RED, alpha=0).flatten(background=BLUE)
    assert flat.is_opaque and flat.to_rgba()[:3] == bytes(BLUE)
    half = solid(2, 2, WHITE, alpha=128).flatten(background=(0, 0, 0))
    assert 126 <= half.to_rgba()[0] <= 130
    assert (
        solid(2, 2, RED).flatten(background=BLUE).to_rgba() == solid(2, 2, RED).to_rgba()
    )


def test_quantize_limits_colors_and_validates():
    gradient = from_pixels(
        [[(column * 8, row * 8, 40) for column in range(32)] for row in range(32)]
    )
    for colors in (2, 8, 64):
        rgba = gradient.quantize(colors).to_rgba()
        assert len(set(pixel_colors(rgba))) <= colors
    assert gradient.quantize(8, should_dither=True).is_opaque
    for bad in (1, 257):
        with pytest.raises(TerminalImageError):
            gradient.quantize(bad)


def test_timing_helpers():
    clip = _animation_from(
        [solid(4, 4, (index * 50, 0, 0), duration_milliseconds=100) for index in range(5)]
    )
    assert clip.with_frames_per_second(10).frame_durations() == [100] * 5
    assert sum(clip.with_frames_per_second(24).frame_durations()) in range(
        205, 215
    )  # 5 frames at 24 frames per second
    assert clip.with_speed(2.0).frame_durations() == [50] * 5
    assert clip.first_frames(2).frame_count == 2 and clip.still_frame(3).frame_count == 1
    assert clip.still_frame(3).to_rgba() == clip.to_rgba(3)
    for call in (
        lambda: clip.first_frames(0),
        lambda: clip.still_frame(9),
        lambda: clip.with_frames_per_second(0),
        lambda: clip.with_speed(-1),
    ):
        with pytest.raises(TerminalImageError):
            call()


def test_frame_index_at_loops_and_clamps():
    clip = _animation_from(
        [solid(2, 2, (index, 0, 0), duration_milliseconds=100) for index in range(3)]
    )
    assert [clip.frame_index_at(elapsed) for elapsed in (0, 99, 100, 250, 299)] == [
        0,
        0,
        1,
        2,
        2,
    ]
    assert clip.frame_index_at(310) == 0  # wraps
    assert clip.frame_index_at(310, should_loop=False) == 2
    assert clip.frame_index_at(-5) == 0


def test_focal_crop_matches_scale_then_fit_to_canvas():
    base = from_pixels(
        [[(column * 30, row * 40, 90) for column in range(8)] for row in range(6)]
    )
    focal = base.focal_crop(6, 4, scale=2.0)
    manual = base.scale(2.0).fit_to_canvas(6, 4)
    assert focal.to_rgba() == manual.to_rgba()
    assert (focal.width, focal.height) == (6, 4)
    with pytest.raises(TerminalImageError):
        base.focal_crop(6, 4, scale=0)


def test_operations_do_not_mutate_the_original():
    image = solid(4, 4, RED)
    before = image.to_rgba()
    (
        image.resize(2, 2),
        image.crop(0, 0, 2, 2),
        image.flatten(BLUE),
        image.quantize(4),
    )
    assert image.to_rgba() == before and (image.width, image.height) == (4, 4)


# --------------------------------------------------------------- cell output


def test_half_blocks_map_two_pixel_rows_to_foreground_and_background():
    image = from_pixels([[RED, GREEN], [BLUE, WHITE]])  # 2 columns, 2 pixel rows
    grid = image.to_cell_grid(fit='crop')
    assert cell_grid_size(grid) == (2, 1)
    assert cell_grid_to_text(grid) == ['▀▀']
    assert cell_colors(grid) == [(RED, BLUE), (GREEN, WHITE)]


def test_odd_height_duplicates_the_last_row():
    grid = from_pixels([[RED], [GREEN], [BLUE]]).to_cell_grid(fit='crop')
    assert cell_grid_size(grid) == (1, 2)
    assert cell_colors(grid) == [(RED, GREEN), (BLUE, BLUE)]


def test_two_pixels_per_cell_averages_horizontally():
    image = from_pixels([[(0, 0, 0), (100, 200, 40)], [(0, 0, 0), (100, 200, 40)]])
    grid = image.to_cell_grid(fit='crop', horizontal_pixels_per_cell=2)
    assert cell_grid_size(grid) == (1, 1)
    assert cell_colors(grid)[0][0] == (50, 100, 20)


def test_natural_size_and_derived_dimensions():
    image = solid(40, 20, RED)
    assert cell_grid_size(image.to_cell_grid()) == (40, 10)
    assert cell_grid_size(image.to_cell_grid(columns=20)) == (20, 5)
    assert cell_grid_size(image.to_cell_grid(rows=8)) == (32, 8)
    assert cell_grid_size(image.to_cell_grid(15, 15)) == (15, 15)


@pytest.mark.parametrize('fit', ['crop', 'contain', 'cover', 'stretch', 'smart'])
def test_box_fits_always_fill_the_requested_grid(fit):
    assert cell_grid_size(solid(40, 20, RED).to_cell_grid(12, 9, fit=fit)) == (12, 9)


def test_contain_letterboxes_and_cover_fills():
    wide = solid(8, 2, RED)  # a 4:1 strip into a square box
    contained = cell_colors(wide.to_cell_grid(4, 4, fit='contain', background=BLUE))
    # 4x4 cells = 4x8 pixels; the strip scales to 4x1 pixels, centered vertically
    assert contained[0] == (BLUE, BLUE) and any(RED in pair for pair in contained)
    covered = cell_colors(wide.to_cell_grid(4, 4, fit='cover', background=BLUE))
    assert all(pair == (RED, RED) for pair in covered)


def test_crop_never_resizes_so_small_images_are_padded():
    grid = solid(2, 2, RED).to_cell_grid(4, 4, fit='crop', background=BLUE)
    colors = cell_colors(grid)
    assert colors[0] == (BLUE, BLUE)
    assert (RED, RED) in colors


def test_smart_covers_close_aspects_and_contains_distant_ones():
    square = solid(10, 10, RED)
    nearly = cell_colors(
        square.to_cell_grid(5, 3, fit='smart', background=BLUE)
    )  # 5x6 pixels against 10x10
    assert all(pair == (RED, RED) for pair in nearly)
    far = cell_colors(square.to_cell_grid(12, 2, fit='smart', background=BLUE))
    assert any(BLUE in pair for pair in far)


def test_aspect_correction_keeps_proportions_with_two_pixels_per_cell():
    image = solid(40, 20, RED)
    plain = cell_grid_size(image.to_cell_grid(30, None, horizontal_pixels_per_cell=2))
    fixed = cell_grid_size(
        image.to_cell_grid(
            30, None, horizontal_pixels_per_cell=2, should_correct_aspect_ratio=True
        )
    )
    one = cell_grid_size(image.to_cell_grid(30, None, horizontal_pixels_per_cell=1))
    assert fixed == one == (30, 8)
    assert plain[1] > fixed[1]


def test_transparency_blends_over_the_background_in_cells():
    grid = solid(2, 2, RED, alpha=0).to_cell_grid(fit='crop', background=GREEN)
    assert all(pair == (GREEN, GREEN) for pair in cell_colors(grid))


def test_cell_grids_match_single_frame_conversion():
    clip = _animation_from([solid(6, 4, (index * 60, 10, 10)) for index in range(3)])
    frames = clip.to_cell_grids(6, 2)
    assert len(frames) == 3
    assert frames == [clip.to_cell_grid(6, 2, frame_index=index) for index in range(3)]
    assert frames[0] != frames[2]


@pytest.mark.parametrize(
    'options',
    [
        {'fit': 'tile'},
        {'resampling_filter': 'magic'},
        {'horizontal_pixels_per_cell': 3},
        {'horizontal_pixels_per_cell': 0},
        {'columns': 0},
        {'rows': 5000},
        {'frame_index': 3},
    ],
)
def test_bad_conversion_options_raise(options):
    image = solid(4, 4, RED)
    with pytest.raises(TerminalImageError):
        image.to_cell_grid(**options)
    if 'frame_index' not in options:
        with pytest.raises(TerminalImageError):
            image.to_cell_animation(**options)
        with pytest.raises(TerminalImageError):
            image.to_cell_grids(**options)


def test_to_ansi_prints_one_line_per_row():
    text = solid(6, 4, RED).to_ansi(6, 2)
    assert len(text.split('\n')) == 2 and '\x1b[0m' in text and '▀' in text


# ------------------------------------------------------------- protocols


def test_half_block_graphics_defaults():
    graphics = TerminalGraphics.half_blocks()
    assert graphics.protocol == 'half_blocks'
    width, height = graphics.cell_size_in_pixels
    assert width > 0 and height > 0
    assert isinstance(graphics.capabilities, list) and 'half_blocks' in repr(graphics)
    grid = solid(8, 8, RED).to_cell_grid(4, 2, graphics=graphics)
    assert cell_grid_to_text(grid) == ['▀▀▀▀', '▀▀▀▀']


def test_unknown_protocol_is_rejected():
    with pytest.raises(TerminalImageError, match="'telepathy'"):
        TerminalGraphics.half_blocks().with_protocol(cast(Any, 'telepathy'))
    with pytest.raises(TerminalImageError, match="'half_blocks'"):
        TerminalGraphics.half_blocks().with_protocol(cast(Any, 'halfblocks'))


@pytest.mark.parametrize(
    ('protocol', 'marker'),
    [('sixel', '\x1bP'), ('kitty', '\x1b_G'), ('iterm2', '\x1b]1337')],
)
def test_graphics_protocols_emit_their_escape_sequences(protocol, marker):
    graphics = TerminalGraphics.half_blocks().with_protocol(protocol)
    assert graphics.protocol == protocol
    grid = solid(16, 16, RED).to_cell_grid(8, 4, graphics=graphics)
    assert cell_grid_size(grid) == (8, 4)
    assert marker in cell_grid_to_ansi(grid)
    assert marker not in ''.join(cell_grid_to_text(grid))


# ------------------------------------------------------------- cell grids


def test_invalid_grids_are_rejected_cleanly():
    good = solid(4, 4, RED).to_cell_grid(fit='crop')
    bad = [
        b'',
        b'XCG',
        b'NOPE' + good[4:],
        good[:-1],
        good + b'\x00',
        good[:8] + b'\xff' * 20,
        b'XCG1' + struct.pack('<HH', 65535, 65535),
    ]
    for data in bad:
        for helper in (cell_grid_size, cell_grid_to_text, cell_grid_to_ansi):
            with pytest.raises(TerminalImageError):
                helper(data)
