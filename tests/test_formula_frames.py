"""
tests.test_formula_frames

A canvas whose formulas do not read the clock goes idle, and one that does keeps drawing.
"""

from __future__ import annotations

import time

import pytest

import xnano
from xnano.canvas import Canvas
from xnano.expressions import ParentWidth, TimeElapsed, Width


@pytest.fixture
def frame_counter(monkeypatch):
    counter = {'frames': 0}
    original = Canvas._on_loop_frame

    def counting(self, core_context):
        counter['frames'] += 1
        return original(self, core_context)

    monkeypatch.setattr(Canvas, '_on_loop_frame', counting)
    return counter


# A canvas that keeps drawing passes this in any half second, even on a slow machine, while
# an idle canvas draws no frames at all.
KEEPS_DRAWING_FRAMES = 2


def frames_while_waiting(canvas, counter) -> int:
    time.sleep(0.3)
    before = counter['frames']
    time.sleep(0.5)
    return counter['frames'] - before


class TestFormulaFrames:
    def test_a_static_formula_leaves_the_canvas_idle(self, frame_counter):
        with xnano.new(width=40, height=5, realtime=True, fps=30) as canvas:
            placement = canvas.screen.write('ab')
            placement.x = ParentWidth - Width
            placement.width = Width + 0
            assert frames_while_waiting(canvas, frame_counter) == 0
            assert placement.x == 38

    def test_a_static_range_leaves_the_canvas_idle(self, frame_counter):
        with xnano.new(width=40, height=5, realtime=True, fps=30) as canvas:
            placement = canvas.screen.write('ab')
            placement.x = (0, ParentWidth - Width)
            assert frames_while_waiting(canvas, frame_counter) == 0

    def test_a_formula_that_reads_the_clock_keeps_drawing(self, frame_counter):
        with xnano.new(width=40, height=5, realtime=True, fps=30) as canvas:
            placement = canvas.screen.write('ab')
            placement.x = (ParentWidth - Width) * ((TimeElapsed / 2) % 1.0)
            assert frames_while_waiting(canvas, frame_counter) >= KEEPS_DRAWING_FRAMES

    def test_a_formula_that_reads_the_canvas_time_keeps_drawing(self, frame_counter):
        with xnano.new(width=40, height=5, realtime=True, fps=30) as canvas:
            placement = canvas.screen.write('ab')
            placement.x = (canvas.clock / 2 % 1.0) * 30
            assert frames_while_waiting(canvas, frame_counter) >= KEEPS_DRAWING_FRAMES

    def test_a_formula_that_reads_the_audio_beat_keeps_drawing(self, frame_counter):
        with xnano.new(width=40, height=5, realtime=True, fps=30) as canvas:
            placement = canvas.screen.write('ab')
            placement.x = (canvas.clock.beats.position % 1) * 19
            assert frames_while_waiting(canvas, frame_counter) >= KEEPS_DRAWING_FRAMES

    def test_a_formula_that_reads_the_audio_level_keeps_drawing(self, frame_counter):
        with xnano.new(width=40, height=5, realtime=True, fps=30) as canvas:
            placement = canvas.screen.write('ab')
            placement.x = canvas.microphone.level * 19
            assert frames_while_waiting(canvas, frame_counter) >= KEEPS_DRAWING_FRAMES
