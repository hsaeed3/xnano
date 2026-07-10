"""Tests for xnano.beta.components.chart — declarative Chart."""

from __future__ import annotations

from helpers import render_component_to_text

from xnano.beta.components.abstract import ComponentRenderContext
from xnano.beta.components.chart import Chart
from xnano.beta.components.schema import Series
from xnano.beta.core.nodes import ChartNode
from xnano.beta.types import Area


def _ctx() -> ComponentRenderContext:
    return ComponentRenderContext(area=Area(x=0, y=0, width=40, height=12))


# ---------------------------------------------------------------------------
# Point normalization
# ---------------------------------------------------------------------------


def test_bare_y_values_become_indexed_points() -> None:
    node = Chart(series={"cpu": [10, 20, 30]}).get_node(_ctx())
    assert isinstance(node, ChartNode)
    assert node.datasets[0].data == [(0.0, 10.0), (1.0, 20.0), (2.0, 30.0)]


def test_xy_pairs_are_preserved() -> None:
    node = Chart(series={"load": [(1, 3), (2, 5), (4, 2)]}).get_node(_ctx())
    assert isinstance(node, ChartNode)
    assert node.datasets[0].data == [(1.0, 3.0), (2.0, 5.0), (4.0, 2.0)]


def test_mixed_list_points_normalize() -> None:
    node = Chart(series={"s": [[0, 1], [1, 2]]}).get_node(_ctx())
    assert isinstance(node, ChartNode)
    assert node.datasets[0].data == [(0.0, 1.0), (1.0, 2.0)]


# ---------------------------------------------------------------------------
# Bounds derivation
# ---------------------------------------------------------------------------


def test_auto_bounds_from_data() -> None:
    node = Chart(series={"a": [10, 50, 30]}).get_node(_ctx())
    assert isinstance(node, ChartNode)
    assert node.x_axis is not None
    assert node.y_axis is not None
    assert node.x_axis.bounds == (0.0, 2.0)
    assert node.y_axis.bounds == (10.0, 50.0)


def test_explicit_bounds_override() -> None:
    node = Chart(
        series={"a": [1, 2, 3]},
        x_bounds=(0.0, 10.0),
        y_bounds=(-5.0, 5.0),
    ).get_node(_ctx())
    assert isinstance(node, ChartNode)
    assert node.x_axis is not None
    assert node.y_axis is not None
    assert node.x_axis.bounds == (0.0, 10.0)
    assert node.y_axis.bounds == (-5.0, 5.0)


def test_flat_series_expands_bounds() -> None:
    node = Chart(series={"flat": [5, 5, 5]}).get_node(_ctx())
    assert isinstance(node, ChartNode)
    assert node.y_axis is not None
    assert node.y_axis.bounds == (5.0, 6.0)


def test_empty_series_default_bounds() -> None:
    node = Chart().get_node(_ctx())
    assert isinstance(node, ChartNode)
    assert node.x_axis is not None
    assert node.y_axis is not None
    assert node.x_axis.bounds == (0.0, 1.0)
    assert node.y_axis.bounds == (0.0, 1.0)
    assert node.datasets == []


# ---------------------------------------------------------------------------
# Multi-series + palette
# ---------------------------------------------------------------------------


def test_multi_series_creates_datasets() -> None:
    node = Chart(series={"cpu": [1, 2], "mem": [3, 4]}).get_node(_ctx())
    assert isinstance(node, ChartNode)
    assert [dataset.name for dataset in node.datasets] == ["cpu", "mem"]


def test_default_palette_cycles_colors() -> None:
    node = Chart(series={"a": [1], "b": [2], "c": [3]}).get_node(_ctx())
    assert isinstance(node, ChartNode)
    colors = [dataset.color for dataset in node.datasets]
    assert colors == ["cyan", "magenta", "green"]


def test_custom_palette() -> None:
    node = Chart(
        series={"a": [1], "b": [2]},
        colors=("red", "blue"),
    ).get_node(_ctx())
    assert isinstance(node, ChartNode)
    assert [dataset.color for dataset in node.datasets] == ["red", "blue"]


def test_kind_propagates_to_datasets() -> None:
    node = Chart(series={"a": [1, 2]}, kind="bar").get_node(_ctx())
    assert isinstance(node, ChartNode)
    assert node.datasets[0].graph_type == "bar"


def test_scatter_kind() -> None:
    node = Chart(series={"a": [1, 2]}, kind="scatter").get_node(_ctx())
    assert isinstance(node, ChartNode)
    assert node.datasets[0].graph_type == "scatter"


# ---------------------------------------------------------------------------
# Legend + axes labels
# ---------------------------------------------------------------------------


def test_legend_position_default() -> None:
    node = Chart(series={"a": [1]}).get_node(_ctx())
    assert isinstance(node, ChartNode)
    assert node.legend_position == "top_right"


def test_legend_disabled() -> None:
    node = Chart(series={"a": [1]}, legend=False).get_node(_ctx())
    assert isinstance(node, ChartNode)
    assert node.legend_position is None


def test_axis_titles() -> None:
    node = Chart(
        series={"a": [1, 2]},
        x_label="time",
        y_label="load",
    ).get_node(_ctx())
    assert isinstance(node, ChartNode)
    assert node.x_axis is not None
    assert node.y_axis is not None
    assert node.x_axis.title == "time"
    assert node.y_axis.title == "load"


def test_threads_z_and_visible() -> None:
    node = Chart(series={"a": [1]}, z=5, visible=False).get_node(_ctx())
    assert isinstance(node, ChartNode)
    assert node.z == 5
    assert node.visible is False


# ---------------------------------------------------------------------------
# Declarative subclass with Series descriptors
# ---------------------------------------------------------------------------


class Latency(Chart):
    p50 = Series(color="green")
    p99 = Series(color="red", kind="scatter", label="99th")


def test_subclass_captures_declared_series() -> None:
    assert list(Latency._declared) == ["p50", "p99"]


def test_subclass_applies_series_styling() -> None:
    node = Latency(series={"p50": [1, 2, 3], "p99": [4, 5, 6]}).get_node(
        _ctx()
    )
    assert isinstance(node, ChartNode)
    by_name = {dataset.name: dataset for dataset in node.datasets}
    assert by_name["p50"].color == "green"
    assert by_name["p50"].graph_type == "line"  # chart default
    assert by_name["99th"].color == "red"
    assert by_name["99th"].graph_type == "scatter"


def test_subclass_orders_declared_series_first() -> None:
    node = Latency(series={"extra": [9], "p99": [2], "p50": [1]}).get_node(
        _ctx()
    )
    assert isinstance(node, ChartNode)
    names = [dataset.name for dataset in node.datasets]
    assert names == ["p50", "99th", "extra"]


def test_subclass_skips_declared_series_without_data() -> None:
    node = Latency(series={"p50": [1, 2]}).get_node(_ctx())
    assert isinstance(node, ChartNode)
    assert [dataset.name for dataset in node.datasets] == ["p50"]


# ---------------------------------------------------------------------------
# Offscreen render
# ---------------------------------------------------------------------------


def test_render_chart_is_safe() -> None:
    out = render_component_to_text(
        Chart(series={"cpu": [30, 42, 38, 55], "mem": [60, 61, 63, 62]}),
        width=40,
        height=12,
    )
    assert isinstance(out, str)
    assert len(out) > 0


def test_render_empty_chart_is_safe() -> None:
    out = render_component_to_text(Chart(), width=20, height=8)
    assert isinstance(out, str)


def test_render_bar_chart_is_safe() -> None:
    out = render_component_to_text(
        Chart(series={"load": [(0, 3), (1, 5), (2, 4)]}, kind="bar"),
        width=30,
        height=10,
    )
    assert isinstance(out, str)


def test_render_subclass_is_safe() -> None:
    out = render_component_to_text(
        Latency(series={"p50": [1, 2, 3], "p99": [3, 4, 5]}),
        width=40,
        height=12,
    )
    assert isinstance(out, str)
