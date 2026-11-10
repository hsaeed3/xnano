"""
xnano.reader._tables

A table of a Markdown document, as a [`Table`][xnano.widgets.Table] widget.
"""

from __future__ import annotations

import dataclasses
import re

from xnano.reader._inline import inline_runs
from xnano.reader._lines import Run, fit_widths, line_of, pad_runs, styled, wrap_runs
from xnano.themes import Theme
from xnano_core import Block, Table, TableRow, display_width

__all__ = ['MarkdownTable', 'markdown_table']


@dataclasses.dataclass(frozen=True, slots=True)
class MarkdownTable:
    """
    A table that was read from Markdown.

    Attributes:
        table: The widget that draws the table.
        width: The width of the table with its border, in cells.
        height: The height of the table with its border, in rows.
        description: The text of every cell, which a search reads.
        end: The index of the first line after the table in the document.
    """

    table: Table
    width: int
    height: int
    description: str
    end: int


def markdown_table(
    lines: list[str],
    index: int,
    *,
    references: dict[str, str],
    theme: Theme,
    available: int,
) -> MarkdownTable:
    """
    Read the table that starts at ``lines[index]``.

    A column is as wide as its text, or narrower when the table must fit: the widest
    column gives way first, and its text is wrapped.

    Args:
        lines: The lines of the document.
        index: The index of the header row of the table. The next line is its divider.
        references: The targets of the reference links of the document.
        theme: The theme that the table is drawn in.
        available: The width that the table must fit in, in cells.

    Returns:
        The table and its size.
    """
    header = _cells(lines[index])
    count = len(header)
    alignments = (
        [_alignment(cell) for cell in _cells(lines[index + 1])] + ['left'] * count
    )[:count]
    index += 2
    rows: list[list[str]] = []
    while index < len(lines) and lines[index].strip() and '|' in lines[index]:
        rows.append(_cells(lines[index]))
        index += 1
    cells = [
        [inline_runs(cell, references) for cell in (row + [''] * count)[:count]]
        for row in [header, *rows]
    ]
    widths = fit_widths(
        [
            max((_width(row[column]) for row in cells), default=1) or 1
            for column in range(count)
        ],
        available - 2 - 2 * (count - 1),
    )
    built = [
        _row(row, widths, alignments, theme, is_header=row_index == 0)
        for row_index, row in enumerate(cells)
    ]
    table_rows = [row for row, _ in built]
    table = Table(
        table_rows[1:],
        header=table_rows[0],
        widths=widths,
        column_spacing=2,
        style=theme.style(),
        block=Block(border_type='rounded', border_style=theme.style(role='border')),
    )
    return MarkdownTable(
        table,
        width=sum(widths) + 2 * (count - 1) + 2,
        height=2 + sum(height for _, height in built),
        description=' '.join(' '.join(row) for row in [header, *rows]),
        end=index,
    )


def _cells(line: str) -> list[str]:
    """The cells of one row of a table."""
    text = line.strip()
    if text.startswith('|'):
        text = text[1:]
    if text.endswith('|') and not text.endswith('\\|'):
        text = text[:-1]
    return [cell.strip().replace('\\|', '|') for cell in re.split(r'(?<!\\)\|', text)]


def _alignment(cell: str) -> str:
    """The alignment that one cell of the divider row asks for."""
    if cell.startswith(':') and cell.endswith(':'):
        return 'center'
    return 'right' if cell.endswith(':') else 'left'


def _width(runs: list[Run]) -> int:
    """The width of the text of ``runs``, in cells."""
    return display_width(''.join(run.text for run in runs))


def _row(
    row: list[list[Run]],
    widths: list[int],
    alignments: list[str],
    theme: Theme,
    *,
    is_header: bool,
) -> tuple[TableRow, int]:
    """One row of the table and its height: the text of each cell is wrapped in its column."""
    wrapped = [wrap_runs(cell, widths[column]) for column, cell in enumerate(row)]
    height = max(len(cell) for cell in wrapped)
    row_shown = TableRow(
        [
            styled(
                [
                    line_of(pad_runs(part, widths[column], alignments[column]))
                    for part in cell
                ],
                theme,
            )
            for column, cell in enumerate(wrapped)
        ],
        height=height,
        style=theme.style(role='heading', bold=True) if is_header else None,
    )
    return row_shown, height
