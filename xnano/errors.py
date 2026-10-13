"""
xnano.errors

Errors a terminal raises about itself.
"""

from __future__ import annotations


class TerminalError(RuntimeError):
    """Base class of the errors a terminal raises about itself."""


class TerminalClosedError(TerminalError):
    """Raised by a terminal that has been closed."""


class TerminalAlreadyOpenError(TerminalError):
    """Raised when a second live terminal is opened while one is already open."""


def release_frames(error: BaseException | None) -> str:
    """
    Drop the stack frames an error and the errors that caused it carry, and return their text.

    A traceback keeps every frame it passed through alive, with all their local variables,
    and some of those hold things that may only be released on the terminal's own thread. The
    text keeps what a developer needs to find the mistake.
    """
    if error is None:
        return ''
    import traceback  # only a failing terminal needs it

    report = ''.join(traceback.format_exception(error))
    pending = [error]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        current.__traceback__ = None
        pending.extend(
            cause
            for cause in (current.__cause__, current.__context__)
            if cause is not None
        )
    return report
