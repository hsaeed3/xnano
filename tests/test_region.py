"""
tests.test_region

Region: standalone and live, indexing to Pixel, slices, containment, resize, resolutions,
batched shading and images.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import pytest

import xnano
from xnano import Color, Pixel, new
from xnano.errors import TerminalError
from xnano.layout import Region
from xnano.layout._region import _timeline_region
from xnano_core import Event, ParentWidth, Point, Size, TimeElapsed


@pytest.fixture
def canvas():
    with new(width=12, height=5, fps=10) as opened:
        yield opened


class TestStandalone:
    def test_write_makes_a_region_the_size_of_its_text(self):
        region = xnano.write('hello\nworld!')
        assert isinstance(region, Region)
        assert (region.width, region.height) == (6, 2)
        assert region.render().split('\n') == ['hello', 'world!']

    def test_write_takes_the_look_of_text(self):
        card = xnano.write('hi', border='rounded', padding={'horizontal': 1})
        assert (card.width, card.height) == (6, 3)
        assert card.render().split('\n') == ['╭────╮', '│ hi │', '╰────╯']
        card.border.title = 'T'
        assert card.render().split('\n')[0] == '╭T───╮'
        card.border = False
        assert card.render().strip() == 'hi'

    def test_a_per_side_border_on_a_standalone_region(self):
        card = xnano.write('hi', border='plain')
        card.border.top = 'double'
        card.border.left = False
        assert card.render().split('\n') == ['══╗', 'hi│', '──┘']

    def test_a_box_has_no_border_unless_one_is_asked_for(self):
        plain = xnano.box(5, 3)
        assert plain.render().strip() == ''
        assert plain.border.kind is None
        assert xnano.box(4, 2, border=False).render().strip() == ''

    def test_a_border_is_drawn_when_asked_for(self):
        for border in ('plain', True):
            frame = xnano.box(5, 3, border=border)
            assert frame.render().split('\n') == ['┌───┐', '│   │', '└───┘']
        rounded = xnano.box(4, 3, border='rounded', title='x')
        assert rounded.render().split('\n')[0] == '╭x─╮'

    def test_a_box_keeps_its_size_and_content_when_the_look_changes(self):
        frame = xnano.box(6, 4, border='plain')
        frame[1:3, 1:2] = 'ab'
        frame.border = 'double'
        assert (frame.width, frame.height) == (6, 4)
        assert frame.render().split('\n')[1] == '║ab  ║'

    def test_a_box_needs_a_size(self):
        with pytest.raises(TerminalError) as caught:
            xnano.box(0, 3)
        assert caught.value.details[0].location == ('width',)
        assert caught.value.details[0].input_value == 0

    def test_an_unknown_look_is_named(self):
        with pytest.raises(TypeError, match='no setting called'):
            xnano.write('x', bordr='plain')  # type: ignore[call-arg]

    def test_a_standalone_region_has_its_screen_origin_at_zero(self):
        region = xnano.write('abc')
        assert (region.x, region.y) == (0, 0)
        assert (0, 0) in region and (2, 0) in region
        assert (3, 0) not in region and (0, 1) not in region

    def test_resize_keeps_cells_that_fit(self):
        region = xnano.box(3, 3, border=False)
        region[0, 0] = 'a'
        region.resize(5, 2)
        assert (region.width, region.height) == (5, 2)
        assert region[0, 0].character == 'a'
        with pytest.raises(ValueError, match='at least 1 by 1'):
            region.resize(0, 1)

    def test_a_text_region_is_sized_by_its_text(self):
        region = xnano.write('hi', border='rounded')
        with pytest.raises(TerminalError, match='sized by its text'):
            region.resize(10, 5)
        region.border.color = 'red'
        assert (region.width, region.height) == (4, 3)

    def test_a_region_written_into_a_canvas_is_a_snapshot(self, canvas):
        region = xnano.write('abc')
        placement = canvas.screen.write(region)
        region[0, 0] = 'Z'
        canvas.clock.step()
        assert canvas.screen.render().split('\n')[0] == 'abc'
        assert placement.width == 3
        second = canvas.screen.write(region, y=2)
        canvas.clock.step()
        assert canvas.screen.render().split('\n')[2] == 'Zbc'
        second.remove()

    def test_changing_a_written_region_leaves_the_placement_look_alone(self, canvas):
        region = xnano.write('abc')
        placement = canvas.screen.write(region)
        region.border = 'double'
        placement.border = 'plain'
        region.border = False
        canvas.clock.step()
        assert canvas.screen.render().split('\n')[0] == '┌───┐'
        assert (placement.width, placement.height) == (5, 3)

    def test_a_box_keeps_its_cells_when_its_border_changes(self):
        box = xnano.box(5, 3, border='plain')
        box[1, 1] = xnano.Pixel('star')
        box.border = 'double'
        assert box[1, 1].character == '★'
        assert box[0, 0].character == '╔'

    def test_copy_is_independent(self):
        region = xnano.write('abc', border='plain')
        copy = region.copy()
        region[1, 1] = 'Z'
        assert copy[1, 1].character == 'a'
        copy.border = False
        assert region.border.kind == 'plain'

    def test_a_region_can_be_printed(self):
        text = xnano.write('hi', foreground='red').render(format='ansi')
        assert '\x1b[' in text and 'hi' in text

    def test_a_region_prints_as_its_text(self, capsys):
        card = xnano.write('hi', border='rounded')
        assert str(card) == card.render()
        print(card)  # noqa: T201
        assert capsys.readouterr().out.splitlines() == ['╭──╮', '│hi│', '╰──╯']
        with new(width=5, height=1) as canvas:
            canvas.screen.write('hello')
            canvas.clock.step()
            assert str(canvas.screen.region) == canvas.screen.region.render()

    def test_region_is_not_a_top_level_name(self):
        assert not hasattr(xnano, 'Region')
        assert 'Region' not in xnano.__all__


class TestLiveViews:
    def test_a_canvas_region_reads_and_writes_cells(self, canvas):
        region = canvas.screen.region
        assert (region.width, region.height) == (12, 5)
        region[0, 0] = Pixel('star', foreground='red')
        assert region[0, 0].character == '★'
        assert region[0, 0].foreground == Color('red')
        assert canvas.screen.render().split('\n')[0] == '★'

    def test_a_placement_region_is_inside_its_decoration(self, canvas):
        label = canvas.screen.write('abc', border='rounded', padding=1, margin=1)
        region = label.region
        assert (region.width, region.height) == (3, 1)
        region[0, 0] = Pixel('star')
        canvas.clock.step()
        assert '★bc' in canvas.screen.render()
        assert (label.width, label.height) == (9, 7)

    def test_a_region_of_a_decorated_widget_is_inside_the_border(self, canvas):
        from xnano_core import Buffer

        block = canvas.screen.write(Buffer(width=4, height=2), border='plain')
        assert (block.region.width, block.region.height) == (4, 2)

    def test_resize_on_a_placement_resizes_the_placement(self, canvas):
        label = canvas.screen.write('abcd', border='plain')
        label.region.resize(6, 2)
        assert (label.width, label.height) == (8, 4)

    def test_resize_gives_the_region_the_requested_size_inside_a_decoration(self, canvas):
        block = canvas.screen.write(
            xnano.box(4, 2, border=False), x=2, y=1, border='plain', padding=1
        )
        block.region.resize(6, 3)
        canvas.clock.step()
        assert (block.region.width, block.region.height) == (6, 3)
        shrunk = canvas.screen.write(
            xnano.box(4, 2, border=False), x=2, y=1, border='plain', padding=1
        )
        shrunk.region.resize(1, 1)
        canvas.clock.step()
        assert (shrunk.region.width, shrunk.region.height) == (1, 1)

    def test_resizing_a_decorated_box_draws_its_border_at_the_new_size(self):
        frame = xnano.box(5, 3, border='plain', padding=1)
        frame.resize(8, 5)
        assert frame.render().splitlines() == [
            '┌──────┐',
            '│      │',
            '│      │',
            '│      │',
            '└──────┘',
        ]
        frame.border = 'double'
        assert frame.render().splitlines() == [
            '╔══════╗',
            '║      ║',
            '║      ║',
            '║      ║',
            '╚══════╝',
        ]

    def test_shrinking_a_decorated_box_keeps_its_border_whole(self):
        plain = xnano.box(6, 4, border='plain')
        plain[1, 1] = 'X'
        plain[4, 2] = 'Y'
        plain.resize(4, 3)
        assert plain.render().splitlines() == ['┌──┐', '│X │', '└──┘']
        padded = xnano.box(8, 6, border='plain', padding=1)
        padded.resize(4, 4)
        assert padded.render().splitlines() == ['┌──┐', '│  │', '│  │', '└──┘']
        tiny = xnano.box(6, 4, border='plain')
        tiny.resize(3, 3)
        assert tiny.render().splitlines() == ['┌─┐', '│ │', '└─┘']

    def test_resize_on_a_canvas_view_is_refused(self, canvas):
        with pytest.raises(TerminalError, match='follows its screen'):
            canvas.screen.region.resize(3, 3)

    def test_a_view_has_no_appearance_of_its_own(self, canvas):
        for name in ('color', 'border', 'padding', 'margin'):
            with pytest.raises(TerminalError, match=f'canvas.{name}'):
                getattr(canvas.screen.region, name)
        with pytest.raises(TerminalError, match='instead of region.border'):
            canvas.screen.region.border = 'plain'

    def test_containment_uses_screen_cells_and_local_converts(self, canvas):
        label = canvas.screen.write('abcd', x=3, y=2)
        canvas.clock.step()
        region = label.region
        assert (region.x, region.y) == (3, 2)
        assert (3, 2) in region and Point(6, 2) in region
        assert (2, 2) not in region and (7, 2) not in region and (3, 3) not in region
        assert region.local(Point(5, 2)) == Point(2, 0)
        assert region[region.local(Point(5, 2)).x, 0].character == 'c'

    def test_containment_in_a_mouse_hook(self, canvas):
        label = canvas.screen.write('abcd', x=3, y=2)
        hits: list[str] = []

        @canvas.hook(on="mouse.kind == 'press'")
        def press(context):
            hits.append('in' if context.mouse.position in label.region else 'out')

        for column in (3, 8):
            canvas.push(
                Event.mouse_event(column=column, row=2, kind='press', button='left')
            )
            canvas.deliver_events()
        assert hits == ['in', 'out']

    def test_a_placement_local_and_a_canvas_local(self, canvas):
        label = canvas.screen.write('abcd', x=3, y=2)
        assert label.local(Point(5, 3)) == Point(2, 1)
        assert canvas.screen.local(Point(5, 3)) == Point(5, 3)

    def test_a_view_is_rendered_as_text(self, canvas):
        canvas.screen.region[0:3, 0:1] = 'abc'
        assert canvas.screen.region[0:3, 0:1].render() == 'abc'


class TestIndexing:
    def test_out_of_range_names_the_valid_ranges(self, canvas):
        with pytest.raises(IndexError, match=r'x runs from 0 to 11 and y from 0 to 4'):
            canvas.screen.region[12, 0]
        with pytest.raises(IndexError, match='region.local'):
            canvas.screen.region[0, 5] = 'x'

    def test_a_screen_point_is_refused(self, canvas):
        with pytest.raises(TypeError, match='takes region cells'):
            canvas.screen.region[Point(1, 1)]
        with pytest.raises(TypeError, match='takes region cells'):
            canvas.screen.region[Point(1, 1)] = 'x'

    def test_keys_must_be_pairs_of_whole_numbers_or_slices(self, canvas):
        with pytest.raises(TypeError, match='indexed by'):
            canvas.screen.region[1]  # type: ignore[index]
        with pytest.raises(TypeError, match='whole number or a slice'):
            canvas.screen.region[1.5, 0]  # type: ignore[index]

    def test_a_slice_is_a_view(self, canvas):
        canvas.screen.region[2:5, 1:3] = 'abc'
        part = canvas.screen.region[2:5, 1:3]
        assert isinstance(part, Region)
        assert (part.width, part.height) == (3, 2)
        assert part[0, 0].character == 'a'
        part[1, 1] = Pixel('x')
        assert canvas.screen.region[3, 2].character == 'x'
        assert canvas.screen.region[:, :].width == 12
        assert canvas.screen.region[-3:, -1:].width == 3

    def test_a_slice_with_a_step_is_explained(self, canvas):
        with pytest.raises(ValueError, match='cannot have a step'):
            canvas.screen.region[0:6:2, 0:2] = 'x'

    def test_assigning_a_string_is_text_never_a_color(self, canvas):
        canvas.screen.region[0:5, 0:2] = 'hello'
        assert canvas.screen.render().split('\n')[0] == 'hello'
        assert canvas.screen.region[0, 0].background is None
        canvas.screen.region[0, 1] = 'red'
        assert canvas.screen.region[0, 1].character == 'r'

    def test_a_color_sets_the_background_of_a_cell_or_a_slice(self, canvas):
        canvas.screen.region[1, 1] = (10, 20, 30)
        assert canvas.screen.region[1, 1].background.to_rgb() == (10, 20, 30)
        canvas.screen.region[2:4, 1:3] = Color('#ff0000')
        for column in (2, 3):
            assert canvas.screen.region[column, 2].background.to_rgb() == (255, 0, 0)
        assert canvas.screen.region[4, 2].background is None

    def test_a_pixel_fills_a_slice(self, canvas):
        canvas.screen.region[0:3, 0:2] = Pixel('shade_light', foreground='green')
        assert canvas.screen.render().split('\n')[:2] == ['░░░', '░░░']

    def test_content_covers_a_slice_and_a_cell_refuses_it(self, canvas):
        canvas.screen.region[2:6, 1:3] = xnano.write('xy')
        canvas.clock.step()
        assert canvas.screen.render().split('\n')[1].startswith('  xy')
        with pytest.raises(TypeError, match='two slices'):
            canvas.screen.region[0, 0] = xnano.write('x')

    def test_the_original_cells_are_read_as_pixels(self, canvas):
        found = canvas.screen.region[0, 0]
        assert isinstance(found, Pixel)
        assert found.character == ' '
        assert found.foreground is None and found.background is None


class TestResolutions:
    def test_half_blocks_have_two_pixels_per_cell(self, canvas):
        pixels = canvas.screen.region.half_blocks
        assert (pixels.width, pixels.height) == (12, 10)
        assert pixels.resolution == 'half_blocks'
        pixels[0, 0] = (255, 0, 0)
        pixels[0, 1] = (0, 0, 255)
        assert canvas.screen.region[0, 0].character == '▀'
        assert pixels[0, 0].foreground.to_rgb() == (255, 0, 0)
        assert pixels[0, 1].foreground.to_rgb() == (0, 0, 255)

    def test_braille_has_eight_dots_per_cell(self, canvas):
        dots = canvas.screen.region.braille
        assert (dots.width, dots.height) == (24, 20)
        dots[3, 5] = (255, 255, 255)
        assert dots[3, 5].character == '•'
        assert dots[2, 5].character == ' '
        assert canvas.screen.region[1, 1].character == '⠐'

    def test_text_is_not_written_at_a_pixel_resolution(self, canvas):
        with pytest.raises(TypeError, match='cell resolution|cell region'):
            canvas.screen.region.braille[0, 0] = 'x'
        with pytest.raises(TypeError, match='color or a Pixel'):
            canvas.screen.region.half_blocks[0:2, 0:1] = 'red'

    def test_a_slice_of_a_pixel_view_is_refused(self, canvas):
        with pytest.raises(ValueError, match='cut cells in two'):
            canvas.screen.region.half_blocks[0:2, 0:2]

    def test_cell_and_pixel_conversion(self, canvas):
        pixels = canvas.screen.region.half_blocks
        assert pixels.cell_for_pixel(3, 5) == (3, 2)
        assert pixels.pixel_for_cell(1, 1, anchor='top_left') == (1, 2)
        assert canvas.screen.region.cell_for_pixel(3, 5) == (3, 5)
        assert canvas.screen.region.pixel_for_cell(3, 5) == (3, 5)


class TestShade:
    def test_cells_are_shaded_in_one_batched_write(self, canvas):
        canvas.screen.region.shade(lambda x, y: (x * 20, y * 40, 0) if x < 10 else None)
        assert canvas.screen.region[3, 2].background.to_rgb() == (60, 80, 0)
        assert canvas.screen.region[11, 2].background is None

    def test_pixels_and_dots_are_shaded_at_their_resolution(self, canvas):
        calls: list[tuple[int, int]] = []

        def paint(x: int, y: int):
            calls.append((x, y))
            return (x, y, 0)

        canvas.screen.region.half_blocks.shade(paint)
        assert len(calls) == 12 * 10
        calls.clear()
        canvas.screen.region.braille.shade(paint)
        assert len(calls) == 24 * 20

    def test_shading_a_slice_uses_slice_coordinates(self, canvas):
        part = canvas.screen.region[2:5, 1:3]
        part.shade(lambda x, y: (x, y, 9))
        assert canvas.screen.region[2, 1].background.to_rgb() == (0, 0, 9)
        assert canvas.screen.region[4, 2].background.to_rgb() == (2, 1, 9)
        assert canvas.screen.region[5, 2].background is None

    def test_shading_a_placement_matches_a_per_cell_loop(self, canvas):
        label = canvas.screen.write('abcdef', y=1)
        label.region.shade(lambda x, y: (x * 30, 0, 0))
        for column in range(6):
            assert label.region[column, 0].background.to_rgb() == (column * 30, 0, 0)
            assert label.region[column, 0].character == 'abcdef'[column]


class TestImages:
    def test_color_bytes_are_drawn_at_a_pixel_position(self, canvas):
        canvas.screen.region.draw_color_bytes(
            bytes([255, 0, 0, 255]) * 4, width=2, height=2, x=4, y=0
        )
        assert canvas.screen.region[4, 0].background.to_rgb() == (255, 0, 0)

    def test_an_image_is_drawn_and_may_be_scrolled(self, canvas):
        class Picture:
            width = 2
            height = 2

            def to_rgba(self, frame_index: int) -> bytes:
                return bytes([0, 255, 0, 255]) * 4

        canvas.screen.region.draw_image(Picture(), x=1, y=0)
        assert canvas.screen.region[1, 0].background.to_rgb() == (0, 255, 0)
        canvas.screen.region.draw_image(Picture(), x=-1, y=0, mode='replace')
        assert canvas.screen.region[0, 0].background.to_rgb() == (0, 255, 0)


class TestCursorFollowsARegion:
    def test_the_cursor_follows_a_region_cell(self, canvas):
        label = canvas.screen.write('name', x=3, y=1, border='plain')
        canvas.screen.cursor.follow(label.region, x=2)
        canvas.clock.step()
        assert canvas.screen.cursor.position == Point(3 + 1 + 2, 1 + 1)


class TestCoordinates:
    def test_an_integer_beside_a_slice_must_be_inside_the_region(self, canvas):
        region = canvas.screen.region
        for key in ((99, slice(0, 2)), (-1, slice(0, 2)), (slice(0, 2), 7)):
            with pytest.raises(IndexError, match='outside this region'):
                region[key]
            with pytest.raises(IndexError, match='outside this region'):
                region[key] = Pixel('block')
        assert region[3, 0:2].height == 2

    def test_wrong_arguments_say_what_to_pass(self):
        for width in ('a', 2.5):
            with pytest.raises(TerminalError, match='whole number of cells') as caught:
                xnano.box(width, 2)  # type: ignore[arg-type]
            assert caught.value.details[0].location == ('width',)
        card = xnano.box(4, 2)
        with pytest.raises(TypeError, match='whole number of cells'):
            card.resize('a', 4)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='xnano.Image'):
            card.draw_image(5)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='takes a Point'):
            card.local((1, 1))  # type: ignore[arg-type]
        with pytest.raises(TypeError, match=r'canvas\.screen\.write\(region, x=1\)'):
            xnano.write('a', x=1)  # type: ignore[call-arg]
        with pytest.raises(TypeError, match=r'canvas\.screen\.write\(region, width=1\)'):
            xnano.box(2, 2, width=1)  # type: ignore[call-arg]

    def test_write_and_box_say_what_they_take(self):
        with pytest.raises(TypeError, match=r'xnano\.write\(\) takes text'):
            xnano.write(5)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='canvas.screen.write'):
            xnano.write({'a': 1})  # type: ignore[arg-type]

    def test_a_standalone_region_is_shaded_through_its_colors(self):
        card = xnano.box(6, 3)
        card.color.bg.shade(lambda x, y: (x * 40, y * 40, 0))
        assert card[5, 2].background.to_rgb() == (200, 80, 0)
        label = xnano.write('hi', foreground='red')
        label.color.fg.shade(lambda x, y: (x * 40, y * 40, 0))
        assert label[1, 0].foreground.to_rgb() == (40, 0, 0)

    def test_a_region_with_no_columns_is_shaded_without_error(self, canvas):
        empty = canvas.screen.write('x', width=0)
        empty.color.bg.shade(lambda x, y: 'red')
        empty.color.fg.shade(lambda x, y: 'red')
        canvas.screen.region[3:3, 0:2].shade(lambda x, y: 'red')

    def test_the_foreground_shade_keeps_symbols_and_backgrounds(self, canvas):
        canvas.screen.region[0:3, 0:1] = 'abc'
        canvas.screen.region[0:3, 0:1] = Color('#102030')
        canvas.screen.color.fg.shade(lambda x, y: (x * 10, 0, 0) if x < 2 else None)
        first = canvas.screen.region[1, 0]
        assert first.character == 'b'
        assert first.foreground.to_rgb() == (10, 0, 0)
        assert first.background.to_rgb() == (0x10, 0x20, 0x30)
        assert canvas.screen.region[2, 0].foreground is None


class TestBoxArgumentsTeach:
    def test_a_border_kind_that_does_not_exist_names_the_kinds(self):
        with pytest.raises(ValueError, match='is not a border kind'):
            xnano.box(4, 2, border='single')  # type: ignore[arg-type]
        with pytest.raises(ValueError, match='is not a border kind'):
            xnano.write('a', border='single')  # type: ignore[arg-type]

    def test_a_color_modifier_or_title_of_the_wrong_type_is_refused(self):
        with pytest.raises((TypeError, ValueError), match='foreground must be a color'):
            xnano.box(4, 2, foreground='nocolor')
        with pytest.raises(TypeError, match='bold must be True or False'):
            xnano.box(4, 2, bold='x')  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='title must be text'):
            xnano.box(4, 2, title=5)  # type: ignore[arg-type]

    def test_a_placement_keyword_hint_gives_a_working_example(self):
        with pytest.raises(TypeError, match=r"effects=\[\{'kind': 'effect.fade_to'"):
            xnano.write('a', effects=1)  # type: ignore[call-arg]
        with pytest.raises(TypeError, match=r'lock=True'):
            xnano.write('a', lock=1)  # type: ignore[call-arg]


class TestBoxSizes:
    def test_a_box_without_a_border_shows_its_background(self):
        region = xnano.box(4, 1, background='green')
        assert region.render().strip() == ''
        green = Color('green')
        assert [region[column, 0].background for column in range(4)] == [green] * 4

    def test_a_background_fills_the_inside_of_a_bordered_box(self):
        region = xnano.box(4, 3, background='green', border='plain', padding=0)
        green = Color('green')
        for row in range(3):
            assert [region[column, row].background for column in range(4)] == [green] * 4
        region.color.bg = 'reset'
        assert region[1, 1].background is None
        assert region[0, 0].background is None

    def test_a_background_follows_a_resize(self):
        region = xnano.box(2, 1, background='green')
        region.resize(5, 2)
        green = Color('green')
        assert [
            region[column, row].background for row in range(2) for column in range(5)
        ] == [green] * 10

    def test_a_percentage_is_measured_against_the_active_canvas(self):
        with xnano.new(width=80, height=4):
            assert xnano.box('50%', 3).width == 40
            assert xnano.box(' 25% ', '100%').height == 4
        with xnano.new(width=20, height=2):
            assert xnano.box(ParentWidth - 4, 1).width == 16

    def test_a_percentage_without_a_canvas_is_measured_against_the_window(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            'xnano.terminal._screen.window_size', lambda: os.terminal_size((60, 20))
        )
        region = xnano.box('50%', '50%')
        assert (region.width, region.height) == (30, 10)

    def test_a_whole_size_never_asks_for_the_window(self, monkeypatch):
        def refuse() -> os.terminal_size:
            raise AssertionError('The window was asked for the size of a plain box.')

        monkeypatch.setattr('xnano.terminal._screen.window_size', refuse)
        assert xnano.box(3, 2).width == 3

    def test_a_copy_keeps_the_relative_size_and_a_resize_makes_it_whole_cells(self):
        formula = ParentWidth - 30
        with xnano.new(width=40, height=10):
            region = xnano.box('50%', formula)
        assert (region.width, region.height) == (20, 10)
        kept = region.copy()._box_size
        assert kept is not None
        assert isinstance(kept[0], str) and kept[0] == '50%'
        assert kept[1] is formula
        region.resize(7, 3)
        assert (region.width, region.height) == (7, 3)
        assert region.copy()._box_size == (7, 3)

    def test_a_percentage_or_formula_is_held_to_the_cells_a_region_can_have(self):
        assert xnano.box('1e9%', 1).width == 65535
        assert xnano.box(ParentWidth * 0, 1).width == 1

    def test_a_reference_to_the_state_sizes_a_box(self):
        @dataclass
        class Sizes:
            wide: int = 10

        with xnano.new(width=40, height=4, state=Sizes(), fps=10) as canvas:
            reference = canvas.state_reference(lambda state: state.wide)
            frame = xnano.box(reference, 2, border='plain')
            assert (frame.width, frame.height) == (10, 2)
            placement = canvas.screen.write(frame)
            assert (placement.width, placement.height) == (10, 2)
            canvas.state.wide = 20
            canvas.clock.step()
            assert placement.width == 20
            assert canvas.screen.render().splitlines()[0] == '┌' + '─' * 18 + '┐'

    def test_a_reference_to_the_state_is_held_to_the_cells_a_region_can_have(self):
        @dataclass
        class Sizes:
            wide: int = 10**7

        with xnano.new(width=40, height=4, state=Sizes()) as canvas:
            reference = canvas.state_reference(lambda state: state.wide)
            assert xnano.box(reference, 1).width == 65535

    def test_a_formula_that_reads_the_clock_is_refused(self):
        with xnano.new(width=20, height=2):
            with pytest.raises(TerminalError, match='canvas.screen.write') as caught:
                xnano.box(TimeElapsed * 3, 1)
        assert caught.value.code == 'validation.value'
        assert caught.value.details[0].location == ('width',)

    @pytest.mark.parametrize(
        'width',
        ['abc', 'center', '0%', (1, 5), 2.5, True, 0, 10**6],
        ids=repr,
    )
    def test_a_bad_size_is_refused_with_its_location(self, width):
        with pytest.raises(TerminalError) as caught:
            xnano.box(width, 3)  # type: ignore[arg-type]
        detail = caught.value.details[0]
        assert detail.location == ('width',)
        assert detail.input_value == width
        assert 'xnano.box()' in str(caught.value)

    def test_a_bad_height_is_refused_with_its_location(self):
        with pytest.raises(TerminalError) as caught:
            xnano.box(3, 'tall')
        detail = caught.value.details[0]
        assert detail.location == ('height',)
        assert detail.input_value == 'tall'


class TestWrittenBoxes:
    @pytest.fixture
    def wide(self):
        with new(width=80, height=4, fps=10) as opened:
            yield opened

    def test_a_half_width_box_is_half_the_canvas(self, wide):
        placement = wide.screen.write(xnano.box('50%', 3, border='plain'))
        assert (placement.width, placement.height) == (40, 3)
        rows = wide.screen.render().splitlines()
        assert rows[0].rstrip() == '┌' + '─' * 38 + '┐'
        assert rows[1].rstrip() == '│' + ' ' * 38 + '│'
        assert rows[2].rstrip() == '└' + '─' * 38 + '┘'

    def test_a_relative_box_refits_after_a_resize(self, wide):
        placement = wide.screen.write(xnano.box('50%', 3, border='plain'))
        wide.push(Event.resize(width=40, height=4))
        wide.clock.step()
        assert placement.width == 20
        rows = wide.screen.render().splitlines()
        assert rows[0].rstrip() == '┌' + '─' * 18 + '┐'
        assert rows[2].rstrip() == '└' + '─' * 18 + '┘'

    def test_a_formula_sized_box_follows_the_canvas(self, wide):
        placement = wide.screen.write(xnano.box(ParentWidth - 4, 3, border='plain'))
        assert placement.width == 76
        wide.push(Event.resize(width=30, height=4))
        wide.clock.step()
        assert placement.width == 26
        assert wide.screen.render().splitlines()[0] == '┌' + '─' * 24 + '┐'

    def test_a_size_given_to_write_wins_over_the_box(self, wide):
        narrow = wide.screen.write(xnano.box('50%', 3, border='plain'), width=10)
        assert (narrow.width, narrow.height) == (10, 3)
        assert wide.screen.render().splitlines()[0] == '┌' + '─' * 8 + '┐'
        narrow.remove()
        wider = wide.screen.write(xnano.box(6, 3, border='plain'), width=12)
        assert (wider.width, wider.height) == (12, 3)
        assert wide.screen.render().splitlines()[0] == '┌' + '─' * 10 + '┐'

    def test_a_relative_box_keeps_its_cells_and_background(self, wide):
        frame = xnano.box('50%', 3, border='plain', background='red')
        frame[1, 1] = 'x'
        placement = wide.screen.write(frame)
        assert placement.region[0, 0].character == 'x'
        assert placement.region[1, 0].background == Color('red')
        wide.push(Event.resize(width=40, height=4))
        wide.clock.step()
        assert placement.region.width == 18
        assert placement.region[0, 0].character == 'x'
        assert placement.region[17, 0].background == Color('red')
        ring = wide.screen.render(format='ansi').splitlines()[0]
        assert ring.count('\x1b[0;41m') == 1

    def test_a_background_without_a_border_follows_a_resize(self, wide):
        placement = wide.screen.write(xnano.box('25%', 1, background='green'))
        assert placement.width == 20
        wide.push(Event.resize(width=40, height=4))
        wide.clock.step()
        assert placement.width == 10
        assert all(
            placement.region[column, 0].background == Color('green')
            for column in range(10)
        )
        wide.push(Event.resize(width=80, height=4))
        wide.clock.step()
        assert placement.width == 20
        assert all(
            placement.region[column, 0].background == Color('green')
            for column in range(20)
        )

    def test_the_look_given_to_write_applies_over_the_look_of_the_box(self, wide):
        frame = xnano.box('50%', 3, border='plain', foreground='cyan')
        placement = wide.screen.write(
            frame, border='double', background='blue', bold=True
        )
        assert (placement.width, placement.height) == (40, 3)
        assert wide.screen.render().splitlines()[0] == '╔' + '═' * 38 + '╗'
        assert placement.color.fg.value == Color('cyan')
        assert placement.color.bg.value == Color('blue')
        assert placement.is_bold
        assert frame.border.kind == 'plain'

    def test_a_border_of_false_leaves_out_the_border_of_the_box(self, wide):
        frame = xnano.box('50%', 3, border='plain', title='Menu')
        frame.border.top = 'double'
        placement = wide.screen.write(frame, border=False)
        assert (placement.width, placement.height) == (40, 3)
        assert wide.screen.render().strip() == ''
        assert frame.border.kind == 'plain'
        wide.push(Event.resize(width=40, height=4))
        wide.clock.step()
        assert wide.screen.render().strip() == ''

    def test_a_border_of_false_leaves_out_the_border_of_a_whole_cell_box(self, wide):
        frame = xnano.box(3, 2, border='plain')
        placement = wide.screen.write(frame, border=False)
        assert (placement.width, placement.height) == (3, 2)
        assert wide.screen.render().strip() == ''
        assert frame.border.kind == 'plain'

    def test_a_border_of_false_leaves_out_the_title_of_a_whole_cell_box(self, wide):
        frame = xnano.box(8, 3, border='plain', title='Menu')
        placement = wide.screen.write(frame, border=False)
        assert (placement.width, placement.height) == (8, 3)
        assert 'Menu' not in wide.screen.render()
        assert wide.screen.render().strip() == ''
        assert frame.border.kind == 'plain'
        assert frame.render().splitlines()[0] == '┌Menu──┐'

    def test_a_border_given_to_write_replaces_the_border_of_a_whole_cell_box(self, wide):
        frame = xnano.box(3, 2, border='plain')
        placement = wide.screen.write(frame, border='double')
        assert (placement.width, placement.height) == (3, 2)
        assert wide.screen.render().splitlines()[:2] == ['╔═╗', '╚═╝']
        assert frame.border.kind == 'plain'

    def test_a_border_given_to_write_replaces_the_border_of_a_box_on_a_placement(
        self, wide
    ):
        holder = wide.screen.write(None, width=20, height=4)
        placement = holder.write(xnano.box(3, 2, border='plain'), border='double')
        assert (placement.width, placement.height) == (3, 2)
        assert wide.screen.render().splitlines()[:2] == ['╔═╗', '╚═╝']
        placement.remove()
        removed = holder.write(xnano.box(3, 2, border='plain'), border=False)
        assert (removed.width, removed.height) == (3, 2)
        assert wide.screen.render().strip() == ''

    def test_the_look_given_to_write_is_laid_over_the_look_of_a_whole_cell_box(
        self, wide
    ):
        frame = xnano.box(4, 2, foreground='cyan')
        placement = wide.screen.write(frame, background='blue')
        assert (placement.width, placement.height) == (4, 2)
        assert placement.color.fg.value == Color('cyan')
        assert placement.color.bg.value == Color('blue')
        assert frame.color.bg.value is None

    def test_a_border_given_to_write_is_inside_the_size_of_a_box_with_no_border(
        self, wide
    ):
        placement = wide.screen.write(xnano.box(3, 2), border='plain')
        assert (placement.width, placement.height) == (3, 2)
        assert wide.screen.render().splitlines()[:2] == ['┌─┐', '└─┘']

    def test_a_color_on_a_box_does_not_change_the_size_a_border_gives_it(self, wide):
        plain = wide.screen.write(xnano.box(6, 3), border='double')
        colored = wide.screen.write(
            xnano.box(6, 3, foreground='cyan'), x=10, border='double'
        )
        assert (plain.width, plain.height) == (colored.width, colored.height) == (6, 3)

    def test_a_margin_given_to_write_surrounds_a_box_that_keeps_its_size(self, wide):
        placement = wide.screen.write(xnano.box(4, 3, border='plain'), margin=1)
        assert (placement.width, placement.height) == (6, 5)
        assert wide.screen.render().splitlines()[1:4] == [' ┌──┐', ' │  │', ' └──┘']

    def test_a_margin_on_some_edges_adds_only_those_edges_to_the_size_of_a_box(
        self, wide
    ):
        placement = wide.screen.write(
            xnano.box(4, 3, border='plain'), margin={'left': 2, 'top': 1}
        )
        assert (placement.width, placement.height) == (6, 4)
        assert wide.screen.render().splitlines()[1:4] == ['  ┌──┐', '  │  │', '  └──┘']

    def test_a_border_given_with_false_draws_over_the_box(self, wide):
        frame = xnano.box('50%', 3, border='plain')
        wide.screen.write(frame, border=False, title='Menu')
        assert wide.screen.render().splitlines()[0] == '┌Menu' + '─' * 34 + '┐'

    def test_the_border_of_a_relative_box_is_on_its_placement(self, wide):
        placement = wide.screen.write(xnano.box('50%', 3, border='plain'))
        assert placement.region.width == 38
        assert placement.region[0, 0].character == ' '

    def test_the_border_of_a_snapshot_is_in_the_cells_of_its_placement(self, wide):
        placement = wide.screen.write(xnano.box(6, 3, border='plain'), x=2)
        assert placement.region.width == 6
        assert placement.region[0, 0].character == '┌'

    def test_a_relative_box_keeps_the_sides_of_its_border(self, wide):
        frame = xnano.box('50%', 3, border='plain')
        frame.border.top = 'double'
        wide.screen.write(frame)
        wide.push(Event.resize(width=40, height=4))
        wide.clock.step()
        rows = wide.screen.render().splitlines()
        assert rows[0] == '╔' + '═' * 18 + '╗'
        assert rows[2] == '└' + '─' * 18 + '┘'

    def test_a_relative_box_is_a_slot_of_a_stacking_canvas(self):
        with new(width=20, height=8, layout='column', fps=10) as stacked:
            top = stacked.screen.write(xnano.box('100%', 3, border='plain', title='a'))
            bottom = stacked.screen.write(xnano.box('50%', '50%', border='rounded'))
            stacked.clock.step()
            assert (top.width, top.height) == (20, 3)
            assert (bottom.width, bottom.height) == (10, 4)
            rows = stacked.screen.render().splitlines()
            assert rows[0] == '┌a' + '─' * 17 + '┐'
            assert rows[3] == '╭' + '─' * 8 + '╮'

    def test_a_relative_box_nests_inside_a_placement(self, wide):
        outer = wide.screen.write(xnano.box('100%', '100%', border='double'))
        inner = outer.write(xnano.box('50%', 3, border='plain'), x=1, y=0)
        assert (inner.width, inner.height) == (39, 3)
        wide.push(Event.resize(width=40, height=4))
        wide.clock.step()
        assert (outer.width, inner.width) == (40, 19)
        assert wide.screen.render().splitlines()[1].startswith('║ ┌' + '─' * 17 + '┐')

    def test_a_locked_relative_box_keeps_its_size(self, wide):
        placement = wide.screen.write(xnano.box('50%', 3, border='plain'), lock=True)
        wide.push(Event.resize(width=40, height=4))
        wide.clock.step()
        assert placement.width == 40

    def test_a_box_smaller_than_its_border_still_draws(self, wide):
        placement = wide.screen.write(
            xnano.box('50%', 3, border='plain', padding=1, background='blue')
        )
        wide.push(Event.resize(width=4, height=4))
        wide.clock.step()
        assert (placement.width, placement.height) == (2, 3)
        assert wide.screen.render().splitlines()[0] == '┌┐'

    def test_a_refused_write_leaves_nothing_behind(self, wide):
        with pytest.raises(ValueError, match='width'):
            wide.screen.write(xnano.box('50%', 3, border='plain'), width='sideways')
        assert wide.screen.render().strip() == ''

    def test_a_whole_cell_box_written_as_it_is_is_still_a_snapshot(self, wide):
        placement = wide.screen.write(xnano.box(6, 3, border='plain'))
        assert (placement.width, placement.height) == (6, 3)
        assert placement.region.width == 6
        assert placement.region[0, 0].character == '┌'

    def test_a_margin_given_to_write_surrounds_a_box_with_no_look_of_its_own(self, wide):
        placement = wide.screen.write(xnano.box(6, 3), margin=1)
        assert (placement.width, placement.height) == (8, 5)

    def test_a_margin_that_is_a_share_is_measured_against_the_box(self):
        with new(width=30, height=10, fps=10) as tall:
            placement = tall.screen.write(xnano.box(10, 4, border='plain'), margin='20%')
            assert (placement.width, placement.height) == (14, 6)
            rows = tall.screen.render().splitlines()
            assert rows[1].rstrip() == '  ┌' + '─' * 8 + '┐'
            assert rows[4].rstrip() == '  └' + '─' * 8 + '┘'

    def test_a_margin_that_is_a_share_stays_a_share_on_an_axis_with_a_size(self, wide):
        placement = wide.screen.write(
            xnano.box(10, 3, border='plain'), width='50%', margin='10%'
        )
        assert (placement.width, placement.height) == (40, 3)
        assert wide.screen.render().splitlines()[0].startswith('    ┌')
        wide.push(Event.resize(width=40, height=4))
        wide.clock.step()
        assert placement.width == 20
        assert wide.screen.render().splitlines()[0].startswith('  ┌')


_TEMPO_CHANGE = ((0.0, 120.0), (2.0, 60.0))


def _chord_region(**changes):
    """A region from beat 1 for 2 beats over the chord C4 E4 G4 at a changing tempo."""
    arguments = {
        'start_beats': 1.0,
        'length_beats': 2.0,
        'pitches': [60, 64, 67],
        'tempo_changes': _TEMPO_CHANGE,
    }
    arguments.update(changes)
    return _timeline_region(**arguments)


class TestTimeline:
    def test_a_region_on_the_timeline_is_beats_by_semitones(self):
        region = _chord_region()
        assert region.resolution == 'beats'
        assert (region.x, region.width) == (1.0, 2.0)
        assert (region.y, region.height) == (60, 8)

    def test_ticks_are_sixteenth_notes_four_to_a_beat(self):
        ticks = _chord_region().ticks
        assert ticks.resolution == 'ticks'
        assert (ticks.x, ticks.width) == (4.0, 8.0)
        assert (ticks.y, ticks.height) == (60, 8)

    def test_milliseconds_follow_the_tempo(self):
        steady = _chord_region(tempo_changes=((0.0, 120.0),)).milliseconds
        assert steady.resolution == 'milliseconds'
        assert (steady.x, steady.width) == (500.0, 1000.0)
        assert (steady.y, steady.height) == (60, 8)

    def test_milliseconds_integrate_a_tempo_change(self):
        # Beat 1 is 0.5 s in at 120 bpm; beats 1 to 2 last 0.5 s, then beats 2 to 3 last 1 s at 60.
        slowing = _chord_region().milliseconds
        assert (slowing.x, slowing.width) == (500.0, 1500.0)
        later = _chord_region(start_beats=3.0, length_beats=1.0).milliseconds
        assert (later.x, later.width) == (2000.0, 1000.0)
        assert _chord_region().beats.milliseconds.width == 1500.0

    def test_a_chord_spans_every_semitone_between_its_pitches(self):
        assert (_chord_region(pitches=[67, 60, 64]).y, _chord_region().height) == (60, 8)
        single = _chord_region(pitches=[72])
        assert (single.y, single.height) == (72, 1)
        for view in (single.ticks, single.milliseconds):
            assert (view.y, view.height) == (72, 1)

    def test_no_pitches_span_no_semitones(self):
        silent = _chord_region(pitches=[])
        assert (silent.y, silent.height) == (0, 0)
        assert (1.5, 0) not in silent

    def test_a_timeline_without_tempo_changes_is_refused(self):
        with pytest.raises(ValueError, match='tempo_changes is empty'):
            _chord_region(tempo_changes=())

    def test_the_first_tempo_change_must_be_at_beat_zero(self):
        with pytest.raises(ValueError, match=r'at beat 1\.0') as caught:
            _chord_region(tempo_changes=((1.0, 120.0),))
        assert 'first tempo change' in str(caught.value)

    @pytest.mark.parametrize('tempo', [0.0, -60.0, float('nan')], ids=repr)
    def test_every_tempo_must_be_above_zero(self, tempo):
        with pytest.raises(ValueError, match='above 0 beats per minute') as caught:
            _chord_region(tempo_changes=((0.0, 120.0), (2.0, tempo)))
        assert 'beat 2.0' in str(caught.value)
        with pytest.raises(ValueError, match='above 0 beats per minute'):
            _chord_region(tempo_changes=((0.0, tempo),))

    def test_a_view_carries_the_span(self):
        region = _chord_region()
        assert region.beats.ticks.milliseconds.ticks.x == 4.0
        assert repr(region) == (
            "Region(timeline, x=1.0, width=2.0, y=60, height=8, resolution='beats')"
        )
        assert repr(region.ticks) == (
            "Region(timeline, x=4.0, width=8.0, y=60, height=8, resolution='ticks')"
        )

    def test_a_beat_and_a_pitch_are_in_the_region_in_its_own_grid(self):
        region = _chord_region()
        assert (1, 60) in region and (1.5, 67) in region and (2.999, 63.5) in region
        assert (0.999, 60) not in region and (3, 60) not in region
        assert (1, 59) not in region and (1, 68) not in region
        assert (4, 60) in region.ticks and (3.9, 60) not in region.ticks
        assert (500, 64) in region.milliseconds and (2000, 64) not in region.milliseconds

    def test_anything_but_a_pair_of_numbers_is_not_in_the_region(self):
        region = _chord_region()
        for point in (
            'ab',
            None,
            (1,),
            (1, 60, 3),
            ('1', 60),
            (1, None),
            (True, 60),
            [1, 60],
            Point(1, 60),
        ):
            assert point not in region

    def test_local_is_relative_to_the_start_and_the_lowest_pitch(self):
        region = _chord_region()
        assert region.local((1.5, 62)) == (0.5, 2)
        assert region.ticks.local((6, 60)) == (2, 0)
        assert region.milliseconds.local((750.0, 64)) == (250.0, 4)

    def test_local_takes_a_pair_on_the_timeline_and_a_point_on_the_screen(self, canvas):
        for point in (Point(1, 60), 'ab', (1,), (1, 'x')):
            with pytest.raises(TerminalError, match=r'\(beat, pitch\)') as caught:
                _chord_region().local(point)
            assert caught.value.code == 'validation.type'
        with pytest.raises(TerminalError, match='takes a Point') as caught:
            canvas.screen.region.local((1, 1))
        assert caught.value.code == 'validation.type'

    @pytest.mark.parametrize(
        'read',
        [
            pytest.param(lambda region: region.half_blocks, id='half_blocks'),
            pytest.param(lambda region: region.braille, id='braille'),
            pytest.param(lambda region: region.cells, id='cells'),
            pytest.param(lambda region: region.size, id='size'),
            pytest.param(lambda region: region[0, 0], id='getitem'),
            pytest.param(lambda region: region[0:1, 0:1], id='getitem-slice'),
            pytest.param(lambda region: region.color, id='color'),
            pytest.param(lambda region: region.border, id='border'),
            pytest.param(lambda region: region.padding, id='padding'),
            pytest.param(lambda region: region.margin, id='margin'),
            pytest.param(lambda region: region.render(), id='render'),
            pytest.param(lambda region: region.copy(), id='copy'),
            pytest.param(lambda region: region.__xnano_write__(), id='xnano_render'),
            pytest.param(lambda region: region.cell_for_pixel(0, 0), id='cell_for_pixel'),
            pytest.param(lambda region: region.pixel_for_cell(0, 0), id='pixel_for_cell'),
            pytest.param(lambda region: region.resize(2, 2), id='resize'),
            pytest.param(lambda region: region.shade(lambda x, y: None), id='shade'),
            pytest.param(
                lambda region: region.draw_color_bytes(b'\0' * 4, width=1, height=1),
                id='draw_color_bytes',
            ),
            pytest.param(lambda region: region.draw_image(object()), id='draw_image'),
        ],
    )
    def test_a_screen_member_refuses_a_region_on_the_timeline(self, read):
        with pytest.raises(TerminalError, match='timeline') as caught:
            read(_chord_region())
        assert caught.value.code == 'canvas.state'
        assert 'screen' in str(caught.value)
        assert 'region.beats' in str(caught.value)

    @pytest.mark.parametrize(
        'write',
        [
            pytest.param(lambda region: region.__setitem__((0, 0), 'x'), id='setitem'),
            pytest.param(
                lambda region: region.__setitem__((0, 0), Pixel('block')),
                id='setitem-pixel',
            ),
            pytest.param(
                lambda region: region.__setitem__((slice(0, 1), slice(0, 1)), 'x'),
                id='setitem-slice',
            ),
            pytest.param(
                lambda region: setattr(region, 'border', 'plain'), id='set-border'
            ),
            pytest.param(lambda region: setattr(region, 'padding', 1), id='set-padding'),
            pytest.param(lambda region: setattr(region, 'margin', 1), id='set-margin'),
        ],
    )
    def test_writing_to_a_region_on_the_timeline_is_refused(self, write):
        with pytest.raises(TerminalError, match='timeline') as caught:
            write(_chord_region())
        assert caught.value.code == 'canvas.state'

    def test_the_views_of_a_region_on_the_timeline_refuse_the_screen_too(self):
        for view in (
            _chord_region().ticks,
            _chord_region().milliseconds,
            _chord_region().beats,
        ):
            with pytest.raises(TerminalError, match='timeline') as caught:
                _ = view.half_blocks
            assert caught.value.code == 'canvas.state'

    def test_the_message_names_the_member_the_medium_and_what_to_use(self):
        with pytest.raises(TerminalError) as caught:
            _ = _chord_region().half_blocks
        message = str(caught.value)
        assert (
            'region.half_blocks is a view of a region on the screen, but this region is on '
            'the timeline: beats by semitones, from a Note, a Melody, audio or the '
            'context of a playable. On the timeline read region.beats, region.ticks or '
            'region.milliseconds, and x, y, width and height.'
        ) in message
        with pytest.raises(
            TerminalError, match=r'region\.copy\(\) needs a region on the screen'
        ):
            _chord_region().copy()

    def test_writing_a_region_on_the_timeline_to_a_canvas_is_refused(self, canvas):
        with pytest.raises(TerminalError, match='timeline') as caught:
            canvas.screen.write(_chord_region())
        assert caught.value.code == 'canvas.state'
        assert canvas.screen.region[0, 0].character == ' '

    def test_the_refusal_to_write_a_timeline_region_names_the_call_that_was_written(
        self, canvas
    ):
        with pytest.raises(TerminalError) as caught:
            canvas.screen.write(xnano.note('C4').region)
        message = str(caught.value)
        assert (
            'canvas.screen.write() draws the cells of a region on the screen' in message
        )
        assert 'region.copy()' not in message
        assert 'canvas.speaker.play()' in message
        label = canvas.screen.write('x')
        with pytest.raises(TerminalError) as caught:
            label.write(_chord_region())
        assert 'placement.write() draws the cells' in str(caught.value)
        assert canvas.screen.render().splitlines()[0].startswith('x')

    def test_str_of_a_region_on_the_timeline_is_its_repr(self):
        region = _chord_region()
        assert str(region) == repr(region)
        assert f'{region.ticks}' == repr(region.ticks)
        assert str(xnano.note('C4').region).startswith(
            'Region(timeline, x=0.0, width=1.0'
        )

    def test_str_of_a_region_on_the_screen_is_its_characters(self, canvas):
        assert str(xnano.write('hi')) == 'hi'
        assert str(canvas.screen.region) == canvas.screen.region.render()

    @pytest.mark.parametrize('name', ['beats', 'ticks', 'milliseconds'])
    def test_a_region_on_the_screen_refuses_the_timeline_views(self, canvas, name):
        for region in (
            canvas.screen.region,
            canvas.screen.region.braille,
            canvas.screen.region[0:3, 0:2],
            xnano.box(4, 2),
            xnano.write('hi'),
        ):
            with pytest.raises(TerminalError, match='screen') as caught:
                getattr(region, name)
            assert caught.value.code == 'canvas.state'
            assert f'region.{name}' in str(caught.value)
            assert 'region.cells' in str(caught.value)
            assert 'timeline' in str(caught.value)

    def test_a_region_on_the_screen_has_cells_and_a_size(self, canvas):
        assert canvas.screen.region.cells.resolution == 'cells'
        assert canvas.screen.region.size == Size(12, 5)
        assert canvas.screen.region.half_blocks.size == Size(12, 10)
        assert canvas.screen.region.braille.size == Size(24, 20)
        assert canvas.screen.region.braille.cells.size == Size(12, 5)
        assert canvas.screen.region[2:5, 1:3].size == Size(3, 2)
        assert xnano.write('hello\nworld!').size == Size(6, 2)

    def test_a_screen_region_still_has_whole_number_coordinates(self, canvas):
        label = canvas.screen.write('abcd', x=3, y=2)
        canvas.clock.step()
        region = label.region
        assert (type(region.x), type(region.y)) == (int, int)
        assert (type(region.width), type(region.height)) == (int, int)
        assert (region.x, region.y, region.width, region.height) == (3, 2, 4, 1)
        assert (region.braille.width, region.braille.height) == (8, 4)

    def test_a_resolution_must_match_its_medium(self):
        placeholder = _chord_region()._buffer
        with pytest.raises(TerminalError, match='without a timeline') as caught:
            Region(placeholder, resolution='beats')
        assert caught.value.code == 'validation.value'
        span = _chord_region()._timeline
        with pytest.raises(TerminalError, match='screen resolution') as caught:
            Region(placeholder, resolution='cells', timeline=span)
        assert caught.value.code == 'validation.value'
