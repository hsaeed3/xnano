"""
tests.test_media

Images become buffers, and animated images move on the terminal's clock.
"""

from __future__ import annotations

import pytest
from xnano_image import TerminalImage

import xnano
from xnano_core import Buffer


def solid(width: int, height: int, color: tuple[int, int, int]) -> TerminalImage:
    pixels = bytes([*color, 255]) * (width * height)
    return TerminalImage.from_rgba(width, height, pixels)


def cell_at(terminal, column, row):
    frame = terminal.output.render()
    return Buffer.from_cell_grid(frame.to_cell_grid())[column, row]


@pytest.fixture
def terminal():
    with xnano.open(offscreen=True, width=20, height=6) as terminal:
        yield terminal


class TestImages:
    def test_an_image_keeps_its_own_size(self, terminal):
        placement = terminal.add(solid(8, 8, (255, 0, 0)))
        assert (placement.width, placement.height) == (8, 4)

    def test_a_large_image_shrinks_to_fit_the_terminal(self, terminal):
        placement = terminal.add(solid(80, 40, (0, 255, 0)))
        assert placement.width <= 20 and placement.height <= 6
        assert placement.width / placement.height == pytest.approx(80 / 20, rel=0.3)

    def test_one_size_keeps_the_proportions(self, terminal):
        placement = terminal.add(solid(16, 16, (0, 0, 255)), width=10)
        assert placement.width == 10
        assert placement.height == 5

    def test_a_percentage_is_a_share_of_the_terminal(self, terminal):
        placement = terminal.add(solid(16, 16, (0, 0, 255)), width='50%')
        assert placement.width == 10

    def test_both_sizes_fit_the_image_inside_the_box(self, terminal):
        placement = terminal.add(solid(8, 8, (9, 9, 9)), width=12, height=3)
        assert (placement.width, placement.height) == (12, 3)

    def test_the_cells_show_the_pixels(self, terminal):
        terminal.add(solid(4, 2, (255, 0, 0)))
        cell = cell_at(terminal, 0, 0)
        assert cell.foreground.to_rgb() == (255, 0, 0)

    def test_an_image_file_is_shown_from_its_path(self, terminal, tmp_path):
        path = tmp_path / 'red.png'
        solid(6, 4, (255, 0, 0)).save(path)
        placement = terminal.add(path)
        assert (placement.width, placement.height) == (6, 2)

    def test_an_image_can_be_composed_before_it_is_placed(self, terminal):
        composition = xnano.make(solid(10, 10, (1, 2, 3)), width=6)
        buffer = composition.build()
        assert isinstance(buffer, Buffer)
        assert buffer.width == 6
        assert terminal.add(composition).width == 6


class TestResponsiveImages:
    def test_a_percentage_width_follows_the_terminal_size(self):
        with xnano.open(offscreen=True, width=20, height=8) as terminal:
            placement = terminal.add(solid(40, 40, (255, 0, 0)), width='50%')
            terminal.loop.advance(0.05)
            assert placement.width == 10
            terminal._runtime.resize(width=40, height=8)
            terminal.loop.advance(0.05)
            assert placement.width == 20
            cell = cell_at(terminal, 19, 0)
            assert cell.foreground.to_rgb() == (255, 0, 0)

    def test_a_fixed_size_does_not_change_when_the_terminal_does(self):
        with xnano.open(offscreen=True, width=20, height=8) as terminal:
            placement = terminal.add(solid(40, 40, (255, 0, 0)), width=6)
            terminal._runtime.resize(width=40, height=8)
            terminal.loop.advance(0.05)
            assert placement.width == 6

    def test_an_image_without_a_size_refits_when_the_terminal_shrinks(self):
        with xnano.open(offscreen=True, width=40, height=20) as terminal:
            placement = terminal.add(solid(30, 30, (0, 255, 0)))
            assert placement.width == 30
            terminal._runtime.resize(width=10, height=20)
            terminal.loop.advance(0.05)
            assert placement.width <= 10


class TestAnimatedImages:
    @pytest.fixture
    def animation(self):
        frames = [solid(4, 2, (255, 0, 0)), solid(4, 2, (0, 0, 255))]
        return TerminalImage.from_frames(frames).with_frames_per_second(10)

    def test_the_frame_follows_the_clock(self, animation):
        with xnano.open(offscreen=True, width=8, height=2) as terminal:
            terminal.add(animation)
            first = cell_at(terminal, 0, 0).foreground.to_rgb()
            terminal.loop.advance(0.15)
            second = cell_at(terminal, 0, 0).foreground.to_rgb()
            terminal.loop.advance(0.1)
            looped = cell_at(terminal, 0, 0).foreground.to_rgb()
        assert first != second
        assert looped == first

    def test_removing_the_placement_stops_the_animation(self, animation):
        with xnano.open(offscreen=True, width=8, height=2) as terminal:
            placement = terminal.add(animation)
            placement.remove()
            assert not terminal._images


def test_content_that_is_not_showable_says_what_is_accepted(terminal):
    with pytest.raises(TypeError, match='an image or the path of an image file'):
        terminal.add(3.5)  # type: ignore[arg-type]
