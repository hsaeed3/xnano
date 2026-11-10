"""
xnano.reader

Read a file and show it: Markdown, text, JSON, tables, PDFs, images and sounds.

[`view`][xnano.reader.view] shows a file. On a terminal it opens a viewer that a person
scrolls, searches and clicks. Without a terminal (a pipe, a file, a test) it prints the
document. ``xnano FILE`` on the command line calls it.
[`from_markdown`][xnano.reader.from_markdown] lays Markdown out as styled text that any
canvas can write.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import sys
from typing import TextIO

from xnano._internal._optional import is_installed
from xnano.reader._documents import (
    Document,
    audio_lines,
    load_audio_of,
    read_document,
    table_of,
)
from xnano.reader._images import cells_for, load_image_in_cells, pixel_size
from xnano.reader._lines import Line, Run, content_lines, line_of, styled
from xnano.reader._markdown import layout_markdown
from xnano.themes import Theme, ThemeName, theme_of
from xnano_core import StyledText

__all__ = ['from_markdown', 'view']

DEFAULT_WIDTH = 80
MAXIMUM_PRINTED_WIDTH = 100
ROWS_PER_CANVAS = 200


def from_markdown(
    text: str, *, width: int = DEFAULT_WIDTH, theme: ThemeName | None = None
) -> StyledText:
    r"""
    Lay Markdown out as styled text, ready to write on a canvas.

    Headings, emphasis, code, links, lists, quotes, fenced code and tables keep their look.
    The text is wrapped at ``width`` cells. An image and a table are named in brackets: to
    show them, use [`view`][xnano.reader.view].

    Args:
        text: The Markdown source.
        width: The width to wrap the text at, in cells.
        theme: The colors of the text. By default the colors of the terminal. See
            [`ThemeName`][xnano.themes.ThemeName] for the themes and their authors.

    Returns:
        The styled text, with a newline between two lines.

    Raises:
        ValueError: No theme has the name in ``theme``.

    Examples:
        ```python
        import xnano

        text = xnano.from_markdown('# Notes\n\nA **bold** word and `code`.', width=30)
        assert str(text).splitlines()[0] == 'Notes'
        with xnano.new(width=30, height=4) as canvas:
            canvas.write(text)
            assert 'A bold word and code.' in canvas.render()
        ```
    """
    chosen = theme_of(theme)
    return styled(
        layout_markdown(text, width=width, theme=chosen, directory=None), chosen
    )


def view(
    file: str | os.PathLike[str],
    *,
    interactive: bool | None = None,
    width: int | None = None,
    theme: ThemeName | None = None,
    output: TextIO | None = None,
) -> None:
    r"""
    Show a file: in a viewer on a terminal, or printed when there is no terminal.

    The kind of file decides how it is shown. Markdown is laid out with its images, JSON is
    indented and colored, comma and tab separated values become a table, a PDF gives its
    text, an image is drawn, a sound is played, and any other text is shown with line
    numbers. Images need ``xnano[image]``, sounds need ``xnano[audio]`` and PDFs need
    ``xnano[pdf]``. An image or a sound that cannot be shown or played is named in text.

    In the viewer, the arrow keys, the wheel and a drag scroll, ``/`` finds text, ``o``
    lists the headings, ``r`` shows the source, a click follows a link, and ``q`` leaves.
    Every key on the last line of the window is also a button for the mouse.

    Args:
        file: The path of the file.
        interactive: Whether to open the viewer. By default the viewer opens when the
            program runs on a terminal, and the document is printed otherwise.
        width: The width of the printed document in cells. By default the width of the
            terminal, and 80 cells when there is none.
        theme: The colors of the document. By default the colors of the terminal. See
            [`ThemeName`][xnano.themes.ThemeName] for the themes and their authors.
        output: Where the document is printed. Standard output by default.

    Raises:
        FileNotFoundError: No file exists at the path.
        IsADirectoryError: The path is a directory.
        ImportError: The file is a PDF and ``pypdf`` is not installed.
        ValueError: No theme has the name in ``theme``.

    Examples:
        ```python
        import io
        import pathlib
        import tempfile

        import xnano

        with tempfile.TemporaryDirectory() as directory:
            notes = pathlib.Path(directory) / 'notes.md'
            notes.write_text('# Notes\n\n- one\n- two\n')
            printed = io.StringIO()
            xnano.view(notes, interactive=False, width=20, output=printed)
        assert printed.getvalue().splitlines()[0] == 'Notes'
        assert '• one' in printed.getvalue()
        ```
    """
    chosen = theme_of(theme)
    document = read_document(pathlib.Path(file))
    stream = sys.stdout if output is None else output
    if interactive is None:
        interactive = (
            output is None and _is_terminal(sys.stdout) and _is_terminal(sys.stdin)
        )
    if interactive:
        from xnano.reader._viewer import run_viewer

        run_viewer(document, chosen)
        return
    _print(document, stream, width, chosen)


def _is_terminal(stream: object) -> bool:
    """Whether ``stream`` is a terminal."""
    is_terminal = getattr(stream, 'isatty', None)
    try:
        return bool(is_terminal and is_terminal())
    except ValueError:
        return False


def _print(document: Document, stream: TextIO, width: int | None, theme: Theme) -> None:
    """Print ``document`` to ``stream``: with colors on a terminal, as plain text otherwise."""
    import xnano

    has_color = _is_terminal(stream) and not os.environ.get('NO_COLOR')
    if width is None:
        columns = shutil.get_terminal_size((DEFAULT_WIDTH, 24)).columns
        width = (
            min(columns, MAXIMUM_PRINTED_WIDTH) if _is_terminal(stream) else DEFAULT_WIDTH
        )
    width = max(width, 8)
    lines = _printed_lines(document, width, theme)
    if document.note:
        stream.write(f'{document.note}\n')
    format = 'ansi' if has_color else 'text'
    start = 0
    while start < len(lines):
        end = min(start + ROWS_PER_CANVAS, len(lines))
        while (
            end < len(lines) and lines[end].content is not None and lines[end].content_row
        ):
            end += 1  # an image or a table stays whole
        chunk = lines[start:end]
        with xnano.new(width=width, height=len(chunk)) as canvas:
            if theme.background is not None and theme.text is not None:
                canvas.screen.color.bg = theme.background
                canvas.screen.color.fg = theme.text
            canvas.write(styled(chunk, theme), x=0, y=0, width=width, height=len(chunk))
            for row, line in enumerate(chunk):
                if line.content is None or line.content_row:
                    continue
                columns, rows = line.content_size
                content = line.content
                if isinstance(content, pathlib.Path):
                    content = load_image_in_cells(content, columns, rows, is_still=True)
                if content is None:
                    canvas.write(
                        f'[image: {line.description}]',
                        x=line.content_column,
                        y=row,
                        style=theme.style(dim=True),
                    )
                    continue
                canvas.write(
                    content,  # type: ignore[arg-type]
                    x=line.content_column,
                    y=row,
                    width=columns,
                    height=rows,
                    layer=1,
                )
            rendered = canvas.render(format=format)
        for text in rendered.split('\n'):
            stream.write((text if has_color else text.rstrip()) + '\n')
        start = end
    stream.flush()


def _printed_lines(document: Document, width: int, theme: Theme) -> list[Line]:
    """The lines to print for ``document``: a table, an image and a sound included."""
    if document.kind == 'table':
        table, rows = table_of(document, width, theme)
        return content_lines(table, columns=width, rows=len(rows) + 1)
    if document.kind == 'image':
        pixels = pixel_size(document.path) if is_installed('image') else None
        if pixels is None:
            return [line_of([Run(f'[image: {document.path.name}]')])]
        columns, rows = cells_for(pixels, width, height=10_000)
        return content_lines(
            document.path, columns=columns, rows=rows, description=document.path.name
        )
    if document.kind == 'audio':
        return audio_lines(document, load_audio_of(document))
    return document.lines(width, theme)
