"""Tests for actionable errors raised across public core workflows."""

from __future__ import annotations

import pytest

from xnano.core.exceptions import (
    ExtraNotInstalledError,
    FieldValidationError,
    HookError,
    TerminalNotActiveError,
)


def test_runtime_errors_preserve_actionable_context() -> None:
    cause = LookupError("missing service")
    hook_error = HookError("refresh", cause)
    assert hook_error.hook_name == "refresh"
    assert hook_error.cause is cause
    assert hook_error.__cause__ is cause
    assert "refresh" in str(hook_error)

    class ValidationFailure:
        def errors(self) -> list[dict[str, str]]:
            return [{"message": "must be positive"}]

    assert "must be positive" in str(
        FieldValidationError("retries", ValidationFailure())  # type: ignore
    )
    assert "active live runtime" in str(TerminalNotActiveError())
    assert "Pillow" in str(ExtraNotInstalledError("images"))
    assert "standard library" in str(ExtraNotInstalledError("requests"))
    with pytest.raises(ValueError, match="Unknown extra"):
        ExtraNotInstalledError("audio")
