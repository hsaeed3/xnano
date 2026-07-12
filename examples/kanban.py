"""xnano example — kanban.py

Project board with live velocity chart and sprint health metrics.
  · Tab-navigable columns (Backlog / Focus / Shipped)
  · TaskList with priority badges (TableNode)
  · Recent activity feed (bottom of board column)
  · Velocity filled-area chart (28-day history)
  · Priority distribution bar chart
  · Sprint health gauges (LineGaugeNode)
"""

from __future__ import annotations

import dataclasses
import random
import time
from typing import Literal, cast

from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.tui import Terminal
from xnano.events import on_keyboard, on_tick
from xnano.components.text import Text
from xnano.components.abstract import (
    AbstractComponent,
    ComponentRenderContext,
)
from xnano.color import ColorLike, tailwind_color


# ── Palette ───────────────────────────────────────────────────────────────────

Priority = Literal["high", "mid", "low"]

_PRIORITY_FG = {
    "high": tailwind_color("rose", 400),
    "mid": tailwind_color("amber", 400),
    "low": tailwind_color("teal", 400),
}
_PRIORITY_SYMBOLS = {"high": "●", "mid": "◆", "low": "▲"}
_PRIORITY_CYCLE: dict[str, Priority] = {
    "low": "mid",
    "mid": "high",
    "high": "low",
}

_COL_NAMES = ["Backlog", "Focus", "Shipped"]
_COL_ACCENTS = [
    tailwind_color("slate", 500),
    tailwind_color("violet", 500),
    tailwind_color("emerald", 500),
]
_COL_HL_BG = [
    tailwind_color("slate", 700),
    tailwind_color("violet", 700),
    tailwind_color("emerald", 700),
]
_COL_BORDER = [
    tailwind_color("slate", 600),
    tailwind_color("violet", 700),
    tailwind_color("emerald", 700),
]

_CHART_DAYS = 28


def _color_hex(c) -> str:
    return f"#{c.r:02x}{c.g:02x}{c.b:02x}"


def _smooth(data: list[float], alpha: float = 0.2) -> list[float]:
    if len(data) < 2:
        return data
    fwd = [data[0]]
    for v in data[1:]:
        fwd.append(alpha * v + (1 - alpha) * fwd[-1])
    bwd = [fwd[-1]]
    for v in reversed(fwd[:-1]):
        bwd.append(alpha * v + (1 - alpha) * bwd[-1])
    return list(reversed(bwd))


# ── Data model ────────────────────────────────────────────────────────────────


@dataclasses.dataclass
class Task:
    title: str
    priority: Priority
    tag: str
    tid: int


_counter = 0


def _next_id() -> int:
    global _counter
    _counter += 1
    return _counter


def _t(title: str, priority: Priority, tag: str) -> Task:
    return Task(title=title, priority=priority, tag=tag, tid=_next_id())


_TITLE_POOL = [
    "Add dark mode support",
    "Write API documentation",
    "Set up CI pipeline",
    "Refactor auth module",
    "Benchmark render loop",
    "Fix memory leak",
    "Audit dependency versions",
    "Add rate limiting",
    "Update OpenAPI spec",
    "Profile startup time",
    "Cache query results",
    "Add integration tests",
    "Improve error messages",
    "Extract config service",
    "Harden input validation",
    "Add webhook support",
    "Migrate database schema",
    "Write runbook",
]
_TAGS = ["ui", "backend", "infra", "docs", "perf", "ux", "api", "tests"]

_SEED: tuple[list[Task], list[Task], list[Task]] = (
    [
        _t("Add dark mode support", "mid", "ui"),
        _t("Write API documentation", "low", "docs"),
        _t("Set up CI pipeline", "high", "infra"),
        _t("Refactor auth module", "mid", "backend"),
        _t("Benchmark render loop", "low", "perf"),
        _t("Fix memory leak", "high", "backend"),
        _t("Audit dependency versions", "low", "infra"),
    ],
    [
        _t("Migrate to Rust parser", "high", "backend"),
        _t("Design onboarding flow", "mid", "ui"),
        _t("Improve error messages", "low", "ux"),
    ],
    [
        _t("Initial project setup", "low", "infra"),
        _t("Prototype terminal renderer", "high", "backend"),
        _t("Draft feature spec", "low", "docs"),
        _t("Basic auth flow", "mid", "backend"),
        _t("Core API scaffolding", "high", "api"),
    ],
)


def _seed_velocity() -> list[int]:
    series = [random.randint(0, 3)]
    for _ in range(_CHART_DAYS - 1):
        series.append(max(0, series[-1] + random.randint(-1, 2)))
    return series


# ── Custom components ─────────────────────────────────────────────────────────


@dataclasses.dataclass
class BoardTabs(AbstractComponent):
    active: int = 0
    counts: list = dataclasses.field(default_factory=lambda: [0, 0, 0])
    fit_content: bool = dataclasses.field(default=False, kw_only=True)

    def get_terminal_node(self, ctx: ComponentRenderContext):  # type: ignore[override]
        from xnano.tui.nodes import LineNode, SpanNode, TabsNode

        titles: list[str | LineNode | SpanNode] = [
            SpanNode(
                content=f"{name}  ({self.counts[i]})",
                color=_COL_ACCENTS[i],
                modifiers=["bold"] if i == self.active else [],
            )
            for i, name in enumerate(_COL_NAMES)
        ]
        return TabsNode(
            titles=titles,
            selected=self.active,
            highlight_color=_COL_ACCENTS[self.active],
            highlight_background=_COL_HL_BG[self.active],
            color=tailwind_color("slate", 600),
            divider="  │  ",
            padding_left="  ",
            padding_right="  ",
        )


@dataclasses.dataclass
class TaskList(AbstractComponent):
    tasks: list = dataclasses.field(default_factory=list)
    selected: int = 0
    accent_bg: ColorLike | None = dataclasses.field(default=None)
    fit_content: bool = dataclasses.field(default=False, kw_only=True)

    def get_terminal_node(self, ctx: ComponentRenderContext):  # type: ignore[override]
        from xnano.tui.nodes import (
            SpanNode,
            TableCellItem,
            TableNode,
            TableRowItem,
        )

        dim = tailwind_color("slate", 500)
        header = TableRowItem(
            cells=[
                TableCellItem(content=" Pri  ", color=dim),
                TableCellItem(content="Task", color=dim),
                TableCellItem(content="Tag   ", color=dim),
            ],
            height=1,
        )

        rows = []
        for task in self.tasks:
            pc = _PRIORITY_FG[task.priority]
            sym = _PRIORITY_SYMBOLS[task.priority]
            rows.append(
                TableRowItem(
                    cells=[
                        TableCellItem(
                            content=SpanNode(
                                content=f" {sym} {task.priority[:3]} ",
                                color=pc,
                                modifiers=["bold"],
                            )
                        ),
                        TableCellItem(
                            content=f"  {task.title}",
                            color=tailwind_color("slate", 700),
                        ),
                        TableCellItem(
                            content=SpanNode(
                                content=f" #{task.tag}",
                                color=tailwind_color("slate", 500),
                            )
                        ),
                    ],
                    height=1,
                )
            )

        return TableNode(
            rows=rows,
            header=header,
            column_widths=[0.20, 0.62, 0.18],
            column_spacing=0,
            selected_row=self.selected if self.tasks else None,
            highlight_background=self.accent_bg
            or tailwind_color("violet", 700),
            highlight_color="white",
            highlight_symbol="▶ ",
        )


@dataclasses.dataclass
class ActivityFeed(AbstractComponent):
    """Recent board actions as a scrolling log."""

    events: list = dataclasses.field(default_factory=list)
    fit_content: bool = dataclasses.field(default=False, kw_only=True)

    def get_terminal_node(self, ctx: ComponentRenderContext):  # type: ignore[override]
        from xnano.tui.nodes import (
            SpanNode,
            TableCellItem,
            TableNode,
            TableRowItem,
        )

        rows = []
        for ts, icon, action, col_idx in self.events:
            rows.append(
                TableRowItem(
                    cells=[
                        TableCellItem(
                            content=f" {ts} ",
                            color=tailwind_color("slate", 600),
                        ),
                        TableCellItem(
                            content=SpanNode(
                                content=f" {icon} ",
                                color=_COL_ACCENTS[col_idx],
                                modifiers=["bold"],
                            )
                        ),
                        TableCellItem(
                            content=f" {action}",
                            color=tailwind_color("slate", 700),
                        ),
                    ],
                    height=1,
                )
            )

        return TableNode(
            rows=rows,
            column_widths=[0.22, 0.08, 0.70],
            column_spacing=0,
        )


@dataclasses.dataclass
class VelocityChart(AbstractComponent):
    data: list = dataclasses.field(default_factory=list)
    accent: ColorLike | None = dataclasses.field(default=None)
    fit_content: bool = dataclasses.field(default=False, kw_only=True)

    def get_terminal_node(self, ctx: ComponentRenderContext):  # type: ignore[override]
        from xnano.tui.nodes import (
            CanvasLine,
            CanvasNode,
            CanvasPrint,
            SpanNode,
        )

        data = self.data or [0]
        n = len(data)
        max_v = max(max(data), 1)
        area_c = _color_hex(tailwind_color("violet", 700))
        avg_c = _color_hex(tailwind_color("violet", 400))
        axis_c = tailwind_color("slate", 600)
        shapes = []

        for i, v in enumerate(data):
            if v > 0:
                shapes.append(
                    CanvasLine(
                        x1=float(i),
                        y1=0.0,
                        x2=float(i),
                        y2=float(v),
                        color=area_c,
                    )
                )

        smoothed = _smooth([float(v) for v in data])
        for i in range(1, len(smoothed)):
            shapes.append(
                CanvasLine(
                    x1=float(i - 1),
                    y1=smoothed[i - 1],
                    x2=float(i),
                    y2=smoothed[i],
                    color=avg_c,
                )
            )

        for frac in (0.5, 1.0):
            val = max_v * frac
            shapes.append(
                CanvasPrint(
                    x=0.3,
                    y=val,
                    content=SpanNode(content=f"{val:.0f}", color=axis_c),
                )
            )

        shapes.append(
            CanvasLine(
                x1=float(n - 1),
                y1=0.0,
                x2=float(n - 1),
                y2=float(max_v),
                color=_color_hex(tailwind_color("emerald", 600)),
            )
        )

        return CanvasNode(
            shapes=shapes,
            x_bounds=(0.0, float(n - 1)),
            y_bounds=(0.0, float(max_v) * 1.1),
            marker="half_block",
        )


@dataclasses.dataclass
class PriorityBreakdown(AbstractComponent):
    all_tasks: list = dataclasses.field(default_factory=list)
    fit_content: bool = dataclasses.field(default=False, kw_only=True)

    def get_terminal_node(self, ctx: ComponentRenderContext):  # type: ignore[override]
        from xnano.tui.nodes import (
            BarChartNode,
            BarGroupItem,
            BarItem,
        )

        counts: dict[str, int] = {"high": 0, "mid": 0, "low": 0}
        for task in self.all_tasks:
            counts[task.priority] += 1

        max_v = max(max(counts.values(), default=0), 1)
        groups = [
            BarGroupItem(
                bars=[
                    BarItem(
                        value=counts[p], label=p[:3], color=_PRIORITY_FG[p]
                    )
                ]
            )
            for p in ("high", "mid", "low")
        ]
        return BarChartNode(
            groups=groups,
            bar_width=5,
            bar_gap=0,
            group_gap=3,
            max_value=max_v,
            direction="vertical",
            label_color=tailwind_color("slate", 600),
        )


@dataclasses.dataclass
class SprintGauge(AbstractComponent):
    """Single-metric LineGaugeNode for sprint health panel."""

    label: str = ""
    progress: float = 0.0
    filled: ColorLike | None = dataclasses.field(default=None)
    fit_content: bool = dataclasses.field(default=False, kw_only=True)

    def get_terminal_node(self, ctx: ComponentRenderContext):  # type: ignore[override]
        from xnano.tui.nodes import LineGaugeNode

        return LineGaugeNode(
            progress=self.progress,
            label=self.label,
            filled_color=self.filled or tailwind_color("violet", 500),
            unfilled_color=tailwind_color("slate", 600),
            color=tailwind_color("slate", 700),
        )


# ── Layout ────────────────────────────────────────────────────────────────────


class SprintStats(BaseGrid, direction="vertical", gap=0):
    completion: SprintGauge = Field(
        default_factory=SprintGauge,
        height=3,
        border="plain",
        border_color=tailwind_color("slate", 800),
    )
    in_focus: SprintGauge = Field(
        default_factory=SprintGauge,
        height=3,
        border="plain",
        border_color=tailwind_color("slate", 800),
    )
    high_pri: SprintGauge = Field(
        default_factory=SprintGauge,
        height=3,
        border="plain",
        border_color=tailwind_color("slate", 800),
    )


class LeftPane(BaseGrid, direction="vertical", gap=1):
    col_tabs: BoardTabs = Field(
        default_factory=BoardTabs,
        height=3,
        border="rounded",
        border_color=tailwind_color("violet", 800),
    )
    cards: TaskList = Field(
        default_factory=TaskList,
        border="rounded",
        border_color=tailwind_color("slate", 700),
    )
    activity: ActivityFeed = Field(
        default_factory=ActivityFeed,
        height=9,
        border="rounded",
        border_color=tailwind_color("slate", 700),
        title=" Recent Activity ",
    )


class RightPane(BaseGrid, direction="vertical", gap=1):
    velocity: VelocityChart = Field(
        default_factory=VelocityChart,
        border="rounded",
        border_color=tailwind_color("violet", 800),
        title=" Velocity  (28 days) ",
    )
    breakdown: PriorityBreakdown = Field(
        default_factory=PriorityBreakdown,
        height=10,
        border="rounded",
        border_color=tailwind_color("slate", 700),
        title=" Priority Distribution ",
    )
    sprint: SprintStats = Field(
        default_factory=SprintStats,
        height=9,
        border="rounded",
        border_color=tailwind_color("slate", 700),
        title=" Sprint Health ",
    )


class MainArea(BaseGrid, direction="horizontal", gap=1):
    left: LeftPane = Field(default_factory=LeftPane, width="45%")
    right: RightPane = Field(default_factory=RightPane)


class KanbanApp(BaseGrid, direction="vertical"):
    header: str = Field(
        default="  BOARD",
        height=1,
        color=tailwind_color("violet", 500),
        modifiers=["bold"],
    )
    main: MainArea = Field(default_factory=MainArea)
    footer: str = Field(
        default="",
        height=1,
        color=tailwind_color("slate", 600),
    )

    task_data: list = Field(
        default_factory=lambda: [list(col) for col in _SEED], state=True
    )
    active_col: int = Field(default=0, state=True)
    col_sel: list = Field(default_factory=lambda: [0, 0, 0], state=True)
    velocity: list = Field(default_factory=_seed_velocity, state=True)
    last_action: str = Field(default="", state=True)
    ts: str = Field(default_factory=lambda: time.strftime("%H:%M"), state=True)
    activity: list = Field(default_factory=list, state=True)

    def _log(self, icon: str, action: str, col_idx: int) -> None:
        ev = (time.strftime("%H:%M:%S"), icon, action, col_idx)
        self.activity = (self.activity + [ev])[-8:]

    @on_keyboard("left")
    def _col_left(self) -> None:
        self.active_col = (self.active_col - 1) % 3

    @on_keyboard("right")
    def _col_right(self) -> None:
        self.active_col = (self.active_col + 1) % 3

    @on_keyboard("up")
    def _row_up(self) -> None:
        sel = list(self.col_sel)
        c = self.active_col
        if self.task_data[c]:
            sel[c] = max(0, sel[c] - 1)
        self.col_sel = sel

    @on_keyboard("down")
    def _row_down(self) -> None:
        sel = list(self.col_sel)
        c = self.active_col
        n = len(self.task_data[c])
        if n:
            sel[c] = min(n - 1, sel[c] + 1)
        self.col_sel = sel

    @on_keyboard("shift+right")
    def _move_right(self) -> None:
        c = self.active_col
        if c >= 2:
            return
        data = [list(col) for col in self.task_data]
        sel = list(self.col_sel)
        if not data[c]:
            return
        task = data[c].pop(sel[c])
        data[c + 1].append(task)
        sel[c] = max(0, min(sel[c], len(data[c]) - 1)) if data[c] else 0
        sel[c + 1] = len(data[c + 1]) - 1
        self.task_data = data
        self.col_sel = sel
        self.active_col = c + 1
        self.last_action = f"→ {_COL_NAMES[c + 1]}"
        self._log("→", f"{task.title[:28]} → {_COL_NAMES[c + 1]}", c + 1)
        if c + 1 == 2:
            vel = list(self.velocity)
            vel[-1] += 1
            self.velocity = vel

    @on_keyboard("shift+left")
    def _move_left(self) -> None:
        c = self.active_col
        if c <= 0:
            return
        data = [list(col) for col in self.task_data]
        sel = list(self.col_sel)
        if not data[c]:
            return
        task = data[c].pop(sel[c])
        data[c - 1].append(task)
        sel[c] = max(0, min(sel[c], len(data[c]) - 1)) if data[c] else 0
        sel[c - 1] = len(data[c - 1]) - 1
        self.task_data = data
        self.col_sel = sel
        self.active_col = c - 1
        self.last_action = f"← {_COL_NAMES[c - 1]}"
        self._log("←", f"{task.title[:28]} → {_COL_NAMES[c - 1]}", c - 1)

    @on_keyboard("n")
    def _new_task(self) -> None:
        data = [list(col) for col in self.task_data]
        task = Task(
            title=random.choice(_TITLE_POOL),
            priority=cast(
                Priority,
                random.choices(["high", "mid", "low"], weights=[2, 5, 3])[0],
            ),
            tag=random.choice(_TAGS),
            tid=_next_id(),
        )
        data[self.active_col].append(task)
        sel = list(self.col_sel)
        sel[self.active_col] = len(data[self.active_col]) - 1
        self.task_data = data
        self.col_sel = sel
        self.last_action = f"+ {task.title[:22]}"
        self._log("+", f"Added: {task.title[:30]}", self.active_col)

    @on_keyboard("x")
    def _delete(self) -> None:
        c = self.active_col
        data = [list(col) for col in self.task_data]
        sel = list(self.col_sel)
        if not data[c]:
            return
        task = data[c].pop(sel[c])
        sel[c] = max(0, min(sel[c], len(data[c]) - 1)) if data[c] else 0
        self.task_data = data
        self.col_sel = sel
        self.last_action = f"✖ {task.title[:22]}"
        self._log("✖", f"Removed: {task.title[:28]}", c)

    @on_keyboard("p")
    def _cycle_priority(self) -> None:
        c = self.active_col
        data = [list(col) for col in self.task_data]
        if not data[c]:
            return
        idx = self.col_sel[c]
        old = data[c][idx]
        new_p: Priority = _PRIORITY_CYCLE[old.priority]
        data[c][idx] = Task(
            title=old.title, priority=new_p, tag=old.tag, tid=old.tid
        )
        self.task_data = data
        self.last_action = f"priority → {new_p}"
        self._log("◆", f"{old.title[:24]} → {new_p}", c)

    @on_keyboard("q")
    def _quit(self, ctx) -> None:
        ctx.terminal.request_exit()

    @on_tick(3000)
    def _tick(self) -> None:
        self.ts = time.strftime("%H:%M")
        vel = list(self.velocity)
        vel[-1] = max(0, vel[-1] + random.randint(-1, 1))
        self.velocity = vel

    def grid_render(self) -> None:
        c = self.active_col
        sel = self.col_sel
        data = self.task_data

        counts = [len(data[i]) for i in range(3)]
        total = sum(counts)
        all_tasks = [t for col in data for t in col]
        high_open = sum(1 for t in data[0] + data[1] if t.priority == "high")

        # Left pane
        self.main.left.col_tabs = BoardTabs(active=c, counts=counts)
        self.main.left.cards = TaskList(
            tasks=data[c], selected=sel[c], accent_bg=_COL_HL_BG[c]
        )
        self.main.left.activity = ActivityFeed(events=list(self.activity))

        # Right pane — charts
        self.main.right.velocity = VelocityChart(data=self.velocity)
        self.main.right.breakdown = PriorityBreakdown(all_tasks=all_tasks)

        # Sprint health gauges
        shipped_pct = counts[2] / max(total, 1)
        focus_pct = counts[1] / max(total, 1)
        danger_pct = min(1.0, high_open / 10.0)
        sp = self.main.right.sprint
        sp.completion = SprintGauge(
            label=f"  Shipped    {counts[2]}/{total}",
            progress=shipped_pct,
            filled=tailwind_color("emerald", 500),
        )
        sp.in_focus = SprintGauge(
            label=f"  In Focus   {counts[1]} tasks",
            progress=focus_pct,
            filled=tailwind_color("violet", 500),
        )
        sp.high_pri = SprintGauge(
            label=f"  High Pri   {high_open} open",
            progress=danger_pct,
            filled=tailwind_color("rose", 500)
            if high_open > 3
            else tailwind_color("amber", 400),
        )

        # Header & footer
        self.header = (
            f"  BOARD  ·  {total} tasks  ·  {counts[2]} shipped  ·  {self.ts}"
        )
        action = f"  ·  {self.last_action}" if self.last_action else ""
        self.footer = (
            f"  [↑↓] Select  [←→] Column  [⇧←→] Move  "
            f"[n] New  [x] Delete  [p] Priority  [q] Quit{action}"
        )


if __name__ == "__main__":
    Terminal(tick_interval=3000).run(KanbanApp())
