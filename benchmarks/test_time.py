"""
benchmarks.test_time

Benchmarks for the time controls of a canvas: stepping a static canvas, creating and closing
one, and writing and removing text.

Measurements on an optimized build (Apple M-series, Python 3.11, minimum of 7 rounds):

| Case | Measured | Budget |
| --- | --- | --- |
| ``step()`` of a static canvas, 80 by 24, with its ``Frame`` | 2.6 us | 4.0 us |
| ``step()`` of a static canvas, 200 by 50 | 2.6 us | 4.0 us |
| ``new()`` then ``close()``, 80 by 24 | 16 us | 23.1 us |
| ``write('hi')`` then ``remove()`` | 6.5 us | 7.8 us |

The budgets are asserted only when ``XNANO_CHECK_BUDGETS=1`` is set on an optimized build
outside CodSpeed (``make benchmark-xnano`` does it): a debug build is several times slower and
says nothing about the code's speed.
"""

from __future__ import annotations

import itertools
import time

import pytest
from benchmark_budgets import check_budget, skip_unless_budgets_are_checked

import xnano

STEP_BUDGET_MICROSECONDS = 4.0
"""A step of a static canvas draws nothing, so it must stay near the cost of the clock."""

CREATE_BUDGET_MICROSECONDS = 23.1
"""Creating and closing a canvas costs little more than the runtime that it creates."""

WRITE_BUDGET_MICROSECONDS = 7.8
"""Writing and removing text costs about a fifth more than the measured figure at most."""


def minimum_microseconds(function, *, number: int = 1000, repeat: int = 7) -> float:
    """The fastest of several runs of a loop, per call, in microseconds."""
    results = []
    for _ in range(repeat):
        start = time.perf_counter()
        for _ in range(number):
            function()
        results.append((time.perf_counter() - start) / number * 1e6)
    return min(results)


@pytest.mark.parametrize(('width', 'height'), [(80, 24), (200, 50)])
def test_a_step_of_a_static_canvas(benchmark, width, height):
    with xnano.new(width=width, height=height) as canvas:
        canvas.screen.write('static')
        canvas.clock.step()
        frame = benchmark.pedantic(canvas.clock.step, rounds=200, iterations=10)
        assert frame.elapsed_seconds > 0
        assert canvas._frame_demand == 0
        check_budget(
            lambda: minimum_microseconds(canvas.clock.step),
            STEP_BUDGET_MICROSECONDS,
            f'step() of a static {width} by {height} canvas',
        )


def test_the_cost_of_a_step_does_not_grow_with_the_canvas():
    skip_unless_budgets_are_checked()
    costs = []
    for width, height in ((80, 24), (200, 50)):
        with xnano.new(width=width, height=height) as canvas:
            canvas.screen.write('static')
            canvas.clock.step()
            costs.append(minimum_microseconds(canvas.clock.step))
    check_budget(lambda: costs[1], costs[0] * 1.1, 'step() of a static 200 by 50 canvas')


def test_creating_and_closing_a_canvas(benchmark):
    sizes = itertools.cycle(((80, 24), (79, 24)))

    def create_and_close() -> int:
        width, height = next(sizes)
        canvas = xnano.new(width=width, height=height)
        canvas.close()
        return width

    assert benchmark.pedantic(create_and_close, rounds=100, iterations=1) in (79, 80)
    check_budget(
        lambda: minimum_microseconds(lambda: xnano.new().close(), number=300),
        CREATE_BUDGET_MICROSECONDS,
        'new() then close()',
    )


def test_writing_and_removing_text(benchmark):
    texts = itertools.cycle(('hi', 'ho'))
    with xnano.new() as canvas:

        def write_and_remove() -> int:
            placement = canvas.screen.write(next(texts))
            width = placement.width
            placement.remove()
            return width

        assert benchmark.pedantic(write_and_remove, rounds=200, iterations=1) == 2
        check_budget(
            lambda: minimum_microseconds(lambda: canvas.screen.write('hi').remove()),
            WRITE_BUDGET_MICROSECONDS,
            "write('hi') then remove()",
        )
