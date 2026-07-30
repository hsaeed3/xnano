"""benchmarks.test_rendering

---

Whole-frame cost. ``lower_content`` is the funnel every renderable crosses on
its way into rust, and the runtime benchmarks below drive the complete path —
hook dispatch, grid layout, native paint and frame serialization — for a data
dashboard, a nest of grids, the animated showcase, a markdown document and the
print-like ``render()`` helper.
"""

from __future__ import annotations

import io
from typing import Iterator

import pytest

from xnano.actions import Action
from xnano.components.chart import Chart
from xnano.components.component import ComponentRenderContext
from xnano.components.table import Table
from xnano.components.text import Text
from xnano.core import Runtime
from xnano.core.demo import Showcase
from xnano.core.rendering import lower_content
from xnano.fields import Field
from xnano.grids import BaseGrid
from xnano.markdown import render_markdown
from xnano.rendering import render
from xnano.terminal import Terminal
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

_MARKDOWN = """# xnano report

A **bold** intro with *emphasis*, `inline code` and a [link](https://x.dev).

## Details

- first item with **bold**
- second item with `code`
- third item

> [!NOTE]
> A blockquote admonition with *emphasis*.

---

A closing paragraph long enough that the wrapping logic has something real to
lay out instead of a single short span.
"""


class Dashboard(BaseGrid, direction="vertical"):
    """A header, a 50-row table, a live chart and a status line."""

    header: Text = Field(
        default_factory=lambda: Text(
            "xnano dashboard", foreground="cyan", modifiers=("bold",)
        ),
        height=1,
    )
    table: Table = Field(default_factory=lambda: Table(data=_ROWS, selected=2))
    chart: Chart = Field(
        default_factory=lambda: Chart(
            series={
                "cpu": [(index, (index * 13) % 100) for index in range(120)]
            }
        )
    )
    footer: str = Field(default="ready", height=1)


class Row(BaseGrid, direction="horizontal"):
    """Two side-by-side text slots."""

    left: Text = Field(default_factory=lambda: Text("left"))
    right: Text = Field(default_factory=lambda: Text("right"))


class Nested(BaseGrid, direction="vertical"):
    """Four horizontal rows stacked vertically."""

    first: Row = Field(default_factory=Row)
    second: Row = Field(default_factory=Row)
    third: Row = Field(default_factory=Row)
    fourth: Row = Field(default_factory=Row)


def _offscreen(root: object, width: int, height: int) -> Runtime:
    """Open an offscreen runtime with ``root`` mounted and first frame drawn."""
    runtime = Runtime.offscreen(width, height)
    runtime.set_root(root)
    runtime.render()
    return runtime


def _render_frame(runtime: Runtime) -> object:
    """Render and serialize one frame."""
    return runtime.render()


def _paint_frame(runtime: Runtime) -> None:
    """Paint one frame without serializing it, as the live loop does."""
    runtime._render()


def _tick_and_render(runtime: Runtime) -> object:
    """Advance the animation clock, then render one frame."""
    runtime.perform(Action.tick(80))
    return runtime.render()


def _lower(node: object) -> object:
    """Lower a python content tree into the native render ir."""
    return lower_content(node)


def _render_markdown(terminal: Terminal) -> object:
    """Parse and paint a markdown document into a frame."""
    return render_markdown(_MARKDOWN, terminal=terminal)


def _render_helper() -> str:
    """Run the print-like helper into an in-memory stream."""
    buffer = io.StringIO()
    render(
        "hello xnano",
        color="cyan",
        background="black",
        border="rounded",
        border_color="blue",
        title="Report",
        padding=1,
        file=buffer,
    )
    return buffer.getvalue()


@pytest.fixture
def dashboard_runtime() -> Iterator[Runtime]:
    """A 120x40 offscreen runtime rendering the dashboard."""
    runtime = _offscreen(Dashboard(), 120, 40)
    yield runtime
    runtime.close()


@pytest.fixture
def nested_runtime() -> Iterator[Runtime]:
    """A 100x30 offscreen runtime rendering nested grids."""
    runtime = _offscreen(Nested(), 100, 30)
    yield runtime
    runtime.close()


@pytest.fixture
def markdown_terminal() -> Iterator[Terminal]:
    """An offscreen terminal reused across markdown renders."""
    terminal = Terminal.offscreen(cols=80, rows=30)
    yield terminal
    terminal.close()


def test_lower_content_table(benchmark) -> None:
    """Pure python overhead on the critical path into rust."""
    context = ComponentRenderContext(area=Area(x=0, y=0, width=80, height=24))
    node = Table(data=_ROWS, selected=3).compose(context)
    lowered = benchmark(_lower, node)
    assert lowered is not None


def test_dashboard_frame(benchmark, dashboard_runtime) -> None:
    """The headline end-to-end frame: layout, paint and serialization."""
    frame = benchmark(_render_frame, dashboard_runtime)
    assert "xnano dashboard" in frame.text


def test_dashboard_paint(benchmark, dashboard_runtime) -> None:
    """The same frame without serialization, isolating layout and paint."""
    benchmark(_paint_frame, dashboard_runtime)


def test_nested_grid_frame(benchmark, nested_runtime) -> None:
    """Recursive slot resolution without a heavy component payload."""
    frame = benchmark(_render_frame, nested_runtime)
    assert "left" in frame.text


def test_render_markdown(benchmark, markdown_terminal) -> None:
    """The public markdown surface, from source string to painted frame."""
    frame = benchmark(_render_markdown, markdown_terminal)
    assert frame.contains("Details")


def test_render_helper(benchmark) -> None:
    """A one-shot styled print, including its own terminal lifecycle."""
    output = benchmark(_render_helper)
    assert "hello xnano" in output


@pytest.mark.parametrize(
    "width, height",
    (
        pytest.param(80, 24, id="80x24"),
        pytest.param(160, 48, id="160x48"),
    ),
)
def test_showcase_frame(benchmark, width, height) -> None:
    """One animated frame of the built-in demo at two terminal sizes."""
    runtime = _offscreen(Showcase(), width, height)
    try:
        frame = benchmark(_tick_and_render, runtime)
        assert frame.width == width
        assert frame.height == height
    finally:
        runtime.close()
