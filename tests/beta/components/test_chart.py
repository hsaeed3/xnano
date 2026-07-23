"""Tests for beta ``Chart``."""

from __future__ import annotations

from typing import Any

from xnano.beta.components.chart import Chart, Series
from xnano.beta.components.component import ComponentRenderContext
from xnano.beta.core import Runtime
from xnano.beta.core.content import Plot
from xnano.beta.types import Area


def _ctx() -> ComponentRenderContext[Any]:
    return ComponentRenderContext(area=Area(x=0, y=0, width=40, height=12))


def _node(chart: Chart) -> Any:
    content = chart.compose(_ctx())
    assert isinstance(content, Plot)
    return content


def test_bare_y_values_become_indexed_points() -> None:
    node = _node(Chart(series={"cpu": [10, 20, 30]}))
    assert node.datasets[0].data == ((0.0, 10.0), (1.0, 20.0), (2.0, 30.0))


def test_xy_pairs_are_preserved() -> None:
    node = _node(Chart(series={"load": [(1, 3), (2, 5), (4, 2)]}))
    assert node.datasets[0].data == ((1.0, 3.0), (2.0, 5.0), (4.0, 2.0))


def test_auto_bounds_from_data() -> None:
    node = _node(Chart(series={"a": [10, 50, 30]}))
    assert node.x_axis is not None
    assert node.y_axis is not None
    assert node.x_axis.bounds[0] <= 0.0
    assert node.x_axis.bounds[1] >= 2.0
    assert node.y_axis.bounds[0] <= 10.0
    assert node.y_axis.bounds[1] >= 50.0


def test_explicit_bounds_override() -> None:
    node = _node(
        Chart(
            series={"a": [1, 2, 3]},
            x_bounds=(0.0, 10.0),
            y_bounds=(-5.0, 5.0),
        )
    )
    assert node.x_axis.bounds == (0.0, 10.0)
    assert node.y_axis.bounds == (-5.0, 5.0)


def test_flat_series_expands_bounds() -> None:
    node = _node(Chart(series={"flat": [5, 5, 5]}))
    low, high = node.y_axis.bounds
    assert low == 5.0
    assert high > 5.0


def test_negative_flat_series_expands_bounds() -> None:
    node = _node(Chart(series={"neg": [-3, -3]}))
    low, high = node.y_axis.bounds
    assert high == -3.0
    assert low < -3.0


def test_empty_series_default_bounds() -> None:
    node = _node(Chart())
    assert node.x_axis.bounds == (0.0, 1.0)
    assert node.y_axis.bounds == (0.0, 1.0)
    assert node.datasets == ()


def test_datasets_property_is_resolved_view() -> None:
    chart = Chart(series={"cpu": [1, 2], "mem": [3, 4]})
    datasets = chart.datasets
    assert [entry[0] for entry in datasets] == ["cpu", "mem"]
    assert datasets[0][1] == ((0.0, 1.0), (1.0, 2.0))


def test_hidden_series_omitted() -> None:
    chart = Chart(
        series={"cpu": [1, 2], "mem": [3, 4]},
        hidden_series=("mem",),
    )
    assert [entry[0] for entry in chart.datasets] == ["cpu"]
    node = _node(chart)
    assert [dataset.name for dataset in node.datasets] == ["cpu"]


def test_default_palette_cycles_colors() -> None:
    node = _node(Chart(series={"a": [1], "b": [2], "c": [3]}))
    colors = [dataset.color for dataset in node.datasets]
    assert colors == ["cyan", "magenta", "green"]


def test_kind_and_marker_propagate() -> None:
    node = _node(Chart(series={"a": [1, 2]}, kind="scatter", marker="braille"))
    assert node.datasets[0].graph_type == "scatter"
    assert node.datasets[0].marker == "braille"


def test_legend_disabled() -> None:
    node = _node(Chart(series={"a": [1]}, legend=False))
    assert node.legend_position is None


def test_axis_titles_and_labels() -> None:
    node = _node(
        Chart(
            series={"a": [1, 2]},
            x_label="time",
            y_label="load",
            x_labels=["a", "b"],
            y_labels=["0", "1"],
        )
    )
    assert node.x_axis.title == "time"
    assert node.y_axis.title == "load"
    assert node.x_axis.labels == ("a", "b")
    assert node.y_axis.labels == ("0", "1")


class Latency(Chart):
    p50 = Series(color="green")
    p99 = Series(color="red", kind="scatter", label="99th", marker="dot")


def test_subclass_captures_declared_series() -> None:
    assert list(Latency._declared) == ["p50", "p99"]


def test_subclass_applies_series_styling() -> None:
    node = _node(Latency(series={"p50": [1, 2, 3], "p99": [4, 5, 6]}))
    by_name = {dataset.name: dataset for dataset in node.datasets}
    assert by_name["p50"].color == "green"
    assert by_name["p50"].graph_type == "line"
    assert by_name["99th"].color == "red"
    assert by_name["99th"].graph_type == "scatter"
    assert by_name["99th"].marker == "dot"


def test_subclass_orders_declared_series_first() -> None:
    node = _node(Latency(series={"extra": [9], "p99": [2], "p50": [1]}))
    names = [dataset.name for dataset in node.datasets]
    assert names == ["p50", "99th", "extra"]


def test_runtime_offscreen_render_smoke() -> None:
    runtime = Runtime.offscreen(40, 12)
    try:
        frame = runtime.render(
            Chart(series={"cpu": [30, 42, 38, 55], "mem": [60, 61, 63, 62]})
        )
        assert isinstance(frame.text, str)
        assert len(frame.text) > 0
    finally:
        runtime.close()


def test_runtime_empty_chart_is_safe() -> None:
    runtime = Runtime.offscreen(20, 8)
    try:
        frame = runtime.render(Chart())
        assert isinstance(frame.text, str)
    finally:
        runtime.close()
