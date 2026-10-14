"""
tests.test_cursor

The terminal's cursor, and moving placements and canvases by cells.
"""

from __future__ import annotations

import pytest

import xnano
from xnano.cursor import Cursor
from xnano.events import Event
from xnano_core import Move, Place, Point


@pytest.fixture
def terminal():
    with xnano.open(offscreen=True, width=20, height=6, fps=10) as opened:
        yield opened


def dispatch(terminal, event) -> None:
    terminal._runtime.dispatch(event)
    terminal.loop.step()


class TestCursor:
    def test_the_terminal_has_one_cursor_without_a_position(self, terminal):
        assert isinstance(terminal.cursor, Cursor)
        assert terminal.cursor is terminal.cursor
        assert terminal.cursor.position is None
        assert terminal.cursor.is_visible

    def test_position_takes_a_pair_a_point_or_none(self, terminal):
        terminal.cursor.position = (3, 2)
        assert terminal.cursor.position == Point(3, 2)
        terminal.cursor.position = Point(1, 1)
        assert terminal.cursor.position == Point(1, 1)
        terminal.cursor.position = None
        assert terminal.cursor.position is None

    def test_shape_and_blinking_pass_through(self, terminal):
        terminal.cursor.shape = 'bar'
        terminal.cursor.is_blinking = True
        assert terminal.cursor.shape == 'bar'
        assert terminal.cursor.is_blinking

    def test_the_four_directions_move_by_a_count(self, terminal):
        cursor = terminal.cursor
        cursor.position = (5, 3)
        cursor.up()
        assert cursor.position == Point(5, 2)
        cursor.down(2)
        assert cursor.position == Point(5, 4)
        cursor.left(3)
        assert cursor.position == Point(2, 4)
        cursor.right()
        assert cursor.position == Point(3, 4)

    def test_moving_chains_and_returns_the_cursor(self, terminal):
        result = terminal.cursor.home().right(4).down(2).left()
        assert result is terminal.cursor
        assert terminal.cursor.position == Point(3, 2)

    def test_a_cursor_without_a_position_moves_from_the_top_left(self, terminal):
        terminal.cursor.right(2)
        assert terminal.cursor.position == Point(2, 0)

    def test_the_cursor_stops_at_the_edges_of_the_terminal(self, terminal):
        terminal.cursor.move(x=99, y=99)
        assert terminal.cursor.position == Point(19, 5)
        terminal.cursor.move(x=-99, y=-99)
        assert terminal.cursor.position == Point(0, 0)

    def test_move_takes_x_and_y_with_negative_numbers(self, terminal):
        terminal.cursor.position = (4, 4)
        terminal.cursor.move(x=-2, y=-3)
        assert terminal.cursor.position == Point(2, 1)
        terminal.cursor.move(y=2)
        assert terminal.cursor.position == Point(2, 3)

    def test_counts_that_are_not_cells_are_explained(self, terminal):
        with pytest.raises(ValueError, match='zero or more'):
            terminal.cursor.up(-1)
        with pytest.raises(TypeError, match='whole number of cells'):
            terminal.cursor.right(1.5)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='whole number of cells'):
            terminal.cursor.move(x=True)  # type: ignore[arg-type]

    def test_hide_keeps_the_position_and_show_brings_the_cursor_back(self, terminal):
        terminal.cursor.position = (4, 1)
        terminal.cursor.hide()
        assert not terminal.cursor.is_visible
        assert terminal.cursor.position == Point(4, 1)
        terminal.cursor.show()
        assert terminal.cursor.is_visible
        assert terminal.cursor.position == Point(4, 1)

    def test_show_gives_a_cursor_without_a_position_the_top_left_cell(self, terminal):
        terminal.cursor.show()
        assert terminal.cursor.position == Point(0, 0)

    def test_the_cursor_follows_a_placement(self, terminal):
        field = terminal.write('name', x=5, y=1)
        terminal.cursor.follow(field, x=4)
        field.x = 8
        assert terminal.cursor.position == Point(12, 1)
        field.down()
        assert terminal.cursor.position == Point(12, 2)

    def test_moving_stops_following_and_unfollow_leaves_the_cursor_in_place(
        self, terminal
    ):
        field = terminal.write('name', x=5, y=1)
        terminal.cursor.follow(field)
        terminal.cursor.unfollow()
        field.x = 9
        assert terminal.cursor.position == Point(5, 1)
        terminal.cursor.follow(field)
        terminal.cursor.right()
        field.x = 1
        assert terminal.cursor.position == Point(10, 1)

    def test_a_hook_sees_the_same_cursor(self, terminal):
        seen = []

        @terminal.on_key('x')
        def record(context):
            seen.append((context.cursor, context.root.cursor))

        dispatch(terminal, Event.key_press('x'))
        assert seen == [(terminal.cursor, terminal.cursor)]

    def test_a_closed_terminal_says_so(self):
        with xnano.open(offscreen=True, width=4, height=1) as closed:
            cursor = closed.cursor
        with pytest.raises(xnano.errors.TerminalClosedError):
            _ = cursor.position
        with pytest.raises(xnano.errors.TerminalClosedError):
            _ = closed.cursor

    def test_repr_names_the_position(self, terminal):
        assert repr(terminal.cursor) == 'Cursor(position=None, is_visible=True)'
        terminal.cursor.position = (2, 1)
        assert repr(terminal.cursor) == 'Cursor(position=(2, 1), is_visible=True)'


class TestMovingPlacements:
    def test_a_placement_moves_by_cells(self, terminal):
        mark = terminal.write('#', x=2, y=2)
        mark.move(x=3, y=-1)
        assert (mark.x, mark.y) == (5, 1)

    def test_the_four_directions_move_a_placement(self, terminal):
        mark = terminal.write('#', x=5, y=3)
        mark.up().left(2).down(2).right()
        assert (mark.x, mark.y) == (4, 4)

    def test_moving_returns_the_placement_so_calls_chain(self, terminal):
        mark = terminal.write('#')
        assert mark.right(2).down() is mark

    def test_a_range_holds_a_move_inside_it(self, terminal):
        thumb = terminal.write('#', x=(0, 10), y=1)
        thumb.right(99)
        assert thumb.x == 10
        thumb.left(99)
        assert thumb.x == 0

    def test_a_formula_keeps_its_formula_and_shifts_it(self, terminal):
        mark = terminal.write('#')
        mark.x = xnano.expressions.ParentWidth - 5
        terminal.loop.advance(0.05)
        assert mark.x == 15
        mark.left(2)
        terminal.loop.advance(0.05)
        assert mark.x == 13

    def test_piping_a_move_operation_is_held_inside_ranges_too(self, terminal):
        thumb = terminal.write('#', x=(0, 10), y=1)
        thumb | Move(50, 0)
        assert thumb.x == 10
        thumb | Place(-4, 1)
        assert thumb.x == 0

    def test_amounts_that_are_not_cells_are_explained(self, terminal):
        mark = terminal.write('#')
        with pytest.raises(ValueError, match='zero or more'):
            mark.left(-1)
        with pytest.raises(TypeError, match='whole number of cells'):
            mark.move(y=0.5)  # type: ignore[arg-type]


class TestMovingCanvases:
    def test_a_canvas_moves_by_cells(self):
        card = xnano.new('hi', x=2).right(3).down()
        assert (card.x, card.y) == (5, 1)

    def test_a_canvas_with_no_position_starts_from_zero(self):
        card = xnano.new('hi')
        card.right(2).down(3)
        assert (card.x, card.y) == (2, 3)

    def test_a_formula_position_stays_a_formula(self):
        card = xnano.new('hi', x=xnano.expressions.ParentWidth - 4)
        card.right(1)
        assert not isinstance(card.x, int)

    def test_a_built_canvas_moves_its_buffer(self):
        card = xnano.new('hi', x=1)
        buffer = card.build()
        card.right(2)
        assert buffer.x == 3

    def test_a_canvas_with_a_word_or_range_cannot_be_moved_from(self):
        for position in ('center', '50%', (0, 9)):
            with pytest.raises(TypeError, match='no single cell to move from'):
                xnano.new('hi', x=position).right(1)
