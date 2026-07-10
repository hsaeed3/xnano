#!/usr/bin/env python3
"""Generate screenshots and demo GIFs for xnano README examples.

Embeds each README example inline, writes it to a temp file, records it with
VHS, and saves the output to docs/assets/demos/. Static examples produce short
GIFs; reactive ones show interactions before quitting.

Requirements:
- `vhs` on PATH (brew install vhs on macOS)
- xnano importable in the active environment (uv sync from repo root)

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


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "docs" / "assets" / "demos"

TERMINAL_SETTINGS = """
Require python

Set Shell "bash"
Set FontSize 18
Set LineHeight 1.15
Set Width 1200
Set Height {height}
Set Theme "GruvboxDark"
Set Padding 40
Set Margin 28
Set MarginFill "#11111b"
Set BorderRadius 14
Set WindowBar Colorful
Set WindowBarSize 36
Set Framerate 30
Set PlaybackSpeed 1.0
Set TypingSpeed 35ms

Env TERM "xterm-256color"
Env COLORTERM "truecolor"
""".strip()


@dataclass(frozen=True)
class Demo:
    name: str
    code: str
    steps: tuple[str, ...] = field(default_factory=tuple)
    launch_delay: str = "1.5s"
    tape_env: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    height: int = 700
    """Recording height in pixels, fitted to the example's content."""


# All inline examples include a `q` quit handler so the tape exits cleanly.
# build_tape() always appends a hidden `Type "q"` + sleep to terminate.
DEMOS: tuple[Demo, ...] = (
    Demo(
        name="hello_world",
        code=dedent("""\
            from xnano.grid import Grid
            from xnano.fields import Field
            from xnano.terminal import Terminal
            from xnano.context import Context
            from xnano.color import tailwind_color
            from xnano.hooks import on_tick, on_keyboard

            class App(Grid):
                message: str = Field(default="Hello, world!", color=tailwind_color("sky", 500))
                current_color: str = Field(default="sky", state=True)

                @on_tick(1000)
                def update_color(self) -> None:
                    if self.current_color == "sky":
                        self.current_color = "emerald"
                        self.grid_set_field("message", color="white")
                    else:
                        self.current_color = "sky"
                        self.grid_set_field("message", color=tailwind_color("sky", 500))

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(App())
        """),
        launch_delay="1s",
        steps=(
            "Sleep 1s",
            "Sleep 1s",
            "Sleep 1s",
            "Sleep 1s",
            "Sleep 1s",
            "Sleep 1s",
        ),
        height=280,
    ),
    Demo(
        name="layout_nesting",
        launch_delay="1.5s",
        code=dedent("""\
            from xnano.grid import Grid
            from xnano.fields import Field
            from xnano.terminal import Terminal
            from xnano.context import Context
            from xnano.hooks import on_keyboard

            class SidebarTitle(Grid, align="center"):
                title: str = Field("This is a title.", align="center")

            class Sidebar(Grid, direction="vertical"):
                title: SidebarTitle = Field(default_factory=SidebarTitle, height="10%")
                nav: str = Field(default="- Home", height="1fr")

            class App(Grid, direction="horizontal", gap=1):
                sidebar: Sidebar = Field(default_factory=Sidebar, width="25%")
                content: str = Field(default="Main area", width="1fr", border="rounded")

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(App())
        """),
        steps=("Sleep 1.5s",),
        height=330,
    ),
    Demo(
        name="keyboard_events",
        launch_delay="1.5s",
        code=dedent("""\
            from xnano.grid import Grid
            from xnano.fields import Field
            from xnano.terminal import Terminal
            from xnano.context import Context
            from xnano.hooks import on_keyboard

            class Counter(Grid, direction="vertical", gap=1):
                label: str = Field(default="Count: 0", height=1)
                hint: str = Field(default="Press up/down · q to quit", height=1)
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
            "Up@350ms 3",
            "Sleep 400ms",
            "Down@350ms 1",
            "Sleep 400ms",
            "Up@350ms 2",
            "Sleep 600ms",
        ),
        height=270,
    ),
    Demo(
        name="click_handlers",
        launch_delay="1.5s",
        tape_env=(("XNANO_VHS_DEMO", "click_handlers"),),
        code=dedent("""\
            import os

            from xnano.grid import Grid
            from xnano.fields import Field
            from xnano.terminal import Terminal
            from xnano.context import Context
            from xnano.hooks import on_click, on_keyboard


            class App(Grid, direction="vertical", gap=1):
                button: str = Field(default="[ Click me ]", height=3, border="rounded")
                status: str = Field(default="Waiting...", height="1fr")

                @on_click("button")
                def on_button(self, ctx: Context) -> None:
                    self.status = "Clicked!"

                @on_keyboard("c")
                def _vhs_simulate_click(self, ctx: Context) -> None:
                    # VHS has no mouse-click command; the recorder sends this
                    # hidden key to fire the same handler after layout settles.
                    if os.environ.get("XNANO_VHS_DEMO") == "click_handlers":
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
            "Sleep 400ms",
            "Show",
            "Sleep 1.5s",
        ),
        height=350,
    ),
    Demo(
        name="timed_updates",
        launch_delay="1.5s",
        code=dedent("""\
            import time
            from xnano.grid import Grid
            from xnano.fields import Field
            from xnano.terminal import Terminal
            from xnano.context import Context
            from xnano.hooks import on_tick, on_keyboard

            class Clock(Grid, direction="vertical"):
                time_display: str = Field(default="", height=3, border="rounded")

                def __post_init__(self) -> None:
                    self.time_display = time.strftime("%H:%M:%S")

                @on_tick(1000)
                def update_time(self) -> None:
                    self.time_display = time.strftime("%H:%M:%S")

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(Clock())
        """),
        steps=("Sleep 3.5s",),
        height=310,
    ),
    Demo(
        name="state_context",
        launch_delay="1.5s",
        code=dedent("""\
            from dataclasses import dataclass
            from xnano.grid import Grid
            from xnano.fields import Field
            from xnano.terminal import Terminal
            from xnano.context import Context
            from xnano.hooks import on_keyboard

            @dataclass
            class AppState:
                username: str = "guest"

            class App(Grid, direction="vertical", gap=1):
                header: str = Field(default="", height=1)
                body: str = Field(default="Press q to quit", height="1fr")

                def grid_render(self) -> None:
                    self.header = f"Hello, {self.state.username}!"

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()

            with Terminal(state=AppState(username="hammad")) as t:
                t.run(App())
        """),
        steps=("Sleep 1.5s",),
        height=270,
    ),
    Demo(
        name="custom_component",
        launch_delay="1.5s",
        code=dedent("""\
            import dataclasses
            from xnano.grid import Grid
            from xnano.fields import Field
            from xnano.terminal import Terminal
            from xnano.context import Context
            from xnano.color import tailwind_color, pydantic_color
            from xnano.hooks import on_keyboard
            from xnano.components.abstract import AbstractComponent, ComponentRenderContext
            from xnano.core.nodes.terminal import ParagraphNode, AbstractTerminalNode


            @dataclasses.dataclass
            class Badge(AbstractComponent):
                label: str = ""
                color: str = "white"

                def get_terminal_node(self, ctx: ComponentRenderContext) -> AbstractTerminalNode:
                    return ParagraphNode(text=self.label, color=self.color)


            class StatusBoard(Grid, direction="vertical", gap=1):
                ok: Badge = Field(default_factory=lambda: Badge(label="● OK", color=tailwind_color("emerald", 500)), height=1)
                warn: Badge = Field(default_factory=lambda: Badge(label="● Warning", color="yellow"), height=1)
                err: Badge = Field(default_factory=lambda: Badge(label="● Error", color=pydantic_color("palevioletred")), height=1)

                @on_keyboard("q")
                def quit(self, ctx: Context) -> None:
                    ctx.terminal.request_exit()


            Terminal().run(StatusBoard())
        """),
        steps=("Sleep 1.5s",),
        height=310,
    ),
)


def build_tape(
    demo: Demo, output: Path, output_rel: Path, code_path: Path
) -> str:
    python = sys.executable
    demo_env = [f'Env {key} "{value}"' for key, value in demo.tape_env]
    lines = [
        f"Output {output_rel.as_posix()}",
        TERMINAL_SETTINGS.format(height=demo.height),
        *demo_env,
        "Hide",
        f'Type "{python} {code_path.as_posix()}"',
        "Enter",
        f"Sleep {demo.launch_delay}",
        "Show",
        *demo.steps,
        "Hide",
        'Type "q"',
        "Sleep 500ms",
    ]
    return "\n".join(lines) + "\n"


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise SystemExit(
            f"Missing required tool: {name}\n"
            f"Install VHS: https://github.com/charmbracelet/vhs\n"
            f"  macOS: brew install vhs\n"
            f"  Linux: see VHS install docs (requires ffmpeg)"
        )
    return path


def run_vhs(vhs_path: str, tape_path: Path, *, quiet: bool) -> None:
    command = [vhs_path, str(tape_path)]
    if quiet:
        command.append("--quiet")
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def optimize_gif(gif_path: Path, *, gifsicle: str | None) -> None:
    if gifsicle is None:
        return
    subprocess.run(
        [gifsicle, "-O3", "--lossy=30", str(gif_path), "-o", str(gif_path)],
        check=True,
    )


def generate_demo(
    demo: Demo,
    *,
    vhs_path: str,
    gifsicle_path: str | None,
    dry_run: bool,
    quiet: bool,
) -> Path:
    output = OUTPUT_DIR / f"example_{demo.name}.gif"
    output_rel = output.relative_to(REPO_ROOT)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=f"-{demo.name}.py",
        prefix="xnano-demo-",
        delete=False,
    ) as code_file:
        code_file.write(demo.code)
        code_path = Path(code_file.name)

    tape_body = build_tape(demo, output, output_rel, code_path)

    if dry_run:
        print(f"# {demo.name} -> {output.relative_to(REPO_ROOT)}")
        print(f"# code: {code_path}")
        print(tape_body)
        code_path.unlink(missing_ok=True)
        return output

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=f"-{demo.name}.tape",
        prefix="xnano-readme-",
        delete=False,
    ) as tape_file:
        tape_file.write(tape_body)
        tape_path = Path(tape_file.name)

    try:
        print(f"Recording {demo.name} -> {output.relative_to(REPO_ROOT)}")
        run_vhs(vhs_path, tape_path, quiet=quiet)
        optimize_gif(output, gifsicle=gifsicle_path)
    finally:
        code_path.unlink(missing_ok=True)
        tape_path.unlink(missing_ok=True)

    if not output.is_file():
        raise SystemExit(f"Expected GIF was not created: {output}")

    size_kb = output.stat().st_size / 1024
    print(f"  wrote {output.name} ({size_kb:.0f} KiB)")
    return output


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--demo",
        choices=[demo.name for demo in DEMOS],
        help="Record a single demo instead of all",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated VHS tape files without recording",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Pass --quiet through to VHS",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    demos = (
        [d for d in DEMOS if d.name == args.demo] if args.demo else list(DEMOS)
    )

    vhs_path = require_tool("vhs") if not args.dry_run else ""
    gifsicle_path = shutil.which("gifsicle")

    for demo in demos:
        generate_demo(
            demo,
            vhs_path=vhs_path,
            gifsicle_path=gifsicle_path,
            dry_run=args.dry_run,
            quiet=args.quiet,
        )

    if not args.dry_run:
        print(
            f"\nDone — {len(demos)} demo GIF(s) in {OUTPUT_DIR.relative_to(REPO_ROOT)}/"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
