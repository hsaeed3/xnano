"""xnano._convert"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Sequence, TypeAlias, Union, cast

from xnano import _core

if TYPE_CHECKING:
    from xnano.color import Color, ColorName
    from xnano.style import Modifier, ModifierName
    from xnano.text import Line, Span, Text


Content: TypeAlias = Union[str, "Span", "Line", "Text"]
"""Anything that can be used as text content in a widget.

Accepts plain strings, styled ``Span`` objects, ``Line`` objects, or
multi-line ``Text`` objects. All widget APIs that display text accept
this type.
"""

ColorLike: TypeAlias = Union["Color", "ColorName", str]
"""Anything that can be resolved to a ``Color``.

Accepts a ``Color`` instance, a named color string (e.g. ``"red"``),
or a hex color string (e.g. ``"#ff0000"``).
"""

ModifierLike: TypeAlias = Union[
    "Modifier", "ModifierName", Sequence["ModifierName"]
]
"""Anything that can be resolved to a ``Modifier``.

Accepts a ``Modifier`` instance, a single modifier name string
(e.g. ``"bold"``), or a sequence of modifier names
(e.g. ``["bold", "italic"]``).
"""


def _resolve_color(value: ColorLike) -> _core.Color:
    """Resolve a color-like value to a native ``core.Color``.

    Args:
        value: A ``Color`` instance, a named color string, or a hex
            color string.

    Returns:
        The resolved native color.

    Raises:
        TypeError: If *value* is not a recognized color-like type.
        ValueError: If *value* is a string that cannot be parsed as a
            color name or hex code.
    """
    from xnano.color import COLORS_BY_NAME, Color

    if isinstance(value, Color):
        return value._to_core()
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in COLORS_BY_NAME:
            c = Color.from_name(cast("ColorName", lowered))
            return c._to_core()
        # Try hex / pydantic color parsing
        c = Color.from_hex(value)
        return c._to_core()
    raise TypeError(
        f"expected Color, color name, or hex string, got {type(value)!r}"
    )


def _resolve_modifier(value: ModifierLike) -> _core.Modifier:
    """Resolve a modifier-like value to a native ``core.Modifier``.

    Args:
        value: A ``Modifier`` instance, a single modifier name, or a
            sequence of modifier names.

    Returns:
        The resolved native modifier.
    """
    from xnano.style import Modifier, _core_modifier

    if isinstance(value, Modifier):
        return value._to_core()
    if isinstance(value, str):
        return _core_modifier(frozenset([cast("ModifierName", value)]))
    if isinstance(value, Sequence):
        return _core_modifier(frozenset(cast(Sequence["ModifierName"], value)))
    raise TypeError(
        f"expected Modifier, modifier name, or sequence of names, "
        f"got {type(value)!r}"
    )


def as_span(content: Content) -> _core.Span:
    """Convert any ``Content`` value to a native ``core.Span``."""
    if isinstance(content, str):
        return _core.Span.raw(content)
    from xnano.text import Line, Span, Text

    if isinstance(content, Span):
        return content._to_core()
    if isinstance(content, Line):
        return _core.Span.raw(content.text)
    if isinstance(content, Text):
        lines = content.lines()
        return _core.Span.raw("\n".join(lines) if lines else "")
    raise TypeError(
        f"expected str, Span, Line, or Text, got {type(content)!r}"
    )


def as_line(content: Content) -> _core.Line:
    """Convert any ``Content`` value to a native ``core.Line``."""
    if isinstance(content, str):
        return _core.Line.raw(content)
    from xnano.text import Line, Span, Text

    if isinstance(content, Span):
        return _core.Line.from_spans([content._to_core()])
    if isinstance(content, Line):
        return content._to_core()
    if isinstance(content, Text):
        return _core.Line.raw("\n".join(content.lines()))
    raise TypeError(
        f"expected str, Span, Line, or Text, got {type(content)!r}"
    )


def as_text(content: Content) -> _core.Text:
    """Convert any ``Content`` value to a native ``core.Text``."""
    if isinstance(content, str):
        return _core.Text.raw(content)
    from xnano.text import Line, Span, Text

    if isinstance(content, Span):
        return _core.Text.from_lines(
            [_core.Line.from_spans([content._to_core()])]
        )
    if isinstance(content, Line):
        return _core.Text.from_lines([content._to_core()])
    if isinstance(content, Text):
        return content._to_core()
    raise TypeError(
        f"expected str, Span, Line, or Text, got {type(content)!r}"
    )


def as_lines(content: Content | list[Content]) -> list[_core.Line]:
    """Convert content to a list of native ``core.Line`` objects."""
    if isinstance(content, list):
        return [as_line(item) for item in content]
    return [as_line(content)]


def unwrap(value: Any) -> Any:
    """Extract the native core object from any xnano wrapper.

    Uses the ``_to_core()`` protocol. If the value has a ``_to_core``
    method, it is called and the result returned. Otherwise the value
    is returned unchanged (assumed to already be a native type).
    """
    to_core = getattr(value, "_to_core", None)
    if callable(to_core):
        return to_core()
    # Fallback: check for _inner attribute (direct core wrapper)
    inner = getattr(value, "_inner", None)
    if inner is not None:
        return inner
    return value
