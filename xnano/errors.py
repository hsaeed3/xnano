"""
xnano.errors

Errors a canvas raises about itself, each one a labelled report.
"""

from __future__ import annotations

import os
import sys
import traceback
from collections.abc import Sequence
from types import TracebackType
from typing import ClassVar, Final, cast

from xnano._schema._errors import TerminalErrorCode as TerminalErrorCode
from xnano_core import ErrorDetail as _ErrorDetail
from xnano_core import ErrorReport as _ErrorReport
from xnano_core import ReportedError as _ReportedError

__all__ = [
    'TerminalAlreadyOpenError',
    'TerminalClosedError',
    'TerminalError',
    'TerminalErrorCode',
]

_TYPE_CODES: Final = frozenset({'validation.type', 'validation.keyword'})
"""Codes whose errors are also ``TypeError``, as Python raises for a wrong type or keyword."""

_VALUE_CODES: Final = frozenset({'validation.value', 'validation.bounds'})
"""Codes whose errors are also ``ValueError``, as pydantic's ``ValidationError`` is."""


class TerminalError(_ReportedError, RuntimeError):
    """
    An error a canvas raises about itself: one or more problems, each with a label.

    The text of the error is a report in the style of a pydantic ``ValidationError``: how
    many problems there are, then for each one where it is, what went wrong with its
    ``[code=...]`` and the value it is about, and what to do next. An uncaught
    ``TerminalError`` is printed with colors when the output is a terminal. Every
    ``TerminalError`` is also a ``RuntimeError``; one whose ``code`` is
    ``'validation.type'`` or ``'validation.keyword'`` is also a ``TypeError``, and one whose
    ``code`` is ``'validation.value'`` or ``'validation.bounds'`` is also a ``ValueError``, so
    ``except TypeError`` and ``except ValueError`` catch them as well.

    Args:
        message: What went wrong, in a sentence, or a whole ``ErrorReport``.
        code: The label of the problem; see [`TerminalErrorCode`][xnano.errors.TerminalErrorCode].
            Left out, it is the error class's own: ``'canvas.state'`` for a
            ``TerminalError``.
        location: Where the value is, such as ``'height'`` or ``('settings', 'height')``.
        hint: What to do next.
        title: What the report is about, such as ``'canvas.write()'``.
        input_value: The value the problem is about, when there is one.

    Attributes:
        code: The label of the first problem.
        report: The whole [`ErrorReport`][xnano_core.ErrorReport].
        details: The problems, each an [`ErrorDetail`][xnano_core.ErrorDetail].

    Examples:
        ```python
        import pytest
        from xnano.errors import TerminalError

        with pytest.raises(TypeError) as caught:
            raise TerminalError(
                'layer must be a whole number.',
                code='validation.type',
                location='layer',
                input_value='top',
            )
        error = caught.value
        assert isinstance(error, TerminalError) and error.code == 'validation.type'
        assert str(error).splitlines()[1:] == [
            'layer',
            "  layer must be a whole number. [code=validation.type, input_value='top', input_type=str]",
        ]
        assert TerminalError('The canvas cannot step now.').code == 'canvas.state'
        ```
    """

    default_code: ClassVar[TerminalErrorCode] = 'canvas.state'
    """The code of an error of this class that is raised without one."""

    def __new__(
        cls,
        message: str | _ErrorReport,
        *arguments: object,
        code: TerminalErrorCode | None = None,
        **keywords: object,
    ) -> TerminalError:
        """Pick the class that is also ``TypeError`` or ``ValueError`` for the code."""
        chosen: type[TerminalError] = cls
        if cls is TerminalError:
            first_code = (
                message.details[0].code if isinstance(message, _ErrorReport) else code
            )
            if first_code in _TYPE_CODES:
                chosen = _TerminalTypeError
            elif first_code in _VALUE_CODES:
                chosen = _TerminalValueError
        return cast('TerminalError', _ReportedError.__new__(chosen))

    def __init__(
        self,
        message: str | _ErrorReport,
        *,
        code: TerminalErrorCode | None = None,
        location: str | int | Sequence[str | int] | None = None,
        hint: str | None = None,
        title: str = '',
        **input_value: object,
    ) -> None:
        """
        Make the report of the error.

        Args:
            message: What went wrong, in a sentence, or a whole ``ErrorReport``.
            code: The label of the problem; the class's ``default_code`` when left out.
            location: Where the value is, such as ``'height'`` or ``('settings', 'height')``.
            hint: What to do next.
            title: What the report is about, such as ``'canvas.write()'``.
            input_value: The value the problem is about, given as ``input_value=...``.
        """
        if isinstance(message, _ErrorReport):
            report = message
        else:
            detail = _ErrorDetail(
                code or type(self).default_code,
                message,
                location=location,
                hint=hint,
                **input_value,
            )
            report = _ErrorReport(title, [detail])
        super().__init__(report)

    def __reduce__(self) -> tuple[type[TerminalError], tuple[object, ...]]:
        """Pickle through the public class, which picks the one for the code again."""
        public = TerminalError if type(self) in _HIDDEN_CLASSES else type(self)
        return (public, self.args)

    @property
    def report(self) -> _ErrorReport:
        """The whole report: its title and every problem."""
        return cast('_ErrorReport', self.args[0])

    @property
    def details(self) -> tuple[_ErrorDetail, ...]:
        """The problems, each an [`ErrorDetail`][xnano_core.ErrorDetail]."""
        return self.report.details

    @property
    def code(self) -> TerminalErrorCode:
        """The label of the first problem; see [`TerminalErrorCode`][xnano.errors.TerminalErrorCode]."""
        return cast('TerminalErrorCode', self.report.details[0].code)


class _TerminalTypeError(TerminalError, TypeError):
    """A ``TerminalError`` about a wrong type or keyword, which is also a ``TypeError``."""


class _TerminalValueError(TerminalError, ValueError):
    """A ``TerminalError`` about a value or its range, which is also a ``ValueError``."""


_HIDDEN_CLASSES: Final = (_TerminalTypeError, _TerminalValueError)
for _hidden in _HIDDEN_CLASSES:
    # Tracebacks name the public class.
    _hidden.__name__ = _hidden.__qualname__ = 'TerminalError'


class TerminalClosedError(TerminalError):
    """Raised by a canvas that has been closed, or when no canvas is running."""

    default_code: ClassVar[TerminalErrorCode] = 'canvas.closed'
    """The code of an error of this class that is raised without one."""


class TerminalAlreadyOpenError(TerminalError):
    """Raised when a second canvas is opened on the screen while one is already there."""

    default_code: ClassVar[TerminalErrorCode] = 'screen.already_open'
    """The code of an error of this class that is raised without one."""


def _is_colored(stream: object) -> bool:
    """Whether a report written to ``stream`` should have colors."""
    if os.environ.get('NO_COLOR'):
        return False
    if os.environ.get('FORCE_COLOR'):
        return True
    is_terminal = getattr(stream, 'isatty', None)
    return bool(is_terminal is not None and is_terminal())


def _print_uncaught(
    exception_type: type[BaseException],
    error: BaseException,
    error_traceback: TracebackType | None,
) -> None:
    """Print an uncaught ``TerminalError`` with its report styled; hand anything else on."""
    if not isinstance(error, TerminalError):
        _previous_exception_hook(exception_type, error, error_traceback)
        return
    stream = sys.stderr
    if stream is None:
        return
    printed = traceback.TracebackException(
        exception_type, error, error_traceback, compact=True
    )
    chunks = list(printed.format())
    last = ''.join(printed.format_exception_only())
    text = ''.join(chunks)
    if _is_colored(stream) and text.endswith(last):
        styled = error.report.render(is_colored=True)
        text = text[: -len(last)] + f'{exception_type.__qualname__}: {styled}\n'
    stream.write(text)
    stream.flush()


_previous_exception_hook = sys.excepthook
if sys.excepthook is not _print_uncaught:
    sys.excepthook = _print_uncaught


def _release_frames(error: BaseException | None) -> str:
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
