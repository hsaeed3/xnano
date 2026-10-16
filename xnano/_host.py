"""
xnano._host

The loop a canvas runs on: inline for a manual clock, a thread otherwise.
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
    from xnano.canvas import Canvas

from xnano.errors import TerminalClosedError, TerminalError, release_frames

ResultT = TypeVar('ResultT')

_CALL_TIMEOUT_SECONDS: Final = 10.0


class _Registration:
    """
    One thing a canvas registered with its runtime, kept so that it can be registered again.

    A runtime forgets its hooks and timers when it closes, so a canvas that moves to a new
    runtime (when it is opened on the screen) calls every factory again on the new one.

    Attributes:
        factory: Registers the thing with a runtime and returns the handle that cancels it.
        handle: The handle of the current registration, or ``None`` while unbound.
        due_seconds: The canvas time a timer is due at, or ``None`` for anything else.
        is_cancelled: Whether the registration was cancelled for good.
    """

    __slots__ = ('due_seconds', 'factory', 'handle', 'is_cancelled')

    def __init__(
        self,
        factory: Callable[[_core.Runtime], object],
        *,
        due_seconds: float | None = None,
    ) -> None:
        """
        Keep a registration. Use ``Canvas._register`` instead of calling this.

        Args:
            factory: Registers the thing with a runtime and returns its handle.
            due_seconds: The canvas time a timer is due at, or ``None``.
        """
        self.factory = factory
        self.handle: object = None
        self.due_seconds = due_seconds
        self.is_cancelled = False

    def bind(self, runtime: _core.Runtime) -> None:
        """Register with ``runtime``, unless the registration was cancelled."""
        if self.is_cancelled:
            return
        self.handle = self.factory(runtime)

    def unbind(self) -> None:
        """Cancel the current registration and keep the factory for the next runtime."""
        handle = self.handle
        self.handle = None
        cancel = getattr(handle, 'cancel', None)
        if cancel is not None:
            cancel()

    def cancel(self) -> None:
        """Cancel the registration for good."""
        self.is_cancelled = True
        self.unbind()


class _Host:
    """Where a canvas's runtime runs, and how the rest of the program reaches it."""

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
        """Stop the loop, release the canvas and wait for the loop to finish."""
        raise NotImplementedError

    def retire(self) -> None:
        """Close the runtime without releasing the canvas, which moves to another runtime."""
        raise NotImplementedError

    def require_retirable(self) -> None:
        """Raise a TerminalError when the calling thread may not retire this host."""


class _InlineHost(_Host):
    """
    The runtime lives on the thread that created the canvas and moves only when told to.

    Every call runs at once on the calling thread, which makes the canvas deterministic.
    """

    is_autonomous = False

    def __init__(
        self, canvas: Canvas[object, object], create_runtime: Callable[[], _core.Runtime]
    ) -> None:
        """
        Create the runtime on the calling thread and bind the canvas to it.

        Args:
            canvas: The canvas the loop belongs to.
            create_runtime: Creates the runtime; called once, on the calling thread.
        """
        self._canvas = canvas
        self._thread = threading.current_thread()
        canvas._host = self
        runtime = create_runtime()
        # Entering the runtime is what marks the loop as running.
        runtime.__enter__()
        self._runtime: _core.Runtime | None = runtime
        canvas._bind(runtime)

    def is_on_loop(self) -> bool:
        return True

    def post(self, function: Callable[[], object]) -> None:
        function()

    def call(self, function: Callable[[], ResultT]) -> ResultT:
        return function()

    def shutdown(self) -> None:
        runtime = self._runtime
        if runtime is None:
            return
        self._canvas._detach()
        self._runtime = None
        runtime.close()

    def require_retirable(self) -> None:
        if threading.current_thread() is not self._thread:
            raise TerminalError(
                'A canvas with a manual clock belongs to the thread that created it, and this '
                'is another one. Open it on the screen from the thread that called '
                'xnano.new().'
            )

    def retire(self) -> None:
        runtime = self._runtime
        if runtime is None:
            return
        self.require_retirable()
        self._runtime = None
        runtime.close()


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
        self,
        canvas: Canvas[object, object],
        create_runtime: Callable[[], _core.Runtime],
        *,
        defer_bind: bool = False,
    ) -> None:
        """
        Start the loop's thread and wait until the runtime exists, or failed.

        Args:
            canvas: The canvas the loop belongs to.
            create_runtime: Creates the runtime; called once, on the loop's own thread.
            defer_bind: Whether the loop waits for ``bind_now`` before it binds the canvas
                and starts running. A canvas that moves onto this loop is bound later, once
                its previous runtime is closed.

        Raises:
            BaseException: Whatever the runtime raised while it was being created.
        """
        self._canvas = canvas
        if not defer_bind:
            canvas._host = self
        self._create_runtime = create_runtime
        self._defer_bind = defer_bind
        self._ready = threading.Event()
        self._finished = threading.Event()
        self._bind_requested = threading.Event()
        self._bind_done = threading.Event()
        self._startup_error: BaseException | None = None
        self._bind_error: BaseException | None = None
        self._is_bound = False
        self._is_retiring = False
        self._waker: _core.Waker | None = None
        self._thread = threading.Thread(
            target=self._main, name='xnano-terminal', daemon=True
        )
        self._thread.start()
        self._ready.wait()
        if self._startup_error is not None:
            error = self._startup_error
            self._startup_error = None
            raise error

    def bind_now(self) -> None:
        """
        Bind the canvas to the waiting runtime, on the loop's thread, and start the loop.

        Raises:
            BaseException: Whatever binding raised; the loop then closes its runtime.
        """
        self._bind_requested.set()
        self._bind_done.wait(_CALL_TIMEOUT_SECONDS)
        if self._bind_error is not None:
            error = self._bind_error
            self._bind_error = None
            raise error

    def _main(self) -> None:
        canvas = self._canvas
        runtime: _core.Runtime | None = None
        try:
            from xnano.canvas import _active_canvas

            _active_canvas.set(canvas)
            runtime = self._create_runtime()
            runtime.__enter__()
            self._waker = runtime.waker()
            if self._defer_bind:
                self._ready.set()
                self._bind_requested.wait()
                if self._is_retiring:
                    return
            try:
                canvas._bind(runtime)
                self._is_bound = True
            except BaseException as error:
                self._bind_error = error
                raise
            finally:
                self._bind_done.set()
            self._ready.set()
            runtime.run()
        except BaseException as error:  # reported to the thread that owns the canvas
            if self._is_bound and not self._is_retiring:
                canvas._record_failure(error)
            elif not self._ready.is_set():
                self._startup_error = error
        finally:
            try:
                if self._is_bound and not self._is_retiring:
                    canvas._detach()
                if runtime is not None:
                    runtime.close()
            except BaseException as error:
                if canvas._failure is None and self._is_bound and not self._is_retiring:
                    canvas._record_failure(error)
            # The runtime may only be dropped on this thread, so let go of every reference
            # to it (the canvas and any traceback hold some) before the thread ends.
            if self._is_bound:
                canvas._forget_runtime()
            runtime = None
            release_frames(self._startup_error)
            release_frames(self._bind_error)
            self._ready.set()
            self._bind_done.set()
            self._finished.set()
            if self._is_bound and not self._is_retiring:
                canvas._stop_requested.set()

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
        import concurrent.futures  # only a canvas on its own thread needs it

        outcome: concurrent.futures.Future[ResultT] = concurrent.futures.Future()

        def run() -> None:
            try:
                outcome.set_result(function())
            except BaseException as error:
                outcome.set_exception(error)

        if self._finished.is_set() or self._waker is None:
            raise TerminalClosedError(
                'The canvas has finished, so it can no longer be asked for anything. Create '
                'a new one with xnano.new() or xnano.open().'
            )
        self._waker.call_soon(run)
        try:
            return outcome.result(timeout=_CALL_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            raise TerminalError(
                f'The canvas did not answer within {_CALL_TIMEOUT_SECONDS:g} seconds. A '
                f'callback that never returns is blocking its loop; keep callbacks short, '
                f'or hand slow work to another thread.'
            ) from None

    def wait(self, timeout: float | None = None) -> bool:
        """Wait for the loop to finish; return whether it has."""
        return self._finished.wait(timeout)

    def shutdown(self) -> None:
        if not self._is_bound and not self._finished.is_set():
            # A loop that was never bound is still waiting for bind_now.
            self._is_retiring = True
            self._bind_requested.set()
        else:
            self.post(lambda: self._canvas._stop_runtime())
        self._join()

    def retire(self) -> None:
        self._is_retiring = True
        if not self._is_bound:
            self._bind_requested.set()
        else:
            self.post(lambda: self._canvas._stop_runtime())
        self._join()

    def _join(self) -> None:
        if self.is_on_loop():
            return
        self._thread.join(timeout=_CALL_TIMEOUT_SECONDS)
        if self._thread.is_alive():
            raise TerminalError(
                f'The canvas did not stop within {_CALL_TIMEOUT_SECONDS:g} seconds. A '
                f'callback that never returns is blocking its loop; keep callbacks short, '
                f'or hand slow work to another thread.'
            )
