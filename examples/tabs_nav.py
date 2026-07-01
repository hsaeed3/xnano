"""xnano example — tabs_nav.py

Tab-based layout demonstrating completely changing screens, layouts, and styles.
"""

from __future__ import annotations

import time
from xnano.events import poll_event
from xnano.layout import Layout
from xnano.style import Style
from xnano.tailwind import tailwind
from xnano.terminal import Terminal
from xnano.widgets import Block, Paragraph, Tabs, Gauge
from xnano.chart import Sparkline


class MultiScreenApp:
    def __init__(self) -> None:
        self.selected_tab = 0
        self.tabs = ["System Monitor", "Configuration", "Log Viewer"]
        self.start_time = time.time()
        
        # Log viewer mock logs
        self.logs = [
            "[INFO] System initialized.",
            "[INFO] Rust PyO3 TUI binding loaded successfully.",
            "[DEBUG] String pool aligned.",
            "[INFO] Running main event loop.",
            "[WARN] CPU temperature spiked to 72°C.",
            "[INFO] Flushing off-screen buffers.",
            "[DEBUG] Garbage collection complete.",
            "[INFO] Active connections: 42.",
        ]

    def draw(self, frame) -> None:
        area = frame.area()
        elapsed = time.time() - self.start_time

        # Split the screen into:
        # 1. Navigation Header (height=3)
        # 2. Main Content Canvas (fill)
        # Using named constraints dictionary API!
        root_layout = Layout(
            direction="vertical",
            constraints={
                "nav": 3,
                "canvas": "fill"
            }
        )
        
        if self.selected_tab == 0:
            border_color = tailwind("emerald", 500)
            accent_color = tailwind("emerald", 400)
        elif self.selected_tab == 1:
            border_color = tailwind("amber", 500)
            accent_color = tailwind("amber", 400)
        else:
            border_color = tailwind("indigo", 500)
            accent_color = tailwind("indigo", 400)

        nav_widget = Tabs(
            [f" {t} " for t in self.tabs],
            selected=self.selected_tab,
            block=Block(
                title=" Multi-Screen Demonstration App (Switch with Left/Right) ",
                borders="all",
                border_type="rounded",
                border_style=Style(foreground=border_color)
            ),
            highlight_style=Style(foreground=accent_color, modifiers="bold")
        )

        areas = root_layout.split(area)
        frame.render_widget(nav_widget, areas["nav"])
        
        canvas_area = areas["canvas"]

        # Render completely different layout per tab screen
        if self.selected_tab == 0:
            self.draw_monitor_screen(frame, canvas_area, elapsed)
        elif self.selected_tab == 1:
            self.draw_config_screen(frame, canvas_area, elapsed)
        else:
            self.draw_logs_screen(frame, canvas_area, elapsed)

    def draw_monitor_screen(self, frame, area, elapsed: float) -> None:
        # Layout: Split horizontally into Left Panel (percentage=60) and Right Panel (percentage=40)
        screen_layout = Layout(
            direction="horizontal",
            constraints={
                "left": 0.60,
                "right": 0.40
            },
            spacing=1
        )
        
        # Left panel has a vertical layout for Gauges
        left_layout = Layout(
            direction="vertical",
            constraints={
                "cpu": 3,
                "memory": 3,
                "disk": 3
            },
            spacing=1
        )
        
        # Calculate dynamic values for gauges
        cpu_val = int(50 + 30 * (elapsed % 3 - 1.5))
        mem_val = int(65 + 10 * (elapsed % 5 - 2.5))
        disk_val = 42

        areas = screen_layout.split(area)
        
        # Map left section gauges using Layout.map
        frame.render(
            left_layout.map(
                areas["left"],
                widgets={
                    "cpu": Gauge(
                        ratio=cpu_val / 100.0,
                        label=f"CPU Load: {cpu_val}%",
                        style=Style(foreground=tailwind("emerald", 400), background=tailwind("slate", 800)),
                        block=Block(borders="all", border_type="rounded", border_style=Style(foreground=tailwind("emerald", 600)))
                    ),
                    "memory": Gauge(
                        ratio=mem_val / 100.0,
                        label=f"Memory Usage: {mem_val}%",
                        style=Style(foreground=tailwind("teal", 400), background=tailwind("slate", 800)),
                        block=Block(borders="all", border_type="rounded", border_style=Style(foreground=tailwind("teal", 600)))
                    ),
                    "disk": Gauge(
                        ratio=disk_val / 100.0,
                        label=f"Disk Usage: {disk_val}%",
                        style=Style(foreground=tailwind("cyan", 400), background=tailwind("slate", 800)),
                        block=Block(borders="all", border_type="rounded", border_style=Style(foreground=tailwind("cyan", 600)))
                    )
                }
            )
        )

        # Right panel shows a Sparkline history graph
        spark_data = [int(10 + 5 * (i % 3) + 2 * (elapsed % 2)) for i in range(40)]
        spark_widget = Sparkline(
            spark_data,
            style=Style(foreground=tailwind("emerald", 400)),
            block=Block(
                title=" CPU Load History ",
                borders="all",
                border_type="rounded",
                border_style=Style(foreground=tailwind("emerald", 600))
            )
        )
        frame.render_widget(spark_widget, areas["right"])

    def draw_config_screen(self, frame, area, elapsed: float) -> None:
        # Layout: Center configuration card
        screen_layout = Layout(
            direction="vertical",
            constraints={
                "padding_top": "fill",
                "card": 14,
                "padding_bottom": "fill"
            }
        )
        
        card_layout = Layout(
            direction="horizontal",
            constraints={
                "padding_left": "fill",
                "content": 60,
                "padding_right": "fill"
            }
        )

        areas = screen_layout.split(area)
        cols = card_layout.split(areas["card"])

        config_text = (
            "  DATABASE ENGINE CONFIGURATION\n"
            "  ====================================\n\n"
            "  [Connection Details]\n"
            "  - DB_HOST: localhost (Active)\n"
            "  - DB_USER: admin_postgres\n"
            "  - SSL_MODE: require (Encrypted)\n\n"
            f"  - Active Connections: {int(20 + elapsed % 5)}\n"
            "  - Thread Pool State: Idle"
        )
        
        card_widget = Paragraph(
            config_text,
            block=Block(
                title=" PostgreSQL Credentials ",
                borders="all",
                border_type="rounded",
                border_style=Style(foreground=tailwind("amber", 500))
            ),
            style=Style(foreground=tailwind("zinc", 100))
        )
        frame.render_widget(card_widget, cols["content"])

    def draw_logs_screen(self, frame, area, elapsed: float) -> None:
        screen_layout = Layout(
            direction="vertical",
            constraints={
                "logs": "fill",
                "status": 3
            }
        )
        
        log_content = "\n".join(self.logs)
        
        logs_widget = Paragraph(
            log_content,
            block=Block(
                title=" System Events Log Stream ",
                borders="all",
                border_type="rounded",
                border_style=Style(foreground=tailwind("indigo", 500))
            ),
            style=Style(foreground=tailwind("slate", 300))
        )
        
        status_widget = Paragraph(
            f"  [Log Stream Active] Elapsed time: {elapsed:.2f}s  ●  Press [q] to exit",
            block=Block(
                borders="all",
                border_type="rounded",
                border_style=Style(foreground=tailwind("indigo", 600))
            ),
            style=Style(foreground=tailwind("indigo", 300))
        )

        frame.render(
            screen_layout.map(
                area,
                widgets={
                    "logs": logs_widget,
                    "status": status_widget
                }
            )
        )


def main() -> None:
    app = MultiScreenApp()

    with Terminal() as term:
        term.clear()

        while True:
            event = poll_event(16)
            if event and event.key and event.key.is_press:
                if event.key.matches("ctrl+c") or event.key.matches("q"):
                    break
                elif event.key.matches("left"):
                    app.selected_tab = (app.selected_tab - 1) % len(app.tabs)
                elif event.key.matches("right"):
                    app.selected_tab = (app.selected_tab + 1) % len(app.tabs)

            term.draw(app.draw)


if __name__ == "__main__":
    main()
