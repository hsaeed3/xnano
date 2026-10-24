"""
tests.test_cursor

The canvas's cursor, and moving placements and canvases by cells.
"""

from __future__ import annotations

import pytest

import xnano
from xnano.devices import Cursor
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
        assert isinstance(canvas.screen.cursor, Cursor)
        assert canvas.screen.cursor is canvas.screen.cursor
        assert canvas.screen.cursor.position is None
        assert canvas.screen.cursor.is_visible

    def test_position_takes_a_pair_a_point_or_none(self, canvas):
        canvas.screen.cursor.position = (3, 2)
        assert canvas.screen.cursor.position == Point(3, 2)
        canvas.screen.cursor.position = Point(1, 1)
        assert canvas.screen.cursor.position == Point(1, 1)
        canvas.screen.cursor.position = None
        assert canvas.screen.cursor.position is None

    def test_shape_and_blinking_pass_through(self, canvas):
        canvas.screen.cursor.shape = 'bar'
        canvas.screen.cursor.is_blinking = True
        assert canvas.screen.cursor.shape == 'bar'
        assert canvas.screen.cursor.is_blinking

    def test_the_four_directions_move_by_a_count(self, canvas):
        cursor = canvas.screen.cursor
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
        result = canvas.screen.cursor.home().right(4).down(2).left()
        assert result is canvas.screen.cursor
        assert canvas.screen.cursor.position == Point(3, 2)

    def test_a_cursor_without_a_position_moves_from_the_top_left(self, canvas):
        canvas.screen.cursor.right(2)
        assert canvas.screen.cursor.position == Point(2, 0)

    def test_the_cursor_stops_at_the_edges_of_the_terminal(self, canvas):
        canvas.screen.cursor.move(x=99, y=99)
        assert canvas.screen.cursor.position == Point(19, 5)
        canvas.screen.cursor.move(x=-99, y=-99)
        assert canvas.screen.cursor.position == Point(0, 0)

    def test_move_takes_x_and_y_with_negative_numbers(self, canvas):
        canvas.screen.cursor.position = (4, 4)
        canvas.screen.cursor.move(x=-2, y=-3)
        assert canvas.screen.cursor.position == Point(2, 1)
        canvas.screen.cursor.move(y=2)
        assert canvas.screen.cursor.position == Point(2, 3)

    def test_counts_that_are_not_cells_are_explained(self, canvas):
        with pytest.raises(ValueError, match='zero or more'):
            canvas.screen.cursor.up(-1)
        with pytest.raises(TypeError, match='whole number of cells'):
            canvas.screen.cursor.right(1.5)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='whole number of cells'):
            canvas.screen.cursor.move(x=True)  # type: ignore[arg-type]

    def test_hide_keeps_the_position_and_show_brings_the_cursor_back(self, canvas):
        canvas.screen.cursor.position = (4, 1)
        canvas.screen.cursor.hide()
        assert not canvas.screen.cursor.is_visible
        assert canvas.screen.cursor.position == Point(4, 1)
        canvas.screen.cursor.show()
        assert canvas.screen.cursor.is_visible
        assert canvas.screen.cursor.position == Point(4, 1)

    def test_show_gives_a_cursor_without_a_position_the_top_left_cell(self, canvas):
        canvas.screen.cursor.show()
        assert canvas.screen.cursor.position == Point(0, 0)

    def test_the_cursor_follows_a_placement(self, canvas):
        field = canvas.screen.write('name', x=5, y=1)
        canvas.screen.cursor.follow(field, x=4)
        field.x = 8
        assert canvas.screen.cursor.position == Point(12, 1)
        field.down()
        assert canvas.screen.cursor.position == Point(12, 2)

    def test_a_position_that_is_not_a_point_says_x_and_y(self, canvas):
        with pytest.raises(TypeError, match=r'an \(x, y\) pair of whole numbers'):
            canvas.screen.cursor.position = 5  # type: ignore[assignment]

    def test_a_removed_placement_cannot_be_followed(self, canvas):
        field = canvas.screen.write('abc', x=1, y=1)
        field.remove()
        with pytest.raises(
            xnano.errors.TerminalClosedError, match='placement was removed'
        ):
            canvas.screen.cursor.follow(field)
        canvas.clock.step()
        assert canvas.screen.cursor.position is None

    def test_a_region_of_a_removed_placement_cannot_be_followed(self, canvas):
        field = canvas.screen.write('abc', x=1, y=1)
        region = field.region
        field.remove()
        with pytest.raises(
            xnano.errors.TerminalClosedError, match='placement was removed'
        ):
            canvas.screen.cursor.follow(region)

    def test_moving_or_stop_following_leaves_the_cursor_in_place(self, canvas):
        field = canvas.screen.write('name', x=5, y=1)
        canvas.screen.cursor.follow(field)
        canvas.screen.cursor.stop_following()
        field.x = 9
        assert canvas.screen.cursor.position == Point(5, 1)
        canvas.screen.cursor.follow(field)
        canvas.screen.cursor.right()
        field.x = 1
        assert canvas.screen.cursor.position == Point(10, 1)

    def test_a_hook_sees_the_same_cursor(self, canvas):
        seen = []

        @canvas.hook(on='key', keys='x')
        def record(context):
            seen.append((context.screen.cursor, context.root.screen.cursor))

        dispatch(canvas, Event.key_press('x'))
        assert seen == [(canvas.screen.cursor, canvas.screen.cursor)]

    def test_a_closed_terminal_says_so(self):
        with xnano.new(width=4, height=1) as closed:
            cursor = closed.screen.cursor
        with pytest.raises(xnano.errors.TerminalClosedError):
            _ = cursor.position
        with pytest.raises(xnano.errors.TerminalClosedError):
            _ = closed.screen.cursor

    def test_repr_names_the_position(self, canvas):
        assert repr(canvas.screen.cursor) == 'Cursor(position=None, is_visible=True)'
        canvas.screen.cursor.position = (2, 1)
        assert repr(canvas.screen.cursor) == 'Cursor(position=(2, 1), is_visible=True)'


class TestMovingPlacements:
    def test_a_placement_moves_by_cells(self, canvas):
        mark = canvas.screen.write('#', x=2, y=2)
        mark.move(x=3, y=-1)
        assert (mark.x, mark.y) == (5, 1)

    def test_the_four_directions_move_a_placement(self, canvas):
        mark = canvas.screen.write('#', x=5, y=3)
        mark.up().left(2).down(2).right()
        assert (mark.x, mark.y) == (4, 4)

    def test_moving_returns_the_placement_so_calls_chain(self, canvas):
        mark = canvas.screen.write('#')
        assert mark.right(2).down() is mark

    def test_a_range_holds_a_move_inside_it(self, canvas):
        thumb = canvas.screen.write('#', x=(0, 10), y=1)
        thumb.right(99)
        assert thumb.x == 10
        thumb.left(99)
        assert thumb.x == 0

    def test_a_formula_keeps_its_formula_and_shifts_it(self, canvas):
        mark = canvas.screen.write('#')
        mark.x = xnano.expressions.ParentWidth - 5
        canvas.clock.step(delta_seconds=0.05)
        assert mark.x == 15
        mark.left(2)
        canvas.clock.step(delta_seconds=0.05)
        assert mark.x == 13

    def test_piping_a_move_operation_is_held_inside_ranges_too(self, canvas):
        thumb = canvas.screen.write('#', x=(0, 10), y=1)
        thumb | Move(50, 0)
        assert thumb.x == 10
        thumb | Place(-4, 1)
        assert thumb.x == 0

    def test_amounts_that_are_not_cells_are_explained(self, canvas):
        mark = canvas.screen.write('#')
        with pytest.raises(ValueError, match='zero or more'):
            mark.left(-1)
        with pytest.raises(TypeError, match='whole number of cells'):
            mark.move(y=0.5)  # type: ignore[arg-type]


class TestMovingCanvases:
    def test_a_canvas_sits_at_the_origin(self, canvas):
        assert (canvas.screen.x, canvas.screen.y) == (0, 0)
        assert canvas.screen.local(Point(3, 2)) == Point(3, 2)

    @pytest.mark.parametrize(
        'move',
        [
            lambda canvas: canvas.screen.up(),
            lambda canvas: canvas.screen.down(2),
            lambda canvas: canvas.screen.left(),
            lambda canvas: canvas.screen.right(),
            lambda canvas: canvas.screen.move(x=1, y=1),
        ],
    )
    def test_a_canvas_cannot_be_moved_and_says_what_moves(self, canvas, move):
        with pytest.raises(xnano.errors.TerminalError, match=r'placement\.move'):
            move(canvas)

    def test_what_is_written_on_a_canvas_moves_by_cells(self, canvas):
        card = canvas.screen.write('hi', x=2).right(3).down()
        assert (card.x, card.y) == (5, 1)

    def test_a_formula_position_stays_a_formula(self, canvas):
        card = canvas.screen.write('hi', x=xnano.expressions.ParentWidth - 4)
        card.right(1)
        assert card._bindings['x'][0] is not None
        canvas.clock.step()
        assert card.x == 17


class TestCursorFlags:
    @pytest.mark.parametrize('name', ['is_visible', 'is_blinking'])
    @pytest.mark.parametrize('value', [5, 'x', None])
    def test_a_flag_that_is_not_a_boolean_says_what_to_pass(self, canvas, name, value):
        with pytest.raises(TypeError, match=rf'{name} must be True or False, but got'):
            setattr(canvas.screen.cursor, name, value)
