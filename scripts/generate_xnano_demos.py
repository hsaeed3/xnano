#!/usr/bin/env python3
"""scripts.generate_xnano_demos

---

Generate GIFs for the built-in ``python -m xnano`` feature tour.

Produces two recordings under ``docs/assets/``:

- ``xnano-title.gif`` — watercolor title splash and centered wordmark
- ``xnano-panels.gif`` — interactive feature panels with navigation

Requirements:
    vhs on PATH  (brew install vhs on macOS)
    xnano importable in the active environment (uv sync from repo root)

Usage:
    uv run python scripts/generate_xnano_demos.py
    uv run python scripts/generate_xnano_demos.py --demo title
    uv run python scripts/generate_xnano_demos.py --demo panels
    uv run python scripts/generate_xnano_demos.py --dry-run
"""

from __future__ import annotations

import argparse
import dataclasses
import pathlib
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT_DIRECTORY = REPOSITORY_ROOT / "docs" / "assets"
SCRIPTS_DIRECTORY = REPOSITORY_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIRECTORY))

from vhs_showcase_themes import (  # noqa: E402
    get_margin_fill,
    get_vhs_theme,
)
from vhs_tape import build_run_tape  # noqa: E402


_THEME = "dark"
"""VHS chrome theme; the tour paints its own truecolor wash."""

_FONT_SIZE = 14
_WIDTH = 1000
_HEIGHT = 560
_PADDING = 12
_MARGIN = 12


@dataclasses.dataclass(frozen=True)
class Demo:
    """A feature-tour recording and its VHS interaction steps."""

    name: str
    output_name: str
    steps: tuple[str, ...]
    launch_delay: str
    record_delay: str
    description: str
    width: int = _WIDTH
    height: int = _HEIGHT
    window_bar: bool = True
    """Whether to draw the macOS-style traffic-light chrome."""
    border_radius: int = 10
    margin: int = _MARGIN
    """Frame margin around the terminal; also draws the border outline."""


DEMOS: tuple[Demo, ...] = (
    Demo(
        name="title",
        output_name="xnano-title.gif",
        description="Watercolor title splash with drifting pigment",
        # Cold ``uv run`` plus the first full-terminal paint needs headroom.
        launch_delay="2.5s",
        # Hold long enough for the wash to drift and the logo to read.
        steps=("Sleep 4s",),
        record_delay="1.5s",
        # 230px yields an even terminal row count at FontSize 14 /
        # LineHeight 1.2, so the wordmark's leftover rows split evenly
        # top and bottom instead of biasing toward one edge.
        height=230,
        window_bar=False,
        border_radius=0,
        margin=0,
    ),
    Demo(
        name="panels",
        output_name="xnano-panels.gif",
        description="Interactive feature panels and effect tour",
        launch_delay="2s",
        steps=(
            "Sleep 1.2s",
            'Type "2"',
            "Sleep 900ms",
            'Type "3"',
            "Sleep 900ms",
            'Type "1"',
            "Sleep 700ms",
            'Type "c"',
            "Sleep 900ms",
            'Type "f"',
            "Sleep 900ms",
            'Type "s"',
            "Sleep 900ms",
            'Type "d"',
            "Sleep 900ms",
            "Right@400ms 1",
            "Sleep 700ms",
            "Left@400ms 1",
            "Sleep 700ms",
        ),
        record_delay="1.2s",
    ),
)

_DEMO_MAP: dict[str, Demo] = {demo.name: demo for demo in DEMOS}


def _base_settings(demo: Demo) -> str:
    """Return the VHS settings block for one feature-tour recording."""
    # VHS has no "no window bar" theme name — omitting the setting is
    # what leaves the chrome off entirely.
    window_bar_lines = (
        "Set WindowBar Colorful\nSet WindowBarSize 28"
        if demo.window_bar
        else ""
    )
    return f'''Require python

Set Shell "bash"
Set FontSize {_FONT_SIZE}
Set LineHeight 1.2
Set Width {demo.width}
Set Height {demo.height}
Set Padding {_PADDING}
Set Margin {demo.margin}
Set MarginFill "{get_margin_fill(_THEME)}"
Set BorderRadius {demo.border_radius}
{window_bar_lines}
Set Framerate 30
Set PlaybackSpeed 1.0
Set TypingSpeed 40ms
Set Theme {get_vhs_theme(_THEME)}

Env TERM "xterm-256color"
Env COLORTERM "truecolor"'''


def get_tape(demo: Demo, output: pathlib.Path) -> str:
    """Build the VHS tape for one feature-tour recording."""
    return build_run_tape(
        output=output.relative_to(REPOSITORY_ROOT),
        settings=_base_settings(demo),
        launch_command=(
            "uv run python scripts/generate_xnano_demos.py "
            f"--run-example {demo.name}"
        ),
        steps=demo.steps,
        launch_delay=demo.launch_delay,
        record_delay=demo.record_delay,
        env_lines=(),
    )


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


def optimize(gif: pathlib.Path) -> None:
    """Lossy-optimize a GIF when gifsicle is available."""
    gifsicle = shutil.which("gifsicle")
    if gifsicle is None:
        return
    subprocess.run(
        [gifsicle, "-O3", "--lossy=30", str(gif), "-o", str(gif)],
        check=True,
    )


def run_example(name: str) -> None:
    """Launch one feature-tour stage for VHS to record."""
    if name == "title":
        from xnano.core.demo.title import TitleSplash
        from xnano.terminal import Terminal

        Terminal(title="xnano · title", tick_interval=16).run(TitleSplash())
        return

    if name == "panels":
        from xnano.core.demo.panels import XnanoDemo
        from xnano.terminal import Terminal

        Terminal(title="xnano · feature tour", tick_interval=16).run(
            XnanoDemo()
        )
        return

    raise SystemExit(f"Unknown example: {name!r}")


def generate_demo(
    demo: Demo,
    *,
    vhs: str,
    dry_run: bool,
    quiet: bool,
) -> None:
    """Record one feature-tour GIF into ``docs/assets``."""
    output = OUTPUT_DIRECTORY / demo.output_name
    tape_body = get_tape(demo, output)

    if dry_run:
        print(f"# {demo.name} -> {output.relative_to(REPOSITORY_ROOT)}")
        print(tape_body)
        return

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=f"-xnano-{demo.name}.tape",
        prefix="xnano-",
        delete=False,
    ) as tape_file:
        tape_file.write(tape_body)
        tape_path = pathlib.Path(tape_file.name)

    try:
        print(
            f"Recording {demo.name} ({demo.description}) "
            f"-> {output.relative_to(REPOSITORY_ROOT)}"
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
    """Generate feature-tour GIFs or run one stage for VHS."""
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
