"""
tests.test_art_image_transparency

Pictures with transparent pixels let the canvas below show through; opaque pictures are unchanged.
"""

from __future__ import annotations

import pytest
from xnano_image import TerminalImage

import xnano
from xnano.art._images import image_buffer
from xnano_core import Buffer

RED = (255, 0, 0)
BLUE = (0, 0, 255)


def picture(width: int, height: int, pixel) -> TerminalImage:
    pixels = b''.join(
        bytes(pixel(column, row)) for row in range(height) for column in range(width)
    )
    return TerminalImage.from_rgba(width, height, pixels)


def left_half_red(width: int = 4, height: int = 4) -> TerminalImage:
    """Opaque red on the left half, fully transparent on the right half."""
    return picture(
        width,
        height,
        lambda column, _row: (*RED, 255) if column < width // 2 else (0, 0, 0, 0),
    )


def blue_canvas(width: int = 8, height: int = 4):
    canvas = xnano.new(width=width, height=height)
    canvas.screen.write([' ' * width] * height, background='#0000ff', x=0, y=0)
    return canvas


def cell_at(canvas, column, row):
    return Buffer.from_cell_grid(canvas.screen.output.render().to_cell_grid())[
        column, row
    ]


class TestTransparentPixels:
    def test_transparent_pixels_show_the_canvas(self):
        with blue_canvas() as canvas:
            canvas.screen.write(xnano.Image(left_half_red()), x=0, y=0)
            assert cell_at(canvas, 0, 0).background.to_rgb() == RED
            assert cell_at(canvas, 3, 0).background.to_rgb() == BLUE
            assert cell_at(canvas, 3, 1).background.to_rgb() == BLUE

    def test_the_image_is_not_painted_black(self):
        with blue_canvas() as canvas:
            canvas.screen.write(xnano.Image(left_half_red()), x=0, y=0)
            ansi = canvas.screen.render(format='ansi')
        assert '48;2;0;0;0' not in ansi
        assert '38;2;0;0;0' not in ansi

    def test_a_background_does_not_fill_transparent_pixels(self):
        with blue_canvas() as canvas:
            canvas.screen.write(
                xnano.Image(left_half_red(), background=(0, 255, 0)), x=0, y=0
            )
            assert cell_at(canvas, 3, 0).background.to_rgb() == BLUE

    def test_the_margins_of_a_contained_picture_show_the_canvas(self):
        wide = picture(8, 2, lambda _c, _r: (*RED, 255) if _c < 4 else (0, 0, 0, 0))
        with blue_canvas(8, 6) as canvas:
            canvas.screen.write(xnano.Image(wide, width=8, height=6), x=0, y=0)
            assert cell_at(canvas, 0, 0).background.to_rgb() == BLUE
            assert cell_at(canvas, 0, 5).background.to_rgb() == BLUE
            middle = [cell_at(canvas, 0, row) for row in range(6)]
        assert any(cell.background.to_rgb() == RED for cell in middle)

    def test_a_partly_transparent_pixel_blends_with_the_background(self):
        half = picture(2, 2, lambda _c, _r: (255, 255, 255, 128))
        with blue_canvas(4, 2) as canvas:
            canvas.screen.write(xnano.Image(half), x=0, y=0)
            assert cell_at(canvas, 0, 0).background.to_rgb() == (128, 128, 128)
        with blue_canvas(4, 2) as canvas:
            canvas.screen.write(xnano.Image(half, background=(255, 255, 255)), x=0, y=0)
            assert cell_at(canvas, 0, 0).background.to_rgb() == (255, 255, 255)

    def test_a_fully_transparent_pixel_stays_transparent_with_a_background(self):
        with blue_canvas() as canvas:
            canvas.screen.write(
                xnano.Image(left_half_red(), background=(255, 255, 255)), x=0, y=0
            )
            assert cell_at(canvas, 3, 0).background.to_rgb() == BLUE

    def test_a_cell_with_one_transparent_half_shows_the_default_color(self):
        top_only = picture(
            2, 2, lambda _c, row: (*RED, 255) if row == 0 else (0, 0, 0, 0)
        )
        with blue_canvas(4, 2) as canvas:
            canvas.screen.write(xnano.Image(top_only), x=0, y=0)
            cell = cell_at(canvas, 0, 0)
        assert cell.symbol == '▀'
        assert cell.foreground.to_rgb() == RED
        assert cell.background.to_rgb() != BLUE

    def test_an_opaque_picture_is_drawn_in_every_cell(self):
        with blue_canvas() as canvas:
            canvas.screen.write(
                xnano.Image(picture(4, 4, lambda _c, _r: (*RED, 255))), x=0, y=0
            )
            assert cell_at(canvas, 3, 1).foreground.to_rgb() == RED


class TestOpaquePicturesAreUnchanged:
    @pytest.mark.parametrize('fit', ['contain', 'cover', 'stretch', 'crop', 'smart'])
    @pytest.mark.parametrize('size', [(6, None), (None, 3), (6, 3), (3, 5)])
    def test_the_cells_are_those_of_the_cell_grid(self, fit, size):
        opaque = picture(
            7, 5, lambda column, row: (column * 30, row * 40, (column + row) * 10, 255)
        )
        columns, rows = size
        buffer, animation = image_buffer(
            opaque,
            columns=columns,
            rows=rows,
            fit=fit,
            resampling_filter='nearest',
            background=(9, 8, 7),
        )
        expected = opaque.to_cell_grid(
            columns, rows, fit=fit, resampling_filter='nearest', background=(9, 8, 7)
        )
        assert animation is None
        assert buffer.to_cell_grid() == expected

    def test_an_unsized_picture_is_stretched_to_its_own_size(self):
        opaque = picture(7, 5, lambda column, row: (column * 30, row * 40, 9, 255))
        buffer, _ = image_buffer(opaque, resampling_filter='nearest')
        expected = opaque.to_cell_grid(7, 3, fit='stretch', resampling_filter='nearest')
        assert buffer.to_cell_grid() == expected


class TestTransparentPicturesHaveTheSameSize:
    @pytest.mark.parametrize('fit', ['contain', 'cover', 'stretch', 'crop', 'smart'])
    @pytest.mark.parametrize(
        'size', [(None, None), (6, None), (None, 3), (6, 3), (3, 5), (9, 2)]
    )
    def test_the_size_matches_the_cell_grid(self, fit, size):
        transparent = picture(
            7,
            5,
            lambda column, row: (column * 30, row * 40, 9, 0 if column == 0 else 255),
        )
        columns, rows = size
        buffer, _ = image_buffer(
            transparent, columns=columns, rows=rows, fit=fit, resampling_filter='nearest'
        )
        grid = transparent.to_cell_grid(
            columns, rows, fit=fit, resampling_filter='nearest'
        )
        expected = Buffer.from_cell_grid(grid)
        assert (buffer.width, buffer.height) == (expected.width, expected.height)


class TestAnimatedTransparentPictures:
    @pytest.fixture
    def animation(self):
        red = left_half_red()
        green = picture(
            4, 4, lambda column, _row: (0, 255, 0, 255) if column < 2 else (0, 0, 0, 0)
        )
        return TerminalImage.from_frames([red, green]).with_frames_per_second(10)

    def test_every_frame_keeps_the_canvas_visible(self, animation):
        with blue_canvas() as canvas:
            canvas.screen.write(xnano.Image(animation), x=0, y=0)
            first = cell_at(canvas, 0, 0).background.to_rgb()
            assert cell_at(canvas, 3, 0).background.to_rgb() == BLUE
            canvas.clock.step(delta_seconds=0.15)
            second = cell_at(canvas, 0, 0).background.to_rgb()
            assert cell_at(canvas, 3, 0).background.to_rgb() == BLUE
            canvas.clock.step(delta_seconds=0.1)
            looped = cell_at(canvas, 0, 0).background.to_rgb()
        assert first == RED
        assert second == (0, 255, 0)
        assert looped == first


class TestResizingTransparentPictures:
    def test_the_picture_is_fitted_again_and_stays_transparent(self):
        with xnano.new(width=8, height=4) as canvas:
            canvas.screen.write([' ' * 8] * 4, background='#0000ff', x=0, y=0)
            placement = canvas.screen.write(
                xnano.Image(left_half_red(8, 8)), x=0, y=0, width='50%'
            )
            assert placement.width == 4
            canvas._runtime.resize(width=16, height=4)
            canvas.clock.step(delta_seconds=0.05)
            assert placement.width == 8
            assert cell_at(canvas, 0, 0).background.to_rgb() == RED
            assert cell_at(canvas, 7, 0).background.to_rgb() != RED
