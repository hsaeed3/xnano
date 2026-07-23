"""xnano.beta.core.exceptions

---

Errors raised by beta runtimes, hooks, fields, and optional components.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic_core import ValidationError as PydanticValidationError


class Exit(BaseException):
    """Request that the active runtime stop."""


class HookError(RuntimeError):
    """Report a hook failure while preserving its original cause."""

    def __init__(self, hook_name: str, cause: BaseException) -> None:
        self.hook_name = hook_name
        self.cause = cause
        super().__init__(f"Hook {hook_name!r} raised: {cause!r}")
        self.__cause__ = cause


class FieldValidationError(ValueError):
    """Report strict validation failure for a grid field."""

    def __init__(
        self,
        field_name: str,
        validation_error: "PydanticValidationError",
    ) -> None:
        super().__init__(
            f"Field {field_name!r} failed validation: "
            f"{validation_error.errors()}"
        )


class TerminalNotActiveError(RuntimeError):
    """Report an operation that requires an active live runtime."""

    def __init__(self) -> None:
        super().__init__("This operation requires an active live runtime.")


class ExtraNotInstalledError(RuntimeError):
    """Report a missing optional dependency."""

    def __init__(self, extra: str) -> None:
        if extra == "images":
            message = (
                "Image rendering requires Pillow. Install `xnano[images]` "
                "or `pillow`."
            )
        elif extra == "requests":
            message = "HTTP request hooks use the standard library."
        else:
            raise ValueError(f"Unknown extra: {extra}")
        super().__init__(message)


ValidationError = FieldValidationError
XnanoError = RuntimeError

__all__ = (
    "Exit",
    "ExtraNotInstalledError",
    "FieldValidationError",
    "HookError",
    "TerminalNotActiveError",
    "ValidationError",
    "XnanoError",
)
