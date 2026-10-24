"""
tests.test_text_alignment

Text in a placement larger than the text (a given width or height) sits where the words that
place the placement say: ``x='center'`` centers the lines inside the box as well as the box.
"""

from __future__ import annotations

import pytest

import xnano
from xnano_core import Buffer


@pytest.fixture
def canvas():
    with xnano.new(width=20, height=5) as opened:
        yield opened


def row(canvas, index: int) -> str:
    return canvas.screen.render().splitlines()[index]


class TestAcross:
    def test_centered_text_in_a_full_width_box_is_centered(self, canvas):
        placement = canvas.screen.write('hello', width='100%', x='center', y=0)
        assert (placement.x, placement.width) == (0, 20)
        assert row(canvas, 0) == ' ' * 7 + 'hello'

    def test_it_lands_where_centering_the_text_alone_does(self, canvas):
        alone = canvas.screen.write('hello', x='center', y=0)
        canvas.screen.write('hello', width='100%', x='center', y=1)
        rows = canvas.screen.render().splitlines()
        assert rows[0].index('hello') == rows[1].index('hello') == alone.x

    def test_right_aligns_the_text_to_the_right_edge(self, canvas):
        canvas.screen.write('hello', width='100%', x='right', y=0)
        assert row(canvas, 0) == ' ' * 15 + 'hello'

    def test_a_number_or_a_percentage_keeps_the_text_at_the_left(self, canvas):
        canvas.screen.write('hello', width=10, x=2, y=0)
        canvas.screen.write('hello', width=10, x='50%', y=1)
        assert row(canvas, 0) == '  hello'
        assert row(canvas, 1) == ' ' * 10 + 'hello'

    def test_each_line_is_centered_on_its_own(self, canvas):
        canvas.screen.write('a\nabc', width='100%', x='center', y=0)
        assert row(canvas, 0) == ' ' * 9 + 'a'
        assert row(canvas, 1) == ' ' * 8 + 'abc'

    def test_the_words_are_read_as_written_in_any_case(self, canvas):
        canvas.screen.write('hello', width='100%', x='Center', y=0)
        assert row(canvas, 0) == ' ' * 7 + 'hello'


class TestDown:
    def test_centered_text_in_a_tall_box_is_centered_down(self, canvas):
        canvas.screen.write('mid', width=3, height=5, y='center', x=0)
        assert canvas.screen.render().splitlines()[2] == 'mid'

    def test_bottom_puts_the_text_on_the_last_row(self, canvas):
        canvas.screen.write('end', height='100%', y='bottom', x=0)
        assert canvas.screen.render().splitlines()[4] == 'end'


class TestLooks:
    def test_a_border_goes_around_the_whole_box(self, canvas):
        canvas.screen.write('hello', width='100%', x='center', y=0, border='rounded')
        rows = canvas.screen.render().splitlines()
        assert rows[0] == '╭' + '─' * 18 + '╮'
        assert rows[1] == '│' + ' ' * 6 + 'hello' + ' ' * 7 + '│'

    def test_bordered_text_lands_on_the_same_column_as_plain_text(self, canvas):
        canvas.screen.write('hello', width='100%', x='center', y=0)
        canvas.screen.write('hello', width='100%', x='center', y=1, border='rounded')
        rows = canvas.screen.render().splitlines()
        assert rows[0].index('hello') == rows[2].index('hello')

    def test_padding_keeps_its_room_inside_the_box(self, canvas):
        canvas.screen.write('hello', width='100%', x='center', y=0, padding=1)
        assert canvas.screen.render().splitlines()[1] == ' ' * 7 + 'hello'

    def test_a_colored_text_is_centered(self, canvas):
        canvas.screen.write('hello', width='100%', x='center', y=0, foreground='red')
        assert row(canvas, 0) == ' ' * 7 + 'hello'

    def test_a_background_colors_the_whole_box(self, canvas):
        canvas.screen.write('hi', width=6, x='center', y=0, background='#0000ff')
        canvas.screen.render()
        cells = Buffer.from_cell_grid(canvas.screen.output.render().to_cell_grid())
        blue = (0, 0, 255)
        assert row(canvas, 0) == ' ' * 9 + 'hi'
        assert [cells[column, 0].background.to_rgb() for column in (7, 12)] == [
            blue,
            blue,
        ]
        assert cells[6, 0].background.to_rgb() != blue


class TestChanges:
    def test_text_assigned_later_keeps_a_given_width(self, canvas):
        placement = canvas.screen.write('hi', width=10, x='center', y=0)
        placement.text = 'hello'
        assert placement.width == 10
        assert row(canvas, 0) == ' ' * 7 + 'hello'

    def test_text_assigned_later_still_grows_a_box_with_no_given_size(self, canvas):
        placement = canvas.screen.write('hi', y=0)
        placement.text = 'hello there'
        assert placement.width == 11

    def test_the_text_reads_back_without_the_alignment(self, canvas):
        placement = canvas.screen.write('hello', width='100%', x='center', y=0)
        assert placement.text == 'hello'

    def test_moving_the_placement_with_a_number_aligns_it_left(self, canvas):
        placement = canvas.screen.write('hello', width=10, x='center', y=0)
        placement.x = 0
        assert row(canvas, 0) == 'hello'

    def test_a_resized_box_centers_again(self, canvas):
        placement = canvas.screen.write('hello', width=10, x='center', y=0)
        placement.width = 20
        assert row(canvas, 0) == ' ' * 7 + 'hello'

    def test_a_percentage_width_and_centered_x_follow_a_resize(self):
        with xnano.new(width=20, height=2) as canvas:
            canvas.screen.write('hello', width='50%', x='center', y=0)
            assert row(canvas, 0) == ' ' * 7 + 'hello'


class TestOtherContent:
    def test_a_region_in_a_full_width_box_is_centered(self, canvas):
        card = xnano.write('card', border='rounded')
        canvas.screen.write(card, width='100%', x='center', y=0)
        rows = canvas.screen.render().splitlines()
        assert rows[0] == ' ' * 7 + '╭────╮'
        assert rows[1] == ' ' * 7 + '│card│'

    def test_a_region_moved_to_a_number_goes_back_to_the_left(self, canvas):
        placement = canvas.screen.write(
            xnano.write('card'), width='100%', x='center', y=0
        )
        placement.x = 0
        assert row(canvas, 0) == 'card'

    def test_centered_art_is_placed_before_the_first_frame(self, canvas):
        art = xnano.draw(['RR', 'RR'], {'R': 'red'})
        placement = canvas.screen.write(art, x='center')
        assert placement.x == (20 - 2) // 2
