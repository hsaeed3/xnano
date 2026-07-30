"""benchmarks.test_components

---

Component construction and ``compose()`` — the per-frame work of turning
declarative component instances into the content tree the renderer consumes.
Sizes are picked to be representative of a real screen rather than minimal:
a 50-row table, three 200-point series, a 120-value bar strip, and a
500-item searchable list.
"""

from __future__ import annotations

from typing import Any, Sequence

import pytest

from xnano.components.bar import Bar
from xnano.components.chart import Chart
from xnano.components.component import ComponentRenderContext
from xnano.components.options import Options
from xnano.components.table import Column, Table
from xnano.components.text import Text
from xnano.types import Area

_REGIONS = ("us-east", "eu-west", "ap-south")

_ROWS = [
    {
        "service": f"svc-{index}",
        "status": "ok" if index % 3 else "degraded",
        "latency": index * 7 % 120,
        "region": _REGIONS[index % 3],
    }
    for index in range(50)
]

_COLUMNS = {
    "service": "Service",
    "status": "State",
    "latency": Column(format="{}ms", align="right", width=8),
    "region": "Region",
}

_SERIES: dict[str, Sequence[Any]] = {
    "cpu": [(index, (index * 13) % 100) for index in range(200)],
    "mem": [(index, (index * 7) % 80) for index in range(200)],
    "io": [(index, (index * 3) % 60) for index in range(200)],
}

_BAR_DATA = [(index * 17) % 100 for index in range(120)]

_OPTION_ITEMS = [
    f"item-{index}-{'alpha' if index % 2 else 'beta'}-name"
    for index in range(500)
]


@pytest.fixture
def context() -> ComponentRenderContext:
    """A render context sized like a full-screen laptop terminal."""
    return ComponentRenderContext(area=Area(x=0, y=0, width=80, height=24))


def _compose_nested_text(context: ComponentRenderContext) -> list[object]:
    """Build and compose 20 nested-span text blocks."""
    return [
        Text(
            [
                Text("ok", foreground="green", modifiers=("bold",)),
                Text(" ready ", foreground="cyan"),
                Text(f"#{index}", modifiers=("dim",)),
            ]
        ).compose(context)
        for index in range(20)
    ]


def _compose_table(context: ComponentRenderContext) -> object:
    """Infer columns, sort, format and highlight a 50-row table."""
    return Table(
        data=_ROWS,
        columns=_COLUMNS,
        selected=3,
        highlight_symbol="> ",
        sort="latency",
        sort_direction="descending",
    ).compose(context)


def _compose_chart(context: ComponentRenderContext) -> object:
    """Coerce and bound 600 points across three series."""
    return Chart(series=_SERIES, kind="line", legend=True).compose(context)


def _compose_bar(context: ComponentRenderContext) -> object:
    """Pick a glyph per value for a 120-value bar strip."""
    return Bar(
        data=_BAR_DATA,
        foreground="green",
        max_value=100,
        direction="up",
    ).compose(context)


def _filter_options(options: Options) -> object:
    """Score and sort a fuzzy query over 500 items."""
    return options.filtered


def _compose_options(
    options: Options, context: ComponentRenderContext
) -> object:
    """Filter, emphasize match indices and lay out 500 rows."""
    return options.compose(context)


def test_text_nested_compose(benchmark, context) -> None:
    """The most common component in any xnano ui."""
    blocks = benchmark(_compose_nested_text, context)
    assert len(blocks) == 20


def test_table_compose(benchmark, context) -> None:
    """200 formatted cells: the classic large-data component cost."""
    node = benchmark(_compose_table, context)
    assert len(node.rows) == len(_ROWS)


def test_chart_compose(benchmark, context) -> None:
    """Per-frame cost of a live multi-series chart."""
    node = benchmark(_compose_chart, context)
    assert len(node.datasets) == len(_SERIES)


def test_bar_compose(benchmark, context) -> None:
    """Sparkline rebuild, typically re-run on every animation tick."""
    node = benchmark(_compose_bar, context)
    assert node is not None


def test_options_filter(benchmark) -> None:
    """The fuzzy scorer and score sort, the hot loop of a picker."""
    options = Options(items=_OPTION_ITEMS, query="itmalph", searchable=True)
    matched = benchmark(_filter_options, options)
    assert 0 < len(matched) < len(_OPTION_ITEMS)


def test_options_compose(benchmark, context) -> None:
    """Filter plus per-row match emphasis for a 500-item list."""
    options = Options(items=_OPTION_ITEMS, query="itmalph", searchable=True)
    node = benchmark(_compose_options, options, context)
    assert node is not None
