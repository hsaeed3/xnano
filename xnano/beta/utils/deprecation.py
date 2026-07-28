"""xnano.beta.utils.deprecation

---

Shared deprecation helpers for beta APIs. Currently provides the
``color`` -> ``foreground`` field-parameter migration used by any
dataclass or callable that pairs a foreground color with a
``background``.
"""

from __future__ import annotations

import functools
import warnings
from typing import Any, Callable, TypeVar

_ClassT = TypeVar("_ClassT", bound=type)
_CallableT = TypeVar("_CallableT", bound=Callable[..., Any])

_COLOR_MESSAGE = (
    "The 'color' parameter is deprecated; use 'foreground' instead."
)


def warn_color_alias(stacklevel: int = 3) -> None:
    """Emit the standard ``color`` deprecation warning.

    Args:
        stacklevel: Frames to skip so the warning points at caller code.
    """
    warnings.warn(_COLOR_MESSAGE, DeprecationWarning, stacklevel=stacklevel)


def resolve_color_alias(
    foreground: Any,
    color: Any,
    *,
    unset: Any = None,
    stacklevel: int = 3,
) -> Any:
    """Return the foreground value, honoring the deprecated ``color`` alias.

    ``foreground`` wins when both are supplied. Passing ``color`` emits a
    ``DeprecationWarning``.

    Args:
        foreground: Canonical foreground argument.
        color: Deprecated alias argument.
        unset: Sentinel meaning "argument not supplied".
        stacklevel: Frames to skip so the warning points at caller code.

    Returns:
        The resolved foreground value (may be ``unset``).
    """
    if color is not unset:
        warn_color_alias(stacklevel=stacklevel)
        if foreground is unset:
            return color
    return foreground


def color_alias_dataclass(cls: _ClassT) -> _ClassT:
    """Add a deprecated ``color`` alias for a dataclass ``foreground`` field.

    The class must already declare a ``foreground`` field. The decorator
    wraps ``__init__`` to accept a ``color`` keyword (deprecated,
    ``foreground`` wins when both are given) and installs a ``color``
    property mapped to ``foreground`` so existing ``self.color`` code and
    external reads keep working.

    Args:
        cls: The dataclass to augment.

    Returns:
        The same class, augmented in place.
    """
    original_init = cls.__init__

    @functools.wraps(original_init)
    def __init__(self: Any, *args: Any, **kwargs: Any) -> None:
        if "color" in kwargs:
            warn_color_alias(stacklevel=2)
            color = kwargs.pop("color")
            kwargs.setdefault("foreground", color)
        original_init(self, *args, **kwargs)

    cls.__init__ = __init__  # ty: ignore[invalid-assignment]

    def _get_color(self: Any) -> Any:
        return self.foreground

    def _set_color(self: Any, value: Any) -> None:
        self.foreground = value

    cls.color = property(  # ty: ignore[unresolved-attribute]
        _get_color, _set_color
    )
    return cls


__all__ = (
    "color_alias_dataclass",
    "resolve_color_alias",
    "warn_color_alias",
)
