"""
benchmarks.test_canvas

Benchmarks for building a canvas and for drawing one frame of it.

Each timed call builds a new canvas or changes the frame, so a second call cannot reuse an
unchanged result. Setup stays outside the timed call.
"""

from __future__ import annotations

import itertools
import time

from benchmark_budgets import check_budget

import xnano
from xnano.operations import Border, Effect, Write
from xnano.widgets import Gauge
from xnano_core import Event


def test_new_builds_a_bordered_canvas(benchmark):
    widths = itertools.cycle((12, 14))

    def build() -> str:
        with xnano.new(width=next(widths), height=3) as canvas:
            canvas.update(Border('rounded'))
            return canvas.render()

    rendered = benchmark.pedantic(build, rounds=20, iterations=1)
    assert '╭' in rendered


def test_new_builds_a_canvas_with_a_gauge_and_an_effect(benchmark):
    ratios = itertools.cycle((0.25, 0.75))

    def build() -> str:
        with xnano.new(width=20, height=1) as canvas:
            gauge = canvas.write(Gauge(next(ratios), width=20, height=1))
            gauge.update(Effect.fade_to('red', duration_milliseconds=80))
            canvas.step(delta_seconds=0.1)
            return canvas.render()

    rendered = benchmark.pedantic(build, rounds=20, iterations=1)
    assert '█' in rendered or '▌' in rendered


def test_a_canvas_draws_a_changed_frame(benchmark):
    canvas = xnano.new(width=40, height=2, fps=60)
    texts = itertools.cycle(('left', 'right'))

    def draw() -> str:
        canvas.update(Write(next(texts), x=0, y=0))
        canvas.step(delta_seconds=1 / 60)
        return canvas.output.lines()[0]

    try:
        line = benchmark.pedantic(draw, rounds=10, iterations=1)
    finally:
        canvas.close()
    assert 'left' in line or 'right' in line


# -- decoration ---------------------------------------------------------------------------
#
# Budgets, set against a release build without coverage instrumentation (Apple M-series,
# Python 3.11): `write('hi', border='rounded')` plus `remove()` takes 12 us; 200 bordered
# text placements on a 200 by 50 canvas draw a frame in 238 us and take 239 us for a pointer
# move plus a step. Text with a uniform border is one buffer, so the budgets are 1.3 times the
# first figure and 1.1 times the other two. The same screen with a border on a different
# side of every placement uses two buffers each; it is recorded and has no budget.

CREATE_BUDGET_MICROSECONDS = 15.6
FRAME_BUDGET_MICROSECONDS = 262.0
POINTER_BUDGET_MICROSECONDS = 263.0
PLACEMENTS = 200


def fastest_microseconds(function, *, rounds: int = 30) -> float:
    results = []
    for _ in range(rounds):
        start = time.perf_counter()
        function()
        results.append((time.perf_counter() - start) * 1e6)
    return min(results)


def test_a_bordered_text_is_written_and_removed(benchmark):
    with xnano.new(width=40, height=10) as canvas:

        def write_and_remove() -> None:
            canvas.write('hi', border='rounded').remove()

        benchmark.pedantic(write_and_remove, rounds=50, iterations=20)
        check_budget(
            lambda: fastest_microseconds(write_and_remove),
            CREATE_BUDGET_MICROSECONDS,
            'write with a border',
        )


def _screen_of_cards(canvas, *, has_side_override: bool) -> list:
    cards = []
    for index in range(PLACEMENTS):
        card = canvas.write('ab', x=(index % 40) * 5, y=(index // 40) * 3, border='plain')
        if has_side_override:
            card.border.top = 'double'
        cards.append(card)
    canvas.step()
    return cards


def test_a_frame_of_bordered_text_placements(benchmark):
    with xnano.new(width=200, height=50) as canvas:
        cards = _screen_of_cards(canvas, has_side_override=False)
        assert all(card._decorated is None for card in cards)
        colors = itertools.cycle(('red', 'blue'))

        def change_and_draw() -> None:
            cards[0].color.fg = next(colors)
            canvas.step()

        benchmark.pedantic(change_and_draw, rounds=30, iterations=1)
        check_budget(
            lambda: fastest_microseconds(change_and_draw),
            FRAME_BUDGET_MICROSECONDS,
            'a frame of 200 cards',
        )


def test_a_pointer_move_over_bordered_text_placements(benchmark):
    with xnano.new(width=200, height=50) as canvas:
        _screen_of_cards(canvas, has_side_override=False)
        columns = itertools.cycle((3, 4))

        def move_and_step() -> None:
            canvas.push(Event.mouse_event(column=next(columns), row=1, kind='move'))
            canvas.step()

        benchmark.pedantic(move_and_step, rounds=30, iterations=1)
        check_budget(
            lambda: fastest_microseconds(move_and_step),
            POINTER_BUDGET_MICROSECONDS,
            'a pointer move',
        )


def test_a_frame_of_text_placements_with_two_buffers_is_recorded(benchmark):
    with xnano.new(width=200, height=50) as canvas:
        cards = _screen_of_cards(canvas, has_side_override=True)
        assert all(card._decorated is not None for card in cards)
        colors = itertools.cycle(('red', 'blue'))

        def change_and_draw() -> None:
            cards[0].color.fg = next(colors)
            canvas.step()

        benchmark.pedantic(change_and_draw, rounds=30, iterations=1)
