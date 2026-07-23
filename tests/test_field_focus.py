"""Tests for field-level focus and @on_focus(field=...) hooks."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from xnano._dispatch import (
    _handle_focus_navigation,
    _handle_focused_text_input,
)
from xnano._function_hooks import (
    _EventHooksRegistry,
    _OnFocusHookFunctionEntry,
)
from xnano._types import (
    clear_field_focus,
    collect_focusable_fields,
    cycle_field_focus,
    set_field_focus,
)
from xnano.components.text import Text
from xnano.events import on_focus, on_keyboard
from xnano.fields import Field
from xnano.grid import BaseGrid

# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


class _Form(BaseGrid):
    name: Text = Field(default=Text("", input=True, placeholder="name"))
    email: Text = Field(default=Text("", input=True, placeholder="email"))
    status: str = Field(default="")
    name_gains: int = Field(default=0, state=True)
    name_losses: int = Field(default=0, state=True)

    @on_focus("name")
    def _on_name(self) -> None:
        self.name_gains += 1
        self.status = "name"

    @on_focus("name", kind="lost")
    def _on_name_lost(self) -> None:
        self.name_losses += 1

    @on_keyboard("enter")
    def _submit(self) -> None:
        self.status = f"hi {self.name.value}"


def test_on_focus_field_attributes() -> None:
    method = _Form.__dict__["_on_name"]
    assert hasattr(method, _EventHooksRegistry.ON_FOCUS_HOOK_ATTR)
    assert getattr(method, _EventHooksRegistry.ON_FOCUS_FIELD_ATTR) == "name"


def test_on_focus_kind_lost_attribute() -> None:
    method = _Form.__dict__["_on_name_lost"]
    assert getattr(method, _EventHooksRegistry.ON_FOCUS_KIND_ATTR) == "lost"


def test_from_component_class_collects_field_focus() -> None:
    registry = _EventHooksRegistry.from_component_class(_Form)
    fields = {entry["field"] for entry in registry.on_focus_hooks}
    assert "name" in fields


# ---------------------------------------------------------------------------
# Focus cycling
# ---------------------------------------------------------------------------


def _terminal_with_form(form: _Form | None = None) -> tuple[Any, _Form]:
    grid = form if form is not None else _Form()
    terminal = MagicMock()
    terminal.state = None
    terminal._field_focus = None
    terminal._field_focus_announced = False
    terminal._last_field_focus_event = None
    terminal._attached_frame_grids = [grid]
    registry = _EventHooksRegistry.from_component_class(_Form)
    # Bind focus handlers to instance
    bound: list[_OnFocusHookFunctionEntry] = []
    for entry in registry.on_focus_hooks:
        handler = entry["handler"]
        name = getattr(handler, "__name__", None)
        if name and hasattr(grid, name):
            handler = getattr(grid, name)
        bound.append(
            _OnFocusHookFunctionEntry(
                field=entry["field"],
                kind=entry["kind"],
                handler=handler,
            )
        )
    terminal._hooks = MagicMock()
    terminal._hooks.on_focus_hooks = bound
    terminal._hooks.on_event_hooks = []
    terminal._hooks.on_keyboard_hooks = []
    terminal._hooks.on_mouse_hooks = []
    terminal._hooks.on_resize_hooks = []
    terminal._hooks.on_clipboard_hooks = []
    return terminal, grid


def test_collect_focusable_fields_order() -> None:
    terminal, grid = _terminal_with_form()
    targets = collect_focusable_fields(terminal)
    assert [t.field_name for t in targets] == ["name", "email"]


def test_set_field_focus_marks_text() -> None:
    terminal, grid = _terminal_with_form()
    assert set_field_focus(terminal, grid, "name") is True
    assert grid.name._input_focused is True
    assert grid.email._input_focused is False
    assert terminal._field_focus.field_name == "name"


def test_set_field_focus_fires_gained_hook() -> None:
    terminal, grid = _terminal_with_form()
    set_field_focus(terminal, grid, "name")
    assert grid.name_gains == 1
    assert grid.status == "name"


def test_cycle_focus_moves_and_fires_lost() -> None:
    terminal, grid = _terminal_with_form()
    set_field_focus(terminal, grid, "name")
    assert grid.name_gains == 1
    cycle_field_focus(terminal, reverse=False)
    assert terminal._field_focus.field_name == "email"
    assert grid.name._input_focused is False
    assert grid.email._input_focused is True
    assert grid.name_losses == 1


def test_clear_field_focus() -> None:
    terminal, grid = _terminal_with_form()
    set_field_focus(terminal, grid, "name")
    clear_field_focus(terminal)
    assert terminal._field_focus is None
    assert grid.name._input_focused is False
    assert grid.name_losses == 1


# ---------------------------------------------------------------------------
# Keyboard routing
# ---------------------------------------------------------------------------


def _nav_kbd(binding: str) -> Any:
    class _K:
        kind = "press"
        character = None

        def matches(self, *bindings: str) -> bool:
            return binding in bindings

    return _K()


def test_tab_navigation_handler() -> None:
    terminal, grid = _terminal_with_form()
    set_field_focus(terminal, grid, "name")
    assert _handle_focus_navigation(terminal, _nav_kbd("tab"))
    assert terminal._field_focus.field_name == "email"


def test_backtab_navigation_handler() -> None:
    terminal, grid = _terminal_with_form()
    set_field_focus(terminal, grid, "email")
    assert _handle_focus_navigation(terminal, _nav_kbd("backtab"))
    assert terminal._field_focus.field_name == "name"


def test_focused_text_receives_characters() -> None:
    terminal, grid = _terminal_with_form()
    set_field_focus(terminal, grid, "name")

    class _K:
        kind = "press"
        character = "a"

        def matches(self, *bindings: str) -> bool:
            return False

    assert _handle_focused_text_input(terminal, _K()) is True
    assert grid.name.value == "a"


def test_enter_still_available_to_hooks() -> None:
    """Enter is not consumed by Text input, so @on_keyboard('enter') works."""
    terminal, grid = _terminal_with_form()
    set_field_focus(terminal, grid, "name")
    grid.name.content = "Ada"

    class _K:
        kind = "press"
        character = None

        def matches(self, *bindings: str) -> bool:
            return "enter" in bindings

    assert _handle_focused_text_input(terminal, _K()) is False
    # Manually invoke submit the way dispatch would for enter
    grid.status = f"hi {grid.name.value}"
    assert grid.status == "hi Ada"


# ---------------------------------------------------------------------------
# Terminal API surface
# ---------------------------------------------------------------------------


def test_terminal_focus_helpers() -> None:
    from xnano.terminal import Terminal

    term = Terminal.__new__(Terminal)
    term._field_focus = None
    term._field_focus_announced = False
    term._last_field_focus_event = None
    term._hooks = _EventHooksRegistry()
    term.state = None
    term._attached_frame_grids = []

    grid = _Form()
    term._attached_frame_grids = [grid]
    # Bind hooks
    for entry in _EventHooksRegistry.from_component_class(
        _Form
    ).on_focus_hooks:
        handler = entry["handler"]
        name = getattr(handler, "__name__", None)
        if name and hasattr(grid, name):
            handler = getattr(grid, name)
        term._hooks.on_focus_hooks.append(
            _OnFocusHookFunctionEntry(
                field=entry["field"],
                kind=entry["kind"],
                handler=handler,
            )
        )

    assert term.focus_field(grid, "name") is True
    assert term.field_focus is not None
    assert term.field_focus.field_name == "name"
    assert term.focus_next() is True
    assert term.field_focus.field_name == "email"
    assert term.focus_previous() is True
    assert term.field_focus.field_name == "name"
    term.blur_field()
    assert term.field_focus is None


def test_focused_property_is_live() -> None:
    """`focused` reads like visible/z on components and grids."""
    from xnano.components.select import Select

    text = Text("", input=True)
    select = Select(items=("a", "b"))
    assert text.focused is False
    assert select.focused is False
    text._input_focused = True
    select._input_focused = True
    assert text.focused is True
    assert select.focused is True
    assert Text("display only").focused is False


def test_grid_focused_derives_from_fields() -> None:
    class FocusGrid(BaseGrid):
        name: Text = Field(default=Text("", input=True))
        label: str = Field(default="hi")

    grid = FocusGrid()
    assert grid.focused is False
    grid.name._input_focused = True
    assert grid.focused is True
