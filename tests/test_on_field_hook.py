"""Tests for the @on_field hook decorator."""

from __future__ import annotations

import dataclasses
from typing import Any, cast

from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.events import on_field
from xnano._function_hooks import (
    _EventHooksRegistry,
    _OnFieldHookFunctionEntry,
)
from xnano.context import Context
from xnano._dispatch import pump_tick
from xnano._introspection import evaluate_state_expression


# ---------------------------------------------------------------------------
# Decorator registration
# ---------------------------------------------------------------------------


class _SimpleLabelGrid(BaseGrid):
    label: str = Field(default="initial")
    active: bool = Field(default=False, state=True)
    fired: bool = Field(default=False, state=True)

    @on_field("active")
    def _on_active(self) -> None:
        self.fired = True


def test_on_field_sets_hook_attribute() -> None:
    method = _SimpleLabelGrid.__dict__["_on_active"]
    assert hasattr(method, _EventHooksRegistry.ON_FIELD_HOOK_ATTR)


def test_on_field_sets_expression_attribute() -> None:
    method = _SimpleLabelGrid.__dict__["_on_active"]
    expression = getattr(method, _EventHooksRegistry.ON_FIELD_EXPRESSION_ATTR)
    assert expression == "active"


def test_from_component_class_collects_on_field_hook() -> None:
    registry = _EventHooksRegistry.from_component_class(_SimpleLabelGrid)
    assert len(registry.on_field_hooks) == 1
    entry: _OnFieldHookFunctionEntry = registry.on_field_hooks[0]
    assert entry["expression"] == "active"


# ---------------------------------------------------------------------------
# evaluate_state_expression against a grid instance
# ---------------------------------------------------------------------------


def test_evaluate_against_grid_simple_bool_field() -> None:
    grid = _SimpleLabelGrid()
    assert not evaluate_state_expression("active", grid)
    grid.active = True
    assert evaluate_state_expression("active", grid)


def test_evaluate_against_grid_string_comparison() -> None:
    grid = _SimpleLabelGrid()
    grid.label = "hello"
    assert evaluate_state_expression("label == 'hello'", grid)
    assert not evaluate_state_expression("label == 'world'", grid)


# ---------------------------------------------------------------------------
# Dict-valued state field (matches the test.py scenario)
# ---------------------------------------------------------------------------


class _NameSwitcherGrid(BaseGrid):
    config: dict[str, Any] = Field(default_factory=dict, state=True)
    current_text: str = Field(default="choose a name")
    john_fired: bool = Field(default=False, state=True)
    jane_fired: bool = Field(default=False, state=True)

    def __post_init__(self) -> None:
        self.config["name"] = "nobody"

    @on_field("config.get('name') == 'john'")
    def _on_john(self) -> None:
        self.current_text = "Hello, John!"
        self.john_fired = True

    @on_field("config.get('name') == 'jane'")
    def _on_jane(self) -> None:
        self.current_text = "Hello, Jane!"
        self.jane_fired = True


def test_evaluate_dict_field_expression_true() -> None:
    grid = _NameSwitcherGrid()
    grid.config["name"] = "john"
    assert evaluate_state_expression("config.get('name') == 'john'", grid)


def test_evaluate_dict_field_expression_false_for_other_name() -> None:
    grid = _NameSwitcherGrid()
    grid.config["name"] = "jane"
    assert not evaluate_state_expression("config.get('name') == 'john'", grid)


def test_from_component_class_collects_multiple_on_field_hooks() -> None:
    registry = _EventHooksRegistry.from_component_class(_NameSwitcherGrid)
    assert len(registry.on_field_hooks) == 2
    expressions = {e["expression"] for e in registry.on_field_hooks}
    assert "config.get('name') == 'john'" in expressions
    assert "config.get('name') == 'jane'" in expressions


# ---------------------------------------------------------------------------
# pump_tick dispatch via a minimal stub terminal
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class _StubTerminal:
    """Minimal terminal stub for testing pump_tick without a real session."""

    state: Any = None
    _hooks: _EventHooksRegistry = dataclasses.field(
        default_factory=_EventHooksRegistry
    )
    _attached_frame_grids: list[Any] = dataclasses.field(default_factory=list)

    def _attach_grid(self, grid: Any) -> None:
        """Register a grid so resolve_hook_grid can find it."""
        collected = _EventHooksRegistry.from_component_class(type(grid))
        for entry in collected.on_field_hooks:
            handler_name = getattr(entry["handler"], "__name__", None)
            bound = (
                getattr(grid, handler_name)
                if handler_name and hasattr(grid, handler_name)
                else entry["handler"]
            )
            self._hooks.on_field_hooks.append(
                _OnFieldHookFunctionEntry(
                    expression=entry["expression"],
                    handler=bound,
                )
            )
        self._attached_frame_grids.append(grid)


def test_pump_tick_fires_on_field_hook_when_expression_true() -> None:
    grid = _NameSwitcherGrid()
    terminal = _StubTerminal()
    terminal._attach_grid(grid)

    grid.config["name"] = "john"
    pump_tick(cast(Any, terminal))

    assert grid.john_fired
    assert not grid.jane_fired
    assert grid.current_text == "Hello, John!"


def test_pump_tick_fires_correct_hook_for_second_name() -> None:
    grid = _NameSwitcherGrid()
    terminal = _StubTerminal()
    terminal._attach_grid(grid)

    grid.config["name"] = "jane"
    pump_tick(cast(Any, terminal))

    assert grid.jane_fired
    assert not grid.john_fired
    assert grid.current_text == "Hello, Jane!"


def test_pump_tick_does_not_fire_when_expression_false() -> None:
    grid = _NameSwitcherGrid()
    terminal = _StubTerminal()
    terminal._attach_grid(grid)

    # config["name"] starts as "nobody" — neither hook should fire
    pump_tick(cast(Any, terminal))

    assert not grid.john_fired
    assert not grid.jane_fired
    assert grid.current_text == "choose a name"


def test_pump_tick_switches_hooks_on_name_change() -> None:
    grid = _NameSwitcherGrid()
    terminal = _StubTerminal()
    terminal._attach_grid(grid)

    grid.config["name"] = "john"
    pump_tick(cast(Any, terminal))
    assert grid.current_text == "Hello, John!"

    grid.config["name"] = "jane"
    pump_tick(cast(Any, terminal))
    assert grid.current_text == "Hello, Jane!"
