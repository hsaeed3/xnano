"""
tests.test_async

The ``_async`` spellings of the canvas's waiting calls: they wait with ``await``, so the rest of
an event loop runs meanwhile, and they behave the way their blocking twins do.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Coroutine
from typing import TypeVar

import pytest

import xnano
from xnano.canvas import Canvas
from xnano.devices import Clock, Keyboard
from xnano.errors import TerminalError
from xnano.events import Event

ResultT = TypeVar('ResultT')


def run(coroutine: Coroutine[object, object, ResultT]) -> ResultT:
    return asyncio.run(coroutine)


async def count_while(
    waiting: Coroutine[object, object, ResultT],
) -> tuple[ResultT, int]:
    """Await ``waiting`` while another task counts, and return its result and the count."""
    ticks = [0]

    async def tick() -> None:
        while True:
            ticks[0] += 1
            await asyncio.sleep(0.005)

    ticker = asyncio.ensure_future(tick())
    try:
        result = await waiting
    finally:
        ticker.cancel()
    return result, ticks[0]


class TestTwins:
    @pytest.mark.parametrize(
        ('owner', 'blocking', 'awaiting'),
        [
            (Canvas, 'run', 'run_async'),
            (Canvas, 'iter', 'iter_async'),
            (Canvas, 'close', 'close_async'),
            (Canvas, 'open', 'open_async'),
            (Keyboard, 'wait', 'wait_async'),
            (Keyboard, 'prompt', 'prompt_async'),
            (Clock, 'sleep', 'sleep_async'),
        ],
    )
    def test_each_twin_takes_the_same_arguments(self, owner, blocking, awaiting):
        assert inspect.signature(getattr(owner, blocking)).parameters.keys() == (
            inspect.signature(getattr(owner, awaiting)).parameters.keys()
        )

    def test_the_module_level_open_has_a_twin(self):
        assert inspect.signature(xnano.open).parameters.keys() == (
            inspect.signature(xnano.open_async).parameters.keys()
        )


class TestAsyncWith:
    def test_leaving_the_block_closes_the_canvas(self):
        async def main() -> Canvas:
            async with xnano.new(width=8, height=1) as canvas:
                canvas.screen.write('hello')
                assert canvas.screen.render() == 'hello'
            return canvas

        assert run(main()).is_closed

    def test_a_canvas_that_runs_by_itself_closes_without_blocking_the_loop(self):
        async def main() -> int:
            canvas = xnano.new(realtime=True, width=8, height=1)
            await canvas.__aenter__()
            _, ticks = await count_while(canvas.__aexit__(None, None, None))
            assert canvas.is_closed
            return ticks

        assert run(main()) >= 1

    def test_the_canvas_is_active_inside_the_block(self):
        async def main() -> None:
            async with xnano.new(width=8, height=1) as canvas:
                assert xnano.active() is canvas
            assert xnano.active(is_required=False) is None

        run(main())

    def test_a_failing_hook_is_raised_when_the_block_ends(self):
        async def main() -> None:
            async with xnano.new(realtime=True, width=8, height=1) as canvas:

                @canvas.hook(on='tick')
                def fail(context: xnano.Context) -> None:
                    raise RuntimeError('boom')

                await asyncio.sleep(0.2)

        with pytest.raises(TerminalError, match='boom'):
            run(main())

    def test_close_async_twice_is_harmless(self):
        async def main() -> None:
            canvas = xnano.new(realtime=True, width=8, height=1)
            await canvas.close_async()
            await canvas.close_async()
            assert canvas.is_closed

        run(main())


class TestIterAsync:
    def test_a_manual_clock_yields_the_frames_iter_yields(self):
        with xnano.new(width=8, height=1, fps=10) as canvas:
            blocking = [frame.elapsed_seconds for frame in canvas.iter(frames=3)]

        async def main() -> list[float]:
            async with xnano.new(width=8, height=1, fps=10) as canvas:
                return [
                    frame.elapsed_seconds async for frame in canvas.iter_async(frames=3)
                ]

        assert run(main()) == blocking == [0.0, 0.1, 0.2]

    def test_seconds_ends_the_iteration(self):
        async def main() -> int:
            async with xnano.new(width=8, height=1, fps=10) as canvas:
                return len([frame async for frame in canvas.iter_async(seconds=0.5)])

        assert run(main()) == 5

    def test_changes_between_frames_are_drawn(self):
        async def main() -> list[str]:
            async with xnano.new(width=8, height=1) as canvas:
                label = canvas.screen.write('0')
                drawn = []
                async for frame in canvas.iter_async(frames=3):
                    label.text = str(frame.index)
                    drawn.append(canvas.screen.render())
                return drawn

        assert run(main()) == ['0', '1', '2']

    def test_bad_keywords_are_refused_when_called(self):
        with xnano.new(width=8, height=1) as canvas:
            with pytest.raises(ValueError, match='frames must be a whole number'):
                canvas.iter_async(frames=-1)
            with pytest.raises(ValueError, match='seconds must be a number above zero'):
                canvas.iter_async(seconds=0)

    def test_a_canvas_that_runs_by_itself_lets_other_tasks_run(self):
        async def main() -> int:
            async with xnano.new(realtime=True, width=8, height=1, fps=50) as canvas:

                async def frames() -> int:
                    return len([frame async for frame in canvas.iter_async(frames=5)])

                count, ticks = await count_while(frames())
                assert count == 5
                return ticks

        assert run(main()) >= 2

    def test_quit_ends_the_iteration(self):
        async def main() -> int:
            async with xnano.new(width=8, height=1) as canvas:
                count = 0
                async for _ in canvas.iter_async():
                    count += 1
                    if count == 4:
                        canvas.quit()
                return count

        assert run(main()) == 4


class TestRunAsync:
    def test_it_returns_when_the_canvas_quits(self):
        async def main() -> int:
            async with xnano.new(realtime=True, width=8, height=1) as canvas:

                @canvas.hook(on='tick', after=0.05)
                def finish(context: xnano.Context) -> None:
                    context.canvas.quit()

                _, ticks = await count_while(canvas.run_async())
                return ticks

        assert run(main()) >= 1

    def test_a_quit_key_ends_it(self):
        async def main() -> None:
            async with xnano.new(realtime=True, width=8, height=1) as canvas:

                @canvas.hook(on='tick', after=0.05)
                def press(context: xnano.Context) -> None:
                    canvas.push(Event.key_press('q'))

                await asyncio.wait_for(canvas.run_async(quit_on='q'), timeout=5)

        run(main())

    def test_a_manual_clock_is_refused_by_name(self):
        async def main() -> None:
            async with xnano.new(width=8, height=1) as canvas:
                await canvas.run_async()

        with pytest.raises(TerminalError, match=r'so run_async\(\) would wait forever'):
            run(main())

    def test_a_failing_hook_is_raised(self):
        async def main() -> None:
            async with xnano.new(realtime=True, width=8, height=1) as canvas:

                @canvas.hook(on='tick')
                def fail(context: xnano.Context) -> None:
                    raise RuntimeError('boom')

                await canvas.run_async()

        with pytest.raises(TerminalError, match='boom') as caught:
            run(main())
        assert caught.value.code == 'canvas.callback'

    def test_cancelling_the_wait_quits_the_canvas(self):
        async def main() -> bool:
            canvas = xnano.new(realtime=True, width=8, height=1)
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(canvas.run_async(), timeout=0.1)
            is_running = canvas.is_running
            await canvas.close_async()
            return is_running

        assert run(main()) is False


class TestWaitingForInput:
    def test_wait_for_key_async_returns_the_key(self):
        async def main() -> tuple[object, int]:
            async with xnano.new(realtime=True, width=20, height=1) as canvas:

                @canvas.hook(on='tick', after=0.05)
                def press(context: xnano.Context) -> None:
                    canvas.push(Event.key_press('a'))
                    canvas.push(Event.key_press('enter'))

                return await count_while(canvas.keyboard.wait_async('enter'))

        key, ticks = run(main())
        assert key == 'enter'
        assert ticks >= 1

    def test_a_cancelled_wait_leaves_no_hook_behind(self):
        async def main() -> None:
            async with xnano.new(realtime=True, width=20, height=1) as canvas:
                before = len(canvas._registrations)
                with pytest.raises(asyncio.TimeoutError):
                    await asyncio.wait_for(canvas.keyboard.wait_async(), timeout=0.05)
                assert len(canvas._registrations) == before

        run(main())

    def test_the_canvas_ending_ends_the_wait(self):
        async def main() -> None:
            async with xnano.new(realtime=True, width=20, height=1) as canvas:

                @canvas.hook(on='tick', after=0.05)
                def finish(context: xnano.Context) -> None:
                    context.canvas.quit()

                await canvas.keyboard.wait_async()

        with pytest.raises(TerminalError, match='ended while waiting for a key'):
            run(main())

    def test_a_manual_clock_cannot_wait_for_a_key(self):
        async def main() -> None:
            async with xnano.new(width=20, height=1) as canvas:
                await canvas.keyboard.wait_async()

        with pytest.raises(TerminalError, match='never moves by itself'):
            run(main())

    def test_prompt_async_returns_what_was_typed_and_takes_the_prompt_away(self):
        async def main() -> tuple[str, str]:
            async with xnano.new(realtime=True, width=30, height=2) as canvas:

                @canvas.hook(on='tick', after=0.05)
                def type_answer(context: xnano.Context) -> None:
                    for letter in 'Adaa':
                        canvas.push(Event.key_press(letter))
                    canvas.push(Event.key_press('backspace'))
                    canvas.push(Event.key_press('enter'))

                answer = await canvas.keyboard.prompt_async('Name: ', default='')
                return answer, canvas.screen.render()

        answer, screen = run(main())
        assert answer == 'Ada'
        assert 'Name:' not in screen


class TestOpenAsync:
    def test_nothing_opens_until_it_is_awaited(self):
        with xnano.new(width=8, height=1) as canvas:
            opening = canvas.open_async()
            assert not isinstance(canvas, xnano.Terminal)
            assert opening.terminal is None

    def test_an_error_is_raised_when_it_is_awaited(self):
        async def main() -> None:
            await xnano.open_async(realtime=True)

        opening = xnano.open_async(realtime=True)
        del opening
        with pytest.raises(TypeError, match=r'open_async\(\) takes no realtime'):
            run(main())
