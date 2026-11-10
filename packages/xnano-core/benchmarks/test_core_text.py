"""
Benchmarks for xnano-core text: wrapping, measuring and styling.
"""

from __future__ import annotations

from xnano_core._xnano_core import (
    Buffer,
    Paragraph,
    Style,
    StyledText,
    Write,
    display_width,
)

ASCII_WORDS = ('terminal', 'cell', 'buffer', 'layout', 'ratatui', 'xnano')
WORDS = (*ASCII_WORDS, '界面', 'ünïcödé')
PROSE = ' '.join(WORDS[index % len(WORDS)] for index in range(2000))
ASCII_PROSE = ' '.join(ASCII_WORDS[index % len(ASCII_WORDS)] for index in range(2000))
COLORED_LOG = ''.join(
    f'\x1b[2m12:00:{index % 60:02}\x1b[0m \x1b[1;{31 + index % 7}m{WORDS[index % len(WORDS)]}'
    f'\x1b[0m request {index} took \x1b[38;5;{index % 256}m{index % 97} ms\x1b[0m\n'
    for index in range(2000)
)
"""Two thousand lines of colored log output, as a program prints them for a terminal."""


def test_display_width_mixed(benchmark):
    width = benchmark(display_width, PROSE)
    assert width > len(PROSE)


def test_display_width_ascii(benchmark):
    assert benchmark(display_width, ASCII_PROSE) == len(ASCII_PROSE)


def test_paragraph_wrap_render(benchmark):
    paragraph = Paragraph(PROSE, width=80, height=60, should_wrap=True)
    text = benchmark(paragraph.render, format='text')
    assert 'terminal' in text


def test_write_styled_text(benchmark):
    buffer = Buffer(width=200, height=60)
    style = Style('red', bold=True)
    operations = [
        Write(ASCII_PROSE[offset : offset + 190], x=0, y=row, style=style)
        for row, offset in enumerate(range(0, 60 * 190, 190))
    ]
    benchmark(buffer.update, *operations)
    assert buffer[0, 0].symbol == 't'
    assert buffer[0, 0].foreground.to_rgb() is None


def test_write_styled_mixed_unicode_text(benchmark):
    buffer = Buffer(width=200, height=60)
    style = Style('red', bold=True)
    operations = [
        Write(PROSE[offset : offset + 190], x=0, y=row, style=style)
        for row, offset in enumerate(range(0, 60 * 190, 190))
    ]
    benchmark(buffer.update, *operations)
    assert buffer[0, 0].symbol != ' '


def test_styled_text_from_ansi_log(benchmark):
    text = benchmark(StyledText.from_ansi, COLORED_LOG)
    assert text.height == 2000
    assert str(text).startswith('12:00:00 terminal request 0 took 0 ms')
