"""xnano.beta.core.dispatch

---

Collect and invoke beta hook markers for terminal, web, and synthetic events.
"""

from __future__ import annotations

from typing import Any, Iterator

from xnano.beta import hooks
from xnano.beta.context import Context
from xnano.beta.utils.dispatch import invoke_hook
from xnano.beta.utils.introspection import (
    _MISSING,
    evaluate_reference_value,
    evaluate_state_expression,
    is_reference_expression,
)


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


def dispatch_post_init(root: Any, runtime: Any) -> None:
    """Fire ``grid_post_init`` once per grid instance in the tree.

    Runs the first time each grid is seen by a live or offscreen runtime,
    after its hooks are bound and before its first paint — the beta
    counterpart to the main API's per-instance ``track_frame_grid`` call.
    """
    fired = runtime._post_init_grids
    context = Context(event=None, terminal=runtime, state=runtime.state)
    for grid in iter_grids(root):
        if grid is None or id(grid) in fired:
            continue
        fired.add(id(grid))
        handler = getattr(grid, "grid_post_init", None)
        if callable(handler):
            invoke_hook(handler, None, context)


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


def _expression_hook_fires(
    runtime: Any,
    grid: Any,
    function: Any,
    kind: str,
    expression: str,
    target: Any,
) -> bool:
    """Return whether a state/field expression hook should fire this frame.

    A bare reference (``@on_state("count")``) fires whenever the watched
    value is *mutated*: the current value is compared against the last one
    seen for this hook, and a difference triggers exactly once. Anything
    with computation (``count > 0``) keeps the truthiness semantics, firing
    every frame the expression holds.
    """
    if not is_reference_expression(expression):
        return evaluate_state_expression(expression, target)
    current = evaluate_reference_value(expression, target)
    if current is _MISSING:
        return False
    key = (id(grid), getattr(function, "__name__", ""), kind)
    watched = runtime._watch_values
    previous = watched.get(key, _MISSING)
    watched[key] = current
    # First observation establishes a baseline without firing — nothing
    # has been mutated yet.
    return previous is not _MISSING and current != previous


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
            if state_expression is not None and runtime.state is not None:
                if _expression_hook_fires(
                    runtime,
                    grid,
                    function,
                    "state",
                    state_expression,
                    runtime.state,
                ):
                    invoke_hook(handler, grid, context)
            field_expression = getattr(
                function,
                hooks.ON_FIELD_EXPRESSION_ATTR,
                None,
            )
            if field_expression is not None and _expression_hook_fires(
                runtime, grid, function, "field", field_expression, grid
            ):
                invoke_hook(handler, grid, context)


__all__ = (
    "dispatch_event",
    "dispatch_frame",
    "dispatch_idle",
    "dispatch_post_init",
    "iter_grids",
)
