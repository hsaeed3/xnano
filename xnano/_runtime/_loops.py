"""
xnano._runtime._loops

Waiting for a canvas from a thread or from a coroutine, and the event loops that coroutines of
``async def`` hooks run on.
"""

from __future__ import annotations

import sys
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Loaded only by a program that awaits, so that importing xnano stays quick.
    import asyncio


def _resolve(future: asyncio.Future[None]) -> None:
    """Finish a future that nobody finished or cancelled yet. Runs on the future's loop."""
    if not future.done():
        future.set_result(None)


class _AwaitableEvent(threading.Event):
    """
    A ``threading.Event`` that a coroutine can also wait for, without blocking its loop.

    Any thread may set it. A thread waits with ``wait``, a coroutine with ``wait_async``.
    """

    def __init__(self) -> None:
        """Create the event, not yet set."""
        super().__init__()
        self._waiting_futures: list[asyncio.Future[None]] = []
        self._futures_lock = threading.Lock()

    def set(self) -> None:
        """Set the event, waking every thread and coroutine waiting for it."""
        super().set()
        with self._futures_lock:
            futures, self._waiting_futures = self._waiting_futures, []
        for future in futures:
            loop = future.get_loop()
            if loop.is_closed():
                continue
            try:
                loop.call_soon_threadsafe(_resolve, future)
            except RuntimeError:
                # The loop closed between the check and the call; nobody is waiting anymore.
                pass

    async def wait_async(self, timeout: float | None = None) -> bool:
        """
        Wait until the event is set, or ``timeout`` seconds pass, without blocking the loop.

        Returns:
            Whether the event is set.
        """
        import asyncio

        if self.is_set():
            return True
        future: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        with self._futures_lock:
            self._waiting_futures.append(future)
        try:
            # Set between the first check and the registration: the future would never finish.
            if self.is_set():
                return True
            finished, _ = await asyncio.wait({future}, timeout=timeout)
            return bool(finished) or self.is_set()
        finally:
            with self._futures_lock:
                if future in self._waiting_futures:
                    self._waiting_futures.remove(future)
            future.cancel()


def running_loop() -> asyncio.AbstractEventLoop | None:
    """The event loop running on the calling thread, or ``None``, without importing asyncio."""
    module = sys.modules.get('asyncio')
    if module is None:
        # Nothing imported asyncio, so no event loop can be running.
        return None
    try:
        return module.get_running_loop()
    except RuntimeError:
        return None


_background_loop: asyncio.AbstractEventLoop | None = None
_background_lock = threading.Lock()


def background_loop() -> asyncio.AbstractEventLoop:
    """
    An event loop of xnano's own, for the coroutines of a program that runs no loop itself.

    It runs on a daemon thread, starts the first time it is needed and is never closed, so
    clients that keep connections open across calls (such as model providers) keep working.
    """
    global _background_loop
    with _background_lock:
        if _background_loop is None:
            import asyncio

            loop = asyncio.new_event_loop()
            is_running = threading.Event()

            def run_forever() -> None:
                asyncio.set_event_loop(loop)
                loop.call_soon(is_running.set)
                loop.run_forever()

            threading.Thread(
                target=run_forever, name='xnano-event-loop', daemon=True
            ).start()
            is_running.wait()
            _background_loop = loop
        return _background_loop


_thread_marks = threading.local()


def mark_canvas_loop_thread() -> None:
    """Note that the calling thread runs the loop of a canvas that runs by itself."""
    _thread_marks.is_canvas_loop = True


def is_canvas_loop_thread() -> bool:
    """Whether the calling thread runs the loop of a canvas that runs by itself."""
    return getattr(_thread_marks, 'is_canvas_loop', False)
