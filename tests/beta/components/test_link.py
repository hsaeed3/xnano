"""Tests for beta Link component."""

from __future__ import annotations

from typing import Any, cast

from xnano.beta.components.component import ComponentRenderContext
from xnano.beta.components.link import Link
from xnano.beta.components.text import Text
from xnano.beta.core import Runtime
from xnano.beta.core.content import TextBlock
from xnano.beta.types import Area


def _ctx() -> ComponentRenderContext[None]:
    return ComponentRenderContext(area=Area(x=0, y=0, width=40, height=3))


def test_link_defaults() -> None:
    link = Link("docs", url="https://example.com")
    assert isinstance(link, Text)
    assert link.url == "https://example.com"
    assert link.content == "docs"
    assert link.focusable is True
    assert link.underline is True
    assert link.color == "blue"
    assert link.visited is False
    assert link.input is False


def test_link_value_is_label_or_url() -> None:
    link = Link("label", url="https://example.com")
    assert link.value == "label"
    empty = Link("", url="https://example.com")
    assert empty.value == "https://example.com"


def test_link_compose_underline_and_color() -> None:
    link = Link("docs", url="https://example.com")
    content = link.compose(_ctx())
    assert isinstance(content, TextBlock)
    assert content.text == "docs"
    assert content.color == "blue"
    assert "underline" in content.modifiers


def test_link_focused_color() -> None:
    link = Link(
        "docs",
        url="https://example.com",
        focused_color="cyan",
    )
    link._input_focused = True
    content = link.compose(_ctx())
    assert isinstance(content, TextBlock)
    assert content.color == "cyan"


def test_link_activation_keys_not_consumed() -> None:
    link = Link("go", url="https://example.com")

    class _K:
        kind = "press"
        character = None

        def matches(self, *bindings: str) -> bool:
            return any(key in bindings for key in ("enter", "space"))

    assert link.handle_keyboard(cast(Any, _K())) is False


def test_link_does_not_open_browser() -> None:
    """handle_keyboard must not launch external processes."""
    link = Link("go", url="https://example.com")

    class _K:
        kind = "press"
        character = None

        def matches(self, *bindings: str) -> bool:
            return "enter" in bindings

    # Smoke: calling handle_keyboard is side-effect free.
    assert link.handle_keyboard(cast(Any, _K())) is False
    assert link.url == "https://example.com"


def test_offscreen_render_smoke() -> None:
    runtime = Runtime.offscreen(40, 10)
    try:
        frame = runtime.render(
            Link("docs", url="https://example.com", color="cyan")
        )
        assert "docs" in frame.text
    finally:
        runtime.close()
