"""
Record the animated examples of the documentation's homepage in real Kitty windows.

Run it from the repository root with
``uv run --no-sync python scripts/docs_assets.py [NAME ...]``, where each name is one of
``RECORDINGS`` (all of them without names). Every program in ``scripts/docs_examples/`` runs
as written in a Kitty window of ``COLUMNS`` by ``ROWS`` cells, while the actions of its
recording press keys, and the window is photographed into a looping gif. Each program is
recorded twice, once for each theme of the documentation site, in a window colored like the
site's page, so the gif blends into it: the files are
``docs/assets/home/<name>-light.gif`` and ``docs/assets/home/<name>-dark.gif``.

A gif keeps at most 256 colors, so the page color could drift while the colors are chosen.
The palette is therefore given the page color exactly, and every gif is checked afterwards:
the corners of its first and last frames must be the page color, or the script fails.

The windows, their font (IBM Plex Mono when it is installed), the recorder and the theme
colors are those of ``readme_assets.py``. On macOS
the Kitty windows are shown on screen while they record (a minimized window is not drawn)
and the piano example plays its notes out loud.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import readme_assets  # noqa: E402
from readme_assets import (  # noqa: E402
    ActualTerminal,
    Click,
    Press,
    ReadmeAssetError,
    Recorder,
    Theme,
    Type,
    Wait,
    apply_theme,
    font_notice,
    font_overrides,
    run_action,
)

EXAMPLES = ROOT / "scripts" / "docs_examples"
OUTPUT = ROOT / "docs" / "assets" / "home"

COLUMNS = 80
ROWS = 24
"""Every window is this many cells, so every gif has the same size."""
STARTUP_TIMEOUT = 20

LIGHT_THEME = Theme(
    "light",
    background="#e6e8eb",
    foreground="#15171c",
    palette=readme_assets.LIGHT_THEME.palette,
    dim_opacity=0.6,
)
DARK_THEME = Theme(
    "dark",
    background="#0e0f12",
    foreground="#e4e5e9",
    palette=readme_assets.DARK_THEME.palette,
    dim_opacity=0.5,
)
THEMES = (LIGHT_THEME, DARK_THEME)
"""The page colors of the documentation site, which every gif is recorded against."""


@dataclass(frozen=True)
class KeyDown:
    """Press a key and keep holding it, as Kitty reports a held key to the program."""

    key: str


@dataclass(frozen=True)
class KeyUp:
    """Let go of a key held with ``KeyDown``."""

    key: str


def held_key_report(key: str, *, is_release: bool) -> str:
    """
    Return the report of the kitty keyboard protocol for pressing or releasing a key.

    ``send-key`` presses and releases at once, so a held key is sent as these reports. The
    program receives them as releases only when it asked for them with
    ``keyboard='release_events'``.
    """
    if len(key) != 1:
        raise ReadmeAssetError(
            f"A held key is one character, such as 'a', but got '{key}'. Use Press for "
            "named keys."
        )
    return f"\x1b[{ord(key)};1:{3 if is_release else 1}u"


@dataclass(frozen=True)
class Recording:
    """One example program and the actions that play it while it is recorded."""

    name: str
    actions: tuple[Wait | Press | Type | Click | KeyDown | KeyUp, ...]
    loop_seconds: float
    """How long the gif lasts: the last frame is followed by the first one."""

    @property
    def program(self) -> pathlib.Path:
        """The example's source file."""
        return EXAMPLES / f"{self.name}.py"

    def target(self, theme: Theme) -> pathlib.Path:
        """The gif of the recording for a theme."""
        return OUTPUT / f"{self.name}-{theme.name}.gif"


def hold(key: str, seconds: float) -> tuple[KeyDown, Wait, KeyUp]:
    """Hold a key for ``seconds``."""
    return KeyDown(key), Wait(seconds), KeyUp(key)


def chord(keys: tuple[str, ...], seconds: float) -> tuple[KeyDown | Wait | KeyUp, ...]:
    """Hold several keys together for ``seconds``."""
    return (
        *(KeyDown(key) for key in keys),
        Wait(seconds),
        *(KeyUp(key) for key in keys),
    )


def presses(*steps: tuple[str, float]) -> tuple[Press | Wait, ...]:
    """Press each key of ``steps`` and wait the seconds that come with it."""
    return tuple(
        action for key, seconds in steps for action in (Press((key,)), Wait(seconds))
    )


def typing(text: str, characters_at_once: int = 3) -> tuple[Type, ...]:
    """
    Type ``text`` a few characters at a time.

    Kitty takes about 70 milliseconds to send each piece while the window is photographed,
    which is the pace of the typing: one character at a time would be too slow to follow.
    """
    return tuple(
        Type(text[start : start + characters_at_once])
        for start in range(0, len(text), characters_at_once)
    )


SOUND = Recording(
    "sound",
    actions=(
        Wait(0.7),
        # a bluesy run up from C, through the black key D#
        *hold("a", 0.2),
        Wait(0.05),
        *hold("e", 0.2),
        Wait(0.05),
        *hold("d", 0.2),
        Wait(0.05),
        *hold("g", 0.2),
        Wait(0.05),
        *hold("h", 0.2),
        Wait(0.05),
        *hold("k", 0.45),
        Wait(0.2),
        # and back down, leaning on the black key F#
        *hold("k", 0.2),
        Wait(0.05),
        *hold("h", 0.2),
        Wait(0.05),
        *hold("g", 0.2),
        Wait(0.05),
        *hold("t", 0.2),
        Wait(0.05),
        *hold("g", 0.45),
        Wait(0.25),
        # an F chord, then a C chord
        *chord(("f", "h", "k"), 0.7),
        Wait(0.1),
        *chord(("a", "d", "g", "k"), 1.1),
    ),
    loop_seconds=8.0,
)
"""A short tune on the piano that ends in silence, so the gif starts again cleanly."""

INPUT = Recording(
    "input",
    actions=(
        Wait(0.6),
        # along the path, harvesting each ripe crop of the front row and watering its seed
        *presses(("right", 0.3), ("up", 0.25), ("space", 0.45), ("space", 0.5)),
        *presses(("right", 0.3), ("up", 0.25), ("space", 0.45), ("space", 0.5)),
        *presses(("right", 0.3), ("up", 0.25), ("space", 0.45), ("space", 0.5)),
        # then back to where the farmer started, facing the same way
        *presses(("left", 0.25), ("left", 0.25), ("left", 0.3), ("down", 0.3)),
    ),
    loop_seconds=8.0,
)
"""A walk along the farm: the crops harvested and watered grow ripe again before it loops."""

WIDGETS = Recording(
    "widgets",
    actions=(
        Wait(0.6),
        # down through three commits, the details following the selection
        *presses(("down", 0.45), ("down", 0.45), ("down", 0.5)),
        # open the REMOTE folder of the branch tree with a click
        Click(4, 9),
        Wait(0.7),
        # open the branch menu, move through it and close it again
        *presses(("b", 0.55), ("down", 0.45), ("down", 0.5), ("escape", 0.5)),
        # close the REMOTE folder and go back up to the first commit
        Click(4, 9),
        Wait(0.5),
        *presses(("up", 0.4), ("up", 0.4), ("up", 0.4)),
    ),
    loop_seconds=8.0,
)
"""A walk through a git client: commits, a folder of the branch tree and the branch menu."""

EFFECTS = Recording(
    "effects",
    actions=(
        Wait(0.5),
        # the cards one after the other, along the top row and then the bottom one
        *presses(*((str(number), 0.65) for number in range(1, 9))),
    ),
    loop_seconds=8.0,
)
"""A wave of effects across the cards: each one is back in its place before the gif loops."""

AI = Recording(
    "ai",
    actions=(
        Wait(0.5),
        # ask for a widget
        *typing("a now playing card with a progress bar"),
        Wait(0.3),
        Press(("enter",)),
        Wait(1.9),
        # then for a change to it
        *typing("make it pink"),
        Wait(0.3),
        Press(("enter",)),
        Wait(2.1),
        # and clear both, back to how the program starts
        Press(("escape",)),
    ),
    loop_seconds=8.0,
)
"""A widget asked for and changed, from answers a model gave that the program replays."""

RECORDINGS = {
    recording.name: recording for recording in (WIDGETS, SOUND, INPUT, EFFECTS, AI)
}


def run_recording_action(
    window: ActualTerminal, action: Wait | Press | Type | Click | KeyDown | KeyUp
) -> None:
    """Perform one action of a recording in the window."""
    if isinstance(action, (KeyDown, KeyUp)):
        report = held_key_report(action.key, is_release=isinstance(action, KeyUp))
        window.command("send-text", data="text:" + report)
    else:
        run_action(window, action)


def hex_color(color: str) -> tuple[int, int, int]:
    """Return a ``#rrggbb`` color as red, green and blue."""
    value = int(color.removeprefix("#"), 16)
    return (value >> 16 & 255, value >> 8 & 255, value & 255)


def ffmpeg(*arguments: str, output: bool = False) -> bytes:
    """Run ffmpeg quietly and return what it wrote to its standard output."""
    try:
        completed = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", *arguments],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        raise ReadmeAssetError(
            "ffmpeg is not installed, and gifs need it. Install it (for example with "
            "brew install ffmpeg) and try again."
        ) from None
    except subprocess.CalledProcessError as error:
        raise ReadmeAssetError(
            f"ffmpeg failed: {error.stderr.decode(errors='replace').strip()}. Fix the "
            "problem it reports and try again."
        ) from error
    return completed.stdout if output else b""


def build_gif(
    frames: list[tuple[pathlib.Path, float]],
    length: float,
    target: pathlib.Path,
    background: tuple[int, int, int],
) -> None:
    """
    Join the frames into a looping gif whose palette holds the page color exactly.

    Each frame is shown for as long as it was on screen, and the last one until ``length``.
    """
    if not frames:
        raise ReadmeAssetError("The recording has no frames. Increase its length.")
    directory = frames[0][0].parent
    listing = directory / "frames.txt"
    lines = []
    for index, (path, start) in enumerate(frames):
        end = frames[index + 1][1] if index + 1 < len(frames) else length
        lines.append(f"file '{path}'\nduration {max(end - start, 0.01):.4f}")
    lines.append(f"file '{frames[-1][0]}'")
    listing.write_text("\n".join(lines) + "\n")
    source = ["-f", "concat", "-safe", "0", "-i", str(listing)]
    palette = bytearray(
        ffmpeg(
            *source,
            "-vf",
            "palettegen=stats_mode=full:reserve_transparent=0",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
            output=True,
        )
    )
    # The page color is the most common color, but the palette holds the average of the
    # colors near it: put it back exactly, in place of the entry closest to it.
    closest = min(
        range(len(palette) // 3),
        key=lambda entry: sum(
            (palette[entry * 3 + channel] - background[channel]) ** 2
            for channel in range(3)
        ),
    )
    palette[closest * 3 : closest * 3 + 3] = bytes(background)
    palette_path = directory / "palette.rgb"
    palette_path.write_bytes(bytes(palette))
    ffmpeg(
        *source,
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-video_size",
        "16x16",
        "-i",
        str(palette_path),
        "-lavfi",
        "paletteuse=dither=none:diff_mode=rectangle",
        "-fps_mode",
        "vfr",
        "-loop",
        "0",
        str(target),
    )


def frame_count(path: pathlib.Path) -> int:
    """Return how many frames a gif has."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-count_frames",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=nb_read_frames",
            "-of",
            "csv=p=0",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return int(result.stdout.strip())


def corner_colors(path: pathlib.Path, frame: int) -> list[tuple[int, int, int]]:
    """Return the colors of the four corner pixels of one frame of a gif."""
    size = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    width, height = (int(value) for value in size.split(","))
    colors = []
    for x, y in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)):
        pixel = ffmpeg(
            "-i",
            str(path),
            "-vf",
            f"select=eq(n\\,{frame}),crop=1:1:{x}:{y}",
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
            output=True,
        )
        colors.append((pixel[0], pixel[1], pixel[2]))
    return colors


def check_background(path: pathlib.Path, theme: Theme) -> tuple[int, int, int]:
    """Fail unless the corners of the first and last frames are exactly the page color."""
    expected = hex_color(theme.background)
    last = frame_count(path) - 1
    for frame in (0, last):
        for color in corner_colors(path, frame):
            if color != expected:
                raise ReadmeAssetError(
                    f"{path.name} has the color {color} in a corner of frame {frame}, but "
                    f"the {theme.name} page is {expected}. Render it again; if it keeps "
                    "happening, check that nothing covers the Kitty window."
                )
    return expected


def record(recording: Recording, theme: Theme) -> tuple[int, int, int]:
    """
    Run the example in Kitty with a theme's colors, play its actions and save the gif.

    Returns:
        The page color that the corners of the gif were checked to be.
    """
    target = recording.target(theme)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    window = ActualTerminal(
        recording.program.read_text(encoding="utf-8"),
        columns=COLUMNS,
        rows=ROWS,
        overrides=(f"dim_opacity={theme.dim_opacity}", *font_overrides()),
    )
    try:
        apply_theme(window, theme)
        try:
            window.wait_until(
                lambda: bool(window.text().strip()), timeout=STARTUP_TIMEOUT
            )
        except (AssertionError, RuntimeError) as error:
            raise ReadmeAssetError(
                f"{recording.program.name} drew nothing within {STARTUP_TIMEOUT} seconds: "
                f"{error}. Run it on its own and fix what it reports."
            ) from error
        time.sleep(0.5)  # let the first frames settle before the gif starts
        with tempfile.TemporaryDirectory(prefix="xnano-frames-") as frames:
            recorder = Recorder(window, pathlib.Path(frames))
            recorder.start()
            try:
                for action in recording.actions:
                    run_recording_action(window, action)
                remaining = recording.loop_seconds + 0.2 - recorder.seconds()
                if remaining > 0:
                    time.sleep(remaining)
            finally:
                recorder.stop()
            kept = [
                (path, start)
                for path, start in recorder.frames
                if start < recording.loop_seconds
            ]
            build_gif(kept, recording.loop_seconds, target, hex_color(theme.background))
    finally:
        window.close()
    return check_background(target, theme)


def main() -> int:
    """Record the requested examples (all of them without arguments) in both themes."""
    wanted = sys.argv[1:] or list(RECORDINGS)
    unknown = [name for name in wanted if name not in RECORDINGS]
    if unknown:
        sys.stderr.write(
            f"There is no recording named '{unknown[0]}'. Choose from: "
            f"{', '.join(RECORDINGS)}.\n"
        )
        return 1
    sys.stdout.write(f"{font_notice()}\n")
    try:
        for name in wanted:
            for theme in THEMES:
                recording = RECORDINGS[name]
                background = record(recording, theme)
                sys.stdout.write(
                    f"{recording.target(theme).relative_to(ROOT)}: the corners of its "
                    f"first and last frames are {background}\n"
                )
    except ReadmeAssetError as error:
        sys.stderr.write(f"{error}\n")
        return 1
    except (AssertionError, RuntimeError) as error:
        sys.stderr.write(f"Kitty could not run the example: {error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
