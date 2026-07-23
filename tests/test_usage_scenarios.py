"""End-to-end usage scenarios — hooks + components working together.

These are not unit checks of single conditionals. Each test builds a small
app-like ``BaseGrid``, drives it through an offscreen ``Terminal``, and asserts
on rendered output and cross-feature behavior (focus → input → submit,
table/progress/chart in one layout, tick/poll/field chains, etc.).
"""

from __future__ import annotations

import asyncio
from typing import Any

from helpers import (
    FakeEvent,
    close_offscreen_app,
    open_offscreen_app,
    paint,
    press,
    type_text,
)

from xnano._dispatch import pump_poll, pump_tick
from xnano._function_hooks import _EventHooksRegistry
from xnano.components.chart import Chart
from xnano.components.progress import Progress
from xnano.components.schema import Column, Series
from xnano.components.table import Table
from xnano.components.text import Text
from xnano.events import (
    on_field,
    on_focus,
    on_keyboard,
    on_poll,
    on_tick,
)
from xnano.fields import Field
from xnano.grid import BaseGrid

# ---------------------------------------------------------------------------
# Scenario 1 — login form: focus + Text input + enter submit + re-render
# ---------------------------------------------------------------------------


class LoginForm(BaseGrid):
    """Two-field form with focus hooks and submit-on-enter."""

    heading: str = Field(default="Sign in", height=1)
    username: Text = Field(
        default_factory=lambda: Text("", input=True, placeholder="username"),
        height=1,
    )
    password: Text = Field(
        default_factory=lambda: Text("", input=True, placeholder="password"),
        height=1,
    )
    status: str = Field(default="ready", height=1)
    focus_log: list[str] = Field(default_factory=list, state=True)

    @on_focus("username")
    def _username_gained(self) -> None:
        self.focus_log.append("username+")
        self.status = "editing username"

    @on_focus("username", kind="lost")
    def _username_lost(self) -> None:
        self.focus_log.append("username-")

    @on_focus("password")
    def _password_gained(self) -> None:
        self.focus_log.append("password+")
        self.status = "editing password"

    @on_keyboard("enter")
    def _submit(self) -> None:
        self.status = f"ok:{self.username.value}/{self.password.value}"


def test_login_form_type_tab_submit_and_render() -> None:
    form = LoginForm()
    terminal = open_offscreen_app(form, cols=40, rows=8)
    try:
        # Auto-focus first input; placeholder path replaced by caret once focused.
        assert terminal.field_focus is not None
        assert terminal.field_focus.field_name == "username"
        assert form.username._input_focused is True
        assert "username+" in form.focus_log

        type_text(terminal, "ada")
        assert form.username.value == "ada"

        press(terminal, "tab")
        assert terminal.field_focus.field_name == "password"
        assert form.username._input_focused is False
        assert form.password._input_focused is True
        assert "username-" in form.focus_log
        assert "password+" in form.focus_log

        type_text(terminal, "s3cret")
        assert form.password.value == "s3cret"

        press(terminal, "enter")
        assert form.status == "ok:ada/s3cret"

        out = paint(terminal, form)
        assert "Sign in" in out
        assert "ada" in out
        # password field is focused → caret visible in buffer
        assert "s3cret" in out or "▌" in out
        assert "ok:ada/s3cret" in out
    finally:
        close_offscreen_app(terminal)


def test_login_form_backspace_and_cycle_wrap() -> None:
    form = LoginForm()
    terminal = open_offscreen_app(form)
    try:
        type_text(terminal, "ab")
        press(terminal, "backspace")
        assert form.username.value == "a"

        # tab → password → tab wraps to username
        press(terminal, "tab")
        press(terminal, "tab")
        assert terminal.field_focus.field_name == "username"

        press(terminal, "backtab")
        assert terminal.field_focus.field_name == "password"
    finally:
        close_offscreen_app(terminal)


def test_login_form_paste_into_focused_input() -> None:
    from typing import Any, cast

    from xnano._dispatch import dispatch_hooks
    from xnano.context import Context

    form = LoginForm()
    terminal = open_offscreen_app(form)
    try:
        type_text(terminal, "pre")
        event = FakeEvent(clipboard_text="-fix")
        ctx = Context(event=cast(Any, event), terminal=terminal, state=None)
        dispatch_hooks(terminal, ctx)
        assert form.username.value == "pre-fix"
    finally:
        close_offscreen_app(terminal)


# ---------------------------------------------------------------------------
# Scenario 2 — dashboard: Table + Progress + Chart + tick-driven updates
# ---------------------------------------------------------------------------


class ServicesTable(Table):
    service: str = Column()
    status: str = Column(
        color=lambda value: "green" if value == "ok" else "red"
    )
    latency: int = Column(align="right", format="{}ms", width=6)


class CpuChart(Chart):
    cpu = Series(color="cyan")
    mem = Series(color="magenta")


class Dashboard(BaseGrid):
    title: str = Field(default="ops", height=1)
    table: Table = Field(
        default_factory=lambda: ServicesTable(
            data=[
                {"service": "api", "status": "ok", "latency": 12},
                {"service": "cache", "status": "degraded", "latency": 88},
            ],
            selected=0,
            highlight_symbol="> ",
        ),
        height=5,
    )
    load: Progress = Field(
        default_factory=lambda: Progress(value=40, total=100, color="green"),
        height=3,
    )
    chart: Chart = Field(
        default_factory=lambda: CpuChart(
            series={"cpu": [10, 20, 30, 25], "mem": [50, 55, 52, 60]}
        ),
        height=6,
    )
    tick_count: int = Field(default=0, state=True)
    load_hits: int = Field(default=0, state=True)

    @on_tick
    def _pulse(self) -> None:
        self.tick_count += 1
        # Bump progress and table selection each tick.
        next_value = min(100, int(self.load.value) + 10)
        self.load = Progress(value=next_value, total=100, color="green")
        selected = 0 if self.table.selected else 1
        self.table = ServicesTable(
            data=list(self.table.data),
            selected=selected,
            highlight_symbol="> ",
        )

    @on_field("load.ratio >= 0.5")
    def _halfway(self) -> None:
        self.load_hits += 1


def test_dashboard_renders_components_together() -> None:
    app = Dashboard()
    terminal = open_offscreen_app(app, cols=56, rows=18)
    try:
        out = paint(terminal, app)
        assert "ops" in out
        assert "Service" in out or "api" in out
        assert "api" in out
        assert "cache" in out
        # progress auto-label
        assert "40%" in out
        # selection marker on first row
        assert "> " in out or "api" in out
    finally:
        close_offscreen_app(terminal)


def test_dashboard_tick_updates_progress_and_fires_on_field() -> None:
    app = Dashboard()
    terminal = open_offscreen_app(app, cols=56, rows=18)
    try:
        # Wire bound instance hooks the way Terminal.attach_grid/merge does.
        collected = _EventHooksRegistry.from_component_class(Dashboard)
        terminal._hooks.on_tick_hooks.clear()
        terminal._hooks.on_field_hooks.clear()
        for entry in collected.on_tick_hooks:
            name = getattr(entry["handler"], "__name__", None)
            handler = getattr(app, name) if name else entry["handler"]
            terminal._hooks.on_tick_hooks.append(
                {
                    "interval": entry["interval"],
                    "handler": handler,
                    "last_fire_ms": 0.0,
                }
            )
        for entry in collected.on_field_hooks:
            name = getattr(entry["handler"], "__name__", None)
            handler = getattr(app, name) if name else entry["handler"]
            terminal._hooks.on_field_hooks.append(
                {
                    "expression": entry["expression"],
                    "handler": handler,
                }
            )

        assert app.load.ratio == 0.4
        pump_tick(terminal)
        assert app.tick_count == 1
        assert app.load.ratio == 0.5
        # on_field("load.ratio >= 0.5") should now be true
        assert app.load_hits >= 1

        out = paint(terminal, app)
        assert "50%" in out
    finally:
        close_offscreen_app(terminal)


# ---------------------------------------------------------------------------
# Scenario 3 — chat prompt: free keys go to input; enter submits; slash cmd
# ---------------------------------------------------------------------------


class ChatApp(BaseGrid):
    log: Text = Field(
        default_factory=lambda: Text("welcome"),
        height=4,
    )
    prompt: Text = Field(
        default_factory=lambda: Text("", input=True, placeholder="message"),
        height=1,
    )
    history: list[str] = Field(default_factory=list, state=True)

    @on_keyboard("enter")
    def _send(self) -> None:
        message = self.prompt.value.strip()
        if not message:
            return
        self.history.append(message)
        if message.startswith("/clear"):
            self.history.clear()
            self.log = Text("cleared")
        else:
            self.log = Text("\n".join(self.history[-4:]))
        self.prompt = Text("", input=True, placeholder="message")
        # keep focus on the new prompt instance
        from xnano._types import set_field_focus
        from xnano.terminal import _ACTIVE_TERMINAL

        term = _ACTIVE_TERMINAL.get()
        if term is not None:
            set_field_focus(term, self, "prompt")


def test_chat_prompt_type_submit_command_flow() -> None:
    app = ChatApp()
    terminal = open_offscreen_app(app, cols=40, rows=10)
    try:
        type_text(terminal, "hello")
        press(terminal, "enter")
        assert app.history == ["hello"]
        out = paint(terminal, app)
        assert "hello" in out

        type_text(terminal, "/clear")
        press(terminal, "enter")
        assert app.history == []
        out = paint(terminal, app)
        assert "cleared" in out
        # prompt emptied and re-focused
        assert app.prompt.value == ""
        assert app.prompt._input_focused is True
    finally:
        close_offscreen_app(terminal)


# ---------------------------------------------------------------------------
# Scenario 4 — on_poll idle + on_tick + keyboard state machine
# ---------------------------------------------------------------------------


class WorkerApp(BaseGrid):
    label: str = Field(default="boot", height=1)
    idle_count: int = Field(default=0, state=True)
    frame_count: int = Field(default=0, state=True)
    ticks: int = Field(default=0, state=True)
    mode: str = Field(default="idle", state=True)

    @on_poll  # idle
    def _on_idle(self) -> None:
        self.idle_count += 1
        if self.mode == "idle":
            self.label = f"idle:{self.idle_count}"

    @on_poll("frame")
    def _on_frame(self) -> None:
        self.frame_count += 1

    @on_tick
    def _on_tick(self) -> None:
        self.ticks += 1

    @on_keyboard("r")
    def _run(self) -> None:
        self.mode = "run"
        self.label = "running"

    @on_field("mode == 'run'")
    def _when_running(self) -> None:
        self.label = f"run-ticks:{self.ticks}"


def _bind_all_hooks(terminal: Any, grid: Any, cls: type) -> None:
    collected = _EventHooksRegistry.from_component_class(cls)
    terminal._hooks = _EventHooksRegistry()
    for entry in collected.on_poll_hooks:
        name = getattr(entry["handler"], "__name__", None)
        handler = getattr(grid, name) if name else entry["handler"]
        terminal._hooks.on_poll_hooks.append(
            {"when": entry["when"], "handler": handler}
        )
    for entry in collected.on_tick_hooks:
        name = getattr(entry["handler"], "__name__", None)
        handler = getattr(grid, name) if name else entry["handler"]
        terminal._hooks.on_tick_hooks.append(
            {
                "interval": entry["interval"],
                "handler": handler,
                "last_fire_ms": 0.0,
            }
        )
    for entry in collected.on_field_hooks:
        name = getattr(entry["handler"], "__name__", None)
        handler = getattr(grid, name) if name else entry["handler"]
        terminal._hooks.on_field_hooks.append(
            {"expression": entry["expression"], "handler": handler}
        )
    for entry in collected.on_keyboard_hooks:
        name = getattr(entry["handler"], "__name__", None)
        handler = getattr(grid, name) if name else entry["handler"]
        terminal._hooks.on_keyboard_hooks.append(
            {
                "bindings": entry["bindings"],
                "kind": entry["kind"],
                "handler": handler,
            }
        )
    for entry in collected.on_focus_hooks:
        name = getattr(entry["handler"], "__name__", None)
        handler = getattr(grid, name) if name else entry["handler"]
        terminal._hooks.on_focus_hooks.append(
            {
                "field": entry["field"],
                "kind": entry["kind"],
                "handler": handler,
            }
        )


def test_worker_poll_tick_keyboard_field_chain() -> None:
    app = WorkerApp()
    terminal = open_offscreen_app(app, cols=30, rows=4)
    try:
        _bind_all_hooks(terminal, app, WorkerApp)
        terminal._attached_frame_grids = [app]

        # Idle poll path without touching the real Session method.
        pump_poll(terminal, "idle")
        assert app.idle_count == 1
        assert "idle:1" in app.label

        pump_poll(terminal, "frame")
        assert app.frame_count == 1

        pump_tick(terminal)
        assert app.ticks == 1

        # @on_keyboard("r") — named binding match
        press(terminal, "r")
        assert app.mode == "run"
        pump_tick(terminal)
        assert app.ticks == 2
        assert app.label == "run-ticks:2"

        out = paint(terminal, app)
        assert "run-ticks:2" in out
    finally:
        close_offscreen_app(terminal)


# ---------------------------------------------------------------------------
# Scenario 5 — async tick mutates Progress, then field hook reacts
# ---------------------------------------------------------------------------


class AsyncMeter(BaseGrid):
    meter: Progress = Field(
        default_factory=lambda: Progress(value=0, total=10),
        height=3,
    )
    note: str = Field(default="", height=1)
    async_fires: int = Field(default=0, state=True)

    @on_tick
    async def _async_bump(self) -> None:
        await asyncio.sleep(0)
        self.async_fires += 1
        self.meter = Progress(
            value=min(10, self.async_fires), total=10, color="cyan"
        )

    @on_field("meter.ratio >= 0.3")
    def _note(self) -> None:
        self.note = f"ratio={self.meter.ratio:.1f}"


def test_async_tick_with_progress_and_on_field() -> None:
    app = AsyncMeter()
    terminal = open_offscreen_app(app, cols=32, rows=6)
    try:
        _bind_all_hooks(terminal, app, AsyncMeter)
        terminal._attached_frame_grids = [app]

        pump_tick(terminal)
        pump_tick(terminal)
        pump_tick(terminal)
        assert app.async_fires == 3
        assert app.meter.ratio == 0.3
        assert app.note == "ratio=0.3"

        out = paint(terminal, app)
        assert "30%" in out
        assert "ratio=0.3" in out
    finally:
        close_offscreen_app(terminal)


# ---------------------------------------------------------------------------
# Scenario 6 — multi-grid: independent focus + shared terminal hooks
# ---------------------------------------------------------------------------


class Panel(BaseGrid):
    name: str = Field(default="panel", height=1, state=True)
    field: Text = Field(
        default_factory=lambda: Text("", input=True, placeholder="…"),
        height=1,
    )


class Dual(BaseGrid):
    left: Panel = Field(default_factory=lambda: Panel(name="left"))
    right: Panel = Field(default_factory=lambda: Panel(name="right"))


def test_nested_panels_render_and_focus_left_input() -> None:
    root = Dual()
    root.left.name = "left"
    root.right.name = "right"
    terminal = open_offscreen_app(root, cols=40, rows=6)
    try:
        out = paint(terminal, root)
        assert isinstance(out, str)
        # Nested panels re-register during paint.
        names = {
            type(grid).__name__ for grid in terminal._attached_frame_grids
        }
        assert "Dual" in names
        assert "Panel" in names
        assert len(terminal._attached_frame_grids) >= 3  # root + 2 panels

        # Explicitly focus left panel input and type.
        from xnano._types import set_field_focus

        assert set_field_focus(terminal, root.left, "field") is True
        type_text(terminal, "xy")
        assert root.left.field.value == "xy"
        out2 = paint(terminal, root)
        assert "xy" in out2
    finally:
        close_offscreen_app(terminal)


# ---------------------------------------------------------------------------
# Scenario 7 — Table selection + keyboard moves selection + Progress mirrors
# ---------------------------------------------------------------------------


class Picker(BaseGrid):
    # Note: cannot name a layout field ``rows`` — BaseGrid owns ``rows``/``columns``.
    items: Table = Field(
        default_factory=lambda: Table(
            data=[
                {"item": "alpha", "n": 1},
                {"item": "beta", "n": 2},
                {"item": "gamma", "n": 3},
            ],
            columns=["item", "n"],
            selected=0,
            highlight_symbol="* ",
        ),
        height=6,
    )
    bar: Progress = Field(
        default_factory=lambda: Progress(value=1, total=3),
        height=3,
    )

    @on_keyboard("down")
    def _down(self) -> None:
        index = (self.items.selected or 0) + 1
        index = min(index, len(self.items.data) - 1)
        self.items = Table(
            data=self.items.data,
            columns=["item", "n"],
            selected=index,
            highlight_symbol="* ",
        )
        self.bar = Progress(value=index + 1, total=3)

    @on_keyboard("up")
    def _up(self) -> None:
        index = max(0, (self.items.selected or 0) - 1)
        self.items = Table(
            data=self.items.data,
            columns=["item", "n"],
            selected=index,
            highlight_symbol="* ",
        )
        self.bar = Progress(value=index + 1, total=3)


def test_picker_keyboard_moves_selection_and_progress() -> None:
    app = Picker()
    terminal = open_offscreen_app(app, cols=36, rows=12)
    try:
        _bind_all_hooks(terminal, app, Picker)
        out = paint(terminal, app)
        assert "alpha" in out
        assert "33%" in out  # progress 1/3

        press(terminal, "down")
        assert app.items.selected == 1
        assert abs(app.bar.ratio - (2 / 3)) < 1e-9
        out = paint(terminal, app)
        assert "beta" in out
        assert "67%" in out

        press(terminal, "down")
        assert app.items.selected == 2
        assert app.bar.ratio == 1.0
        out = paint(terminal, app)
        assert "100%" in out
        assert "gamma" in out
    finally:
        close_offscreen_app(terminal)


# ---------------------------------------------------------------------------
# Scenario 8 — exception in hook still leaves terminal usable (restore path)
# ---------------------------------------------------------------------------


class BoomApp(BaseGrid):
    label: str = Field(default="safe", height=1)

    @on_keyboard("x")
    def _boom(self) -> None:
        raise ValueError("kaboom")


def test_hook_exception_logs_and_terminal_still_paints(
    caplog: Any,
) -> None:
    import logging

    app = BoomApp()
    terminal = open_offscreen_app(app, cols=20, rows=3)
    try:
        _bind_all_hooks(terminal, app, BoomApp)
        with caplog.at_level(logging.ERROR, logger="xnano.hooks"):
            try:
                press(terminal, "x")
            except ValueError as exc:
                assert "kaboom" in str(exc)
            else:
                raise AssertionError("expected ValueError")
        assert any("Uncaught exception" in r.message for r in caplog.records)
        # Terminal session still paints after the failure.
        app.label = "recovered"
        out = paint(terminal, app)
        assert "recovered" in out
    finally:
        close_offscreen_app(terminal)


# ---------------------------------------------------------------------------
# Scenario — two instances of one grid class each receive their own hooks
# ---------------------------------------------------------------------------


class _Tally(BaseGrid):
    label: str = Field(default="", height=1)
    count: int = Field(default=0, state=True)

    @on_keyboard("k")
    def bump(self) -> None:
        self.count += 1


def test_same_grid_class_instances_each_receive_hooks() -> None:
    # Hook registration is per instance — a per-class guard would leave
    # every instance after the first without hooks (or firing on the
    # wrong ``self``).
    first = _Tally()
    second = _Tally()
    terminal = open_offscreen_app(first)
    try:
        terminal.attach_grid(second)
        press(terminal, "k")
        assert first.count == 1
        assert second.count == 1

        # Re-attaching an already-known instance must not double-register.
        terminal.attach_grid(first)
        press(terminal, "k")
        assert first.count == 2
        assert second.count == 2
    finally:
        close_offscreen_app(terminal)
