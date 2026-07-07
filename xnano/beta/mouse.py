"""xnano.mouse

Aliases for mouse-specific (non-event) related types used by
``xnano.beta.events`` and ``xnano.beta.hooks``.
"""

from __future__ import annotations

from typing import Literal, TypeAlias


MouseButton: TypeAlias = Literal["left", "right", "middle", "unknown"]
"""The name of a mouse button that can be pressed or released to trigger
a mouse event.
"""


__all__ = ("MouseButton",)
