"""xnano.beta.rendering

---

Display styled values through a live runtime or print them as terminal text.
"""

from __future__ import annotations

import dataclasses
import shutil
import sys
from typing import IO, Any, Sequence, TextIO

from xnano.beta.colors import ColorLike
from xnano.beta.types import (
    Alignment,
    Border,
    CharacterModifier,
    Direction,
    FrameTitlePosition,
    PaddingLike,
    Side,
)


@dataclasses.dataclass
class _StreamRegion:
    content: str = ""
    line_count: int = 0


_STREAM_REGIONS: dict[str, _StreamRegion] = {}


def _normalize_stream_id(stream: str | bool | None) -> str | None:
    if stream is None or stream is False:
        return None
    return "default" if stream is True else str(stream)


def _count_display_lines(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") if text.endswith("\n") else text.count("\n") + 1


def _rewind_stream_region(file: IO[str], line_count: int) -> None:
    if line_count <= 0:
        return
    file.write(f"\033[{line_count}A\r")
    for index in range(line_count):
        file.write("\033[2K")
        if index + 1 < line_count:
            file.write("\n")
    if line_count > 1:
        file.write(f"\033[{line_count - 1}A\r")


def _frame_text(frame: Any, *, styled: bool) -> str:
    raw = frame.ansi if styled else frame.text
    lines = [line.rstrip() for line in raw.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _plain_render_size(
    renderables: tuple[Any, ...],
    *,
    direction: Direction,
    gap: int,
    border: Border | None,
    border_sides: Sequence[Side] | None,
    padding: PaddingLike | None,
) -> tuple[int, int] | None:
    if not all(
        isinstance(value, (str, int, float, bool)) for value in renderables
    ):
        return None
    groups = [str(value).splitlines() or [""] for value in renderables]
    widths = [max(map(len, lines), default=0) for lines in groups]
    heights = [len(lines) for lines in groups]
    if direction == "horizontal":
        width = sum(widths) + max(0, len(groups) - 1) * gap
        height = max(heights, default=1)
    else:
        width = max(widths, default=1)
        height = sum(heights) + max(0, len(groups) - 1) * gap

    from xnano.beta.types import Padding

    parsed_padding = Padding.parse(padding)
    width += parsed_padding.left + parsed_padding.right
    height += parsed_padding.top + parsed_padding.bottom
    sides = (
        set(border_sides)
        if border_sides is not None
        else {"top", "right", "bottom", "left"}
        if border is not None
        else set()
    )
    width += int("left" in sides) + int("right" in sides)
    height += int("top" in sides) + int("bottom" in sides)
    return (max(1, width), max(1, height))


def clear_stream(stream: str | bool = True) -> None:
    """Forget a named live-output stream.

    Args:
        stream: Stream name, or ``True`` for the default stream.
    """
    stream_id = _normalize_stream_id(stream)
    if stream_id is not None:
        _STREAM_REGIONS.pop(stream_id, None)


def get_stream_content(stream: str | bool = True) -> str:
    """Return the text currently owned by a named stream.

    Args:
        stream: Stream name, or ``True`` for the default stream.

    Returns:
        Accumulated stream text, or an empty string when it does not exist.
    """
    stream_id = _normalize_stream_id(stream)
    region = _STREAM_REGIONS.get(stream_id) if stream_id is not None else None
    return "" if region is None else region.content


def render(
    *renderables: Any,
    direction: Direction = "vertical",
    color: ColorLike | None = None,
    background: ColorLike | None = None,
    modifiers: Sequence[CharacterModifier] | None = None,
    align: Alignment | None = None,
    border: Border | None = None,
    border_sides: Sequence[Side] | None = None,
    border_color: ColorLike | None = None,
    title: str | None = None,
    title_position: FrameTitlePosition | None = None,
    padding: PaddingLike | None = None,
    gap: int = 0,
    sep: str | None = " ",
    end: str | None = "\n",
    file: IO[str] | TextIO | None = None,
    flush: bool = False,
    stream: str | bool | None = None,
    update: bool = False,
) -> None:
    """Display renderables as print-like terminal output.

    A live beta runtime paints the values into its current viewport. Otherwise
    xnano uses an offscreen native terminal and writes the resulting cells to
    ``file`` or standard output.

    Args:
        *renderables: Grids, components, content primitives, or plain values.
        direction: Direction used to lay out multiple renderables.
        color: Foreground color applied to plain values.
        background: Background color for the rendered area.
        modifiers: Character modifiers applied to plain values.
        align: Horizontal alignment applied to plain values.
        border: Border style around the rendered area.
        border_sides: Border sides to draw.
        border_color: Border foreground color.
        title: Optional border title.
        title_position: Border edge that holds the title.
        padding: Space between the border and content.
        gap: Cells between multiple renderables.
        sep: Separator used between horizontally arranged plain values.
        end: Text appended after the rendered output.
        file: Text stream written outside a live runtime.
        flush: Whether to flush the output stream after writing.
        stream: Named append-or-replace output region.
        update: Replace the named stream instead of appending to it.
    """
    from xnano.beta.core.runtime import get_active_runtime

    runtime = get_active_runtime()
    target = sys.stdout if file is None else file
    if runtime is not None and target is sys.stdout and stream is None:
        runtime.render(
            *renderables,
            direction=direction,
            color=color,
            background=background,
            modifiers=modifiers,
            align=align,
            border=border,
            border_sides=border_sides,
            border_color=border_color,
            title=title,
            title_position=title_position,
            padding=padding,
            gap=gap,
        )
        if flush:
            target.flush()
        return

    from xnano.beta.terminal import Terminal

    values = renderables
    if direction == "horizontal" and all(
        isinstance(value, (str, int, float, bool)) for value in values
    ):
        values = ((sep if sep is not None else " ").join(map(str, values)),)
    measured_size = _plain_render_size(
        values,
        direction=direction,
        gap=gap,
        border=border,
        border_sides=border_sides,
        padding=padding,
    )
    columns, rows = (
        measured_size
        if measured_size is not None
        else shutil.get_terminal_size((80, 24))
    )
    terminal = Terminal.offscreen(cols=columns, rows=rows)
    try:
        frame = terminal.render(
            *values,
            direction=direction,
            color=color,
            background=background,
            modifiers=modifiers,
            align=align,
            border=border,
            border_sides=border_sides,
            border_color=border_color,
            title=title,
            title_position=title_position,
            padding=padding,
            gap=gap,
        )
    finally:
        terminal.close()

    body = _frame_text(
        frame,
        styled=any(
            value is not None
            for value in (
                color,
                background,
                modifiers,
                border,
                border_sides,
                border_color,
            )
        ),
    )
    chunk = body + ("\n" if end is None else end)
    stream_id = _normalize_stream_id(stream)
    if stream_id is None:
        target.write(chunk)
    else:
        region = _STREAM_REGIONS.setdefault(stream_id, _StreamRegion())
        if update:
            _rewind_stream_region(target, region.line_count)
            region.content = chunk
        else:
            region.content += chunk
        target.write(region.content if update else chunk)
        region.line_count = _count_display_lines(region.content)
    if flush:
        target.flush()


__all__ = ("clear_stream", "get_stream_content", "render")
