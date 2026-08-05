"""xnano.core.demo

---

Entry point for the bundled showcase and the Markdown document viewer.

With no arguments this runs the feature showcase: a mosaic of differently
sized boxes, several with their own inner tabs and effects, driven entirely
through ``xnano``. The whole scene stays fluid because every animated box
follows one rule — a per-pixel ``CellCanvas`` is built once and stored on its
component, then returned unchanged from ``compose`` until a throttled tick
rebuilds it. The renderer caches lowered canvas IR by object identity, so
reusing the same canvas between rebuilds is a cache hit rather than a full
re-lowering every frame.
"""

from __future__ import annotations

import colorsys
import dataclasses
import functools
import math
import pathlib
import time
import urllib.request
from typing import Any, Sequence

from xnano.components.bar import Bar
from xnano.components.chart import Chart
from xnano.components.component import Component, ComponentRenderContext
from xnano.components.loader import Loader
from xnano.components.table import Table
from xnano.components.text import Text
from xnano.core.content import (
    CellCanvas,
    CellSpan,
    Content,
    LineGauge,
    Stack,
)
from xnano.core.runtime import get_active_runtime
from xnano.fields import Field
from xnano.grids import BaseGrid
from xnano.hooks import on_keyboard, on_tick

# ── Frame-rate-independent animation clock ──────────────────────────────────

# Continuous animations fire every tick and advance by real elapsed seconds
# rather than a fixed per-tick step, so motion runs at the same speed whatever
# paint cadence the terminal size selects (see ``_paint_interval_ms``).

_ANIMATION_TICK_MS = 16
"""Fire continuous-animation ticks as fast as the paint cadence allows."""


def _delta_seconds(ctx: Any) -> float:
    """Seconds elapsed since the previous tick, from the tick event.

    Reads the framework's reported per-tick delta rather than the wall clock so
    animation advances identically under a live terminal and under synthetic
    ``Action.tick(ms)`` in tests.
    """
    tick = ctx.tick_event
    return 0.0 if tick is None else tick.elapsed_ms / 1000.0


# ── Palettes ────────────────────────────────────────────────────────────────

_PLASMA_PALETTE: tuple[str, ...] = (
    "#14161f",
    "#26374f",
    "#42597a",
    "#7a7290",
    "#b78f88",
    "#d8bfa8",
)
"""Twilight ramp — deep navy through dusty rose to warm peach."""

_ORBIT_TRAIL: tuple[str, ...] = (
    "#1a1e2b",
    "#33455f",
    "#5c6f92",
    "#9a9ac0",
    "#e0d2d0",
)
"""Cool trail ramp, tail to head — navy through periwinkle."""

_ACCENT = "#b0a6c8"
"""Focused-box border accent (soft lavender)."""

_DIM = "#3a3f4e"
"""Unfocused-box border color."""

_STAGE_MODES: tuple[str, ...] = ("Aurora", "Ink", "Flow")
"""Inner tabs for the stage box."""


# ── Cheap per-frame math ────────────────────────────────────────────────────


def build_sin_table(
    count: int,
    frequency: float,
    phase: float,
) -> list[float]:
    """Precompute ``sin(index * frequency + phase)`` for one axis.

    One table per axis keeps per-frame trig at ``width + height`` calls rather
    than ``width * height`` — what makes a full-screen animated canvas
    affordable on every rebuild.
    """
    return [math.sin(index * frequency + phase) for index in range(count)]


def build_plasma_frame(
    width: int,
    height: int,
    phase: float,
    palette: Sequence[str] = _PLASMA_PALETTE,
) -> CellCanvas:
    """Build an interference-plasma canvas from per-axis sin tables."""
    width = max(1, width)
    height = max(1, height)
    column_wave = build_sin_table(width, 0.18, phase)
    row_wave = build_sin_table(height, 0.32, -phase * 0.7)
    glyphs = " ░▒▓█"
    drift = int(phase * 4)
    palette_length = len(palette)
    rows: list[tuple[CellSpan, ...]] = []
    for row_index in range(height):
        vertical = row_wave[row_index]
        spans: list[CellSpan] = []
        for column_index in range(width):
            energy = column_wave[column_index] + vertical
            level = min(4, max(0, int((energy + 2.0) * 1.25)))
            color = palette[
                (column_index + row_index + drift) % palette_length
            ]
            spans.append(CellSpan(text=glyphs[level], foreground=color))
        rows.append(tuple(spans))
    return CellCanvas(rows=tuple(rows), width=width, height=height)


def build_orbit_frame(
    width: int,
    height: int,
    phase: float,
) -> CellCanvas:
    """Build a Lissajous orbit with a fading trail on a dark field."""
    width = max(1, width)
    height = max(1, height)
    grid: list[list[int]] = [[-1] * width for _ in range(height)]
    trail_length = len(_ORBIT_TRAIL)
    samples = 26
    for step in range(samples):
        theta = phase - step * 0.16
        x_norm = 0.5 + 0.42 * math.sin(theta * 1.0)
        y_norm = 0.5 + 0.42 * math.sin(theta * 1.4 + 1.2)
        column = min(width - 1, max(0, int(x_norm * (width - 1))))
        row = min(height - 1, max(0, int(y_norm * (height - 1))))
        intensity = trail_length - 1 - min(trail_length - 1, step // 5)
        if intensity > grid[row][column]:
            grid[row][column] = intensity
    rows: list[tuple[CellSpan, ...]] = []
    for row_index in range(height):
        spans: list[CellSpan] = []
        for column_index in range(width):
            level = grid[row_index][column_index]
            if level < 0:
                spans.append(CellSpan(text="·", foreground="#182234"))
            else:
                glyph = "●" if level >= trail_length - 1 else "•"
                spans.append(
                    CellSpan(text=glyph, foreground=_ORBIT_TRAIL[level])
                )
        rows.append(tuple(spans))
    return CellCanvas(rows=tuple(rows), width=width, height=height)


def build_spiral_frame(
    width: int,
    height: int,
    phase: float,
) -> CellCanvas:
    """Build a rotating Archimedean spiral of glowing points."""
    width = max(1, width)
    height = max(1, height)
    grid: list[list[int]] = [[-1] * width for _ in range(height)]
    trail_length = len(_ORBIT_TRAIL)
    center_x = (width - 1) / 2
    center_y = (height - 1) / 2
    for step in range(60):
        angle = step * 0.5 + phase
        radius = step * 0.08
        column = int(center_x + math.cos(angle) * radius * center_x * 0.9)
        row = int(center_y + math.sin(angle) * radius * center_y * 0.9)
        if 0 <= column < width and 0 <= row < height:
            level = trail_length - 1 - min(trail_length - 1, step // 12)
            grid[row][column] = max(grid[row][column], level)
    rows: list[tuple[CellSpan, ...]] = []
    for row_index in range(height):
        spans: list[CellSpan] = []
        for column_index in range(width):
            level = grid[row_index][column_index]
            if level < 0:
                spans.append(CellSpan(text="·", foreground="#182234"))
            else:
                spans.append(
                    CellSpan(text="✦", foreground=_ORBIT_TRAIL[level])
                )
        rows.append(tuple(spans))
    return CellCanvas(rows=tuple(rows), width=width, height=height)


def build_ripple_frame(
    width: int,
    height: int,
    phase: float,
) -> CellCanvas:
    """Build concentric rings pulsing outward from the center."""
    width = max(1, width)
    height = max(1, height)
    ramp = _ORBIT_TRAIL
    ramp_length = len(ramp)
    center_x = (width - 1) / 2
    center_y = (height - 1) / 2
    glyphs = " ·∘○●"
    rows: list[tuple[CellSpan, ...]] = []
    for row_index in range(height):
        dy = (row_index - center_y) * 2.0
        spans: list[CellSpan] = []
        for column_index in range(width):
            dx = column_index - center_x
            distance = math.sqrt(dx * dx + dy * dy)
            wave = math.sin(distance * 0.6 - phase * 1.5)
            level = int((wave + 1.0) * 2.0)
            level = min(ramp_length - 1, max(0, level))
            spans.append(CellSpan(text=glyphs[level], foreground=ramp[level]))
        rows.append(tuple(spans))
    return CellCanvas(rows=tuple(rows), width=width, height=height)


_TWILIGHT: tuple[str, ...] = (
    "#14161f",
    "#1d2740",
    "#26374f",
    "#344863",
    "#42597a",
    "#4f6486",
    "#5c6f92",
    "#6b7191",
    "#7a7290",
    "#8a86a8",
    "#9a9ac0",
    "#a99fa4",
    "#b78f88",
    "#c7a798",
    "#d8bfa8",
    "#e6ded6",
)
"""16-step twilight ramp — deep navy through dusty rose to warm peach."""


def build_aurora_frame(
    width: int,
    height: int,
    phase: float,
) -> CellCanvas:
    """Build drifting aurora bands from summed, domain-warped sine layers."""
    width = max(1, width)
    height = max(1, height)
    ramp = _TWILIGHT
    top = len(ramp) - 1
    glyphs = " ░▒▓█"
    column_slow = [math.sin(x * 0.11 + phase * 1.3) for x in range(width)]
    column_fine = [math.sin(x * 0.045 - phase * 0.7) for x in range(width)]
    row_slow = [math.sin(y * 0.5 - phase * 1.1) for y in range(height)]
    row_fine = [math.cos(y * 0.19 + phase * 0.5) for y in range(height)]
    rows: list[tuple[CellSpan, ...]] = []
    for row_index in range(height):
        vertical = row_slow[row_index]
        drift = row_fine[row_index]
        spans: list[CellSpan] = []
        for column_index in range(width):
            warp = column_fine[column_index] * 1.4
            energy = column_slow[column_index] + vertical + drift * 0.6 + warp
            index = int((energy + 3.0) * (top / 6.0))
            if index < 0:
                index = 0
            elif index > top:
                index = top
            glyph = glyphs[min(4, index * 5 // (top + 1))]
            spans.append(CellSpan(text=glyph, foreground=ramp[index]))
        rows.append(tuple(spans))
    return CellCanvas(rows=tuple(rows), width=width, height=height)


def build_ink_frame(
    width: int,
    height: int,
    phase: float,
) -> CellCanvas:
    """Build ink-in-water: horizontal drift with vertical bleed, block shades."""
    width = max(1, width)
    height = max(1, height)
    ramp = _TWILIGHT
    top = len(ramp) - 1
    glyphs = " ▁▂▃▄▅▆▇█"
    glyph_top = len(glyphs) - 1
    column_slow = [math.sin(x * 0.16 + phase) for x in range(width)]
    column_fine = [math.cos(x * 0.07 - phase * 0.55) for x in range(width)]
    row_slow = [math.sin(y * 0.28 - phase * 0.9) for y in range(height)]
    row_bleed = [math.sin(y * 0.09 + phase * 0.4) for y in range(height)]
    rows: list[tuple[CellSpan, ...]] = []
    for row_index in range(height):
        vertical = row_slow[row_index]
        bleed = row_bleed[row_index]
        spans: list[CellSpan] = []
        for column_index in range(width):
            value = column_slow[column_index] * (0.6 + 0.4 * bleed)
            value += column_fine[column_index] * vertical + vertical * 0.5
            norm = (value + 2.2) / 4.4
            if norm < 0.0:
                norm = 0.0
            elif norm > 1.0:
                norm = 1.0
            index = int(norm * top)
            glyph = glyphs[int(norm * glyph_top)]
            foreground = ramp[min(top, index + 2)]
            spans.append(
                CellSpan(
                    text=glyph, foreground=foreground, background=ramp[index]
                )
            )
        rows.append(tuple(spans))
    return CellCanvas(rows=tuple(rows), width=width, height=height)


def build_flow_frame(
    width: int,
    height: int,
    phase: float,
) -> CellCanvas:
    """Build a soft diagonal flow field of crossed, domain-warped bands."""
    width = max(1, width)
    height = max(1, height)
    ramp = _TWILIGHT
    top = len(ramp) - 1
    glyphs = " ·∘○●"
    column_slow = [math.sin(x * 0.13 + phase * 0.9) for x in range(width)]
    column_fine = [math.sin(x * 0.31 - phase * 1.4) for x in range(width)]
    row_slow = [math.sin(y * 0.21 + phase * 1.2) for y in range(height)]
    row_fine = [math.cos(y * 0.4 - phase * 0.6) for y in range(height)]
    rows: list[tuple[CellSpan, ...]] = []
    for row_index in range(height):
        vertical = row_slow[row_index]
        warp_axis = row_fine[row_index]
        spans: list[CellSpan] = []
        for column_index in range(width):
            warped = column_fine[column_index] * warp_axis
            value = column_slow[column_index] + vertical + warped * 1.3
            norm = (value + 3.3) / 6.6
            if norm < 0.0:
                norm = 0.0
            elif norm > 1.0:
                norm = 1.0
            index = int(norm * top)
            glyph = glyphs[min(4, int(norm * 5))]
            spans.append(
                CellSpan(
                    text=glyph,
                    foreground=ramp[index],
                    background=ramp[max(0, index - 3)],
                )
            )
        rows.append(tuple(spans))
    return CellCanvas(rows=tuple(rows), width=width, height=height)


_CANVAS_BUILDERS = {
    "Aurora": build_aurora_frame,
    "Ink": build_ink_frame,
    "Flow": build_flow_frame,
    "Plasma": build_plasma_frame,
    "Orbit": build_orbit_frame,
    "Spiral": build_spiral_frame,
    "Ripple": build_ripple_frame,
}
"""Mode name → canvas frame builder, shared by every animated canvas box."""


_LETTER_ROWS: dict[str, tuple[str, ...]] = {
    "x": ("█   █", " █ █ ", "  █  ", " █ █ ", "█   █"),
    "n": ("█   █", "██  █", "█ █ █", "█  ██", "█   █"),
    "a": (" ███ ", "█   █", "█████", "█   █", "█   █"),
    "o": (" ███ ", "█   █", "█   █", "█   █", " ███ "),
}
"""Five-row block glyphs for the splash wordmark (letters of ``xnano``)."""


def build_wordmark_rows(word: str) -> list[str]:
    """Assemble one word into five rows of block glyphs."""
    rows = ["", "", "", "", ""]
    blank = ("     ",) * 5
    for character in word:
        pattern = _LETTER_ROWS.get(character, blank)
        for index in range(5):
            rows[index] += pattern[index] + " "
    return [row.rstrip() for row in rows]


_WORDMARK = build_wordmark_rows("xnano")
"""Precomputed block wordmark rows."""


def _overlay_centered(
    rows: list[list[CellSpan]],
    width: int,
    row_index: int,
    text: str,
    color: str,
    *,
    bold: bool = False,
) -> None:
    """Draw ``text`` centered on one canvas row, over the existing cells."""
    if not 0 <= row_index < len(rows):
        return
    left = max(0, (width - len(text)) // 2)
    modifiers = ("bold",) if bold else ()
    for offset, character in enumerate(text):
        column = left + offset
        if character != " " and 0 <= column < width:
            rows[row_index][column] = CellSpan(
                text=character, foreground=color, modifiers=modifiers
            )


def build_title_frame(
    width: int,
    height: int,
    phase: float,
) -> CellCanvas:
    """Build the splash: an ``xnano`` wordmark cut out of a live plasma."""
    width = max(1, width)
    height = max(1, height)
    base = build_plasma_frame(width, height, phase)
    rows = [list(row) for row in base.rows]
    mark_width = max((len(line) for line in _WORDMARK), default=0)
    left = max(0, (width - mark_width) // 2)
    top = max(0, height // 2 - 4)
    glow = mix_hex("#d8bfa8", "#f0e6dc", 0.5 + 0.5 * math.sin(phase * 2))
    for line_index, line in enumerate(_WORDMARK):
        target = top + line_index
        if not 0 <= target < height:
            continue
        for column_offset, character in enumerate(line):
            column = left + column_offset
            if character != " " and 0 <= column < width:
                rows[target][column] = CellSpan(
                    text="█", foreground=glow, modifiers=("bold",)
                )
    _overlay_centered(
        rows, width, height - 2, "press any key to begin", "#9a9ac0"
    )
    return CellCanvas(
        rows=tuple(tuple(row) for row in rows),
        width=width,
        height=height,
    )


def mix_hex(start: str, end: str, ratio: float) -> str:
    """Interpolate two ``#rrggbb`` colors."""
    start_rgb = (
        int(start[1:3], 16),
        int(start[3:5], 16),
        int(start[5:7], 16),
    )
    end_rgb = (int(end[1:3], 16), int(end[3:5], 16), int(end[5:7], 16))
    mixed = tuple(
        round(a + (b - a) * ratio) for a, b in zip(start_rgb, end_rgb)
    )
    return f"#{mixed[0]:02x}{mixed[1]:02x}{mixed[2]:02x}"


# ── Animated canvas component ───────────────────────────────────────────────


@dataclasses.dataclass
class AnimatedCanvas(Component):
    """A stored, tick-rebuilt canvas that renders one of the stage modes.

    ``compose`` returns the same :class:`CellCanvas` between rebuilds so the
    renderer's identity cache stays warm; ``rebuild`` swaps in a fresh canvas
    from a throttled tick.
    """

    mode: str = "Plasma"
    phase: float = 0.0
    _canvas: CellCanvas | None = dataclasses.field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )
    _size: tuple[int, int] = dataclasses.field(
        default=(1, 1),
        init=False,
        repr=False,
        compare=False,
    )

    def rebuild(self, width: int, height: int) -> None:
        """Rebuild and store the canvas for the current mode and phase."""
        self._size = (max(1, width), max(1, height))
        builder = _CANVAS_BUILDERS.get(self.mode, build_plasma_frame)
        self._canvas = builder(*self._size, self.phase)

    def compose(self, ctx: ComponentRenderContext) -> Content | None:
        if self._canvas is None:
            self.rebuild(ctx.area.width, ctx.area.height)
        return self._canvas


_INTRO_CLIPS: tuple[str, ...] = ("luffy",)
"""Precomputed ``.xni`` clip(s) eligible for the intro splash. Just the
straw-hat spin — it's the eyecatcher and renders smoothly."""

_XNI_CACHE_DIRECTORY = pathlib.Path(__file__).resolve().parents[1]
"""Package-local directory holding ignored one-time clip caches."""

_XNI_SOURCE_DIRECTORY = (
    pathlib.Path(__file__).resolve().parents[2] / "docs" / "assets"
)
"""Repository fallback used by editable/development installations."""

_XNI_URL_ROOT = (
    "https://raw.githubusercontent.com/hsaeed3/xnano/main/docs/assets"
)
"""Remote root used once by installed packages without a local cache."""

_WORDMARK_FG = "#f0e6dc"
"""Wordmark letter color burned into the clip."""


@functools.lru_cache(maxsize=16)
def _get_intro_clip_data(image_name: str) -> Any | None:
    """Resolve, optionally download, and decode one intro clip.

    Lookup order:

    1. Package-local cache (``xnano/<name>.xni``) — written on first download
    2. Repository ``docs/assets/<name>.xni`` — editable/dev checkouts
    3. GitHub raw download into the package cache

    Args:
        image_name: Registered clip basename without its ``.xni`` suffix.

    Returns:
        Decoded ``ImageData``, or ``None`` when the clip cannot be resolved.
    """
    if image_name not in _INTRO_CLIPS:
        return None

    from xnano.components.image import ImageData

    filename = f"{image_name}.xni"
    cache = _XNI_CACHE_DIRECTORY / filename
    source = _XNI_SOURCE_DIRECTORY / filename

    if cache.is_file():
        try:
            return ImageData.from_bytes(cache.read_bytes())
        except Exception:
            return None

    if source.is_file():
        try:
            payload = source.read_bytes()
        except OSError:
            return None
    else:
        request = urllib.request.Request(
            f"{_XNI_URL_ROOT}/{filename}",
            headers={"User-Agent": "xnano-demo"},
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = response.read()
        except OSError:
            return None

    try:
        image_data = ImageData.from_bytes(payload)
    except Exception:
        return None

    try:
        cache.write_bytes(payload)
    except OSError:
        pass
    return image_data


def _load_intro_clip() -> Any | None:
    """Load the intro clip, downloading it on first use when needed."""
    return _get_intro_clip_data(_INTRO_CLIPS[0])


_WORDMARK_OVERLAY_IR: Any = None
"""Lazily built transparent overlay IR of the wordmark (letters only)."""


def _wordmark_overlay_ir() -> Any:
    """Return the wordmark as a transparent glyph overlay (gaps see through).

    Space cells are skipped by the native overlay, so only the block letters
    paint — the clip shows through everything else.
    """
    global _WORDMARK_OVERLAY_IR
    if _WORDMARK_OVERLAY_IR is None:
        from xnano_core import core

        from xnano.colors import get_native_color

        foreground = get_native_color(_WORDMARK_FG)
        mark_width = max((len(line) for line in _WORDMARK), default=0)
        lines = [
            core.IrLine.from_spans(
                [
                    (character, foreground, None, [])
                    for character in line.ljust(mark_width)
                ]
            )
            for line in _WORDMARK
        ]
        _WORDMARK_OVERLAY_IR = core.CoreRenderIR.glyph_overlay(lines)
    return _WORDMARK_OVERLAY_IR


_INTRO_HINT = "press any key to continue"
"""Hint shown along the bottom of the intro splash."""

_INTRO_HINT_IR: Any = None
"""Lazily built transparent overlay IR of the intro hint."""


def _hint_overlay_ir() -> Any:
    """Return the intro hint as a transparent glyph overlay."""
    global _INTRO_HINT_IR
    if _INTRO_HINT_IR is None:
        from xnano_core import core

        from xnano.colors import get_native_color

        foreground = get_native_color("#b0a6c8")
        line = core.IrLine.from_spans(
            [(character, foreground, None, []) for character in _INTRO_HINT]
        )
        _INTRO_HINT_IR = core.CoreRenderIR.glyph_overlay([line])
    return _INTRO_HINT_IR


@dataclasses.dataclass
class IntroSplash(Component):
    """The opening title splash: an animated ``.xni`` clip with the ``xnano``
    wordmark centered over it on a higher ``z``.

    The wordmark is a transparent glyph overlay — a small, fixed-position node
    that paints only its letters, so the clip keeps animating through the gaps
    with no band around the text. Falls back to the plasma title when the clip
    cannot be decoded.
    """

    _image: Any = dataclasses.field(
        default=None, init=False, repr=False, compare=False
    )
    _resolved: bool = dataclasses.field(
        default=False, init=False, repr=False, compare=False
    )
    phase: float = 0.0

    def _ensure_image(self) -> Any:
        if not self._resolved:
            from xnano.components.image import Image

            data = _load_intro_clip()
            self._image = (
                None
                if data is None
                else Image(
                    source=data,
                    fit="smart",
                    horizontal_pixels_per_cell=2,
                    correct_terminal_aspect=True,
                    loop=True,
                )
            )
            self._resolved = True
        return self._image

    def compose(self, ctx: ComponentRenderContext) -> Content | None:
        from xnano_core import core

        from xnano.core.content import Native
        from xnano.core.rendering import _cell_canvas_ir

        width = max(1, ctx.area.width)
        height = max(1, ctx.area.height)
        image = self._ensure_image()
        if image is None:
            return build_title_frame(width, height, self.phase)
        frame_canvas = image.compose(ctx)
        clip = core.CoreRenderNode(
            x=0,
            y=0,
            width=width,
            height=height,
            content=core.CoreRenderContent.ir(_cell_canvas_ir(frame_canvas)),
            z=0,
        )
        mark_width = max((len(line) for line in _WORDMARK), default=0)
        mark_height = len(_WORDMARK)
        wordmark = core.CoreRenderNode(
            x=max(0, (width - mark_width) // 2),
            y=max(0, (height - mark_height) // 2),
            width=mark_width,
            height=mark_height,
            content=core.CoreRenderContent.ir(_wordmark_overlay_ir()),
            z=10,
        )
        hint = core.CoreRenderNode(
            x=max(0, (width - len(_INTRO_HINT)) // 2),
            y=max(0, height - 2),
            width=len(_INTRO_HINT),
            height=1,
            content=core.CoreRenderContent.ir(_hint_overlay_ir()),
            z=10,
        )
        stack = core.CoreRenderNode.stack(
            0, 0, width, height, [clip, wordmark, hint]
        )
        return Native(interface_kind="terminal", payload=stack)


# ── Metrics component ───────────────────────────────────────────────────────


@dataclasses.dataclass
class MetricsPanel(Component):
    """Three live line gauges that drift off the wall clock — paint budget,
    memory, and frame rate."""

    def compose(self, ctx: ComponentRenderContext) -> Content | None:
        now = time.monotonic()
        paint = 0.55 + 0.28 * math.sin(now * 1.3)
        memory = 0.45 + 0.16 * math.sin(now * 0.7 + 1.0)
        frames = 0.82 + 0.15 * math.sin(now * 2.1)
        return Stack(
            children=(
                LineGauge(
                    progress=paint,
                    label=f"paint  {paint * 100:3.0f}%",
                    filled_color="#8f92c0",
                ),
                LineGauge(
                    progress=memory,
                    label=f"mem    {memory * 100:3.0f}%",
                    filled_color="#d8b9a3",
                ),
                LineGauge(
                    progress=frames,
                    label=f"fps    {frames * 60:3.0f}",
                    filled_color="#c9a6b8",
                ),
            ),
            direction="vertical",
            gap=1,
        )


# ── Boxes ───────────────────────────────────────────────────────────────────


class StageBox(BaseGrid, direction="vertical"):
    """The large center stage: an animated canvas with three inner tabs."""

    tab_index: int = Field(default=1, state=True)
    view: AnimatedCanvas = Field(
        default_factory=lambda: AnimatedCanvas(mode=_STAGE_MODES[1]),
        width="1fr",
        height="1fr",
    )

    def select_tab(self, index: int) -> None:
        """Set the stage animation mode and force an immediate rebuild."""
        self.tab_index = index % len(_STAGE_MODES)
        self.view.mode = _STAGE_MODES[self.tab_index]
        self.view.rebuild(max(1, self.columns), max(1, self.rows))

    def cycle_tab(self, delta: int) -> None:
        """Switch the stage animation mode by ``delta`` tabs."""
        self.select_tab(self.tab_index + delta)

    @on_tick(_ANIMATION_TICK_MS)
    def _advance(self, ctx) -> None:
        if _is_paused():
            return
        self.view.phase += 1.375 * _delta_seconds(ctx)
        self.view.rebuild(max(1, self.columns), max(1, self.rows))


_ORBIT_MODES: tuple[str, ...] = ("Orbit", "Spiral", "Ripple")
"""Inner tabs for the orbit box."""


class OrbitBox(BaseGrid, direction="vertical"):
    """A drifting canvas with three motion tabs of its own."""

    tab_index: int = Field(default=0, state=True)
    view: AnimatedCanvas = Field(
        default_factory=lambda: AnimatedCanvas(mode="Orbit"),
        width="1fr",
        height="1fr",
    )

    def select_tab(self, index: int) -> None:
        """Set the orbit motion pattern and force an immediate rebuild."""
        self.tab_index = index % len(_ORBIT_MODES)
        self.view.mode = _ORBIT_MODES[self.tab_index]
        self.view.rebuild(max(1, self.columns), max(1, self.rows))

    def cycle_tab(self, delta: int) -> None:
        """Rotate the orbit motion pattern by ``delta`` tabs."""
        self.select_tab(self.tab_index + delta)

    @on_tick(_ANIMATION_TICK_MS)
    def _advance(self, ctx) -> None:
        if _is_paused():
            return
        self.view.phase += 1.5 * _delta_seconds(ctx)
        self.view.rebuild(max(1, self.columns), max(1, self.rows))


_SIGNAL_A = "#4a6a92"
"""Bar-gradient start (slate blue)."""

_SIGNAL_B = "#d8b9a3"
"""Bar-gradient end (warm peach)."""


def _signal_sample(step: int) -> float:
    """One point of the live signal, in ``0..1`` (two summed waves)."""
    return 0.5 + 0.32 * math.sin(step * 0.35) + 0.14 * math.sin(step * 0.11)


def _bar_gradient(count: int) -> tuple[str, ...]:
    """Interpolate a per-bar blue→cyan gradient of ``count`` colors."""
    if count <= 1:
        return (_SIGNAL_A,)
    return tuple(
        mix_hex(_SIGNAL_A, _SIGNAL_B, index / (count - 1))
        for index in range(count)
    )


class SignalBox(BaseGrid, direction="vertical"):
    """Live signal box with Wave, Bars, and Spark inner tabs."""

    tab_index: int = Field(default=0, state=True)
    view: Any = Field(default_factory=Text, width="1fr", height="1fr")

    _TABS = ("Wave", "Bars", "Spark")

    def grid_post_init(self) -> None:
        self._step = 40
        self._series: list[float] = [
            _signal_sample(index) for index in range(40)
        ]

    def select_tab(self, index: int) -> None:
        """Select the wave, bar, or spark view by tab index."""
        self.tab_index = index % len(self._TABS)

    def cycle_tab(self, delta: int) -> None:
        """Rotate through the signal views."""
        self.select_tab(self.tab_index + delta)

    @on_tick(90)
    def _advance(self) -> None:
        if _is_paused():
            return
        series = getattr(self, "_series", None)
        if series is None:
            return
        self._step = getattr(self, "_step", 40) + 1
        self._series = (series + [_signal_sample(self._step)])[-40:]

    def grid_render(self) -> None:
        series = getattr(self, "_series", None) or [_signal_sample(0)]
        tab = self._TABS[self.tab_index]
        if tab == "Bars":
            window = series[-28:]
            self.view = Bar(
                data=tuple(value * 100 for value in window),
                colors=_bar_gradient(len(window)),
                glyphs="blocks",
            )
        elif tab == "Spark":
            self.view = Bar(
                data=tuple(value * 100 for value in series),
                foreground=_SIGNAL_B,
                glyphs="braille",
            )
        else:
            self.view = Chart(
                series={"signal": tuple(enumerate(series))},
                kind="line",
                colors=(_SIGNAL_B,),
                legend=False,
            )


def _build_palette_canvas(width: int, height: int) -> CellCanvas:
    """Build a full-spectrum color field: hue across, value down."""
    width = max(1, width)
    height = max(1, height)
    rows: list[tuple[CellSpan, ...]] = []
    for row_index in range(height):
        value = 1.0 - 0.72 * (row_index / max(1, height - 1))
        spans: list[CellSpan] = []
        for column_index in range(width):
            hue = column_index / max(1, width - 1)
            red, green, blue = colorsys.hsv_to_rgb(hue, 0.62, value)
            color = (
                f"#{int(red * 255):02x}"
                f"{int(green * 255):02x}"
                f"{int(blue * 255):02x}"
            )
            spans.append(CellSpan(text="█", foreground=color))
        rows.append(tuple(spans))
    return CellCanvas(rows=tuple(rows), width=width, height=height)


@dataclasses.dataclass
class PalettePanel(Component):
    """A static color-palette swatch strip — every good TUI has one.

    The swatch canvas is stored and only rebuilt when the box is resized, so it
    reuses the same cached object every frame.
    """

    _canvas: CellCanvas | None = dataclasses.field(
        default=None, init=False, repr=False, compare=False
    )
    _size: tuple[int, int] = dataclasses.field(
        default=(0, 0), init=False, repr=False, compare=False
    )

    def compose(self, ctx: ComponentRenderContext) -> Content | None:
        size = (max(1, ctx.area.width), max(1, ctx.area.height))
        if self._canvas is None or self._size != size:
            self._size = size
            self._canvas = _build_palette_canvas(*size)
        return self._canvas


_DECK_TABS = ("Overview", "Table", "Code")
"""Inner tabs for the deck box."""

_DECK_CODE = (
    "class App(BaseGrid):\n"
    "    art = Field(\n"
    "        border='rounded',\n"
    "    )\n\n"
    "    @on_keyboard('space')\n"
    "    def toggle(self, ctx):\n"
    "        ...\n"
)
"""Sample source shown on the deck's Code tab."""

_DECK_ROWS = (
    {"box": "stage", "kind": "canvas", "tabs": 3},
    {"box": "signal", "kind": "chart", "tabs": 2},
    {"box": "orbit", "kind": "canvas", "tabs": 1},
    {"box": "deck", "kind": "mixed", "tabs": 3},
)
"""Rows shown on the deck's Table tab."""


class DeckBox(BaseGrid, direction="vertical"):
    """A three-tab reference deck: overview text, a table, and code."""

    tab_index: int = Field(default=0, state=True)
    view: Any = Field(default_factory=Text, width="1fr", height="1fr")

    def select_tab(self, index: int) -> None:
        """Select a deck tab by index."""
        self.tab_index = index % len(_DECK_TABS)

    def cycle_tab(self, delta: int) -> None:
        """Rotate through the deck tabs."""
        self.select_tab(self.tab_index + delta)

    def grid_render(self) -> None:
        tab = _DECK_TABS[self.tab_index]
        header = "  ".join(
            f"[{index + 1}]{name}" for index, name in enumerate(_DECK_TABS)
        )
        if tab == "Table":
            self.view = Table(data=list(_DECK_ROWS))
        elif tab == "Code":
            self.view = Text(
                content=f"{header}\n\n{_DECK_CODE}",
                foreground="#d8d2cc",
            )
        else:
            self.view = Text(
                content=(
                    f"{header}\n\n"
                    "A grid of live boxes. Several carry their own inner\n"
                    "tabs and effects. Focus a box, then cycle its tabs\n"
                    "and replay an effect — every keybind does something."
                ),
                foreground="#e6ded6",
                wrap=True,
            )


class LogBox(BaseGrid, direction="vertical"):
    """A rolling event log, appended to as keybinds fire."""

    view: Text = Field(default_factory=Text, width="1fr", height="1fr")

    def grid_post_init(self) -> None:
        self._lines: list[str] = []

    def append(self, message: str) -> None:
        """Record one event line."""
        self._lines = (self._lines + [message])[-40:]

    def grid_render(self) -> None:
        visible = max(1, self.rows)
        lines = getattr(self, "_lines", None) or []
        tail = lines[-visible:] or ["ready."]
        self.view = Text(content="\n".join(tail), foreground="#b0a6c8")


# ── Columns ─────────────────────────────────────────────────────────────────


class LeftColumn(BaseGrid, direction="vertical", gap=1):
    """Narrow rail: metrics over the event log."""

    metrics: MetricsPanel = Field(
        default_factory=MetricsPanel,
        height=7,
        border="rounded",
        title=" Metrics ",
        padding=(0, 1),
        group="metrics",
        border_color=_DIM,
    )
    log: LogBox = Field(
        default_factory=LogBox,
        height="1fr",
        border="rounded",
        title=" Event log ",
        padding=(0, 1),
        group="log",
        border_color=_DIM,
    )

    def grid_render(self) -> None:
        _highlight(self, {"metrics": "metrics", "log": "log"})


class CenterColumn(BaseGrid, direction="vertical", gap=1):
    """The main column: the stage over a signal/orbit strip."""

    stage: StageBox = Field(
        default_factory=StageBox,
        height="62%",
        border="double",
        title=" Stage ",
        group="stage",
        autofocus=True,
        border_color=_ACCENT,
    )
    strip: "StripRow" = Field(default_factory=lambda: StripRow(), height="1fr")


class StripRow(BaseGrid, direction="horizontal", gap=1):
    """Signal chart beside the orbit canvas."""

    signal: SignalBox = Field(
        default_factory=SignalBox,
        width="55%",
        border="rounded",
        title=" Signals ",
        group="signal",
        border_color=_DIM,
    )
    orbit: OrbitBox = Field(
        default_factory=OrbitBox,
        width="1fr",
        border="rounded",
        title=" Orbit ",
        group="orbit",
        border_color=_DIM,
    )

    def grid_render(self) -> None:
        _highlight(self, {"signal": "signal", "orbit": "orbit"})


class RightColumn(BaseGrid, direction="vertical", gap=1):
    """Wide rail: color palette over the reference deck."""

    palette: PalettePanel = Field(
        default_factory=PalettePanel,
        height=10,
        border="rounded",
        title=" Palette ",
        padding=(0, 1),
        group="palette",
        border_color=_DIM,
    )
    deck: DeckBox = Field(
        default_factory=DeckBox,
        height="1fr",
        border="rounded",
        title=" Deck ",
        padding=(0, 1),
        group="deck",
        border_color=_DIM,
    )

    def grid_render(self) -> None:
        _highlight(self, {"palette": "palette", "deck": "deck"})


class Body(BaseGrid, direction="horizontal", gap=1):
    """The three-column mosaic."""

    left: LeftColumn = Field(default_factory=LeftColumn, width=26)
    center: CenterColumn = Field(default_factory=CenterColumn, width="1fr")
    right: RightColumn = Field(default_factory=RightColumn, width=34)


# ── Focus + pause helpers ───────────────────────────────────────────────────

_PAUSED = False
"""Whether animation ticks are frozen. Toggled by the pause keybind."""


def _is_paused() -> bool:
    """Return whether animation is paused."""
    return _PAUSED


def _highlight(grid: BaseGrid, fields: dict[str, str]) -> None:
    """Tint each field's border by whether its group holds focus."""
    runtime = get_active_runtime()
    focused = None if runtime is None else runtime.focused_group
    for field_name, group in fields.items():
        grid.grid_update_field(
            field_name,
            border_color=_ACCENT if group == focused else _DIM,
        )


# ── Root ────────────────────────────────────────────────────────────────────

_EFFECTS: tuple[str, ...] = ("fade", "dissolve", "coalesce", "sweep_in")
"""Effect kinds cycled by the effect keybind."""


class Showcase(BaseGrid, direction="vertical", gap=0):
    """The full showcase: header, the box mosaic, and a keybind legend."""

    header: Text = Field(
        default_factory=lambda: Text(
            content="  xnano · showcase",
            foreground="#d8bfa8",
            modifiers=("bold",),
        ),
        height=1,
    )
    body: Body = Field(default_factory=Body, height="1fr")
    footer: Text = Field(default_factory=Text, height=1)

    def grid_post_init(self) -> None:
        self._effect_index = 0
        self._status_loader = Loader(style="spinner")
        left = self.body.left
        center = self.body.center
        right = self.body.right
        strip = center.strip
        self._boxes = {
            "metrics": left.metrics,
            "log": left.log,
            "stage": center.stage,
            "signal": strip.signal,
            "orbit": strip.orbit,
            "palette": right.palette,
            "deck": right.deck,
        }
        self._effect_targets = {
            "metrics": (left, "metrics"),
            "log": (left, "log"),
            "stage": (center, "stage"),
            "signal": (strip, "signal"),
            "orbit": (strip, "orbit"),
            "palette": (right, "palette"),
            "deck": (right, "deck"),
        }

    def _log(self, message: str) -> None:
        """Append one line to the event log box, if present."""
        log = getattr(self, "_boxes", {}).get("log")
        if isinstance(log, LogBox):
            log.append(message)

    def _focused_box(self) -> tuple[str | None, BaseGrid | None]:
        runtime = get_active_runtime()
        group = None if runtime is None else runtime.focused_group
        boxes = getattr(self, "_boxes", {})
        return group, boxes.get(group) if group else None

    @on_keyboard("]", ".", "shift+right")
    def _next_tab(self) -> None:
        group, box = self._focused_box()
        cycle = getattr(box, "cycle_tab", None)
        if callable(cycle):
            cycle(1)
            self._log(f"{group}: next tab")

    @on_keyboard("[", ",", "shift+left")
    def _previous_tab(self) -> None:
        group, box = self._focused_box()
        cycle = getattr(box, "cycle_tab", None)
        if callable(cycle):
            cycle(-1)
            self._log(f"{group}: prev tab")

    @on_keyboard("1", "2", "3")
    def _select_tab(self, ctx) -> None:
        group, box = self._focused_box()
        select = getattr(box, "select_tab", None)
        key = (
            ctx.keyboard_event.key if ctx.keyboard_event is not None else None
        )
        if callable(select) and isinstance(key, str) and key.isdigit():
            select(int(key) - 1)
            self._log(f"{group}: tab {key}")

    @on_keyboard("e")
    def _replay_effect(self) -> None:
        group, _ = self._focused_box()
        targets = getattr(self, "_effect_targets", {})
        target = targets.get(group) if group else None
        if target is None:
            return
        parent, field_name = target
        index = getattr(self, "_effect_index", 0)
        kind = _EFFECTS[index % len(_EFFECTS)]
        self._effect_index = index + 1
        parent.grid_effect(kind, duration_ms=420, fields=[field_name])
        self._log(f"{group}: effect {kind}")

    @on_keyboard("p", "space")
    def _toggle_pause(self) -> None:
        global _PAUSED
        _PAUSED = not _PAUSED
        self._log("paused" if _PAUSED else "resumed")

    @on_keyboard("q", "escape")
    def _quit(self) -> None:
        runtime = get_active_runtime()
        if runtime is not None:
            runtime.request_exit()

    def grid_render(self) -> None:
        runtime = get_active_runtime()
        focused = None if runtime is None else runtime.focused_group
        state = "paused" if _PAUSED else "live"
        spinner = self._status_loader.current_frame()
        self.header = Text(
            content=f"  {spinner} xnano · showcase",
            foreground="#d8bfa8",
            modifiers=("bold",),
        )
        self.footer = Text(
            content=(
                f"  focus:{focused or '-':<8} {state}   "
                "[ ]/1-3 tabs · arrows focus · E effect · P pause · Q quit"
            ),
            foreground="#7a7290",
        )


# ── Root: intro splash, then the mosaic ─────────────────────────────────────


class Demo(BaseGrid, direction="vertical"):
    """The full experience: a title splash that gives way to the mosaic."""

    _INTRO_SECONDS = 3.0
    """Splash length in wall-clock seconds, independent of paint cadence."""

    view: Any = Field(default_factory=IntroSplash, height="1fr")

    def grid_post_init(self) -> None:
        self._elapsed = 0.0

    def _enter_showcase(self) -> None:
        """Replace the splash with the live mosaic, once."""
        if isinstance(self.view, IntroSplash):
            self.view = Showcase()

    @on_tick(_ANIMATION_TICK_MS)
    def _advance(self, ctx) -> None:
        view = self.view
        if isinstance(view, IntroSplash):
            delta = _delta_seconds(ctx)
            view.phase += 1.818 * delta
            self._elapsed = getattr(self, "_elapsed", 0.0) + delta
            if self._elapsed >= self._INTRO_SECONDS:
                self._enter_showcase()

    @on_keyboard
    def _skip(self) -> None:
        self._enter_showcase()


# ── Entrypoint ──────────────────────────────────────────────────────────────


def _paint_interval_ms(width: int, height: int) -> int:
    """Pick a paint cadence from the terminal's cell count.

    The animations drift slowly, so a modest cadence reads as smooth once the
    frame is atomic (the synchronized-update wrapper removed the tearing that
    used to make low rates *look* choppy). Painting less often is the whole
    lever for CPU here — every frame re-lowers the animated truecolor cells and
    the emulator repaints them — so keep the rate low and back it off further
    on big terminals, where each frame costs proportionally more cells. Motion
    advances on the wall clock, so speed is unchanged whatever the cadence.
    """
    cells = max(1, width) * max(1, height)
    if cells <= 10_000:
        return 66  # ~15fps  (up to ~200x50)
    if cells <= 20_000:
        return 80  # ~12fps  (up to ~280x70)
    return 100  # ~10fps  (4K / tmux-fullscreen)


def run_showcase() -> None:
    """Run the feature showcase on the live terminal."""
    import shutil

    from xnano.terminal import Terminal

    width, height = shutil.get_terminal_size(fallback=(120, 40))
    interval = _paint_interval_ms(width, height)
    Terminal(title="xnano · showcase", tick_interval=interval).run(Demo())


def run_demo(arguments: Sequence[str] | None = None) -> None:
    """Run the feature showcase, or view a Markdown document.

    Args:
        arguments: Optional command arguments. When the first value is a
            path, it is opened in the Markdown viewer; otherwise the
            interactive feature showcase runs.
    """
    values = list(arguments or ())
    if values:
        from xnano.markdown import run_markdown

        run_markdown(pathlib.Path(values[0]))
        return
    run_showcase()


__all__ = ("Demo", "Showcase", "run_demo", "run_showcase")
