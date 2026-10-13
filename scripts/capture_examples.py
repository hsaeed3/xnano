"""
scripts.capture_examples

Write ``examples/README.md``: each example run on an emulated terminal, with its screen.

Run it from the repository root with ``uv run python scripts/capture_examples.py``. The
screens are what a user sees a moment after starting the example (and after the keys listed
here), so the page doubles as a visual check that every example draws what it promises.
"""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

from emulator import Screen  # noqa: E402

EXAMPLES = ROOT / "examples"

# file: (rows, columns, seconds to wait, keys pressed before the capture, one line summary)
SPECS: dict[str, tuple[int, int, float, tuple[str, ...], str]] = {
    "01_hello.py": (
        6,
        50,
        1.0,
        (),
        "The smallest program: a region below your prompt.",
    ),
    "02_layout.py": (
        16,
        60,
        1.5,
        (),
        "Percentages and formulas for every position and size.",
    ),
    "03_animation.py": (
        8,
        70,
        2.0,
        (),
        "Motion from a formula of the clock, with no loop.",
    ),
    "04_slider.py": (6, 60, 1.0, (), "A slider from a range and a drag hook."),
    "05_pixels.py": (14, 64, 1.5, (), "Per-pixel drawing, two pixels to a cell."),
    "06_images.py": (24, 70, 1.5, ("right", "+"), "Pan and zoom over real pixel art."),
    "07_effects.py": (9, 60, 3.0, (), "tachyonfx effects, one after another."),
    "08_events.py": (
        14,
        70,
        1.0,
        ("x", "c", "t", "t", "t"),
        "Every kind of event in one log.",
    ),
    "09_state.py": (6, 50, 1.0, ("up", "up"), "Typed state read by expressions."),
    "10_audio.py": (
        8,
        70,
        1.0,
        ("a", "2", "k"),
        "Notes from the keyboard and a musical clock.",
    ),
    "11_text_field.py": (
        6,
        60,
        1.0,
        tuple("Ada") + ("enter",),
        "A text field with the cursor.",
    ),
    "12_widgets.py": (12, 60, 2.0, (), "Composed widgets that follow the clock."),
    "13_menu.py": (10, 40, 1.0, ("down", "enter"), "A keyboard menu over typed state."),
    "14_dashboard.py": (
        20,
        64,
        1.5,
        (),
        "A chart, a bar chart and a table on a timer.",
    ),
    "15_canvas.py": (18, 54, 1.5, (), "Shapes in your own coordinates."),
    "16_snake.py": (14, 40, 1.0, ("down",), "A game on a fixed time step."),
    "17_tabs.py": (14, 50, 1.0, ("right",), "Tabs that switch between pages."),
    "18_paint.py": (
        16,
        54,
        1.0,
        ("2",),
        "Painting with the mouse, two pixels to a cell.",
    ),
    "20_world.py": (
        25,
        80,
        1.0,
        ("right", "right", "right"),
        "A playable pixel-art world with a walking hero.",
    ),
    "21_melody.py": (
        6,
        60,
        1.5,
        ("up",),
        "A melody written as text, and a metronome on the beat.",
    ),
    "19_progress.py": (
        6,
        50,
        0.8,
        (),
        "A job with a progress bar, window title and printed output.",
    ),
}


def to_html(screen: Screen) -> str:
    """The screen as colored text, one span per run of cells with the same colors."""
    names = {"default": None}
    rows = []
    for row in range(screen.rows):
        runs: list[tuple[tuple[str | None, str | None], str]] = []
        for column in range(screen.columns):
            cell = screen.cell(column, row)
            colors = (names.get(cell.fg, cell.fg), names.get(cell.bg, cell.bg))
            if runs and runs[-1][0] == colors:
                runs[-1] = (colors, runs[-1][1] + cell.data)
            else:
                runs.append((colors, cell.data))
        parts = []
        for (foreground, background), text in runs:
            style = []
            if foreground and len(foreground) == 6:
                style.append(f"color:#{foreground}")
            if background and len(background) == 6:
                style.append(f"background:#{background}")
            escaped = text.replace("&", "&amp;").replace("<", "&lt;")
            parts.append(
                f'<span style="{";".join(style)}">{escaped}</span>'
                if style
                else escaped
            )
        rows.append("".join(parts).rstrip())
    return "\n".join(rows).rstrip()


def capture(
    name: str, rows: int, columns: int, seconds: float, keys: tuple[str, ...]
) -> tuple[str, str]:
    """Run one example, press the keys, and return its screen as text and as colored HTML."""
    screen = Screen(
        command=[sys.executable, str(EXAMPLES / name)], rows=rows, columns=columns
    )
    try:
        screen.settle(seconds)
        for key in keys:
            screen.press(key)
            screen.settle(0.4)
        text, html = screen.text, to_html(screen)
        if screen.process.poll() is None:  # (a few examples finish by themselves)
            screen.press("q" if name != "11_text_field.py" else "escape")
        screen.finish()
        return text, html
    finally:
        screen.close()


def main() -> None:
    """Write the README and the colored gallery."""
    lines = [
        "# Examples",
        "",
        "Each example is a complete program. Run one with `uv run python examples/<name>.py`;",
        "press `q` (or `Ctrl-C`) to leave. The screens below are generated by",
        "`scripts/capture_examples.py` (colors are in `gallery.html`), and",
        "`tests/test_examples.py` runs every example on an emulated terminal and checks what it",
        "draws.",
        "",
    ]
    gallery = [
        "<!doctype html><meta charset=utf-8><title>xnano examples</title>",
        "<style>body{background:#16161d;color:#ddd;font:14px/1.2 ui-monospace,monospace;"
        "margin:2rem}pre{background:#000;padding:1rem;border-radius:6px;overflow:auto}"
        "h2{font-weight:500;margin-top:2rem}</style>",
        "<h1>xnano examples</h1>",
    ]
    for name, (rows, columns, seconds, keys, summary) in SPECS.items():
        text, html = capture(name, rows, columns, seconds, keys)
        lines += [f"## `{name}`", "", summary, "", "```text", text, "```", ""]
        gallery += [f"<h2>{name}</h2><p>{summary}</p><pre>{html}</pre>"]
    (EXAMPLES / "README.md").write_text("\n".join(lines).rstrip() + "\n")
    (EXAMPLES / "gallery.html").write_text("\n".join(gallery) + "\n")


if __name__ == "__main__":
    main()
