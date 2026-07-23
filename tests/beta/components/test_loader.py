"""Tests for beta ``Loader`` (progress + spinner)."""

from __future__ import annotations

import time
from typing import Any

import pytest

from xnano.beta.components.component import ComponentRenderContext
from xnano.beta.components.loader import (
    Loader,
    resolve_loader_symbols,
)
from xnano.beta.core import Runtime
from xnano.beta.core.content import Gauge, LineGauge, TextBlock
from xnano.beta.types import Area


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
