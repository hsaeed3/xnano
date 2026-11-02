"""
tests.test_live_values

A position or a size can read input that the canvas did not receive yet, such as the pointer
before it moves: the placement is written, is not drawn until the input arrives, and then
follows it. A placement's text can be styled text, drawn with the styles of its spans.
"""

from __future__ import annotations

import time
from typing import cast

import pytest

import xnano
from xnano.events import Event
from xnano.expressions import MousePosition, PointerPosition
from xnano.styles import Style, StyledText


@pytest.fixture
def canvas():
    with xnano.new(width=20, height=4) as opened:
        yield opened


def rows(canvas) -> list[str]:
    return canvas.screen.render().splitlines()


def move_pointer(canvas, column: int, row: int) -> None:
    canvas.push(Event.mouse_event(column=column, row=row, kind='move'))
    canvas.deliver_events()
    canvas.clock.step()


def is_blank(canvas) -> bool:
    return canvas.screen.render().strip() == ''


class TestFollowingThePointer:
    def test_a_placement_that_reads_the_pointer_is_not_drawn_before_it_moves(
        self, canvas
    ):
        cursor = canvas.screen.write('+', x=PointerPosition.x, y=PointerPosition.y)
        canvas.clock.step()
        assert is_blank(canvas)
        assert cursor.is_visible, 'waiting for the pointer must not change is_visible'
        assert cursor.core_buffer.is_visible

    def test_it_is_drawn_at_the_pointer_after_the_pointer_moves(self, canvas):
        cursor = canvas.screen.write('+', x=PointerPosition.x, y=PointerPosition.y)
        move_pointer(canvas, 4, 1)
        assert (cursor.x, cursor.y) == (4, 1)
        assert rows(canvas)[1] == '    +'

    def test_it_follows_each_move_of_the_pointer(self, canvas):
        cursor = canvas.screen.write('<+>', x=PointerPosition.x - 1, y=PointerPosition.y)
        move_pointer(canvas, 4, 1)
        move_pointer(canvas, 10, 3)
        assert (cursor.x, cursor.y) == (9, 3)
        assert rows(canvas)[3] == '         <+>'
        assert rows(canvas)[1] == ''

    def test_the_pointer_keeps_its_value_after_a_key(self, canvas):
        cursor = canvas.screen.write('+', x=PointerPosition.x, y=PointerPosition.y)
        move_pointer(canvas, 6, 2)
        canvas.push(Event.key_press('a'))
        canvas.clock.step()
        assert canvas.evaluate(PointerPosition) is not None
        assert (cursor.x, cursor.y) == (6, 2)
        assert rows(canvas)[2] == '      +'

    def test_a_placement_that_reads_the_mouse_position_keeps_its_place_after_a_key(
        self, canvas
    ):
        marker = canvas.screen.write('m', x=MousePosition.x, y=MousePosition.y)
        canvas.clock.step()
        assert is_blank(canvas)
        move_pointer(canvas, 3, 1)
        canvas.push(Event.key_press('a'))
        canvas.clock.step()
        assert canvas.evaluate(MousePosition) is None
        assert (marker.x, marker.y) == (3, 1)
        assert rows(canvas)[1] == '   m'

    def test_a_placement_the_user_hid_stays_hidden_after_the_pointer_moves(self, canvas):
        cursor = canvas.screen.write('+', x=PointerPosition.x, y=PointerPosition.y)
        cursor.is_visible = False
        move_pointer(canvas, 4, 1)
        assert not cursor.is_visible
        assert is_blank(canvas)
        cursor.is_visible = True
        canvas.clock.step()
        assert rows(canvas)[1] == '    +'

    def test_showing_it_before_the_pointer_moves_does_not_draw_it(self, canvas):
        cursor = canvas.screen.write('+', x=PointerPosition.x, y=PointerPosition.y)
        cursor.is_visible = False
        cursor.is_visible = True
        canvas.clock.step()
        assert cursor.is_visible
        assert is_blank(canvas)

    def test_a_mouse_hook_on_it_does_not_hear_clicks_before_it_is_drawn(self, canvas):
        heard = []
        cursor = canvas.screen.write('+', x=PointerPosition.x, y=0)
        cursor.hook(lambda context: heard.append(context.mouse.kind), on='mouse')
        canvas.clock.step()
        canvas.push(Event.mouse_event(column=0, row=0, kind='press', button='left'))
        canvas.deliver_events()
        assert heard == []
        canvas.clock.step()
        canvas.push(Event.mouse_event(column=0, row=0, kind='press', button='left'))
        canvas.deliver_events()
        assert heard == ['press']

    def test_a_canvas_that_runs_by_itself_draws_it_when_the_pointer_moves(self):
        with xnano.new(width=10, height=2, realtime=True) as running:
            cursor = running.screen.write('+', x=PointerPosition.x, y=PointerPosition.y)
            assert running.screen.render().strip() == ''
            running.push(Event.mouse_event(column=3, row=1, kind='move'))
            deadline = time.monotonic() + 5
            while running.screen.render().strip() == '' and time.monotonic() < deadline:
                time.sleep(0.01)
            assert running.screen.render().splitlines()[1] == '   +'
            assert (cursor.x, cursor.y) == (3, 1)

    def test_a_number_given_while_it_waits_draws_it_at_once(self, canvas):
        cursor = canvas.screen.write('+', x=PointerPosition.x, y=PointerPosition.y)
        cursor.x = 2
        cursor.y = 3
        canvas.clock.step()
        assert rows(canvas)[3] == '  +'


class TestAxesBeforeTheInputArrives:
    def test_a_new_placement_reads_zero_for_its_position(self, canvas):
        cursor = canvas.screen.write('<+>', x=PointerPosition.x - 1, y=PointerPosition.y)
        assert (cursor.x, cursor.y) == (0, 0)
        assert (cursor.width, cursor.height) == (3, 1)
        assert (cursor.right_edge, cursor.bottom_edge) == (3, 1)

    def test_an_axis_keeps_the_value_it_had_before_the_expression(self, canvas):
        label = canvas.screen.write('hi', x=5, y=2)
        label.x = PointerPosition.x
        canvas.clock.step()
        assert (cast('int', label.x), label.y) == (5, 2)
        assert is_blank(canvas)
        move_pointer(canvas, 11, 0)
        assert cast('int', label.x) == 11
        assert rows(canvas)[2] == '           hi'

    def test_a_size_that_reads_the_pointer_waits_for_it(self, canvas):
        bar = canvas.screen.write(
            '=', x=0, y=1, width=PointerPosition.x + 1, background='blue'
        )
        canvas.clock.step()
        assert bar.width == 1
        assert is_blank(canvas)
        move_pointer(canvas, 5, 3)
        assert bar.width == 6
        assert rows(canvas)[1].startswith('=')
        assert bar.core_buffer[5, 0].background == xnano.Color('blue')

    def test_a_range_bound_that_reads_the_pointer_limits_nothing_until_it_moves(
        self, canvas
    ):
        thumb = canvas.screen.write('#', x=(0, PointerPosition.x), y=0)
        thumb.x = 15
        canvas.clock.step()
        assert thumb.x == 15
        assert rows(canvas)[0] == ' ' * 15 + '#'
        move_pointer(canvas, 6, 0)
        assert thumb.x == 6

    def test_lock_refuses_an_axis_that_waits_for_input(self, canvas):
        with pytest.raises(ValueError, match=r'lock=True .* x reads input'):
            canvas.screen.write('+', x=PointerPosition.x, y=0, lock=True)
        move_pointer(canvas, 4, 0)
        assert is_blank(canvas)


ANSI_LINE = '\x1b[31merror\x1b[0m: disk full'


class TestStyledTextAssignment:
    def test_styled_text_is_drawn_with_the_styles_of_its_spans(self, canvas):
        log = canvas.screen.write('starting')
        log.text = StyledText.from_ansi(ANSI_LINE)
        assert log.core_buffer[0, 0].style == Style('red')
        assert log.core_buffer[4, 0].foreground == xnano.Color('red')
        assert log.core_buffer[5, 0].style == Style()
        assert '\x1b[0;31merror' in canvas.render(format='ansi')

    def test_reading_styled_text_gives_the_plain_text(self, canvas):
        log = canvas.screen.write('')
        log.text = StyledText.from_ansi(ANSI_LINE)
        assert log.text == 'error: disk full'
        assert rows(canvas)[0] == 'error: disk full'

    def test_styled_text_resizes_the_placement_like_a_string(self, canvas):
        styled = canvas.screen.write('starting', x=0, y=0)
        plain = canvas.screen.write('starting', x=0, y=2)
        styled.text = StyledText.from_ansi('\x1b[32mok\x1b[0m\nlonger line')
        plain.text = 'ok\nlonger line'
        assert (styled.width, styled.height) == (plain.width, plain.height) == (11, 2)
        styled.text = StyledText.from_ansi('\x1b[32ma\x1b[0m')
        assert (styled.width, styled.height) == (1, 1)

    def test_a_given_size_and_alignment_place_styled_text_like_a_string(self, canvas):
        status = canvas.screen.write('x', x='right', y=0, width=10, height=1)
        status.text = StyledText.from_ansi('\x1b[31mabc\x1b[0m')
        assert (status.width, status.height) == (10, 1)
        assert rows(canvas)[0] == ' ' * 17 + 'abc'
        assert status.core_buffer[7, 0].foreground == xnano.Color('red')

    def test_the_look_of_the_placement_goes_over_the_spans(self, canvas):
        log = canvas.screen.write('', dim=True)
        log.text = StyledText.from_ansi(ANSI_LINE)
        canvas.clock.step()
        assert log.core_buffer[0, 0].style == Style('red', dim=True)
        assert log.core_buffer[5, 0].style == Style(dim=True)
        assert log.text == 'error: disk full'

    def test_styled_text_in_a_border_keeps_its_styles(self, canvas):
        card = canvas.screen.write('', border='plain')
        card.text = StyledText.from_ansi('\x1b[34mblue\x1b[0m')
        canvas.clock.step()
        assert card.render().splitlines() == ['┌────┐', '│blue│', '└────┘']
        assert card.core_buffer[1, 1].foreground == xnano.Color('blue')

    def test_a_look_set_after_styled_text_keeps_the_spans(self, canvas):
        log = canvas.screen.write('')
        log.text = StyledText.from_ansi(ANSI_LINE)
        log.is_bold = True
        canvas.clock.step()
        assert log.core_buffer[0, 0].style == Style('red', bold=True)
        assert log.text == 'error: disk full'

    def test_styled_text_wraps_with_its_styles(self):
        with xnano.new(width=10, height=3) as canvas:
            note = canvas.screen.write('x', x=0, y=0, edges='wrap')
            note.text = StyledText.from_ansi('\x1b[31mone two\x1b[0m three four')
            assert rows(canvas)[:2] == ['one two', 'three four']
            assert note.text == 'one two three four'
            assert note.core_buffer[4, 0].foreground == xnano.Color('red')
            assert note.core_buffer[0, 1].style == Style()

    def test_plain_text_after_styled_text_has_no_styles(self, canvas):
        log = canvas.screen.write('')
        log.text = StyledText.from_ansi(ANSI_LINE)
        log.text = 'ok'
        assert log.core_buffer[0, 0].style == Style()
        assert (log.text, log.width) == ('ok', 2)

    @pytest.mark.parametrize('value', [3, None, ['a', 'b'], b'bytes'])
    def test_a_value_that_is_not_text_is_refused(self, canvas, value):
        log = canvas.screen.write('starting')
        with pytest.raises(TypeError, match='text must be a string or a StyledText'):
            log.text = value
        assert log.text == 'starting'
