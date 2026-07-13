#!/usr/bin/env python3
"""scripts.generate_showcase_demos

---

Generate color and monotone GIFs for full-app showcase examples.

Records ``examples/feed.py``, ``examples/kanban.py``, and
``examples/agent_chat.py`` into ``docs/assets/examples/`` as:

- ``{name}-{theme}.gif``
- ``{name}-{theme}-mono.gif``
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, TypeAlias

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIRECTORY = REPOSITORY_ROOT / "examples"
OUTPUT_DIRECTORY = REPOSITORY_ROOT / "docs" / "assets" / "examples"
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from vhs_docs import (  # noqa: E402
    THEMES,
    Demo,
    ThemeKey,
    purge_legacy_demo_artifacts,
    record_demo,
    require_vhs,
)

VariantKey: TypeAlias = Literal["color", "mono"]
"""Showcase palette — full color or single-tone foreground."""

VARIANTS: tuple[VariantKey, ...] = ("color", "mono")


@dataclasses.dataclass(frozen=True)
class ShowcaseExample:
    """Recording settings for one showcase application script."""

    name: str
    """Example stem matching ``examples/{name}.py``."""
    steps: tuple[str, ...] = dataclasses.field(default_factory=tuple)
    """VHS interaction steps after the launch delay."""
    launch_delay: str = "2s"
    """Wait after starting the script before showing the terminal."""
    record_delay: str = "2s"
    """Hold after interactions before stopping."""
    width: int = 1400
    """Recording pixel width."""
    content_rows: int = 32
    """Approximate terminal rows for proportional height."""
    font_size: int = 13
    """VHS font size for denser full-app frames."""
    padding: int = 16
    """Space between terminal content and recording edge."""
    gap_rows: int = 4
    """Spare vertical rows so chrome is not clipped."""
    script: str | None = None
    """Optional repo-relative script path override."""


SHOWCASES: tuple[ShowcaseExample, ...] = (
    ShowcaseExample(
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
        width=1500,
        content_rows=34,
    ),
    ShowcaseExample(
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
        width=1500,
        content_rows=32,
    ),
    ShowcaseExample(
        name="agent_chat",
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
        width=1200,
        content_rows=28,
        font_size=12,
        padding=14,
    ),
)

_SHOWCASE_MAP = {example.name: example for example in SHOWCASES}


def _as_demo(example: ShowcaseExample, *, mono: bool) -> Demo:
    """Adapt a showcase config into a ``vhs_docs.Demo``."""
    env: tuple[tuple[str, str], ...]
    if mono:
        env = (("XNANO_VHS_MONO", "1"),)
    else:
        env = (
            ("XNANO_VHS_MONO", "0"),
            ("XNANO_VHS_DOCS_BG", "0"),
        )
    return Demo(
        name=example.name,
        code="",
        steps=example.steps,
        launch_delay=example.launch_delay,
        record_delay=example.record_delay,
        env=env,
        auto_quit=True,
        content_rows=example.content_rows,
        width=example.width,
        font_size=example.font_size,
        padding=example.padding,
        gap_rows=example.gap_rows,
        margin=16,
        border_radius=10,
    )


def _script_path(example: ShowcaseExample) -> Path:
    """Resolve the example script path."""
    if example.script is not None:
        return REPOSITORY_ROOT / example.script
    return EXAMPLES_DIRECTORY / f"{example.name}.py"


def _output_name(
    example: str,
    theme: ThemeKey,
    variant: VariantKey,
) -> str:
    """Return the GIF filename for one recording."""
    if variant == "mono":
        return f"{example}-{theme}-mono.gif"
    return f"{example}-{theme}.gif"


def generate(
    example: ShowcaseExample,
    theme: ThemeKey,
    variant: VariantKey,
    *,
    vhs: str,
    dry_run: bool,
    quiet: bool,
) -> None:
    """Record one showcase example / theme / palette variant."""
    script = _script_path(example)
    if not script.is_file():
        print(
            f"  skip {example.name} — {script} not found",
            file=sys.stderr,
        )
        return

    mono = variant == "mono"
    demo = _as_demo(example, mono=mono)
    output = OUTPUT_DIRECTORY / _output_name(example.name, theme, variant)
    launch = f"uv run python {script.relative_to(REPOSITORY_ROOT).as_posix()}"
    record_demo(
        demo,
        output=output,
        theme=theme,
        launch_command=launch,
        vhs=vhs,
        dry_run=dry_run,
        quiet=quiet,
        monotone=mono,
        tape_label="showcase",
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--example",
        "--demo",
        dest="example",
        choices=list(_SHOWCASE_MAP),
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
    """CLI entrypoint."""
    args = parse_args(argv)

    # Never purge on dry-run — dry-run is for inspecting tapes only.
    if not args.dry_run:
        for path in purge_legacy_demo_artifacts():
            print(f"removed legacy {path}")

    examples = (
        [_SHOWCASE_MAP[args.example]] if args.example else list(SHOWCASES)
    )
    themes: tuple[ThemeKey, ...] = (args.theme,) if args.theme else THEMES
    variants: tuple[VariantKey, ...] = (
        (args.variant,) if args.variant else VARIANTS
    )
    vhs = "" if args.dry_run else require_vhs()

    for example in examples:
        for theme in themes:
            for variant in variants:
                generate(
                    example,
                    theme,
                    variant,
                    vhs=vhs,
                    dry_run=args.dry_run,
                    quiet=args.quiet,
                )

    if not args.dry_run:
        total = len(examples) * len(themes) * len(variants)
        print(
            f"\nDone — {total} GIF(s) in "
            f"{OUTPUT_DIRECTORY.relative_to(REPOSITORY_ROOT)}/"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
