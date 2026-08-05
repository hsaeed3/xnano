"""xnano.utils.deprecation

---

Shared deprecation helpers for APIs. Currently provides the
``color`` -> ``foreground`` field-parameter migration used by any
dataclass or callable that pairs a foreground color with a
``background``.
"""

from __future__ import annotations

import functools
import sys
import warnings
from typing import Any, Callable, TypeVar

if sys.version_info >= (3, 13):
    _deprecated = warnings.deprecated
else:
    from typing_extensions import deprecated as _deprecated

_ClassT = TypeVar("_ClassT", bound=type)
_CallableT = TypeVar("_CallableT", bound=Callable[..., Any])

_COLOR_MESSAGE = (
    "The 'color' parameter is deprecated; use 'foreground' instead."
)
_ALIAS_UNSET = object()


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


def resolve_renamed_alias(
    new_value: Any,
    old_value: Any,
    *,
    old: str,
    new: str,
    unset: Any = None,
    stacklevel: int = 3,
) -> Any:
    """Return ``new_value``, honoring a deprecated ``old_value`` alias.

    The generic form of `resolve_color_alias` for any renamed keyword.
    The new name wins when both are supplied.

    Args:
        new_value: Canonical argument.
        old_value: Deprecated alias argument.
        old: Deprecated parameter name, for the message.
        new: Replacement parameter name, for the message.
        unset: Sentinel meaning "argument not supplied".
        stacklevel: Frames to skip so the warning points at caller code.

    Returns:
        The resolved value (may be ``unset``).
    """
    if old_value is not unset:
        warnings.warn(
            f"The '{old}' parameter is deprecated; use '{new}' instead.",
            DeprecationWarning,
            stacklevel=stacklevel,
        )
        if new_value is unset:
            return old_value
    return new_value


def warn_renamed_attribute(
    old: str, new: str
) -> Callable[[_CallableT], _CallableT]:
    """Decorate a renamed attribute/property getter as deprecated.

    Applies PEP 702 ``@deprecated``, so type checkers render callers of the
    old name with a strikethrough and a ``DeprecationWarning`` is emitted at
    runtime when it is used. Apply below ``@property`` on the getter.

    Args:
        old: Fully qualified deprecated name (e.g. ``"Context.keyboard"``).
        new: Fully qualified replacement name.

    Returns:
        The ``@deprecated`` decorator carrying the rename message.
    """
    # Message is dynamic, not a LiteralString; deprecated() accepts any str.
    message = f"'{old}' is deprecated; use '{new}' instead."
    return _deprecated(message)  # ty: ignore[invalid-argument-type]


def renamed_alias_dataclass(
    old: str, new: str
) -> Callable[[_ClassT], _ClassT]:
    """Add a deprecated ``old`` keyword alias for a dataclass ``new`` field.

    Wraps ``__init__`` to accept ``old`` (deprecated, ``new`` wins when
    both are given) and installs an ``old`` property mapped to ``new`` so
    existing attribute reads keep working.

    Args:
        old: Deprecated field name.
        new: Replacement field name, which the class must declare.

    Returns:
        A decorator augmenting the dataclass in place.
    """

    def decorate(cls: _ClassT) -> _ClassT:
        original_init = cls.__init__

        @functools.wraps(original_init)
        def __init__(self: Any, *args: Any, **kwargs: Any) -> None:
            if old in kwargs:
                warnings.warn(
                    f"The '{old}' parameter is deprecated; "
                    f"use '{new}' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                kwargs.setdefault(new, kwargs.pop(old))
                kwargs.pop(old, None)
            original_init(self, *args, **kwargs)

        cls.__init__ = __init__  # ty: ignore[invalid-assignment]
        setattr(
            cls,
            old,
            property(
                lambda self: getattr(self, new),
                lambda self, value: setattr(self, new, value),
            ),
        )
        return cls

    return decorate


def renamed_alias_property(
    old: str, new: str
) -> Callable[[_ClassT], _ClassT]:
    """Install a deprecated alias property on a dataclass.

    Use with a dataclass ``InitVar`` when the alias is on a hot constructor;
    this keeps the generated initializer instead of wrapping it with
    ``*args``/``**kwargs``.
    """

    def decorate(cls: _ClassT) -> _ClassT:
        setattr(
            cls,
            old,
            property(
                lambda self: getattr(self, new),
                lambda self, value: setattr(self, new, value),
            ),
        )
        return cls

    return decorate


def resolve_init_alias(
    instance: Any,
    value: Any,
    *,
    old: str,
    new: str,
) -> None:
    """Apply a deprecated dataclass ``InitVar`` alias in ``__post_init__``."""
    if value is _ALIAS_UNSET:
        return
    warnings.warn(
        f"The '{old}' parameter is deprecated; use '{new}' instead.",
        DeprecationWarning,
        stacklevel=3,
    )
    if getattr(instance, new) is None:
        object.__setattr__(instance, new, value)


color_alias_dataclass = renamed_alias_dataclass("color", "foreground")
"""Deprecated ``color`` alias for a dataclass ``foreground`` field."""

align_alias_dataclass = renamed_alias_dataclass("align", "horizontal_align")
"""Deprecated ``align`` alias for a ``horizontal_align`` field."""


__all__ = (
    "align_alias_dataclass",
    "color_alias_dataclass",
    "renamed_alias_dataclass",
    "renamed_alias_property",
    "resolve_init_alias",
    "resolve_renamed_alias",
    "resolve_color_alias",
    "warn_color_alias",
    "warn_renamed_attribute",
)
