"""xnano._function_hooks

---

Registry and marker plumbing behind the public ``@on_*`` decorators in
``xnano.events``.
"""

from __future__ import annotations

import dataclasses
import functools
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    ClassVar,
    Literal,
    TypeAlias,
    TypedDict,
    TypeVar,
)

if TYPE_CHECKING:
    from xnano.context import Context
    from xnano.events import KeyboardEventKind, MouseEventKind


StateT = TypeVar("StateT")


EventHookFunction: TypeAlias = (
    Callable[..., Any | Awaitable[Any]]
    | Callable[["Context[StateT]"], Any | Awaitable[Any]]
    | Callable[["Context[StateT]", tuple[Any, ...]], Any | Awaitable[Any]]
)
"""A function that can be decorated by an ``@on_<event>`` decorator within
a grid for adding event handling.
"""


_PENDING_HOOKS: list[EventHookFunction] = []


class _OnKeyboardHookFunctionEntry(TypedDict):
    bindings: tuple[str, ...]
    kind: "KeyboardEventKind | None"
    handler: EventHookFunction


class _OnMouseHookFunctionEntry(TypedDict):
    buttons: tuple[str, ...]
    kind: "MouseEventKind | None"
    handler: EventHookFunction


class _OnTickHookFunctionEntry(TypedDict):
    interval: int
    handler: EventHookFunction
    last_fire_ms: float | None


class _OnStateHookFunctionEntry(TypedDict):
    expression: str
    handler: EventHookFunction


class _OnFieldHookFunctionEntry(TypedDict):
    expression: str
    handler: EventHookFunction


PollWhen: TypeAlias = Literal["idle", "frame"]
"""When an ``@on_poll`` hook fires.

Values:
    ``"idle"``: Fires when an event poll returns no input within the tick
        interval — an idle hook, distinct from the interval-gated ``on_tick``.
    ``"frame"``: Fires once per render-loop iteration, regardless of events.
"""


class _OnPollHookFunctionEntry(TypedDict):
    when: PollWhen
    handler: EventHookFunction


FocusHookKind: TypeAlias = Literal["gained", "lost"]
"""Whether a field ``@on_focus`` hook fires on gain, loss, or both (``None``)."""


class _OnFocusHookFunctionEntry(TypedDict):
    field: str | None
    kind: FocusHookKind | None
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
    ON_FOCUS_FIELD_ATTR: ClassVar[str] = "__xnano_on_focus_field__"
    ON_FOCUS_KIND_ATTR: ClassVar[str] = "__xnano_on_focus_kind__"
    ON_POLL_HOOK_ATTR: ClassVar[str] = "__xnano_on_poll__"
    ON_POLL_WHEN_ATTR: ClassVar[str] = "__xnano_on_poll_when__"
    ON_TICK_HOOK_ATTR: ClassVar[str] = "__xnano_on_tick__"
    ON_STATE_HOOK_ATTR: ClassVar[str] = "__xnano_on_state__"
    ON_KEYBOARD_FILTER_ATTR: ClassVar[str] = "__xnano_on_keyboard_filter__"
    ON_MOUSE_FILTER_ATTR: ClassVar[str] = "__xnano_on_mouse_filter__"
    ON_MOUSE_FIELD_ATTR: ClassVar[str] = "__xnano_on_mouse_field__"
    ON_TICK_INTERVAL_ATTR: ClassVar[str] = "__xnano_on_tick_interval__"
    ON_STATE_EXPRESSION_ATTR: ClassVar[str] = "__xnano_on_state_expression__"
    ON_FIELD_HOOK_ATTR: ClassVar[str] = "__xnano_on_field__"
    ON_FIELD_EXPRESSION_ATTR: ClassVar[str] = "__xnano_on_field_expression__"

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
    on_focus_hooks: list[_OnFocusHookFunctionEntry] = dataclasses.field(
        default_factory=list, init=False
    )
    on_poll_hooks: list[_OnPollHookFunctionEntry] = dataclasses.field(
        default_factory=list, init=False
    )
    on_tick_hooks: list[_OnTickHookFunctionEntry] = dataclasses.field(
        default_factory=list, init=False
    )
    on_state_hooks: list[_OnStateHookFunctionEntry] = dataclasses.field(
        default_factory=list, init=False
    )
    on_field_hooks: list[_OnFieldHookFunctionEntry] = dataclasses.field(
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
            self.on_focus_hooks.append(
                _OnFocusHookFunctionEntry(
                    field=getattr(handler, self.ON_FOCUS_FIELD_ATTR, None),
                    kind=getattr(handler, self.ON_FOCUS_KIND_ATTR, None),
                    handler=handler,
                )
            )
        if hasattr(handler, self.ON_POLL_HOOK_ATTR):
            when = getattr(handler, self.ON_POLL_WHEN_ATTR, "idle")
            self.on_poll_hooks.append(
                _OnPollHookFunctionEntry(when=when, handler=handler)
            )
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
                    last_fire_ms=None,
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
        if hasattr(handler, self.ON_FIELD_HOOK_ATTR):
            expression = getattr(handler, self.ON_FIELD_EXPRESSION_ATTR, "")
            self.on_field_hooks.append(
                _OnFieldHookFunctionEntry(
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
        cached = cls._get_component_class_hooks(component_class)
        registry = cls()
        registry.on_event_hooks = cached.on_event_hooks.copy()
        registry.on_keyboard_hooks = [
            entry.copy() for entry in cached.on_keyboard_hooks
        ]
        registry.on_mouse_hooks = [
            entry.copy() for entry in cached.on_mouse_hooks
        ]
        registry.on_resize_hooks = cached.on_resize_hooks.copy()
        registry.on_clipboard_hooks = cached.on_clipboard_hooks.copy()
        registry.on_focus_hooks = [
            entry.copy() for entry in cached.on_focus_hooks
        ]
        registry.on_poll_hooks = [
            entry.copy() for entry in cached.on_poll_hooks
        ]
        registry.on_tick_hooks = [
            entry.copy() for entry in cached.on_tick_hooks
        ]
        registry.on_state_hooks = [
            entry.copy() for entry in cached.on_state_hooks
        ]
        registry.on_field_hooks = [
            entry.copy() for entry in cached.on_field_hooks
        ]
        return registry

    @classmethod
    @functools.cache
    def _get_component_class_hooks(
        cls, component_class: type
    ) -> _EventHooksRegistry:
        """Collect and cache the immutable hook template for a class."""
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
            cls.ON_FIELD_HOOK_ATTR,
        )

        # A name defined on a more-derived class shadows any base definition —
        # without this, overriding a hook method registers both the override
        # and the base member, which rebind to the same bound method and fire
        # twice per event.
        seen_names: set[str] = set()
        for base in component_class.__mro__:
            if base is object:
                continue
            for name, member in base.__dict__.items():
                if not callable(member):
                    continue
                if name in seen_names:
                    continue
                seen_names.add(name)

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
                    registry.on_focus_hooks.append(
                        _OnFocusHookFunctionEntry(
                            field=getattr(
                                member, cls.ON_FOCUS_FIELD_ATTR, None
                            ),
                            kind=getattr(member, cls.ON_FOCUS_KIND_ATTR, None),
                            handler=member,
                        )
                    )
                if hasattr(member, cls.ON_POLL_HOOK_ATTR):
                    when = getattr(member, cls.ON_POLL_WHEN_ATTR, "idle")
                    registry.on_poll_hooks.append(
                        _OnPollHookFunctionEntry(when=when, handler=member)
                    )
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
                            last_fire_ms=None,
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
                if hasattr(member, cls.ON_FIELD_HOOK_ATTR):
                    expression = getattr(
                        member, cls.ON_FIELD_EXPRESSION_ATTR, ""
                    )
                    registry.on_field_hooks.append(
                        _OnFieldHookFunctionEntry(
                            expression=expression,
                            handler=member,
                        )
                    )
        return registry


HttpMethod: TypeAlias = Literal["GET", "POST"]
"""HTTP methods supported by request hooks."""


class _OnRequestHookEntry(TypedDict):
    method: HttpMethod
    path: str
    handler: EventHookFunction


@dataclasses.dataclass(slots=True)
class _RequestHooksRegistry:
    """Internal utility class for managing HTTP request hook registration
    within grids.
    """

    ON_GET_HOOK_ATTR: ClassVar[str] = "__xnano_on_get__"
    ON_POST_HOOK_ATTR: ClassVar[str] = "__xnano_on_post__"
    ON_REQUEST_PATH_ATTR: ClassVar[str] = "__xnano_on_request_path__"

    on_get_hooks: list[_OnRequestHookEntry] = dataclasses.field(
        default_factory=list, init=False
    )
    on_post_hooks: list[_OnRequestHookEntry] = dataclasses.field(
        default_factory=list, init=False
    )

    def all_hooks(self) -> list[_OnRequestHookEntry]:
        """Return GET and POST hooks in registration order.

        Returns:
            Combined list of request hook entries.
        """
        return [*self.on_get_hooks, *self.on_post_hooks]

    @classmethod
    def from_component_class(
        cls, component_class: type
    ) -> _RequestHooksRegistry:
        """Collect ``@on_get_request`` / ``@on_post_request`` hooks from a component class.

        A name defined on a more-derived class shadows any base definition,
        matching ``_EventHooksRegistry.from_component_class``.

        Args:
            component_class: The grid (or component) class to scan.

        Returns:
            A registry of collected request hooks.
        """
        cached = cls._get_component_class_hooks(component_class)
        registry = cls()
        registry.on_get_hooks = [entry.copy() for entry in cached.on_get_hooks]
        registry.on_post_hooks = [
            entry.copy() for entry in cached.on_post_hooks
        ]
        return registry

    @classmethod
    @functools.cache
    def _get_component_class_hooks(
        cls, component_class: type
    ) -> _RequestHooksRegistry:
        """Collect and cache the immutable request-hook template for a class."""
        registry = cls()
        hook_attributes = (
            cls.ON_GET_HOOK_ATTR,
            cls.ON_POST_HOOK_ATTR,
        )

        seen_names: set[str] = set()
        for base in component_class.__mro__:
            if base is object:
                continue
            for name, member in base.__dict__.items():
                if not callable(member):
                    continue
                if name in seen_names:
                    continue
                seen_names.add(name)

                is_hook_method = any(
                    hasattr(member, attribute) for attribute in hook_attributes
                )
                if name.startswith("_") and not is_hook_method:
                    continue

                path = getattr(member, cls.ON_REQUEST_PATH_ATTR, None)
                if path is None:
                    continue

                if hasattr(member, cls.ON_GET_HOOK_ATTR):
                    registry.on_get_hooks.append(
                        _OnRequestHookEntry(
                            method="GET",
                            path=path,
                            handler=member,
                        )
                    )
                if hasattr(member, cls.ON_POST_HOOK_ATTR):
                    registry.on_post_hooks.append(
                        _OnRequestHookEntry(
                            method="POST",
                            path=path,
                            handler=member,
                        )
                    )
        return registry
