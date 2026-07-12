"""CoreSession query and state mirror tests."""

from __future__ import annotations

from xnano_core.rust.engine import (
    CoreRenderContent,
    CoreRenderNode,
    CoreSession,
)
from xnano_core.rust.native import ClearType


def test_offscreen_title_roundtrip(offscreen_session: CoreSession) -> None:
    offscreen_session.set_title("pytest-title")
    assert offscreen_session.get_title() == "pytest-title"


def test_get_size_queries_terminal(offscreen_session: CoreSession) -> None:
    size = offscreen_session.get_size()
    assert size.width > 0
    assert size.height > 0


def test_clear_and_scroll_do_not_raise(offscreen_session: CoreSession) -> None:
    offscreen_session.clear(ClearType.All)
    offscreen_session.scroll_up(1)
    offscreen_session.scroll_down(1)


def test_cursor_hint_smoke(
    offscreen_session: CoreSession, sample_paragraph
) -> None:
    node = CoreRenderNode(
        content=CoreRenderContent.widget(sample_paragraph),
        cursor_hint=(1, 1),
    )
    offscreen_session.render(node)
    # Cursor hints are consumed during render; offscreen has no live cursor.
    assert offscreen_session.buffer_snapshot().area.width == 40
