"""Tests for the web cell-frame serializer and offscreen renderer."""

from __future__ import annotations

from xnano import BaseGrid, Field
from xnano.components.table import Table
from xnano.components.text import Text
from xnano.web.frame import (
    MOD_BOLD,
    build_frame,
    color_to_web,
)
from xnano.web.render import WebRenderer


def _row_text(spans: list[list[object]]) -> str:
    return "".join(str(span[0]) for span in spans)


# ---------------------------------------------------------------------------
# color_to_web
# ---------------------------------------------------------------------------


class _FakeColor:
    def __init__(self, rep: str) -> None:
        self._rep = rep

    def __repr__(self) -> str:
        return self._rep


def test_named_color_to_hex() -> None:
    assert color_to_web(_FakeColor("Red")) == "#cd0000"
    assert color_to_web(_FakeColor("LightRed")) == "#ff0000"


def test_rgb_color_to_hex() -> None:
    assert color_to_web(_FakeColor("Rgb(1, 2, 3)")) == "#010203"


def test_indexed_color_to_hex() -> None:
    assert color_to_web(_FakeColor("Indexed(196)")) == "#ff0000"


def test_reset_color_is_none() -> None:
    assert color_to_web(_FakeColor("Reset")) is None


# ---------------------------------------------------------------------------
# build_frame diffing
# ---------------------------------------------------------------------------


def test_first_frame_is_full() -> None:
    rows = ((("hi", "#ff0000", None, MOD_BOLD),), ((" ", None, None, 0),))
    frame = build_frame(rows, width=2, height=2, cursor=None, previous=None)
    assert frame["full"] is True
    assert set(frame["rows"]) == {"0", "1"}
    assert frame["rows"]["0"] == [["hi", "#ff0000", None, MOD_BOLD]]


def test_diff_sends_only_changed_rows() -> None:
    a = ((("a", None, None, 0),), (("b", None, None, 0),))
    b = ((("a", None, None, 0),), (("B", None, None, 0),))
    frame = build_frame(b, width=1, height=2, cursor=None, previous=a)
    assert frame["full"] is False
    assert set(frame["rows"]) == {"1"}


def test_resize_forces_full_frame() -> None:
    a = ((("a", None, None, 0),),)
    b = ((("a", None, None, 0),), (("b", None, None, 0),))
    frame = build_frame(b, width=1, height=2, cursor=None, previous=a)
    assert frame["full"] is True


# ---------------------------------------------------------------------------
# WebRenderer (real engine)
# ---------------------------------------------------------------------------


def test_renderer_emits_styled_cells() -> None:
    class Hello(BaseGrid):
        title: Text = Field(default=Text("Hello", color="red"))

    renderer = WebRenderer(Hello(), cols=10, rows=2)
    try:
        frame = renderer.frame()
        assert frame["full"] is True
        first = frame["rows"]["0"]
        assert _row_text(first).startswith("Hello")
        assert first[0][1] == "#ff0000"
    finally:
        renderer.close()


def test_unchanged_second_frame_is_empty_diff() -> None:
    class Hello(BaseGrid):
        title: Text = Field(default=Text("Hi"))

    renderer = WebRenderer(Hello(), cols=8, rows=2)
    try:
        renderer.frame()
        second = renderer.frame()
        assert second["full"] is False
        assert second["rows"] == {}
    finally:
        renderer.close()


def test_table_renders_on_web_without_web_code() -> None:
    """The headline: a component with no get_web_node renders on web."""

    class Dash(BaseGrid):
        table: Table = Field(default=Table(data=[{"name": "ada", "n": 1}]))

    renderer = WebRenderer(Dash(), cols=24, rows=4)
    try:
        frame = renderer.frame()
        text = "\n".join(_row_text(frame["rows"][str(y)]) for y in range(4))
        assert "Name" in text
        assert "ada" in text
    finally:
        renderer.close()
