"""
xnano.components

Components: functions and objects that draw or play themselves, and run again only when
something they read changes.
"""

from __future__ import annotations

import dataclasses
import functools
import inspect
import os
import sys
import threading
import warnings
from collections import deque
from collections.abc import Callable, Generator, Mapping, Sequence
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Concatenate,
    Generic,
    cast,
    final,
    overload,
)

import xnano_core as _core
from xnano._internal._content import check_context_method
from xnano._schema._content import Content as Content
from xnano._schema._content import Playable as Playable
from xnano._schema._content import PlaySource as PlaySource
from xnano._schema._content import SupportsPlay as SupportsPlay
from xnano._schema._content import SupportsRender as SupportsRender
from xnano._schema._content import SupportsWrite as SupportsWrite
from xnano._schema._content import Writable as Writable
from xnano._schema._generics import DepsT, ParametersT, StateT
from xnano.audio._notes import Note, PlayHandle
from xnano.errors import TerminalError
from xnano.hooks._context import Context, ReadLog
from xnano.state import StatePath, _HookRun

if TYPE_CHECKING:
    from xnano._schema._hooks import HookTrigger, KeyName
    from xnano._schema._media import PlayOptions
    from xnano.canvas import Canvas
    from xnano.devices._screen import Screen
    from xnano.effects._controller import EffectState
    from xnano.hooks._context import Frame
    from xnano.hooks._handles import HookHandle, _Hooked
    from xnano.layout._placement import Placement
    from xnano.layout._region import Region
    from xnano.state import StateNamespace, _StateFollower

__all__ = [
    'ComponentContext',
    'ComponentHook',
    'Content',
    'PlaySource',
    'Playable',
    'PlayableComponent',
    'PlayableFunction',
    'RenderableComponent',
    'RenderableFunction',
    'SupportsPlay',
    'SupportsRender',
    'SupportsWrite',
    'Writable',
    'WritableComponent',
    'WritableFunction',
    'playable',
    'renderable',
    'writable',
]

_INPUT_EVENTS = {'key': 'key', 'mouse': 'mouse', 'scroll': 'scroll', 'paste': 'paste'}
_EXAMPLE_NAMES = {'writable': 'gauge', 'renderable': 'meter', 'playable': 'chime'}
_PROTOCOL_METHODS = {
    'writable': '__xnano_write__',
    'renderable': '__xnano_render__',
    'playable': '__xnano_play__',
}
_warned_classes: set[type] = set()
_warned_lock = threading.Lock()


# -- component hooks ----------------------------------------------------------------------


@final
@dataclasses.dataclass(frozen=True, slots=True)
class ComponentContext(Generic[DepsT, StateT]):
    """
    What a component's hook receives besides the hook's own context.

    Attributes:
        component: The component the hook belongs to.
        placement: The placement the component is drawn in, or ``None`` for a playable
            component, which has no placement.
        arguments: The component's own parameters, by name.

    Examples:
        ```python
        import xnano

        @xnano.writable
        def gauge(context: xnano.Context, ratio: float = 0.0) -> str:
            return '#' * round(ratio * 10)

        with xnano.new(width=12, height=1) as canvas:
            seen = []
            gauge.hook(
                lambda context, component_context: seen.append(
                    component_context.arguments['ratio']
                ),
                on='tick',
            )
            canvas.screen.write(gauge(ratio=0.5))
            canvas.clock.step(delta_seconds=0.1)
            assert seen == [0.5]
        ```
    """

    component: WritableComponent[DepsT, StateT] | PlayableComponent[DepsT, StateT]
    """The component the hook belongs to."""
    placement: Placement[DepsT, StateT] | None
    """The placement the component is drawn in, or ``None`` for a playable component."""
    arguments: Mapping[str, object]
    """The component's own parameters, by name."""


@dataclasses.dataclass(frozen=True, slots=True)
class _HookSettings:
    """The keywords of ``hook`` that a component hook passes on to each placement."""

    on: HookTrigger[object, object] | None
    every: float | None
    after: float | None
    keys: KeyName | Sequence[KeyName] | None
    requires_deps: bool


@final
class ComponentHook:
    """
    What ``component.hook(...)`` returns: a hook on every placement of a component.

    The hook is installed on the placements that exist now and on those created later;
    ``remove`` takes it off all of them. It never starts a placement of its own.

    Attributes:
        handles: The [`HookHandle`][xnano.hooks.HookHandle] on each placement it is installed
            on right now.
        is_removed: Whether ``remove`` was called.
    """

    __slots__ = ('_function', '_handles', '_is_removed', '_owner', '_settings')

    def __init__(
        self,
        owner: _HookSource,
        function: Callable[..., object],
        settings: _HookSettings,
    ) -> None:
        """
        Create the hook. Use ``component.hook(...)`` instead of calling this.

        Args:
            owner: The component or component function the hook was added to.
            function: The function to call with a context and a component context.
            settings: The keywords of ``hook``.
        """
        self._owner = owner
        self._function = function
        self._settings = settings
        self._handles: list[tuple[object, HookHandle[object, object]]] = []
        self._is_removed = False

    @property
    def handles(self) -> tuple[HookHandle[object, object], ...]:
        """The hook on each placement it is installed on right now."""
        return tuple(handle for _, handle in self._handles if not handle.is_removed)

    @property
    def is_removed(self) -> bool:
        """Whether ``remove`` was called."""
        return self._is_removed

    def remove(self) -> None:
        """Take the hook off every placement. Removing twice does nothing."""
        if self._is_removed:
            return
        self._is_removed = True
        if self in self._owner._hooks:
            self._owner._hooks.remove(self)
        handles, self._handles = self._handles, []
        for _, handle in handles:
            handle.remove()

    def _release(self, target: object) -> None:
        """Take the hook off one placement (or the canvas) it was installed on."""
        kept = []
        for installed_on, handle in self._handles:
            if installed_on is target:
                handle.remove()
            else:
                kept.append((installed_on, handle))
        self._handles = kept

    def _install(
        self,
        target: Placement[object, object] | Canvas[object, object],
        component: WritableComponent[object, object]
        | PlayableComponent[object, object]
        | WritableFunction[..., object, object]
        | PlayableFunction[..., object, object],
        *,
        timeline: Callable[[], Region[float]] | None = None,
    ) -> None:
        """
        Install the hook on a placement (or on the canvas for a playable).

        ``timeline`` returns the region on the timeline of what a playable is playing; the
        hook's contexts report it as ``context.region``.
        """
        if self._is_removed:
            return
        placement = target if hasattr(target, 'refresh') else None
        context = ComponentContext(
            cast('WritableComponent[object, object]', component),
            cast('Placement[object, object] | None', placement),
            component.arguments,
        )
        function = self._function
        if inspect.isgeneratorfunction(function):

            @functools.wraps(function)
            def generator_hook(
                hook_context: Context[object, object],
            ) -> Generator[None, Context[object, object], None]:
                running = cast(
                    'Generator[None, Context[object, object], None]',
                    function(hook_context, context),
                )
                if timeline is None:
                    yield from running
                    return
                hook_context._timeline = timeline
                yield from _resumed_on_timeline(running, timeline)

            wrapped: Callable[..., object] = generator_hook
        else:

            @functools.wraps(function)
            def plain_hook(hook_context: Context[object, object]) -> object:
                if timeline is not None:
                    hook_context._timeline = timeline
                return function(hook_context, context)

            wrapped = plain_hook
        settings = self._settings
        handle = target.hook(
            wrapped,
            on=settings.on,
            every=settings.every,
            after=settings.after,
            keys=settings.keys,
            requires_deps=settings.requires_deps,
        )
        self._handles.append((target, cast('HookHandle[object, object]', handle)))

    def __repr__(self) -> str:
        state = 'removed' if self._is_removed else f'{len(self.handles)} installed'
        return f'ComponentHook({state})'


def _resumed_on_timeline(
    running: Generator[None, Context[object, object], None],
    timeline: Callable[[], Region[float]],
) -> Generator[None, Context[object, object], None]:
    """
    Run a generator hook, giving each context that resumes it the ``timeline`` of a playable.

    A generator hook is resumed with a new context at each event, and only the first one
    passes through the hook that installed it.
    """
    try:
        yielded = next(running)
        while True:
            resumed = yield yielded
            resumed._timeline = timeline
            yielded = running.send(resumed)
    except StopIteration:
        return
    finally:
        running.close()


class _PlacementLike:
    """Stands in for a placement while the arguments of a component hook are checked."""

    _parent_owner = None


class _HookSource:
    """The hooks of a component, and the places they are installed."""

    def __init__(self) -> None:
        """Start with no hooks and no placements."""
        self._hooks: list[ComponentHook] = []
        self._targets: list[
            tuple[object, object, Callable[[], Region[float]] | None]
        ] = []

    def _owners(self) -> tuple[_HookSource, ...]:
        """Where hooks for this component are kept: itself, and its function if it has one."""
        return (self,)

    @overload
    def hook(
        self,
        function: Callable[..., object],
        /,
        *,
        on: HookTrigger[object, object] | None = None,
        every: float | None = None,
        after: float | None = None,
        keys: KeyName | Sequence[KeyName] | None = None,
        requires_deps: bool = False,
    ) -> ComponentHook: ...
    @overload
    def hook(
        self,
        /,
        *,
        on: HookTrigger[object, object] | None = None,
        every: float | None = None,
        after: float | None = None,
        keys: KeyName | Sequence[KeyName] | None = None,
        requires_deps: bool = False,
    ) -> Callable[[Callable[..., object]], ComponentHook]: ...
    def hook(
        self,
        function: Callable[..., object] | None = None,
        /,
        *,
        on: HookTrigger[object, object] | None = None,
        every: float | None = None,
        after: float | None = None,
        keys: KeyName | Sequence[KeyName] | None = None,
        requires_deps: bool = False,
    ) -> ComponentHook | Callable[[Callable[..., object]], ComponentHook]:
        """
        Call a function when something happens to a placement of this component.

        The function receives the hook's [`Context`][xnano.hooks.Context] and a
        [`ComponentContext`][xnano.components.ComponentContext]. The arguments are those of
        ``hook`` on a placement, and a mouse, scroll or drag hook hears only the pointer
        inside the placement. Keys are not consumed: while nothing has focus, every key hook
        hears a key. On a component function the hook is installed on every
        placement of that function, those that exist now and those created later; on a
        component made by calling it, only on its placements. A playable component has no
        placement: its hook is installed on the canvas when the component is played.

        Args:
            function: The function to call, or ``None`` to use this as a decorator.
            on: When the hook runs: a kind of event, the name of a custom event, or a
                condition; see [`HookTrigger`][xnano.hooks.HookTrigger].
            every: Repeat every this many seconds (``'tick'``) or beats (``'beat'``).
            after: Run once after this many seconds or beats.
            keys: The key or keys an ``on='key'`` hook reacts to.
            requires_deps: Whether the hook needs the dependencies given to
                ``new(deps=...)``. Checked each time the hook is installed.

        Returns:
            A [`ComponentHook`][xnano.components.ComponentHook], whose ``remove`` takes the
            hook off every placement; or, without a function, the decorator.

        Raises:
            ValueError: The combination of arguments does not make sense; see
                [`hook`][xnano.canvas.Canvas.hook].
            TerminalError: ``requires_deps`` is true and the canvas was created without
                ``deps``.

        Examples:
            ```python
            import xnano
            from xnano_core import Event

            @xnano.writable
            def label(context: xnano.Context, text: str = 'x') -> str:
                return text

            with xnano.new(width=10, height=1) as canvas:
                pressed = []

                @label.hook(on='key', keys='a')
                def heard(
                    context: xnano.Context,
                    component_context: xnano.components.ComponentContext,
                ) -> None:
                    pressed.append(component_context.arguments['text'])

                canvas.screen.write(label(text='hi'))
                canvas.push(Event.key_press('a'))
                canvas.deliver_events()
                assert pressed == ['hi']
            ```
        """
        from xnano.hooks._handles import (
            _check_hook_arguments,
            _check_hook_function,
            resolve_trigger,
        )
        from xnano.hooks._triggers import compile_when

        kind, condition = resolve_trigger(on, every=every, after=after, keys=keys)
        _check_hook_arguments(
            cast('_Hooked[object, object]', _PlacementLike()), kind, every, after, keys
        )
        compile_when(condition)
        settings = _HookSettings(on, every, after, keys, requires_deps)

        def attach(callback: Callable[..., object]) -> ComponentHook:
            component_hook = ComponentHook(
                self, _check_hook_function(callback, arguments=2), settings
            )
            self._hooks.append(component_hook)
            try:
                self._install_everywhere(component_hook)
            except BaseException:
                component_hook.remove()
                raise
            return component_hook

        if function is None:
            return attach
        return attach(function)

    def _install_everywhere(self, component_hook: ComponentHook) -> None:
        """Install a new hook on every placement the component has now."""
        for target, component, timeline in list(self._targets):
            component_hook._install(
                cast('Placement[object, object]', target),
                cast('WritableComponent[object, object]', component),
                timeline=timeline,
            )

    def _placed(
        self,
        target: object,
        component: object,
        *,
        timeline: Callable[[], Region[float]] | None = None,
    ) -> None:
        """
        Install every hook of this component, and of its function, on a new target.

        ``timeline`` is given for a playable: it returns the region on the timeline of what
        the playable is playing.
        """
        for owner in self._owners():
            for component_hook in list(owner._hooks):
                component_hook._install(
                    cast('Placement[object, object]', target),
                    cast('WritableComponent[object, object]', component),
                    timeline=timeline,
                )
            owner._targets.append((target, component, timeline))

    def _released(self, target: object) -> None:
        for owner in self._owners():
            owner._targets[:] = [
                entry for entry in owner._targets if entry[0] is not target
            ]
            for component_hook in owner._hooks:
                component_hook._release(target)


# -- decorated functions and the components they make --------------------------------------


def _own_signature(
    function: Callable[..., object], decorator: str
) -> tuple[inspect.Signature, bool]:
    """
    The parameters a component is written with, and whether its function takes the context.

    The first positional parameter is the context. A function with no parameters at all takes
    nothing, so it is called without the context.
    """
    if inspect.isclass(function) or not callable(function):
        raise TypeError(
            f'@xnano.{decorator} decorates a function, such as @xnano.{decorator} '
            f'def {_EXAMPLE_NAMES[decorator]}(context): ..., but got {function!r}. A class '
            f'is a component when it has a method {_PROTOCOL_METHODS[decorator]}'
            f'(self, context).'
        )
    signature = inspect.signature(function)
    parameters = list(signature.parameters.values())
    if not parameters:
        if decorator == 'renderable':
            name = getattr(function, '__name__', 'the function')
            raise TypeError(
                f'@xnano.renderable needs a function that takes the context, because it '
                f'draws on context.screen and plays on context.speaker, but {name} takes no '
                f'parameters. Write def {name}(context: xnano.Context) -> None:, or use '
                f'@xnano.writable for a function that returns content to write.'
            )
        return signature, False
    if parameters[0].kind not in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    ):
        name = getattr(function, '__name__', 'the function')
        raise TypeError(
            f'@xnano.{decorator} needs a function whose first parameter is the context, '
            f'or one with no parameters, but {name} starts with {parameters[0]}. Write '
            f'def {name}(context: xnano.Context, ...): and give the rest of the parameters '
            f'when you write it: canvas.screen.write({name}(...)).'
        )
    return signature.replace(parameters=parameters[1:]), True


class _ComponentFunction(_HookSource, Generic[ParametersT, DepsT, StateT]):
    """A function turned into a component: what ``@writable``, ``@renderable`` and ``@playable`` return."""

    _decorator = 'writable'
    _component_class: type

    def __init__(
        self,
        function: Callable[Concatenate[Context[DepsT, StateT], ParametersT], object],
    ) -> None:
        """Keep the function. Use ``@xnano.writable``, ``@xnano.renderable`` or ``@xnano.playable``."""
        super().__init__()
        self._function = function
        self._signature, self._takes_context = _own_signature(function, self._decorator)
        functools.update_wrapper(self, function)  # pyright: ignore[reportArgumentType]

    @property
    def arguments(self) -> Mapping[str, object]:
        """The parameters the component is written with: none, so the defaults apply."""
        return MappingProxyType({})

    def _bind(self, *arguments: object, **keywords: object) -> _BoundComponent:
        name = getattr(self._function, '__name__', 'the component')
        try:
            bound = self._signature.bind(*arguments, **keywords)
        except TypeError as error:
            raise TypeError(
                f'{name}{self._signature} cannot be called with those arguments: {error}. '
                f'The context is passed for you; give only its own parameters.'
            ) from None
        bound.apply_defaults()
        return self._component_class(self, bound)

    def _call_with_defaults(self, context: Context[object, object]) -> object:
        name = getattr(self._function, '__name__', 'the component')
        try:
            self._signature.bind()
        except TypeError:
            raise TypeError(
                f'{name}{self._signature} needs arguments, so it cannot be used without '
                f'them. Give them when you use it: canvas.screen.write({name}(...)).'
            ) from None
        if not self._takes_context:
            return self._function()  # type: ignore[call-arg]
        return self._function(context)  # type: ignore[call-arg]

    def __repr__(self) -> str:
        return f'{type(self).__name__}({getattr(self._function, "__name__", "?")})'


class _BoundComponent(_HookSource):
    """A component function with its own parameters given."""

    def __init__(
        self,
        function: _ComponentFunction[..., object, object],
        bound: inspect.BoundArguments,
    ) -> None:
        """Keep the function and its arguments. Call the decorated function instead."""
        super().__init__()
        self.function = function
        self._bound = bound

    @property
    def arguments(self) -> Mapping[str, object]:
        """The component's own parameters, by name."""
        return MappingProxyType(self._bound.arguments)

    def _owners(self) -> tuple[_HookSource, ...]:
        return (self.function, self)

    def _call(self, context: Context[object, object]) -> object:
        leading = (context,) if self.function._takes_context else ()
        return self.function._function(  # type: ignore[call-arg]
            *leading, *self._bound.args, **self._bound.kwargs
        )

    def __repr__(self) -> str:
        name = getattr(self.function._function, '__name__', '?')
        arguments = ', '.join(f'{key}={value!r}' for key, value in self.arguments.items())
        return f'{name}({arguments})'


class WritableComponent(_BoundComponent, Generic[DepsT, StateT]):
    """
    A writable function with its own parameters given: ``gauge(ratio=0.7)``.

    Write it with ``canvas.screen.write(component)``. It is evaluated once, and again only when it
    read something that changes. See [`writable`][xnano.writable].

    Attributes:
        arguments: The component's own parameters, by name.
    """

    def __xnano_write__(self, context: Context[DepsT, StateT]) -> Writable:
        """Draw the component with the parameters it was given."""
        return cast('Writable', self._call(context))


class PlayableComponent(_BoundComponent, Generic[DepsT, StateT]):
    """
    A playable function with its own parameters given: ``arpeggio(root='C4')``.

    Play it with ``canvas.speaker.play(component)``. See [`playable`][xnano.playable].

    Attributes:
        arguments: The component's own parameters, by name.
    """

    def __xnano_play__(self, context: Context[DepsT, StateT]) -> Playable:
        """Return what to play, with the parameters the component was given."""
        return cast('Playable', self._call(context))


class WritableFunction(_ComponentFunction[ParametersT, DepsT, StateT]):
    """
    A function that draws itself: what [`writable`][xnano.writable] returns.

    The function is the component. ``canvas.screen.write(function)`` draws it with its default
    parameters, and ``canvas.screen.write(function(ratio=0.7))`` gives it its own parameters
    first. Calling it does not run it; it makes a
    [`WritableComponent`][xnano.components.WritableComponent].

    Attributes:
        arguments: The parameters it is written with, none: the defaults apply.
    """

    _decorator = 'writable'
    _component_class = WritableComponent

    def __call__(
        self, *arguments: ParametersT.args, **keywords: ParametersT.kwargs
    ) -> WritableComponent[DepsT, StateT]:
        """Give the component its own parameters; the context is passed for you."""
        return cast(
            'WritableComponent[DepsT, StateT]', self._bind(*arguments, **keywords)
        )

    def __xnano_write__(self, context: Context[DepsT, StateT]) -> Writable:
        """Draw the component with its default parameters."""
        return cast('Writable', self._call_with_defaults(context))


class PlayableFunction(_ComponentFunction[ParametersT, DepsT, StateT]):
    """
    A function that plays itself: what [`playable`][xnano.playable] returns.

    ``canvas.speaker.play(function)`` plays it with its default parameters, and
    ``canvas.speaker.play(function(root='C4'))`` gives it its own parameters first.

    Attributes:
        arguments: The parameters it is played with, none: the defaults apply.
    """

    _decorator = 'playable'
    _component_class = PlayableComponent

    def __call__(
        self, *arguments: ParametersT.args, **keywords: ParametersT.kwargs
    ) -> PlayableComponent[DepsT, StateT]:
        """Give the component its own parameters; the context is passed for you."""
        return cast(
            'PlayableComponent[DepsT, StateT]', self._bind(*arguments, **keywords)
        )

    def __xnano_play__(self, context: Context[DepsT, StateT]) -> Playable:
        """Return what to play with the default parameters."""
        return cast('Playable', self._call_with_defaults(context))


class RenderableComponent(_BoundComponent, Generic[DepsT, StateT]):
    """
    A renderable function with its own parameters given: ``meter(limit=0.9)``.

    Write it with ``canvas.screen.write(component)``. See [`renderable`][xnano.renderable].

    Attributes:
        arguments: The component's own parameters, by name.
    """

    def __xnano_render__(self, context: Context[DepsT, StateT]) -> None:
        """Draw on ``context.screen`` and play on ``context.speaker``, with the parameters given."""
        return cast('None', self._call(context))


class RenderableFunction(_ComponentFunction[ParametersT, DepsT, StateT]):
    """
    A function with a screen of its own: what [`renderable`][xnano.renderable] returns.

    The function is the component. ``canvas.screen.write(function)`` runs it with its default
    parameters, and ``canvas.screen.write(function(limit=0.9))`` gives it its own parameters
    first. Calling it does not run it; it makes a
    [`RenderableComponent`][xnano.components.RenderableComponent].

    Attributes:
        arguments: The parameters it is written with, none: the defaults apply.
    """

    _decorator = 'renderable'
    _component_class = RenderableComponent

    def __call__(
        self, *arguments: ParametersT.args, **keywords: ParametersT.kwargs
    ) -> RenderableComponent[DepsT, StateT]:
        """Give the component its own parameters; the context is passed for you."""
        return cast(
            'RenderableComponent[DepsT, StateT]', self._bind(*arguments, **keywords)
        )

    def __xnano_render__(self, context: Context[DepsT, StateT]) -> None:
        """Draw on ``context.screen`` and play on ``context.speaker``, with the defaults."""
        return cast('None', self._call_with_defaults(context))


@overload
def writable(function: Callable[[], Writable], /) -> WritableFunction[[], None, None]: ...
@overload
def writable(  # pyright: ignore[reportGeneralTypeIssues]
    function: Callable[Concatenate[Context[DepsT, StateT], ParametersT], Writable], /
) -> WritableFunction[ParametersT, DepsT, StateT]: ...
def writable(  # pyright: ignore[reportGeneralTypeIssues]
    function: Callable[Concatenate[Context[DepsT, StateT], ParametersT], Writable]
    | Callable[[], Writable],
    /,
) -> WritableFunction[ParametersT, DepsT, StateT] | WritableFunction[[], None, None]:
    """
    Turn a function into a component that draws itself.

    The function takes the [`Context`][xnano.hooks.Context] first, then its own parameters,
    and returns anything ``canvas.screen.write`` accepts; a function with no parameters at all is
    called without the context. The decorated object is the component:
    ``canvas.screen.write(gauge)`` draws it with its defaults, ``canvas.screen.write(gauge(ratio=0.7))`` gives
    it parameters, and ``gauge.hook(...)`` adds behavior to its placements.

    A component is evaluated once, and again only when it read something that changes: the
    time or the event (every frame), the size of its buffer, the parent or the canvas (when
    the screen is resized), a state path (when it changes), or an input such as
    ``context.keyboard`` (when it arrives). What it reads is recorded as it runs. Reads of
    ``context.deps`` and of mutable fields on ``self`` are not tracked: when they change, call
    [`placement.refresh()`][xnano.layout.Placement.refresh].

    Args:
        function: The function ``(context, **own_parameters) -> content``.

    Raises:
        TypeError: The decorated object is a class or is not callable, or the function's
            first parameter is keyword-only or variadic, so it cannot take the context.

    Examples:
        ```python
        import xnano

        @xnano.writable
        def gauge(context: xnano.Context, ratio: float = 0.5) -> str:
            return '#' * round(ratio * 10)

        with xnano.new(width=12, height=1) as canvas:
            canvas.screen.write(gauge(ratio=0.3))
            assert canvas.screen.render().strip() == '###'
        ```
    """
    return WritableFunction(
        cast(
            'Callable[Concatenate[Context[DepsT, StateT], ParametersT], Writable]',
            function,
        )
    )


def renderable(  # pyright: ignore[reportGeneralTypeIssues]
    function: Callable[Concatenate[Context[DepsT, StateT], ParametersT], None], /
) -> RenderableFunction[ParametersT, DepsT, StateT]:
    """
    Turn a function into a component with a screen of its own, which draws and plays.

    The function takes the [`Context`][xnano.hooks.Context] first, then its own parameters,
    and returns nothing. Its ``context.screen`` is its own: a screen where the component is
    written, as large as what the function writes on it unless the component was written
    with a ``width`` or a ``height``. Its ``context.speaker``, ``context.clock``,
    ``context.keyboard`` and ``context.mouse`` are the canvas's. Write it with
    ``canvas.screen.write(meter)``, or ``canvas.screen.write(meter(limit=0.9))`` to give it
    parameters; ``meter.hook(...)`` adds behavior to where it is written.

    The function runs once, and again only when it read something that changes, as a
    [`writable`][xnano.writable] does. Each run starts from an empty screen: what the run
    before wrote is removed first, so the screen shows what the latest run wrote. What a run
    plays starts when that run plays it.

    Args:
        function: The function ``(context, **own_parameters) -> None``.

    Raises:
        TypeError: The decorated object is a class or is not callable, or the function takes
            no parameters or its first parameter is keyword-only or variadic, so it cannot
            take the context.

    Examples:
        ```python
        import xnano

        @xnano.renderable
        def meter(context: xnano.Context, level: float = 0.5) -> None:
            context.screen.write('level')
            context.screen.write('#' * round(level * 10))

        with xnano.new(width=12, height=3) as canvas:
            placement = canvas.screen.write(meter(level=0.3), y=1)
            assert canvas.screen.render().splitlines()[1:] == ['level', '###']
            assert (placement.width, placement.height) == (5, 2)
        ```
    """
    return RenderableFunction(function)


@overload
def playable(function: Callable[[], Playable], /) -> PlayableFunction[[], None, None]: ...
@overload
def playable(  # pyright: ignore[reportGeneralTypeIssues]
    function: Callable[Concatenate[Context[DepsT, StateT], ParametersT], Playable], /
) -> PlayableFunction[ParametersT, DepsT, StateT]: ...
def playable(  # pyright: ignore[reportGeneralTypeIssues]
    function: Callable[Concatenate[Context[DepsT, StateT], ParametersT], Playable]
    | Callable[[], Playable],
    /,
) -> PlayableFunction[ParametersT, DepsT, StateT] | PlayableFunction[[], None, None]:
    """
    Turn a function into a component that plays itself.

    The function takes the [`Context`][xnano.hooks.Context] first, then its own parameters,
    and returns anything ``canvas.play`` accepts; a function with no parameters at all is
    called without the context. It is evaluated once when played, and again
    on a beat only when it read something that changes (the time or the beat, a state path or
    an input), playing the new result each time. ``canvas.play`` returns a
    [`PlayHandle`][xnano.audio.PlayHandle] whose ``remove()`` stops it.

    Args:
        function: The function ``(context, **own_parameters) -> playable``.

    Raises:
        TypeError: The decorated object is a class or is not callable, or the function's
            first parameter is keyword-only or variadic, so it cannot take the context.

    Examples:
        ```python
        import xnano

        @xnano.playable
        def chord(context: xnano.Context, root: str = 'C4') -> xnano.Note:
            return xnano.Note(root, beats=0.5)

        with xnano.new(width=8, height=1) as canvas:
            canvas.speaker.play(chord(root='E4'))
            canvas.clock.step(delta_seconds=0.5)
            assert canvas.speaker.render().peak > 0.0
        ```
    """
    return PlayableFunction(
        cast(
            'Callable[Concatenate[Context[DepsT, StateT], ParametersT], Playable]',
            function,
        )
    )


# -- running components --------------------------------------------------------------------


def _is_component(content: object) -> bool:
    """Whether ``content`` is an object that draws itself with ``__xnano_write__``."""
    return not isinstance(content, type) and hasattr(content, '__xnano_write__')


class _Stack:
    """A sequence that holds components, drawn from top to bottom."""

    def __init__(self, items: Sequence[object]) -> None:
        """Keep the items to draw one below the other."""
        self.items = items

    def __xnano_write__(self, context: Context[object, object]) -> Writable:
        return cast('Writable', list(self.items))


def _as_component(content: object) -> object | None:
    """
    Return the component to run for ``content``, or ``None`` when it is not one.

    Anything with ``__xnano_write__`` is its own component; a sequence that holds one is
    wrapped so that it is evaluated with a context.
    """
    if isinstance(content, (str, bytes, bytearray)):
        return None
    if _is_component(content):
        return content
    if isinstance(content, Sequence) and any(
        _as_component(item) is not None for item in content
    ):
        return _Stack(content)
    return None


class _Driver:
    """What re-runs a component: the read log, the subscriptions and the state it follows."""

    def __init__(self, canvas: Canvas[object, object], component: object) -> None:
        """Start a driver for a component on a canvas."""
        self._root = canvas
        self.component = component
        self.log = ReadLog()
        self._is_closed = False
        self._is_dirty = False
        self._pending_event: object = None
        self._followed: frozenset[StatePath] | None = None
        self._own_revisions: deque[int] = deque(maxlen=4)
        self._input_hooks: dict[str, HookHandle[object, object]] = {}
        self._plugin_state: StateNamespace | None = None
        self._effect_state: EffectState | None = None

    @property
    def _canvas(self) -> Canvas[object, object]:
        """The root canvas the component runs on."""
        return self._root

    @property
    def canvas(self) -> Canvas[object, object]:
        """The root canvas the component runs on."""
        return self._canvas

    @property
    def is_closed(self) -> bool:
        """Whether the driver was closed."""
        return self._is_closed

    @property
    def is_removed(self) -> bool:
        """Whether the component stopped being drawn."""
        return self._is_closed

    def remove(self) -> None:
        """Stop re-running the component. Removing it twice does nothing."""
        self.close()

    @property
    def _name(self) -> str:
        function = getattr(self.component, 'function', None)
        function = getattr(function, '_function', None) or getattr(
            self.component, '_function', None
        )
        return getattr(function, '__name__', type(self.component).__name__)

    def _state_namespace(self) -> StateNamespace:
        namespace = self._plugin_state
        if namespace is None:
            namespace = self._plugin_state = self._canvas._new_state_namespace('plugins')
        return namespace

    # -- evaluating ----------------------------------------------------------------------

    def _timeline(self) -> Callable[[], Region[float]] | None:
        """Returns the region on the timeline of what is playing, or ``None`` off the timeline."""
        return None

    def _context(
        self,
        owner: Placement[object, object] | Canvas[object, object],
        event: object,
        log: ReadLog,
        screen: Screen[object, object] | None = None,
    ) -> Context[object, object]:
        return Context(
            self._canvas,
            owner,
            cast('HookHandle[object, object]', self),
            cast('_core.Event | _core.TerminalStateChange | Frame | None', event),
            None,
            log=log,
            timeline=self._timeline(),
            screen=screen,
        )

    def _run(self, call: Callable[[], object]) -> tuple[object, ReadLog, _HookRun]:
        """Call ``call`` while recording the state it reads and the values it sets."""
        canvas = self._canvas
        run = _HookRun(track=True)
        run.handle = cast('HookHandle[object, object]', self)
        previous = canvas._active_run
        run.begin()
        canvas._active_run = run
        canvas._runs_in_progress += 1
        try:
            result = call()
        except BaseException:
            run.discard()
            raise
        finally:
            canvas._runs_in_progress -= 1
            canvas._active_run = previous
        return result, self.log, run

    def _finish(self, run: _HookRun) -> None:
        """Save what the run set in one transaction and follow what it read."""
        canvas = self._canvas
        run.is_active = False
        run.snapshot = None
        if run.pending:
            try:
                change = canvas._commit_state(run.pending)
            finally:
                run.pending.clear()
            if change is not None:
                self._own_revisions.append(change.revision)
        reads = frozenset(run.reads)
        run.reads.clear()
        if reads != (self._followed or frozenset()):
            self._followed = reads or None
            if reads:
                canvas._host.post(
                    lambda: canvas._follow_state(cast('_StateFollower', self), reads)
                )
            else:
                canvas._host.post(
                    lambda: canvas._unfollow_state(cast('_StateFollower', self))
                )

    # -- what marks it dirty -------------------------------------------------------------

    def _listen(self, kinds: set[str]) -> None:
        """Mark the component dirty when an input of these kinds arrives."""
        canvas = self._canvas
        for kind in kinds:
            if kind in self._input_hooks:
                continue
            on = _INPUT_EVENTS[kind]

            def heard(context: Context[object, object], kind: str = kind) -> None:
                if self._is_closed or not self._concerns(context, kind):
                    return
                self._pending_event = context._event
                self.mark_dirty()

            heard._component_name = self._name  # type: ignore[attr-defined]
            self._input_hooks[kind] = canvas.hook(heard, on=on)  # type: ignore[call-overload]

    def _concerns(self, context: Context[object, object], kind: str) -> bool:
        """Whether an input event matters to this component."""
        return True

    def mark_dirty(self) -> None:
        """Make the component run again at the next frame (or beat)."""
        self._is_dirty = True
        self._canvas._host.post(self._schedule)

    def _schedule(self) -> None:
        raise NotImplementedError

    # -- state follower ------------------------------------------------------------------

    def _state_followed(self, change: _core.TerminalStateChange) -> None:
        raise NotImplementedError

    def _state_loop(
        self, change: _core.TerminalStateChange, others: list[_StateFollower]
    ) -> None:
        path = '.'.join(str(part) for part in change.paths[0]) if change.paths else ''
        self._fail(
            TerminalError(
                f'The component {self._name} keeps being run again because {path!r} keeps '
                f'changing. Make it stop writing what it reads, or write only when the '
                f'value differs.'
            )
        )

    def _fail(self, error: BaseException) -> None:
        if isinstance(error, TerminalError) and error.__cause__ is None:
            failure = error
        else:
            failure = TerminalError(
                f'The component {self._name} failed: {type(error).__name__}: '
                f'{str(error).rstrip(".")}. Fix the component, then create a new canvas '
                f'with xnano.new() or xnano.open().'
            )
            failure.__cause__ = error
        self._canvas._record_failure(failure)
        self._canvas._stop_runtime()

    def close(self) -> None:
        """Stop re-running the component and let go of everything it registered."""
        if self._is_closed:
            return
        self._is_closed = True
        effect_state = self._effect_state
        if effect_state is not None:
            self._effect_state = None
            effect_state.clear()
        for handle in self._input_hooks.values():
            handle.remove()
        self._input_hooks.clear()
        canvas = self._canvas
        canvas._host.post(lambda: canvas._unfollow_state(cast('_StateFollower', self)))
        namespace = self._plugin_state
        if namespace is not None:
            self._plugin_state = None
            namespace._remove()


class _ComponentDriver(_Driver):
    """
    Draws a component into its placement, and again when something it read changes.

    A component that read nothing that changes is evaluated once.

    Attributes:
        placement: The placement the component is drawn in.
        component: The object whose ``__xnano_write__`` method is run.
        log: What the last run read.
    """

    def __init__(
        self,
        placement: Placement[object, object],
        component: object,
        *,
        is_width_given: bool,
        is_height_given: bool,
    ) -> None:
        """
        Create the driver. Use ``canvas.screen.write(component)`` instead of calling this.

        Args:
            placement: The placement the component is drawn in.
            component: An object with ``__xnano_write__``.
            is_width_given: Whether the caller fixed the width of the placement.
            is_height_given: Whether the caller fixed the height.
        """
        super().__init__(placement._canvas, component)
        self.placement = placement
        self._is_width_given = is_width_given
        self._is_height_given = is_height_given
        self._is_fitting = False
        self._cancel_frames: Callable[[], None] | None = None
        self._resize_hook: HookHandle[object, object] | None = None
        self._last_elapsed: float | None = None

    @property
    def _canvas(self) -> Canvas[object, object]:
        """The root canvas the component runs on, which a nested canvas can change."""
        return self.placement._canvas

    @property
    def is_size_followed(self) -> bool:
        """Whether the component read a size and the placement was resized from outside."""
        return self.log.uses_size and not self._is_fitting

    def start(self) -> None:
        """Draw the component for the first time, and let errors reach the caller."""
        self.evaluate(None)
        self._warn_if_mutable()

    def _warn_if_mutable(self) -> None:
        component = self.component
        kind = type(component)
        if self.log.is_dynamic or self._followed or kind in _warned_classes:
            return
        if isinstance(component, (_BoundComponent, _ComponentFunction, _Stack)):
            return
        from xnano.art import Art

        if isinstance(component, Art):
            return
        if dataclasses.is_dataclass(kind):
            dataclass_parameters = getattr(kind, '__dataclass_params__', None)
            is_mutable = not getattr(dataclass_parameters, 'frozen', False)
        else:
            is_mutable = hasattr(component, '__dict__') or bool(
                getattr(kind, '__slots__', ())
            )
        if not is_mutable:
            return
        with _warned_lock:
            if kind in _warned_classes:
                return
            _warned_classes.add(kind)
        warnings.warn(
            f'{kind.__name__} is drawn once because its __xnano_write__ method read nothing that '
            f'changes. If you change its attributes later, call placement.refresh() to draw '
            f'it again, or make the class a frozen dataclass if it never changes.',
            UserWarning,
            stacklevel=_caller_stack_level(),
        )

    def evaluate(self, event: object) -> None:
        """Run the component and show the result."""
        if self._is_closed or self.placement._removed:
            return
        canvas = self._canvas
        self.log = log = ReadLog()
        context = self._context(self.placement, event, log)

        def call() -> _core.Buffer:
            from xnano._internal._content import content_buffer

            buffer, _ = content_buffer(
                cast('Content', self.component), limit=canvas.screen.size, context=context
            )
            return buffer

        buffer, _, run = self._run(call)
        self._show(cast('_core.Buffer', buffer))
        self._finish(run)
        self._last_elapsed = canvas._clock_view.elapsed_seconds
        self._follow_log()

    def _show(self, buffer: _core.Buffer) -> None:
        """Put the result in the placement, resizing it if the caller left the size open."""
        placement = self.placement
        decorated = placement._decorated
        extra_width = extra_height = 0
        if decorated is not None:
            extra_width = decorated.insets.horizontal
            extra_height = decorated.insets.vertical
        self._is_fitting = True
        try:
            if not self._is_width_given and placement.width != buffer.width + extra_width:
                placement.width = buffer.width + extra_width
            if (
                not self._is_height_given
                and placement.height != buffer.height + extra_height
            ):
                placement.height = buffer.height + extra_height
        finally:
            self._is_fitting = False
        placement._content.update(_core.Fill(' '), _core.Paste(buffer, mode='replace'))
        if placement._appearance is not None:
            placement._look_changed()
        self.placement._canvas._request_frame()

    def _follow_log(self) -> None:
        """Subscribe to whatever the last run read."""
        log = self.log
        canvas = self.placement._canvas
        if log.uses_time:
            if self._cancel_frames is None:
                self._cancel_frames = canvas._on_frame(self._on_frame)
        elif self._cancel_frames is not None and not self._is_dirty:
            cancel, self._cancel_frames = self._cancel_frames, None
            cancel()
        if log.uses_size and self._resize_hook is None:
            self._resize_hook = canvas.hook(self._resized, on='resize')
        if log.input_kinds:
            self._listen(log.input_kinds)

    def _resized(self, context: Context[object, object]) -> None:
        self._pending_event = None
        self.mark_dirty()

    def _concerns(self, context: Context[object, object], kind: str) -> bool:
        if kind not in ('mouse', 'scroll'):
            return True
        event = context._event
        mouse = event.mouse if isinstance(event, _core.Event) else None
        if mouse is None:
            return False
        bounds = self.placement._buffer._absolute_bounds
        return bool(bounds.contains(mouse.position))

    def _schedule(self) -> None:
        if self._is_closed or self.placement._removed:
            return
        if self._cancel_frames is None:
            self._cancel_frames = self.placement._canvas._on_frame(self._on_frame)
        else:
            self.placement._canvas._request_frame()

    def _on_frame(self, frame: Frame) -> None:
        if self._is_closed or self.placement._removed:
            return
        elapsed = frame.elapsed_seconds
        is_due = self._is_dirty or (self.log.uses_time and elapsed != self._last_elapsed)
        if is_due:
            self._last_elapsed = elapsed
            self._is_dirty = False
            event, self._pending_event = self._pending_event or frame, None
            try:
                self.evaluate(event)
            except Exception as error:
                self._fail(error)
                return
        if not self.log.uses_time and not self._is_dirty:
            cancel, self._cancel_frames = self._cancel_frames, None
            if cancel is not None:
                cancel()

    def _state_followed(self, change: _core.TerminalStateChange) -> None:
        if self._is_closed:
            return
        try:
            self.evaluate(change)
        except Exception as error:
            self._fail(error)

    def refresh(self) -> None:
        """Evaluate the component again at the next frame."""
        self._pending_event = None
        self.mark_dirty()

    def close(self) -> None:
        """Stop re-running the component. Called when the placement is removed."""
        if self._is_closed:
            return
        super().close()
        cancel, self._cancel_frames = self._cancel_frames, None
        if cancel is not None:
            cancel()
        hook, self._resize_hook = self._resize_hook, None
        if hook is not None:
            hook.remove()
        component = self.component
        released = getattr(component, '_released', None)
        if released is not None:
            released(self.placement)


def _caller_stack_level() -> int:
    """The ``stacklevel`` that makes a warning point at the first caller outside xnano."""
    package_directory = os.path.dirname(os.path.abspath(__file__))
    level = 1
    frame = sys._getframe(1)
    while frame is not None and os.path.abspath(frame.f_code.co_filename).startswith(
        package_directory
    ):
        frame = frame.f_back
        level += 1
    return level


def _attach_component(
    placement: Placement[object, object],
    component: object,
    *,
    is_width_given: bool,
    is_height_given: bool,
) -> None:
    """Draw ``component`` in ``placement``, install its hooks and keep it up to date."""
    driver = _ComponentDriver(
        placement,
        component,
        is_width_given=is_width_given,
        is_height_given=is_height_given,
    )
    placement._driver = driver
    placed = getattr(component, '_placed', None)
    if placed is not None:
        placed(placement, component)
    driver.start()


class _RenderingDriver(_ComponentDriver):
    """
    Runs a renderable on a screen of its own, and again when something it read changes.

    Each run starts from an empty screen: what the run before wrote is removed first.

    Attributes:
        placement: The placement that shows the component's screen.
        area: The canvas whose screen the component draws on.
        component: The object whose ``__xnano_render__`` method is run.
        log: What the last run read.
    """

    def __init__(
        self,
        placement: Placement[object, object],
        component: object,
        area: Canvas[object, object],
    ) -> None:
        """
        Create the driver. Use ``canvas.screen.write(component)`` instead of calling this.

        Args:
            placement: The placement that shows the component's screen.
            component: An object with ``__xnano_render__``.
            area: The canvas written in the placement, whose screen the component draws on.
        """
        super().__init__(placement, component, is_width_given=True, is_height_given=True)
        self.area = area
        self._written: list[Placement[object, object]] = []

    def evaluate(self, event: object) -> None:
        """Clear the component's screen, then run the component on it."""
        if self._is_closed or self.placement._removed:
            return
        area = self.area
        for written in self._written:
            if not written._removed:
                written.remove()
        self._written = run_writes = []
        area._content.update(_core.Fill(' '))
        self.log = log = ReadLog()
        context = self._context(self.placement, event, log, screen=area.screen)
        component = self.component

        def call() -> None:
            area._rendering_writes = run_writes
            try:
                result = cast(
                    'SupportsRender[object, object]', component
                ).__xnano_render__(context)
            finally:
                area._rendering_writes = None
            if result is not None:
                raise _returned_content_error(component, result)

        _, _, run = self._run(call)
        self._finish(run)
        self._last_elapsed = self._canvas._clock_view.elapsed_seconds
        self._follow_log()
        self._canvas._request_frame()


def _returned_content_error(component: object, result: object) -> TypeError:
    """The error for an ``__xnano_render__`` that returned content instead of drawing it."""
    if isinstance(component, (RenderableFunction, RenderableComponent)):
        function = (
            component._function if isinstance(component, RenderableFunction) else None
        )
        function = function or getattr(component, 'function', None)
        name = getattr(getattr(function, '_function', function), '__name__', 'it')
        return TypeError(
            f'{name} returned {type(result).__name__}, but a renderable draws on '
            f'context.screen and returns nothing. Write it with context.screen.write(...), '
            f'or decorate {name} with @xnano.writable to return content to write.'
        )
    kind = type(component).__name__
    return TypeError(
        f'{kind}.__xnano_render__ returned {type(result).__name__}, but it draws on '
        f'context.screen and returns nothing. Write it with context.screen.write(...), or '
        f'name the method __xnano_write__ to return content to write.'
    )


def _attach_rendering(
    placement: Placement[object, object],
    component: object,
    area: Canvas[object, object],
) -> None:
    """Run the renderable ``component`` on ``area``, install its hooks and keep it up to date."""
    check_context_method(component, '__xnano_render__')
    driver = _RenderingDriver(placement, component, area)
    placement._driver = driver
    placed = getattr(component, '_placed', None)
    if placed is not None:
        placed(placement, component)
    driver.start()


# -- playing -------------------------------------------------------------------------------


def _resolve_playable(
    item: object, context: Context[object, object], depth: int = 0
) -> object:
    """Replace every component in ``item`` by what it plays."""
    if depth > 8:
        raise TerminalError(
            f'{type(item).__name__}.__xnano_play__ keeps returning something that plays '
            f'again. Return a Note, a Melody, an xnano.Audio, text or a list of those.'
        )
    if isinstance(item, (str, bytes, bytearray)):
        return item
    if hasattr(item, '__xnano_play__'):
        check_context_method(item, '__xnano_play__')
        played = cast('SupportsPlay[object, object]', item).__xnano_play__(
            cast('Context[object, object]', context)
        )
        if played is item:
            return item
        return _resolve_playable(played, context, depth + 1)
    if isinstance(item, Sequence):
        return [_resolve_playable(part, context, depth + 1) for part in item]
    return item


def _holds_component(item: object) -> bool:
    if isinstance(item, (str, bytes, bytearray, Note)):
        return False
    if hasattr(item, '__xnano_play__'):
        return True
    return isinstance(item, Sequence) and any(_holds_component(part) for part in item)


class _PlayableDriver(_Driver):
    """
    Plays a playable component, and plays it again on a beat when something it read changed.

    Attributes:
        component: The object whose ``__xnano_play__`` method is run.
        log: What the last run read.
        is_finished: Whether nothing is left to sound.
    """

    def __init__(
        self,
        canvas: Canvas[object, object],
        component: object,
        options: PlayOptions,
    ) -> None:
        """
        Create the driver. Use ``canvas.speaker.play(component)`` instead of calling this.

        Args:
            canvas: The root canvas that plays.
            component: An object with ``__xnano_play__``.
            options: The keyword options of ``play``.
        """
        super().__init__(canvas, component)
        self._options = cast('PlayOptions', dict(options))
        self._handles: list[PlayHandle] = []
        self._beat_hook: HookHandle[object, object] | None = None
        self._component_hooks: list[HookHandle[object, object]] = []
        self._playing: PlayHandle | None = None

    @property
    def is_finished(self) -> bool:
        """Whether nothing is left to sound: it is closed, or static and every sound ended."""
        if self._is_closed:
            return True
        if self._beat_hook is not None:
            return False
        return all(handle.is_finished for handle in self._handles)

    def _timeline_region(self) -> Region[float]:
        """
        Where the sound the component played last is on the timeline of the canvas.

        Before it has played anything the region is empty and starts at the beat the canvas
        has reached, or at the ``at_beat`` it is played on.
        """
        playing = self._playing
        if playing is not None:
            region = playing._region
            if region is not None:
                return region
        from xnano.layout._region import _timeline_region

        canvas = self._canvas
        at_beat = self._options.get('at_beat')
        return _timeline_region(
            start_beats=(
                canvas._clock_view.elapsed_seconds * canvas._clock_view.bpm / 60.0
                if at_beat is None
                else float(at_beat)
            ),
            length_beats=0.0,
            pitches=(),
            tempo_changes=((0.0, canvas._clock_view.bpm),),
        )

    def _timeline(self) -> Callable[[], Region[float]] | None:
        return self._timeline_region

    def start(self) -> None:
        """Play the component for the first time, and let errors reach the caller."""
        component = self.component
        placed = getattr(component, '_placed', None)
        if placed is not None:
            if isinstance(component, _HookSource):
                placed(self._canvas, component, timeline=self._timeline_region)
            else:
                placed(self._canvas, component)
        self.evaluate(None)

    def evaluate(self, event: object) -> None:
        """Run the component and play the result."""
        canvas = self._canvas
        self.log = log = ReadLog()
        context = self._context(canvas, event, log)

        def call() -> object:
            return _resolve_playable(self.component, context)

        result, _, run = self._run(call)
        self._finish(run)
        if self._is_closed:
            return
        self._handles = [handle for handle in self._handles if not handle.is_finished]
        handle = canvas._audio_device().play(cast('Playable', result), **self._options)
        self._handles.append(handle)
        if handle._has_region:
            self._playing = handle
        if (log.uses_time or log.input_kinds or self._followed) and (
            self._beat_hook is None
        ):
            self._beat_hook = canvas.hook(self._on_beat, on='beat')
        if log.input_kinds:
            self._listen(log.input_kinds)

    def _on_beat(self, context: Context[object, object]) -> None:
        if self._is_closed:
            return
        if self.log.uses_time or self._is_dirty:
            self._is_dirty = False
            event, self._pending_event = self._pending_event, None
            self.evaluate(event or context._event)

    def _schedule(self) -> None:
        """A playable runs on the next beat, so there is nothing to arm."""

    def _state_followed(self, change: _core.TerminalStateChange) -> None:
        self._pending_event = change
        self._is_dirty = True

    def close(self) -> None:
        """Stop the component and silence what it started."""
        if self._is_closed:
            return
        super().close()
        hook, self._beat_hook = self._beat_hook, None
        if hook is not None:
            hook.remove()
        for handle in self._handles:
            handle.remove()
        self._handles.clear()
        released = getattr(self.component, '_released', None)
        if released is not None:
            released(self._canvas)


class _ComponentPlayHandle(PlayHandle):
    """The handle of a playable component: finished when nothing is left to sound."""

    __slots__ = ('_driver',)

    def __init__(self, driver: _PlayableDriver) -> None:
        """Wrap the driver of a playable component."""
        super().__init__(clock=lambda: 0.0, end_seconds=0.0, cancel=driver.close)
        self._driver = driver

    @property
    def is_finished(self) -> bool:
        """Whether the component is closed, or static and every sound it made ended."""
        return self._is_removed or self._driver.is_finished


def _play_component(
    canvas: Canvas[object, object], playable_value: object, options: PlayOptions
) -> PlayHandle | None:
    """
    Play something that holds a component and return a handle, or ``None`` when it holds none.

    A single component is evaluated now and again on the beats where it read something that
    changed; a sequence that holds components is resolved once.
    """
    if not _holds_component(playable_value):
        return None
    driver = _PlayableDriver(canvas, playable_value, options)
    driver.start()
    return _ComponentPlayHandle(driver)
