"""
tests.test_cursor

The canvas's cursor, and moving placements and canvases by cells.
"""

from __future__ import annotations

import pytest

import xnano
from xnano.cursor import Cursor
from xnano.events import Event
from xnano_core import Move, Place, Point


@pytest.fixture
def canvas():
    with xnano.new(width=20, height=6, fps=10) as opened:
        yield opened


def dispatch(canvas, event) -> None:
    canvas.push(event)
    canvas.deliver_events()


class TestCursor:
    def test_the_terminal_has_one_cursor_without_a_position(self, canvas):
        assert isinstance(canvas.cursor, Cursor)
        assert canvas.cursor is canvas.cursor
        assert canvas.cursor.position is None
        assert canvas.cursor.is_visible

    def test_position_takes_a_pair_a_point_or_none(self, canvas):
        canvas.cursor.position = (3, 2)
        assert canvas.cursor.position == Point(3, 2)
        canvas.cursor.position = Point(1, 1)
        assert canvas.cursor.position == Point(1, 1)
        canvas.cursor.position = None
        assert canvas.cursor.position is None

    def test_shape_and_blinking_pass_through(self, canvas):
        canvas.cursor.shape = 'bar'
        canvas.cursor.is_blinking = True
        assert canvas.cursor.shape == 'bar'
        assert canvas.cursor.is_blinking

    def test_the_four_directions_move_by_a_count(self, canvas):
        cursor = canvas.cursor
        cursor.position = (5, 3)
        cursor.up()
        assert cursor.position == Point(5, 2)
        cursor.down(2)
        assert cursor.position == Point(5, 4)
        cursor.left(3)
        assert cursor.position == Point(2, 4)
        cursor.right()
        assert cursor.position == Point(3, 4)

    def test_moving_chains_and_returns_the_cursor(self, canvas):
        result = canvas.cursor.home().right(4).down(2).left()
        assert result is canvas.cursor
        assert canvas.cursor.position == Point(3, 2)

    def test_a_cursor_without_a_position_moves_from_the_top_left(self, canvas):
        canvas.cursor.right(2)
        assert canvas.cursor.position == Point(2, 0)

    def test_the_cursor_stops_at_the_edges_of_the_terminal(self, canvas):
        canvas.cursor.move(x=99, y=99)
        assert canvas.cursor.position == Point(19, 5)
        canvas.cursor.move(x=-99, y=-99)
        assert canvas.cursor.position == Point(0, 0)

    def test_move_takes_x_and_y_with_negative_numbers(self, canvas):
        canvas.cursor.position = (4, 4)
        canvas.cursor.move(x=-2, y=-3)
        assert canvas.cursor.position == Point(2, 1)
        canvas.cursor.move(y=2)
        assert canvas.cursor.position == Point(2, 3)

    def test_counts_that_are_not_cells_are_explained(self, canvas):
        with pytest.raises(ValueError, match='zero or more'):
            canvas.cursor.up(-1)
        with pytest.raises(TypeError, match='whole number of cells'):
            canvas.cursor.right(1.5)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='whole number of cells'):
            canvas.cursor.move(x=True)  # type: ignore[arg-type]

    def test_hide_keeps_the_position_and_show_brings_the_cursor_back(self, canvas):
        canvas.cursor.position = (4, 1)
        canvas.cursor.hide()
        assert not canvas.cursor.is_visible
        assert canvas.cursor.position == Point(4, 1)
        canvas.cursor.show()
        assert canvas.cursor.is_visible
        assert canvas.cursor.position == Point(4, 1)

    def test_show_gives_a_cursor_without_a_position_the_top_left_cell(self, canvas):
        canvas.cursor.show()
        assert canvas.cursor.position == Point(0, 0)

    def test_the_cursor_follows_a_placement(self, canvas):
        field = canvas.write('name', x=5, y=1)
        canvas.cursor.follow(field, x=4)
        field.x = 8
        assert canvas.cursor.position == Point(12, 1)
        field.down()
        assert canvas.cursor.position == Point(12, 2)

    def test_moving_stops_following_and_unfollow_leaves_the_cursor_in_place(self, canvas):
        field = canvas.write('name', x=5, y=1)
        canvas.cursor.follow(field)
        canvas.cursor.unfollow()
        field.x = 9
        assert canvas.cursor.position == Point(5, 1)
        canvas.cursor.follow(field)
        canvas.cursor.right()
        field.x = 1
        assert canvas.cursor.position == Point(10, 1)

    def test_a_hook_sees_the_same_cursor(self, canvas):
        seen = []

        @canvas.on_key('x')
        def record(context):
            seen.append((context.cursor, context.root.cursor))

        dispatch(canvas, Event.key_press('x'))
        assert seen == [(canvas.cursor, canvas.cursor)]

    def test_a_closed_terminal_says_so(self):
        with xnano.new(width=4, height=1) as closed:
            cursor = closed.cursor
        with pytest.raises(xnano.errors.TerminalClosedError):
            _ = cursor.position
        with pytest.raises(xnano.errors.TerminalClosedError):
            _ = closed.cursor

    def test_repr_names_the_position(self, canvas):
        assert repr(canvas.cursor) == 'Cursor(position=None, is_visible=True)'
        canvas.cursor.position = (2, 1)
        assert repr(canvas.cursor) == 'Cursor(position=(2, 1), is_visible=True)'


class TestMovingPlacements:
    def test_a_placement_moves_by_cells(self, canvas):
        mark = canvas.write('#', x=2, y=2)
        mark.move(x=3, y=-1)
        assert (mark.x, mark.y) == (5, 1)

    def test_the_four_directions_move_a_placement(self, canvas):
        mark = canvas.write('#', x=5, y=3)
        mark.up().left(2).down(2).right()
        assert (mark.x, mark.y) == (4, 4)

    def test_moving_returns_the_placement_so_calls_chain(self, canvas):
        mark = canvas.write('#')
        assert mark.right(2).down() is mark

    def test_a_range_holds_a_move_inside_it(self, canvas):
        thumb = canvas.write('#', x=(0, 10), y=1)
        thumb.right(99)
        assert thumb.x == 10
        thumb.left(99)
        assert thumb.x == 0

    def test_a_formula_keeps_its_formula_and_shifts_it(self, canvas):
        mark = canvas.write('#')
        mark.x = xnano.expressions.ParentWidth - 5
        canvas.step(delta_seconds=0.05)
        assert mark.x == 15
        mark.left(2)
        canvas.step(delta_seconds=0.05)
        assert mark.x == 13

    def test_piping_a_move_operation_is_held_inside_ranges_too(self, canvas):
        thumb = canvas.write('#', x=(0, 10), y=1)
        thumb | Move(50, 0)
        assert thumb.x == 10
        thumb | Place(-4, 1)
        assert thumb.x == 0

    def test_amounts_that_are_not_cells_are_explained(self, canvas):
        mark = canvas.write('#')
        with pytest.raises(ValueError, match='zero or more'):
            mark.left(-1)
        with pytest.raises(TypeError, match='whole number of cells'):
            mark.move(y=0.5)  # type: ignore[arg-type]


class TestMovingCanvases:
    def test_a_canvas_sits_at_the_origin(self, canvas):
        assert (canvas.x, canvas.y) == (0, 0)
        assert canvas.local(Point(3, 2)) == Point(3, 2)

    @pytest.mark.parametrize(
        'move',
        [
            lambda canvas: canvas.up(),
            lambda canvas: canvas.down(2),
            lambda canvas: canvas.left(),
            lambda canvas: canvas.right(),
            lambda canvas: canvas.move(x=1, y=1),
        ],
    )
    def test_a_canvas_cannot_be_moved_and_says_what_moves(self, canvas, move):
        with pytest.raises(xnano.errors.TerminalError, match=r'placement\.move'):
            move(canvas)

    def test_what_is_written_on_a_canvas_moves_by_cells(self, canvas):
        card = canvas.write('hi', x=2).right(3).down()
        assert (card.x, card.y) == (5, 1)

    def test_a_formula_position_stays_a_formula(self, canvas):
        card = canvas.write('hi', x=xnano.expressions.ParentWidth - 4)
        card.right(1)
        assert card._bindings['x'][0] is not None
        canvas.step()
        assert card.x == 17
