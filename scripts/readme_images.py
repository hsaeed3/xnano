"""
Render the README's pictures: the demo and every Quick Start example, photographed in Kitty.

Run it from the repository root with ``make readme-images`` (or
``uv run python scripts/readme_images.py [NAME ...]``). Each program runs in a real Kitty
window, and Kitty draws the pixels, so the pictures show what a user sees, fonts and colors
included. Kitty windows are shown while they are photographed (a minimized window is not
drawn), and each one closes when its picture is saved. Install Kitty with
``make install-terminal``.
"""

from __future__ import annotations

import os
import pathlib
import re
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

os.environ.setdefault("XNANO_TERMINAL_VISIBLE", "1")

from actual_terminal import ActualTerminal  # noqa: E402

OUTPUT = ROOT / "docs" / "assets" / "readme"
README = ROOT / "README.md"

DEMO_PROGRAM = "import runpy\nrunpy.run_module('xnano', run_name='__main__')\n"
"""The Python the Kitty window runs for the demo."""

PYTHON_BLOCK = re.compile(r"^```python\n(.*?)^```", re.MULTILINE | re.DOTALL)
QUICK_START_SECTION = re.compile(
    r"^## Quick Start\n(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL
)


@dataclass(frozen=True)
class Picture:
    """One picture: how big the window is, and when the program in it is ready to be taken."""

    name: str
    columns: int
    rows: int
    ready_text: str
    keys: Sequence[str] = ()
    seconds: float = 2.0  # time to let the program draw and animate before the picture
    program: str = DEMO_PROGRAM  # the Python the Kitty window runs


def quick_start_programs() -> list[str]:
    """Return the Python blocks of the README's Quick Start section, in order."""
    section = QUICK_START_SECTION.search(README.read_text(encoding="utf-8"))
    if section is None:
        raise ValueError(
            f"{README.relative_to(ROOT)} has no '## Quick Start' section to take the "
            "example programs from. Add the section or update scripts/readme_images.py."
        )
    return PYTHON_BLOCK.findall(section.group(1))


# name, columns, rows, ready_text, keys, seconds: one for each Python block of the Quick Start
QUICK_START_PICTURES = (
    ("quick-start-canvas", 44, 8, "Hello, world!", (), 1.0),
    ("quick-start-formulas", 44, 5, "●", (), 1.2),
    ("quick-start-hooks", 34, 5, "press space", ("space",), 0.5),
    ("quick-start-effects", 44, 7, "xnano", (), 0.6),
    ("quick-start-art-and-sound", 24, 7, "♪", (), 1.0),
)


def quick_start_pictures() -> list[Picture]:
    """Return one picture for each Python block of the README's Quick Start section."""
    programs = quick_start_programs()
    if len(programs) != len(QUICK_START_PICTURES):
        raise ValueError(
            f"The README's Quick Start has {len(programs)} Python blocks, but "
            f"{len(QUICK_START_PICTURES)} pictures are named. Update the names in "
            "scripts/readme_images.py so each block has exactly one picture."
        )
    return [
        Picture(name, columns, rows, ready_text, keys, seconds, program)
        for (name, columns, rows, ready_text, keys, seconds), program in zip(
            QUICK_START_PICTURES, programs, strict=True
        )
    ]


PICTURES = (
    Picture("demo", 150, 42, "press any key", ("x",), 3.0),
    *quick_start_pictures(),
)


def take(picture: Picture) -> pathlib.Path:
    """Run the picture's program in Kitty and save the window as a PNG."""
    target = OUTPUT / f"{picture.name}.png"
    window = ActualTerminal(picture.program, columns=picture.columns, rows=picture.rows)
    try:
        window.wait_for(picture.ready_text, timeout=20)
        for key in picture.keys:
            window.press(key)
            time.sleep(0.4)
        time.sleep(picture.seconds)
        window.screenshot(target)
        window.wait_until(target.exists, timeout=10)
    finally:
        window.close()
    return target


def main() -> int:
    """Take the requested pictures (all of them without arguments)."""
    wanted = set(sys.argv[1:])
    unknown = wanted - {picture.name for picture in PICTURES}
    if unknown:
        names = ", ".join(picture.name for picture in PICTURES)
        sys.stderr.write(f"Unknown pictures {sorted(unknown)}. Choose from: {names}.\n")
        return 2
    for picture in PICTURES:
        if wanted and picture.name not in wanted:
            continue
        sys.stdout.write(f"{picture.name}: {take(picture).relative_to(ROOT)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
