#!/usr/bin/env python3
"""Generate autoplay demo GIFs for xnano examples.

Records each script under ``examples/`` with the `VHS`_ terminal recorder and
writes GIFs to ``docs/assets/demos/`` for embedding in the docs landing page.

.. _VHS: https://github.com/charmbracelet/vhs

Requirements
------------
- `vhs` on ``PATH`` (``brew install vhs`` on macOS)
- `ffmpeg` on ``PATH`` (pulled in automatically by Homebrew with ``vhs``)
- ``xnano`` importable in the active environment (``uv sync`` from repo root)

Usage
-----
::

    uv run python scripts/generate_demo_gifs.py
    uv run python scripts/generate_demo_gifs.py --demo dashboard
    uv run python scripts/generate_demo_gifs.py --dry-run
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

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "docs" / "assets" / "demos"

TERMINAL_SETTINGS = """
Require python

Set Shell "bash"
Set FontSize 16
Set Width 1200
Set Height 700
Set Theme "Catppuccin Mocha"
Set Padding 20
Set MarginFill "#1e1e2e"
Set Framerate 30
Set PlaybackSpeed 1.0

Env TERM "xterm-256color"
Env COLORTERM "truecolor"
""".strip()


@dataclass(frozen=True)
class Demo:
    name: str
    script: str
    steps: tuple[str, ...] = field(default_factory=tuple)
    launch_delay: str = "1s"


DEMOS: tuple[Demo, ...] = (
    Demo(
        name="dashboard",
        script="examples/dashboard.py",
        launch_delay="2s",
        steps=(
            "Down@300ms 2",
            "Sleep 1s",
            "Up@300ms 1",
            "Sleep 2s",
        ),
    ),
    Demo(
        name="effects_demo",
        script="examples/effects_demo.py",
        launch_delay="2s",
        steps=(
            "Sleep 1.5s",
            'Type "c"',
            "Sleep 2s",
            'Type "f"',
            "Sleep 2s",
            'Type "d"',
            "Sleep 2s",
            'Type "s"',
            "Sleep 1.5s",
        ),
    ),
    Demo(
        name="tabs_nav",
        script="examples/tabs_nav.py",
        launch_delay="1.5s",
        steps=(
            "Right@400ms 2",
            "Sleep 1s",
            "Left@400ms 1",
            "Sleep 500ms",
            "Down@250ms 3",
            "Sleep 1s",
            "Right@400ms 1",
            "Sleep 500ms",
            "Down@250ms 2",
            "Sleep 1s",
            "Right@400ms 1",
            "Sleep 1.5s",
        ),
    ),
    Demo(
        name="agent_chat",
        script="examples/agent_chat.py",
        launch_delay="1.5s",
        steps=(
            'Type@40ms "run tests"',
            "Enter",
            "Sleep 5s",
            'Type@60ms "/"',
            "Sleep 800ms",
            "Down@150ms 2",
            "Tab",
            "Sleep 1s",
            "Backspace@80ms 4",
            'Type@40ms "hello"',
            "Enter",
            "Sleep 3s",
        ),
    ),
)


def build_tape(demo: Demo, output: Path) -> str:
    lines = [
        f"Output {output.as_posix()}",
        TERMINAL_SETTINGS,
        "Hide",
        f'Type "python {demo.script}"',
        "Enter",
        f"Sleep {demo.launch_delay}",
        "Show",
        *demo.steps,
        "Hide",
        "Ctrl+C",
        "Sleep 300ms",
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
    output = OUTPUT_DIR / f"{demo.name}.gif"
    tape_body = build_tape(demo, output.relative_to(REPO_ROOT))

    if dry_run:
        print(f"# {demo.name} -> {output.relative_to(REPO_ROOT)}")
        print(tape_body)
        return output

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=f"-{demo.name}.tape",
        prefix="xnano-",
        delete=False,
    ) as tape_file:
        tape_file.write(tape_body)
        tape_path = Path(tape_file.name)

    try:
        print(f"Recording {demo.name} -> {output.relative_to(REPO_ROOT)}")
        run_vhs(vhs_path, tape_path, quiet=quiet)
        optimize_gif(output, gifsicle=gifsicle_path)
    finally:
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
        help="Record a single demo instead of all examples",
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
        [demo for demo in DEMOS if demo.name == args.demo]
        if args.demo
        else list(DEMOS)
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
