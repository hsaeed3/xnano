"""Tests for xnano exception types."""

from __future__ import annotations

from pydantic_core import ValidationError

from xnano.beta.exceptions import FieldValidationError, TerminalNotActiveError


def test_field_validation_error_message() -> None:
    try:
        raise ValidationError.from_exception_data(
            "test",
            [{"type": "int_type", "loc": ("x",), "input": "nope"}],
        )
    except ValidationError as exc:
        error = FieldValidationError("count", exc)
    assert "count" in str(error)
    assert "ValidationError" in str(error)


def test_terminal_not_active_error_message() -> None:
    error = TerminalNotActiveError()
    assert "not active" in str(error).lower()
