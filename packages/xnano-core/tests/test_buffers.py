"""Buffers, regions and surfaces: content, geometry and compositing."""

from __future__ import annotations

import pytest
from helpers import rows

from xnano_core._xnano_core import (
    Background,
    Buffer,
    Cell,
    Clear,
    Color,
    Fill,
    Foreground,
    InvalidRegionError,
    Move,
    Paste,
    Place,
    Rectangle,
    Resize,
    Style,
    Write,
)


def test_buffer_sizes_itself_from_its_content():
    buffer = Buffer(['ab', 'cdef'])
    assert (buffer.width, buffer.height) == (4, 2)
    assert rows(buffer) == ['ab', 'cdef']


def test_explicit_size_wins_over_content():
    buffer = Buffer('hello', width=3, height=2)
    assert (buffer.width, buffer.height) == (3, 2)
    assert rows(buffer) == ['hel', '']


def test_oversized_buffers_are_refused_with_a_recovery_hint():
    with pytest.raises(ValueError, match='smaller width or height'):
        Buffer(width=65535, height=65535)
    with pytest.raises(ValueError, match='zero or more'):
        Buffer(width=-1, height=2)


def test_cells_are_detached_snapshots():
    buffer = Buffer('hi')
    cell = buffer[0, 0]
    assert cell.symbol == 'h'
    cell.symbol = 'X'
    assert buffer[0, 0].symbol == 'h'
    buffer[0, 0] = cell
    assert buffer[0, 0].symbol == 'X'


def test_cell_index_errors_name_the_axis_and_size():
    buffer = Buffer(width=3, height=2)
    with pytest.raises(IndexError, match='row'):
        buffer[0, 5]
    with pytest.raises(IndexError, match='column'):
        buffer[3, 0]
    assert buffer[-1, -1].symbol == ' '


def test_a_cell_holds_one_grapheme():
    with pytest.raises(ValueError, match='one character'):
        Cell('ab')
    assert Cell('世').symbol == '世'
    buffer = Buffer(width=4, height=1)
    with pytest.raises(ValueError):
        buffer[0, 0] = 'toolong'


def test_write_clips_by_display_columns_and_keeps_graphemes_whole():
    buffer = Buffer(width=5, height=1)
    buffer.update(Write('ab世界cd'))
    assert rows(buffer) == ['ab世']
    narrow = Buffer(width=3, height=1)
    narrow.update(Write('a世b'))
    assert rows(narrow) == ['a世']
    narrow.update(Write('世', x=2))
    assert rows(narrow) == ['a世'], (
        'a glyph that does not fit whole is dropped, not split'
    )


def test_overwriting_half_of_a_wide_glyph_repairs_it():
    buffer = Buffer(width=4, height=1)
    buffer.update(Write('世界'))
    buffer.update(Write('x', x=1))
    assert rows(buffer) == [' x界']
    buffer.update(Write('y', x=2))
    assert rows(buffer) == [' xy']


def test_write_modes_control_the_background():
    buffer = Buffer(width=3, height=1, style=Style(background='blue'))
    buffer.update(Write('a', mode='preserve_background'))
    assert str(buffer[0, 0].background) != str(buffer[2, 0].foreground)
    assert buffer[0, 0].style.background is not None
    buffer.update(Write('b', x=1, mode='replace'))
    assert buffer[1, 0].style.background is None


def test_style_operations():
    buffer = Buffer('ab')
    buffer.update(Foreground('red'), Background((1, 2, 3)))
    assert buffer[0, 0].style.foreground is not None
    assert buffer[1, 0].style.background.to_rgb() == (1, 2, 3)


def test_fill_and_clear():
    buffer = Buffer(width=3, height=2)
    buffer.update(Fill('#'))
    assert rows(buffer) == ['###', '###']
    buffer.update(Clear())
    assert rows(buffer) == ['', '']
    with pytest.raises(ValueError, match='one column'):
        buffer.fill('世')


def test_background_colors_are_set_in_one_batch():
    buffer = Buffer(['abc', 'def'])
    before = buffer.revision
    buffer.set_background_colors(
        ['red', None, (0, 0, 255), Color('#00ff00'), 'blue', None], width=3
    )
    assert buffer.revision == before + 1, 'one batch counts as one change'
    assert buffer[0, 0].background == Color('red')
    assert buffer[1, 0].background == Color.reset
    assert buffer[2, 0].background == Color('#0000ff')
    assert buffer[0, 1].background == Color('#00ff00')
    assert buffer[1, 1].background == Color('blue')
    assert buffer[2, 1].background == Color.reset
    assert rows(buffer) == ['abc', 'def'], 'symbols are kept'


def test_background_colors_keep_the_foreground_and_accept_an_offset_block():
    buffer = Buffer(['abcd', 'efgh'])
    buffer.update(Foreground('red'))
    buffer.set_background_colors(['white', 'black'], width=1, x=2, y=0)
    assert buffer[2, 0].background == Color('white')
    assert buffer[2, 1].background == Color('black')
    assert buffer[2, 0].foreground == Color('red')
    assert buffer[1, 0].background == Color.reset


def test_background_colors_of_a_region_use_local_coordinates():
    buffer = Buffer(['abcd', 'efgh', 'ijkl'])
    region = buffer[1:3, 1:3]
    region.set_background_colors(['red', 'green'], width=2)
    assert buffer[1, 1].background == Color('red')
    assert buffer[2, 1].background == Color('green')
    assert buffer[0, 1].background == Color.reset
    assert buffer[1, 2].background == Color.reset


def test_background_colors_refuse_a_block_that_does_not_fit_and_say_why():
    buffer = Buffer(['abc', 'def'])
    with pytest.raises(ValueError, match='width=2'):
        buffer.set_background_colors(['red', 'red', 'red'], width=2)
    with pytest.raises(ValueError, match='at least 1'):
        buffer.set_background_colors(['red'], width=0)
    with pytest.raises(ValueError, match='does not fit'):
        buffer.set_background_colors(['red', 'red'], width=2, x=2)
    with pytest.raises(ValueError, match='does not fit'):
        buffer.set_background_colors(['red', 'red', 'red'], width=1, y=0, x=-1)
    with pytest.raises(ValueError, match='does not fit'):
        buffer.set_background_colors(['red'] * 3, width=1, y=1)
    with pytest.raises(ValueError, match='color'):
        buffer.set_background_colors(['not a color'], width=1)
    with pytest.raises(TypeError, match='color'):
        buffer.set_background_colors([object()], width=1)
    with pytest.raises(TypeError, match='needs a sequence of colors'):
        buffer.set_background_colors(5, width=1)  # type: ignore[arg-type]
    assert buffer[0, 0].background == Color.reset, 'a refused call changes nothing'


def test_background_colors_refuse_offsets_too_large_to_add_without_overflow():
    buffer = Buffer(width=3, height=2)
    with pytest.raises(ValueError, match='does not fit'):
        buffer.set_background_colors(['red', 'red'], width=2, x=2**31 - 1)
    with pytest.raises(ValueError, match='does not fit'):
        buffer.set_background_colors(['red', 'red'], width=1, y=2**31 - 1)


def test_background_colors_ask_for_a_sequence_when_given_one_string():
    buffer = Buffer(width=3, height=1)
    with pytest.raises(TypeError, match='sequence of colors'):
        buffer.set_background_colors('red', width=1)
    assert buffer[0, 0].background == Color.reset


def test_regions_share_storage_and_use_local_indexes():
    buffer = Buffer(['abcd', 'efgh', 'ijkl'])
    region = buffer[1:3, 1:3]
    assert (region.width, region.height) == (2, 2)
    assert region[0, 0].symbol == 'f'
    region.update(Write('ZZ'))
    assert rows(buffer) == ['abcd', 'eZZh', 'ijkl']
    region.fill('.')
    assert rows(buffer) == ['abcd', 'e..h', 'i..l']


def test_regions_stay_valid_only_while_they_fit():
    buffer = Buffer(width=6, height=3)
    region = buffer.region(Rectangle(4, 0, 2, 2))
    assert region.is_valid
    buffer.update(Resize(3, 3))
    assert not region.is_valid
    with pytest.raises(InvalidRegionError, match='no longer fits'):
        region.update(Write('x'))
    copy = buffer.region(Rectangle(0, 0, 2, 2)).copy()
    assert isinstance(copy, Buffer) and copy.width == 2


def test_a_region_outside_its_buffer_is_refused_when_created():
    buffer = Buffer(width=3, height=3)
    with pytest.raises(ValueError, match='does not fit'):
        buffer.region(Rectangle(2, 2, 3, 3))


def test_resize_keeps_intersecting_content():
    buffer = Buffer(['abcd', 'efgh'])
    buffer.update(Resize(2, 3))
    assert (buffer.width, buffer.height) == (2, 3)
    assert rows(buffer) == ['ab', 'ef', '']
    buffer.width = 3
    assert buffer.width == 3 and rows(buffer)[0] == 'ab'


def test_move_and_place_update_the_position():
    buffer = Buffer(width=2, height=2)
    buffer.update(Place(3, 4), Move(1, -1))
    assert (buffer.x, buffer.y) == (4, 3)
    assert buffer.position.x == 4 and buffer.bounds.y == 3


def test_paste_copies_a_source_snapshot():
    source = Buffer('xy')
    target = Buffer(width=5, height=2)
    target.paste(source, x=1, y=1)
    assert rows(target) == ['', ' xy']
    operation = Paste(source, x=0)
    source.update(Write('QQ'))
    target.update(operation)
    assert rows(target)[0] == 'xy'


def test_children_composite_by_layer_then_attachment_order():
    parent = Buffer(width=6, height=1)
    low = Buffer('aaa', x=1)
    high = Buffer('b', x=2)
    parent.attach(low)
    parent.attach(high)
    assert rows(parent) == [' aba']
    high.layer = -1
    assert rows(parent) == [' aaa']


def test_transparent_children_skip_marked_cells_only():
    parent = Buffer('......')
    child = Buffer(width=3, height=1)
    child.update(Write('a c'))
    child[1, 0] = Cell(' ', is_transparent=True)
    parent.attach(child, mode='transparent')
    assert rows(parent) == ['a.c...']
    parent.detach(child)
    parent.attach(child, mode='replace')
    assert rows(parent) == ['a c...']


def test_attach_rules():
    parent = Buffer(width=2, height=2)
    child = Buffer(width=1, height=1)
    parent.attach(child)
    assert parent.children == (child,)
    with pytest.raises(ValueError, match='already attached'):
        Buffer().attach(child)
    with pytest.raises(ValueError, match='itself'):
        parent.attach(parent)
    with pytest.raises(ValueError, match='loop'):
        child.attach(parent)
    parent.detach(child)
    assert parent.children == ()
    with pytest.raises(ValueError, match='not attached'):
        parent.detach(child)


def test_visibility_hides_a_child():
    parent = Buffer('....')
    child = Buffer('x')
    parent.attach(child)
    assert rows(parent) == ['x...']
    child.is_visible = False
    assert rows(parent) == ['....']


def test_copy_duplicates_content_geometry_and_children_only():
    parent = Buffer('abc', x=2)
    child = Buffer('d', x=1)
    parent.attach(child)
    parent.add_hook(lambda context: None)
    duplicate = parent.copy()
    assert duplicate is not parent
    assert (duplicate.x, duplicate.width) == (2, 3)
    assert len(duplicate.children) == 1 and duplicate.children[0] is not child
    parent.update(Write('ZZZ'))
    assert rows(duplicate) == ['adc']


def test_render_formats():
    buffer = Buffer('hi')
    assert buffer.render(format='text') == 'hi'
    assert '\x1b[' in buffer.render(format='ansi')
    with pytest.raises(ValueError, match='ansi'):
        buffer.render(format='html')
    assert str(buffer()).startswith('\x1b[')


def test_constructors():
    assert Buffer.with_size(3, 2).height == 2
    assert Buffer.with_text('x').width == 1
    cells = [Cell(symbol) for symbol in 'abcd']
    assert rows(Buffer.with_cells(cells, width=2, height=2)) == ['ab', 'cd']
    with pytest.raises(ValueError, match='needs 4 cells'):
        Buffer.with_cells(cells[:3], width=2, height=2)


def test_cell_grid_round_trip():
    original = Buffer(['ab', 'cd'])
    original.update(Foreground('red'))
    restored = Buffer.from_cell_grid(original.to_cell_grid())
    assert rows(restored) == ['ab', 'cd']
    assert restored[0, 0].foreground == original[0, 0].foreground


def test_revisions_count_changes_and_content_setter_replaces():
    buffer = Buffer('abc')
    before = buffer.revision
    buffer.update(Write('x'))
    assert buffer.revision > before
    buffer.content = 'q'
    assert rows(buffer) == ['q']
    assert buffer.cells.width == buffer.content.width == 3
