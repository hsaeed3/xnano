"""xnano.printing

---

Stdout printing utilities for xnano widgets and components.
"""

from __future__ import annotations

import sys
from typing import Any

from xnano.buffer import Buffer, render_widget
from xnano.layout import Rectangle


def print(
    *renderables: Any,
    sep: str = " ",
    end: str = "\n",
    height: int | None = None,
) -> None:
    """Print xnano widgets, components, or standard objects directly to stdout.

    This behaves like Python's built-in ``print()``, but formats any xnano
    widgets/components with full ANSI styles and layouts, printing them straight
    to the terminal scrollback without entering alternate screen or raw mode.

    Args:
        *renderables: The objects, widgets, or Components to print.
        sep: String separator inserted between values, default is a space.
        end: String appended after the last value, default is a newline.
        height: The height of the rendering buffer for widgets. If None, it
            defaults to the terminal height, and trailing empty lines will be
            automatically clipped.
    """
    import os

    try:
        cols, rows = os.get_terminal_size(sys.stdout.fileno())
    except OSError:
        cols, rows = 80, 24

    render_height = height if height is not None else rows
    clip_bottom = height is None

    outputs: list[str] = []
    for widget in renderables:
        is_xnano = (
            hasattr(widget, "render")
            or hasattr(widget, "_to_core")
            or hasattr(widget, "_inner")
        )
        if is_xnano:
            area = Rectangle(x=0, y=0, width=cols, height=render_height)
            buffer = Buffer.empty(area)
            render_widget(widget, area, buffer)
            lines = buffer.to_ansi_lines(clip_bottom=clip_bottom)
            outputs.append("\n".join(lines))
        else:
            outputs.append(str(widget))

    sys.stdout.write(sep.join(outputs) + end)
    sys.stdout.flush()
