"""
xnano.reader._markdown

Markdown, read into blocks and laid out as lines of styled text at a width in cells.

The reader covers the Markdown that documents use in practice: headings, paragraphs, emphasis,
code, links and reference links, images, lists with tasks, quotes, fenced code, tables and
rules, and the HTML that READMEs mix in (comments, ``<img>``, ``<br>``). It needs no package
besides xnano.
"""

from __future__ import annotations

import dataclasses
import pathlib
import re

from xnano.reader._images import cells_for, image_file, pixel_size
from xnano.reader._lines import (
    Line,
    Run,
    content_lines,
    line_of,
    pad_runs,
    styled,
    wrap_runs,
)
from xnano.themes import Theme
from xnano_core import display_width

__all__ = ['layout_markdown']

FENCE = re.compile(
    r'^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})\s*(?P<language>[^`\s]*).*$'
)
HEADING = re.compile(r'^ {0,3}(?P<marks>#{1,6})(?:\s+(?P<text>.*?))?(?:\s+#+)?\s*$')
RULE = re.compile(r'^ {0,3}(?:(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,})$')
SETEXT = re.compile(r'^ {0,3}(?P<mark>=+|-+)\s*$')
QUOTE = re.compile(r'^ {0,3}>\s?(?P<text>.*)$')
ITEM = re.compile(r'^(?P<indent>\s*)(?P<marker>[-*+]|\d{1,9}[.)])(?:\s+(?P<text>.*))?$')
TASK = re.compile(r'^\[(?P<mark>[ xX])\]\s+(?P<text>.*)$')
TABLE_DIVIDER = re.compile(r'^\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)*\|?\s*$')
REFERENCE = re.compile(r'^ {0,3}\[(?P<name>[^\]]+)\]:\s*(?P<target><[^>]*>|\S+).*$')
COMMENT = re.compile(r'<!--.*?-->', re.DOTALL)
HTML_BLOCK = re.compile(r'^ {0,3}</?[A-Za-z][^>]*>')
HTML_TAG = re.compile(r'</?[A-Za-z][^>]*>')
HTML_IMAGE = re.compile(r'<img\b[^>]*>', re.IGNORECASE)
HTML_ATTRIBUTE = re.compile(r'(?P<name>[A-Za-z-]+)\s*=\s*"(?P<value>[^"]*)"')
INLINE = re.compile(
    r"""
      (?P<escape>\\[\\`*_{}\[\]()#+\-.!|~<>])
    | (?P<code>(?P<ticks>`+)(?P<code_text>.+?)(?<!`)(?P=ticks)(?!`))
    | (?P<image>!\[(?P<alt>[^\]]*)\]\((?P<source><[^>]*>|[^)\s]*)(?:\s+"[^"]*")?\))
    | (?P<link>\[(?P<label>(?:[^\[\]]|!?\[[^\]]*\](?:\([^)]*\))?)*)\]
        \((?P<target><[^>]*>|[^)\s]*)(?:\s+"[^"]*")?\))
    | (?P<reference>\[(?P<reference_label>[^\[\]]+)\]\[(?P<reference_name>[^\]]*)\])
    | (?P<autolink><(?P<address>https?://[^>\s]+)>)
    | (?P<break><br\s*/?>)
    | (?P<html></?[A-Za-z][^>]*>)
    | (?P<strong>\*\*(?=\S)(?P<strong_star>.+?)(?<=\S)\*\*
        |(?<![A-Za-z0-9])__(?=\S)(?P<strong_under>.+?)(?<=\S)__(?![A-Za-z0-9]))
    | (?P<strike>~~(?=\S)(?P<strike_text>.+?)(?<=\S)~~)
    | (?P<emphasis>(?:\*(?=[^\s*])(?P<star_text>.+?)(?<=[^\s*])\*(?!\*))
        |(?:(?<![A-Za-z0-9_])_(?=[^\s_])(?P<under_text>.+?)(?<=[^\s_])_(?![A-Za-z0-9_])))
    """,
    re.VERBOSE | re.DOTALL,
)


@dataclasses.dataclass
class _Context:
    """What the layout of one document needs: its width, its folder and its link names."""

    width: int
    directory: pathlib.Path | None
    references: dict[str, str]
    theme: Theme
    lines: list[Line] = dataclasses.field(default_factory=list)

    def gap(self) -> None:
        """Leave one empty line before the next block, but none at the top."""
        if self.lines and (self.lines[-1].spans or self.lines[-1].content is not None):
            self.lines.append(Line())


def layout_markdown(
    text: str, *, width: int, theme: Theme, directory: pathlib.Path | None = None
) -> list[Line]:
    """
    Lay Markdown out as lines no wider than ``width`` cells.

    Args:
        text: The Markdown source.
        width: The width of the lines, in cells.
        theme: The theme that the tables of the document are drawn in.
        directory: The folder that the paths of images and links are relative to, or
            ``None`` when the text does not come from a file.

    Returns:
        The lines, in order. The lines that an image takes name its file.
    """
    source = _without_comments(text.expandtabs(4)).split('\n')
    references: dict[str, str] = {}
    kept: list[str] = []
    is_fenced = False
    for line in source:
        if FENCE.match(line):
            is_fenced = not is_fenced
        match = None if is_fenced else REFERENCE.match(line)
        if match is None:
            kept.append(line)
        else:
            references[match['name'].lower()] = match['target'].strip('<>')
    context = _Context(
        width=max(width, 8), directory=directory, references=references, theme=theme
    )
    _blocks(kept, context, prefix=[], rest=[])
    while (
        context.lines
        and not context.lines[-1].spans
        and context.lines[-1].content is None
    ):
        context.lines.pop()
    return context.lines


def _without_comments(text: str) -> str:
    """The text without HTML comments, keeping the comments inside fenced code."""
    parts = re.split(
        r'(^ {0,3}(?:`{3,}|~{3,}).*?^ {0,3}(?:`{3,}|~{3,})[^\n]*$)',
        text,
        flags=re.M | re.S,
    )
    return ''.join(
        part if index % 2 else COMMENT.sub('', part) for index, part in enumerate(parts)
    )


def _blocks(
    lines: list[str], context: _Context, *, prefix: list[Run], rest: list[Run]
) -> None:
    """
    Lay out the blocks of ``lines``.

    ``prefix`` starts the first line that is written (a list marker, a quote bar) and
    ``rest`` starts every line after it.
    """
    state = _Prefix(prefix, rest)
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        fence = FENCE.match(line)
        if fence is not None:
            index = _code_block(lines, index, fence, context, state)
            continue
        heading = HEADING.match(line)
        if heading is not None:
            _heading(heading['text'] or '', len(heading['marks']), context, state)
            index += 1
            continue
        if RULE.match(line):
            context.gap()
            inner = context.width - state.width()
            context.lines.append(
                line_of([*state.take(), Run('─' * max(inner, 1), dim=True)])
            )
            index += 1
            continue
        if QUOTE.match(line):
            index = _quote(lines, index, context, state)
            continue
        item = ITEM.match(line)
        if item and (item['text'] is not None or index + 1 < len(lines)):
            index = _list(lines, index, context, state)
            continue
        if (
            '|' in line
            and index + 1 < len(lines)
            and TABLE_DIVIDER.match(lines[index + 1])
        ):
            index = _table(lines, index, context, state)
            continue
        if HTML_BLOCK.match(line):
            index = _html_block(lines, index, context, state)
            continue
        index = _paragraph(lines, index, context, state)


class _Prefix:
    """The runs that start the lines of a block: one set for the first line, one for the rest."""

    def __init__(self, first: list[Run], rest: list[Run]) -> None:
        """Keep the two sets of runs."""
        self.first = first
        self.rest = rest
        self.is_first = True

    def take(self) -> list[Run]:
        """The runs for the next line: the first set once, then the other."""
        if self.is_first:
            self.is_first = False
            return list(self.first)
        return list(self.rest)

    def width(self) -> int:
        """The cells that the runs take."""
        return sum(display_width(run.text) for run in self.rest)


def _write(runs: list[Run], context: _Context, state: _Prefix, **options: object) -> None:
    """Wrap ``runs`` to the width that is left and add the lines, each with its prefix."""
    inner = max(context.width - state.width(), 4)
    for index, wrapped in enumerate(wrap_runs(runs, inner)):
        line = line_of([*state.take(), *wrapped])
        if index == 0:
            for name, value in options.items():
                setattr(line, name, value)
        context.lines.append(line)


def _heading(text: str, level: int, context: _Context, state: _Prefix) -> None:
    """A heading: bold, with a rule under the first two levels."""
    context.gap()
    runs = [
        dataclasses.replace(run, bold=True, role=run.role or 'heading')
        for run in _inline(text.strip(), context)
    ]
    plain = ''.join(run.text for run in runs)
    _write(runs, context, state, heading=(level, plain))
    if level <= 2:
        inner = max(context.width - state.width(), 4)
        mark = '━' if level == 1 else '─'
        context.lines.append(line_of([*state.take(), Run(mark * inner, dim=True)]))


def _paragraph(lines: list[str], index: int, context: _Context, state: _Prefix) -> int:
    """A paragraph, up to an empty line or the start of another block."""
    collected = [lines[index]]
    index += 1
    while index < len(lines):
        line = lines[index]
        setext = SETEXT.match(line)
        if setext is not None and collected:
            _heading(
                ' '.join(part.strip() for part in collected),
                1 if setext['mark'][0] == '=' else 2,
                context,
                state,
            )
            return index + 1
        if (
            not line.strip()
            or FENCE.match(line)
            or HEADING.match(line)
            or RULE.match(line)
            or QUOTE.match(line)
            or ((item := ITEM.match(line)) and item['text'] is not None)
            or HTML_BLOCK.match(line)
        ):
            break
        collected.append(line)
        index += 1
    text = '\n'.join(
        part.strip() + ('  ' if part.endswith(('  ', '\\')) else '') for part in collected
    )
    text = re.sub(r'(?:  |\\)\n', '\0', text).replace('\n', ' ').replace('\0', '\n')
    _flow(text, context, state)
    return index


def _flow(text: str, context: _Context, state: _Prefix) -> None:
    """A run of inline text: its images on rows of their own, the rest as wrapped lines."""
    runs = _inline(text, context)
    images = [run for run in runs if run.image_source is not None]
    is_only_images = (
        images
        and not ''.join(run.text for run in runs if run.image_source is None).strip()
    )
    context.gap()
    if is_only_images:
        for run in images:
            _image(run.image_source or '', run.text, context, state)
        return
    _write([_image_as_text(run) for run in runs], context, state)


def _image_as_text(run: Run) -> Run:
    """An image inside a sentence, as its description in brackets."""
    if run.image_source is None:
        return run
    label = run.text or run.image_source
    if run.target is not None:
        return dataclasses.replace(run, text=label, image_source=None)
    return dataclasses.replace(run, text=f'[image: {label}]', dim=True, image_source=None)


def _image(source: str, description: str, context: _Context, state: _Prefix) -> None:
    """An image on rows of its own, or its description when it cannot be shown."""
    inner = max(context.width - state.width(), 4)
    path = image_file(source, context.directory)
    pixels = None if path is None else pixel_size(path)
    if path is None or pixels is None:
        _write([Run(f'[image: {description or source}]', dim=True)], context, state)
        return
    columns, rows = cells_for(pixels, inner)
    _place(path, columns, rows, description or source, context, state)


def _place(
    content: object,
    columns: int,
    rows: int,
    description: str,
    context: _Context,
    state: _Prefix,
) -> None:
    """Keep ``rows`` lines for content that is written over them: an image or a table."""
    first = state.take()
    lines = content_lines(
        content,
        columns=columns,
        rows=rows,
        column=state.width(),
        description=description,
        prefix=state.rest,
    )
    lines[0].spans = [run for run in first if run.text]
    context.lines.extend(lines)


def _code_block(
    lines: list[str], index: int, fence: re.Match[str], context: _Context, state: _Prefix
) -> int:
    """A fenced block of code: its lines as they are, behind a bar, never joined."""
    mark, indent = fence['fence'], len(fence['indent'])
    index += 1
    body: list[str] = []
    while index < len(lines):
        closing = FENCE.match(lines[index])
        if (
            closing is not None
            and closing['fence'][0] == mark[0]
            and len(closing['fence']) >= len(mark)
            and not closing['language']
        ):
            index += 1
            break
        body.append(
            lines[index][indent:] if lines[index][:indent].isspace() else lines[index]
        )
        index += 1
    context.gap()
    bar = Run('│ ', dim=True)
    inner = max(context.width - state.width() - 2, 4)
    if fence['language']:
        context.lines.append(
            line_of([*state.take(), bar, Run(fence['language'], dim=True)])
        )
    for text in body or ['']:
        for wrapped in wrap_runs([Run(text, code=True)], inner, keeps_spaces=True):
            context.lines.append(line_of([*state.take(), bar, *wrapped]))
    return index


def _quote(lines: list[str], index: int, context: _Context, state: _Prefix) -> int:
    """A quote: the blocks inside it behind a bar."""
    body: list[str] = []
    while index < len(lines):
        match = QUOTE.match(lines[index])
        if match is None:
            if not lines[index].strip() or not body or not body[-1].strip():
                break
            body.append(lines[index])  # a lazy line continues the paragraph of the quote
        else:
            body.append(match['text'])
        index += 1
    context.gap()
    bar = Run('▌ ', dim=True)
    _blocks(body, context, prefix=[*state.take(), bar], rest=[*state.rest, bar])
    return index


def _list(lines: list[str], index: int, context: _Context, state: _Prefix) -> int:
    """A list: each item behind its marker, with the blocks inside it indented."""
    first = ITEM.match(lines[index])
    assert first is not None
    base = len(first['indent'])
    is_ordered = first['marker'][0].isdigit()
    number = int(first['marker'][:-1]) if is_ordered else 0
    if not state.rest or state.is_first:
        context.gap()  # a list inside an item follows the text of the item directly
    while index < len(lines):
        match = ITEM.match(lines[index])
        if match is None or len(match['indent']) != base:
            break
        if match['marker'][0].isdigit() != is_ordered:
            break
        content_indent = len(match['indent']) + len(match['marker']) + 1
        body = [match['text'] or '']
        index += 1
        while index < len(lines):
            line = lines[index]
            if not line.strip():
                following = next(
                    (other for other in lines[index + 1 :] if other.strip()), None
                )
                if (
                    following is None
                    or len(following) - len(following.lstrip()) < content_indent
                ):
                    break
                body.append('')
                index += 1
                continue
            indent = len(line) - len(line.lstrip())
            if indent >= content_indent:
                body.append(line[content_indent:])
            elif ITEM.match(line) and indent > base:
                body.append(line[min(indent, base + 2) :])
            elif (
                ITEM.match(line)
                or indent < content_indent
                and (HEADING.match(line) or FENCE.match(line) or RULE.match(line))
            ):
                break
            else:
                body.append(line.strip())  # a lazy line continues the item
            index += 1
        marker = f'{number}. ' if is_ordered else '• '
        task = TASK.match(body[0])
        if task is not None:
            marker = '[x] ' if task['mark'] != ' ' else '[ ] '
            body[0] = task['text']
        number += 1
        gap = Run(' ' * display_width(marker))
        before = len(context.lines)
        _blocks(
            body,
            context,
            prefix=[*state.take(), Run(marker, dim=not task or task['mark'] == ' ')],
            rest=[*state.rest, gap],
        )
        # Items sit on consecutive lines: only the blocks inside one item are spaced.
        if before < len(context.lines) and not context.lines[before].spans:
            del context.lines[before]
    return index


def _cells(line: str) -> list[str]:
    """The cells of one row of a table."""
    text = line.strip()
    if text.startswith('|'):
        text = text[1:]
    if text.endswith('|') and not text.endswith('\\|'):
        text = text[:-1]
    return [cell.strip().replace('\\|', '|') for cell in re.split(r'(?<!\\)\|', text)]


def _table(lines: list[str], index: int, context: _Context, state: _Prefix) -> int:
    """A table, as a [`Table`][xnano.widgets.Table] with its text wrapped inside its columns."""
    from xnano_core import Block, Table, TableRow

    theme = context.theme

    header = _cells(lines[index])
    alignments = [
        'center'
        if cell.startswith(':') and cell.endswith(':')
        else 'right'
        if cell.endswith(':')
        else 'left'
        for cell in _cells(lines[index + 1])
    ]
    index += 2
    rows: list[list[str]] = []
    while index < len(lines) and lines[index].strip() and '|' in lines[index]:
        rows.append(_cells(lines[index]))
        index += 1
    count = len(header)
    alignments = (alignments + ['left'] * count)[:count]
    cells = [
        [_inline(cell, context) for cell in (row + [''] * count)[:count]]
        for row in [header, *rows]
    ]
    widths = [
        max(
            max(
                (
                    display_width(''.join(run.text for run in row[column]))
                    for row in cells
                ),
                default=1,
            ),
            1,
        )
        for column in range(count)
    ]
    # A column is as wide as its text, or narrower when the table must fit: the widest
    # column gives way first, and its text is wrapped.
    available = max(context.width - state.width() - 2 - 2 * (count - 1), count * 3)
    while sum(widths) > available:
        widest = max(range(count), key=lambda column: widths[column])
        if widths[widest] <= 3:
            break
        widths[widest] -= 1
    table_rows: list[TableRow] = []
    height = 2
    for row_index, row in enumerate(cells):
        wrapped = [wrap_runs(cell, widths[column]) for column, cell in enumerate(row)]
        row_height = max(len(cell) for cell in wrapped)
        height += row_height
        table_rows.append(
            TableRow(
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
                height=row_height,
                style=theme.style(role='heading', bold=True) if row_index == 0 else None,
            )
        )
    table = Table(
        table_rows[1:],
        header=table_rows[0],
        widths=widths,
        column_spacing=2,
        style=theme.style(),
        block=Block(border_type='rounded', border_style=theme.style(role='border')),
    )
    context.gap()
    description = ' '.join(' '.join(row) for row in [header, *rows])
    _place(table, sum(widths) + 2 * (count - 1) + 2, height, description, context, state)
    return index


def _html_block(lines: list[str], index: int, context: _Context, state: _Prefix) -> int:
    """A block of HTML: its images, and the text between its tags."""
    body: list[str] = []
    while index < len(lines) and lines[index].strip():
        body.append(lines[index])
        index += 1
    html = '\n'.join(body)
    for tag in HTML_IMAGE.findall(html):
        attributes = {
            match['name'].lower(): match['value']
            for match in HTML_ATTRIBUTE.finditer(tag)
        }
        if attributes.get('src'):
            context.gap()
            _image(attributes['src'], attributes.get('alt', ''), context, state)
    text = ' '.join(HTML_TAG.sub(' ', html).split())
    if text:
        _flow(text, context, state)
    return index


def _inline(text: str, context: _Context) -> list[Run]:
    """The runs of a piece of inline Markdown."""
    runs: list[Run] = []
    position = 0
    for match in INLINE.finditer(text):
        if match.start() > position:
            runs.append(Run(text[position : match.start()]))
        position = match.end()
        kind = _kind_of(match)
        if kind == 'escape':
            runs.append(Run(match['escape'][1]))
        elif kind == 'code':
            runs.append(Run(match['code_text'].strip() or match['code_text'], code=True))
        elif kind == 'image':
            source = match['source'].strip('<>')
            runs.append(Run(match['alt'], image_source=source))
        elif kind == 'link':
            runs.extend(_linked(match['label'], match['target'].strip('<>'), context))
        elif kind == 'reference':
            name = (match['reference_name'] or match['reference_label']).lower()
            target = context.references.get(name)
            if target is None:
                runs.append(Run(match['reference']))
            else:
                runs.extend(_linked(match['reference_label'], target, context))
        elif kind == 'autolink':
            runs.append(Run(match['address'], target=match['address']))
        elif kind == 'break':
            runs.append(Run('\n'))
        elif kind == 'strong':
            inner = match['strong_star'] or match['strong_under']
            runs.extend(
                dataclasses.replace(run, bold=True) for run in _inline(inner, context)
            )
        elif kind == 'strike':
            runs.extend(
                dataclasses.replace(run, strike=True)
                for run in _inline(match['strike_text'], context)
            )
        elif kind == 'emphasis':
            inner = match['star_text'] or match['under_text']
            runs.extend(
                dataclasses.replace(run, italic=True) for run in _inline(inner, context)
            )
        # An HTML tag inside a sentence is left out.
    if position < len(text):
        runs.append(Run(text[position:]))
    return [run for run in runs if run.text or run.image_source is not None]


_INLINE_KINDS = (
    'escape',
    'code',
    'image',
    'link',
    'reference',
    'autolink',
    'break',
    'html',
    'strong',
    'strike',
    'emphasis',
)


def _kind_of(match: re.Match[str]) -> str:
    """The kind of inline text that a match found, by its outer group."""
    return next(kind for kind in _INLINE_KINDS if match[kind] is not None)


def _linked(label: str, target: str, context: _Context) -> list[Run]:
    """The runs of a link: its label, underlined, with the place that it leads to."""
    return [
        _image_as_text(dataclasses.replace(run, target=target))
        for run in _inline(label, context)
    ] or [Run(target, target=target)]
