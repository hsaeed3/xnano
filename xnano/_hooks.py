"""
xnano._hooks

Hooks: functions that a canvas or a placement calls when something happens.
"""

from __future__ import annotations

import difflib
import inspect
from collections import deque
from collections.abc import Callable, Generator, Sequence
from typing import (
    TYPE_CHECKING,
    Final,
    Generic,
    Literal,
    TypeAlias,
    cast,
    overload,
)

import xnano_core as _core
from xnano_core import CoreContext

if TYPE_CHECKING:
    from xnano._effect_controller import EffectState
    from xnano._host import _Registration
    from xnano.canvas import Canvas
    from xnano.placement import Placement

from xnano._customize import Customization
from xnano._values import DepsT, KeyName, StateT
from xnano._when import CompiledWhen, compile_when, normalize_chord
from xnano.context import Context, Frame, Update
from xnano.errors import TerminalError
from xnano.state import StateFollower, StateNamespace, _HookRun, dotted

HookKind: TypeAlias = Literal[
    'frame',
    'tick',
    'beat',
    'key',
    'mouse',
    'scroll',
    'drag',
    'paste',
    'focus',
    'resize',
    'state',
    'custom',
]
"""
When a hook runs.

``'frame'`` before each frame, ``'tick'`` at each simulation step, ``'beat'`` on the canvas's
musical beat, ``'key'``, ``'mouse'``, ``'scroll'``, ``'drag'``, ``'paste'``, ``'focus'`` and
``'resize'`` when that input arrives, ``'state'`` when state the hook read changes, and
``'custom'`` for events you push yourself. A hook without ``on`` hears every input event.
"""

When: TypeAlias = (
    'str | Callable[[Context[DepsT, StateT]], bool] | _core.Expression[bool]'
)
"""
The condition of a hook: an expression, a function of the context, or a string.

* An expression built from the scopes in [`xnano.expressions`][xnano.expressions], such as
  ``Keyboard.key == 'q'``, is checked by the runtime before Python is called.
* A function takes the context and returns ``True`` when the hook should run.
* A string such as ``"keyboard.key == 'q' and not mouse.is_down"`` is parsed once. It uses the
  names ``keyboard``, ``mouse``, ``scroll``, ``buffer``, ``parent``, ``root``, ``time`` and
  ``deps``, and the operators ``==``, ``!=``, ``<``, ``<=``, ``>``, ``>=``, ``in``, ``and``,
  ``or`` and ``not``.

A value the event did not carry, such as ``keyboard.key`` while a mouse event arrives, is
neither equal to nor different from anything, so every comparison with it is false.
"""

HookGenerator: TypeAlias = Generator[None, Context[DepsT, StateT], None]
"""A hook that spans several events: it receives the next context at each bare ``yield``."""

Hook: TypeAlias = Callable[
    [Context[DepsT, StateT]], 'object | HookGenerator[DepsT, StateT]'
]
"""What a canvas or placement calls when an event counts."""

_EVENT_KINDS: Final[dict[str | None, tuple[str, ...]]] = {
    None: ('key', 'mouse', 'paste', 'resize', 'focus_gained', 'focus_lost', 'custom'),
    'key': ('key',),
    'mouse': ('mouse',),
    'scroll': ('mouse',),
    'drag': ('mouse',),
    'paste': ('paste',),
    'focus': ('focus_gained', 'focus_lost'),
    'resize': ('resize',),
    'custom': ('custom',),
    'state': (),
}
"""The core event kinds each ``on`` listens to; ``'state'`` is followed through the state store."""

_TIMED: Final = frozenset({'frame', 'tick', 'beat'})
_LEGACY_ON: Final[dict[str, str]] = {
    'click': "on='mouse', when=\"mouse.kind == 'press'\"",
    'immediate': "on='tick', after=0.0",
    'state_change': "on='state'",
    'update': "on='tick'",
}
_MAXIMUM_CATCH_UP: Final = 100_000


def _check_hook_arguments(
    owner: _Hooked[object, object],
    on: str | None,
    every: float | None,
    after: float | None,
    keys: object,
) -> tuple[str, ...]:
    """Check the arguments of ``hook`` against each other; return the normalized keys."""
    kinds = ', '.join(
        repr(kind) for kind in (*_EVENT_KINDS, 'frame', 'tick', 'beat') if kind
    )
    if on is not None and on not in _EVENT_KINDS and on not in _TIMED:
        legacy = _LEGACY_ON.get(on)
        if legacy is not None:
            raise ValueError(
                f'on={on!r} is not a kind of hook. Use hook({legacy}) instead. The kinds '
                f'are {kinds}.'
            )
        close = difflib.get_close_matches(
            on, [kind for kind in (*_EVENT_KINDS, *_TIMED) if kind], n=1
        )
        hint = f' Did you mean {close[0]!r}?' if close else ''
        raise ValueError(f'on={on!r} is not a kind of hook.{hint} The kinds are {kinds}.')
    if on is None:
        given = [
            name
            for name, value in (('every', every), ('after', after), ('keys', keys))
            if value is not None
        ]
        if given:
            raise ValueError(
                f'{given[0]}= needs an on= to say what it applies to: use '
                f"hook(on='tick', every=...) for seconds, hook(on='beat', every=...) for "
                f"beats, or hook(on='key', keys=...) for keys. Nothing is guessed."
            )
    if every is not None and after is not None:
        raise ValueError(
            'every= and after= cannot be given together. Use every= to repeat, or after= to '
            "run once: hook(on='tick', every=2) or hook(on='tick', after=2)."
        )
    if (every is not None or after is not None) and on not in ('tick', 'beat'):
        name = 'every' if every is not None else 'after'
        raise ValueError(
            f"{name}= is for on='tick' (seconds) or on='beat' (beats), but this hook has "
            f"on={on!r}. {name}=2 means 2 seconds for on='tick' and 2 beats for on='beat'."
        )
    for name, value in (('every', every), ('after', after)):
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or (value <= 0 if name == 'every' else value < 0)
        ):
            minimum = 'above 0' if name == 'every' else '0 or more'
            raise ValueError(
                f'{name}= must be a number {minimum}, but was {value!r}. In seconds for '
                f"on='tick' and in beats for on='beat'."
            )
    if keys is not None and on != 'key':
        raise ValueError(
            f"keys= is for on='key', but this hook has on={on!r}. Write "
            f"hook(on='key', keys={keys!r}) to react to those keys."
        )
    if on == 'resize' and hasattr(owner, '_parent_owner'):
        raise ValueError(
            'resize events are reported to the canvas; register this hook on the canvas '
            "with canvas.hook(on='resize') and read context.size."
        )
    if keys is None:
        return ()
    if not isinstance(keys, (str, list, tuple, set, frozenset)):
        raise TypeError(
            f"keys= takes a key name such as 'q' or a list of them such as ['q', 'escape'], "
            f'but got {keys!r}.'
        )
    names = (keys,) if isinstance(keys, str) else tuple(cast('Sequence[str]', keys))
    return tuple(normalize_chord(name) for name in names)


class HookHandle(Generic[DepsT, StateT]):
    """
    One hook attached to a canvas or a placement.

    ``remove`` stops the hook, cancels its timer and closes its generator.

    Attributes:
        function: The function that is called when an event counts.
        on: When the hook runs, or ``None`` for a hook that hears every input event.
        is_removed: Whether ``remove`` was called.
    """

    function: Callable[[Context[DepsT, StateT]], object]
    """The function called with a context when an event counts."""
    on: HookKind | None
    """When the hook runs, or ``None`` for a hook that hears every input event."""

    def __init__(
        self,
        owner: _Hooked[DepsT, StateT],
        function: Callable[[Context[DepsT, StateT]], object],
        *,
        on: HookKind | None,
        when: CompiledWhen,
        every: float | None,
        after: float | None,
        keys: tuple[str, ...],
    ) -> None:
        """
        Attach a function to a canvas or placement. Use ``hook`` instead of calling this.

        Args:
            owner: The canvas or placement the hook listens on.
            function: The function to call with a [`Context`][xnano.context.Context].
            on: When the hook runs.
            when: The compiled condition.
            every: Seconds (``'tick'``) or beats (``'beat'``) between runs.
            after: Seconds or beats before the one run.
            keys: The normalized keys of an ``on='key'`` hook.
        """
        self._owner = owner
        self.function = function
        self.on = on
        self._when = when
        self._every = every
        self._after = after
        self._keys = keys
        self._removed = False
        self._is_generator_function = inspect.isgeneratorfunction(function)
        self._generator: Generator[None, Context[DepsT, StateT], None] | None = None
        self._core_hook: _core.Hook | None = None
        self._registration: _Registration | None = None
        self._stop_frames: Callable[[], None] | None = None
        self._due: float | None = None
        self._is_captured = False
        self._own_revisions: deque[int] = deque(maxlen=4)
        self._state_run: _HookRun = _HookRun(track=on == 'state')
        self._followed: frozenset[tuple[str | int, ...]] | None = None
        self._plugin_state: StateNamespace | None = None
        self._effect_state: EffectState | None = None

    @property
    def is_removed(self) -> bool:
        """Whether ``remove`` was called."""
        return self._removed

    def remove(self) -> None:
        """Stop this hook. Removing it twice does nothing."""
        if self._removed:
            return
        self._removed = True
        effect_state = self._effect_state
        if effect_state is not None:
            self._effect_state = None
            effect_state.clear()
        generator = self._generator
        self._generator = None
        if generator is not None and inspect.getgeneratorstate(generator) != (
            inspect.GEN_RUNNING
        ):
            generator.close()
        registrations = self._owner._registrations
        if self in registrations:
            registrations.remove(self)
        owner = self._owner
        owner._canvas._host.post(self._unregister)

    def _unregister(self) -> None:
        """Take the hook off the runtime. Runs on the canvas's loop."""
        core_hook = self._core_hook
        self._core_hook = None
        if core_hook is not None:
            core_hook.cancel()
        registration = self._registration
        self._registration = None
        if registration is not None:
            self._owner._canvas._unregister(registration)
        stop_frames = self._stop_frames
        self._stop_frames = None
        if stop_frames is not None:
            stop_frames()
        canvas = self._owner._canvas
        canvas._unfollow_state(self)
        plugin_state = self._plugin_state
        if plugin_state is not None:
            self._plugin_state = None
            plugin_state._remove()

    # -- registering ---------------------------------------------------------------------

    def _register(self) -> None:
        """Register with the runtime, once. Runs on the canvas's loop."""
        if self._removed:
            return
        owner = self._owner
        canvas = owner._canvas
        owner._registrations.append(self)
        try:
            self._register_kind(canvas, owner)
        except BaseException:
            # A hook that could not be registered must not stay listed as a live one.
            self._removed = True
            if self in owner._registrations:
                owner._registrations.remove(self)
            raise

    def _register_kind(
        self, canvas: Canvas[DepsT, StateT], owner: _Hooked[DepsT, StateT]
    ) -> None:
        """Register with the runtime in the way this hook's trigger needs."""
        kind = self.on
        if kind == 'frame':
            self._stop_frames = canvas._on_frame(self._on_frame)
        elif kind == 'tick':
            if self._after is not None:
                self._arm(lambda: self._after or 0.0)
            else:
                self._registration = canvas._on_update(
                    self._on_update, fixed_step_seconds=self._every
                )
        elif kind == 'beat':
            self._arm(self._beat_seconds)
        elif kind == 'state':
            canvas._follow_state(self, self._followed)
        else:
            self._attach_core_hook(owner._buffer)

    def _attach_core_hook(self, buffer: _core.Buffer) -> None:
        """Listen for this hook's events on ``buffer``."""
        self._core_hook = buffer.add_hook(
            self._on_core,
            events=cast('list[_core.HookEventKind]', list(_EVENT_KINDS[self.on])),
            condition=self._native_condition(),
        )

    def _move_to_buffer(self, buffer: _core.Buffer) -> None:
        """Move the hook to a new buffer of its owner. Safe to call from any thread."""

        def move() -> None:
            core_hook = self._core_hook
            if core_hook is None or self._removed:
                return
            core_hook.cancel()
            self._attach_core_hook(buffer)

        self._owner._canvas._host.post(move)

    def _native_condition(self) -> _core.Predicate | None:
        """The condition the runtime checks before Python is called."""
        from xnano_core import KeyboardScope, MouseScope, ScrollScope

        kind = self.on
        parts: list[_core.Predicate] = []
        if kind == 'key' and self._keys:
            matched = KeyboardScope.chord == self._keys[0]
            for key in self._keys[1:]:
                matched = matched | (KeyboardScope.chord == key)
            parts.append(matched & (KeyboardScope.kind != 'release'))
        elif kind == 'mouse':
            parts.append((ScrollScope.x == 0) & (ScrollScope.y == 0))
        elif kind == 'scroll':
            parts.append((ScrollScope.x != 0) | (ScrollScope.y != 0))
        elif kind == 'drag':
            parts.append(
                (MouseScope.kind == 'press')
                | (MouseScope.kind == 'drag')
                | (MouseScope.kind == 'release')
            )
        expression = self._when.expression
        if expression is not None:
            parts.append(cast('_core.Predicate', expression))
        if not parts:
            return None
        condition = parts[0]
        for part in parts[1:]:
            condition = condition & part
        return condition

    def _needed_gates(self) -> frozenset[str]:
        """The input gates of a screen this hook needs to hear its events."""
        kind = self.on
        needed: set[str] = set()
        if kind == 'key':
            needed.add('keyboard')
        elif kind in ('mouse', 'drag'):
            needed.add('mouse')
        elif kind == 'scroll':
            needed.add('scroll')
        elif kind == 'paste':
            needed.add('paste')
        elif kind == 'focus':
            needed.add('focus')
        elif kind is None:
            needed.update(
                gate for gate in ('mouse', 'scroll') if gate in self._when.reads
            )
        if self._when.mentions_release:
            needed.add('keyboard_release')
        return frozenset(needed)

    # -- timers --------------------------------------------------------------------------

    def _beat_seconds(self) -> float:
        beats = self._after if self._after is not None else self._every
        return (1.0 if beats is None else beats) * 60.0 / self._owner._canvas.bpm

    def _arm(self, seconds: Callable[[], float]) -> None:
        """Call this hook once the seconds ``seconds()`` gives have passed on the canvas clock."""
        canvas = self._owner._canvas
        self._due = None

        def factory(runtime: _core.Runtime) -> _core.ScheduledCall:
            if self._due is None:
                self._due = runtime.clock.elapsed_seconds + max(0.0, seconds())
            remaining = max(0.0, self._due - runtime.clock.elapsed_seconds)
            return runtime.call_later(remaining, self._fire)

        self._registration = canvas._register(factory)

    def _fire(self) -> None:
        """A timer is due. Runs on the canvas's loop."""
        if self._removed:
            return
        owner = self._owner
        canvas = owner._canvas
        registration = self._registration
        self._registration = None
        if registration is not None:
            canvas._unregister(registration)
        runtime = canvas._runtime
        now = runtime.clock.elapsed_seconds
        is_manual = runtime.clock.source == 'manual'
        due = self._due if self._due is not None else now
        is_repeating = self.on == 'beat' and self._after is None
        runs = 0
        while True:
            runs += 1
            self._call_timer()
            if self._removed or not is_repeating:
                return
            due += self._beat_seconds()
            if not (is_manual and due <= now and runs < _MAXIMUM_CATCH_UP):
                break
        if not is_manual:
            due = max(due, now)
        self._due = due
        self._arm_at_due()

    def _arm_at_due(self) -> None:
        canvas = self._owner._canvas
        due = self._due

        def factory(runtime: _core.Runtime) -> _core.ScheduledCall:
            assert due is not None
            remaining = max(0.0, due - runtime.clock.elapsed_seconds)
            return runtime.call_later(remaining, self._fire)

        self._registration = canvas._register(factory)

    def _call_timer(self) -> None:
        if not self._passes_expression():
            return
        try:
            self._run(self._context(None, None))
        except Exception as error:
            self._fail(None, error)

    # -- events --------------------------------------------------------------------------

    def _context(
        self,
        core_context: CoreContext | None,
        event: _core.Event | _core.TerminalStateChange | Frame | Update | None,
    ) -> Context[DepsT, StateT]:
        canvas = self._owner._canvas
        return cast(
            'Context[DepsT, StateT]',
            Context(
                canvas,
                cast('Canvas[object, object] | Placement[object, object]', self._owner),
                cast('HookHandle[object, object]', self),
                event,
                core_context,
            ),
        )

    def _passes_expression(self) -> bool:
        """Whether the native part of ``when`` holds, for the hooks the runtime does not filter."""
        expression = self._when.expression
        if expression is None:
            return True
        return bool(self._owner._buffer.inspect(expression))

    def _on_frame(self, frame: Frame) -> None:
        if self._removed:
            return
        try:
            if self._passes_expression():
                self._run(self._context(None, frame))
        except Exception as error:
            self._fail(frame, error)

    def _on_update(self, update: Update) -> None:
        if self._removed:
            return
        try:
            if self._passes_expression():
                self._run(self._context(None, update))
        except Exception as error:
            self._fail(update, error)

    def _on_core(self, core_context: CoreContext) -> None:
        """Hear an event the runtime reported and its native condition accepted."""
        if self._removed:
            return
        event = _event_of(core_context)
        try:
            kind = self.on
            if kind in ('mouse', 'scroll', 'drag') and not self._handle_pointer(
                core_context, event
            ):
                return
            self._run(self._context(core_context, event))
        except Exception as error:
            self._fail(event, error)

    def _handle_pointer(
        self,
        core_context: CoreContext,
        event: _core.Event | _core.TerminalStateChange | None,
    ) -> bool:
        """Scope a pointer event to the region and capture the pointer; say whether to run."""
        mouse = event.mouse if isinstance(event, _core.Event) else None
        if mouse is None:
            return False
        kind = self.on
        if not self._is_captured and not core_context.bounds.contains(mouse.position):
            return False
        mouse_kind = mouse.kind
        if mouse_kind == 'press' and kind in ('mouse', 'drag'):
            capture = getattr(core_context, 'capture_pointer', None)
            if capture is not None:
                capture()
            self._is_captured = True
            return kind == 'mouse'
        if mouse_kind == 'release' and kind in ('mouse', 'drag'):
            self._is_captured = False
            # Only a running generator hears the release that ends its drag.
            return kind == 'mouse' or self._generator is not None
        return True

    def _run(self, context: Context[DepsT, StateT]) -> None:
        canvas = self._owner._canvas
        run = self._state_run
        if run.is_active:
            run = _HookRun(track=run.track)
        previous = canvas._active_run
        run.begin()
        run.handle = cast('HookHandle[object, object]', self)
        canvas._active_run = run
        try:
            predicate = self._when.predicate
            if predicate is None or predicate(context):
                if self._is_generator_function:
                    self._advance(context)
                else:
                    result = self.function(context)
                    if result is not None:
                        self._apply_result(result)
        except BaseException:
            run.discard()
            raise
        finally:
            canvas._active_run = previous
        self._finish_run(canvas, run)

    def _finish_run(self, canvas: Canvas[DepsT, StateT], run: _HookRun) -> None:
        """Save what the run pushed in one transaction and note what it read."""
        run.is_active = False
        run.snapshot = None
        pending = run.pending
        if pending:
            try:
                change = canvas._commit_state(pending)
            finally:
                pending.clear()
            if change is not None:
                self._own_revisions.append(change.revision)
        if run.track and run.reads:
            reads = frozenset(run.reads)
            run.reads.clear()
            if reads != self._followed:
                self._followed = reads
                canvas._follow_state(self, reads)

    def _state_followed(self, change: _core.TerminalStateChange) -> None:
        """Run again because state this hook follows changed. Runs on the canvas's loop."""
        if self._removed:
            return
        try:
            if self._passes_expression():
                self._run(self._context(None, change))
        except Exception as error:
            self._fail(change, error)

    def _state_loop(
        self, change: _core.TerminalStateChange, others: list[StateFollower]
    ) -> None:
        """Report that this hook keeps being run again by hooks that change what it reads."""
        names = [_hook_name(self.function)]
        names.extend(
            _hook_name(other.function)
            for other in others
            if isinstance(other, HookHandle)
        )
        path = dotted(change.paths[0]) if change.paths else ''
        if len(names) == 1:
            text = (
                f'The hook {names[0]!r} keeps being run again because {path!r} keeps '
                f'changing. Make the hook stop writing what it reads, or write only when the '
                f'value differs.'
            )
        else:
            listed = ', '.join(repr(name) for name in names[:-1]) + f' and {names[-1]!r}'
            text = (
                f'The hooks {listed} keep changing {path!r} for each other. Make one of '
                f'them stop writing it, or write only when the value differs.'
            )
        self._fail(change, TerminalError(text))

    def _state_namespace(self) -> StateNamespace:
        """The namespace of this hook's own state, which ``context.plugin.state`` returns."""
        namespace = self._plugin_state
        if namespace is None:
            namespace = self._plugin_state = self._owner._canvas._new_state_namespace(
                'plugins'
            )
        return namespace

    def _advance(self, context: Context[DepsT, StateT]) -> None:
        """Start the generator, or resume it with the newest context."""
        generator = self._generator
        try:
            if generator is None:
                generator = cast(
                    'Generator[None, Context[DepsT, StateT], None]',
                    self.function(context),
                )
                if not inspect.isgenerator(generator):
                    raise TerminalError(
                        f'{self.function!r} was started as a generator, but it returned '
                        f'{generator!r}. A hook that spans several events must be a '
                        f'generator function that uses yield.'
                    )
                self._generator = generator
                yielded = next(generator)
            else:
                yielded = generator.send(context)
        except StopIteration:
            self._generator = None
            return
        if yielded is not None:
            generator.close()
            self._generator = None
            raise TerminalError(
                f'A hook generator must yield nothing, but it yielded {yielded!r}. Write '
                f"'context = yield' to wait for the next event. To wait for time, use "
                f"hook(on='tick', every=...) or hook(on='tick', after=...)."
            )

    def _apply_result(self, result: object) -> None:
        """Apply a returned operation, style or effect to the hook's buffer."""
        from xnano.operations import ContextualOperation

        owner = self._owner
        if isinstance(result, (ContextualOperation, Customization)):
            result.apply_to(owner)  # type: ignore[arg-type]
            return
        if isinstance(result, (_core.Operation, _core.Style)):
            owner.update(result)  # type: ignore[attr-defined]
            return
        if isinstance(result, (str, _core.Buffer)) or hasattr(result, '__xnano_render__'):
            name = getattr(self.function, '__name__', 'hook')
            raise TerminalError(
                f'The hook {name} returned content to draw, but a hook cannot return '
                f'content. Use @xnano.renderable for content that changes, or write it '
                f'with canvas.write(...).'
            )

    def _fail(self, event: object, error: BaseException) -> None:
        self._owner._fail(self.function, event, error)

    # -- moving to another runtime -------------------------------------------------------

    def _unbind(self) -> None:
        """Let go of what belongs to the runtime that is going away."""

    def _rebind(self, runtime: _core.Runtime) -> None:
        """Register again with a new runtime."""
        if self.on == 'state' and not self._removed:
            self._owner._canvas._follow_state(self, self._followed)


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

    def _require_attached(self) -> None:
        """Raise when this object can no longer hold a hook."""
        self._canvas._require_open()

    @overload
    def hook(
        self,
        function: Hook[DepsT, StateT],
        /,
        *,
        on: HookKind | None = None,
        when: When[DepsT, StateT] | None = None,
        every: float | None = None,
        after: float | None = None,
        keys: KeyName | Sequence[KeyName] | None = None,
        requires_deps: bool = False,
    ) -> HookHandle[DepsT, StateT]: ...
    @overload
    def hook(
        self,
        /,
        *,
        on: HookKind | None = None,
        when: When[DepsT, StateT] | None = None,
        every: float | None = None,
        after: float | None = None,
        keys: KeyName | Sequence[KeyName] | None = None,
        requires_deps: bool = False,
    ) -> Callable[[Hook[DepsT, StateT]], HookHandle[DepsT, StateT]]: ...
    def hook(
        self,
        function: Hook[DepsT, StateT] | None = None,
        /,
        *,
        on: HookKind | None = None,
        when: When[DepsT, StateT] | None = None,
        every: float | None = None,
        after: float | None = None,
        keys: KeyName | Sequence[KeyName] | None = None,
        requires_deps: bool = False,
    ) -> (
        HookHandle[DepsT, StateT]
        | Callable[[Hook[DepsT, StateT]], HookHandle[DepsT, StateT]]
    ):
        """
        Call a function when something happens on this canvas or placement.

        ``on`` says what to listen to. A hook without ``on`` hears every input event. A mouse,
        scroll or drag hook on a placement hears only the pointer inside the placement, and a
        press inside holds the pointer for the hook until the button is released. A hook that
        matches an event stops it from reaching the parent; a hook that does not match lets it
        through.

        ``hook(function, ...)`` attaches one function, and ``@target.hook(...)`` decorates the
        function that follows. A hook function may be a generator that receives a new context
        at each bare ``yield``: write ``context = yield``. A drag is a loop that runs while
        ``context.mouse.is_down``.

        ``every`` and ``after`` are seconds for ``on='tick'`` and beats for ``on='beat'``:
        ``every=2`` means 2 seconds for a tick hook and 2 beats for a beat hook. On a canvas
        from ``new()`` a hook that is due several times in one ``step`` runs once for each
        interval. The function's return value is ignored, unless it is an operation, a style
        or an effect, which is applied to this target.

        Args:
            function: The function to call with a [`Context`][xnano.context.Context].
            on: What to listen to: ``'frame'``, ``'tick'``, ``'beat'``, ``'key'``, ``'mouse'``,
                ``'scroll'``, ``'drag'``, ``'paste'``, ``'focus'``, ``'resize'``, ``'state'``
                or ``'custom'``. See [`HookKind`][xnano.types.HookKind].
            when: A condition that must hold: an expression, a function of the context, or a
                string. See [`When`][xnano.types.When]. A string tells xnano which input
                the hook needs, so the mouse, scroll and key-release gates it reads are
                turned on when the canvas opens. An expression or a function does not, so a
                condition that reads ``Mouse``, ``Scroll`` or key releases needs the gate set
                on ``new()`` or ``open()`` yourself: ``mouse=True``, ``scroll=True`` or
                ``keyboard='release_events'``.
            every: Repeat every this many seconds (``'tick'``) or beats (``'beat'``).
            after: Run once after this many seconds (``'tick'``) or beats (``'beat'``).
            keys: The key or keys an ``on='key'`` hook reacts to, such as ``'q'`` or
                ``'ctrl+s'``. A key hook with keys hears presses and repeats; omit them and
                test ``keyboard.kind`` to hear releases.
            requires_deps: Whether the hook needs the dependencies given to
                ``new(deps=...)``.

        Returns:
            The hook, whose ``remove`` stops it; or, without a function, the decorator.

        Raises:
            ValueError: The combination of arguments does not make sense, a key name is
                unknown, or a ``when`` string is not a condition. The message says what to
                write instead.
            TypeError: ``when`` is a plain ``bool``.
            TerminalError: ``requires_deps`` is true and the canvas was created without
                ``deps``, or the canvas is on a screen with an input gate this hook needs
                turned off.

        Examples:
            ```python
            import xnano
            from xnano_core import Event

            with xnano.new(width=8, height=1) as canvas:
                heard = []

                @canvas.hook(on='key', keys=['q', 'escape'])
                def leave(context: xnano.context.Context) -> None:
                    heard.append(context.keyboard.key)

                @canvas.hook(on='tick', every=0.5)
                def blink(context: xnano.context.Context) -> None:
                    heard.append('tick')

                canvas.push(Event.key_press('q'))
                canvas.step(delta_seconds=1.0)
                assert heard == ['q', 'tick', 'tick']
            ```
        """
        canvas = self._canvas
        canvas._require_open()
        owner = cast('_Hooked[object, object]', self)
        normalized_keys = _check_hook_arguments(owner, on, every, after, keys)
        compiled = compile_when(when)
        if on is None and not compiled.is_opaque and compiled.reads:
            if not compiled.reads & {'keyboard', 'mouse', 'scroll'}:
                raise ValueError(
                    'when reads time, the size of the parent or deps, but a hook with no on= is '
                    'only checked when an input event arrives. Add on="tick" or '
                    'on="frame" so it is checked as time passes, or read an input in the '
                    'condition.'
                )
        if requires_deps and not canvas._deps_given:
            raise TerminalError(
                'This hook needs dependencies (requires_deps=True), but the canvas has none '
                'yet. Give them when you create the canvas: xnano.new(deps=your_dependencies) '
                'or xnano.open(deps=your_dependencies), or open the canvas with '
                'canvas.open(deps=your_dependencies) before you register this hook.'
            )

        def attach(
            callback: Hook[DepsT, StateT],
        ) -> HookHandle[DepsT, StateT]:
            return self._attach_hook(
                cast('Callable[[Context[DepsT, StateT]], object]', callback),
                on=on,
                when=compiled,
                every=every,
                after=after,
                keys=normalized_keys,
            )

        if function is None:
            return attach
        return attach(function)

    def _attach_hook(
        self,
        function: Callable[[Context[DepsT, StateT]], object],
        *,
        on: HookKind | None,
        when: CompiledWhen,
        every: float | None,
        after: float | None,
        keys: tuple[str, ...],
    ) -> HookHandle[DepsT, StateT]:
        self._require_attached()
        handle: HookHandle[DepsT, StateT] = HookHandle(
            self, function, on=on, when=when, every=every, after=after, keys=keys
        )
        self._canvas._check_gates(handle)
        if on == 'state':
            # A state change pushed right after this call must reach the hook, so it
            # subscribes before the call returns.
            self._canvas._host.call(handle._register)
        else:
            self._canvas._host.post(handle._register)
        return handle

    def _fail(
        self,
        function: Callable[[Context[DepsT, StateT]], object],
        event: object,
        error: BaseException,
    ) -> None:
        name = getattr(function, '__name__', 'hook')
        failure = TerminalError(
            f'The hook {name} failed while handling {event!r}: {type(error).__name__}: '
            f'{str(error).rstrip(".")}. Fix the hook, then create a new canvas with xnano.new() or '
            f'xnano.open().'
        )
        failure.__cause__ = error
        self._canvas._record_failure(failure)
        self._canvas._stop_requested.set()
        self._canvas._stop_runtime()

    def _cancel_hooks(self) -> None:
        for registration in list(self._registrations):
            registration.remove()


def _hook_name(function: Callable[..., object]) -> str:
    return getattr(function, '__name__', 'hook')


def _event_of(core_context: CoreContext) -> _core.Event | None:
    event: _core.Event | None = getattr(core_context, 'event', None)
    return event
