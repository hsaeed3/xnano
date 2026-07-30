"""tests.benchmarks.test_core_performance

---

Track the core lowering, native rendering, and frame snapshot paths.
"""

from __future__ import annotations

import pytest
from xnano_core.core import (
    CoreRenderContent,
    CoreRenderIR,
    CoreRenderNode,
    CoreSession,
)
from xnano_core.rust.native import Constraint

from xnano.core.content import (
    Bar,
    BarGroup,
    Bars,
    CellCanvas,
    CellSpan,
    Gauge,
    Items,
    Panel,
    Sparkline,
    Stack,
    TableGrid,
    TableRow,
    TextBlock,
)
from xnano.core.rendering import lower_content
from xnano.core.runtime import Runtime


def _dashboard_content(rows: int) -> Stack:
    services = tuple(
        TableRow(cells=(f"service-{index}", "ready", str(index)))
        for index in range(rows)
    )
    return Stack(
        children=(
            Panel(
                child=TextBlock(text="All systems operational"),
                title="Status",
                border="rounded",
            ),
            Gauge(progress=0.72, label="CPU 72%"),
            Sparkline(data=tuple(range(32))),
            Bars(
                groups=(
                    BarGroup(
                        label="requests",
                        bars=tuple(
                            Bar(value=index + 1, label=str(index))
                            for index in range(8)
                        ),
                    ),
                ),
                max_value=8,
            ),
            Items(items=tuple(f"worker-{index}" for index in range(rows))),
            TableGrid(
                header=TableRow(cells=("Service", "State", "Queue")),
                rows=services,
                column_widths=(18, 8, 8),
            ),
        ),
    )


@pytest.mark.parametrize(
    "rows",
    (10, 100),
    ids=("small-dashboard", "large-dashboard"),
)
def test_bench_core_content_lowering(benchmark, rows: int) -> None:
    """Measure Python content lowering without terminal setup."""
    content = _dashboard_content(rows)
    node = benchmark(lower_content, content)
    assert isinstance(node, CoreRenderNode)


def test_bench_core_cell_canvas_cache_hit(benchmark) -> None:
    """Measure the hot identity-cache path used by images and animation."""
    canvas = CellCanvas.from_rows(
        tuple(
            (
                CellSpan(
                    " " * 80,
                    background=f"#{row:02x}4080",
                ),
            )
            for row in range(24)
        )
    )
    lower_content(canvas)
    node = benchmark(lower_content, canvas)
    assert isinstance(node, CoreRenderNode)


def test_bench_core_native_render_tree(benchmark) -> None:
    """Measure native layout and paint for a representative scene graph."""
    session = CoreSession.offscreen(120, 40)
    children = [
        CoreRenderNode.leaf(
            CoreRenderContent.ir(
                CoreRenderIR.paragraph_raw(
                    f"row {index} " * 8,
                    None,
                    None,
                    [],
                    None,
                    True,
                )
            )
        )
        for index in range(20)
    ]
    tree = CoreRenderNode.column(
        children,
        constraints=[Constraint.fill(1) for _ in children],
    )
    benchmark(session.render, tree)
    assert session.buffer_snapshot().to_string_lines()


@pytest.mark.parametrize(
    ("width", "height"),
    ((80, 24), (200, 50)),
    ids=("terminal", "dashboard"),
)
def test_bench_runtime_render_and_snapshot(
    benchmark,
    width: int,
    height: int,
) -> None:
    """Measure the public core paint path including frame serialization."""
    runtime = Runtime.offscreen(width, height)
    runtime.set_root(_dashboard_content(20))
    try:
        frame = benchmark(runtime.render)
        assert frame.width == width
        assert frame.height == height
    finally:
        runtime.close()
