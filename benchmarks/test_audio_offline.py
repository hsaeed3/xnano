"""
benchmarks.test_audio_offline

Benchmarks for sound on a canvas whose clock you move: playing records a description, and
``render_sound()`` mixes what overlaps the window with the native mixer.

Measured on Apple M-series, Python 3.11 (the first row is Python work only, the second was
measured on a debug build and is lower on an optimized one):

| Case | Time |
| --- | --- |
| ``play(note)`` on a canvas without a device | 6.5 us |
| ``render_sound()`` of one second with four cached notes | 2100 us (debug) |

The budgets below are asserted only when ``XNANO_CHECK_BUDGETS=1`` is set on an optimized
build outside CodSpeed (``make benchmark-xnano`` does it).
"""

from __future__ import annotations

import time

from benchmark_budgets import check_budget

import xnano

PLAY_BUDGET_MICROSECONDS = 12.0
"""Recording a note costs a description, not a synthesis."""

MIX_BUDGET_MICROSECONDS = 2000.0
"""One second of four cached layers mixes natively, far below the 14 ms of a Python mix."""

NOTES = ('C4', 'E4', 'G4', 'C5')


def minimum_microseconds(function, *, number: int, repeat: int = 7) -> float:
    """The fastest of several runs of a loop, per call, in microseconds."""
    results = []
    for _ in range(repeat):
        start = time.perf_counter()
        for _ in range(number):
            function()
        results.append((time.perf_counter() - start) / number * 1e6)
    return min(results)


def test_playing_a_note_records_it_without_synthesizing(benchmark):
    note = xnano.Note('C4', beats=0.5)
    with xnano.new(width=8, height=1) as canvas:

        def play() -> int:
            canvas.speaker.play(note)
            return len(canvas._audio_device()._recordings)

        assert benchmark.pedantic(play, rounds=200, iterations=10) > 0
        canvas._audio_device()._recordings.clear()
        check_budget(
            lambda: minimum_microseconds(play, number=500),
            PLAY_BUDGET_MICROSECONDS,
            'canvas.speaker.play(note) without a device',
        )


def test_rendering_a_second_of_four_cached_notes(benchmark):
    notes = [xnano.Note(pitch, beats=2.0) for pitch in NOTES]
    with xnano.new(width=8, height=1, fps=1) as canvas:

        def render() -> float:
            canvas.speaker.play(notes[:1])
            for note in notes[1:]:
                canvas.speaker.play(note)
            canvas.clock.step()
            return canvas.speaker.render().duration_milliseconds

        render()
        assert benchmark.pedantic(render, rounds=30, iterations=1) == 1000.0
        check_budget(
            lambda: minimum_microseconds(render, number=10),
            MIX_BUDGET_MICROSECONDS,
            'render_sound() of one second with four cached notes',
        )
