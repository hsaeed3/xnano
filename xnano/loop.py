"""
xnano.loop

The terminal's loop: its frames, its simulation updates and, with a manual clock, its steps.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING

import xnano_core as _core
from xnano.context import Frame, Update
from xnano.errors import TerminalError
from xnano_core import FrameContext, UpdateContext

if TYPE_CHECKING:
    from xnano.terminal import Terminal

__all__ = ['Loop']


class Loop:
    """
    The loop a terminal draws on: frames, simulation updates and the pace of both.

    Get it from [`Terminal.loop`][xnano.terminal.Terminal.loop]. A terminal that runs by itself
    needs none of this to draw; use it to pace your own code with
    [`iter`][xnano.terminal.Terminal.iter], to run a function before every frame, or to move a
    manual clock.

    Attributes:
        fps: The rate frames are drawn at, at most.

    Examples:
        ```python
        import xnano

        with xnano.open(offscreen=True, width=8, height=1, fps=10) as terminal:
            elapsed = [frame.elapsed_seconds for frame in terminal.iter(count=3)]
        assert elapsed == [0.0, 0.1, 0.2]
        ```
    """

    def __init__(self, terminal: Terminal[object]) -> None:
        """
        Create the loop's view of a terminal. Use ``terminal.loop`` instead of calling this.

        Args:
            terminal: The terminal the loop belongs to.
        """
        self._terminal = terminal

    @property
    def fps(self) -> float:
        """The rate [`iter`][xnano.terminal.Terminal.iter] aims for, and the most frames drawn per second."""
        return self._terminal._fps

    def step(self, *, timeout_seconds: float | None = 0.0) -> bool:
        """
        Run one iteration of a terminal whose clock you drive.

        Args:
            timeout_seconds: How long to wait for something to do; ``None`` waits for the
                next deadline.

        Returns:
            Whether a frame was drawn.

        Raises:
            TerminalError: The terminal runs by itself.
        """
        terminal = self._terminal
        terminal._require_open()
        self._require_manual('step')
        milliseconds = None if timeout_seconds is None else int(timeout_seconds * 1000)
        return terminal._runtime.step(timeout_milliseconds=milliseconds).did_render

    def advance(self, seconds: float) -> None:
        """
        Move an offscreen terminal's clock forward and draw a frame.

        Args:
            seconds: How far to move the clock.

        Raises:
            TerminalError: The terminal runs by itself, so its clock cannot be moved.
        """
        terminal = self._terminal
        terminal._require_open()
        self._require_manual('advance')
        milliseconds = int(round(seconds * 1000))
        terminal._offscreen_milliseconds += milliseconds
        runtime = terminal._runtime
        runtime.advance_clock(milliseconds)
        runtime.request_frame()
        runtime.step()

    def _frames(
        self, *, count: int | None = None, duration_seconds: float | None = None
    ) -> Iterator[Frame]:
        """Yield the terminal's frames; see [`Terminal.iter`][xnano.terminal.Terminal.iter]."""
        terminal = self._terminal
        terminal._require_open()
        interval = 1.0 / terminal._fps
        terminal_time = terminal.time
        start = terminal_time.elapsed
        previous = start
        index = 0
        deadline = time.monotonic()
        while terminal.is_running:
            if count is not None and index >= count:
                return
            elapsed = terminal_time.elapsed
            if (
                duration_seconds is not None
                and elapsed - start >= duration_seconds - 1e-9
            ):
                return
            size = terminal.size
            yield Frame(
                terminal=terminal,
                index=index,
                elapsed_seconds=elapsed,
                delta_seconds=elapsed - previous,
                area=_core.Rectangle(0, 0, size.width, size.height),
            )
            previous = elapsed
            index += 1
            if not terminal.is_running:
                return
            if terminal._host.is_autonomous:
                now = time.monotonic()
                deadline += interval
                if deadline < now - interval:
                    deadline = now
                terminal._stop_requested.wait(max(0.0, deadline - now))
            else:
                target = round(index * interval * 1000)
                runtime = terminal._runtime
                runtime.advance_clock(target - terminal._offscreen_milliseconds)
                terminal._offscreen_milliseconds = target
                runtime.request_frame()
                runtime.step()

    def on_frame(
        self, callback: Callable[[Frame], object], /
    ) -> Callable[[Frame], object]:
        """
        Call a function before each frame is drawn, on the terminal's loop.

        Having such a function means the terminal draws a frame every
        [`fps`][xnano.loop.Loop.fps], so use it for things that move.
        A terminal draws only when something changed otherwise.

        Args:
            callback: Called with a [`Frame`][xnano.context.Frame].

        Returns:
            The callback, so this can be used as a decorator.

        Examples:
            ```python
            import xnano

            with xnano.open(offscreen=True, width=8, height=1) as terminal:
                seen = []
                terminal.loop.on_frame(lambda frame: seen.append(frame.index))
                terminal.loop.advance(0.1)
            assert seen
            ```
        """
        terminal = self._terminal
        terminal._require_open()
        counter = iter(range(1 << 62))
        previous = [0.0]

        def hook(core_context: FrameContext) -> None:
            elapsed = core_context.elapsed_seconds
            frame = Frame(
                terminal=terminal,
                index=next(counter),
                elapsed_seconds=elapsed,
                delta_seconds=elapsed - previous[0],
                area=core_context.area,
            )
            previous[0] = elapsed
            callback(frame)

        terminal._frame_callback_count += 1
        self._register(lambda: terminal._runtime.on_frame(hook, target=terminal._root))
        terminal._request_frame()
        return callback

    def on_update(
        self,
        *,
        fixed_step_seconds: float | None = None,
        maximum_delta_seconds: float | None = None,
    ) -> Callable[[Callable[[Update], object]], Callable[[Update], object]]:
        """
        Call a function for simulation updates, which run separately from drawing.

        The function runs on the terminal's loop.

        Args:
            fixed_step_seconds: When given, the function is called once for every whole
                step of this length that has elapsed, however long a frame took.
            maximum_delta_seconds: The longest step to report when the steps vary.
        """
        terminal = self._terminal
        terminal._require_open()

        def decorator(
            callback: Callable[[Update], object],
        ) -> Callable[[Update], object]:
            def hook(core_context: UpdateContext) -> None:
                callback(
                    Update(
                        terminal=terminal,
                        elapsed_seconds=core_context.elapsed_seconds,
                        delta_seconds=core_context.delta_seconds,
                        is_fixed_step=core_context.is_fixed_step,
                    )
                )

            self._register(
                lambda: terminal._runtime.on_update(
                    hook,
                    target=terminal._root,
                    fixed_step_seconds=fixed_step_seconds,
                    maximum_delta_seconds=maximum_delta_seconds,
                )
            )
            return callback

        return decorator

    def _register(self, create_hook: Callable[[], _core.Hook]) -> None:
        terminal = self._terminal

        def register() -> None:
            terminal._runtime_hooks.append(create_hook())

        terminal._host.post(register)

    def _require_manual(self, name: str) -> None:
        if self._terminal._host.is_autonomous:
            raise TerminalError(
                f'terminal.loop.{name}() drives a terminal whose clock you move yourself, '
                f'but this one runs by itself and is already drawing. Declare what you '
                f'want and it appears; use terminal.iter() to pace your own '
                f'drawing.'
            )
