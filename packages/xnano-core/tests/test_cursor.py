"""The terminal's cursor: one per runtime, settable from any thread."""

from __future__ import annotations

import threading

import pytest
from helpers import rows

from xnano_core._xnano_core import Buffer, Cursor, Point


@pytest.fixture
def screen(runtime):
    root = Buffer()
    runtime.mount(root, geometry='inherit')
    return root


def test_the_cursor_is_hidden_until_it_has_a_position(runtime, screen):
    assert isinstance(runtime.cursor, Cursor)
    assert runtime.cursor.position is None
    frame = runtime.render()
    assert frame.cursor_position is None and not frame.is_cursor_visible


def test_a_position_is_a_point_or_a_pair(runtime, screen):
    runtime.cursor.position = (3, 1)
    assert runtime.cursor.position == Point(3, 1)
    assert runtime.render().cursor_position == Point(3, 1)
    runtime.cursor.position = Point(5, 2)
    assert runtime.render().cursor_position == Point(5, 2)
    runtime.cursor.position = None
    assert not runtime.render().is_cursor_visible


def test_a_bad_position_is_explained(runtime):
    with pytest.raises(TypeError, match='Point or an \\(x, y\\) pair'):
        runtime.cursor.position = 'here'
    with pytest.raises(TypeError, match='whole numbers'):
        runtime.cursor.position = (1, 2, 3)


def test_the_cursor_is_not_shown_outside_the_area(runtime, screen):
    for position in ((-1, 0), (40, 0), (0, 10), (0, -3)):
        runtime.cursor.position = position
        assert runtime.render().cursor_position is None, position


def test_visibility_and_style(runtime, screen):
    runtime.cursor.position = (0, 0)
    assert runtime.cursor.is_visible and runtime.cursor.shape is None
    runtime.cursor.shape = 'bar'
    runtime.cursor.is_blinking = True
    assert (runtime.cursor.shape, runtime.cursor.is_blinking) == ('bar', True)
    runtime.cursor.is_visible = False
    assert not runtime.render().is_cursor_visible
    runtime.cursor.is_visible = True
    assert runtime.render().is_cursor_visible
    runtime.cursor.shape = None
    assert runtime.cursor.shape is None
    with pytest.raises(ValueError, match='block", "bar" or "underline'):
        runtime.cursor.shape = 'heart'


def test_a_change_to_the_cursor_alone_draws_a_frame(runtime, screen):
    runtime.render()
    runtime.step()
    assert not runtime.needs_frame
    runtime.cursor.position = (1, 1)
    assert runtime.needs_frame
    assert runtime.step().did_render


def test_the_cursor_follows_a_buffer(runtime, screen):
    field = Buffer(width=6, height=1, x=2, y=1)
    screen.attach(field)
    runtime.cursor.follow(field, x=4)
    assert runtime.render().cursor_position == Point(6, 1)
    assert runtime.cursor.position == Point(6, 1)
    field.x = 3
    assert runtime.render().cursor_position == Point(7, 1)
    field.is_visible = False
    assert runtime.render().cursor_position is None
    field.is_visible = True
    screen.is_visible = False
    assert runtime.render().cursor_position is None


def test_a_position_stops_following(runtime, screen):
    field = Buffer(width=6, height=1, x=2, y=1)
    screen.attach(field)
    runtime.cursor.follow(field)
    runtime.cursor.position = (0, 0)
    field.x = 8
    assert runtime.render().cursor_position == Point(0, 0)
    runtime.cursor.follow(field)
    runtime.cursor.follow(None)
    assert runtime.cursor.position == Point(0, 0)


def test_the_cursor_is_set_from_another_thread(runtime, screen):
    errors = []
    # The runtime belongs to this thread; its cursor can be used from any thread.
    cursor = runtime.cursor

    def move():
        try:
            cursor.position = (4, 2)
            cursor.shape = 'underline'
        except Exception as error:  # noqa: BLE001
            errors.append(error)

    thread = threading.Thread(target=move)
    thread.start()
    thread.join()
    assert errors == []
    assert runtime.render().cursor_position == Point(4, 2)


def test_the_cursor_does_not_change_the_cells(runtime, screen):
    screen.write('abc')
    runtime.cursor.position = (1, 0)
    runtime.render()
    assert rows(screen)[0] == 'abc'
    assert 'Cursor' in repr(runtime.cursor)
