"""xnano.components.progress

---

``Progress`` component for ratio or value/total progress indicators.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Literal

from xnano.components.abstract import AbstractComponent


if TYPE_CHECKING:
    from xnano.color import ColorLike
    from xnano.components.abstract import ComponentRenderContext
    from xnano.tui.nodes import AbstractTerminalNode


ProgressStyle = Literal["bar", "line"]
"""Visual style for a ``Progress`` component."""


@dataclasses.dataclass
class Progress(AbstractComponent):
    """Declarative progress indicator.

    Describe *how much* is done — as a ``0.0``–``1.0`` ratio, or a ``value``
    out of a ``total`` — and pick a ``style`` (block bar or thin line), with
    an auto-derived percentage label.

        Progress(value=0.6)                      # 60% block bar
        Progress(value=70, total=100)            # derived ratio, "70%"
        Progress(value=0.4, style="line", label="cpu")
    """

    value: float = 0.0
    """Current progress. A ``0.0``–``1.0`` ratio, or an absolute amount when
    ``total`` is set."""
    total: float | None = None
    """When set, the ratio is ``value / total``; otherwise ``value`` is the
    ratio directly. A non-positive total yields a ratio of ``0.0``."""
    label: str | Literal[False] | None = None
    """Text drawn over the indicator. ``None`` auto-derives a percentage;
    ``False`` hides the label."""
    style: ProgressStyle = "bar"
    """``"bar"`` for a full block gauge, ``"line"`` for a thin line gauge."""
    color: ColorLike = "green"
    """Filled-portion foreground color."""
    background: ColorLike | None = None
    """Widget background color."""
    filled_color: ColorLike | None = None
    """``line`` style only: filled-portion color (defaults to ``color``)."""
    unfilled_color: ColorLike | None = None
    """``line`` style only: unfilled-portion color."""
    fit_content: bool = dataclasses.field(default=False, kw_only=True)

    @property
    def ratio(self) -> float:
        """Return the completion ratio, clamped to ``0.0``–``1.0``."""
        if self.total is None:
            raw = self.value
        elif self.total <= 0:
            raw = 0.0
        else:
            raw = self.value / self.total
        return max(0.0, min(1.0, raw))

    def _resolve_label(self) -> str | None:
        if self.label is False:
            return None
        if self.label is None:
            return f"{round(self.ratio * 100)}%"
        return self.label

    def compose(self, ctx):
        """Compose Content via Native tui payload of the existing node tree."""
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
        from xnano.tui.nodes import LineGaugeNode, ProgressBarNode

        ratio = self.ratio
        label = self._resolve_label()
        if self.style == "line":
            return LineGaugeNode(
                progress=ratio,
                label=label,
                color=self.color,
                filled_color=self.filled_color or self.color,
                unfilled_color=self.unfilled_color,
                background=self.background,
                z=self.z,
                visible=self.visible,
            )
        return ProgressBarNode(
            progress=ratio,
            label=label,
            color=self.color,
            background=self.background,
            z=self.z,
            visible=self.visible,
        )


__all__ = ("Progress", "ProgressStyle")
