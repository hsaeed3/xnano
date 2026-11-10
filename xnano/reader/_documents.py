"""
xnano.reader._documents

A file, read as the kind of document that it is, and laid out as lines.

The kind comes from the name of the file and, when the name does not say, from its content.
Markdown is laid out, JSON is indented and colored, comma or tab separated values become a
table, a PDF gives its text, and any other text is shown as it is with line numbers.
An image and a sound are not lines: the viewer shows and plays them itself.
"""

from __future__ import annotations

import csv
import dataclasses
import importlib.util
import io
import json
import pathlib
import re
from typing import Literal

from xnano.reader._lines import Line, Run, line_of, wrap_runs
from xnano.reader._markdown import layout_markdown
from xnano.themes import Theme
from xnano_core import display_width

__all__ = [
    'Document',
    'DocumentKind',
    'audio_lines',
    'load_audio_of',
    'read_document',
    'table_of',
]

DocumentKind = Literal[
    'markdown', 'text', 'json', 'table', 'pdf', 'image', 'audio', 'bytes'
]
KINDS: dict[str, DocumentKind] = {
    **dict.fromkeys(('.md', '.markdown', '.mdown', '.mkd'), 'markdown'),
    **dict.fromkeys(('.json', '.jsonl', '.ndjson', '.geojson', '.ipynb'), 'json'),
    **dict.fromkeys(('.csv', '.tsv'), 'table'),
    '.pdf': 'pdf',
    **dict.fromkeys(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.xni'), 'image'),
    **dict.fromkeys(('.wav', '.mp3', '.flac', '.ogg', '.oga', '.m4a', '.aac'), 'audio'),
}
SIGNATURES: tuple[tuple[bytes, DocumentKind], ...] = (
    (b'%PDF-', 'pdf'),
    (b'\x89PNG\r\n\x1a\n', 'image'),
    (b'\xff\xd8\xff', 'image'),
    (b'GIF8', 'image'),
    (b'RIFF', 'audio'),
    (b'fLaC', 'audio'),
    (b'OggS', 'audio'),
    (b'ID3', 'audio'),
)
JSON_TOKEN = re.compile(
    r'(?P<key>"(?:[^"\\]|\\.)*"(?=\s*:))|(?P<string>"(?:[^"\\]|\\.)*")'
    r'|(?P<number>-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)|(?P<word>\btrue\b|\bfalse\b|\bnull\b)'
)
MAXIMUM_COLUMN = 40
BYTES_PER_ROW = 16


@dataclasses.dataclass
class Document:
    """
    A file that the reader shows.

    Attributes:
        path: The file.
        kind: What kind of document the file is.
        text: The text of the file, or nothing for an image, a sound and other bytes.
        data: The bytes of a file that is not text.
        note: Something that the reader must tell the person about the file, or nothing.
    """

    path: pathlib.Path
    kind: DocumentKind
    text: str = ''
    data: bytes = b''
    note: str = ''

    @property
    def has_source(self) -> bool:
        """Whether the document has a source to show besides its laid out form."""
        return self.kind in ('markdown', 'json', 'table')

    def lines(self, width: int, theme: Theme, *, is_source: bool = False) -> list[Line]:
        """
        The document as lines no wider than ``width`` cells.

        Args:
            width: The width of the lines, in cells.
            theme: The theme that the tables of the document are drawn in.
            is_source: Whether to give the text of the file as it is, with line numbers,
                and not its laid out form.

        Returns:
            The lines, in order.
        """
        if self.kind == 'bytes':
            return _bytes_lines(self.data, width)
        if is_source or self.kind in ('text', 'pdf'):
            return _text_lines(self.text, width, has_numbers=self.kind != 'pdf')
        if self.kind == 'markdown':
            return layout_markdown(
                self.text, width=width, directory=self.path.parent, theme=theme
            )
        if self.kind == 'json':
            return _json_lines(self.text, width)
        if self.kind == 'table':
            return _text_lines(self.text, width, has_numbers=True)
        return []


def read_document(file: str | pathlib.Path) -> Document:
    """
    Read a file as the kind of document that it is.

    Args:
        file: The path of the file.

    Returns:
        The document.

    Raises:
        FileNotFoundError: No file exists at the path.
        IsADirectoryError: The path is a directory.
        ImportError: The file is a PDF and ``pypdf`` is not installed.
    """
    path = pathlib.Path(file).expanduser()
    if path.is_dir():
        raise IsADirectoryError(
            f'{path} is a directory, and the reader shows one file. Give the path of a '
            f'file inside it, for example: xnano {path / "README.md"}'
        )
    if not path.exists():
        raise FileNotFoundError(
            f'There is no file at {path}. Check the path, and give it again.'
        )
    data = path.read_bytes()
    kind: DocumentKind | None = KINDS.get(path.suffix.lower())
    if kind is None:
        kind = next((kind for mark, kind in SIGNATURES if data.startswith(mark)), None)
    if kind in ('image', 'audio'):
        return Document(path, kind, data=data)
    if kind == 'pdf':
        return Document(path, 'pdf', text=_pdf_text(path))
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = None
    if text is None or '\x00' in text:
        return Document(path, 'bytes', data=data)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    if kind == 'json' or (kind is None and text.lstrip()[:1] in ('{', '[')):
        try:
            _parse_json(text)
        except ValueError as error:
            if kind == 'json':
                return Document(path, 'text', text=text, note=f'not valid JSON: {error}')
            kind = None
        else:
            kind = 'json'
    shown: DocumentKind = kind or 'text'
    return Document(path, shown, text=text)


def _pdf_text(path: pathlib.Path) -> str:
    """The text of the pages of a PDF, with a line that names each page."""
    if importlib.util.find_spec('pypdf') is None:
        raise ImportError(
            f'{path.name} is a PDF, and reading a PDF needs the optional package pypdf. '
            f'Install it with: pip install "xnano[pdf]"'
        )
    import pypdf

    pages = pypdf.PdfReader(path).pages
    parts: list[str] = []
    for number, page in enumerate(pages, 1):
        parts.append(f'── page {number} of {len(pages)} ──')
        parts.append((page.extract_text() or '').strip() or '(this page has no text)')
        parts.append('')
    return '\n'.join(parts).rstrip('\n')


def _text_lines(text: str, width: int, *, has_numbers: bool) -> list[Line]:
    """The lines of plain text, wrapped, each behind the number of its line in the file."""
    source = text.expandtabs(4).split('\n')
    if source and not source[-1]:
        source.pop()
    digits = len(str(max(len(source), 1)))
    gutter = digits + 1 if has_numbers else 0
    inner = max(width - gutter, 8)
    lines: list[Line] = []
    for number, content in enumerate(source, 1):
        for index, wrapped in enumerate(
            wrap_runs([Run(content)], inner, keeps_spaces=True)
        ):
            runs = list(wrapped)
            if has_numbers:
                mark = str(number).rjust(digits) if index == 0 else ' ' * digits
                runs.insert(0, Run(f'{mark} ', dim=True))
            line = line_of(runs)
            line.number = number
            lines.append(line)
    return lines


def _parse_json(text: str) -> list[object]:
    """The values of JSON text: one, or one on each line of a file of JSON lines."""
    try:
        return [json.loads(text)]
    except ValueError:
        rows = [row for row in text.split('\n') if row.strip()]
        if len(rows) < 2:
            raise
        return [json.loads(row) for row in rows]


def _json_lines(text: str, width: int) -> list[Line]:
    """JSON with two spaces for each level, and a color for each kind of value."""
    lines: list[Line] = []
    for value in _parse_json(text):
        shown = json.dumps(value, indent=2, ensure_ascii=False)
        for content in shown.split('\n'):
            runs: list[Run] = []
            position = 0
            for match in JSON_TOKEN.finditer(content):
                if match.start() > position:
                    runs.append(Run(content[position : match.start()], dim=True))
                position = match.end()
                kind = match.lastgroup
                if kind == 'key':
                    runs.append(Run(match[0], bold=True))
                elif kind == 'string':
                    runs.append(Run(match[0], role='string'))
                elif kind == 'number':
                    runs.append(Run(match[0], role='number'))
                else:
                    runs.append(Run(match[0], role='keyword'))
            if position < len(content):
                runs.append(Run(content[position:], dim=True))
            indent = len(content) - len(content.lstrip())
            # A long value goes on under itself, two cells in from where its line starts.
            hang = indent + 2 if indent + 10 < width else 0
            for index, wrapped in enumerate(
                wrap_runs(runs, max(width - hang, 8), keeps_spaces=True)
            ):
                if index:
                    wrapped = [Run(' ' * hang), *wrapped]
                lines.append(line_of(wrapped))
    return lines


def table_of(document: Document, width: int, theme: Theme) -> tuple[object, list[Line]]:
    """
    Comma or tab separated values as a [`Table`][xnano.widgets.Table].

    The first row of the file is the header of the table, which stays in view while the
    rows scroll. A column is as wide as its values, up to a limit, and narrower when the
    table must fit in ``width`` cells. Columns of numbers are aligned to the right.

    Args:
        document: A document of the kind ``'table'``.
        width: The width that the table must fit in, in cells.
        theme: The theme that the table is drawn in.

    Returns:
        The table, and one line for each of its rows below the header, which hold the text
        that the search reads.
    """
    from xnano_core import Table, TableRow

    delimiter = '\t' if document.path.suffix.lower() == '.tsv' else ','
    rows = [
        row for row in csv.reader(io.StringIO(document.text), delimiter=delimiter) if row
    ]
    if not rows:
        rows = [['']]
    count = max(len(row) for row in rows)
    rows = [[*row, *([''] * (count - len(row)))] for row in rows]
    widths = [
        min(max(max(display_width(row[column]) for row in rows), 1), MAXIMUM_COLUMN)
        for column in range(count)
    ]
    available = max(width - 2 * (count - 1), count * 3)
    while sum(widths) > available:
        widest = max(range(count), key=lambda column: widths[column])
        if widths[widest] <= 3:
            break
        widths[widest] -= 1
    is_number = [
        len(rows) > 1
        and all(
            re.fullmatch(r'-?[\d.,]+%?', row[column].strip() or '0') for row in rows[1:]
        )
        for column in range(count)
    ]

    def cells(row: list[str], is_header: bool) -> list[str]:
        shown: list[str] = []
        for column, value in enumerate(row):
            while display_width(value) > widths[column]:
                value = value[:-2] + '…'
            space = ' ' * (widths[column] - display_width(value))
            shown.append(space + value if is_number[column] and not is_header else value)
        return shown

    table = Table(
        [cells(row, False) for row in rows[1:]],
        header=TableRow(
            cells(rows[0], True),
            style=theme.style(role='heading', bold=True, underline=True),
        ),
        widths=widths,
        column_spacing=2,
        style=theme.style(),
        row_highlight_style=theme.style(reverse=True),
    )
    lines: list[Line] = []
    for number, row in enumerate(rows[1:], 2):
        line = Line(description=' '.join(row), content=table)
        line.number = number
        lines.append(line)
    return table, lines


def _bytes_lines(data: bytes, width: int) -> list[Line]:
    """Bytes that are not text: their place in the file, their values and their characters."""
    lines: list[Line] = []
    per_row = BYTES_PER_ROW if width >= 76 else 8
    for offset in range(0, min(len(data), 65536), per_row):
        chunk = data[offset : offset + per_row]
        values = ' '.join(f'{byte:02x}' for byte in chunk).ljust(per_row * 3 - 1)
        characters = ''.join(chr(byte) if 32 <= byte < 127 else '·' for byte in chunk)
        lines.append(
            line_of(
                [
                    Run(f'{offset:08x}  ', dim=True),
                    Run(values),
                    Run('  '),
                    Run(characters, role='accent'),
                ]
            )
        )
    if len(data) > 65536:
        lines.append(line_of([Run(f'… {len(data) - 65536} more bytes', dim=True)]))
    return lines


def load_audio_of(document: Document) -> object | None:
    """
    The sound of a document of the kind ``'audio'``.

    Returns:
        The [`Audio`][xnano.Audio], or ``None`` when ``xnano[audio]`` is not installed or
        the file cannot be decoded. The reader then names the sound in text.
    """
    from xnano._internal._optional import is_installed

    if not is_installed('audio'):
        return None
    from xnano.audio import load_audio

    try:
        return load_audio(document.path)
    except (OSError, ValueError):
        return None


def audio_lines(document: Document, audio: object | None) -> list[Line]:
    """The lines that say what a sound file holds, or why it cannot be played."""
    from xnano._internal._optional import is_installed

    lines = [line_of([Run(document.path.name, bold=True)]), Line()]
    if audio is None:
        reason = (
            'This file cannot be played.'
            if is_installed('audio')
            else 'Sound needs an extra: pip install "xnano[audio]"'
        )
        lines.append(line_of([Run(reason)]))
        return lines
    seconds = int(audio.duration_milliseconds / 1000)  # type: ignore[attr-defined]
    rate = audio.sample_rate  # type: ignore[attr-defined]
    lines.append(
        line_of([Run('length  ', dim=True), Run(f'{seconds // 60}:{seconds % 60:02d}')])
    )
    lines.append(line_of([Run('rate    ', dim=True), Run(f'{rate} samples a second')]))
    return lines
