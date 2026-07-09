"""Tests for the @on_poll hook decorator and pump_poll dispatch."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from xnano.beta import Field, Grid, on_poll
from xnano.beta.core.dispatch import pump_events, pump_poll
from xnano.beta.hooks import (
    PollWhen,
    _EventHooksRegistry,
    _OnPollHookFunctionEntry,
)


# ---------------------------------------------------------------------------
# Decorator registration
# ---------------------------------------------------------------------------


class _IdleGrid(Grid):
    idle_count: int = Field(default=0, state=True)
    frame_count: int = Field(default=0, state=True)

    @on_poll
    def _on_idle(self) -> None:
        self.idle_count += 1

    @on_poll("frame")
    def _on_frame(self) -> None:
        self.frame_count += 1


class _KeywordIdleGrid(Grid):
    hits: int = Field(default=0, state=True)

    @on_poll(when="idle")
    def _on_idle(self) -> None:
        self.hits += 1


def test_on_poll_bare_defaults_to_idle() -> None:
    method = _IdleGrid.__dict__["_on_idle"]
    assert hasattr(method, _EventHooksRegistry.ON_POLL_HOOK_ATTR)
    assert getattr(method, _EventHooksRegistry.ON_POLL_WHEN_ATTR) == "idle"


def test_on_poll_positional_frame() -> None:
    method = _IdleGrid.__dict__["_on_frame"]
    assert getattr(method, _EventHooksRegistry.ON_POLL_WHEN_ATTR) == "frame"


def test_on_poll_keyword_when() -> None:
    method = _KeywordIdleGrid.__dict__["_on_idle"]
    assert getattr(method, _EventHooksRegistry.ON_POLL_WHEN_ATTR) == "idle"


def test_from_component_class_collects_poll_hooks() -> None:
    registry = _EventHooksRegistry.from_component_class(_IdleGrid)
    assert len(registry.on_poll_hooks) == 2
    by_when = {entry["when"]: entry for entry in registry.on_poll_hooks}
    assert set(by_when) == {"idle", "frame"}


def test_invalid_when_raises() -> None:
    with pytest.raises(TypeError, match="idle"):
        # Bypass overloads so the runtime validation path is exercised.
        cast(Any, on_poll)("nope")


# ---------------------------------------------------------------------------
# pump_poll dispatch
# ---------------------------------------------------------------------------


def _stub_terminal(grid: Grid) -> Any:
    terminal = MagicMock()
    terminal.state = None
    registry = _EventHooksRegistry.from_component_class(type(grid))
    bound: list[_OnPollHookFunctionEntry] = []
    for entry in registry.on_poll_hooks:
        handler = entry["handler"]
        name = getattr(handler, "__name__", None)
        if name and hasattr(grid, name):
            handler = getattr(grid, name)
        bound.append(
            _OnPollHookFunctionEntry(when=entry["when"], handler=handler)
        )
    terminal._hooks = MagicMock()
    terminal._hooks.on_poll_hooks = bound
    terminal._attached_frame_grids = [grid]
    return terminal


def test_pump_poll_idle_fires_only_idle_handlers() -> None:
    grid = _IdleGrid()
    terminal = _stub_terminal(grid)
    pump_poll(terminal, "idle")
    assert grid.idle_count == 1
    assert grid.frame_count == 0


def test_pump_poll_frame_fires_only_frame_handlers() -> None:
    grid = _IdleGrid()
    terminal = _stub_terminal(grid)
    pump_poll(terminal, "frame")
    assert grid.idle_count == 0
    assert grid.frame_count == 1


def test_pump_events_idle_when_poll_returns_none() -> None:
    grid = _IdleGrid()
    terminal = _stub_terminal(grid)
    session = MagicMock()
    session.poll_core_event.return_value = None
    terminal.session = session
    terminal.tick_interval = 16

    pump_events(terminal)

    assert grid.idle_count == 1
    assert grid.frame_count == 0
    session.poll_core_event.assert_called_once_with(timeout=16)


def test_pump_events_skips_idle_when_event_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    grid = _IdleGrid()
    terminal = _stub_terminal(grid)
    session = MagicMock()
    fake_event = MagicMock()
    session.poll_core_event.side_effect = [fake_event, None]
    terminal.session = session
    terminal.tick_interval = 16
    terminal._mouse_geometry_active = False

    from xnano.beta import events as events_mod

    class _FakeEvent:
        def is_mouse_event(self) -> bool:
            return False

        def is_keyboard_event(self) -> bool:
            return False

        def is_resize_event(self) -> bool:
            return False

        def is_clipboard_event(self) -> bool:
            return False

        def is_focus_event(self) -> bool:
            return False

    monkeypatch.setattr(
        events_mod, "Event", lambda core: _FakeEvent(), raising=True
    )
    pump_events(terminal)
    assert grid.idle_count == 0


def test_poll_when_values() -> None:
    values: list[PollWhen] = ["idle", "frame"]
    assert values == ["idle", "frame"]
