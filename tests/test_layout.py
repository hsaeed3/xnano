"""
Tests for a canvas's ``layout`` (stacking in write order) and the ``edges`` of content.
"""

from __future__ import annotations

import pytest

import xnano
from xnano.events import Event


def drawn_rows(canvas: xnano.Canvas[object, object]) -> dict[int, str]:
    """The rows of a canvas that hold something, by row number."""
    return {
        index: line
        for index, line in enumerate(canvas.screen.render().split('\n'))
        if line.strip()
    }


class TestColumnLayout:
    def test_text_written_before_a_written_canvas_takes_the_space_above_it(self):
        with xnano.new(width=20, height=10, layout='column') as terminal:
            terminal.screen.write('text', y='center')
            with xnano.new(height='50%') as canvas:
                canvas.screen.write('canvas')
            terminal.screen.write(canvas)
            assert drawn_rows(terminal) == {2: 'text', 5: 'canvas'}

    def test_text_written_after_a_canvas_takes_the_space_below_it(self):
        with xnano.new(width=20, height=10, layout='column') as terminal:
            terminal.screen.new('canvas', height='50%')
            terminal.screen.write('text', y='center')
            assert drawn_rows(terminal) == {0: 'canvas', 7: 'text'}

    def test_a_canvas_that_is_never_written_takes_no_space(self):
        with xnano.new(width=20, height=10, layout='column') as terminal:
            terminal.screen.write('text', y='50%')
            with xnano.new(height='50%') as canvas:
                canvas.screen.write('hidden')
            assert drawn_rows(terminal) == {5: 'text'}

    def test_bottom_is_the_last_row_of_the_slot(self):
        with xnano.new(width=20, height=10, layout='column') as terminal:
            terminal.screen.write('text', y='bottom')
            terminal.screen.new(height='50%')
            assert drawn_rows(terminal) == {4: 'text'}

    def test_pieces_without_a_size_share_what_is_left_equally(self):
        with xnano.new(width=10, height=9, layout='column') as terminal:
            terminal.screen.write('a')
            terminal.screen.write('b', height=3)
            terminal.screen.write('c')
            assert drawn_rows(terminal) == {0: 'a', 3: 'b', 6: 'c'}

    def test_removing_a_piece_gives_its_slot_to_the_others(self):
        with xnano.new(width=10, height=4, layout='column') as terminal:
            first = terminal.screen.write('first')
            terminal.screen.write('second')
            assert drawn_rows(terminal) == {0: 'first', 2: 'second'}
            first.remove()
            assert drawn_rows(terminal) == {0: 'second'}

    def test_closing_a_written_canvas_gives_its_slot_back(self):
        with xnano.new(width=10, height=4, layout='column') as terminal:
            panel = terminal.screen.new('panel', height=2)
            terminal.screen.write('text')
            assert drawn_rows(terminal) == {0: 'panel', 2: 'text'}
            panel.close()
            assert drawn_rows(terminal) == {0: 'text'}

    def test_terminal_text_in_a_shown_canvas_block_lands_in_its_slot(self):
        with xnano.new(width=10, height=6, layout='column') as terminal:
            terminal.screen.write('top')
            panel = terminal.screen.new(height=3)
            with panel:
                terminal.screen.write('in panel', y='bottom')
            assert drawn_rows(terminal) == {0: 'top', 5: 'in panel'}

    def test_a_window_resize_splits_the_slots_again(self):
        with xnano.new(width=10, height=4, layout='column') as terminal:
            terminal.screen.write('a')
            terminal.screen.write('b')
            terminal.push(Event.resize(width=10, height=8))
            terminal.clock.step()
            assert drawn_rows(terminal) == {0: 'a', 4: 'b'}


class TestRowLayout:
    def test_pieces_stack_from_left_to_right(self):
        with xnano.new(width=12, height=1, layout='row') as terminal:
            terminal.screen.write('ab', width=4)
            terminal.screen.write('cd')
            assert terminal.screen.render() == 'ab  cd'


class TestLayoutSettings:
    def test_overlay_is_the_default_and_places_each_piece_on_its_own(self):
        with xnano.new(width=10, height=2) as canvas:
            assert canvas.screen.layout == 'overlay'
            canvas.screen.write('aaaa', x=0, y=0)
            canvas.screen.write('b', x=0, y=0)
            assert drawn_rows(canvas) == {0: 'baaa'}

    def test_an_unknown_layout_is_refused(self):
        with pytest.raises(
            ValueError, match="layout must be 'overlay', 'column' or 'row'"
        ):
            xnano.new(layout='grid')  # type: ignore[call-overload]

    def test_a_size_that_is_not_cells_or_a_percentage_is_refused(self):
        with xnano.new(width=10, height=4, layout='column') as terminal:
            with pytest.raises(ValueError, match='size of its slot'):
                terminal.screen.write('x', height=xnano.expressions.ParentHeight - 1)
            terminal.screen.write('y')
            assert drawn_rows(terminal) == {0: 'y'}

    def test_a_canvas_keeps_the_layout_it_was_created_with(self):
        canvas = xnano.new(width=4, height=1, layout='column')
        with pytest.raises(TypeError, match='keeps the layout it was created with'):
            canvas.open(layout='row')
        canvas.close()


class TestStopEdges:
    @pytest.mark.parametrize(
        ('moves', 'position'),
        [
            (lambda ball: ball.up(9), (4, 0)),
            (lambda ball: ball.down(9), (4, 4)),
            (lambda ball: ball.left(9), (0, 2)),
            (lambda ball: ball.right(9), (8, 2)),
        ],
    )
    def test_moved_content_stops_at_every_edge(self, moves, position):
        with xnano.new(width=10, height=5) as canvas:
            ball = canvas.screen.write('oo', x=4, y=2, edges='stop')
            moves(ball)
            assert (ball.x, ball.y) == position

    def test_moves_past_the_edge_do_not_pile_up_on_a_formula_position(self):
        with xnano.new(width=10, height=3) as canvas:
            label = canvas.screen.write('ab', x='center', y='center', edges='stop')
            label.left(20)
            canvas.clock.step()
            assert label.x == 0
            label.right(1)
            canvas.clock.step()
            assert label.x == 1, 'the opposite move shows at once'
            label.right(20).down(20)
            canvas.clock.step()
            assert (label.x, label.y) == (8, 2)

    def test_an_assigned_position_and_a_formula_stop_at_the_edge(self):
        with xnano.new(width=10, height=3, fps=10) as canvas:
            ball = canvas.screen.write('o', edges='stop')
            ball.x = 40
            assert ball.x == 9
            ball.y = xnano.expressions.TimeElapsed * 100
            canvas.clock.step(delta_seconds=1.0)
            assert ball.y == 2

    def test_a_range_takes_the_place_of_the_edges(self):
        with xnano.new(width=10, height=3) as canvas:
            thumb = canvas.screen.write('#', x=(0, 4), edges='stop')
            thumb.right(9)
            assert thumb.x == 4

    def test_content_larger_than_its_area_stays_at_the_start(self):
        with xnano.new(width=4, height=1) as canvas:
            wide = canvas.screen.write('too wide', edges='stop')
            wide.right(3)
            assert wide.x == 0

    def test_the_canvas_setting_is_followed_until_a_piece_has_its_own(self):
        with xnano.new(width=10, height=2, edges='stop') as canvas:
            assert canvas.screen.edges == 'stop'
            ball = canvas.screen.write('o')
            assert ball.edges == 'stop'
            ball.right(20)
            assert ball.x == 9
            ball.edges = 'clip'
            ball.right(20)
            assert ball.x == 29
            ball.edges = None
            assert ball.x == 9

    def test_changing_the_canvas_setting_holds_what_is_already_written(self):
        with xnano.new(width=10, height=2) as canvas:
            ball = canvas.screen.write('o', x=30)
            canvas.screen.edges = 'stop'
            assert ball.x == 9

    def test_a_canvas_created_in_a_block_takes_the_edges_of_the_canvas_around_it(self):
        with xnano.new(width=10, height=4, edges='stop'):
            with xnano.new() as inner:
                assert inner.screen.edges == 'stop'
            with xnano.new(edges='wrap') as own:
                assert own.screen.edges == 'wrap'

    def test_terminal_text_in_a_canvas_block_follows_that_canvas(self):
        with xnano.new(width=10, height=6) as terminal:
            with xnano.new(height='50%', edges='stop') as canvas:
                label = terminal.screen.write('ab')
            assert label.edges == 'stop'
            label.down(9).right(20)
            assert (label.x, label.y) == (8, 2)
            canvas.screen.edges = 'clip'
            assert label.edges == 'clip'

    def test_a_written_canvas_stops_at_the_edges_of_the_canvas_around_it(self):
        with xnano.new(width=10, height=4, edges='stop') as outer:
            panel = outer.screen.new('box', width=3, height=1)
            panel.screen.down(10).right(10)
            assert (panel.screen.x, panel.screen.y) == (7, 3)

    def test_an_unknown_value_is_refused(self):
        with xnano.new(width=4, height=1) as canvas:
            with pytest.raises(
                ValueError, match="edges must be 'clip', 'stop' or 'wrap'"
            ):
                canvas.screen.write('x', edges='bounce')  # type: ignore[arg-type]
            assert canvas.screen.render() == ''


class TestWrapEdges:
    def test_text_continues_on_the_next_rows_and_keeps_what_was_written(self):
        with xnano.new(width=8, height=3) as canvas:
            note = canvas.screen.write('one two three', edges='wrap')
            assert note.text == 'one two three'
            assert drawn_rows(canvas) == {0: 'one two', 1: 'three'}
            note.text = 'a b'
            assert drawn_rows(canvas) == {0: 'a b'}

    def test_text_is_wrapped_again_when_its_area_changes_width(self):
        with xnano.new(width=8, height=3) as canvas:
            canvas.screen.write('one two three', edges='wrap')
            canvas.push(Event.resize(width=4, height=3))
            canvas.clock.step()
            assert drawn_rows(canvas) == {0: 'one', 1: 'two', 2: 'thre'}

    def test_turning_wrapping_off_shows_the_text_as_written(self):
        with xnano.new(width=20, height=3) as canvas:
            note = canvas.screen.write('aaaa bbbb', edges='wrap')
            note.edges = 'clip'
            assert note.text == 'aaaa bbbb'
            assert drawn_rows(canvas) == {0: 'aaaa bbbb'}

    def test_turning_wrapping_off_keeps_a_width_that_was_given(self):
        with xnano.new(width=20, height=3) as canvas:
            note = canvas.screen.write('aaaa bbbb', width=4, edges='wrap')
            note.edges = 'clip'
            assert note.text == 'aaaa bbbb'
            assert note.width == 4
            assert drawn_rows(canvas) == {0: 'aaaa'}
