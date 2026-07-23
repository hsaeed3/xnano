"""xnano.beta.components.input

---

Edit single-line or multiline text with optional masking and length limits.
"""

from __future__ import annotations

import dataclasses
from typing import Sequence

from xnano.beta.components.text import Text


@dataclasses.dataclass
class Input(Text):
    """Editable text field.

    Input is single-line by default. Set ``multiline=True`` for an editor
    that supports line breaks, selection, and navigation.

    Example:
        ``Input(placeholder="Search", submit_keys=("enter",))``

    Attributes:
        submit_keys: Keys reserved for submit hooks instead of text editing.
    """

    submit_keys: Sequence[str] = ("enter",)
    """Read-only convenience for hook matching; not consumed here."""

    def component_post_init(self) -> None:
        """Force input mode, then run ``Text`` editor setup."""
        self.input = True
        super().component_post_init()


__all__ = ("Input",)
