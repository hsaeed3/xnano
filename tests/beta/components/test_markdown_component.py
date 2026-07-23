"""Tests for beta Markdown component (not the document runner)."""

from __future__ import annotations

import pathlib

from xnano.beta.components.component import ComponentRenderContext
from xnano.beta.components.markdown import Markdown
from xnano.beta.components.text import Text
from xnano.beta.core import Runtime
from xnano.beta.core.content import TextBlock
from xnano.beta.types import Area


def _ctx() -> ComponentRenderContext[None]:
    return ComponentRenderContext(area=Area(x=0, y=0, width=40, height=10))


def test_markdown_defaults() -> None:
    document = Markdown("# Hello")
    assert document.markdown is True
    assert document.images is True
    assert document.links is True
    assert document.base_path is None
    assert document.content == "# Hello"
    assert isinstance(document, Text)


def test_markdown_base_path_and_flags() -> None:
    root = pathlib.Path("/tmp/docs")
    document = Markdown(
        "see [a](./a.md)",
        base_path=root,
        images=False,
        links=True,
    )
    assert document.base_path == root
    assert document.images is False
    assert document.links is True


def test_markdown_compose_uses_markup() -> None:
    document = Markdown("# Title\n\nBody")
    content = document.compose(_ctx())
    assert isinstance(content, TextBlock)
    assert content.lines  # parsed into run lines


def test_markdown_is_not_input() -> None:
    document = Markdown("hi")
    assert document.input is False
    assert document.focusable is False


def test_offscreen_render_smoke() -> None:
    runtime = Runtime.offscreen(40, 10)
    try:
        frame = runtime.render(Markdown("# Hello"))
        assert "Hello" in frame.text
    finally:
        runtime.close()
