"""xnano.beta.components.markdown

---

Render Markdown content with terminal styling.
"""

from __future__ import annotations

import dataclasses
import pathlib

from xnano.beta.components.text import Text


@dataclasses.dataclass
class Markdown(Text):
    """Display Markdown with terminal-friendly styling.

    Content remains live and supports the same color, alignment, and wrapping
    options as ``Text``.

    Example:
        ``Markdown(content="# Status\\n\\nAll systems operational.")``

    Attributes:
        base_path: Root for resolving relative image and link targets.
        images: When ``True``, allow image constructs when supported.
        links: When ``True``, allow link constructs when supported.
    """

    base_path: pathlib.Path | None = None
    """Root path for resolving relative image and link targets."""
    images: bool = True
    """Whether image constructs may be emitted when supported."""
    links: bool = True
    """Whether link constructs may be emitted when supported."""

    def component_post_init(self) -> None:
        """Force markdown mode, then run ``Text`` setup."""
        self.markdown = True
        super().component_post_init()


__all__ = ("Markdown",)
