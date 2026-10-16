"""
benchmarks.test_canvas

Benchmarks for building a canvas and for drawing one frame of it.

Each timed call builds a new canvas or changes the frame, so a second call cannot reuse an
unchanged result. Setup stays outside the timed call.
"""

from __future__ import annotations

import itertools

import xnano
from xnano.effects import Effect
from xnano.operations import Border, Write
from xnano.widgets import Gauge


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
        return canvas.output.snapshot().lines()[0]

    try:
        line = benchmark.pedantic(draw, rounds=10, iterations=1)
    finally:
        canvas.close()
    assert 'left' in line or 'right' in line
