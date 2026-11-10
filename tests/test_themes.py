"""
tests.test_themes

Themes on a canvas: ``theme=`` of ``new()`` and ``write()`` colors the canvas, text, borders
and widgets, and leaves alone what has colors of its own.
"""

from __future__ import annotations

import pytest

import xnano
from xnano.styles import Style, StyledText, TextSpan
from xnano.themes import theme_of
from xnano.widgets import ItemList, Scrollbar
from xnano_core import Buffer

DRACULA = theme_of('dracula')


def _colors(canvas, column, row):
    cell = Buffer.from_cell_grid(canvas.screen.output.render().to_cell_grid())[
        column, row
    ]
    return cell.foreground, cell.background


def test_a_canvas_without_a_theme_keeps_the_colors_of_the_terminal():
    with xnano.new(width=8, height=1) as canvas:
        canvas.write('hello')
        assert canvas.theme is None
        assert canvas.render(format='ansi') == '\x1b[0mhello   \x1b[0m'


def test_a_theme_colors_the_canvas_and_its_text():
    with xnano.new(width=8, height=2, theme='dracula') as canvas:
        canvas.write('hello')
        assert canvas.theme == 'dracula'
        text, background = xnano.Color(DRACULA.text), xnano.Color(DRACULA.background)
        assert _colors(canvas, 0, 0) == (text, background)
        assert _colors(canvas, 7, 1) == (text, background)


def test_secondary_text_gets_the_muted_color():
    with xnano.new(width=8, height=1, theme='dracula') as canvas:
        canvas.write('hint', dim=True)
        assert _colors(canvas, 0, 0)[0] == xnano.Color(DRACULA.muted)


def test_colors_that_are_given_stay():
    with xnano.new(width=12, height=1, theme='dracula') as canvas:
        canvas.write('red', foreground='red')
        canvas.write(StyledText([TextSpan('ok', style=Style('green'))]), x=4, y=0)
        assert _colors(canvas, 0, 0) == (
            xnano.Color('red'),
            xnano.Color(DRACULA.background),
        )
        assert _colors(canvas, 4, 0)[0] == xnano.Color('green')


def test_text_that_changes_keeps_the_theme():
    with xnano.new(width=12, height=1, theme='dracula') as canvas:
        line = canvas.write('first')
        line.text = 'second'
        assert line.text == 'second'
        assert _colors(canvas, 0, 0)[0] == xnano.Color(DRACULA.text)
        line.text = StyledText([TextSpan('a'), TextSpan('b', style=Style('red'))])
        assert _colors(canvas, 0, 0)[0] == xnano.Color(DRACULA.text)
        assert _colors(canvas, 1, 0)[0] == xnano.Color('red')


def test_a_border_and_a_widget_get_the_colors_of_the_theme():
    with xnano.new(width=20, height=3, theme='dracula') as canvas:
        canvas.write('box', border='rounded')
        assert _colors(canvas, 0, 0)[0] == xnano.Color(DRACULA.border)
        choices = ItemList(['one', 'two'], selected=0)
        bar = Scrollbar(10, 0, thumb_style=Style('red'))
        canvas.write(choices, x=8, y=0, width=6, height=2)
        canvas.write(bar, x='right', y=0, width=1, height=3)
        assert choices.highlight_style.foreground == xnano.Color(DRACULA.accent)
        assert bar.thumb_style == Style('red')
        assert bar.track_style.foreground == xnano.Color(DRACULA.border)
        assert _colors(canvas, 8, 0)[0] == xnano.Color(DRACULA.accent)
        assert _colors(canvas, 8, 1)[0] == xnano.Color(DRACULA.text)


def test_write_takes_a_theme_of_its_own():
    with xnano.new(width=12, height=2, theme='dracula') as canvas:
        canvas.write('other', y=1, theme='github-light')
        assert _colors(canvas, 0, 1) == (xnano.Color('#1f2328'), xnano.Color('#ffffff'))
    with xnano.new(width=12, height=1) as canvas:
        canvas.write('one', theme='github-light')
        assert _colors(canvas, 0, 0)[1] == xnano.Color('#ffffff')
        assert _colors(canvas, 8, 0)[1] != xnano.Color('#ffffff')


def test_a_canvas_inside_another_takes_its_theme():
    with xnano.new(width=12, height=2, theme='xnano-night') as outer:
        with xnano.new(width=6, height=1) as inner:
            inner.write('in')
            assert inner.theme == 'xnano-night'
        with xnano.new(width=6, height=1, theme='xnano-day') as other:
            assert other.theme == 'xnano-day'
        assert outer.theme == 'xnano-night'


def test_the_text_of_the_screen_is_the_same_with_a_theme():
    def draw(**settings):
        with xnano.new(width=20, height=3, **settings) as canvas:
            canvas.write('title', bold=True)
            canvas.write(ItemList(['one', 'two']), y=1, width=8, height=2)
            return canvas.render()

    assert draw(theme='monokai') == draw()


def test_an_unknown_theme_names_the_themes():
    with pytest.raises(ValueError, match="no theme named 'sepia'.*'dracula'"):
        xnano.new(theme='sepia')  # pyright: ignore[reportArgumentType]
    with xnano.new(width=4, height=1) as canvas, pytest.raises(ValueError, match='sepia'):
        canvas.write('x', theme='sepia')  # pyright: ignore[reportArgumentType]


def test_secondary_text_that_changes_stays_secondary():
    with xnano.new(width=12, height=1, theme='dracula') as canvas:
        hint = canvas.write('hint', dim=True)
        hint.text = 'other'
        assert _colors(canvas, 0, 0)[0] == xnano.Color(DRACULA.muted)


def test_a_style_with_colors_stays_under_a_theme():
    with xnano.new(width=8, height=1, theme='dracula') as canvas:
        text = StyledText([TextSpan('ok')])
        canvas.write(text, width=6, style=Style(background='blue'))
        assert _colors(canvas, 4, 0)[1] == xnano.Color('blue')
    with xnano.new(
        width=4, height=1, theme='dracula', style=Style('red', 'blue')
    ) as canvas:
        assert _colors(canvas, 3, 0) == (xnano.Color('red'), xnano.Color('blue'))


def test_content_written_in_a_box_keeps_the_theme():
    with xnano.new(width=12, height=3, theme='dracula') as canvas:
        box = canvas.write('', width=10, height=3, border='rounded')
        box.write('in')
        assert _colors(canvas, 1, 1)[0] == xnano.Color(DRACULA.text)
