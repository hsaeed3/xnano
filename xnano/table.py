"""xnano.table"""

from __future__ import annotations

import dataclasses
from typing import Any, Sequence

from xnano import _core
from xnano._convert import Content, as_line, as_text
from xnano.layout import Constraint
from xnano.style import HighlightSpacingName, Style, _core_highlight_spacing
from xnano.widgets import Block


class Cell:
    """A single cell inside a Table Row.

    Example::

        cell = Cell("Value", style=Style(foreground="green", modifiers="bold"))
    """

    __slots__ = ("_inner",)
    _inner: _core.Cell

    def __init__(
        self, content: Content, *, style: Style | None = None
    ) -> None:
        """Create a new Table Cell.

        Args:
            content: The text content of this cell.
            style: Optional styling for this cell.
        """
        inner = _core.Cell.new(as_line(content))
        if style is not None:
            inner = inner.style(style._to_core())
        object.__setattr__(self, "_inner", inner)

    @classmethod
    def _from_core(cls, inner: _core.Cell) -> Cell:
        """Construct from a native ``_core.Cell``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.Cell:
        """Return the native cell."""
        return self._inner

    def __repr__(self) -> str:
        return "Cell()"

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Cell is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Cell is immutable")


class Row:
    """A horizontal row of cells in a Table widget.

    Example::

        row = Row([Cell("A"), Cell("B"), Cell("C")], height=2)
    """

    __slots__ = ("_inner",)
    _inner: _core.Row

    def __init__(
        self,
        cells: Sequence[Cell | Content],
        *,
        style: Style | None = None,
        height: int | None = None,
        top_margin: int | None = None,
        bottom_margin: int | None = None,
    ) -> None:
        """Create a new Row.

        Args:
            cells: List of cell contents in the row. Can be Strings, Spans,
                or explicit ``Cell`` instances.
            style: Default base style for all cells in the row.
            height: Row height in terminal cell lines.
            top_margin: Height margin above the row.
            bottom_margin: Height margin below the row.
        """
        native_cells = [
            cell._to_core()
            if isinstance(cell, Cell)
            else _core.Cell.new(as_line(cell))
            for cell in cells
        ]
        inner = _core.Row.new(native_cells)

        if style is not None:
            inner = inner.style(style._to_core())
        if height is not None:
            inner = inner.height(height)
        if top_margin is not None:
            inner = inner.top_margin(top_margin)
        if bottom_margin is not None:
            inner = inner.bottom_margin(bottom_margin)

        object.__setattr__(self, "_inner", inner)

    @classmethod
    def _from_core(cls, inner: _core.Row) -> Row:
        """Construct from a native ``_core.Row``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.Row:
        """Return the native row."""
        return self._inner

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Row is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Row is immutable")


class Table:
    """A tabular grid widget for displaying structured data.

    Example::

        table = Table(
            [Row(["Value 1", "Value 2"])],
            [Constraint.percentage(50), Constraint.percentage(50)],
            header=Row(["Col A", "Col B"])
        )
    """

    __slots__ = ("_inner", "width", "height")
    _inner: _core.RatTable

    def __init__(
        self,
        rows: Sequence[Row],
        widths: Sequence[Constraint],
        *,
        header: Row | None = None,
        footer: Row | None = None,
        block: Block | None = None,
        style: Style | None = None,
        row_highlight_style: Style | None = None,
        column_highlight_style: Style | None = None,
        cell_highlight_style: Style | None = None,
        highlight_symbol: Content | None = None,
        highlight_spacing: HighlightSpacingName | None = None,
        column_spacing: int | None = None,
        width: int | None = None,
        height: int | None = None,
        class_name: str | None = None,
    ) -> None:
        """Create a Table.

        Args:
            rows: List of Rows to draw in the table body.
            widths: Layout constraint width for each column.
            header: Header row.
            footer: Footer row.
            block: Background/border block around the table.
            style: Base visual style.
            row_highlight_style: Selected row styling.
            column_highlight_style: Selected column styling.
            cell_highlight_style: Selected cell styling.
            highlight_symbol: Symbol drawn next to selected row.
            highlight_spacing: Highlight spacing mode.
            column_spacing: Inter-column spacing gap in cells.
            width: Optional fixed width constraint.
            height: Optional fixed height constraint.
            class_name: Optional space-separated Tailwind utility classes.
        """
        from xnano.widgets import _merge_tailwind

        style, width, height, block = _merge_tailwind(
            class_name, style, width, height, block
        )
        inner = _core.RatTable.new(
            [row._to_core() for row in rows],
            [w._to_core() for w in widths],
        )

        if header is not None:
            inner = inner.header(header._to_core())
        if footer is not None:
            inner = inner.footer(footer._to_core())
        if block is not None:
            inner = inner.block(block._to_core())
        if style is not None:
            inner = inner.style(style._to_core())
        if row_highlight_style is not None:
            inner = inner.row_highlight_style(row_highlight_style._to_core())
        if column_highlight_style is not None:
            inner = inner.column_highlight_style(
                column_highlight_style._to_core()
            )
        if cell_highlight_style is not None:
            inner = inner.cell_highlight_style(cell_highlight_style._to_core())
        if highlight_symbol is not None:
            inner = inner.highlight_symbol(as_text(highlight_symbol))
        if highlight_spacing is not None:
            inner = inner.highlight_spacing(
                _core_highlight_spacing(highlight_spacing)
            )
        if column_spacing is not None:
            inner = inner.column_spacing(column_spacing)

        if width is None and block is not None:
            width = getattr(block, "width", None)
        if height is None and block is not None:
            height = getattr(block, "height", None)

        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "width", width)
        object.__setattr__(self, "height", height)

    @classmethod
    def _from_core(cls, inner: _core.RatTable) -> Table:
        """Construct from a native ``_core.RatTable``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.RatTable:
        """Return the native table."""
        return self._inner

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Table is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Table is immutable")


class TableState:
    """Mutable selection and scroll state tracking for a ``Table`` widget.

    Example::

        state = TableState()
        state.select(0)
    """

    __slots__ = ("_inner",)
    _inner: _core.TableState

    def __init__(
        self,
        *,
        selected: int | None = None,
        selected_column: int | None = None,
    ) -> None:
        """Create a new mutable TableState.

        Args:
            selected: Optional initial selected row index.
            selected_column: Optional initial selected column index.
        """
        inner = _core.TableState()
        if selected is not None:
            inner.select(selected)
        if selected_column is not None:
            inner.select_column(selected_column)
        object.__setattr__(self, "_inner", inner)

    @classmethod
    def _from_core(cls, inner: _core.TableState) -> TableState:
        """Construct from a native ``_core.TableState``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.TableState:
        """Return the native table state."""
        return self._inner

    def select(self, index: int | None = None) -> None:
        """Select the row at the given index, or clear row selection."""
        self._inner.select(index)

    @property
    def selected(self) -> int | None:
        """The index of the currently selected row, or ``None``."""
        return self._inner.selected

    @property
    def selected_column(self) -> int | None:
        """The index of the currently selected column, or ``None``."""
        return self._inner.selected_column

    def selected_cell(self) -> tuple[int, int] | None:
        """Return a tuple of ``(row_index, column_index)`` representing the selected cell."""
        return self._inner.selected_cell()

    @property
    def offset(self) -> int:
        """The row scroll offset of the table viewport."""
        return self._inner.offset

    def select_column(self, index: int | None = None) -> None:
        """Select the column at the given index, or clear column selection."""
        self._inner.select_column(index)

    def select_cell(self, indexes: tuple[int, int] | None = None) -> None:
        """Select the cell at the given row/column index coordinate tuple."""
        self._inner.select_cell(indexes)

    def select_next(self) -> None:
        """Select the next row in the table."""
        self._inner.select_next()

    def select_previous(self) -> None:
        """Select the previous row in the table."""
        self._inner.select_previous()

    def select_next_column(self) -> None:
        """Select the next column to the right."""
        self._inner.select_next_column()

    def select_previous_column(self) -> None:
        """Select the previous column to the left."""
        self._inner.select_previous_column()

    def select_first(self) -> None:
        """Select the first row in the table."""
        self._inner.select_first()

    def select_last(self) -> None:
        """Select the last row in the table."""
        self._inner.select_last()

    def select_first_column(self) -> None:
        """Select the first column to the far left."""
        self._inner.select_first_column()

    def select_last_column(self) -> None:
        """Select the last column to the far right."""
        self._inner.select_last_column()

    def scroll_down_by(self, amount: int) -> None:
        """Scroll the viewport down by *amount* rows."""
        self._inner.scroll_down_by(amount)

    def scroll_up_by(self, amount: int) -> None:
        """Scroll the viewport up by *amount* rows."""
        self._inner.scroll_up_by(amount)

    def scroll_right_by(self, amount: int) -> None:
        """Scroll the viewport right by *amount* columns."""
        self._inner.scroll_right_by(amount)

    def scroll_left_by(self, amount: int) -> None:
        """Scroll the viewport left by *amount* columns."""
        self._inner.scroll_left_by(amount)

    def __repr__(self) -> str:
        return repr(self._inner)


__all__ = ("Cell", "Row", "Table", "TableState")
