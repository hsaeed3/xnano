#!/usr/bin/env python3
"""Generate example GIFs for all xnano example scripts.

Produces one GIF per example per theme (docs dark + light palettes) and
writes them to docs/assets/examples/.

Requirements:
    vhs on PATH  (brew install vhs on macOS)
    xnano importable in the active environment (uv sync from repo root)

Usage:
    uv run python scripts/generate_example_screenshots.py
    uv run python scripts/generate_example_screenshots.py --example dashboard
    uv run python scripts/generate_example_screenshots.py --theme dark
    uv run python scripts/generate_example_screenshots.py --dry-run
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
EXAMPLES_DIR = REPO_ROOT / "examples"
OUTPUT_DIR = REPO_ROOT / "docs" / "assets" / "examples"
SCRIPTS_DIR = REPO_ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))
from vhs_doc_themes import get_margin_fill, get_theme_name  # noqa: E402
from vhs_tape import build_run_tape  # noqa: E402

THEMES = {
    "dark": "GruvboxDark",
    "light": "AtomOneLight",
}

_BASE_SETTINGS = """
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
Set Theme "{theme}"

Env TERM "xterm-256color"
Env COLORTERM "truecolor"
""".strip()


@dataclass(frozen=True)
class ExampleConfig:
    name: str
    """Stem of the example file, e.g. ``"dashboard"``."""
    steps: tuple[str, ...] = field(default_factory=tuple)
    """VHS interaction steps inserted after the launch delay."""
    launch_delay: str = "2s"
    """How long to wait after starting the script before showing the terminal."""
    record_delay: str = "2s"
    """Additional sleep after interactions before stopping the recording."""
    env: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    """Extra ``Env KEY "VALUE"`` lines added to the tape."""


EXAMPLES: tuple[ExampleConfig, ...] = (
    ExampleConfig(
        name="dashboard",
        launch_delay="2.5s",
        steps=(
            "Down@400ms 2",
            "Sleep 1s",
            "Up@400ms 1",
            "Sleep 1s",
            "Down@400ms 1",
        ),
        record_delay="2s",
    ),
    ExampleConfig(
        name="effects_demo",
        launch_delay="2s",
        steps=(
            "Sleep 1s",
            'Type "c"',
            "Sleep 1.5s",
            'Type "f"',
            "Sleep 1.5s",
            'Type "d"',
            "Sleep 1.5s",
            'Type "s"',
        ),
        record_delay="1.5s",
    ),
    ExampleConfig(
        name="tabs_nav",
        launch_delay="1.5s",
        steps=(
            "Right@500ms 2",
            "Sleep 800ms",
            "Left@500ms 1",
            "Sleep 800ms",
            "Right@500ms 1",
        ),
        record_delay="1.5s",
    ),
    ExampleConfig(
        name="agent_chat",
        launch_delay="1.5s",
        steps=(
            'Type@50ms "run tests"',
            "Enter",
            "Sleep 4s",
            'Type@60ms "/"',
            "Sleep 600ms",
            "Down@200ms 2",
            "Tab",
            "Sleep 800ms",
        ),
        record_delay="2s",
    ),
)

_EXAMPLE_MAP: dict[str, ExampleConfig] = {e.name: e for e in EXAMPLES}


def _base_settings(theme_key: str) -> str:
    return _BASE_SETTINGS.format(
        theme=get_theme_name(theme_key),
        margin_fill=get_margin_fill(theme_key),
    )


def build_tape(
    example: ExampleConfig,
    script_path: Path,
    output_path: Path,
    theme_key: str,
) -> str:
    output_rel = output_path.relative_to(REPO_ROOT)
    env_lines = [f'Env {key} "{value}"' for key, value in example.env]
    return build_run_tape(
        output=output_rel,
        settings=_base_settings(theme_key),
        launch_command=f"scripts/vhs-example {example.name}",
        steps=example.steps,
        launch_delay=example.launch_delay,
        record_delay=example.record_delay,
        env_lines=env_lines,
        quit_key="q",
    )


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
    cmd = [vhs, str(tape)]
    if quiet:
        cmd.append("--quiet")
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def optimize(gif: Path) -> None:
    gifsicle = shutil.which("gifsicle")
    if gifsicle is None:
        return
    subprocess.run(
        [gifsicle, "-O3", "--lossy=30", str(gif), "-o", str(gif)],
        check=True,
    )


def generate(
    example: ExampleConfig,
    theme_key: str,
    *,
    vhs: str,
    dry_run: bool,
    quiet: bool,
) -> None:
    script = EXAMPLES_DIR / f"{example.name}.py"
    if not script.exists():
        print(f"  skip {example.name} — {script} not found", file=sys.stderr)
        return

    output = OUTPUT_DIR / f"{example.name}-{theme_key}.gif"
    tape_body = build_tape(example, script, output, theme_key)

    if dry_run:
        print(
            f"# {example.name} [{theme_key}] -> {output.relative_to(REPO_ROOT)}"
        )
        print(tape_body)
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=f"-{example.name}-{theme_key}.tape",
        prefix="xnano-",
        delete=False,
    ) as f:
        f.write(tape_body)
        tape_path = Path(f.name)

    try:
        label = f"{example.name} [{THEMES[theme_key]}]"
        print(f"Recording {label} -> {output.relative_to(REPO_ROOT)}")
        run_vhs(vhs, tape_path, quiet=quiet)
        optimize(output)
    finally:
        tape_path.unlink(missing_ok=True)

    if not output.is_file():
        raise SystemExit(f"Expected GIF not created: {output}")

    kb = output.stat().st_size / 1024
    print(f"  wrote {output.name} ({kb:.0f} KiB)")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--example",
        choices=list(_EXAMPLE_MAP),
        help="Record a single example",
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
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    examples = [_EXAMPLE_MAP[args.example]] if args.example else list(EXAMPLES)
    themes = [args.theme] if args.theme else list(THEMES)

    vhs = require_vhs() if not args.dry_run else ""

    for example in examples:
        for theme_key in themes:
            generate(
                example,
                theme_key,
                vhs=vhs,
                dry_run=args.dry_run,
                quiet=args.quiet,
            )

    if not args.dry_run:
        total = len(examples) * len(themes)
        print(
            f"\nDone — {total} GIF(s) in {OUTPUT_DIR.relative_to(REPO_ROOT)}/"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
