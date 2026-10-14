"""
Benchmarks for xnano-core drawing: serializing buffers, compositing layers and drawing
frames on an offscreen runtime.

Every timed call does the work it names. State that must change between calls is
prepared in ``setup`` (which is not timed) so repeating an identical operation cannot
turn into a no-op.
"""

from __future__ import annotations

import itertools

import pytest

from xnano_core._xnano_core import (
    Buffer,
    Cell,
    Runtime,
    Style,
    Write,
    cell_grid_to_ansi,
)

WIDTH, HEIGHT = 200, 60
COLORS = ('red', 'green', 'blue', 'yellow', 'magenta', 'cyan', 'white', 'gray')


def styled_screen(width: int = WIDTH, height: int = HEIGHT) -> Buffer:
    """A full screen where every row has its own colors, so no run of cells repeats."""
    buffer = Buffer(width=width, height=height)
    for row in range(height):
        style = Style(
            COLORS[row % len(COLORS)], COLORS[(row + 3) % len(COLORS)], bold=row % 2 == 0
        )
        buffer.write(chr(ord('a') + row % 26) * width, x=0, y=row, style=style)
    return buffer


@pytest.fixture(scope='module')
def screen() -> Buffer:
    return styled_screen()


def test_render_text_full_screen(benchmark, screen):
    text = benchmark(screen.render, format='text')
    assert len(text.split('\n')) == HEIGHT


def test_render_ansi_full_screen(benchmark, screen):
    ansi = benchmark(screen.render, format='ansi')
    assert '\x1b[' in ansi and len(ansi.splitlines()) == HEIGHT


def test_render_ansi_unstyled_full_screen(benchmark):
    buffer = Buffer(width=WIDTH, height=HEIGHT)
    buffer.update(Write('\n'.join(['x' * WIDTH] * HEIGHT)))
    ansi = benchmark(buffer.render, format='ansi')
    assert ansi.count('x') == WIDTH * HEIGHT


def test_render_wide_characters(benchmark):
    buffer = Buffer(width=WIDTH, height=HEIGHT)
    row = '界' * (WIDTH // 2)
    buffer.update(Write('\n'.join([row] * HEIGHT)))
    text = benchmark(buffer.render, format='text')
    assert text.split('\n')[0] == row


def test_render_overlapping_children(benchmark):
    """Fifty layered children, each covering part of the screen, composited per render."""
    parent = Buffer(width=WIDTH, height=HEIGHT)
    for index in range(50):
        child = Buffer(width=60, height=20, x=index * 2, y=index % 40)
        child.write(
            chr(ord('A') + index % 26) * 60, x=0, y=0, style=Style(COLORS[index % 8])
        )
        child.fill(Cell(chr(ord('A') + index % 26)))
        parent.attach(child)
    text = benchmark(parent.render, format='text')
    assert 'A' in text and 'Y' in text


def test_fill_full_screen(benchmark):
    """Fill alternates between two symbols so every call changes every cell."""
    buffer = Buffer(width=WIDTH, height=HEIGHT)
    symbols = itertools.cycle(('a', 'b'))
    benchmark(lambda: buffer.fill(next(symbols)))
    assert buffer[0, 0].symbol in ('a', 'b')


def test_cell_grid_round_trip(benchmark, screen):
    def round_trip() -> str:
        return cell_grid_to_ansi(
            Buffer.from_cell_grid(screen.to_cell_grid()).to_cell_grid()
        )

    ansi = benchmark(round_trip)
    assert len(ansi.splitlines()) == HEIGHT


def test_to_cell_grid(benchmark, screen):
    packed = benchmark(screen.to_cell_grid)
    assert packed[:4] == b'XCG1'


def test_from_cell_grid(benchmark, screen):
    packed = screen.to_cell_grid()
    buffer = benchmark(Buffer.from_cell_grid, packed)
    assert (buffer.width, buffer.height) == (WIDTH, HEIGHT)


def test_runtime_frame_after_full_redraw(benchmark):
    """One offscreen frame in which every cell of the screen changed."""
    runtime = Runtime.offscreen(width=WIDTH, height=HEIGHT)
    root = Buffer()
    runtime.mount(root, geometry='inherit')
    runtime.step()
    symbols = itertools.cycle(('a', 'b'))

    def setup():
        root.fill(next(symbols))
        return (), {}

    benchmark.pedantic(runtime.step, setup=setup, rounds=200, warmup_rounds=5)
    assert runtime.snapshot().lines()[0].startswith(('a', 'b'))
    runtime.close()


def test_runtime_frame_after_small_change(benchmark):
    """One offscreen frame in which a single cell changed on a large screen."""
    runtime = Runtime.offscreen(width=WIDTH, height=HEIGHT)
    root = Buffer()
    runtime.mount(root, geometry='inherit')
    root.update(Write('\n'.join(['x' * WIDTH] * HEIGHT)))
    runtime.step()
    symbols = itertools.cycle(('a', 'b'))

    def setup():
        root[0, 0] = next(symbols)
        return (), {}

    benchmark.pedantic(runtime.step, setup=setup, rounds=500, warmup_rounds=5)
    assert runtime.snapshot().lines()[0][0] in ('a', 'b')
    runtime.close()


def test_runtime_idle_step(benchmark):
    """Stepping with nothing to do must be nearly free."""
    runtime = Runtime.offscreen(width=WIDTH, height=HEIGHT)
    root = Buffer()
    runtime.mount(root, geometry='inherit')
    runtime.step()
    benchmark(runtime.step)
    assert not runtime.needs_frame
    runtime.close()
