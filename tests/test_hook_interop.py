"""Tests for complex interactions between hook types.

Sections:
  1.  Shared stub terminal
  2.  Keyboard → on_field chains
  3.  Mutual exclusion and repeated firing
  4.  Cascading field hooks
  5.  on_tick + on_field interaction (with interval gating)
  6.  Compound / boolean expressions
  7.  Python field-type diversity
      - Optional[str], set[str], tuple, float, nested dict,
        string operators, list membership, chained comparisons,
        built-ins (max/min/abs/isinstance/hasattr/getattr)
  8.  Expression using the implicit ``state`` variable
  9.  Safe-eval resilience (bad expressions never crash)
  10. Duplicate hooks — two handlers on the same expression
  11. Fire-count tracking over multiple ticks
  12. Inheritance patterns (parent hooks, child hooks, override)
  13. Multi-grid isolation and cross-grid independence
  14. on_state / on_field source separation
  15. Dict state field (the test.py scenario formalised)
"""

from __future__ import annotations

import dataclasses
import enum
from typing import Any, cast

from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.events import on_field, on_keyboard, on_tick
from xnano.context import Context
from xnano._dispatch import invoke_hook, pump_tick
from xnano._function_hooks import (
    _EventHooksRegistry,
    _OnFieldHookFunctionEntry,
    _OnKeyboardHookFunctionEntry,
    _OnStateHookFunctionEntry,
    _OnTickHookFunctionEntry,
)
from xnano.events import on_state
from xnano.state import State
from xnano._introspection import evaluate_state_expression


# ---------------------------------------------------------------------------
# 1. Shared stub terminal
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class _StubTerminal:
    """Minimal terminal stub for dispatch tests without a real session."""

    state: Any = None
    _hooks: _EventHooksRegistry = dataclasses.field(
        default_factory=_EventHooksRegistry
    )
    _attached_frame_grids: list[Any] = dataclasses.field(default_factory=list)

    def attach(self, grid: Any) -> None:
        collected = _EventHooksRegistry.from_component_class(type(grid))

        for entry in collected.on_field_hooks:
            name = getattr(entry["handler"], "__name__", None)
            bound = (
                getattr(grid, name)
                if name and hasattr(grid, name)
                else entry["handler"]
            )
            self._hooks.on_field_hooks.append(
                _OnFieldHookFunctionEntry(
                    expression=entry["expression"], handler=bound
                )
            )

        for entry in collected.on_tick_hooks:
            name = getattr(entry["handler"], "__name__", None)
            bound = (
                getattr(grid, name)
                if name and hasattr(grid, name)
                else entry["handler"]
            )
            self._hooks.on_tick_hooks.append(
                _OnTickHookFunctionEntry(
                    interval=entry["interval"],
                    handler=bound,
                    last_fire_ms=0.0,
                )
            )

        for entry in collected.on_keyboard_hooks:
            name = getattr(entry["handler"], "__name__", None)
            bound = (
                getattr(grid, name)
                if name and hasattr(grid, name)
                else entry["handler"]
            )
            self._hooks.on_keyboard_hooks.append(
                _OnKeyboardHookFunctionEntry(
                    bindings=entry["bindings"],
                    kind=entry["kind"],
                    handler=bound,
                )
            )

        for entry in collected.on_state_hooks:
            name = getattr(entry["handler"], "__name__", None)
            bound = (
                getattr(grid, name)
                if name and hasattr(grid, name)
                else entry["handler"]
            )
            self._hooks.on_state_hooks.append(
                _OnStateHookFunctionEntry(
                    expression=entry["expression"], handler=bound
                )
            )

        self._attached_frame_grids.append(grid)

    def fire_keyboard(self, handler_name: str) -> None:
        """Directly invoke a keyboard handler by name (skips event routing)."""
        ctx = Context(event=None, terminal=cast(Any, self), state=self.state)
        for entry in self._hooks.on_keyboard_hooks:
            h = entry["handler"]
            if getattr(h, "__name__", None) == handler_name:
                invoke_hook(h, None, ctx)
                return
        raise KeyError(f"no keyboard hook named {handler_name!r}")


# ---------------------------------------------------------------------------
# 2. Keyboard → on_field chains
# ---------------------------------------------------------------------------


class _SwitcherGrid(BaseGrid):
    mode: str = Field(default="idle", state=True)
    label: str = Field(default="idle mode")
    john_count: int = Field(default=0, state=True)
    jane_count: int = Field(default=0, state=True)

    @on_keyboard("a")
    def _press_a(self) -> None:
        self.mode = "john"

    @on_keyboard("d")
    def _press_d(self) -> None:
        self.mode = "jane"

    @on_field("mode == 'john'")
    def _on_john(self) -> None:
        self.label = "Hello, John!"
        self.john_count += 1

    @on_field("mode == 'jane'")
    def _on_jane(self) -> None:
        self.label = "Hello, Jane!"
        self.jane_count += 1


def test_keyboard_then_field_hook_fires() -> None:
    grid = _SwitcherGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    terminal.fire_keyboard("_press_a")
    pump_tick(cast(Any, terminal))

    assert grid.label == "Hello, John!"
    assert grid.john_count == 1
    assert grid.jane_count == 0


def test_keyboard_switches_which_field_hook_fires() -> None:
    grid = _SwitcherGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    terminal.fire_keyboard("_press_a")
    pump_tick(cast(Any, terminal))
    assert grid.label == "Hello, John!"

    terminal.fire_keyboard("_press_d")
    pump_tick(cast(Any, terminal))
    assert grid.label == "Hello, Jane!"
    assert grid.john_count == 1
    assert grid.jane_count == 1


def test_no_key_press_means_no_field_hook() -> None:
    grid = _SwitcherGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    pump_tick(cast(Any, terminal))
    assert grid.label == "idle mode"
    assert grid.john_count == 0


def test_multiple_keyboard_presses_before_tick_last_wins() -> None:
    """Back-to-back key presses before a tick — only the final state matters."""
    grid = _SwitcherGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    terminal.fire_keyboard("_press_a")
    terminal.fire_keyboard("_press_d")
    terminal.fire_keyboard("_press_a")
    pump_tick(cast(Any, terminal))

    assert grid.mode == "john"
    assert grid.john_count == 1
    assert grid.jane_count == 0


# ---------------------------------------------------------------------------
# 3. Mutual exclusion and repeated firing
# ---------------------------------------------------------------------------


class _TrafficLightGrid(BaseGrid):
    color: str = Field(default="green", state=True)
    red_fires: int = Field(default=0, state=True)
    yellow_fires: int = Field(default=0, state=True)
    green_fires: int = Field(default=0, state=True)

    @on_field("color == 'red'")
    def _on_red(self) -> None:
        self.red_fires += 1

    @on_field("color == 'yellow'")
    def _on_yellow(self) -> None:
        self.yellow_fires += 1

    @on_field("color == 'green'")
    def _on_green(self) -> None:
        self.green_fires += 1


def test_only_matching_field_hook_fires() -> None:
    grid = _TrafficLightGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    pump_tick(cast(Any, terminal))
    assert grid.green_fires == 1
    assert grid.red_fires == 0
    assert grid.yellow_fires == 0

    grid.color = "red"
    pump_tick(cast(Any, terminal))
    assert grid.red_fires == 1
    assert grid.green_fires == 1
    assert grid.yellow_fires == 0


def test_field_hook_fires_every_tick_while_condition_holds() -> None:
    grid = _TrafficLightGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    for _ in range(5):
        pump_tick(cast(Any, terminal))

    assert grid.green_fires == 5
    assert grid.red_fires == 0


def test_field_hook_stops_when_condition_becomes_false() -> None:
    grid = _TrafficLightGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    pump_tick(cast(Any, terminal))
    assert grid.green_fires == 1

    grid.color = "red"
    pump_tick(cast(Any, terminal))
    assert grid.green_fires == 1  # did not increment again
    assert grid.red_fires == 1


# ---------------------------------------------------------------------------
# 4. Cascading field hooks
# ---------------------------------------------------------------------------


class _CascadeGrid(BaseGrid):
    step: int = Field(default=0, state=True)
    stage_a_reached: bool = Field(default=False, state=True)
    stage_b_reached: bool = Field(default=False, state=True)

    @on_field("step == 1")
    def _on_step_one(self) -> None:
        self.stage_a_reached = True
        self.step = 2

    @on_field("step == 2")
    def _on_step_two(self) -> None:
        self.stage_b_reached = True


def test_cascade_second_step_fires_on_next_tick() -> None:
    grid = _CascadeGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.step = 1
    pump_tick(cast(Any, terminal))
    assert grid.stage_a_reached

    pump_tick(cast(Any, terminal))
    assert grid.stage_b_reached


# ---------------------------------------------------------------------------
# 5. on_tick + on_field interaction (with interval gating)
# ---------------------------------------------------------------------------


class _CountdownGrid(BaseGrid):
    ticks: int = Field(default=0, state=True)
    threshold_reached: bool = Field(default=False, state=True)

    @on_tick
    def _increment(self) -> None:
        self.ticks += 1

    @on_field("ticks >= 3")
    def _on_threshold(self) -> None:
        self.threshold_reached = True


def test_tick_increments_then_field_hook_fires_at_threshold() -> None:
    grid = _CountdownGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    pump_tick(cast(Any, terminal))
    assert grid.ticks == 1 and not grid.threshold_reached

    pump_tick(cast(Any, terminal))
    assert grid.ticks == 2 and not grid.threshold_reached

    pump_tick(cast(Any, terminal))
    assert grid.ticks == 3 and grid.threshold_reached


class _IntervalGrid(BaseGrid):
    """on_tick with a huge interval fires only once (first call starts from
    last_fire_ms=0, so elapsed is large enough to trip the interval gate
    immediately). on_field fires on every tick regardless.
    """

    slow_ticks: int = Field(default=0, state=True)
    field_ticks: int = Field(default=0, state=True)

    @on_tick(
        9_999_999
    )  # only fires once: first pump_tick has elapsed≥interval
    def _slow(self) -> None:
        self.slow_ticks += 1

    @on_field("slow_ticks >= 0")  # always true — not gated by tick interval
    def _on_always(self) -> None:
        self.field_ticks += 1


# def test_interval_tick_fires_once_field_hook_fires_every_tick() -> None:
#     """Interval tick fires on tick #1 (last_fire_ms=0 → large elapsed).
#     Subsequent ticks: interval not elapsed, tick hook skipped.
#     Field hook fires on all 3 ticks because it has no interval.
#     """
#     grid = _IntervalGrid()
#     terminal = _StubTerminal()
#     terminal.attach(grid)

#     for _ in range(3):
#         pump_tick(cast(Any, terminal))

#     assert grid.slow_ticks == 1  # fired once on first pump_tick
#     assert grid.field_ticks == 3  # fired on every tick


# ---------------------------------------------------------------------------
# 6. Compound / boolean expressions
# ---------------------------------------------------------------------------


class _CompoundGrid(BaseGrid):
    count: int = Field(default=0, state=True)
    active: bool = Field(default=False, state=True)
    fired: bool = Field(default=False, state=True)
    negation_fired: bool = Field(default=False, state=True)
    or_fired: bool = Field(default=False, state=True)

    @on_field("count > 2 and active")
    def _on_compound_and(self) -> None:
        self.fired = True

    @on_field("not active")
    def _on_negation(self) -> None:
        self.negation_fired = True

    @on_field("count > 100 or active")
    def _on_or(self) -> None:
        self.or_fired = True


def test_compound_and_requires_both_conditions() -> None:
    grid = _CompoundGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.count = 5
    pump_tick(cast(Any, terminal))
    assert not grid.fired  # active is still False

    grid.active = True
    pump_tick(cast(Any, terminal))
    assert grid.fired


def test_negation_expression_fires_when_field_is_false() -> None:
    grid = _CompoundGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    pump_tick(cast(Any, terminal))
    assert grid.negation_fired  # active starts False

    grid.negation_fired = False
    grid.active = True
    pump_tick(cast(Any, terminal))
    assert not grid.negation_fired


def test_or_expression_fires_on_either_condition() -> None:
    grid = _CompoundGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    pump_tick(cast(Any, terminal))
    assert not grid.or_fired  # count=0, active=False

    grid.active = True
    pump_tick(cast(Any, terminal))
    assert grid.or_fired


def test_chained_comparison_expression() -> None:
    class _RangeGrid(BaseGrid):
        value: int = Field(default=0, state=True)
        in_range: bool = Field(default=False, state=True)

        @on_field("0 < value < 100")
        def _on_in_range(self) -> None:
            self.in_range = True

    grid = _RangeGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.value = 50
    pump_tick(cast(Any, terminal))
    assert grid.in_range

    grid.in_range = False
    grid.value = 150
    pump_tick(cast(Any, terminal))
    assert not grid.in_range


# ---------------------------------------------------------------------------
# 7. Python field-type diversity
# ---------------------------------------------------------------------------


# 7a. Optional[str] — truthiness and None check
class _OptionalGrid(BaseGrid):
    username: str | None = Field(default=None, state=True)
    logged_in: bool = Field(default=False, state=True)
    logged_out: bool = Field(default=False, state=True)

    @on_field("username is not None")
    def _on_login(self) -> None:
        self.logged_in = True

    @on_field("username is None")
    def _on_logout(self) -> None:
        self.logged_out = True


def test_optional_field_none_check() -> None:
    grid = _OptionalGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    pump_tick(cast(Any, terminal))
    assert not grid.logged_in
    assert grid.logged_out

    grid.username = "alice"
    grid.logged_out = False
    pump_tick(cast(Any, terminal))
    assert grid.logged_in
    assert not grid.logged_out


# 7b. set[str] — membership test
class _PermissionsGrid(BaseGrid):
    roles: set[str] = Field(default_factory=set, state=True)
    is_admin: bool = Field(default=False, state=True)
    is_editor: bool = Field(default=False, state=True)
    no_roles: bool = Field(default=False, state=True)

    @on_field("'admin' in roles")
    def _on_admin(self) -> None:
        self.is_admin = True

    @on_field("'editor' in roles")
    def _on_editor(self) -> None:
        self.is_editor = True

    @on_field("len(roles) == 0")
    def _on_empty(self) -> None:
        self.no_roles = True


def test_set_membership_expression() -> None:
    grid = _PermissionsGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    pump_tick(cast(Any, terminal))
    assert not grid.is_admin
    assert grid.no_roles

    grid.roles.add("admin")
    grid.no_roles = False
    pump_tick(cast(Any, terminal))
    assert grid.is_admin
    assert not grid.no_roles


def test_set_multiple_memberships() -> None:
    grid = _PermissionsGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.roles = {"admin", "editor"}
    pump_tick(cast(Any, terminal))
    assert grid.is_admin
    assert grid.is_editor


# 7c. tuple — index access
class _CoordGrid(BaseGrid):
    position: tuple[int, int] = Field(default=(0, 0), state=True)
    in_positive_quadrant: bool = Field(default=False, state=True)
    at_origin: bool = Field(default=False, state=True)

    @on_field("position[0] > 0 and position[1] > 0")
    def _on_positive(self) -> None:
        self.in_positive_quadrant = True

    @on_field("position[0] == 0 and position[1] == 0")
    def _on_origin(self) -> None:
        self.at_origin = True


def test_tuple_index_expression() -> None:
    grid = _CoordGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    pump_tick(cast(Any, terminal))
    assert grid.at_origin
    assert not grid.in_positive_quadrant

    grid.position = (5, 10)
    grid.at_origin = False
    pump_tick(cast(Any, terminal))
    assert grid.in_positive_quadrant
    assert not grid.at_origin


# 7d. float — threshold and abs comparison
class _ProgressGrid(BaseGrid):
    progress: float = Field(default=0.0, state=True)
    complete: bool = Field(default=False, state=True)
    near_half: bool = Field(default=False, state=True)

    @on_field("progress >= 1.0")
    def _on_complete(self) -> None:
        self.complete = True

    @on_field("abs(progress - 0.5) < 0.05")
    def _on_near_half(self) -> None:
        self.near_half = True


def test_float_threshold_expression() -> None:
    grid = _ProgressGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.progress = 0.999
    pump_tick(cast(Any, terminal))
    assert not grid.complete

    grid.progress = 1.0
    pump_tick(cast(Any, terminal))
    assert grid.complete


def test_float_abs_proximity_expression() -> None:
    grid = _ProgressGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.progress = 0.52
    pump_tick(cast(Any, terminal))
    assert grid.near_half

    grid.near_half = False
    grid.progress = 0.9
    pump_tick(cast(Any, terminal))
    assert not grid.near_half


# 7e. Nested dict — deep key access
class _ConfigGrid(BaseGrid):
    config: dict[str, Any] = Field(default_factory=dict, state=True)
    is_admin: bool = Field(default=False, state=True)
    theme_dark: bool = Field(default=False, state=True)

    def __post_init__(self) -> None:
        self.config = {
            "user": {"role": "guest"},
            "ui": {"theme": "light"},
        }

    @on_field("config.get('user', {}).get('role') == 'admin'")
    def _on_admin(self) -> None:
        self.is_admin = True

    @on_field("config.get('ui', {}).get('theme') == 'dark'")
    def _on_dark(self) -> None:
        self.theme_dark = True


def test_nested_dict_expression() -> None:
    grid = _ConfigGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    pump_tick(cast(Any, terminal))
    assert not grid.is_admin
    assert not grid.theme_dark

    grid.config["user"]["role"] = "admin"
    grid.config["ui"]["theme"] = "dark"
    pump_tick(cast(Any, terminal))
    assert grid.is_admin
    assert grid.theme_dark


# 7f. String operators — in, len, str() conversion
class _StringFieldGrid(BaseGrid):
    message: str = Field(default="", state=True)
    count: int = Field(default=0, state=True)
    has_error: bool = Field(default=False, state=True)
    long_message: bool = Field(default=False, state=True)
    count_starts_with_1: bool = Field(default=False, state=True)

    @on_field("'error' in message")
    def _on_error(self) -> None:
        self.has_error = True

    @on_field("len(message) > 20")
    def _on_long(self) -> None:
        self.long_message = True

    @on_field("str(count).startswith('1')")
    def _on_starts_one(self) -> None:
        self.count_starts_with_1 = True


def test_string_in_operator_expression() -> None:
    grid = _StringFieldGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.message = "connection error occurred"
    pump_tick(cast(Any, terminal))
    assert grid.has_error


def test_string_len_expression() -> None:
    grid = _StringFieldGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.message = "this message is definitely longer than twenty chars"
    pump_tick(cast(Any, terminal))
    assert grid.long_message


def test_str_conversion_expression() -> None:
    grid = _StringFieldGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.count = 100
    pump_tick(cast(Any, terminal))
    assert grid.count_starts_with_1

    grid.count_starts_with_1 = False
    grid.count = 200
    pump_tick(cast(Any, terminal))
    assert not grid.count_starts_with_1


# 7g. List membership and truthiness
class _LogGrid(BaseGrid):
    log: list[str] = Field(default_factory=list, state=True)
    has_warning: bool = Field(default=False, state=True)
    is_empty: bool = Field(default=False, state=True)
    overflow: bool = Field(default=False, state=True)

    @on_field("'WARNING' in log")
    def _on_warning(self) -> None:
        self.has_warning = True

    @on_field("not log")
    def _on_empty(self) -> None:
        self.is_empty = True

    @on_field("len(log) > 10")
    def _on_overflow(self) -> None:
        self.overflow = True


def test_list_membership_expression() -> None:
    grid = _LogGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    pump_tick(cast(Any, terminal))
    assert grid.is_empty
    assert not grid.has_warning

    grid.log.append("WARNING")
    grid.is_empty = False
    pump_tick(cast(Any, terminal))
    assert grid.has_warning
    assert not grid.is_empty


def test_list_truthiness_and_len() -> None:
    grid = _LogGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.log = [f"line {i}" for i in range(11)]
    pump_tick(cast(Any, terminal))
    assert grid.overflow
    assert not grid.is_empty


# 7h. max / min built-in expressions
class _ScoreGrid(BaseGrid):
    scores: list[int] = Field(default_factory=list, state=True)
    high_score: bool = Field(default=False, state=True)
    low_score: bool = Field(default=False, state=True)

    @on_field("bool(scores) and max(scores) >= 90")
    def _on_high(self) -> None:
        self.high_score = True

    @on_field("bool(scores) and min(scores) <= 10")
    def _on_low(self) -> None:
        self.low_score = True


def test_max_builtin_expression() -> None:
    grid = _ScoreGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.scores = [70, 80, 95]
    pump_tick(cast(Any, terminal))
    assert grid.high_score


def test_min_builtin_expression() -> None:
    grid = _ScoreGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.scores = [5, 50, 70]
    pump_tick(cast(Any, terminal))
    assert grid.low_score


# 7i. isinstance and hasattr
class _TypeCheckGrid(BaseGrid):
    value: Any = Field(default=None, state=True)
    is_int: bool = Field(default=False, state=True)
    has_name: bool = Field(default=False, state=True)

    @on_field("isinstance(value, int)")
    def _on_int(self) -> None:
        self.is_int = True

    @on_field("hasattr(value, '__len__')")
    def _on_has_len(self) -> None:
        self.has_name = True


def test_isinstance_expression() -> None:
    grid = _TypeCheckGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.value = 42
    pump_tick(cast(Any, terminal))
    assert grid.is_int

    grid.is_int = False
    grid.value = "not an int"
    pump_tick(cast(Any, terminal))
    assert not grid.is_int


def test_hasattr_expression() -> None:
    grid = _TypeCheckGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.value = [1, 2, 3]
    pump_tick(cast(Any, terminal))
    assert grid.has_name


# ---------------------------------------------------------------------------
# 8. Expression using the implicit ``state`` variable
#    evaluate_state_expression binds ``state`` to the grid instance itself.
# ---------------------------------------------------------------------------


class _StateVarGrid(BaseGrid):
    count: int = Field(default=0, state=True)
    via_state: bool = Field(default=False, state=True)
    has_count_attr: bool = Field(default=False, state=True)
    via_getattr: bool = Field(default=False, state=True)

    @on_field("state.count > 5")
    def _on_via_state(self) -> None:
        self.via_state = True

    @on_field("hasattr(state, 'count')")
    def _on_hasattr(self) -> None:
        self.has_count_attr = True

    @on_field("getattr(state, 'count', 0) == 10")
    def _on_via_getattr(self) -> None:
        self.via_getattr = True


def test_state_variable_attribute_access() -> None:
    grid = _StateVarGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.count = 6
    pump_tick(cast(Any, terminal))
    assert grid.via_state


def test_state_variable_hasattr() -> None:
    grid = _StateVarGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    pump_tick(cast(Any, terminal))
    assert grid.has_count_attr


def test_state_variable_getattr() -> None:
    grid = _StateVarGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.count = 10
    pump_tick(cast(Any, terminal))
    assert grid.via_getattr


# ---------------------------------------------------------------------------
# 9. Safe-eval resilience
# ---------------------------------------------------------------------------


class _SafeGrid(BaseGrid):
    count: int = Field(default=5, state=True)
    denominator: int = Field(default=0, state=True)


def test_missing_field_returns_false() -> None:
    grid = _SafeGrid()
    assert not evaluate_state_expression("nonexistent_field > 0", grid)


def test_division_by_zero_returns_false() -> None:
    grid = _SafeGrid()
    # denominator is 0 — expression would raise ZeroDivisionError
    assert not evaluate_state_expression("count / denominator > 1", grid)


def test_syntax_error_returns_false() -> None:
    grid = _SafeGrid()
    assert not evaluate_state_expression(
        "this is definitely not valid python !!", grid
    )


def test_attribute_error_on_int_returns_false() -> None:
    grid = _SafeGrid()
    # int has no .nonexistent
    assert not evaluate_state_expression("count.nonexistent", grid)


def test_invalid_index_returns_false() -> None:
    grid = _SafeGrid()
    # count is an int, not subscriptable
    assert not evaluate_state_expression("count['key']", grid)


def test_bad_expression_does_not_fire_hook() -> None:
    class _BadExprGrid(BaseGrid):
        count: int = Field(default=5, state=True)
        fired: bool = Field(default=False, state=True)

        @on_field("count / 0 > 1")
        def _on_bad(self) -> None:
            self.fired = True

    grid = _BadExprGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    pump_tick(cast(Any, terminal))
    assert not grid.fired


# ---------------------------------------------------------------------------
# 10. Duplicate hooks — two handlers watching the same expression
# ---------------------------------------------------------------------------


class _TwoHandlerGrid(BaseGrid):
    active: bool = Field(default=False, state=True)
    handler_a_count: int = Field(default=0, state=True)
    handler_b_count: int = Field(default=0, state=True)

    @on_field("active")
    def _handler_a(self) -> None:
        self.handler_a_count += 1

    @on_field("active")
    def _handler_b(self) -> None:
        self.handler_b_count += 1


def test_two_handlers_same_expression_both_fire() -> None:
    grid = _TwoHandlerGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.active = True
    pump_tick(cast(Any, terminal))

    assert grid.handler_a_count == 1
    assert grid.handler_b_count == 1


def test_two_handlers_neither_fires_when_false() -> None:
    grid = _TwoHandlerGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    pump_tick(cast(Any, terminal))
    assert grid.handler_a_count == 0
    assert grid.handler_b_count == 0


# ---------------------------------------------------------------------------
# 11. Fire-count tracking over multiple ticks
# ---------------------------------------------------------------------------


class _FireCountGrid(BaseGrid):
    active: bool = Field(default=True, state=True)
    fire_count: int = Field(default=0, state=True)

    @on_field("active")
    def _on_active(self) -> None:
        self.fire_count += 1


def test_hook_fires_once_per_tick_while_true() -> None:
    grid = _FireCountGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    for _ in range(7):
        pump_tick(cast(Any, terminal))

    assert grid.fire_count == 7


def test_hook_fire_count_matches_true_ticks_only() -> None:
    grid = _FireCountGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    pump_tick(cast(Any, terminal))  # true → fires
    grid.active = False
    pump_tick(cast(Any, terminal))  # false → no fire
    grid.active = True
    pump_tick(cast(Any, terminal))  # true → fires
    pump_tick(cast(Any, terminal))  # true → fires

    assert grid.fire_count == 3


# ---------------------------------------------------------------------------
# 12. Inheritance patterns
# ---------------------------------------------------------------------------


class _ParentGrid(BaseGrid):
    base_flag: bool = Field(default=False, state=True)
    parent_fired: bool = Field(default=False, state=True)

    @on_field("base_flag")
    def _on_base(self) -> None:
        self.parent_fired = True


class _ChildGrid(_ParentGrid):
    child_flag: bool = Field(default=False, state=True)
    child_fired: bool = Field(default=False, state=True)

    @on_field("child_flag")
    def _on_child(self) -> None:
        self.child_fired = True


class _GrandchildGrid(_ChildGrid):
    grand_flag: bool = Field(default=False, state=True)
    grand_fired: bool = Field(default=False, state=True)

    @on_field("grand_flag")
    def _on_grand(self) -> None:
        self.grand_fired = True


def test_child_inherits_parent_on_field_hooks() -> None:
    grid = _ChildGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.base_flag = True
    pump_tick(cast(Any, terminal))
    assert grid.parent_fired


def test_child_own_hook_also_fires() -> None:
    grid = _ChildGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.child_flag = True
    pump_tick(cast(Any, terminal))
    assert grid.child_fired


def test_child_parent_and_own_hooks_fire_independently() -> None:
    grid = _ChildGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.base_flag = True
    grid.child_flag = True
    pump_tick(cast(Any, terminal))
    assert grid.parent_fired
    assert grid.child_fired


def test_grandchild_inherits_all_three_hook_layers() -> None:
    grid = _GrandchildGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.base_flag = True
    grid.child_flag = True
    grid.grand_flag = True
    pump_tick(cast(Any, terminal))
    assert grid.parent_fired
    assert grid.child_fired
    assert grid.grand_fired


def test_grandchild_only_grand_fires_when_others_false() -> None:
    grid = _GrandchildGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    grid.grand_flag = True
    pump_tick(cast(Any, terminal))
    assert grid.grand_fired
    assert not grid.parent_fired
    assert not grid.child_fired


def test_parent_used_alone_has_only_parent_hook() -> None:
    registry = _EventHooksRegistry.from_component_class(_ParentGrid)
    assert len(registry.on_field_hooks) == 1

    registry_child = _EventHooksRegistry.from_component_class(_ChildGrid)
    assert len(registry_child.on_field_hooks) == 2

    registry_grand = _EventHooksRegistry.from_component_class(_GrandchildGrid)
    assert len(registry_grand.on_field_hooks) == 3


def test_overridden_hook_registers_once() -> None:
    # A subclass overriding a parent's hook method must shadow it — both
    # collected members rebind to the same bound method, so registering
    # both would fire the override twice per event.
    class _OverrideParent(BaseGrid):
        flag: bool = Field(default=False, state=True)
        fired: int = Field(default=0, state=True)

        @on_field("flag")
        def react(self) -> None:
            self.fired += 1

    class _OverrideChild(_OverrideParent):
        @on_field("flag")
        def react(self) -> None:
            self.fired += 10

    registry = _EventHooksRegistry.from_component_class(_OverrideChild)
    assert len(registry.on_field_hooks) == 1

    grid = _OverrideChild()
    terminal = _StubTerminal()
    terminal.attach(grid)
    grid.flag = True
    pump_tick(cast(Any, terminal))
    assert grid.fired == 10


# ---------------------------------------------------------------------------
# 13. Multi-grid isolation and cross-grid independence
# ---------------------------------------------------------------------------


class _IsolatedGrid(BaseGrid):
    value: int = Field(default=0, state=True)
    fired: bool = Field(default=False, state=True)
    fire_count: int = Field(default=0, state=True)

    @on_field("value == 99")
    def _on_trigger(self) -> None:
        self.fired = True
        self.fire_count += 1


def test_field_hooks_isolated_across_instances() -> None:
    grid_a = _IsolatedGrid()
    grid_b = _IsolatedGrid()
    terminal = _StubTerminal()
    terminal.attach(grid_a)
    terminal.attach(grid_b)

    grid_a.value = 99
    pump_tick(cast(Any, terminal))

    assert grid_a.fired
    assert not grid_b.fired


def test_both_grids_fire_independently() -> None:
    grid_a = _IsolatedGrid()
    grid_b = _IsolatedGrid()
    terminal = _StubTerminal()
    terminal.attach(grid_a)
    terminal.attach(grid_b)

    grid_a.value = 99
    grid_b.value = 99
    pump_tick(cast(Any, terminal))

    assert grid_a.fired and grid_b.fired


def test_three_grids_only_one_matching() -> None:
    grids = [_IsolatedGrid() for _ in range(3)]
    terminal = _StubTerminal()
    for g in grids:
        terminal.attach(g)

    grids[1].value = 99
    pump_tick(cast(Any, terminal))

    assert not grids[0].fired
    assert grids[1].fired
    assert not grids[2].fired


def test_mixed_grid_types_do_not_contaminate() -> None:
    grid_isolated = _IsolatedGrid()
    grid_countdown = _CountdownGrid()
    terminal = _StubTerminal()
    terminal.attach(grid_isolated)
    terminal.attach(grid_countdown)

    pump_tick(cast(Any, terminal))

    assert not grid_isolated.fired  # value is 0, not 99
    assert grid_countdown.ticks == 1  # tick hook incremented


# ---------------------------------------------------------------------------
# 14. on_state / on_field source separation
# ---------------------------------------------------------------------------


class _DualSourceGrid(BaseGrid):
    grid_flag: bool = Field(default=False, state=True)
    field_hook_fired: bool = Field(default=False, state=True)
    state_hook_fired: bool = Field(default=False, state=True)

    @on_field("grid_flag")
    def _on_grid_flag(self) -> None:
        self.field_hook_fired = True

    @on_state("terminal_flag")
    def _on_terminal_flag(self) -> None:
        self.state_hook_fired = True


def test_on_field_fires_without_terminal_state() -> None:
    grid = _DualSourceGrid()
    terminal = _StubTerminal(state=None)
    terminal.attach(grid)

    grid.grid_flag = True
    pump_tick(cast(Any, terminal))

    assert grid.field_hook_fired
    assert not grid.state_hook_fired


def test_on_state_fires_from_terminal_state_not_grid() -> None:
    grid = _DualSourceGrid()
    terminal = _StubTerminal(state=State(terminal_flag=True))
    terminal.attach(grid)

    pump_tick(cast(Any, terminal))

    assert grid.state_hook_fired
    assert not grid.field_hook_fired


def test_on_field_and_on_state_fire_independently() -> None:
    grid = _DualSourceGrid()
    terminal = _StubTerminal(state=State(terminal_flag=True))
    terminal.attach(grid)

    grid.grid_flag = True
    pump_tick(cast(Any, terminal))

    assert grid.field_hook_fired
    assert grid.state_hook_fired


def test_on_field_not_confused_by_terminal_state_attribute() -> None:
    """on_field must evaluate against the grid, not terminal.state,
    even if terminal.state has a same-named attribute."""

    class _AmbiguousGrid(BaseGrid):
        count: int = Field(default=10, state=True)
        correct: bool = Field(default=False, state=True)

        @on_field("count == 10")
        def _on_ten(self) -> None:
            self.correct = True

    grid = _AmbiguousGrid()
    # terminal state also has count, but with a different value
    terminal = _StubTerminal(state=State(count=999))
    terminal.attach(grid)

    pump_tick(cast(Any, terminal))
    # hook must fire because grid.count == 10, ignoring state.count == 999
    assert grid.correct


# ---------------------------------------------------------------------------
# 15. Dict state field (test.py scenario formalised)
# ---------------------------------------------------------------------------


class _DictStateGrid(BaseGrid):
    config: dict[str, Any] = Field(default_factory=dict, state=True)
    display: str = Field(default="waiting")

    def __post_init__(self) -> None:
        self.config["name"] = "nobody"

    @on_keyboard("a")
    def _set_alice(self) -> None:
        self.config["name"] = "alice"

    @on_keyboard("b")
    def _set_bob(self) -> None:
        self.config["name"] = "bob"

    @on_field("config.get('name') == 'alice'")
    def _on_alice(self) -> None:
        self.display = "Hello, Alice!"

    @on_field("config.get('name') == 'bob'")
    def _on_bob(self) -> None:
        self.display = "Hello, Bob!"


def test_dict_state_keyboard_to_display_alice() -> None:
    grid = _DictStateGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    terminal.fire_keyboard("_set_alice")
    pump_tick(cast(Any, terminal))
    assert grid.display == "Hello, Alice!"


def test_dict_state_keyboard_to_display_bob() -> None:
    grid = _DictStateGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    terminal.fire_keyboard("_set_bob")
    pump_tick(cast(Any, terminal))
    assert grid.display == "Hello, Bob!"


def test_dict_state_display_unchanged_without_keypress() -> None:
    grid = _DictStateGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    pump_tick(cast(Any, terminal))
    assert grid.display == "waiting"


def test_dict_state_switches_correctly() -> None:
    grid = _DictStateGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    terminal.fire_keyboard("_set_alice")
    pump_tick(cast(Any, terminal))
    assert grid.display == "Hello, Alice!"

    terminal.fire_keyboard("_set_bob")
    pump_tick(cast(Any, terminal))
    assert grid.display == "Hello, Bob!"
