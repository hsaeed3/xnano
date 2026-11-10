"""
xnano.reader._viewer

The reader on a live terminal: a document that a person scrolls, searches and clicks.

The window has a title line, the document, a status line and a line of keys. Every key on
the last line is also a button for the mouse. The wheel scrolls, the
[`Scrollbar`][xnano.widgets.Scrollbar] at the right edge moves when it is dragged or
clicked, a drag on the document moves it, and a click on a link follows it.
"""

from __future__ import annotations

import dataclasses
import functools
import pathlib
import re
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

import xnano
from xnano.expressions import ParentHeight
from xnano.reader._documents import (
    Document,
    read_document,
    table_of,
)
from xnano.reader._images import ADDRESS
from xnano.reader._lines import Line, Run, line_of, styled
from xnano.reader._viewer_find import (
    close_outline,
    find_text,
    next_match,
    start_search,
    toggle_outline,
)
from xnano.reader._viewer_input import hear_body, listen
from xnano.reader._viewer_media import (
    audio_document_lines,
    image_lines,
    image_of,
    stop_audio,
    toggle_audio,
)
from xnano.themes import Theme
from xnano_core import (
    ItemList,
    LineGauge,
    Scrollbar,
    StyledText,
    Table,
    TextSpan,
    display_width,
)

if TYPE_CHECKING:
    from xnano.canvas import Canvas
    from xnano.hooks._context import Context
    from xnano.layout._placement import Placement
    from xnano.terminal import Terminal

__all__ = ['run_viewer']


@dataclasses.dataclass(frozen=True, slots=True)
class _Key:
    """One entry of the line of keys: what to press, what it does, and the action."""

    key: str
    label: str
    action: Callable[[], None]


def run_viewer(document: Document, theme: Theme) -> None:
    """
    Show ``document`` in the whole window until the person leaves.

    Args:
        document: The document to show first. A link to another file opens that file.
        theme: The colors of the viewer and of the document.
    """
    with xnano.open(
        mouse=True, scroll=True, title=document.path.name, state=None
    ) as terminal:
        viewer = _Viewer(terminal, document, theme)
        viewer.build()
        try:
            terminal.run()
        finally:
            stop_audio(viewer)


class _Viewer:
    """The state of the reader: the document, where it is scrolled to, and what is open."""

    def __init__(
        self, terminal: Terminal[None, None], document: Document, theme: Theme
    ) -> None:
        """Prepare the reader for ``document`` on ``terminal``, in the colors of ``theme``."""
        self.terminal = terminal
        self.theme = theme
        self.document = document
        self.history: list[tuple[Document, int]] = []
        self.lines: list[Line] = []
        self.top = 0
        self.is_source = False
        self.message = document.note
        self.query = ''
        self.typed: str | None = None
        self.matches: list[int] = []
        self.headings: list[tuple[int, int, str]] = []
        self.outline_choice: int | None = None
        self.outline_first = 0
        self.body: Canvas[None, None] | None = None
        self.body_placement: Placement[None, None] | None = None
        self.text: Placement[None, None] | None = None
        self.table: Table | None = None
        self.written: dict[int, Placement[None, None]] = {}
        self.images: dict[pathlib.Path, object | None] = {}
        self.images_lock = threading.Lock()
        self.is_loading: set[pathlib.Path] = set()
        self.image_generation = 0
        self.key_placements: list[Placement[None, None]] = []
        self.audio: object | None = None
        self.audio_handle: object | None = None
        self.audio_started: float | None = None
        self.gauge: LineGauge | None = None

    # -- the parts of the window --------------------------------------------------------

    @property
    def width(self) -> int:
        """The width of the document, in cells: the window without the bar at its edge."""
        return max(self.terminal.screen.width - 1, 8)

    @property
    def height(self) -> int:
        """The rows of the document: the window without its title, status and key lines."""
        return max(self.terminal.screen.height - 3, 1)

    @property
    def rows(self) -> int:
        """The lines in view at once. The header of a table takes one row of the window."""
        return max(self.height - 1, 1) if self.table is not None else self.height

    def build(self) -> None:
        """Write the parts of the window, and start hearing the keys and the mouse."""
        screen = self.terminal.screen
        theme = self.theme
        if theme.background is not None and theme.text is not None:
            screen.color.bg = theme.background
            screen.color.fg = theme.text
        secondary = theme.style(dim=True)
        self.title = screen.write(
            '',
            x=0,
            y=0,
            width='100%',
            style=theme.style(reverse=True)
            if theme.is_terminal
            else theme.style(bold=True, on_surface=True),
        )
        self.scrollbar = Scrollbar(
            1,
            0,
            viewport_content_length=1,
            orientation='vertical_right',
            thumb_symbol='█',
            track_symbol='│',
            has_begin=False,
            has_end=False,
            thumb_style=theme.style(role='accent'),
            track_style=theme.style(role='border'),
        )
        self.bar = screen.write(
            self.scrollbar, x='right', y=1, width=1, height=ParentHeight - 3, layer=1
        )
        self.status = screen.write('', x=1, y=ParentHeight - 2, style=secondary)
        self.place = screen.write('', x='right', y=ParentHeight - 2, style=secondary)
        self.build_outline()
        listen(self)
        self.show_document()

    def build_outline(self) -> None:
        """Write the list of headings, which stays hidden until it is asked for."""
        screen = self.terminal.screen
        theme = self.theme
        self.outline = ItemList(
            [],
            highlight_symbol='› ',
            highlight_style=theme.style(role='accent', bold=True, on_surface=True),
            style=theme.style(on_surface=True),
        )
        self.panel = screen.write(
            self.outline,
            x='center',
            y='center',
            layer=4,
            border='rounded',
            border_style=theme.style(role='border', on_surface=True),
            style=theme.style(on_surface=True),
            title='outline',
        )
        self.panel.is_visible = False

    def show_document(self) -> None:
        """Lay the document out for the size of the window, and draw everything."""
        terminal = self.terminal
        self.close_body()
        document = self.document
        self.body = xnano.new(width=self.width, height=self.height)
        theme = self.theme
        if theme.background is not None and theme.text is not None:
            self.body.screen.color.bg = theme.background
            self.body.screen.color.fg = theme.text
        self.body_placement = terminal.screen.write(self.body, x=0, y=1)
        self.text = self.body.write('', x=0, y=0, width=self.width, height=self.height)
        if document.kind == 'table' and not self.is_source:
            self.table, self.lines = table_of(document, self.width, self.theme)  # type: ignore[assignment]
            self.body.write(
                self.table, x=0, y=0, width=self.width, height=self.height, layer=1
            )
        elif document.kind == 'image':
            self.lines = image_lines(self)
        elif document.kind == 'audio':
            self.lines = audio_document_lines(self)
        else:
            self.lines = document.lines(self.width, self.theme, is_source=self.is_source)
        self.headings = [
            (index, *line.heading)
            for index, line in enumerate(self.lines)
            if line.heading
        ]
        find_text(self, self.query)
        hear_body(self)
        self.build_keys()
        self.scroll_to(self.top)

    def close_body(self) -> None:
        """Take the document off the window, with what was written over its lines."""
        if self.body_placement is not None:
            self.body_placement.remove()
        if self.body is not None:
            self.body.close()
        self.written = {}
        with self.images_lock:
            # The images are sized for the layout, so a new layout loads them again.
            self.images = {}
            self.is_loading = set()
            self.image_generation += 1
        self.body = self.body_placement = self.text = self.table = self.gauge = None

    # -- drawing -------------------------------------------------------------------------

    def scroll_to(self, top: int) -> None:
        """Show the document from line ``top``, kept inside the document."""
        self.top = max(0, min(top, len(self.lines) - self.rows))
        self.draw()

    def draw(self) -> None:
        """Draw the lines in view, what is written over them, the bar and the status."""
        if self.body is None or self.text is None:
            return
        top, rows, total = self.top, self.rows, len(self.lines)
        if self.table is not None:
            self.table.offset = top
        else:
            self.text.text = self.highlighted(self.lines[top : top + rows])
            self.draw_content()
        self.scrollbar.content_length = max(total - rows + 1, 1)
        self.scrollbar.viewport_content_length = rows
        self.scrollbar.content_position = top
        self.bar.is_visible = total > rows
        document = self.document
        name = f' {document.path.name} '
        kind = 'source' if self.is_source and document.has_source else document.kind
        space = max(self.terminal.screen.width - display_width(name), 0)
        self.title.text = name + f'{kind} '.rjust(space)
        if self.typed is not None:
            self.status.text = f'/{self.typed}▏'
        else:
            self.status.text = self.message[: max(self.terminal.screen.width - 26, 8)]
        if total > rows:
            share = round(100 * top / (total - rows))
            self.place.text = f'{top + 1}-{min(top + rows, total)} of {total} · {share}% '
        else:
            self.place.text = ''

    def highlighted(self, window: list[Line]) -> StyledText:
        """The lines in view as styled text, with what the search found in reverse video."""
        window = [self.standing_for(line) for line in window]
        if not self.query:
            return styled(window, self.theme)
        needle = re.escape(self.query.lower())
        theme = self.theme
        match = theme.style(reverse=True, bold=True)
        spans: list[TextSpan] = []
        for index, line in enumerate(window):
            if index:
                spans.append(TextSpan('\n'))
            text = ''.join(run.text for run in line.spans).lower()
            found = [match.span() for match in re.finditer(needle, text)]
            position = 0
            for run in line.spans:
                end = position + len(run.text)
                cut = position
                for start, stop in found:
                    if stop <= position or start >= end:
                        continue
                    start, stop = max(start, position), min(stop, end)
                    if start > cut:
                        part = run.text[cut - position : start - position]
                        spans.append(TextSpan(part, style=theme.style_of(run)))
                    spans.append(
                        TextSpan(
                            run.text[start - position : stop - position], style=match
                        )
                    )
                    cut = stop
                if cut < end:
                    spans.append(
                        TextSpan(run.text[cut - position :], style=theme.style_of(run))
                    )
                position = end
        return StyledText(spans or [TextSpan('')])

    def standing_for(self, line: Line) -> Line:
        """The line, or the words that stand for an image that is loading or cannot be read."""
        path = line.content
        if not isinstance(path, pathlib.Path) or line.content_row:
            return line
        with self.images_lock:
            is_known, image = path in self.images, self.images.get(path)
        if is_known and image is not None:
            return line
        words = f'[image: {line.description}]' if is_known else 'loading image…'
        return line_of([*line.spans, Run(words, dim=True)])

    def draw_content(self) -> None:
        """Put each image and table where its lines are, and hide the ones out of view."""
        if self.body is None:
            return
        top, rows = self.top, self.rows
        in_view: set[int] = set()
        for index in range(max(top - 256, 0), min(top + rows, len(self.lines))):
            line = self.lines[index]
            if line.content is None:
                continue
            start = index - line.content_row
            columns, height = line.content_size
            if start + height <= top or start in in_view:
                continue
            placement = self.written.get(start)
            if placement is None:
                content = line.content
                if isinstance(content, pathlib.Path):
                    content = image_of(self, content, columns, height)
                    if content is None:
                        continue
                placement = self.body.write(
                    content,  # type: ignore[arg-type]
                    x=line.content_column,
                    y=start - top,
                    width=columns,
                    height=height,
                    layer=1,
                )
                self.written[start] = placement
            in_view.add(start)
            placement.y = start - top
            placement.is_visible = True
        for start, placement in self.written.items():
            if start not in in_view:
                placement.is_visible = False

    # -- the line of keys ----------------------------------------------------------------

    def keys(self) -> list[_Key]:
        """The keys that the document in view has, the one that leaves last."""
        document = self.document
        keys: list[_Key] = []
        if document.kind == 'audio':
            if self.gauge is not None:
                keys.append(
                    _Key('space', 'play or stop', functools.partial(toggle_audio, self))
                )
        elif document.kind != 'image':
            keys.append(_Key('↑', 'up', lambda: self.scroll_to(self.top - 1)))
            keys.append(_Key('↓', 'down', lambda: self.scroll_to(self.top + 1)))
            keys.append(_Key('/', 'find', functools.partial(start_search, self)))
            if self.query:
                keys.append(_Key('n', 'next', lambda: next_match(self, 1)))
            if self.headings:
                keys.append(_Key('o', 'outline', functools.partial(toggle_outline, self)))
            if document.has_source:
                label = 'laid out' if self.is_source else 'source'
                keys.append(_Key('r', label, self.toggle_source))
        if self.history:
            keys.append(_Key('backspace', 'back', self.go_back))
        keys.append(_Key('q', 'quit', self.terminal.end_run))
        return keys

    def build_keys(self) -> None:
        """Write the line of keys: each key bold with its action, and a click runs the action."""
        for placement in self.key_placements:
            placement.remove()
        self.key_placements = []
        screen = self.terminal.screen
        keys = self.keys()

        def size(key: _Key) -> int:
            return display_width(f'{key.key} {key.label}')

        while len(keys) > 1 and sum(size(key) + 3 for key in keys) > screen.width:
            del keys[-2]  # the window is narrow: the key that leaves stays
        column = 1
        for index, key in enumerate(keys):
            text = StyledText(
                [
                    TextSpan(key.key, style=self.theme.style(bold=True)),
                    TextSpan(f' {key.label}', style=self.theme.style(dim=True)),
                ]
            )
            placement = screen.write(text, x=column, y='bottom')
            self.on_press(placement, key.action)
            self.key_placements.append(placement)
            column += size(key)
            if index < len(keys) - 1:
                self.key_placements.append(
                    screen.write(
                        ' · ', x=column, y='bottom', style=self.theme.style(dim=True)
                    )
                )
                column += 3

    def on_press(
        self, placement: Placement[None, None], action: Callable[[], None]
    ) -> None:
        """Run ``action`` when the mouse is pressed on ``placement``."""

        @placement.hook(on='mouse')
        def press(context: Context) -> None:
            if context.mouse.kind == 'press':
                action()

    # -- the outline ---------------------------------------------------------------------

    # -- the source, links and other files -------------------------------------------------

    def toggle_source(self) -> None:
        """Show the text of the file as it is, or its laid out form again."""
        if not self.document.has_source:
            return
        self.is_source = not self.is_source
        self.top = 0
        close_outline(self)
        self.show_document()

    def follow(self, target: str) -> None:
        """Follow a link: to a heading, to another file on this computer, or name the address."""
        if target.startswith('#'):
            wanted = target[1:].lower()
            for index, _, text in self.headings:
                if _anchor(text) == wanted:
                    self.message = ''
                    self.scroll_to(index)
                    return
            self.message = f'no heading is named {target}'
        elif ADDRESS.match(target):
            self.message = target
        else:
            name, _, heading = target.partition('#')
            path = self.document.path.parent / name
            if path.is_file():
                self.open(path)
                if heading:
                    self.follow(f'#{heading}')
                return
            self.message = f'{target} is not a file here'
        self.draw()

    def open(self, path: pathlib.Path) -> None:
        """Show another file, and remember this one to go back to."""
        try:
            document = read_document(path)
        except (OSError, ImportError) as error:
            self.message = str(error)
            self.draw()
            return
        stop_audio(self)
        self.history.append((self.document, self.top))
        self.document, self.top, self.is_source, self.audio = document, 0, False, None
        self.message, self.query = document.note, ''
        self.show_document()

    def go_back(self) -> None:
        """Show the file that a link was followed from."""
        if self.history:
            stop_audio(self)
            self.document, self.top = self.history.pop()
            self.is_source, self.audio, self.message, self.query = False, None, '', ''
            self.show_document()


def _anchor(heading: str) -> str:
    """The name that a link uses for a heading: lowercase, with hyphens for spaces."""
    kept = re.sub(r'[^\w\- ]', '', heading.lower())
    return kept.strip().replace(' ', '-')
