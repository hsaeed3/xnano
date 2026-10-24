"""
xnano.hooks._handles

Hooks: functions that a canvas or a placement calls when something happens.
"""

from __future__ import annotations

import difflib
import functools
import inspect
import math
import re
from collections import deque
from collections.abc import Awaitable, Callable, Generator, Sequence
from typing import TYPE_CHECKING, Final, Generic, cast, overload

import xnano_core as _core
from xnano_core import CoreContext

if TYPE_CHECKING:
    from xnano._runtime._host import _Registration
    from xnano.canvas import Canvas
    from xnano.effects._controller import EffectState
    from xnano.layout._placement import Placement

from xnano._internal._dynamic_operations import DynamicOperation
from xnano._schema._generics import DepsT, StateT
from xnano._schema._hooks import Hook, HookKind, HookTrigger, IfRunning, KeyName
from xnano.errors import TerminalError
from xnano.hooks._context import Context, Frame, Update
from xnano.hooks._coroutines import CoroutineRuns
from xnano.hooks._triggers import CompiledWhen, compile_when, normalize_binding
from xnano.state import StateNamespace, _dotted, _HookRun, _StateFollower

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
    'click': 'on="mouse.kind == \'press\'"',
    'immediate': "on='tick', after=0.0",
    'state_change': "on='state'",
    'update': "on='tick'",
}
_MAXIMUM_CATCH_UP: Final = 100_000
_HELD_BUTTON_REPEAT_DELAY_SECONDS: Final = 0.15
"""How long a mouse button is held after its press before a hook without ``on`` runs on frames."""


def _is_finite(value: float) -> bool:
    """Whether ``value`` is a number that has a finite size in seconds or beats."""
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _check_hook_function(
    function: object, *, arguments: int = 1
) -> Callable[..., object]:
    """
    Refuse something that cannot be called with a hook's arguments, and return what to call.

    A hook receives ``arguments`` values (the context, and for a component hook the component
    context). A function may take fewer of them, down to none: it then gets the leading ones it
    takes, through a wrapper that keeps its name and stays a generator function when it is one.
    """
    name = getattr(function, '__name__', None) or repr(function)
    if not callable(function):
        raise TypeError(
            f'hook() takes a function, such as hook(lambda context: ...) or a def with no '
            f'parameters, but got {function!r}. Pass the function itself, without calling it.'
        )
    if inspect.isasyncgenfunction(function):
        raise TypeError(
            f'{name} is an async generator, but a hook is a plain function, a generator '
            f'function or an async def function. Write it with async def and await what it '
            f'waits for, or write a generator with def and context = yield.'
        )
    try:
        signature = inspect.signature(function, follow_wrapped=False)
    except (TypeError, ValueError):
        return function
    for count in range(arguments, -1, -1):
        try:
            signature.bind(*([None] * count))
        except TypeError:
            continue
        break
    else:
        received = (
            'the context' if arguments == 1 else 'the context and the component context'
        )
        parameters = 'context' if arguments == 1 else 'context, component_context'
        written = (
            f'lambda {parameters}: ... or def my_hook({parameters})'
            if name.startswith('<')
            else f'def {name}({parameters})'
        )
        raise TypeError(
            f'{name} cannot take the arguments a hook receives, which are {received}. '
            f'Write it as {written}, or with no parameters at all.'
        ) from None
    if count == arguments:
        return function
    return _taking_leading_arguments(function, count)


def _taking_leading_arguments(
    function: Callable[..., object], count: int
) -> Callable[..., object]:
    """Wrap ``function`` so that it is called with only the first ``count`` arguments."""
    if inspect.iscoroutinefunction(function):

        @functools.wraps(function)
        async def coroutine_hook(*received: object) -> object:
            return await cast('Callable[..., Awaitable[object]]', function)(
                *received[:count]
            )

        return coroutine_hook

    if inspect.isgeneratorfunction(function):

        @functools.wraps(function)
        def generator_hook(*received: object) -> Generator[None, object, None]:
            yield from cast('Generator[None, object, None]', function(*received[:count]))

        return generator_hook

    @functools.wraps(function)
    def plain_hook(*received: object) -> object:
        return function(*received[:count])

    return plain_hook


_CONDITION_SCOPES: Final = frozenset(
    {'keyboard', 'mouse', 'scroll', 'buffer', 'parent', 'root', 'time', 'deps'}
)
"""The names a condition string reads; a custom event's name starts with none of them."""

_EVENT_NAME: Final = re.compile(r'[A-Za-z_][A-Za-z0-9_-]*(?:\.[A-Za-z0-9_-]+)*')

_INPUT_KINDS: Final[dict[str, str]] = {
    'keyboard': 'key',
    'mouse': 'mouse',
    'scroll': 'scroll',
}
"""The kind of hook that hears the one input a condition string reads."""


def _is_one_edit_away(text: str, word: str) -> bool:
    """Whether ``text`` is ``word`` with one letter added, dropped, changed or swapped."""
    if abs(len(text) - len(word)) > 1 or text == word:
        return False
    if len(text) == len(word):
        differences = [
            index for index, (a, b) in enumerate(zip(text, word, strict=True)) if a != b
        ]
        return len(differences) == 1 or (
            len(differences) == 2
            and differences[1] == differences[0] + 1
            and text[differences[0]] == word[differences[1]]
            and text[differences[1]] == word[differences[0]]
        )
    shorter, longer = sorted((text, word), key=len)
    return any(
        longer[:index] + longer[index + 1 :] == shorter for index in range(len(longer))
    )


def resolve_trigger(
    on: object,
    *,
    every: float | None,
    after: float | None,
    keys: object,
) -> tuple[HookKind | None, object]:
    """
    Read the ``on`` of a hook as the kind of event it hears and the condition it checks.

    Returns:
        The kind (``None`` for every input event) and the condition (``None`` for none), in
        the forms the hook machinery takes.

    Raises:
        TypeError: ``on`` is a ``bool`` or not a kind, a name or a condition.
        ValueError: ``on`` is a kind that no longer exists, or one letter away from a kind.
    """
    kinds = ', '.join(repr(kind) for kind in (*_EVENT_KINDS, *_TIMED) if kind)
    if on is None:
        return None, None
    if isinstance(on, bool):
        raise TypeError(
            f'on= received {on}. That is what `is` and `and` give on an expression. Build the '
            f'condition with ==, & and |, for example on=Keyboard.key == "q", or write it as a '
            f'string, on="keyboard.key == \'q\'".'
        )
    if isinstance(on, str):
        if on in _EVENT_KINDS or on in _TIMED:
            return cast('HookKind', on), None
        legacy = _LEGACY_ON.get(on)
        if legacy is not None:
            raise ValueError(
                f'on={on!r} is not a kind of hook. Use hook({legacy}) instead. The kinds '
                f'are {kinds}.'
            )
        if _EVENT_NAME.fullmatch(on) and on.split('.', 1)[0] not in _CONDITION_SCOPES:
            close = [
                kind
                for kind in (*_EVENT_KINDS, *_TIMED)
                if kind and '.' not in on and _is_one_edit_away(on, kind)
            ]
            if close:
                raise ValueError(
                    f'on={on!r} is not a kind of hook. Did you mean {close[0]!r}? To hear a '
                    f'custom event of that name, give it a name with a dot, such as '
                    f"Event.custom('app.{on}') heard with on='app.{on}'. The kinds are {kinds}."
                )
            return 'custom', _custom_event_named(on)
    elif not (isinstance(on, _core.Expression) or callable(on)):
        raise TypeError(
            f"on= takes a kind of hook such as on='key', the name of a custom event such as "
            f"on='volume_changed', or a condition (a string, an expression or a function of "
            f'the context), but got {on!r} of type {type(on).__name__}. To listen to several '
            f'kinds, register one hook for each.'
        )
    # A condition: the kind follows what it is checked on, or the one input it reads.
    if keys is not None:
        return 'key', on
    if every is not None or after is not None:
        return 'tick', on
    if isinstance(on, str):
        inputs = compile_when(on).reads & set(_INPUT_KINDS)
        if len(inputs) == 1:
            return cast('HookKind', _INPUT_KINDS[next(iter(inputs))]), on
        if not inputs:
            return 'tick', on
    return None, on


def _custom_event_named(name: str) -> Callable[[Context[object, object]], bool]:
    """The condition that holds for a custom event of one name."""

    def is_named(context: Context[object, object]) -> bool:
        event = context.event
        return getattr(event, 'custom_name', None) == name

    is_named.__name__ = f'is_custom_event_{name}'
    return is_named


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
    if on is not None and not isinstance(on, str):
        raise TypeError(
            f"on= takes one kind of hook as text, such as on='key', but got {on!r}. To listen "
            f'to several kinds, register one hook for each. The kinds are {kinds}.'
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
            or not _is_finite(value)
            or (value <= 0 if name == 'every' else value < 0)
        ):
            minimum = 'above 0' if name == 'every' else '0 or more'
            raise ValueError(
                f'{name}= must be a finite number {minimum}, but was {value!r}. In seconds '
                f"for on='tick' and in beats for on='beat'."
            )
    if keys is not None and on != 'key':
        raise ValueError(
            f"keys= is for on='key', but this hook has on={on!r}. Write "
            f"hook(on='key', keys={keys!r}) to react to those keys."
        )
    if on == 'resize' and hasattr(owner, '_parent_owner'):
        raise ValueError(
            'resize events are reported to the canvas; register this hook on the canvas '
            "with canvas.hook(on='resize') and read context.canvas.screen.size for the window, or "
            'context.region for the cells inside its border and padding.'
        )
    if keys is None:
        return ()
    if not isinstance(keys, (str, list, tuple, set, frozenset)):
        raise TypeError(
            f"keys= takes a key name such as 'q' or a list of them such as ['q', 'escape'], "
            f'but got {keys!r}.'
        )
    names = (keys,) if isinstance(keys, str) else tuple(cast('Sequence[str]', keys))
    for name in names:
        if not isinstance(name, str):
            raise TypeError(
                f"keys= takes key names such as 'q' or 'ctrl+s', but one of them is "
                f'{name!r}. Write each key as text, for example keys=["q", "escape"].'
            )
    return tuple(normalize_binding(name) for name in names)


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
        if_running: IfRunning = 'replace',
    ) -> None:
        """
        Attach a function to a canvas or placement. Use ``hook`` instead of calling this.

        Args:
            owner: The canvas or placement the hook listens on.
            function: The function to call with a [`Context`][xnano.hooks.Context].
            on: When the hook runs.
            when: The compiled condition.
            every: Seconds (``'tick'``) or beats (``'beat'``) between runs.
            after: Seconds or beats before the one run.
            keys: The normalized keys of an ``on='key'`` hook.
            if_running: What an ``async def`` hook does when it is called again while its
                previous run has not finished.
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
        # The runs of an async def hook, which happen on an event loop.
        self._coroutine_runs: CoroutineRuns | None = (
            CoroutineRuns(if_running) if inspect.iscoroutinefunction(function) else None
        )
        self._generator: Generator[None, Context[DepsT, StateT], None] | None = None
        self._core_hook: _core.Hook | None = None
        self._registration: _Registration | None = None
        self._stop_frames: Callable[[], None] | None = None
        # A hook without on= also runs on every frame while a mouse button it heard is held,
        # once the button has been held for a short delay after its press.
        self._stop_held_button_frames: Callable[[], None] | None = None
        self._has_heard_input_since_frame = False
        self._held_button_pressed_at_seconds = 0.0
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
        coroutine_runs = self._coroutine_runs
        if coroutine_runs is not None:
            coroutine_runs.cancel()
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
        self._stop_following_held_button()
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
        """The terminal settings a screen needs for this hook to hear its events."""
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
                gate
                for gate in ('keyboard', 'mouse', 'scroll')
                if gate in self._when.reads
            )
        if self._when.mentions_release:
            needed.add('keyboard_release')
        return frozenset(needed)

    # -- timers --------------------------------------------------------------------------

    def _beat_seconds(self) -> float:
        beats = self._after if self._after is not None else self._every
        return (
            (1.0 if beats is None else beats) * 60.0 / self._owner._canvas._clock_view.bpm
        )

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
            context = self._context(core_context, event)
            is_predicate_checked = False
            if kind in ('mouse', 'scroll', 'drag'):
                should_run, is_predicate_checked = self._handle_pointer(
                    core_context, event, context
                )
                if not should_run:
                    return
            self._run(context, is_predicate_checked=is_predicate_checked)
            if kind is None:
                self._follow_held_button(event)
        except Exception as error:
            self._fail(event, error)

    def _follow_held_button(
        self, event: _core.Event | _core.TerminalStateChange | None
    ) -> None:
        """
        After a pointer event, run this hook on every frame while a mouse button is held.

        The frames during a short delay after a press stay quiet, so a quick click runs the
        hook only for the press and the release.
        """
        self._has_heard_input_since_frame = True
        if self._removed:
            return
        mouse = event.mouse if isinstance(event, _core.Event) else None
        if mouse is None or mouse.kind == 'scroll':
            return
        is_following = self._stop_held_button_frames is not None
        if is_following and mouse.kind != 'press':
            return
        canvas = self._owner._canvas
        self._held_button_pressed_at_seconds = canvas._time_source.elapsed_seconds
        if is_following:
            return
        state = canvas._input_state
        if state is None or not state.is_mouse_down:
            return
        self._stop_held_button_frames = canvas._on_frame(self._on_held_button_frame)

    def _on_held_button_frame(self, frame: Frame) -> None:
        """Run once on a frame that brought this hook no input, while a button is held."""
        if self._removed:
            return
        state = self._owner._canvas._input_state
        if state is None or not state.is_mouse_down:
            self._stop_following_held_button()
            return
        if self._has_heard_input_since_frame:
            # The input this hook heard during the frame was its run for the frame.
            self._has_heard_input_since_frame = False
            return
        held_seconds = frame.elapsed_seconds - self._held_button_pressed_at_seconds
        if held_seconds < _HELD_BUTTON_REPEAT_DELAY_SECONDS:
            return
        try:
            if self._passes_expression():
                self._run(self._context(None, frame))
        except Exception as error:
            self._fail(frame, error)

    def _stop_following_held_button(self) -> None:
        """Stop the runs on every frame that a held mouse button started."""
        stop = self._stop_held_button_frames
        self._stop_held_button_frames = None
        self._has_heard_input_since_frame = False
        if stop is not None:
            stop()

    def _handle_pointer(
        self,
        core_context: CoreContext,
        event: _core.Event | _core.TerminalStateChange | None,
        context: Context[DepsT, StateT],
    ) -> tuple[bool, bool]:
        """
        Scope a pointer event to the region and capture the pointer.

        Return whether to run the hook, and whether its Python condition was already
        checked here (a press is only captured when the condition holds).
        """
        mouse = event.mouse if isinstance(event, _core.Event) else None
        if mouse is None:
            return False, False
        kind = self.on
        if not self._is_captured and not core_context.bounds.contains(mouse.position):
            return False, False
        mouse_kind = mouse.kind
        if mouse_kind == 'press' and kind in ('mouse', 'drag'):
            predicate = self._when.predicate
            is_checked = not self._is_captured and predicate is not None
            if is_checked and predicate is not None and not predicate(context):
                return False, True
            capture = getattr(core_context, 'capture_pointer', None)
            if capture is not None:
                capture()
            self._is_captured = True
            return kind == 'mouse', is_checked
        if mouse_kind == 'release' and kind in ('mouse', 'drag'):
            self._is_captured = False
            # Only a running generator hears the release that ends its drag.
            return kind == 'mouse' or self._generator is not None, False
        return True, False

    def _run(
        self, context: Context[DepsT, StateT], *, is_predicate_checked: bool = False
    ) -> None:
        canvas = self._owner._canvas
        if canvas._stop_requested.is_set():
            # The loop was asked to end, so an event or timer that was already queued is dropped.
            return
        run = self._state_run
        if run.is_active:
            run = _HookRun(track=run.track)
        previous = canvas._active_run
        run.begin()
        run.handle = cast('HookHandle[object, object]', self)
        canvas._active_run = run
        canvas._runs_in_progress += 1
        try:
            predicate = self._when.predicate
            if predicate is None or is_predicate_checked or predicate(context):
                coroutine_runs = self._coroutine_runs
                if coroutine_runs is not None:
                    coroutine_runs.start(
                        cast('HookHandle[object, object]', self),
                        cast('Context[object, object]', context),
                    )
                elif self._is_generator_function:
                    self._advance(context)
                else:
                    result = self.function(context)
                    if result is not None:
                        self._apply_result(result)
        except BaseException:
            run.discard()
            raise
        finally:
            canvas._runs_in_progress -= 1
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
        self, change: _core.TerminalStateChange, others: list[_StateFollower]
    ) -> None:
        """Report that this hook keeps being run again by hooks that change what it reads."""
        names = [_hook_name(self.function)]
        names.extend(
            _hook_name(other.function)
            for other in others
            if isinstance(other, HookHandle)
        )
        path = _dotted(change.paths[0]) if change.paths else ''
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
        if isinstance(result, (ContextualOperation, DynamicOperation)):
            result.apply_to(owner)  # type: ignore[arg-type]
            return
        if isinstance(result, (_core.Operation, _core.Style)):
            owner.update(result)  # type: ignore[attr-defined]
            return
        if isinstance(result, (str, _core.Buffer)) or hasattr(result, '__xnano_write__'):
            name = getattr(self.function, '__name__', 'hook')
            raise TerminalError(
                f'The hook {name} returned content to draw, but a hook cannot return '
                f'content. Use @xnano.writable for content that changes, or write it '
                f'with canvas.screen.write(...).'
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
        [`Placement`][xnano.layout.Placement].
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
        on: HookTrigger[DepsT, StateT] | None = None,
        every: float | None = None,
        after: float | None = None,
        keys: KeyName | Sequence[KeyName] | None = None,
        requires_deps: bool = False,
        if_running: IfRunning = 'replace',
    ) -> HookHandle[DepsT, StateT]: ...
    @overload
    def hook(
        self,
        /,
        *,
        on: HookTrigger[DepsT, StateT] | None = None,
        every: float | None = None,
        after: float | None = None,
        keys: KeyName | Sequence[KeyName] | None = None,
        requires_deps: bool = False,
        if_running: IfRunning = 'replace',
    ) -> Callable[[Hook[DepsT, StateT]], HookHandle[DepsT, StateT]]: ...
    def hook(
        self,
        function: Hook[DepsT, StateT] | None = None,
        /,
        *,
        on: HookTrigger[DepsT, StateT] | None = None,
        every: float | None = None,
        after: float | None = None,
        keys: KeyName | Sequence[KeyName] | None = None,
        requires_deps: bool = False,
        if_running: IfRunning = 'replace',
    ) -> (
        HookHandle[DepsT, StateT]
        | Callable[[Hook[DepsT, StateT]], HookHandle[DepsT, StateT]]
    ):
        """
        Call a function when something happens on this canvas or placement.

        ``on`` says when the hook runs: a kind of event such as ``'key'`` or ``'tick'``, the
        name of an event pushed with ``Event.custom(name)``, or a condition such as
        ``"mouse.kind == 'press'"`` (see [`HookTrigger`][xnano.hooks.HookTrigger]). A hook
        without ``on`` hears every input event. A mouse,
        scroll or drag hook on a placement hears only the pointer inside the placement, and a
        press inside holds the pointer for the hook until the button is released. A pointer hook
        that matches an event stops it from reaching the parent; a hook that does not match lets
        it through. Keys are not consumed: while nothing has focus, every key hook hears a key.

        A hook hears only the input the screen reports. A hook added to a canvas that is
        already on the screen turns no terminal setting on, so one that needs input the screen
        does not report, such as ``on='mouse'`` on a canvas opened without ``mouse=True``, is
        attached and never runs.

        ``hook(function, ...)`` attaches one function, and ``@target.hook(...)`` decorates the
        function that follows. A hook function may be a generator that receives a new context
        at each bare ``yield``: write ``context = yield``. A drag is a loop that runs while
        ``context.mouse.is_down``.

        A hook without ``on`` hears every input event. While a mouse button it heard is held,
        it also runs on every frame once the button has been held for 0.15 seconds, so a
        quick click runs it only for the press and the release. A release names its button
        in ``context.mouse.button``; test ``context.mouse.is_down`` to leave the release out.

        A hook function may also be written with ``async def``. Each time the hook runs, its
        coroutine starts on the event loop the canvas was created or opened in, and on
        xnano's own background loop when there is none, and the canvas goes on drawing while
        it awaits. ``if_running`` says what happens when the hook runs again before the
        previous run has finished. A canvas with a manual clock (from ``new()``) needs an event
        loop of its own for that: create it in a coroutine or use ``async with`` on it.
        [`wait_for_tasks_async`][xnano.canvas.Canvas.wait_for_tasks_async] waits until every
        run has finished. A run that raises ends the canvas like a plain hook that raises; a
        cancelled run is not a failure.

        ``every`` and ``after`` are seconds for ``on='tick'`` and beats for ``on='beat'``:
        ``every=2`` means 2 seconds for a tick hook and 2 beats for a beat hook. On a canvas
        from ``new()`` a hook that is due several times in one ``step`` runs once for each
        interval, up to 100,000 times in one step; the intervals that remain run in the steps
        that follow. The function's return value is ignored, unless it is an operation, a
        style or an effect, which is applied to this target.

        Args:
            function: The function to call with a [`Context`][xnano.hooks.Context], or a
                function with no parameters, which is called without it.
            on: When the hook runs. A kind: ``'frame'``, ``'tick'``, ``'beat'``, ``'key'``,
                ``'mouse'``, ``'scroll'``, ``'drag'``, ``'paste'``, ``'focus'``, ``'resize'``,
                ``'state'`` or ``'custom'`` (every custom event); see
                [`HookKind`][xnano.hooks.HookKind]. The name of a custom event, such as
                ``'volume_changed'``. Or a condition: a string, an expression or a function of
                the context; see [`When`][xnano.hooks.When]. A string that reads one input
                hears only that input (``"mouse.kind == 'press'"`` is a mouse hook, and hears
                the pointer inside a placement), a string that reads no input is checked on
                every tick, and a string tells xnano which terminal settings the hook needs,
                so ``mouse`` and ``scroll`` turn on when the canvas opens. A string that reads
                key releases needs ``keyboard='release_events'`` given to ``new()`` or
                ``open()``. An expression or a function hears every input event and does not
                tell xnano what it reads, so one that reads ``Mouse``, ``Scroll`` or key
                releases needs ``mouse=True``, ``scroll=True`` or
                ``keyboard='release_events'`` given to ``new()`` or ``open()`` yourself. With
                ``every``, ``after`` or ``keys`` a condition is checked on those ticks or keys.
                A comparison with an input the event does not carry, such as ``keyboard.key``
                on a paste, does not hold; ``!=`` is one of them, so ``keyboard.key != 'q'``
                hears only key events. ``not`` and ``not in`` negate the whole comparison, so
                ``not keyboard.key == 'q'`` and ``keyboard.key not in ['q']`` also hold for
                events that have no key.
            every: Repeat every this many seconds (``'tick'``) or beats (``'beat'``).
            after: Run once after this many seconds (``'tick'``) or beats (``'beat'``).
            keys: The key or keys an ``on='key'`` hook reacts to, such as ``'q'`` or
                ``'ctrl+s'``. A key hook with keys hears presses and repeats; omit them and
                test ``keyboard.kind`` to hear releases.
            requires_deps: Whether the hook needs the dependencies given to
                ``new(deps=...)``.
            if_running: For an ``async def`` hook, what happens when it runs again while
                its previous run has not finished: ``'replace'`` cancels that run (the
                latest wins), ``'ignore'`` drops the new one, ``'queue'`` runs them one after
                the other and ``'overlap'`` runs them together. See
                [`IfRunning`][xnano.hooks.IfRunning].

        Returns:
            The hook, whose ``remove`` stops it; removing it cancels the unfinished runs of
            an ``async def`` hook. Without a function, the decorator.

        Raises:
            ValueError: The combination of arguments does not make sense, a key name is
                unknown, a condition string is not a condition, ``on`` is one letter away
                from a kind, or ``if_running`` is given to a function that is not
                ``async def``. The message says what to write instead.
            TypeError: ``on`` is a plain ``bool`` or not a kind, a name or a condition, or the
                function is not callable with a context, or is an async generator.
            TerminalError: ``requires_deps`` is true and the canvas was created without
                ``deps``, or an ``async def`` hook has no event loop to run on.

        Examples:
            ```python
            import xnano
            from xnano_core import Event

            with xnano.new(width=8, height=1) as canvas:
                heard = []

                @canvas.hook(on='key', keys=['q', 'escape'])
                def leave(context: xnano.Context) -> None:
                    heard.append(context.keyboard.key)

                @canvas.hook(on='tick', every=0.5)
                def blink(context: xnano.Context) -> None:
                    heard.append('tick')

                canvas.push(Event.key_press('q'))
                canvas.clock.step(delta_seconds=1.0)
                assert heard == ['q', 'tick', 'tick']
            ```
        """
        canvas = self._canvas
        self._require_attached()
        owner = cast('_Hooked[object, object]', self)
        kind, condition = resolve_trigger(on, every=every, after=after, keys=keys)
        normalized_keys = _check_hook_arguments(owner, kind, every, after, keys)
        compiled = compile_when(condition)
        if requires_deps and not canvas._deps_given:
            raise TerminalError(
                'This hook needs dependencies (requires_deps=True), but the canvas has none '
                'yet. Give them when you create the canvas: xnano.new(deps=your_dependencies) '
                'or xnano.open(deps=your_dependencies), or open the canvas with '
                'canvas.open(deps=your_dependencies) before you register this hook.'
            )

        _check_if_running(if_running)

        def attach(
            callback: Hook[DepsT, StateT],
        ) -> HookHandle[DepsT, StateT]:
            checked = _check_hook_function(callback)
            _check_coroutine_hook(owner, checked, kind, if_running)
            return self._attach_hook(
                cast('Callable[[Context[DepsT, StateT]], object]', checked),
                on=kind,
                when=compiled,
                every=every,
                after=after,
                keys=normalized_keys,
                if_running=if_running,
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
        if_running: IfRunning = 'replace',
    ) -> HookHandle[DepsT, StateT]:
        self._require_attached()
        handle: HookHandle[DepsT, StateT] = HookHandle(
            self,
            function,
            on=on,
            when=when,
            every=every,
            after=after,
            keys=keys,
            if_running=if_running,
        )
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
        if isinstance(event, _core.Event):
            handling = f' while handling {event!r}'
        elif isinstance(event, Update):
            handling = ' while running its timer'
        elif isinstance(event, Frame):
            handling = ' while drawing a frame'
        elif event is None:
            handling = ''
        else:
            handling = ' while following the state'
        failure = TerminalError(
            f'The hook {name} failed{handling}: {type(error).__name__}: '
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


_IF_RUNNING: Final = ('replace', 'ignore', 'queue', 'overlap')


def _check_if_running(if_running: object) -> None:
    """Refuse an ``if_running`` that is not one of its words."""
    if if_running not in _IF_RUNNING:
        close = difflib.get_close_matches(str(if_running), _IF_RUNNING, n=1)
        hint = f' Did you mean {close[0]!r}?' if close else ''
        raise ValueError(
            f'if_running must be one of {", ".join(repr(word) for word in _IF_RUNNING)}, '
            f'but was {if_running!r}.{hint}'
        )


def _check_if_running_fits(
    function: Callable[..., object], if_running: IfRunning
) -> None:
    """Refuse an ``if_running`` other than the default for a function that is not async."""
    if if_running != 'replace' and not inspect.iscoroutinefunction(function):
        name = _hook_name(function)
        raise ValueError(
            f'if_running={if_running!r} says what an async def hook does while its '
            f'previous run has not finished, but {name} is a plain function, which always '
            f'finishes before it runs again. Remove if_running, or write {name} with '
            f'async def.'
        )


def _check_coroutine_hook(
    owner: _Hooked[object, object],
    function: Callable[..., object],
    kind: HookKind | None,
    if_running: IfRunning,
) -> None:
    """Refuse an ``async def`` hook that could not run, and ``if_running`` on a plain one."""
    name = _hook_name(function)
    if not inspect.iscoroutinefunction(function):
        _check_if_running_fits(function, if_running)
        return
    if kind == 'state':
        raise ValueError(
            f"{name} is an async def hook, which cannot follow state with on='state': the "
            f'state it reads after an await is not known when the hook is registered. '
            f'Follow the state with a plain function and start the async work from it, or '
            f'read the state in an async def hook that runs on another kind of event.'
        )
    root = owner._canvas._canvas
    if not root._host.is_autonomous and root._event_loop is None:
        raise TerminalError(
            f'{name} is an async def hook, but this canvas has a manual clock and no event '
            f'loop to run it on, because it was created outside a coroutine. Create the '
            f'canvas inside a coroutine (such as async def main() run with '
            f'asyncio.run(main())), enter it with async with, or create it with '
            f'realtime=True, whose async def hooks run on a background event loop.',
            code='canvas.loop',
        )


def _event_of(core_context: CoreContext) -> _core.Event | None:
    event: _core.Event | None = getattr(core_context, 'event', None)
    return event
