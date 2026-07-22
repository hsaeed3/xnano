"""xnano.web.frame

---

Serialize a native render ``Buffer`` into compact, JSON-friendly cell
frames for the browser canvas painter, plus a row-diff so only changed
rows travel on the wire.

Wire shape (one frame):

    {
        "w": 80, "h": 24,
        "full": true,                 # full frame, else a row diff
        "rows": {                     # y -> run-length spans
            "0": [["hi ", "#ff0000", null, 1], ["there", null, null, 0]],
            ...
        },
        "cursor": [x, y]              # or null
    }

A span is ``[text, fg, bg, modifiers]`` where ``fg``/``bg`` are
``"#rrggbb"`` strings or ``null`` (terminal default) and ``modifiers``
is a small bitfield.
"""

from __future__ import annotations

import re
from typing import Any, TypeAlias

from xnano._markup import _BASE_COLORS, _BRIGHT_COLORS, _color_from_256

Span: TypeAlias = "tuple[str, str | None, str | None, int]"
Row: TypeAlias = "tuple[Span, ...]"

# Modifier bitfield mirrored on the JS painter side.
MOD_BOLD = 1
MOD_DIM = 2
MOD_ITALIC = 4
MOD_UNDERLINE = 8
MOD_REVERSED = 16

_MODIFIER_BITS: dict[str, int] = {
    "BOLD": MOD_BOLD,
    "DIM": MOD_DIM,
    "ITALIC": MOD_ITALIC,
    "UNDERLINED": MOD_UNDERLINE,
    "REVERSED": MOD_REVERSED,
}

# Native ``repr(Color)`` name -> xterm palette index (0-15).
_NAMED_INDEX: dict[str, int] = {
    "Black": 0,
    "Red": 1,
    "Green": 2,
    "Yellow": 3,
    "Blue": 4,
    "Magenta": 5,
    "Cyan": 6,
    "Gray": 7,
    "DarkGray": 8,
    "LightRed": 9,
    "LightGreen": 10,
    "LightYellow": 11,
    "LightBlue": 12,
    "LightMagenta": 13,
    "LightCyan": 14,
    "White": 15,
}

_RGB_PATTERN = re.compile(r"Rgb\((\d+), (\d+), (\d+)\)")
_INDEXED_PATTERN = re.compile(r"Indexed\((\d+)\)")


def _palette_hex(index: int) -> str:
    if index < 8:
        return _BASE_COLORS[index]
    if index < 16:
        return _BRIGHT_COLORS[index - 8]
    return _color_from_256(index)


def color_to_web(color: Any) -> str | None:
    """Convert a native ``Color`` to ``"#rrggbb"`` or ``None`` (default)."""
    value = repr(color)
    index = _NAMED_INDEX.get(value)
    if index is not None:
        return _palette_hex(index)
    rgb = _RGB_PATTERN.fullmatch(value)
    if rgb is not None:
        red, green, blue = (int(part) for part in rgb.groups())
        return f"#{red:02x}{green:02x}{blue:02x}"
    indexed = _INDEXED_PATTERN.fullmatch(value)
    if indexed is not None:
        return _palette_hex(int(indexed.group(1)))
    return None  # Reset / Default / unknown


def _modifier_bits(modifier: Any) -> int:
    names = repr(modifier).split(" | ")
    bits = 0
    for name in names:
        bits |= _MODIFIER_BITS.get(name, 0)
    return bits


def serialize_rows(buffer: Any) -> tuple[Row, ...]:
    """Convert a native buffer to run-length span rows (one per line)."""
    area = buffer.area
    rows: list[Row] = []
    for y in range(area.y, area.y + area.height):
        spans: list[Span] = []
        text = ""
        run_fg: str | None = None
        run_bg: str | None = None
        run_mods = 0
        started = False
        for x in range(area.x, area.x + area.width):
            cell = buffer.cell(x, y)
            if cell is None:
                symbol, fg, bg, mods = " ", None, None, 0
            else:
                symbol = cell.symbol or " "
                fg = color_to_web(cell.fg)
                bg = color_to_web(cell.bg)
                mods = _modifier_bits(cell.modifier)
            if (
                started
                and (fg, bg, mods) == (run_fg, run_bg, run_mods)
            ):
                text += symbol
                continue
            if started:
                spans.append((text, run_fg, run_bg, run_mods))
            text = symbol
            run_fg, run_bg, run_mods = fg, bg, mods
            started = True
        if started:
            spans.append((text, run_fg, run_bg, run_mods))
        rows.append(tuple(spans))
    return tuple(rows)


def build_frame(
    rows: tuple[Row, ...],
    *,
    width: int,
    height: int,
    cursor: tuple[int, int] | None,
    previous: tuple[Row, ...] | None,
) -> dict[str, Any]:
    """Build a wire frame, diffing against ``previous`` when shapes match.

    A full frame is sent on first paint or whenever the grid resizes;
    otherwise only rows that changed since ``previous`` are included.
    """
    full = previous is None or len(previous) != len(rows)
    if full:
        changed = {str(y): _row_json(row) for y, row in enumerate(rows)}
    else:
        changed = {
            str(y): _row_json(row)
            for y, row in enumerate(rows)
            if row != previous[y]
        }
    return {
        "w": width,
        "h": height,
        "full": full,
        "rows": changed,
        "cursor": list(cursor) if cursor is not None else None,
    }


def _row_json(row: Row) -> list[list[Any]]:
    return [[text, fg, bg, mods] for text, fg, bg, mods in row]


__all__ = (
    "Row",
    "Span",
    "build_frame",
    "color_to_web",
    "serialize_rows",
)
