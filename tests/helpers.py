"""tests.helpers"""

from __future__ import annotations

from typing import Any, cast

from xnano.beta.fields import Field, UNSET


def invalid_field(default: Any) -> Any:
    """Mark an intentionally invalid ``Field(default=...)`` for negative tests."""
    return cast(Any, Field(default=default))  # type: ignore


def assign_attr(instance: object, name: str, value: object) -> None:
    """Assign an attribute while bypassing static type checks in tests."""
    object.__setattr__(instance, name, value)
