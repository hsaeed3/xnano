"""
Benchmarks for xnano-core text: wrapping, measuring and editing.
"""

from __future__ import annotations

from xnano_core._xnano_core import (
    Buffer,
    Paragraph,
    Style,
    TextEditor,
    Write,
    display_width,
    layout_text,
)

ASCII_WORDS = ('terminal', 'cell', 'buffer', 'layout', 'ratatui', 'xnano')
WORDS = (*ASCII_WORDS, '界面', 'ünïcödé')
PROSE = ' '.join(WORDS[index % len(WORDS)] for index in range(2000))
ASCII_PROSE = ' '.join(ASCII_WORDS[index % len(ASCII_WORDS)] for index in range(2000))


def test_layout_text_wrap(benchmark):
    layout = benchmark(layout_text, PROSE, width=80)
    # A trailing space may hang past the edge instead of forcing a wrap.
    assert max(display_width(line.text.rstrip()) for line in layout.lines) <= 80
    assert len(layout.lines) > 100


def test_layout_text_wrap_ascii(benchmark):
    layout = benchmark(layout_text, ASCII_PROSE, width=80)
    assert max(display_width(line.text.rstrip()) for line in layout.lines) <= 80
    assert ''.join(line.text for line in layout.lines) == ASCII_PROSE


def test_layout_text_no_wrap_with_cursor(benchmark):
    benchmark(
        lambda: layout_text(
            PROSE, width=80, should_wrap=False, cursor_offset=len(PROSE) // 2
        )
    )


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


def test_text_editor_typing(benchmark):
    def type_text() -> str:
        editor = TextEditor()
        for character in PROSE[:400]:
            editor.insert_text(character)
        return editor.text

    text = benchmark(type_text)
    assert text == PROSE[:400]
