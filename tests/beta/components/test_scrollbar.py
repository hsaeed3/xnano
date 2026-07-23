"""Tests for beta ``Scrollbar``."""

from __future__ import annotations

from typing import Any, cast

from xnano.beta.components.component import ComponentRenderContext
from xnano.beta.components.scrollbar import Scrollbar
from xnano.beta.core import Runtime
from xnano.beta.core.content import Scrollbar as ScrollbarContent
from xnano.beta.types import Area


def _ctx() -> ComponentRenderContext[Any]:
    return ComponentRenderContext(area=Area(x=0, y=0, width=1, height=10))


def _node(bar: Scrollbar) -> Any:
    content = bar.compose(_ctx())
    assert isinstance(content, ScrollbarContent)
    return content


def test_compose_native_scrollbar() -> None:
    bar = Scrollbar(
        content_length=100,
        position=20,
        viewport_length=10,
        orientation="vertical_right",
        color="gray",
        thumb_color="white",
    )
    node = _node(bar)
    assert node.content_length == 100
    assert node.position == 20
    assert node.viewport_length == 10
    assert node.orientation == "vertical_right"
    assert node.color == "gray"
    assert node.thumb_color == "white"


def test_clamp_negative_lengths() -> None:
    bar = Scrollbar(content_length=-5, position=-2, viewport_length=-1)
    bar._clamp_state()
    assert bar.content_length == 0
    assert bar.position == 0
    assert bar.viewport_length == 0


def test_clamp_position_to_content() -> None:
    bar = Scrollbar(content_length=50, position=999, viewport_length=10)
    bar._clamp_state()
    assert bar.position == 40


def test_begin_end_symbols() -> None:
    bar = Scrollbar(
        content_length=20,
        position=0,
        viewport_length=5,
        begin="▲",
        end="▼",
    )
    node = _node(bar)
    assert node.begin_symbol == "▲"
    assert node.end_symbol == "▼"


def test_horizontal_orientation() -> None:
    bar = Scrollbar(
        content_length=80,
        position=10,
        viewport_length=20,
        orientation="horizontal_bottom",
    )
    node = _node(bar)
    assert node.orientation == "horizontal_bottom"


def test_from_scroll_handle() -> None:
    class _Handle:
        offset = 7
        follow = True

    bar = Scrollbar.from_scroll_handle(
        cast(Any, _Handle()),
        content_length=40,
        viewport_length=8,
        thumb_color="cyan",
    )
    assert bar.position == 7
    assert bar.content_length == 40
    assert bar.viewport_length == 8
    assert bar.thumb_color == "cyan"

    # Live handle updates are picked up on compose.
    _Handle.offset = 12
    node = _node(bar)
    assert node.position == 12


def test_runtime_offscreen_render_smoke() -> None:
    runtime = Runtime.offscreen(4, 12)
    try:
        frame = runtime.render(
            Scrollbar(
                content_length=100,
                position=25,
                viewport_length=10,
            )
        )
        assert isinstance(frame.text, str)
    finally:
        runtime.close()
