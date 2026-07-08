"""CoreSession behaviour using the offscreen backend (no TTY required)."""

from __future__ import annotations

import time

import pytest

from xnano_core.rust.native import Color, paint_fg, sleep_effect
from xnano_core.rust.engine import (
    CoreRenderContent,
    CoreRenderNode,
    CoreSession,
)


def test_offscreen_factory_sets_frame_area() -> None:
    session = CoreSession.offscreen(50, 20)
    area = session.get_last_frame_area()
    assert area is not None
    assert area.width == 50
    assert area.height == 20


def test_render_updates_buffer_snapshot(
    offscreen_session: CoreSession, column_tree: CoreRenderNode
) -> None:
    offscreen_session.render(column_tree)
    snapshot = offscreen_session.buffer_snapshot()
    assert snapshot.area.width == 40
    assert snapshot.area.height == 12
    assert any("hello" in line for line in snapshot.to_string_lines())


def test_context_manager_restore_offscreen() -> None:
    with CoreSession.offscreen(10, 5) as session:
        session.render(CoreRenderNode.leaf(CoreRenderContent.empty()))
    # Offscreen sessions have no terminal; restore must not raise.


def test_device_state_defaults_offscreen(
    offscreen_session: CoreSession,
) -> None:
    assert not offscreen_session.is_raw_mode_enabled()
    assert not offscreen_session.is_mouse_capture_enabled()
    assert not offscreen_session.is_bracketed_paste_enabled()
    assert not offscreen_session.is_focus_change_enabled()
    assert not offscreen_session.is_alternate_screen_enabled()
    assert not offscreen_session.is_cursor_visible()


def test_offscreen_is_not_inline(offscreen_session: CoreSession) -> None:
    assert offscreen_session.is_inline() is False
    assert offscreen_session.get_inline_height() is None


def test_poll_event_returns_none_without_tick_clock(
    offscreen_session: CoreSession,
) -> None:
    # Offscreen sessions disable the tick clock; poll should time out cleanly.
    assert offscreen_session.poll_event(timeout_ms=1) is None


def test_offscreen_get_terminal_raises(offscreen_session: CoreSession) -> None:
    with pytest.raises(RuntimeError, match="no live terminal"):
        offscreen_session.get_terminal()


def test_is_animating_becomes_false_after_effect_completes(
    offscreen_session: CoreSession,
    column_tree: CoreRenderNode,
) -> None:
    offscreen_session.add_effect(sleep_effect(50))
    offscreen_session.render(column_tree)
    assert offscreen_session.is_animating()
    time.sleep(0.15)
    offscreen_session.render(column_tree)
    assert not offscreen_session.is_animating()


def test_cancel_effect_stops_animation(
    offscreen_session: CoreSession,
    column_tree: CoreRenderNode,
) -> None:
    offscreen_session.add_unique_effect("pulse", paint_fg(Color.BLUE, 500))
    offscreen_session.render(column_tree)
    assert offscreen_session.is_animating()
    offscreen_session.cancel_effect("pulse")
    offscreen_session.render(column_tree)
    assert not offscreen_session.is_animating()


def test_effects_processed_during_render(
    offscreen_session: CoreSession, column_tree: CoreRenderNode
) -> None:
    effect = paint_fg(Color.RED, 300)
    offscreen_session.add_effect(effect)
    offscreen_session.render(column_tree)
    assert offscreen_session.is_animating()


def test_unique_effect_lifecycle(
    offscreen_session: CoreSession, column_tree: CoreRenderNode
) -> None:
    effect = paint_fg(Color.BLUE, 250)
    offscreen_session.add_unique_effect("pulse", effect)
    offscreen_session.render(column_tree)
    assert offscreen_session.is_animating()
    offscreen_session.cancel_effect("pulse")
    offscreen_session.render(column_tree)


def test_effect_area_binding_with_unique_effect(
    offscreen_session: CoreSession, sample_paragraph
) -> None:
    node = CoreRenderNode(
        content=CoreRenderContent.widget(sample_paragraph),
        effect_key="banner",
    )
    effect = paint_fg(Color.GREEN, 200)
    offscreen_session.render(node)
    area = offscreen_session.effect_area_for("banner")
    assert area is not None
    bound = effect.with_area(area)
    offscreen_session.add_unique_effect("banner-fx", bound)
    offscreen_session.render(node)
    assert offscreen_session.is_animating()
