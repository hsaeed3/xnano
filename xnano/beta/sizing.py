"""xnano.beta.sizing

---

The unified sizing vocabulary shared by every box in ``xnano`` — the terminal
viewport, grid fields, and standalone renderables.

A ``Sizing`` expresses one axis's *intent* rather than a resolved length:

    - ``cells``     — a fixed number of terminal cells (``Constraint::Length``)
    - ``percent``   — a percentage of the available axis (``Constraint::Percentage``)
    - ``ratio``     — a fraction ``numerator/denominator`` of the axis (``Constraint::Ratio``)
    - ``fraction``  — a relative fill weight (``Constraint::Fill``)
    - ``fit``       — the measured intrinsic size of the content

Every point on this spectrum resolves through the same two operations —
measure the content, then place it — so content-driven leaves and
constraint-driven containers compose with one model.
"""

from __future__ import annotations

import dataclasses
from typing import Literal, TypeAlias, Union

from xnano.beta.types import _FLEX_CLASS_WEIGHTS


SizingKind: TypeAlias = Literal[
    "cells",
    "percent",
    "ratio",
    "fraction",
    "fit",
]
"""The kind of sizing intent expressed by a ``Sizing``.

Values:
    ``"cells"``: A fixed number of terminal cells.
    ``"percent"``: A percentage (0-100) of the available axis length.
    ``"ratio"``: A ``numerator / denominator`` fraction of the axis length.
    ``"fraction"``: A relative fill weight distributed across leftover space.
    ``"fit"``: The measured intrinsic size of the content.
"""


@dataclasses.dataclass(frozen=True, slots=True)
class Sizing:
    """A single-axis sizing intent.

    ``Sizing`` is the unified currency of layout: the same value can describe a
    grid field's width, a terminal's height, or a renderable's extent. Use the
    constructor helpers (:meth:`cells`, :meth:`percent`, :meth:`ratio`,
    :meth:`fraction`, :meth:`fit`) or :meth:`parse` to build one.

    Attributes:
        kind: The kind of sizing intent.
        value: The primary magnitude — cell count, percentage, ratio
            numerator, or fill weight depending on ``kind``.
        denominator: The ratio denominator (only meaningful for ``"ratio"``).
        minimum: An optional lower clamp in cells applied after resolution.
        maximum: An optional upper clamp in cells applied after resolution.
    """

    kind: SizingKind
    """The kind of sizing intent."""
    value: int = 0
    """The primary magnitude for this sizing intent."""
    denominator: int = 1
    """The ratio denominator (only meaningful for ``"ratio"``)."""
    minimum: int | None = None
    """An optional lower clamp in cells applied after resolution."""
    maximum: int | None = None
    """An optional upper clamp in cells applied after resolution."""

    @classmethod
    def cells(cls, count: int) -> Sizing:
        """Return a fixed-length sizing of ``count`` terminal cells.

        Args:
            count: The number of cells to occupy.

        Returns:
            A ``"cells"`` ``Sizing``.
        """
        return cls(kind="cells", value=max(0, int(count)))

    @classmethod
    def percent(cls, percentage: float) -> Sizing:
        """Return a percentage sizing of the available axis length.

        Args:
            percentage: The percentage of the axis to occupy. Values in the
                ``0..=1`` range are treated as fractions (``0.5`` → 50%);
                larger values are treated as literal percentages.

        Returns:
            A ``"percent"`` ``Sizing``.
        """
        pct = percentage * 100 if 0 <= percentage <= 1 else percentage
        return cls(kind="percent", value=max(0, min(100, int(round(pct)))))

    @classmethod
    def ratio(cls, numerator: int, denominator: int) -> Sizing:
        """Return a ratio sizing of ``numerator / denominator`` of the axis.

        Args:
            numerator: The ratio numerator.
            denominator: The ratio denominator.

        Returns:
            A ``"ratio"`` ``Sizing``.
        """
        return cls(
            kind="ratio",
            value=max(0, int(numerator)),
            denominator=max(1, int(denominator)),
        )

    @classmethod
    def fraction(cls, weight: int = 1) -> Sizing:
        """Return a relative fill-weight sizing.

        Args:
            weight: The fill weight. Higher weights claim proportionally more
                of the leftover space.

        Returns:
            A ``"fraction"`` ``Sizing``.
        """
        return cls(kind="fraction", value=max(0, int(weight)))

    @classmethod
    def fit(
        cls,
        *,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> Sizing:
        """Return a content-measured sizing.

        Args:
            minimum: An optional lower clamp in cells.
            maximum: An optional upper clamp in cells.

        Returns:
            A ``"fit"`` ``Sizing``.
        """
        return cls(kind="fit", minimum=minimum, maximum=maximum)

    def with_bounds(
        self,
        *,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> Sizing:
        """Return a copy of this sizing with clamps applied.

        Args:
            minimum: An optional lower clamp in cells.
            maximum: An optional upper clamp in cells.

        Returns:
            A new ``Sizing`` carrying the given bounds.
        """
        return dataclasses.replace(self, minimum=minimum, maximum=maximum)

    @property
    def is_fill(self) -> bool:
        """Whether this sizing grows to fill the available axis."""
        return self.kind == "fraction"

    @property
    def is_fit(self) -> bool:
        """Whether this sizing measures its content."""
        return self.kind == "fit"

    def resolve(self, available: int, content: int | None = None) -> int:
        """Resolve this sizing to a concrete cell length.

        Args:
            available: The available axis length to resolve against.
            content: The measured content length, used by ``"fit"`` sizings.

        Returns:
            The resolved length in cells, after applying any clamps.
        """
        if self.kind == "cells":
            length = self.value
        elif self.kind == "percent":
            length = available * self.value // 100
        elif self.kind == "ratio":
            length = available * self.value // self.denominator
        elif self.kind == "fit":
            length = content if content is not None else 0
        else:  # fraction — a lone fill claims all available space
            length = available
        if self.minimum is not None:
            length = max(length, self.minimum)
        if self.maximum is not None:
            length = min(length, self.maximum)
        return max(0, length)

    @classmethod
    def parse(cls, value: SizingLike | None) -> Sizing | None:
        """Normalize any accepted sizing form into a ``Sizing``.

        Accepted forms:
            - ``None`` → ``None``
            - ``Sizing`` → itself
            - ``int`` → :meth:`cells`
            - ``float`` in ``0..=1`` → :meth:`percent`, otherwise :meth:`cells`
            - ``"50%"`` → :meth:`percent`
            - ``"2fr"`` → :meth:`fraction`
            - ``"fit"`` / ``"auto"`` / ``"content"`` → :meth:`fit`
            - ``"fill"`` / ``"grow"`` / Tailwind flex class → :meth:`fraction`
            - a decimal string → :meth:`cells`

        Args:
            value: The value to normalize.

        Returns:
            A ``Sizing`` instance, or ``None`` when ``value`` is ``None``.

        Raises:
            ValueError: If a string value is not a recognized sizing form.
            TypeError: If ``value`` is an unsupported type.
        """
        if value is None:
            return None
        if isinstance(value, Sizing):
            return value
        if isinstance(value, bool):
            raise TypeError("bool is not a valid sizing value")
        if isinstance(value, int):
            return cls.cells(value)
        if isinstance(value, float):
            if 0 <= value <= 1:
                return cls.percent(value)
            return cls.cells(int(value))
        if isinstance(value, str):
            return cls._parse_string(value)
        raise TypeError(
            f"sizing must be an int, float, str, or Sizing, "
            f"got {type(value).__name__}"
        )

    @classmethod
    def _parse_string(cls, text: str) -> Sizing:
        token = text.strip().lower()
        if token in ("fit", "auto", "content"):
            return cls.fit()
        if token in ("fill", "grow"):
            return cls.fraction(1)
        if token in _FLEX_CLASS_WEIGHTS:
            return cls.fraction(_FLEX_CLASS_WEIGHTS[token])
        if token.endswith("%"):
            return cls.percent(float(token[:-1]))
        if token.endswith("fr"):
            weight = token[:-2].strip() or "1"
            return cls.fraction(int(weight))
        if "/" in token:
            numerator, _, denominator = token.partition("/")
            return cls.ratio(int(numerator), int(denominator))
        try:
            return cls.cells(int(token))
        except ValueError as error:
            raise ValueError(f"invalid sizing string: {text!r}") from error


SizingLike: TypeAlias = Union[int, float, str, Sizing]
"""Any value accepted where a :class:`Sizing` is expected.

See :meth:`Sizing.parse` for the full list of accepted forms.
"""


__all__ = ("Sizing", "SizingKind", "SizingLike")
