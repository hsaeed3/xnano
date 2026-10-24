"""
xnano.ai._background

Model calls started from a canvas that finish as an event on it, so a plain hook can start a
slow call and another hook can use its answer when it lands.
"""

from __future__ import annotations

import asyncio
import itertools
import re
import threading
from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any, Final, Generic, TypeVar, cast

from xnano._runtime._loops import running_loop
from xnano.ai.models import _close, _run_blocking
from xnano.errors import TerminalError
from xnano.hooks._coroutines import event_loop_of

if TYPE_CHECKING:
    from xnano._schema._hooks import IfRunning
    from xnano.canvas import Canvas
    from xnano.hooks._context import Context

__all__ = ['BackgroundRun', 'BackgroundRuns', 'background']

ResultT = TypeVar('ResultT')

_NAME: Final = re.compile(r'[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*')

_IF_RUNNING: Final = ('replace', 'ignore', 'queue', 'overlap')


class BackgroundRun(Generic[ResultT]):
    """
    One call running in the background of a canvas, such as a model's answer.

    [`BackgroundRuns.start`][xnano.ai.BackgroundRuns.start] returns one. When it finishes, the
    canvas hears the custom event ``event_name``, and a hook on that event reads the answer
    with [`BackgroundRuns.result`][xnano.ai.BackgroundRuns.result]. A run that was replaced
    or cancelled sends no event.

    Attributes:
        name: The name it was started with, such as ``'move'``.
        event_name: The custom event its finishing sends: ``'ai.'`` and the name.
        is_finished: Whether it finished, with a result or an error.
        is_cancelled: Whether it was cancelled or replaced before it finished.
        error: The error the call raised, or ``None``.
    """

    def __init__(self, name: str, identifier: str) -> None:
        """Track a run. Use ``BackgroundRuns.start`` instead of calling this."""
        self.name = name
        self.event_name = f'ai.{name}'
        self._identifier = identifier
        self._result: ResultT | None = None
        self.error: BaseException | None = None
        self.is_finished = False
        self.is_cancelled = False
        self._task: asyncio.Task[None] | None = None

    def __repr__(self) -> str:
        status = (
            'cancelled'
            if self.is_cancelled
            else 'finished'
            if self.is_finished
            else 'running'
        )
        return f'BackgroundRun({self.name!r}, {status})'

    @property
    def result(self) -> ResultT:
        """
        What the call returned.

        Raises:
            TerminalError: The run has not finished, or was cancelled.
            BaseException: The error the call raised.
        """
        if self.error is not None:
            raise self.error
        if self.is_cancelled:
            raise TerminalError(
                f'The background run {self.name!r} was cancelled, so it has no result. Read '
                f'the result in a hook on its event, which only finished runs send.'
            )
        if not self.is_finished:
            raise TerminalError(
                f'The background run {self.name!r} has not finished yet. Read the result in a '
                f'hook with on={self.event_name!r}, which runs when it has.'
            )
        return cast('ResultT', self._result)

    def cancel(self) -> None:
        """Cancel the run if it has not finished; it then sends no event. Safe from any thread."""
        if self.is_finished:
            return
        self.is_cancelled = True
        task = self._task
        if task is None:
            return
        loop = task.get_loop()
        if loop.is_closed():
            return
        if running_loop() is loop:
            task.cancel()
        else:
            loop.call_soon_threadsafe(task.cancel)


class BackgroundRuns:
    """
    The background runs of one canvas: start calls, and read their answers when they land.

    Get it with [`background`][xnano.ai.background]. A run starts on the event loop the canvas
    was created or opened in, or on xnano's own background loop. On a canvas with a manual
    clock and no event loop (a test or a script), the call runs at once, and its event is heard
    in the same ``step()`` when a hook started it, or at the next one otherwise, so the program
    stays the same from run to run.
    """

    def __init__(self, canvas: Canvas[object, object]) -> None:
        """Keep the runs of ``canvas``. Use ``background(canvas)`` instead of calling this."""
        self._canvas = canvas
        self._runs: dict[str, BackgroundRun[Any]] = {}
        self._unfinished: dict[str, list[BackgroundRun[Any]]] = {}
        self._counter = itertools.count(1)
        self._lock = threading.Lock()

    def start(
        self,
        call: Awaitable[ResultT],
        *,
        name: str,
        if_running: IfRunning = 'replace',
    ) -> BackgroundRun[ResultT]:
        """
        Start a call in the background; the canvas hears ``'ai.<name>'`` when it finishes.

        Args:
            call: What to run, such as ``pick.choose_async(context, options)``.
            name: The name of the run, such as ``'move'``: letters, digits and underscores,
                with dots between parts. Its event is ``'ai.'`` and the name.
            if_running: What happens when a run of the same name has not finished:
                ``'replace'`` cancels it, so the latest call wins; ``'ignore'`` keeps it and
                drops this call; ``'queue'`` runs this one after it; ``'overlap'`` runs both.

        Returns:
            The [`BackgroundRun`][xnano.ai.BackgroundRun].

        Raises:
            ValueError: ``name`` is not a name, or ``if_running`` is not one of its words.
            TerminalClosedError: The canvas is closed.

        Examples:
            ```python
            import xnano
            from xnano.ai.models.decisions import ChoiceModel
            from xnano.ai import background
            from xnano.ai.testing import ScriptedDecisionModel
            from xnano.events import Event

            pick = ChoiceModel(ScriptedDecisionModel({'response': 'jump'}))

            with xnano.new(width=20, height=1) as canvas:
                runs = background(canvas)
                hero = canvas.screen.write('hero')

                @canvas.hook(on='key', keys='enter')
                def ask(context: xnano.Context) -> None:
                    runs.start(pick.choose_async(context, ['jump', 'duck']), name='move')

                @canvas.hook(on='ai.move')
                def moved(context: xnano.Context) -> None:
                    hero.text = f'hero: {runs.result(context).choice}'

                canvas.push(Event.key_press('enter'))
                canvas.clock.step()
                assert canvas.screen.render() == 'hero: jump'
            ```
        """
        canvas = self._canvas
        if not isinstance(name, str) or not _NAME.fullmatch(name):
            _close(call)
            raise ValueError(
                f'A background run is named with letters, digits and underscores, with dots '
                f"between parts, such as name='move' or name='hero.move', but got {name!r}."
            )
        if if_running not in _IF_RUNNING:
            _close(call)
            raise ValueError(
                f'if_running must be one of {", ".join(repr(word) for word in _IF_RUNNING)}, '
                f'but was {if_running!r}.'
            )
        canvas._require_open()
        run: BackgroundRun[ResultT] = BackgroundRun(name, f'{name}#{next(self._counter)}')
        with self._lock:
            self._runs[run._identifier] = run
        root = canvas._canvas
        if not root._host.is_autonomous and (
            root._event_loop is None or root._event_loop.is_closed()
        ):
            # A manual clock and no event loop: run now, and be heard at the next step.
            try:
                run._result = _run_blocking(call, None)
            except Exception as error:
                run.error = error
            run.is_finished = True
            self._deliver(run)
            return run
        self._schedule(run, call, if_running)
        return run

    def _schedule(
        self, run: BackgroundRun[ResultT], call: Awaitable[ResultT], if_running: IfRunning
    ) -> None:
        canvas = self._canvas._canvas
        loop = event_loop_of(canvas)
        count = canvas._task_count()
        count.started()

        def begin() -> None:
            with self._lock:
                unfinished = [
                    other
                    for other in self._unfinished.get(run.name, [])
                    if not other.is_finished and not other.is_cancelled
                ]
            if (
                run.is_cancelled
                or canvas._is_closed
                or (if_running == 'ignore' and unfinished)
            ):
                run.is_cancelled = True
                _close(call)
                count.finished()
                return
            if if_running == 'replace':
                for other in unfinished:
                    other.cancel()
            previous = unfinished[-1] if if_running == 'queue' and unfinished else None
            task = loop.create_task(self._drive(run, call, previous))
            run._task = task
            with self._lock:
                self._unfinished[run.name] = [*unfinished, run]
            task.add_done_callback(lambda finished: count.finished())

        if running_loop() is loop:
            begin()
            return
        try:
            loop.call_soon_threadsafe(begin)
        except RuntimeError:
            run.is_cancelled = True
            _close(call)
            count.finished()

    async def _drive(
        self,
        run: BackgroundRun[ResultT],
        call: Awaitable[ResultT],
        previous: BackgroundRun[Any] | None,
    ) -> None:
        if previous is not None and previous._task is not None:
            await asyncio.wait({previous._task})
        try:
            run._result = await call
        except asyncio.CancelledError:
            run.is_cancelled = True
            raise
        except Exception as error:
            run.error = error
        finally:
            with self._lock:
                unfinished = self._unfinished.get(run.name, [])
                if run in unfinished:
                    unfinished.remove(run)
        if run.is_cancelled:
            return
        run.is_finished = True
        self._deliver(run)

    def _deliver(self, run: BackgroundRun[Any]) -> None:
        """Send the event a finished run is heard by."""
        from xnano.events import Event

        canvas = self._canvas._canvas
        if canvas._is_closed:
            return
        canvas.push(Event.custom(run.event_name, data=run._identifier))

    def run(self, context: Context[Any, Any]) -> BackgroundRun[Any]:
        """
        The run whose finishing event a hook heard.

        Args:
            context: The context of a hook on a run's event, such as ``on='ai.move'``.

        Raises:
            TerminalError: The context's event is not the finishing event of one of these runs.
        """
        event = context.event
        identifier = getattr(event, 'custom_data', None)
        with self._lock:
            run = self._runs.get(identifier) if isinstance(identifier, str) else None
        if run is None:
            name = getattr(event, 'custom_name', None)
            raise TerminalError(
                f'This hook heard {name!r}, which is not the event of a background run of this '
                f"canvas. Read results in a hook on the run's event, such as "
                f"on='ai.move' for runs.start(..., name='move')."
            )
        return run

    def result(self, context: Context[Any, Any]) -> Any:
        """
        What the run whose event a hook heard returned.

        Args:
            context: The context of a hook on a run's event, such as ``on='ai.move'``.

        Raises:
            TerminalError: The event is not the finishing event of one of these runs.
            BaseException: The error the run's call raised.
        """
        run = self.run(context)
        with self._lock:
            self._runs.pop(run._identifier, None)
        return run.result


def background(canvas: Canvas[Any, Any]) -> BackgroundRuns:
    """
    The background runs of a canvas, to start slow calls from a plain hook.

    A hook must not wait for a model, or the canvas stops drawing until it answers. A hook
    starts the call in the background instead, and a hook on the run's event uses the answer
    when it lands. In an async program, an ``async def`` hook that awaits the call is the
    shorter way; ``background()`` is for programs that do not await, and for delivering the
    answer to another hook.

    Args:
        canvas: The canvas whose runs to start; a canvas written into another one shares the
            runs of the outer one.

    Returns:
        The canvas's [`BackgroundRuns`][xnano.ai.BackgroundRuns]; the same each time.
    """
    root = cast('Canvas[object, object]', canvas)._canvas
    runs = root.__dict__.get('_background_runs')
    if runs is None:
        with root._lock:
            runs = root.__dict__.get('_background_runs')
            if runs is None:
                runs = BackgroundRuns(root)
                root._background_runs = runs  # type: ignore[attr-defined]
    return runs
