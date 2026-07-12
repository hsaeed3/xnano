"""xnano._demo

---

The ``python -m xnano`` feature-showcase application: a compact,
interactive feature tour for the ``xnano`` framework, opened by an
animated title stage.
"""

from __future__ import annotations

import functools
import math
import random
from typing import TypeAlias

import xnano
from xnano.color import Color, tailwind_color
from xnano.components.sparkline import Sparkline
from xnano.components.text import Text
from xnano.events import on_keyboard, on_tick
from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.tui.terminal import Terminal

_COLOR_RING = [
    tailwind_color("rose", 500),
    tailwind_color("orange", 400),
    tailwind_color("amber", 300),
    tailwind_color("lime", 400),
    tailwind_color("emerald", 400),
    tailwind_color("cyan", 400),
    tailwind_color("sky", 400),
    tailwind_color("indigo", 400),
    tailwind_color("violet", 500),
    tailwind_color("fuchsia", 500),
]
"""Accent colors shared by the title and feature panels."""

_PAGES = ("Overview", "Components", "Architecture")
_EFFECT_NAMES = {
    "c": "coalesce",
    "f": "fade",
    "d": "dissolve",
    "s": "sweep_in",
}


def _get_color_as_hex(color: Color) -> str:
    """Return an xnano color as a hexadecimal string."""
    return f"#{color.r:02x}{color.g:02x}{color.b:02x}"


def _get_ring_color(position: float) -> str:
    """Sample the cyclic showcase color ring."""
    scaled = (position % 1.0) * len(_COLOR_RING)
    start_index = int(scaled) % len(_COLOR_RING)
    end_index = (start_index + 1) % len(_COLOR_RING)
    ratio = scaled - int(scaled)
    start = _COLOR_RING[start_index]
    end = _COLOR_RING[end_index]
    return (
        f"#{int(start.r + (end.r - start.r) * ratio):02x}"
        f"{int(start.g + (end.g - start.g) * ratio):02x}"
        f"{int(start.b + (end.b - start.b) * ratio):02x}"
    )


def _build_tabs(selected_page: int) -> Text:
    """Build the numbered page navigator."""
    parts: list[str | Text] = [Text("  ")]
    for page_index, name in enumerate(_PAGES):
        selected = page_index == selected_page
        parts.append(
            Text(
                f" {page_index + 1}  {name} ",
                color="black" if selected else tailwind_color("slate", 400),
                background=(
                    _COLOR_RING[(page_index * 3 + 5) % len(_COLOR_RING)]
                    if selected
                    else None
                ),
                modifiers=("bold",) if selected else (),
            )
        )
        parts.append(Text("  "))
    return Text(parts)


def _build_gauge(label: str, ratio: float, width: int, color: str) -> Text:
    """Build a compact labeled text gauge."""
    filled = max(0, min(width, round(ratio * width)))
    return Text(
        [
            Text(f" {label:<8}", color=tailwind_color("slate", 400)),
            Text("━" * filled, color=color),
            Text("─" * (width - filled), color=tailwind_color("slate", 800)),
            Text(f" {ratio:>4.0%}\n", color=tailwind_color("slate", 300)),
        ]
    )


def _build_feature_page(page: int, phase: float) -> Text:
    """Build the content of the currently selected feature page."""
    if page == 0:
        items = (
            ("BaseGrid", "declarative, nested flex layouts"),
            ("Text", "truecolor spans, alignment & styles"),
            ("Hooks", "keyboard, mouse, resize & tick events"),
            ("Effects", "tachyonfx animations on any field"),
            ("Core", "ratatui + crossterm through Rust/PyO3"),
        )
        heading = "Build lively terminal apps in pure Python."
    elif page == 1:
        items = (
            ("Text", "span · line · paragraph"),
            ("Sparkline", "fast streaming time series"),
            ("Table", "declarative rows and columns"),
            ("Charts", "lines, bars, axes and datasets"),
            ("Canvas", "points, shapes and custom drawing"),
        )
        heading = "Small components, composed into real interfaces."
    else:
        items = (
            ("Your app", "BaseGrid + Field + @on_* hooks"),
            ("xnano", "layout, state, events, render IR"),
            ("core", "scene graph, sessions and effects"),
            ("native", "ratatui · crossterm · tachyonfx"),
            ("terminal", "one fast, flicker-free frame"),
        )
        heading = "A thin Python layer over a serious native core."

    lines: list[str | Text] = [
        Text(heading + "\n\n", color="white", modifiers=("bold",)),
    ]
    for item_index, (name, description) in enumerate(items):
        lines.append(
            Text(
                [
                    Text(" ◆ ", color=_get_ring_color(item_index / 7 - phase)),
                    Text(f"{name:<12}", color=tailwind_color("slate", 200)),
                    Text(
                        description + "\n", color=tailwind_color("slate", 500)
                    ),
                ]
            )
        )
    return Text(lines)


def _build_palette() -> Text:
    """Build the compact Tailwind palette sampler."""
    lines: list[str | Text] = []
    for color_name in ("rose", "amber", "emerald", "cyan", "blue", "violet"):
        row: list[str | Text] = [
            Text(f" {color_name:<8}", color=tailwind_color("slate", 400))
        ]
        for shade in (300, 400, 500, 600, 700, 800):
            row.append(Text("██", color=tailwind_color(color_name, shade)))
        row.append("\n")
        lines.append(Text(row))
    return Text(lines)


def _build_effect_menu(active_effect: str) -> Text:
    """Build the effect keyboard menu."""
    lines: list[str | Text] = []
    for key, effect_name in _EFFECT_NAMES.items():
        active = effect_name == active_effect
        lines.append(
            Text(
                [
                    Text(
                        f" {key.upper()} ",
                        color="black"
                        if active
                        else tailwind_color("cyan", 300),
                        background=(
                            tailwind_color("cyan", 400) if active else None
                        ),
                        modifiers=("bold",),
                    ),
                    Text(
                        f" {effect_name.replace('_', ' '):<10}\n",
                        color="white",
                    ),
                ]
            )
        )
    lines.append(
        Text("\n SPACE  shuffle all", color=tailwind_color("slate", 500))
    )
    return Text(lines)


class LowerPanels(BaseGrid, direction="horizontal", gap=1):
    """The pair of compact live panels below the main feature window."""

    metrics: Text = Field(
        default=Text(""),
        border="rounded",
        border_color=tailwind_color("emerald", 700),
        title=" Live metrics ",
        padding=(0, 1),
    )
    stream: Sparkline = Field(
        default_factory=Sparkline,
        border="rounded",
        border_color=tailwind_color("sky", 700),
        title=" Render stream ",
    )


class CenterPanels(BaseGrid, direction="vertical", gap=1):
    """The primary feature window and its live supporting panels."""

    feature: Text = Field(
        default=Text(""),
        border="double",
        border_color=tailwind_color("violet", 500),
        title=" Overview ",
        padding=(1, 2),
    )
    lower: LowerPanels = Field(default_factory=LowerPanels, height=8)


class SidePanels(BaseGrid, direction="vertical", gap=1):
    """Small independent showcase panels on the right side."""

    palette: Text = Field(
        default_factory=_build_palette,
        height=9,
        border="rounded",
        border_color=tailwind_color("fuchsia", 700),
        title=" Truecolor ",
    )
    effects: Text = Field(
        default=Text(""),
        border="rounded",
        border_color=tailwind_color("cyan", 700),
        title=" Effect lab ",
        padding=(0, 1),
    )
    status: Text = Field(
        default=Text(""),
        height=5,
        border="rounded",
        border_color=tailwind_color("amber", 700),
        title=" Runtime ",
        padding=(0, 1),
    )


class ShowcasePanels(BaseGrid, direction="horizontal", gap=1):
    """The main multi-window area of the demo."""

    center: CenterPanels = Field(default_factory=CenterPanels)
    side: SidePanels = Field(default_factory=SidePanels, width=28)


class XnanoDemo(BaseGrid, direction="vertical", gap=0):
    """A playful, dense, interactive tour of xnano."""

    header: Text = Field(default=Text(""), height=1, width="1fr")
    tabs: Text = Field(default=Text(""), height=1, width="1fr")
    panels: ShowcasePanels = Field(default_factory=ShowcasePanels)
    footer: Text = Field(default=Text(""), height=1, width="1fr")

    selected_page: int = Field(default=0, state=True)
    phase: float = Field(default=0.0, state=True)
    frame_count: int = Field(default=0, state=True)
    active_effect: str = Field(default="coalesce", state=True)
    render_history: list = Field(
        default_factory=lambda: [random.randint(20, 80) for _ in range(100)],
        state=True,
    )
    activity: float = Field(default=0.55, state=True)
    memory: float = Field(default=0.38, state=True)

    def _select_page(self, page: int) -> None:
        """Select a page and animate only the primary window."""
        self.selected_page = page % len(_PAGES)
        self.grid_play_effect("coalesce", duration_ms=240, fields=["panels"])

    def _play_panel_effect(self, key: str) -> None:
        """Play a named effect on the independent effect panel."""
        self.active_effect = _EFFECT_NAMES[key]
        if key == "f":
            self.grid_play_effect(
                "fade",
                duration_ms=650,
                color=tailwind_color("violet", 500),
                fields=["panels"],
            )
        elif key == "s":
            self.grid_play_effect(
                "sweep_in",
                duration_ms=650,
                direction="left_to_right",
                gradient_length=10,
                fields=["panels"],
            )
        elif key == "c":
            self.grid_play_effect(
                "coalesce", duration_ms=650, fields=["panels"]
            )
        else:
            self.grid_play_effect(
                "dissolve", duration_ms=650, fields=["panels"]
            )

    @on_keyboard
    def _handle_keyboard(self, context) -> None:
        """Handle navigation, effect triggers and exit keys."""
        if context.keyboard is None:
            return
        key = context.keyboard.key
        if key in ("right", "l", "tab"):
            self._select_page(self.selected_page + 1)
        elif key in ("left", "h"):
            self._select_page(self.selected_page - 1)
        elif isinstance(key, str) and key in "123":
            self._select_page(int(key) - 1)
        elif key in _EFFECT_NAMES:
            self._play_panel_effect(key)
        elif key == "space":
            chosen_key = random.choice(tuple(_EFFECT_NAMES))
            self._play_panel_effect(chosen_key)
        elif key in ("q", "esc"):
            context.terminal.request_exit()

    @on_tick
    def _update_animation(self) -> None:
        """Advance all live data used by the showcase."""
        self.phase = (self.phase + 0.008) % 1.0
        self.frame_count += 1
        self.activity = 0.56 + math.sin(self.frame_count * 0.08) * 0.22
        self.memory = 0.42 + math.sin(self.frame_count * 0.035 + 2) * 0.12
        self.render_history.pop(0)
        next_value = self.render_history[-1] + random.randint(-14, 14)
        self.render_history.append(max(4, min(100, next_value)))

    def grid_render(self) -> None:
        """Refresh each independently composed window."""
        accent = _get_ring_color(self.phase)
        self.header = Text(
            [
                Text(
                    " ◆ xnano ",
                    color="black",
                    background=accent,
                    modifiers=("bold",),
                ),
                Text(
                    f" v{xnano.__version__} ",
                    color=tailwind_color("slate", 300),
                ),
                Text(
                    "Python ergonomics · Rust speed",
                    color=tailwind_color("slate", 600),
                ),
            ]
        )
        self.tabs = _build_tabs(self.selected_page)
        self.panels.center.feature = _build_feature_page(
            self.selected_page, self.phase
        )
        self.panels.center.grid_set_field(
            "feature", title=f" {_PAGES[self.selected_page]} "
        )
        gauge_width = max(8, min(24, self.columns // 7))
        self.panels.center.lower.metrics = Text(
            [
                _build_gauge("paint", self.activity, gauge_width, accent),
                _build_gauge(
                    "memory",
                    self.memory,
                    gauge_width,
                    _get_color_as_hex(tailwind_color("sky", 400)),
                ),
            ]
        )
        stream_width = max(12, self.columns // 3)
        self.panels.center.lower.stream = Sparkline(
            data=self.render_history[-stream_width:],
            max_value=100,
            colors=tuple(
                _get_ring_color(index / max(stream_width, 1) - self.phase)
                for index in range(stream_width)
            ),
        )
        self.panels.side.effects = _build_effect_menu(self.active_effect)
        self.panels.side.status = Text(
            [
                Text(
                    "● LIVE  ",
                    color=tailwind_color("emerald", 400),
                    modifiers=("bold",),
                ),
                Text(
                    f"frame {self.frame_count:,}\n",
                    color=tailwind_color("slate", 400),
                ),
                Text(
                    "60-ish FPS · native buffer",
                    color=tailwind_color("slate", 600),
                ),
            ]
        )
        self.footer = Text(
            [
                Text(
                    " ←/→ ",
                    color="black",
                    background=tailwind_color("slate", 300),
                    modifiers=("bold",),
                ),
                Text(" pages  ", color=tailwind_color("slate", 500)),
                Text(
                    " 1–3 ",
                    color="black",
                    background=tailwind_color("slate", 300),
                    modifiers=("bold",),
                ),
                Text(" jump  ", color=tailwind_color("slate", 500)),
                Text(
                    " C F D S ",
                    color="black",
                    background=tailwind_color("cyan", 400),
                    modifiers=("bold",),
                ),
                Text(" effects  ", color=tailwind_color("slate", 500)),
                Text(
                    " SPACE ",
                    color="black",
                    background=tailwind_color("violet", 400),
                    modifiers=("bold",),
                ),
                Text(" shuffle  ", color=tailwind_color("slate", 500)),
                Text(
                    " Q ",
                    color="black",
                    background=tailwind_color("rose", 400),
                    modifiers=("bold",),
                ),
                Text(" quit", color=tailwind_color("slate", 500)),
            ]
        )


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
):
    """Build a full-terminal watercolor as a CellCanvas overlay content.

    Returns a ``CellCanvas`` (core Content) so Stage/controllers lower it
    natively; TitleSplash still assigns it to the canvas field.
    """
    from xnano.core.content import CellCanvas, CellSpan

    width = max(columns, _TITLE_WIDTH)
    height = max(rows, len(_TITLE_ROWS))
    logo_left = max(0, (width - _TITLE_WIDTH) // 2)
    logo_top = max(0, (height - len(_TITLE_ROWS) + 1) // 2)
    row_spans: list[tuple] = []

    for row_index in range(height):
        spans: list[CellSpan] = []
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
                    CellSpan(
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
                CellSpan(
                    current_text,
                    color=current_color,
                    background=current_background,
                    modifiers=("bold",) if current_color else (),
                )
            )
        row_spans.append(tuple(spans))

    return CellCanvas(
        width=width,
        height=height,
        rows=tuple(row_spans),
    )


class TitleSplash(BaseGrid):
    """A terminal-sized watercolor wash with a centered xnano wordmark."""

    canvas: object = Field(default=None, width="1fr", height="1fr")

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


class DemoSequence(BaseGrid):
    """A seamless title-to-panels sequence for ``python -m xnano``."""

    content: BaseGrid = Field(
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


__all__ = ("DemoSequence", "TitleSplash", "XnanoDemo", "run_demo")


if __name__ == "__main__":
    run_demo()
