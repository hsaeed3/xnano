#!/usr/bin/env python3
"""scripts.generate_concept_demos

---

Generate fitted light/dark GIFs for docs/core-concepts.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = REPOSITORY_ROOT / "docs" / "assets" / "concepts"
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
        name="hello_render",
        code=code("""
            import time
            from xnano import render
            from xnano.components.text import Text

            render(
                Text("Hello from xnano!", color="violet", modifiers=["bold"]),
                Text(
                    "Render returns immediately — no event loop needed.",
                    color="slate-400",
                ),
            )
            time.sleep(3)
        """),
        launch_delay="800ms",
        steps=("Sleep 2s",),
        record_delay="500ms",
        auto_quit=False,
        content_rows=3,
        content_columns=56,
    ),
    Demo(
        name="grid_basic",
        code=code("""
            import time
            from xnano import BaseGrid, Field, Terminal

            class App(BaseGrid, direction="vertical"):
                # Pin field heights so borders wrap content instead of
                # expanding to fill the terminal (looks like a lone top edge).
                title: str = Field(
                    default="My App", border="rounded", height=1
                )
                body: str = Field(default="", height=1)
                name: str = Field(default="Hammad", state=True)

                def __post_init__(self):
                    self.body = f"Hello, {self.name}!"

            # ~3 rows for bordered title + 1 body + slack
            Terminal(height=6).render(App())
            time.sleep(3)
        """),
        launch_delay="800ms",
        steps=("Sleep 2s",),
        record_delay="500ms",
        auto_quit=False,
        content_rows=6,
        gap_rows=2,
    ),
    Demo(
        name="grid_settings",
        code=code("""
            import time
            from xnano import BaseGrid, Field, Terminal

            class Dashboard(
                BaseGrid,
                direction="horizontal",
                gap=1,
                border="rounded",
                title=" Dashboard ",
            ):
                left: str = Field(default="Left", width="1fr", height=1)
                right: str = Field(default="Right", width="1fr", height=1)

            # Outer border + title row + content + slack
            Terminal(height=6).render(Dashboard())
            time.sleep(3)
        """),
        launch_delay="800ms",
        steps=("Sleep 2s",),
        record_delay="500ms",
        auto_quit=False,
        content_rows=6,
        gap_rows=2,
    ),
    Demo(
        name="fields_card",
        code=code("""
            import time
            from xnano import BaseGrid, Field, Terminal

            class Card(BaseGrid, direction="vertical"):
                heading: str = Field(
                    default="Reminder",
                    color="violet",
                    border="rounded",
                    width="fit",
                    height=1,
                )
                body: str = Field(default="Water the plants.", height=1)

            Terminal(height=6).render(Card())
            time.sleep(3)
        """),
        launch_delay="800ms",
        steps=("Sleep 2s",),
        record_delay="500ms",
        auto_quit=False,
        content_rows=6,
        gap_rows=2,
    ),
    Demo(
        name="hooks_keyboard",
        code=code("""
            from xnano import BaseGrid, Field, Terminal
            from xnano.events import on_keyboard

            class Counter(BaseGrid, direction="vertical", gap=1):
                label: str = Field(default="Count: 0", height=1)
                hint: str = Field(
                    default="↑ / ↓ to count",
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
        content_rows=7,
        content_columns=36,
    ),
    Demo(
        name="hooks_tick",
        code=code("""
            import time
            from xnano import BaseGrid, Field, Terminal
            from xnano.events import on_tick

            class Clock(BaseGrid, direction="vertical"):
                display: str = Field(
                    default="",
                    height=3,
                    border="rounded",
                    title=" Time ",
                )

                @on_tick(1000)
                def update(self) -> None:
                    self.display = time.strftime("  %H:%M:%S")

            Terminal(tick_interval=1000).run(Clock())
        """),
        steps=("Sleep 3.5s",),
        record_delay="500ms",
        content_rows=7,
        content_columns=28,
    ),
    Demo(
        name="actions_binding",
        code=code("""
            from xnano import Action, BaseGrid, Field, Terminal, on
            from xnano.events import on_keyboard

            SAVE = Action.keyboard("ctrl+s")

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

                @on_keyboard("e")
                def edit(self) -> None:
                    self.dirty = True
                    self.status = "unsaved"

            Terminal().run(Editor())
        """),
        steps=(
            "Sleep 500ms",
            "Ctrl+S",
            "Sleep 700ms",
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
        name="context_state",
        code=code("""
            import dataclasses
            from xnano import BaseGrid, Context, Field, Terminal
            from xnano.events import on_keyboard

            @dataclasses.dataclass
            class AppState:
                count: int = 0

            class Counter(BaseGrid, direction="vertical", gap=1):
                label: str = Field(default="Count: 0", height=1)
                hint: str = Field(
                    default="↑ / ↓ · shared state",
                    height=1,
                    color="slate-500",
                )

                @on_keyboard("up")
                def inc(self, ctx: Context[AppState]) -> None:
                    state = ctx.get_state()
                    state.count += 1
                    self.label = f"Count: {state.count}"

                @on_keyboard("down")
                def dec(self, ctx: Context[AppState]) -> None:
                    state = ctx.get_state()
                    state.count -= 1
                    self.label = f"Count: {state.count}"

            Terminal(state=AppState()).run(Counter())
        """),
        steps=(
            "Up@300ms 3",
            "Sleep 400ms",
            "Down@300ms 1",
            "Sleep 600ms",
        ),
        record_delay="500ms",
        content_rows=6,
        content_columns=40,
    ),
    Demo(
        name="terminal_session",
        code=code("""
            import time
            from xnano.tui import Terminal
            from xnano.components.text import Text

            Terminal().render(
                Text(
                    "Build complete.",
                    color="emerald-400",
                    modifiers=["bold"],
                ),
                Text("12 tests passed.", color="slate-400"),
            )
            time.sleep(3)
        """),
        launch_delay="800ms",
        steps=("Sleep 2s",),
        record_delay="500ms",
        auto_quit=False,
        content_rows=3,
        content_columns=40,
    ),
    Demo(
        name="styled_field",
        code=code("""
            import time
            from xnano import BaseGrid, Field, Terminal

            class Card(BaseGrid, direction="vertical", gap=1):
                heading: str = Field(
                    default="Styled field",
                    color="violet-400",
                    border="rounded",
                    modifiers=["bold", "italic"],
                    width="fit",
                    height=1,
                )
                body: str = Field(
                    default="Borders and modifiers on a field slot.",
                    color="slate-400",
                    height=1,
                )

            Terminal(height=6).render(Card())
            time.sleep(3)
        """),
        launch_delay="800ms",
        steps=("Sleep 2s",),
        record_delay="500ms",
        auto_quit=False,
        content_rows=6,
        gap_rows=2,
    ),
    Demo(
        name="styled_tailwind",
        code=code("""
            import time
            from xnano import BaseGrid, Field, Terminal

            class Card(BaseGrid, direction="vertical"):
                body: str = Field(
                    default="  Tailwind utilities on a field  ",
                    class_name="text-violet-400 bg-slate-900 p-2 rounded-lg",
                    height=3,
                )

            Terminal(height=5).render(Card())
            time.sleep(3)
        """),
        launch_delay="800ms",
        steps=("Sleep 2s",),
        record_delay="500ms",
        auto_quit=False,
        content_rows=5,
        gap_rows=2,
    ),
    Demo(
        name="component_progress",
        code=code("""
            import time
            from xnano import BaseGrid, Field, Terminal
            from xnano.components.progress import Progress

            class Download(BaseGrid, direction="vertical", gap=1):
                status: str = Field(default="Downloading…", height=1)
                bar: Progress = Field(
                    default_factory=lambda: Progress(value=0.4),
                    height=1,
                )

            Terminal(height=4).render(Download())
            time.sleep(3)
        """),
        launch_delay="800ms",
        steps=("Sleep 2s",),
        record_delay="500ms",
        auto_quit=False,
        content_rows=4,
        content_columns=48,
    ),
    Demo(
        name="device_title",
        code=code("""
            import dataclasses
            from xnano import BaseGrid, Context, Field, Terminal
            from xnano.events import on_keyboard

            @dataclasses.dataclass
            class AppState:
                unread: int = 0

            class Inbox(BaseGrid, direction="vertical", gap=1):
                body: str = Field(default="  inbox · 0 unread", height=1)
                hint: str = Field(
                    default="  ↑ add · title updates",
                    height=1,
                    color="slate-500",
                )

                @on_keyboard("up")
                def bump(self, ctx: Context[AppState]) -> None:
                    state = ctx.get_state()
                    state.unread += 1
                    self.body = f"  inbox · {state.unread} unread"
                    ctx.device.title = f"({state.unread}) inbox"

            Terminal(state=AppState()).run(Inbox())
        """),
        steps=(
            "Up@350ms 3",
            "Sleep 700ms",
        ),
        record_delay="500ms",
        content_rows=5,
        content_columns=40,
    ),
    Demo(
        name="cli_root",
        code=code("""
            import time
            from xnano.cli import Command

            cli = Command(name="tool", description="A small utility")

            @cli
            @Command.option("--name", default="world", help="Who to greet")
            def greet(name: str = "world") -> None:
                print(f"hello, {name}")

            print("$ tool --name hammad")
            cli.run(["--name", "hammad"])
            time.sleep(3)
        """),
        launch_delay="600ms",
        steps=("Sleep 2s",),
        record_delay="500ms",
        auto_quit=False,
        content_rows=4,
    ),
    Demo(
        name="cli_flags",
        code=code("""
            import time
            from xnano.cli import Command

            cli = Command(name="build", description="Compile the project")

            @cli
            @Command.option("--count", default=1, help="How many times")
            @Command.option(
                ["--verbose", "-v"], is_flag=True, help="Verbose output"
            )
            def main(count: int = 1, verbose: bool = False) -> None:
                mode = "verbose" if verbose else "quiet"
                print(f"building ×{count} ({mode})")

            print("$ build --count 3 -v")
            cli.run(["--count", "3", "-v"])
            time.sleep(3)
        """),
        launch_delay="600ms",
        steps=("Sleep 2s",),
        record_delay="500ms",
        auto_quit=False,
        content_rows=4,
    ),
    Demo(
        name="cli_subcommands",
        code=code("""
            import time
            from xnano.cli import Command

            cli = Command(name="ship", description="Release helpers")

            @cli.command(name="greet", description="Print a greeting")
            @Command.option("--name", default="world", help="Who to greet")
            def greet(name: str = "world") -> None:
                print(f"hello, {name}")

            @cli.command(name="bump")
            @Command.option(
                "--major", is_flag=True, help="Bump the major version"
            )
            def bump(major: bool = False) -> None:
                kind = "major" if major else "patch"
                print(f"bumping {kind}")

            print("$ ship greet --name crew")
            cli.run(["greet", "--name", "crew"])
            print()
            print("$ ship bump --major")
            cli.run(["bump", "--major"])
            time.sleep(3)
        """),
        launch_delay="600ms",
        steps=("Sleep 2s",),
        record_delay="500ms",
        auto_quit=False,
        content_rows=8,
    ),
    Demo(
        name="cli_help",
        code=code("""
            import time
            from xnano.cli import Command

            cli = Command(name="tool", description="A small utility")

            @cli
            @Command.option("--name", default="world", help="Who to greet")
            def greet(name: str = "world") -> None:
                print(f"hello, {name}")

            print("$ tool --help")
            print()
            print(cli.get_help())
            time.sleep(3)
        """),
        launch_delay="600ms",
        steps=("Sleep 2s",),
        record_delay="500ms",
        auto_quit=False,
        content_rows=10,
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
    """Record one concept demo for a single theme."""
    output = OUTPUT_DIRECTORY / f"{demo.name}-{theme}.gif"
    launch = (
        "uv run python scripts/generate_concept_demos.py "
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
        tape_label="concept",
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
        run_embedded_code(_DEMO_MAP[args.run_example], label="concept")
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
