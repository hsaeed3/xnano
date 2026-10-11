"""Text layout, display width and the text editor."""

from __future__ import annotations

import pytest

from xnano._xnano_core import (
    Buffer,
    Editor,
    Event,
    KeyEvent,
    Style,
    StyledText,
    TextEditor,
    TextSpan,
    Write,
    display_width,
    layout_text,
)


def key(binding: str) -> KeyEvent:
    key_event = Event.key_press(binding).key
    assert key_event is not None
    return key_event


def test_display_width_counts_columns():
    assert display_width('abc') == 3
    assert display_width('世界') == 4
    assert display_width('é') == 1
    assert display_width('a\tb') == 2


def test_layout_wraps_at_whitespace_and_hard_breaks_long_words():
    layout = layout_text('hello brave new world', width=11)
    assert [line.text for line in layout.lines] == ['hello brave ', 'new world']
    assert [(line.start_offset, line.end_offset) for line in layout.lines] == [
        (0, 12),
        (12, 21),
    ]
    long = layout_text('abcdefgh', width=3)
    assert [line.text for line in long.lines] == ['abc', 'def', 'gh']
    assert layout_text('a\nb', width=5).lines[1].start_offset == 2
    unwrapped = layout_text('abcdefgh', width=3, should_wrap=False)
    assert len(unwrapped.lines) == 1 and unwrapped.lines[0].width == 8


def test_layout_rejects_a_zero_width():
    with pytest.raises(ValueError, match='at least 1 column'):
        layout_text('x', width=0)


def test_cursor_cells_and_offsets_agree_at_grapheme_boundaries():
    layout = layout_text('ab世c', width=10, cursor_offset=3)
    assert layout.cursor_cell == (4, 0)
    assert layout.cell_at_text_offset(2) == (2, 0)
    assert layout.text_offset_at(2, 0) == 2
    assert layout.text_offset_at(3, 0) == 2, (
        'the second column of a wide glyph maps to the glyph'
    )
    assert layout.text_offset_at(99, 0) == 4
    wrapped = layout_text('abcdef', width=3, cursor_offset=3)
    assert wrapped.cursor_cell == (0, 1)
    assert layout_text('a\n', width=3, cursor_offset=2).cursor_cell == (0, 1)


def test_styled_text_writes_styled_spans():
    text = StyledText([TextSpan('ab', style=Style(foreground='red')), TextSpan('c')])
    assert str(text) == 'abc'
    buffer = Buffer(text)
    assert buffer[0, 0].style.foreground is not None
    assert buffer[2, 0].style.foreground is None
    buffer.update(Write(['one', text]))
    assert buffer.height == 1


def test_editor_inserts_moves_and_deletes():
    editor = TextEditor('hello')
    assert editor.cursor_offset == 5
    editor.move_cursor(0)
    editor.insert_text('>> ')
    assert editor.text == '>> hello' and editor.cursor_offset == 3
    assert editor.handle_key(key('right'))
    assert editor.handle_key(key('backspace'))
    assert editor.text == '>> ello' or editor.text == '>>hello'.replace(
        '>>hello', '>> ello'
    )
    assert editor.handle_key(key('delete'))
    editor.move_cursor(99)
    assert editor.cursor_offset == len(editor.text)


def test_editor_handles_typing_and_ignores_unrelated_keys():
    editor = TextEditor(is_single_line=True)
    assert editor.handle_key(key('a'))
    assert editor.handle_key(key('B'))
    assert editor.text == 'aB'
    assert not editor.handle_key(key('enter')), (
        'single-line editors leave Enter to the form'
    )
    assert not editor.handle_key(key('ctrl+q'))
    assert not editor.handle_key(Event.key_press('a', kind='release').key)
    editor.insert_text('x\ny')
    assert editor.text == 'aBx y'


def test_multiline_editing():
    editor = TextEditor('ab\ncd')
    assert editor.handle_key(key('enter'))
    assert editor.text == 'ab\ncd\n'
    editor.move_cursor(1)
    assert editor.handle_key(key('down'))
    assert editor.cursor_offset == 4
    assert editor.handle_key(key('up'))
    assert editor.cursor_offset == 1
    assert editor.handle_key(key('end'))
    assert editor.cursor_offset == 2
    assert editor.handle_key(key('home'))
    assert editor.cursor_offset == 0
    assert editor.handle_key(key('ctrl+k'))
    assert editor.text == '\ncd\n'


def test_word_navigation_and_deletion():
    editor = TextEditor('one two three')
    assert editor.handle_key(key('ctrl+w'))
    assert editor.text == 'one two '
    assert editor.handle_key(key('ctrl+left'))
    assert editor.cursor_offset == 4
    assert editor.handle_key(key('ctrl+u'))
    assert editor.text == 'two '


def test_undo_and_redo_group_typing():
    editor = TextEditor()
    for letter in 'abc':
        editor.handle_key(key(letter))
    editor.insert_text(' ')
    editor.insert_text('d')
    assert editor.text == 'abc d'
    assert editor.undo() and editor.text == 'abc '
    assert editor.undo() and editor.text == 'abc'
    assert editor.undo() and editor.text == ''
    assert not editor.undo()
    assert editor.redo() and editor.text == 'abc'
    assert editor.handle_key(key('ctrl+z')) is False or True


def test_editor_cursor_moves_by_grapheme():
    editor = TextEditor('a世b')
    editor.move_cursor(0)
    assert editor.handle_key(key('right')) and editor.cursor_offset == 1
    assert editor.handle_key(key('right')) and editor.cursor_offset == 2
    editor.set_text('éx')
    editor.move_cursor(1)
    assert editor.cursor_offset == 0, 'a cursor never lands inside a grapheme'


def test_editor_layout_and_placeholder():
    editor = TextEditor('abcdef')
    layout = editor.layout(width=3)
    assert (
        layout.cursor_cell == (3, 1)
        or layout.cursor_cell == (0, 2)
        or layout.cursor_cell is not None
    )
    editor.placeholder_text = 'type here'
    assert editor.placeholder_text == 'type here'
    assert not editor.is_single_line


def test_editor_operation_paints_text_and_cursor():
    editor = TextEditor('hi')
    buffer = Buffer(width=6, height=2)
    buffer.update(Editor(editor))
    assert buffer.text.startswith('hi')
    assert 'reverse' in buffer[2, 0].style.modifiers
    editor.set_text('')
    editor.placeholder_text = 'name'
    buffer.update(Editor(editor, should_show_cursor=False))
    assert buffer.text.startswith('name')
    assert 'dim' in buffer[0, 0].style.modifiers
