"""
xnano._host

The loop a terminal runs on: inline for a manual clock, a thread otherwise.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import (
    TYPE_CHECKING,
    Final,
    TypeVar,
)

import xnano_core as _core

if TYPE_CHECKING:
    from xnano.terminal import Terminal

from xnano.errors import TerminalClosedError, TerminalError, release_frames

ResultT = TypeVar('ResultT')

_CALL_TIMEOUT_SECONDS: Final = 10.0


class _Host:
    """Where a terminal's runtime runs, and how the rest of the program reaches it."""

    is_autonomous: bool

    def is_on_loop(self) -> bool:
        """Whether the calling thread is the one the runtime belongs to."""
        raise NotImplementedError

    def post(self, function: Callable[[], object]) -> None:
        """Run a function on the loop soon, without waiting for it."""
        raise NotImplementedError

    def call(self, function: Callable[[], ResultT]) -> ResultT:
        """Run a function on the loop and return what it returned."""
        raise NotImplementedError

    def shutdown(self) -> None:
        """Stop the loop and wait for it to finish."""
        raise NotImplementedError


class _InlineHost(_Host):
    """
    The runtime lives on the thread that opened the terminal and moves only when told to.

    Every call runs at once on the calling thread, which makes the terminal deterministic.
    """

    is_autonomous = False

    def __init__(
        self, terminal: Terminal, create_runtime: Callable[[], _core.Runtime]
    ) -> None:
        """
        Create the runtime on the calling thread and attach the terminal to it.

        Args:
            terminal: The terminal the loop belongs to.
            create_runtime: Creates the runtime; called once, on the calling thread.
        """
        self._terminal = terminal
        terminal._host = self
        runtime = create_runtime()
        # Entering the runtime is what opens the screen and marks the loop as running.
        runtime.__enter__()
        self._runtime = runtime
        terminal._attach(runtime)

    def is_on_loop(self) -> bool:
        return True

    def post(self, function: Callable[[], object]) -> None:
        function()

    def call(self, function: Callable[[], ResultT]) -> ResultT:
        return function()

    def shutdown(self) -> None:
        self._terminal._detach()
        self._runtime.close()


class _ThreadHost(_Host):
    """
    The runtime lives on a thread of its own and runs by itself.

    The rest of the program never waits for a frame, and a frame never waits for the rest
    of the program: it changes buffers, which any thread may do, and the loop draws them
    the moment it can. Work that needs the runtime itself is handed to the loop with
    ``post``.
    """

    is_autonomous = True

    def __init__(
        self, terminal: Terminal, create_runtime: Callable[[], _core.Runtime]
    ) -> None:
        """
        Start the loop's thread and wait until the terminal is attached or failed.

        Args:
            terminal: The terminal the loop belongs to.
            create_runtime: Creates the runtime; called once, on the loop's own thread.

        Raises:
            BaseException: Whatever the runtime raised while it was being created.
        """
        self._terminal = terminal
        terminal._host = self
        self._create_runtime = create_runtime
        self._ready = threading.Event()
        self._finished = threading.Event()
        self._startup_error: BaseException | None = None
        self._waker: _core.Waker | None = None
        self._thread = threading.Thread(
            target=self._main, name='xnano-terminal', daemon=True
        )
        self._thread.start()
        self._ready.wait()
        if self._startup_error is not None:
            raise self._startup_error

    def _main(self) -> None:
        terminal = self._terminal
        runtime: _core.Runtime | None = None
        try:
            from xnano.terminal import _active_terminal

            _active_terminal.set(terminal)
            runtime = self._create_runtime()
            runtime.__enter__()
            self._waker = runtime.waker()
            terminal._attach(runtime)
            self._ready.set()
            runtime.run()
        except BaseException as error:  # reported to the thread that owns the terminal
            if self._ready.is_set():
                terminal._record_failure(error)
            else:
                self._startup_error = error
        finally:
            try:
                terminal._detach()
                if runtime is not None:
                    runtime.close()
            except BaseException as error:
                if terminal._failure is None and self._ready.is_set():
                    terminal._record_failure(error)
            # The runtime may only be dropped on this thread, so let go of every reference
            # to it (the terminal and any traceback hold some) before the thread ends.
            terminal._runtime_object = None
            runtime = None
            release_frames(self._startup_error)
            self._ready.set()
            self._finished.set()
            terminal._stop_requested.set()

    def is_on_loop(self) -> bool:
        return threading.current_thread() is self._thread

    def post(self, function: Callable[[], object]) -> None:
        if self.is_on_loop():
            function()
        elif self._waker is not None and not self._finished.is_set():
            self._waker.call_soon(function)

    def call(self, function: Callable[[], ResultT]) -> ResultT:
        if self.is_on_loop():
            return function()
        import concurrent.futures  # only a terminal on its own thread needs it

        outcome: concurrent.futures.Future[ResultT] = concurrent.futures.Future()

        def run() -> None:
            try:
                outcome.set_result(function())
            except BaseException as error:
                outcome.set_exception(error)

        if self._finished.is_set() or self._waker is None:
            raise TerminalClosedError(
                'The terminal has finished, so it can no longer be asked for anything.'
            )
        self._waker.call_soon(run)
        try:
            return outcome.result(timeout=_CALL_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            raise TerminalError(
                f'The terminal did not answer within {_CALL_TIMEOUT_SECONDS:g} seconds. A '
                f'callback that never returns is blocking its loop; keep callbacks short, '
                f'or hand slow work to another thread.'
            ) from None

    def wait(self, timeout: float | None = None) -> bool:
        """Wait for the loop to finish; return whether it has."""
        return self._finished.wait(timeout)

    def shutdown(self) -> None:
        self.post(lambda: self._terminal._stop_runtime())
        if self.is_on_loop():
            return
        self._thread.join(timeout=_CALL_TIMEOUT_SECONDS)
        if self._thread.is_alive():
            raise TerminalError(
                f'The terminal did not stop within {_CALL_TIMEOUT_SECONDS:g} seconds. A '
                f'callback that never returns is blocking its loop; keep callbacks short, '
                f'or hand slow work to another thread.'
            )
