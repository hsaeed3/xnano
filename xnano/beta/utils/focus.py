"""xnano.beta.utils.focus

---

Discover, move, and synchronize focus across beta grid fields.
"""

from __future__ import annotations

from typing import Any

from xnano.beta.types import (
    FieldFocus,
    ScrollHandle,
    is_component,
    is_focusable_component,
    uses_default_component_size,
)


def get_focusable_component(grid: Any, field_name: str) -> Any | None:
    """Return a focusable component stored in one grid field."""
    value = getattr(grid, field_name, None)
    return value if is_focusable_component(value) else None


def field_group(grid: Any, field_name: str) -> str | None:
    """Return the configured group for a grid field."""
    info = getattr(grid, "_grid_field_info", lambda name: None)(field_name)
    return None if info is None else info.group


def _walk_grids(root: Any):
    """Yield a grid and its nested grid field values."""
    if not isinstance(getattr(type(root), "_grid_fields", None), dict):
        return
    yield root
    for name in root._grid_fields:
        child = getattr(root, name, None)
        yield from _walk_grids(child)


def collect_focusable_fields(terminal: Any) -> list[FieldFocus]:
    """Collect focusable fields from the runtime's root grid."""
    root = getattr(terminal, "_root", None)
    targets: list[FieldFocus] = []
    for grid in _walk_grids(root):
        for name, info in grid._grid_fields.items():
            component = get_focusable_component(grid, name)
            if component is not None or info.autofocus or info.group:
                targets.append(
                    FieldFocus(
                        grid=grid,
                        field_name=name,
                        group=info.group,
                    )
                )
    return targets


def collect_group_targets(terminal: Any) -> dict[str, FieldFocus]:
    """Map focus group names to their first matching field."""
    return {
        target.group: target
        for target in collect_focusable_fields(terminal)
        if target.group is not None
    }


def resolve_group_target(terminal: Any, group: str) -> FieldFocus | None:
    """Return the field targeted by a focus group."""
    return collect_group_targets(terminal).get(group)


def set_field_focus(
    terminal: Any,
    target: FieldFocus | None,
    *,
    fire_hooks: bool = True,
) -> bool:
    """Set the focused field and synchronize component flags."""
    del fire_hooks
    current = getattr(terminal, "_field_focus", None)
    if current == target:
        return False
    setattr(terminal, "_field_focus", target)
    sync_input_focus_flags(terminal)
    if target is not None:
        setattr(terminal, "_focused_group", target.group)
    return True


def clear_field_focus(terminal: Any, *, fire_hooks: bool = True) -> bool:
    """Clear the active field focus."""
    return set_field_focus(terminal, None, fire_hooks=fire_hooks)


def focus_group(terminal: Any, group: str) -> bool:
    """Focus the field registered for a group."""
    target = resolve_group_target(terminal, group)
    return False if target is None else set_field_focus(terminal, target)


def focused_group_name(terminal: Any) -> str | None:
    """Return the focused field's group name."""
    target = getattr(terminal, "_field_focus", None)
    return None if target is None else target.group


def is_group_focused(terminal: Any, group: str) -> bool:
    """Return whether a focus group is active."""
    return focused_group_name(terminal) == group


def focused_component(terminal: Any) -> Any | None:
    """Return the component inside the focused field."""
    target = getattr(terminal, "_field_focus", None)
    if target is None:
        return None
    return get_focusable_component(target.grid, target.field_name)


def sync_input_focus_flags(terminal: Any) -> None:
    """Synchronize component and field-state focus flags."""
    active = getattr(terminal, "_field_focus", None)
    for target in collect_focusable_fields(terminal):
        focused = target == active
        component = getattr(target.grid, target.field_name, None)
        if is_component(component):
            setattr(component, "_input_focused", focused)
        state = target.grid.get_field_state(target.field_name)
        if state is not None:
            state.focused = focused


def cycle_field_focus(terminal: Any, step: int = 1) -> bool:
    """Move focus forward or backward through focusable fields."""
    targets = collect_focusable_fields(terminal)
    if not targets:
        return False
    current = getattr(terminal, "_field_focus", None)
    index = targets.index(current) if current in targets else -1
    return set_field_focus(terminal, targets[(index + step) % len(targets)])


def ensure_default_field_focus(terminal: Any) -> None:
    """Apply autofocus or select the first focusable field."""
    if getattr(terminal, "_field_focus", None) is not None:
        return
    targets = collect_focusable_fields(terminal)
    target = next(
        (
            item
            for item in targets
            if getattr(
                item.grid._grid_field_info(item.field_name),
                "autofocus",
                False,
            )
        ),
        targets[0] if targets else None,
    )
    if target is not None:
        set_field_focus(terminal, target, fire_hooks=False)


def apply_text_keyboard(text: Any, keyboard: Any) -> bool:
    """Send keyboard input to a focused text component."""
    handler = getattr(text, "handle_keyboard", None)
    return bool(handler(keyboard)) if callable(handler) else False


def place_cursor_for_focus(terminal: Any) -> None:
    """Place the cursor using the focused component's cursor hint."""
    component = focused_component(terminal)
    position = getattr(component, "cursor_position", None)
    if component is not None and position is not None:
        terminal.cursor.position = position


def scroll_handle_for_group(
    terminal: Any,
    group: str,
) -> ScrollHandle | None:
    """Return mutable scroll state for a grouped scroll field."""
    target = resolve_group_target(terminal, group)
    if target is None:
        return None
    handles = getattr(target.grid, "_grid_scroll_handles", None)
    if handles is None:
        handles = {}
        object.__setattr__(target.grid, "_grid_scroll_handles", handles)
    info = target.grid._grid_field_info(target.field_name)
    axis = "x" if info.scroll == "horizontal" else "y"
    return handles.setdefault(group, ScrollHandle(group=group, axis=axis))


__all__ = (
    "apply_text_keyboard",
    "clear_field_focus",
    "collect_focusable_fields",
    "collect_group_targets",
    "cycle_field_focus",
    "ensure_default_field_focus",
    "field_group",
    "focus_group",
    "focused_component",
    "focused_group_name",
    "get_focusable_component",
    "is_component",
    "is_focusable_component",
    "is_group_focused",
    "place_cursor_for_focus",
    "resolve_group_target",
    "scroll_handle_for_group",
    "set_field_focus",
    "sync_input_focus_flags",
    "uses_default_component_size",
)
