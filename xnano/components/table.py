"""xnano.components.table

---

``Table`` component for declarative, data-driven tabular layouts.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Callable, ClassVar, TypeAlias, cast, TYPE_CHECKING

from xnano.components.abstract import AbstractComponent
from xnano.components.schema import (
    Column,
    ComponentDescriptor,
    DeclarativeComponentMeta,
)

if TYPE_CHECKING:
    from xnano.color import ColorLike
    from xnano.components.abstract import ComponentRenderContext
    from xnano.tui.nodes import AbstractTerminalNode


ColumnsArg: TypeAlias = (
    "dict[str, Column | str | Callable[[Any], Any]] | list[str] | None"
)
"""Optional column overrides for the data-driven ``Table`` path."""


@dataclasses.dataclass
class Table(AbstractComponent, metaclass=DeclarativeComponentMeta):
    """Declarative data table.

    Feed it a list of rows — dicts, dataclasses, or arbitrary objects — and the
    columns are derived for you. Selection is a single attribute (the native
    table scrolls to keep it in view). For full control, subclass and declare
    ``Column`` descriptors, the way a ``BaseGrid`` declares ``Field``:

        # data-driven — columns inferred from the dict keys
        Table(data=[{"service": "api", "status": "ok", "latency": 12}])

        # data-driven with per-column overrides, no subclass
        Table(data=rows, columns={
            "service": "Service",
            "latency": Column(align="right", format="{}ms"),
        })

        # declarative subclass — reads like a schema
        class Services(Table):
            service: str = Column()
            status:  str = Column(
                color=lambda v: "green" if v == "ok" else "red")
            latency: int = Column(align="right", format="{}ms")

        Services(data=rows, selected=0)
    """

    data: list[Any] = dataclasses.field(default_factory=list)
    """The rows — dicts, dataclasses, or objects with attributes."""
    columns: ColumnsArg = None  # type: ignore[assignment]
    """Optional column overrides for the data-driven path: a list of field
    names (to select/order) or a mapping of name → ``Column`` / header string /
    accessor. Ignored when the subclass declares ``Column`` descriptors."""
    selected: int | None = None
    """Highlighted row index; the native table scrolls to keep it visible."""
    show_header: bool = True
    """Whether to render the derived header row."""
    column_spacing: int = 1
    """Space between columns in terminal columns."""
    highlight_color: ColorLike | None = None
    """Selection foreground color."""
    highlight_background: ColorLike | None = None
    """Selection background color."""
    highlight_symbol: str | None = None
    """Glyph prepended to the selected row."""

    _declared: ClassVar[dict[str, ComponentDescriptor]] = {}

    # ── column resolution ────────────────────────────────────────────────

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
                    # Copy so mutating ``.name`` does not touch a shared
                    # descriptor instance the caller may reuse elsewhere.
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

    # ── rendering ────────────────────────────────────────────────────────

    def compose(self, ctx):
        """Compose Content via Native tui payload of the existing node tree."""
        from xnano.core.content import Native

        return Native(
            interface_kind="tui",
            payload=self.get_terminal_node(ctx),
            z=self.z,
            visible=self.visible,
        )

    def get_terminal_node(
        self, ctx: ComponentRenderContext
    ) -> AbstractTerminalNode:
        from xnano.tui.nodes import (
            TableCellItem,
            TableNode,
            TableRowItem,
        )

        columns = self._resolve_columns()

        header: TableRowItem | None = None
        if self.show_header and columns:
            header = TableRowItem(
                cells=[column.resolve_header() for column in columns]
            )

        rows: list[TableRowItem] = []
        for item in self.data:
            cells: list[TableCellItem | str] = []
            for column in columns:
                value = column.resolve_value(item)
                text = self._align_text(column.resolve_text(value), column)
                cells.append(
                    TableCellItem(
                        content=text,
                        color=column.resolve_color(value),
                        background=column.resolve_background(value),
                    )
                )
            rows.append(TableRowItem(cells=cells))

        column_widths: list[int | float] | None = None
        if columns and all(column.width is not None for column in columns):
            column_widths = [
                cast(int | float, column.width) for column in columns
            ]

        return TableNode(
            rows=rows,
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


__all__ = ("Table", "ColumnsArg")
