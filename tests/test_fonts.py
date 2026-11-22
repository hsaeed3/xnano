"""
tests.test_fonts

Text written in a font: placed, themed and changed like any other text, and frames as images.
"""

from __future__ import annotations

import pytest

import xnano
from xnano import symbols
from xnano.styles import Font

BOXES_FONT = 'flf2a$ 2 1 2 0 0\n' + ''.join(
    ' $@\n $@@\n' if code == 32 else '[]@\n<>@@\n' for code in range(32, 127)
)
"""A FIGlet font two rows tall: every character is ``[]`` over ``<>``."""


@pytest.fixture
def boxes() -> Font:
    return Font.from_bytes(BOXES_FONT.encode(), name='boxes')


class TestWritingInAFont:
    def test_text_in_a_font_takes_the_cells_of_the_font(self, boxes: Font):
        with xnano.new(width=10, height=3) as canvas:
            title = canvas.screen.write('ab', font=boxes)
            canvas.screen.write('next')
            assert (title.width, title.height) == (4, 2)
            assert canvas.render().splitlines() == ['[][]', '<><>', 'next']

    def test_pixel_font_text_is_drawn_with_half_blocks(self):
        with xnano.new(width=10, height=4) as canvas:
            title = canvas.screen.write('I', font='small', foreground='cyan')
            assert (title.width, title.height) == (5, 4)
            assert set(canvas.render()) <= set(' ▀▄█\n')
            assert title.core_buffer[2, 0].foreground == xnano.Color('cyan')

    def test_text_keeps_the_text_it_was_given(self, boxes: Font):
        with xnano.new(width=10, height=2) as canvas:
            title = canvas.screen.write('ab', font=boxes)
            assert title.text == 'ab'
            title.text = 'abc'
            assert title.text == 'abc'
            assert (title.width, title.height) == (6, 2)
            assert canvas.render().splitlines() == ['[][][]', '<><><>']

    def test_new_text_must_be_a_string(self, boxes: Font):
        with xnano.new(width=10, height=2) as canvas:
            title = canvas.screen.write('ab', font=boxes)
            with pytest.raises(TypeError, match="font 'boxes'"):
                title.text = xnano.styles.StyledText([xnano.styles.TextSpan('x')])

    def test_lines_of_text_are_written_in_the_font(self, boxes: Font):
        with xnano.new(width=10, height=4) as canvas:
            canvas.screen.write(['a', 'b'], font=boxes)
            assert canvas.render().splitlines() == ['[]', '<>', '[]', '<>']

    def test_text_in_a_font_is_aligned_like_text(self, boxes: Font):
        with xnano.new(width=8, height=2) as canvas:
            canvas.screen.write('a', font=boxes, x='center')
            assert canvas.render().splitlines()[0] == '   []'

    def test_text_in_a_font_works_in_a_placement_and_with_a_theme(self, boxes: Font):
        with xnano.new(width=10, height=4, theme='xnano-night') as canvas:
            panel = canvas.screen.write(None, width=10, height=4)
            panel.write('a', font=boxes)
            assert canvas.render().splitlines()[:2] == ['[]', '<>']

    def test_xnano_write_takes_a_font(self, boxes: Font):
        with xnano.new(width=10, height=2) as canvas:
            xnano.write('a', font=boxes)
            assert canvas.render().splitlines() == ['[]', '<>']

    def test_only_text_can_have_a_font(self):
        with xnano.new(width=10, height=2) as canvas:
            with pytest.raises(TypeError, match='font= writes text'):
                canvas.screen.write(xnano.pixel_art(['RR'], 'R=red'), font='small')


class TestFontNames:
    def test_a_registered_font_is_found_by_name(self, boxes: Font):
        symbols.register('boxes', boxes)
        try:
            with xnano.new(width=10, height=2) as canvas:
                canvas.screen.write('a', font='boxes')
                assert canvas.render().splitlines() == ['[]', '<>']
        finally:
            symbols.remove('boxes')

    def test_an_unknown_name_lists_the_fonts(self):
        with xnano.new(width=10, height=2) as canvas:
            with pytest.raises(ValueError, match="'small', 'large'") as caught:
                canvas.screen.write('a', font='huge')
            assert 'xnano.symbols.register' in str(caught.value)

    def test_a_symbol_of_another_kind_is_not_a_font(self):
        symbols.register('accent', xnano.Color('red'))
        try:
            with xnano.new(width=10, height=2) as canvas:
                with pytest.raises(ValueError, match='not a Font'):
                    canvas.screen.write('a', font='accent')
        finally:
            symbols.remove('accent')

    def test_a_font_that_is_not_a_font_or_name_is_refused(self):
        with xnano.new(width=10, height=2) as canvas:
            with pytest.raises(TypeError, match='font must be a Font'):
                canvas.screen.write('a', font=3)  # type: ignore[arg-type]


class TestImages:
    def test_canvas_renders_as_png(self):
        with xnano.new(width=4, height=2) as canvas:
            canvas.screen.write('hi')
            image = canvas.render(format='png')
            assert image.startswith(b'\x89PNG')
            assert image == canvas.screen.render(format='png')

    def test_png_cells_can_use_a_registered_font(self):
        symbols.register('tiny', Font('small'))
        try:
            with xnano.new(width=4, height=2) as canvas:
                assert canvas.render(format='png', font='tiny') == canvas.render(
                    format='png', font='small'
                )
        finally:
            symbols.remove('tiny')

    def test_png_needs_a_pixel_font(self, boxes: Font):
        with xnano.new(width=4, height=2) as canvas:
            with pytest.raises(ValueError, match='character font'):
                canvas.render(format='png', font=boxes)

    def test_font_works_only_with_png(self):
        with xnano.new(width=4, height=2) as canvas:
            with pytest.raises(ValueError, match="only with format='png'"):
                canvas.render(format='text', font='small')  # type: ignore[call-overload]
            with pytest.raises(ValueError, match="'png'"):
                canvas.render(format='jpeg')  # type: ignore[call-overload]

    def test_a_canvas_written_into_another_renders_as_png(self):
        with xnano.new(width=8, height=4) as outer, xnano.new(width=4, height=2) as inner:
            inner.screen.write('hi')
            outer.screen.write(inner)
            assert inner.render(format='png', font='small').startswith(b'\x89PNG')
