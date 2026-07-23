"""xnano.beta.components.schema

---

Declare table columns and chart series as component class attributes.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Callable, TypeAlias

if TYPE_CHECKING:
    from xnano.beta.colors import ColorLike
    from xnano.beta.types import Alignment, GraphTypeLike

ColorResolver: TypeAlias = Any
FormatResolver: TypeAlias = str | Callable[[Any], str] | None


@dataclasses.dataclass
class ComponentDescriptor:
    """Named declarative component field.

    Attributes:
        name: Attribute name assigned by the owning component class.
    """

    name: str = dataclasses.field(default="", init=False)
    """Attribute name assigned by the component class."""


@dataclasses.dataclass
class Column(ComponentDescriptor):
    """Describe one table column.

    Attributes:
        header: Header displayed for the column.
        accessor: Row attribute, mapping key, or value callback.
        format: Optional format string or value callback.
        color: Cell foreground color.
        background: Cell background color.
        align: Cell alignment.
        width: Fixed or proportional column width.
    """

    header: str | None = None
    """Displayed column header."""
    accessor: Callable[[Any], Any] | None = None
    """Custom row value accessor."""
    format: FormatResolver = None
    """Value formatter."""
    color: ColorResolver = None
    """Foreground color or resolver."""
    background: ColorResolver = None
    """Background color or resolver."""
    align: "Alignment | None" = None
    """Cell text alignment."""
    width: int | float | None = None
    """Fixed width or fractional width."""

    if TYPE_CHECKING:

        def __new__(cls, *args: Any, **kwargs: Any) -> Any: ...

    def resolve_header(self) -> str:
        """Return the displayed header."""
        return self.header or self.name.replace("_", " ").title()

    def resolve_value(self, row: Any) -> Any:
        """Read this column's value from a row."""
        if self.accessor is not None:
            return self.accessor(row)
        if isinstance(row, dict):
            return row.get(self.name)
        return getattr(row, self.name, None)

    def resolve_text(self, value: Any) -> str:
        """Format a value for display."""
        if value is None:
            return ""
        if self.format is None:
            return str(value)
        if isinstance(self.format, str):
            return self.format.format(value)
        return self.format(value)

    def resolve_color(self, value: Any) -> Any:
        """Resolve the foreground color for a value."""
        return self.color(value) if callable(self.color) else self.color

    def resolve_background(self, value: Any) -> Any:
        """Resolve the background color for a value."""
        return (
            self.background(value)
            if callable(self.background)
            else self.background
        )


@dataclasses.dataclass
class Series(ComponentDescriptor):
    """Describe one chart series.

    Attributes:
        label: Legend label.
        color: Series color.
        kind: Plot representation.
    """

    label: str | None = None
    """Legend label."""
    color: "ColorLike | None" = None
    """Series color."""
    kind: "GraphTypeLike | None" = None
    """Graph representation."""

    if TYPE_CHECKING:

        def __new__(cls, *args: Any, **kwargs: Any) -> Any: ...

    def resolve_label(self) -> str:
        """Return the displayed legend label."""
        return self.label or self.name


__all__ = (
    "ColorResolver",
    "Column",
    "ComponentDescriptor",
    "FormatResolver",
    "Series",
)
