"""xnano.components.input

---

Edit single-line or multiline text with optional masking and length limits.
"""

from __future__ import annotations

import dataclasses
import math
from typing import TYPE_CHECKING, Sequence

from xnano.area import Size
from xnano.components.text import Text

if TYPE_CHECKING:
    from xnano.components.component import ComponentRenderContext


@dataclasses.dataclass
class Input(Text):
    """Editable text field.

    Input is single-line by default. Set ``multiline=True`` for an editor
    that supports line breaks, selection, and navigation. Set
    ``auto_height=True`` for a composer that grows as the text soft-wraps,
    bounded by ``min_rows`` and ``max_rows`` — pair it with a
    ``Field(height="fit")`` slot so layout consumes the reported height.

    Example:
        ``Input(placeholder="Search", submit_keys=("enter",))``

    Attributes:
        submit_keys: Keys reserved for submit hooks instead of text editing.
        auto_height: Grow the reported height to fit soft-wrapped content.
        min_rows: Minimum reported height when ``auto_height`` is set.
        max_rows: Maximum reported height when ``auto_height`` is set.
    """

    submit_keys: Sequence[str] = ("enter",)
    """Read-only convenience for hook matching; not consumed here."""
    auto_height: bool = False
    """Report a preferred height that grows with soft-wrapped content.

    Works with a ``Field(height="fit")`` slot: the input measures how many
    rows its value occupies at the available width and reports that height,
    clamped to ``[min_rows, max_rows]`` — no manual ``grid_set_field`` loop.
    """
    min_rows: int = 1
    """Smallest reported height (rows) while ``auto_height`` is set."""
    max_rows: int | None = None
    """Largest reported height (rows) while ``auto_height`` is set, or
    ``None`` for unbounded growth."""

    def component_post_init(self) -> None:
        """Force input mode, then run ``Text`` editor setup."""
        self.input = True
        super().component_post_init()

    def _wrapped_row_count(self, text: str, width: int) -> int:
        """Return how many rows ``text`` occupies at ``width`` cells."""
        lines = text.split("\n")
        if width <= 0 or not self.wrap:
            return max(1, len(lines))
        rows = 0
        for line in lines:
            rows += max(1, math.ceil(len(line) / width))
        return max(1, rows)

    def get_size(self, ctx: "ComponentRenderContext") -> Size:
        """Report the preferred cell size, growing with content when asked."""
        text = self.value
        width = ctx.area.width
        if self.auto_height:
            rows = self._wrapped_row_count(text, width)
            rows = max(self.min_rows, rows)
            if self.max_rows is not None:
                rows = min(self.max_rows, rows)
        else:
            rows = self.rows if self.rows is not None else text.count("\n") + 1
        preferred_width = width or max(
            (len(line) for line in text.split("\n")), default=0
        )
        return Size(width=preferred_width, height=rows)


__all__ = ("Input",)
