"""xnano.beta.core.dispatch

---

Collect and invoke beta hook markers for terminal, web, and synthetic events.
"""

from __future__ import annotations

from typing import Any, Iterator

from xnano.beta import hooks
from xnano.beta.context import Context
from xnano.beta.utils.dispatch import invoke_hook
from xnano.beta.utils.introspection import evaluate_state_expression


def iter_grids(root: Any) -> Iterator[Any]:
    """Yield a root grid and every nested grid."""
    fields = getattr(type(root), "_grid_fields", None)
    if not isinstance(fields, dict):
        return
    yield root
    for name in fields:
        yield from iter_grids(getattr(root, name, None))


def _iter_handlers(grid: Any) -> Iterator[Any]:
    """Yield marked methods once, respecting class overrides."""
    seen: set[str] = set()
    for base in type(grid).__mro__:
        for name, member in base.__dict__.items():
            if name in seen:
                continue
            seen.add(name)
            if callable(member):
                yield getattr(grid, name)


def dispatch_event(root: Any, runtime: Any, event: Any) -> None:
    """Dispatch one event through all matching grid hooks.

    Args:
        root: Root beta grid.
        runtime: Runtime handling the event.
        event: Public beta event.
    """
    context = Context(event=event, terminal=runtime, state=runtime.state)
    for grid in iter_grids(root):
        for handler in _iter_handlers(grid):
            function = getattr(handler, "__func__", handler)
            if getattr(function, hooks.ON_EVENT_HOOK_ATTR, False):
                invoke_hook(handler, grid, context)
            if event.is_keyboard_event() and getattr(
                function, hooks.ON_KEYBOARD_HOOK_ATTR, False
            ):
                bindings, kind = getattr(
                    function,
                    hooks.ON_KEYBOARD_FILTER_ATTR,
                    ((), None),
                )
                keyboard = event.keyboard_event
                if keyboard is not None and (
                    (kind is None or keyboard.kind == kind)
                    and (not bindings or keyboard.matches(*bindings))
                ):
                    invoke_hook(handler, grid, context)
            if event.is_mouse_event() and getattr(
                function, hooks.ON_MOUSE_HOOK_ATTR, False
            ):
                buttons, kind = getattr(
                    function,
                    hooks.ON_MOUSE_FILTER_ATTR,
                    ((), None),
                )
                mouse = event.mouse_event
                expected_field = getattr(
                    function,
                    hooks.ON_MOUSE_FIELD_ATTR,
                    None,
                )
                expected_group = getattr(
                    function,
                    hooks.ON_MOUSE_GROUP_ATTR,
                    None,
                )
                if mouse is not None and (
                    (kind is None or mouse.kind == kind)
                    and (not buttons or mouse.button in buttons)
                    and (
                        expected_field is None or mouse.field == expected_field
                    )
                    and (
                        expected_group is None or mouse.group == expected_group
                    )
                ):
                    invoke_hook(handler, grid, context)
            if event.is_resize_event() and getattr(
                function,
                hooks.ON_RESIZE_HOOK_ATTR,
                False,
            ):
                invoke_hook(handler, grid, context)
            if event.is_clipboard_event() and getattr(
                function,
                hooks.ON_CLIPBOARD_HOOK_ATTR,
                False,
            ):
                invoke_hook(handler, grid, context)
            if event.is_focus_event() and getattr(
                function,
                hooks.ON_FOCUS_HOOK_ATTR,
                False,
            ):
                focus = event.focus_event
                expected = getattr(function, hooks.ON_FOCUS_KIND_ATTR, None)
                expected_field = getattr(
                    function, hooks.ON_FOCUS_FIELD_ATTR, None
                )
                expected_group = getattr(
                    function, hooks.ON_FOCUS_GROUP_ATTR, None
                )
                if (
                    focus is not None
                    and (
                        expected is None
                        or focus.kind.removeprefix("field_") == expected
                    )
                    and (
                        expected_field is None or focus.field == expected_field
                    )
                    and (
                        expected_group is None or focus.group == expected_group
                    )
                ):
                    invoke_hook(handler, grid, context)
            if event.is_tick_event() and getattr(
                function,
                hooks.ON_TICK_HOOK_ATTR,
                False,
            ):
                interval = getattr(function, hooks.ON_TICK_INTERVAL_ATTR, 0)
                key = (id(grid), getattr(function, "__name__", ""))
                last = runtime._tick_hook_times.get(key, 0)
                if interval <= 0 or runtime._elapsed_ms - last >= interval:
                    runtime._tick_hook_times[key] = runtime._elapsed_ms
                    invoke_hook(handler, grid, context)


def dispatch_idle(root: Any, runtime: Any) -> None:
    """Dispatch hooks that run when event polling returns no input."""
    context = Context(event=None, terminal=runtime, state=runtime.state)
    for grid in iter_grids(root):
        for handler in _iter_handlers(grid):
            function = getattr(handler, "__func__", handler)
            if (
                getattr(function, hooks.ON_POLL_HOOK_ATTR, False)
                and getattr(function, hooks.ON_POLL_WHEN_ATTR, "idle")
                == "idle"
            ):
                invoke_hook(handler, grid, context)


def dispatch_frame(root: Any, runtime: Any) -> None:
    """Dispatch frame poll and expression hooks before painting."""
    context = Context(event=None, terminal=runtime, state=runtime.state)
    for grid in iter_grids(root):
        for handler in _iter_handlers(grid):
            function = getattr(handler, "__func__", handler)
            if (
                getattr(function, hooks.ON_POLL_HOOK_ATTR, False)
                and getattr(function, hooks.ON_POLL_WHEN_ATTR, "idle")
                == "frame"
            ):
                invoke_hook(handler, grid, context)
            state_expression = getattr(
                function,
                hooks.ON_STATE_EXPRESSION_ATTR,
                None,
            )
            if (
                state_expression is not None
                and runtime.state is not None
                and evaluate_state_expression(state_expression, runtime.state)
            ):
                invoke_hook(handler, grid, context)
            field_expression = getattr(
                function,
                hooks.ON_FIELD_EXPRESSION_ATTR,
                None,
            )
            if field_expression is not None and evaluate_state_expression(
                field_expression, grid
            ):
                invoke_hook(handler, grid, context)


__all__ = ("dispatch_event", "dispatch_frame", "dispatch_idle", "iter_grids")
