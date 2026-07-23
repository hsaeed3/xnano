"""xnano.beta.cli.errors

---

Errors raised while parsing or running commands.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xnano.beta.cli.command import Command


@dataclasses.dataclass
class CliError(Exception):
    """User-facing CLI failure.

    Attributes:
        message: Error text shown to the user.
        command: Command that failed, when known.
        exit_code: Process exit status used by ``run()``.
    """

    message: str
    """Error text shown to the user."""
    command: "Command | None" = None
    """Command that failed."""
    exit_code: int = 2
    """Process exit status."""

    def __post_init__(self) -> None:
        super().__init__(self.message)


@dataclasses.dataclass
class HelpRequested(Exception):
    """Internal control flow when help was requested.

    Attributes:
        command: Command whose help was requested.
    """

    command: "Command"
    """Command whose help was requested."""


__all__ = ("CliError", "HelpRequested")
