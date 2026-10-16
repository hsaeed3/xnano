"""
tests.test_rich_parity

Text layout checked against rich, which is the reference for how canvas text behaves.

The inputs are the ones rich's own tests use (``tests/test_text.py`` and ``tests/test_cells.py``
in its repository): wide characters, emoji built from several code points, long words, runs of
spaces, tabs and text that is cut off. Rich says what the answer should be; xnano has to give the
same one. Skipped when rich is not installed (``uv sync --group compare``).
"""

from __future__ import annotations

import io

import pytest

import xnano
from xnano.buffers import Buffer
from xnano.widgets import Paragraph

rich_text = pytest.importorskip('rich.text')
rich_console = pytest.importorskip('rich.console')
rich_cells = pytest.importorskip('rich.cells')

FEMALE_MECHANIC = '👩‍🔧'


def rich_lines(text: str, width: int, *, overflow: str = 'fold') -> list[str]:
    """The lines rich wraps ``text`` into, without trailing spaces."""
    console = rich_console.Console(file=io.StringIO(), width=width, legacy_windows=False)
    lines = rich_text.Text(text).wrap(console, width, overflow=overflow)
    return [line.plain.rstrip() for line in lines]


def xnano_lines(text: str, width: int) -> list[str]:
    """The lines xnano wraps ``text`` into, without trailing spaces."""
    rows = max(2, len(text) + 2)
    widget = Paragraph(
        text, should_wrap=True, should_trim=False, width=width, height=rows
    )
    return widget.render(format='text').split('\n')


def trimmed(lines: list[str]) -> list[str]:
    """Lines without the empty rows a fixed-height widget ends with."""
    result = [line.rstrip() for line in lines]
    while result and not result[-1]:
        result.pop()
    return result


CELL_WIDTH_CASES = [
    '',
    'a',
    'abc' * 200,
    'a' * 511,
    'a' * 512,
    '💩',
    '😽😽',
    'わさび',
    '日本語のテキスト',
    '123ありがとうございました',
    'เป็นเกมที่ต้องมีความอดทนมากที่สุดตั้งเเต่เคยเล่นมา',
    FEMALE_MECHANIC,
    FEMALE_MECHANIC * 5,
    'é',  # an e with a combining accent
    'ｆｕｌｌｗｉｄｔｈ',
    '🇯🇵🇺🇸',
    '👍🏽',
]


@pytest.mark.parametrize('text', CELL_WIDTH_CASES)
def test_the_width_of_text_matches_rich(text):
    if not text:
        return
    assert Buffer.with_text(text).width == rich_cells.cell_len(text)


WRAP_CASES = [
    ('foo bar baz', 3),
    ('foo bar baz', 4),
    ('1234 12345678', 7),
    ('わさび', 4),
    ('わさび', 3),
    ('123ありがとうございました', 8),
    ('abracadabra', 4),
    (FEMALE_MECHANIC * 5, 4),
    ('Some more words', 4),
    ('Some more words', 15),
    ('the quick brown fox jumps over the lazy dog', 10),
    ('the quick brown fox jumps over the lazy dog', 1 + 5),
    ('averyveryverylongwordthatdoesnotfit and short', 12),
    ('a', 1),
    ('ab', 1),
    ('supercalifragilisticexpialidocious', 8),
    ('日本語のテキスト and english', 9),
    ('emoji 😽😽😽😽 mixed', 7),
]


@pytest.mark.parametrize(('text', 'width'), WRAP_CASES)
def test_wrapping_breaks_where_rich_breaks(text, width):
    assert trimmed(xnano_lines(text, width)) == trimmed(rich_lines(text, width))


@pytest.mark.parametrize(('text', 'width'), WRAP_CASES)
def test_nothing_is_lost_or_cut_by_wrapping(text, width):
    lines = trimmed(xnano_lines(text, width))
    assert ''.join(lines).replace(' ', '') == text.replace(' ', '')
    for line in lines:
        assert rich_cells.cell_len(line) <= width


@pytest.mark.parametrize('width', [5, 8, 13, 21])
def test_wrapping_a_paragraph_matches_rich_at_every_width(width):
    text = (
        'The quick brown fox jumps over the lazy dog while the five boxing wizards jump '
        'quickly, and pack my box with five dozen liquor jugs.'
    )
    assert trimmed(xnano_lines(text, width)) == trimmed(rich_lines(text, width))


@pytest.mark.parametrize('width', [1, 2, 3, 4])
def test_wrapping_a_paragraph_at_a_tiny_width_loses_nothing(width):
    text = 'The quick brown fox jumps over the lazy dog'
    lines = trimmed(xnano_lines(text, width))
    assert ''.join(lines) == text.replace(' ', '')
    assert all(len(line) <= width for line in lines)


@pytest.mark.parametrize(
    ('alignment', 'rich_justify'),
    [('left', 'left'), ('center', 'center'), ('right', 'right')],
)
@pytest.mark.parametrize('text', ['foo', 'foo bar', 'わさび', 'x'])
def test_alignment_places_text_as_rich_does(text, alignment, rich_justify):
    width = 12
    console = rich_console.Console(file=io.StringIO(), width=width, legacy_windows=False)
    with console.capture() as capture:
        console.print(rich_text.Text(text), justify=rich_justify, end='')
    expected = capture.get().rstrip('\n')
    widget = Paragraph(
        text, should_wrap=False, alignment=alignment, width=width, height=1
    )
    shown = widget.render(format='text')
    assert shown.strip() == expected.strip() == text
    left_ours = len(shown) - len(shown.lstrip(' '))
    left_rich = len(expected) - len(expected.lstrip(' '))
    # Centering a text in an odd amount of room puts the extra column on one side or the
    # other: rich gives it to the right, xnano to the left. Everything else is identical.
    assert abs(left_ours - left_rich) <= (1 if alignment == 'center' else 0)


@pytest.mark.parametrize(
    ('text', 'width'),
    [
        ('hello world', 5),
        ('わさびわさび', 5),
        ('short', 10),
        ('exactly ten', 11),
        ('a' * 50, 12),
    ],
)
def test_text_that_does_not_wrap_is_cut_at_the_width_like_rich_crop(text, width):
    console = rich_console.Console(file=io.StringIO(), width=width, legacy_windows=False)
    with console.capture() as capture:
        console.print(rich_text.Text(text), no_wrap=True, overflow='crop', end='')
    widget = Paragraph(text, should_wrap=False, width=width, height=1)
    assert widget.render(format='text') == capture.get().rstrip()


def test_a_terminal_shows_wide_characters_in_two_cells_and_never_splits_them():
    with xnano.new(width=5, height=2) as canvas:
        canvas.write('わさび')
        canvas.output.render()
        lines = canvas.output.snapshot().lines()
    assert lines[0] == 'わさ'
    assert rich_cells.cell_len(lines[0]) == 4


@pytest.mark.parametrize('count', [1, 2, 3, 4])
def test_a_wide_character_that_does_not_fit_is_dropped_not_cut(count):
    with xnano.new(width=count, height=1) as canvas:
        canvas.write('😽😽😽')
        canvas.output.render()
        line = canvas.output.snapshot().lines()[0]
    assert rich_cells.cell_len(line) <= count
    assert line == '😽' * (count // 2)
