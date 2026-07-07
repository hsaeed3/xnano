"""xnano example — tabs_nav.py

Tab-based layout demonstrating completely different screens per tab.
"""

from __future__ import annotations

import time

from xnano.beta import Field, Grid, Terminal, on_keyboard, on_tick
from xnano.beta.components import Text
from xnano.beta.color import tailwind_color


_TABS = ["System Monitor", "Configuration", "Log Viewer"]

_LOGS = [
    "[INFO] System initialized.",
    "[INFO] Rust PyO3 TUI binding loaded successfully.",
    "[DEBUG] String pool aligned.",
    "[INFO] Running main event loop.",
    "[WARN] CPU temperature spiked to 72°C.",
    "[INFO] Flushing off-screen buffers.",
    "[DEBUG] Garbage collection complete.",
    "[INFO] Active connections: 42.",
]


def _tab_bar(selected: int) -> Text:
    border_color = [
        tailwind_color("emerald", 500),
        tailwind_color("amber", 500),
        tailwind_color("indigo", 500),
    ][selected]
    accent = [
        tailwind_color("emerald", 400),
        tailwind_color("amber", 400),
        tailwind_color("indigo", 400),
    ][selected]
    parts: list[str | Text] = []
    for i, name in enumerate(_TABS):
        if i == selected:
            parts.append(
                Text(
                    f" {name} ", color=accent, modifiers=("bold", "underline")
                )
            )
        else:
            parts.append(Text(f" {name} ", color=tailwind_color("slate", 500)))
        if i < len(_TABS) - 1:
            parts.append(Text(" │ ", color=border_color))
    return Text(parts)


def _monitor_screen(elapsed: float) -> Text:
    def gauge(label: str, ratio: float, color: str, width: int = 36) -> Text:
        filled = int(ratio * width)
        return Text(
            [
                Text(
                    f"  {label}: {ratio * 100:.0f}%\n",
                    color=tailwind_color("slate", 300),
                ),
                Text("  "),
                Text("█" * filled, color=color),
                Text(
                    "░" * (width - filled), color=tailwind_color("slate", 700)
                ),
                Text("\n"),
            ]
        )

    cpu = (50 + 30 * (elapsed % 3 - 1.5)) / 100
    mem = (65 + 10 * (elapsed % 5 - 2.5)) / 100
    cpu = max(0.0, min(1.0, cpu))
    mem = max(0.0, min(1.0, mem))
    disk = 0.42

    spark_data = [int(10 + 5 * (i % 3) + 2 * (elapsed % 2)) for i in range(40)]
    spark_chars = " ▁▂▃▄▅▆▇█"
    spark = "".join(
        spark_chars[
            min(int(v / 30 * (len(spark_chars) - 1)), len(spark_chars) - 1)
        ]
        for v in spark_data
    )

    return Text(
        [
            Text("\n"),
            gauge(
                "CPU Load",
                cpu,
                f"#{tailwind_color('emerald', 400).r:02x}{tailwind_color('emerald', 400).g:02x}{tailwind_color('emerald', 400).b:02x}",
            ),
            Text("\n"),
            gauge(
                "Memory  ",
                mem,
                f"#{tailwind_color('teal', 400).r:02x}{tailwind_color('teal', 400).g:02x}{tailwind_color('teal', 400).b:02x}",
            ),
            Text("\n"),
            gauge(
                "Disk     ",
                disk,
                f"#{tailwind_color('cyan', 400).r:02x}{tailwind_color('cyan', 400).g:02x}{tailwind_color('cyan', 400).b:02x}",
            ),
            Text("\n\n"),
            Text("  CPU Load History\n", color=tailwind_color("slate", 400)),
            Text(f"  {spark}", color=tailwind_color("emerald", 400)),
        ]
    )


def _config_screen(elapsed: float) -> str:
    active_conns = int(20 + elapsed % 5)
    return (
        "\n"
        "  DATABASE ENGINE CONFIGURATION\n"
        "  ====================================\n\n"
        "  [Connection Details]\n"
        "  - DB_HOST: localhost (Active)\n"
        "  - DB_USER: admin_postgres\n"
        "  - SSL_MODE: require (Encrypted)\n\n"
        f"  - Active Connections: {active_conns}\n"
        "  - Thread Pool State: Idle"
    )


def _logs_screen(elapsed: float) -> str:
    return "\n".join(_LOGS)


class TabNav(Grid, direction="vertical"):
    tab_bar: Text = Field(
        default=Text(""),
        size=3,
        border="rounded",
        border_color=tailwind_color("emerald", 500),
        title=" Multi-Screen Demonstration App (Switch with Left/Right) ",
    )
    screen: Text = Field(
        default=Text(""),
        border="rounded",
        border_color=tailwind_color("emerald", 500),
        color=tailwind_color("slate", 300),
    )
    status: str = Field(
        default="",
        size=3,
        border="rounded",
        border_color=tailwind_color("slate", 700),
        color=tailwind_color("slate", 400),
    )

    selected_tab: int = Field(default=0, state=True)
    start_time: float = Field(default_factory=time.time, state=True)

    @on_keyboard("left")
    def _prev_tab(self) -> None:
        self.selected_tab = (self.selected_tab - 1) % len(_TABS)

    @on_keyboard("right")
    def _next_tab(self) -> None:
        self.selected_tab = (self.selected_tab + 1) % len(_TABS)

    def grid_render(self) -> None:
        tab = self.selected_tab
        elapsed = time.time() - self.start_time

        accent = [
            tailwind_color("emerald", 500),
            tailwind_color("amber", 500),
            tailwind_color("indigo", 500),
        ][tab]
        accent_hex = f"#{accent.r:02x}{accent.g:02x}{accent.b:02x}"

        self.grid_set_field("tab_bar", border_color=accent)
        self.grid_set_field("screen", border_color=accent)
        self.grid_set_field("status", border_color=accent)

        self.tab_bar = _tab_bar(tab)

        if tab == 0:
            self.screen = _monitor_screen(elapsed)
        elif tab == 1:
            self.screen = Text(
                _config_screen(elapsed),
                color=tailwind_color("zinc", 100),
            )
        else:
            self.screen = Text(_logs_screen(elapsed))

        self.status = f"  [Log Stream Active] Elapsed: {elapsed:.1f}s  ●  Press [q] to exit"


if __name__ == "__main__":
    Terminal(tick_interval=32).run(TabNav())
