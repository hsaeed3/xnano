"""Performance benchmarks for hook dispatch and frame rendering.

Run with:
    uv run pytest tests/test_hook_perf.py -v --benchmark-sort=mean
    uv run pytest tests/test_hook_perf.py --benchmark-histogram

Sections:
  1.  Shared helpers and grid fixtures
  2.  pump_tick throughput — varying hook counts (non-firing)
  3.  pump_tick throughput — hooks that FIRE (handler runs every iteration)
  4.  Expression evaluation — all field-type variants
  5.  Frame render at multiple viewport sizes
  6.  Frame-to-frame loop (render + pump_tick)
  7.  Multi-grid pump_tick scaling
  8.  Mixed hook types (field + tick + state active simultaneously)
  9.  Registry collection (from_component_class) — simple and inherited
"""

from __future__ import annotations

import dataclasses
from typing import Any, cast

from xnano_core.core import CoreSession

from xnano._dispatch import pump_tick
from xnano._function_hooks import (
    _EventHooksRegistry,
    _OnFieldHookFunctionEntry,
    _OnStateHookFunctionEntry,
    _OnTickHookFunctionEntry,
)
from xnano._introspection import evaluate_state_expression
from xnano._types import Area
from xnano.core.controllers.tui import TerminalController
from xnano.events import on_field, on_tick
from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.state import State


# ---------------------------------------------------------------------------
# 1. Shared helpers and grid fixtures
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class _StubTerminal:
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


def _make_offscreen(
    width: int = 80, height: int = 24
) -> tuple[CoreSession, TerminalController]:
    core = CoreSession.offscreen(width=width, height=height)
    sess = TerminalController(
        core, terminal_width=width, terminal_height=height, is_offscreen=True
    )
    return core, sess


def _one_frame(grid: BaseGrid, sess: TerminalController, area: Area) -> None:
    sess.begin_viewport_frame()
    grid._grid_build_frame(area, sess)
    sess.commit_requests()


def _frame_and_tick(
    grid: BaseGrid,
    sess: TerminalController,
    area: Area,
    terminal: _StubTerminal,
) -> None:
    sess.begin_viewport_frame()
    grid._grid_build_frame(area, sess)
    sess.commit_requests()
    pump_tick(cast(Any, terminal))


# ---------------------------------------------------------------------------
# BaseGrid fixtures
# ---------------------------------------------------------------------------


class _CounterGrid(BaseGrid):
    count: int = Field(default=0, state=True)
    active: bool = Field(default=True, state=True)
    label: str = Field(default="running")

    @on_field("count > 1_000_000")  # never true in benchmarks
    def _on_high(self) -> None:
        self.label = "high"

    @on_field("not active")  # never true in benchmarks
    def _on_inactive(self) -> None:
        self.label = "inactive"

    @on_tick
    def _tick(self) -> None:
        self.count += 1


class _AlwaysFiringGrid(BaseGrid):
    """All on_field hooks evaluate to true every tick."""

    count: int = Field(default=5, state=True)
    active: bool = Field(default=True, state=True)
    name: str = Field(default="alice", state=True)
    calls: int = Field(default=0, state=True)

    @on_field("count > 0")
    def _on_count(self) -> None:
        self.calls += 1

    @on_field("active")
    def _on_active(self) -> None:
        self.calls += 1

    @on_field("name == 'alice'")
    def _on_name(self) -> None:
        self.calls += 1


class _RenderGrid(BaseGrid):
    title: str = Field(default="Benchmark BaseGrid", height=1)
    body: str = Field(
        default=(
            "frame content goes here — this simulates a typical "
            "terminal application layout with a title, body, and status"
        )
    )
    status: str = Field(default="ok", height=1)


class _NestedRenderGrid(BaseGrid):
    header: str = Field(default="Header", height=1)
    left: _RenderGrid = Field(default_factory=_RenderGrid)
    right: _RenderGrid = Field(default_factory=_RenderGrid)
    footer: str = Field(default="Footer", height=1)


class _ExprGrid(BaseGrid):
    count: int = Field(default=42, state=True)
    active: bool = Field(default=True, state=True)
    name: str = Field(default="alice", state=True)
    progress: float = Field(default=0.52, state=True)
    config: dict[str, Any] = Field(
        default_factory=lambda: {"user": {"role": "admin"}}, state=True
    )
    roles: set[str] = Field(
        default_factory=lambda: {"admin", "editor"}, state=True
    )
    position: tuple[int, int] = Field(default=(5, 10), state=True)
    log: list[str] = Field(
        default_factory=lambda: ["INFO", "WARNING", "ERROR"], state=True
    )
    scores: list[int] = Field(default_factory=lambda: [70, 85, 95], state=True)
    username: str | None = Field(default="alice", state=True)
    denominator: int = Field(default=2, state=True)


# ---------------------------------------------------------------------------
# 2. pump_tick throughput — non-firing hooks (expression always false)
# ---------------------------------------------------------------------------


def _make_nonfiring_terminal(n: int) -> _StubTerminal:
    grid = _CounterGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)
    bound_noop = (lambda self: None).__get__(grid, type(grid))
    for i in range(n):
        terminal._hooks.on_field_hooks.append(
            _OnFieldHookFunctionEntry(
                expression=f"count > {10_000_000 + i}",
                handler=bound_noop,
            )
        )
    return terminal


def test_bench_pump_tick_baseline(benchmark) -> None:
    """Baseline: 2 non-firing field hooks + 1 tick hook."""
    terminal = _make_nonfiring_terminal(0)
    benchmark(pump_tick, terminal)  # type: ignore[arg-type]


def test_bench_pump_tick_10_nonfiring(benchmark) -> None:
    terminal = _make_nonfiring_terminal(10)
    benchmark(pump_tick, terminal)  # type: ignore[arg-type]


def test_bench_pump_tick_50_nonfiring(benchmark) -> None:
    terminal = _make_nonfiring_terminal(50)
    benchmark(pump_tick, terminal)  # type: ignore[arg-type]


def test_bench_pump_tick_100_nonfiring(benchmark) -> None:
    terminal = _make_nonfiring_terminal(100)
    benchmark(pump_tick, terminal)  # type: ignore[arg-type]


def test_bench_pump_tick_500_nonfiring(benchmark) -> None:
    terminal = _make_nonfiring_terminal(500)
    benchmark(pump_tick, terminal)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 3. pump_tick throughput — hooks that FIRE (handler runs every call)
# ---------------------------------------------------------------------------


def test_bench_pump_tick_all_firing(benchmark) -> None:
    """3 on_field hooks all evaluate true and run their handlers."""
    grid = _AlwaysFiringGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)
    benchmark(pump_tick, terminal)  # type: ignore[arg-type]


def _make_firing_terminal(n: int) -> _StubTerminal:
    grid = _AlwaysFiringGrid()
    terminal = _StubTerminal()
    terminal.attach(grid)

    def noop(self) -> None:  # type: ignore[misc]
        pass

    bound_noop = noop.__get__(grid, type(grid))
    for i in range(n):
        terminal._hooks.on_field_hooks.append(
            _OnFieldHookFunctionEntry(
                expression="active",  # always true
                handler=bound_noop,
            )
        )
    return terminal


def test_bench_pump_tick_10_firing(benchmark) -> None:
    terminal = _make_firing_terminal(10)
    benchmark(pump_tick, terminal)  # type: ignore[arg-type]


def test_bench_pump_tick_50_firing(benchmark) -> None:
    terminal = _make_firing_terminal(50)
    benchmark(pump_tick, terminal)  # type: ignore[arg-type]


def test_bench_pump_tick_100_firing(benchmark) -> None:
    terminal = _make_firing_terminal(100)
    benchmark(pump_tick, terminal)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 4. Expression evaluation — all field-type variants
# ---------------------------------------------------------------------------


def test_bench_expr_bool_field(benchmark) -> None:
    grid = _ExprGrid()
    benchmark(evaluate_state_expression, "active", grid)


def test_bench_expr_int_comparison(benchmark) -> None:
    grid = _ExprGrid()
    benchmark(evaluate_state_expression, "count > 10", grid)


def test_bench_expr_chained_comparison(benchmark) -> None:
    grid = _ExprGrid()
    benchmark(evaluate_state_expression, "0 < count < 100", grid)


def test_bench_expr_compound_and(benchmark) -> None:
    grid = _ExprGrid()
    benchmark(
        evaluate_state_expression,
        "count > 10 and active and name == 'alice'",
        grid,
    )


def test_bench_expr_float_abs(benchmark) -> None:
    grid = _ExprGrid()
    benchmark(evaluate_state_expression, "abs(progress - 0.5) < 0.05", grid)


def test_bench_expr_float_threshold(benchmark) -> None:
    grid = _ExprGrid()
    benchmark(evaluate_state_expression, "progress >= 0.5", grid)


def test_bench_expr_dict_get_flat(benchmark) -> None:
    grid = _ExprGrid()
    grid.config["name"] = "john"
    benchmark(evaluate_state_expression, "config.get('name') == 'john'", grid)


def test_bench_expr_dict_get_nested(benchmark) -> None:
    grid = _ExprGrid()
    benchmark(
        evaluate_state_expression,
        "config.get('user', {}).get('role') == 'admin'",
        grid,
    )


def test_bench_expr_set_membership(benchmark) -> None:
    grid = _ExprGrid()
    benchmark(evaluate_state_expression, "'admin' in roles", grid)


def test_bench_expr_list_membership(benchmark) -> None:
    grid = _ExprGrid()
    benchmark(evaluate_state_expression, "'WARNING' in log", grid)


def test_bench_expr_list_len(benchmark) -> None:
    grid = _ExprGrid()
    benchmark(evaluate_state_expression, "len(log) > 2", grid)


def test_bench_expr_tuple_index(benchmark) -> None:
    grid = _ExprGrid()
    benchmark(
        evaluate_state_expression,
        "position[0] > 0 and position[1] > 0",
        grid,
    )


def test_bench_expr_optional_none_check(benchmark) -> None:
    grid = _ExprGrid()
    benchmark(evaluate_state_expression, "username is not None", grid)


def test_bench_expr_max_builtin(benchmark) -> None:
    grid = _ExprGrid()
    benchmark(
        evaluate_state_expression,
        "bool(scores) and max(scores) >= 90",
        grid,
    )


def test_bench_expr_str_conversion(benchmark) -> None:
    grid = _ExprGrid()
    benchmark(evaluate_state_expression, "str(count).startswith('4')", grid)


def test_bench_expr_isinstance(benchmark) -> None:
    grid = _ExprGrid()
    benchmark(evaluate_state_expression, "isinstance(count, int)", grid)


def test_bench_expr_state_variable(benchmark) -> None:
    grid = _ExprGrid()
    benchmark(evaluate_state_expression, "state.count > 10", grid)


def test_bench_expr_getattr_builtin(benchmark) -> None:
    grid = _ExprGrid()
    benchmark(
        evaluate_state_expression,
        "getattr(state, 'count', 0) > 10",
        grid,
    )


def test_bench_expr_bad_expression_resilience(benchmark) -> None:
    """Safe-eval error path: expression fails, returns False."""
    grid = _ExprGrid()
    benchmark(evaluate_state_expression, "count / 0 > 1", grid)


# ---------------------------------------------------------------------------
# 5. Frame render at multiple viewport sizes
# ---------------------------------------------------------------------------


def test_bench_frame_render_40x10(benchmark) -> None:
    grid = _RenderGrid()
    _, sess = _make_offscreen(40, 10)
    area = Area(x=0, y=0, width=40, height=10)
    benchmark(_one_frame, grid, sess, area)


def test_bench_frame_render_80x24(benchmark) -> None:
    grid = _RenderGrid()
    _, sess = _make_offscreen(80, 24)
    area = Area(x=0, y=0, width=80, height=24)
    benchmark(_one_frame, grid, sess, area)


def test_bench_frame_render_120x40(benchmark) -> None:
    grid = _RenderGrid()
    _, sess = _make_offscreen(120, 40)
    area = Area(x=0, y=0, width=120, height=40)
    benchmark(_one_frame, grid, sess, area)


def test_bench_frame_render_220x50_fullhd(benchmark) -> None:
    grid = _RenderGrid()
    _, sess = _make_offscreen(220, 50)
    area = Area(x=0, y=0, width=220, height=50)
    benchmark(_one_frame, grid, sess, area)


def test_bench_frame_render_nested_80x24(benchmark) -> None:
    """Nested grid: header + two child RenderGrids + footer."""
    grid = _NestedRenderGrid()
    _, sess = _make_offscreen(80, 24)
    area = Area(x=0, y=0, width=80, height=24)
    benchmark(_one_frame, grid, sess, area)


def test_bench_frame_render_nested_220x50(benchmark) -> None:
    grid = _NestedRenderGrid()
    _, sess = _make_offscreen(220, 50)
    area = Area(x=0, y=0, width=220, height=50)
    benchmark(_one_frame, grid, sess, area)


# ---------------------------------------------------------------------------
# 6. Frame-to-frame loop (render + pump_tick back-to-back)
# ---------------------------------------------------------------------------


def test_bench_frame_and_tick_80x24(benchmark) -> None:
    grid = _CounterGrid()
    _, sess = _make_offscreen(80, 24)
    area = Area(x=0, y=0, width=80, height=24)
    terminal = _StubTerminal()
    terminal.attach(grid)
    benchmark(_frame_and_tick, grid, sess, area, terminal)


def test_bench_frame_and_tick_220x50(benchmark) -> None:
    grid = _CounterGrid()
    _, sess = _make_offscreen(220, 50)
    area = Area(x=0, y=0, width=220, height=50)
    terminal = _StubTerminal()
    terminal.attach(grid)
    benchmark(_frame_and_tick, grid, sess, area, terminal)


def test_bench_frame_and_tick_nested_80x24(benchmark) -> None:
    grid = _NestedRenderGrid()
    _, sess = _make_offscreen(80, 24)
    area = Area(x=0, y=0, width=80, height=24)
    terminal = _StubTerminal()
    terminal.attach(grid)
    benchmark(_frame_and_tick, grid, sess, area, terminal)


def test_bench_frame_and_tick_always_firing(benchmark) -> None:
    """Hot path with hooks that actually invoke handlers each frame."""
    grid = _AlwaysFiringGrid()
    _, sess = _make_offscreen(80, 24)
    area = Area(x=0, y=0, width=80, height=24)
    terminal = _StubTerminal()
    terminal.attach(grid)
    benchmark(_frame_and_tick, grid, sess, area, terminal)


# ---------------------------------------------------------------------------
# 7. Multi-grid pump_tick scaling
# ---------------------------------------------------------------------------


def test_bench_pump_tick_1_grid(benchmark) -> None:
    terminal = _StubTerminal()
    terminal.attach(_CounterGrid())
    benchmark(pump_tick, terminal)  # type: ignore[arg-type]


def test_bench_pump_tick_5_grids(benchmark) -> None:
    terminal = _StubTerminal()
    for _ in range(5):
        terminal.attach(_CounterGrid())
    benchmark(pump_tick, terminal)  # type: ignore[arg-type]


def test_bench_pump_tick_20_grids(benchmark) -> None:
    terminal = _StubTerminal()
    for _ in range(20):
        terminal.attach(_CounterGrid())
    benchmark(pump_tick, terminal)  # type: ignore[arg-type]


def test_bench_pump_tick_50_grids(benchmark) -> None:
    terminal = _StubTerminal()
    for _ in range(50):
        terminal.attach(_CounterGrid())
    benchmark(pump_tick, terminal)  # type: ignore[arg-type]


def test_bench_pump_tick_mixed_grid_types(benchmark) -> None:
    """Mix of CounterGrid and AlwaysFiringGrid — realistic diversity."""
    terminal = _StubTerminal()
    for _ in range(5):
        terminal.attach(_CounterGrid())
    for _ in range(5):
        terminal.attach(_AlwaysFiringGrid())
    benchmark(pump_tick, terminal)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 8. Mixed hook types (field + tick + state all active)
# ---------------------------------------------------------------------------


class _MixedHookGrid(BaseGrid):
    count: int = Field(default=5, state=True)
    active: bool = Field(default=True, state=True)
    label: str = Field(default="running")

    @on_tick
    def _tick(self) -> None:
        pass

    @on_field("count > 0")
    def _on_count(self) -> None:
        pass

    @on_field("active")
    def _on_active(self) -> None:
        pass


def test_bench_mixed_hooks_no_terminal_state(benchmark) -> None:
    grid = _MixedHookGrid()
    terminal = _StubTerminal(state=None)
    terminal.attach(grid)
    benchmark(pump_tick, terminal)  # type: ignore[arg-type]


def test_bench_mixed_hooks_with_terminal_state(benchmark) -> None:
    grid = _MixedHookGrid()

    from xnano.events import on_state

    class _WithStateGrid(_MixedHookGrid):
        state_fired: bool = Field(default=False, state=True)

        @on_state("flag")
        def _on_state(self) -> None:
            self.state_fired = True

    grid2 = _WithStateGrid()
    terminal = _StubTerminal(state=State(flag=True))
    terminal.attach(grid2)
    benchmark(pump_tick, terminal)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 9. Registry collection (from_component_class) — simple and inherited
# ---------------------------------------------------------------------------


def test_bench_registry_simple(benchmark) -> None:
    benchmark(_EventHooksRegistry.from_component_class, _CounterGrid)


def test_bench_registry_few_hooks(benchmark) -> None:
    benchmark(_EventHooksRegistry.from_component_class, _AlwaysFiringGrid)


class _DeepGrid(_GrandchildGrid if False else BaseGrid):
    pass


# Re-define inline to avoid forward-reference to test_hook_interop
class _L0(BaseGrid):
    f0: bool = Field(default=False, state=True)

    @on_field("f0")
    def _h0(self) -> None:
        pass


class _L1(_L0):
    f1: bool = Field(default=False, state=True)

    @on_field("f1")
    def _h1(self) -> None:
        pass


class _L2(_L1):
    f2: bool = Field(default=False, state=True)

    @on_field("f2")
    def _h2(self) -> None:
        pass


class _L3(_L2):
    f3: bool = Field(default=False, state=True)

    @on_field("f3")
    def _h3(self) -> None:
        pass


def test_bench_registry_deep_inheritance(benchmark) -> None:
    benchmark(_EventHooksRegistry.from_component_class, _L3)
