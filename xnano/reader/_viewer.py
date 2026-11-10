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
import pathlib
import re
import threading
from collections.abc import Callable, Generator
from typing import TYPE_CHECKING

import xnano
from xnano._internal._optional import is_installed
from xnano.expressions import ParentHeight
from xnano.reader._documents import (
    Document,
    audio_lines,
    load_audio_of,
    read_document,
    table_of,
)
from xnano.reader._images import ADDRESS, cells_for, load_image_in_cells, pixel_size
from xnano.reader._lines import Line, Run, content_lines, line_of, styled
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

WHEEL_LINES = 3


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
            viewer.stop_audio()


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
        self.listen()
        self.show_document()

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
            self.lines = self.image_lines()
        elif document.kind == 'audio':
            self.lines = self.audio_document_lines()
        else:
            self.lines = document.lines(self.width, self.theme, is_source=self.is_source)
        self.headings = [
            (index, *line.heading)
            for index, line in enumerate(self.lines)
            if line.heading
        ]
        self.find(self.query)
        self.hear_body()
        self.build_keys()
        self.scroll_to(self.top)

    def close_body(self) -> None:
        """Take the document off the window, with what was written over its lines."""
        if self.body_placement is not None:
            self.body_placement.remove()
        if self.body is not None:
            self.body.close()
        self.written = {}
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
        assert self.body is not None
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
                    content = self.image(content, columns, height)
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

    def image(self, path: pathlib.Path, columns: int, rows: int) -> object | None:
        """
        The image of ``path``, or ``None`` while it loads or when it cannot be read.

        An image is decoded on another thread the first time that it comes into view, so a
        large image never stops the scrolling. The window is drawn again when it is ready.
        """
        with self.images_lock:
            if path in self.images:
                return self.images[path]
            if path in self.is_loading:
                return None
            self.is_loading.add(path)
        is_still = self.document.kind != 'image'

        def load() -> None:
            image = load_image_in_cells(path, columns, rows, is_still=is_still)
            with self.images_lock:
                self.images[path] = image
                self.is_loading.discard(path)

        threading.Thread(target=load, name='xnano-reader-image', daemon=True).start()
        return None

    # -- an image and a sound, which are not lines ----------------------------------------

    def image_lines(self) -> list[Line]:
        """An image file as large as the window allows, in the middle of it."""
        document = self.document
        pixels = pixel_size(document.path) if is_installed('image') else None
        if pixels is None:
            words = (
                'This file is not an image that xnano can read.'
                if is_installed('image')
                else 'Images need an extra: pip install "xnano[image]"'
            )
            return [
                line_of([Run(document.path.name, bold=True)]),
                Line(),
                line_of([Run(words)]),
            ]
        columns, rows = cells_for(pixels, self.width, height=self.height)
        if not self.message:
            self.message = f'{pixels[0]} × {pixels[1]} pixels'
        return [Line() for _ in range((self.height - rows) // 2)] + content_lines(
            document.path,
            columns=columns,
            rows=rows,
            column=(self.width - columns) // 2,
            description=document.path.name,
        )

    def audio_document_lines(self) -> list[Line]:
        """What a sound file holds, and a gauge that follows how far it has played."""
        if self.audio is None:
            self.audio = load_audio_of(self.document)
        lines = audio_lines(self.document, self.audio)
        if self.audio is None:
            return lines
        if not self.terminal.speaker.is_available:
            lines.append(Line())
            lines.append(line_of([Run('× This computer has no sound output.')]))
            return lines
        self.gauge = LineGauge(
            0.0,
            label='■ 0:00',
            filled_style=self.theme.style(role='accent'),
            unfilled_style=self.theme.style(role='border'),
            style=self.theme.style(),
        )
        lines.append(Line())
        lines.extend(content_lines(self.gauge, columns=min(self.width - 2, 60), rows=1))
        return lines

    def toggle_audio(self) -> None:
        """Play the sound from its start, or stop it."""
        if self.audio is None or self.gauge is None:
            return
        if self.audio_started is not None:
            self.stop_audio()
        else:
            self.audio_handle = self.terminal.speaker.play(self.audio)  # type: ignore[arg-type]
            self.audio_started = self.terminal.clock.elapsed_seconds
        self.follow_audio()

    def stop_audio(self) -> None:
        """Stop the sound if it plays."""
        handle, self.audio_handle, self.audio_started = self.audio_handle, None, None
        if handle is not None:
            handle.remove()  # type: ignore[attr-defined]

    def follow_audio(self) -> None:
        """Move the gauge to where the sound is, and notice when it has ended."""
        if self.audio is None or self.gauge is None:
            return
        seconds = self.audio.duration_milliseconds / 1000  # type: ignore[attr-defined]
        played = 0.0
        if self.audio_started is not None:
            played = self.terminal.clock.elapsed_seconds - self.audio_started
            if played >= seconds:
                self.stop_audio()
                played = 0.0
        mark = '▶' if self.audio_started is not None else '■'
        self.gauge.ratio = min(played / seconds, 1.0) if seconds else 0.0
        self.gauge.label = f'{mark} {_minutes(played)} of {_minutes(seconds)}'

    # -- the line of keys ----------------------------------------------------------------

    def keys(self) -> list[_Key]:
        """The keys that the document in view has, the one that leaves last."""
        document = self.document
        keys: list[_Key] = []
        if document.kind == 'audio':
            if self.gauge is not None:
                keys.append(_Key('space', 'play or stop', self.toggle_audio))
        elif document.kind != 'image':
            keys.append(_Key('↑', 'up', lambda: self.scroll_to(self.top - 1)))
            keys.append(_Key('↓', 'down', lambda: self.scroll_to(self.top + 1)))
            keys.append(_Key('/', 'find', self.start_search))
            if self.query:
                keys.append(_Key('n', 'next', lambda: self.next_match(1)))
            if self.headings:
                keys.append(_Key('o', 'outline', self.toggle_outline))
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

    # -- the search ----------------------------------------------------------------------

    def start_search(self) -> None:
        """Start to take the keys as the text to find."""
        self.typed = ''
        self.close_outline()
        self.draw()

    def find(self, query: str) -> None:
        """Find the lines that hold ``query``, whatever its case."""
        self.query = query
        needle = query.lower()
        self.matches = [
            index
            for index, line in enumerate(self.lines)
            if needle and needle in line.text.lower()
        ]
        if self.table is not None:
            self.table.selected_row = None

    def finish_search(self) -> None:
        """Take the typed text as the search, and go to the first line that holds it."""
        typed, self.typed = self.typed or '', None
        self.find(typed)
        self.build_keys()
        if not typed:
            self.message = ''
            self.draw()
        elif not self.matches:
            self.message = f'"{typed}" is not in this document'
            self.draw()
        else:
            self.next_match(1, from_line=self.top - 1)

    def next_match(self, step: int, *, from_line: int | None = None) -> None:
        """Go to the next line that holds the search, or the one before, around the ends."""
        if not self.matches:
            return
        start = self.top if from_line is None else from_line
        if self.table is not None and isinstance(self.table.selected_row, int):
            start = self.table.selected_row
        if step > 0:
            target = next(
                (index for index in self.matches if index > start), self.matches[0]
            )
        else:
            target = next(
                (index for index in reversed(self.matches) if index < start),
                self.matches[-1],
            )
        number = self.matches.index(target) + 1
        self.message = f'"{self.query}" {number} of {len(self.matches)}'
        if self.table is not None:
            self.table.selected_row = target
        self.scroll_to(target)

    # -- the outline ---------------------------------------------------------------------

    def toggle_outline(self) -> None:
        """Open the list of headings, or close it."""
        if self.outline_choice is not None:
            self.close_outline()
            self.message = ''
            self.draw()
        elif self.headings:
            self.outline_choice = max(
                (
                    place
                    for place, entry in enumerate(self.headings)
                    if entry[0] <= self.top
                ),
                default=0,
            )
            self.draw_outline()

    def close_outline(self) -> None:
        """Close the list of headings."""
        self.outline_choice = None
        self.panel.is_visible = False

    def draw_outline(self) -> None:
        """Show the list of headings around the chosen one, on top of the document."""
        choice = self.outline_choice
        assert choice is not None
        rows = max(min(len(self.headings), self.height - 4), 1)
        width = max(min(self.width - 8, 56), 12)
        first = max(0, min(choice - rows // 2, len(self.headings) - rows))
        self.outline_first = first
        names: list[str] = []
        for _, level, text in self.headings[first : first + rows]:
            name = '  ' * (level - 1) + text
            while display_width(name) > width - 2:
                name = name[:-2] + '…'
            names.append(name)
        self.outline.clear()
        self.outline.extend(names)
        self.outline.selected = choice - first
        self.panel.width, self.panel.height = width + 2, rows + 2
        self.panel.is_visible = True
        self.message = '↑ ↓ choose · enter go · esc close'
        self.draw()

    def choose_heading(self, place: int) -> None:
        """Go to the heading at ``place`` of the list, and close the list."""
        if 0 <= place < len(self.headings):
            self.close_outline()
            self.message = ''
            self.scroll_to(self.headings[place][0])

    # -- the source, links and other files -------------------------------------------------

    def toggle_source(self) -> None:
        """Show the text of the file as it is, or its laid out form again."""
        if not self.document.has_source:
            return
        self.is_source = not self.is_source
        self.top = 0
        self.close_outline()
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
            path = self.document.path.parent / target.split('#', 1)[0]
            if path.is_file():
                self.open(path)
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
        self.stop_audio()
        self.history.append((self.document, self.top))
        self.document, self.top, self.is_source, self.audio = document, 0, False, None
        self.message, self.query = document.note, ''
        self.show_document()

    def go_back(self) -> None:
        """Show the file that a link was followed from."""
        if self.history:
            self.stop_audio()
            self.document, self.top = self.history.pop()
            self.is_source, self.audio, self.message, self.query = False, None, '', ''
            self.show_document()

    # -- the keys and the mouse ----------------------------------------------------------

    def listen(self) -> None:
        """Hear the keys, the wheel, the bar at the edge and a change of the window size."""
        terminal = self.terminal

        @terminal.hook(on='key')
        def press(context: Context) -> None:
            keyboard = context.keyboard
            self.key(keyboard.key, keyboard.text, keyboard.binding)

        @terminal.hook(on='scroll')
        def wheel(context: Context) -> None:
            if self.outline_choice is None:
                self.scroll_to(self.top + WHEEL_LINES * context.mouse.scroll.y)

        @terminal.hook(on='resize')
        def fit(context: Context) -> None:
            first = self.lines[self.top].number if self.top < len(self.lines) else None
            self.show_document()
            if first is not None:
                numbers = (line.number for line in self.lines)
                self.scroll_to(
                    next(
                        (
                            index
                            for index, number in enumerate(numbers)
                            if number == first
                        ),
                        0,
                    )
                )
            if self.outline_choice is not None:
                self.draw_outline()

        @terminal.hook(on='tick', every=0.1)
        def follow(context: Context) -> None:
            if self.audio_started is not None:
                self.follow_audio()
            with self.images_lock:
                is_waiting = bool(self.is_loading)
                has_new = any(
                    isinstance(line.content, pathlib.Path)
                    and line.content in self.images
                    and index - line.content_row not in self.written
                    for index, line in enumerate(
                        self.lines[self.top : self.top + self.rows], self.top
                    )
                    if line.content is not None
                    and self.images.get(line.content) is not None  # type: ignore[arg-type]
                )
            if has_new or is_waiting:
                self.draw()

        @self.bar.hook(on='drag')
        def drag_bar(context: Context) -> Generator[None, Context, None]:
            while context.mouse.is_down:
                position = context.mouse.position
                if position is not None:
                    share = (position.y - 1) / max(self.height - 1, 1)
                    total = max(len(self.lines) - self.rows, 0)
                    self.scroll_to(round(total * min(max(share, 0.0), 1.0)))
                context = yield

        @self.panel.hook(on='mouse')
        def pick(context: Context) -> None:
            position = context.mouse.position
            if context.mouse.kind == 'press' and position is not None:
                row = self.panel.local(position).y - 1
                self.choose_heading(self.outline_first + row)

    def hear_body(self) -> None:
        """Hear a click on a link of the document, and a drag that moves the document."""
        placement = self.body_placement
        assert placement is not None

        @placement.hook(on='drag')
        def drag(context: Context) -> Generator[None, Context, None]:
            start = context.mouse.position
            top = self.top
            has_moved = False
            while context.mouse.is_down:
                position = context.mouse.position
                if start is not None and position is not None and position.y != start.y:
                    has_moved = True
                    self.scroll_to(top - (position.y - start.y))
                context = yield
            if not has_moved and start is not None:
                self.click(start.x, start.y - 1)

    def click(self, column: int, row: int) -> None:
        """Follow the link under a click, if there is one."""
        index = self.top + row
        if self.outline_choice is not None or not 0 <= index < len(self.lines):
            return
        for start, end, target in self.lines[index].links:
            if start <= column < end:
                self.follow(target)
                return

    def key(self, key: str | None, text: str | None, binding: str | None) -> None:
        """Act on a key: as text for the search, in the list of headings, or on the document."""
        if self.typed is not None:
            self.search_key(key, text)
            return
        if self.outline_choice is not None:
            self.outline_key(key, text)
            return
        page = max(self.rows - 1, 1)
        is_audio = self.document.kind == 'audio'
        if key == 'q' or (key == 'escape' and not self.query):
            self.terminal.end_run()
        elif key == 'escape':
            self.find('')
            self.message = ''
            self.build_keys()
            self.draw()
        elif binding == 'ctrl+d':
            self.scroll_to(self.top + page // 2)
        elif binding == 'ctrl+u':
            self.scroll_to(self.top - page // 2)
        elif key == 'space' and is_audio:
            self.toggle_audio()
        elif key in ('down', 'enter') or text == 'j':
            self.scroll_to(self.top + 1)
        elif key == 'up' or text == 'k':
            self.scroll_to(self.top - 1)
        elif key in ('page_down', 'space') or text == 'f':
            self.scroll_to(self.top + page)
        elif key == 'page_up' or text == 'b':
            self.scroll_to(self.top - page)
        elif key == 'home' or text == 'g':
            self.scroll_to(0)
        elif key == 'end' or text == 'G':
            self.scroll_to(len(self.lines))
        elif text == '/':
            self.start_search()
        elif text == 'n':
            self.next_match(1)
        elif text == 'N':
            self.next_match(-1)
        elif text == 'o':
            self.toggle_outline()
        elif text == 'r':
            self.toggle_source()
        elif key == 'backspace':
            self.go_back()

    def search_key(self, key: str | None, text: str | None) -> None:
        """Take a key while the person types the text to find."""
        assert self.typed is not None
        if key == 'enter':
            self.finish_search()
            return
        if key == 'escape':
            self.typed = None
        elif key == 'backspace':
            self.typed = self.typed[:-1]
        elif text and text.isprintable():
            self.typed += text
        self.draw()

    def outline_key(self, key: str | None, text: str | None) -> None:
        """Take a key while the list of headings is open."""
        choice = self.outline_choice
        assert choice is not None
        if key == 'q':
            self.terminal.end_run()
        elif key == 'escape' or text == 'o':
            self.toggle_outline()
        elif key == 'enter':
            self.choose_heading(choice)
        elif key in ('up', 'down') or text in ('j', 'k'):
            step = 1 if key == 'down' or text == 'j' else -1
            self.outline_choice = (choice + step) % len(self.headings)
            self.draw_outline()


def _minutes(seconds: float) -> str:
    """Seconds as minutes and seconds, such as ``1:05``."""
    whole = int(seconds)
    return f'{whole // 60}:{whole % 60:02d}'


def _anchor(heading: str) -> str:
    """The name that a link uses for a heading: lowercase, with hyphens for spaces."""
    kept = re.sub(r'[^\w\- ]', '', heading.lower())
    return kept.strip().replace(' ', '-')
