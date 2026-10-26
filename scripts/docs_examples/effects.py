"""
Eight cards, each playing tachyonfx effects: most leave with one and come back with another.

Every card is a buffer of full blocks, and its effects start on it with ``card.fx``: the
keys ``1`` to ``8`` play the effects named under a card. A card that leaves with one effect
comes back with the next, which starts just before the first one ends, so the card never
shows in between. Run it with ``python effects.py`` and press ``q`` to quit.
"""

from typing import Any

import xnano
from xnano.buffers import Buffer, Cell

COLORS = (
    (232, 118, 170),  # pastel pink
    (148, 108, 230),  # purple
    (96, 152, 236),  # pastel blue
    (228, 160, 62),  # light amber
)
INK = (21, 23, 28)
CARD_WIDTH, CARD_HEIGHT = 18, 9
STEP_SECONDS = 0.5
INK_SWEEP = {"color": INK, "gradient_length": 6, "randomness": 3}
# each card's effects in order, by name with their settings: a card leaves with the first
# and comes back with the second, or plays one effect that ends where it started
EFFECTS: tuple[tuple[tuple[str, dict[str, Any]], ...], ...] = (
    (("dissolve", {}), ("coalesce", {})),
    (("sweep_out", INK_SWEEP), ("sweep_in", INK_SWEEP)),
    (("hsl_shift", {"foreground": (360.0, 0.0, 0.0)}),),
    (
        ("evolve_into", {"symbols": "blocks_vertical"}),
        ("evolve_from", {"symbols": "blocks_vertical"}),
    ),
    (("slide_out", {"color": INK}), ("slide_in", {"color": INK})),
    (("fade_to", {"foreground": INK}), ("fade_from", {"foreground": INK})),
    (("paint", {"foreground": COLORS[0]}), ("fade_from", {"foreground": COLORS[0]})),
    (("lighten", {"foreground": 1.0}), ("fade_from", {"foreground": "white"})),
)


def blend(
    start: tuple[int, int, int], end: tuple[int, int, int], share: float
) -> tuple[int, int, int]:
    """The color ``share`` of the way from ``start`` to ``end``."""
    red, green, blue = (
        round(first + (second - first) * share)
        for first, second in zip(start, end, strict=True)
    )
    return red, green, blue


def card(index: int) -> Buffer:
    """A card of full blocks that fades from one color to the next, top to bottom."""
    top, bottom = COLORS[index % 4], COLORS[(index + 1) % 4]
    buffer = Buffer(width=CARD_WIDTH, height=CARD_HEIGHT)
    for row in range(CARD_HEIGHT):
        color = blend(top, bottom, row / (CARD_HEIGHT - 1))
        for column in range(CARD_WIDTH):
            buffer[column, row] = Cell("█", foreground=color)
    return buffer


with xnano.open(title="effects") as terminal:
    cards = []
    for index, steps in enumerate(EFFECTS):
        x, y = 1 + index % 4 * (CARD_WIDTH + 2), index // 4 * (CARD_HEIGHT + 3)
        cards.append(terminal.screen.write(card(index), x=x, y=y))
        # the card's number, then the names of its effects, one per line
        terminal.screen.write(f"{index + 1}", x=x, y=y + CARD_HEIGHT, dim=True)
        for line, (name, _) in enumerate(steps):
            terminal.screen.write(
                f"fx.{name}", x=x + 2, y=y + CARD_HEIGHT + line, bold=line == 0
            )
    hint = "1 – 8  play the effects of a card  ·  q  quit"
    terminal.screen.write(hint, x="center", y="bottom", dim=True)

    @terminal.hook(on="key", keys=list("12345678"), if_running="overlap")
    async def play(context: xnano.Context) -> None:
        """Play the effects of the card whose number was pressed, one after the other."""
        index = int(context.keyboard.key or "1") - 1
        steps = EFFECTS[index]
        for number, (name, settings) in enumerate(steps):
            if number:
                await context.clock.sleep_async(STEP_SECONDS)
            seconds = STEP_SECONDS * 2 / len(steps)  # a single effect takes both steps
            if number + 1 < len(steps):
                seconds += 0.1  # on past the wait, so the card never shows in between
            start = getattr(cards[index].fx, name)
            start(duration_milliseconds=round(seconds * 1000), **settings)

    terminal.run(stop_on="q")
