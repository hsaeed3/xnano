"""
xnano.time

The terminal's time: how long it has run, whether it is stopped, and the formulas that follow it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import xnano_core as _core

if TYPE_CHECKING:
    from xnano.terminal import Terminal

__all__ = ['Time']


class Time:
    """
    The time a terminal runs on.

    Get it from [`Terminal.time`][xnano.terminal.Terminal.time] or from ``context.time`` inside
    a hook. Everything that moves follows it: animations, effects, formulas,
    [`every`][xnano.terminal.Terminal.every] and [`after`][xnano.terminal.Terminal.after]
    timers, fixed-step updates and the musical beat. Any thread may read it. Used in arithmetic
    it is the formula for [`seconds`][xnano.time.Time.seconds], so ``terminal.time / 2`` is a
    value that follows the clock. Stopping it with
    [`pause`][xnano.time.Time.pause] stops all of them while input keeps arriving.

    Attributes:
        elapsed: Seconds since the terminal started, not counting time spent paused.
        elapsed_milliseconds: The same, in milliseconds.
        delta: Seconds between the two most recent frames.
        frame: The number of frames drawn so far.
        fps: The frame rate measured over recent frames.
        is_paused: Whether time is stopped.
        is_realtime: Whether time follows the wall clock. An offscreen terminal that was not
            opened with ``realtime=True`` moves only when you move it.
        seconds: A formula for [`elapsed`][xnano.time.Time.elapsed], recomputed every frame.
        milliseconds: A formula for
            [`elapsed_milliseconds`][xnano.time.Time.elapsed_milliseconds].

    Examples:
        ```python
        import xnano

        with xnano.iter(offscreen=True, width=20, height=1) as terminal:
            ball = terminal.write('o')
            ball.x = (terminal.width - 1) * ((terminal.time.seconds / 2) % 1.0)
            terminal.loop.advance(1.0)
            assert terminal.time.elapsed == 1.0
            terminal.time.pause()
            assert terminal.time.is_paused
        ```
    """

    def __init__(self, terminal: Terminal[object]) -> None:
        """
        Create the terminal's time. Use ``terminal.time`` instead of calling this.

        Args:
            terminal: The terminal the time belongs to.
        """
        self._terminal = terminal

    @property
    def elapsed(self) -> float:
        """Seconds since the terminal started, not counting time spent paused."""
        return self._terminal._time_source.elapsed_seconds

    @property
    def elapsed_milliseconds(self) -> float:
        """Milliseconds since the terminal started, not counting time spent paused."""
        return self._terminal._time_source.elapsed_milliseconds

    @property
    def delta(self) -> float:
        """Seconds between the two most recent frames."""
        return self._terminal._time_source.delta_seconds

    @property
    def frame(self) -> int:
        """The number of frames drawn so far."""
        return self._terminal._time_source.frame

    @property
    def fps(self) -> float:
        """The frame rate measured over recent frames."""
        return self._terminal._time_source.frames_per_second

    @property
    def is_paused(self) -> bool:
        """Whether time is stopped."""
        return self._terminal._time_source.is_paused

    @property
    def is_realtime(self) -> bool:
        """Whether time follows the wall clock instead of moving only when you move it."""
        return self._terminal._time_source.source == 'monotonic'

    @property
    def seconds(self) -> _core.NumericValue:
        """A formula for the elapsed seconds, recomputed every frame."""
        return _core.TimeElapsed

    @property
    def milliseconds(self) -> _core.NumericValue:
        """A formula for the elapsed milliseconds, recomputed every frame."""
        return _core.TimeElapsedMilliseconds

    def pause(self) -> None:
        """
        Stop time.

        Animations, effects, formulas, timers, fixed-step updates and the musical beat stand
        still. Input still arrives, so a key can [`resume`][xnano.time.Time.resume] it.

        Raises:
            TerminalClosedError: The terminal is closed.
        """
        terminal = self._terminal
        terminal._require_open()
        terminal._time_source.pause()
        audio = terminal._audio
        if audio is not None:
            terminal._host.post(audio._hold)

    def resume(self) -> None:
        """
        Let time run on from where [`pause`][xnano.time.Time.pause] stopped it.

        Raises:
            TerminalClosedError: The terminal is closed.
        """
        terminal = self._terminal
        terminal._require_open()
        terminal._time_source.resume()
        audio = terminal._audio
        if audio is not None:
            terminal._host.post(audio._release)

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
        return f'Time(elapsed={self.elapsed:.3f}, is_paused={self.is_paused})'
