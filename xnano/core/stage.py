"""xnano.core.stage

---

Layout map and cell-level paint / wireframe helpers for the active host
(``host.stage`` / ``ctx.stage``).
"""

from __future__ import annotations

import dataclasses
from typing import Any, Callable, Sequence, TYPE_CHECKING

from xnano._types import Area, Size

if TYPE_CHECKING:
    from xnano.core.hosts import AbstractHost


@dataclasses.dataclass(slots=True)
class _PaintSpan:
    """One run-length span on a mutable paint row."""

    text: str
    """Contiguous cell characters sharing one style."""
    style: Any = None
    """Optional style payload for this span."""


@dataclasses.dataclass
class _PaintCanvas:
    """Mutable per-cell lattice used for Stage paint and wireframe.

    Distinct from content ``CellCanvas`` (immutable run-length rows).
    Controllers lower this overlay via ``get_cell`` / ``as_span_rows``.
    """

    width: int
    """Lattice width in cells."""
    height: int
    """Lattice height in cells."""
    _cells: list[list[tuple[str, Any]]] = dataclasses.field(
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        width = max(0, int(self.width))
        height = max(0, int(self.height))
        self.width = width
        self.height = height
        self._cells = [
            [(" ", None) for _ in range(width)] for _ in range(height)
        ]

    def set_cell(
        self,
        x: int,
        y: int,
        char: str,
        style: Any = None,
    ) -> None:
        """Write one cell, clipping out-of-bounds coordinates.

        Args:
            x: Column index.
            y: Row index.
            char: Character to store (first codepoint used).
            style: Optional style payload.
        """
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return
        glyph = char[0] if char else " "
        self._cells[y][x] = (glyph, style)

    def get_cell(self, x: int, y: int) -> tuple[str, Any]:
        """Return ``(char, style)`` for a cell, or a blank.

        Args:
            x: Column index.
            y: Row index.

        Returns:
            The cell payload, or ``(" ", None)`` when out of bounds.
        """
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return (" ", None)
        return self._cells[y][x]

    def fill(self, style: Any = None, char: str = " ") -> None:
        """Fill the entire canvas with ``char`` / ``style``.

        Args:
            style: Optional style payload.
            char: Fill character (first codepoint used).
        """
        glyph = char[0] if char else " "
        for y in range(self.height):
            row = self._cells[y]
            for x in range(self.width):
                row[x] = (glyph, style)

    def as_span_rows(self) -> list[list[_PaintSpan]]:
        """Export rows as run-length-encoded paint spans.

        Returns:
            One list of spans per row.
        """
        rows: list[list[_PaintSpan]] = []
        for y in range(self.height):
            spans: list[_PaintSpan] = []
            current_text = ""
            current_style: Any = None
            for x in range(self.width):
                glyph, style = self._cells[y][x]
                if current_text and style != current_style:
                    spans.append(
                        _PaintSpan(text=current_text, style=current_style)
                    )
                    current_text = ""
                current_text += glyph
                current_style = style
            if current_text:
                spans.append(
                    _PaintSpan(text=current_text, style=current_style)
                )
            rows.append(spans)
        return rows


# Public aliases used by Stage paint/wireframe APIs and tests.
CellSpan = _PaintSpan
CellCanvas = _PaintCanvas


@dataclasses.dataclass(slots=True)
class LayoutEntry:
    """One resolved geometry record for the current frame.

    Attributes:
        interface: BaseGrid/component instance that owns the region.
        field: Field name within ``interface``, or ``None`` for the
            interface root area.
        area: Resolved cell ``Area`` for this entry.
        z: Stacking order among siblings (higher paints later).
    """

    interface: Any
    """BaseGrid/component instance that owns the region."""
    field: str | None
    """Field name within ``interface``, or ``None`` for the root."""
    area: Area
    """Resolved cell area for this entry."""
    z: int = 0
    """Stacking order among siblings."""


class LayoutMap:
    """Always-on resolved geometry for the current frame.

    Hosts record ``interface`` / ``field`` → ``Area`` (plus ``z``) while
    laying out each frame so the stage can answer where everything is
    without re-running layout.
    """

    def __init__(self) -> None:
        self._entries: list[LayoutEntry] = []
        self._index: dict[tuple[int, str | None], LayoutEntry] = {}

    def clear(self) -> None:
        """Drop every recorded entry for a new frame."""
        self._entries.clear()
        self._index.clear()

    def record(
        self,
        interface: Any,
        field: str | None,
        area: Area,
        *,
        z: int = 0,
    ) -> None:
        """Record resolved geometry for ``interface`` / ``field``.

        Re-recording the same ``(interface, field)`` replaces the prior
        entry while preserving relative order of other entries.

        Args:
            interface: BaseGrid/component instance.
            field: Field name, or ``None`` for the interface root.
            area: Resolved cell area.
            z: Stacking order among siblings.
        """
        key = (id(interface), field)
        entry = LayoutEntry(
            interface=interface,
            field=field,
            area=area,
            z=z,
        )
        previous = self._index.get(key)
        if previous is not None:
            try:
                index = self._entries.index(previous)
            except ValueError:
                self._entries.append(entry)
            else:
                self._entries[index] = entry
        else:
            self._entries.append(entry)
        self._index[key] = entry

    def region_of(
        self,
        interface: Any,
        field: str | None = None,
    ) -> Area | None:
        """Return the recorded area for ``interface`` / ``field``.

        Args:
            interface: BaseGrid/component instance.
            field: Field name, or ``None`` for the interface root.

        Returns:
            The stored ``Area``, or ``None``.
        """
        entry = self._index.get((id(interface), field))
        if entry is None:
            return None
        return entry.area

    def entries(self) -> Sequence[LayoutEntry]:
        """Return recorded entries in record order.

        Returns:
            A sequence of ``LayoutEntry`` values.
        """
        return tuple(self._entries)


class StageRegion:
    """Paintable view of an ``Area`` on the stage.

    Coordinates passed to ``paint`` / ``map_cells`` are relative to this
    region's top-left corner.
    """

    def __init__(self, stage: "Stage", area: Area) -> None:
        self._stage = stage
        self._area = area

    @property
    def area(self) -> Area:
        """Absolute area this region covers on the stage."""
        return self._area

    def paint(
        self,
        x: int,
        y: int,
        char: str,
        style: Any = None,
    ) -> None:
        """Paint one cell relative to this region's origin.

        Args:
            x: Column offset within the region.
            y: Row offset within the region.
            char: Character to paint (first codepoint used).
            style: Optional style payload.
        """
        if x < 0 or y < 0 or x >= self._area.width or y >= self._area.height:
            return
        self._stage._paint_absolute(
            self._area.x + x,
            self._area.y + y,
            char,
            style,
        )

    def fill(self, style: Any = None, char: str = " ") -> None:
        """Fill every cell in this region.

        Args:
            style: Optional style payload.
            char: Fill character (first codepoint used).
        """
        for row in range(self._area.height):
            for column in range(self._area.width):
                self.paint(column, row, char, style)

    def map_cells(
        self,
        fn: Callable[[int, int, str, Any], tuple[str, Any] | None],
    ) -> None:
        """Map ``fn`` over every cell in this region.

        ``fn`` receives ``(x, y, char, style)`` in region-relative
        coordinates. Returning ``None`` leaves the cell unchanged;
        returning ``(char, style)`` writes that payload.

        Args:
            fn: Per-cell mapper.
        """
        for row in range(self._area.height):
            for column in range(self._area.width):
                abs_x = self._area.x + column
                abs_y = self._area.y + row
                char, style = self._stage._read_absolute(abs_x, abs_y)
                result = fn(column, row, char, style)
                if result is None:
                    continue
                new_char, new_style = result
                self.paint(column, row, new_char, new_style)


class Stage:
    """Treat the active grid as an addressable cell lattice.

    Exposed as ``host.stage`` / ``ctx.stage``. Layout geometry is read
    from the always-on ``LayoutMap``; paints accumulate into a
    per-frame ``CellCanvas`` overlay retrieved via ``take_overlay``.
    """

    def __init__(self, host: "AbstractHost | None" = None) -> None:
        if host is None:
            from xnano.core.hosts import get_active_host

            host = get_active_host()
        self._host = host
        self._layout = LayoutMap()
        self._wireframe: bool = False
        self._wireframe_region: Area | None = None
        self._wireframe_of: tuple[Any, str | None] | None = None
        self._paint_canvas: CellCanvas | None = None
        self._size_override: Size | None = None

    @property
    def host(self) -> "AbstractHost | None":
        """Host this stage is bound to, if any."""
        return self._host

    @property
    def size(self) -> Size:
        """Active lattice size in cells.

        Prefers an explicit override, then ``host.device.size``, else
        a zero size.
        """
        if self._size_override is not None:
            return self._size_override
        host = self._host
        if host is not None:
            device = getattr(host, "device", None)
            if device is not None:
                size = getattr(device, "size", None)
                if isinstance(size, Size):
                    return size
                if (
                    isinstance(size, tuple)
                    and len(size) == 2
                    and all(isinstance(part, int) for part in size)
                ):
                    return Size(width=size[0], height=size[1])
        return Size(width=0, height=0)

    def set_size(self, size: Size) -> None:
        """Override the lattice size used for paint/wireframe canvases.

        Args:
            size: Explicit stage size.
        """
        self._size_override = size

    @property
    def layout(self) -> LayoutMap:
        """Resolved geometry map for the current frame."""
        return self._layout

    def region(self, area: Area) -> StageRegion:
        """Return a paintable view over ``area``.

        Args:
            area: Absolute cell area on the stage.

        Returns:
            A ``StageRegion`` bound to this stage.
        """
        return StageRegion(self, area)

    def region_of(
        self,
        interface: Any,
        field: str | None = None,
    ) -> StageRegion | None:
        """Return a region for a recorded layout entry.

        Args:
            interface: BaseGrid/component instance.
            field: Field name, or ``None`` for the interface root.

        Returns:
            A ``StageRegion``, or ``None`` if unmapped.
        """
        area = self._layout.region_of(interface, field)
        if area is None:
            return None
        return StageRegion(self, area)

    def wireframe(
        self,
        enabled: bool = True,
        *,
        region: Area | None = None,
        of: tuple[Any, str | None] | None = None,
    ) -> None:
        """Enable or disable wireframe overlay for the layout map.

        Wireframe is an **overlay only** — it never reflows, replaces,
        or locks in-slot content. The layout lattice (sizing/flex) stays
        the source of truth; content inside fields paints unchanged.

        Scope:
            * default — entire active ``LayoutMap``
            * ``region=`` — only entries intersecting that ``Area``
            * ``of=(interface, field)`` — one field (or whole interface
              when ``field`` is ``None``)

        Args:
            enabled: Whether wireframe mode is active.
            region: Optional absolute area filter.
            of: Optional ``(interface, field)`` resolved via LayoutMap.
        """
        self._wireframe = bool(enabled)
        self._wireframe_region = region
        self._wireframe_of = of

    def is_wireframe(self) -> bool:
        """Return whether wireframe mode is enabled.

        Returns:
            ``True`` when ``wireframe`` last enabled the flag.
        """
        return self._wireframe

    def take_overlay(self) -> CellCanvas | None:
        """Return accumulated ``CellCanvas`` paints this frame.

        Does not clear paints; call ``clear_paints`` at frame end.

        Returns:
            The paint canvas if any cells were written, else ``None``.
        """
        return self._paint_canvas

    def clear_paints(self) -> None:
        """Drop accumulated paint overlay for the next frame."""
        self._paint_canvas = None

    def _wireframe_entries(self) -> Sequence[LayoutEntry]:
        """Layout entries included in the current wireframe scope."""
        entries = list(self._layout.entries())
        if self._wireframe_of is not None:
            interface, field = self._wireframe_of
            target = self._layout.region_of(interface, field)
            if target is None:
                return ()
            return [
                entry
                for entry in entries
                if _areas_intersect(entry.area, target)
                or (entry.interface is interface and entry.field == field)
            ]
        if self._wireframe_region is not None:
            region = self._wireframe_region
            return [
                entry
                for entry in entries
                if _areas_intersect(entry.area, region)
            ]
        return entries

    def build_wireframe_canvas(self) -> CellCanvas | None:
        """Draw field boundaries from the layout map with box chars.

        Overlay-only: does not modify field content. Labels prefer the
        field name, falling back to the interface type name. Honors the
        scope set by ``wireframe`` (full map, region, or field).

        Returns:
            A wireframe ``CellCanvas``, or ``None``.
        """
        entries = self._wireframe_entries()
        if not entries:
            return None
        size = self.size
        if size.width <= 0 or size.height <= 0:
            # Derive a bounding box from recorded areas when size is
            # not yet known from the host device.
            max_right = 0
            max_bottom = 0
            for entry in entries:
                area = entry.area
                max_right = max(max_right, area.x + area.width)
                max_bottom = max(max_bottom, area.y + area.height)
            if max_right <= 0 or max_bottom <= 0:
                return None
            size = Size(width=max_right, height=max_bottom)

        canvas = CellCanvas(width=size.width, height=size.height)
        ordered = sorted(entries, key=lambda entry: entry.z)
        for entry in ordered:
            label = entry.field
            if not label:
                interface = entry.interface
                label = type(interface).__name__ if interface else ""
            _draw_wireframe_box(canvas, entry.area, label=label or "")
        return canvas

    def _ensure_paint_canvas(self) -> CellCanvas:
        """Return the paint canvas, allocating from ``size``."""
        if self._paint_canvas is None:
            size = self.size
            width = size.width
            height = size.height
            if width <= 0 or height <= 0:
                width = max(width, 1)
                height = max(height, 1)
            self._paint_canvas = CellCanvas(width=width, height=height)
        return self._paint_canvas

    def _paint_absolute(
        self,
        x: int,
        y: int,
        char: str,
        style: Any = None,
    ) -> None:
        """Write a cell in absolute stage coordinates.

        Args:
            x: Absolute column.
            y: Absolute row.
            char: Character to paint.
            style: Optional style payload.
        """
        canvas = self._ensure_paint_canvas()
        # Grow the canvas if a paint lands outside the current bounds.
        if x >= canvas.width or y >= canvas.height:
            new_width = max(canvas.width, x + 1)
            new_height = max(canvas.height, y + 1)
            grown = CellCanvas(width=new_width, height=new_height)
            for row in range(canvas.height):
                for column in range(canvas.width):
                    glyph, cell_style = canvas.get_cell(column, row)
                    grown.set_cell(column, row, glyph, cell_style)
            self._paint_canvas = grown
            canvas = grown
        canvas.set_cell(x, y, char, style)

    def _read_absolute(self, x: int, y: int) -> tuple[str, Any]:
        """Read a cell from the paint canvas (blank if unpainted).

        Args:
            x: Absolute column.
            y: Absolute row.

        Returns:
            ``(char, style)`` for the cell.
        """
        if self._paint_canvas is None:
            return (" ", None)
        return self._paint_canvas.get_cell(x, y)


def _areas_intersect(left: Area, right: Area) -> bool:
    """Return whether two areas share any cell.

    Args:
        left: First area.
        right: Second area.

    Returns:
        ``True`` when the rectangles overlap.
    """
    return not (
        left.x + left.width <= right.x
        or right.x + right.width <= left.x
        or left.y + left.height <= right.y
        or right.y + right.height <= left.y
    )


def _draw_wireframe_box(
    canvas: CellCanvas,
    area: Area,
    *,
    label: str = "",
) -> None:
    """Stroke a box-drawing outline into ``canvas`` for ``area``.

    Args:
        canvas: Destination cell lattice.
        area: Absolute region to outline.
        label: Optional top-edge label.
    """
    if area.width <= 0 or area.height <= 0:
        return

    left = area.x
    top = area.y
    right = area.x + area.width - 1
    bottom = area.y + area.height - 1

    if area.width == 1 and area.height == 1:
        canvas.set_cell(left, top, "□")
        return

    if area.width == 1:
        for row in range(top, bottom + 1):
            canvas.set_cell(left, row, "│")
        return

    if area.height == 1:
        for column in range(left, right + 1):
            canvas.set_cell(column, top, "─")
        return

    canvas.set_cell(left, top, "┌")
    canvas.set_cell(right, top, "┐")
    canvas.set_cell(left, bottom, "└")
    canvas.set_cell(right, bottom, "┘")

    for column in range(left + 1, right):
        canvas.set_cell(column, top, "─")
        canvas.set_cell(column, bottom, "─")
    for row in range(top + 1, bottom):
        canvas.set_cell(left, row, "│")
        canvas.set_cell(right, row, "│")

    if label:
        # Place the label on the top edge, clipped to the inner width.
        inner_width = max(0, area.width - 2)
        if inner_width > 0:
            text = f" {label} "
            if len(text) > inner_width:
                text = label[:inner_width]
            start = left + 1
            for offset, glyph in enumerate(text):
                if start + offset >= right:
                    break
                canvas.set_cell(start + offset, top, glyph)


__all__ = (
    "CellCanvas",
    "CellSpan",
    "LayoutEntry",
    "LayoutMap",
    "Stage",
    "StageRegion",
)
