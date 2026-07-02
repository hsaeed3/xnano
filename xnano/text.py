"""xnano.text"""

from __future__ import annotations

import re
from typing import Sequence

from xnano import _core
from xnano._convert import (
    ColorLike,
    Content,
    ModifierLike,
    _resolve_color,
    _resolve_modifier,
    as_text,
)
from xnano.color import Color
from xnano.layout import Alignment, _core_alignment
from xnano.style import Modifier, Style


class Span:
    """A styled string that does not contain any newlines.

    ``Span`` is the smallest unit of styled text. It pairs a plain string
    with a :class:`Style`.

    Example::

        span = Span("Hello", foreground="red", modifiers="bold")
    """

    __slots__ = ("_inner",)
    _inner: _core.Span

    def __init__(
        self,
        content: str = "",
        *,
        style: Style | None = None,
        foreground: ColorLike | None = None,
        background: ColorLike | None = None,
        modifiers: ModifierLike | None = None,
    ) -> None:
        """Create a styled text span.

        If *style* is provided, it is applied directly. Otherwise, a style
        is constructed on the fly from the provided *foreground*, *background*,
        and *modifiers* arguments.

        Args:
            content: The text content of the span (should not contain newlines).
            style: An optional explicit ``Style`` instance.
            foreground: Text color (accepts a Color, color name, or hex string).
            background: Background color (same types as foreground).
            modifiers: Text modifiers (e.g. "bold", ["bold", "italic"]).
        """
        if style is not None:
            inner = _core.Span.styled(content, style._to_core())
        elif (
            foreground is not None
            or background is not None
            or modifiers is not None
        ):
            inner = _core.styled_span(
                content,
                fg=_resolve_color(foreground)
                if foreground is not None
                else None,
                bg=_resolve_color(background)
                if background is not None
                else None,
                modifiers=_resolve_modifier(modifiers)
                if modifiers is not None
                else None,
            )
        else:
            inner = _core.Span.raw(content)

        object.__setattr__(self, "_inner", inner)

    @classmethod
    def _from_core(cls, inner: _core.Span) -> Span:
        """Construct a Span from the native ``_core.Span`` object."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.Span:
        """Return the wrapped native ``_core.Span`` object."""
        return self._inner

    def style(self, style: Style) -> Span:
        """Return a new Span with the style replaced."""
        return Span._from_core(self._inner.style(style._to_core()))

    def patch_style(self, style: Style) -> Span:
        """Return a new Span with properties of the given style overlayed."""
        return Span._from_core(self._inner.patch_style(style._to_core()))

    def reset_style(self) -> Span:
        """Return a new Span with all styles reset to defaults."""
        return Span._from_core(self._inner.reset_style())

    def width(self) -> int:
        """Return the visual width of the span content in cells."""
        return self._inner.width()

    @property
    def text(self) -> str:
        """The plain text content of this span."""
        return self._inner.text

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Span is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Span is immutable")


class Line:
    """A line of text made of multiple styled spans."""

    __slots__ = ("_inner",)
    _inner: _core.Line

    def __init__(
        self,
        content: str | Sequence[Span] | None = None,
        *,
        style: Style | None = None,
        alignment: Alignment | None = None,
    ) -> None:
        """Create a new line of styled spans.

        Args:
            content: The content of the line. Can be a plain string, a list/sequence
                of ``Span`` objects, or ``None``.
            style: An optional style to apply to the entire line.
            alignment: Optional horizontal alignment for the line.
        """
        if isinstance(content, str):
            inner = _core.Line.raw(content)
        elif isinstance(content, Sequence):
            inner = _core.Line.from_spans(
                [span._to_core() for span in content]
            )
        elif content is None:
            inner = _core.Line.raw("")
        else:
            raise TypeError(
                f"expected str, list/Sequence of Span, or None, got {type(content)!r}"
            )

        if style is not None:
            inner = inner.style(style._to_core())
        if alignment is not None:
            inner = inner.alignment(_core_alignment(alignment))

        object.__setattr__(self, "_inner", inner)

    @classmethod
    def _from_core(cls, inner: _core.Line) -> Line:
        """Construct a Line from the native ``_core.Line`` object."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.Line:
        """Return the wrapped native ``_core.Line`` object."""
        return self._inner

    def style(self, style: Style) -> Line:
        """Return a new Line with the style replaced."""
        return Line._from_core(self._inner.style(style._to_core()))

    def patch_style(self, style: Style) -> Line:
        """Return a new Line overlayed with properties of the given style."""
        return Line._from_core(self._inner.patch_style(style._to_core()))

    def reset_style(self) -> Line:
        """Return a new Line with all styles reset to defaults."""
        return Line._from_core(self._inner.reset_style())

    def width(self) -> int:
        """Return the visual width of the line in cells."""
        return self._inner.width()

    def left_aligned(self) -> Line:
        """Return a new Line aligned to the left."""
        return Line._from_core(self._inner.left_aligned())

    def centered(self) -> Line:
        """Return a new Line aligned to the center."""
        return Line._from_core(self._inner.centered())

    def right_aligned(self) -> Line:
        """Return a new Line aligned to the right."""
        return Line._from_core(self._inner.right_aligned())

    def spans(self, spans: Sequence[Span]) -> Line:
        """Return a new Line with the spans replaced."""
        return Line._from_core(
            self._inner.spans([span._to_core() for span in spans])
        )

    @property
    def text(self) -> str:
        """Return the plain text representation of this line."""
        # Parse text representation out of repr
        matches = re.findall(
            r'(?:Span::from|Span::styled|from)\("([^"]*)"', repr(self._inner)
        )
        return "".join(matches)

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Line is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Line is immutable")


class Text:
    """Multi-line styled text content."""

    __slots__ = ("_inner",)
    _inner: _core.Text

    def __init__(
        self,
        content: str | Sequence[Line] | None = None,
        *,
        style: Style | None = None,
        alignment: Alignment | None = None,
    ) -> None:
        """Create multi-line styled text.

        Args:
            content: The text content. Can be a plain string, a list/sequence
                of ``Line`` objects, or ``None``.
            style: An optional style to apply to all lines.
            alignment: Optional alignment for the text block.
        """
        if isinstance(content, str):
            inner = _core.Text.raw(content)
        elif isinstance(content, Sequence):
            inner = _core.Text.from_lines([l._to_core() for l in content])
        elif content is None:
            inner = _core.Text.raw("")
        else:
            raise TypeError(
                f"expected str, list/Sequence of Line, or None, got {type(content)!r}"
            )

        if style is not None:
            inner = inner.style(style._to_core())
        if alignment is not None:
            inner = inner.alignment(_core_alignment(alignment))

        object.__setattr__(self, "_inner", inner)

    @property
    def text(self) -> str:
        """Return the plain text content of this ``Text``."""
        return "\n".join(self.lines())

    @classmethod
    def _from_core(cls, inner: _core.Text) -> Text:
        """Construct a Text object from the native ``_core.Text``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.Text:
        """Return the wrapped native ``_core.Text`` object."""
        return self._inner

    def style(self, style: Style) -> Text:
        """Return a new Text with the style replaced."""
        return Text._from_core(self._inner.style(style._to_core()))

    def patch_style(self, style: Style) -> Text:
        """Return a new Text overlayed with properties of the given style."""
        return Text._from_core(self._inner.patch_style(style._to_core()))

    def reset_style(self) -> Text:
        """Return a new Text with all styles reset to defaults."""
        return Text._from_core(self._inner.reset_style())

    def width(self) -> int:
        """Return the visual width of the widest line in cells."""
        return self._inner.width()

    def height(self) -> int:
        """Return the number of lines of text."""
        return self._inner.height()

    def lines(self) -> list[str]:
        """Return the text content as a list of raw strings."""
        parts = repr(self._inner).split("Line::")[1:]
        result = []
        for p in parts:
            matches = re.findall(
                r'(?:Span::from|Span::styled|from)\("([^"]*)"', p
            )
            result.append("".join(matches))
        if not result and repr(self._inner) == "Text::from(Line::default())":
            return [""]
        return result

    def left_aligned(self) -> Text:
        """Return a new Text aligned to the left."""
        return Text._from_core(self._inner.left_aligned())

    def centered(self) -> Text:
        """Return a new Text aligned to the center."""
        return Text._from_core(self._inner.centered())

    def right_aligned(self) -> Text:
        """Return a new Text aligned to the right."""
        return Text._from_core(self._inner.right_aligned())

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Text is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Text is immutable")


__all__ = ("Line", "Span", "Text")
