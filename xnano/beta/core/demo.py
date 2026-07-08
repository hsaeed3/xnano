"""xnano.beta.core.demo

---

A self-contained, animated showcase application for the ``xnano``
framework, styled after the classic ``ratatui`` splash and the
``python -m rich`` feature tour.
"""

from __future__ import annotations

import math
import random
from typing import Callable

from xnano.beta import Field, Grid, Terminal, on_keyboard, on_tick
from xnano.beta.color import (
    Color,
    TailwindColorName,
    TailwindColorShade,
    tailwind_color,
)
from xnano.beta.components import Text
from xnano.beta.types import CharacterModifier


_SPECTRUM: list[Color] = [
    tailwind_color("sky", 400),
    tailwind_color("cyan", 400),
    tailwind_color("teal", 400),
    tailwind_color("emerald", 400),
    tailwind_color("lime", 400),
    tailwind_color("amber", 400),
    tailwind_color("orange", 500),
    tailwind_color("rose", 500),
    tailwind_color("fuchsia", 500),
    tailwind_color("violet", 500),
    tailwind_color("indigo", 500),
    tailwind_color("blue", 500),
]
"""Cyclic gradient ring used for the banner and all accents."""

_SWATCH_PALETTES: list[TailwindColorName] = [
    "sky", "cyan", "teal", "emerald", "lime", "amber", "orange",
    "red", "rose", "fuchsia", "violet", "indigo", "blue", "slate",
]
_SWATCH_SHADES: list[TailwindColorShade] = [
    200, 300, 400, 500, 600, 700, 800, 900,
]

_MODIFIERS: list[tuple[CharacterModifier, str]] = [
    ("bold", "Emphasised, heavier weight"),
    ("dim", "Reduced intensity"),
    ("italic", "Slanted for emphasis"),
    ("underline", "Underscored text"),
    ("slow_blink", "Attention-grabbing pulse"),
    ("reversed", "Swapped fg / bg"),
]

_FEATURES = [
    "Declarative Grid layouts with flex-style sizing",
    "20+ Tailwind palettes, hex, RGB & named colors",
    "Ratatui widgets: tables, charts, gauges, canvas",
    "tachyonfx effects: fade, sweep, coalesce, slide",
    "Reactive @on_keyboard / @on_tick / @on_mouse hooks",
    "A Rust + PyO3 core for fast, flicker-free frames",
]

_TABS = ["Home", "Palette", "Type", "Charts", "About"]
_SPARK_BLOCKS = " ▁▂▃▄▅▆▇█"


# Each glyph is five equal-width rows; "#" is a filled cell.
_GLYPHS: dict[str, list[str]] = {
    "X": ["#   #", " # # ", "  #  ", " # # ", "#   #"],
    "N": ["#   #", "##  #", "# # #", "#  ##", "#   #"],
    "A": [" ### ", "#   #", "#####", "#   #", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", " ### "],
}
_WORDMARK = "XNANO"
_GLYPH_GAP = 2


def _color_hex(color: Color) -> str:
    return f"#{color.r:02x}{color.g:02x}{color.b:02x}"


def _lerp(start: int, end: int, ratio: float) -> int:
    return int(start + (end - start) * ratio)


def _spectrum_hex(position: float) -> str:
    """Sample the cyclic spectrum ring at ``position`` (wraps at 1.0)."""
    position = position % 1.0
    scaled = position * len(_SPECTRUM)
    index = int(scaled) % len(_SPECTRUM)
    nxt = (index + 1) % len(_SPECTRUM)
    ratio = scaled - int(scaled)
    start, end = _SPECTRUM[index], _SPECTRUM[nxt]
    return (
        f"#{_lerp(start.r, end.r, ratio):02x}"
        f"{_lerp(start.g, end.g, ratio):02x}"
        f"{_lerp(start.b, end.b, ratio):02x}"
    )


def _wordmark_rows() -> list[str]:
    """Compose the five doubled-width rows of the ``XNANO`` wordmark."""
    rows: list[str] = []
    for row_index in range(5):
        segments: list[str] = []
        for letter in _WORDMARK:
            source = _GLYPHS[letter][row_index]
            segments.append(
                "".join("██" if cell == "#" else "  " for cell in source)
            )
        rows.append((" " * _GLYPH_GAP).join(segments))
    return rows


_WORDMARK_ROWS = _wordmark_rows()
_WORDMARK_WIDTH = max(len(row) for row in _WORDMARK_ROWS)


def _banner(tick: float) -> Text:
    """Build the animated gradient wordmark plus tagline."""
    lines: list[str | Text] = [Text("")]
    for row in _WORDMARK_ROWS:
        spans: list[str | Text] = []
        for column, char in enumerate(row):
            if char == " ":
                spans.append(Text(" "))
                continue
            hue = column / _WORDMARK_WIDTH * 1.4 - tick * 0.012
            spans.append(Text(char, color=_spectrum_hex(hue)))
        lines.append(Text(spans))
    lines.append(Text(""))
    lines.append(
        Text(
            "a python tui framework · ratatui + tachyonfx",
            color=tailwind_color("slate", 500),
            modifiers=("italic",),
        )
    )
    return Text(lines, align="center")



def _tab_bar(selected: int, tick: float) -> Text:
    accent = _spectrum_hex(-tick * 0.012)
    parts: list[str | Text] = [Text("  ")]
    for index, name in enumerate(_TABS):
        active = index == selected
        marker = "●" if active else "○"
        parts.append(
            Text(
                f"{marker} {index + 1} {name}",
                color=accent if active else tailwind_color("slate", 600),
                modifiers=("bold",) if active else (),
            )
        )
        if index < len(_TABS) - 1:
            parts.append(
                Text("   ·   ", color=tailwind_color("slate", 800))
            )
    return Text(parts)


def _spark(data: list[int], max_value: int, tick: float) -> Text:
    """Render a sample series as a gradient block sparkline."""
    ceiling = max(max_value, 1)
    spans: list[str | Text] = []
    total = max(len(data), 1)
    for index, value in enumerate(data):
        level = min(int(value / ceiling * 8), 8)
        hue = index / total - tick * 0.01
        spans.append(Text(_SPARK_BLOCKS[level], color=_spectrum_hex(hue)))
    return Text(spans)


def _gauge(label: str, ratio: float, width: int, color: str) -> Text:
    filled = max(0, min(width, int(ratio * width)))
    return Text(
        [
            Text(f"  {label:<12}", color=tailwind_color("slate", 300)),
            Text("█" * filled, color=color),
            Text("░" * (width - filled), color=tailwind_color("slate", 700)),
            Text(f"  {ratio * 100:4.0f}%\n", color=tailwind_color("slate", 500)),
        ]
    )


def _home_panel(demo: "Demo") -> Text:
    lines: list[str | Text] = [
        Text("\n"),
        Text(
            "  Welcome to xnano\n",
            color=tailwind_color("slate", 100),
            modifiers=("bold",),
        ),
        Text(
            "  Build reactive terminal interfaces in pure Python.\n\n",
            color=tailwind_color("slate", 400),
        ),
    ]
    for index, feature in enumerate(_FEATURES):
        hue = index / len(_FEATURES)
        lines.append(
            Text(
                [
                    Text("  ◆ ", color=_spectrum_hex(hue)),
                    Text(
                        feature + "\n", color=tailwind_color("slate", 300)
                    ),
                ]
            )
        )
    lines.append(Text("\n"))
    lines.append(
        Text("  live\n", color=tailwind_color("slate", 500))
    )
    lines.append(Text("  "))
    lines.append(_spark(demo.history[-56:], 100, demo.tick))
    return Text(lines)


def _palette_panel(demo: "Demo") -> Text:
    lines: list[str | Text] = [
        Text(
            "\n  Tailwind color palette\n\n",
            color=tailwind_color("slate", 100),
            modifiers=("bold",),
        )
    ]
    for palette in _SWATCH_PALETTES:
        row: list[str | Text] = [
            Text(f"  {palette:<9}", color=tailwind_color("slate", 400))
        ]
        for shade in _SWATCH_SHADES:
            row.append(Text("██", color=tailwind_color(palette, shade)))
        row.append(Text("\n"))
        lines.append(Text(row))
    lines.append(
        Text(
            "\n  shades 200 → 900, left to right\n",
            color=tailwind_color("slate", 600),
            modifiers=("italic",),
        )
    )
    return Text(lines)


def _type_panel(demo: "Demo") -> Text:
    lines: list[str | Text] = [
        Text(
            "\n  Text styles & modifiers\n\n",
            color=tailwind_color("slate", 100),
            modifiers=("bold",),
        )
    ]
    for name, description in _MODIFIERS:
        lines.append(
            Text(
                [
                    Text(
                        f"  {name:<12}",
                        color=tailwind_color("sky", 300),
                        modifiers=(name,),
                    ),
                    Text(
                        description + "\n",
                        color=tailwind_color("slate", 400),
                    ),
                ]
            )
        )
    lines.append(
        Text(
            "\n  Named & tailwind colors\n",
            color=tailwind_color("slate", 100),
            modifiers=("bold",),
        )
    )
    swatch_row: list[str | Text] = [Text("  ")]
    for name in ("red", "orange", "gold", "springgreen", "cyan", "violet"):
        swatch_row.append(Text(f"{name} ", color=name))
    lines.append(Text(swatch_row))
    lines.append(Text("\n\n"))

    sentence = "the quick brown fox jumps over the lazy dog"
    grad: list[str | Text] = [Text("  ")]
    for index, char in enumerate(sentence):
        hue = index / len(sentence) - demo.tick * 0.01
        grad.append(Text(char, color=_spectrum_hex(hue), modifiers=("bold",)))
    lines.append(Text(grad))
    lines.append(
        Text(
            "\n\n  gradient text animates via @on_tick\n",
            color=tailwind_color("slate", 600),
            modifiers=("italic",),
        )
    )
    return Text(lines)


def _charts_panel(demo: "Demo") -> Text:
    width = max(16, min(48, demo.columns // 2))
    lines: list[str | Text] = [
        Text(
            "\n  Live metrics\n\n",
            color=tailwind_color("slate", 100),
            modifiers=("bold",),
        )
    ]
    labels = ("throughput", "latency", "errors", "queue")
    colors = (
        _color_hex(tailwind_color("emerald", 400)),
        _color_hex(tailwind_color("sky", 400)),
        _color_hex(tailwind_color("rose", 400)),
        _color_hex(tailwind_color("amber", 400)),
    )
    for label, color, ratio in zip(labels, colors, demo.gauges):
        lines.append(_gauge(label, ratio, width, color))
    lines.append(
        Text(
            "\n  cpu history\n  ",
            color=tailwind_color("slate", 500),
        )
    )
    lines.append(_spark(demo.history[-width * 2 :], 100, demo.tick))
    lines.append(
        Text(
            "\n  net history\n  ",
            color=tailwind_color("slate", 500),
        )
    )
    lines.append(_spark(demo.history_2[-width * 2 :], 100, demo.tick))
    return Text(lines)


def _about_panel(demo: "Demo") -> Text:
    stack = [
        ("User app", "Grid subclass + @on_* hooks"),
        ("xnano.beta", "layout, events, render IR, colors"),
        ("xnano_core.core", "session, nodes, events"),
        ("rust.native", "ratatui / crossterm / tachyonfx"),
    ]
    lines: list[str | Text] = [
        Text(
            "\n  About xnano\n\n",
            color=tailwind_color("slate", 100),
            modifiers=("bold",),
        ),
        Text(
            "  A declarative TUI framework layering an ergonomic\n"
            "  Python API over a compiled Rust rendering core.\n\n",
            color=tailwind_color("slate", 400),
        ),
        Text(
            "  Layer stack\n",
            color=tailwind_color("slate", 300),
            modifiers=("bold",),
        ),
    ]
    for index, (name, detail) in enumerate(stack):
        hue = index / len(stack)
        lines.append(
            Text(
                [
                    Text("  ▸ ", color=_spectrum_hex(hue)),
                    Text(
                        f"{name:<18}",
                        color=tailwind_color("slate", 200),
                    ),
                    Text(
                        detail + "\n", color=tailwind_color("slate", 500)
                    ),
                ]
            )
        )
    lines.append(Text("\n"))
    lines.append(
        Text(
            "  docs   ",
            color=tailwind_color("slate", 500),
        )
    )
    lines.append(
        Text("github.com/hsaeed3/xnano\n", color=tailwind_color("sky", 400))
    )
    return Text(lines)


_PANELS: list[Callable[["Demo"], Text]] = [
    _home_panel,
    _palette_panel,
    _type_panel,
    _charts_panel,
    _about_panel,
]



class Demo(Grid, direction="vertical", gap=0):
    """The ``xnano`` feature-tour splash application."""

    header: str = Field(
        default="  ◆ xnano  ·  v1.0.0b2  ·  a terminal ui framework",
        height=1,
        color=tailwind_color("sky", 400),
        modifiers=["bold"],
    )
    banner: Text = Field(default=Text(""), height=8)
    tabs: Text = Field(default=Text(""), height=1)
    body: Text = Field(
        default=Text(""),
        border="rounded",
        border_color=tailwind_color("slate", 700),
        padding=(0, 1),
    )
    footer: str = Field(
        default="",
        height=1,
        color=tailwind_color("slate", 600),
    )

    selected_tab: int = Field(default=0, state=True)
    tick: float = Field(default=0.0, state=True)
    history: list = Field(
        default_factory=lambda: [random.randint(20, 70) for _ in range(120)],
        state=True,
    )
    history_2: list = Field(
        default_factory=lambda: [random.randint(10, 60) for _ in range(120)],
        state=True,
    )
    gauges: list = Field(
        default_factory=lambda: [0.62, 0.34, 0.08, 0.45],
        state=True,
    )

    def _select(self, index: int) -> None:
        if index == self.selected_tab:
            return
        self.selected_tab = index % len(_TABS)
        self.grid_play_effect(
            "coalesce",
            duration_ms=260,
            fields=["body"],
        )

    @on_keyboard
    def _on_key(self, ctx) -> None:
        keyboard = ctx.keyboard
        if keyboard is None:
            return
        key = keyboard.key
        if key in ("right", "l"):
            self._select((self.selected_tab + 1) % len(_TABS))
        elif key in ("left", "h"):
            self._select((self.selected_tab - 1) % len(_TABS))
        elif key in ("q", "esc"):
            ctx.terminal.request_exit()
        elif isinstance(key, str) and key in "12345" and len(key) == 1:
            self._select(int(key) - 1)

    @on_tick
    def _animate(self) -> None:
        self.tick += 1.0

        self.history.pop(0)
        drift = random.randint(-12, 12)
        self.history.append(
            max(0, min(100, self.history[-1] + drift))
        )
        self.history_2.pop(0)
        self.history_2.append(
            max(0, min(100, self.history_2[-1] + random.randint(-12, 12)))
        )

        phase = self.tick * 0.05
        self.gauges = [
            0.5 + 0.35 * math.sin(phase),
            0.5 + 0.35 * math.sin(phase + 1.6),
            0.15 + 0.14 * (math.sin(phase * 0.7) + 1) / 2,
            0.5 + 0.35 * math.sin(phase + 3.1),
        ]

    def grid_render(self) -> None:
        self.banner = _banner(self.tick)
        self.tabs = _tab_bar(self.selected_tab, self.tick)
        self.body = _PANELS[self.selected_tab](self)
        self.grid_set_field(
            "body", title=f" {_TABS[self.selected_tab]} "
        )
        self.footer = (
            "  [←/→ h/l] switch   [1-5] jump   [q] quit"
            "     xnano showcase"
        )


def run_demo() -> None:
    """Launch the interactive ``xnano`` showcase and block until exit."""
    Terminal(title="xnano", tick_interval=40).run(Demo())


__all__ = ("Demo", "run_demo")
