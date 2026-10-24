"""
xnano.devices._clock

The clock of a terminal: how long it has run, whether it is stopped, the rate it draws at, its
tempo and musical beats, and the formulas that follow it.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Final

import xnano_core as _core

if TYPE_CHECKING:
    from xnano.canvas import Canvas
    from xnano.hooks._context import Frame

__all__ = ['Beats', 'Clock']

_STOPPED_POLL: Final = 0.05
"""How often, in seconds, a wait on a stopped clock looks whether time runs again."""


class Clock:
    """
    The clock of a terminal: the time everything that moves follows.

    Get it from [`Canvas.clock`][xnano.canvas.Canvas.clock], or from ``context.clock`` inside
    a hook. Animations, effects, formulas, [`hook`][xnano.canvas.Canvas.hook] timers (``every``
    and ``after``), fixed-step updates, the frame rate and the musical beat all follow it. Any
    thread may read it. Used in arithmetic it is the formula for
    [`seconds`][xnano.devices.Clock.seconds], so ``canvas.clock / 2`` is a value that follows
    the clock. [`stop`][xnano.devices.Clock.stop] freezes all of them while input keeps
    arriving, [`step`][xnano.devices.Clock.step] moves a clock one frame at a time, and
    [`sleep`][xnano.devices.Clock.sleep] waits until some of its time has passed.

    ``elapsed``, ``delta`` and ``measured_fps`` are numbers you read now; ``seconds`` and
    ``milliseconds`` are formulas that a placement keeps following. A
    [`Frame`][xnano.hooks.Frame] carries the same numbers as ``elapsed_seconds`` and
    ``delta_seconds``. ``fps`` is the most frames the canvas draws per second, and
    ``measured_fps`` the rate it reached over recent frames.

    Attributes:
        elapsed: Seconds since the canvas started, not counting time spent stopped.
        elapsed_milliseconds: The same, in milliseconds.
        delta: Seconds between the two most recent frames.
        frame: The number of steps the clock has counted.
        fps: The most frames drawn per second, and the rate ``iter`` aims for.
        measured_fps: The frame rate measured over recent frames.
        bpm: Beats per minute: the length of a beat for beat timers, notes and melodies.
        beats: The musical clock: its position in beats, started and stopped on its own.
        is_stopped: Whether time is frozen.
        is_realtime: Whether time follows the wall clock. A canvas from ``xnano.new()``
            without ``realtime=True`` moves only when you move it.
        seconds: A formula for [`elapsed`][xnano.devices.Clock.elapsed], recomputed every frame.
        milliseconds: A formula for
            [`elapsed_milliseconds`][xnano.devices.Clock.elapsed_milliseconds].

    Examples:
        ```python
        import xnano

        with xnano.new(width=20, height=1) as canvas:
            ball = canvas.screen.write('o')
            ball.x = (canvas.screen.width - 1) * ((canvas.clock.seconds / 2) % 1.0)
            canvas.clock.step(delta_seconds=1.0)
            assert canvas.clock.elapsed == 1.0
            canvas.clock.stop()
            assert canvas.clock.is_stopped
            canvas.clock.step(delta_seconds=0.5)
            assert canvas.clock.elapsed == 1.5
        ```
    """

    def __init__(self, canvas: Canvas[object, object]) -> None:
        """
        Create the canvas's clock. Use ``canvas.clock`` instead of calling this.

        Args:
            canvas: The root canvas the clock belongs to.
        """
        self._canvas = canvas

    @property
    def elapsed(self) -> float:
        """Seconds since the canvas started, not counting time spent stopped."""
        return self._canvas._time_source.elapsed_seconds

    @property
    def elapsed_milliseconds(self) -> float:
        """Milliseconds since the canvas started, not counting time spent stopped."""
        return self._canvas._time_source.elapsed_milliseconds

    @property
    def delta(self) -> float:
        """Seconds between the two most recent frames."""
        return self._canvas._time_source.delta_seconds

    @property
    def frame(self) -> int:
        """The number of steps the clock has counted, including steps that drew nothing."""
        return self._canvas._time_source.frame

    @property
    def measured_fps(self) -> float:
        """The frame rate measured over recent frames."""
        return self._canvas._time_source.frames_per_second

    @property
    def fps(self) -> float:
        """
        The most frames drawn per second, and the rate ``iter`` aims for.

        Assign a new rate at any time, from a hook as well: the next frame follows it, and a
        canvas from ``new()`` steps by the new length from its next step on.

        Raises:
            TypeError: The rate is not a number.
            ValueError: The rate is not above 0.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=1, fps=10) as canvas:
                canvas.clock.step()
                canvas.clock.fps = 20
                frame = canvas.clock.step()
                assert round(frame.delta_seconds, 3) == 0.05
            ```
        """
        return self._canvas._fps

    @fps.setter
    def fps(self, value: float) -> None:
        self._canvas._set_fps(value)

    @property
    def bpm(self) -> float:
        """
        Beats per minute: the length of a beat for beat timers, notes and melodies.

        It is 120 unless ``new(bpm=...)`` said otherwise, and it can change while things
        are playing; the change applies from the next beat.

        Raises:
            ValueError: The tempo is not above 0 and at most 600000.
        """
        return self._canvas._bpm

    @bpm.setter
    def bpm(self, value: float) -> None:
        self._canvas._set_bpm(value)

    @property
    def beats(self) -> Beats:
        """The musical clock: its position in beats, started, paused and stopped on its own."""
        return Beats(self._canvas)

    @property
    def is_stopped(self) -> bool:
        """Whether time is frozen by [`stop`][xnano.devices.Clock.stop]."""
        return self._canvas._time_source.is_stopped

    @property
    def is_realtime(self) -> bool:
        """Whether time follows the wall clock instead of moving only when you move it."""
        return self._canvas._time_source.source == 'monotonic'

    @property
    def seconds(self) -> _core.NumericValue:
        """A formula for the elapsed seconds, recomputed every frame."""
        return _core.TimeElapsed

    @property
    def milliseconds(self) -> _core.NumericValue:
        """A formula for the elapsed milliseconds, recomputed every frame."""
        return _core.TimeElapsedMilliseconds

    def stop(self) -> None:
        """
        Freeze time.

        Animations, effects, formulas, timers, fixed-step updates and the musical beat stand
        still. The canvas still draws and input still arrives, so a key can
        [`resume`][xnano.devices.Clock.resume] it, and [`step`][xnano.devices.Clock.step] moves it one
        frame at a time. Stopping a stopped canvas does nothing.

        Raises:
            TerminalClosedError: The canvas is closed.
        """
        canvas = self._canvas
        canvas._require_open()
        canvas._time_source.stop()
        audio = canvas._audio
        if audio is not None:
            canvas._host.post(audio._hold)
        # A frozen canvas still draws what changes, so it draws once more now.
        canvas._request_frame()

    def resume(self) -> None:
        """
        Let time run on from where [`stop`][xnano.devices.Clock.stop] froze it.

        Resuming a canvas that is not stopped does nothing.

        Raises:
            TerminalClosedError: The canvas is closed.
        """
        canvas = self._canvas
        canvas._require_open()
        canvas._time_source.resume()
        audio = canvas._audio
        if audio is not None:
            canvas._host.post(audio._release)

    def step(self, *, delta_seconds: float | None = None) -> Frame:
        """
        Move time by ``delta_seconds``, one frame by default, and draw exactly one frame.

        This is [`step`][xnano.devices.Clock.step]; see it for every case.

        Args:
            delta_seconds: How far to move, above zero; one frame of the canvas's ``fps``
                when ``None``.

        Returns:
            The [`Frame`][xnano.hooks.Frame] that was drawn.
        """
        return self._canvas._step(delta_seconds)

    def sleep(self, seconds: float) -> None:
        """
        Wait until ``seconds`` of the canvas's time have passed, while it goes on drawing.

        On a canvas that runs by itself (on the screen, or ``realtime=True``) your program waits
        here, like ``time.sleep``, while animations, hooks and input go on. Time spent stopped
        does not count, so on a stopped canvas the wait goes on until it is resumed. On a canvas
        from ``new()`` the clock moves ``seconds`` at once, one frame of its ``fps`` at a time,
        so the hooks, timers and animations due in that time run as they would have.

        The wait ends early when the canvas quits or closes.

        Args:
            seconds: How long to wait, in seconds of the canvas's time; ``0`` or more.

        Raises:
            ValueError: ``seconds`` is negative or not a finite number.
            TerminalError: It was called from a hook of a canvas that runs by itself, where
                waiting would freeze the screen; or the canvas has a manual clock that is
                stopped, so the time would never pass.
            TerminalClosedError: The canvas is closed.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=1, fps=10) as canvas:
                ticks = []
                canvas.hook(lambda: ticks.append(1), on='tick', every=0.5)
                canvas.clock.sleep(2)
                assert round(canvas.clock.elapsed, 6) == 2.0 and len(ticks) == 4
            ```
        """
        canvas = self._check_sleep(seconds)
        if canvas._host.is_autonomous:
            clock = canvas._time_source
            target = clock.elapsed_seconds + seconds
            while canvas.is_running:
                remaining = target - clock.elapsed_seconds
                if remaining <= 0:
                    return
                canvas._stop_requested.wait(
                    _STOPPED_POLL if clock.is_stopped else remaining
                )
            return
        for delta in self._manual_steps(canvas, seconds):
            canvas._step(delta)

    async def sleep_async(self, seconds: float) -> None:
        """
        Wait until ``seconds`` of the canvas's time have passed, with ``await``.

        The same as [`sleep`][xnano.devices.Clock.sleep], while your event loop goes on running
        other tasks; on a canvas from ``new()`` other tasks run between the frames it moves.

        Examples:
            ```python
            import asyncio

            import xnano


            async def main() -> float:
                async with xnano.new(realtime=True, width=8, height=1) as canvas:
                    start = canvas.clock.elapsed
                    await canvas.clock.sleep_async(0.05)
                    return canvas.clock.elapsed - start


            assert asyncio.run(main()) >= 0.05
            ```
        """
        import asyncio

        canvas = self._check_sleep(seconds)
        if canvas._host.is_autonomous:
            clock = canvas._time_source
            target = clock.elapsed_seconds + seconds
            while canvas.is_running:
                remaining = target - clock.elapsed_seconds
                if remaining <= 0:
                    return
                await canvas._stop_requested.wait_async(
                    _STOPPED_POLL if clock.is_stopped else remaining
                )
            return
        for delta in self._manual_steps(canvas, seconds):
            canvas._step(delta)
            await asyncio.sleep(0)

    def _check_sleep(self, seconds: float) -> Canvas[object, object]:
        """Check what ``sleep`` was given, and return the canvas whose time passes."""
        from xnano.errors import TerminalError

        canvas = self._canvas._canvas
        canvas._require_open()
        if (
            isinstance(seconds, bool)
            or not isinstance(seconds, (int, float))
            or not math.isfinite(seconds)
            or seconds < 0
        ):
            raise ValueError(
                f'sleep() takes the seconds to wait, 0 or more, but got {seconds!r}. Write '
                f'canvas.clock.sleep(0.5) to wait half a second.'
            )
        if canvas._host.is_autonomous and canvas._host.is_on_loop():
            # A hook runs on the loop that draws, so waiting there would freeze the screen.
            raise TerminalError(
                f'sleep({seconds:g}) was called from a hook of a canvas that runs by itself, '
                f'where waiting would freeze the screen. To act later, register a hook with '
                f"on='tick' and after={seconds:g}, or write the hook with async def and await "
                f'context.clock.sleep_async({seconds:g}).'
            )
        if not canvas._host.is_autonomous and canvas._time_source.is_stopped and seconds:
            raise TerminalError(
                f'sleep({seconds:g}) would never end: this canvas has a manual clock, and its '
                f'time is stopped. Call canvas.clock.resume() first, or move the stopped clock '
                f'with canvas.clock.step().'
            )
        return canvas

    @staticmethod
    def _manual_steps(
        canvas: Canvas[object, object], seconds: float
    ) -> list[float | None]:
        """
        The steps that move a manual clock by ``seconds``: whole frames, then what is left.

        A whole frame is ``None``, the canvas's own frame step, which keeps the clock on whole
        milliseconds so that it never drifts from ``fps``.
        """
        steps: list[float | None] = []
        target = seconds * 1000.0
        moved = canvas._moved
        interval = 1000.0 / canvas._fps
        passed = 0
        while True:
            frame = round((moved + 1) * interval) - round(moved * interval)
            if passed + frame > target + 1e-6:
                break
            steps.append(None)
            passed += frame
            moved += 1
        if target - passed > 1e-6:
            steps.append((target - passed) / 1000.0)
        return steps

    def __add__(self, other: object) -> _core.NumericValue:
        return self.seconds.__add__(other)  # type: ignore[operator]

    def __radd__(self, other: object) -> _core.NumericValue:
        return self.seconds.__radd__(other)  # type: ignore[operator]

    def __sub__(self, other: object) -> _core.NumericValue:
        return self.seconds.__sub__(other)  # type: ignore[operator]

    def __rsub__(self, other: object) -> _core.NumericValue:
        return self.seconds.__rsub__(other)  # type: ignore[operator]

    def __mul__(self, other: object) -> _core.NumericValue:
        return self.seconds.__mul__(other)  # type: ignore[operator]

    def __rmul__(self, other: object) -> _core.NumericValue:
        return self.seconds.__rmul__(other)  # type: ignore[operator]

    def __truediv__(self, other: object) -> _core.NumericValue:
        return self.seconds.__truediv__(other)  # type: ignore[operator]

    def __rtruediv__(self, other: object) -> _core.NumericValue:
        return self.seconds.__rtruediv__(other)  # type: ignore[operator]

    def __floordiv__(self, other: object) -> _core.NumericValue:
        return self.seconds.__floordiv__(other)  # type: ignore[operator]

    def __rfloordiv__(self, other: object) -> _core.NumericValue:
        return self.seconds.__rfloordiv__(other)  # type: ignore[operator]

    def __mod__(self, other: object) -> _core.NumericValue:
        return self.seconds.__mod__(other)  # type: ignore[operator]

    def __rmod__(self, other: object) -> _core.NumericValue:
        return self.seconds.__rmod__(other)  # type: ignore[operator]

    def __pow__(self, other: object) -> _core.NumericValue:
        return self.seconds.__pow__(other)  # type: ignore[operator]

    def __rpow__(self, other: object) -> _core.NumericValue:
        return self.seconds.__rpow__(other)  # type: ignore[operator]

    def __neg__(self) -> _core.NumericValue:
        return -self.seconds

    def __repr__(self) -> str:
        return f'Clock(elapsed={self.elapsed:.3f}, is_stopped={self.is_stopped})'


class Beats:
    """
    The musical clock of a terminal: where the music is, in beats.

    Get it from ``clock.beats``. It counts beats at the clock's ``bpm`` from when it is
    started, and stands still while it is paused or the whole clock is stopped. Notes and
    melodies played with ``at_beat`` wait for it.

    Attributes:
        position: The position in beats, as an expression that follows the clock.

    Examples:
        ```python
        import xnano

        with xnano.new(width=20, height=2) as canvas:
            ball = canvas.screen.write('o')
            ball.x = (canvas.clock.beats.position % 1) * 19
            canvas.clock.beats.start()
            canvas.clock.step(delta_seconds=0.25)
            assert canvas.inspect(canvas.clock.beats.position) == 0.5
        ```
    """

    __slots__ = ('_canvas',)

    def __init__(self, canvas: Canvas[object, object]) -> None:
        """Create a view of the musical clock. Use ``clock.beats`` instead of calling this."""
        self._canvas = canvas

    @property
    def position(self) -> _core.NumericValue:
        """
        The musical clock's position in beats, as an expression.

        It stays at ``0`` until the clock is started with
        [`start`][xnano.devices.Beats.start] or a sound is played with ``at_beat``.
        """
        return self._canvas._audio_device().beat

    def start(self) -> None:
        """Start the musical clock."""
        self._canvas._audio_device().start()

    def pause(self) -> None:
        """Pause the musical clock, keeping its position."""
        self._canvas._audio_device().pause()

    def resume(self) -> None:
        """Let the musical clock run on from where [`pause`][xnano.devices.Beats.pause] left it."""
        self._canvas._audio_device().resume()

    def stop(self) -> None:
        """
        Stop the musical clock and return it to the first beat.

        This rewinds only the musical clock. To freeze the whole canvas, this clock included,
        use [`Clock.stop`][xnano.devices.Clock.stop].
        """
        self._canvas._audio_device().stop()
