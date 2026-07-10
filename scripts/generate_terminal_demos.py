#!/usr/bin/env python3
"""scripts.generate_terminal_demos

---

Generate fitted terminal documentation GIFs with VHS.
"""

from __future__ import annotations

import argparse
import dataclasses
import pathlib
import shutil
import subprocess
import sys
import tempfile
import textwrap
from collections.abc import Sequence


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = REPOSITORY_ROOT / "docs" / "assets" / "terminal"
SCRIPTS_DIRECTORY = REPOSITORY_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIRECTORY))

from vhs_showcase_themes import (  # noqa: E402
    get_margin_fill,
    get_vhs_theme,
)
from vhs_tape import build_run_tape  # noqa: E402


THEMES = ("dark", "light")


@dataclasses.dataclass(frozen=True)
class Demo:
    """A runnable documentation example and its fitted recording settings."""

    name: str
    code: str
    width: int
    height: int
    steps: tuple[str, ...] = ()
    auto_quit: bool = False


def get_code(source: str) -> str:
    """Return normalized source for a generated example."""
    return textwrap.dedent(source).strip() + "\n"


DEMOS = (
    Demo(
        "render-once",
        get_code("""
            import time
            from xnano.components.text import Text
            from xnano.terminal import Terminal

            Terminal().render(
                Text("Build complete", color="emerald-400"),
                Text("12 tests passed", color="slate-400"),
                gap=1,
            )
            time.sleep(3)
        """),
        680,
        270,
    ),
    Demo(
        "run-interface",
        get_code("""
            from xnano.fields import Field
            from xnano.grid import Grid
            from xnano.hooks import on_keyboard
            from xnano.terminal import Terminal

            class App(Grid):
                message: str = Field(default="Press q to leave")

                @on_keyboard("q")
                def close_app(self, context) -> None:
                    context.terminal.request_exit()

            Terminal(width=38, height=4).run(App())
        """),
        700,
        300,
        auto_quit=True,
    ),
    Demo(
        "sized-inline",
        get_code("""
            import time
            from xnano.terminal import Terminal

            Terminal(width=36, height=3).render(
                "A compact result",
                border="rounded",
                padding=(0, 1),
            )
            time.sleep(3)
        """),
        700,
        290,
    ),
    Demo(
        "context-session",
        get_code("""
            from xnano.fields import Field
            from xnano.grid import Grid
            from xnano.hooks import on_keyboard
            from xnano.terminal import Terminal

            class App(Grid):
                message: str = Field(default="Tasks · press q to leave")

                @on_keyboard("q")
                def close_app(self, context) -> None:
                    context.terminal.request_exit()

            with Terminal(title="Tasks", mouse_events=True, height=4) as terminal:
                terminal.run(App())
        """),
        720,
        300,
        auto_quit=True,
    ),
    Demo(
        "device-options",
        get_code("""
            from xnano.fields import Field
            from xnano.grid import Grid
            from xnano.hooks import on_keyboard
            from xnano.terminal import Terminal

            class App(Grid):
                message: str = Field(default="Device modes are active · press q")

                @on_keyboard("q")
                def close_app(self, context) -> None:
                    context.terminal.request_exit()

            with Terminal(
                title="Inspector",
                mouse_events=True,
                bracketed_paste=True,
                synchronized_updates=True,
                height=4,
            ) as terminal:
                terminal.run(App())
        """),
        760,
        300,
        auto_quit=True,
    ),
    Demo(
        "device-live-title",
        get_code("""
            from xnano.fields import Field
            from xnano.grid import Grid
            from xnano.hooks import on_keyboard
            from xnano.terminal import Terminal

            class App(Grid):
                message: str = Field(default="Press t to update the window title")

                @on_keyboard("t")
                def update_title(self, context) -> None:
                    context.device.set_title("Tasks · updated")
                    self.message = "Window title updated"

                @on_keyboard("q")
                def close_app(self, context) -> None:
                    context.terminal.request_exit()

            Terminal(title="Tasks", height=4).run(App())
        """),
        760,
        300,
        ('Type "t"', "Sleep 1s"),
        True,
    ),
    Demo(
        "device-clear-line",
        get_code("""
            from xnano.fields import Field
            from xnano.grid import Grid
            from xnano.hooks import on_keyboard
            from xnano.terminal import Terminal

            class App(Grid):
                message: str = Field(default="Press c to clear the current line")

                @on_keyboard("c")
                def clear_current_line(self, context) -> None:
                    context.device.clear("current_line")
                    context.device.scroll_up(1)

                @on_keyboard("q")
                def close_app(self, context) -> None:
                    context.terminal.request_exit()

            Terminal(height=4).run(App())
        """),
        760,
        300,
        ('Type "c"', "Sleep 1s"),
        True,
    ),
    Demo(
        "cursor-style",
        get_code("""
            from xnano.fields import Field
            from xnano.grid import Grid
            from xnano.hooks import on_keyboard
            from xnano.terminal import Terminal

            class App(Grid):
                message: str = Field(default="Press i for a steady bar cursor")

                @on_keyboard("i")
                def show_insert_cursor(self, context) -> None:
                    context.cursor.visible = True
                    context.cursor.style = "steady_bar"

                @on_keyboard("q")
                def close_app(self, context) -> None:
                    context.terminal.request_exit()

            Terminal(height=4).run(App())
        """),
        760,
        300,
        ('Type "i"', "Sleep 1s"),
        True,
    ),
    Demo(
        "cursor-position",
        get_code("""
            from xnano.fields import Field
            from xnano.grid import Grid
            from xnano.hooks import on_keyboard
            from xnano.terminal import Terminal

            class App(Grid):
                message: str = Field(default="Press p to preview a cursor move")

                @on_keyboard("p")
                def preview_cursor_position(self, context) -> None:
                    context.cursor.save_position()
                    context.cursor.move_to(4, 2)
                    context.cursor.restore_position()

                @on_keyboard("q")
                def close_app(self, context) -> None:
                    context.terminal.request_exit()

            Terminal(height=4).run(App())
        """),
        760,
        300,
        ('Type "p"', "Sleep 1s"),
        True,
    ),
)


def get_tape(demo: Demo, theme: str, output: pathlib.Path) -> str:
    """Build the VHS tape for one demo and theme."""
    settings = f'''Require python
Set Shell "bash"
Set FontSize 16
Set LineHeight 1.2
Set Width {demo.width}
Set Height {demo.height}
Set Padding 22
Set Margin 20
Set MarginFill "{get_margin_fill(theme)}"
Set BorderRadius 10
Set WindowBar Colorful
Set WindowBarSize 28
Set Framerate 30
Set Theme {get_vhs_theme(theme)}
Env TERM "xterm-256color"
Env COLORTERM "truecolor"'''
    tape = build_run_tape(
        output=output.relative_to(REPOSITORY_ROOT),
        settings=settings,
        launch_command=(
            f"uv run python scripts/generate_terminal_demos.py "
            f"--run-example {demo.name}"
        ),
        steps=demo.steps,
        launch_delay="800ms",
        record_delay="1s",
        env_lines=(),
    )
    if not demo.auto_quit:
        return tape.replace('Type "q"\nSleep 300ms\n', "")
    return tape


def generate_demo(demo: Demo, theme: str, vhs: str) -> None:
    """Record one demo and optimize its GIF when gifsicle is available."""
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIRECTORY / f"{demo.name}-{theme}.gif"
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".tape", delete=False
    ) as file:
        file.write(get_tape(demo, theme, output))
        tape = pathlib.Path(file.name)
    try:
        subprocess.run(
            [vhs, str(tape), "--quiet"], cwd=REPOSITORY_ROOT, check=True
        )
    finally:
        tape.unlink(missing_ok=True)
    gifsicle = shutil.which("gifsicle")
    if gifsicle is not None:
        subprocess.run(
            [gifsicle, "-O3", "--lossy=30", str(output), "-o", str(output)],
            check=True,
        )
    print(f"wrote {output.relative_to(REPOSITORY_ROOT)}")


def main(arguments: Sequence[str] | None = None) -> int:
    """Generate selected assets or execute one embedded example."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="append")
    parser.add_argument("--theme", choices=THEMES)
    parser.add_argument("--run-example")
    parsed = parser.parse_args(arguments)
    demo_map = {demo.name: demo for demo in DEMOS}
    if parsed.run_example:
        code = demo_map[parsed.run_example].code
        exec(
            compile(code, parsed.run_example, "exec"), {"__name__": "__main__"}
        )
        return 0
    selected = (
        [demo_map[name] for name in parsed.demo] if parsed.demo else DEMOS
    )
    vhs = shutil.which("vhs")
    if vhs is None:
        raise SystemExit(
            "vhs is required to generate terminal documentation assets"
        )
    for demo in selected:
        for theme in [parsed.theme] if parsed.theme else THEMES:
            generate_demo(demo, theme, vhs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
