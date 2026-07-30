"""Tests for Link component."""

from __future__ import annotations

from typing import Any, cast

from xnano.actions import Action
from xnano.components.component import ComponentRenderContext
from xnano.components.link import Link
from xnano.components.text import Text
from xnano.core import Runtime
from xnano.core.content import TextBlock
from xnano.fields import Field
from xnano.grids import BaseGrid
from xnano.hooks import on_keyboard
from xnano.types import Area


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


def test_link_label_assignment_obeys_text_limits() -> None:
    link = Link("documentation", url="/docs", max_length=4, cursor=99)
    link.value = "reference"
    assert link.value == "refe"
    assert link.content == "refe"
    assert link.cursor == 4


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


def test_visited_link_uses_default_visited_cue() -> None:
    link = Link("docs", url="/docs", visited=True)
    content = link.compose(_ctx())
    assert isinstance(content, TextBlock)
    assert content.color == "magenta"


def test_link_activation_keys_not_consumed() -> None:
    link = Link(
        "go",
        url="https://example.com",
        passthrough=("ctrl+p",),
    )

    class _K:
        kind = "press"
        character = None

        def matches(self, *bindings: str) -> bool:
            return any(key in bindings for key in ("enter", "space"))

    assert link.handle_keyboard(cast(Any, _K())) is False

    class _Passthrough:
        def matches(self, *bindings: str) -> bool:
            return "ctrl+p" in bindings

    assert link.handle_keyboard(cast(Any, _Passthrough())) is False


def test_link_activation_updates_composed_navigation() -> None:
    class Navigation(BaseGrid, direction="vertical"):
        docs: Link = Field(
            default_factory=lambda: Link(
                [Text("API ", modifiers=("bold",)), Text("docs")],
                url="https://example.com/docs",
                focused_color="cyan",
            ),
            group="docs",
            height=1,
        )
        status: str = Field(default="Not visited", height=1)

        @on_keyboard("enter")
        def visit_docs(self) -> None:
            self.docs.visited = True
            self.status = self.docs.url

    runtime = Runtime.offscreen(40, 4)
    try:
        navigation = Navigation()
        runtime.set_root(navigation)
        assert runtime.focus("docs")
        assert "API docs" in runtime.render().text

        runtime.perform(Action.keyboard("enter"))
        frame = runtime.render()
        assert navigation.docs.visited is True
        assert "https://example.com/docs" in frame.text
        assert navigation.docs.color == "blue"
        assert navigation.docs.modifiers == ()
    finally:
        runtime.close()
