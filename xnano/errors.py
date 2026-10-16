"""
xnano.errors

Errors a canvas raises about itself.
"""

from __future__ import annotations


class TerminalError(RuntimeError):
    """Base class of the errors a canvas raises about itself."""


class TerminalClosedError(TerminalError):
    """Raised by a canvas that has been closed, or when no canvas is running."""


class TerminalAlreadyOpenError(TerminalError):
    """Raised when a second canvas is opened on the screen while one is already there."""


def release_frames(error: BaseException | None) -> str:
    """
    Drop the stack frames an error and the errors that caused it carry, and return their text.

    A traceback keeps every frame it passed through alive, with all their local variables,
    and some of those hold things that may only be released on the canvas's own thread. The
    text keeps what a developer needs to find the mistake.
    """
    if error is None:
        return ''
    import traceback  # only a failing canvas needs it

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
