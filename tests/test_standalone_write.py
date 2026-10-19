"""
tests.test_standalone_write

``xnano.write()`` takes what ``canvas.write()`` takes and measures it where it is created.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from typing_extensions import assert_type
from xnano_image import TerminalImage

import xnano
from xnano.errors import TerminalError
from xnano.region import Region
from xnano.widgets import Gauge
from xnano_core import Buffer, ParentWidth, TimeElapsed


def solid(width: int, height: int) -> xnano.Image:
    pixels = bytes([200, 10, 10, 255]) * (width * height)
    return xnano.Image(TerminalImage.from_rgba(width, height, pixels))


class TestText:
    def test_the_text_call_is_unchanged(self):
        card = xnano.write('hello', border='rounded', padding={'horizontal': 1})
        assert_type(card, Region[int])
        assert card.render().splitlines() == ['╭───────╮', '│ hello │', '╰───────╯']
        card.border = False
        assert card.render().strip() == 'hello'

    def test_lines_are_joined(self):
        assert xnano.write(['ab', 'cde']).render().splitlines() == ['ab', 'cde']

    def test_text_with_a_size_is_drawn_at_that_size(self):
        region = xnano.write('hi', width=6, height=2)
        assert (region.width, region.height) == (6, 2)
        assert region.render().splitlines()[0].startswith('hi')

    def test_placement_keywords_stay_on_the_later_write(self):
        for name in ('x', 'y', 'layer', 'lock', 'edges', 'effects'):
            with pytest.raises(TypeError, match=r'canvas\.write\(region'):
                xnano.write(Gauge(0.5), **{name: 1})  # type: ignore[arg-type]

    def test_unsupported_content_says_what_to_pass(self):
        with pytest.raises(TypeError, match=r'xnano\.write\(\) takes text'):
            xnano.write(5)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='canvas.write'):
            xnano.write({'a': 1})  # type: ignore[arg-type]


class TestContent:
    def test_a_widget_is_drawn_at_its_own_size(self):
        region = xnano.write(Gauge(0.5, label='half', width=12, height=1))
        assert (region.width, region.height) == (12, 1)
        assert 'half' in region.render()

    def test_a_widget_takes_a_size_and_a_look(self):
        region = xnano.write(
            Gauge(0.6, label='60%'), width=20, height=3, border='plain', title='cpu'
        )
        lines = region.render().splitlines()
        assert (region.width, region.height) == (20, 3)
        assert lines[0].startswith('┌cpu') and lines[1].startswith('│')
        assert '60%' in lines[1]

    def test_a_buffer_is_kept_as_cells(self):
        region = xnano.write(Buffer.with_text('abc'), foreground='red', margin=1)
        assert region.render().splitlines() == ['', ' abc']

    def test_art_is_kept_as_cells(self):
        region = xnano.write(xnano.draw(['ab', 'ba'], {'a': 'red', 'b': 'blue'}))
        assert region.height >= 1 and region.width >= 2

    def test_an_image_is_fitted_to_the_size(self):
        region = xnano.write(solid(4, 4), width=8, height=2)
        assert region.width <= 8 and region.height <= 2
        assert region.render(format='ansi').count('\x1b') > 0

    def test_a_component_reads_the_canvas_it_is_made_in(self):
        @xnano.renderable
        def label(context: xnano.Context) -> str:
            return f'{context.canvas.width} wide'

        with xnano.new(width=33, height=3):
            assert xnano.write(label).render().strip() == '33 wide'

    def test_a_region_is_copied(self):
        original = xnano.write('abc', border='plain')
        duplicate = xnano.write(original)
        duplicate.border = False
        assert original.render() != duplicate.render()
        assert original.render().splitlines()[0] == '┌───┐'

    def test_a_region_given_a_size_or_look_is_refused(self):
        original = xnano.write('abc')
        with pytest.raises(TerminalError, match=r'canvas\.write\(region, width='):
            xnano.write(original, width=9)
        with pytest.raises(TerminalError, match='its own'):
            xnano.write(original, border='plain')

    def test_none_makes_an_empty_box(self):
        assert (xnano.write().width, xnano.write().height) == (1, 1)
        box = xnano.write(None, width=5, height=3, border='plain')
        assert box.render().splitlines() == ['┌───┐', '│   │', '└───┘']

    def test_a_canvas_is_refused(self):
        with xnano.new(width=4, height=2) as canvas:
            with pytest.raises(TerminalError, match=r'outer\.write\(canvas\)'):
                xnano.write(canvas)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        'width', ['wide', 'center', 0, 2.5, True, (1, 5), '0%'], ids=repr
    )
    def test_a_bad_size_is_refused_with_its_location(self, width):
        with pytest.raises(TerminalError) as caught:
            xnano.write(Gauge(0.5), width=width)  # type: ignore[arg-type]
        assert caught.value.details[0].location == ('width',)
        assert 'xnano.write()' in str(caught.value)

    def test_a_formula_that_reads_the_clock_is_refused(self):
        with pytest.raises(TerminalError, match=r'canvas\.write\(region, height='):
            xnano.write(Gauge(0.5), height=TimeElapsed * 3)


class TestContext:
    def test_a_relative_size_is_measured_against_the_active_canvas(self):
        with xnano.new(width=40, height=10):
            assert xnano.write(Gauge(0.5), width='50%', height='50%').width == 20
            assert xnano.write(Gauge(0.5), width=ParentWidth - 4).width == 36
            assert xnano.write(Gauge(0.5), height='50%').height == 5
            assert xnano.write(width='25%', height=2).width == 10

    def test_with_no_canvas_the_window_is_measured(self):
        window = xnano.box('100%', 1).width
        assert xnano.write(Gauge(0.5), width='100%').width == window
        assert xnano.write(width='50%', height=1).width == max(1, int(window * 0.5 + 0.5))

    def test_a_state_reference_is_measured_on_the_canvas(self):
        @dataclass
        class Sizes:
            wide: int = 12

        with xnano.new(width=30, height=4, state=Sizes()) as canvas:
            reference = canvas.state_reference(lambda state: state.wide)
            region = xnano.write(Gauge(0.5), width=reference)
            assert region.width == 12

    def test_nothing_is_left_on_the_active_canvas(self):
        with xnano.new(width=20, height=3) as canvas:
            xnano.write(Gauge(0.5), width='50%')
            assert canvas.render().strip() == ''

    def test_a_widget_region_is_written_into_a_canvas(self):
        with xnano.new(width=40, height=4) as canvas:
            region = xnano.write(Gauge(0.6, label='60%'), width='50%')
            placement = canvas.write(region, x=10)
            assert (placement.x, placement.width) == (10, 20)
            assert '60%' in canvas.render().splitlines()[0]

    def test_an_empty_relative_box_is_measured_again_where_it_is_written(self):
        region = xnano.write(None, width='50%', height=1, border='plain')
        with xnano.new(width=40, height=4) as small:
            assert small.write(region).width == 20
        with xnano.new(width=80, height=4) as large:
            placement = large.write(region)
            assert placement.width == 40
            large._runtime.resize(width=60, height=4)
            large.deliver_events()
            large.output.render()
            assert placement.width == 30


class TestActiveCanvasIsUntouched:
    def test_a_column_canvas_keeps_its_placements_and_children(self):
        with xnano.new(width=20, height=6, layout='column') as canvas:
            first = canvas.write('top')
            second = canvas.write('bottom')
            before = (first.y, second.y, first.height, second.height)
            text = canvas.render()
            placements = len(canvas._placements)
            children = len(canvas._children)
            region = xnano.write(Gauge(0.5, label='half'), width='50%')
            assert region.width == 10
            assert (first.y, second.y, first.height, second.height) == before
            assert len(canvas._placements) == placements
            assert len(canvas._children) == children
            assert canvas.render() == text

    def test_a_formula_reads_the_clock_of_the_active_canvas(self):
        @xnano.renderable
        def seconds(context: xnano.Context) -> str:
            return f'{context.time.elapsed:.0f}s'

        with xnano.new(width=20, height=3, fps=10) as canvas:
            canvas.step(delta_seconds=2)
            assert xnano.write(seconds).render().strip() == '2s'

    def test_a_state_reference_reads_the_state_of_the_active_canvas(self):
        @dataclass
        class Sizes:
            wide: int = 5

        with xnano.new(width=30, height=3, state=Sizes(), fps=10) as canvas:
            canvas.state.wide = 9
            canvas.step()
            reference = canvas.state_reference(lambda state: state.wide)
            assert xnano.write(Gauge(0.5), width=reference).width == 9
