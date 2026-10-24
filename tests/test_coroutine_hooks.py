"""
tests.test_coroutine_hooks

Hooks written with ``async def``: they run on the canvas's event loop while it goes on
drawing, ``if_running`` says what a new run does to one that has not finished, and a failure
ends the canvas the way a failing plain hook does.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from typing import TypeVar

import pytest

import xnano
from xnano.errors import TerminalError
from xnano.events import Event

ResultT = TypeVar('ResultT')


def run(coroutine: Coroutine[object, object, ResultT]) -> ResultT:
    return asyncio.run(coroutine)


def press(canvas: xnano.Canvas, *keys: str) -> None:
    for key in keys:
        canvas.push(Event.key_press(key))
    canvas.clock.step()


class TestRunning:
    def test_a_run_changes_the_canvas_after_it_awaits(self):
        async def main() -> str:
            async with xnano.new(width=20, height=1) as canvas:
                label = canvas.screen.write('...')

                @canvas.hook(on='key', keys='enter')
                async def answer(context: xnano.Context) -> None:
                    await asyncio.sleep(0.01)
                    label.text = 'answered'

                press(canvas, 'enter')
                assert canvas.screen.render() == '...'
                await canvas.wait_for_tasks_async()
                return canvas.screen.render()

        assert run(main()) == 'answered'

    def test_the_context_is_still_readable_after_an_await(self):
        async def main() -> list[str | None]:
            async with xnano.new(width=20, height=1) as canvas:
                heard: list[str | None] = []

                @canvas.hook(on='key', if_running='overlap')
                async def remember(context: xnano.Context) -> None:
                    await asyncio.sleep(0)
                    heard.append(context.keyboard.key)

                press(canvas, 'a', 'b')
                await canvas.wait_for_tasks_async()
                return heard

        assert run(main()) == ['a', 'b']

    def test_a_function_without_parameters_may_be_async(self):
        async def main() -> list[int]:
            async with xnano.new(width=20, height=1) as canvas:
                runs: list[int] = []

                @canvas.hook(on='key')
                async def count() -> None:
                    runs.append(1)

                press(canvas, 'a')
                await canvas.wait_for_tasks_async()
                return runs

        assert run(main()) == [1]

    def test_waiting_with_nothing_running_returns_at_once(self):
        async def main() -> None:
            async with xnano.new(width=8, height=1) as canvas:
                await asyncio.wait_for(canvas.wait_for_tasks_async(), timeout=1)

        run(main())

    def test_a_reusable_hook_may_be_async(self):
        runs: list[str] = []

        @xnano.hook(on='key', if_running='queue')
        async def note(context: xnano.Context) -> None:
            await asyncio.sleep(0)
            runs.append(str(context.keyboard.key))

        async def main() -> None:
            async with xnano.new(width=8, height=1) as canvas:
                canvas.screen | note
                press(canvas, 'x', 'y')
                await canvas.wait_for_tasks_async()

        run(main())
        assert runs == ['x', 'y']


class TestIfRunning:
    @staticmethod
    def runs_of(if_running: str) -> tuple[list[str], int]:
        """Press three keys while each run waits, and return what finished and the overlap."""

        async def main() -> tuple[list[str], int]:
            async with xnano.new(width=8, height=1) as canvas:
                finished: list[str] = []
                active = [0, 0]

                @canvas.hook(on='key', if_running=if_running)  # type: ignore[arg-type]
                async def slow(context: xnano.Context) -> None:
                    active[0] += 1
                    active[1] = max(active)
                    try:
                        await asyncio.sleep(0.02)
                        finished.append(str(context.keyboard.key))
                    finally:
                        active[0] -= 1

                for key in 'abc':
                    press(canvas, key)
                    await asyncio.sleep(0)
                await canvas.wait_for_tasks_async()
                return finished, active[1]

        return run(main())

    def test_replace_lets_the_latest_run_finish(self):
        assert self.runs_of('replace') == (['c'], 1)

    def test_ignore_keeps_the_first_run(self):
        assert self.runs_of('ignore') == (['a'], 1)

    def test_queue_runs_them_one_after_the_other_in_order(self):
        assert self.runs_of('queue') == (['a', 'b', 'c'], 1)

    def test_overlap_runs_them_together(self):
        finished, most = self.runs_of('overlap')
        assert sorted(finished) == ['a', 'b', 'c']
        assert most == 3

    def test_replace_is_the_default(self):
        async def main() -> list[str]:
            async with xnano.new(width=8, height=1) as canvas:
                finished: list[str] = []

                @canvas.hook(on='key')
                async def slow(context: xnano.Context) -> None:
                    await asyncio.sleep(0.02)
                    finished.append(str(context.keyboard.key))

                press(canvas, 'a')
                await asyncio.sleep(0)
                press(canvas, 'b')
                await canvas.wait_for_tasks_async()
                return finished

        assert run(main()) == ['b']

    def test_an_unknown_word_names_the_closest(self):
        with xnano.new(realtime=True, width=8, height=1) as canvas:
            with pytest.raises(ValueError, match=r"if_running must be one of.*'queue'"):
                canvas.hook(lambda context: None, on='key', if_running='queu')  # type: ignore[arg-type]

    def test_it_is_refused_for_a_plain_function(self):
        with xnano.new(realtime=True, width=8, height=1) as canvas:
            with pytest.raises(ValueError, match='is a plain function'):
                canvas.hook(lambda context: None, on='key', if_running='queue')
            with pytest.raises(ValueError, match='is a plain function'):
                xnano.hook(lambda context: None, on='key', if_running='ignore')  # type: ignore[call-overload]


class TestEnding:
    def test_a_failing_run_ends_the_canvas(self):
        async def main() -> None:
            async with xnano.new(width=8, height=1) as canvas:

                @canvas.hook(on='key')
                async def broken(context: xnano.Context) -> None:
                    await asyncio.sleep(0)
                    raise RuntimeError('boom')

                press(canvas, 'a')
                await canvas.wait_for_tasks_async()

        with pytest.raises(TerminalError, match=r'The hook broken failed.*boom'):
            run(main())

    def test_a_failing_run_ends_a_canvas_that_runs_by_itself(self):
        async def main() -> None:
            async with xnano.new(realtime=True, width=8, height=1) as canvas:

                @canvas.hook(on='key')
                async def broken(context: xnano.Context) -> None:
                    raise RuntimeError('boom')

                @canvas.hook(on='tick', after=0.02)
                def press_a(context: xnano.Context) -> None:
                    canvas.push(Event.key_press('a'))

                await asyncio.wait_for(canvas.run_async(quit_on=None), timeout=5)

        with pytest.raises(TerminalError, match=r'The hook broken failed.*boom'):
            run(main())

    def test_removing_the_hook_cancels_its_run(self):
        async def main() -> list[str]:
            async with xnano.new(width=8, height=1) as canvas:
                ended: list[str] = []

                @canvas.hook(on='key')
                async def slow(context: xnano.Context) -> None:
                    try:
                        await asyncio.sleep(10)
                        ended.append('finished')
                    except asyncio.CancelledError:
                        ended.append('cancelled')
                        raise

                press(canvas, 'a')
                await asyncio.sleep(0)
                slow.remove()
                await asyncio.wait_for(canvas.wait_for_tasks_async(), timeout=2)
                return ended

        assert run(main()) == ['cancelled']

    def test_closing_the_canvas_cancels_the_runs(self):
        async def main() -> list[str]:
            ended: list[str] = []
            canvas = xnano.new(width=8, height=1)
            async with canvas:

                @canvas.hook(on='key')
                async def slow(context: xnano.Context) -> None:
                    try:
                        await asyncio.sleep(10)
                    except asyncio.CancelledError:
                        ended.append('cancelled')
                        raise

                press(canvas, 'a')
                await asyncio.sleep(0)
            await asyncio.sleep(0)
            await asyncio.wait_for(canvas.wait_for_tasks_async(), timeout=2)
            return ended

        assert run(main()) == ['cancelled']

    def test_a_cancelled_run_is_not_a_failure(self):
        async def main() -> bool:
            async with xnano.new(width=8, height=1) as canvas:

                @canvas.hook(on='key')
                async def slow(context: xnano.Context) -> None:
                    await asyncio.sleep(10)

                press(canvas, 'a')
                await asyncio.sleep(0)
                press(canvas, 'b')
                await asyncio.sleep(0)
                slow.remove()
                await canvas.wait_for_tasks_async()
                return canvas.is_running

        assert run(main()) is True


class TestLoops:
    def test_a_manual_canvas_outside_a_coroutine_has_no_loop(self):
        with xnano.new(width=8, height=1) as canvas:
            with pytest.raises(TerminalError, match='no event loop') as caught:

                @canvas.hook(on='key')
                async def answer(context: xnano.Context) -> None:
                    pass

        assert caught.value.code == 'canvas.loop'

    def test_entering_it_with_async_with_gives_it_one(self):
        canvas = xnano.new(width=8, height=1)

        async def main() -> list[int]:
            runs: list[int] = []
            async with canvas:

                @canvas.hook(on='key')
                async def answer(context: xnano.Context) -> None:
                    runs.append(1)

                press(canvas, 'a')
                await canvas.wait_for_tasks_async()
            return runs

        assert run(main()) == [1]

    def test_a_canvas_that_runs_by_itself_uses_a_background_loop(self):
        finished = threading.Event()
        threads: list[str] = []
        with xnano.new(realtime=True, width=20, height=1) as canvas:
            label = canvas.screen.write('...')

            @canvas.hook(on='key')
            async def answer(context: xnano.Context) -> None:
                await asyncio.sleep(0.01)
                label.text = 'answered'
                threads.append(threading.current_thread().name)
                finished.set()

            canvas.push(Event.key_press('a'))
            assert finished.wait(5)
            assert canvas.screen.render() == 'answered'
        assert threads == ['xnano-event-loop']

    def test_a_run_may_end_the_canvas(self):
        async def main() -> None:
            async with xnano.new(realtime=True, width=8, height=1) as canvas:

                @canvas.hook(on='key', keys='q')
                async def leave(context: xnano.Context) -> None:
                    await asyncio.sleep(0.01)
                    context.canvas.quit()

                @canvas.hook(on='tick', after=0.05)
                def press_q(context: xnano.Context) -> None:
                    canvas.push(Event.key_press('q'))

                await asyncio.wait_for(canvas.run_async(quit_on=None), timeout=5)

        run(main())

    def test_an_async_hook_cannot_follow_state(self):
        async def main() -> None:
            async with xnano.new(width=8, height=1) as canvas:

                @canvas.hook(on='state')
                async def follow(context: xnano.Context) -> None:
                    pass

        with pytest.raises(ValueError, match="cannot follow state with on='state'"):
            run(main())
