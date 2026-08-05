"""tests.test_effects

---

Covers ``grid_effect`` end to end through the public API: that an effect
actually changes rendered output, that it advances across frames without
blocking hook logic, and that the handle's ``cancel``/context-manager
forms stop it.

Existing effect coverage asserted only that ``grid_play_effect`` returned
``True`` — which merely means the field had a painted rect. These tests
inspect the rendered cells instead.
"""

from __future__ import annotations

import time
import warnings

import pytest

from xnano.actions import TickAction
from xnano.effects import Effect, EffectHandle, FadeEffect
from xnano.fields import Field
from xnano.grids import BaseGrid
from xnano.hooks import on_tick
from xnano.terminal import Terminal


class _App(BaseGrid):
    body: str = Field(default="EFFECTTEXT", background="black")


def _attached(cols: int = 24, rows: int = 6):
    terminal = Terminal.offscreen(cols=cols, rows=rows)
    grid = _App()
    terminal.attach_grid(grid)
    terminal.render()  # records effect areas for the fields
    return terminal, grid


def test_effect_changes_rendered_cells() -> None:
    """The whole point: playing an effect must alter painted output."""
    terminal, grid = _attached()
    try:
        before = terminal.get_output_as_ansi()
        handle = grid.grid_effect(
            "paint_fg", color="#ff0000", duration_ms=400, fields=["body"]
        )
        assert handle
        terminal.render()
        after = terminal.get_output_as_ansi()
        assert after != before
        assert "38;2;255;0;0" in after
    finally:
        terminal.close()


def test_effect_advances_across_frames_and_completes() -> None:
    terminal, grid = _attached()
    try:
        grid.grid_effect("fade", duration_ms=60, fields=["body"])
        terminal.render()
        assert terminal.runtime.is_animating()
        time.sleep(0.12)
        terminal.render()
        assert not terminal.runtime.is_animating()
    finally:
        terminal.close()


def test_starting_an_effect_does_not_block() -> None:
    """``duration_ms`` is an animation length, never a sleep."""
    terminal, grid = _attached()
    try:
        started = time.monotonic()
        grid.grid_effect("fade", duration_ms=5_000, fields=["body"])
        assert time.monotonic() - started < 1.0
    finally:
        terminal.close()


def test_handle_cancel_stops_the_effect() -> None:
    terminal, grid = _attached()
    try:
        handle = grid.grid_effect("fade", duration_ms=5_000, fields=["body"])
        terminal.render()
        assert terminal.runtime.is_animating()
        assert handle.active
        handle.cancel()
        terminal.render()
        assert not terminal.runtime.is_animating()
        assert not handle.active
    finally:
        terminal.close()


def test_cancel_is_idempotent() -> None:
    terminal, grid = _attached()
    try:
        handle = grid.grid_effect("fade", duration_ms=500, fields=["body"])
        handle.cancel()
        handle.cancel()
        assert not handle.active
    finally:
        terminal.close()


def test_context_manager_scopes_the_effect_to_the_block() -> None:
    terminal, grid = _attached()
    try:
        with grid.grid_effect("fade", fields=["body"]) as handle:
            terminal.render()
            assert terminal.runtime.is_animating()
            assert handle.active
        terminal.render()
        assert not terminal.runtime.is_animating()
    finally:
        terminal.close()


def test_context_manager_effect_outlives_its_default_duration() -> None:
    """Without an explicit duration the block-scoped effect loops.

    A plain 300ms effect would finish on its own well inside this block.
    """
    terminal, grid = _attached()
    try:
        with grid.grid_effect("fade", fields=["body"]):
            terminal.render()
            time.sleep(0.45)
            terminal.render()
            assert terminal.runtime.is_animating()
        terminal.render()
        assert not terminal.runtime.is_animating()
    finally:
        terminal.close()


def test_context_manager_cancels_even_when_the_block_raises() -> None:
    terminal, grid = _attached()
    try:
        with pytest.raises(RuntimeError):
            with grid.grid_effect("fade", fields=["body"]):
                terminal.render()
                raise RuntimeError("boom")
        terminal.render()
        assert not terminal.runtime.is_animating()
    finally:
        terminal.close()


def test_key_dedupes_repeated_starts_instead_of_stacking() -> None:
    terminal, grid = _attached()
    try:
        first = grid.grid_effect(
            "fade", duration_ms=500, fields=["body"], key="spin"
        )
        for _ in range(5):
            grid.grid_effect(
                "fade", duration_ms=500, fields=["body"], key="spin"
            )
        assert first.keys == ("spin:body",)
        # One key means one registered effect; cancelling it stops
        # everything rather than leaving four more running.
        terminal.render()
        assert terminal.runtime.is_animating()
        first.cancel()
        terminal.render()
        assert not terminal.runtime.is_animating()
    finally:
        terminal.close()


def test_effect_from_on_tick_does_not_stall_other_hook_logic() -> None:
    class TickApp(BaseGrid):
        body: str = Field(default="TICKING", background="black")
        ticks: int = Field(default=0, state=True)

        @on_tick
        def _pulse(self) -> None:
            self.ticks += 1
            self.grid_effect(
                "fade", duration_ms=200, fields=["body"], key="pulse"
            )

    terminal = Terminal.offscreen(cols=24, rows=6)
    try:
        grid = TickApp()
        terminal.attach_grid(grid)
        terminal.render()
        for _ in range(5):
            terminal.runtime.perform(TickAction(interval_ms=16))
            terminal.render()
        # The hook kept running on every tick while the effect played.
        assert grid.ticks >= 5
    finally:
        terminal.close()


def test_handle_is_falsy_when_no_field_matched() -> None:
    terminal, grid = _attached()
    try:
        handle = grid.grid_effect("fade", fields=["does_not_exist"])
        assert not handle
        assert handle.keys == ()
        assert not handle.active
        handle.cancel()
    finally:
        terminal.close()


def test_handle_without_runtime_is_inert() -> None:
    handle = EffectHandle()
    assert not handle
    assert not handle.active
    handle.cancel()


def test_effect_instances_are_accepted_alongside_kind_strings() -> None:
    terminal, grid = _attached()
    try:
        assert grid.grid_effect(FadeEffect(duration_ms=50), fields=["body"])
        assert grid.grid_effect(
            Effect("coalesce", duration_ms=50), fields=["body"]
        )
    finally:
        terminal.close()


def test_grid_play_effect_still_works_and_warns() -> None:
    terminal, grid = _attached()
    try:
        with pytest.warns(DeprecationWarning):
            played = grid.grid_play_effect(
                "fade", duration_ms=100, fields=["body"]
            )
        assert played is True
        with pytest.warns(DeprecationWarning):
            assert grid.grid_play_effect("fade", fields=["missing"]) is False
    finally:
        terminal.close()


def test_grid_effect_is_the_non_deprecated_path() -> None:
    terminal, grid = _attached()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            assert grid.grid_effect("fade", fields=["body"])
    finally:
        terminal.close()
