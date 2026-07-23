"""xnano.terminal

---

Terminal interface kind: ``Terminal`` host, cursor and device controls,
render nodes, and native effects lowering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xnano.terminal.terminal import (
        _ACTIVE_TERMINAL,
        Terminal,
        exit_terminal,
    )

__all__ = (
    "Terminal",
    "_ACTIVE_TERMINAL",
    "exit_terminal",
)


def __getattr__(name: str):
    if name in ("Terminal", "_ACTIVE_TERMINAL", "exit_terminal"):
        from xnano.terminal import terminal as _terminal

        return getattr(_terminal, name)
    if name == "exit":
        from xnano.terminal.terminal import exit_terminal

        return exit_terminal
    raise AttributeError(f"module 'xnano.terminal' has no attribute {name!r}")
