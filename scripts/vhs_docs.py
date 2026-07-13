"""scripts.vhs_docs

---

Shared recording stack for docs demo GIFs.

Matches the launch / tape / theme patterns used by
``generate_xnano_demos`` and ``generate_readme_demos``:

- ``vhs_tape.build_run_tape`` (hidden launch, clean shell env)
- docs dark/light themes + margin fill from ``vhs_showcase_themes``
- ``COLORTERM=truecolor`` for Tailwind / truecolor colors
- fixed smallish window width (content fills the full terminal width)
- height sized to content rows + spare vertical gap so nothing clips

Usage is always via a generator script that embeds examples and
re-invokes itself with ``--run-example``.
"""

from __future__ import annotations

import dataclasses
import math
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from textwrap import dedent
from typing import Literal, TypeAlias

from vhs_showcase_themes import get_margin_fill, get_vhs_theme
from vhs_tape import build_run_tape

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
"""Repository root (parent of ``scripts/``)."""

_LEGACY_PURGE_MARKER = (
    REPOSITORY_ROOT / "docs" / "assets" / ".demo-assets-purged"
)
"""Marker written after the one-shot legacy asset/script purge."""


def purge_legacy_demo_artifacts(*, force: bool = False) -> list[str]:
    """Remove obsolete generators and stale GIF trees once.

    Safe after regeneration: a marker file prevents re-deleting new GIFs.
    Pass ``force=True`` to run again (destroys current concept/component/
    demo/example media).

    Args:
        force: Ignore the marker and purge again.

    Returns:
        Relative paths that were removed.
    """
    if _LEGACY_PURGE_MARKER.is_file() and not force:
        return []

    removed: list[str] = []
    scripts_dir = REPOSITORY_ROOT / "scripts"
    for name in (
        "generate_demo_gifs.py",
        "generate_example_screenshots.py",
        "generate_terminal_demos.py",
        "run_vhs_demo.py",
        "check_concept_demos.py",
        "vhs_doc_themes.py",
        "vhs_recording.py",
        "_cleanup_legacy_demos.py",
    ):
        path = scripts_dir / name
        if path.is_file():
            path.unlink(missing_ok=True)
            removed.append(f"scripts/{name}")

    media_suffixes = {".gif", ".jpg", ".jpeg", ".png", ".webp"}
    for folder in ("concepts", "components", "demos", "examples"):
        directory = REPOSITORY_ROOT / "docs" / "assets" / folder
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir()):
            if path.is_file() and path.suffix.lower() in media_suffixes:
                path.unlink(missing_ok=True)
                removed.append(
                    str(path.relative_to(REPOSITORY_ROOT))
                )

    terminal_dir = REPOSITORY_ROOT / "docs" / "assets" / "terminal"
    if terminal_dir.is_dir():
        shutil.rmtree(terminal_dir, ignore_errors=True)
        removed.append("docs/assets/terminal/")

    _LEGACY_PURGE_MARKER.parent.mkdir(parents=True, exist_ok=True)
    _LEGACY_PURGE_MARKER.write_text(
        "legacy demo assets purged\n",
        encoding="utf-8",
    )
    return removed


ThemeKey: TypeAlias = Literal["dark", "light"]
"""Docs palette keys used for dual-theme GIF pairs."""

THEMES: tuple[ThemeKey, ...] = ("dark", "light")
"""Default themes generated for concept / component / tutorial demos."""

_DEFAULT_FONT_SIZE = 16
_DEFAULT_LINE_HEIGHT = 1.2
_DEFAULT_PADDING = 12
_DEFAULT_MARGIN = 12
_DEFAULT_WINDOW_BAR = 32
_DEFAULT_WIDTH = 960
"""Shared smallish recording width — content fills this full window."""
_DEFAULT_GAP_ROWS = 2
"""Extra terminal rows so content is not clipped against the frame edge."""

_MINIMUM_HEIGHT = 200
"""Floor for very short demos (chrome + a couple of content rows)."""


def code(body: str) -> str:
    """Normalize demo source — avoids broken dedent from indented closers.

    Args:
        body: Indented multi-line Python source.

    Returns:
        Dedented source ending in a newline.
    """
    content = "\n".join(line for line in body.splitlines() if line.strip())
    return dedent(content).strip() + "\n"


def fitted_height(
    content_rows: int,
    *,
    gap_rows: int = _DEFAULT_GAP_ROWS,
    font_size: int = _DEFAULT_FONT_SIZE,
    line_height: float = _DEFAULT_LINE_HEIGHT,
    padding: int = _DEFAULT_PADDING,
    margin: int = _DEFAULT_MARGIN,
    window_bar: int = _DEFAULT_WINDOW_BAR,
) -> int:
    """Compute recording height for ``content_rows`` plus a small vertical gap.

    Does not change zoom or scale — only the VHS ``Height`` so short demos
    are not full-screen and tall demos are not clipped.

    Args:
        content_rows: Rows of visible content (field heights + borders).
        gap_rows: Extra empty rows for vertical breathing room.
        font_size: VHS ``FontSize``.
        line_height: VHS ``LineHeight``.
        padding: VHS ``Padding`` (all sides).
        margin: VHS ``Margin`` (all sides).
        window_bar: Approximate height of the colorful window bar.

    Returns:
        Pixel height for ``Set Height``.
    """
    row_pixels = font_size * line_height
    body = (max(1, content_rows) + max(0, gap_rows)) * row_pixels
    height = int(math.ceil(window_bar + body + 2 * padding + 2 * margin))
    return max(_MINIMUM_HEIGHT, height)


@dataclasses.dataclass(frozen=True)
class Demo:
    """One docs example recording (theme applied at generation time)."""

    name: str
    """Filename stem, e.g. ``hooks_keyboard`` → ``hooks_keyboard-dark.gif``."""
    code: str
    """Complete Python source executed via ``--run-example``."""
    steps: tuple[str, ...] = dataclasses.field(default_factory=tuple)
    """VHS interaction steps after the launch delay."""
    launch_delay: str = "1.5s"
    """Wait after starting the script before showing the terminal."""
    record_delay: str = "1s"
    """Hold after interactions before stopping."""
    env: tuple[tuple[str, str], ...] = dataclasses.field(default_factory=tuple)
    """Extra ``Env KEY "VALUE"`` lines for the tape."""
    auto_quit: bool = True
    """Send hidden ``q`` after the recording hold (interactive ``run()``)."""
    content_rows: int = 6
    """Visible content rows used only to size ``Height`` (not width/zoom)."""
    content_columns: int | None = None
    """Ignored for sizing — kept so older demo kwargs still construct."""
    width: int | None = None
    """Override pixel width; when ``None``, use the shared smallish default."""
    height: int | None = None
    """Override pixel height; when ``None``, use ``fitted_height``."""
    padding: int = _DEFAULT_PADDING
    """Space between terminal content and recording edge."""
    margin: int = _DEFAULT_MARGIN
    """Outer margin around the terminal chrome."""
    gap_rows: int = _DEFAULT_GAP_ROWS
    """Extra empty rows reserved above/below content."""
    font_size: int = _DEFAULT_FONT_SIZE
    """VHS font size for this recording."""
    window_bar: bool = True
    """Whether to draw the macOS-style traffic-light chrome."""
    border_radius: int = 12
    """Recording border radius."""

    def resolve_width(self) -> int:
        """Return the pixel width for this demo.

        Always the shared full-window width unless explicitly overridden.
        Width is never derived from content (that zoomed demos in).
        """
        if self.width is not None:
            return self.width
        return _DEFAULT_WIDTH

    def resolve_height(self) -> int:
        """Return the pixel height for this demo."""
        if self.height is not None:
            return self.height
        window_bar = _DEFAULT_WINDOW_BAR if self.window_bar else 0
        return fitted_height(
            self.content_rows,
            gap_rows=self.gap_rows,
            font_size=self.font_size,
            padding=self.padding,
            margin=self.margin,
            window_bar=window_bar,
        )


def build_settings(
    theme: ThemeKey,
    demo: Demo,
    *,
    monotone: bool = False,
) -> str:
    """Return the VHS settings block for one recording.

    Args:
        theme: Docs palette key.
        demo: Demo whose dimensions and chrome settings apply.
        monotone: When true, use the monotone showcase palette.

    Returns:
        Pre-formatted VHS settings string.
    """
    if monotone:
        from vhs_showcase_themes import get_vhs_monotone_theme

        theme_json = get_vhs_monotone_theme(theme)
    else:
        theme_json = get_vhs_theme(theme)

    window_bar_lines = (
        "Set WindowBar Colorful\nSet WindowBarSize 32"
        if demo.window_bar
        else ""
    )
    # Truecolor RGB from the app bypasses VHS's 16-color mono theme.
    # Drop COLORTERM for monotone so palette + grayscale pass can win.
    colorterm_line = (
        ""
        if monotone
        else 'Env COLORTERM "truecolor"'
    )
    return f'''Require python

Set Shell "bash"
Set FontSize {demo.font_size}
Set LineHeight {_DEFAULT_LINE_HEIGHT}
Set Width {demo.resolve_width()}
Set Height {demo.resolve_height()}
Set Padding {demo.padding}
Set Margin {demo.margin}
Set MarginFill "{get_margin_fill(theme)}"
Set BorderRadius {demo.border_radius}
{window_bar_lines}
Set Framerate 30
Set PlaybackSpeed 1.0
Set TypingSpeed 40ms
Set Theme {theme_json}

Env TERM "xterm-256color"
{colorterm_line}'''


def require_vhs() -> str:
    """Return the vhs executable path or exit with install guidance.

    Returns:
        Absolute path to the ``vhs`` binary.

    Raises:
        SystemExit: When vhs is not on ``PATH``.
    """
    path = shutil.which("vhs")
    if path is None:
        raise SystemExit(
            "vhs not found on PATH.\n"
            "  macOS:  brew install vhs\n"
            "  Linux:  https://github.com/charmbracelet/vhs#installation"
        )
    return path


def optimize_gif(gif: Path) -> None:
    """Lossy-optimize a GIF when gifsicle is available.

    Args:
        gif: Path to a recorded GIF.
    """
    gifsicle = shutil.which("gifsicle")
    if gifsicle is None:
        return
    subprocess.run(
        [gifsicle, "-O3", "--lossy=30", str(gif), "-o", str(gif)],
        check=True,
    )


def desaturate_gif(gif: Path) -> None:
    """Force a GIF to grayscale for monotone showcase recordings.

    Apps paint truecolor RGB (Tailwind shades), so a mono VHS theme alone
    cannot strip chroma. Convert after capture when ImageMagick or ffmpeg
    is available.

    Args:
        gif: Path to a recorded GIF.
    """
    magick = shutil.which("magick")
    if magick is not None:
        subprocess.run(
            [magick, str(gif), "-colorspace", "Gray", str(gif)],
            check=True,
        )
        return

    convert = shutil.which("convert")
    if convert is not None:
        subprocess.run(
            [convert, str(gif), "-colorspace", "Gray", str(gif)],
            check=True,
        )
        return

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is not None:
        temporary = gif.with_suffix(".mono-tmp.gif")
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(gif),
                "-vf",
                "format=gray",
                str(temporary),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        temporary.replace(gif)
        return

    print(
        "  warning: no magick/convert/ffmpeg — mono GIF may still be color "
        f"({gif.name})",
        file=sys.stderr,
    )


def build_demo_tape(
    *,
    demo: Demo,
    output: Path,
    theme: ThemeKey,
    launch_command: str,
    monotone: bool = False,
) -> str:
    """Build a complete VHS tape for one demo recording.

    Args:
        demo: Demo definition.
        output: Absolute output path for the GIF.
        theme: Docs palette key.
        launch_command: Short command typed while the terminal is hidden.
        monotone: Use monotone theme when true.

    Returns:
        Tape file contents.
    """
    env_lines = [f'Env {key} "{value}"' for key, value in demo.env]
    env_lines.extend(
        (
            'Env XNANO_VHS_DOCS_BG "1"',
            f'Env XNANO_VHS_THEME "{theme}"',
        )
    )
    if monotone:
        # Ensure mono flag is set even if the Demo.env list omitted it.
        if not any(line.startswith('Env XNANO_VHS_MONO ') for line in env_lines):
            env_lines.append('Env XNANO_VHS_MONO "1"')
        # Explicitly clear truecolor for the app process.
        env_lines.append('Env COLORTERM ""')
    tape = build_run_tape(
        output=output.relative_to(REPOSITORY_ROOT),
        settings=build_settings(theme, demo, monotone=monotone),
        launch_command=launch_command,
        steps=demo.steps,
        launch_delay=demo.launch_delay,
        record_delay=demo.record_delay,
        env_lines=env_lines,
    )
    if not demo.auto_quit:
        tape = tape.replace('Type "q"\nSleep 300ms\n', "")
    return tape


def record_demo(
    demo: Demo,
    *,
    output: Path,
    theme: ThemeKey,
    launch_command: str,
    vhs: str,
    dry_run: bool,
    quiet: bool,
    monotone: bool = False,
    tape_label: str = "docs",
) -> None:
    """Record one demo GIF to ``output``.

    Args:
        demo: Demo definition.
        output: Absolute GIF path.
        theme: Docs palette key.
        launch_command: Command VHS types to launch the example.
        vhs: Path to the vhs binary (ignored when ``dry_run``).
        dry_run: Print the tape instead of recording.
        quiet: Pass ``--quiet`` to VHS.
        monotone: Use monotone theme when true.
        tape_label: Prefix used in temporary tape filenames.
    """
    tape_body = build_demo_tape(
        demo=demo,
        output=output,
        theme=theme,
        launch_command=launch_command,
        monotone=monotone,
    )

    if dry_run:
        print(f"# {demo.name}/{theme} -> {output.relative_to(REPOSITORY_ROOT)}")
        print(tape_body)
        return

    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=f"-{tape_label}-{demo.name}-{theme}.tape",
        prefix="xnano-",
        delete=False,
    ) as tape_file:
        tape_file.write(tape_body)
        tape_path = Path(tape_file.name)

    try:
        print(
            f"Recording {demo.name} ({theme}"
            f"{', mono' if monotone else ''}) "
            f"-> {output.relative_to(REPOSITORY_ROOT)}"
        )
        command = [vhs, str(tape_path)]
        if quiet:
            command.append("--quiet")
        subprocess.run(command, cwd=REPOSITORY_ROOT, check=True)
        if monotone:
            desaturate_gif(output)
        optimize_gif(output)
    finally:
        tape_path.unlink(missing_ok=True)

    if not output.is_file():
        raise SystemExit(f"Expected GIF not created: {output}")

    size_kb = output.stat().st_size / 1024
    print(f"  wrote {output.name} ({size_kb:.0f} KiB)")


def run_embedded_code(demo: Demo, *, label: str) -> None:
    """Execute a demo's embedded source for VHS to record.

    Args:
        demo: Demo whose ``code`` field should be executed.
        label: Tag used in the synthetic filename for tracebacks.
    """
    exec(
        compile(demo.code, f"<{label}-demo:{demo.name}>", "exec"),
        {"__name__": "__main__"},
    )


def demo_map(demos: Sequence[Demo]) -> dict[str, Demo]:
    """Index demos by name.

    Args:
        demos: Demo sequence.

    Returns:
        Mapping of demo name to definition.
    """
    return {demo.name: demo for demo in demos}
