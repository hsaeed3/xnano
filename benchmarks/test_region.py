"""
benchmarks.test_region

Benchmarks for reading and writing cells, pixels and dots through a region, and for shading a
whole region in one write.

Each timed call that changes a region also draws the frame that shows it, so the figure is the
cost a user sees. The colors change between calls, so a second call cannot reuse an unchanged
result.

Budgets, from measurements on an optimized build (Apple M-series, Python 3.11, 80 by 24):
shading 3840 half-block pixels with the frame takes about 3.5 ms; a single cell written from a
pixel that already holds its core cell takes about 0.5 us, and a cold pixel about 1.8 us; a
read takes about 1.4 us.

The budgets are asserted only when ``XNANO_CHECK_BUDGETS=1`` is set on an optimized build
outside CodSpeed (``make benchmark-xnano`` does it): a debug build is several times slower and
says nothing about the code's speed.
"""

from __future__ import annotations

import itertools
import time

import pytest
from benchmark_budgets import check_budget

import xnano
from xnano import Pixel

WIDTH = 80
HEIGHT = 24

HALF_BLOCK_SHADE_BUDGET_MILLISECONDS = 5.0
"""Shading every half-block pixel of an 80 by 24 canvas and drawing the frame."""

CELL_SHADE_BUDGET_MILLISECONDS = 4.0
"""Shading every cell of an 80 by 24 canvas and drawing the frame."""

FOREGROUND_SHADE_BUDGET_MILLISECONDS = 1.0
"""Coloring the text of every cell of an 80 by 24 canvas and drawing the frame; it is one pass
over the cells, like a background shade."""

LARGE_FOREGROUND_SHADE_BUDGET_MILLISECONDS = 3.0
"""The same for a 200 by 50 canvas, where the function is called for ten thousand cells."""

WARM_WRITE_BUDGET_MICROSECONDS = 1.0
"""Writing a pixel that already holds its core cell into one cell."""

COLD_WRITE_BUDGET_MICROSECONDS = 2.5
"""Writing a new pixel into one cell."""

READ_BUDGET_MICROSECONDS = 2.0
"""Reading one cell as a pixel."""

REPEATS = 1000


def fastest(function, *, rounds: int = 15) -> float:
    """The fastest of several calls, in seconds."""
    results = []
    for _ in range(rounds):
        start = time.perf_counter()
        function()
        results.append(time.perf_counter() - start)
    return min(results)


def test_half_block_shade_with_its_frame(benchmark):
    phases = itertools.count()
    with xnano.new(width=WIDTH, height=HEIGHT) as canvas:
        pixels = canvas.region.half_blocks

        def shade_and_draw() -> None:
            phase = next(phases) % 200
            pixels.shade(lambda x, y: (x + phase, y + phase, 80))
            canvas.step()

        benchmark.pedantic(shade_and_draw, rounds=10, iterations=1)
        assert canvas.region.half_blocks[3, 3].foreground is not None
        check_budget(
            lambda: fastest(shade_and_draw) * 1e3,
            HALF_BLOCK_SHADE_BUDGET_MILLISECONDS,
            'half-block shade with a frame',
            unit='ms',
        )


def test_cell_shade_with_its_frame(benchmark):
    phases = itertools.count()
    with xnano.new(width=WIDTH, height=HEIGHT) as canvas:
        region = canvas.region

        def shade_and_draw() -> None:
            phase = next(phases) % 200
            region.shade(lambda x, y: (x + phase, y + phase, 80))
            canvas.step()

        benchmark.pedantic(shade_and_draw, rounds=10, iterations=1)
        assert region[5, 5].background is not None
        check_budget(
            lambda: fastest(shade_and_draw) * 1e3,
            CELL_SHADE_BUDGET_MILLISECONDS,
            'cell shade with a frame',
            unit='ms',
        )


@pytest.mark.parametrize(
    ('width', 'height', 'budget'),
    [
        (WIDTH, HEIGHT, FOREGROUND_SHADE_BUDGET_MILLISECONDS),
        (200, 50, LARGE_FOREGROUND_SHADE_BUDGET_MILLISECONDS),
    ],
)
def test_foreground_shade_with_its_frame(benchmark, width, height, budget):
    phases = itertools.count()
    with xnano.new(width=width, height=height) as canvas:
        canvas.region[0:4, 0:1] = 'abcd'
        slot = canvas.color.fg

        def shade_and_draw() -> None:
            phase = next(phases) % 200
            slot.shade(lambda x, y: (x + phase, y + phase, 80))
            canvas.step()

        benchmark.pedantic(shade_and_draw, rounds=10, iterations=1)
        assert canvas.region[1, 0].character == 'b'
        assert canvas.region[1, 0].foreground is not None
        check_budget(
            lambda: fastest(shade_and_draw) * 1e3,
            budget,
            f'foreground shade of {width} by {height} with a frame',
            unit='ms',
        )


def test_a_cell_written_from_a_warm_pixel(benchmark):
    pixel = Pixel('star', foreground='red')
    pixel.cell()
    with xnano.new(width=WIDTH, height=HEIGHT) as canvas:
        region = canvas.region

        def write_many() -> None:
            for _ in range(REPEATS):
                region[3, 3] = pixel

        benchmark.pedantic(write_many, rounds=20, iterations=1)
        canvas.step()
        assert region[3, 3].character == '★'
        check_budget(
            lambda: fastest(write_many) / REPEATS * 1e6,
            WARM_WRITE_BUDGET_MICROSECONDS,
            'a warm pixel write',
        )


def test_a_cell_written_from_a_new_pixel(benchmark):
    with xnano.new(width=WIDTH, height=HEIGHT) as canvas:
        region = canvas.region

        def write_many() -> None:
            for index in range(REPEATS):
                region[3, 3] = Pixel('dot', foreground=(index % 256, 0, 0))

        benchmark.pedantic(write_many, rounds=20, iterations=1)
        canvas.step()
        assert region[3, 3].character == '•'
        check_budget(
            lambda: fastest(write_many) / REPEATS * 1e6,
            COLD_WRITE_BUDGET_MICROSECONDS,
            'a cold pixel write',
        )


def test_a_cell_read_as_a_pixel(benchmark):
    with xnano.new(width=WIDTH, height=HEIGHT) as canvas:
        region = canvas.region
        region[3, 3] = Pixel('star', foreground='red')

        def read_many() -> Pixel:
            found = region[3, 3]
            for _ in range(REPEATS):
                found = region[3, 3]
            return found

        found = benchmark.pedantic(read_many, rounds=20, iterations=1)
        assert found.character == '★'
        check_budget(
            lambda: fastest(read_many) / REPEATS * 1e6,
            READ_BUDGET_MICROSECONDS,
            'a pixel read',
        )
