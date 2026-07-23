"""xnano.state

---

Lightweight dynamic state container for simple apps (prefer dataclasses
or models when you need a fixed schema).
"""

from __future__ import annotations

from typing import Any, get_type_hints

from typing_extensions import deprecated

from xnano._validation import validate_type


@deprecated(
    "'xnano.State' is deprecated and will be removed in v1.2; use "
    "'xnano.beta.State' instead.",
    category=DeprecationWarning,
    stacklevel=2,
)
class State:
    """Convenience runtime context wrapper that allows for setting
    state variables within using dot notation with no
    additional boilerplate.

    (In practice, you probably would not want to think about touching
    this, and opt for ``dataclasses.dataclass`` or ``pydantic.BaseModel``
    instead.)

    Example:

        **Initialization:**

        >>> # state is now aware that it has name & age, which will be type
        >>> # hinted correctly within the ide when accessing attributes
        >>> my_state = State(name="John", age=30)
        >>> my_state.name

        **Attribute Access:**

        >>> # if an attribute is not set, it can be created at any point
        >>> my_state.address = "123 Main St, Anytown, USA"

        **Type Validation:**

        >>> # any attributes set by base classing this state class will
        >>> # be type validated through ``xnano``'s native integration
        >>> # with ``pydantic-core``
        >>> class MyState(State):
        ...     name: str

        >>> # would raise a ``pydantic.ValidationError``
        >>> my_state = MyState(name=123)
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
