"""xnano._markup

---

Pre-styled text ingestion: ANSI escape parsing into ``Run`` lines.

Everything here returns interface-neutral ``Run`` tuples, so the same
parse feeds terminal rendering (through ``TextBlock``) and web spans.
"""

from __future__ import annotations

import functools
import re

from xnano._types import CharacterModifier
from xnano.core.content import Run

_ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_SGR_PATTERN = re.compile(r"\x1b\[([0-9;]*)m")

# Standard xterm palette for the 16 base colors (30-37 / 90-97).
_BASE_COLORS = (
    "#000000",
    "#cd0000",
    "#00cd00",
    "#cdcd00",
    "#0000ee",
    "#cd00cd",
    "#00cdcd",
    "#e5e5e5",
)
_BRIGHT_COLORS = (
    "#7f7f7f",
    "#ff0000",
    "#00ff00",
    "#ffff00",
    "#5c5cff",
    "#ff00ff",
    "#00ffff",
    "#ffffff",
)

_SGR_MODIFIERS: dict[int, CharacterModifier] = {
    1: "bold",
    2: "dim",
    3: "italic",
    4: "underline",
    5: "slow_blink",
    6: "rapid_blink",
    7: "reversed",
}

_CUBE_STEPS = (0, 95, 135, 175, 215, 255)


def _color_from_256(index: int) -> str:
    """Resolve an xterm 256-color index to a hex color."""
    if index < 8:
        return _BASE_COLORS[index]
    if index < 16:
        return _BRIGHT_COLORS[index - 8]
    if index < 232:
        cube = index - 16
        red = _CUBE_STEPS[cube // 36]
        green = _CUBE_STEPS[(cube // 6) % 6]
        blue = _CUBE_STEPS[cube % 6]
        return f"#{red:02x}{green:02x}{blue:02x}"
    gray = 8 + (index - 232) * 10
    return f"#{gray:02x}{gray:02x}{gray:02x}"


def strip_ansi_escapes(content: str) -> str:
    """Return ``content`` with all ANSI escape sequences removed."""
    return _ANSI_ESCAPE_PATTERN.sub("", content)


def _consume_extended_color(codes: list[int]) -> str | None:
    """Consume a 38/48 extended-color parameter list, returning hex."""
    if not codes:
        return None
    mode = codes.pop(0)
    if mode == 5 and codes:
        return _color_from_256(codes.pop(0) % 256)
    if mode == 2 and len(codes) >= 3:
        red = codes.pop(0) % 256
        green = codes.pop(0) % 256
        blue = codes.pop(0) % 256
        return f"#{red:02x}{green:02x}{blue:02x}"
    return None


@functools.lru_cache(maxsize=128)
def parse_ansi_lines(content: str) -> tuple[tuple[Run, ...], ...]:
    """Parse ANSI-escaped content into styled ``Run`` lines.

    SGR (color/style) sequences become run styles carried across
    lines; all other escape sequences are stripped, not emulated —
    this is a log view, not a terminal emulator.

    Args:
        content: Raw text containing ANSI escape sequences.

    Returns:
        One tuple of ``Run`` spans per source line.
    """
    # ponytail: full-buffer re-parse per append; Rust fast path if
    # streamed logs ever get huge.
    color: str | None = None
    background: str | None = None
    modifiers: tuple[CharacterModifier, ...] = ()

    lines: list[tuple[Run, ...]] = []
    runs: list[Run] = []

    def emit(text: str) -> None:
        for index, segment in enumerate(text.split("\n")):
            if index > 0:
                lines.append(tuple(runs))
                runs.clear()
            if segment:
                runs.append(
                    Run(
                        text=segment,
                        color=color,
                        background=background,
                        modifiers=modifiers,
                    )
                )

    position = 0
    for match in _SGR_PATTERN.finditer(content):
        emit(strip_ansi_escapes(content[position : match.start()]))
        position = match.end()
        codes = [
            int(part) if part else 0
            for part in (match.group(1) or "0").split(";")
        ]
        while codes:
            code = codes.pop(0)
            if code == 0:
                color = background = None
                modifiers = ()
            elif code in _SGR_MODIFIERS:
                modifier = _SGR_MODIFIERS[code]
                if modifier not in modifiers:
                    modifiers = (*modifiers, modifier)
            elif code in (22, 23, 24, 25, 27):
                cleared = {
                    22: ("bold", "dim"),
                    23: ("italic",),
                    24: ("underline",),
                    25: ("slow_blink", "rapid_blink"),
                    27: ("reversed",),
                }[code]
                modifiers = tuple(
                    modifier
                    for modifier in modifiers
                    if modifier not in cleared
                )
            elif 30 <= code <= 37:
                color = _BASE_COLORS[code - 30]
            elif 90 <= code <= 97:
                color = _BRIGHT_COLORS[code - 90]
            elif 40 <= code <= 47:
                background = _BASE_COLORS[code - 40]
            elif 100 <= code <= 107:
                background = _BRIGHT_COLORS[code - 100]
            elif code == 38:
                color = _consume_extended_color(codes) or color
            elif code == 48:
                background = _consume_extended_color(codes) or background
            elif code == 39:
                color = None
            elif code == 49:
                background = None
    emit(strip_ansi_escapes(content[position:]))
    lines.append(tuple(runs))
    return tuple(lines)


__all__ = (
    "parse_ansi_lines",
    "strip_ansi_escapes",
)
