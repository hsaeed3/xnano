#!/usr/bin/env python3
"""scripts.generate_readme_demos

---

Generate demo GIFs for README inline examples.

Owns **only** README assets under ``docs/assets/demos/``:

    docs/assets/demos/example_<name>.gif

Concept docs use ``scripts/generate_concept_demos.py`` →
``docs/assets/concepts/``. Full-app galleries use
``docs/assets/examples/``. Do not cross-link those trees from the README.

Recording stack matches ``generate_concept_demos`` /
``generate_xnano_demos``:

- ``vhs_tape.build_run_tape`` (hidden launch, clean shell env)
- docs-dark VHS theme + margin fill from ``vhs_showcase_themes``
- ``COLORTERM=truecolor`` for Tailwind / truecolor colors
- fitted width / height / padding (not a full-screen terminal)

Requirements:
    vhs on PATH  (brew install vhs on macOS)
    xnano importable in the active environment (uv sync from repo root)

Usage:
    uv run python scripts/generate_readme_demos.py
    uv run python scripts/generate_readme_demos.py --demo hello_world
    uv run python scripts/generate_readme_demos.py --dry-run
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = REPOSITORY_ROOT / "docs" / "assets" / "demos"
SCRIPTS_DIRECTORY = REPOSITORY_ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS_DIRECTORY))
from vhs_showcase_themes import (  # noqa: E402
    get_margin_fill,
    get_vhs_theme,
)
from vhs_tape import build_run_tape  # noqa: E402

_THEME = "dark"
"""README demos record against the docs dark palette only."""

_WIDTH = 960
"""Shared full recording width for every README demo GIF."""

_BASE_SETTINGS = """\
Require python

Set Shell "bash"
Set FontSize 16
Set LineHeight 1.2
Set Width {_WIDTH}
Set Height {height}
Set Padding {padding}
Set Margin 12
Set MarginFill "{margin_fill}"
Set BorderRadius 12
Set WindowBar Colorful
Set WindowBarSize 32
Set Framerate 30
Set PlaybackSpeed 1.0
Set TypingSpeed 40ms
Set Theme {theme}

Env TERM "xterm-256color"
Env COLORTERM "truecolor"\
""".replace("{_WIDTH}", str(_WIDTH))


def _code(body: str) -> str:
    """Normalize demo source — avoids broken dedent from indented closers."""
    content = "\n".join(line for line in body.splitlines() if line.strip())
    return dedent(content).strip() + "\n"


@dataclass(frozen=True)
class Demo:
    """One README example recording."""

    name: str
    """Stem used in ``example_<name>.gif``."""
    code: str
    """Complete Python source executed via ``--run-example``."""
    steps: tuple[str, ...] = field(default_factory=tuple)
    """VHS interaction steps after the launch delay."""
    launch_delay: str = "1.5s"
    """Wait after starting the script before showing the terminal."""
    record_delay: str = "1s"
    """Hold after interactions before stopping."""
    env: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    """Extra ``Env KEY "VALUE"`` lines for the tape."""
    auto_quit: bool = True
    """Send hidden ``q`` after the recording hold (interactive ``run()``)."""
    height: int = 320
    """Recording height in pixels — only dimension that varies per demo."""
    padding: int = 12
    """Space between terminal content and recording edge."""


# Static demos use the print-like ``xnano.render`` (stdout ANSI, no session
# enter/exit flash). Interactive demos use ``Terminal().run``.
DEMOS: tuple[Demo, ...] = (
    Demo(
        name="render_text",
        code=_code("""
            import time
            from xnano import render
            from xnano.components.text import Text

            render(
                Text("Hello from xnano!", color="violet", modifiers=["bold"])
            )
            time.sleep(4)
        """),
        launch_delay="800ms",
        steps=("Sleep 2.5s",),
        record_delay="500ms",
        auto_quit=False,
        height=200,
    ),
    Demo(
        name="render_multiple",
        code=_code("""
            import time
            from xnano import render
            from xnano.components.text import Text

            render(
                Text("● Done: ", color="emerald-400", modifiers=["bold"]),
                Text("All 12 checks passed.", color="slate-400"),
            )
            time.sleep(4)
        """),
        launch_delay="800ms",
        steps=("Sleep 2.5s",),
        record_delay="500ms",
        auto_quit=False,
        height=220,
    ),
    Demo(
        name="styled_text",
        code=_code("""
            import time
            from xnano import render
            from xnano.components.text import Text

            message = Text([
                Text("● ", color="emerald-400"),
                Text("Done: ", color="white", modifiers=["bold"]),
                Text("all tests passed\\n", color="slate-300"),
            ])

            render(message)
            time.sleep(4)
        """),
        launch_delay="800ms",
        steps=("Sleep 2.5s",),
        record_delay="500ms",
        auto_quit=False,
        height=240,
    ),
    Demo(
        name="hello_world",
        code=_code("""
            from xnano.grid import BaseGrid
            from xnano.fields import Field
            from xnano.tui import Terminal
            from xnano.context import Context
            from xnano.color import tailwind_color
            from xnano.events import on_tick, on_keyboard

            class App(BaseGrid):
                message: str = Field(
                    default="Hello, world!",
                    color=tailwind_color("sky", 500),
                )
                current_color: str = Field(default="sky", state=True)

                @on_tick(1000)
                def update_color(self) -> None:
                    if self.current_color == "sky":
                        self.current_color = "white"
                        self.grid_set_field("message", color="white")
                    else:
                        self.current_color = "sky"
                        self.grid_set_field(
                            "message",
                            color=tailwind_color("sky", 500),
                        )

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(App())
        """),
        launch_delay="1.2s",
        steps=(
            "Sleep 1s",
            "Sleep 1s",
            "Sleep 1s",
            "Sleep 1s",
            "Sleep 1s",
        ),
        record_delay="500ms",
        height=280,
    ),
    Demo(
        name="layout_nesting",
        code=_code("""
            from xnano.grid import BaseGrid
            from xnano.fields import Field
            from xnano.tui import Terminal
            from xnano.context import Context
            from xnano.events import on_keyboard

            class SidebarTitle(BaseGrid, align="center"):
                title: str = Field("This is a title.", align="center")

            class Sidebar(BaseGrid, direction="vertical"):
                title: SidebarTitle = Field(
                    default_factory=SidebarTitle,
                    height="10%",
                )
                nav: str = Field(default="- Home", height="1fr")

            class App(BaseGrid, direction="horizontal", gap=1):
                sidebar: Sidebar = Field(
                    default_factory=Sidebar,
                    width="25%",
                )
                content: str = Field(
                    default="Main area",
                    width="1fr",
                    border="rounded",
                )

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(App())
        """),
        steps=("Sleep 2s",),
        record_delay="500ms",
        height=320,
    ),
    Demo(
        name="keyboard_events",
        code=_code("""
            from xnano.grid import BaseGrid
            from xnano.fields import Field
            from xnano.tui import Terminal
            from xnano.context import Context
            from xnano.events import on_keyboard

            class Counter(BaseGrid, direction="vertical", gap=1):
                label: str = Field(
                    default="Count: 0",
                    height=1,
                    border="rounded",
                    border_color="violet-500",
                )
                hint: str = Field(
                    default="  ↑ / ↓ to count  ·  q to quit",
                    height=1,
                    color="slate-500",
                )
                count: int = Field(default=0, state=True)

                @on_keyboard("up")
                def increment(self) -> None:
                    self.count += 1
                    self.label = f"Count: {self.count}"

                @on_keyboard("down")
                def decrement(self) -> None:
                    self.count -= 1
                    self.label = f"Count: {self.count}"

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(Counter())
        """),
        steps=(
            "Up@300ms 3",
            "Sleep 400ms",
            "Down@300ms 1",
            "Sleep 400ms",
            "Up@300ms 2",
            "Sleep 600ms",
        ),
        record_delay="500ms",
        height=280,
    ),
    Demo(
        name="click_handlers",
        code=_code("""
            import os
            from xnano.grid import BaseGrid
            from xnano.fields import Field
            from xnano.tui import Terminal
            from xnano.context import Context
            from xnano.events import on_click, on_keyboard

            class App(BaseGrid, direction="vertical", gap=1):
                button: str = Field(
                    default="  [ Click me ]  ",
                    height=3,
                    border="rounded",
                    border_color="violet-500",
                )
                status: str = Field(
                    default="  Waiting...",
                    height=1,
                    color="slate-400",
                )

                @on_click("button")
                def on_button(self, ctx: Context) -> None:
                    self.status = "  Clicked!"

                @on_keyboard("c")
                def _vhs_simulate_click(self, ctx: Context) -> None:
                    # VHS has no mouse-click command; fire the same handler.
                    if os.environ.get("XNANO_VHS_DEMO") == "1":
                        self.on_button(ctx)

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            Terminal(mouse_events=True).run(App())
        """),
        steps=(
            "Sleep 800ms",
            "Hide",
            'Type "c"',
            "Sleep 500ms",
            "Show",
            "Sleep 1s",
        ),
        launch_delay="1.5s",
        record_delay="500ms",
        env=(("XNANO_VHS_DEMO", "1"),),
        height=280,
    ),
    Demo(
        name="timed_updates",
        code=_code("""
            import time
            from xnano.grid import BaseGrid
            from xnano.fields import Field
            from xnano.tui import Terminal
            from xnano.context import Context
            from xnano.events import on_tick, on_keyboard

            class Clock(BaseGrid, direction="vertical", gap=1):
                time_display: str = Field(
                    default="",
                    height=3,
                    border="rounded",
                    border_color="teal-500",
                    title=" Clock ",
                )
                hint: str = Field(
                    default="  q to quit",
                    height=1,
                    color="slate-500",
                )

                def __post_init__(self) -> None:
                    self.time_display = f"  {time.strftime('%H:%M:%S')}"

                @on_tick(1000)
                def update_time(self) -> None:
                    self.time_display = f"  {time.strftime('%H:%M:%S')}"

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            Terminal(tick_interval=1000).run(Clock())
        """),
        steps=("Sleep 3.5s",),
        record_delay="500ms",
        height=280,
    ),
    Demo(
        name="state_context",
        code=_code("""
            from dataclasses import dataclass
            from xnano.grid import BaseGrid
            from xnano.fields import Field
            from xnano.tui import Terminal
            from xnano.context import Context
            from xnano.events import on_keyboard

            @dataclass
            class AppState:
                username: str = "guest"

            class App(BaseGrid, direction="vertical", gap=1):
                header: str = Field(
                    default="",
                    height=1,
                    color="white",
                    background="violet-900",
                )
                body: str = Field(
                    default="Press q to quit",
                    color="slate-400",
                )

                def grid_render(self) -> None:
                    self.header = f"  Hello, {self.state.username}!"

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            with Terminal(state=AppState(username="hammad")) as t:
                t.run(App())
        """),
        steps=("Sleep 2s",),
        record_delay="500ms",
        height=260,
    ),
    Demo(
        name="custom_component",
        code=_code("""
            import dataclasses
            from xnano.grid import BaseGrid
            from xnano.fields import Field
            from xnano.tui import Terminal
            from xnano.context import Context
            from xnano.color import tailwind_color, pydantic_color
            from xnano.events import on_keyboard
            from xnano.components.abstract import (
                AbstractComponent,
                ComponentRenderContext,
            )
            from xnano.tui.nodes import ParagraphNode, AbstractTerminalNode

            @dataclasses.dataclass
            class Badge(AbstractComponent):
                label: str = ""
                color: str = "white"

                def get_terminal_node(
                    self,
                    ctx: ComponentRenderContext,
                ) -> AbstractTerminalNode:
                    return ParagraphNode(text=self.label, color=self.color)

            class StatusBoard(BaseGrid, direction="vertical", gap=1):
                ok: Badge = Field(
                    default_factory=lambda: Badge(
                        label="● OK",
                        color=tailwind_color("emerald", 500),
                    ),
                    height=1,
                )
                warn: Badge = Field(
                    default_factory=lambda: Badge(
                        label="● Warning",
                        color="yellow",
                    ),
                    height=1,
                )
                err: Badge = Field(
                    default_factory=lambda: Badge(
                        label="● Error",
                        color=pydantic_color("palevioletred"),
                    ),
                    height=1,
                )

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(StatusBoard())
        """),
        steps=("Sleep 2s",),
        record_delay="500ms",
        height=260,
    ),
)

_DEMO_MAP: dict[str, Demo] = {demo.name: demo for demo in DEMOS}


def _settings(demo: Demo) -> str:
    """Return the VHS settings block for one README recording."""
    return _BASE_SETTINGS.format(
        theme=get_vhs_theme(_THEME),
        margin_fill=get_margin_fill(_THEME),
        height=demo.height,
        padding=demo.padding,
    )


def get_tape(demo: Demo, output: Path) -> str:
    """Build the VHS tape for one README demo."""
    env_lines = [f'Env {key} "{value}"' for key, value in demo.env]
    env_lines.extend(
        (
            'Env XNANO_VHS_DOCS_BG "1"',
            f'Env XNANO_VHS_THEME "{_THEME}"',
        )
    )
    tape = build_run_tape(
        output=output.relative_to(REPOSITORY_ROOT),
        settings=_settings(demo),
        launch_command=(
            "uv run python scripts/generate_readme_demos.py "
            f"--run-example {demo.name}"
        ),
        steps=demo.steps,
        launch_delay=demo.launch_delay,
        record_delay=demo.record_delay,
        env_lines=env_lines,
    )
    if not demo.auto_quit:
        tape = tape.replace('Type "q"\nSleep 300ms\n', "")
    return tape


def require_vhs() -> str:
    """Return the vhs executable path or exit with install guidance."""
    path = shutil.which("vhs")
    if path is None:
        raise SystemExit(
            "vhs not found on PATH.\n"
            "  macOS:  brew install vhs\n"
            "  Linux:  https://github.com/charmbracelet/vhs#installation"
        )
    return path


def optimize(gif: Path) -> None:
    """Lossy-optimize a GIF when gifsicle is available."""
    gifsicle = shutil.which("gifsicle")
    if gifsicle is None:
        return
    subprocess.run(
        [gifsicle, "-O3", "--lossy=30", str(gif), "-o", str(gif)],
        check=True,
    )


def run_example(name: str) -> None:
    """Execute one README demo script for VHS to record."""
    demo = _DEMO_MAP.get(name)
    if demo is None:
        raise SystemExit(f"Unknown example: {name!r}")
    exec(
        compile(demo.code, f"<readme-demo:{name}>", "exec"),
        {"__name__": "__main__"},
    )


def generate_demo(
    demo: Demo,
    *,
    vhs: str,
    dry_run: bool,
    quiet: bool,
) -> None:
    """Record one README GIF into ``docs/assets/demos``."""
    output = OUTPUT_DIRECTORY / f"example_{demo.name}.gif"
    tape_body = get_tape(demo, output)

    if dry_run:
        print(f"# {demo.name} -> {output.relative_to(REPOSITORY_ROOT)}")
        print(tape_body)
        return

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=f"-readme-{demo.name}.tape",
        prefix="xnano-",
        delete=False,
    ) as tape_file:
        tape_file.write(tape_body)
        tape_path = Path(tape_file.name)

    try:
        print(
            f"Recording {demo.name} -> {output.relative_to(REPOSITORY_ROOT)}"
        )
        command = [vhs, str(tape_path)]
        if quiet:
            command.append("--quiet")
        subprocess.run(command, cwd=REPOSITORY_ROOT, check=True)
        optimize(output)
    finally:
        tape_path.unlink(missing_ok=True)

    if not output.is_file():
        raise SystemExit(f"Expected GIF not created: {output}")

    size_kb = output.stat().st_size / 1024
    print(f"  wrote {output.name} ({size_kb:.0f} KiB)")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for recording or embedded launch."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--demo",
        choices=list(_DEMO_MAP),
        action="append",
        help="Record only the named demo (repeatable)",
    )
    parser.add_argument(
        "--run-example",
        choices=list(_DEMO_MAP),
        help=argparse.SUPPRESS,
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
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Generate README demos or run one example for VHS."""
    args = parse_args(argv)

    if args.run_example:
        run_example(args.run_example)
        return 0

    demos = (
        [_DEMO_MAP[name] for name in args.demo] if args.demo else list(DEMOS)
    )
    vhs = require_vhs() if not args.dry_run else ""

    for demo in demos:
        generate_demo(
            demo,
            vhs=vhs,
            dry_run=args.dry_run,
            quiet=args.quiet,
        )

    if not args.dry_run:
        print(
            f"\nDone — {len(demos)} GIF(s) in "
            f"{OUTPUT_DIRECTORY.relative_to(REPOSITORY_ROOT)}/"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
