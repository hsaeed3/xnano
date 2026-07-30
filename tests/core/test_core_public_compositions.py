"""Tests for composed public content through the core runtime."""

from __future__ import annotations

from typing import Any

from xnano_core.core import (
    CoreRenderContent,
    CoreRenderIR,
    CoreRenderNode,
    CoreSession,
)

from xnano.core.content import (
    Bar,
    BarGroup,
    Bars,
    Canvas,
    CanvasCircle,
    CanvasLine,
    CanvasPoints,
    CanvasPrint,
    CanvasRectangle,
    CellCanvas,
    Clear,
    Gauge,
    Items,
    LineGauge,
    Native,
    Panel,
    Plot,
    PlotAxis,
    PlotDataset,
    Run,
    Scrollbar,
    Sparkline,
    Stack,
    TableGrid,
    TableRow,
    TextBlock,
)
from xnano.core.rendering import lower_content
from xnano.core.runtime import Runtime
from xnano.fields import Field
from xnano.grids import BaseGrid
from xnano.types import Sizing


def test_operations_dashboard_switches_between_composed_views() -> None:
    runtime = Runtime.offscreen(48, 12)
    try:
        overview = Stack(
            children=(
                Panel(
                    child=TextBlock(text="All systems operational"),
                    title="Status",
                    border="rounded",
                ),
                Gauge(progress=0.72, label="CPU 72%"),
                LineGauge(progress=0.4, label="Queue 40%"),
            )
        )
        frame = runtime.render(overview)
        assert frame.contains("Status")
        assert frame.contains("All systems operational")
        assert frame.contains("CPU 72%")
        assert frame.contains("Queue 40%")

        detail = Stack(
            direction="horizontal",
            children=(
                Items(
                    items=("api", "worker", "scheduler"),
                    selected=1,
                    highlight_symbol="› ",
                ),
                TableGrid(
                    header=TableRow(cells=("Service", "State")),
                    rows=(
                        TableRow(cells=("api", "ready")),
                        TableRow(cells=("worker", "busy")),
                    ),
                    column_widths=(10, 8),
                    selected_row=1,
                ),
            ),
        )
        frame = runtime.render(detail)
        assert all(
            frame.contains(value)
            for value in ("scheduler", "Service", "api", "ready", "busy")
        )
        assert frame.revision > 0
    finally:
        runtime.close()


def test_metrics_view_combines_chart_canvas_and_scroll_position() -> None:
    runtime = Runtime.offscreen(48, 12)
    try:
        metrics = Stack(
            children=(
                Bars(
                    groups=(
                        BarGroup(
                            label="requests",
                            bars=(
                                Bar(value=8, label="GET"),
                                Bar(value=3, label="POST"),
                            ),
                        ),
                    ),
                    max_value=10,
                ),
                Sparkline(data=(1, 4, 2, 8, 5)),
                CellCanvas.from_rows((("cache: warm",), ("region: west",))),
                Scrollbar(
                    content_length=100,
                    viewport_length=20,
                    position=40,
                    orientation="horizontal_bottom",
                ),
            )
        )

        frame = runtime.render(metrics)
        assert frame.width == 48
        assert frame.height == 12
        assert frame.contains("cache: warm")
        assert frame.contains("region: west")
        assert frame.text.strip()
        assert frame.ansi
        assert len(frame.rows) == 12
    finally:
        runtime.close()


def test_canvas_overview_combines_geometry_and_styled_annotations() -> None:
    runtime = Runtime.offscreen(48, 12)
    try:
        canvas = Canvas(
            x_bounds=(0.0, 10.0),
            y_bounds=(0.0, 10.0),
            marker="braille",
            shapes=(
                CanvasRectangle(x=1, y=1, width=8, height=6, color="blue"),
                CanvasLine(x1=1, y1=1, x2=9, y2=7, color="cyan"),
                CanvasCircle(x=5, y=5, radius=2, color="green"),
                CanvasPoints(coords=((2, 8), (5, 9), (8, 8)), color="yellow"),
                CanvasPrint(
                    x=3,
                    y=5,
                    content=Run(
                        text="LIVE",
                        color="white",
                        modifiers=("bold",),
                    ),
                ),
            ),
        )

        frame = runtime.render(canvas)
        assert frame.contains("LIVE")
        assert frame.text.strip()
    finally:
        runtime.close()


def test_native_escape_hatches_and_fallback_content_render_together() -> None:
    runtime = Runtime.offscreen(40, 8)
    try:
        node = CoreRenderNode.leaf(
            CoreRenderContent.ir(CoreRenderIR.span("native-node", None, None, []))
        )
        content = Stack(
            children=(
                Native(interface_kind="terminal", payload=node),
                Native(
                    interface_kind="terminal",
                    payload=CoreRenderIR.span("native-ir", None, None, []),
                ),
                Native(interface_kind="terminal", payload={"state": "ready"}),
            )
        )
        frame = runtime.render(content)
        assert frame.contains("native-node")
        assert frame.contains("native-ir")
        assert frame.contains("'state': 'ready'")

        class ServiceState:
            def __str__(self) -> str:
                return "fallback-service"

        assert runtime.render(ServiceState()).contains("fallback-service")
        assert not runtime.render(Clear()).text.strip()
    finally:
        runtime.close()


def test_configured_plot_and_partial_panel_render_as_one_status_view() -> None:
    runtime = Runtime.offscreen(48, 12)
    try:
        view = Stack(
            children=(
                Plot(
                    datasets=(
                        PlotDataset(
                            data=((0, 2), (1, 5), (2, 3)),
                            name="latency",
                            graph_type="line",
                            marker="dot",
                            color="cyan",
                        ),
                    ),
                    x_axis=PlotAxis(
                        title="minute",
                        bounds=(0, 2),
                        labels=("now", "later"),
                        color="white",
                    ),
                    y_axis=PlotAxis(title="ms", bounds=(0, 5)),
                    color="blue",
                    legend_position="bottom_left",
                ),
                Panel(
                    child=TextBlock(text="healthy"),
                    title="Service",
                    title_position="bottom",
                    border_sides=("left", "right"),
                    border_color="green",
                    background="black",
                ),
            )
        )
        frame = runtime.render(view)
        assert frame.contains("ms")
        assert frame.contains("healthy")
        assert frame.contains("Service")
    finally:
        runtime.close()


def test_grid_mixes_fixed_percent_ratio_fit_and_flexible_fields() -> None:
    class Dashboard(BaseGrid, gap=1):
        title: Any = Field(default="Overview", height=1)
        alerts: Any = Field(default="No alerts", height="20%")
        jobs: Any = Field(default="Jobs", height="1/4")
        detail: Any = Field(default="Detail", height=Sizing.fit(minimum=1))
        footer: Any = Field(default="Ready", height="1fr")

    session = CoreSession.offscreen(40, 16)
    session.render(lower_content(Dashboard()))
    text = "\n".join(session.buffer_snapshot().to_string_lines())
    assert all(
        value in text
        for value in ("Overview", "No alerts", "Jobs", "Detail", "Ready")
    )
