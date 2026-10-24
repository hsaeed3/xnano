"""
tests.test_time_sleep

``canvas.clock.sleep()``: waiting for the canvas's own time to pass, on a canvas that runs by
itself and on one whose clock you move.
"""

from __future__ import annotations

import asyncio
import threading
import time

import pytest

import xnano
from xnano.errors import TerminalError


class TestManualClock:
    def test_the_clock_moves_by_the_seconds_frame_by_frame(self):
        with xnano.new(width=8, height=1, fps=10) as canvas:
            ticks: list[float] = []
            canvas.hook(
                lambda context: ticks.append(context.clock.elapsed), on='tick', every=0.5
            )
            canvas.clock.sleep(2)
            assert round(canvas.clock.elapsed, 6) == 2.0
            assert canvas.clock.frame == 20
            assert [round(tick, 6) for tick in ticks] == [0.5, 1.0, 1.5, 2.0]

    def test_a_time_between_frames_moves_by_the_rest_at_the_end(self):
        with xnano.new(width=8, height=1, fps=10) as canvas:
            canvas.clock.sleep(0.25)
            assert round(canvas.clock.elapsed, 6) == 0.25
            assert canvas.clock.frame == 3

    def test_an_animation_moves_while_it_sleeps(self):
        with xnano.new(width=20, height=1, fps=10) as canvas:
            ball = canvas.screen.write('o', y=0)
            ball.x = canvas.clock.seconds * 4
            canvas.clock.sleep(1)
            assert ball.x == 4

    def test_zero_seconds_is_no_wait(self):
        with xnano.new(width=8, height=1) as canvas:
            canvas.clock.sleep(0)
            assert canvas.clock.elapsed == 0.0

    def test_a_stopped_manual_clock_would_never_move(self):
        with xnano.new(width=8, height=1) as canvas:
            canvas.clock.stop()
            with pytest.raises(TerminalError, match='would never end'):
                canvas.clock.sleep(1)

    @pytest.mark.parametrize('seconds', [-1, float('nan'), float('inf'), 'soon', True])
    def test_seconds_must_be_a_finite_number_of_zero_or_more(self, seconds):
        with xnano.new(width=8, height=1) as canvas:
            with pytest.raises(ValueError, match='sleep\\(\\) takes the seconds to wait'):
                canvas.clock.sleep(seconds)

    def test_the_awaited_spelling_moves_the_clock_too(self):
        async def main() -> float:
            async with xnano.new(width=8, height=1, fps=10) as canvas:
                await canvas.clock.sleep_async(1)
                return round(canvas.clock.elapsed, 6)

        assert asyncio.run(main()) == 1.0


class TestRealtime:
    def test_it_waits_for_the_canvas_time_to_pass(self):
        with xnano.new(realtime=True, width=8, height=1) as canvas:
            start = time.monotonic()
            before = canvas.clock.elapsed
            canvas.clock.sleep(0.1)
            assert time.monotonic() - start >= 0.1
            assert canvas.clock.elapsed - before >= 0.1

    def test_stopped_time_does_not_count(self):
        with xnano.new(realtime=True, width=8, height=1) as canvas:
            canvas.clock.stop()
            resumed = threading.Timer(0.15, canvas.clock.resume)
            resumed.start()
            start = time.monotonic()
            canvas.clock.sleep(0.05)
            resumed.join()
            assert time.monotonic() - start >= 0.15

    def test_quitting_ends_the_wait(self):
        with xnano.new(realtime=True, width=8, height=1) as canvas:
            threading.Timer(0.05, canvas.quit).start()
            start = time.monotonic()
            canvas.clock.sleep(10)
            assert time.monotonic() - start < 5

    def test_a_hook_that_sleeps_is_refused(self):
        messages: list[str] = []
        heard = threading.Event()
        with xnano.new(realtime=True, width=8, height=1) as canvas:

            @canvas.hook(on='tick', after=0.0)
            def wait(context: xnano.Context) -> None:
                try:
                    context.clock.sleep(1)
                except TerminalError as error:
                    messages.append(str(error))
                heard.set()

            assert heard.wait(5)
        assert 'freeze the screen' in messages[0]
        assert "on='tick' and after=1" in messages[0]

    def test_the_awaited_spelling_lets_other_tasks_run(self):
        async def main() -> int:
            async with xnano.new(realtime=True, width=8, height=1) as canvas:
                counted = [0]

                async def count() -> None:
                    while True:
                        counted[0] += 1
                        await asyncio.sleep(0.005)

                counter = asyncio.ensure_future(count())
                await canvas.clock.sleep_async(0.05)
                counter.cancel()
                return counted[0]

        assert asyncio.run(main()) >= 2

    def test_an_async_hook_may_sleep(self):
        async def main() -> list[str]:
            async with xnano.new(realtime=True, width=8, height=1) as canvas:
                steps: list[str] = []

                @canvas.hook(on='tick', after=0.0)
                async def later(context: xnano.Context) -> None:
                    steps.append('start')
                    await context.clock.sleep_async(0.05)
                    steps.append('after')

                await asyncio.sleep(0.02)
                await canvas.wait_for_tasks_async()
                return steps

        assert asyncio.run(main()) == ['start', 'after']


def test_a_closed_canvas_cannot_sleep():
    canvas = xnano.new(width=8, height=1)
    canvas.close()
    with pytest.raises(TerminalError):
        canvas.clock.sleep(1)
