"""xnano._renderable

---

Print-like rendering for styled content: stdout ANSI fallback, active-session
paint, and stream regions that can append or replace in place.
"""

from __future__ import annotations

import dataclasses
import sys
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    Mapping,
    Sequence,
    TextIO,
)

if TYPE_CHECKING:
    from xnano._types import (
        Alignment,
        Border,
        CharacterModifier,
        Direction,
        FrameTitlePosition,
        PaddingLike,
        Side,
    )
    from xnano.color import ColorLike


_RESET = "\033[0m"

_MODIFIER_CODES: dict[str, str] = {
    "bold": "\033[1m",
    "dim": "\033[2m",
    "italic": "\033[3m",
    "underline": "\033[4m",
    "slow_blink": "\033[5m",
    "rapid_blink": "\033[6m",
    "reversed": "\033[7m",
}

# (top_left, horizontal, top_right, vertical, bottom_left, bottom_right)
_BORDER_CHARS: dict[str, tuple[str, str, str, str, str, str]] = {
    "plain": ("+", "-", "+", "|", "+", "+"),
    "rounded": ("╭", "─", "╮", "│", "╰", "╯"),
    "double": ("╔", "═", "╗", "║", "╚", "╝"),
    "thick": ("┏", "━", "┓", "┃", "┗", "┛"),
    "quadrant_inside": ("▛", "▀", "▜", "▌", "▙", "▟"),
    "quadrant_outside": ("▗", "▄", "▖", "▐", "▝", "▘"),
}

_SPARK_BARS = "▁▂▃▄▅▆▇█"


@dataclasses.dataclass
class _StreamRegion:
    """Tracked content for a named stream region (append or replace)."""

    content: str = ""
    """Full text currently owned by this stream (including prior chunks)."""
    line_count: int = 0
    """Display lines occupied after the last write (for cursor rewinds)."""
    renderables: tuple[Any, ...] = ()
    """Last full content payload when using update mode with structured values."""


_STREAM_REGIONS: dict[str, _StreamRegion] = {}
"""Module-level stream regions for stdout / inactive-terminal streaming."""


def _ansi_color(r: int, g: int, b: int, *, bg: bool = False) -> str:
    return f"\033[{'48' if bg else '38'};2;{r};{g};{b}m"


def _build_ansi_prefix(
    color: Any | None,
    background: Any | None,
    modifiers: Sequence[str] | None,
) -> str:
    parts: list[str] = []
    if modifiers:
        for m in modifiers:
            code = _MODIFIER_CODES.get(m)
            if code:
                parts.append(code)
    if color is not None:
        try:
            from xnano.color import Color

            c = Color.parse(color)
            parts.append(_ansi_color(c.r, c.g, c.b))
        except Exception:
            pass
    if background is not None:
        try:
            from xnano.color import Color

            c = Color.parse(background)
            parts.append(_ansi_color(c.r, c.g, c.b, bg=True))
        except Exception:
            pass
    return "".join(parts)


def _is_text_component(value: Any) -> bool:
    """Return True when ``value`` is an ``xnano.components.text.Text``."""
    cls = type(value)
    return cls.__name__ == "Text" and getattr(cls, "__module__", "").endswith(
        "components.text"
    )


def _component_kind(value: Any) -> str | None:
    """Return a short component class name when ``value`` is a known component."""
    cls = type(value)
    module = getattr(cls, "__module__", "")
    if not module.startswith("xnano.components"):
        return None
    return cls.__name__


def _style_plain_text(
    text: str,
    color: Any | None,
    background: Any | None,
    modifiers: Sequence[str] | None,
) -> str:
    """Wrap plain text in ANSI styling when any style is set."""
    prefix = _build_ansi_prefix(color, background, modifiers)
    if not prefix:
        return text
    return f"{prefix}{text}{_RESET}"


def _text_component_to_ansi(value: Any) -> str:
    """Flatten a ``Text`` tree to a single ANSI string (may include newlines).

    Leaf nodes apply their own color / background / modifiers. Nested lists of
    leaf ``Text`` children join inline (one line of spans). Nested multi-span
    children join with newlines (paragraph mode).
    """
    content = getattr(value, "content", "")
    color = getattr(value, "color", None)
    background = getattr(value, "background", None)
    modifiers = getattr(value, "modifiers", None) or None

    if isinstance(content, str):
        return _style_plain_text(content, color, background, modifiers)

    if _is_text_component(content):
        return _text_component_to_ansi(content)

    if isinstance(content, (list, tuple)):
        pieces: list[str] = []
        join_with_newline = False
        for item in content:
            if isinstance(item, str):
                pieces.append(item)
            elif _is_text_component(item):
                child_content = getattr(item, "content", "")
                if isinstance(child_content, (list, tuple)):
                    join_with_newline = True
                pieces.append(_text_component_to_ansi(item))
            else:
                pieces.append(str(item))
        separator = "\n" if join_with_newline else ""
        body = separator.join(pieces)
        return _style_plain_text(body, color, background, modifiers)

    return _style_plain_text(str(content), color, background, modifiers)


def _progress_to_lines(value: Any) -> list[str]:
    """ASCII progress bar for stdout fallback."""
    raw = float(getattr(value, "value", 0.0) or 0.0)
    total = getattr(value, "total", None)
    if total is not None:
        total_f = float(total)
        ratio = 0.0 if total_f <= 0 else max(0.0, min(1.0, raw / total_f))
        percent = int(round(ratio * 100))
    else:
        ratio = max(0.0, min(1.0, raw))
        percent = int(round(ratio * 100))

    width = 20
    filled = int(round(ratio * width))
    bar = "█" * filled + "░" * (width - filled)
    label = getattr(value, "label", None)
    if label is False:
        return [bar]
    if label is None:
        return [f"{bar} {percent}%"]
    return [f"{bar} {label}"]


def _sparkline_to_lines(value: Any) -> list[str]:
    """Unicode sparkline for stdout fallback."""
    data = list(getattr(value, "data", None) or [])
    if not data:
        return [""]
    ceiling = getattr(value, "max_value", None)
    max_value = (
        float(ceiling) if ceiling is not None else float(max(data) or 1)
    )
    if max_value <= 0:
        max_value = 1.0
    chars: list[str] = []
    last = len(_SPARK_BARS) - 1
    for sample in data:
        level = max(0.0, min(1.0, float(sample) / max_value))
        chars.append(_SPARK_BARS[int(round(level * last))])
    return ["".join(chars)]


def _table_to_lines(value: Any) -> list[str]:
    """Simple columnar text table for stdout fallback."""
    data = list(getattr(value, "data", None) or [])
    if not data:
        return [""]

    columns_arg = getattr(value, "columns", None)
    if isinstance(columns_arg, list) and columns_arg:
        headers = [str(c) for c in columns_arg]
    elif isinstance(columns_arg, Mapping) and columns_arg:
        headers = [str(k) for k in columns_arg]
    else:
        first = data[0]
        if isinstance(first, Mapping):
            headers = [str(k) for k in first]
        elif dataclasses.is_dataclass(first) and not isinstance(first, type):
            headers = [f.name for f in dataclasses.fields(first)]
        else:
            headers = ["value"]

    rows: list[list[str]] = []
    for row in data:
        cells: list[str] = []
        for header in headers:
            if isinstance(row, Mapping):
                cells.append(str(row.get(header, "")))
            elif dataclasses.is_dataclass(row) and not isinstance(row, type):
                cells.append(str(getattr(row, header, "")))
            else:
                cells.append(str(getattr(row, header, row)))
        rows.append(cells)

    widths = [len(h) for h in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def _fmt(cells: Sequence[str]) -> str:
        return "  ".join(
            cell.ljust(widths[index]) for index, cell in enumerate(cells)
        )

    lines = [_fmt(headers), _fmt(["-" * w for w in widths])]
    lines.extend(_fmt(row) for row in rows)
    return lines


def _chart_to_lines(value: Any) -> list[str]:
    """Compact chart summary for stdout fallback."""
    series = getattr(value, "series", None) or getattr(value, "data", None)
    if series is None:
        return ["[chart]"]
    if isinstance(series, Mapping):
        count = len(series)
    elif isinstance(series, Sequence) and not isinstance(series, (str, bytes)):
        count = len(series)
    else:
        count = 1
    return [f"[chart: {count} series]"]


def _schema_to_lines(value: Any) -> list[str]:
    """Schema component fallback lines."""
    name = type(value).__name__
    return [f"[{name}]"]


def _abstract_component_to_lines(value: Any) -> list[str] | None:
    """Dispatch known components to text fallbacks; else use ``str``/``repr``.

    Returns:
        Display lines for a recognized component, or ``None`` when ``value``
        is not an ``xnano.components`` instance.
    """
    kind = _component_kind(value)
    if kind is None:
        return None
    if kind == "Text":
        return _text_component_to_ansi(value).splitlines() or [""]
    if kind == "Progress":
        return _progress_to_lines(value)
    if kind == "Sparkline":
        return _sparkline_to_lines(value)
    if kind == "Table":
        return _table_to_lines(value)
    if kind == "Chart":
        return _chart_to_lines(value)
    if kind in ("Schema", "Form"):
        return _schema_to_lines(value)
    # Custom AbstractComponent subclasses — prefer str, then repr.
    text = str(value)
    if text and text != object.__repr__(value):
        return text.splitlines() or [""]
    return repr(value).splitlines() or [""]


def _base_grid_to_lines(value: Any) -> list[str] | None:
    """Plain-text fallback for ``BaseGrid`` outside a live terminal session.

    Used by Pyodide / stdout ``render()`` so interactive docs can show field
    content without ``xnano-core``.
    """
    # Duck-type via ClassVar maps set by ``BaseGrid`` metaclass.
    render_fields = getattr(type(value), "_grid_fields", None)
    if not isinstance(render_fields, Mapping) or not render_fields:
        return None

    lines: list[str] = []
    for name, info in render_fields.items():
        if getattr(info, "state", False):
            continue
        field_value = getattr(value, name, None)
        if field_value is None:
            continue
        border = getattr(info, "border", None)
        title = getattr(info, "title", None) or (name if border else None)
        field_lines = _renderable_to_lines(field_value)
        if border:
            field_lines = _apply_border(
                field_lines,
                border,
                getattr(info, "border_sides", None),
                "",
                title,
                getattr(info, "title_position", None),
            )
        lines.extend(field_lines)
    return lines or [f"[{type(value).__name__}]"]


def _renderable_to_lines(value: Any) -> list[str]:
    """Convert a renderable to display lines (ANSI allowed for styled Text)."""
    component_lines = _abstract_component_to_lines(value)
    if component_lines is not None:
        return component_lines
    if isinstance(value, str):
        return value.splitlines() or [""]
    if isinstance(value, (int, float, bool)):
        return [str(value)]
    if isinstance(value, (list, tuple)):
        lines: list[str] = []
        for item in value:
            lines.extend(_renderable_to_lines(item))
        return lines
    grid_lines = _base_grid_to_lines(value)
    if grid_lines is not None:
        return grid_lines
    return repr(value).splitlines() or [""]


def _apply_padding(lines: list[str], padding: Any | None) -> list[str]:
    if padding is None:
        return lines
    from xnano._types import Padding

    pad = Padding.parse(padding)
    inner_width = max((len(l) for l in lines), default=0)
    h_pad = " " * pad.left + "{}" + " " * pad.right
    padded = [h_pad.format(line.ljust(inner_width)) for line in lines]
    empty = " " * (inner_width + pad.left + pad.right)
    return [empty] * pad.top + padded + [empty] * pad.bottom


def _align_lines(lines: list[str], width: int, align: str | None) -> list[str]:
    if align == "center":
        return [line.center(width) for line in lines]
    if align == "right":
        return [line.rjust(width) for line in lines]
    return [line.ljust(width) for line in lines]


def _apply_border(
    lines: list[str],
    border: str | None,
    border_sides: Sequence[str] | None,
    border_color_prefix: str,
    title: str | None,
    title_position: str | None,
) -> list[str]:
    if border is None and not border_sides:
        return lines

    chars = _BORDER_CHARS.get(border or "plain", _BORDER_CHARS["plain"])
    tl, h, tr, v, bl, br = chars

    sides = (
        set(border_sides)
        if border_sides
        else {"top", "bottom", "left", "right"}
    )
    draw_top = "top" in sides
    draw_bottom = "bottom" in sides
    draw_left = "left" in sides
    draw_right = "right" in sides

    inner_width = max((len(l) for l in lines), default=0)
    bc = border_color_prefix
    rst = _RESET if bc else ""

    result: list[str] = []

    if draw_top:
        top_fill = h * inner_width
        if title:
            tp = title_position or "top"
            if tp == "bottom":
                pass
            else:
                label = f" {title} "
                fill_len = max(0, inner_width - len(label))
                left_fill = h * (fill_len // 2)
                right_fill = h * (fill_len - fill_len // 2)
                top_fill = left_fill + label + right_fill
        left_corner = (bc + tl + rst) if draw_left else ""
        right_corner = (bc + tr + rst) if draw_right else ""
        result.append(left_corner + bc + top_fill + rst + right_corner)

    for line in lines:
        left_wall = (bc + v + rst) if draw_left else ""
        right_wall = (bc + v + rst) if draw_right else ""
        result.append(left_wall + line + right_wall)

    if draw_bottom:
        bot_fill = h * inner_width
        if title and (title_position or "top") == "bottom":
            label = f" {title} "
            fill_len = max(0, inner_width - len(label))
            left_fill = h * (fill_len // 2)
            right_fill = h * (fill_len - fill_len // 2)
            bot_fill = left_fill + label + right_fill
        left_corner = (bc + bl + rst) if draw_left else ""
        right_corner = (bc + br + rst) if draw_right else ""
        result.append(left_corner + bc + bot_fill + rst + right_corner)

    return result


def _join_horizontal(groups: list[list[str]], *, sep: str = "") -> list[str]:
    if not groups:
        return []
    height = max(len(g) for g in groups)
    widths = [max((len(l) for l in g), default=0) for g in groups]
    result: list[str] = []
    for row in range(height):
        parts: list[str] = []
        for index, (group, width) in enumerate(zip(groups, widths)):
            if index and sep:
                parts.append(sep)
            parts.append(
                group[row].ljust(width) if row < len(group) else " " * width
            )
        result.append("".join(parts))
    return result


def _count_display_lines(text: str) -> int:
    """Count visual lines occupied by ``text`` after write."""
    if not text:
        return 0
    # Trailing newline means the cursor is on a fresh empty line after content.
    if text.endswith("\n"):
        return text.count("\n")
    return text.count("\n") + 1


def _rewind_stream_region(file: IO[str], line_count: int) -> None:
    """Move the cursor up and clear the previous stream region."""
    if line_count <= 0:
        return
    # Move to start of the region, clear each line.
    file.write(f"\033[{line_count}A\r")
    for index in range(line_count):
        file.write("\033[2K")
        if index + 1 < line_count:
            file.write("\n")
    if line_count > 1:
        file.write(f"\033[{line_count - 1}A\r")


def format_renderables(
    renderables: tuple[Any, ...],
    *,
    direction: str = "vertical",
    color: Any | None = None,
    background: Any | None = None,
    modifiers: Sequence[str] | None = None,
    align: str | None = None,
    border: str | None = None,
    border_sides: Sequence[str] | None = None,
    border_color: Any | None = None,
    title: str | None = None,
    title_position: str | None = None,
    padding: Any | None = None,
    sep: str = " ",
) -> str:
    """Format renderables to a single string (no I/O).

    Args:
        renderables: Values to format.
        direction: ``"vertical"`` stacks blocks; ``"horizontal"`` joins rows.
        color: Foreground color for plain values.
        background: Background color for plain values.
        modifiers: Character modifiers for plain values.
        align: Horizontal alignment inside each block.
        border: Border style around each block.
        border_sides: Optional subset of border sides.
        border_color: Border color.
        title: Border title.
        title_position: Border title placement.
        padding: Padding around content.
        sep: Separator between blocks (horizontal layout, or single-line
            vertical joins that behave like builtins.print).

    Returns:
        Formatted body without the trailing ``end`` character.
    """
    prefix = _build_ansi_prefix(color, background, modifiers)
    suffix = _RESET if prefix else ""
    border_color_prefix = _build_ansi_prefix(border_color, None, None)

    line_groups: list[list[str]] = []
    for renderable in renderables:
        raw_lines = _renderable_to_lines(renderable)
        raw_lines = _apply_padding(raw_lines, padding)

        if align:
            width = max((len(l) for l in raw_lines), default=0)
            raw_lines = _align_lines(raw_lines, width, align)

        if prefix and not _is_text_component(renderable):
            raw_lines = [prefix + line + suffix for line in raw_lines]

        raw_lines = _apply_border(
            raw_lines,
            border,
            border_sides,
            border_color_prefix,
            title,
            title_position,
        )
        line_groups.append(raw_lines)

    if not line_groups:
        return ""

    if direction == "horizontal":
        # ``sep`` is the gap between side-by-side blocks (print-like).
        final_lines = _join_horizontal(line_groups, sep=sep)
        return "\n".join(final_lines)

    # Vertical stacks always join blocks with newlines so multi-line borders
    # and multi-renderable docs demos stay readable. Use direction=
    # "horizontal" (and ``sep``) for print-like same-line joins.
    return "\n".join(line for group in line_groups for line in (group or [""]))


def _render_to_stdout(
    renderables: tuple[Any, ...],
    *,
    direction: str,
    color: Any | None,
    background: Any | None,
    modifiers: Sequence[str] | None,
    align: str | None,
    border: str | None,
    border_sides: Sequence[str] | None,
    border_color: Any | None,
    title: str | None,
    title_position: str | None,
    padding: Any | None,
    sep: str = " ",
    end: str = "\n",
    file: IO[str] | None = None,
    flush: bool = False,
    stream: str | bool | None = None,
    update: bool = False,
) -> None:
    """Write formatted renderables to a text stream (default stdout)."""
    body = format_renderables(
        renderables,
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
        sep=sep,
    )
    target: IO[str] = file if file is not None else sys.stdout
    stream_id = _normalize_stream_id(stream)

    if stream_id is None:
        target.write(body + end)
        if flush:
            target.flush()
        return

    region = _STREAM_REGIONS.setdefault(stream_id, _StreamRegion())
    chunk = body + end

    if update:
        _rewind_stream_region(target, region.line_count)
        region.content = chunk
        region.renderables = renderables
        target.write(region.content)
        region.line_count = _count_display_lines(region.content)
    else:
        region.content = f"{region.content}{chunk}"
        region.renderables = region.renderables + renderables
        target.write(chunk)
        region.line_count = _count_display_lines(region.content)

    if flush:
        target.flush()


def _normalize_stream_id(stream: str | bool | None) -> str | None:
    """Normalize ``stream`` kwarg to a region id or ``None``."""
    if stream is None or stream is False:
        return None
    if stream is True:
        return "default"
    return str(stream)


def clear_stream(stream: str | bool = True) -> None:
    """Drop a tracked stream region without writing to the terminal.

    Args:
        stream: Stream id (``True`` → ``"default"``).
    """
    stream_id = _normalize_stream_id(stream)
    if stream_id is not None:
        _STREAM_REGIONS.pop(stream_id, None)


def get_stream_content(stream: str | bool = True) -> str:
    """Return the full content currently held by a stream region.

    Args:
        stream: Stream id (``True`` → ``"default"``).

    Returns:
        Accumulated or last-updated content, or ``""`` when unknown.
    """
    stream_id = _normalize_stream_id(stream)
    if stream_id is None:
        return ""
    region = _STREAM_REGIONS.get(stream_id)
    return "" if region is None else region.content


class Renderable:
    """Marker type for renderable values accepted by layout fields and render().

    A renderable is any value — strings, ints, floats, dataclasses, pydantic
    models, ``AbstractComponent``, ``BaseGrid``, ``AbstractRenderNode``, or a
    ``Sequence`` of those.  Anything is displayable via ``str()``.
    """


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
    # builtins.print-compatible parameters
    sep: str | None = " ",
    end: str | None = "\n",
    file: IO[str] | TextIO | None = None,
    flush: bool = False,
    # stream / live-update parameters
    stream: str | bool | None = None,
    update: bool = False,
) -> None:
    """Display renderables as print-like terminal output.

    Accepts any renderable value — strings, numbers, components, grids, render
    nodes, dataclasses, pydantic models, or sequences of those.

    Outside an active terminal session, content is formatted to ANSI text and
    written to ``file`` (default ``sys.stdout``), honoring ``sep`` / ``end`` /
    ``flush`` like builtins.print.

    Inside an active ``Terminal`` session, content is painted into the live
    viewport. Stream regions (``stream=``) can **append** chunks or **replace**
    the full region content (``update=True``) without needing delta encoding.

    Args:
        *renderables: Values to display.
        direction: Layout direction when multiple renderables are given.
        color: Foreground color for plain text content.
        background: Background color for the render area.
        modifiers: Character modifiers (bold, italic, etc.) applied to text.
        align: Horizontal alignment of content within the area.
        border: Border style to wrap the rendered area.
        border_sides: Specific sides on which to draw the border.
        border_color: Color of the border.
        title: Title drawn in the border frame.
        title_position: Alignment of the border title.
        padding: Padding around the content area.
        sep: String inserted between renderables (print-compatible; also used
            as horizontal column separator).
        end: String appended after the content (print-compatible; default
            newline).
        file: Text stream to write to when not painting a live session.
            Defaults to ``sys.stdout``.
        flush: Whether to flush ``file`` after writing.
        stream: Enable a named stream region (``True`` → ``"default"``).
            When set, successive calls can append or replace content.
        update: When ``True`` with ``stream``, replace the full stream region
            with the new content instead of appending a chunk.
    """
    sep_value = " " if sep is None else sep
    end_value = "\n" if end is None else end

    from xnano.fields import GridFieldInfo

    field = GridFieldInfo(
        color=color,
        background=background,
        modifiers=list(modifiers) if modifiers else None,
        align=align,
        border=border,
        border_sides=list(border_sides) if border_sides else None,
        border_color=border_color,
        title=title,
        title_position=title_position,
        padding=padding,
        direction=direction,
    )

    # Native / live-session imports are deferred so pure-Python installs
    # (e.g. Pyodide docs via micropip) can use the stdout ANSI path without
    # ``xnano-core`` being present.
    try:
        from xnano.terminal.terminal import _ACTIVE_TERMINAL

        terminal = _ACTIVE_TERMINAL.get()
    except ImportError:
        terminal = None

    stream_id = _normalize_stream_id(stream)

    # Explicit non-stdout file always takes the text path, even mid-session.
    if file is not None and file is not sys.stdout:
        _render_to_stdout(
            renderables,
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
            sep=sep_value,
            end=end_value,
            file=file,  # type: ignore[arg-type]
            flush=flush,
            stream=stream,
            update=update,
        )
        return

    if terminal is not None and getattr(terminal, "_is_live", False):
        # Prefer the terminal's full paint path when a live session owns the
        # display — streams re-paint the whole region with the latest content.
        from xnano._core_bindings import get_area_from_native_rect

        if stream_id is not None:
            region = _STREAM_REGIONS.setdefault(stream_id, _StreamRegion())
            if update or not region.renderables:
                region.renderables = renderables
            else:
                region.renderables = region.renderables + renderables
            paint_items = region.renderables
        else:
            paint_items = renderables

        try:
            # Prefer Terminal.render session preparation when available so
            # stream updates and one-shots share sizing logic.
            if hasattr(terminal, "_render_stream_items"):
                terminal._render_stream_items(  # type: ignore[attr-defined]
                    paint_items,
                    field=field,
                    flush=flush,
                )
            else:
                sess = terminal.session
                area = get_area_from_native_rect(
                    sess.get_native_viewport_area()
                )
                for renderable in paint_items:
                    sess.paint_field_slot(renderable, area, field)
        except Exception:
            # Fall back to text if the session cannot paint.
            _render_to_stdout(
                renderables,
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
                sep=sep_value,
                end=end_value,
                file=file,  # type: ignore[arg-type]
                flush=flush,
                stream=stream,
                update=update,
            )
        return

    # Wasm / no-live-terminal builds: use the real layout engine via a
    # buffer-backed Terminal.render, not the ANSI text approximation.
    try:
        from xnano_core.core import CoreSession

        buffer_backed = not CoreSession.supports_live_terminal()
    except Exception:
        buffer_backed = False

    if buffer_backed and stream_id is None:
        try:
            from xnano.terminal.terminal import Terminal

            Terminal().render(
                *renderables,
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
                direction=direction,
                sep=sep_value,
                end=end_value,
                file=file,
                flush=flush,
            )
            return
        except Exception:
            # Fall through to the pure-Python ANSI path if core paint fails.
            pass

    _render_to_stdout(
        renderables,
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
        sep=sep_value,
        end=end_value,
        file=file,  # type: ignore[arg-type]
        flush=flush,
        stream=stream,
        update=update,
    )


__all__ = (
    "Renderable",
    "clear_stream",
    "format_renderables",
    "get_stream_content",
    "render",
)
