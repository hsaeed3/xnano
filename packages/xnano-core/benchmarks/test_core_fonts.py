"""
Benchmarks for fonts: writing text in a font, measuring it, and drawing a frame as a PNG image.

Each timed call does all of its work: ``Font.render`` and ``display_size`` keep no cache
of earlier text, and a PNG image is drawn and encoded again on every call.
"""

from __future__ import annotations

import pytest

from xnano_core._xnano_core import Buffer, Font, Style, display_size

WIDTH, HEIGHT = 200, 60
COLORS = ('red', 'green', 'blue', 'yellow', 'magenta', 'cyan', 'white', 'gray')
SENTENCE = 'The quick brown fox jumps over the lazy dog 0123456789'


@pytest.fixture(scope='module')
def screen() -> Buffer:
    """A full screen where every row has its own colors and a line of pixel art."""
    buffer = Buffer(width=WIDTH, height=HEIGHT)
    for row in range(HEIGHT):
        style = Style(COLORS[row % len(COLORS)], COLORS[(row + 3) % len(COLORS)])
        text = chr(ord('a') + row % 26) * (WIDTH // 2) + '▀▄█⣿' * (WIDTH // 8)
        buffer.write(text, x=0, y=row, style=style)
    return buffer


def test_render_sentence_in_the_small_font(benchmark):
    font = Font('small')
    rows = benchmark(font.render, SENTENCE)
    assert len(rows.split('\n')) == 4


def test_measure_sentence_in_the_large_font(benchmark):
    size = benchmark(display_size, SENTENCE, font='large')
    assert size.width == len(SENTENCE) * 8


def test_render_full_screen_as_png(benchmark, screen):
    image = benchmark.pedantic(
        screen.render, kwargs={'format': 'png'}, rounds=20, iterations=1
    )
    assert image.startswith(b'\x89PNG')


def test_render_terminal_screen_as_png(benchmark):
    terminal = Buffer(width=80, height=24)
    for row in range(24):
        terminal.write(f'{row:>3} ' + SENTENCE, x=0, y=row, style=Style(COLORS[row % 8]))
    image = benchmark.pedantic(
        terminal.render, kwargs={'format': 'png'}, rounds=50, iterations=1
    )
    assert image.startswith(b'\x89PNG')
