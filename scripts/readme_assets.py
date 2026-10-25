"""
Render the README's pictures and recordings from annotated code blocks, photographed in Kitty.

Run it from the repository root with ``make readme-assets`` (or
``uv run --no-sync python scripts/readme_assets.py [NAME ...]``). A ``python`` code block
is rendered when the lines directly above its opening fence are an HTML comment, which
GitHub does not show. The first line of the comment holds the options and the lines after
it, if any, are the actions, one per line, run in order::

    <!-- @code-block name="interactive-text" type="gif" height=10 duration=5
    wait 1
    press left
    click 30 4
    -->
    ```python
    ...
    ```

Options (all but ``name`` are optional):

- ``name="..."``: the name the asset files start with (lowercase letters, digits and
  hyphens), unique across the README.
- ``type="image"`` (a PNG, the default) or ``type="gif"``.
- ``height=ROWS``: the window height in terminal rows (default 12). Every window is
  ``COLUMNS`` columns wide, so every asset has the same width in pixels.
- ``duration=SECONDS``: how long a gif records (``gif`` only). The default is the total of
  the ``wait`` actions plus one second, and at least two seconds.

Actions (coordinates are 0-based terminal cells, the column first, like xnano's own):

- ``wait SECONDS``
- ``press KEY [KEY ...]``: keys such as ``left``, ``space``, ``q`` or ``ctrl+s``.
- ``type TEXT``: the rest of the line, typed as text.
- ``paste TEXT``: the rest of the line, as a bracketed paste.
- ``click COLUMN ROW [left|right|middle]``
- ``drag COLUMN ROW COLUMN ROW``: left button down, moved in steps, released.
- ``scroll up|down COLUMN ROW [COUNT]``

Mouse actions send xterm SGR mouse reports. A program only receives them when it has turned
mouse reporting on, so a block that uses them must open its terminal with ``mouse=True``
(and ``scroll=True`` for the wheel).

The block's code runs as written in a real Kitty window, so the assets show what a user
sees, fonts included. Every block is rendered twice, once for each GitHub theme, in a window
colored like GitHub's own page so the picture blends into it: ``THEMES`` holds the dark
theme (background ``#0d1117``, text ``#e6edf3``) and the light theme (background ``#ffffff``,
text ``#1f2328``), and the cursor is hidden in both. Each theme also sets the 16 ANSI colors
to GitHub's palette, so named colors such as ``yellow`` stay readable on both pages
(explicit RGB colors are drawn as written), and draws dim text at an opacity that stays
legible on its page. The files are ``<name>-dark`` and
``<name>-light`` with the extension ``.png`` or ``.gif``.

After rendering, a region with a ``<picture>`` element is written directly below each
annotated block: GitHub shows the dark file to readers using its dark theme and the light
file to everyone else. The region is replaced on every run and removed when the block loses
its annotation. On macOS the Kitty windows are shown on screen while they render (a
minimized window is not drawn) and are closed afterwards. On Linux without a ``DISPLAY`` the
script runs itself again under ``xvfb-run``, so it works headlessly. Install Kitty and
``xvfb-run`` with ``make install-terminal``.
"""

from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

os.environ.setdefault("XNANO_TERMINAL_VISIBLE", "1")

from actual_terminal import ActualTerminal  # noqa: E402

README = ROOT / "README.md"
OUTPUT = ROOT / "docs" / "assets" / "readme"
ASSET_PATH = OUTPUT.relative_to(README.parent).as_posix()
"""Where the README links its assets from, relative to the README, as GitHub resolves it."""

COLUMNS = 100
"""The width of every window in terminal columns."""
DEFAULT_HEIGHT = 12
MINIMUM_HEIGHT = 3
MAXIMUM_HEIGHT = 60
FRAMES_PER_SECOND = 12
"""Gif capture rate: a Kitty screenshot takes about 40 ms, so this leaves room to spare."""
DRAG_STEPS = 8
STARTUP_TIMEOUT = 20

NAME_PATTERN = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
OPTION_PATTERN = re.compile(r'\s*(\w+)=("[^"]*"|\S+)')
MOUSE_BUTTONS = {"left": 0, "middle": 1, "right": 2}
SCROLL_BUTTONS = {"up": 64, "down": 65}
REGION_PATTERN = re.compile(
    r'\n<!-- @code-block-asset name="[^"]*" -->\n.*?<!-- /@code-block-asset -->\n',
    re.DOTALL,
)


@dataclass(frozen=True)
class Theme:
    """The page colors of one GitHub theme, which its assets are drawn against."""

    name: str
    background: str
    foreground: str
    palette: tuple[str, ...]
    """The 16 ANSI colors as ``#rrggbb``, indexed by ANSI color number."""
    dim_opacity: float
    """How strongly dim text keeps its color, from 0 (invisible) to 1 (not dimmed)."""


DARK_THEME = Theme(
    "dark",
    background="#0d1117",
    foreground="#e6edf3",
    palette=(
        "#484f58",
        "#ff7b72",
        "#3fb950",
        "#d29922",
        "#58a6ff",
        "#bc8cff",
        "#39c5cf",
        "#b1bac4",
        "#6e7681",
        "#ffa198",
        "#56d364",
        "#e3b341",
        "#79c0ff",
        "#d2a8ff",
        "#56d4dd",
        "#ffffff",
    ),
    dim_opacity=0.5,
)
LIGHT_THEME = Theme(
    "light",
    background="#ffffff",
    foreground="#1f2328",
    palette=(
        "#24292f",
        "#cf222e",
        "#116329",
        "#9a6700",
        "#0969da",
        "#8250df",
        "#1b7c83",
        "#6e7781",
        "#57606a",
        "#a40e26",
        "#1a7f37",
        "#bf8700",
        "#218bff",
        "#a475f9",
        "#3192aa",
        "#8c959f",
    ),
    dim_opacity=0.6,
)
THEMES = (DARK_THEME, LIGHT_THEME)
"""The themes every block is rendered in."""


class ReadmeAssetError(Exception):
    """A problem a person can fix, told in plain sentences."""


def fail(line: int, problem: str, expected: str, fix: str) -> ReadmeAssetError:
    """Build the error for a README line: what is wrong, what was expected, how to fix it."""
    return ReadmeAssetError(
        f"README.md line {line}: {problem}. Expected {expected}. {fix}"
    )


@dataclass(frozen=True)
class Options:
    """The options on the first line of a ``@code-block`` comment."""

    name: str
    kind: str = "image"
    height: int = DEFAULT_HEIGHT
    duration: float | None = None

    def filename(self, theme: Theme) -> str:
        """Return the asset's file name for a theme, such as ``demo-dark.png``."""
        return f"{self.name}-{theme.name}.{'gif' if self.kind == 'gif' else 'png'}"


@dataclass(frozen=True)
class Wait:
    """Pause for ``seconds``."""

    seconds: float


@dataclass(frozen=True)
class Press:
    """Press keys through Kitty's key encoder."""

    keys: tuple[str, ...]


@dataclass(frozen=True)
class Type:
    """Type text."""

    text: str


@dataclass(frozen=True)
class Paste:
    """Paste text as a bracketed paste."""

    text: str


@dataclass(frozen=True)
class Click:
    """Press and release a mouse button at a cell."""

    column: int
    row: int
    button: str = "left"


@dataclass(frozen=True)
class Drag:
    """Hold the left button at one cell, move to another and release."""

    start_column: int
    start_row: int
    end_column: int
    end_row: int


@dataclass(frozen=True)
class Scroll:
    """Turn the mouse wheel ``count`` ticks at a cell."""

    direction: str
    column: int
    row: int
    count: int = 1


Action = Wait | Press | Type | Paste | Click | Drag | Scroll


@dataclass(frozen=True)
class Block:
    """An annotated code block: where it is, how to render it and the program to run."""

    line: int
    options: Options
    actions: tuple[Action, ...]
    code: str
    closing_line: int  # the index of the closing fence line


def parse_options(text: str, line: int) -> Options:
    """Parse the option text of a ``@code-block`` comment (everything after the marker)."""
    values: dict[str, str] = {}
    position = 0
    text = text.strip()
    while position < len(text):
        match = OPTION_PATTERN.match(text, position)
        if match is None:
            raise fail(
                line,
                f"cannot read the options at '{text[position:].strip()}'",
                'options written as name="value" or height=10',
                "Fix the first line of the @code-block comment.",
            )
        key, value = match.groups()
        if key in values:
            raise fail(
                line,
                f"option '{key}' is given twice",
                "each option once",
                f"Remove one '{key}'.",
            )
        values[key] = value
        position = match.end()

    def quoted(key: str, value: str, expected: str) -> str:
        if len(value) < 2 or not (value.startswith('"') and value.endswith('"')):
            raise fail(
                line,
                f"option '{key}' has the value {value}",
                expected,
                f'Write it as {key}="...".',
            )
        return value[1:-1]

    def number(key: str, value: str, expected: str) -> float:
        try:
            parsed = float(value)
        except ValueError:
            raise fail(
                line,
                f"option '{key}' has the value {value}",
                expected,
                f"Write it as {key}=NUMBER, without quotes.",
            ) from None
        return parsed

    unknown = sorted(set(values) - {"name", "type", "height", "duration"})
    if unknown:
        raise fail(
            line,
            f"unknown option '{unknown[0]}'",
            "one of name, type, height or duration",
            "Remove it or correct its spelling.",
        )
    if "name" not in values:
        raise fail(
            line,
            "the option 'name' is missing",
            'name="lowercase-words" to name the asset file',
            'Add name="..." to the first line of the comment.',
        )
    name = quoted("name", values["name"], "lowercase letters, digits and hyphens")
    if NAME_PATTERN.fullmatch(name) is None:
        raise fail(
            line,
            f"option 'name' has the value \"{name}\"",
            'lowercase letters, digits and single hyphens, such as "interactive-text"',
            "Rename it.",
        )
    kind = "image"
    if "type" in values:
        kind = quoted("type", values["type"], '"image" or "gif"')
        if kind not in {"image", "gif"}:
            raise fail(
                line,
                f"option 'type' has the value \"{kind}\"",
                '"image" or "gif"',
                'Write type="image" or type="gif".',
            )
    height = DEFAULT_HEIGHT
    if "height" in values:
        expected = f"a whole number of rows from {MINIMUM_HEIGHT} to {MAXIMUM_HEIGHT}"
        parsed = number("height", values["height"], expected)
        if parsed != int(parsed) or not MINIMUM_HEIGHT <= parsed <= MAXIMUM_HEIGHT:
            raise fail(
                line,
                f"option 'height' has the value {values['height']}",
                expected,
                "Change the height.",
            )
        height = int(parsed)
    duration = None
    if "duration" in values:
        if kind != "gif":
            raise fail(
                line,
                "option 'duration' is given with type=\"image\"",
                'duration only with type="gif"',
                'Remove the duration or set type="gif".',
            )
        duration = number("duration", values["duration"], "a number of seconds")
        if duration <= 0:
            raise fail(
                line,
                f"option 'duration' has the value {values['duration']}",
                "a number of seconds above zero",
                "Change the duration.",
            )
    return Options(name=name, kind=kind, height=height, duration=duration)


def parse_action(text: str, line: int, options: Options) -> Action:
    """Parse one action line of a ``@code-block`` comment."""
    verb, _, rest = text.strip().partition(" ")
    rest = rest.strip()
    words = rest.split()

    def whole(word: str, expected: str, fix: str) -> int:
        if not word.isdigit():
            raise fail(line, f"'{verb}' has the value '{word}'", expected, fix)
        return int(word)

    def cell(column_word: str, row_word: str) -> tuple[int, int]:
        column = whole(
            column_word,
            f"a column from 0 to {COLUMNS - 1}",
            "Columns and rows are 0-based whole numbers.",
        )
        row = whole(
            row_word,
            f"a row from 0 to {options.height - 1}",
            "Columns and rows are 0-based whole numbers.",
        )
        if column >= COLUMNS or row >= options.height:
            raise fail(
                line,
                f"the cell {column} {row} is outside the {COLUMNS} by {options.height} window",
                f"a column below {COLUMNS} and a row below {options.height}",
                "Change the coordinates or the height option.",
            )
        return column, row

    def arguments(count_low: int, count_high: int, usage: str) -> None:
        if not count_low <= len(words) <= count_high:
            raise fail(
                line, f"'{verb}' has {len(words)} arguments", usage, "Fix the line."
            )

    if verb == "wait":
        arguments(1, 1, "wait SECONDS")
        try:
            seconds = float(words[0])
        except ValueError:
            seconds = -1.0
        if seconds < 0:
            raise fail(
                line,
                f"'wait' has the value '{words[0]}'",
                "a number of seconds, zero or more",
                "Write it as wait 0.5.",
            )
        return Wait(seconds)
    if verb == "press":
        arguments(1, 10_000, "press KEY [KEY ...]")
        return Press(tuple(words))
    if verb in {"type", "paste"}:
        if not rest:
            raise fail(line, f"'{verb}' has no text", f"{verb} TEXT", "Add the text.")
        return Type(rest) if verb == "type" else Paste(rest)
    if verb == "click":
        arguments(2, 3, "click COLUMN ROW [left|right|middle]")
        column, row = cell(words[0], words[1])
        button = words[2] if len(words) == 3 else "left"
        if button not in MOUSE_BUTTONS:
            raise fail(
                line,
                f"'click' has the button '{button}'",
                "left, right or middle",
                "Change the button.",
            )
        return Click(column, row, button)
    if verb == "drag":
        arguments(4, 4, "drag COLUMN ROW COLUMN ROW")
        start = cell(words[0], words[1])
        end = cell(words[2], words[3])
        return Drag(*start, *end)
    if verb == "scroll":
        arguments(3, 4, "scroll up|down COLUMN ROW [COUNT]")
        if words[0] not in SCROLL_BUTTONS:
            raise fail(
                line,
                f"'scroll' has the direction '{words[0]}'",
                "up or down",
                "Change the direction.",
            )
        column, row = cell(words[1], words[2])
        count = (
            whole(words[3], "a whole number of ticks", "Write it as scroll up 10 4 3.")
            if len(words) == 4
            else 1
        )
        if count < 1:
            raise fail(
                line, "'scroll' has a count of 0", "at least 1", "Change the count."
            )
        return Scroll(words[0], column, row, count)
    raise fail(
        line,
        f"unknown action '{verb}'",
        "wait, press, type, paste, click, drag or scroll",
        "Remove the line or correct its spelling.",
    )


def total_wait(actions: tuple[Action, ...]) -> float:
    """Return the seconds the ``wait`` actions add up to."""
    return sum(action.seconds for action in actions if isinstance(action, Wait))


def recording_seconds(block: Block) -> float:
    """Return how long a gif of the block records."""
    waited = total_wait(block.actions)
    return block.options.duration or max(2.0, waited + 1.0)


def parse_blocks(text: str) -> list[Block]:
    """Find the annotated ``python`` blocks of the README text."""
    lines = text.split("\n")
    blocks: list[Block] = []
    for index, line in enumerate(lines):
        if line != "```python" or index == 0:
            continue
        above = lines[index - 1].strip()
        if not above.endswith("-->"):
            continue
        start = index - 1
        while start >= 0 and not lines[start].startswith("<!--"):
            start -= 1
        if start < 0 or not lines[start].startswith("<!-- @code-block "):
            continue
        comment = lines[start:index]
        first = comment[0][len("<!-- @code-block ") :]
        number = start + 1
        if len(comment) == 1:
            if not first.rstrip().endswith("-->"):
                continue
            option_text = first.rstrip()[:-3]
            action_lines: list[str] = []
        else:
            if first.rstrip().endswith("-->"):
                raise fail(
                    number,
                    "the comment ends on its first line but has more lines below it",
                    "the options on the first line and the actions on the lines below, "
                    "closed by a line with only -->",
                    "Move the --> to its own line.",
                )
            if comment[-1].strip() != "-->":
                raise fail(
                    index,
                    "the comment does not end with a line holding only -->",
                    "-->  on its own line after the last action",
                    "Move the --> to its own line.",
                )
            option_text = first
            action_lines = comment[1:-1]
        options = parse_options(option_text, number)
        actions = tuple(
            parse_action(action, start + 2 + offset, options)
            for offset, action in enumerate(action_lines)
            if action.strip()
        )
        try:
            closing = lines.index("```", index + 1)
        except ValueError:
            raise fail(
                index + 1,
                "the code block is never closed",
                "a closing ``` line",
                "Close the block.",
            ) from None
        block = Block(
            number,
            options,
            actions,
            "\n".join(lines[index + 1 : closing]) + "\n",
            closing,
        )
        if options.duration is not None and options.duration < total_wait(actions):
            raise fail(
                number,
                f"option 'duration' is {options.duration:g} seconds but the actions wait "
                f"{total_wait(actions):g} seconds",
                "a duration of at least the total wait",
                "Raise the duration or shorten the waits.",
            )
        blocks.append(block)
    seen: dict[str, int] = {}
    for block in blocks:
        name = block.options.name
        if name in seen:
            raise fail(
                block.line,
                f'the name "{name}" is already used on line {seen[name]}',
                "a name that is unique in the README",
                "Rename one of the blocks.",
            )
        seen[name] = block.line
    return blocks


def mouse_report(
    button: int, column: int, row: int, *, is_release: bool = False
) -> str:
    """Return the SGR mouse report for a 0-based cell (the report itself is 1-based)."""
    return f"\x1b[<{button};{column + 1};{row + 1}{'m' if is_release else 'M'}"


def mouse_reports(action: Click | Drag | Scroll) -> list[str]:
    """Return the SGR reports an action sends, in order."""
    if isinstance(action, Click):
        button = MOUSE_BUTTONS[action.button]
        return [
            mouse_report(button, action.column, action.row),
            mouse_report(button, action.column, action.row, is_release=True),
        ]
    if isinstance(action, Drag):
        reports = [mouse_report(0, action.start_column, action.start_row)]
        for step in range(1, DRAG_STEPS + 1):
            column = action.start_column + round(
                (action.end_column - action.start_column) * step / DRAG_STEPS
            )
            row = action.start_row + round(
                (action.end_row - action.start_row) * step / DRAG_STEPS
            )
            reports.append(mouse_report(32, column, row))  # 32 marks motion
        reports.append(
            mouse_report(0, action.end_column, action.end_row, is_release=True)
        )
        return reports
    return [
        mouse_report(SCROLL_BUTTONS[action.direction], action.column, action.row)
    ] * action.count


def run_action(window: ActualTerminal, action: Action) -> None:
    """Perform one action in the window."""
    if isinstance(action, Wait):
        time.sleep(action.seconds)
    elif isinstance(action, Press):
        window.press(*action.keys)
    elif isinstance(action, Type):
        window.command("send-text", data="text:" + action.text)
    elif isinstance(action, Paste):
        window.paste(action.text)
    else:
        for report in mouse_reports(action):
            window.command("send-text", data="text:" + report)
            time.sleep(0.03 if isinstance(action, Drag) else 0.05)


class Recorder:
    """Photograph the window at a fixed rate on a background thread."""

    def __init__(self, window: ActualTerminal, directory: pathlib.Path) -> None:
        self.window = window
        self.directory = directory
        self.frames: list[tuple[pathlib.Path, float]] = []
        self.started = 0.0
        self.error: BaseException | None = None
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self) -> None:
        """Take screenshots until stopped, keeping the time of each."""
        interval = 1 / FRAMES_PER_SECOND
        next_frame = self.started
        try:
            while not self.stopped.is_set():
                path = self.directory / f"frame-{len(self.frames):05d}.png"
                taken = time.monotonic()
                self.window.screenshot(path)
                self.frames.append((path, taken - self.started))
                next_frame += interval
                self.stopped.wait(max(0.0, next_frame - time.monotonic()))
        except BaseException as error:  # noqa: BLE001 - re-raised on the main thread
            self.error = error

    def start(self) -> None:
        """Start photographing; the clock starts now."""
        self.started = time.monotonic()
        self.thread.start()

    def seconds(self) -> float:
        """Return the seconds since the recording started."""
        return time.monotonic() - self.started

    def stop(self) -> float:
        """Stop photographing and return the length of the recording in seconds."""
        length = self.seconds()
        self.stopped.set()
        self.thread.join()
        if self.error is not None:
            raise ReadmeAssetError(
                f"Recording the window failed: {self.error}. Check that Kitty is running "
                "and try again."
            ) from self.error
        return length


def build_gif(
    frames: list[tuple[pathlib.Path, float]], length: float, target: pathlib.Path
) -> None:
    """Join the frames into a looping gif, each shown for as long as it was on screen."""
    if not frames:
        raise ReadmeAssetError("The recording has no frames. Increase its duration.")
    directory = frames[0][0].parent
    listing = directory / "frames.txt"
    lines = []
    for index, (path, start) in enumerate(frames):
        end = frames[index + 1][1] if index + 1 < len(frames) else length
        lines.append(f"file '{path}'\nduration {max(end - start, 0.01):.4f}")
    lines.append(f"file '{frames[-1][0]}'")
    listing.write_text("\n".join(lines) + "\n")
    palette = directory / "palette.png"
    base = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(listing),
    ]
    try:
        subprocess.run(
            [*base, "-vf", "palettegen=stats_mode=diff", str(palette)],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                *base,
                "-i",
                str(palette),
                "-lavfi",
                "paletteuse=dither=none:diff_mode=rectangle",
                "-fps_mode",
                "vfr",
                "-loop",
                "0",
                str(target),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        raise ReadmeAssetError(
            "ffmpeg is not installed, and gifs need it. Install it (for example with "
            "brew install ffmpeg) and try again."
        ) from None
    except subprocess.CalledProcessError as error:
        raise ReadmeAssetError(
            f"ffmpeg could not build {target.name}: {error.stderr.strip()}. Fix the "
            "problem it reports and try again."
        ) from error


def kitty_color(color: str) -> int:
    """Return a ``#rrggbb`` color as the 24-bit integer Kitty's remote control expects."""
    return int(color.removeprefix("#"), 16)


def apply_theme(window: ActualTerminal, theme: Theme) -> None:
    """Color the window like a GitHub theme: its page, its ANSI palette and a hidden cursor."""
    background = kitty_color(theme.background)
    try:
        window.command(
            "set-colors",
            colors={
                "background": background,
                "foreground": kitty_color(theme.foreground),
                "cursor": background,
                "cursor_text_color": background,
                **{
                    f"color{number}": kitty_color(color)
                    for number, color in enumerate(theme.palette)
                },
            },
            all=True,
        )
    except RuntimeError as error:
        raise ReadmeAssetError(
            f"Kitty could not set the colors of the {theme.name} theme: {error}. Check "
            "that Kitty is version 0.49 or newer and try again."
        ) from error


def render_theme(block: Block, theme: Theme) -> pathlib.Path:
    """Run the block in Kitty with a theme's colors and save its image or gif."""
    options = block.options
    target = OUTPUT / options.filename(theme)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    window = ActualTerminal(
        block.code,
        columns=COLUMNS,
        rows=options.height,
        overrides=(f"dim_opacity={theme.dim_opacity}",),
    )
    try:
        apply_theme(window, theme)
        try:
            window.wait_until(
                lambda: bool(window.text().strip()), timeout=STARTUP_TIMEOUT
            )
        except (AssertionError, RuntimeError) as error:
            raise ReadmeAssetError(
                f"The code block of '{options.name}' (README line {block.line}) drew "
                f"nothing within {STARTUP_TIMEOUT} seconds: {error}. Run the code on "
                "its own and fix what it reports."
            ) from error
        if options.kind == "image":
            for action in block.actions:
                run_action(window, action)
            window.screenshot(target)
        else:
            with tempfile.TemporaryDirectory(prefix="xnano-frames-") as frames:
                recorder = Recorder(window, pathlib.Path(frames))
                recorder.start()
                try:
                    for action in block.actions:
                        run_action(window, action)
                    remaining = recording_seconds(block) - recorder.seconds()
                    if remaining > 0:
                        time.sleep(remaining)
                finally:
                    length = recorder.stop()
                build_gif(recorder.frames, length, target)
    finally:
        window.close()
    return target


def render(block: Block) -> tuple[pathlib.Path, ...]:
    """Render the block once for every theme, one window after the other."""
    return tuple(render_theme(block, theme) for theme in THEMES)


def image_width(path: pathlib.Path) -> int:
    """Return the width in pixels of a PNG or gif, read from its header."""
    header = path.read_bytes()[:26]
    if header.startswith(b"\x89PNG"):
        return int.from_bytes(header[16:20], "big")
    if header.startswith(b"GIF8"):
        return int.from_bytes(header[6:8], "little")
    raise ReadmeAssetError(f"{path.name} is neither a PNG nor a gif. Render it again.")


def check_widths(blocks: list[Block]) -> None:
    """Fail when the assets of the README are not all the same number of pixels wide."""
    widths = {
        filename: image_width(OUTPUT / filename)
        for block in blocks
        for filename in (block.options.filename(theme) for theme in THEMES)
        if (OUTPUT / filename).exists()
    }
    if len(set(widths.values())) > 1:
        listing = ", ".join(
            f"{name} is {width}" for name, width in sorted(widths.items())
        )
        raise ReadmeAssetError(
            f"The assets are not all the same width in pixels ({listing}). Render all of "
            "them again, on the same display, by running the script without names."
        )


def asset_region(options: Options) -> str:
    """Return the generated region holding the ``<picture>`` of an asset's two themes."""
    dark = f"{ASSET_PATH}/{options.filename(DARK_THEME)}"
    light = f"{ASSET_PATH}/{options.filename(LIGHT_THEME)}"
    return (
        f'<!-- @code-block-asset name="{options.name}" -->\n'
        "<picture>\n"
        f'  <source media="(prefers-color-scheme: dark)" srcset="{dark}">\n'
        f'  <img alt="{options.name}" src="{light}">\n'
        "</picture>\n"
        "<!-- /@code-block-asset -->\n"
    )


def update_regions(text: str) -> str:
    """Return the README text with a fresh asset region below every annotated block."""
    text = REGION_PATTERN.sub("", text)
    blocks = parse_blocks(text)
    lines = text.split("\n")
    for block in reversed(blocks):
        region = ["", *asset_region(block.options).rstrip("\n").split("\n")]
        lines[block.closing_line + 1 : block.closing_line + 1] = region
    return "\n".join(lines)


def main() -> int:
    """Render the requested blocks (all of them without arguments) and write their links."""
    if sys.platform == "linux" and not os.environ.get("DISPLAY"):
        display_runner = shutil.which("xvfb-run")
        if display_runner is None:
            sys.stderr.write(
                "Cannot render the README assets without a display. Install the development "
                "tools with make install-terminal, or set DISPLAY to an existing X display.\n"
            )
            return 1
        os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
        return subprocess.run(
            [
                display_runner,
                "--auto-servernum",
                "--server-args=-screen 0 1920x1080x24",
                sys.executable,
                *sys.argv,
            ],
            check=False,
        ).returncode
    wanted = sys.argv[1:]
    try:
        text = README.read_text(encoding="utf-8")
        blocks = parse_blocks(text)
        names = [block.options.name for block in blocks]
        unknown = [name for name in wanted if name not in names]
        if unknown:
            raise ReadmeAssetError(
                f"README.md has no annotated block named '{unknown[0]}'. Choose from: "
                f"{', '.join(names) or 'no blocks are annotated'}."
            )
        for block in blocks:
            if wanted and block.options.name not in wanted:
                if not all(
                    (OUTPUT / block.options.filename(theme)).exists()
                    for theme in THEMES
                ):
                    raise ReadmeAssetError(
                        f"'{block.options.name}' has no dark and light assets yet. Run the "
                        "script without names to render every block."
                    )
                continue
            for path in render(block):
                sys.stdout.write(f"{block.options.name}: {path.relative_to(ROOT)}\n")
        check_widths(blocks)
        README.write_text(update_regions(text), encoding="utf-8")
    except ReadmeAssetError as error:
        sys.stderr.write(f"{error}\n")
        return 1
    except (AssertionError, RuntimeError) as error:
        sys.stderr.write(f"Kitty could not run the example: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
