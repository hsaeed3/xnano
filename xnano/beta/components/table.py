"""xnano.beta.components.table

---

Render mappings, dataclasses, or objects as a sortable data table.
"""

from __future__ import annotations

import dataclasses
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Literal,
    Sequence,
    TypeAlias,
    cast,
)

from xnano.beta.components.component import Component
from xnano.beta.components.schema import Column, ComponentDescriptor
from xnano.beta.core.content import (
    TableCell,
    TableGrid,
    TableRow,
)

if TYPE_CHECKING:
    from xnano.beta.colors import ColorLike
    from xnano.beta.components.component import ComponentRenderContext
    from xnano.beta.events import KeyboardEventData

ColumnsArg: TypeAlias = (
    "dict[str, Column | str | Callable[[Any], Any]] | list[str] | None"
)
"""Optional column overrides for the data-driven ``Table`` path."""

SortDirection: TypeAlias = Literal["ascending", "descending"]
"""Sort order applied to a derived row index without mutating data."""


@dataclasses.dataclass
class Table(Component):
    """Declarative data table.

    Feed it a list of rows — dicts, dataclasses, or arbitrary objects —
    and the columns are derived for you. Selection is a single attribute.
    For full control, subclass and declare ``Column`` descriptors.

    Example:
        ``Table(data=({"name": "Ada", "role": "Engineer"},))``

    Attributes:
        data: The rows — dicts, dataclasses, or objects with attributes.
        columns: Optional column overrides for the data-driven path.
        selected: Highlighted row index in display order.
        show_header: Whether to render the derived header row.
        column_spacing: Space between columns in terminal columns.
        highlight_color: Selection foreground color.
        highlight_background: Selection background color.
        highlight_symbol: Glyph prepended to the selected row.
        focusable: Whether keyboard navigation is enabled.
        passthrough: Key bindings that bubble without being consumed.
        sort: Optional column name used for a derived sort index.
        sort_direction: Ascending or descending sort order.
    """

    data: list[Any] = dataclasses.field(default_factory=list)
    """The rows — dicts, dataclasses, or objects with attributes."""
    columns: ColumnsArg = None  # type: ignore[assignment]
    """Optional column overrides for the data-driven path."""
    selected: int | None = None
    """Highlighted row index in display order."""
    show_header: bool = True
    """Whether to render the derived header row."""
    column_spacing: int = 1
    """Space between columns in terminal columns."""
    highlight_color: "ColorLike | None" = None
    """Selection foreground color."""
    highlight_background: "ColorLike | None" = None
    """Selection background color."""
    highlight_symbol: str | None = None
    """Glyph prepended to the selected row."""
    focusable: bool = False
    """Whether keyboard navigation is enabled."""
    passthrough: Sequence[str] = ()
    """Key bindings that bubble without being consumed."""
    sort: str | None = None
    """Optional column name used for a derived sort index."""
    sort_direction: SortDirection = "ascending"
    """Ascending or descending sort order."""

    _declared: ClassVar[dict[str, ComponentDescriptor]] = {}

    @staticmethod
    def _named(name: str, **kwargs: Any) -> Column:
        column = Column(**kwargs)
        column.name = name
        return column

    def _columns_from_arg(self, columns: Any) -> list[Column]:
        if isinstance(columns, dict):
            result: list[Column] = []
            for name, spec in columns.items():
                if isinstance(spec, Column):
                    column = Column(
                        header=spec.header,
                        accessor=spec.accessor,
                        format=spec.format,
                        color=spec.color,
                        background=spec.background,
                        align=spec.align,
                        width=spec.width,
                    )
                    column.name = name
                    result.append(column)
                elif isinstance(spec, str):
                    result.append(self._named(name, header=spec))
                elif callable(spec):
                    result.append(self._named(name, accessor=spec))
                else:
                    result.append(self._named(name))
            return result
        return [self._named(name) for name in columns]

    def _infer_columns(self) -> list[Column]:
        if not self.data:
            return []
        first = self.data[0]
        names: list[str]
        if isinstance(first, dict):
            names = [str(key) for key in first.keys()]
        elif dataclasses.is_dataclass(first) and not isinstance(first, type):
            names = [field.name for field in dataclasses.fields(first)]
        elif hasattr(first, "__dict__"):
            names = list(vars(first).keys())
        else:
            names = []
        return [self._named(name) for name in names]

    def _resolve_columns(self) -> list[Column]:
        if self._declared:
            return [cast(Column, column) for column in self._declared.values()]
        if self.columns is not None:
            return self._columns_from_arg(self.columns)
        return self._infer_columns()

    def _display_indices(self) -> list[int]:
        indices = list(range(len(self.data)))
        if self.sort is None or not self.data:
            return indices
        columns = {column.name: column for column in self._resolve_columns()}
        column = columns.get(self.sort)
        if column is None:
            # Fall back to raw key/attr access by sort name.
            column = self._named(self.sort)

        def sort_key(index: int) -> Any:
            value = column.resolve_value(self.data[index])
            return (value is None, value)

        reverse = self.sort_direction == "descending"
        return sorted(indices, key=sort_key, reverse=reverse)

    @staticmethod
    def _align_text(text: str, column: Column) -> str:
        if column.align is None or not isinstance(column.width, int):
            return text
        width = column.width
        if column.align == "right":
            return text.rjust(width)
        if column.align == "center":
            return text.center(width)
        return text.ljust(width)

    @property
    def selected_row(self) -> Any | None:
        """Return the source row currently selected, if any."""
        if self.selected is None:
            return None
        indices = self._display_indices()
        if self.selected < 0 or self.selected >= len(indices):
            return None
        return self.data[indices[self.selected]]

    @property
    def value(self) -> Any | None:
        """Alias for ``selected_row``."""
        return self.selected_row

    def move(self, delta: int) -> int | None:
        """Move the selection by ``delta`` rows in display order.

        Args:
            delta: Positive moves down; negative moves up.

        Returns:
            The new selected index, or ``None`` when there is no data.
        """
        count = len(self.data)
        if count == 0:
            self.selected = None
            return None
        current = 0 if self.selected is None else self.selected
        self.selected = max(0, min(count - 1, current + delta))
        return self.selected

    def handle_keyboard(self, keyboard: "KeyboardEventData") -> bool:
        """Navigate selection when ``focusable`` is enabled.

        Returns:
            ``True`` when the event was consumed.
        """
        if not self.focusable:
            return False
        for binding in self.passthrough:
            if keyboard.matches(binding):
                return False
        if keyboard.matches("up", "k"):
            self.move(-1)
            return True
        if keyboard.matches("down", "j"):
            self.move(1)
            return True
        if keyboard.matches("home"):
            if self.data:
                self.selected = 0
            return True
        if keyboard.matches("end"):
            if self.data:
                self.selected = len(self.data) - 1
            return True
        if keyboard.matches("pageup"):
            self.move(-10)
            return True
        if keyboard.matches("pagedown"):
            self.move(10)
            return True
        return False

    def _compose_table_grid(self) -> TableGrid:
        columns = self._resolve_columns()
        indices = self._display_indices()

        header: TableRow | None = None
        if self.show_header and columns:
            header = TableRow(
                cells=tuple(
                    TableCell(content=column.resolve_header())
                    for column in columns
                )
            )

        rows: list[TableRow] = []
        for index in indices:
            item = self.data[index]
            cells: list[TableCell] = []
            for column in columns:
                value = column.resolve_value(item)
                text = self._align_text(column.resolve_text(value), column)
                cells.append(
                    TableCell(
                        content=text,
                        color=column.resolve_color(value),
                        background=column.resolve_background(value),
                    )
                )
            rows.append(TableRow(cells=tuple(cells)))

        column_widths: tuple[int | float, ...] | None = None
        if columns and all(column.width is not None for column in columns):
            column_widths = tuple(
                cast(int | float, column.width) for column in columns
            )

        return TableGrid(
            rows=tuple(rows),
            header=header,
            column_widths=column_widths,
            column_spacing=self.column_spacing,
            selected_row=self.selected,
            highlight_color=self.highlight_color,
            highlight_background=self.highlight_background,
            highlight_symbol=self.highlight_symbol,
            z=self.z,
            visible=self.visible,
        )

    def compose(self, ctx: "ComponentRenderContext"):
        """Compose TableGrid content with a native TableNode paint fallback.

        Returns:
            Interface-neutral content for this table.
        """
        return self._compose_table_grid()


__all__ = (
    "Column",
    "ColumnsArg",
    "SortDirection",
    "Table",
)
