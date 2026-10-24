"""
xnano.hooks._coroutines

Hooks written with ``async def``: the event loop their runs happen on, and what a new run does
to one that has not finished.

A run starts on the loop the canvas was created or opened in, and on xnano's own background
loop when there is none. The canvas counts the runs that have not finished, so a program or a
test can wait for them with ``wait_for_tasks_async``.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, cast

from xnano._runtime._loops import _AwaitableEvent, background_loop, running_loop

if TYPE_CHECKING:
    import asyncio

    from xnano._schema._hooks import IfRunning
    from xnano.canvas import Canvas
    from xnano.hooks._context import Context
    from xnano.hooks._handles import HookHandle

__all__ = ['CoroutineRuns', 'TaskCount', 'event_loop_of']


class TaskCount:
    """
    The runs of ``async def`` hooks on one canvas that have not finished.

    Attributes:
        idle: Set while no run is unfinished; a caller awaits it to wait for every run.
    """

    __slots__ = ('_count', '_lock', 'idle')

    def __init__(self) -> None:
        """Start with no runs."""
        self._count = 0
        self._lock = threading.Lock()
        self.idle = _AwaitableEvent()
        self.idle.set()

    def started(self) -> None:
        """Count a run that is about to start."""
        with self._lock:
            self._count += 1
            self.idle.clear()

    def finished(self) -> None:
        """Count a run that finished, was cancelled or never started."""
        with self._lock:
            self._count = max(0, self._count - 1)
            is_idle = self._count == 0
        if is_idle:
            self.idle.set()

    def forget(self) -> None:
        """Stop waiting for runs that can no longer finish, because the canvas closed."""
        with self._lock:
            self._count = 0
        self.idle.set()


def event_loop_of(canvas: Canvas[object, object]) -> asyncio.AbstractEventLoop:
    """The loop the runs of a canvas's ``async def`` hooks happen on."""
    loop = canvas._canvas._event_loop
    if loop is not None and not loop.is_closed():
        return loop
    return background_loop()


class CoroutineRuns:
    """
    The runs of one ``async def`` hook that have not finished, and what a new run does to them.

    Attributes:
        if_running: What a run that starts while another has not finished does.
    """

    __slots__ = ('_lock', '_tasks', 'if_running')

    def __init__(self, if_running: IfRunning) -> None:
        """
        Track the runs of one hook.

        Args:
            if_running: What a run that starts while another has not finished does.
        """
        self.if_running: IfRunning = if_running
        self._tasks: list[asyncio.Task[None]] = []
        self._lock = threading.Lock()

    def start(
        self, handle: HookHandle[object, object], context: Context[object, object]
    ) -> None:
        """Start a run for something the hook heard. Called on the canvas's loop."""
        canvas = handle._owner._canvas._canvas
        loop = event_loop_of(canvas)
        count = canvas._task_count()
        count.started()

        def begin() -> None:
            # On the event loop's thread, so the tasks are only touched there.
            if handle._removed or canvas._is_closed:
                count.finished()
                return
            with self._lock:
                unfinished = [task for task in self._tasks if not task.done()]
            if self.if_running == 'ignore' and unfinished:
                count.finished()
                return
            if self.if_running == 'replace':
                for task in unfinished:
                    task.cancel()
            previous = (
                unfinished[-1] if self.if_running == 'queue' and unfinished else None
            )
            task = loop.create_task(self._run(handle, context, previous))
            with self._lock:
                self._tasks = [*unfinished, task]

            def done(finished: asyncio.Task[None]) -> None:
                with self._lock:
                    if finished in self._tasks:
                        self._tasks.remove(finished)
                count.finished()

            task.add_done_callback(done)

        if running_loop() is loop:
            begin()
            return
        try:
            loop.call_soon_threadsafe(begin)
        except RuntimeError:
            # The program's loop has closed, so this run can never happen.
            count.finished()

    async def _run(
        self,
        handle: HookHandle[object, object],
        context: Context[object, object],
        previous: asyncio.Task[None] | None,
    ) -> None:
        import asyncio

        if previous is not None:
            # Queued: the earlier run finishes first, however it ends.
            await asyncio.wait({previous})
        try:
            await cast('asyncio.Future[None]', handle.function(context))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            root = handle._owner._canvas._canvas
            if root._is_closed:
                return
            failure = error
            event = context._event
            owner = handle._owner

            def fail() -> None:
                owner._fail(handle.function, event, failure)

            # The canvas stops on its own loop, the way it does when a plain hook fails.
            root._host.post(fail)

    def cancel(self) -> None:
        """Cancel every unfinished run. Safe from any thread."""
        with self._lock:
            tasks, self._tasks = self._tasks, []
        for task in tasks:
            loop = task.get_loop()
            if loop.is_closed():
                continue
            if running_loop() is loop:
                task.cancel()
                continue
            try:
                loop.call_soon_threadsafe(task.cancel)
            except RuntimeError:
                pass
