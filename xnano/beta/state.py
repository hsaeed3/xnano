"""xnano.beta.state

---

Lightweight dynamic state container for simple apps (prefer dataclasses
or models when you need a fixed schema).
"""

from __future__ import annotations

from typing import Any, get_type_hints

from xnano.beta.utils.validation import validate_type


class State:
    """Store application state with optional annotation validation.

    Public attributes are supplied at initialization or assigned later.
    Subclass annotations validate assignments; use a dataclass when the
    state has a fixed schema and does not need dynamic attributes.

    Attributes:
        _state_annotations: Resolved annotations used for validation.
        **values: User-defined public state attributes.

    Example:
        >>> state = State(name="John", age=30)
        >>> state.name
        'John'
        >>> state.address = "123 Main St"
        >>> state.address
        '123 Main St'
    """

    _state_annotations: dict[str, Any] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        try:
            cls._state_annotations = get_type_hints(cls)
        except Exception:
            cls._state_annotations = dict(getattr(cls, "__annotations__", {}))

    def __init__(self, **values: Any) -> None:
        for name, value in values.items():
            self.__setattr__(name, value)

    def _state_get_annotation(self, name: str) -> Any | None:
        """Return the declared type annotation for ``name``, if any.

        Returns:
            The resolved annotation for ``name``, or ``None`` when the
            attribute is not declared on the class.
        """
        return type(self)._state_annotations.get(name)

    def _state_validate_value(self, name: str, value: Any) -> Any:
        """Validate ``value`` when ``name`` has a declared annotation.

        Args:
            name: Attribute name being assigned.
            value: Proposed attribute value.

        Returns:
            The validated value.

        Raises:
            ValidationError: If ``value`` does not satisfy the annotation.
        """
        annotation = self._state_get_annotation(name)
        if annotation is None:
            return value
        return validate_type(value, annotation)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        validated = self._state_validate_value(name, value)
        object.__setattr__(self, name, validated)

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(
            f"{type(self).__name__!r} object has no attribute {name!r}"
        )

    def __repr__(self) -> str:
        items = ", ".join(
            f"{name}={value!r}"
            for name, value in self.__dict__.items()
            if not name.startswith("_")
        )
        return f"{type(self).__name__}({items})"


__all__ = ("State",)
