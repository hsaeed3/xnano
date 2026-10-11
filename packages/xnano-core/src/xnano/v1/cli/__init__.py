"""
xnano.v1.cli

---

Build typed commands, options, subcommands, and help screens.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xnano.v1.cli.command import Command, HelpException
    from xnano.v1.cli.errors import CliError
    from xnano.v1.cli.help import render_help
    from xnano.v1.cli.parameters import Argument, Option

__all__ = (
    'Argument',
    'CliError',
    'Command',
    'HelpException',
    'Option',
    'render_help',
)


def __getattr__(name: str) -> Any:
    if name in {'Command', 'HelpException'}:
        from xnano.v1.cli import command as _command

        return getattr(_command, name)
    if name in {'Argument', 'Option'}:
        from xnano.v1.cli import parameters as _parameters

        return getattr(_parameters, name)
    if name == 'CliError':
        from xnano.v1.cli.errors import CliError

        return CliError
    if name == 'render_help':
        from xnano.v1.cli import help as _help

        return _help.render_help
    raise AttributeError(f"module 'xnano.v1.cli' has no attribute {name!r}")


def __dir__() -> list[str]:
    return list(__all__)
