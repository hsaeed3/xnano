"""Tests for xnano.components.progress — declarative Progress."""

from __future__ import annotations

from helpers import render_component_to_text

from xnano.components.abstract import ComponentRenderContext
from xnano.components.progress import Progress
from xnano.tui.nodes import (
    LineGaugeNode,
    ProgressBarNode,
)
from xnano._types import Area


def _ctx() -> ComponentRenderContext:
    return ComponentRenderContext(area=Area(x=0, y=0, width=40, height=3))


# ---------------------------------------------------------------------------
# Ratio derivation
# ---------------------------------------------------------------------------


def test_ratio_from_direct_value() -> None:
    assert Progress(value=0.6).ratio == 0.6


def test_ratio_from_value_and_total() -> None:
    assert Progress(value=70, total=100).ratio == 0.7


def test_ratio_clamps_above_one() -> None:
    assert Progress(value=1.5).ratio == 1.0
    assert Progress(value=150, total=100).ratio == 1.0


def test_ratio_clamps_below_zero() -> None:
    assert Progress(value=-0.2).ratio == 0.0


def test_ratio_zero_total_is_zero() -> None:
    assert Progress(value=5, total=0).ratio == 0.0
    assert Progress(value=5, total=-10).ratio == 0.0


def test_ratio_none_total_uses_value() -> None:
    assert Progress(value=0.25, total=None).ratio == 0.25


# ---------------------------------------------------------------------------
# Label resolution
# ---------------------------------------------------------------------------


def test_auto_label_is_percentage() -> None:
    node = Progress(value=0.7).get_terminal_node(_ctx())
    assert isinstance(node, ProgressBarNode)
    assert node.label == "70%"


def test_auto_label_from_value_total() -> None:
    node = Progress(value=1, total=3).get_terminal_node(_ctx())
    assert isinstance(node, ProgressBarNode)
    assert node.label == "33%"


def test_explicit_label() -> None:
    node = Progress(value=0.5, label="half").get_terminal_node(_ctx())
    assert isinstance(node, ProgressBarNode)
    assert node.label == "half"


def test_label_false_hides_label() -> None:
    node = Progress(value=0.5, label=False).get_terminal_node(_ctx())
    assert isinstance(node, ProgressBarNode)
    assert node.label is None


# ---------------------------------------------------------------------------
# Style dispatch
# ---------------------------------------------------------------------------


def test_bar_style_yields_progress_bar_node() -> None:
    node = Progress(value=0.4, style="bar").get_terminal_node(_ctx())
    assert isinstance(node, ProgressBarNode)
    assert node.progress == 0.4


def test_line_style_yields_line_gauge_node() -> None:
    node = Progress(value=0.4, style="line").get_terminal_node(_ctx())
    assert isinstance(node, LineGaugeNode)
    assert node.progress == 0.4


def test_line_style_uses_filled_color_fallback() -> None:
    node = Progress(value=0.5, style="line", color="cyan").get_terminal_node(
        _ctx()
    )
    assert isinstance(node, LineGaugeNode)
    assert node.filled_color == "cyan"


def test_line_style_explicit_filled_and_unfilled() -> None:
    node = Progress(
        value=0.5,
        style="line",
        filled_color="green",
        unfilled_color="gray",
    ).get_terminal_node(_ctx())
    assert isinstance(node, LineGaugeNode)
    assert node.filled_color == "green"
    assert node.unfilled_color == "gray"


def test_bar_threads_color_and_background() -> None:
    node = Progress(
        value=0.5, color="blue", background="black"
    ).get_terminal_node(_ctx())
    assert isinstance(node, ProgressBarNode)
    assert node.color == "blue"
    assert node.background == "black"


def test_threads_z_and_visible() -> None:
    node = Progress(value=0.1, z=3, visible=False).get_terminal_node(_ctx())
    assert isinstance(node, ProgressBarNode)
    assert node.z == 3
    assert node.visible is False


# ---------------------------------------------------------------------------
# Offscreen render
# ---------------------------------------------------------------------------


def test_render_bar_shows_percentage() -> None:
    out = render_component_to_text(Progress(value=0.7), width=30, height=3)
    assert "70%" in out


def test_render_line_shows_label() -> None:
    out = render_component_to_text(
        Progress(value=0.4, style="line", label="cpu"),
        width=30,
        height=3,
    )
    assert "cpu" in out


def test_render_empty_progress_is_safe() -> None:
    out = render_component_to_text(Progress(value=0.0), width=20, height=3)
    assert isinstance(out, str)


def test_render_full_progress_is_safe() -> None:
    out = render_component_to_text(Progress(value=1.0), width=20, height=3)
    assert isinstance(out, str)
