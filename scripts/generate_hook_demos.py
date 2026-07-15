#!/usr/bin/env python3
"""scripts.generate_hook_demos

---

Generate fitted light/dark GIFs for docs/hooks.
"""

from __future__ import annotations

import argparse
import collections.abc
import pathlib
import sys

REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = REPOSITORY_ROOT / "docs" / "assets" / "hooks"
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from vhs_docs import (  # noqa: E402
    THEMES,
    Demo,
    ThemeKey,
    code,
    demo_map,
    record_demo,
    require_vhs,
    run_embedded_code,
)

DEMOS: tuple[Demo, ...] = (
    Demo(
        name="overview",
        code=code("""
            import time
            from xnano import Action, BaseGrid, Field, Terminal, on_action

            OPEN = Action.keyboard("enter")

            class Notice(
                BaseGrid,
                border="rounded",
                title=" Hooks & Actions ",
                padding=1,
            ):
                message: str = Field(
                    default="waiting for OPEN",
                    height=1,
                    align="center",
                    color="slate-400",
                )
                detail: str = Field(
                    default="one trigger · one dispatch path",
                    height=1,
                    align="center",
                    color="violet-400",
                )

                @on_action(OPEN)
                def open_notice(self) -> None:
                    self.message = "OPEN performed"

            notice = Notice()
            terminal = Terminal.offscreen(cols=52, rows=8)
            try:
                terminal.render(notice)
                terminal.perform(OPEN)
                terminal.render(notice)
                print(terminal.get_output_as_ansi())
                time.sleep(3)
            finally:
                terminal.__exit__(None, None, None)
        """),
        launch_delay="800ms",
        steps=("Sleep 2s",),
        record_delay="500ms",
        auto_quit=False,
        content_rows=8,
        content_columns=52,
    ),
)

_DEMO_MAP = demo_map(DEMOS)


def generate_demo(
    demo: Demo,
    theme: ThemeKey,
    *,
    vhs: str,
    dry_run: bool,
    quiet: bool,
) -> None:
    """Record one hook demo for a single theme.

    Args:
        demo: Demo to record.
        theme: Documentation theme to apply.
        vhs: Resolved VHS executable.
        dry_run: Print the tape without recording it.
        quiet: Suppress VHS output.
    """
    output = OUTPUT_DIRECTORY / f"{demo.name}-{theme}.gif"
    launch = (
        "uv run python scripts/generate_hook_demos.py "
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
        tape_label="hook",
    )


def parse_arguments(
    arguments: collections.abc.Sequence[str] | None = None,
) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        arguments: Optional argument sequence.

    Returns:
        Parsed command-line namespace.
    """
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
    return parser.parse_args(arguments)


def run_generator(
    arguments: collections.abc.Sequence[str] | None = None,
) -> int:
    """Generate the selected hook demos.

    Args:
        arguments: Optional command-line arguments.

    Returns:
        Process exit code.
    """
    parsed = parse_arguments(arguments)
    if parsed.run_example:
        run_embedded_code(_DEMO_MAP[parsed.run_example], label="hook")
        return 0

    selected = (
        [_DEMO_MAP[name] for name in parsed.demo]
        if parsed.demo
        else list(DEMOS)
    )
    themes: tuple[ThemeKey, ...] = (
        (parsed.theme,) if parsed.theme else THEMES
    )
    vhs = "" if parsed.dry_run else require_vhs()
    for demo in selected:
        for theme in themes:
            generate_demo(
                demo,
                theme,
                vhs=vhs,
                dry_run=parsed.dry_run,
                quiet=parsed.quiet,
            )

    if not parsed.dry_run:
        total = len(selected) * len(themes)
        relative_output = OUTPUT_DIRECTORY.relative_to(REPOSITORY_ROOT)
        print(f"\nDone — {total} GIF(s) in {relative_output}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_generator())
