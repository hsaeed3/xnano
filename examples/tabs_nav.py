"""xnano example — tabs_nav.py

Tab-based layout and list scrollbar selection demo.
"""

from __future__ import annotations

import sys

from xnano.events import poll_event
from xnano.layout import Constraint, Layout, Rectangle
from xnano.scroll import Scrollbar, ScrollbarState
from xnano.style import Borders, Style
from xnano.tailwind import tailwind
from xnano.terminal import Frame, Terminal
from xnano.text import Line
from xnano.widgets import Block, ListItem, ListState, ListView, Paragraph, Tabs


class MultiTabApp:
    def __init__(self) -> None:
        self.selected_tab = 0
        self.tabs = ["Home Settings", "Database Config", "About Antigravity"]

        # Selection lists for Tab 0 & Tab 1
        self.settings_options = [
            "Enable Auto-save",
            "Color Theme: Catppuccin",
            "Enable Telemetry",
            "Port Number: 8080",
            "Buffer Size: 4096",
            "Max Threads: 8",
        ]
        self.settings_state = ListState(selected=0)

        self.db_options = [
            "Host: localhost",
            "User: postgres",
            "Password: *****",
            "Database: test_db",
            "SSL Mode: require",
            "Pool Size: 20",
        ]
        self.db_state = ListState(selected=0)

        # Style System
        self.border_style = Style(foreground=tailwind("sky", 500))
        self.accent_style = Style(
            foreground=tailwind("sky", 400), modifiers="bold"
        )
        self.muted_style = Style(foreground=tailwind("slate", 400))

    def draw(self, frame: Frame) -> None:
        area = frame.area()

        # Vertical layout: Tab bar header (3), Content Canvas (fill), Footer Instructions (1)
        root_layout = Layout(
            direction="vertical",
            constraints=[
                Constraint.length(3),
                Constraint.fill(1),
                Constraint.length(1),
            ],
        )
        splits = root_layout.split(area)
        tab_area, content_area, footer_area = splits[0], splits[1], splits[2]

        # Draw Tabs Widget
        tab_titles = [f" {t} " for t in self.tabs]
        tabs_widget = Tabs(
            tab_titles,
            selected=self.selected_tab,
            block=Block(
                title=" Project Settings TUI ",
                borders="all",
                border_type="rounded",
                border_style=self.border_style,
            ),
            highlight_style=self.accent_style,
        )
        frame.render_widget(tabs_widget, tab_area)

        # Render Content based on selected tab
        if self.selected_tab == 0:
            self.draw_settings_page(frame, content_area)
        elif self.selected_tab == 1:
            self.draw_db_page(frame, content_area)
        else:
            self.draw_about_page(frame, content_area)

        # Render Footer
        footer = Paragraph(
            Line(
                "  [Left/Right] Switch Tabs  ●  [Up/Down] Select Options  ●  [Ctrl+C] Quit  ",
                style=self.muted_style,
            )
        )
        frame.render_widget(footer, footer_area)

    def draw_settings_page(self, frame: Frame, area: Rectangle) -> None:
        # Split page horizontally: list of options vs help preview card
        layout = Layout(
            direction="horizontal",
            constraints=[Constraint.percentage(60), Constraint.percentage(40)],
            spacing=1,
        )
        cols = layout.split(area)
        list_area, preview_area = cols[0], cols[1]

        # List selection
        items = [ListItem(opt) for opt in self.settings_options]
        list_widget = ListView(
            items,
            block=Block(
                title=" General Settings Options ",
                borders="all",
                border_type="rounded",
                border_style=self.border_style,
            ),
            highlight_symbol="✔ ",
            highlight_style=self.accent_style,
        )
        frame.render_stateful_widget(
            list_widget, list_area, self.settings_state
        )

        # Preview Card
        curr_selected = self.settings_options[
            self.settings_state.selected or 0
        ]
        preview_text = (
            f"Option: {curr_selected}\n\n"
            "This toggle enables configuration properties inside the "
            "Antigravity platform CLI engine environment."
        )
        preview_widget = Paragraph(
            preview_text,
            block=Block(
                title=" Help Preview ",
                borders="all",
                border_type="rounded",
                border_style=self.border_style,
            ),
            style=self.muted_style,
        )
        frame.render_widget(preview_widget, preview_area)

    def draw_db_page(self, frame: Frame, area: Rectangle) -> None:
        # DB Configuration Tab
        items = [ListItem(opt) for opt in self.db_options]
        list_widget = ListView(
            items,
            block=Block(
                title=" PostgreSQL Credentials Config ",
                borders="all",
                border_type="rounded",
                border_style=self.border_style,
            ),
            highlight_symbol="⚡ ",
            highlight_style=Style(
                foreground=tailwind("amber", 400), modifiers="bold"
            ),
        )
        frame.render_stateful_widget(list_widget, area, self.db_state)

    def draw_about_page(self, frame: Frame, area: Rectangle) -> None:
        # About text block
        about_text = (
            "Antigravity CLI Framework v2.0\n\n"
            "This client wrapper wraps Ratatui (Rust TUI engine) and Tachyonfx "
            "(animation system) using PyO3 bindings into a beautiful, native-feeling, "
            "Pydantic-like declarative layout system for Python.\n\n"
            "Developed with love by Google DeepMind Advanced Agentic Coding."
        )
        widget = Paragraph(
            about_text,
            block=Block(
                title=" Project Information ",
                borders="all",
                border_type="rounded",
                border_style=self.border_style,
            ),
            style=Style(foreground=tailwind("sky", 100)),
        )
        frame.render_widget(widget, area)


def main() -> None:
    app = MultiTabApp()

    with Terminal() as term:
        term.clear()

        while True:
            event = poll_event(100)
            if event and event.key and event.key.is_press:
                if event.key.matches("ctrl+c") or event.key.matches("q"):
                    break
                elif event.key.matches("left"):
                    app.selected_tab = (app.selected_tab - 1) % len(app.tabs)
                elif event.key.matches("right"):
                    app.selected_tab = (app.selected_tab + 1) % len(app.tabs)
                elif event.key.matches("up"):
                    if app.selected_tab == 0:
                        app.settings_state.select_previous()
                    elif app.selected_tab == 1:
                        app.db_state.select_previous()
                elif event.key.matches("down"):
                    if app.selected_tab == 0:
                        app.settings_state.select_next()
                    elif app.selected_tab == 1:
                        app.db_state.select_next()

            term.draw(app.draw)


if __name__ == "__main__":
    main()
