"""
xnano.time

A canvas's time: how long it has run, whether it is stopped, and the formulas that follow it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import xnano_core as _core

if TYPE_CHECKING:
    from xnano.canvas import Canvas
    from xnano.context import Frame

__all__ = ['Time']


class Time:
    """
    The time a canvas runs on.

    Get it from [`Canvas.time`][xnano.canvas.Canvas.time] or from ``context.time`` inside a
    hook. Everything that moves follows it: animations, effects, formulas,
    [`every`][xnano.canvas.Canvas.every] and [`after`][xnano.canvas.Canvas.after] timers,
    fixed-step updates and the musical beat. Any thread may read it. Used in arithmetic it is
    the formula for [`seconds`][xnano.time.Time.seconds], so ``canvas.time / 2`` is a value
    that follows the clock. [`stop`][xnano.time.Time.stop] freezes all of them while input
    keeps arriving, and [`step`][xnano.time.Time.step] moves a frozen clock one frame at a
    time.

    Attributes:
        elapsed: Seconds since the canvas started, not counting time spent stopped.
        elapsed_milliseconds: The same, in milliseconds.
        delta: Seconds between the two most recent frames.
        frame: The number of steps the clock has counted.
        fps: The frame rate measured over recent frames.
        is_stopped: Whether time is frozen.
        is_realtime: Whether time follows the wall clock. A canvas from ``xnano.new()``
            without ``realtime=True`` moves only when you move it.
        seconds: A formula for [`elapsed`][xnano.time.Time.elapsed], recomputed every frame.
        milliseconds: A formula for
            [`elapsed_milliseconds`][xnano.time.Time.elapsed_milliseconds].

    Examples:
        ```python
        import xnano

        with xnano.new(width=20, height=1) as canvas:
            ball = canvas.write('o')
            ball.x = (canvas.width - 1) * ((canvas.time.seconds / 2) % 1.0)
            canvas.step(delta_seconds=1.0)
            assert canvas.time.elapsed == 1.0
            canvas.time.stop()
            assert canvas.time.is_stopped
            canvas.time.step(delta_seconds=0.5)
            assert canvas.time.elapsed == 1.5
        ```
    """

    def __init__(self, canvas: Canvas[object, object]) -> None:
        """
        Create the canvas's time. Use ``canvas.time`` instead of calling this.

        Args:
            canvas: The canvas the time belongs to.
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
    def fps(self) -> float:
        """The frame rate measured over recent frames."""
        return self._canvas._time_source.frames_per_second

    @property
    def is_stopped(self) -> bool:
        """Whether time is frozen by [`stop`][xnano.time.Time.stop]."""
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
        [`resume`][xnano.time.Time.resume] it, and [`step`][xnano.time.Time.step] moves it one
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
        Let time run on from where [`stop`][xnano.time.Time.stop] froze it.

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

        This is [`Canvas.step`][xnano.canvas.Canvas.step]; see it for every case.

        Args:
            delta_seconds: How far to move, above zero; one frame of the canvas's ``fps``
                when ``None``.

        Returns:
            The [`Frame`][xnano.context.Frame] that was drawn.
        """
        return self._canvas._step(delta_seconds)

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
        return f'Time(elapsed={self.elapsed:.3f}, is_stopped={self.is_stopped})'
