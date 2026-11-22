"""Fonts made of characters or pixels, text written in them, and frames drawn as PNG images."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest

from xnano_core import (
    Buffer,
    Font,
    Runtime,
    Size,
    Style,
    display_size,
    display_width,
)

BOXES_FONT = 'flf2a$ 2 1 2 0 1\na font of boxes\n' + ''.join(
    ' $@\n $@@\n' if code == 32 else '[]@\n<>@@\n' for code in range(32, 127)
)
"""A FIGlet font two rows tall: every character is ``[]`` over ``<>``."""

BAR_FONT = """STARTFONT 2.1
FONT bar
SIZE 4 75 75
FONTBOUNDINGBOX 3 4 0 0
CHARS 1
STARTCHAR I
ENCODING 73
DWIDTH 3 0
BBX 3 4 0 0
BITMAP
40
40
40
40
ENDCHAR
ENDFONT
"""
"""A BDF font of 3 by 4 pixels with one glyph: ``I``, a bar down the middle column."""


def png_pixels(data: bytes) -> tuple[int, int, bytes]:
    """The width, height and RGB bytes of a PNG image written without filters."""
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    position = 8
    width = height = 0
    compressed = b''
    while position < len(data):
        (length,) = struct.unpack('>I', data[position : position + 4])
        kind = data[position + 4 : position + 8]
        body = data[position + 8 : position + 8 + length]
        if kind == b'IHDR':
            width, height = struct.unpack('>II', body[:8])
        elif kind == b'IDAT':
            compressed += body
        position += 12 + length
    raw = zlib.decompress(compressed)
    stride = width * 3 + 1
    rows = bytearray()
    previous = bytearray(width * 3)
    for row in range(height):
        line = bytearray(raw[row * stride + 1 : (row + 1) * stride])
        kind = raw[row * stride]
        for index in range(len(line)):
            left = line[index - 3] if index >= 3 else 0
            above = previous[index]
            upper_left = previous[index - 3] if index >= 3 else 0
            if kind == 1:
                line[index] = (line[index] + left) & 0xFF
            elif kind == 2:
                line[index] = (line[index] + above) & 0xFF
            elif kind == 3:
                line[index] = (line[index] + (left + above) // 2) & 0xFF
            elif kind == 4:
                estimate = left + above - upper_left
                distances = (
                    abs(estimate - left),
                    abs(estimate - above),
                    abs(estimate - upper_left),
                )
                predictor = (left, above, upper_left)[distances.index(min(distances))]
                line[index] = (line[index] + predictor) & 0xFF
        rows += line
        previous = line
    return width, height, bytes(rows)


def test_builtin_fonts_are_pixel_fonts():
    assert Font() == Font('small')
    assert Font('small').glyph_size == Size(5, 7)
    assert Font('large').glyph_size == Size(8, 13)
    assert Font('large').kind == 'pixel'
    assert (
        repr(Font('small'))
        == "Font(name='small', kind='pixel', glyph_size=Size(width=5, height=7))"
    )


def test_unknown_builtin_font_names_the_builtin_fonts():
    with pytest.raises(ValueError, match='"small" and "large"'):
        Font('huge')  # type: ignore[arg-type]


def test_character_font_writes_rows_side_by_side():
    font = Font.from_bytes(BOXES_FONT.encode(), name='boxes')
    assert (font.name, font.kind) == ('boxes', 'character')
    assert font.glyph_size == Size(2, 2)
    assert font.render('ab c') == '[][]  []\n<><>  <>'
    assert font.render('a\nb') == '[]\n<>\n[]\n<>'


def test_pixel_font_writes_half_blocks():
    font = Font.from_bytes(BAR_FONT.encode())
    assert font.name == 'bar'
    assert font.render('I') == ' █ \n █ '
    assert font.has_character('I')
    assert not font.has_character('J')


def test_missing_character_is_written_as_itself():
    font = Font.from_bytes(BAR_FONT.encode())
    assert font.render('J') == 'J  \n   '


def test_has_character_takes_one_character():
    with pytest.raises(ValueError, match='one character'):
        Font().has_character('ab')


def test_from_file_reads_the_kind_from_the_contents(tmp_path: Path):
    path = tmp_path / 'bar.txt'
    path.write_text(BAR_FONT)
    assert Font.from_file(path).kind == 'pixel'


def test_from_file_reports_a_missing_file(tmp_path: Path):
    with pytest.raises(OSError, match='could not be read'):
        Font.from_file(tmp_path / 'missing.bdf')


def test_from_bytes_refuses_data_that_is_not_a_font():
    with pytest.raises(ValueError, match='flf2a.*STARTFONT 2.1'):
        Font.from_bytes(b'hello', name='notes')


def test_from_bytes_refuses_an_incomplete_figlet_font():
    with pytest.raises(ValueError, match='ends before the character 33'):
        Font.from_bytes(b'flf2a$ 2 1 2 0 0\n $@\n $@@\n')


def test_display_size_measures_text_in_a_font():
    assert display_size('hello\nhi') == Size(5, 2)
    assert display_size('') == Size(0, 1)
    assert display_size('ab', font='small') == Size(10, 4)
    assert display_size('ab\nc', font=Font.from_bytes(BOXES_FONT.encode())) == Size(4, 4)
    assert display_width('ab', font='large') == 16
    assert display_width('日本') == 4


def test_font_argument_rejects_other_values():
    with pytest.raises(TypeError, match='font must be a Font'):
        display_width('a', font=3)  # type: ignore[arg-type]


def test_buffer_renders_as_png_with_one_glyph_per_cell():
    buffer = Buffer.with_text(
        '█ ', style=Style(foreground='#ff0000', background='#0000ff')
    )
    width, height, pixels = png_pixels(buffer.render(format='png'))
    assert (width, height) == (16, 13)
    assert pixels[0:3] == b'\xff\x00\x00'
    assert pixels[8 * 3 : 8 * 3 + 3] == b'\x00\x00\xff'
    width, height, _ = png_pixels(buffer.render(format='png', font='small'))
    assert (width, height) == (10, 7)


def test_png_draws_half_blocks_as_shapes_with_any_font():
    buffer = Buffer.with_text(
        '▀', style=Style(foreground='#00ff00', background='#000000')
    )
    font = Font.from_bytes(BAR_FONT.encode())
    width, height, pixels = png_pixels(buffer.render(format='png', font=font))
    assert (width, height) == (3, 4)
    row = width * 3
    assert pixels[0:3] == b'\x00\xff\x00'
    assert pixels[3 * row : 3 * row + 3] == b'\x00\x00\x00'


def test_png_needs_a_pixel_font():
    font = Font.from_bytes(BOXES_FONT.encode(), name='boxes')
    with pytest.raises(ValueError, match='"boxes" is a character font'):
        Buffer.with_text('a').render(format='png', font=font)


def test_font_works_only_with_png():
    with pytest.raises(ValueError, match='only with'):
        Buffer.with_text('a').render(format='text', font='small')  # type: ignore[call-overload]
    with pytest.raises(ValueError, match='"png"'):
        Buffer.with_text('a').render(format='jpeg')  # type: ignore[call-overload]


def test_frame_snapshot_draws_the_frame_as_png():
    with Runtime.offscreen(width=3, height=2) as runtime:
        image = runtime.render().to_png(font='small')
    width, height, _ = png_pixels(image)
    assert (width, height) == (15, 14)
