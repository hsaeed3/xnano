"""tests.stress.test_runtime_scale

---

Exercise mixed components, large data, and live service updates.
"""

import queue
import threading

from xnano.components.chart import Chart
from xnano.components.options import Options
from xnano.components.table import Table
from xnano.core.runtime import Runtime
from xnano.fields import Field
from xnano.grids import BaseGrid


def test_large_mixed_dashboard_updates_as_one_render_tree() -> None:
    models = tuple(f"model-{index:04d}" for index in range(3_000))
    rows = [
        {"model": model, "latency": index % 100}
        for index, model in enumerate(models)
    ]

    class Dashboard(BaseGrid, direction="vertical"):
        models: Options = Field(
            default_factory=lambda: Options(
                items=models,
                selected=1_500,
            ),
            height=12,
        )
        requests: Chart = Field(
            default_factory=lambda: Chart(
                series={"latency": tuple(range(3_000))},
                legend=False,
            ),
            height=10,
        )
        results: Table = Field(
            default_factory=lambda: Table(data=rows, selected=1_500),
            height=16,
        )

    dashboard = Dashboard()
    runtime = Runtime.offscreen(width=100, height=40)
    runtime.set_root(dashboard)
    try:
        first = runtime.render()
        dashboard.models.select(2_999)
        dashboard.requests.series = {
            "latency": tuple(reversed(range(3_000)))
        }
        dashboard.results.data = list(reversed(rows))
        second = runtime.render()

        assert (first.width, first.height) == (second.width, second.height)
        assert dashboard.models.selected_value == "model-2999"
        assert dashboard.results.selected_row is not None
    finally:
        runtime.close()


def test_large_options_render_at_common_terminal_sizes() -> None:
    items = tuple(f"endpoint-{index:04d}" for index in range(3_000))
    for width, height in ((40, 10), (80, 24), (160, 50)):
        options = Options(items=items, selected=2_999, searchable=True)
        runtime = Runtime.offscreen(width=width, height=height)
        try:
            frame = runtime.render(options)
            assert frame.width == width
            assert frame.height == height
            assert options.selected_value == "endpoint-2999"
        finally:
            runtime.close()


def test_service_snapshots_can_feed_repeated_renders() -> None:
    snapshots: queue.Queue[tuple[str, ...]] = queue.Queue(maxsize=1)
    options = Options(items=(), selected=1_500)
    runtime = Runtime.offscreen(width=80, height=24)
    runtime.set_root(options)

    def run_service() -> None:
        for revision in range(5):
            snapshots.put(
                tuple(
                    f"revision-{revision}-model-{index:04d}"
                    for index in range(3_000)
                )
            )

    worker = threading.Thread(target=run_service)
    worker.start()
    try:
        for revision in range(5):
            options.items = snapshots.get()
            frame = runtime.render()
            assert f"revision-{revision}" in options.selected_label
            assert frame.height == 24
    finally:
        worker.join()
        runtime.close()
