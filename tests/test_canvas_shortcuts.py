"""
tests.test_canvas_shortcuts

A canvas has ``write``, ``render``, ``fx`` and ``in`` of its screen, and ``xnano.write`` writes
on the running canvas.
"""

from __future__ import annotations

import inspect

import pytest

import xnano
from xnano.devices import Screen
from xnano.errors import TerminalClosedError
from xnano.layout import Placement
from xnano_core import Point


def screen_write_parameters() -> list[inspect.Parameter]:
    """The parameters of ``Screen.write``, without ``self``."""
    return list(inspect.signature(Screen.write).parameters.values())[1:]


class TestWrite:
    def test_write_returns_a_placement_and_draws_like_screen_write(self):
        with xnano.new(width=12, height=3) as by_canvas:
            placement = by_canvas.write('hello', x=2, y=1)
            drawn_by_canvas = by_canvas.screen.render(format='ansi')
        with xnano.new(width=12, height=3) as by_screen:
            by_screen.screen.write('hello', x=2, y=1)
            drawn_by_screen = by_screen.screen.render(format='ansi')
        assert isinstance(placement, Placement)
        assert (placement.x, placement.y, placement.width, placement.height) == (
            2,
            1,
            5,
            1,
        )
        assert drawn_by_canvas == drawn_by_screen

    def test_the_keyword_options_pass_through(self):
        options = {
            'x': 'center',
            'y': 'bottom',
            'foreground': 'green',
            'bold': True,
            'border': 'rounded',
            'title': 'Status',
        }
        with xnano.new(width=20, height=5) as by_canvas:
            placement = by_canvas.write('Ready', **options)
            drawn_by_canvas = by_canvas.screen.render(format='ansi')
            rows = by_canvas.screen.render().splitlines()
        with xnano.new(width=20, height=5) as by_screen:
            expected = by_screen.screen.write('Ready', **options)
            drawn_by_screen = by_screen.screen.render(format='ansi')
        assert (placement.x, placement.y, placement.width, placement.height) == (
            expected.x,
            expected.y,
            expected.width,
            expected.height,
        )
        assert drawn_by_canvas == drawn_by_screen
        assert rows[-3].strip().startswith('╭Status')
        assert rows[-2].strip() == '│Ready │'

    def test_each_write_with_no_position_goes_on_the_next_line(self):
        with xnano.new(width=12, height=3) as canvas:
            first = canvas.write('first')
            second = canvas.write('second')
            assert (first.y, second.y) == (0, 1)
            assert canvas.render().splitlines()[:2] == ['first', 'second']

    def test_write_takes_the_parameters_of_screen_write(self):
        parameters = list(inspect.signature(xnano.Canvas.write).parameters.values())
        assert parameters[1:] == screen_write_parameters()

    def test_an_unknown_keyword_is_refused_with_the_known_ones(self):
        with xnano.new(width=8, height=1) as canvas:
            with pytest.raises(
                TypeError, match=r"Canvas\.write\(\) has no setting called 'colour'"
            ):
                canvas.write('hello', colour='red')  # pyright: ignore[reportCallIssue]


class TestRender:
    @pytest.mark.parametrize('format', ['text', 'ansi'])
    def test_render_is_the_render_of_the_screen(self, format):
        with xnano.new(width=12, height=2) as canvas:
            canvas.write('hello', foreground='red', y=1)
            canvas.clock.step()
            assert canvas.render(format=format) == canvas.screen.render(format=format)

    def test_render_gives_the_text_by_default(self):
        with xnano.new(width=6, height=2) as canvas:
            canvas.write('hello', y=1)
            assert canvas.render().splitlines() == ['', 'hello']

    def test_an_unknown_format_is_refused(self):
        with xnano.new(width=6, height=1) as canvas:
            with pytest.raises(ValueError, match="format must be 'text' or 'ansi'"):
                canvas.render(format='html')  # pyright: ignore[reportArgumentType]


class TestEffects:
    def test_fx_is_the_effects_of_the_screen(self):
        with xnano.new('hello', width=8, height=1) as canvas:
            assert canvas.fx is canvas.screen.fx

    def test_an_effect_on_fx_changes_all_of_the_canvas(self):
        with xnano.new('hello', width=8, height=1, fps=10) as canvas:
            canvas.clock.step()
            before = canvas.render(format='ansi')
            fade = canvas.fx.fade_from(foreground='black', duration_milliseconds=300)
            assert canvas.fx.active == (fade,)
            assert canvas._effects[0][1] is canvas
            canvas.clock.step()
            assert canvas.render(format='ansi') != before
            canvas.clock.step(delta_seconds=1.0)
            assert canvas.render(format='ansi') == before


class TestContains:
    @pytest.mark.parametrize('point', [(0, 0), (11, 3), Point(4, 2)])
    def test_a_cell_of_the_screen_is_in_the_canvas(self, point):
        with xnano.new(width=12, height=4) as canvas:
            assert point in canvas
            assert point in canvas.screen.region

    @pytest.mark.parametrize('point', [(12, 0), (0, 4), (-1, 0), Point(20, 1)])
    def test_a_point_outside_the_screen_is_not_in_the_canvas(self, point):
        with xnano.new(width=12, height=4) as canvas:
            assert point not in canvas
            assert point not in canvas.screen.region


class TestModuleWrite:
    def test_it_writes_on_the_running_canvas(self):
        with xnano.new(width=12, height=2) as canvas:
            placement = xnano.write('hello', x=2, foreground='green')
            assert isinstance(placement, Placement)
            assert canvas.render().splitlines()[0] == '  hello'

    def test_it_draws_like_screen_write(self):
        with xnano.new(width=20, height=4) as by_module:
            xnano.write('Ready', x='center', y='bottom', border='rounded', bold=True)
            drawn_by_module = by_module.render(format='ansi')
        with xnano.new(width=20, height=4) as by_screen:
            by_screen.screen.write(
                'Ready', x='center', y='bottom', border='rounded', bold=True
            )
            drawn_by_screen = by_screen.render(format='ansi')
        assert drawn_by_module == drawn_by_screen

    def test_with_no_canvas_running_it_says_how_to_start_one(self):
        assert xnano.active(is_required=False) is None
        with pytest.raises(TerminalClosedError) as caught:
            xnano.write('hello')
        message = str(caught.value)
        assert 'xnano.write() did not write, because no canvas is running.' in message
        assert 'with xnano.open() as terminal:' in message
        assert 'with xnano.new() as canvas:' in message

    def test_after_the_canvas_closes_it_raises(self):
        with xnano.new(width=8, height=1):
            pass
        with pytest.raises(TerminalClosedError, match='no canvas is running'):
            xnano.write('hello')

    def test_it_takes_the_parameters_of_screen_write(self):
        parameters = list(inspect.signature(xnano.write).parameters.values())
        assert parameters == screen_write_parameters()

    def test_it_is_exported_next_to_play(self):
        assert 'write' in xnano.__all__
        assert xnano.write is xnano.canvas.write


class TestTerminal:
    @pytest.mark.parametrize('name', ['write', 'render', 'fx', '__contains__'])
    def test_a_terminal_has_the_members_of_the_canvas(self, name):
        assert inspect.getattr_static(xnano.Terminal, name) is inspect.getattr_static(
            xnano.Canvas, name
        )
