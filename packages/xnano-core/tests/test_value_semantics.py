"""Value types compare and hash by value; mutable types compare but never hash."""

from __future__ import annotations

import copy

import pytest

from xnano_core._xnano_core import (
    Cell,
    Color,
    Drawing,
    KeyBinding,
    Margin,
    Offset,
    Point,
    Rectangle,
    Size,
    SizeRule,
    Style,
    StyledText,
    TextEditor,
    TextSpan,
)

VALUE_TYPES = {
    'Point': (lambda: Point(1, 2), lambda: Point(2, 1)),
    'Size': (lambda: Size(3, 4), lambda: Size(4, 3)),
    'Rectangle': (lambda: Rectangle(1, 2, 3, 4), lambda: Rectangle(1, 2, 4, 3)),
    'Offset': (lambda: Offset(1, -2), lambda: Offset(-1, 2)),
    'Margin': (lambda: Margin(1, 2), lambda: Margin(2, 1)),
    'Color': (lambda: Color('red'), lambda: Color('#ff8800')),
    'Style': (
        lambda: Style('red', 'black', bold=True, underline_color='blue'),
        lambda: Style('red', 'black', bold=True),
    ),
    'TextSpan': (
        lambda: TextSpan('hi', style=Style('red')),
        lambda: TextSpan('hi'),
    ),
    'StyledText': (
        lambda: StyledText([TextSpan('a'), TextSpan('b', style=Style('red'))]),
        lambda: StyledText([TextSpan('a')]),
    ),
    'KeyBinding': (lambda: KeyBinding.parse('ctrl+c'), lambda: KeyBinding.parse('c')),
    'SizeRule': (lambda: SizeRule.cells(3), lambda: SizeRule.cells(4)),
}

COMPARABLE_ONLY = {
    'Cell': (lambda: Cell('x'), lambda: Cell('y')),
    'Drawing': (lambda: Drawing(['ab']), lambda: Drawing(['ba'])),
    'TextEditor': (lambda: TextEditor('hello'), lambda: TextEditor('world')),
}

COPYABLE = {**VALUE_TYPES, 'TextEditor': COMPARABLE_ONLY['TextEditor']}


@pytest.mark.parametrize('name', sorted(VALUE_TYPES))
def test_value_types_compare_by_value(name):
    make, other = VALUE_TYPES[name]
    assert make() == make()
    assert make() != other()
    for foreign in (None, 0, '', 'text', 1.5, (), object()):
        assert make() != foreign


@pytest.mark.parametrize('name', sorted(VALUE_TYPES))
def test_value_types_hash_by_value_and_work_as_keys(name):
    make, other = VALUE_TYPES[name]
    assert hash(make()) == hash(make())
    table = {make(): 'first'}
    assert table[make()] == 'first' and other() not in table
    assert len({make(), make(), other()}) == 2


@pytest.mark.parametrize('name', sorted(COMPARABLE_ONLY))
def test_mutable_types_compare_by_value_but_do_not_hash(name):
    make, other = COMPARABLE_ONLY[name]
    assert make() == make() and make() != other()
    with pytest.raises(TypeError):
        hash(make())


@pytest.mark.parametrize('name', sorted(COPYABLE))
def test_copies_are_equal_and_of_the_same_type(name):
    make, _ = COPYABLE[name]
    original = make()
    for clone in (copy.copy(original), copy.deepcopy(original)):
        assert clone == original and type(clone) is type(original)
        assert repr(clone) == repr(original)


@pytest.mark.parametrize('name', sorted({**VALUE_TYPES, **COMPARABLE_ONLY}))
def test_every_repr_names_its_class(name):
    make, _ = {**VALUE_TYPES, **COMPARABLE_ONLY}[name]
    assert type(make()).__name__ in repr(make())


def test_a_copied_editor_is_independent():
    original = TextEditor('ab')
    clone = copy.copy(original)
    clone.insert_text('c')
    assert original.text == 'ab' and clone.text == 'abc'


def test_geometry_arithmetic_and_sequences():
    assert Point(1, 2) + Offset(1, 1) == Point(2, 3)
    assert Point(1, 2) - Point(1, 1) == Point(0, 1)
    assert -Point(1, -2) == Point(-1, 2) and Point(1, 2) * 2 == Point(2, 4)
    assert Point(1, 2).offset_to(Point(4, 6)) == Offset(3, 4)
    assert Offset(1, 2) + Offset(1, 1) == Offset(2, 3) and -Offset(1, 2) == Offset(-1, -2)
    assert Size(3, 2) + Size(1, 1) == Size(4, 3) and Size(3, 2) - Size(5, 1) == Size(0, 1)
    assert Size(3, 2) * 2 == Size(6, 4) and Size(3, 2).area == 6
    assert not Size(0, 3) and bool(Size(1, 1)) and Size(0, 3).is_empty
    assert tuple(Point(1, 2)) == (1, 2) and Point(1, 2)[-1] == 2 and len(Point()) == 2
    assert tuple(Rectangle(1, 2, 3, 4)) == (1, 2, 3, 4) and len(Rectangle()) == 4
    with pytest.raises(IndexError, match='outside'):
        Point(1, 2)[2]
    with pytest.raises(ValueError, match='margin'):
        Margin(-1, 0)
    with pytest.raises(ValueError, match='multiplier'):
        Size(1, 1) * -1


def test_rectangle_helpers():
    area = Rectangle(2, 3, 10, 4)
    assert (area.left, area.top, area.right, area.bottom) == (2, 3, 12, 7)
    assert area.offset(Offset(1, -1)) == Rectangle(3, 2, 10, 4)
    assert area.resize(Size(2, 2)) == Rectangle(2, 3, 2, 2)
    assert area.centered(4, 2) == Rectangle(5, 4, 4, 2)
    assert area.centered_horizontally(4) == Rectangle(5, 3, 4, 4)
    assert area.centered_vertically(2) == Rectangle(2, 4, 10, 2)
    assert area.inner_area(Margin(1, 1)) == Rectangle(3, 4, 8, 2)
    assert area.outer(Margin(1, 1)) == Rectangle(1, 2, 12, 6)
    assert [row.y for row in area.rows()] == [3, 4, 5, 6]
    assert len(area.columns()) == 10 and area.columns()[0] == Rectangle(2, 3, 1, 4)
    assert Rectangle(0, 0, 20, 20).clamp(Rectangle(5, 5, 4, 4)) == Rectangle(5, 5, 4, 4)
    assert Rectangle(8, 8, 3, 3).clamp(Rectangle(0, 0, 10, 10)) == Rectangle(7, 7, 3, 3)
    assert Point(3, 4) in area and Point(0, 0) not in area
    assert (area & Rectangle(0, 0, 5, 5)) == area.intersection(Rectangle(0, 0, 5, 5))
    assert (area | Rectangle(0, 0, 1, 1)) == area.union(Rectangle(0, 0, 1, 1))


def test_rectangle_translate_takes_x_and_y_and_inset_keeps_the_layout_names():
    area = Rectangle(5, 5, 4, 2)
    assert area.translate(2, 1) == Rectangle(7, 6, 4, 2)
    assert area.translate(x=-1, y=-2) == Rectangle(4, 3, 4, 2)
    assert area.translate(y=1) == Rectangle(5, 6, 4, 2)
    assert area.translate() == area
    with pytest.raises(TypeError):
        area.translate(horizontal=1)
    assert Rectangle(0, 0, 10, 5).inset(horizontal=1, vertical=1) == Rectangle(1, 1, 8, 3)


def test_color_constants_and_conversions():
    assert Color.red == Color('red') and Color.dark_gray == Color('dark_gray')
    assert Color.reset.is_reset and not Color.red.is_reset
    hue, saturation, lightness = Color('#ff0000').to_hsl()
    assert (round(hue), round(saturation), round(lightness)) == (0, 100, 50)
    assert Color.from_hsl(0, 100, 50).to_rgb() == (255, 0, 0)
    assert Color.from_hsv(120, 100, 100).to_rgb() == (0, 255, 0)
    assert Color('#000000').lerp('#ffffff', 1.0) == Color('#ffffff')
    assert Color('#000000').lerp('#ffffff', 0.0) == Color('#000000')
    assert Color('#808080').lighten(1.0).to_rgb() == (255, 255, 255)
    with pytest.raises(ValueError, match='reset'):
        Color.reset.to_hsl()
    with pytest.raises(ValueError, match='color space'):
        Color.red.lerp('blue', 0.5, color_space='lab')
    with pytest.raises(ValueError, match='hue'):
        Color.from_hsl(400, 0, 0)


def test_darken_moves_toward_black_and_rejects_amounts_outside_zero_to_one():
    base = Color('#336699')
    assert base.darken(0.0) == base
    assert Color('#808080').darken(1.0).to_rgb() == (0, 0, 0)
    assert base.darken(0.2).to_hsl()[2] < base.to_hsl()[2]
    assert base.darken(0.2) == base.lighten(-0.2)
    for color_space in ('rgb', 'hsl', 'hsv'):
        assert base.darken(0.3, color_space=color_space) == base.lighten(
            -0.3, color_space=color_space
        )
    assert Color('red').darken(0.5).to_hsl()[2] < Color('red').to_hsl()[2]
    with pytest.raises(ValueError, match='lighten'):
        base.darken(-0.1)
    with pytest.raises(ValueError, match='0.0 to 1.0'):
        base.darken(1.5)
    with pytest.raises(ValueError, match='0.0 to 1.0'):
        base.darken(float('nan'))
    with pytest.raises(ValueError, match='reset'):
        Color.reset.darken(0.5)
    with pytest.raises(ValueError, match='color space'):
        base.darken(0.5, color_space='lab')


def test_inverse_flips_every_channel_and_inverting_twice_restores_the_color():
    assert Color('#ff8000').inverse().to_hex() == '#007fff'
    assert Color('#000000').inverse() == Color('#ffffff')
    assert Color('#336699').inverse().inverse() == Color('#336699')
    named = Color('red').inverse()
    assert named.to_hex() == '#7fffff'
    assert Color('red').to_rgb() is None, 'named colors have no fixed value of their own'
    assert Color('white').inverse() != Color('white')
    with pytest.raises(ValueError, match='cannot be inverted'):
        Color.reset.inverse()


def test_style_builders_and_modifiers():
    style = Style('red', rapid_blink=True, underline_color='blue')
    assert style.underline_color == Color('blue') and 'rapid_blink' in style.modifiers
    assert 'blink' not in style.modifiers
    assert style.with_foreground('green').foreground == Color('green')
    assert style.with_foreground(None).foreground is None
    assert style.with_background('black').background == Color('black')
    assert 'bold' in style.add_modifier('bold', 'italic').modifiers
    removed = Style().remove_modifier('bold')
    assert removed.removed_modifiers == frozenset({'bold'})
    assert removed != Style()
    assert (Style('red') | Style(background='blue')) == Style('red', 'blue')
    assert not Style() and Style(bold=True)
    assert Style.reset() != Style()
    with pytest.raises(ValueError, match='modifier'):
        style.add_modifier('sparkly')


def test_text_values():
    text = StyledText([TextSpan('ab'), TextSpan('c\nde')])
    assert text.text == 'abc\nde' and text.height == 2 and text.width == 3
    assert (text + 'f').text == 'abc\ndef'
    assert (text + TextSpan('g')).text == 'abc\ndeg'
    assert (text + text).text == 'abc\ndeabc\nde'
    assert text.patch_style(Style(bold=True)).spans[0].style == Style(bold=True)
    assert TextSpan('x', style=Style('red')) == TextSpan('x', style=Style('red'))
    assert not StyledText([TextSpan('')]) and text
    with pytest.raises(TypeError, match='cannot add'):
        text + 3  # pyright: ignore[reportOperatorIssue]


def test_text_editor_selection_and_cursor_style():
    editor = TextEditor('hello world')
    assert editor.selection is None and editor.selected_text == ''
    editor.select(0, 5)
    assert editor.selection == (0, 5) and editor.selected_text == 'hello'
    editor.replace_selection('bye')
    assert editor.text == 'bye world' and editor.selection is None
    editor.select_all()
    assert editor.delete_selection() and editor.text == ''
    assert not editor.delete_selection()
    editor.set_text('one two')
    editor.move_to_start()
    editor.move_word_right()
    assert editor.cursor_offset == 3
    editor.move_word_left()
    assert editor.cursor_offset == 0
    editor.move_to_line_end()
    assert editor.cursor_offset == 7
    editor.cursor_style = Style(background='red')
    assert editor.cursor_style == Style(background='red')


def test_text_editor_shift_arrows_extend_the_selection():
    from xnano_core._xnano_core import Event

    editor = TextEditor('abc')
    editor.move_to_start()
    editor.handle_key(Event.key_press('shift+right').key)
    editor.handle_key(Event.key_press('shift+right').key)
    assert editor.selection == (0, 2) and editor.selected_text == 'ab'
    editor.handle_key(Event.key_press('x').key)
    assert editor.text == 'xc'
    editor.select_all()
    editor.handle_key(Event.key_press('backspace').key)
    assert editor.text == ''
    editor.set_text('abc')
    editor.select_all()
    editor.handle_key(Event.key_press('left').key)
    assert editor.selection is None


def test_operation_classes_report_the_native_module():
    from xnano_core._xnano_core import Editor, Fill, Write

    for cls in (Write, Fill, Editor):
        assert cls.__module__ == 'xnano_core._xnano_core'
