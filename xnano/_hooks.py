"""
xnano._hooks

Hooks and the triggers that decide when they run.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Generator, Sequence
from types import EllipsisType
from typing import TYPE_CHECKING, Generic, TypeAlias, cast, overload

import xnano_core as _core
from xnano_core import CoreContext

if TYPE_CHECKING:
    from xnano.canvas import Canvas
    from xnano.operations import ContextualOperation, OperationResult, OperationTrigger
    from xnano.placement import Placement

from xnano._values import DepsT, StateT
from xnano.context import Context, Frame, Update
from xnano.errors import TerminalError

HappenedEvent: TypeAlias = _core.Event | _core.TerminalStateChange | None
"""What a trigger or hook generator is sent: the next event, or ``None`` when a wait ran out."""

TriggerGenerator: TypeAlias = Generator[float | None, HappenedEvent, HappenedEvent]
"""A trigger that spans time: it yields seconds to wait and returns the event that counts."""

HookGenerator: TypeAlias = Generator[float | None, HappenedEvent, None]
"""A hook that spans time: it yields seconds to wait for the next event."""

Trigger: TypeAlias = Callable[[Context[DepsT, StateT]], bool | TriggerGenerator]
"""Decides which events count: a function that returns true, or a [`TriggerGenerator`]."""

Hook: TypeAlias = Callable[[Context[DepsT, StateT]], None | HookGenerator]
"""What a canvas or placement calls when an event counts."""

_INPUT_EVENTS = (
    'key',
    'mouse',
    'paste',
    'resize',
    'focus_gained',
    'focus_lost',
    'state_change',
    'custom',
)


class HookHandle(Generic[DepsT, StateT]):
    """
    One hook attached to a canvas or a placement.

    ``remove`` stops the hook, cancels the timer it is waiting on and closes its
    generator.

    Attributes:
        function: The function that is called when an event counts.

    """

    function: Callable[[Context[DepsT, StateT]], object]
    """The function called with a context when an event counts."""

    def __init__(
        self,
        owner: _Hooked[DepsT, StateT],
        function: Callable[[Context[DepsT, StateT]], object],
        trigger: Trigger[DepsT, StateT] | None,
    ) -> None:
        """
        Attach a function to a canvas or placement. Use ``hook`` instead of calling this.

        Args:
            owner: The canvas or placement the hook listens on.
            function: The function to call with a [`Context`][xnano.context.Context].
            trigger: Decides which events count; without one every event counts.
        """
        self._owner = owner
        self.function = function
        self._trigger = trigger
        self._removed = False
        self._trigger_generator: TriggerGenerator | None = None
        self._hook_generator: HookGenerator | None = None
        self._timer: _core.ScheduledCall | None = None
        # The canvas time the timer is due at, kept so the timer can be armed again on the
        # runtime of a canvas that is opened on the screen.
        self._timer_due_seconds: float | None = None
        self._token = 0
        self._role: str | None = None

    def remove(self) -> None:
        """Stop this hook. Removing it twice does nothing."""
        if self._removed:
            return
        self._removed = True
        self._cancel_timer()
        for generator in (self._trigger_generator, self._hook_generator):
            if generator is not None:
                generator.close()
        self._trigger_generator = None
        self._hook_generator = None
        registrations = self._owner._registrations
        if self in registrations:
            registrations.remove(self)

    def start(self) -> None:
        """Begin a generator trigger. Runs on the canvas's loop."""
        if self._removed or not inspect.isgeneratorfunction(self._trigger):
            return
        context = self._owner._context_for(None, self)
        self._begin(self._trigger, context, role='trigger')

    def deliver(self, core_context: CoreContext) -> None:
        """Hand an event the runtime reported to this hook. Runs on the canvas's loop."""
        if self._removed:
            return
        context = self._owner._context_for(core_context, self)
        try:
            self._deliver(context)
        except Exception as error:
            self._owner._fail(self.function, context.event, error)

    def _deliver(self, context: Context[DepsT, StateT]) -> None:
        trigger = self._trigger
        if self._role == 'trigger' and self._trigger_generator is not None:
            self._resume(context.event)
            return
        if trigger is None:
            self._run_hook(context)
            return
        if inspect.isgeneratorfunction(trigger):
            if self._trigger_generator is None:
                self._begin(trigger, context, role='trigger')
            return
        if trigger(context):
            self._run_hook(context)

    def _run_hook(self, context: Context[DepsT, StateT]) -> None:
        if inspect.isgeneratorfunction(self.function):
            if self._hook_generator is None:
                self._begin(self.function, context, role='hook')
            else:
                self._role = 'hook'
                self._resume(context.event)
            return
        self.function(context)

    def _begin(
        self,
        function: Callable[[Context[DepsT, StateT]], object],
        context: Context[DepsT, StateT],
        *,
        role: str,
    ) -> None:
        generator = function(context)
        if not inspect.isgenerator(generator):
            raise TerminalError(
                f'{function!r} was started as a generator, but it returned {generator!r}. A '
                f'trigger or hook that waits must be a generator function that uses yield.'
            )
        if role == 'trigger':
            self._trigger_generator = cast('TriggerGenerator', generator)
        else:
            self._hook_generator = cast('HookGenerator', generator)
        self._role = role
        self._advance(
            cast('TriggerGenerator | HookGenerator', generator),
            start=True,
            incoming=None,
        )

    def _resume(self, incoming: HappenedEvent | Frame | Update) -> None:
        self._cancel_timer()
        generator = (
            self._trigger_generator if self._role == 'trigger' else self._hook_generator
        )
        if generator is None:
            return
        self._advance(generator, start=False, incoming=incoming)

    def _advance(
        self,
        generator: TriggerGenerator | HookGenerator,
        *,
        start: bool,
        incoming: HappenedEvent | Frame | Update,
    ) -> None:
        try:
            yielded = (
                next(generator)
                if start
                else generator.send(cast('HappenedEvent', incoming))
            )
        except StopIteration as stop:
            self._finished(stop.value)
            return
        self._arm(yielded)

    def _finished(self, value: HappenedEvent) -> None:
        role = self._role
        self._cancel_timer()
        if role == 'trigger':
            self._trigger_generator = None
            self._role = None
            context = self._owner._context_for(None, self, event=value)
            self._run_hook(context)
            if not self._removed and inspect.isgeneratorfunction(self._trigger):
                self._begin(self._trigger, context, role='trigger')
            return
        self._hook_generator = None
        self._role = None

    def _arm(self, yielded: float | None) -> None:
        if yielded is None:
            return
        runtime = self._owner._canvas._runtime
        self._timer_due_seconds = runtime.clock.elapsed_seconds + max(0.0, float(yielded))
        self._schedule(runtime)

    def _schedule(self, runtime: _core.Runtime) -> None:
        """Ask ``runtime`` to resume this hook when its timer is due."""
        due = self._timer_due_seconds
        if due is None:
            return
        self._token += 1
        token = self._token
        role = self._role

        def fire() -> None:
            if token != self._token or self._removed or self._role != role:
                return
            self._timer = None
            self._timer_due_seconds = None
            self._resume(None)

        remaining = max(0.0, due - runtime.clock.elapsed_seconds)
        self._timer = runtime.call_later(remaining, fire)

    def _unbind(self) -> None:
        """Cancel the timer on the runtime that is going away, and keep when it is due."""
        timer = self._timer
        self._timer = None
        if timer is not None:
            timer.cancel()

    def _rebind(self, runtime: _core.Runtime) -> None:
        """Arm the timer again on a new runtime, for the time that was left."""
        if not self._removed:
            self._schedule(runtime)

    def _needed_gates(self) -> frozenset[str]:
        """The input gates of a screen this hook needs to hear its events."""
        trigger = self._trigger
        kind = trigger.kind if isinstance(trigger, _core.Trigger) else None
        if kind in ('click', 'drag', 'mouse'):
            return frozenset({'mouse'})
        if kind == 'paste':
            return frozenset({'paste'})
        return frozenset()

    def _cancel_timer(self) -> None:
        self._token += 1
        self._timer_due_seconds = None
        timer = self._timer
        self._timer = None
        if timer is not None:
            timer.cancel()


def _wait(seconds: Callable[[], float]) -> Trigger[DepsT, StateT]:
    """Wait the number of seconds ``seconds()`` gives, read again each time it starts."""

    def trigger(context: Context[DepsT, StateT]) -> TriggerGenerator:
        deadline = context.time.elapsed + seconds()
        while True:
            event = yield max(0.0, deadline - context.time.elapsed)
            if event is None:
                return None  # noqa: B901

    return trigger


class _Hooked(Generic[DepsT, StateT]):
    """Hooks for an object that owns a buffer."""

    _canvas: Canvas[DepsT, StateT]
    _buffer: _core.Buffer

    def __init__(self) -> None:
        """
        Prepare the list of hooks. Used by [`Canvas`][xnano.canvas.Canvas] and
        [`Placement`][xnano.placement.Placement].
        """
        self._registrations: list[HookHandle[DepsT, StateT]] = []
        self._core_hook: _core.Hook | None = None

    @overload
    def hook(
        self,
        function: Callable[[Context[DepsT, StateT]], object],
        /,
        *,
        when: Trigger[DepsT, StateT] | None = None,
    ) -> HookHandle[DepsT, StateT]: ...
    @overload
    def hook(
        self, /, *, when: Trigger[DepsT, StateT]
    ) -> Callable[[Hook[DepsT, StateT]], HookHandle[DepsT, StateT]]: ...
    @overload
    def hook(
        self,
        function: Callable[[Context[DepsT, StateT]], OperationResult],
        /,
        *,
        on: OperationTrigger,
        every: float | None = None,
        after: float | None = None,
        keys: str | Sequence[str] | None = None,
        when: Trigger[DepsT, StateT] | None = None,
    ) -> ContextualOperation[DepsT, StateT]: ...
    @overload
    def hook(
        self,
        function: Callable[[Context[DepsT, StateT]], OperationResult],
        /,
        *,
        on: OperationTrigger = 'frame',
        every: float,
        after: float | None = None,
        keys: str | Sequence[str] | None = None,
        when: Trigger[DepsT, StateT] | None = None,
    ) -> ContextualOperation[DepsT, StateT]: ...
    @overload
    def hook(
        self,
        function: Callable[[Context[DepsT, StateT]], OperationResult],
        /,
        *,
        on: OperationTrigger = 'frame',
        every: float | None = None,
        after: float,
        keys: str | Sequence[str] | None = None,
        when: Trigger[DepsT, StateT] | None = None,
    ) -> ContextualOperation[DepsT, StateT]: ...
    @overload
    def hook(
        self,
        /,
        *,
        on: OperationTrigger,
        every: float | None = None,
        after: float | None = None,
        keys: str | Sequence[str] | None = None,
        when: Trigger[DepsT, StateT] | None = None,
    ) -> Callable[
        [Callable[[Context[DepsT, StateT]], OperationResult]],
        ContextualOperation[DepsT, StateT],
    ]: ...
    @overload
    def hook(
        self,
        /,
        *,
        on: OperationTrigger = 'frame',
        every: float,
        after: float | None = None,
        keys: str | Sequence[str] | None = None,
        when: Trigger[DepsT, StateT] | None = None,
    ) -> Callable[
        [Callable[[Context[DepsT, StateT]], OperationResult]],
        ContextualOperation[DepsT, StateT],
    ]: ...
    @overload
    def hook(
        self,
        /,
        *,
        on: OperationTrigger = 'frame',
        every: float | None = None,
        after: float,
        keys: str | Sequence[str] | None = None,
        when: Trigger[DepsT, StateT] | None = None,
    ) -> Callable[
        [Callable[[Context[DepsT, StateT]], OperationResult]],
        ContextualOperation[DepsT, StateT],
    ]: ...
    def hook(
        self,
        function: Callable[[Context[DepsT, StateT]], object] | None = None,
        /,
        *,
        when: Trigger[DepsT, StateT] | None = None,
        on: OperationTrigger | None = None,
        every: float | None = None,
        after: float | None = None,
        keys: str | Sequence[str] | None = None,
    ) -> (
        HookHandle[DepsT, StateT]
        | ContextualOperation[DepsT, StateT]
        | Callable[[Hook[DepsT, StateT]], HookHandle[DepsT, StateT]]
        | Callable[
            [Callable[[Context[DepsT, StateT]], OperationResult]],
            ContextualOperation[DepsT, StateT],
        ]
    ):
        """
        Call a function when this target hears an event.

        Use it bare to hear every event, or pass a trigger that decides which events
        count. A trigger is a function of the context that returns true, or a generator
        that yields seconds to wait and returns when the event has happened.

        ``target.hook(function, when=...)`` attaches one function, and the same function
        can be attached to more than one target. Without a function, ``@target.hook(when=...)``
        decorates the function that follows.

        Give ``on``, ``every`` or ``after`` to make the function a
        [`ContextualOperation`][xnano.operations.ContextualOperation] instead: it runs on that
        trigger, may return text, a buffer, a style or an operation to draw on this target, and
        is mounted at once. ``@canvas.hook(on='frame')`` runs on every frame and
        ``@canvas.hook(every=0.5)`` twice a second.

        Args:
            function: The function to call with a [`Context`][xnano.context.Context].
            when: Decides which events count. Without one, every event counts.
            on: When a contextual operation runs, such as ``'frame'``, ``'click'`` or ``'key'``.
            every: Seconds between runs of a contextual operation.
            after: Seconds before a contextual operation runs once.
            keys: Key names a contextual operation reacts to when ``on='key'``.

        Returns:
            The hook registration (call ``remove`` to stop the hook), or the mounted
            contextual operation when ``on``, ``every`` or ``after`` is given.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=1) as canvas:
                heard = []

                def is_paste(context: xnano.context.Context) -> bool:
                    return context.pasted is not None

                @canvas.hook(when=is_paste)
                def record(context: xnano.context.Context) -> None:
                    heard.append(context.pasted)
            ```
        """
        self._canvas._require_open()
        if on is not None or every is not None or after is not None or keys is not None:
            from xnano.operations import hook as contextual_hook

            decorate = contextual_hook(
                on=on or 'frame', every=every, after=after, keys=keys, when=when
            )

            def mount(
                callback: Callable[[Context[DepsT, StateT]], OperationResult],
            ) -> ContextualOperation[DepsT, StateT]:
                operation = decorate(callback)
                operation.apply_to(
                    cast('Canvas[DepsT, StateT] | Placement[DepsT, StateT]', self)
                )
                return operation

            if function is not None:
                return mount(
                    cast('Callable[[Context[DepsT, StateT]], OperationResult]', function)
                )
            return mount
        if function is None:
            if when is None:
                raise ValueError(
                    'hook needs a function, or a when trigger to decorate one with: '
                    'canvas.hook(function) or @canvas.hook(when=trigger).'
                )

            def decorator(callback: Hook[DepsT, StateT]) -> HookHandle[DepsT, StateT]:
                return self._attach_hook(callback, when)

            return decorator
        return self._attach_hook(function, when)

    def on_key(
        self, *keys: str
    ) -> Callable[[Hook[DepsT, StateT]], HookHandle[DepsT, StateT]]:
        """
        Call the decorated function when a key is pressed, or held down so it repeats.

        Args:
            keys: The keys to react to, such as ``'q'``, ``'enter'``, ``'page_up'`` or a chord
                like ``'ctrl+s'``. Give none to react to every key.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=1) as canvas:

                @canvas.on_key('q', 'escape')
                def leave(context: xnano.context.Context) -> None:
                    context.canvas.quit()
            ```
        """
        return self.hook(when=_core.Trigger.key(*keys))

    def on_key_release(
        self, *keys: str
    ) -> Callable[[Hook[DepsT, StateT]], HookHandle[DepsT, StateT]]:
        """
        Call the decorated function when a key is let go.

        Releases are reported only by a terminal with the enhanced keyboard protocol, and
        only when the canvas was opened with ``keyboard='release_events'``.

        Args:
            keys: The key names to react to. Give none to react to every key.
        """
        return self.hook(when=_core.Trigger.key_release(*keys))

    @overload
    def on_click(self, function: Hook[DepsT, StateT], /) -> HookHandle[DepsT, StateT]: ...
    @overload
    def on_click(
        self, /
    ) -> Callable[[Hook[DepsT, StateT]], HookHandle[DepsT, StateT]]: ...
    def on_click(
        self, function: Hook[DepsT, StateT] | None = None, /
    ) -> (
        HookHandle[DepsT, StateT]
        | Callable[[Hook[DepsT, StateT]], HookHandle[DepsT, StateT]]
    ):
        """
        Call the function when a mouse button is pressed on this target.

        The pointer's cell is ``context.mouse.position``. Open the canvas with
        ``mouse=True`` to receive clicks. Use it as ``@canvas.on_click``.
        """
        return self._with_function(_core.Trigger.click(), function)

    @overload
    def on_drag(self, function: Hook[DepsT, StateT], /) -> HookHandle[DepsT, StateT]: ...
    @overload
    def on_drag(
        self, /
    ) -> Callable[[Hook[DepsT, StateT]], HookHandle[DepsT, StateT]]: ...
    def on_drag(
        self, function: Hook[DepsT, StateT] | None = None, /
    ) -> (
        HookHandle[DepsT, StateT]
        | Callable[[Hook[DepsT, StateT]], HookHandle[DepsT, StateT]]
    ):
        """
        Call the function while the pointer moves with a mouse button held down.

        Open the canvas with ``mouse=True`` to receive drags. Use it as
        ``@canvas.on_drag``.
        """
        return self._with_function(_core.Trigger.drag(), function)

    def every(
        self, seconds: float | None = None, *, beats: float | None = None
    ) -> Callable[[Hook[DepsT, StateT]], HookHandle[DepsT, StateT]]:
        """
        Call the decorated function at a steady interval on the canvas's clock.

        Give ``seconds`` for a time, or ``beats`` for music: a beat lasts as long as the
        canvas's [`bpm`][xnano.canvas.Canvas.bpm] says, and a change of tempo applies from
        the next call. The wait follows the clock, so [`stop`][xnano.time.Time.stop] stops it
        too. Events that arrive during the wait do not count, and ``context.event`` is ``None``.

        Args:
            seconds: The time between calls.
            beats: The number of beats between calls, such as ``1`` or ``0.5``.

        Raises:
            ValueError: Neither or both of ``seconds`` and ``beats`` were given.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=1) as canvas:
                ticks = []

                @canvas.every(0.1)
                def tick(context: xnano.context.Context) -> None:
                    ticks.append(context.time.elapsed)

                canvas.step(delta_seconds=0.25)
            assert len(ticks) >= 1
            ```
        """
        if (seconds is None) == (beats is None):
            raise ValueError(
                'every needs either seconds or beats, such as every(0.5) or every(beats=1), '
                'and not both.'
            )
        if seconds is not None:
            return self.hook(when=_wait(lambda: seconds))
        beats_per_call = cast('float', beats)
        return self.hook(when=_wait(lambda: beats_per_call * 60.0 / self._canvas.bpm))

    def after(
        self, seconds: float
    ) -> Callable[[Hook[DepsT, StateT]], HookHandle[DepsT, StateT]]:
        """
        Call the decorated function once, after ``seconds`` on the canvas's clock.

        Args:
            seconds: The delay before the function runs.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=1) as canvas:
                seen = []

                @canvas.after(0.1)
                def later(context: xnano.context.Context) -> None:
                    seen.append(context.time.elapsed)

                canvas.step(delta_seconds=0.3)
            assert len(seen) == 1
            ```
        """

        def decorator(callback: Hook[DepsT, StateT]) -> HookHandle[DepsT, StateT]:
            @functools.wraps(callback)
            def once(context: Context[DepsT, StateT]) -> None | HookGenerator:
                context.hook.remove()
                return callback(context)

            return self.hook(once, when=_wait(lambda: seconds))

        return decorator

    def _with_function(
        self,
        when: Trigger[DepsT, StateT],
        function: Hook[DepsT, StateT] | None,
    ) -> (
        HookHandle[DepsT, StateT]
        | Callable[[Hook[DepsT, StateT]], HookHandle[DepsT, StateT]]
    ):
        """Attach ``function``, or return the decorator that will, for a ready-made trigger."""
        if function is None:
            return self.hook(when=when)
        return self.hook(function, when=when)

    def _attach_hook(
        self,
        function: Callable[[Context[DepsT, StateT]], object],
        trigger: Trigger[DepsT, StateT] | None,
    ) -> HookHandle[DepsT, StateT]:
        handle: HookHandle[DepsT, StateT] = HookHandle(self, function, trigger)
        self._canvas._check_gates(handle)

        def register() -> None:
            if handle._removed:
                return
            self._ensure_core_hook()
            self._registrations.append(handle)
            handle.start()

        self._canvas._host.post(register)
        return handle

    def _ensure_core_hook(self) -> None:
        if self._core_hook is not None:
            return
        self._core_hook = self._buffer.add_hook(
            self._on_core_event, events=list(_INPUT_EVENTS)
        )

    def _on_core_event(self, core_context: CoreContext) -> None:
        for registration in list(self._registrations):
            registration.deliver(core_context)

    def _context_for(
        self,
        core_context: CoreContext | None,
        handle: HookHandle[DepsT, StateT],
        event: HappenedEvent | Frame | Update | EllipsisType = ...,
    ) -> Context[DepsT, StateT]:
        canvas = self._canvas
        if event is ...:
            event = _event_of(core_context)
        key, mouse, pasted, size_changed, focus_gained = _narrow(event)
        if size_changed is not None:
            canvas._size = canvas._runtime.device.size
        bounds = _core.Rectangle(0, 0, 0, 0)
        if core_context is not None:
            bounds = core_context.bounds
        elif self._buffer is not None:
            bounds = _core.Rectangle(
                self._buffer.x, self._buffer.y, self._buffer.width, self._buffer.height
            )
        return Context(
            canvas=cast('Canvas[object, object]', canvas),
            target=cast('Canvas[object, object] | Placement[object, object]', self),
            event=event,
            hook=cast('HookHandle[object, object]', handle),
            keyboard=key,
            mouse=mouse,
            pasted=pasted,
            size_changed=size_changed,
            focus_gained=focus_gained,
            bounds=bounds,
            state=cast('StateT', canvas._state_namespace),
            core=core_context,
        )

    def _fail(
        self,
        function: Callable[[Context[DepsT, StateT]], object],
        event: object,
        error: BaseException,
    ) -> None:
        name = getattr(function, '__name__', 'hook')
        failure = TerminalError(
            f'The hook {name} failed while handling {event!r}: {type(error).__name__}: '
            f'{error}. Fix the hook, then create a new canvas with xnano.new() or '
            f'xnano.open().'
        )
        failure.__cause__ = error
        self._canvas._record_failure(failure)
        self._canvas._stop_runtime()

    def _cancel_hooks(self) -> None:
        for registration in list(self._registrations):
            registration.remove()
        if self._core_hook is not None:
            self._core_hook.cancel()
            self._core_hook = None


def _event_of(core_context: CoreContext | None) -> HappenedEvent:
    if core_context is None:
        return None
    state_change = core_context.state_change
    event: _core.Event | None = getattr(core_context, 'event', None)
    if state_change is not None and (event is None or event.kind == 'state_change'):
        return state_change
    return event


def _narrow(
    event: object,
) -> tuple[
    _core.KeyEvent | None,
    _core.MouseEvent | None,
    str | None,
    _core.Size | None,
    _core.Event | None,
]:
    if not isinstance(event, _core.Event):
        return None, None, None, None, None
    focus = event if event.kind == 'focus_gained' else None
    return event.key, event.mouse, event.pasted_text, event.size, focus
