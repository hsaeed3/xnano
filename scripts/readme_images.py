"""
Render the README's pictures: each chosen example run in a real Kitty window, then photographed.

Run it from the repository root with ``make readme-images`` (or
``uv run python scripts/readme_images.py [NAME ...]``). Kitty draws the pixels, so the
pictures show what a user sees, fonts and colors included; the examples are the source of
truth, so a changed example only needs this script run again. Kitty windows are shown while
they are photographed (a minimized window is not drawn), and each one closes when its picture
is saved. Install Kitty with ``make install-terminal``.
"""

from __future__ import annotations

import os
import pathlib
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

os.environ.setdefault("XNANO_TERMINAL_VISIBLE", "1")

from actual_terminal import ActualTerminal  # noqa: E402

OUTPUT = ROOT / "docs" / "assets" / "readme"


@dataclass(frozen=True)
class Picture:
    """One picture: what to run, how big the window is, and when it is ready to be taken."""

    name: str
    program: str  # an example file under examples/, or "xnano" for the demo
    columns: int
    rows: int
    ready_text: str
    keys: Sequence[str] = ()
    seconds: float = 2.0  # time to let the program draw and animate before the picture


PICTURES = (
    Picture("demo", "xnano", 150, 42, "press any key", ("x",), 3.0),
    Picture("world", "20_world.py", 110, 34, "hold the mouse", (), 1.5),
    Picture("dusk", "24_dusk.py", 120, 36, "resize the window", (), 1.5),
    Picture("sprites", "23_sprites.py", 84, 13, "pixel art, written as text", (), 1.5),
    Picture("images", "06_images.py", 70, 24, "zoom", ("right", "right"), 1.0),
    Picture(
        "instruments", "10_audio.py", 70, 14, "up/down: instrument", ("down", "a"), 1.0
    ),
    Picture("song", "22_song.py", 64, 8, "A song written as text", (), 4.0),
    Picture("dashboard", "14_dashboard.py", 66, 20, "requests", (), 2.5),
)


def program_for(picture: Picture) -> str:
    """The Python the Kitty window runs."""
    if picture.program == "xnano":
        return "import runpy\nrunpy.run_module('xnano', run_name='__main__')\n"
    path = ROOT / "examples" / picture.program
    return f"import runpy\nrunpy.run_path({str(path)!r}, run_name='__main__')\n"


def take(picture: Picture) -> pathlib.Path:
    """Run one picture's program in Kitty and save the window as a PNG."""
    target = OUTPUT / f"{picture.name}.png"
    window = ActualTerminal(
        program_for(picture), columns=picture.columns, rows=picture.rows
    )
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
