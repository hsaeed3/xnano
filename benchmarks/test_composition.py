"""
benchmarks.test_composition

Benchmarks for composing a buffer and for drawing one frame of a terminal.

Each timed call builds a new composition or changes the frame, so a second call
cannot reuse an unchanged result. Setup stays outside the timed call.
"""

from __future__ import annotations

import itertools

import xnano
from xnano.effects import Effect
from xnano.operations import Border, Write
from xnano.widgets import Gauge


def test_make_builds_a_bordered_buffer(benchmark):
    widths = itertools.cycle((12, 14))

    def build() -> str:
        card = xnano.make(width=next(widths), height=3) | Border('rounded')
        return card.build().render(format='text')

    rendered = benchmark.pedantic(build, rounds=20, iterations=1)
    assert '╭' in rendered


def test_make_builds_a_gauge_with_an_effect(benchmark):
    ratios = itertools.cycle((0.25, 0.75))

    def build() -> float:
        gauge = xnano.make(Gauge, ratio=next(ratios), width=20, height=1)
        gauge |= Effect.fade_to('red', duration_milliseconds=80)
        ratio = gauge.ratio
        assert isinstance(ratio, float)
        return ratio

    ratio = benchmark.pedantic(build, rounds=20, iterations=1)
    assert ratio in (0.25, 0.75)


def test_a_terminal_draws_a_changed_frame(benchmark):
    terminal = xnano.open(offscreen=True, width=40, height=2, fps=60)
    texts = itertools.cycle(('left', 'right'))

    def draw() -> str:
        terminal.update(Write(next(texts), x=0, y=0))
        terminal.loop.advance(1 / 60)
        return terminal.output.snapshot().lines()[0]

    try:
        line = benchmark.pedantic(draw, rounds=10, iterations=1)
    finally:
        terminal.close()
    assert 'left' in line or 'right' in line
