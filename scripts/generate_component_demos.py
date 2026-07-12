#!/usr/bin/env python3
"""scripts.generate_component_demos

---

Generate the fitted GIFs used by ``docs/components``.
"""

from __future__ import annotations

import argparse
import pathlib
from collections.abc import Sequence

import generate_concept_demos
from generate_concept_demos import Demo, generate, require_vhs

generate_concept_demos.OUTPUT_DIR = (
    pathlib.Path(__file__).resolve().parents[1]
    / "docs"
    / "assets"
    / "components"
)


def _demo_code(imports: str, expression: str, width: int, height: int) -> str:
    return f"""import time
{imports}
from xnano.tui import Terminal

Terminal(width={width}, height={height}).render({expression})
time.sleep(3)
"""


DEMOS: tuple[Demo, ...] = (
    Demo(
        "component-grid",
        _demo_code(
            "from xnano.components.progress import Progress",
            "Progress(0.72)",
            42,
            3,
        ),
        auto_quit=False,
        width=620,
        height=200,
    ),
    Demo(
        "custom-badge",
        _demo_code(
            "from xnano.components.text import Text",
            'Text("● ready", color="green")',
            18,
            1,
        ),
        auto_quit=False,
        width=420,
        height=180,
    ),
    Demo(
        "text-styled",
        _demo_code(
            "from xnano.components.text import Text",
            'Text([Text("build ", color="gray"), Text("passed", color="green", modifiers=("bold",))])',
            24,
            1,
        ),
        auto_quit=False,
        width=460,
        height=180,
    ),
    Demo(
        "text-multiline",
        _demo_code(
            "from xnano.components.text import Text",
            'Text([Text([Text("Tests ", color="gray"), Text("42", color="cyan")]), Text([Text("Failed ", color="gray"), Text("0", color="green")])], align="right")',
            24,
            2,
        ),
        auto_quit=False,
        width=460,
        height=180,
    ),
    Demo(
        "text-input",
        _demo_code(
            "from xnano.components.text import Text",
            'Text("Search xnano", input=True, color="cyan")',
            36,
            1,
        ),
        auto_quit=False,
        width=560,
        height=180,
    ),
    Demo(
        "progress-bar",
        _demo_code(
            "from xnano.components.progress import Progress",
            'Progress(value=37, total=50, color="cyan")',
            32,
            1,
        ),
        auto_quit=False,
        width=520,
        height=180,
    ),
    Demo(
        "progress-line",
        _demo_code(
            "from xnano.components.progress import Progress",
            'Progress(value=0.42, style="line", label="upload", filled_color="violet", unfilled_color="gray")',
            32,
            1,
        ),
        auto_quit=False,
        width=520,
        height=180,
    ),
    Demo(
        "sparkline-basic",
        _demo_code(
            "from xnano.components.sparkline import Sparkline",
            'Sparkline(data=[2, 4, 3, 7, 5, 8, 6, 9], color="cyan", max_value=10)',
            20,
            4,
        ),
        auto_quit=False,
        width=440,
        height=220,
    ),
    Demo(
        "sparkline-colors",
        _demo_code(
            "from xnano.components.sparkline import Sparkline",
            'Sparkline(data=[1, 3, 5, 7, 9], colors=("blue", "cyan", "green", "yellow", "red"))',
            14,
            3,
        ),
        auto_quit=False,
        width=380,
        height=200,
    ),
    Demo(
        "table-basic",
        _demo_code(
            "from xnano.components.table import Table",
            'Table(data=[{"service": "api", "status": "ready", "latency": 12}, {"service": "worker", "status": "busy", "latency": 48}], selected=0, highlight_background="blue")',
            44,
            4,
        ),
        auto_quit=False,
        width=700,
        height=220,
    ),
    Demo(
        "table-columns",
        _demo_code(
            "from xnano.components.schema import Column\nfrom xnano.components.table import Table",
            'Table(data=[{"service": "api", "status": "ready", "latency": 12}, {"service": "worker", "status": "busy", "latency": 48}], columns={"service": "Service", "status": Column(color=lambda value: "green" if value == "ready" else "yellow"), "latency": Column(header="Latency", align="right", format="{} ms")})',
            44,
            4,
        ),
        auto_quit=False,
        width=700,
        height=220,
    ),
    Demo(
        "table-declarative",
        _demo_code(
            "from xnano.components.table import Table",
            'Table(data=[{"service": "api", "status": "ready", "latency": "12 ms"}, {"service": "worker", "status": "busy", "latency": "48 ms"}])',
            44,
            4,
        ),
        auto_quit=False,
        width=700,
        height=220,
    ),
    Demo(
        "chart-lines",
        _demo_code(
            "from xnano.components.chart import Chart",
            'Chart(series={"cpu": [30, 42, 38, 55, 49], "memory": [60, 61, 63, 62, 65]}, x_label="sample", y_label="percent")',
            58,
            14,
        ),
        auto_quit=False,
        width=860,
        height=420,
    ),
    Demo(
        "chart-bars",
        _demo_code(
            "from xnano.components.chart import Chart",
            'Chart(series={"requests": [(0, 18), (1, 31), (2, 24), (3, 40)]}, kind="bar", y_bounds=(0, 50), legend=False)',
            48,
            12,
        ),
        auto_quit=False,
        width=760,
        height=380,
    ),
    Demo(
        "chart-declarative",
        _demo_code(
            "from xnano.components.chart import Chart",
            'Chart(series={"p50": [12, 14, 13, 16], "p99": [28, 32, 29, 41]}, colors=("green", "red"))',
            54,
            14,
        ),
        auto_quit=False,
        width=820,
        height=420,
    ),
)

_DEMO_MAP = {demo.name: demo for demo in DEMOS}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", choices=list(_DEMO_MAP), action="append")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    arguments = parser.parse_args(argv)
    selected = (
        [_DEMO_MAP[name] for name in arguments.demo]
        if arguments.demo
        else list(DEMOS)
    )
    vhs = "" if arguments.dry_run else require_vhs()
    for demo in selected:
        generate(
            demo,
            "dark",
            vhs=vhs,
            dry_run=arguments.dry_run,
            quiet=arguments.quiet,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
