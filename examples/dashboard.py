"""xnano example — dashboard.py

A premium system monitoring dashboard simulation using xnano widgets.
"""

from __future__ import annotations

import random
import sys
import time

from xnano.chart import Sparkline
from xnano.color import Color
from xnano.events import poll_event
from xnano.layout import Constraint, Layout
from xnano.style import Borders, Style
from xnano.table import Cell, Row, Table, TableState
from xnano.tailwind import tailwind
from xnano.terminal import Frame, Terminal
from xnano.text import Line
from xnano.widgets import Block, Gauge, Paragraph


class SystemDashboard:
    def __init__(self) -> None:
        self.cpu_history: list[int] = [
            random.randint(5, 40) for _ in range(200)
        ]
        self.memory_ratio = 0.35
        self.disk_percent = 55
        self.processes = [
            ("systemd", "1.2%", "120MB", "Running"),
            ("xnano_agent", "18.5%", "45MB", "Running"),
            ("rust_core", "5.4%", "180MB", "Running"),
            ("python_tui", "2.1%", "60MB", "Running"),
            ("dockerd", "0.0%", "310MB", "Sleeping"),
        ]
        self.selected_row = 0
        self.table_state = TableState(selected=0)

        # Style System
        self.purple_border = Style(foreground=tailwind("violet", 500))
        self.emerald_accent = Style(
            foreground=tailwind("emerald", 400), modifiers="bold"
        )
        self.rose_accent = Style(foreground=tailwind("rose", 400))
        self.sky_accent = Style(foreground=tailwind("sky", 400))
        self.dim_style = Style(foreground=tailwind("slate", 500))

    def update(self) -> None:
        # Simulate live metric updates
        self.cpu_history.pop(0)
        new_val = max(
            0, min(100, self.cpu_history[-1] + random.randint(-15, 15))
        )
        self.cpu_history.append(new_val)

        self.memory_ratio = max(
            0.1, min(1.0, self.memory_ratio + random.uniform(-0.02, 0.02))
        )

        # Keep table selection in bounds
        if (
            random.random() < 0.1
        ):  # periodically move selection to simulate user behavior or activity
            self.selected_row = (self.selected_row + 1) % len(self.processes)
            self.table_state.select(self.selected_row)

    def draw(self, frame: Frame) -> None:
        area = frame.area()

        # Layout Tree:
        # Vertical split: Title Header (1 row), Main Content (fill), Footer Help (1 row)
        root_layout = Layout(
            direction="vertical",
            constraints=[
                Constraint.length(1),
                Constraint.fill(1),
                Constraint.length(1),
            ],
        )
        splits = root_layout.split(area)
        header_area, main_area, footer_area = splits[0], splits[1], splits[2]

        # Draw Header
        header_text = Line(
            "   SUPER COOL VERY IMPORTANT DASHBOARD   ",
            style=Style(
                foreground="white",
                background=tailwind("violet", 950),
                modifiers="bold",
            ),
        )
        frame.render_widget(Paragraph(header_text), header_area)

        # Main Area: Split horizontally into Left Column (Metrics) and Right Column (Processes)
        main_layout = Layout(
            direction="horizontal",
            constraints=[
                Constraint.percentage(40),
                Constraint.percentage(60),
            ],
            spacing=1,
        )
        cols = main_layout.split(main_area)
        left_col, right_col = cols[0], cols[1]

        # Left Column: Split vertically into CPU Sparkline (fill 1) and Memory/Disk Gauges (fill 1)
        left_layout = Layout(
            direction="vertical",
            constraints=[
                Constraint.fill(1),
                Constraint.fill(1),
            ],
        )
        left_splits = left_layout.split(left_col)
        cpu_area, gauges_area = left_splits[0], left_splits[1]

        # Render CPU Sparkline border Block
        cpu_block = Block(
            title=" CPU Usage History (%) ",
            borders="all",
            border_type="rounded",
            border_style=self.purple_border,
        )
        frame.render_widget(cpu_block, cpu_area)

        inner_area = cpu_block.inner(cpu_area)
        W = inner_area.width

        if W > 0:
            # We want a transition like: Blue -> Cyan -> Green -> Yellow -> Orange -> Red -> Purple -> Violet -> Blue
            keyframes = [
                Color.from_hex("#38bdf8"),  # sky-400
                Color.from_hex("#2dd4bf"),  # teal-400
                Color.from_hex("#4ade80"),  # emerald-400
                Color.from_hex("#a3e635"),  # lime-400
                Color.from_hex("#facc15"),  # amber-400
                Color.from_hex("#f97316"),  # orange-500
                Color.from_hex("#ef4444"),  # red-500
                Color.from_hex("#ec4899"),  # pink-500
                Color.from_hex("#a855f7"),  # purple-500
                Color.from_hex("#6366f1"),  # indigo-500
                Color.from_hex("#3b82f6"),  # blue-500
            ]

            def get_gradient_color(i: int, total: int) -> Color:
                if total <= 1:
                    return keyframes[0]
                pos = (i / (total - 1)) * (len(keyframes) - 1)
                idx = int(pos)
                t = pos - idx
                if idx >= len(keyframes) - 1:
                    return keyframes[-1]
                return Color.lerp(keyframes[idx], keyframes[idx + 1], t)

            # Draw sparkline column by column to apply the gradient colors
            data_to_draw = (
                self.cpu_history[-W:]
                if len(self.cpu_history) >= W
                else ([0] * (W - len(self.cpu_history)) + self.cpu_history)
            )
            col_layout = Layout(
                direction="horizontal", constraints=[Constraint.length(1)] * W
            )
            cols = col_layout.split(inner_area)

            for i in range(W):
                val = data_to_draw[i]
                col_color = get_gradient_color(i, W)
                col_style = Style(foreground=col_color, modifiers="bold")
                spark = Sparkline([val], max_value=100, style=col_style)
                frame.render_widget(spark, cols[i])

        # Render Gauges (Memory & Disk)
        gauges_layout = Layout(
            direction="vertical",
            constraints=[
                Constraint.length(3),
                Constraint.length(3),
            ],
            spacing=1,
        )
        gauge_splits = gauges_layout.split(gauges_area)
        mem_area, disk_area = gauge_splits[0], gauge_splits[1]

        mem_gauge = Gauge(
            ratio=self.memory_ratio,
            label=f"RAM: {self.memory_ratio * 100:.1f}%",
            block=Block(
                title=" Memory Info ",
                borders="all",
                border_type="rounded",
                border_style=self.purple_border,
            ),
            gauge_style=self.sky_accent,
        )
        frame.render_widget(mem_gauge, mem_area)

        disk_gauge = Gauge(
            percent=self.disk_percent,
            label=f"Disk Space: {self.disk_percent}%",
            block=Block(
                title=" Disk Storage ",
                borders="all",
                border_type="rounded",
                border_style=self.purple_border,
            ),
            gauge_style=self.rose_accent,
        )
        frame.render_widget(disk_gauge, disk_area)

        # Right Column: Processes Table
        table_rows = []
        for name, cpu, ram, status in self.processes:
            table_rows.append(
                Row(
                    [
                        Cell(
                            name,
                            style=Style(foreground="white", modifiers="bold"),
                        ),
                        Cell(cpu, style=self.emerald_accent),
                        Cell(ram, style=self.sky_accent),
                        Cell(status, style=self.dim_style),
                    ]
                )
            )

        headers = Row(
            [
                Cell("Process Name", style=self.dim_style),
                Cell("CPU %", style=self.dim_style),
                Cell("Memory", style=self.dim_style),
                Cell("Status", style=self.dim_style),
            ]
        )

        table = Table(
            table_rows,
            [
                Constraint.percentage(35),
                Constraint.percentage(20),
                Constraint.percentage(25),
                Constraint.percentage(20),
            ],
            header=headers,
            block=Block(
                title=" Active Processes ",
                borders="all",
                border_type="rounded",
                border_style=self.purple_border,
            ),
            row_highlight_style=Style(
                background=tailwind("violet", 900),
                foreground="white",
                modifiers="bold",
            ),
            highlight_symbol="→ ",
        )
        frame.render_stateful_widget(table, right_col, self.table_state)

        # Draw Footer Help Bar
        footer_text = Line(
            "  [Ctrl+C] Quit  ●  [Up/Down] Navigate Table  ",
            style=self.dim_style,
        )
        frame.render_widget(Paragraph(footer_text), footer_area)


def main() -> None:
    dash = SystemDashboard()

    with Terminal() as term:
        term.clear()

        while True:
            # Poll events with a 250ms frame step for real-time tick updates
            event = poll_event(250)
            if event and event.keyboard and event.keyboard.is_press:
                if event.keyboard.matches("ctrl+c") or event.keyboard.matches(
                    "q"
                ):
                    break
                elif event.keyboard.matches("up"):
                    dash.selected_row = (dash.selected_row - 1) % len(
                        dash.processes
                    )
                    dash.table_state.select(dash.selected_row)
                elif event.keyboard.matches("down"):
                    dash.selected_row = (dash.selected_row + 1) % len(
                        dash.processes
                    )
                    dash.table_state.select(dash.selected_row)

            dash.update()
            term.draw(dash.draw)


if __name__ == "__main__":
    main()
