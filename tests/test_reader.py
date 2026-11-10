"""
tests.test_reader

The reader: how it lays Markdown out, which kind it gives a file, how it prints a document
without a terminal, its themes, the ``xnano FILE`` command, and the viewer on an emulated
terminal.
"""

from __future__ import annotations

import io
import json
import struct
import sys
import zlib
from typing import get_args

import pytest

import xnano
from xnano.__main__ import main
from xnano.reader._documents import read_document
from xnano.reader._images import cells_for, pixel_size
from xnano.reader._markdown import layout_markdown
from xnano.themes import THEMES, ThemeName, theme_of
from xnano_core import display_width

MARKDOWN = """# Field notes

A **bold** word, `code` and a [link](other.md).

## Tasks

- one
- [x] done

| Service | Requests |
| ------- | -------: |
| api     | 1200     |

![a missing picture](missing.png)
"""


def _png(width: int, height: int) -> bytes:
    """A valid PNG file of one color."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body))

    header = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    rows = b''.join(b'\x00' + b'\x40\x80\xc0' * width for _ in range(height))
    return (
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', header)
        + chunk(b'IDAT', zlib.compress(rows))
        + chunk(b'IEND', b'')
    )


def _printed(path, **options) -> str:
    output = io.StringIO()
    xnano.view(path, interactive=False, output=output, **options)
    return output.getvalue()


# -- Markdown ---------------------------------------------------------------------------


def test_markdown_lines_fit_the_width():
    lines = layout_markdown(MARKDOWN * 3, width=30, theme=theme_of(None))
    assert lines
    assert all(display_width(line.text) <= 30 for line in lines)


def test_markdown_keeps_headings_links_and_lists():
    lines = layout_markdown(MARKDOWN, width=60, theme=theme_of(None))
    text = [line.text for line in lines]
    assert text[0] == 'Field notes'
    assert [line.heading for line in lines if line.heading] == [
        (1, 'Field notes'),
        (2, 'Tasks'),
    ]
    assert any('• one' in line for line in text)
    assert [target for line in lines for _, _, target in line.links] == ['other.md']


def test_markdown_names_an_image_that_it_cannot_show():
    lines = layout_markdown(MARKDOWN, width=60, theme=theme_of(None))
    assert any('[image: a missing picture]' in line.text for line in lines)


def test_from_markdown_gives_styled_text():
    text = xnano.from_markdown('# Notes\n\nA **bold** word.', width=30)
    assert str(text).splitlines()[0] == 'Notes'
    with xnano.new(width=30, height=4) as canvas:
        canvas.write(text)
        assert 'A bold word.' in canvas.render()


# -- kinds of files ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ('name', 'content', 'kind'),
    [
        ('notes.md', b'# Notes\n', 'markdown'),
        ('data.json', b'{"a": 1}', 'json'),
        ('rows.csv', b'a,b\n1,2\n', 'table'),
        ('plain.txt', b'hello\n', 'text'),
        ('no_suffix', b'{"a": [1, 2]}', 'json'),
        ('blob.bin', b'\x00\x01\x02\xff', 'bytes'),
        ('picture', _png(4, 2), 'image'),
    ],
)
def test_a_file_gets_its_kind(tmp_path, name, content, kind):
    path = tmp_path / name
    path.write_bytes(content)
    assert read_document(path).kind == kind


def test_json_that_is_not_valid_is_shown_as_text(tmp_path):
    path = tmp_path / 'broken.json'
    path.write_text('{"a": ')
    document = read_document(path)
    assert document.kind == 'text'
    assert 'not valid JSON' in document.note


def test_a_missing_file_and_a_directory_say_what_to_do(tmp_path):
    with pytest.raises(FileNotFoundError, match='nothing.md'):
        read_document(tmp_path / 'nothing.md')
    with pytest.raises(IsADirectoryError):
        read_document(tmp_path)


def test_the_size_of_an_image_comes_from_its_header(tmp_path):
    path = tmp_path / 'picture.png'
    path.write_bytes(_png(40, 20))
    assert pixel_size(path) == (40, 20)
    columns, rows = cells_for((40, 20), 20)
    assert columns <= 20
    assert rows >= 1


# -- printing ---------------------------------------------------------------------------


def test_view_prints_markdown_as_plain_text(tmp_path):
    path = tmp_path / 'notes.md'
    path.write_text(MARKDOWN)
    printed = _printed(path, width=40)
    lines = printed.splitlines()
    assert lines[0] == 'Field notes'
    assert '\x1b' not in printed
    assert all(display_width(line) <= 40 for line in lines)
    assert any('api' in line and '1200' in line for line in lines)


def test_view_prints_json_indented(tmp_path):
    path = tmp_path / 'data.json'
    path.write_text(json.dumps({'name': 'xnano', 'ratio': 0.5, 'tags': ['a']}))
    lines = _printed(path, width=40).splitlines()
    assert lines[0] == '{'
    assert '  "name": "xnano",' in lines


def test_view_prints_a_table_with_its_header(tmp_path):
    path = tmp_path / 'rows.csv'
    path.write_text('service,requests\napi,1200\nweb,880\n')
    lines = _printed(path, width=40).splitlines()
    assert lines[0].split() == ['service', 'requests']
    assert lines[1].split() == ['api', '1200']


def test_view_prints_the_same_text_in_every_theme(tmp_path):
    path = tmp_path / 'notes.md'
    path.write_text(MARKDOWN)
    plain = _printed(path, width=40)
    for name in get_args(ThemeName):
        assert _printed(path, width=40, theme=name) == plain, name


# -- themes -----------------------------------------------------------------------------


def test_every_theme_name_has_a_theme_with_colors():
    assert set(get_args(ThemeName)) == set(THEMES)
    for name, theme in THEMES.items():
        assert theme.name == name
        for color in (theme.background, theme.surface, theme.text, theme.link):
            assert color is not None, name
            assert len(color) == 7, name
            assert color.startswith('#'), name


def test_a_theme_colors_text_and_its_background():
    text = xnano.from_markdown('A [link](a.md).', width=20, theme='dracula')
    with xnano.new(width=20, height=1) as canvas:
        canvas.write(text)
        rendered = canvas.render(format='ansi')
    assert '40;42;54' in rendered  # the background of Dracula, #282a36
    assert '139;233;253' in rendered  # its link color, #8be9fd


def test_an_unknown_theme_names_the_themes():
    with pytest.raises(ValueError, match="no theme named 'sepia'.*'xnano-night'"):
        xnano.from_markdown('text', theme='sepia')  # pyright: ignore[reportArgumentType]


# -- the command ------------------------------------------------------------------------


def test_the_command_prints_a_file(tmp_path, capsys):
    path = tmp_path / 'notes.md'
    path.write_text(MARKDOWN)
    assert main([str(path), '--print', '--width', '40', '--theme', 'xnano-day']) == 0
    assert capsys.readouterr().out.splitlines()[0] == 'Field notes'


def test_the_command_reports_a_missing_file(tmp_path, capsys):
    assert main([str(tmp_path / 'nothing.md')]) == 1
    assert 'nothing.md' in capsys.readouterr().err


# -- the viewer -------------------------------------------------------------------------


@pytest.fixture
def viewer(tmp_path):
    pytest.importorskip('pyte')
    if sys.platform == 'win32':
        pytest.skip('needs a pseudo-terminal')
    from emulator import Screen

    path = tmp_path / 'notes.md'
    filler = '\n\n'.join(f'Paragraph {number} of the notes.' for number in range(60))
    path.write_text(f'# Field notes\n\n{filler}\n\n## The end\n\nLast line here.\n')
    screen = Screen(
        command=[sys.executable, '-m', 'xnano', str(path)], rows=20, columns=60
    )
    try:
        assert screen.wait_for('q quit'), screen.text
        yield screen
    finally:
        screen.close()


def test_the_viewer_scrolls_finds_and_leaves(viewer):
    assert 'Field notes' in viewer.text
    viewer.press('G')
    assert viewer.wait_for('Last line here.'), viewer.text
    viewer.press('g')
    assert viewer.wait_for('Paragraph 0 of'), viewer.text
    viewer.scroll(10, 10, direction='down')
    assert viewer.wait_until(lambda: 'Field notes' not in viewer.lines()[1]), viewer.text
    viewer.send('/Paragraph 40')
    viewer.press('enter')
    assert viewer.wait_for('Paragraph 40 of'), viewer.text
    assert viewer.wait_for('1 of 1'), viewer.text
    viewer.press('q')
    assert viewer.finish() == 0


def test_the_viewer_has_buttons_and_an_outline(viewer):
    column, row = viewer.find('outline')
    viewer.click(column, row)
    assert viewer.wait_for('The end'), viewer.text
    viewer.press('down')
    viewer.press('enter')
    assert viewer.wait_for('Last line here.'), viewer.text
    column, row = viewer.find('quit')
    viewer.click(column, row)
    assert viewer.finish() == 0


# -- details of the layout --------------------------------------------------------------


def test_from_markdown_keeps_a_table_as_text():
    text = str(xnano.from_markdown('| A | B |\n|---|--:|\n| one | 2 |\n', width=30))
    assert '│A    B│' in text
    assert '│one  2│' in text


def test_markdown_keeps_an_address_at_the_start_of_a_line():
    lines = layout_markdown('<https://xnano.hammad.app>', width=40, theme=theme_of(None))
    assert lines[0].text == 'https://xnano.hammad.app'
    assert lines[0].links[0][2] == 'https://xnano.hammad.app'


def test_a_backslash_at_the_end_of_a_line_breaks_the_line():
    lines = layout_markdown('one\\\ntwo', width=40, theme=theme_of(None))
    assert [line.text for line in lines] == ['one', 'two']


def test_a_fence_of_the_other_kind_does_not_end_a_code_block():
    source = '```\n~~~\n[name]: not-a-reference\n```\n'
    lines = layout_markdown(source, width=40, theme=theme_of(None))
    assert any('[name]: not-a-reference' in line.text for line in lines)


def test_a_table_with_many_columns_stays_inside_the_width():
    header = '|' + '|'.join('abcdef' for _ in range(8)) + '|'
    source = f'{header}\n|{"|".join(["---"] * 8)}|\n{header}\n'
    lines = layout_markdown(source, width=30, theme=theme_of(None))
    assert max(line.content_size[0] for line in lines if line.content is not None) <= 30


def test_a_long_word_breaks_between_characters_and_not_inside_one():
    family = '\U0001f468‍\U0001f469‍\U0001f467'
    lines = layout_markdown(family * 4, width=4, theme=theme_of(None))
    assert all(
        line.text.count('\U0001f468') == line.text.count('\U0001f467') for line in lines
    )


def test_bytes_fit_in_a_narrow_width(tmp_path):
    path = tmp_path / 'blob.bin'
    path.write_bytes(bytes(range(256)))
    for width in (20, 40, 80):
        lines = _printed(path, width=width).splitlines()
        assert all(display_width(line) <= width for line in lines), width


def test_a_webp_file_without_a_suffix_is_an_image(tmp_path):
    path = tmp_path / 'picture'
    path.write_bytes(b'RIFF\x1a\x00\x00\x00WEBPVP8L' + b'\x00' * 16)
    assert read_document(path).kind == 'image'
    wave = tmp_path / 'sound'
    wave.write_bytes(b'RIFF\x24\x00\x00\x00WAVEfmt ' + b'\x00' * 16)
    assert read_document(wave).kind == 'audio'


def test_the_size_of_an_xni_image_comes_from_its_header(tmp_path):
    path = tmp_path / 'art.xni'
    path.write_bytes(b'XNI1' + struct.pack('>HHH', 24, 12, 1))
    assert pixel_size(path) == (24, 12)


def test_inline_code_and_link_targets_keep_their_text():
    lines = layout_markdown(
        '`` ` `` and ` a ` and [x](a(b).md)', width=40, theme=theme_of(None)
    )
    assert lines[0].text == '` and a and x'
    assert lines[0].links[0][2] == 'a(b).md'


def test_a_click_on_a_link_opens_the_file(tmp_path):
    pytest.importorskip('pyte')
    if sys.platform == 'win32':
        pytest.skip('needs a pseudo-terminal')
    from emulator import Screen

    (tmp_path / 'other.md').write_text(
        '# Other\n\nfiller\n\n## Install\n\nThe second file.\n'
    )
    first = tmp_path / 'first.md'
    first.write_text('# First\n\nGo to the [next file](other.md).\n')
    screen = Screen(
        command=[sys.executable, '-m', 'xnano', str(first)], rows=12, columns=50
    )
    try:
        assert screen.wait_for('q quit'), screen.text
        found = screen.find('next file')
        assert found is not None, screen.text
        column, row = found
        screen.click(column + 2, row)
        assert screen.wait_for('The second file.'), screen.text
        screen.press('q')
        assert screen.finish() == 0
    finally:
        screen.close()
