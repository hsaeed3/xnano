"""xnano.beta.hooks"""

from __future__ import annotations

import dataclasses
from typing import (
    Any,
    Awaitable,
    Callable,
    ClassVar,
    Generic,
    Literal,
    TypeAlias,
    TypeVar,
    TypedDict,
    Union,
    TYPE_CHECKING,
    overload,
)

from xnano.beta.utils.core import get_first_function_parameter_type
from xnano.beta.context import Context
from xnano.beta.events import KeyboardEventKind, MouseEventKind, EventDataType
from xnano.beta.keyboard import KeyboardBinding
from xnano.beta.mouse import MouseButton


StateT = TypeVar("StateT")


EventHookFunction: TypeAlias = (
    Callable[..., Any | Awaitable[Any]]
    | Callable[[Context[StateT]], Any | Awaitable[Any]]
    | Callable[[Context[StateT], tuple[Any, ...]], Any | Awaitable[Any]]
)
"""A function that can be decorated by an ``@on_<event>`` decorator within
a grid for adding event handling.
"""


_PENDING_HOOKS: list[EventHookFunction] = []


class _OnKeyboardHookFunctionEntry(TypedDict):
    bindings: tuple[str, ...]
    kind: KeyboardEventKind | None
    handler: EventHookFunction


class _OnMouseHookFunctionEntry(TypedDict):
    buttons: tuple[str, ...]
    kind: MouseEventKind | None
    handler: EventHookFunction


class _OnTickHookFunctionEntry(TypedDict):
    interval: int
    handler: EventHookFunction


class _OnStateHookFunctionEntry(TypedDict):
    expression: str
    handler: EventHookFunction


@dataclasses.dataclass(slots=True)
class _EventHooksRegistry:
    """Internal utility class for managing event hook registration within
    grids.
    """

    ON_EVENT_HOOK_ATTR: ClassVar[str] = "__xnano_on_event__"
    ON_KEYBOARD_HOOK_ATTR: ClassVar[str] = "__xnano_on_keyboard__"
    ON_MOUSE_HOOK_ATTR: ClassVar[str] = "__xnano_on_mouse__"
    ON_RESIZE_HOOK_ATTR: ClassVar[str] = "__xnano_on_resize__"
    ON_CLIPBOARD_HOOK_ATTR: ClassVar[str] = "__xnano_on_clipboard__"
    ON_FOCUS_HOOK_ATTR: ClassVar[str] = "__xnano_on_focus__"
    ON_POLL_HOOK_ATTR: ClassVar[str] = "__xnano_on_poll__"
    ON_TICK_HOOK_ATTR: ClassVar[str] = "__xnano_on_tick__"
    ON_STATE_HOOK_ATTR: ClassVar[str] = "__xnano_on_state__"
    ON_KEYBOARD_FILTER_ATTR: ClassVar[str] = "__xnano_on_keyboard_filter__"
    ON_MOUSE_FILTER_ATTR: ClassVar[str] = "__xnano_on_mouse_filter__"
    ON_MOUSE_FIELD_ATTR: ClassVar[str] = "__xnano_on_mouse_field__"
    ON_TICK_INTERVAL_ATTR: ClassVar[str] = "__xnano_on_tick_interval__"
    ON_STATE_EXPRESSION_ATTR: ClassVar[str] = "__xnano_on_state_expression__"

    on_event_hooks: list[EventHookFunction] = dataclasses.field(
        default_factory=list, init=False
    )
    on_keyboard_hooks: list[_OnKeyboardHookFunctionEntry] = dataclasses.field(
        default_factory=list, init=False
    )
    on_mouse_hooks: list[_OnMouseHookFunctionEntry] = dataclasses.field(
        default_factory=list, init=False
    )
    on_resize_hooks: list[EventHookFunction] = dataclasses.field(
        default_factory=list, init=False
    )
    on_clipboard_hooks: list[EventHookFunction] = dataclasses.field(
        default_factory=list, init=False
    )
    on_focus_hooks: list[EventHookFunction] = dataclasses.field(
        default_factory=list, init=False
    )
    on_poll_hooks: list[EventHookFunction] = dataclasses.field(
        default_factory=list
    )
    on_tick_hooks: list[_OnTickHookFunctionEntry] = dataclasses.field(
        default_factory=list, init=False
    )
    on_state_hooks: list[_OnStateHookFunctionEntry] = dataclasses.field(
        default_factory=list, init=False
    )

    def register_hook(
        self,
        handler: EventHookFunction,
    ) -> None:
        """Registers a function as an event hook.

        Args:
            hook: The function to register as an event hook.
        """
        if hasattr(handler, self.ON_EVENT_HOOK_ATTR):
            self.on_event_hooks.append(handler)
        if hasattr(handler, self.ON_KEYBOARD_HOOK_ATTR):
            filter_specification, kind = getattr(
                handler,
                self.ON_KEYBOARD_FILTER_ATTR,
            )
            self.on_keyboard_hooks.append(
                _OnKeyboardHookFunctionEntry(
                    bindings=filter_specification,
                    kind=kind,
                    handler=handler,
                )
            )
        if hasattr(handler, self.ON_MOUSE_HOOK_ATTR):
            filter_specification, kind = getattr(
                handler,
                self.ON_MOUSE_FILTER_ATTR,
            )
            self.on_mouse_hooks.append(
                _OnMouseHookFunctionEntry(
                    buttons=filter_specification,
                    kind=kind,
                    handler=handler,
                )
            )
        if hasattr(handler, self.ON_RESIZE_HOOK_ATTR):
            self.on_resize_hooks.append(handler)
        if hasattr(handler, self.ON_CLIPBOARD_HOOK_ATTR):
            self.on_clipboard_hooks.append(handler)
        if hasattr(handler, self.ON_FOCUS_HOOK_ATTR):
            self.on_focus_hooks.append(handler)
        if hasattr(handler, self.ON_POLL_HOOK_ATTR):
            self.on_poll_hooks.append(handler)
        if hasattr(handler, self.ON_TICK_HOOK_ATTR):
            interval_milliseconds = getattr(
                handler,
                self.ON_TICK_INTERVAL_ATTR,
                0,
            )
            self.on_tick_hooks.append(
                _OnTickHookFunctionEntry(
                    interval=interval_milliseconds,
                    handler=handler,
                )
            )
        if hasattr(handler, self.ON_STATE_HOOK_ATTR):
            expression = getattr(handler, self.ON_STATE_EXPRESSION_ATTR, "")
            self.on_state_hooks.append(
                _OnStateHookFunctionEntry(
                    expression=expression,
                    handler=handler,
                )
            )

    @classmethod
    def from_component_class(
        cls, component_class: type
    ) -> _EventHooksRegistry:
        """Collects registered ``on_<event>`` hooks decorated onto methods
        within a component class.
        """
        registry = cls()
        hook_attributes = (
            cls.ON_EVENT_HOOK_ATTR,
            cls.ON_KEYBOARD_HOOK_ATTR,
            cls.ON_MOUSE_HOOK_ATTR,
            cls.ON_RESIZE_HOOK_ATTR,
            cls.ON_CLIPBOARD_HOOK_ATTR,
            cls.ON_FOCUS_HOOK_ATTR,
            cls.ON_POLL_HOOK_ATTR,
            cls.ON_TICK_HOOK_ATTR,
            cls.ON_STATE_HOOK_ATTR,
        )

        for base in component_class.__mro__:
            if base is object:
                continue
            for name, member in base.__dict__.items():
                if not callable(member):
                    continue

                is_hook_method = any(
                    hasattr(member, attribute) for attribute in hook_attributes
                )
                if name.startswith("_") and not is_hook_method:
                    continue

                if hasattr(member, cls.ON_EVENT_HOOK_ATTR):
                    registry.on_event_hooks.append(member)
                if hasattr(member, cls.ON_KEYBOARD_HOOK_ATTR):
                    filter_specification, kind = getattr(
                        member,
                        cls.ON_KEYBOARD_FILTER_ATTR,
                    )
                    registry.on_keyboard_hooks.append(
                        _OnKeyboardHookFunctionEntry(
                            bindings=filter_specification,
                            kind=kind,
                            handler=member,
                        )
                    )
                if hasattr(member, cls.ON_MOUSE_HOOK_ATTR):
                    filter_specification, kind = getattr(
                        member,
                        cls.ON_MOUSE_FILTER_ATTR,
                    )
                    registry.on_mouse_hooks.append(
                        _OnMouseHookFunctionEntry(
                            buttons=filter_specification,
                            kind=kind,
                            handler=member,
                        )
                    )
                if hasattr(member, cls.ON_RESIZE_HOOK_ATTR):
                    registry.on_resize_hooks.append(member)
                if hasattr(member, cls.ON_CLIPBOARD_HOOK_ATTR):
                    registry.on_clipboard_hooks.append(member)
                if hasattr(member, cls.ON_FOCUS_HOOK_ATTR):
                    registry.on_focus_hooks.append(member)
                if hasattr(member, cls.ON_POLL_HOOK_ATTR):
                    registry.on_poll_hooks.append(member)
                if hasattr(member, cls.ON_TICK_HOOK_ATTR):
                    interval_milliseconds = getattr(
                        member,
                        cls.ON_TICK_INTERVAL_ATTR,
                        0,
                    )
                    registry.on_tick_hooks.append(
                        _OnTickHookFunctionEntry(
                            interval=interval_milliseconds,
                            handler=member,
                        )
                    )
                if hasattr(member, cls.ON_STATE_HOOK_ATTR):
                    expression = getattr(
                        member, cls.ON_STATE_EXPRESSION_ATTR, ""
                    )
                    registry.on_state_hooks.append(
                        _OnStateHookFunctionEntry(
                            expression=expression,
                            handler=member,
                        )
                    )
        return registry


def _auto_register_hook_function(fn: EventHookFunction) -> EventHookFunction:
    """Register a free-function hook with the active terminal, or queue it.

    Args:
        fn: The hook function to register.

    Returns:
        The hook function.
    """
    from xnano.beta.terminal import _ACTIVE_TERMINAL

    terminal = _ACTIVE_TERMINAL.get()
    if terminal is not None:
        terminal._hooks.register_hook(fn)
    else:
        _PENDING_HOOKS.append(fn)
    return fn


def _decorate_hook_function(fn: EventHookFunction) -> EventHookFunction:
    """Optionally auto-register ``fn`` when it is a module-level function.

    Args:
        fn: The hook function to decorate.

    Returns:
        The decorated hook function.
    """
    qualname = getattr(fn, "__qualname__", "")
    parts = qualname.split(".")
    is_method = len(parts) > 1 and "<locals>" not in parts[-2]
    if not is_method:
        _auto_register_hook_function(fn)
    return fn


def _decorate_on_tick_hook(
    fn: EventHookFunction, interval: int
) -> EventHookFunction:
    """Decorate a hook function with the ``@on_tick`` decorator.

    Args:
        fn: The hook function to decorate.
        interval: The interval in milliseconds to filter the hook function by.

    Returns:
        The decorated hook function.
    """
    setattr(fn, _EventHooksRegistry.ON_TICK_HOOK_ATTR, True)
    setattr(fn, _EventHooksRegistry.ON_TICK_INTERVAL_ATTR, interval)
    return _decorate_hook_function(fn)


def _decorate_on_mouse_hook(
    fn: EventHookFunction,
    *,
    buttons: tuple[str, ...] = (),
    kind: MouseEventKind | None = None,
    field: str | None = None,
) -> EventHookFunction:
    """Decorate a hook function with the ``@on_mouse`` decorator.

    Args:
        fn: The hook function to decorate.
        buttons: The buttons to filter the hook function by.
        kind: The kind of mouse event to filter the hook function by.
        field: The field to filter the hook function by.

    Returns:
        The decorated hook function.
    """
    selected_buttons = buttons if buttons else ("left",)
    selected_kind: MouseEventKind | None = (
        kind if kind is not None else "press"
    )
    setattr(fn, _EventHooksRegistry.ON_MOUSE_HOOK_ATTR, True)
    setattr(
        fn,
        _EventHooksRegistry.ON_MOUSE_FILTER_ATTR,
        (selected_buttons, selected_kind),
    )
    if field is not None:
        setattr(fn, _EventHooksRegistry.ON_MOUSE_FIELD_ATTR, field)
    return _decorate_hook_function(fn)


@overload
def on_keyboard(
    key: KeyboardBinding,
    /,
    *,
    kind: KeyboardEventKind | None = None,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
@overload
def on_keyboard(
    *,
    key: KeyboardBinding,
    kind: KeyboardEventKind | None = None,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
@overload
def on_keyboard(
    handler: EventHookFunction,
    /,
    *,
    key: KeyboardBinding | None = None,
    kind: KeyboardEventKind | None = None,
) -> EventHookFunction: ...
def on_keyboard(
    handler_or_key: "EventHookFunction | KeyboardBinding | None" = None,
    /,
    *keys: KeyboardBinding,
    key: KeyboardBinding | None = None,
    kind: KeyboardEventKind | None = None,
) -> "EventHookFunction | Callable[[EventHookFunction], EventHookFunction]":
    """Decorate a keyboard event hook.

    Args:
        handler_or_key: The handler or key to decorate.
        keys: The keys to filter the hook function by.
        key: The key to filter the hook function by.
        kind: The kind of keyboard event to filter the hook function by.

    Returns:
        The decorated hook function.
    """
    if callable(handler_or_key):
        bindings: tuple[KeyboardBinding, ...] = (
            (key,) if key is not None else keys
        )
        setattr(
            handler_or_key, _EventHooksRegistry.ON_KEYBOARD_HOOK_ATTR, True
        )
        setattr(
            handler_or_key,
            _EventHooksRegistry.ON_KEYBOARD_FILTER_ATTR,
            (bindings, kind),
        )
        return _decorate_hook_function(handler_or_key)

    if handler_or_key is not None:
        keys = (handler_or_key, *keys)  # type: ignore[assignment]
    elif key is not None:
        keys = (key, *keys)
    filter_spec = (keys, kind)

    def decorator(fn: EventHookFunction) -> EventHookFunction:
        setattr(fn, _EventHooksRegistry.ON_KEYBOARD_HOOK_ATTR, True)
        setattr(fn, _EventHooksRegistry.ON_KEYBOARD_FILTER_ATTR, filter_spec)
        return _decorate_hook_function(fn)

    return decorator


@overload
def on_mouse(
    button: MouseButton,
    /,
    *,
    field: str | None = None,
    kind: MouseEventKind | None = None,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
@overload
def on_mouse(
    *,
    button: MouseButton | None = None,
    field: str | None = None,
    kind: MouseEventKind | None = None,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
@overload
def on_mouse(
    handler: EventHookFunction,
    /,
    *,
    button: MouseButton | None = None,
    field: str | None = None,
    kind: MouseEventKind | None = None,
) -> EventHookFunction: ...
def on_mouse(
    handler_or_button: "EventHookFunction | MouseButton | None" = None,
    /,
    *buttons: MouseButton,
    button: MouseButton | None = None,
    field: str | None = None,
    kind: MouseEventKind | None = None,
) -> "EventHookFunction | Callable[[EventHookFunction], EventHookFunction]":
    """Register a mouse event hook.

    Defaults to left-button press when ``button`` and ``kind`` are omitted.
    Pass ``field`` to bind the hook to a grid layout field's interactive region.
    """
    if callable(handler_or_button):
        selected: tuple[MouseButton, ...] = (
            (button,) if button is not None else buttons
        )
        return _decorate_on_mouse_hook(
            handler_or_button,
            buttons=selected,
            kind=kind,
            field=field,
        )

    if handler_or_button is not None:
        buttons = (handler_or_button, *buttons)  # type: ignore[assignment]
    elif button is not None:
        buttons = (button, *buttons)

    def decorator(fn: EventHookFunction) -> EventHookFunction:
        return _decorate_on_mouse_hook(
            fn, buttons=buttons, kind=kind, field=field
        )

    return decorator


@overload
def on_click(
    field: str, /
) -> Callable[[EventHookFunction], EventHookFunction]: ...
@overload
def on_click(
    handler: EventHookFunction,
    /,
    *,
    field: str,
    button: MouseButton = "left",
    kind: MouseEventKind = "press",
) -> EventHookFunction: ...
def on_click(
    field_or_handler: "str | EventHookFunction",
    /,
    *,
    field: str | None = None,
    button: MouseButton = "left",
    kind: MouseEventKind = "press",
) -> "EventHookFunction | Callable[[EventHookFunction], EventHookFunction]":
    """Register a click handler for a grid layout field.

    Example::

        @on_click("body")
        def highlight_body(self, ctx: Context) -> None:
            self.body = Paragraph("clicked", color="red")
    """
    if isinstance(field_or_handler, str):
        field_name = field_or_handler

        def decorator(fn: EventHookFunction) -> EventHookFunction:
            return _decorate_on_mouse_hook(
                fn,
                buttons=(button,),
                kind=kind,
                field=field_name,
            )

        return decorator

    if field is None:
        raise TypeError("on_click requires a field name")
    return _decorate_on_mouse_hook(
        field_or_handler,
        buttons=(button,),
        kind=kind,
        field=field,
    )


@overload
def on_tick(handler: EventHookFunction, /) -> EventHookFunction: ...
@overload
def on_tick(
    interval: int,
    /,
    *,
    interval_milliseconds: int | None = None,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
@overload
def on_tick(
    *,
    interval_milliseconds: int,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
def on_tick(
    handler_or_interval: "EventHookFunction | int | None" = None,
    /,
    *,
    interval_milliseconds: int | None = None,
) -> "EventHookFunction | Callable[[EventHookFunction], EventHookFunction]":
    """Register a tick hook, optionally at a fixed interval.

    Args:
        handler_or_interval: The handler or interval to decorate.
        interval_milliseconds: The interval in milliseconds to filter the hook function by.

    Returns:
        The decorated hook function.
    """
    if callable(handler_or_interval):
        return _decorate_on_tick_hook(handler_or_interval, 0)
    resolved = (
        int(handler_or_interval)
        if isinstance(handler_or_interval, int)
        else interval_milliseconds
    )
    if isinstance(resolved, int):
        return lambda fn: _decorate_on_tick_hook(fn, resolved)
    raise TypeError(
        "on_tick expects a callable or an interval in milliseconds"
    )


def on_event(fn: EventHookFunction) -> EventHookFunction:
    """Register an event hook that triggers on every detected terminal
    event.

    Args:
        fn: The hook function to decorate.

    Returns:
        The decorated hook function.
    """
    setattr(fn, _EventHooksRegistry.ON_EVENT_HOOK_ATTR, True)
    return _decorate_hook_function(fn)


def on_resize(fn: EventHookFunction) -> EventHookFunction:
    """Register a hook fired on terminal resize events."""
    setattr(fn, _EventHooksRegistry.ON_RESIZE_HOOK_ATTR, True)
    return _decorate_hook_function(fn)


def on_focus(fn: EventHookFunction) -> EventHookFunction:
    """Register a hook fired on terminal focus events."""
    setattr(fn, _EventHooksRegistry.ON_FOCUS_HOOK_ATTR, True)
    return _decorate_hook_function(fn)


def on_clipboard(fn: EventHookFunction) -> EventHookFunction:
    """Register a hook fired on clipboard paste events."""
    setattr(fn, _EventHooksRegistry.ON_CLIPBOARD_HOOK_ATTR, True)
    return _decorate_hook_function(fn)


def on_state(
    expression: str,
) -> Callable[[EventHookFunction], EventHookFunction]:
    """Fire the decorated handler each tick when ``expression`` is truthy
    against the current application state's attributes.

    The expression is evaluated with the state object's ``__dict__`` as local
    variables, plus ``state`` bound to the full state object. Only state field
    attributes should be referenced; the evaluation namespace is intentionally
    restricted to safe built-ins.

    Example::

        @on_state("count > 0")
        def _on_positive_count(self, ctx: Context[AppState]) -> None:
            self.counter_label = f"Count: {ctx.get_state().count}"

        @on_state("is_loading")
        def _show_spinner(self, ctx: Context[AppState]) -> None:
            self.status = "Loading…"
    """

    def decorator(fn: EventHookFunction) -> EventHookFunction:
        setattr(fn, _EventHooksRegistry.ON_STATE_HOOK_ATTR, True)
        setattr(fn, _EventHooksRegistry.ON_STATE_EXPRESSION_ATTR, expression)
        return _decorate_hook_function(fn)

    return decorator


__all__ = (
    "on_event",
    "on_resize",
    "on_focus",
    "on_clipboard",
    "on_state",
    "on_keyboard",
    "on_mouse",
    "on_click",
    "on_tick",
)
