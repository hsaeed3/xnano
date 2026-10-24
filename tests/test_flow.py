"""
tests.test_flow

Content given no position goes on the next line (``x`` and ``y`` default to ``'next'``), and
keeps following what was written before it when that grows, shrinks, moves or is removed.
"""

from __future__ import annotations

import time

import pytest

import xnano
from xnano.errors import TerminalError
from xnano.events import Event


@pytest.fixture
def canvas():
    with xnano.new(width=24, height=10) as opened:
        yield opened


def rows(canvas) -> list[str]:
    return canvas.screen.render().splitlines()


class TestNextLine:
    def test_writes_with_no_position_go_on_the_next_line(self, canvas):
        first = canvas.screen.write('first')
        second = canvas.screen.write('second')
        third = canvas.screen.write('third')
        assert [(placement.x, placement.y) for placement in (first, second, third)] == [
            (0, 0),
            (0, 1),
            (0, 2),
        ]
        assert rows(canvas)[:3] == ['first', 'second', 'third']

    def test_a_line_starts_below_the_whole_height_of_the_one_before(self, canvas):
        canvas.screen.write('two\nlines')
        below = canvas.screen.write('below')
        assert below.y == 2

    def test_a_given_x_keeps_the_line_from_the_flow(self, canvas):
        canvas.screen.write('title')
        centered = canvas.screen.write('mid', x='center')
        assert (centered.x, centered.y) == ((24 - 3) // 2, 1)

    def test_content_given_a_row_stays_out_of_the_lines(self, canvas):
        canvas.screen.write('status', y='bottom')
        canvas.screen.write('header', y=3)
        body = canvas.screen.write('body')
        assert body.y == 0

    def test_a_box_and_a_widget_take_their_lines(self, canvas):
        box = canvas.screen.write(xnano.box(6, 3, border='rounded'))
        after = canvas.screen.write('after')
        assert (box.y, after.y) == (0, 3)

    def test_a_bordered_text_takes_its_whole_height(self, canvas):
        card = canvas.screen.write('card', border='rounded')
        after = canvas.screen.write('after')
        assert after.y == card.y + card.height == 3


class TestFollowing:
    def test_a_line_that_grows_moves_every_line_after_it(self, canvas):
        first = canvas.screen.write('first')
        second = canvas.screen.write('second')
        third = canvas.screen.write('third')
        first.text = 'first\ngrows\ntaller'
        assert (second.y, third.y) == (3, 4)
        assert rows(canvas)[:5] == ['first', 'grows', 'taller', 'second', 'third']

    def test_a_line_that_shrinks_pulls_the_lines_after_it_up(self, canvas):
        first = canvas.screen.write('a\nb\nc')
        second = canvas.screen.write('second')
        first.text = 'a'
        assert second.y == 1

    def test_a_line_in_the_middle_that_grows_moves_only_what_follows(self, canvas):
        first = canvas.screen.write('first')
        middle = canvas.screen.write('middle')
        last = canvas.screen.write('last')
        middle.text = 'middle\nlonger'
        assert (first.y, middle.y, last.y) == (0, 1, 3)

    def test_removing_a_line_closes_the_gap(self, canvas):
        canvas.screen.write('first')
        middle = canvas.screen.write('middle')
        last = canvas.screen.write('last')
        middle.remove()
        assert last.y == 1

    def test_removing_the_first_line_moves_the_rest_to_the_top(self, canvas):
        first = canvas.screen.write('first')
        second = canvas.screen.write('second')
        first.remove()
        assert second.y == 0

    def test_a_line_given_a_row_later_leaves_its_place_to_the_lines_after_it(
        self, canvas
    ):
        canvas.screen.write('first')
        middle = canvas.screen.write('middle')
        last = canvas.screen.write('last')
        middle.y = 8
        assert last.y == 1

    def test_a_resized_line_moves_what_follows(self, canvas):
        panel = canvas.screen.write(xnano.box(10, 2, border='plain'))
        after = canvas.screen.write('after')
        panel.height = 5
        assert after.y == 5

    def test_a_component_that_grows_moves_what_follows(self, canvas):
        @xnano.writable
        def listing(context: xnano.Context) -> str:
            count = int(context.root.state.get('count', default=1) or 1)
            return '\n'.join(f'item {index}' for index in range(count))

        items = canvas.screen.write(listing)
        footer = canvas.screen.write('footer')
        assert footer.y == 1
        canvas.state.set('count', 3)
        canvas.deliver_events()
        assert items.height == 3
        assert footer.y == 3

    def test_a_percentage_height_follows_the_canvas_and_moves_what_follows(self):
        with xnano.new(width=20, height=10) as canvas:
            canvas.screen.write(xnano.box(10, '50%'))
            footer = canvas.screen.write('footer')
            assert footer.y == 5


class TestLeavingAndJoining:
    def test_a_position_given_later_leaves_the_flow_on_that_axis(self, canvas):
        first = canvas.screen.write('first')
        second = canvas.screen.write('second')
        second.y = 7
        first.text = 'first\ngrows'
        assert second.y == 7

    def test_a_line_that_left_rejoins_where_it_was_written(self, canvas):
        canvas.screen.write('first')
        second = canvas.screen.write('second')
        third = canvas.screen.write('third')
        second.y = 6
        assert third.y == 1
        second.y = 'next'
        assert (second.y, third.y) == (1, 2)

    def test_assigning_next_follows_the_flow_again(self, canvas):
        canvas.screen.write('first')
        second = canvas.screen.write('second', y=8)
        second.y = 'next'
        assert second.y == 1

    def test_moving_a_line_leaves_the_flow_on_that_axis(self, canvas):
        first = canvas.screen.write('first')
        second = canvas.screen.write('second')
        second.down(2)
        first.text = 'first\ngrows'
        assert second.y == 3

    def test_a_locked_line_keeps_where_it_was_written(self, canvas):
        first = canvas.screen.write('first')
        second = canvas.screen.write('second', lock=True)
        first.text = 'first\ngrows'
        assert second.y == 1

    def test_next_is_a_position_and_not_a_size(self, canvas):
        with pytest.raises(TerminalError, match="'next' places something after"):
            canvas.screen.write('x', width='next')


class TestSameRow:
    def test_a_given_row_continues_after_what_was_written_on_it(self, canvas):
        label = canvas.screen.write('Name: ', y=4)
        field = canvas.screen.write('[____]', y=4)
        button = canvas.screen.write('[ok]', y=4)
        assert (label.x, field.x, button.x) == (0, 6, 12)
        assert rows(canvas)[4] == 'Name: [____][ok]'

    def test_a_row_continuation_follows_when_the_one_before_grows(self, canvas):
        label = canvas.screen.write('Name: ', y=4)
        field = canvas.screen.write('[____]', y=4)
        label.text = 'Your name: '
        assert field.x == 11

    def test_a_row_with_no_room_left_starts_at_the_first_column(self, canvas):
        canvas.screen.write('x' * 20, y=2)
        after = canvas.screen.write('long text', y=2)
        assert after.x == 0

    def test_a_full_width_world_does_not_push_an_overlay_off_the_screen(self, canvas):
        canvas.screen.write(
            xnano.pixel_art(None, width=24, height=20), width='100%', height='100%'
        )
        overlay = canvas.screen.write('HP 10', y=0)
        assert overlay.x == 0

    def test_a_different_row_starts_at_the_first_column(self, canvas):
        canvas.screen.write('above', y=1)
        below = canvas.screen.write('below', y=2)
        assert below.x == 0

    def test_the_next_line_goes_below_the_tallest_part_of_a_line(self, canvas):
        label = canvas.screen.write('Name: ')
        field = canvas.screen.write('one\ntwo\nthree', y=label.y)
        after = canvas.screen.write('after')
        assert field.x == 6
        assert after.y == 3

    def test_a_continuation_of_a_row_given_a_position_is_not_part_of_the_lines(
        self, canvas
    ):
        canvas.screen.write('Name: ', y=5)
        canvas.screen.write('one\ntwo', y=5)
        after = canvas.screen.write('after')
        assert after.y == 0


class TestContainers:
    def test_a_placement_has_its_own_lines_inside_it(self, canvas):
        card = canvas.screen.write(xnano.box(16, 6, border='rounded'))
        first = card.write('first')
        second = card.write('second')
        after = canvas.screen.write('after')
        assert (first.y, second.y) == (0, 1)
        assert after.y == 6

    def test_a_stacking_canvas_gives_each_write_its_own_slot(self):
        with xnano.new(width=10, height=4, layout='column') as canvas:
            top = canvas.screen.write('top')
            bottom = canvas.screen.write('bottom')
            assert rows(canvas)[:3] == ['top', '', 'bottom']
            assert (top.y, bottom.y) == (0, 0)

    def test_a_canvas_written_into_another_takes_a_line(self, canvas):
        canvas.screen.write('above')
        inner = xnano.new(width=10, height=2)
        inner.screen.write('inside')
        placement = canvas.screen.write(inner)
        after = canvas.screen.write('after')
        assert (placement.y, after.y) == (1, 3)
        inner.close()

    def test_a_canvas_made_in_a_block_takes_no_line_until_it_is_written(self, canvas):
        panel = xnano.new(width=10, height=2)
        panel.screen.write('panel')
        first = canvas.screen.write('first')
        assert first.y == 0
        placed = canvas.screen.write(panel)
        assert placed.y == 1

    def test_measuring_a_standalone_write_inside_a_canvas_takes_no_line(self, canvas):
        xnano.region('measured', border='rounded')
        first = canvas.screen.write('first')
        assert first.y == 0


class TestParticipants:
    def test_placements_with_their_own_position_cost_the_flow_nothing(self, canvas):
        for index in range(50):
            canvas.screen.write('.', x=index % 24, y=index % 10)
        hud = canvas.screen.write('hud')
        flow = canvas._flows[id(canvas._content)]
        # Only the line takes part: content given a position stays out of the lines.
        assert flow.participants == [hud]
        assert hud.y == 0

    def test_a_moving_sprite_with_its_own_position_does_not_settle_the_flow(self, canvas):
        sprite = canvas.screen.write('@', x=3, y=9)
        canvas.screen.write('line one', x=0, y=0)
        canvas.screen.write('line two')
        flow = canvas._flows[id(canvas._content)]
        assert sprite not in flow.participants
        sprite.x = 4
        assert sprite._is_flow_participant is False


class TestContentGivenBothCoordinates:
    def test_a_row_continues_after_it(self, canvas):
        canvas.screen.write('Name: ', x=2, y=4)
        field = canvas.screen.write('[__]', y=4)
        assert field.x == 8

    def test_removing_it_moves_the_rest_of_its_row_back(self, canvas):
        canvas.screen.write('ab', y=4)
        label = canvas.screen.write('Name: ', x=2, y=4)
        field = canvas.screen.write('[__]', y=4)
        assert field.x == 8
        label.remove()
        assert field.x == 2

    def test_removing_it_moves_no_line(self, canvas):
        first = canvas.screen.write('first')
        sprite = canvas.screen.write('@', x=5, y=5)
        sprite.remove()
        second = canvas.screen.write('second')
        assert (first.y, second.y) == (0, 1)

    def test_it_can_follow_the_flow_later(self, canvas):
        canvas.screen.write('first')
        note = canvas.screen.write('note', x=10, y=8)
        canvas.screen.write('label', x=1, y=9)
        note.x = 'next'
        note.y = 'next'
        assert (note.x, note.y) == (0, 1)


def test_a_prompt_appears_on_the_next_line():
    with xnano.new(realtime=True, width=30, height=3) as canvas:
        canvas.screen.write('Welcome')

        @canvas.hook(on='tick', after=0.05)
        def answer(context: xnano.Context) -> None:
            assert 'Your name:' in canvas.screen.render().splitlines()[1]
            canvas.push(Event.key_press('enter'))

        assert canvas.keyboard.prompt('Your name: ') == ''


class TestFit:
    def test_a_canvas_that_fits_takes_the_size_of_its_lines(self):
        with xnano.new(width='fit', height='fit') as canvas:
            canvas.screen.write('first line')
            canvas.screen.write('second')
            assert (canvas.screen.width, canvas.screen.height) == (10, 2)
            assert canvas.screen.render().splitlines() == ['first line', 'second']

    def test_it_grows_and_shrinks_with_its_content(self):
        with xnano.new(width='fit', height='fit') as canvas:
            first = canvas.screen.write('a')
            canvas.screen.write('b')
            first.text = 'a much longer line\nand a second'
            assert (canvas.screen.width, canvas.screen.height) == (18, 3)
            first.text = 'a'
            assert (canvas.screen.width, canvas.screen.height) == (1, 2)

    def test_one_axis_can_fit_while_the_other_is_given(self):
        with xnano.new(width=30, height='fit') as canvas:
            canvas.screen.write('title', width='100%', x='center', border='rounded')
            canvas.screen.write('body')
            assert (canvas.screen.width, canvas.screen.height) == (30, 4)
            assert (
                canvas.screen.render().splitlines()[1]
                == '│' + ' ' * 11 + 'title' + ' ' * 12 + '│'
            )

    def test_content_placed_by_the_canvas_size_is_placed_within_the_fit(self):
        with xnano.new(width='fit', height='fit') as canvas:
            canvas.screen.write('a wider line here')
            centered = canvas.screen.write('mid', x='center')
            assert canvas.screen.width == 17
            assert centered.x == 7

    def test_a_relative_size_does_not_grow_a_canvas_that_fits(self):
        with xnano.new(width='fit', height='fit') as canvas:
            canvas.screen.write('twelve chars')
            canvas.screen.write(xnano.box('100%', 1))
            assert canvas.screen.width == 12

    def test_an_empty_canvas_that_fits_is_one_cell(self):
        with xnano.new(width='fit', height='fit') as canvas:
            assert (canvas.screen.width, canvas.screen.height) == (1, 1)

    def test_a_canvas_written_into_another_keeps_the_size_of_its_content(self):
        with xnano.new(width=30, height=10) as outer:
            inner = xnano.new(width='fit', height='fit')
            inner.screen.write('one')
            placed = outer.screen.write(inner)
            after = outer.screen.write('after')
            assert (placed.width, placed.height) == (3, 1)
            assert after.y == 1
            inner.screen.write('two')
            outer.screen.render()
            assert placed.height == 2
            assert after.y == 2
            inner.close()

    def test_no_size_still_means_the_default_size(self):
        with xnano.new() as canvas:
            canvas.screen.write('hello', width='100%', x='center')
            assert (canvas.screen.width, canvas.screen.height) == (80, 24)
            assert canvas.screen.render().splitlines()[0] == ' ' * 37 + 'hello'

    def test_a_stacking_canvas_cannot_fit(self):
        with pytest.raises(ValueError, match='cannot take the size of them'):
            xnano.new(width='fit', layout='column')

    def test_fit_is_spelled_as_a_word(self):
        with pytest.raises(ValueError, match="'fit'"):
            xnano.new(width='fits')


def fastest_seconds(action, *, rounds: int = 3) -> float:
    """The fastest of a few runs of ``action``, each on a canvas of its own."""
    fastest = float('inf')
    for _ in range(rounds):
        with xnano.new(width=80, height=40) as canvas:
            start = time.perf_counter()
            action(canvas)
            fastest = min(fastest, time.perf_counter() - start)
    return fastest


class TestScaling:
    """Writing grows with the number of placements, not with its square."""

    @pytest.mark.parametrize(
        'write',
        [
            lambda canvas, index: canvas.screen.write(f'line {index}'),
            lambda canvas, index: canvas.screen.write(
                f'cell {index}', x='next', y=index % 40
            ),
            lambda canvas, index: canvas.screen.write(f'line {index}', x=0, y=index % 40),
        ],
        ids=['next lines', 'rows that continue', 'explicit positions'],
    )
    def test_four_times_the_writes_take_far_less_than_sixteen_times_as_long(self, write):
        def write_lines(count: int):
            return lambda canvas: [write(canvas, index) for index in range(count)]

        few = fastest_seconds(write_lines(300))
        many = fastest_seconds(write_lines(1200))
        assert many / few < 8, (
            f'{few * 1000:.1f} ms for 300, {many * 1000:.1f} ms for 1200'
        )

    def test_changing_the_last_line_does_not_look_at_every_line(self):
        def seconds_to_change_the_last_of(count: int) -> float:
            fastest = float('inf')
            for _ in range(3):
                with xnano.new(width=80, height=40) as canvas:
                    for index in range(count):
                        canvas.screen.write(f'line {index}')
                    last = canvas.screen.write('0')
                    start = time.perf_counter()
                    for index in range(200):
                        last.text = str(index)
                    fastest = min(fastest, time.perf_counter() - start)
            return fastest

        timings = [seconds_to_change_the_last_of(count) for count in (100, 1600)]
        assert timings[1] / timings[0] < 4, timings
