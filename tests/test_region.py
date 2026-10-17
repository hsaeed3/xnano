"""
tests.test_region

Region: standalone and live, indexing to Pixel, slices, containment, resize, resolutions,
batched shading and images.
"""

from __future__ import annotations

import pytest

import xnano
from xnano import Color, Pixel, new
from xnano.errors import TerminalError
from xnano.region import Region
from xnano_core import Event, Point


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

    def test_box_is_an_empty_bordered_rectangle(self):
        frame = xnano.box(5, 3)
        assert frame.render().split('\n') == ['┌───┐', '│   │', '└───┘']
        plain = xnano.box(4, 2, border=False)
        assert plain.render().strip() == ''
        rounded = xnano.box(4, 3, border='rounded', title='x')
        assert rounded.render().split('\n')[0] == '╭x─╮'

    def test_a_box_keeps_its_size_and_content_when_the_look_changes(self):
        frame = xnano.box(6, 4)
        frame[1:3, 1:2] = 'ab'
        frame.border = 'double'
        assert (frame.width, frame.height) == (6, 4)
        assert frame.render().split('\n')[1] == '║ab  ║'

    def test_a_box_needs_a_size(self):
        with pytest.raises(ValueError, match='at least 1 by 1'):
            xnano.box(0, 3)

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
        placement = canvas.write(region)
        region[0, 0] = 'Z'
        canvas.step()
        assert canvas.render().split('\n')[0] == 'abc'
        assert placement.width == 3
        second = canvas.write(region, y=2)
        canvas.step()
        assert canvas.render().split('\n')[2] == 'Zbc'
        second.remove()

    def test_changing_a_written_region_leaves_the_placement_look_alone(self, canvas):
        region = xnano.write('abc')
        placement = canvas.write(region)
        region.border = 'double'
        placement.border = 'plain'
        region.border = False
        canvas.step()
        assert canvas.render().split('\n')[0] == '┌───┐'
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
            canvas.write('hello')
            canvas.step()
            assert str(canvas.region) == canvas.region.render()

    def test_region_is_not_a_top_level_name(self):
        assert not hasattr(xnano, 'Region')
        assert 'Region' not in xnano.__all__


class TestLiveViews:
    def test_a_canvas_region_reads_and_writes_cells(self, canvas):
        region = canvas.region
        assert (region.width, region.height) == (12, 5)
        region[0, 0] = Pixel('star', foreground='red')
        assert region[0, 0].character == '★'
        assert region[0, 0].foreground == Color('red')
        assert canvas.render().split('\n')[0] == '★'

    def test_a_placement_region_is_inside_its_decoration(self, canvas):
        label = canvas.write('abc', border='rounded', padding=1, margin=1)
        region = label.region
        assert (region.width, region.height) == (3, 1)
        region[0, 0] = Pixel('star')
        canvas.step()
        assert '★bc' in canvas.render()
        assert (label.width, label.height) == (9, 7)

    def test_a_region_of_a_decorated_widget_is_inside_the_border(self, canvas):
        from xnano_core import Buffer

        block = canvas.write(Buffer(width=4, height=2), border='plain')
        assert (block.region.width, block.region.height) == (4, 2)

    def test_resize_on_a_placement_resizes_the_placement(self, canvas):
        label = canvas.write('abcd', border='plain')
        label.region.resize(6, 2)
        assert (label.width, label.height) == (8, 4)

    def test_resize_on_a_canvas_view_is_refused(self, canvas):
        with pytest.raises(TerminalError, match='follows its screen'):
            canvas.region.resize(3, 3)

    def test_a_view_has_no_appearance_of_its_own(self, canvas):
        for name in ('color', 'border', 'padding', 'margin'):
            with pytest.raises(TerminalError, match=f'canvas.{name}'):
                getattr(canvas.region, name)
        with pytest.raises(TerminalError, match='instead of region.border'):
            canvas.region.border = 'plain'

    def test_containment_uses_screen_cells_and_local_converts(self, canvas):
        label = canvas.write('abcd', x=3, y=2)
        canvas.step()
        region = label.region
        assert (region.x, region.y) == (3, 2)
        assert (3, 2) in region and Point(6, 2) in region
        assert (2, 2) not in region and (7, 2) not in region and (3, 3) not in region
        assert region.local(Point(5, 2)) == Point(2, 0)
        assert region[region.local(Point(5, 2)).x, 0].character == 'c'

    def test_containment_in_a_mouse_hook(self, canvas):
        label = canvas.write('abcd', x=3, y=2)
        hits: list[str] = []

        @canvas.hook(on='mouse', when="mouse.kind == 'press'")
        def press(context):
            hits.append('in' if context.mouse.position in label.region else 'out')

        for column in (3, 8):
            canvas.push(
                Event.mouse_event(column=column, row=2, kind='press', button='left')
            )
            canvas.deliver_events()
        assert hits == ['in', 'out']

    def test_a_placement_local_and_a_canvas_local(self, canvas):
        label = canvas.write('abcd', x=3, y=2)
        assert label.local(Point(5, 3)) == Point(2, 1)
        assert canvas.local(Point(5, 3)) == Point(5, 3)

    def test_a_view_is_rendered_as_text(self, canvas):
        canvas.region[0:3, 0:1] = 'abc'
        assert canvas.region[0:3, 0:1].render() == 'abc'


class TestIndexing:
    def test_out_of_range_names_the_valid_ranges(self, canvas):
        with pytest.raises(IndexError, match=r'x runs from 0 to 11 and y from 0 to 4'):
            canvas.region[12, 0]
        with pytest.raises(IndexError, match='region.local'):
            canvas.region[0, 5] = 'x'

    def test_a_screen_point_is_refused(self, canvas):
        with pytest.raises(TypeError, match='takes region cells'):
            canvas.region[Point(1, 1)]
        with pytest.raises(TypeError, match='takes region cells'):
            canvas.region[Point(1, 1)] = 'x'

    def test_keys_must_be_pairs_of_whole_numbers_or_slices(self, canvas):
        with pytest.raises(TypeError, match='indexed by'):
            canvas.region[1]  # type: ignore[index]
        with pytest.raises(TypeError, match='whole number or a slice'):
            canvas.region[1.5, 0]  # type: ignore[index]

    def test_a_slice_is_a_view(self, canvas):
        canvas.region[2:5, 1:3] = 'abc'
        part = canvas.region[2:5, 1:3]
        assert isinstance(part, Region)
        assert (part.width, part.height) == (3, 2)
        assert part[0, 0].character == 'a'
        part[1, 1] = Pixel('x')
        assert canvas.region[3, 2].character == 'x'
        assert canvas.region[:, :].width == 12
        assert canvas.region[-3:, -1:].width == 3

    def test_a_slice_with_a_step_is_explained(self, canvas):
        with pytest.raises(ValueError, match='cannot have a step'):
            canvas.region[0:6:2, 0:2] = 'x'

    def test_assigning_a_string_is_text_never_a_color(self, canvas):
        canvas.region[0:5, 0:2] = 'hello'
        assert canvas.render().split('\n')[0] == 'hello'
        assert canvas.region[0, 0].background is None
        canvas.region[0, 1] = 'red'
        assert canvas.region[0, 1].character == 'r'

    def test_a_color_sets_the_background_of_a_cell_or_a_slice(self, canvas):
        canvas.region[1, 1] = (10, 20, 30)
        assert canvas.region[1, 1].background.to_rgb() == (10, 20, 30)
        canvas.region[2:4, 1:3] = Color('#ff0000')
        for column in (2, 3):
            assert canvas.region[column, 2].background.to_rgb() == (255, 0, 0)
        assert canvas.region[4, 2].background is None

    def test_a_pixel_fills_a_slice(self, canvas):
        canvas.region[0:3, 0:2] = Pixel('shade_light', foreground='green')
        assert canvas.render().split('\n')[:2] == ['░░░', '░░░']

    def test_content_covers_a_slice_and_a_cell_refuses_it(self, canvas):
        canvas.region[2:6, 1:3] = xnano.write('xy')
        canvas.step()
        assert canvas.render().split('\n')[1].startswith('  xy')
        with pytest.raises(TypeError, match='two slices'):
            canvas.region[0, 0] = xnano.write('x')

    def test_the_original_cells_are_read_as_pixels(self, canvas):
        found = canvas.region[0, 0]
        assert isinstance(found, Pixel)
        assert found.character == ' '
        assert found.foreground is None and found.background is None


class TestResolutions:
    def test_half_blocks_have_two_pixels_per_cell(self, canvas):
        pixels = canvas.region.half_blocks
        assert (pixels.width, pixels.height) == (12, 10)
        assert pixels.resolution == 'half_blocks'
        pixels[0, 0] = (255, 0, 0)
        pixels[0, 1] = (0, 0, 255)
        assert canvas.region[0, 0].character == '▀'
        assert pixels[0, 0].foreground.to_rgb() == (255, 0, 0)
        assert pixels[0, 1].foreground.to_rgb() == (0, 0, 255)

    def test_braille_has_eight_dots_per_cell(self, canvas):
        dots = canvas.region.braille
        assert (dots.width, dots.height) == (24, 20)
        dots[3, 5] = (255, 255, 255)
        assert dots[3, 5].character == '•'
        assert dots[2, 5].character == ' '
        assert canvas.region[1, 1].character == '⠐'

    def test_text_is_not_written_at_a_pixel_resolution(self, canvas):
        with pytest.raises(TypeError, match='cell resolution|cell region'):
            canvas.region.braille[0, 0] = 'x'
        with pytest.raises(TypeError, match='color or a Pixel'):
            canvas.region.half_blocks[0:2, 0:1] = 'red'

    def test_a_slice_of_a_pixel_view_is_refused(self, canvas):
        with pytest.raises(ValueError, match='cut cells in two'):
            canvas.region.half_blocks[0:2, 0:2]

    def test_cell_and_pixel_conversion(self, canvas):
        pixels = canvas.region.half_blocks
        assert pixels.cell_for_pixel(3, 5) == (3, 2)
        assert pixels.pixel_for_cell(1, 1, anchor='top_left') == (1, 2)
        assert canvas.region.cell_for_pixel(3, 5) == (3, 5)
        assert canvas.region.pixel_for_cell(3, 5) == (3, 5)


class TestShade:
    def test_cells_are_shaded_in_one_batched_write(self, canvas):
        canvas.region.shade(lambda x, y: (x * 20, y * 40, 0) if x < 10 else None)
        assert canvas.region[3, 2].background.to_rgb() == (60, 80, 0)
        assert canvas.region[11, 2].background is None

    def test_pixels_and_dots_are_shaded_at_their_resolution(self, canvas):
        calls: list[tuple[int, int]] = []

        def paint(x: int, y: int):
            calls.append((x, y))
            return (x, y, 0)

        canvas.region.half_blocks.shade(paint)
        assert len(calls) == 12 * 10
        calls.clear()
        canvas.region.braille.shade(paint)
        assert len(calls) == 24 * 20

    def test_shading_a_slice_uses_slice_coordinates(self, canvas):
        part = canvas.region[2:5, 1:3]
        part.shade(lambda x, y: (x, y, 9))
        assert canvas.region[2, 1].background.to_rgb() == (0, 0, 9)
        assert canvas.region[4, 2].background.to_rgb() == (2, 1, 9)
        assert canvas.region[5, 2].background is None

    def test_shading_a_placement_matches_a_per_cell_loop(self, canvas):
        label = canvas.write('abcdef', y=1)
        label.region.shade(lambda x, y: (x * 30, 0, 0))
        for column in range(6):
            assert label.region[column, 0].background.to_rgb() == (column * 30, 0, 0)
            assert label.region[column, 0].character == 'abcdef'[column]


class TestImages:
    def test_color_bytes_are_drawn_at_a_pixel_position(self, canvas):
        canvas.region.draw_color_bytes(
            bytes([255, 0, 0, 255]) * 4, width=2, height=2, x=4, y=0
        )
        assert canvas.region[4, 0].background.to_rgb() == (255, 0, 0)

    def test_an_image_is_drawn_and_may_be_scrolled(self, canvas):
        class Picture:
            width = 2
            height = 2

            def to_rgba(self, frame_index: int) -> bytes:
                return bytes([0, 255, 0, 255]) * 4

        canvas.region.draw_image(Picture(), x=1, y=0)
        assert canvas.region[1, 0].background.to_rgb() == (0, 255, 0)
        canvas.region.draw_image(Picture(), x=-1, y=0, mode='replace')
        assert canvas.region[0, 0].background.to_rgb() == (0, 255, 0)


class TestCursorFollowsARegion:
    def test_the_cursor_follows_a_region_cell(self, canvas):
        label = canvas.write('name', x=3, y=1, border='plain')
        canvas.cursor.follow(label.region, x=2)
        canvas.step()
        assert canvas.cursor.position == Point(3 + 1 + 2, 1 + 1)


class TestCoordinates:
    def test_an_integer_beside_a_slice_must_be_inside_the_region(self, canvas):
        region = canvas.region
        for key in ((99, slice(0, 2)), (-1, slice(0, 2)), (slice(0, 2), 7)):
            with pytest.raises(IndexError, match='outside this region'):
                region[key]
            with pytest.raises(IndexError, match='outside this region'):
                region[key] = Pixel('block')
        assert region[3, 0:2].height == 2

    def test_wrong_arguments_say_what_to_pass(self):
        with pytest.raises(TypeError, match='whole number of cells'):
            xnano.box('a', 2)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='whole number of cells'):
            xnano.box(2.5, 2)  # type: ignore[arg-type]
        card = xnano.box(4, 2)
        with pytest.raises(TypeError, match='whole number of cells'):
            card.resize('a', 4)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='xnano.Image'):
            card.draw_image(5)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='takes a Point'):
            card.local((1, 1))  # type: ignore[arg-type]
        with pytest.raises(TypeError, match=r'canvas\.write\(region, x=1\)'):
            xnano.write('a', x=1)  # type: ignore[call-arg]
        with pytest.raises(TypeError, match=r'canvas\.write\(region, width=1\)'):
            xnano.box(2, 2, width=1)  # type: ignore[call-arg]

    def test_write_and_box_say_what_they_take(self):
        with pytest.raises(TypeError, match=r'xnano\.write\(\) takes text'):
            xnano.write(5)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='canvas.write'):
            xnano.write({'a': 1})  # type: ignore[arg-type]

    def test_a_standalone_region_is_shaded_through_its_colors(self):
        card = xnano.box(6, 3)
        card.color.bg.shade(lambda x, y: (x * 40, y * 40, 0))
        assert card[5, 2].background.to_rgb() == (200, 80, 0)
        label = xnano.write('hi', foreground='red')
        label.color.fg.shade(lambda x, y: (x * 40, y * 40, 0))
        assert label[1, 0].foreground.to_rgb() == (40, 0, 0)

    def test_a_region_with_no_columns_is_shaded_without_error(self, canvas):
        empty = canvas.write('x', width=0)
        empty.color.bg.shade(lambda x, y: 'red')
        empty.color.fg.shade(lambda x, y: 'red')
        canvas.region[3:3, 0:2].shade(lambda x, y: 'red')

    def test_the_foreground_shade_keeps_symbols_and_backgrounds(self, canvas):
        canvas.region[0:3, 0:1] = 'abc'
        canvas.region[0:3, 0:1] = Color('#102030')
        canvas.color.fg.shade(lambda x, y: (x * 10, 0, 0) if x < 2 else None)
        first = canvas.region[1, 0]
        assert first.character == 'b'
        assert first.foreground.to_rgb() == (10, 0, 0)
        assert first.background.to_rgb() == (0x10, 0x20, 0x30)
        assert canvas.region[2, 0].foreground is None


class TestBoxArgumentsTeach:
    def test_a_border_kind_that_does_not_exist_names_the_kinds(self):
        with pytest.raises(ValueError, match='is not a border kind'):
            xnano.box(4, 2, border='single')  # type: ignore[arg-type]
        with pytest.raises(ValueError, match='is not a border kind'):
            xnano.write('a', border='single')  # type: ignore[arg-type]

    def test_a_color_modifier_or_title_of_the_wrong_type_is_refused(self):
        with pytest.raises((TypeError, ValueError), match='foreground must be a color'):
            xnano.box(4, 2, foreground='nocolor')
        with pytest.raises(TypeError, match='is_bold must be True or False'):
            xnano.box(4, 2, is_bold='x')  # type: ignore[arg-type]
        with pytest.raises(TypeError, match='title must be text'):
            xnano.box(4, 2, title=5)  # type: ignore[arg-type]

    def test_a_placement_keyword_hint_gives_a_working_example(self):
        with pytest.raises(TypeError, match=r"effects=\[\{'kind': 'effect.fade_to'"):
            xnano.write('a', effects=1)  # type: ignore[call-arg]
        with pytest.raises(TypeError, match=r'lock=True'):
            xnano.write('a', lock=1)  # type: ignore[call-arg]
