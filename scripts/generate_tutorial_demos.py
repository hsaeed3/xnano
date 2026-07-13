#!/usr/bin/env python3
"""scripts.generate_tutorial_demos

---

Generate fitted light/dark GIFs for docs/tutorials.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = REPOSITORY_ROOT / "docs" / "assets" / "tutorials"
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

DEMOS: tuple[Demo, ...] = (
    Demo(
        name="streaming_grid",
        code=code("""
            from xnano import BaseGrid, Field, Terminal, Context
            from xnano.events import on_keyboard, on_tick

            class Stream(BaseGrid, direction="vertical", gap=1):
                body: str = Field(
                    default="Press enter to stream…",
                    border="rounded",
                )
                hint: str = Field(
                    default="enter · stream   q · quit",
                    height=1,
                    color="slate-500",
                )
                chunks: list = Field(default_factory=list, state=True)
                index: int = Field(default=0, state=True)

                @on_keyboard("enter")
                def begin(self) -> None:
                    words = (
                        "Streaming is ticks writing into a field, "
                        "one chunk at a time."
                    ).split()
                    self.chunks = [
                        w if i == len(words) - 1 else w + " "
                        for i, w in enumerate(words)
                    ]
                    self.index = 0
                    self.body = ""

                @on_tick(40)
                def advance(self) -> None:
                    if self.index >= len(self.chunks):
                        return
                    self.body = self.body + self.chunks[self.index]
                    self.index += 1

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(Stream())
        """),
        steps=(
            "Sleep 600ms",
            "Enter",
            "Sleep 2.5s",
        ),
        record_delay="500ms",
        content_rows=6,
        content_columns=56,
    ),
    Demo(
        name="text_inputs",
        code=code("""
            from xnano import BaseGrid, Field, Terminal, Context
            from xnano.components.text import Text
            from xnano.events import on_keyboard

            class Form(BaseGrid, direction="vertical", gap=1):
                name: Text = Field(
                    default_factory=lambda: Text(
                        "",
                        input=True,
                        placeholder="your name",
                    ),
                    height=1,
                    border="rounded",
                    title=" Name ",
                )
                result: str = Field(
                    default="Type and press enter.",
                    height=1,
                    color="slate-400",
                )

                @on_keyboard("enter")
                def submit(self) -> None:
                    value = (
                        self.name.content
                        if isinstance(self.name.content, str)
                        else ""
                    )
                    self.result = f"Hello {value or '—'}!"

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(Form())
        """),
        launch_delay="1.2s",
        steps=(
            "Sleep 400ms",
            'Type "Ada Lovelace"',
            "Sleep 500ms",
            "Enter",
            "Sleep 1.2s",
        ),
        record_delay="500ms",
        content_rows=8,
        gap_rows=3,
    ),
    Demo(
        name="selection_list",
        code=code("""
            from xnano import BaseGrid, Field, Terminal, Context
            from xnano.components.text import Text
            from xnano.events import on_keyboard

            ITEMS = ["Home", "Projects", "Settings", "About"]

            class Menu(BaseGrid, direction="vertical", gap=1):
                body: Text = Field(
                    default=Text(""),
                    border="rounded",
                    title=" Menu ",
                )
                status: str = Field(
                    default="Select an item.",
                    height=1,
                    color="slate-400",
                )
                hint: str = Field(
                    default="↑ / ↓ · move   enter · activate",
                    height=1,
                    color="slate-500",
                )
                items: list = Field(
                    default_factory=lambda: list(ITEMS),
                    state=True,
                )
                selected: int = Field(default=0, state=True)

                def _paint(self) -> None:
                    rows: list[Text] = []
                    for index, item in enumerate(self.items):
                        if index == self.selected:
                            rows.append(
                                Text([
                                    Text(
                                        f" › {item}",
                                        color="violet-300",
                                        modifiers=("bold",),
                                    )
                                ])
                            )
                        else:
                            rows.append(
                                Text([
                                    Text(
                                        f"   {item}",
                                        color="slate-400",
                                    )
                                ])
                            )
                    self.body = Text(rows)

                def __post_init__(self) -> None:
                    self._paint()

                @on_keyboard("up")
                def move_up(self) -> None:
                    self.selected = (
                        self.selected - 1
                    ) % len(self.items)
                    self._paint()

                @on_keyboard("down")
                def move_down(self) -> None:
                    self.selected = (
                        self.selected + 1
                    ) % len(self.items)
                    self._paint()

                @on_keyboard("enter")
                def activate(self) -> None:
                    self.status = (
                        f"Opened: {self.items[self.selected]}"
                    )

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(Menu())
        """),
        steps=(
            "Down@350ms 2",
            "Sleep 400ms",
            "Up@350ms 1",
            "Sleep 400ms",
            "Enter",
            "Sleep 700ms",
        ),
        record_delay="500ms",
        content_rows=8,
        content_columns=42,
    ),
    Demo(
        name="tabs",
        code=code("""
            from xnano import BaseGrid, Field, Terminal, Context
            from xnano.components.text import Text
            from xnano.events import on_keyboard

            TABS = ["Overview", "Config", "Logs"]

            class TabApp(BaseGrid, direction="vertical", gap=1):
                tab_bar: Text = Field(default=Text(""), height=1)
                screen: str = Field(
                    default="",
                    border="rounded",
                    title=" Screen ",
                )
                hint: str = Field(
                    default="← / → · switch   1–3 · jump",
                    height=1,
                    color="slate-500",
                )
                selected_tab: int = Field(default=0, state=True)

                @on_keyboard("left")
                def prev_tab(self) -> None:
                    self.selected_tab = (
                        self.selected_tab - 1
                    ) % len(TABS)

                @on_keyboard("right")
                def next_tab(self) -> None:
                    self.selected_tab = (
                        self.selected_tab + 1
                    ) % len(TABS)

                def grid_render(self) -> None:
                    parts: list[Text] = []
                    for index, name in enumerate(TABS):
                        if index == self.selected_tab:
                            parts.append(
                                Text(
                                    f" {name} ",
                                    color="violet-300",
                                    modifiers=("bold", "underline"),
                                )
                            )
                        else:
                            parts.append(
                                Text(f" {name} ", color="slate-500")
                            )
                        if index < len(TABS) - 1:
                            parts.append(
                                Text(" │ ", color="slate-600")
                            )
                    self.tab_bar = Text(parts)
                    bodies = {
                        0: "Overview — a short summary.",
                        1: "Config — host, port, theme.",
                        2: "Logs — [INFO] ready",
                    }
                    self.screen = bodies[self.selected_tab]
                    self.grid_set_field(
                        "screen",
                        title=f" {TABS[self.selected_tab]} ",
                    )

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(TabApp())
        """),
        steps=(
            "Right@400ms 1",
            "Sleep 600ms",
            "Right@400ms 1",
            "Sleep 600ms",
            "Left@400ms 1",
            "Sleep 700ms",
        ),
        record_delay="500ms",
        content_rows=7,
        content_columns=48,
    ),
    Demo(
        name="nested_panels",
        code=code("""
            from xnano import BaseGrid, Field, Terminal, Context
            from xnano.events import on_keyboard

            class Sidebar(BaseGrid, direction="vertical"):
                nav: str = Field(
                    default="  — Home\\n  — About\\n  — Settings",
                    border="rounded",
                    border_color="slate-600",
                    title=" Nav ",
                )
                status: str = Field(
                    default="  Ready",
                    height=1,
                    color="slate-500",
                )

            class Main(BaseGrid, direction="vertical", gap=1):
                title: str = Field(
                    default="  Workspace",
                    height=1,
                    color="violet-300",
                )
                body: str = Field(
                    default="Main content area.",
                    border="rounded",
                    border_color="violet-500",
                    title=" Content ",
                )

            class App(BaseGrid, direction="horizontal", gap=1):
                sidebar: Sidebar = Field(
                    default_factory=Sidebar,
                    width="30%",
                )
                main: Main = Field(
                    default_factory=Main,
                    width="1fr",
                )

                @on_keyboard("1")
                def show_home(self) -> None:
                    self.main.body = "Home — overview of the workspace."
                    self.sidebar.status = "  Home"

                @on_keyboard("2")
                def show_about(self) -> None:
                    self.main.body = "About — what this panel stack is for."
                    self.sidebar.status = "  About"

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(App())
        """),
        steps=(
            "Sleep 700ms",
            'Type "1"',
            "Sleep 700ms",
            'Type "2"',
            "Sleep 800ms",
        ),
        record_delay="500ms",
        content_rows=10,
        content_columns=64,
        width=1000,
    ),
    Demo(
        name="confirm_dialog",
        code=code("""
            from xnano import BaseGrid, Field, Terminal, Context
            from xnano.components.text import Text
            from xnano.events import on_keyboard

            class Trash(BaseGrid, direction="vertical", gap=1):
                body: str = Field(
                    default="Draft report.md is ready.",
                    border="rounded",
                    title=" File ",
                )
                status: str = Field(
                    default="Press d to delete.",
                    height=1,
                    color="slate-400",
                )
                hint: str = Field(
                    default="d · delete   q · quit",
                    height=1,
                    color="slate-500",
                )
                overlay: Text | None = Field(
                    default=None,
                    border="rounded",
                    title=" Confirm ",
                )
                pending: bool = Field(default=False, state=True)

                @on_keyboard("d")
                def request_delete(self) -> None:
                    if self.pending:
                        return
                    self.pending = True
                    self.overlay = Text(
                        "Delete draft report.md?\\n\\n"
                        "  y · confirm    n / esc · cancel",
                        color="amber-200",
                    )
                    self.status = "Waiting for confirmation…"
                    self.hint = "y · confirm   n / esc · cancel"

                @on_keyboard("y")
                def confirm(self) -> None:
                    if not self.pending:
                        return
                    self.body = "(empty — file deleted)"
                    self.status = "Deleted."
                    self._dismiss()

                @on_keyboard("n")
                def cancel(self) -> None:
                    if not self.pending:
                        return
                    self.status = "Delete cancelled."
                    self._dismiss()

                def _dismiss(self) -> None:
                    self.pending = False
                    self.overlay = None
                    self.hint = "d · delete   q · quit"

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(Trash())
        """),
        steps=(
            "Sleep 600ms",
            'Type "d"',
            "Sleep 900ms",
            'Type "n"',
            "Sleep 700ms",
        ),
        record_delay="500ms",
        content_rows=8,
        content_columns=48,
    ),
    Demo(
        name="live_progress",
        code=code("""
            from xnano import BaseGrid, Field, Terminal, Context
            from xnano.components.progress import Progress
            from xnano.events import on_keyboard, on_tick

            class Download(BaseGrid, direction="vertical", gap=1):
                status: str = Field(default="Downloading…", height=1)
                bar: Progress = Field(
                    default_factory=lambda: Progress(
                        value=0.0,
                        color="emerald-400",
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
                    self.bar = Progress(
                        value=ratio,
                        color="emerald-400",
                    )
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
        steps=("Sleep 3.5s",),
        record_delay="500ms",
        content_rows=4,
        content_columns=48,
    ),
    Demo(
        name="composed_text",
        code=code("""
            from xnano import BaseGrid, Field, Terminal, Context
            from xnano.components.text import Text
            from xnano.events import on_keyboard

            _COLORS = {
                "ok": "emerald-400",
                "warn": "amber-400",
                "err": "red-400",
            }
            _LABELS = {
                "ok": "healthy",
                "warn": "degraded",
                "err": "down",
            }

            def status_line(level: str) -> Text:
                color = _COLORS[level]
                return Text([
                    Text("● ", color=color),
                    Text(
                        level.upper(),
                        color=color,
                        modifiers=("bold",),
                    ),
                    Text(
                        f" — {_LABELS[level]}",
                        color="slate-400",
                    ),
                ])

            class StatusBar(BaseGrid, direction="vertical", gap=1):
                line: Text = Field(
                    default_factory=lambda: status_line("ok"),
                    height=1,
                )
                hint: str = Field(
                    default="1 ok · 2 warn · 3 err",
                    height=1,
                    color="slate-500",
                )
                level: str = Field(default="ok", state=True)

                @on_keyboard("1")
                def set_ok(self) -> None:
                    self.level = "ok"
                    self.line = status_line(self.level)

                @on_keyboard("2")
                def set_warn(self) -> None:
                    self.level = "warn"
                    self.line = status_line(self.level)

                @on_keyboard("3")
                def set_err(self) -> None:
                    self.level = "err"
                    self.line = status_line(self.level)

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(StatusBar())
        """),
        steps=(
            'Type "2"',
            "Sleep 600ms",
            'Type "3"',
            "Sleep 600ms",
            'Type "1"',
            "Sleep 700ms",
        ),
        record_delay="500ms",
        content_rows=4,
        content_columns=42,
    ),
    Demo(
        name="shared_state",
        code=code("""
            import dataclasses
            from xnano import BaseGrid, Field, Terminal, Context
            from xnano.events import on_keyboard

            @dataclasses.dataclass
            class AppState:
                count: int = 0
                last_key: str = ""

            class Counter(BaseGrid, direction="vertical", gap=1):
                label: str = Field(default="Count: 0", height=1)
                meta: str = Field(
                    default="last: —",
                    height=1,
                    color="slate-500",
                )

                @on_keyboard("up")
                def inc(self, ctx: Context[AppState]) -> None:
                    state = ctx.get_state()
                    state.count += 1
                    state.last_key = "up"
                    self.label = f"Count: {state.count}"
                    self.meta = f"last: {state.last_key}"

                @on_keyboard("down")
                def dec(self, ctx: Context[AppState]) -> None:
                    state = ctx.get_state()
                    state.count -= 1
                    state.last_key = "down"
                    self.label = f"Count: {state.count}"
                    self.meta = f"last: {state.last_key}"

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            Terminal(state=AppState()).run(Counter())
        """),
        steps=(
            "Up@300ms 3",
            "Sleep 400ms",
            "Down@300ms 1",
            "Sleep 600ms",
        ),
        record_delay="500ms",
        content_rows=4,
        content_columns=36,
    ),
    Demo(
        name="live_sparklines",
        code=code("""
            import random
            from xnano import BaseGrid, Field, Terminal, Context
            from xnano.components.sparkline import Sparkline
            from xnano.events import on_keyboard, on_tick

            _HISTORY = 24

            class MetricStrip(BaseGrid, direction="vertical", gap=1):
                heading: str = Field(
                    default="cpu · simulated",
                    height=1,
                    color="slate-400",
                )
                chart: Sparkline = Field(
                    default_factory=lambda: Sparkline(
                        data=[0] * _HISTORY,
                        max_value=100,
                        color="emerald-400",
                    ),
                    height=4,
                )
                readout: str = Field(default="—", height=1)
                samples: list[int] = Field(
                    default_factory=lambda: [0] * _HISTORY,
                    state=True,
                )

                @on_tick(120)
                def sample(self) -> None:
                    next_value = max(
                        0,
                        min(
                            100,
                            self.samples[-1] + random.randint(-12, 14),
                        ),
                    )
                    self.samples.append(next_value)
                    if len(self.samples) > _HISTORY:
                        self.samples = self.samples[-_HISTORY:]
                    self.chart = Sparkline(
                        data=list(self.samples),
                        max_value=100,
                        color="emerald-400",
                    )
                    self.readout = f"now {next_value:>3}"

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(MetricStrip())
        """),
        steps=("Sleep 3.5s",),
        record_delay="500ms",
        content_rows=7,
        content_columns=40,
    ),
    Demo(
        name="table_browser",
        code=code("""
            from xnano import BaseGrid, Field, Terminal, Context
            from xnano.components.table import Column, Table
            from xnano.events import on_keyboard

            class Services(Table):
                service: str = Column()
                status: str = Column(
                    color=lambda v: "green" if v == "ok" else "red"
                )
                latency: int = Column(align="right", format="{}ms")

            ROWS = [
                {"service": "api", "status": "ok", "latency": 12},
                {
                    "service": "db",
                    "status": "degraded",
                    "latency": 340,
                },
                {"service": "cache", "status": "ok", "latency": 4},
            ]

            class Browser(BaseGrid, direction="vertical", gap=1):
                table: Services = Field(
                    default_factory=lambda: Services(
                        data=ROWS,
                        selected=0,
                    ),
                )
                status: str = Field(
                    default="",
                    height=1,
                    color="slate-400",
                )
                hint: str = Field(
                    default="↑ / ↓ · select",
                    height=1,
                    color="slate-500",
                )
                rows: list = Field(
                    default_factory=lambda: list(ROWS),
                    state=True,
                )
                index: int = Field(default=0, state=True)

                def _refresh(self) -> None:
                    self.table = Services(
                        data=self.rows,
                        selected=self.index,
                    )
                    row = self.rows[self.index]
                    self.status = (
                        f"  {row['service']}: {row['status']} · "
                        f"{row['latency']}ms"
                    )

                @on_keyboard("up")
                def previous(self) -> None:
                    self.index = max(0, self.index - 1)
                    self._refresh()

                @on_keyboard("down")
                def next(self) -> None:
                    self.index = min(
                        len(self.rows) - 1,
                        self.index + 1,
                    )
                    self._refresh()

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

                def __post_init__(self) -> None:
                    self._refresh()

            Terminal().run(Browser())
        """),
        steps=(
            "Down@350ms 2",
            "Sleep 500ms",
            "Up@350ms 1",
            "Sleep 700ms",
        ),
        record_delay="500ms",
        content_rows=8,
        content_columns=52,
    ),
    Demo(
        name="custom_component",
        code=code("""
            import dataclasses
            import time
            from xnano import BaseGrid, Field, Terminal
            from xnano._types import Size
            from xnano.components.abstract import AbstractComponent
            from xnano.core.content import Panel, TextBlock

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

            class Header(BaseGrid, direction="horizontal", gap=1):
                title: str = Field(default="Deploy", height=1)
                badge: Badge = Field(
                    default_factory=lambda: Badge(
                        text="LIVE",
                        color="red",
                    ),
                    width="fit",
                    height=3,
                )

            Terminal(height=4).render(Header())
            time.sleep(3)
        """),
        launch_delay="800ms",
        steps=("Sleep 2s",),
        record_delay="500ms",
        auto_quit=False,
        content_rows=4,
        content_columns=36,
    ),
    Demo(
        name="scrollable_log",
        code=code("""
            from xnano import BaseGrid, Field, Terminal, Context
            from xnano.events import on_keyboard

            VIEW_HEIGHT = 6

            class LogView(BaseGrid, direction="vertical", gap=1):
                body: str = Field(
                    default="",
                    border="rounded",
                    title=" log ",
                )
                hint: str = Field(
                    default="j/k or ↓/↑ · scroll",
                    height=1,
                    color="slate-500",
                )
                buffer: list[str] = Field(
                    default_factory=list,
                    state=True,
                )
                scroll_offset: int = Field(default=0, state=True)

                def __post_init__(self) -> None:
                    self.buffer = [
                        f"line {i:03d}" for i in range(40)
                    ]
                    self.scroll_offset = max(
                        0,
                        len(self.buffer) - VIEW_HEIGHT,
                    )
                    self._paint()

                def _paint(self) -> None:
                    start = self.scroll_offset
                    self.body = "\\n".join(
                        self.buffer[start : start + VIEW_HEIGHT]
                    )

                @on_keyboard("up", "k")
                def scroll_up(self) -> None:
                    self.scroll_offset = max(
                        0,
                        self.scroll_offset - 1,
                    )
                    self._paint()

                @on_keyboard("down", "j")
                def scroll_down(self) -> None:
                    max_offset = max(
                        0,
                        len(self.buffer) - VIEW_HEIGHT,
                    )
                    self.scroll_offset = min(
                        max_offset,
                        self.scroll_offset + 1,
                    )
                    self._paint()

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(LogView())
        """),
        steps=(
            'Type "k"',
            "Sleep 200ms",
            'Type "k"',
            "Sleep 200ms",
            'Type "k"',
            "Sleep 400ms",
            'Type "j"',
            "Sleep 200ms",
            'Type "j"',
            "Sleep 600ms",
        ),
        record_delay="500ms",
        content_rows=9,
        content_columns=40,
    ),
    Demo(
        name="grid_render",
        code=code("""
            import time
            from xnano import BaseGrid, Field, Terminal
            from xnano.events import on_keyboard

            class Clock(BaseGrid, direction="vertical"):
                display: str = Field(
                    default="",
                    height=3,
                    border="rounded",
                    title=" time ",
                )

                def grid_render(self) -> None:
                    self.display = time.strftime("  %H:%M:%S")

                @on_keyboard("q")
                def quit(self, ctx) -> None:
                    ctx.terminal.request_exit()

            Terminal(tick_interval=200).run(Clock())
        """),
        steps=("Sleep 3s",),
        record_delay="500ms",
        content_rows=5,
        content_columns=28,
    ),
    Demo(
        name="action_bindings",
        code=code("""
            from xnano import (
                Action,
                BaseGrid,
                Context,
                Field,
                Terminal,
                on,
            )
            from xnano.events import on_keyboard

            SAVE = Action.keyboard("ctrl+s")
            QUIT = Action.keyboard("q")

            class Editor(BaseGrid, direction="vertical", gap=1):
                status: str = Field(default="unsaved", height=1)
                body: str = Field(
                    default="draft notes…",
                    height=3,
                    border="rounded",
                )
                dirty: bool = Field(default=True, state=True)

                @on(SAVE)
                def save(self) -> None:
                    self.dirty = False
                    self.status = "saved"

                @on(QUIT)
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

                @on_keyboard("e")
                def edit(self) -> None:
                    self.dirty = True
                    self.status = "unsaved"

            Terminal().run(Editor())
        """),
        steps=(
            "Sleep 500ms",
            'Type "e"',
            "Sleep 500ms",
            "Ctrl+S",
            "Sleep 800ms",
        ),
        record_delay="500ms",
        content_rows=6,
        content_columns=36,
    ),
    Demo(
        name="dual_host_terminal",
        code=code("""
            from xnano import BaseGrid, Field, Terminal
            from xnano.events import on_keyboard, on_tick

            class Counter(BaseGrid, direction="vertical", gap=1):
                label: str = Field(default="Count: 0", height=1)
                clock: str = Field(
                    default="uptime: 0s",
                    height=1,
                    color="slate-500",
                )
                hint: str = Field(
                    default="↑ to count · same grid on either host",
                    height=1,
                )
                count: int = Field(default=0, state=True)
                seconds: int = Field(default=0, state=True)

                @on_keyboard("up")
                def bump(self) -> None:
                    self.count += 1
                    self.label = f"Count: {self.count}"

                @on_tick(1000)
                def tick(self) -> None:
                    self.seconds += 1
                    self.clock = f"uptime: {self.seconds}s"

            Terminal().run(Counter())
        """),
        steps=(
            "Up@300ms 3",
            "Sleep 1.2s",
            "Up@300ms 2",
            "Sleep 1s",
        ),
        record_delay="500ms",
        content_rows=5,
        content_columns=48,
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
    """Record one tutorial demo for a single theme."""
    output = OUTPUT_DIRECTORY / f"{demo.name}-{theme}.gif"
    launch = (
        "uv run python scripts/generate_tutorial_demos.py "
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
        tape_label="tutorial",
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
        run_embedded_code(_DEMO_MAP[args.run_example], label="tutorial")
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
