"""xnano.beta.components.loader

---

Show determinate progress or an indeterminate spinner.
"""

from __future__ import annotations

import dataclasses
import time
from typing import TYPE_CHECKING, Literal, Sequence, TypeAlias

from xnano.beta.components.component import Component
from xnano.beta.core.content import Gauge, LineGauge, TextBlock

if TYPE_CHECKING:
    from xnano.beta.colors import ColorLike
    from xnano.beta.components.component import ComponentRenderContext
    from xnano.beta.components.text import Text

LoaderStyle: TypeAlias = Literal["spinner", "bar", "line"]
"""Visual style for a ``Loader`` component."""

LoaderSymbolPreset: TypeAlias = Literal[
    "dots",
    "line",
    "grow",
    "circle",
    "bounce",
    "arc",
]
"""Named spinner frame presets."""

LoaderSymbols: TypeAlias = Sequence[str] | LoaderSymbolPreset
"""Explicit spinner frames or a named preset."""

LoaderLabel: TypeAlias = "str | Text | Literal[False] | None"
"""Label text, nested Text, auto percentage, or hidden."""

_SYMBOL_PRESETS: dict[str, tuple[str, ...]] = {
    "dots": ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"),
    "line": ("-", "\\", "|", "/"),
    "grow": ("▁", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃"),
    "circle": ("◐", "◓", "◑", "◒"),
    "bounce": (".  ", ".. ", "...", " ..", "  .", "   "),
    "arc": ("◜", "◠", "◝", "◞", "◡", "◟"),
}


def resolve_loader_symbols(symbols: LoaderSymbols) -> tuple[str, ...]:
    """Resolve a preset name or frame sequence into spinner frames.

    Args:
        symbols: Named preset or ordered frame strings.

    Returns:
        A non-empty tuple of frame strings.

    Raises:
        ValueError: When no frames are provided.
    """
    if isinstance(symbols, str):
        if symbols in _SYMBOL_PRESETS:
            return _SYMBOL_PRESETS[symbols]
        raise ValueError(f"Unknown loader symbol preset: {symbols!r}")
    frames = tuple(str(frame) for frame in symbols)
    if not frames:
        raise ValueError("Loader symbols require at least one frame.")
    return frames


@dataclasses.dataclass
class Loader(Component):
    """Determinate progress indicator or indeterminate spinner.

    Leave ``value`` as ``None`` to show a spinner. Set ``value`` to a ratio,
    or pair it with ``total``, to show measurable progress.

    Example:
        ``Loader(value=42, total=100, label=True)``

    Attributes:
        value: Current amount, ratio, or ``None`` for indeterminate.
        total: When set, ratio is ``value / total``.
        style: ``"spinner"``, ``"bar"``, or ``"line"``.
        label: Overlay text, auto percentage, nested Text, or hidden.
        symbols: Spinner frames or a named preset.
        interval: Milliseconds between spinner frames.
        color: Primary foreground / filled color.
        background: Widget background color.
        filled_color: Line style filled-portion color.
        unfilled_color: Line style unfilled-portion color.
        running: Whether spinner animation advances.
    """

    value: float | None = None
    """Current amount, ratio, or ``None`` for indeterminate work."""
    total: float | None = None
    """When set, the ratio is ``value / total``."""
    style: LoaderStyle = "spinner"
    """``"spinner"``, block ``"bar"``, or thin ``"line"`` gauge."""
    label: LoaderLabel = None
    """Overlay text. ``None`` auto-derives a percentage when determinate."""
    symbols: LoaderSymbols = "dots"
    """Spinner frames or a named preset."""
    interval: int = 80
    """Milliseconds between spinner frames."""
    color: "ColorLike" = "green"
    """Primary foreground / filled color."""
    background: "ColorLike | None" = None
    """Widget background color."""
    filled_color: "ColorLike | None" = None
    """Line style filled-portion color (defaults to ``color``)."""
    unfilled_color: "ColorLike | None" = None
    """Line style unfilled-portion color."""
    running: bool = True
    """Whether spinner animation advances with wall time."""
    fit_content: bool = dataclasses.field(default=False, kw_only=True)
    """Whether layout should use the loader's natural size."""

    _resolved_symbols: tuple[str, ...] = dataclasses.field(
        init=False, repr=False, compare=False
    )
    _epoch_ns: int = dataclasses.field(init=False, repr=False, compare=False)
    _frozen_frame: int = dataclasses.field(
        default=0, init=False, repr=False, compare=False
    )

    def component_post_init(self) -> None:
        """Resolve spinner frames and start the animation epoch."""
        if self.style not in ("spinner", "bar", "line"):
            raise ValueError(f"Unsupported loader style: {self.style!r}")
        if self.interval <= 0:
            raise ValueError("Loader interval must be greater than zero.")
        self._resolved_symbols = resolve_loader_symbols(self.symbols)
        self._epoch_ns = time.monotonic_ns()
        self._frozen_frame = 0

    @property
    def resolved_symbols(self) -> tuple[str, ...]:
        """Resolved spinner frame ladder."""
        return self._resolved_symbols

    @property
    def ratio(self) -> float:
        """Return the completion ratio, clamped to ``0.0``–``1.0``.

        Indeterminate loaders report ``0.0``.
        """
        if self.value is None:
            return 0.0
        if self.total is None:
            raw = float(self.value)
        elif self.total <= 0:
            raw = 0.0
        else:
            raw = float(self.value) / float(self.total)
        return max(0.0, min(1.0, raw))

    @property
    def finished(self) -> bool:
        """Whether determinate progress has reached completion."""
        if self.value is None:
            return False
        return self.ratio >= 1.0

    def restart(self) -> None:
        """Reset the spinner epoch to the current monotonic time."""
        self._epoch_ns = time.monotonic_ns()
        self._frozen_frame = 0

    def _resolve_label_text(self) -> str | None:
        label = self.label
        if label is False:
            return None
        if label is None:
            if self.value is None:
                return None
            return f"{round(self.ratio * 100)}%"
        if isinstance(label, str):
            return label
        plain = getattr(label, "plain", None)
        if callable(plain):
            return str(plain())
        content = getattr(label, "content", None)
        if content is not None:
            return str(content)
        return str(label)

    def _spinner_frame_index(self) -> int:
        frames = self._resolved_symbols
        if not frames:
            return 0
        if not self.running:
            return self._frozen_frame % len(frames)
        elapsed_ms = (time.monotonic_ns() - self._epoch_ns) / 1_000_000
        index = int(elapsed_ms // self.interval) % len(frames)
        self._frozen_frame = index
        return index

    def _compose_spinner(self) -> TextBlock:
        frame = self._resolved_symbols[self._spinner_frame_index()]
        label = self._resolve_label_text()
        text = frame if not label else f"{frame} {label}"
        return TextBlock(
            text=text,
            color=self.color,
            background=self.background,
            z=self.z,
            visible=self.visible,
        )

    def _compose_determinate(self):
        label = self._resolve_label_text()
        ratio = self.ratio
        if self.style == "line":
            return LineGauge(
                progress=ratio,
                label=label,
                color=self.color,
                filled_color=self.filled_color or self.color,
                unfilled_color=self.unfilled_color,
                background=self.background,
                z=self.z,
                visible=self.visible,
            )
        return Gauge(
            progress=ratio,
            label=label,
            color=self.color,
            background=self.background,
            z=self.z,
            visible=self.visible,
        )

    def compose(self, ctx: "ComponentRenderContext"):
        """Compose spinner text or gauge content for this loader.

        Returns:
            Interface-neutral content for this loader.
        """
        if self.style == "spinner":
            return self._compose_spinner()
        if self.value is None:
            # Indeterminate bar/line: pulse the active spinner frame as
            # the gauge label while progress stays at zero.
            frame = self._resolved_symbols[self._spinner_frame_index()]
            label = self._resolve_label_text()
            pulse_label = frame if label is None else f"{frame} {label}"
            if self.style == "line":
                return LineGauge(
                    progress=0.0,
                    label=pulse_label,
                    color=self.color,
                    filled_color=self.filled_color or self.color,
                    unfilled_color=self.unfilled_color,
                    background=self.background,
                    z=self.z,
                    visible=self.visible,
                )
            return Gauge(
                progress=0.0,
                label=pulse_label,
                color=self.color,
                background=self.background,
                z=self.z,
                visible=self.visible,
            )
        return self._compose_determinate()


__all__ = (
    "Loader",
    "LoaderLabel",
    "LoaderStyle",
    "LoaderSymbolPreset",
    "LoaderSymbols",
    "resolve_loader_symbols",
)
