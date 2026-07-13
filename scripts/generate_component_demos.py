#!/usr/bin/env python3
"""scripts.generate_component_demos

---

Generate fitted light/dark GIFs for docs/components.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = REPOSITORY_ROOT / "docs" / "assets" / "components"
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from vhs_docs import (  # noqa: E402
    THEMES,
    Demo,
    ThemeKey,
    code,
    demo_map,
    purge_legacy_demo_artifacts,
    record_demo,
    require_vhs,
    run_embedded_code,
)


def _render_demo(
    name: str,
    imports: str,
    expression: str,
    *,
    height: int,
) -> Demo:
    """Build a static Terminal.render demo for one component.

    Uses full session width so paint spans the window; only height is fitted.
    """
    source = code(f"""
        import time
        {imports}
        from xnano.tui import Terminal

        Terminal(height={height}).render({expression})
        time.sleep(3)
    """)
    return Demo(
        name=name,
        code=source,
        launch_delay="800ms",
        steps=("Sleep 2s",),
        record_delay="500ms",
        auto_quit=False,
        content_rows=height,
        gap_rows=2,
    )


DEMOS: tuple[Demo, ...] = (
    _render_demo(
        "text_leaf",
        "from xnano.components.text import Text",
        'Text("hello world", color="red", modifiers=("bold",))',
        height=1,
    ),
    _render_demo(
        "text_line",
        "from xnano.components.text import Text",
        ('Text([Text("Hello ", color="cyan"), Text("world", color="red")])'),
        height=1,
    ),
    _render_demo(
        "text_paragraph",
        "from xnano.components.text import Text",
        (
            "Text(["
            'Text([Text("Hello ", color="cyan"), Text("world")]), '
            'Text("Second line", color="blue")'
            "])"
        ),
        height=2,
    ),
    _render_demo(
        "text_input",
        "from xnano.components.text import Text",
        'Text("Search xnano", input=True, color="cyan")',
        height=1,
    ),
    Demo(
        name="progress_bar",
        code=code("""
            from xnano import BaseGrid, Field, Terminal, Context
            from xnano.components.progress import Progress
            from xnano.events import on_keyboard, on_tick

            class Download(BaseGrid, direction="vertical", gap=1):
                status: str = Field(default="Downloading…", height=1)
                bar: Progress = Field(
                    default_factory=lambda: Progress(
                        value=0.0, color="emerald-400"
                    ),
                    height=1,
                )
                done: int = Field(default=0, state=True)
                total: int = Field(default=40, state=True)

                @on_tick(80)
                def advance(self) -> None:
                    if self.done >= self.total:
                        return
                    self.done += 1
                    ratio = self.done / self.total
                    self.bar = Progress(value=ratio, color="emerald-400")
                    self.status = (
                        "Done."
                        if self.done >= self.total
                        else f"Downloading… {self.done}/{self.total}"
                    )

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(Download())
        """),
        steps=("Sleep 4s",),
        record_delay="500ms",
        content_rows=5,
        gap_rows=3,
    ),
    _render_demo(
        "progress_line",
        "from xnano.components.progress import Progress",
        (
            'Progress(value=0.42, style="line", label="upload", '
            'filled_color="violet", unfilled_color="gray")'
        ),
        height=2,
    ),
    _render_demo(
        "sparkline_basic",
        "from xnano.components.sparkline import Sparkline",
        (
            "Sparkline("
            "data=[2, 4, 3, 7, 5, 8, 6, 9], "
            'color="cyan", max_value=10'
            ")"
        ),
        height=4,
    ),
    _render_demo(
        "sparkline_colors",
        "from xnano.components.sparkline import Sparkline",
        (
            "Sparkline("
            "data=[1, 3, 5, 7, 9], "
            'colors=("blue", "cyan", "green", "yellow", "red")'
            ")"
        ),
        height=3,
    ),
    _render_demo(
        "table_basic",
        "from xnano.components.table import Table",
        (
            "Table(data=["
            '{"service": "api", "status": "ok", "latency": 12}, '
            '{"service": "db", "status": "degraded", "latency": 340}'
            '], selected=0, highlight_background="blue")'
        ),
        height=5,
    ),
    Demo(
        name="table_declarative",
        code=code("""
            import time
            from xnano.components.table import Column, Table
            from xnano.tui import Terminal

            class Services(Table):
                service: str = Column()
                status: str = Column(
                    color=lambda v: "green" if v == "ok" else "red"
                )
                latency: int = Column(align="right", format="{}ms")

            Terminal(height=5).render(
                Services(
                    data=[
                        {
                            "service": "api",
                            "status": "ok",
                            "latency": 12,
                        },
                        {
                            "service": "db",
                            "status": "degraded",
                            "latency": 340,
                        },
                        {
                            "service": "cache",
                            "status": "ok",
                            "latency": 4,
                        },
                    ],
                    selected=0,
                )
            )
            time.sleep(3)
        """),
        launch_delay="800ms",
        steps=("Sleep 2s",),
        record_delay="500ms",
        auto_quit=False,
        content_rows=5,
        gap_rows=2,
    ),
    _render_demo(
        "chart_lines",
        "from xnano.components.chart import Chart",
        (
            "Chart(series={"
            '"cpu": [30, 42, 38, 55, 61], '
            '"mem": [60, 61, 63, 62, 64]'
            '}, x_label="sample", y_label="percent")'
        ),
        height=14,
    ),
    _render_demo(
        "chart_bars",
        "from xnano.components.chart import Chart",
        (
            "Chart(series={"
            '"load": [(0, 3), (1, 5), (2, 4), (3, 7)]'
            '}, kind="bar", y_bounds=(0, 10), legend=False)'
        ),
        height=12,
    ),
    Demo(
        name="custom_badge",
        code=code("""
            import dataclasses
            import time
            from xnano._types import Size
            from xnano.components.abstract import AbstractComponent
            from xnano.core.content import Panel, TextBlock
            from xnano.tui import Terminal

            @dataclasses.dataclass
            class Badge(AbstractComponent):
                text: str = ""
                color: str = "white"

                def get_size(self, ctx):
                    return Size(width=len(self.text) + 4, height=3)

                def compose(self, ctx):
                    return Panel(
                        child=TextBlock.from_plain(
                            self.text,
                            color=self.color,
                        ),
                        border="rounded",
                    )

            # Terminal.render paints the composed node; bare render()
            # falls back to the component's repr for unknown types.
            Terminal(height=5).render(Badge(text="NEW", color="emerald-400"))
            time.sleep(3)
        """),
        launch_delay="800ms",
        steps=("Sleep 2s",),
        record_delay="500ms",
        auto_quit=False,
        content_rows=5,
        gap_rows=3,
    ),
)

_DEMO_MAP = demo_map(DEMOS)


def generate(
    demo: Demo,
    theme: ThemeKey,
    *,
    vhs: str,
    dry_run: bool,
    quiet: bool,
) -> None:
    """Record one component demo for a single theme."""
    output = OUTPUT_DIRECTORY / f"{demo.name}-{theme}.gif"
    launch = (
        "uv run python scripts/generate_component_demos.py "
        f"--run-example {demo.name}"
    )
    record_demo(
        demo,
        output=output,
        theme=theme,
        launch_command=launch,
        vhs=vhs,
        dry_run=dry_run,
        quiet=quiet,
        tape_label="component",
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--demo",
        choices=list(_DEMO_MAP),
        action="append",
        help="Record only the named demo (repeatable)",
    )
    parser.add_argument(
        "--theme",
        choices=list(THEMES),
        help="Record one theme only (default: both)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print tape files without recording",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Pass --quiet to VHS",
    )
    parser.add_argument(
        "--run-example",
        choices=list(_DEMO_MAP),
        help=argparse.SUPPRESS,
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(argv)

    if args.run_example:
        run_embedded_code(_DEMO_MAP[args.run_example], label="component")
        return 0

    for path in purge_legacy_demo_artifacts():
        print(f"removed legacy {path}")

    selected = (
        [_DEMO_MAP[name] for name in args.demo] if args.demo else list(DEMOS)
    )
    themes: tuple[ThemeKey, ...] = (args.theme,) if args.theme else THEMES
    vhs = "" if args.dry_run else require_vhs()

    for demo in selected:
        for theme in themes:
            generate(
                demo,
                theme,
                vhs=vhs,
                dry_run=args.dry_run,
                quiet=args.quiet,
            )

    if not args.dry_run:
        total = len(selected) * len(themes)
        print(
            f"\nDone — {total} GIF(s) in "
            f"{OUTPUT_DIRECTORY.relative_to(REPOSITORY_ROOT)}/"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
