"""xnano.core.demo.panels

---

A compact, interactive feature tour for the ``xnano`` framework.
"""

from __future__ import annotations

import math
import random

from xnano import __version__
from xnano.color import Color, tailwind_color
from xnano.components.sparkline import Sparkline
from xnano.components.text import Text
from xnano.fields import Field
from xnano.grid import Grid
from xnano.hooks import on_keyboard, on_tick
from xnano.terminal import Terminal


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
            ("Grid", "declarative, nested flex layouts"),
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
            ("Your app", "Grid + Field + @on_* hooks"),
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


class LowerPanels(Grid, direction="horizontal", gap=1):
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


class CenterPanels(Grid, direction="vertical", gap=1):
    """The primary feature window and its live supporting panels."""

    feature: Text = Field(
        default=Text(""),
        border="double",
        border_color=tailwind_color("violet", 500),
        title=" Overview ",
        padding=(1, 2),
    )
    lower: LowerPanels = Field(default_factory=LowerPanels, height=8)


class SidePanels(Grid, direction="vertical", gap=1):
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


class ShowcasePanels(Grid, direction="horizontal", gap=1):
    """The main multi-window area of the demo."""

    center: CenterPanels = Field(default_factory=CenterPanels)
    side: SidePanels = Field(default_factory=SidePanels, width=28)


class XnanoDemo(Grid, direction="vertical", gap=0):
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
                Text(f" v{__version__} ", color=tailwind_color("slate", 300)),
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


def run_demo() -> None:
    """Launch the interactive xnano feature tour."""
    Terminal(title="xnano · feature tour", tick_interval=16).run(XnanoDemo())


__all__ = ("XnanoDemo", "run_demo")


if __name__ == "__main__":
    run_demo()
