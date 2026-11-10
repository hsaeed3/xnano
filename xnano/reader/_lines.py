"""
xnano.reader._lines

The lines that the reader shows: runs of text with a look, wrapped to a width in cells.

Every kind of file becomes a list of [`Line`][xnano.reader._lines.Line] values. A line holds
its styled text, the links in it, the heading that it starts, and the content (an image, a
table) that it is a row of.
"""

from __future__ import annotations

import dataclasses
import re
from typing import Literal

from xnano.themes import Theme
from xnano_core import StyledText, TextSpan, display_width

__all__ = [
    'Line',
    'Run',
    'content_lines',
    'line_of',
    'pad_runs',
    'styled',
    'wrap_runs',
]

WORD = re.compile(r'\n|[^\S\n]+|\S+')


@dataclasses.dataclass(frozen=True, slots=True)
class Run:
    """
    A piece of text with one look.

    Attributes:
        text: The text. A newline ends the line.
        bold: Whether the text is bold.
        italic: Whether the text is italic.
        dim: Whether the text is dim, for marks and secondary text.
        strike: Whether a line goes through the text.
        code: Whether the text is code.
        role: What the text is, for its color in a theme: ``'heading'``, ``'accent'``,
            ``'string'``, ``'number'``, ``'keyword'``, ``'warning'`` or ``'error'``, or
            ``None`` for plain text.
        target: Where the text leads when it is a link, or ``None``.
        image_source: The path or the address of the image that stands here, with ``text``
            as its description, or ``None``.
    """

    text: str
    bold: bool = False
    italic: bool = False
    dim: bool = False
    strike: bool = False
    code: bool = False
    role: str | None = None
    target: str | None = None
    image_source: str | None = None


@dataclasses.dataclass(slots=True)
class Line:
    """
    One line of a document, as the reader shows it.

    Attributes:
        spans: The pieces of text of the line, in order.
        links: The links of the line: the first column, the column after the last, and
            the place that the link leads to.
        heading: The level and the text of the heading that the line starts, or ``None``.
        content: What is written over the rows that the line is one of, or ``None``: the
            file of an image, or a widget such as a [`Table`][xnano.widgets.Table].
        content_row: Which row of that content the line is, from ``0``.
        content_size: The width and the height of that content, in cells.
        content_column: The column of the left edge of that content.
        description: The words that stand for that content: what the search reads, and
            what the reader shows if an image cannot be decoded.
        number: The number of the line in the file, for the search and the status line.
    """

    spans: list[Run] = dataclasses.field(default_factory=list)
    links: list[tuple[int, int, str]] = dataclasses.field(default_factory=list)
    heading: tuple[int, str] | None = None
    content: object | None = None
    content_row: int = 0
    content_size: tuple[int, int] = (0, 0)
    content_column: int = 0
    description: str = ''
    number: int | None = None

    @property
    def text(self) -> str:
        """The text of the line without its looks, or the words that stand for its content."""
        if self.content is not None and self.content_row == 0:
            return self.description
        return ''.join(run.text for run in self.spans)


def line_of(runs: list[Run]) -> Line:
    """A line of ``runs``, with the columns of its links worked out."""
    line = Line(spans=[run for run in runs if run.text])
    column = 0
    for run in line.spans:
        width = display_width(run.text)
        if run.target is not None:
            if (
                line.links
                and line.links[-1][1] == column
                and line.links[-1][2] == run.target
            ):
                line.links[-1] = (line.links[-1][0], column + width, run.target)
            else:
                line.links.append((column, column + width, run.target))
        column += width
    return line


def styled(lines: list[Line], theme: Theme) -> StyledText:
    """The lines as one styled text in the colors of ``theme``, with a newline between two lines."""
    spans: list[TextSpan] = []
    for index, line in enumerate(lines):
        if index:
            spans.append(TextSpan('\n'))
        spans.extend(TextSpan(run.text, style=theme.style_of(run)) for run in line.spans)
    return StyledText(spans or [TextSpan('')])


def wrap_runs(
    runs: list[Run], width: int, *, keeps_spaces: bool = False
) -> list[list[Run]]:
    """
    Break ``runs`` into lines no wider than ``width`` cells.

    A line breaks at a space, and a word wider than a whole line breaks inside. Width is
    counted in cells, so wide characters keep their alignment.

    Args:
        runs: The runs to wrap. A newline in a run ends the line.
        width: The width of a line, in cells.
        keeps_spaces: Whether the spaces at the start of a line and between words stay as
            they are, for code. Otherwise a broken line starts at its first word.

    Returns:
        The runs of each line. There is always one line.
    """
    width = max(width, 1)
    lines: list[list[Run]] = [[]]
    used = 0
    for run in runs:
        for word in WORD.findall(run.text):
            if word == '\n':
                lines.append([])
                used = 0
                continue
            if word.isspace() and not keeps_spaces:
                if used == 0 or used + 1 > width:
                    continue
                word = ' '
            size = display_width(word)
            if used and used + size > width:
                if not keeps_spaces and lines[-1] and lines[-1][-1].text.isspace():
                    lines[-1].pop()
                lines.append([])
                used = 0
                if word.isspace() and not keeps_spaces:
                    continue
            while size > width:
                head, word = _split(word, width - used)
                lines[-1].append(dataclasses.replace(run, text=head))
                lines.append([])
                used = 0
                size = display_width(word)
            if word:
                lines[-1].append(dataclasses.replace(run, text=word))
                used += size
    for line in lines:
        while not keeps_spaces and line and line[-1].text.isspace():
            line.pop()
    return lines


def _split(word: str, width: int) -> tuple[str, str]:
    """The start of ``word`` that fits in ``width`` cells, and the rest of it."""
    used = 0
    for index, character in enumerate(word):
        size = display_width(character)
        if used + size > width and index:
            return word[:index], word[index:]
        used += size
    return word, ''


def pad_runs(
    runs: list[Run],
    width: int,
    alignment: Literal['left', 'center', 'right'] | str = 'left',
) -> list[Run]:
    """The runs with spaces around them, so that they take exactly ``width`` cells."""
    space = max(width - sum(display_width(run.text) for run in runs), 0)
    before = space if alignment == 'right' else space // 2 if alignment == 'center' else 0
    padded = list(runs)
    if before:
        padded.insert(0, Run(' ' * before))
    if space - before:
        padded.append(Run(' ' * (space - before)))
    return padded


def content_lines(
    content: object,
    *,
    columns: int,
    rows: int,
    column: int = 0,
    description: str = '',
    prefix: list[Run] | None = None,
) -> list[Line]:
    """
    The lines that hold a place for content of ``columns`` by ``rows`` cells.

    Args:
        content: The file of an image, or a widget.
        columns: The width of the content, in cells.
        rows: The height of the content, in cells.
        column: The column of the left edge of the content.
        description: The words that stand for the content.
        prefix: The runs that start each of the lines, such as the bar of a quote.

    Returns:
        One line for each row of the content.
    """
    lines: list[Line] = []
    for row in range(rows):
        line = line_of(list(prefix or []))
        line.content = content
        line.content_row = row
        line.content_size = (columns, rows)
        line.content_column = column
        line.description = description
        lines.append(line)
    return lines
