"""xnano.beta.components.bar

---

Render compact trends and distributions with configurable glyphs.
"""

from __future__ import annotations

import dataclasses
import unicodedata
from typing import TYPE_CHECKING, Literal, Sequence, TypeAlias

from xnano.beta.components.component import Component
from xnano.beta.core.content import CellCanvas, CellSpan, SparklineBar
from xnano.beta.core.content import Sparkline as SparklineContent

if TYPE_CHECKING:
    from xnano.beta.colors import ColorLike
    from xnano.beta.components.component import ComponentRenderContext

BarDirection: TypeAlias = Literal["up", "down"]
"""Whether bar samples grow upward or downward."""

BarGlyphPreset: TypeAlias = Literal["blocks", "braille", "ascii"]
"""Named glyph ladders for compact bar rendering."""

BarGlyphs: TypeAlias = str | Sequence[str] | BarGlyphPreset
"""Explicit ordered symbols or a named preset."""

_GLYPH_PRESETS: dict[str, tuple[str, ...]] = {
    "blocks": (" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"),
    "braille": (" ", "⣀", "⣤", "⣶", "⣿"),
    "ascii": (" ", ".", ":", "-", "=", "+", "*", "#", "@"),
}

_DEFAULT_GLYPHS: tuple[str, ...] = _GLYPH_PRESETS["blocks"]


def _is_single_cell_glyph(symbol: str) -> bool:
    """Return whether ``symbol`` occupies one terminal cell."""
    if not symbol or len(symbol) != 1:
        # Allow multi-codepoint graphemes only when each is narrow.
        if not symbol:
            return False
        width = 0
        for character in symbol:
            category = unicodedata.east_asian_width(character)
            if category in ("F", "W"):
                return False
            if unicodedata.combining(character):
                continue
            width += 1
            if width > 1:
                return False
        return width == 1
    category = unicodedata.east_asian_width(symbol)
    return category not in ("F", "W")


def resolve_bar_glyphs(glyphs: BarGlyphs) -> tuple[str, ...]:
    """Resolve a preset name or symbol sequence into ordered glyphs.

    Args:
        glyphs: Named preset or ordered symbol sequence.

    Returns:
        A tuple of at least two single-cell symbols.

    Raises:
        ValueError: When the glyph set is invalid.
    """
    if isinstance(glyphs, str) and glyphs in _GLYPH_PRESETS:
        return _GLYPH_PRESETS[glyphs]
    if isinstance(glyphs, str):
        symbols = tuple(glyphs)
    else:
        symbols = tuple(str(symbol) for symbol in glyphs)
    if len(symbols) < 2:
        raise ValueError("Bar glyphs require at least two symbols.")
    for symbol in symbols:
        if not _is_single_cell_glyph(symbol):
            raise ValueError(
                f"Bar glyph {symbol!r} must occupy a single terminal cell."
            )
    return symbols


@dataclasses.dataclass
class Bar(Component):
    """Compact inline bar chart for a sequence of samples.

    Fills its layout slot by default and scales sample heights across the
    available vertical area when using the native sparkline path. Supply
    ``colors`` with one entry per sample to tint individual bars.

    Example:
        ``Bar(data=(2, 5, 3, 8), color="cyan")``

    Attributes:
        data: Sequence of sample values.
        color: Default bar foreground color.
        colors: Optional per-bar foreground colors.
        background: Widget background color.
        max_value: Explicit y-axis ceiling; ``None`` auto-scales.
        direction: Whether samples grow ``"up"`` or ``"down"``.
        glyphs: Ordered fill ladder or a named preset.
        absent_color: Color applied to zero or absent samples.
        absent_glyph: Glyph drawn for absent samples.
    """

    data: Sequence[int | float] = dataclasses.field(default_factory=tuple)
    """Sequence of sample values."""
    color: "ColorLike | None" = None
    """Default bar foreground color."""
    colors: Sequence["ColorLike"] | None = None
    """Optional per-bar foreground colors, one per ``data`` entry."""
    background: "ColorLike | None" = None
    """Widget background color."""
    max_value: int | float | None = None
    """Explicit y-axis ceiling; ``None`` auto-scales to the dataset max."""
    direction: BarDirection = "up"
    """Whether samples grow ``"up"`` or ``"down"``."""
    glyphs: BarGlyphs = "blocks"
    """Ordered fill ladder or a named preset (``blocks``/``braille``/``ascii``)."""
    absent_color: "ColorLike | None" = None
    """Color applied to zero or absent samples."""
    absent_glyph: str | None = None
    """Glyph drawn for absent samples."""
    fit_content: bool = dataclasses.field(default=False, kw_only=True)
    """Whether layout should use the sparkline's natural width."""

    _resolved_glyphs: tuple[str, ...] = dataclasses.field(
        init=False, repr=False, compare=False
    )

    def component_post_init(self) -> None:
        """Resolve and validate the glyph ladder once."""
        self._resolved_glyphs = resolve_bar_glyphs(self.glyphs)
        if self.direction not in ("up", "down"):
            raise ValueError(f"Unsupported bar direction: {self.direction!r}")
        if self.absent_glyph is not None and not _is_single_cell_glyph(
            self.absent_glyph
        ):
            raise ValueError(
                "absent_glyph must occupy a single terminal cell."
            )
        if self.colors is not None and len(self.colors) != len(self.data):
            raise ValueError("colors must contain one entry per data sample.")

    @property
    def resolved_glyphs(self) -> tuple[str, ...]:
        """Resolved ordered glyph ladder used for rendering."""
        return self._resolved_glyphs

    def _sample_values(self) -> list[float]:
        values = [float(sample) for sample in self.data]
        if self.direction == "down" and values:
            ceiling = (
                float(self.max_value)
                if self.max_value is not None
                else max(values)
            )
            if ceiling <= 0:
                return [0.0 for _ in values]
            return [max(0.0, ceiling - value) for value in values]
        return [max(0.0, value) for value in values]

    def _ceiling(self, values: Sequence[float]) -> float:
        if self.max_value is not None:
            return max(0.0, float(self.max_value))
        if not values:
            return 1.0
        peak = max(values)
        return peak if peak > 0 else 1.0

    def _uses_native_sparkline(self) -> bool:
        """Prefer the native sparkline path for the default block ladder."""
        return self._resolved_glyphs == _DEFAULT_GLYPHS

    def _compose_sparkline_content(self) -> SparklineContent:
        values = self._sample_values()
        data = tuple(int(round(value)) for value in values)
        bars: tuple[SparklineBar, ...] | None = None
        if self.colors is not None:
            bars = tuple(
                SparklineBar(value=int(round(value)), color=color)
                for value, color in zip(values, self.colors, strict=True)
            )
        max_value = (
            int(round(float(self.max_value)))
            if self.max_value is not None
            else None
        )
        return SparklineContent(
            data=data,
            bars=bars,
            max_value=max_value,
            color=self.color,
            background=self.background,
            absent_value_color=self.absent_color,
            absent_value_symbol=self.absent_glyph,
            z=self.z,
            visible=self.visible,
        )

    def _compose_glyph_canvas(
        self,
        ctx: "ComponentRenderContext",
    ) -> CellCanvas:
        values = self._sample_values()
        ceiling = self._ceiling(values)
        ladder = self._resolved_glyphs
        top = len(ladder) - 1
        absent = (
            self.absent_glyph if self.absent_glyph is not None else ladder[0]
        )
        spans: list[CellSpan] = []
        for index, value in enumerate(values):
            if value <= 0:
                glyph = absent
                color = self.absent_color or self.color
            else:
                level = int(round((value / ceiling) * top))
                level = max(0, min(top, level))
                glyph = ladder[level]
                if self.colors is not None:
                    color = self.colors[index]
                else:
                    color = self.color
            spans.append(
                CellSpan(
                    glyph,
                    color=color,
                    background=self.background,
                )
            )
        width = max(1, len(spans) or int(ctx.area.width or 1))
        if not spans:
            spans = [CellSpan(" ", background=self.background)]
        return CellCanvas(
            width=width,
            height=1,
            rows=(tuple(spans),),
            z=self.z,
            visible=self.visible,
        )

    def compose(self, ctx: "ComponentRenderContext"):
        """Compose sparkline content, with a native/canvas paint path.

        Returns:
            Interface-neutral content for this bar.
        """
        if not self._uses_native_sparkline():
            return self._compose_glyph_canvas(ctx)

        return self._compose_sparkline_content()


# Deprecated migration alias.
Sparkline = Bar


__all__ = (
    "Bar",
    "BarDirection",
    "BarGlyphPreset",
    "BarGlyphs",
    "Sparkline",
    "resolve_bar_glyphs",
)
