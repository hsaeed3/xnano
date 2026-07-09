"""xnano.beta.focus

---

Field-level focus and editable ``Text`` input helpers.

Terminal focus (OS window gained/lost) stays on ``@on_focus`` without a field
name.  Field focus is the grid-field equivalent of a caret — tab order walks
``Text(input=True)`` fields in declaration order, and the focused field
receives printable keys / backspace / arrows.
"""

from __future__ import annotations

import dataclasses
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from xnano.beta.components.text import Text
    from xnano.beta.events import KeyboardEventData
    from xnano.beta.grid import Grid
    from xnano.beta.hooks import FocusHookKind
    from xnano.beta.terminal import Terminal


@dataclasses.dataclass(frozen=True, slots=True)
class FieldFocus:
    """Identity of the currently focused layout field.

    Attributes:
        grid: The grid instance that owns the field.
        field_name: Layout field name on ``grid``.
    """

    grid: Any
    field_name: str


def is_input_text(value: Any) -> bool:
    """Return whether ``value`` is an editable ``Text`` component."""
    from xnano.beta.components.text import Text

    return isinstance(value, Text) and bool(value.input)


def get_input_text(grid: Any, field_name: str) -> Text | None:
    """Return the editable ``Text`` stored on ``grid.field_name``, if any."""
    value = getattr(grid, field_name, None)
    if is_input_text(value):
        return value  # type: ignore[return-value]
    return None


def collect_focusable_fields(terminal: Terminal[Any]) -> list[FieldFocus]:
    """Collect focusable input fields in paint/declaration order.

    Walks ``terminal._attached_frame_grids`` (outer-most first, then nested
    grids as they appear during the last frame) and, for each grid, its
    ``_grid_fields`` declaration order.
    """
    result: list[FieldFocus] = []
    seen: set[tuple[int, str]] = set()
    for grid in terminal._attached_frame_grids:
        fields = getattr(type(grid), "_grid_fields", None) or getattr(
            grid, "_grid_fields", {}
        )
        for field_name in fields:
            value = getattr(grid, field_name, None)
            if is_input_text(value):
                key = (id(grid), field_name)
                if key not in seen:
                    seen.add(key)
                    result.append(
                        FieldFocus(grid=grid, field_name=field_name)
                    )
            elif hasattr(value, "_grid_fields"):
                # Nested grids are also listed in _attached_frame_grids when
                # painted; no need to recurse here.
                pass
    return result


def sync_input_focus_flags(terminal: Terminal[Any]) -> None:
    """Set ``Text._input_focused`` on every attached input to match focus."""
    current = getattr(terminal, "_field_focus", None)
    for target in collect_focusable_fields(terminal):
        text = get_input_text(target.grid, target.field_name)
        if text is None:
            continue
        text._input_focused = (
            current is not None
            and current.grid is target.grid
            and current.field_name == target.field_name
        )


def focused_input_text(terminal: Terminal[Any]) -> Text | None:
    """Return the editable ``Text`` for the current field focus, if any."""
    current = getattr(terminal, "_field_focus", None)
    if current is None:
        return None
    return get_input_text(current.grid, current.field_name)


def apply_text_keyboard(text: Text, keyboard: KeyboardEventData) -> bool:
    """Apply a keyboard event to an editable ``Text``.

    Consumes printable characters, backspace/delete, and left/right/home/end.
    Leaves tab, enter, escape, and arrows up/down for application hooks.

    Args:
        text: The input ``Text`` to mutate.
        keyboard: The keyboard sub-event.

    Returns:
        ``True`` when the event was handled (and should not fire other
        character-level keyboard hooks).
    """
    if not text.input or not isinstance(text.content, str):
        return False
    kind = keyboard.kind
    if kind is not None and kind not in ("press", "repeat"):
        return False

    content = text.content
    position = text.cursor if text.cursor is not None else len(content)
    position = max(0, min(position, len(content)))

    if keyboard.matches("backspace"):
        if position > 0:
            text.content = content[: position - 1] + content[position:]
            text.cursor = position - 1
        return True
    if keyboard.matches("delete"):
        if position < len(content):
            text.content = content[:position] + content[position + 1 :]
            text.cursor = position
        return True
    if keyboard.matches("left"):
        text.cursor = max(0, position - 1)
        return True
    if keyboard.matches("right"):
        text.cursor = min(len(content), position + 1)
        return True
    if keyboard.matches("home"):
        text.cursor = 0
        return True
    if keyboard.matches("end"):
        text.cursor = len(content)
        return True
    # Navigation / submit keys stay available to @on_keyboard hooks.
    if keyboard.matches(
        "tab",
        "backtab",
        "enter",
        "esc",
        "up",
        "down",
        "pageup",
        "pagedown",
    ):
        return False

    character = keyboard.character
    if (
        character is not None
        and len(character) == 1
        and character.isprintable()
        and character not in ("\n", "\r", "\t")
    ):
        text.content = content[:position] + character + content[position:]
        text.cursor = position + 1
        return True
    return False


def _mark_text_focused(text: Text | None, focused: bool) -> None:
    if text is not None:
        text._input_focused = focused


def set_field_focus(
    terminal: Terminal[Any],
    grid: Any,
    field_name: str,
    *,
    fire_hooks: bool = True,
) -> bool:
    """Focus ``grid.field_name`` when it holds an editable ``Text``.

    Args:
        terminal: The live terminal.
        grid: Owner grid.
        field_name: Layout field name.
        fire_hooks: Whether to fire field ``@on_focus`` handlers.

    Returns:
        ``True`` when focus was set (or already there).
    """
    text = get_input_text(grid, field_name)
    if text is None:
        return False
    previous = getattr(terminal, "_field_focus", None)
    target = FieldFocus(grid=grid, field_name=field_name)
    # Compared by identity (not ``==``) so focus tracking never depends on a
    # Grid subclass overriding equality.
    if (
        previous is not None
        and previous.grid is grid
        and previous.field_name == field_name
    ):
        _mark_text_focused(text, True)
        sync_input_focus_flags(terminal)
        return True

    if previous is not None:
        prev_text = get_input_text(previous.grid, previous.field_name)
        _mark_text_focused(prev_text, False)
        if fire_hooks:
            _fire_field_focus_hooks(terminal, previous, kind="lost")

    terminal._field_focus = target
    _mark_text_focused(text, True)
    sync_input_focus_flags(terminal)
    terminal._field_focus_announced = True

    if fire_hooks:
        _fire_field_focus_hooks(terminal, target, kind="gained")
    return True


def clear_field_focus(
    terminal: Terminal[Any],
    *,
    fire_hooks: bool = True,
) -> None:
    """Clear field focus on ``terminal``."""
    previous = getattr(terminal, "_field_focus", None)
    if previous is None:
        return
    prev_text = get_input_text(previous.grid, previous.field_name)
    _mark_text_focused(prev_text, False)
    if fire_hooks:
        _fire_field_focus_hooks(terminal, previous, kind="lost")
    terminal._field_focus = None
    terminal._field_focus_announced = False
    sync_input_focus_flags(terminal)


def cycle_field_focus(
    terminal: Terminal[Any],
    *,
    reverse: bool = False,
) -> bool:
    """Move field focus to the next (or previous) input field.

    Returns:
        ``True`` when focus moved or was established.
    """
    targets = collect_focusable_fields(terminal)
    if not targets:
        return False
    current = getattr(terminal, "_field_focus", None)
    if current is None:
        pick = targets[-1] if reverse else targets[0]
        return set_field_focus(terminal, pick.grid, pick.field_name)

    index = 0
    # Identity comparison, as in ``set_field_focus`` above.
    for i, target in enumerate(targets):
        if (
            target.grid is current.grid
            and target.field_name == current.field_name
        ):
            index = i
            break
    if reverse:
        index = (index - 1) % len(targets)
    else:
        index = (index + 1) % len(targets)
    pick = targets[index]
    return set_field_focus(terminal, pick.grid, pick.field_name)


def ensure_default_field_focus(terminal: Terminal[Any]) -> None:
    """Focus the first input field when nothing is focused yet."""
    current = getattr(terminal, "_field_focus", None)
    if current is not None:
        sync_input_focus_flags(terminal)
        # Seeded pre-paint focus still needs a one-shot ``gained`` announce.
        if not getattr(terminal, "_field_focus_announced", False):
            terminal._field_focus_announced = True
            _fire_field_focus_hooks(terminal, current, kind="gained")
        return
    targets = collect_focusable_fields(terminal)
    if targets:
        set_field_focus(
            terminal,
            targets[0].grid,
            targets[0].field_name,
            fire_hooks=True,
        )


def place_cursor_for_focus(terminal: Terminal[Any]) -> None:
    """Move the hardware cursor into the focused input field, if any."""
    current = getattr(terminal, "_field_focus", None)
    if current is None:
        return
    text = get_input_text(current.grid, current.field_name)
    if text is None or not isinstance(text.content, str):
        return
    slots = getattr(current.grid, "_grid_last_slot_areas", None) or {}
    area = slots.get(current.field_name)
    if area is None:
        return
    position = text.cursor if text.cursor is not None else len(text.content)
    position = max(0, min(position, len(text.content)))
    # Clamp caret into the painted slot width.
    column = min(position, max(0, area.width - 1))
    try:
        terminal.cursor.visible = True
        terminal.cursor.move_to(area.x + column, area.y)
    except Exception:
        pass


def _fire_field_focus_hooks(
    terminal: Terminal[Any],
    target: FieldFocus,
    *,
    kind: "FocusHookKind",
) -> None:
    from xnano.beta.context import Context
    from xnano.beta.core.dispatch import invoke_hook, resolve_hook_grid
    from xnano.beta.events import FocusEventData

    focus_data = FocusEventData(
        kind="field_gained" if kind == "gained" else "field_lost",
        field=target.field_name,
    )
    ctx = Context(event=None, terminal=terminal, state=terminal.state)
    terminal._last_field_focus_event = focus_data

    for entry in terminal._hooks.on_focus_hooks:
        field_filter = entry["field"]
        kind_filter = entry["kind"]
        handler = entry["handler"]

        if field_filter is None:
            # Terminal-only focus hooks ignore field focus transitions.
            continue
        if field_filter != target.field_name:
            continue
        if kind_filter is not None and kind_filter != kind:
            continue

        grid = target.grid
        bound = getattr(handler, "__self__", None)
        if bound is None:
            name = getattr(handler, "__name__", None)
            if name and hasattr(grid, name):
                handler = getattr(grid, name)
            else:
                resolved = resolve_hook_grid(terminal, handler)
                if resolved is not None:
                    grid = resolved
        invoke_hook(handler, grid, ctx)


__all__ = (
    "FieldFocus",
    "is_input_text",
    "get_input_text",
    "collect_focusable_fields",
    "sync_input_focus_flags",
    "focused_input_text",
    "apply_text_keyboard",
    "set_field_focus",
    "clear_field_focus",
    "cycle_field_focus",
    "ensure_default_field_focus",
    "place_cursor_for_focus",
)
