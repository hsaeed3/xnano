"""xnano.components.schema

---

Declarative descriptor infrastructure for data-driven components.

``Column`` and ``Series`` mirror ``xnano.fields.Field``: they are declared
as class attributes on an ``AbstractComponent`` subclass and captured by
``DeclarativeComponentMeta`` at class-creation time, so a component subclass
reads like a schema rather than a pile of ratatui builders:

    class Services(Table):
        service: str = Column()
        status: str = Column(color=lambda v: "green" if v == "ok" else "red")
        latency: int = Column(align="right", format="{}ms")

    Services(data=[{"service": "api", "status": "ok", "latency": 12}])
"""

from __future__ import annotations

import abc
import dataclasses
from typing import TYPE_CHECKING, Any, Callable, TypeAlias


if TYPE_CHECKING:
    from xnano._types import Alignment, GraphTypeLike
    from xnano.color import ColorLike


ColorResolver: TypeAlias = Any
"""A static color, or a callable that derives one from a cell/point value.

Typed as ``Any`` so static checkers do not treat ``ColorLike`` strings as
callables when resolving value-dependent colors.
"""


FormatResolver: TypeAlias = str | Callable[[Any], str] | None
"""A ``str.format`` template, a formatter callable, or ``None``."""


@dataclasses.dataclass
class ComponentDescriptor:
    """Base for declarative class-level descriptors (``Column``, ``Series``).

    The owning attribute name is filled in by ``DeclarativeComponentMeta`` when
    the descriptor is captured.
    """

    name: str = dataclasses.field(default="", init=False)


@dataclasses.dataclass
class Column(ComponentDescriptor):
    """Declares one column of a ``Table``.

    Attributes:
        header: Column header text; ``None`` derives it from the attribute
            name (e.g. ``latency`` → ``"Latency"``).
        accessor: How to pull this column's value from a row; ``None`` reads
            ``row[name]`` for mappings or ``getattr(row, name)`` for objects.
        format: A ``str.format`` template (``"{}ms"``) or a callable applied to
            the value to produce cell text; ``None`` uses ``str(value)``.
        color: Cell foreground — a color or a callable of the value.
        background: Cell background — a color or a callable of the value.
        align: Cell text alignment.
        width: Fixed cell width (``int``) or fractional share (``float`` 0–1);
            ``None`` shares space equally.
    """

    header: str | None = None
    accessor: Callable[[Any], Any] | None = None
    format: FormatResolver = None
    color: ColorResolver = None
    background: ColorResolver = None
    align: "Alignment | None" = None
    width: int | float | None = None

    if TYPE_CHECKING:
        # Class-body assignments like ``latency: int = Column(...)`` are the
        # supported declarative form.  At runtime the metaclass strips the
        # descriptor; at type-check time we type the constructor as ``Any``
        # so the annotation and right-hand side remain compatible.
        def __new__(cls, *args: Any, **kwargs: Any) -> Any: ...

    def resolve_header(self) -> str:
        """Return the header text, deriving one from ``name`` when unset.

        Returns:
            The header text for this column.
        """
        if self.header is not None:
            return self.header
        return self.name.replace("_", " ").title()

    def resolve_value(self, row: Any) -> Any:
        """Read this column's raw value from ``row``.

        Args:
            row: A mapping, dataclass instance, or attribute-bearing object.

        Returns:
            The raw cell value, or ``None`` when the key/attribute is missing.
        """
        if self.accessor is not None:
            return self.accessor(row)
        if isinstance(row, dict):
            return row.get(self.name)
        return getattr(row, self.name, None)

    def resolve_text(self, value: Any) -> str:
        """Format ``value`` into display text.

        Args:
            value: The raw cell value.

        Returns:
            Display text for the cell. Empty string when ``value`` is ``None``.
        """
        if value is None:
            return ""
        formatter = self.format
        if formatter is None:
            return str(value)
        if isinstance(formatter, str):
            return formatter.format(value)
        return formatter(value)

    def resolve_color(self, value: Any) -> Any:
        """Resolve a possibly value-dependent foreground color.

        Args:
            value: The raw cell value.

        Returns:
            A color, or ``None`` when no color is configured.
        """
        color = self.color
        if callable(color):
            return color(value)
        return color

    def resolve_background(self, value: Any) -> Any:
        """Resolve a possibly value-dependent background color.

        Args:
            value: The raw cell value.

        Returns:
            A color, or ``None`` when no background is configured.
        """
        background = self.background
        if callable(background):
            return background(value)
        return background


@dataclasses.dataclass
class Series(ComponentDescriptor):
    """Declares one series of a ``Chart``.

    Attributes:
        label: Legend label; ``None`` derives it from the attribute name.
        color: Series color.
        kind: Per-series plot kind, overriding the chart default.
    """

    label: str | None = None
    color: "ColorLike | None" = None
    kind: "GraphTypeLike | None" = None

    if TYPE_CHECKING:

        def __new__(cls, *args: Any, **kwargs: Any) -> Any: ...

    def resolve_label(self) -> str:
        """Return the legend label, deriving one from ``name`` when unset.

        Returns:
            The legend label for this series.
        """
        return self.label if self.label is not None else self.name


class DeclarativeComponentMeta(abc.ABCMeta):
    """Metaclass that captures ``ComponentDescriptor`` class attributes.

    Descriptors declared on a component subclass are collected in declaration
    order (across the MRO) into ``_declared`` and removed from the class body,
    so instances never expose raw descriptor objects. Mirrors the way
    ``xnano.grid._GridMeta`` captures ``Field`` declarations.
    """

    _declared: dict[str, ComponentDescriptor]

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> DeclarativeComponentMeta:
        declared: dict[str, ComponentDescriptor] = {}
        for base in bases:
            inherited = getattr(base, "_declared", None)
            if inherited:
                declared.update(inherited)
        for key, value in list(namespace.items()):
            if isinstance(value, ComponentDescriptor):
                value.name = key
                declared[key] = value
                del namespace[key]
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        cls._declared = declared
        return cls


__all__ = (
    "ColorResolver",
    "FormatResolver",
    "ComponentDescriptor",
    "Column",
    "Series",
    "DeclarativeComponentMeta",
)
