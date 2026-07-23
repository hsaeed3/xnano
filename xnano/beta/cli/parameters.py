"""xnano.beta.cli.parameters

---

Describe positional arguments and named options on typed commands.
"""

from __future__ import annotations

from typing import Any, Sequence


class Argument:
    """Positional argument metadata.

    Attributes:
        help: Help text for this argument.
        metavar: Optional metavar override.
        choices: Optional allowed values.

    Example:
        >>> argument = Argument(help="Input file", metavar="PATH")
        >>> argument.metavar
        'PATH'
    """

    __slots__ = ("help", "metavar", "choices")

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
    """Option metadata attached via default or ``Annotated``.

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

    __slots__ = ("flags", "help", "metavar", "choices", "hidden")

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


__all__ = ("Argument", "Option")
