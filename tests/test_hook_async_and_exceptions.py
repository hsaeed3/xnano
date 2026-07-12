"""Tests for async @on_* hooks and the hook exception policy."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from xnano._dispatch import invoke_hook, pump_tick, run_awaitable
from xnano._function_hooks import _EventHooksRegistry
from xnano.context import Context
from xnano.core.exceptions import Exit, HookError
from xnano.events import on_tick
from xnano.fields import Field
from xnano.grid import BaseGrid


def _ctx() -> Context[Any]:
    return Context(event=None, terminal=cast(Any, None), state=None)


# ---------------------------------------------------------------------------
# run_awaitable
# ---------------------------------------------------------------------------


async def _async_value(value: int) -> int:
    await asyncio.sleep(0)
    return value


def test_run_awaitable_resolves_coroutine() -> None:
    assert run_awaitable(_async_value(7)) == 7


def test_run_awaitable_rejects_nested_loop() -> None:
    async def _inner() -> None:
        coro = _async_value(1)
        try:
            run_awaitable(coro)
        finally:
            # run_awaitable raises before scheduling; close to avoid warnings.
            coro.close()

    with pytest.raises(RuntimeError, match="already active"):
        asyncio.run(_inner())


# ---------------------------------------------------------------------------
# invoke_hook — async handlers
# ---------------------------------------------------------------------------


class _AsyncTickGrid(BaseGrid):
    count: int = Field(default=0, state=True)

    @on_tick
    async def _tick(self) -> None:
        await asyncio.sleep(0)
        self.count += 1


def test_invoke_hook_awaits_async_bound_method() -> None:
    grid = _AsyncTickGrid()
    invoke_hook(grid._tick, grid, _ctx())
    assert grid.count == 1


def test_pump_tick_awaits_async_handler() -> None:
    grid = _AsyncTickGrid()
    terminal = MagicMock()
    terminal.state = None
    terminal._hooks = MagicMock()
    terminal._hooks.on_tick_hooks = [
        {
            "interval": 0,
            "handler": grid._tick,
            "last_fire_ms": 0.0,
        }
    ]
    terminal._hooks.on_state_hooks = []
    terminal._hooks.on_field_hooks = []
    terminal._attached_frame_grids = [grid]

    pump_tick(cast(Any, terminal))
    assert grid.count == 1


async def _free_async_hook(ctx: Context[Any]) -> str:
    await asyncio.sleep(0)
    return "ok"


def test_invoke_hook_awaits_free_async_function() -> None:
    result = invoke_hook(_free_async_hook, None, _ctx())
    assert result == "ok"


# ---------------------------------------------------------------------------
# Exception policy — log + re-raise; Exit propagates cleanly
# ---------------------------------------------------------------------------


class _BoomGrid(BaseGrid):
    @on_tick
    def _explode(self) -> None:
        raise ValueError("boom")


class _ExitGrid(BaseGrid):
    @on_tick
    def _leave(self) -> None:
        raise Exit()


def test_invoke_hook_logs_and_reraises() -> None:
    grid = _BoomGrid()
    with pytest.raises(ValueError, match="boom"):
        invoke_hook(grid._explode, grid, _ctx())


def test_invoke_hook_logs_exception_record(
    caplog: pytest.LogCaptureFixture,
) -> None:
    grid = _BoomGrid()
    with caplog.at_level(logging.ERROR, logger="xnano.hooks"):
        with pytest.raises(ValueError):
            invoke_hook(grid._explode, grid, _ctx())
    assert any(
        "Uncaught exception in hook" in record.message
        for record in caplog.records
    )


def test_invoke_hook_propagates_exit_without_logging(
    caplog: pytest.LogCaptureFixture,
) -> None:
    grid = _ExitGrid()
    with caplog.at_level(logging.ERROR, logger="xnano.hooks"):
        with pytest.raises(Exit):
            invoke_hook(grid._leave, grid, _ctx())
    assert not any(
        "Uncaught exception" in record.message for record in caplog.records
    )


def test_async_hook_exception_is_logged_and_reraised(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class _AsyncBoom(BaseGrid):
        @on_tick
        async def _explode(self) -> None:
            await asyncio.sleep(0)
            raise RuntimeError("async boom")

    grid = _AsyncBoom()
    with caplog.at_level(logging.ERROR, logger="xnano.hooks"):
        with pytest.raises(RuntimeError, match="async boom"):
            invoke_hook(grid._explode, grid, _ctx())
    assert any(
        "Uncaught exception in hook" in record.message
        for record in caplog.records
    )


def test_hook_error_wraps_cause() -> None:
    cause = ValueError("inner")
    error = HookError("MyGrid._on_tick", cause)
    assert error.hook_name == "MyGrid._on_tick"
    assert error.cause is cause
    assert error.__cause__ is cause
    assert "MyGrid._on_tick" in str(error)


def test_async_hook_can_raise_exit() -> None:
    class _Ready(BaseGrid):
        ready: bool = Field(default=True, state=True)

        @on_tick
        async def _leave(self) -> None:
            await asyncio.sleep(0)
            raise Exit()

    grid = _Ready()
    with pytest.raises(Exit):
        invoke_hook(grid._leave, grid, _ctx())


def test_registry_collects_async_tick() -> None:
    registry = _EventHooksRegistry.from_component_class(_AsyncTickGrid)
    assert len(registry.on_tick_hooks) == 1
