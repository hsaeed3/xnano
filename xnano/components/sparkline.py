"""xnano.components.sparkline

---

``Sparkline`` component for compact inline bar charts.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from xnano.components.abstract import AbstractComponent

if TYPE_CHECKING:
    from xnano.color import ColorLike
    from xnano.components.abstract import ComponentRenderContext
    from xnano.terminal.nodes import AbstractTerminalNode


@dataclasses.dataclass
class Sparkline(AbstractComponent):
    """Compact inline bar chart for a sequence of samples.

    Fills the layout slot it is placed in and scales bar heights across the
    full vertical area. Supply ``colors`` with one entry per sample to tint
    individual bars — useful for gradients across a time series.
    """

    data: list[int] = dataclasses.field(default_factory=list)
    """Sequence of non-negative sample values."""
    colors: tuple[ColorLike, ...] | None = None
    """Optional per-bar foreground colors, one per ``data`` entry."""
    max_value: int | None = None
    """Explicit y-axis ceiling; ``None`` auto-scales to the dataset max."""
    color: ColorLike | None = None
    """Default bar color when ``colors`` is omitted."""
    background: ColorLike | None = None
    """Widget background color."""
    absent_value_color: ColorLike | None = None
    """Color applied to zero or absent samples."""
    absent_value_symbol: str | None = None
    """Glyph drawn for absent samples."""
    fit_content: bool = dataclasses.field(default=False, kw_only=True)

    def compose(self, ctx):
        """Compose
        [`Content`](../core/content.md#xnano.core.content.Content){data-preview}
        via Native tui payload of the existing node tree.
        """
        from xnano.core.content import Native

        return Native(
            interface_kind="tui",
            payload=self.get_terminal_node(ctx),
            z=self.z,
            visible=self.visible,
        )

    def get_terminal_node(
        self, ctx: ComponentRenderContext
    ) -> AbstractTerminalNode:
        from xnano.terminal.nodes import SparklineBarItem, SparklineNode

        bars: list[SparklineBarItem] | None = None
        if self.colors is not None:
            bars = [
                SparklineBarItem(value=value, color=color)
                for value, color in zip(self.data, self.colors, strict=True)
            ]
        return SparklineNode(
            data=self.data,
            bars=bars,
            max_value=self.max_value,
            color=self.color,
            background=self.background,
            absent_value_color=self.absent_value_color,
            absent_value_symbol=self.absent_value_symbol,
            z=self.z,
            visible=self.visible,
        )


__all__ = ("Sparkline",)
