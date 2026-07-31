"""tests.test_user_compositions

---

Exercise realistic applications built by composing xnano objects instead of
testing each object in isolation.
"""

from __future__ import annotations

import http.client
import io
import json
import threading
import types
from typing import Annotated

import pytest

from xnano.actions import Action
from xnano.cli.command import Command
from xnano.cli.help import format_plain_help, print_error, render_help
from xnano.cli.parameters import Argument, Option
from xnano.components.bar import Bar
from xnano.components.button import Button
from xnano.components.chart import Chart
from xnano.components.dropdown import Dropdown
from xnano.components.input import Input
from xnano.components.link import Link
from xnano.components.loader import Loader
from xnano.components.options import Options
from xnano.components.table import Table
from xnano.components.text import Text
from xnano.core.effects import resolve_native_effect
from xnano.core.frame import Frame, frame_from_terminal
from xnano.core.runtime import Runtime
from xnano.effects import AbstractEffect, Effect
from xnano.fields import Field
from xnano.grids import BaseGrid
from xnano.hooks import on_click, on_keyboard
from xnano.requests import Response, on_get_request, on_post_request
from xnano.server.native import NativeWebServer
from xnano.terminal import Terminal
from xnano.web import Web, grid_factory


def test_operator_dashboard_composes_data_display_and_controls() -> None:
    """A dashboard can mix status, trends, records, controls, and hooks."""

    class Dashboard(BaseGrid, direction="vertical", gap=1):
        heading: Text = Field(
            default_factory=lambda: Text(
                [
                    Text("API ", modifiers=("bold",)),
                    Text("healthy", foreground="green-400"),
                ]
            ),
            height=1,
        )
        trend: Chart = Field(
            default_factory=lambda: Chart(
                series={"requests": [2, 5, 4, 8]},
                kind="line",
            ),
            height=4,
        )
        capacity: Bar = Field(
            default_factory=lambda: Bar(
                data=[2, 5, 3, 7],
                max_value=10,
                foreground="cyan-400",
            ),
            height=2,
        )
        progress: Loader = Field(
            default_factory=lambda: Loader(
                value=0.75,
                style="bar",
                label="deploy",
            ),
            height=1,
        )
        services: Table = Field(
            default_factory=lambda: Table(
                data=[
                    {"name": "api", "status": "ok"},
                    {"name": "worker", "status": "busy"},
                ],
                focusable=True,
            ),
            group="services",
            height=5,
        )
        filter: Input = Field(
            default_factory=lambda: Input(placeholder="filter services"),
            group="filter",
            height=1,
        )
        refresh: Button = Field(
            default_factory=lambda: Button(label="Refresh"),
            group="refresh",
            height=1,
        )
        docs: Link = Field(
            default_factory=lambda: Link(
                "Runbook",
                url="https://example.com/runbook",
            ),
            group="docs",
            height=1,
        )
        message: str = Field(default="idle", height=1)

        @on_click("refresh")
        def refresh_data(self) -> None:
            self.message = "refreshed"

    runtime = Runtime.offscreen(60, 20)
    try:
        dashboard = Dashboard()
        runtime.set_root(dashboard)
        frame = runtime.render()
        for expected in ("healthy", "api", "deploy", "Runbook"):
            assert expected in frame.text

        assert runtime.focus("services")
        runtime.perform(Action.keyboard("down"))
        assert dashboard.services.value is not None
        assert dashboard.services.value["name"] == "worker"

        assert runtime.focus("filter")
        runtime.perform(Action.keyboard("a"))
        runtime.perform(Action.keyboard("p"))
        runtime.perform(Action.keyboard("i"))
        assert dashboard.filter.value == "api"

        runtime.perform(Action.click("refresh"))
        assert "refreshed" in runtime.render().text
    finally:
        runtime.close()


def test_settings_form_composes_dropdown_options_and_editable_text() -> None:
    """A settings form can move focus while preserving each editor's state."""

    class Settings(BaseGrid, direction="vertical"):
        environment: Dropdown = Field(
            default_factory=lambda: Dropdown(
                items=("development", "production"),
                placeholder="environment",
            ),
            group="environment",
            height=2,
        )
        features: Options = Field(
            default_factory=lambda: Options(
                items=("logging", "metrics", "tracing"),
                accept="extend",
                searchable=True,
            ),
            group="features",
            height=5,
        )
        notes: Input = Field(
            default_factory=lambda: Input(placeholder="release notes"),
            group="notes",
            height=4,
        )

    runtime = Runtime.offscreen(50, 14)
    try:
        settings = Settings()
        runtime.set_root(settings)
        runtime.render()

        assert runtime.focus("environment")
        runtime.perform(Action.keyboard("down"))
        runtime.perform(Action.keyboard("down"))
        runtime.perform(Action.keyboard("enter"))
        assert settings.environment.value == "production"

        assert runtime.focus("features")
        runtime.perform(Action.keyboard("m"))
        runtime.perform(Action.keyboard("e"))
        runtime.perform(Action.keyboard("enter"))
        assert settings.features.value

        assert runtime.focus("notes")
        for binding in ("r", "e", "a", "d", "y", " ", "n", "o", "w"):
            runtime.perform(Action.keyboard(binding))
        assert "ready" in settings.notes.value
        assert "now" in runtime.render().text
    finally:
        runtime.close()


def test_animation_choreography_composes_every_effect_kind() -> None:
    """An application can build and lower a complete transition palette."""
    leaf = Effect(
        "fade",
        color="violet-400",
        interpolation="sine_in_out",
        key="status",
    )
    kinds = (
        "fade",
        "fade_from",
        "fade_to",
        "fade_from_both",
        "dissolve",
        "coalesce",
        "sweep_in",
        "sweep_out",
        "slide_in",
        "slide_out",
        "paint",
        "paint_fg",
        "paint_bg",
        "sleep",
    )
    palette: list[AbstractEffect] = [
        Effect(
            kind,
            color="cyan-300",
            background="slate-900",
            direction="right_to_left",
            gradient_length=8,
            randomness=1,
            interpolation="linear",
            key=kind,
        )
        for kind in kinds
    ]
    palette.extend(
        (
            Effect("sequence", effects=palette[:2]),
            Effect("parallel", effects=palette[2:4]),
            Effect("repeat", child=leaf, times=2),
            Effect("repeat", child=leaf, duration_ms=450),
            Effect("repeat", child=leaf),
            Effect("delay", child=leaf, duration_ms=50),
        )
    )

    for effect in palette:
        assert resolve_native_effect(effect) is not None
    assert Effect(leaf) is leaf


def test_cli_workflow_composes_typed_arguments_options_and_subcommands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A deployment CLI supports typed repeats, flags, help, and errors."""
    command = Command(
        name="deploy",
        description="Deploy an application.",
        strict=True,
    )
    calls: list[tuple[str, int, list[str], bool]] = []

    @command
    @Command.option(
        ["--verbose", "-v"],
        default=False,
        help="Verbose output",
        is_flag=True,
    )
    def deploy(
        target: Annotated[str, Argument(help="Deployment target")],
        count: Annotated[
            int,
            Option("--count", "-c", help="Replica count", metavar="N"),
        ] = 1,
        tag: Annotated[
            list[str],
            Option("--tag", help="Image tag"),
        ] = [],
        verbose: Annotated[
            bool,
            Option("--verbose", "-v", help="Verbose output"),
        ] = False,
    ) -> None:
        calls.append((target, count, tag, verbose))

    @command.command(description="Show deployment status.")
    def status(
        environment: Annotated[
            str,
            Argument(
                help="Environment",
                metavar="ENV",
                choices=("dev", "prod"),
            ),
        ],
    ) -> str:
        return environment

    command.run(
        [
            "api",
            "--count=3",
            "--tag",
            "stable",
            "--tag",
            "latest",
            "--verbose",
        ]
    )
    assert calls == [("api", 3, ["stable", "latest"], True)]
    assert command.run(["status", "prod"]) == "prod"

    parser = command._build_parser()
    assert command._build_parser() is parser
    help_text = format_plain_help(command)
    assert all(
        text in help_text
        for text in (
            "Usage: deploy",
            "Deployment target",
            "Commands:",
            "status",
        )
    )
    assert render_help(command, stream=io.StringIO()) == help_text

    errors = io.StringIO()
    print_error("bad deployment", command, file=errors)
    assert "Error: bad deployment" in errors.getvalue()

    with pytest.raises(SystemExit) as help_exit:
        command.run(["--help"])
    assert help_exit.value.code == 0
    assert "Usage: deploy" in capsys.readouterr().out

    with pytest.raises(SystemExit) as error_exit:
        command.run(["--unknown"])
    assert error_exit.value.code == 2
    assert "Unknown option" in capsys.readouterr().err


def test_nested_workspace_combines_layout_focus_overlay_and_effects() -> None:
    """A workspace can combine nested grids, focus, overlays, and animation."""

    class Navigation(BaseGrid, direction="vertical"):
        pages: Options = Field(
            default_factory=lambda: Options(
                items=("Overview", "Logs", "Settings"),
                searchable=False,
            ),
            group="navigation",
        )

    class Workspace(BaseGrid, direction="horizontal", gap=1):
        navigation: Navigation = Field(
            default_factory=Navigation,
            width="1/3",
            border="rounded",
            title="Pages",
        )
        content: list[object] = Field(
            default_factory=lambda: [
                Text("Overview", modifiers=("bold",)),
                Chart(series={"cpu": [1, 4, 2, 5]}),
                Table(data=[{"service": "api", "latency": 12}]),
            ],
            direction="vertical",
            width="2fr",
            gap=1,
            border="double",
            title="Workspace",
            group="content",
        )
        notice: Text = Field(
            default_factory=lambda: Text("Saved"),
            overlay=True,
            align="center",
            width=12,
            height=3,
            border="rounded",
            z=5,
        )

        @on_keyboard("s")
        def save(self) -> None:
            self.notice = Text("Saved now")

    runtime = Runtime.offscreen(80, 24)
    try:
        workspace = Workspace()
        runtime.set_root(workspace)
        frame = runtime.render()
        assert all(
            text in frame.text
            for text in ("Pages", "Workspace", "Overview", "Saved")
        )
        assert runtime.focus("navigation")
        runtime.perform(Action.keyboard("down"))
        assert workspace.navigation.pages.value == "Logs"
        runtime.perform(Action.keyboard("s"))
        assert "Saved now" in runtime.render().text
        assert workspace.grid_play_effect(
            Effect("coalesce", duration_ms=20),
            fields=["content"],
        )
    finally:
        runtime.close()


def test_frame_export_combines_render_cursor_device_and_commands() -> None:
    """A rendered frame preserves the metadata needed by remote clients."""
    cursor = types.SimpleNamespace(
        get_position=lambda: (4, 2),
        visible=False,
        style=lambda: "steady_bar",
    )
    device = types.SimpleNamespace(title=lambda: "Operations")
    terminal = types.SimpleNamespace(
        size=types.SimpleNamespace(width=40, height=8),
        get_output=lambda: "ready",
        get_output_as_ansi=lambda: "\x1b[32mready\x1b[0m",
        cursor=cursor,
        device=device,
        _frame_commands=({"kind": "clipboard", "value": "ready"},),
    )

    frame = frame_from_terminal(terminal, revision=7)
    assert frame == Frame(
        width=40,
        height=8,
        text="ready",
        ansi="\x1b[32mready\x1b[0m",
        cursor_position=(4, 2),
        cursor_visible=False,
        cursor_style="steady_bar",
        title="Operations",
        commands=({"kind": "clipboard", "value": "ready"},),
        revision=7,
    )
    assert frame.contains("ready")
    assert frame.rows[0] == "ready"
    assert len(frame.rows) == 8

    fallback = frame_from_terminal(types.SimpleNamespace(size=lambda: (2, 2)))
    assert fallback.rows == ("", "")


def test_browser_session_combines_shell_frames_events_and_request_hooks() -> (
    None
):
    """One web session serves UI, input, and application HTTP routes."""

    class App(BaseGrid):
        message: str = Field(default="waiting")

        @on_keyboard("enter")
        def submit(self) -> None:
            self.message = "submitted"

        @on_get_request("/health")
        def health(self) -> Response:
            return Response.json({"status": "ok"})

        @on_post_request("/jobs")
        def create_job(self, ctx) -> Response:
            return Response.json(
                {"received": ctx.request.json()},
                status=202,
            )

    server = NativeWebServer(
        ("127.0.0.1", 0),
        App,
        title="<Operations>",
        width=32,
        height=6,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = http.client.HTTPConnection(
        "127.0.0.1",
        server.server_address[1],
        timeout=2,
    )
    try:
        connection.request("GET", "/")
        response = connection.getresponse()
        shell = response.read().decode()
        assert response.status == 200
        assert "&lt;Operations&gt;" in shell

        connection.request("GET", "/health")
        response = connection.getresponse()
        assert json.loads(response.read()) == {"status": "ok"}

        connection.request(
            "POST",
            "/jobs?priority=high",
            body=json.dumps({"name": "backup"}),
            headers={"content-type": "application/json"},
        )
        response = connection.getresponse()
        assert response.status == 202
        assert json.loads(response.read()) == {"received": {"name": "backup"}}

        connection.request(
            "POST",
            "/xnano/event",
            body=json.dumps(
                {
                    "type": "keyboard",
                    "binding": "enter",
                    "kind": "press",
                }
            ),
            headers={"content-type": "application/json"},
        )
        response = connection.getresponse()
        response.read()
        assert response.status == 204

        connection.request("GET", "/xnano/frame")
        response = connection.getresponse()
        assert "submitted" in json.loads(response.read())["text"]

        connection.request(
            "POST",
            "/xnano/event",
            body=b"not-json",
            headers={"content-type": "application/json"},
        )
        response = connection.getresponse()
        response.read()
        assert response.status == 400
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_web_host_accepts_component_factory_and_managed_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The web host normalizes roots and forwards its complete configuration."""
    component = Text("ready")
    factory, shared, grid_class = grid_factory(component)
    assert shared is True
    assert grid_class is None
    assert factory() is component

    callable_factory = lambda: Text("fresh")
    factory, shared, grid_class = grid_factory(callable_factory)
    assert factory is callable_factory
    assert shared is False
    assert grid_class is None
    with pytest.raises(TypeError):
        grid_factory(object())

    calls: list[dict[str, object]] = []

    def serve_application(factory, **options) -> None:
        assert isinstance(factory(), Text)
        calls.append(options)

    monkeypatch.setattr(
        "xnano.server.native.serve_native",
        serve_application,
    )
    web = Web(
        title="Status",
        width=100,
        height=30,
    )
    web.run(
        callable_factory,
        state={"tenant": "demo"},
        host="0.0.0.0",
        port=9000,
    )
    assert calls == [
        {
            "state": {"tenant": "demo"},
            "title": "Status",
            "host": "0.0.0.0",
            "port": 9000,
            "width": 100,
            "height": 30,
        }
    ]

    managed = types.SimpleNamespace(
        shutdown=lambda: calls.append({"shutdown": True}),
        server_close=lambda: calls.append({"closed": True}),
    )
    web._server = managed
    web.close()
    assert web._server is None
    assert calls[-2:] == [{"shutdown": True}, {"closed": True}]


def test_terminal_facade_combines_lazy_runtime_state_focus_and_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The high-level terminal keeps one runtime across its public controls."""

    class Form(BaseGrid, direction="vertical"):
        name: Input = Field(default_factory=Input, group="name", height=1)
        email: Input = Field(default_factory=Input, group="email", height=1)

    monkeypatch.setattr(
        Terminal,
        "supports_live_terminal",
        staticmethod(lambda: False),
    )
    terminal = Terminal(title="Signup")
    assert terminal.surface == "terminal"

    form = Form()
    terminal.attach_grid(form)
    frame = terminal.render(form, state={"step": 1})
    assert terminal.state == {"step": 1}
    assert frame.width == terminal.size[0]
    assert terminal.surface == "offscreen"
    assert terminal.device is terminal.runtime.device
    assert terminal.cursor is terminal.runtime.cursor
    assert terminal.actions is terminal.runtime.actions
    assert terminal.stage is terminal.runtime.stage

    terminal.state = {"step": 2}
    assert terminal.runtime.state == {"step": 2}
    assert terminal.focus("name")
    assert terminal.focus_next()
    assert terminal.focused_group == "email"
    assert terminal.focus_previous()
    assert terminal.focused_group == "name"
    terminal.blur()
    assert terminal.focused_group is None
    assert terminal.get_output() == terminal.runtime.get_output()
    assert (
        terminal.get_output_as_ansi() == terminal.runtime.get_output_as_ansi()
    )

    terminal.request_exit()
    assert terminal.runtime._should_exit is True
    terminal.close()
