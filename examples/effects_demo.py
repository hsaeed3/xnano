"""xnano example — effects_demo.py

Visual effects and animation demo — press C / F / D / S to switch modes.
"""

from __future__ import annotations

import math
import time

from xnano.color import tailwind_color
from xnano.components.text import Text
from xnano.effects import AbstractEffect, Effect
from xnano.events import on_keyboard, on_tick
from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.terminal import Terminal

_LOGO = (
    "   ___                 _   _   \n"
    "  / _ \\               | | (_)  \n"
    " / /_\\ \\_ __   ___  __| |  _  ___  _ __  _   _ \n"
    " |  _  | '_ \\ / _ \\/ _` | | |/ _ \\| '_ \\| | | |\n"
    " | | | | | | |  __/ (_| | | | (_) | | | | |_| |\n"
    " \\_| |_/_| |_|\\___|\\__,_| |_|\\___/|_| |_|\\__, |\n"
    "                         / |             __/ |\n"
    "                        |__/            |___/ \n"
)

_EFFECTS = {
    "c": "Coalesce (Typewriter Assemble)",
    "f": "Fade (Teal ↔ Purple)",
    "d": "Dissolve (Random Pixel Fade)",
    "s": "Sweep In (Laser Scanner)",
}

_PALETTES = {
    "c": [
        tailwind_color("teal", 400),
        tailwind_color("cyan", 400),
        tailwind_color("sky", 400),
    ],
    "f": [
        tailwind_color("teal", 400),
        tailwind_color("violet", 400),
        tailwind_color("purple", 400),
    ],
    "d": [
        tailwind_color("slate", 600),
        tailwind_color("teal", 300),
        tailwind_color("slate", 400),
    ],
    "s": [
        tailwind_color("teal", 500),
        tailwind_color("teal", 300),
        tailwind_color("cyan", 500),
    ],
}

_EFFECT_DURATION_MS = 900


def _pulsing_color(palette: list, phase: float) -> str:
    t = (math.sin(phase) + 1) / 2
    idx = int(t * (len(palette) - 1))
    c = palette[min(idx, len(palette) - 1)]
    return f"#{c.r:02x}{c.g:02x}{c.b:02x}"


def _build_canvas_effect(key: str) -> AbstractEffect:
    accent = _PALETTES[key][0]
    accent_color = f"#{accent.r:02x}{accent.g:02x}{accent.b:02x}"
    if key == "c":
        return Effect("coalesce", duration_ms=_EFFECT_DURATION_MS)
    if key == "f":
        violet = tailwind_color("violet", 400)
        return Effect(
            "fade",
            color=f"#{violet.r:02x}{violet.g:02x}{violet.b:02x}",
            duration_ms=_EFFECT_DURATION_MS,
        )
    if key == "d":
        return Effect("dissolve", duration_ms=_EFFECT_DURATION_MS)
    return Effect(
        "sweep_in",
        direction="left_to_right",
        gradient_length=14,
        randomness=2,
        color=accent_color,
        duration_ms=_EFFECT_DURATION_MS,
    )


class EffectsDemo(BaseGrid, direction="vertical"):
    header: str = Field(
        default="  TACHYONFX VISUAL EFFECTS ANIMATION DEMO  ",
        height=1,
        color="white",
        background=tailwind_color("teal", 900),
        modifiers=["bold"],
    )
    canvas: Text = Field(
        default=Text(""),
        border="double",
        border_color=tailwind_color("teal", 500),
        title=" Animation Canvas ",
    )
    footer: str = Field(
        default=(
            "Press keys to trigger animations:\n"
            "  [C] Coalesce  ●  [F] Pulse Fade  ●  [D] Dissolve  ●  [S] Laser Sweep\n"
            "  [Ctrl+C] Quit Demo"
        ),
        height=3,
        color=tailwind_color("slate", 400),
        modifiers=["italic"],
    )

    current_key: str = Field(default="c", state=True)
    phase: float = Field(default=0.0, state=True)
    start_time: float = Field(default_factory=time.time, state=True)

    def _switch_effect(self, key: str) -> None:
        self.current_key = key
        self.phase = 0.0
        self.grid_play_effect(_build_canvas_effect(key), fields=["canvas"])

    @on_keyboard("c")
    def _coalesce(self) -> None:
        self._switch_effect("c")

    @on_keyboard("f")
    def _fade(self) -> None:
        self._switch_effect("f")

    @on_keyboard("d")
    def _dissolve(self) -> None:
        self._switch_effect("d")

    @on_keyboard("s")
    def _sweep(self) -> None:
        self._switch_effect("s")

    @on_tick
    def _tick(self) -> None:
        self.phase += 0.08

    def grid_render(self) -> None:
        palette = _PALETTES[self.current_key]
        color = _pulsing_color(palette, self.phase)
        effect_name = _EFFECTS[self.current_key]

        self.canvas = Text(
            [
                Text("\n"),
                Text(_LOGO, color=color),
                Text(
                    f"\n          [ CURRENT EFFECT: {effect_name} ]\n",
                    color=tailwind_color("teal", 300),
                ),
                Text(
                    "          (Animations render smoothly at 60 FPS in pure rust/python)",
                    color=tailwind_color("slate", 500),
                ),
            ]
        )


if __name__ == "__main__":
    Terminal(tick_interval=16).run(EffectsDemo())
