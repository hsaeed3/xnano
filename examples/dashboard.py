"""xnano example — dashboard.py

A premium system monitoring dashboard simulation.
"""

from __future__ import annotations

import random

from xnano.beta import (
    Field,
    Grid,
    Terminal,
    on_keyboard,
    on_tick,
)
from xnano.beta.components import Sparkline, Text
from xnano.beta.color import tailwind_color


_GRADIENT = [
    tailwind_color("sky", 400),
    tailwind_color("teal", 400),
    tailwind_color("emerald", 400),
    tailwind_color("lime", 400),
    tailwind_color("amber", 400),
    tailwind_color("orange", 500),
    tailwind_color("red", 500),
    tailwind_color("pink", 500),
    tailwind_color("purple", 500),
    tailwind_color("indigo", 500),
    tailwind_color("blue", 500),
]


def _gradient_hex(i: int, total: int) -> str:
    if total <= 1:
        color = _GRADIENT[0]
        return f"#{color.r:02x}{color.g:02x}{color.b:02x}"
    pos = (i / (total - 1)) * (len(_GRADIENT) - 1)
    idx = min(int(pos), len(_GRADIENT) - 2)
    t = pos - idx
    start, end = _GRADIENT[idx], _GRADIENT[idx + 1]
    red = int(start.r + (end.r - start.r) * t)
    green = int(start.g + (end.g - start.g) * t)
    blue = int(start.b + (end.b - start.b) * t)
    return f"#{red:02x}{green:02x}{blue:02x}"


def _build_sparkline(history: list[int], width: int) -> Sparkline:
    data = (
        history[-width:]
        if len(history) >= width
        else [0] * (width - len(history)) + history
    )
    return Sparkline(
        data=data,
        colors=tuple(_gradient_hex(i, width) for i in range(len(data))),
        max_value=100,
    )


def _build_gauge(
    ratio: float, label: str, width: int, fill_color: str
) -> Text:
    filled = int(ratio * width)
    return Text(
        [
            Text(
                f"  {label}: {ratio * 100:.1f}%\n",
                color=tailwind_color("slate", 300),
            ),
            Text("█" * filled, color=fill_color),
            Text("░" * (width - filled), color=tailwind_color("slate", 700)),
        ]
    )


def _build_table(processes: list, selected: int) -> Text:
    dim = tailwind_color("slate", 500)
    lines: list[str | Text] = [
        Text(
            [
                Text(f"  {'Process':<16}", color=dim),
                Text(f"{'CPU %':>6}", color=dim),
                Text(f"  {'Memory':>8}", color=dim),
                Text(f"  {'Status'}\n", color=dim),
            ]
        ),
        Text("  " + "─" * 44 + "\n", color=dim),
    ]
    for i, (name, cpu, ram, status) in enumerate(processes):
        selected_bg = tailwind_color("violet", 900)
        if i == selected:
            lines.append(
                Text(
                    [
                        Text(
                            f"→ {name:<16}",
                            color="white",
                            modifiers=("bold",),
                            background=selected_bg,
                        ),
                        Text(
                            f"{cpu:>6}",
                            color=tailwind_color("emerald", 400),
                            modifiers=("bold",),
                            background=selected_bg,
                        ),
                        Text(
                            f"  {ram:>8}",
                            color=tailwind_color("sky", 400),
                            background=selected_bg,
                        ),
                        Text(
                            f"  {status}\n",
                            color=tailwind_color("slate", 500),
                            background=selected_bg,
                        ),
                    ]
                )
            )
        else:
            lines.append(
                Text(
                    [
                        Text(f"  {name:<16}", color="white"),
                        Text(
                            f"{cpu:>6}", color=tailwind_color("emerald", 400)
                        ),
                        Text(f"  {ram:>8}", color=tailwind_color("sky", 400)),
                        Text(
                            f"  {status}\n", color=tailwind_color("slate", 500)
                        ),
                    ]
                )
            )
    return Text(lines)


class GaugesPanel(Grid, direction="vertical", gap=1):
    mem: Text = Field(
        default=Text(""),
        size=3,
        border="rounded",
        border_color=tailwind_color("violet", 500),
        title=" Memory Info ",
    )
    disk: Text = Field(
        default=Text(""),
        size=3,
        border="rounded",
        border_color=tailwind_color("violet", 500),
        title=" Disk Storage ",
    )


class LeftPanel(Grid, direction="vertical"):
    cpu: Sparkline = Field(
        default_factory=Sparkline,
        border="rounded",
        border_color=tailwind_color("violet", 500),
        title=" CPU Usage History (%) ",
    )
    gauges: GaugesPanel = Field(default_factory=GaugesPanel, size=9)


class MainContent(Grid, direction="horizontal", gap=1):
    left: LeftPanel = Field(default_factory=LeftPanel, size=0.40)
    right: Text = Field(
        default=Text(""),
        border="rounded",
        border_color=tailwind_color("violet", 500),
        title=" Active Processes ",
    )


class Dashboard(Grid, direction="vertical"):
    header: str = Field(
        default="   SUPER COOL VERY IMPORTANT DASHBOARD   ",
        size=1,
        color="white",
        background=tailwind_color("violet", 950),
        modifiers=["bold"],
    )
    main: MainContent = Field(default_factory=MainContent)
    footer: str = Field(
        default="  [Ctrl+C] Quit  ●  [Up/Down] Navigate Table  ",
        size=1,
        color=tailwind_color("slate", 500),
    )

    cpu_history: list = Field(
        default_factory=lambda: [random.randint(5, 40) for _ in range(200)],
        state=True,
    )
    memory_ratio: float = Field(default=0.35, state=True)
    disk_percent: int = Field(default=55, state=True)
    selected_row: int = Field(default=0, state=True)
    processes: list = Field(
        default_factory=lambda: [
            ("systemd", "1.2%", "120MB", "Running"),
            ("xnano_agent", "18.5%", "45MB", "Running"),
            ("rust_core", "5.4%", "180MB", "Running"),
            ("python_tui", "2.1%", "60MB", "Running"),
            ("dockerd", "0.0%", "310MB", "Sleeping"),
        ],
        state=True,
    )

    @on_keyboard("up")
    def _prev(self) -> None:
        self.selected_row = (self.selected_row - 1) % len(self.processes)

    @on_keyboard("down")
    def _next(self) -> None:
        self.selected_row = (self.selected_row + 1) % len(self.processes)

    @on_tick
    def _tick(self) -> None:
        self.cpu_history.pop(0)
        new_val = max(
            0, min(100, self.cpu_history[-1] + random.randint(-15, 15))
        )
        self.cpu_history.append(new_val)
        self.memory_ratio = max(
            0.1, min(1.0, self.memory_ratio + random.uniform(-0.02, 0.02))
        )

    def grid_render(self) -> None:
        spark_width = max(10, int(self.columns * 0.4) - 4)
        gauge_width = max(8, spark_width - 12)
        self.main.left.cpu = _build_sparkline(self.cpu_history, spark_width)
        self.main.left.gauges.mem = _build_gauge(
            self.memory_ratio,
            "RAM",
            gauge_width,
            f"#{tailwind_color('sky', 400).r:02x}{tailwind_color('sky', 400).g:02x}{tailwind_color('sky', 400).b:02x}",
        )
        self.main.left.gauges.disk = _build_gauge(
            self.disk_percent / 100,
            "Disk Space",
            gauge_width,
            f"#{tailwind_color('rose', 400).r:02x}{tailwind_color('rose', 400).g:02x}{tailwind_color('rose', 400).b:02x}",
        )
        self.main.right = _build_table(self.processes, self.selected_row)


if __name__ == "__main__":
    Terminal().run(Dashboard())
