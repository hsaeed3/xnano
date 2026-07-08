#!/usr/bin/env python3
"""Generate demo GIFs for the inline code examples in docs/api/concepts/.

Each Demo corresponds to a complete, runnable code block shown in the concept
docs. Outputs one GIF per demo per theme (docs dark + light palettes) to
docs/assets/concepts/.

Requirements:
    vhs on PATH  (brew install vhs on macOS)
    xnano importable in the active environment (uv sync from repo root)

Usage:
    uv run python scripts/generate_concept_demos.py
    uv run python scripts/generate_concept_demos.py --demo hooks_keyboard
    uv run python scripts/generate_concept_demos.py --theme dark
    uv run python scripts/generate_concept_demos.py --dry-run
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
OUTPUT_DIR = REPO_ROOT / "docs" / "assets" / "concepts"
SCRIPTS_DIR = REPO_ROOT / "scripts"
LAUNCHER = "scripts/vhs-demo"

sys.path.insert(0, str(SCRIPTS_DIR))
from vhs_showcase_themes import get_margin_fill, get_vhs_theme  # noqa: E402
from vhs_tape import build_run_tape  # noqa: E402

THEMES = {
    "dark": "GruvboxDark",
    "light": "AtomOneLight",
}

_BASE_SETTINGS = """\
Require python

Set Shell "bash"
Set FontSize 16
Set LineHeight 1.2
Set Width 1200
Set Height 700
Set Padding 36
Set Margin 24
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
"""


def _code(body: str) -> str:
    """Normalize demo source — avoids broken dedent from indented closers."""
    content = "\n".join(line for line in body.splitlines() if line.strip())
    return dedent(content).strip() + "\n"


@dataclass(frozen=True)
class Demo:
    name: str
    """Output filename stem, e.g. ``"counter"`` → ``counter-dark.gif``."""
    code: str
    """Complete, self-contained Python source executed by ``run_vhs_demo.py``."""
    steps: tuple[str, ...] = field(default_factory=tuple)
    """VHS interaction steps (keypresses, sleeps) after the launch delay."""
    launch_delay: str = "1.5s"
    """Time to wait after starting the script before showing the terminal."""
    record_delay: str = "1s"
    """Extra sleep after interactions before stopping."""
    env: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    """Extra ``Env KEY "VALUE"`` lines to inject into the tape."""
    auto_quit: bool = True
    """Send ``q`` while hidden after the recording hold."""


DEMOS: tuple[Demo, ...] = (
    Demo(
        name="render_text",
        code=_code("""
            import time
            from xnano.beta import Terminal
            from xnano.beta.components import Text

            Terminal().render(
                Text("Hello from xnano!", color="violet", modifiers=["bold"])
            )
            time.sleep(4)
        """),
        launch_delay="600ms",
        steps=("Sleep 2.5s",),
        record_delay="500ms",
        auto_quit=False,
    ),
    Demo(
        name="render_multiple",
        code=_code("""
            import time
            from xnano.beta import Terminal
            from xnano.beta.components import Text

            Terminal().render(
                Text("Success!", color="emerald-400", modifiers=["bold"]),
                Text("All 12 checks passed.", color="slate-400"),
            )
            time.sleep(4)
        """),
        launch_delay="600ms",
        steps=("Sleep 2.5s",),
        record_delay="500ms",
        auto_quit=False,
    ),
    Demo(
        name="styled_text",
        code=_code("""
            import time
            from xnano.beta import Terminal
            from xnano.beta.components import Text

            message = Text([
                Text("● ", color="emerald-400"),
                Text("Done: ", color="white", modifiers=["bold"]),
                Text("all tests passed\\n", color="slate-300"),
            ])

            Terminal().render(message)
            time.sleep(4)
        """),
        launch_delay="600ms",
        steps=("Sleep 2.5s",),
        record_delay="500ms",
        auto_quit=False,
    ),
    Demo(
        name="hello_render",
        code=_code("""
            from xnano.beta import Field, Grid, Terminal
            from xnano.beta.hooks import on_keyboard

            class Hello(Grid, direction="vertical", gap=1):
                line1: str = Field(
                    default="Hello from xnano!",
                    color="violet",
                    modifiers=["bold"],
                    height=1,
                )
                line2: str = Field(
                    default="Render returns immediately — no event loop needed.",
                    color="slate-400",
                )

                @on_keyboard("q")
                def quit(self, ctx) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(Hello())
        """),
        steps=("Sleep 2s",),
        record_delay="500ms",
    ),
    Demo(
        name="hello_grid",
        code=_code("""
            from xnano.beta import Field, Grid, Terminal
            from xnano.beta.hooks import on_keyboard

            class Hello(Grid, direction="vertical"):
                message: str = Field(default="Press q to quit.", height=1)

                @on_keyboard("q")
                def quit(self, ctx) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(Hello())
        """),
        steps=("Sleep 2s",),
        record_delay="500ms",
    ),
    Demo(
        name="terminal_render",
        code=_code("""
            from xnano.beta import Field, Grid, Terminal
            from xnano.beta.hooks import on_keyboard

            class Output(Grid, direction="vertical", gap=1):
                line1: str = Field(
                    default="Build complete.",
                    color="emerald-400",
                    modifiers=["bold"],
                    height=1,
                )
                line2: str = Field(default="12 tests passed.", color="slate-400")

                @on_keyboard("q")
                def quit(self, ctx) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(Output())
        """),
        steps=("Sleep 2s",),
        record_delay="500ms",
    ),
    Demo(
        name="terminal_state",
        code=_code("""
            from dataclasses import dataclass
            from xnano.beta import Field, Grid, Terminal
            from xnano.beta.hooks import on_keyboard

            @dataclass
            class AppState:
                theme: str = "dark"

            class App(Grid, direction="vertical", gap=1):
                header: str = Field(
                    default="",
                    height=1,
                    color="white",
                    background="violet-900",
                )
                body: str = Field(
                    default="Press t to toggle theme · q to quit",
                    color="slate-400",
                )

                def grid_render(self) -> None:
                    theme = self.state.theme if self.state is not None else "dark"
                    self.header = f"  Theme: {theme}"

                @on_keyboard("t")
                def toggle(self, ctx) -> None:
                    if ctx.state is not None:
                        ctx.state.theme = (
                            "light" if ctx.state.theme == "dark" else "dark"
                        )

                @on_keyboard("q")
                def quit(self, ctx) -> None:
                    ctx.terminal.request_exit()

            with Terminal(state=AppState()) as terminal:
                terminal.run(App())
        """),
        steps=(
            'Type "t"',
            "Sleep 800ms",
            'Type "t"',
            "Sleep 800ms",
        ),
        record_delay="500ms",
    ),
    Demo(
        name="grid_basic",
        code=_code("""
            from xnano.beta import Field, Grid, Terminal
            from xnano.beta.hooks import on_keyboard

            class App(Grid, direction="vertical"):
                header: str = Field(
                    default="My App",
                    height=1,
                    color="white",
                    background="violet",
                )
                body: str = Field(default="Hello, world!")
                footer: str = Field(default="[q] quit", height=1, color="slate-500")

                @on_keyboard("q")
                def quit(self, ctx) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(App())
        """),
        steps=("Sleep 2s",),
        record_delay="500ms",
    ),
    Demo(
        name="grid_nested",
        code=_code("""
            from xnano.beta import Field, Grid, Terminal
            from xnano.beta.hooks import on_keyboard

            class Sidebar(Grid, direction="vertical"):
                nav: str = Field(
                    default="  — Home\\n  — About\\n  — Settings",
                    border="rounded",
                    border_color="slate-600",
                )
                status: str = Field(default="  Ready", height=1, color="slate-500")

            class App(Grid, direction="horizontal", gap=1):
                sidebar: Sidebar = Field(default_factory=Sidebar, width="25%")
                main: str = Field(
                    default="Main content area.",
                    width="1fr",
                    border="rounded",
                    border_color="violet-500",
                    title=" Content ",
                )

                @on_keyboard("q")
                def quit(self, ctx) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(App())
        """),
        steps=("Sleep 2s",),
        record_delay="500ms",
    ),
    Demo(
        name="grid_render_method",
        code=_code("""
            from xnano.beta import Field, Grid, Terminal
            from xnano.beta.hooks import on_keyboard

            class App(Grid, direction="vertical", gap=1):
                header: str = Field(
                    default="",
                    height=1,
                    color="white",
                    background="teal-800",
                )
                body: str = Field(
                    default="",
                    border="rounded",
                    border_color="teal-600",
                )
                name: str = Field(default="world", state=True)

                def grid_render(self) -> None:
                    self.header = f"  Hello, {self.name}!"
                    self.body = (
                        f"  grid_render() runs every frame.\\n"
                        f"  Current name: {self.name}"
                    )

                @on_keyboard("q")
                def quit(self, ctx) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(App())
        """),
        steps=("Sleep 2s",),
        record_delay="500ms",
    ),
    Demo(
        name="sizing_mix",
        code=_code("""
            from xnano.beta import Field, Grid, Terminal
            from xnano.beta.hooks import on_keyboard

            class App(Grid, direction="vertical", gap=1):
                header: str = Field(
                    default="  fixed: height=1",
                    height=1,
                    color="white",
                    background="violet-900",
                )
                quarter: str = Field(
                    default="  percent: height=25%",
                    height="25%",
                    border="rounded",
                    border_color="sky-500",
                )
                fill: str = Field(
                    default="  fraction: height=1fr",
                    height="1fr",
                    border="rounded",
                    border_color="teal-500",
                )
                footer: str = Field(
                    default="  fixed: height=2",
                    height=2,
                    color="white",
                    background="violet-900",
                )

                @on_keyboard("q")
                def quit(self, ctx) -> None:
                    ctx.terminal.request_exit()

            Terminal().run(App())
        """),
        steps=("Sleep 2s",),
        record_delay="500ms",
    ),
    Demo(
        name="hooks_keyboard",
        code=_code("""
            from xnano.beta import Field, Grid, Terminal
            from xnano.beta.hooks import on_keyboard

            class Counter(Grid, direction="vertical", gap=1):
                label: str = Field(
                    default="Count: 0",
                    height=1,
                    border="rounded",
                    border_color="violet-500",
                    title=" Counter ",
                )
                hint: str = Field(
                    default="  ↑ / ↓ to count  ·  q to quit",
                    height=1,
                    color="slate-500",
                )
                count: int = Field(default=0, state=True)

                @on_keyboard("up")
                def inc(self) -> None:
                    self.count += 1
                    self.label = f"Count: {self.count}"

                @on_keyboard("down")
                def dec(self) -> None:
                    self.count -= 1
                    self.label = f"Count: {self.count}"

                @on_keyboard("q")
                def quit(self, ctx) -> None:
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
    ),
    Demo(
        name="hooks_tick",
        code=_code("""
            import time
            from xnano.beta import Field, Grid, Terminal
            from xnano.beta.hooks import on_keyboard, on_tick

            class Clock(Grid, direction="vertical", gap=1):
                display: str = Field(
                    default="",
                    height=3,
                    border="rounded",
                    border_color="teal-500",
                    title=" Clock ",
                )
                hint: str = Field(default="  q to quit", height=1, color="slate-500")

                @on_tick(1000)
                def update(self) -> None:
                    self.display = f"  {time.strftime('%H:%M:%S')}"

                @on_keyboard("q")
                def quit(self, ctx) -> None:
                    ctx.terminal.request_exit()

            Terminal(tick_interval=1000).run(Clock())
        """),
        steps=("Sleep 3.5s",),
        record_delay="500ms",
    ),
    Demo(
        name="hooks_click",
        code=_code("""
            import os
            from xnano.beta import Field, Grid, Terminal
            from xnano.beta.hooks import on_click, on_keyboard

            class App(Grid, direction="vertical", gap=1):
                button: str = Field(
                    default="  [ Click me ]  ",
                    height=3,
                    border="rounded",
                    border_color="violet-500",
                )
                result: str = Field(default="  Waiting...", height=1, color="slate-400")

                @on_click("button")
                def clicked(self) -> None:
                    self.result = "  Clicked!"
                    self.grid_set_field("result", color="emerald-400")

                @on_keyboard("c")
                def simulate_click(self, ctx) -> None:
                    if os.environ.get("XNANO_VHS_DEMO") == "1":
                        self.clicked()

                @on_keyboard("q")
                def quit(self, ctx) -> None:
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
    ),
)

_DEMO_MAP = {demo.name: demo for demo in DEMOS}


def _settings(theme_key: str) -> str:
    return _BASE_SETTINGS.format(
        theme=get_vhs_theme(theme_key),
        margin_fill=get_margin_fill(theme_key),
    )


def build_tape(demo: Demo, output: Path, theme_key: str) -> str:
    env_lines = [f'Env {key} "{value}"' for key, value in demo.env]
    env_lines.extend(
        (
            'Env XNANO_VHS_DOCS_BG "1"',
            f'Env XNANO_VHS_THEME "{theme_key}"',
        )
    )
    launch_command = f"{LAUNCHER} {demo.name}"
    tape = build_run_tape(
        output=output.relative_to(REPO_ROOT),
        settings=_settings(theme_key),
        launch_command=launch_command,
        steps=demo.steps,
        launch_delay=demo.launch_delay,
        record_delay=demo.record_delay,
        env_lines=env_lines,
    )
    if not demo.auto_quit:
        tape = tape.replace('Type "q"\nSleep 300ms\n', "")
    return tape


def require_vhs() -> str:
    path = shutil.which("vhs")
    if path is None:
        raise SystemExit(
            "vhs not found on PATH.\n"
            "  macOS:  brew install vhs\n"
            "  Linux:  https://github.com/charmbracelet/vhs#installation"
        )
    return path


def run_vhs(vhs: str, tape: Path, *, quiet: bool) -> None:
    command = [vhs, str(tape)]
    if quiet:
        command.append("--quiet")
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def optimize(gif: Path) -> None:
    gifsicle = shutil.which("gifsicle")
    if gifsicle is None:
        return
    subprocess.run(
        [gifsicle, "-O3", "--lossy=30", str(gif), "-o", str(gif)],
        check=True,
    )


def generate(
    demo: Demo,
    theme_key: str,
    *,
    vhs: str,
    dry_run: bool,
    quiet: bool,
) -> None:
    output = OUTPUT_DIR / f"{demo.name}-{theme_key}.gif"
    tape_body = build_tape(demo, output, theme_key)

    if dry_run:
        print(
            f"# {demo.name} [{theme_key}] -> {output.relative_to(REPO_ROOT)}"
        )
        print(tape_body)
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=f"-{demo.name}-{theme_key}.tape",
        prefix="xnano-",
        delete=False,
    ) as tape_file:
        tape_file.write(tape_body)
        tape_path = Path(tape_file.name)

    try:
        label = THEMES[theme_key]
        print(
            f"Recording {demo.name} [{label}] -> {output.relative_to(REPO_ROOT)}"
        )
        run_vhs(vhs, tape_path, quiet=quiet)
        optimize(output)
    finally:
        tape_path.unlink(missing_ok=True)

    if not output.is_file():
        raise SystemExit(f"Expected GIF not created: {output}")

    size_kb = output.stat().st_size / 1024
    print(f"  wrote {output.name} ({size_kb:.0f} KiB)")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--demo",
        choices=list(_DEMO_MAP),
        action="append",
        dest="demos",
        help="Record one or more demos (repeatable)",
    )
    parser.add_argument(
        "--theme",
        choices=list(THEMES),
        help="Record one theme only (default: both)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print tapes without recording",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Pass --quiet to VHS",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    selected = (
        [_DEMO_MAP[name] for name in args.demos] if args.demos else list(DEMOS)
    )
    themes = [args.theme] if args.theme else list(THEMES)
    vhs = require_vhs() if not args.dry_run else ""

    for demo in selected:
        for theme_key in themes:
            generate(
                demo,
                theme_key,
                vhs=vhs,
                dry_run=args.dry_run,
                quiet=args.quiet,
            )

    if not args.dry_run:
        total = len(selected) * len(themes)
        print(
            f"\nDone — {total} GIF(s) in {OUTPUT_DIR.relative_to(REPO_ROOT)}/"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
