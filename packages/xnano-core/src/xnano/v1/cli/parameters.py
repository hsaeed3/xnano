"""
xnano.v1.cli.parameters

---

Describe positional arguments and named options on typed commands.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from typing import Any


@dataclasses.dataclass(init=False, repr=False, eq=False, slots=True)
class Argument:
    """
    Positional argument metadata.

    Attributes:
        help: Help text for this argument.
        metavar: Optional metavar override.
        choices: Optional allowed values.

    Example:
        >>> argument = Argument(help="Input file", metavar="PATH")
        >>> argument.metavar
        'PATH'
    """

    help: str | None
    metavar: str | None
    choices: Sequence[Any] | None

    def __init__(
        self,
        *,
        help: str | None = None,
        metavar: str | None = None,
        choices: Sequence[Any] | None = None,
    ) -> None:
        self.help = help
        self.metavar = metavar
        self.choices = choices


class Option:
    r"""
    Option metadata attached via default or ``Annotated``.

    Attributes:
        flags: Short/long option flags (e.g. ``\"-f\"``, ``\"--force\"``).
        help: Help text for this option.
        metavar: Optional metavar override.
        choices: Optional allowed values.
        hidden: When ``True``, omit from help.

    Example:
        >>> option = Option("-f", "--force", help="Overwrite output")
        >>> option.flags
        ('-f', '--force')
    """

    __slots__ = ('choices', 'flags', 'help', 'hidden', 'metavar')

    def __init__(
        self,
        *flags: str,
        help: str | None = None,
        metavar: str | None = None,
        choices: Sequence[Any] | None = None,
        hidden: bool = False,
    ) -> None:
        self.flags = tuple(flags)
        self.help = help
        self.metavar = metavar
        self.choices = choices
        self.hidden = hidden


__all__ = ('Argument', 'Option')
