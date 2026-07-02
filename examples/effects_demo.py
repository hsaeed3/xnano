"""xnano example — effects_demo.py

Visual effects and animation transitions demo powered by tachyonfx (xnano.effect).
"""

from __future__ import annotations

import sys
import time

from xnano.color import Color
from xnano.effects import (
    EffectManager,
    coalesce,
    delay,
    dissolve,
    fade_from_fg,
    fade_to_fg,
    ping_pong,
    repeating,
    slide_in,
    slide_out,
    sweep_in,
)
from xnano.events import poll_event
from xnano.layout import Constraint, Layout
from xnano.style import Borders, Style
from xnano.tailwind import tailwind
from xnano.terminal import Frame, Terminal
from xnano.text import Line
from xnano.widgets import Block, Paragraph


class EffectsDemo:
    def __init__(self) -> None:
        self.effect_manager = EffectManager()
        self.delta_ms = 16

        # Style Definitions
        self.bg_style = Style(background="#0f172a")  # Slate 900
        self.border_style = Style(foreground=tailwind("teal", 500))
        self.header_style = Style(
            foreground="white",
            background=tailwind("teal", 900),
            modifiers="bold",
        )
        self.instruction_style = Style(
            foreground=tailwind("slate", 400), modifiers="italic"
        )

        # Set up a continuous background pulse effect on the main header
        # Using a ping-pong fade of the foreground from cyan to indigo
        pulse = ping_pong(
            fade_to_fg(
                duration_ms=1500,
                color=tailwind("indigo", 400),
            )
        )
        self.effect_manager.add_unique("header_pulse", pulse)

        self.current_effect_name = "None"
        self.trigger_coalesce()  # Trigger initial effect

    def trigger_coalesce(self) -> None:
        self.current_effect_name = "Coalesce (Typewriter Assemble)"
        # Coalesce letters of text into place over 1000ms
        eff = coalesce(duration_ms=1200)
        self.effect_manager.add_unique("demo_card", eff)

    def trigger_fade(self) -> None:
        self.current_effect_name = "Fade (Teal ↔ Purple)"
        # Fade foreground color to violet
        eff = ping_pong(
            fade_to_fg(
                duration_ms=1000,
                color=tailwind("violet", 400),
            )
        )
        self.effect_manager.add_unique("demo_card", eff)

    def trigger_dissolve(self) -> None:
        self.current_effect_name = "Dissolve (Random Pixel Fade)"
        # Dissolve cells over 1500ms
        eff = dissolve(duration_ms=1500)
        self.effect_manager.add_unique("demo_card", eff)

    def trigger_sweep(self) -> None:
        self.current_effect_name = "Sweep In (Laser Scanner)"
        # Sweep effect from left to right: direction, gradient_length, randomness, color, duration_ms
        eff = sweep_in(
            "left_to_right",
            5,
            0,
            tailwind("teal", 500),
            800,
        )
        self.effect_manager.add_unique("demo_card", eff)

    def draw(self, frame: Frame) -> None:
        area = frame.area()

        # Layout: Header (1), Content Area (fill), Help Footer (2)
        layout = Layout(
            direction="vertical",
            constraints=[
                Constraint.length(1),
                Constraint.fill(1),
                Constraint.length(3),
            ],
        )
        splits = layout.split(area)
        header_area, content_area, footer_area = (
            splits[0],
            splits[1],
            splits[2],
        )

        # 1. Header Banner
        header = Paragraph(
            Line("  TACHYONFX VISUAL EFFECTS ANIMATION DEMO  "),
            style=self.header_style,
        )
        frame.render_widget(header, header_area)

        # 2. Main Content Card
        card = Paragraph(
            "\n"
            "   ___                 _   _   \n"
            "  / _ \\               | | (_)  \n"
            " / /_\\ \\_ __   ___  __| |  _  ___  _ __  _   _ \n"
            " |  _  | '_ \\ / _ \\/ _` | | |/ _ \\| '_ \\| | | |\n"
            " | | | | | | |  __/ (_| | | | (_) | | | | |_| |\n"
            " \\_| |_/_| |_|\\___|\\__,_| |_|\\___/|_| |_|\\__, |\n"
            "                         / |             __/ |\n"
            "                        |__/            |___/ \n"
            "\n"
            f"          [ CURRENT EFFECT: {self.current_effect_name} ]\n"
            "          (Animations render smoothly at 60 FPS in pure rust/python)",
            block=Block(
                title=" Animation Canvas ",
                borders="all",
                border_type="double",
                border_style=self.border_style,
            ),
            style=Style(foreground=tailwind("teal", 400)),
        )
        frame.render_widget(card, content_area)

        # 3. Footer instructions
        footer = Paragraph(
            "Press keys to trigger animations:\n"
            "  [C] Coalesce  ●  [F] Pulse Fade  ●  [D] Dissolve  ●  [S] Laser Sweep\n"
            "  [Ctrl+C] Quit Demo",
            style=self.instruction_style,
        )
        frame.render_widget(footer, footer_area)

        # Process active effects
        frame.process_effects(
            self.effect_manager, getattr(self, "delta_ms", 16), area
        )


def main() -> None:
    demo = EffectsDemo()
    last_tick = time.time()

    with Terminal() as term:
        term.clear()

        while True:
            # Poll for input with a tiny 16ms wait to achieve 60 FPS update rate!
            event = poll_event(16)
            if event and event.keyboard and event.keyboard.is_press:
                if event.keyboard.matches("ctrl+c") or event.keyboard.matches(
                    "q"
                ):
                    break
                elif event.keyboard.matches("c"):
                    demo.trigger_coalesce()
                elif event.keyboard.matches("f"):
                    demo.trigger_fade()
                elif event.keyboard.matches("d"):
                    demo.trigger_dissolve()
                elif event.keyboard.matches("s"):
                    demo.trigger_sweep()

            # Calculate time delta for fluid animation processing
            now = time.time()
            delta_ms = int((now - last_tick) * 1000)
            last_tick = now
            demo.delta_ms = delta_ms

            term.draw(demo.draw)


if __name__ == "__main__":
    main()
