"""xnano.beta.cli.help

---

Format command help and user-facing errors for terminals and plain-text
streams.
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from xnano.beta.cli.command import Command


def should_use_styled_help(stream: TextIO | None = None) -> bool:
    """Return whether styled help should be attempted.

    Args:
        stream: Output stream (defaults to stdout).

    Returns:
        ``True`` when a live color-capable TTY is available.
    """
    if os.environ.get("NO_COLOR"):
        return False
    target = stream if stream is not None else sys.stdout
    isatty = getattr(target, "isatty", None)
    return bool(callable(isatty) and isatty())


def format_plain_help(command: "Command") -> str:
    """Build deterministic plain-text help for ``command``.

    Args:
        command: Command whose help should be rendered.

    Returns:
        Help text ending with a newline when non-empty.
    """
    lines: list[str] = []
    usage = f"Usage: {command.name or 'cli'}"
    if command.subcommands:
        usage += " [COMMAND]"

    options_list = [
        parameter for parameter in command.parameters if parameter.is_option
    ]
    arguments_list = [
        parameter
        for parameter in command.parameters
        if not parameter.is_option
    ]

    if options_list:
        usage += " [OPTIONS]"
    for argument in arguments_list:
        label = argument.metavar or argument.parameter_name.upper()
        usage += f" {label}"

    lines.append(usage)
    lines.append("")

    if command.description:
        lines.append(command.description.strip())
        lines.append("")

    if arguments_list:
        lines.append("Arguments:")
        for argument in arguments_list:
            help_text = argument.help or ""
            label = argument.metavar or argument.parameter_name.upper()
            desc = f"  {label:<20} {help_text}".rstrip()
            if argument.default is not command.UNSET:
                desc += f" (default: {argument.default})"
            lines.append(desc)
        lines.append("")

    if options_list or command.show_help:
        lines.append("Options:")
        for option in options_list:
            if option.hidden:
                continue
            flags_str = ", ".join(option.flags or [])
            help_text = option.help or ""
            desc = f"  {flags_str:<20} {help_text}".rstrip()
            if option.default is not command.UNSET:
                desc += f" [default: {option.default}]"
            lines.append(desc)
        if command.show_help:
            lines.append(f"  {'--help, -h':<20} Show this message and exit.")
        lines.append("")

    if command.subcommands:
        lines.append("Commands:")
        for name, subcommand in command.subcommands.items():
            description = subcommand.description or ""
            first = description.strip().split("\n")[0]
            lines.append(f"  {name:<20} {first}")
        lines.append("")

    return "\n".join(lines)


def render_help(
    command: "Command",
    *,
    stream: TextIO | None = None,
) -> str:
    """Render help for ``command``, optionally via terminal components.

    Args:
        command: Command to document.
        stream: Unused except for TTY detection.

    Returns:
        Help text. Styled rendering falls back to plain text when the
        terminal path is unavailable.
    """
    plain = format_plain_help(command)
    if not should_use_styled_help(stream):
        return plain
    try:
        from xnano.beta.components.text import Text
        from xnano.beta.terminal import Terminal

        # One-shot styled render; still return plain for callers that
        # capture strings (tests, pipes). Styled paint is best-effort.
        Terminal().render(Text(plain))
    except Exception:
        pass
    return plain


def print_error(
    message: str,
    command: "Command | None" = None,
    *,
    file: TextIO | None = None,
) -> None:
    """Print an error (and optional help) to stderr."""
    target = file if file is not None else sys.stderr
    print(f"Error: {message}", file=target)
    if command is not None:
        print(format_plain_help(command), file=target, end="")


__all__ = (
    "format_plain_help",
    "print_error",
    "render_help",
    "should_use_styled_help",
)
