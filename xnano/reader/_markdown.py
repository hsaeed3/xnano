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
from xnano.reader._inline import image_as_text, inline_runs
from xnano.reader._lines import (
    Line,
    Run,
    content_lines,
    line_of,
    wrap_runs,
)
from xnano.reader._tables import markdown_table
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
HTML_BLOCK = re.compile(r'^ {0,3}</?[A-Za-z][A-Za-z0-9-]*(?:\s[^>]*|/?)>')
HTML_TAG = re.compile(r'</?[A-Za-z][^>]*>')
HTML_IMAGE = re.compile(r'<img\b[^>]*>', re.IGNORECASE)
HTML_ATTRIBUTE = re.compile(r'(?P<name>[A-Za-z-]+)\s*=\s*"(?P<value>[^"]*)"')


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
    opening: str | None = None  # the fence that opened the code block the line is in
    for line in source:
        fence = FENCE.match(line)
        if fence is not None:
            if opening is None:
                opening = fence['fence']
            elif _closes(fence, opening):
                opening = None
        match = None if opening is not None else REFERENCE.match(line)
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
        for run in inline_runs(text.strip(), context.references)
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
        if _ends_paragraph(line):
            break
        collected.append(line)
        index += 1
    text = '\n'.join(
        part.strip().removesuffix('\\').rstrip() + '\0'
        if part.endswith(('  ', '\\'))
        else part.strip()
        for part in collected
    )
    text = text.replace('\0\n', '\0').replace('\n', ' ').replace('\0', '\n').rstrip('\n')
    _flow(text, context, state)
    return index


def _ends_paragraph(line: str) -> bool:
    """Whether ``line`` is empty or starts another block, so the paragraph ends before it."""
    if not line.strip():
        return True
    item = ITEM.match(line)
    if item is not None and item['text'] is not None:
        return True
    return any(
        pattern.match(line) for pattern in (FENCE, HEADING, RULE, QUOTE, HTML_BLOCK)
    )


def _flow(text: str, context: _Context, state: _Prefix) -> None:
    """A run of inline text: its images on rows of their own, the rest as wrapped lines."""
    runs = inline_runs(text, context.references)
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
    _write([image_as_text(run) for run in runs], context, state)


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


def _closes(fence: re.Match[str], opening: str) -> bool:
    """Whether ``fence`` ends the code block that the fence ``opening`` started."""
    return (
        fence['fence'][0] == opening[0]
        and len(fence['fence']) >= len(opening)
        and not fence['language']
    )


def _code_block(
    lines: list[str], index: int, fence: re.Match[str], context: _Context, state: _Prefix
) -> int:
    """A fenced block of code: its lines as they are, behind a bar, never joined."""
    mark, indent = fence['fence'], len(fence['indent'])
    index += 1
    body: list[str] = []
    while index < len(lines):
        closing = FENCE.match(lines[index])
        if closing is not None and _closes(closing, mark):
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
    if first is None:
        return index + 1
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
        body, index = _item_body(lines, index, match, base)
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


def _item_body(
    lines: list[str], index: int, match: re.Match[str], base: int
) -> tuple[list[str], int]:
    """The lines of the item that starts at ``index``, and the index of the line after it."""
    content_indent = len(match['indent']) + len(match['marker']) + 1
    body = [match['text'] or '']
    index += 1
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            if not _continues_after_gap(lines, index, content_indent):
                break
            body.append('')
            index += 1
            continue
        indent = len(line) - len(line.lstrip())
        if indent >= content_indent:
            body.append(line[content_indent:])
        elif ITEM.match(line) and indent > base:
            body.append(line[min(indent, base + 2) :])
        elif ITEM.match(line) or _starts_block(line):
            break
        else:
            body.append(line.strip())  # a lazy line continues the item
        index += 1
    return body, index


def _continues_after_gap(lines: list[str], index: int, content_indent: int) -> bool:
    """Whether the text after the empty line at ``index`` still belongs to the item."""
    following = next((other for other in lines[index + 1 :] if other.strip()), None)
    return (
        following is not None
        and len(following) - len(following.lstrip()) >= content_indent
    )


def _starts_block(line: str) -> bool:
    """Whether ``line`` starts a heading, a fence or a rule."""
    return bool(HEADING.match(line) or FENCE.match(line) or RULE.match(line))


def _table(lines: list[str], index: int, context: _Context, state: _Prefix) -> int:
    """A table, on rows of its own."""
    found = markdown_table(
        lines,
        index,
        references=context.references,
        theme=context.theme,
        available=context.width - state.width(),
    )
    context.gap()
    _place(found.table, found.width, found.height, found.description, context, state)
    return found.end


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
