"""xnano.core.demo.title

---

The animated title stage for the built-in ``xnano`` feature tour.
"""

from __future__ import annotations

import functools
import math
import random
from typing import TypeAlias

from xnano.components.text import Text
from xnano.core.demo.panels import XnanoDemo
from xnano.fields import Field
from xnano.grid import Grid
from xnano.hooks import on_keyboard, on_tick
from xnano.terminal import Terminal


_ASCII_TITLE = r"""
██╗  ██╗███╗   ██╗ █████╗ ███╗   ██╗ ██████╗
╚██╗██╔╝████╗  ██║██╔══██╗████╗  ██║██╔═══██╗
 ╚███╔╝ ██╔██╗ ██║███████║██╔██╗ ██║██║   ██║
 ██╔██╗ ██║╚██╗██║██╔══██║██║╚██╗██║██║   ██║
██╔╝ ██╗██║ ╚████║██║  ██║██║ ╚████║╚██████╔╝
╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝
"""
"""A compact, highly legible ``xnano`` terminal wordmark."""

_TITLE_ROWS = [line for line in _ASCII_TITLE.splitlines() if line]
_TITLE_WIDTH = max(len(line) for line in _TITLE_ROWS)

_WATERCOLOR_SKY = (
    (230, 83, 103),
    (240, 118, 104),
    (246, 148, 96),
    (250, 181, 105),
    (247, 224, 174),
    (255, 241, 203),
    (241, 205, 116),
    (173, 184, 113),
)
"""Coral, orange, cream, yellow and sage watercolor pigments."""

_WATERCOLOR_AURORA = (
    (246, 190, 35),
    (255, 244, 207),
    (248, 204, 71),
    (244, 132, 68),
    (241, 67, 157),
    (201, 103, 218),
    (83, 187, 220),
    (125, 206, 232),
)
"""Yellow, cream, orange, pink, lavender and cyan aurora pigments."""

_WatercolorPalette: TypeAlias = tuple[tuple[int, int, int], ...]
"""An ordered set of RGB pigment anchors."""

_WatercolorProfile: TypeAlias = tuple[
    _WatercolorPalette,
    float,
    float,
    float,
    float,
]
"""A palette, gradient weights, offset, and bloom phase for one run."""

_SPLASH_FRAMES = 107
"""Frames shown before the title dissolves into the feature panels."""

_TRANSITION_FRAMES = 38
"""Frames used to soften the watercolor into the panel scene."""

_BRIDGE_FOREGROUND = "#324537"
"""Ink color shared by the outgoing and incoming transition effects."""

_BRIDGE_BACKGROUND = "#d7b873"
"""Warm wash shared by the outgoing and incoming transition effects."""

_LOGO_INK = "#183b32"
"""Deep forest ink used for the centered wordmark."""

_LOGO_SHADOW = "#fff1cf"
"""Warm paper highlight offset behind the wordmark."""


def _mix_channel(start: int, end: int, ratio: float) -> int:
    """Interpolate one color channel."""
    return round(start + (end - start) * ratio)


@functools.lru_cache(maxsize=32)
def _get_watercolor_profile(seed: int) -> _WatercolorProfile:
    """Choose one reference palette and build one launch's gradient."""
    generator = random.Random(seed)
    palette = (
        _WATERCOLOR_SKY
        if generator.getrandbits(1) == 0
        else _WATERCOLOR_AURORA
    )
    return (
        palette,
        generator.uniform(0.36, 0.58),
        generator.uniform(-0.18, 0.18),
        generator.uniform(0.10, 0.24),
        generator.uniform(0.0, math.tau),
    )


def _get_watercolor_color(
    horizontal: float,
    vertical: float,
    phase: float,
    watercolor_seed: int = 0,
) -> str:
    """Return one cell from a drifting cluster of watercolor pigments."""
    (
        palette,
        vertical_weight,
        horizontal_weight,
        gradient_offset,
        bloom_phase,
    ) = _get_watercolor_profile(watercolor_seed)
    slow_phase = phase * 0.18
    broad_bloom = math.sin(
        horizontal * 4.2
        + math.sin(vertical * 3.1 - slow_phase) * 0.9
        + slow_phase
        + bloom_phase
    )
    crossing_bloom = math.cos(
        vertical * 5.0
        - horizontal * 2.2
        - slow_phase * 0.5
        + bloom_phase * 0.6
    )
    paper_pool = math.sin(
        horizontal * 3.0
        + vertical * 4.1
        + slow_phase * 0.3
        - bloom_phase * 0.35
    )
    if palette is _WATERCOLOR_AURORA:
        # Keep cream within the yellow crown, then wash through orange and
        # pink before opening into lavender and cyan near the lower edge.
        position = 0.03 + vertical * 0.82 + horizontal * 0.04
        position += broad_bloom * 0.085
        position += crossing_bloom * 0.05
        position += paper_pool * 0.02
    else:
        position = gradient_offset
        position += vertical * vertical_weight
        position += horizontal * horizontal_weight
        position += broad_bloom * 0.10
        position += crossing_bloom * 0.06
        position += paper_pool * 0.025
    position = max(0.0, min(0.999, position))

    scaled = position * (len(palette) - 1)
    start_index = int(scaled)
    ratio = scaled - start_index
    start = palette[start_index]
    end = palette[min(start_index + 1, len(palette) - 1)]
    red = _mix_channel(start[0], end[0], ratio)
    green = _mix_channel(start[1], end[1], ratio)
    blue = _mix_channel(start[2], end[2], ratio)
    return f"#{red:02x}{green:02x}{blue:02x}"


def _build_watercolor_frame(
    columns: int,
    rows: int,
    phase: float,
    watercolor_seed: int = 0,
) -> Text:
    """Build a full-terminal watercolor wash with a centered ink logo."""
    width = max(columns, _TITLE_WIDTH)
    height = max(rows, len(_TITLE_ROWS))
    logo_left = max(0, (width - _TITLE_WIDTH) // 2)
    # Bias any odd leftover row upward (ceiling, not floor) so the
    # wordmark reads as vertically centered instead of sitting high.
    logo_top = max(0, (height - len(_TITLE_ROWS) + 1) // 2)
    lines: list[str | Text] = []

    for row_index in range(height):
        spans: list[str | Text] = []
        current_text = ""
        current_color: str | None = None
        current_background: str | None = None
        logo_row = row_index - logo_top

        for column in range(width):
            logo_column = column - logo_left
            character = " "
            color: str | None = None
            if 0 <= logo_row < len(_TITLE_ROWS):
                title_row = _TITLE_ROWS[logo_row]
                if 0 <= logo_column < len(title_row):
                    character = title_row[logo_column]
                    if character != " ":
                        color = _LOGO_INK
            if color is None and 0 < logo_row < len(_TITLE_ROWS):
                shadow_row = _TITLE_ROWS[logo_row - 1]
                shadow_column = logo_column - 1
                if (
                    0 <= shadow_column < len(shadow_row)
                    and shadow_row[shadow_column] != " "
                ):
                    character = shadow_row[shadow_column]
                    color = _LOGO_SHADOW

            background = _get_watercolor_color(
                column / max(width - 1, 1),
                row_index / max(height - 1, 1),
                phase,
                watercolor_seed,
            )

            if current_text and (
                color != current_color or background != current_background
            ):
                spans.append(
                    Text(
                        current_text,
                        color=current_color,
                        background=current_background,
                        modifiers=("bold",) if current_color else (),
                    )
                )
                current_text = ""

            current_text += character
            current_color = color
            current_background = background

        if current_text:
            spans.append(
                Text(
                    current_text,
                    color=current_color,
                    background=current_background,
                    modifiers=("bold",) if current_color else (),
                )
            )
        lines.append(Text(spans))

    # This is a cell canvas, not prose. Wrapping enables ratatui's whitespace
    # trimming, which would discard background-only rows and trailing wash
    # cells around the logo.
    return Text(lines, wrap=False, fit_content=False)


class TitleSplash(Grid):
    """A terminal-sized watercolor wash with a centered xnano wordmark."""

    canvas: Text = Field(default=Text(""), width="1fr", height="1fr")

    phase: float = Field(default=0.0, state=True)
    watercolor_seed: int = Field(
        default_factory=lambda: random.getrandbits(32),
        state=True,
    )

    @on_tick
    def _update_gradient(self) -> None:
        """Advance the slow multi-layer pigment drift."""
        self.phase += 0.034

    def grid_render(self) -> None:
        """Refresh the animated wash and centered ink wordmark."""
        self.canvas = _build_watercolor_frame(
            max(self.columns, 1),
            max(self.rows, 1),
            self.phase,
            self.watercolor_seed,
        )


class DemoSequence(Grid):
    """A seamless title-to-panels sequence for ``python -m xnano``."""

    content: Grid = Field(
        default_factory=TitleSplash,
        width="1fr",
        height="1fr",
    )

    frame_count: int = Field(default=0, state=True)
    showing_title: bool = Field(default=True, state=True)
    transitioning: bool = Field(default=False, state=True)
    transition_frame: int = Field(default=0, state=True)

    def _begin_transition(self) -> None:
        """Settle the watercolor into the shared transition wash."""
        if not self.showing_title or self.transitioning:
            return
        self.transitioning = True
        self.transition_frame = 0
        self.grid_play_effect(
            "fade_to",
            duration_ms=_TRANSITION_FRAMES * 16,
            color=_BRIDGE_FOREGROUND,
            background=_BRIDGE_BACKGROUND,
            interpolation="sine_in_out",
            fields=["content"],
        )

    def _show_panels(self) -> None:
        """Reveal panels from the same wash used to close the title."""
        self.showing_title = False
        self.transitioning = False
        self.content = XnanoDemo()
        self.grid_play_effect(
            "fade_from_both",
            duration_ms=720,
            color=_BRIDGE_FOREGROUND,
            background=_BRIDGE_BACKGROUND,
            interpolation="sine_in_out",
            fields=["content"],
        )

    @on_tick
    def _advance_sequence(self) -> None:
        """Advance the splash timer and reveal the demo panels."""
        if not self.showing_title:
            return
        if self.transitioning:
            self.transition_frame += 1
            if self.transition_frame >= _TRANSITION_FRAMES:
                self._show_panels()
            return
        self.frame_count += 1
        if self.frame_count >= _SPLASH_FRAMES:
            self._begin_transition()

    @on_keyboard
    def _handle_keyboard(self, context) -> None:
        """Allow the splash to be skipped or the application to be closed."""
        if not self.showing_title or context.keyboard is None:
            return
        key = context.keyboard.key
        if key in ("q", "esc"):
            context.terminal.request_exit()
        elif key in ("enter", "space"):
            self._begin_transition()


def run_demo() -> None:
    """Launch the title and interactive feature tour in one session."""
    Terminal(title="xnano · feature tour", tick_interval=16).run(
        DemoSequence()
    )


__all__ = ("DemoSequence", "TitleSplash", "run_demo")
