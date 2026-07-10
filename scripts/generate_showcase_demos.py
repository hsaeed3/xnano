#!/usr/bin/env python3
"""Generate showcase GIFs for feed, kanban, and agent_chat examples.

Produces color and monotone GIFs for each example and theme (12 total) and
writes them to docs/assets/examples/.

Requirements:
    vhs on PATH  (brew install vhs on macOS)
    xnano importable in the active environment (uv sync from repo root)

Usage:
    uv run python scripts/generate_showcase_demos.py
    uv run python scripts/generate_showcase_demos.py --example feed
    uv run python scripts/generate_showcase_demos.py --theme dark
    uv run python scripts/generate_showcase_demos.py --variant mono
    uv run python scripts/generate_showcase_demos.py --dry-run
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
from typing import Literal, TypeAlias

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"
OUTPUT_DIR = REPO_ROOT / "docs" / "assets" / "examples"
SCRIPTS_DIR = REPO_ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))
from vhs_showcase_themes import (  # noqa: E402
    get_margin_fill,
    get_vhs_monotone_theme,
    get_vhs_theme,
)
from vhs_tape import build_run_tape  # noqa: E402

VariantKey: TypeAlias = Literal["color", "mono"]
"""Showcase recording palette — full color or single-tone foreground."""

THEMES = {
    "dark": "xnano-dark",
    "light": "xnano-light",
}

VARIANTS: tuple[VariantKey, ...] = ("color", "mono")

_BASE_SETTINGS = """
Require python

Set Shell "bash"
Set FontSize {font_size}
Set LineHeight 1.2
Set Width {width}
Set Height {height}
Set Padding {padding}
Set Margin 16
Set MarginFill "{margin_fill}"
Set BorderRadius 10
Set WindowBar Colorful
Set WindowBarSize 28
Set Framerate 30
Set PlaybackSpeed 1.0
Set TypingSpeed 40ms
Set Theme {theme}

Env TERM "xterm-256color"
Env COLORTERM "truecolor"
""".strip()


@dataclass(frozen=True)
class ExampleConfig:
    """Recording settings for one showcase application.

    Dimensions belong to the example instead of a site-wide canvas so compact
    applications do not inherit the empty space needed by dashboards.
    """

    name: str
    steps: tuple[str, ...] = field(default_factory=tuple)
    launch_delay: str = "2s"
    record_delay: str = "2s"
    env: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    width: int = 1600
    height: int = 900
    font_size: int = 13
    padding: int = 20
    script: str | None = None
    """Override the default ``examples/{name}.py`` script path (repo-relative)."""


EXAMPLES: tuple[ExampleConfig, ...] = (
    ExampleConfig(
        name="demo",
        script="beta/core/demo.py",
        height=600,
        launch_delay="2s",
        steps=(
            "Sleep 800ms",
            'Type "2"',
            "Sleep 600ms",
            'Type "3"',
            "Sleep 600ms",
            'Type "4"',
            "Sleep 600ms",
            'Type "1"',
            "Sleep 600ms",
        ),
        record_delay="1s",
    ),
    ExampleConfig(
        name="feed",
        launch_delay="2.5s",
        steps=(
            "Sleep 1.5s",
            "Down@600ms 1",
            "Sleep 1s",
            "Down@600ms 1",
            "Sleep 1s",
            "Down@600ms 1",
            "Sleep 1.5s",
            "Up@600ms 2",
            "Sleep 1s",
        ),
        record_delay="2s",
    ),
    ExampleConfig(
        name="kanban",
        launch_delay="1.5s",
        steps=(
            "Down@400ms 2",
            "Sleep 700ms",
            "Down@400ms 2",
            "Sleep 700ms",
            "Right@500ms 1",
            "Sleep 800ms",
            "Down@400ms 1",
            "Sleep 600ms",
            "Right@500ms 1",
            "Sleep 800ms",
            "Left@500ms 1",
            "Sleep 600ms",
            "Left@500ms 1",
            "Sleep 600ms",
            'Type "p"',
            "Sleep 600ms",
            'Type "n"',
            "Sleep 800ms",
        ),
        record_delay="1.5s",
    ),
    ExampleConfig(
        name="agent_chat",
        width=1120,
        height=640,
        font_size=12,
        padding=14,
        launch_delay="2s",
        steps=(
            "Sleep 1.5s",
            'Type "run tests on the grid module"',
            "Sleep 300ms",
            "Enter",
            "Sleep 5.5s",
            'Type "/"',
            "Sleep 500ms",
            "Down@350ms 1",
            "Sleep 700ms",
            'Type "h"',
            "Sleep 800ms",
            "Backspace",
            "Backspace",
            "Sleep 500ms",
        ),
        record_delay="2s",
    ),
)

_EXAMPLE_MAP: dict[str, ExampleConfig] = {
    example.name: example for example in EXAMPLES
}


def _output_name(example: str, theme_key: str, variant: VariantKey) -> str:
    if variant == "mono":
        return f"{example}-{theme_key}-mono.gif"
    return f"{example}-{theme_key}.gif"


def _base_settings(
    theme_key: str,
    variant: VariantKey,
    example: ExampleConfig,
) -> str:
    theme_json = (
        get_vhs_monotone_theme(theme_key)
        if variant == "mono"
        else get_vhs_theme(theme_key)
    )
    return _BASE_SETTINGS.format(
        theme=theme_json,
        margin_fill=get_margin_fill(theme_key),
        width=example.width,
        height=example.height,
        font_size=example.font_size,
        padding=example.padding,
    )


def _vhs_env_lines(theme_key: str, variant: VariantKey) -> list[str]:
    lines = [f'Env XNANO_VHS_THEME "{theme_key}"']
    if variant == "mono":
        lines.append('Env XNANO_VHS_MONO "1"')
    else:
        # Clear inherited flags so color recordings keep full palette.
        lines.append('Env XNANO_VHS_MONO "0"')
        lines.append('Env XNANO_VHS_DOCS_BG "0"')
    return lines


def build_tape(
    example: ExampleConfig,
    script_path: Path,
    output_path: Path,
    theme_key: str,
    variant: VariantKey,
) -> str:
    output_rel = output_path.relative_to(REPO_ROOT)
    env_lines = [f'Env {key} "{value}"' for key, value in example.env]
    env_lines.extend(_vhs_env_lines(theme_key, variant))
    launch_command = (
        f"uv run python {script_path.relative_to(REPO_ROOT).as_posix()}"
    )
    return build_run_tape(
        output=output_rel,
        settings=_base_settings(theme_key, variant, example),
        launch_command=launch_command,
        steps=example.steps,
        launch_delay=example.launch_delay,
        record_delay=example.record_delay,
        env_lines=env_lines,
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
    example: ExampleConfig,
    theme_key: str,
    variant: VariantKey,
    *,
    vhs: str,
    dry_run: bool,
    quiet: bool,
) -> None:
    script = (
        REPO_ROOT / example.script
        if example.script is not None
        else EXAMPLES_DIR / f"{example.name}.py"
    )
    if not script.exists():
        print(f"  skip {example.name} — {script} not found", file=sys.stderr)
        return

    output = OUTPUT_DIR / _output_name(example.name, theme_key, variant)
    tape_body = build_tape(example, script, output, theme_key, variant)

    if dry_run:
        print(
            f"# {example.name} [{theme_key}/{variant}] "
            f"-> {output.relative_to(REPO_ROOT)}"
        )
        print(tape_body)
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=f"-{example.name}-{theme_key}-{variant}.tape",
        prefix="xnano-",
        delete=False,
    ) as tape_file:
        tape_file.write(tape_body)
        tape_path = Path(tape_file.name)

    try:
        label = f"{example.name} [{THEMES[theme_key]} / {variant}]"
        print(f"Recording {label} -> {output.relative_to(REPO_ROOT)}")
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
        "--variant",
        choices=list(VARIANTS),
        help="Record one palette only (default: color + mono)",
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
    variants = [args.variant] if args.variant else list(VARIANTS)

    vhs = require_vhs() if not args.dry_run else ""

    for example in examples:
        for theme_key in themes:
            for variant in variants:
                generate(
                    example,
                    theme_key,
                    variant,
                    vhs=vhs,
                    dry_run=args.dry_run,
                    quiet=args.quiet,
                )

    if not args.dry_run:
        total = len(examples) * len(themes) * len(variants)
        print(
            f"\nDone — {total} GIF(s) in {OUTPUT_DIR.relative_to(REPO_ROOT)}/"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
