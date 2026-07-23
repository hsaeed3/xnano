"""Tests for xnano exception types.

These exercise the real code paths that raise each exception, not just the
exception's own ``__str__`` — a manually-constructed exception's message
containing the substrings its own ``__init__`` hardcodes proves nothing.
"""

from __future__ import annotations

import pytest

from xnano.core.exceptions import FieldValidationError, TerminalNotActiveError
from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.terminal import Terminal


class _Counter(BaseGrid):
    # ``strict=True`` on a state field opts assignments (not just
    # construction) into validation — the default field-level ``strict``
    # is False, since re-validating every attribute set is not free.
    count: int = Field(default=0, state=True, strict=True)


def test_field_validation_error_raised_on_bad_assignment() -> None:
    grid = _Counter()
    with pytest.raises(FieldValidationError):
        grid.count = "not an int"  # ty: ignore[invalid-assignment]


def test_field_validation_error_raised_on_bad_init() -> None:
    with pytest.raises(FieldValidationError):
        _Counter(count="also not an int")  # ty: ignore[invalid-argument-type]


def test_terminal_not_active_error_raised_outside_session() -> None:
    terminal = Terminal()
    with pytest.raises(TerminalNotActiveError):
        _ = terminal.session


def test_terminal_session_available_inside_session() -> None:
    with Terminal.offscreen(cols=10, rows=5) as terminal:
        assert terminal.session is not None
