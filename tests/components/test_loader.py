"""Tests for ``Loader`` (progress + spinner)."""

from __future__ import annotations

import time
from typing import Any, cast

import pytest

from xnano.area import Area
from xnano.components.component import ComponentRenderContext
from xnano.components.loader import (
    Loader,
    LoaderStyle,
    resolve_loader_symbols,
)
from xnano.components.text import Text
from xnano.core import Runtime
from xnano.core.content import Gauge, LineGauge, TextBlock


def _ctx() -> ComponentRenderContext[Any]:
    return ComponentRenderContext(area=Area(x=0, y=0, width=40, height=3))


def test_resolve_dots_preset() -> None:
    frames = resolve_loader_symbols("dots")
    assert len(frames) >= 2


def test_resolve_custom_frames() -> None:
    assert resolve_loader_symbols(["a", "b", "c"]) == ("a", "b", "c")


def test_resolve_unknown_preset() -> None:
    with pytest.raises(ValueError, match="Unknown loader"):
        resolve_loader_symbols("nope")  # type: ignore[arg-type]


def test_loader_rejects_empty_symbols_style_and_interval() -> None:
    with pytest.raises(ValueError, match="at least one"):
        resolve_loader_symbols(())
    with pytest.raises(ValueError, match="Unsupported loader style"):
        Loader(style=cast(Any, "circle"))
    with pytest.raises(ValueError, match="greater than zero"):
        Loader(interval=0)


def test_ratio_from_direct_value() -> None:
    assert Loader(value=0.6, style="bar").ratio == 0.6


def test_ratio_from_value_and_total() -> None:
    assert Loader(value=70, total=100, style="bar").ratio == 0.7


def test_ratio_clamps() -> None:
    assert Loader(value=1.5, style="bar").ratio == 1.0
    assert Loader(value=-0.2, style="bar").ratio == 0.0
    assert Loader(value=5, total=0, style="bar").ratio == 0.0


def test_indeterminate_ratio_is_zero() -> None:
    assert Loader(value=None).ratio == 0.0
    assert Loader().finished is False


def test_finished_when_complete() -> None:
    assert Loader(value=1.0, style="bar").finished is True
    assert Loader(value=50, total=100, style="bar").finished is False


def test_spinner_compose_is_text_block() -> None:
    loader = Loader(symbols=["|", "/", "-", "\\"], interval=50)
    content = loader.compose(_ctx())
    assert isinstance(content, TextBlock)
    assert content.text[0] in "|/-\\"


def test_spinner_label_appended() -> None:
    loader = Loader(
        symbols=["*"],
        label="loading",
        running=False,
    )
    content = loader.compose(_ctx())
    assert isinstance(content, TextBlock)
    assert "loading" in content.text


def test_inline_spinner_uses_component_label_protocols() -> None:
    class PlainLabel:
        def plain(self) -> str:
            return "plain label"

    class StringLabel:
        def __str__(self) -> str:
            return "string label"

    plain = Loader(
        symbols=("*",),
        label=cast(Any, PlainLabel()),
        running=False,
    )
    assert plain.resolved_symbols == ("*",)
    assert plain.current_frame() == "*"
    assert plain.inline_text() == "* plain label"

    fallback = Loader(
        symbols=("*",),
        label=cast(Any, StringLabel()),
        running=False,
    )
    assert fallback.inline_text() == "* string label"
    assert Loader(symbols=("*",), running=False).inline_text() == "*"


def test_bar_style_gauge_content() -> None:
    loader = Loader(value=0.7, style="bar")
    content = loader.compose(_ctx())
    assert isinstance(content, Gauge)
    assert content.progress == pytest.approx(0.7)
    assert content.label == "70%"


def test_line_style_gauge_content() -> None:
    loader = Loader(
        value=0.4,
        style="line",
        label="cpu",
        filled_color="cyan",
        unfilled_color="gray",
    )
    content = loader.compose(_ctx())
    assert isinstance(content, LineGauge)
    assert content.label == "cpu"
    assert content.filled_color == "cyan"
    assert content.unfilled_color == "gray"


def test_label_false_hides_label() -> None:
    loader = Loader(value=0.5, style="bar", label=False)
    content = loader.compose(_ctx())
    assert isinstance(content, Gauge)
    assert content.label is None


@pytest.mark.parametrize(
    ("style", "content_type"),
    (("bar", Gauge), ("line", LineGauge)),
)
def test_indeterminate_progress_uses_composed_text_label(
    style: LoaderStyle,
    content_type: type[Gauge] | type[LineGauge],
) -> None:
    loader = Loader(
        value=None,
        style=style,
        label=Text("Syncing", foreground="cyan"),
        symbols=("*",),
        running=False,
    )
    content = loader.compose(_ctx())
    assert isinstance(content, content_type)
    assert content.progress == 0.0
    assert content.label == "* Syncing"


def test_restart_resets_epoch() -> None:
    loader = Loader(symbols=["a", "b"], interval=10_000, running=True)
    first = loader.compose(_ctx())
    assert isinstance(first, TextBlock)
    loader.restart()
    # Force epoch into the past so the next frame advances when interval is small.
    loader._epoch_ns = time.monotonic_ns() - 50_000_000
    loader.interval = 10
    second = loader.compose(_ctx())
    assert isinstance(second, TextBlock)


def test_running_false_freezes_frame() -> None:
    loader = Loader(symbols=["0", "1", "2"], interval=1, running=True)
    loader._epoch_ns = time.monotonic_ns() - 5_000_000
    content = loader.compose(_ctx())
    assert isinstance(content, TextBlock)
    frozen = content.text
    loader.running = False
    loader._epoch_ns = time.monotonic_ns() - 50_000_000
    again = loader.compose(_ctx())
    assert isinstance(again, TextBlock)
    assert again.text == frozen


def test_runtime_offscreen_spinner_smoke() -> None:
    runtime = Runtime.offscreen(30, 3)
    try:
        frame = runtime.render(Loader(label="wait", symbols=["*"]))
        assert "*" in frame.text or "wait" in frame.text
    finally:
        runtime.close()


def test_runtime_offscreen_bar_smoke() -> None:
    runtime = Runtime.offscreen(30, 3)
    try:
        frame = runtime.render(Loader(value=0.7, style="bar"))
        assert "70%" in frame.text
    finally:
        runtime.close()
