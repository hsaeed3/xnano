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
    from xnano.operations import ContextualOperation, OperationResult, OperationTrigger
    from xnano.placement import Placement
    from xnano.terminal import Terminal

from xnano._values import StateT
from xnano.context import Context
from xnano.errors import TerminalError

HappenedEvent: TypeAlias = _core.Event | _core.TerminalStateChange | None
"""What a trigger or hook generator is sent: the next event, or ``None`` when a wait ran out."""

TriggerGenerator: TypeAlias = Generator[float | None, HappenedEvent, HappenedEvent]
"""A trigger that spans time: it yields seconds to wait and returns the event that counts."""

HookGenerator: TypeAlias = Generator[float | None, HappenedEvent, None]
"""A hook that spans time: it yields seconds to wait for the next event."""

Trigger: TypeAlias = Callable[[Context[StateT]], bool | TriggerGenerator]
"""Decides which events count: a function that returns true, or a [`TriggerGenerator`]."""

Hook: TypeAlias = Callable[[Context[StateT]], None | HookGenerator]
"""What a terminal or placement calls when an event counts."""

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


class HookHandle(Generic[StateT]):
    """
    One hook attached to a terminal or a placement.

    ``remove`` stops the hook, cancels the timer it is waiting on and closes its
    generator.

    Attributes:
        function: The function that is called when an event counts.

    """

    function: Callable[[Context[StateT]], object]
    """The function called with a context when an event counts."""

    def __init__(
        self,
        owner: _Hooked[StateT],
        function: Callable[[Context[StateT]], object],
        trigger: Trigger[StateT] | None,
    ) -> None:
        """
        Attach a function to a terminal or placement. Use ``hook`` instead of calling this.

        Args:
            owner: The terminal or placement the hook listens on.
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
        """Begin a generator trigger. Runs on the terminal's loop."""
        if self._removed or not inspect.isgeneratorfunction(self._trigger):
            return
        context = self._owner._context_for(None, self)
        self._begin(self._trigger, context, role='trigger')

    def deliver(self, core_context: CoreContext) -> None:
        """Hand an event the runtime reported to this hook. Runs on the terminal's loop."""
        if self._removed:
            return
        context = self._owner._context_for(core_context, self)
        try:
            self._deliver(context)
        except Exception as error:
            self._owner._fail(self.function, context.event, error)

    def _deliver(self, context: Context[StateT]) -> None:
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

    def _run_hook(self, context: Context[StateT]) -> None:
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
        function: Callable[[Context[StateT]], object],
        context: Context[StateT],
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

    def _resume(self, incoming: HappenedEvent) -> None:
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
        incoming: HappenedEvent,
    ) -> None:
        try:
            yielded = next(generator) if start else generator.send(incoming)
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
        seconds = float(yielded)
        self._token += 1
        token = self._token
        role = self._role

        def fire() -> None:
            if token != self._token or self._removed or self._role != role:
                return
            self._resume(None)

        self._timer = self._owner._terminal._runtime.call_later(max(0.0, seconds), fire)

    def _cancel_timer(self) -> None:
        self._token += 1
        timer = self._timer
        self._timer = None
        if timer is not None:
            timer.cancel()


def _wait(seconds: Callable[[], float]) -> Trigger[StateT]:
    """Wait the number of seconds ``seconds()`` gives, read again each time it starts."""

    def trigger(context: Context[StateT]) -> TriggerGenerator:
        deadline = context.time.elapsed + seconds()
        while True:
            event = yield max(0.0, deadline - context.time.elapsed)
            if event is None:
                return None  # noqa: B901

    return trigger


class _Hooked(Generic[StateT]):
    """Hooks for an object that owns a buffer."""

    _terminal: Terminal[StateT]
    _buffer: _core.Buffer

    def __init__(self) -> None:
        """
        Prepare the list of hooks. Used by [`Terminal`][xnano.terminal.Terminal] and
        [`Placement`][xnano.placement.Placement].
        """
        self._registrations: list[HookHandle] = []
        self._core_hook: _core.Hook | None = None

    @overload
    def hook(
        self,
        function: Callable[[Context[StateT]], object],
        /,
        *,
        when: Trigger[StateT] | None = None,
    ) -> HookHandle[StateT]: ...
    @overload
    def hook(
        self, /, *, when: Trigger[StateT]
    ) -> Callable[[Hook[StateT]], HookHandle[StateT]]: ...
    @overload
    def hook(
        self,
        function: Callable[[Context[StateT]], OperationResult],
        /,
        *,
        on: OperationTrigger,
        every: float | None = None,
        after: float | None = None,
        keys: str | Sequence[str] | None = None,
        when: Trigger[StateT] | None = None,
    ) -> ContextualOperation[StateT]: ...
    @overload
    def hook(
        self,
        function: Callable[[Context[StateT]], OperationResult],
        /,
        *,
        on: OperationTrigger = 'frame',
        every: float,
        after: float | None = None,
        keys: str | Sequence[str] | None = None,
        when: Trigger[StateT] | None = None,
    ) -> ContextualOperation[StateT]: ...
    @overload
    def hook(
        self,
        function: Callable[[Context[StateT]], OperationResult],
        /,
        *,
        on: OperationTrigger = 'frame',
        every: float | None = None,
        after: float,
        keys: str | Sequence[str] | None = None,
        when: Trigger[StateT] | None = None,
    ) -> ContextualOperation[StateT]: ...
    @overload
    def hook(
        self,
        /,
        *,
        on: OperationTrigger,
        every: float | None = None,
        after: float | None = None,
        keys: str | Sequence[str] | None = None,
        when: Trigger[StateT] | None = None,
    ) -> Callable[
        [Callable[[Context[StateT]], OperationResult]], ContextualOperation[StateT]
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
        when: Trigger[StateT] | None = None,
    ) -> Callable[
        [Callable[[Context[StateT]], OperationResult]], ContextualOperation[StateT]
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
        when: Trigger[StateT] | None = None,
    ) -> Callable[
        [Callable[[Context[StateT]], OperationResult]], ContextualOperation[StateT]
    ]: ...
    def hook(
        self,
        function: Callable[[Context[StateT]], object] | None = None,
        /,
        *,
        when: Trigger[StateT] | None = None,
        on: OperationTrigger | None = None,
        every: float | None = None,
        after: float | None = None,
        keys: str | Sequence[str] | None = None,
    ) -> (
        HookHandle[StateT]
        | ContextualOperation[StateT]
        | Callable[[Hook[StateT]], HookHandle[StateT]]
        | Callable[
            [Callable[[Context[StateT]], OperationResult]], ContextualOperation[StateT]
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
        is mounted at once. ``@terminal.hook(on='frame')`` runs on every frame and
        ``@terminal.hook(every=0.5)`` twice a second.

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

            with xnano.open(offscreen=True, width=8, height=1) as terminal:
                heard = []

                def is_paste(context: xnano.context.Context) -> bool:
                    return context.pasted is not None

                @terminal.hook(when=is_paste)
                def record(context: xnano.context.Context) -> None:
                    heard.append(context.pasted)
            ```
        """
        self._terminal._require_open()
        if on is not None or every is not None or after is not None or keys is not None:
            from xnano.operations import hook as contextual_hook

            decorate = contextual_hook(
                on=on or 'frame', every=every, after=after, keys=keys, when=when
            )

            def mount(
                callback: Callable[[Context[StateT]], OperationResult],
            ) -> ContextualOperation[StateT]:
                operation = decorate(callback)
                operation.apply_to(cast('Terminal[StateT] | Placement[StateT]', self))
                return operation

            if function is not None:
                return mount(
                    cast('Callable[[Context[StateT]], OperationResult]', function)
                )
            return mount
        if function is None:
            if when is None:
                raise ValueError(
                    'hook needs a function, or a when trigger to decorate one with: '
                    'terminal.hook(function) or @terminal.hook(when=trigger).'
                )

            def decorator(callback: Hook[StateT]) -> HookHandle[StateT]:
                return self._attach_hook(callback, when)

            return decorator
        return self._attach_hook(function, when)

    def on_key(self, *keys: str) -> Callable[[Hook[StateT]], HookHandle[StateT]]:
        """
        Call the decorated function when a key is pressed, or held down so it repeats.

        Args:
            keys: The keys to react to, such as ``'q'``, ``'enter'``, ``'page_up'`` or a chord
                like ``'ctrl+s'``. Give none to react to every key.

        Examples:
            ```python
            import xnano

            with xnano.open(offscreen=True, width=8, height=1) as terminal:

                @terminal.on_key('q', 'escape')
                def leave(context: xnano.context.Context) -> None:
                    context.terminal.stop()
            ```
        """
        return self.hook(when=_core.Trigger.key(*keys))

    def on_key_release(self, *keys: str) -> Callable[[Hook[StateT]], HookHandle[StateT]]:
        """
        Call the decorated function when a key is let go.

        Releases are reported only by a terminal with the enhanced keyboard protocol, and
        only when it was opened with ``keyboard='release_events'``.

        Args:
            keys: The key names to react to. Give none to react to every key.
        """
        return self.hook(when=_core.Trigger.key_release(*keys))

    @overload
    def on_click(self, function: Hook[StateT], /) -> HookHandle[StateT]: ...
    @overload
    def on_click(self, /) -> Callable[[Hook[StateT]], HookHandle[StateT]]: ...
    def on_click(
        self, function: Hook[StateT] | None = None, /
    ) -> HookHandle[StateT] | Callable[[Hook[StateT]], HookHandle[StateT]]:
        """
        Call the function when a mouse button is pressed on this target.

        The pointer's cell is ``context.mouse.position``. Open the terminal with
        ``mouse=True`` to receive clicks. Use it as ``@terminal.on_click``.
        """
        return self._with_function(_core.Trigger.click(), function)

    @overload
    def on_drag(self, function: Hook[StateT], /) -> HookHandle[StateT]: ...
    @overload
    def on_drag(self, /) -> Callable[[Hook[StateT]], HookHandle[StateT]]: ...
    def on_drag(
        self, function: Hook[StateT] | None = None, /
    ) -> HookHandle[StateT] | Callable[[Hook[StateT]], HookHandle[StateT]]:
        """
        Call the function while the pointer moves with a mouse button held down.

        Open the terminal with ``mouse=True`` to receive drags. Use it as
        ``@terminal.on_drag``.
        """
        return self._with_function(_core.Trigger.drag(), function)

    def every(
        self, seconds: float | None = None, *, beats: float | None = None
    ) -> Callable[[Hook[StateT]], HookHandle[StateT]]:
        """
        Call the decorated function at a steady interval on the terminal's clock.

        Give ``seconds`` for a time, or ``beats`` for music: a beat lasts as long as the
        terminal's [`tempo`][xnano.terminal.Terminal.tempo] says, and a change of tempo applies from
        the next call. The wait follows the clock, so [`pause`][xnano.terminal.Terminal.pause] stops it
        too. Events that arrive during the wait do not count, and ``context.event`` is ``None``.

        Args:
            seconds: The time between calls.
            beats: The number of beats between calls, such as ``1`` or ``0.5``.

        Raises:
            ValueError: Neither or both of ``seconds`` and ``beats`` were given.

        Examples:
            ```python
            import xnano

            with xnano.open(offscreen=True, width=8, height=1) as terminal:
                ticks = []

                @terminal.every(0.1)
                def tick(context: xnano.context.Context) -> None:
                    ticks.append(context.time.elapsed)

                terminal.loop.advance(0.25)
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
        return self.hook(when=_wait(lambda: beats_per_call * 60.0 / self._terminal.tempo))

    def after(self, seconds: float) -> Callable[[Hook[StateT]], HookHandle[StateT]]:
        """
        Call the decorated function once, after ``seconds`` on the terminal's clock.

        Args:
            seconds: The delay before the function runs.

        Examples:
            ```python
            import xnano

            with xnano.open(offscreen=True, width=8, height=1) as terminal:
                seen = []

                @terminal.after(0.1)
                def later(context: xnano.context.Context) -> None:
                    seen.append(context.time.elapsed)

                terminal.loop.advance(0.3)
            assert len(seen) == 1
            ```
        """

        def decorator(callback: Hook[StateT]) -> HookHandle[StateT]:
            @functools.wraps(callback)
            def once(context: Context[StateT]) -> None | HookGenerator:
                context.hook.remove()
                return callback(context)

            return self.hook(once, when=_wait(lambda: seconds))

        return decorator

    def _with_function(
        self,
        when: Trigger[StateT],
        function: Hook[StateT] | None,
    ) -> HookHandle[StateT] | Callable[[Hook[StateT]], HookHandle[StateT]]:
        """Attach ``function``, or return the decorator that will, for a ready-made trigger."""
        if function is None:
            return self.hook(when=when)
        return self.hook(function, when=when)

    def _attach_hook(
        self,
        function: Callable[[Context[StateT]], object],
        trigger: Trigger[StateT] | None,
    ) -> HookHandle[StateT]:
        handle: HookHandle[StateT] = HookHandle(self, function, trigger)

        def register() -> None:
            if handle._removed:
                return
            self._ensure_core_hook()
            self._registrations.append(handle)
            handle.start()

        self._terminal._host.post(register)
        return handle

    def _ensure_core_hook(self) -> None:
        if self._core_hook is not None:
            return
        self._core_hook = self._buffer.add_hook(
            self._on_core_event, events=list(_INPUT_EVENTS)
        )

    def _on_core_event(self, core_context: CoreContext) -> None:
        event = _event_of(core_context)
        if (
            isinstance(event, _core.Event)
            and event.kind == 'key'
            and not self._terminal._is_keyboard_enabled
        ):
            return
        for registration in list(self._registrations):
            registration.deliver(core_context)

    def _context_for(
        self,
        core_context: CoreContext | None,
        handle: HookHandle[StateT],
        event: HappenedEvent | EllipsisType = ...,
    ) -> Context[StateT]:
        terminal = self._terminal
        if event is ...:
            event = _event_of(core_context)
        key, mouse, pasted, size_changed, focus_gained = _narrow(event)
        if size_changed is not None:
            terminal._size = terminal._runtime.device.size
        bounds = _core.Rectangle(0, 0, 0, 0)
        if core_context is not None:
            bounds = core_context.bounds
        elif self._buffer is not None:
            bounds = _core.Rectangle(
                self._buffer.x, self._buffer.y, self._buffer.width, self._buffer.height
            )
        return Context(
            terminal=cast('Terminal[object]', terminal),
            target=cast('Terminal[object] | Placement[object]', self),
            event=event,
            hook=cast('HookHandle[object]', handle),
            keyboard=key,
            mouse=mouse,
            pasted=pasted,
            size_changed=size_changed,
            focus_gained=focus_gained,
            bounds=bounds,
            state=cast('StateT', terminal._state_proxy),
            core=core_context,
        )

    def _fail(
        self,
        function: Callable[[Context[StateT]], object],
        event: HappenedEvent,
        error: BaseException,
    ) -> None:
        name = getattr(function, '__name__', 'hook')
        failure = TerminalError(
            f'The hook {name} failed while handling {event!r}: {type(error).__name__}: '
            f'{error}. Fix the hook, then open a new terminal with xnano.open().'
        )
        failure.__cause__ = error
        self._terminal._record_failure(failure)
        self._terminal._stop_runtime()

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
    event: HappenedEvent,
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
