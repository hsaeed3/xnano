"""xnano.beta.hooks

---

Handle events by decorating methods on a ``BaseGrid`` subclass::

    from xnano.beta import hooks

    @hooks.on_keyboard("q")
    def quit(self, ctx): ...
"""

from __future__ import annotations

from typing import Any, Callable, Literal, TypeAlias, overload

from xnano.beta.types import KeyboardBinding, MouseButton

EventHookFunction: TypeAlias = Callable[..., Any]

KeyboardEventKind: TypeAlias = Literal["press", "release", "repeat"]
"""The kind of keyboard event a handler filters by.

Values:
    ``"press"``: A key was pressed down.
    ``"release"``: A key was released.
    ``"repeat"``: A key was held down and is repeating.
"""

MouseEventKind: TypeAlias = Literal[
    "press",
    "release",
    "drag",
    "move",
    "scroll_up",
    "scroll_down",
    "scroll_left",
    "scroll_right",
]
"""The kind of mouse event a handler filters by."""

FocusHookKind: TypeAlias = Literal["gained", "lost"]
"""Which half of a focus transition a handler fires on."""

PollWhen: TypeAlias = Literal["idle", "frame"]
"""When a poll hook fires — once per idle event wait, or every frame."""

# Marker attribute names — must match stable's ``_EventHooksRegistry``
# constants exactly, since the shared ``BaseGrid`` metaclass collects
# hooks by these strings regardless of which module set them.
ON_EVENT_HOOK_ATTR = "__xnano_on_event__"
ON_KEYBOARD_HOOK_ATTR = "__xnano_on_keyboard__"
ON_KEYBOARD_FILTER_ATTR = "__xnano_on_keyboard_filter__"
ON_MOUSE_HOOK_ATTR = "__xnano_on_mouse__"
ON_MOUSE_FILTER_ATTR = "__xnano_on_mouse_filter__"
ON_MOUSE_FIELD_ATTR = "__xnano_on_mouse_field__"
ON_MOUSE_GROUP_ATTR = "__xnano_on_mouse_group__"
ON_RESIZE_HOOK_ATTR = "__xnano_on_resize__"
ON_CLIPBOARD_HOOK_ATTR = "__xnano_on_clipboard__"
ON_FOCUS_HOOK_ATTR = "__xnano_on_focus__"
ON_FOCUS_FIELD_ATTR = "__xnano_on_focus_field__"
ON_FOCUS_GROUP_ATTR = "__xnano_on_focus_group__"
ON_FOCUS_KIND_ATTR = "__xnano_on_focus_kind__"
ON_POLL_HOOK_ATTR = "__xnano_on_poll__"
ON_POLL_WHEN_ATTR = "__xnano_on_poll_when__"
ON_TICK_HOOK_ATTR = "__xnano_on_tick__"
ON_TICK_INTERVAL_ATTR = "__xnano_on_tick_interval__"
ON_STATE_HOOK_ATTR = "__xnano_on_state__"
ON_STATE_EXPRESSION_ATTR = "__xnano_on_state_expression__"
ON_FIELD_HOOK_ATTR = "__xnano_on_field__"
ON_FIELD_EXPRESSION_ATTR = "__xnano_on_field_expression__"

_MOUSE_KINDS_WITH_BUTTON = frozenset({"press", "release", "drag"})
"""``MouseEventKind`` values that carry a real pressed button.

``move`` and the ``scroll_*`` kinds always report no button on the
native side, so a button filter would never match them.
"""


def _decorate_hook_function(fn: EventHookFunction) -> EventHookFunction:
    """Return a marked grid hook without wrapping it."""
    return fn


def _decorate_on_tick_hook(
    fn: EventHookFunction, interval: int
) -> EventHookFunction:
    setattr(fn, ON_TICK_HOOK_ATTR, True)
    setattr(fn, ON_TICK_INTERVAL_ATTR, interval)
    return _decorate_hook_function(fn)


def _decorate_on_mouse_hook(
    fn: EventHookFunction,
    *,
    buttons: tuple[str, ...] = (),
    kind: MouseEventKind | None = None,
    field: str | None = None,
    group: str | None = None,
) -> EventHookFunction:
    selected_kind: MouseEventKind | None = (
        kind if kind is not None else "press"
    )
    if buttons:
        selected_buttons = buttons
    elif selected_kind in _MOUSE_KINDS_WITH_BUTTON:
        selected_buttons = ("left",)
    else:
        selected_buttons = ()
    setattr(fn, ON_MOUSE_HOOK_ATTR, True)
    setattr(fn, ON_MOUSE_FILTER_ATTR, (selected_buttons, selected_kind))
    if field is not None:
        setattr(fn, ON_MOUSE_FIELD_ATTR, field)
    if group is not None:
        setattr(fn, ON_MOUSE_GROUP_ATTR, group)
    return _decorate_hook_function(fn)


@overload
def on_keyboard(
    key: KeyboardBinding,
    /,
    *keys: KeyboardBinding,
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
    """Register a keyboard event hook.

    Example:
        @on_keyboard("q")
        def quit(self, ctx): ...

        @on_keyboard("enter", kind="press")
        def submit(self): ...
    """
    if callable(handler_or_key):
        bindings: tuple[KeyboardBinding, ...] = (
            (key,) if key is not None else keys
        )
        setattr(handler_or_key, ON_KEYBOARD_HOOK_ATTR, True)
        setattr(handler_or_key, ON_KEYBOARD_FILTER_ATTR, (bindings, kind))
        return _decorate_hook_function(handler_or_key)

    if handler_or_key is not None:
        keys = (handler_or_key, *keys)  # type: ignore[assignment]
    elif key is not None:
        keys = (key, *keys)
    filter_spec = (keys, kind)

    def decorator(fn: EventHookFunction) -> EventHookFunction:
        setattr(fn, ON_KEYBOARD_HOOK_ATTR, True)
        setattr(fn, ON_KEYBOARD_FILTER_ATTR, filter_spec)
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

    Defaults to left-button press when ``button`` and ``kind`` are
    omitted. Pass ``field`` to bind to a grid layout field's region.
    """
    if callable(handler_or_button):
        selected: tuple[MouseButton, ...] = (
            (button,) if button is not None else buttons
        )
        return _decorate_on_mouse_hook(
            handler_or_button, buttons=selected, kind=kind, field=field
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
@overload
def on_click(
    *,
    group: str,
    button: MouseButton = "left",
    kind: MouseEventKind = "press",
) -> Callable[[EventHookFunction], EventHookFunction]: ...
def on_click(
    field_or_handler: "str | EventHookFunction | None" = None,
    /,
    *,
    field: str | None = None,
    group: str | None = None,
    button: MouseButton = "left",
    kind: MouseEventKind = "press",
) -> "EventHookFunction | Callable[[EventHookFunction], EventHookFunction]":
    """Register a click handler for a grid layout field, or a group.

    A field-scoped handler binds to one field on the declaring grid
    class. A group-scoped handler fires whenever any field sharing
    ``group`` is clicked, regardless of which grid it lives on — see
    ``Field(group=...)``.

    Example:
        @on_click("body")
        def highlight_body(self, ctx): ...

        @on_click(group="composer")
        def focus_composer(self, ctx): ctx.focus("composer")
    """
    if isinstance(field_or_handler, str):
        field_name = field_or_handler

        def decorator(fn: EventHookFunction) -> EventHookFunction:
            return _decorate_on_mouse_hook(
                fn, buttons=(button,), kind=kind, field=field_name
            )

        return decorator

    if field_or_handler is None:
        if group is None and field is None:
            raise TypeError("on_click requires a field name or a group")

        def group_decorator(fn: EventHookFunction) -> EventHookFunction:
            return _decorate_on_mouse_hook(
                fn, buttons=(button,), kind=kind, field=field, group=group
            )

        return group_decorator

    if field is None and group is None:
        raise TypeError("on_click requires a field name or a group")
    return _decorate_on_mouse_hook(
        field_or_handler,
        buttons=(button,),
        kind=kind,
        field=field,
        group=group,
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
    """Register a tick hook, optionally at a fixed interval."""
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
    """Register an event hook that triggers on every detected event."""
    setattr(fn, ON_EVENT_HOOK_ATTR, True)
    return _decorate_hook_function(fn)


def on_resize(fn: EventHookFunction) -> EventHookFunction:
    """Register a hook fired on terminal resize events."""
    setattr(fn, ON_RESIZE_HOOK_ATTR, True)
    return _decorate_hook_function(fn)


@overload
def on_focus(handler: EventHookFunction, /) -> EventHookFunction: ...
@overload
def on_focus(
    field: str,
    /,
    *,
    kind: FocusHookKind | None = None,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
@overload
def on_focus(
    *,
    field: str | None = None,
    group: str | None = None,
    kind: FocusHookKind | None = None,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
def on_focus(
    handler_or_field: "EventHookFunction | str | None" = None,
    /,
    *,
    field: str | None = None,
    group: str | None = None,
    kind: FocusHookKind | None = None,
) -> "EventHookFunction | Callable[[EventHookFunction], EventHookFunction]":
    """Register a focus hook for the terminal window, a field, or a group.

    Bare ``@on_focus`` fires on OS-level terminal focus gained/lost.
    Pass a field name for application field focus; pass ``group=`` to
    listen across grids — see ``Field(group=...)``.
    """

    def _decorate(
        fn: EventHookFunction,
        *,
        field_name: str | None,
        group_name: str | None,
        focus_kind: FocusHookKind | None,
    ) -> EventHookFunction:
        setattr(fn, ON_FOCUS_HOOK_ATTR, True)
        if field_name is not None:
            setattr(fn, ON_FOCUS_FIELD_ATTR, field_name)
        if group_name is not None:
            setattr(fn, ON_FOCUS_GROUP_ATTR, group_name)
        if focus_kind is not None:
            setattr(fn, ON_FOCUS_KIND_ATTR, focus_kind)
        return _decorate_hook_function(fn)

    if callable(handler_or_field):
        return _decorate(
            handler_or_field,
            field_name=field,
            group_name=group,
            focus_kind=kind,
        )

    resolved_field = (
        handler_or_field if isinstance(handler_or_field, str) else field
    )

    def decorator(fn: EventHookFunction) -> EventHookFunction:
        return _decorate(
            fn, field_name=resolved_field, group_name=group, focus_kind=kind
        )

    return decorator


def on_clipboard(fn: EventHookFunction) -> EventHookFunction:
    """Register a hook fired on clipboard paste events."""
    setattr(fn, ON_CLIPBOARD_HOOK_ATTR, True)
    return _decorate_hook_function(fn)


def on_state(
    expression: str,
) -> Callable[[EventHookFunction], EventHookFunction]:
    """Fire the decorated handler based on the application state.

    Pass an expression (``"count > 0"``) to fire each frame it is truthy
    against the state's attributes. Pass a bare reference (``"count"``,
    ``"user.name"``) to fire only when that value is *mutated* — once per
    change rather than every frame.

    Example:
        @on_state("count > 0")
        def _on_positive_count(self, ctx): ...

        @on_state("count")
        def _on_count_changed(self, ctx): ...
    """

    def decorator(fn: EventHookFunction) -> EventHookFunction:
        setattr(fn, ON_STATE_HOOK_ATTR, True)
        setattr(fn, ON_STATE_EXPRESSION_ATTR, expression)
        return _decorate_hook_function(fn)

    return decorator


def on_field(
    expression: str,
) -> Callable[[EventHookFunction], EventHookFunction]:
    """Fire the decorated handler based on this grid's own field values.

    Pass an expression (``"count > 0"``) to fire each frame it is truthy
    against the grid's fields. Pass a bare reference (``"count"``,
    ``"items[0]"``) to fire only when that field is *mutated* — once per
    change rather than every frame.

    Example:
        @on_field("count > 0")
        def _show_count(self): ...

        @on_field("count")
        def _on_count_changed(self): ...
    """

    def decorator(fn: EventHookFunction) -> EventHookFunction:
        setattr(fn, ON_FIELD_HOOK_ATTR, True)
        setattr(fn, ON_FIELD_EXPRESSION_ATTR, expression)
        return _decorate_hook_function(fn)

    return decorator


@overload
def on_poll(handler: EventHookFunction, /) -> EventHookFunction: ...
@overload
def on_poll(
    when: PollWhen = "idle",
    /,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
@overload
def on_poll(
    *,
    when: PollWhen,
) -> Callable[[EventHookFunction], EventHookFunction]: ...
def on_poll(
    handler_or_when: "EventHookFunction | PollWhen | None" = None,
    /,
    *,
    when: PollWhen | None = None,
) -> "EventHookFunction | Callable[[EventHookFunction], EventHookFunction]":
    """Register a poll hook that fires on idle event waits or every frame."""

    def _validate_when(resolved_when: PollWhen) -> None:
        if resolved_when not in ("idle", "frame"):
            raise TypeError(
                "on_poll expects when='idle' or when='frame', got "
                f"{resolved_when!r}"
            )

    def _decorate(
        fn: EventHookFunction, resolved_when: PollWhen
    ) -> EventHookFunction:
        _validate_when(resolved_when)
        setattr(fn, ON_POLL_HOOK_ATTR, True)
        setattr(fn, ON_POLL_WHEN_ATTR, resolved_when)
        return _decorate_hook_function(fn)

    if callable(handler_or_when):
        return _decorate(handler_or_when, when if when is not None else "idle")

    resolved: PollWhen
    if handler_or_when is not None:
        resolved = handler_or_when
    elif when is not None:
        resolved = when
    else:
        resolved = "idle"

    _validate_when(resolved)

    def decorator(fn: EventHookFunction) -> EventHookFunction:
        return _decorate(fn, resolved)

    return decorator


def on_action(
    action: Any,
    /,
) -> Callable[[EventHookFunction], EventHookFunction]:
    """Bind a prebuilt ``Action`` as a hook trigger.

    User-facing sugar for storing an Action on a handler:

        SAVE = Action.keyboard("ctrl+s")

        @on_action(SAVE)
        def save(self, ctx): ...
    """
    from xnano.beta.actions import (
        ClickAction,
        ClipboardAction,
        FocusAction,
        KeyboardAction,
        MouseAction,
        ResizeAction,
        TickAction,
    )

    def decorator(fn: EventHookFunction) -> EventHookFunction:
        if isinstance(action, KeyboardAction):
            setattr(fn, ON_KEYBOARD_HOOK_ATTR, True)
            setattr(
                fn, ON_KEYBOARD_FILTER_ATTR, (action.bindings, action.kind)
            )
        elif isinstance(action, ClickAction):
            return _decorate_on_mouse_hook(
                fn, buttons=(action.button,), kind="press", field=action.field
            )
        elif isinstance(action, MouseAction):
            return _decorate_on_mouse_hook(
                fn, buttons=tuple(action.buttons), kind=action.kind
            )
        elif isinstance(action, FocusAction):
            setattr(fn, ON_FOCUS_HOOK_ATTR, True)
            setattr(fn, ON_FOCUS_FIELD_ATTR, action.field)
            setattr(fn, ON_FOCUS_KIND_ATTR, action.kind)
        elif isinstance(action, ClipboardAction):
            setattr(fn, ON_CLIPBOARD_HOOK_ATTR, True)
        elif isinstance(action, ResizeAction):
            setattr(fn, ON_RESIZE_HOOK_ATTR, True)
        elif isinstance(action, TickAction):
            return _decorate_on_tick_hook(fn, action.interval_ms)
        else:
            raise TypeError(
                f"@on_action expects an Action instance, got {type(action)!r}"
            )
        return _decorate_hook_function(fn)

    return decorator


__all__ = (
    "FocusHookKind",
    "KeyboardEventKind",
    "MouseEventKind",
    "PollWhen",
    "on_action",
    "on_click",
    "on_clipboard",
    "on_event",
    "on_field",
    "on_focus",
    "on_keyboard",
    "on_mouse",
    "on_poll",
    "on_resize",
    "on_state",
    "on_tick",
)
