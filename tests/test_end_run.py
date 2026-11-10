"""
tests.test_end_run

``run()`` can return while the canvas stays open: a key of ``end_on`` or ``end_run()`` ends
the run, and the program goes on with a canvas that still draws and listens.
"""

from __future__ import annotations

import asyncio
import sys
import threading

import pytest

import xnano
from xnano.errors import TerminalError


def press_after(canvas: xnano.Canvas, key: str, seconds: float = 0.05) -> None:
    """Press ``key`` on ``canvas`` once, ``seconds`` after now."""

    @canvas.hook(on='tick', after=seconds)
    def press(context: xnano.Context) -> None:
        context.keyboard.press(key)


def test_end_run_from_a_hook_returns_and_leaves_the_canvas_open():
    with xnano.new(realtime=True, width=20, height=1) as canvas:
        label = canvas.write('loading...')

        @canvas.hook(on='tick', after=0.05)
        def loaded(context: xnano.Context) -> None:
            context.canvas.end_run()

        canvas.run()
        assert canvas.is_running
        assert not canvas.is_closed
        label.text = 'ready'
        assert canvas.render() == 'ready'


def test_end_run_from_another_thread_ends_the_run():
    with xnano.new(realtime=True, width=20, height=1) as canvas:
        timer = threading.Timer(0.05, canvas.end_run)
        timer.start()
        canvas.run()
        timer.join()
        assert canvas.is_running


def test_a_key_of_end_on_ends_the_run():
    with xnano.new(realtime=True, width=20, height=1) as canvas:
        press_after(canvas, 'enter')
        canvas.run(end_on='enter')
        assert canvas.is_running


def test_the_canvas_runs_again_after_a_run_ended():
    with xnano.new(realtime=True, width=20, height=1) as canvas:
        heard = []
        canvas.hook(lambda context: heard.append(context.keyboard.key), on='key')
        press_after(canvas, 'enter')
        canvas.run(end_on=('enter', 'space'))
        press_after(canvas, 'space')
        canvas.run(end_on=('enter', 'space'))
        assert heard == ['enter', 'space']
        press_after(canvas, 'q')
        canvas.run(stop_on='q')
        assert not canvas.is_running


def test_an_end_key_only_ends_the_run_it_was_given_to():
    with xnano.new(realtime=True, width=20, height=1) as canvas:
        press_after(canvas, 'enter')
        canvas.run(end_on='enter')
        # `enter` no longer ends anything, and the stop key of the first run is forgotten too.
        press_after(canvas, 'enter', 0.02)
        press_after(canvas, 'q', 0.04)
        press_after(canvas, 'space', 0.1)
        canvas.run(stop_on='x', end_on='space')
        assert canvas.is_running


def test_a_stop_key_still_stops_the_canvas_when_end_keys_are_given():
    with xnano.new(realtime=True, width=20, height=1) as canvas:
        press_after(canvas, 'q')
        canvas.run(stop_on='q', end_on='enter')
        assert not canvas.is_running


def test_end_run_does_nothing_when_no_run_is_waiting():
    with xnano.new(realtime=True, width=20, height=1) as canvas:
        canvas.end_run()
        press_after(canvas, 'enter', 0.1)
        ended_by_key = []
        canvas.hook(lambda context: ended_by_key.append(True), on='key', keys='enter')
        canvas.run(end_on='enter')
        assert ended_by_key == [True]


def test_end_run_does_nothing_on_a_canvas_with_a_manual_clock():
    with xnano.new(width=20, height=1) as canvas:
        canvas.end_run()
        assert canvas.is_running


def test_a_key_in_both_stop_on_and_end_on_is_refused():
    with xnano.new(realtime=True, width=20, height=1) as canvas:
        with pytest.raises(ValueError, match="'q'.*stop_on.*end_on"):
            canvas.run(stop_on=('q', 'escape'), end_on='q')
        assert canvas.is_running


def test_a_hook_that_raises_still_ends_the_run_with_its_error():
    with pytest.raises(TerminalError):
        with xnano.new(realtime=True, width=20, height=1) as canvas:

            @canvas.hook(on='tick', after=0.05)
            def fail(context: xnano.Context) -> None:
                raise RuntimeError('broken hook')

            canvas.run(end_on='enter')


def test_run_async_ends_with_end_run_and_with_an_end_key():
    async def main() -> None:
        async with xnano.new(realtime=True, width=20, height=1) as canvas:

            @canvas.hook(on='tick', after=0.05)
            def loaded(context: xnano.Context) -> None:
                context.canvas.end_run()

            await asyncio.wait_for(canvas.run_async(), timeout=5)
            assert canvas.is_running
            press_after(canvas, 'enter')
            await asyncio.wait_for(canvas.run_async(end_on='enter'), timeout=5)
            assert canvas.is_running
            press_after(canvas, 'q')
            await asyncio.wait_for(canvas.run_async(stop_on='q'), timeout=5)
            assert not canvas.is_running

    asyncio.run(main())


@pytest.mark.skipif(sys.platform == 'win32', reason='needs a pseudo-terminal')
def test_a_live_terminal_keeps_its_screen_between_two_runs():
    pytest.importorskip('pyte')
    from emulator import Screen

    screen = Screen(
        """
with xnano.open() as terminal:
    message = terminal.write('step one')
    terminal.run(stop_on='q', end_on='enter')
    message.text = 'step two'
    terminal.run(stop_on='q')
print('DONE')
""",
        rows=6,
        columns=30,
    )
    try:
        assert screen.wait_for('step one')
        screen.press('enter')
        assert screen.wait_for('step two'), screen.text
        assert 'DONE' not in screen.text
        screen.press('q')
        assert screen.finish() == 0
        assert 'DONE' in screen.text
        assert 'step two' not in screen.text
    finally:
        screen.close()
