"""xnano.core.exceptions

---

Framework exceptions for session exit, hook failures, field validation,
inactive terminals, and missing optional extras.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic_core import ValidationError


class Exit(BaseException):
    """Exception that can be raised within an `@on_<event>` hook to request
    the exit of the current live terminal session.
    """


class HookError(RuntimeError):
    """Raised when an ``@on_*`` hook fails in a way that needs a clear surface.

    The default dispatch policy logs the original exception and re-raises it
    unchanged so callers see the real traceback.  ``HookError`` is available
    for libraries that want to wrap hook failures explicitly.
    """

    def __init__(self, hook_name: str, cause: BaseException) -> None:
        self.hook_name = hook_name
        self.cause = cause
        super().__init__(f"Hook {hook_name!r} raised: {cause!r}")
        self.__cause__ = cause


class FieldValidationError(ValueError):
    """Exception raised when a ``pydantic-core`` validation error occurs during
    the strict validation of a grid field attribute(s).
    """

    def __init__(
        self,
        field_name: str,
        validation_error: ValidationError,
    ) -> None:
        message = (
            "``pydantic-core.ValidationError`` occured during the initial or "
            f"refresh validation of the ``{field_name}`` field.\n"
            f"Error details: {validation_error.errors()}"
        )
        super().__init__(message)


class TerminalNotActiveError(RuntimeError):
    """Exception raised when a live session-based operation is attempted on a
    terminal instance that is is not within the live session context.
    """

    def __init__(self) -> None:
        super().__init__(
            "This terminal instance is not active. Please use the ``with Terminal(...) as terminal:`` "
            "context manager to set this terminal as the live instance."
        )


class ExtraNotInstalledError(RuntimeError):
    """Exception called internally by the library when a component requiring additional
    dependencies has not been satisfied.
    """

    def __init__(self, extra: str) -> None:
        if extra == "web":
            message = (
                "Using the `Web` interface and associated components requires the "
                "`starlette` and `uvicorn` packages. Install them with: \n"
                "`pip install 'xnano[web]'`\n"
                "or\n"
                "`pip install starlette uvicorn`"
            )
        else:
            raise ValueError(f"Unknown extra: {extra}")

        super().__init__(message)


__all__ = (
    "Exit",
    "HookError",
    "FieldValidationError",
    "TerminalNotActiveError",
    "ExtraNotInstalledError",
)
