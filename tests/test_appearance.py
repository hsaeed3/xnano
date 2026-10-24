"""
tests.test_appearance

The appearance objects: color, border, padding and margin on canvases, placements and regions.
"""

from __future__ import annotations

import pytest

import xnano
import xnano_core
from xnano import Color, new
from xnano.canvas import Canvas
from xnano.errors import TerminalError
from xnano.hooks import Context
from xnano.layout import Placement
from xnano.styles import Colors, ColorSlot
from xnano_core import Buffer, Event


@pytest.fixture
def canvas():
    with new(width=24, height=8, fps=10) as opened:
        yield opened


def lines(canvas: Canvas) -> list[str]:
    canvas.clock.step()
    return canvas.screen.render().split('\n')


class TestColor:
    def test_a_slot_is_live_and_value_is_a_plain_copy(self, canvas):
        label = canvas.screen.write('hi', background='#336699')
        slot = label.color.bg
        assert isinstance(label.color, Colors) and isinstance(slot, ColorSlot)
        before = slot.value
        assert before == Color('#336699')
        assert slot.darken(0.2) is None
        assert slot.value != before
        copy = slot.value.darken(0.5)
        assert copy != slot.value, 'darkening the value returns a new color'
        slot.lighten(0.2)
        assert slot.value is not None

    def test_a_slot_without_a_color_cannot_be_darkened(self, canvas):
        label = canvas.screen.write('hi')
        with pytest.raises(TerminalError, match='not set'):
            label.color.fg.darken(0.1)
        assert label.color.fg.value is None

    def test_colors_are_assigned_by_name_tuple_color_or_slot(self, canvas):
        label = canvas.screen.write('hi')
        label.color.fg = 'red'
        assert label.color.fg.value == Color('red')
        label.color.bg = (0, 0, 80)
        assert label.color.bg.value.to_rgb() == (0, 0, 80)
        label.color.bg = Color('#102030')
        assert label.color.bg.value.to_rgb() == (16, 32, 48)
        other = canvas.screen.write('o')
        other.color.fg = label.color.fg
        label.color.fg = 'blue'
        assert other.color.fg.value == Color('red'), 'a slot is copied, never aliased'

    def test_reset_clears_a_color(self, canvas):
        label = canvas.screen.write('hi', foreground='red')
        label.color.fg = 'reset'
        assert label.color.fg.value is None

    def test_none_is_refused_and_the_message_teaches(self, canvas):
        canvas.screen.color.bg = 'blue'
        other = canvas.screen.write('o')
        other.color.bg = 'red'
        with pytest.raises(TypeError, match=r'darken\(\) changes the color in place'):
            other.color.bg = canvas.screen.color.bg.darken(0.1)  # type: ignore[assignment]
        assert other.color.bg.value == Color('red'), 'the other owner is unchanged'
        assert canvas.screen.color.bg.value != Color('blue'), 'darken already ran'
        with pytest.raises(TypeError, match='Assign False'):
            other.border = None  # type: ignore[assignment]

    def test_the_border_color_is_a_slot_too(self, canvas):
        label = canvas.screen.write('hi', border='plain')
        label.border.color = 'cyan'
        assert label.border.color.value == Color('cyan')
        label.border.color.darken(0.2)
        assert label.border.color.value != Color('cyan')

    def test_shade_colors_every_cell_in_one_write(self, canvas):
        canvas.screen.color.bg.shade(lambda x, y: (x * 10, y * 20, 0))
        assert canvas.screen.region[3, 2].background.to_rgb() == (30, 40, 0)
        card = canvas.screen.write(Buffer(width=3, height=2))
        card.color.shade(lambda x, y: (200, 0, 0) if x == 1 else None)
        assert card.region[1, 1].background.to_rgb() == (200, 0, 0)

    def test_the_text_color_can_be_shaded(self, canvas):
        label = canvas.screen.write('abc')
        label.color.fg.shade(lambda x, y: (x * 50, 0, 0))
        assert label.region[2, 0].foreground.to_rgb() == (100, 0, 0)
        assert label.region[2, 0].character == 'c'

    def test_color_applies_to_content_that_is_not_text(self, canvas):
        block = canvas.screen.write(Buffer(width=3, height=1), background='red')
        canvas.clock.step()
        assert block.region[1, 0].background == Color('red')
        block.color.bg = 'blue'
        canvas.clock.step()
        assert block.region[1, 0].background == Color('blue')


class TestBorder:
    def test_a_border_kind_and_false(self, canvas):
        card = canvas.screen.write('hi', border='rounded')
        assert card.border.kind == 'rounded' and card.border
        assert lines(canvas)[:3] == ['╭──╮', '│hi│', '╰──╯']
        card.border = 'double'
        assert lines(canvas)[0] == '╔══╗'
        card.border = True
        assert card.border.kind == 'plain'
        card.border = False
        assert not card.border and card.border.kind is None
        assert (card.width, card.height) == (2, 1)

    def test_a_kind_that_does_not_exist_is_explained(self, canvas):
        card = canvas.screen.write('hi')
        with pytest.raises(ValueError, match='"plain", "rounded", "double" or "thick"'):
            card.border = 'dotted'  # type: ignore[assignment]
        with pytest.raises(ValueError, match='is not a border kind'):
            card.border.top = 'wavy'  # type: ignore[assignment]

    def test_each_side_has_its_own_kind_and_color(self, canvas):
        card = canvas.screen.write('hi', border='plain')
        card.border.top = 'double'
        card.border.left = False
        card.border.bottom.color = 'red'
        assert card.border.top.kind == 'double'
        assert card.border.left.kind is None
        assert card.border.bottom.color == Color('red')
        assert card.border.right.kind == 'plain'
        assert (card.width, card.height) == (3, 3)
        assert lines(canvas)[:3] == ['══╗', 'hi│', '──┘']
        card.border.left = True
        assert lines(canvas)[:3] == ['╔══╗', '│hi│', '└──┘']
        card.border = 'rounded'
        assert card.border.top.kind == 'rounded', (
            'assigning the whole border resets the sides'
        )

    def test_an_override_that_says_nothing_new_is_forgotten(self, canvas):
        card = canvas.screen.write('hi', border='plain')
        card.border.top = 'plain'
        card.border.right.color = None
        assert card._appearance.sides == {}
        assert card._decorated is None

    def test_a_title_is_written_on_the_top_edge(self, canvas):
        card = canvas.screen.write('hello', border='plain')
        card.border.title = 'Box'
        assert lines(canvas)[0] == '┌Box──┐'
        card.border.title = None
        assert lines(canvas)[0] == '┌─────┐'

    def test_a_border_works_on_a_buffer(self, canvas):
        block = canvas.screen.write(Buffer(width=4, height=2), border='rounded')
        assert (block.width, block.height) == (6, 4)
        assert lines(canvas)[0] == '╭────╮'
        assert block.region.width == 4, 'the region is the area inside the border'
        block.border = False
        assert (block.width, block.height) == (4, 2)

    def test_a_border_works_on_a_widget_written_with_it(self, canvas):
        gauge = canvas.screen.write(
            xnano_core.Gauge(ratio=0.5, width=10, height=1), border='thick'
        )
        assert lines(canvas)[0] == '┏━━━━━━━━━━┓'
        gauge.border = 'plain'
        assert lines(canvas)[0] == '┌──────────┐'

    def test_a_widget_takes_a_border_after_it_was_written(self, canvas):
        gauge = canvas.screen.write(
            xnano_core.Gauge(ratio=0.5, width=10, height=1), x=2, y=1
        )
        hits: list[int] = []

        @gauge.hook(on="mouse.kind == 'press'")
        def hear(context: Context) -> None:
            hits.append(1)

        before = gauge
        gauge.border = 'thick'
        gauge.padding = {'horizontal': 1}
        canvas.clock.step()
        assert gauge is before
        assert (gauge.x, gauge.y, gauge.width, gauge.height) == (2, 1, 14, 3)
        shown = lines(canvas)
        assert shown[1][2:16] == '┏━━━━━━━━━━━━┓'
        assert '50%' in shown[2]
        canvas.push(Event.mouse_event(column=2, row=1, kind='press', button='left'))
        canvas.deliver_events()
        assert hits == [1], 'the hook still hears clicks after the widget moved inside'
        gauge.border = False
        gauge.padding = 0
        canvas.clock.step()
        assert (gauge.width, gauge.height) == (10, 1)
        assert '50%' in lines(canvas)[1], 'the widget keeps drawing itself'

    def test_an_image_takes_a_border_after_it_was_written(self, canvas):
        from xnano_image import TerminalImage

        pixels = bytes([1, 2, 3, 255]) * 16
        picture = canvas.screen.write(
            xnano.Image(TerminalImage.from_rgba(4, 4, pixels), width=4)
        )
        width, height = picture.width, picture.height
        picture.border = 'plain'
        canvas.clock.step()
        assert (picture.width, picture.height) == (width + 2, height + 2)
        assert lines(canvas)[0].startswith('┌')

    def test_a_late_border_keeps_the_stacking_order_of_the_siblings(self, canvas):
        first = canvas.screen.write(xnano_core.Gauge(ratio=0.5, width=6, height=1))
        second = canvas.screen.write('top', x=0, y=0)
        first.border = 'plain'
        canvas.clock.step()
        assert canvas.screen.core_buffer.children[-1] is second.core_buffer
        assert canvas.screen.core_buffer.children[-2] is first._buffer

    def test_a_widget_without_a_size_fits_the_parent_with_its_border(self):
        with new(width=20, height=8) as sized:
            paragraph = sized.screen.write(xnano_core.Paragraph('abc'), border='double')
            sized.clock.step()
            assert paragraph.width == 20
            shown = sized.screen.render().split('\n')
            assert shown[0] == '╔' + '═' * 18 + '╗'
            assert shown[4].endswith('╝')
            late = sized.screen.write(xnano_core.Paragraph('abc'), y=4)
            late.border = 'double'
            sized.clock.step()
            assert late.width == 20
            assert sized.screen.render().split('\n')[4].endswith('╗')

    def test_a_border_works_on_a_region_and_nested_regions(self, canvas):
        frame = xnano.box(6, 3)
        placement = canvas.screen.write(frame, border='double')
        assert (placement.width, placement.height) == (6, 3)
        assert lines(canvas)[0] == '╔════╗'

    def test_a_border_replaces_the_border_of_a_box_instead_of_surrounding_it(
        self, canvas
    ):
        placement = canvas.screen.write(xnano.box(6, 3, border='plain'), border='double')
        assert (placement.width, placement.height) == (6, 3)
        assert lines(canvas)[:3] == ['╔════╗', '║    ║', '╚════╝']

    def test_a_nested_canvas_takes_the_look_it_is_written_with(self, canvas):
        inner = new(width=6, height=2)
        inner.screen.write('zz')
        framed = canvas.screen.write(inner, border='plain')
        assert (framed.width, framed.height) == (8, 4)
        assert lines(canvas)[:2] == ['┌──────┐', '│zz    │']
        second = new(width=6, height=2)
        padded = canvas.screen.write(second, y=5, padding=2, foreground='red')
        canvas.clock.step()
        assert (padded.width, padded.height) == (10, 6)
        assert padded.color.fg.value == Color('red')

    def test_the_text_modifiers_and_style_are_properties_of_a_placement(self, canvas):
        label = canvas.screen.write('x')
        assert label.is_bold is False and label.style is None
        label.is_bold = True
        label.is_underlined = True
        label.style = xnano_core.Style(foreground='red')
        canvas.clock.step()
        assert label.is_bold and label.is_underlined
        assert label.core_buffer[0, 0].foreground == Color('red')
        assert 'bold' in label.core_buffer[0, 0].style.modifiers
        label.is_bold = False
        canvas.clock.step()
        assert 'bold' not in label.core_buffer[0, 0].style.modifiers

    def test_the_text_modifiers_style_content_that_is_not_text(self, canvas):
        block = canvas.screen.write(Buffer(width=2, height=1))
        block.is_italic = True
        canvas.clock.step()
        assert 'italic' in block.core_buffer[0, 0].style.modifiers

    @pytest.mark.parametrize(
        ('keyword', 'field'),
        [
            ('bold', 'is_bold'),
            ('dim', 'is_dim'),
            ('italic', 'is_italic'),
            ('underline', 'is_underlined'),
            ('blink', 'is_blinking'),
            ('reverse', 'is_reversed'),
            ('hidden', 'is_hidden'),
            ('crossed_out', 'is_crossed_out'),
        ],
    )
    def test_each_text_modifier_is_a_keyword_a_property_and_a_method(
        self, canvas, keyword, field
    ):
        written = canvas.screen.write('x', **{keyword: True})
        assert getattr(written, field) is True
        chained = canvas.screen.write('y', x=2)
        assert getattr(chained, keyword)() is chained
        canvas.clock.step()
        assert getattr(chained, field) is True
        assert keyword in chained.core_buffer[0, 0].style.modifiers
        getattr(chained, keyword)(False)
        canvas.clock.step()
        assert getattr(chained, field) is False
        assert keyword not in chained.core_buffer[0, 0].style.modifiers

    def test_a_canvas_takes_the_text_modifiers_as_settings_and_properties(self):
        with new(width=4, height=1, bold=True) as styled:
            assert styled.screen.is_bold
            assert styled.screen.italic().blink() is styled.screen
            assert styled.screen.is_italic and styled.screen.is_blinking
            styled.screen.is_bold = False
            assert not styled.screen.is_bold

    def test_a_text_modifier_method_refuses_a_value_that_is_not_a_boolean(self, canvas):
        label = canvas.screen.write('x')
        with pytest.raises(TypeError, match='is_bold must be True or False'):
            label.bold('yes')  # type: ignore[arg-type]
        assert label.is_bold is False

    def test_the_old_modifier_keywords_are_refused(self, canvas):
        with pytest.raises(TypeError):
            canvas.screen.write('x', is_bold=True)  # type: ignore[call-arg]
        with pytest.raises(TypeError, match="no setting called 'is_bold'"):
            new(width=4, height=1, is_bold=True)  # type: ignore[call-overload]

    def test_a_color_slot_can_be_set_to_a_random_color_or_shade(self, canvas):
        import random

        label = canvas.screen.write('hi')
        random.seed(3)
        chosen = label.color.fg.random()
        random.seed(3)
        assert chosen == Color.random()
        assert label.color.fg.value == chosen
        shade = label.color.bg.random('blue')
        assert label.color.bg.value == shade
        assert round(shade.to_hsl()[0]) == round(Color('blue').to_hsl()[0])
        canvas.clock.step()
        assert label.core_buffer[0, 0].foreground == chosen
        boxed = canvas.screen.write('box', y=2, border='plain')
        border = boxed.border.color.random('#ff8800')
        assert boxed.border.color.value == border

    def test_a_border_is_refused_on_a_closed_canvas(self):
        with new(width=6, height=3) as opened:
            label = opened.screen.write('hi')
        with pytest.raises(TerminalError):
            label.border = 'plain'

    def test_a_text_placement_with_a_uniform_border_is_one_buffer(self, canvas):
        card = canvas.screen.write('hi', border='rounded', padding=1, margin=1)
        assert card._decorated is None
        assert (card.width, card.height) == (8, 7)
        card.border.color = 'red'
        card.color.fg = 'green'
        canvas.clock.step()
        assert card._decorated is None

    def test_a_side_override_or_a_nested_placement_makes_two_buffers(self, canvas):
        card = canvas.screen.write('hi', border='plain')
        card.border.top = 'double'
        canvas.clock.step()
        assert card._decorated is not None
        card.border = 'plain'
        canvas.clock.step()
        assert card._decorated is None
        nested = card.write('inner', x=0, y=0)
        canvas.clock.step()
        assert card._decorated is not None
        nested.remove()
        card.border = False
        assert (card.width, card.height) == (2, 1)

    def test_nested_content_lands_inside_the_border(self, canvas):
        card = canvas.screen.write('hello', border='plain', x=2, y=1)
        child = card.write('ab', x=1, y=0)
        canvas.clock.step()
        assert lines(canvas)[2][2:] == '│hablo│'
        assert child.x == 1
        card.border = False
        assert (card.width, card.height) == (5, 1)
        assert lines(canvas)[1][2:7] == 'hablo'

    def test_a_hook_hears_clicks_on_the_border_and_the_content(self, canvas):
        card = canvas.screen.write(Buffer(width=4, height=2), x=2, y=2)
        hits: list[tuple[int, int]] = []

        @card.hook(on="mouse.kind == 'press'")
        def hear(context: Context) -> None:
            hits.append((context.mouse.position.x, context.mouse.position.y))

        card.border = 'plain'
        canvas.clock.step()
        for column, row in ((2, 2), (4, 3)):
            canvas.push(
                Event.mouse_event(column=column, row=row, kind='press', button='left')
            )
            canvas.deliver_events()
        assert hits == [(2, 2), (4, 3)]

    def test_removing_a_decorated_placement_removes_its_buffers(self, canvas):
        card = canvas.screen.write(Buffer(width=3, height=1), border='plain')
        card.remove()
        assert '┌' not in lines(canvas)[0]


class TestSpacing:
    def test_padding_is_set_per_edge_or_all_at_once(self, canvas):
        label = canvas.screen.write('hi', border='plain')
        label.padding = 1
        assert (label.width, label.height) == (6, 5)
        label.padding.left = 3
        assert (label.padding.left, label.padding.right) == (3, 1)
        assert label.width == 8
        label.padding = {'vertical': 1, 'horizontal': 2}
        assert (label.padding.top, label.padding.left) == (1, 2)
        label.padding = {'top': 2}
        assert (label.padding.top, label.padding.left, label.padding.bottom) == (2, 0, 0)

    def test_margin_is_a_transparent_ring_outside_the_border(self, canvas):
        label = canvas.screen.write('hi', border='plain', margin={'left': 2, 'top': 1})
        assert (label.width, label.height) == (6, 4)
        shown = lines(canvas)
        assert shown[0].strip() == ''
        assert shown[1] == '  ┌──┐'

    def test_percentages_are_shares_of_the_content(self, canvas):
        label = canvas.screen.write('abcdefgh', padding='25%')
        assert label.padding.left == 2
        assert label.width == 12
        label.padding.top = '100%'
        assert label.padding.top == 1

    def test_padding_takes_the_background_color(self, canvas):
        label = canvas.screen.write('x', background='red', padding=1)
        canvas.clock.step()
        assert label.region.width == 1
        assert label.core_buffer[0, 0].background == Color('red')

    def test_none_and_bad_values_are_refused(self, canvas):
        label = canvas.screen.write('x')
        with pytest.raises(TypeError, match='cannot be None'):
            label.padding = None  # type: ignore[assignment]
        with pytest.raises(TypeError, match='cannot be None'):
            label.margin = None  # type: ignore[assignment]

    def test_none_for_spacing_teaches_zero(self, canvas):
        label = canvas.screen.write('x')
        with pytest.raises(TypeError, match='Assign 0 to remove it'):
            label.padding = None  # type: ignore[assignment]
        with pytest.raises(TypeError, match='Assign 0 to remove it'):
            label.margin = None  # type: ignore[assignment]


class TestDrawnOnceAPerFrame:
    def test_several_assignments_draw_once(self, canvas, monkeypatch):
        label = canvas.screen.write('hi')
        redraws: list[int] = []
        original = Placement._redraw_look

        def spy(self: Placement) -> None:
            redraws.append(1)
            original(self)

        monkeypatch.setattr(Placement, '_redraw_look', spy)
        label.border = 'rounded'
        label.padding = 1
        label.color.fg = 'red'
        label.color.bg = 'blue'
        label.border.title = 'x'
        assert redraws == []
        canvas.clock.step()
        assert len(redraws) == 1
        canvas.clock.step()
        assert len(redraws) == 1, 'nothing changed, so nothing is drawn again'

    def test_reading_the_size_draws_first(self, canvas):
        label = canvas.screen.write('hi')
        label.border = 'plain'
        label.padding = 1
        assert (label.width, label.height) == (6, 5)

    def test_the_text_is_immediate(self, canvas):
        label = canvas.screen.write('hi', border='plain')
        label.text = 'hello'
        assert label.width == 7
        assert label.text == 'hello'

    def test_a_dirty_look_asks_for_a_frame_and_then_lets_go(self, canvas):
        label = canvas.screen.write('hi')
        label.border = 'plain'
        assert canvas._dirty_looks
        canvas.clock.step()
        assert not canvas._dirty_looks


class TestRootCanvas:
    def test_a_canvas_border_pads_and_holds_the_content(self):
        with new(width=10, height=5, border='rounded', padding={'horizontal': 1}) as root:
            root.screen.write('hi')
            shown = lines(root)
            assert shown[0] == '╭────────╮'
            assert shown[1] == '│ hi     │'
            assert (root.screen.width, root.screen.height) == (10, 5)
            assert root.screen.border.kind == 'rounded'

    def test_assigning_a_border_later_promotes_and_false_demotes(self):
        with new(width=8, height=4) as root:
            label = root.screen.write('hi')
            root.screen.border = 'plain'
            assert lines(root)[0] == '┌──────┐'
            assert lines(root)[1] == '│hi    │'
            root.screen.border = False
            assert lines(root)[0] == 'hi'
            assert label.x == 0

    def test_the_canvas_colors_fill_the_cells_behind_the_content(self):
        with new(width=6, height=2, background='#001122') as root:
            root.screen.write('hi')
            root.clock.step()
            assert root.screen.region[5, 1].background == Color('#001122')

    def test_canvas_margin_is_transparent(self):
        with new(width=8, height=4, margin={'left': 2}) as root:
            root.screen.write('hi')
            assert lines(root)[0] == '  hi'
            assert root.screen.margin.left == 2


def test_foreground_shade_colors_the_text_and_keeps_the_rest():
    with xnano.new(width=4, height=2) as canvas:
        canvas.screen.region[0:3, 0:1] = 'abc'
        canvas.screen.color.bg = 'blue'
        canvas.screen.color.fg.shade(lambda x, y: (x * 50, 0, 0) if x < 3 else None)
        cell = canvas.screen.region[1, 0]
        assert cell.character == 'b'
        assert cell.foreground.to_rgb() == (50, 0, 0)
        assert cell.background == Color('blue')
        assert canvas.screen.region[3, 0].foreground is None


def test_the_appearance_objects_are_in_the_documentation_examples():
    with xnano.new(width=10, height=3) as canvas:
        label = canvas.screen.write('hi')
        label.color.fg = 'red'
        label.color.bg = (0, 0, 80)
        label.color.bg.lighten(0.1)
        assert label.color.fg.value == xnano.Color('red')


class TestAssignmentsAreChecked:
    """A bad value raises at the assignment and leaves the look as it was."""

    @pytest.fixture
    def card(self, canvas):
        placement = canvas.screen.write(
            'hi', border='plain', padding=1, foreground='green'
        )
        placement.border.title = 'Menu'
        canvas.clock.step()
        return placement

    @pytest.mark.parametrize(
        ('setter', 'error', 'match'),
        [
            (lambda p: setattr(p.color, 'fg', 'nocolor'), ValueError, 'color.fg'),
            (lambda p: setattr(p.color, 'bg', 300), TypeError, 'color.bg'),
            (lambda p: setattr(p.color, 'bg', (1, 2, 300)), ValueError, 'out of range'),
            (lambda p: setattr(p.border, 'color', 'nocolor'), ValueError, 'border.color'),
            (
                lambda p: setattr(p.border.top, 'color', 'nocolor'),
                ValueError,
                'top.color',
            ),
            (lambda p: setattr(p, 'padding', 'abc'), TypeError, 'padding'),
            (lambda p: setattr(p, 'margin', {'diagonal': 1}), ValueError, 'diagonal'),
            (lambda p: setattr(p.padding, 'left', 'abc'), TypeError, 'padding'),
            (lambda p: setattr(p.margin, 'top', True), TypeError, 'margin'),
            (lambda p: setattr(p.border, 'title', 5), TypeError, 'title'),
            (lambda p: setattr(p.border, 'kind', 'wavy'), ValueError, 'border kind'),
        ],
    )
    def test_a_bad_value_raises_at_the_assignment(
        self, canvas, card, setter, error, match
    ):
        before = (
            card.color.fg.value,
            card.color.bg.value,
            card.border.color.value,
            card.border.top.color,
            card.border.title,
            card.border.kind,
            repr(card.padding),
            repr(card.margin),
        )
        with pytest.raises(error, match=match):
            setter(card)
        after = (
            card.color.fg.value,
            card.color.bg.value,
            card.border.color.value,
            card.border.top.color,
            card.border.title,
            card.border.kind,
            repr(card.padding),
            repr(card.margin),
        )
        assert after == before
        canvas.clock.step()


def test_clearing_a_color_on_a_root_canvas_undoes_the_paint():
    with xnano.new(width=6, height=3) as canvas:
        canvas.screen.color.bg = 'blue'
        assert canvas.screen.region[2, 2].background == Color('blue')
        canvas.screen.color.bg = 'reset'
        assert canvas.screen.color.bg.value is None
        assert canvas.screen.region[2, 2].background in (None, Color('reset'))
        canvas.screen.color.fg = 'red'
        canvas.screen.color.fg = 'reset'
        canvas.screen.region[0, 0] = 'x'
        assert canvas.screen.region[0, 0].foreground in (None, Color('reset'))


def test_the_border_color_cannot_be_shaded():
    with xnano.new(width=8, height=4) as canvas:
        card = canvas.screen.write('hi', border='plain')
        with pytest.raises(TerminalError, match='one color'):
            card.border.color.shade(lambda x, y: (255, 0, 0))
        canvas.clock.step()
        assert card.region[0, 0].background is None


def test_clearing_a_color_inside_a_canvas_border_undoes_the_paint():
    with xnano.new(width=8, height=4) as canvas:
        canvas.screen.color.bg = 'blue'
        canvas.screen.border = 'plain'
        canvas.clock.step()
        canvas.screen.color.bg = 'reset'
        canvas.clock.step()
        assert canvas.screen.region[2, 1].background in (None, Color('reset'))


def test_removing_the_border_of_a_canvas_keeps_its_size():
    with xnano.new(width=8, height=4) as canvas:
        canvas.screen.write('hi')
        canvas.screen.border = 'plain'
        canvas.clock.step()
        assert (canvas.screen.region.width, canvas.screen.region.height) == (6, 2)
        canvas.screen.border = False
        canvas.clock.step()
        assert (canvas.screen.region.width, canvas.screen.region.height) == (8, 4)
        assert canvas.screen.render().split('\n')[0] == 'hi'


class TestColorSlotHints:
    def test_the_hint_names_the_slot_that_has_no_color(self, canvas):
        label = canvas.screen.write('hi', border='plain')
        with pytest.raises(TerminalError, match=r'color\.fg = "red"'):
            label.color.fg.darken(0.1)
        with pytest.raises(TerminalError, match=r'color\.bg = "red"'):
            label.color.bg.darken(0.1)
        with pytest.raises(TerminalError, match=r'border\.color = "red"'):
            ColorSlot(label, 'border').darken(0.1)


@pytest.mark.parametrize(('name', 'slot'), [('foreground', 'fg'), ('background', 'bg')])
def test_a_long_color_name_points_to_its_slot(name: str, slot: str) -> None:
    with xnano.new(width=8, height=1) as canvas:
        label = canvas.screen.write('hi')
        with pytest.raises(AttributeError, match=f'write color.{slot} = '):
            setattr(label.color, name, 'red')
        with pytest.raises(AttributeError, match=f"color has no '{name}'"):
            getattr(label.color, name)
