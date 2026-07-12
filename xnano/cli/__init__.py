"""xnano.cli"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xnano.cli.command import Command


__all__ = ("Command",)


def __getattr__(name: str):
    if name == "Command":
        from xnano.cli.command import Command

        return Command
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
