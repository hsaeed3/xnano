"""
xnano.reader._viewer_input

The keys and the mouse of the viewer: what each key does, and what a click and a drag do.
"""

from __future__ import annotations

import functools
import pathlib
from collections.abc import Callable, Generator
from typing import TYPE_CHECKING

from xnano.reader._viewer_find import (
    choose_heading,
    draw_outline,
    find_text,
    finish_search,
    next_match,
    start_search,
    toggle_outline,
)
from xnano.reader._viewer_media import follow_audio, toggle_audio

if TYPE_CHECKING:
    from xnano.hooks._context import Context
    from xnano.reader._viewer import _Viewer

WHEEL_LINES = 3


def listen(viewer: _Viewer) -> None:
    """Hear the keys, the wheel, the bar at the edge and a change of the window size."""
    terminal = viewer.terminal

    @terminal.hook(on='key')
    def press(context: Context) -> None:
        keyboard = context.keyboard
        press_key(viewer, keyboard.key, keyboard.text, keyboard.binding)

    @terminal.hook(on='scroll')
    def wheel(context: Context) -> None:
        if viewer.outline_choice is None:
            viewer.scroll_to(viewer.top + WHEEL_LINES * context.mouse.scroll.y)

    @terminal.hook(on='resize')
    def fit(context: Context) -> None:
        _lay_out_again(viewer)

    @terminal.hook(on='tick', every=0.1)
    def follow(context: Context) -> None:
        if viewer.audio_started is not None:
            follow_audio(viewer)
        if _has_images_to_draw(viewer):
            viewer.draw()

    @viewer.bar.hook(on='drag')
    def drag_bar(context: Context) -> Generator[None, Context, None]:
        while context.mouse.is_down:
            position = context.mouse.position
            if position is not None:
                share = (position.y - 1) / max(viewer.height - 1, 1)
                total = max(len(viewer.lines) - viewer.rows, 0)
                viewer.scroll_to(round(total * min(max(share, 0.0), 1.0)))
            context = yield

    @viewer.panel.hook(on='mouse')
    def pick(context: Context) -> None:
        position = context.mouse.position
        if context.mouse.kind == 'press' and position is not None:
            row = viewer.panel.local(position).y - 1
            choose_heading(viewer, viewer.outline_first + row)


def _lay_out_again(viewer: _Viewer) -> None:
    """Lay the document out for the new size of the window, at the line that was first."""
    first = viewer.lines[viewer.top].number if viewer.top < len(viewer.lines) else None
    viewer.show_document()
    if first is not None:
        numbers = (line.number for line in viewer.lines)
        viewer.scroll_to(
            next((index for index, number in enumerate(numbers) if number == first), 0)
        )
    if viewer.outline_choice is not None:
        draw_outline(viewer)


def _has_images_to_draw(viewer: _Viewer) -> bool:
    """Whether an image in view is loading, or is loaded and not written yet."""
    with viewer.images_lock:
        if viewer.is_loading:
            return True
        return any(
            isinstance(line.content, pathlib.Path)
            and line.content in viewer.images
            and index - line.content_row not in viewer.written
            for index, line in enumerate(
                viewer.lines[viewer.top : viewer.top + viewer.rows], viewer.top
            )
            if line.content is not None and viewer.images.get(line.content) is not None  # type: ignore[arg-type]
        )


def hear_body(viewer: _Viewer) -> None:
    """Hear a click on a link of the document, and a drag that moves the document."""
    placement = viewer.body_placement
    if placement is None:
        return

    @placement.hook(on='drag')
    def drag(context: Context) -> Generator[None, Context, None]:
        start = context.mouse.position
        top = viewer.top
        has_moved = False
        while context.mouse.is_down:
            position = context.mouse.position
            if start is not None and position is not None and position.y != start.y:
                has_moved = True
                viewer.scroll_to(top - (position.y - start.y))
            context = yield
        if not has_moved and start is not None:
            click(viewer, start.x, start.y - 1)


def click(viewer: _Viewer, column: int, row: int) -> None:
    """Follow the link under a click, if there is one."""
    index = viewer.top + row
    if viewer.outline_choice is not None or not 0 <= index < len(viewer.lines):
        return
    for start, end, target in viewer.lines[index].links:
        if start <= column < end:
            viewer.follow(target)
            return


def press_key(
    viewer: _Viewer, key: str | None, text: str | None, binding: str | None
) -> None:
    """Act on a key: as text for the search, in the list of headings, or on the document."""
    if viewer.typed is not None:
        search_key(viewer, key, text)
        return
    if viewer.outline_choice is not None:
        outline_key(viewer, key, text)
        return
    actions = _document_actions(viewer)
    for name in (binding, text, key):
        action = actions.get(name) if name is not None else None
        if action is not None:
            action()
            return


def _document_actions(viewer: _Viewer) -> dict[str, Callable[[], None]]:
    """What each key does on the document, by the name of the key or by its text."""
    page = max(viewer.rows - 1, 1)

    def by(lines: int) -> Callable[[], None]:
        return lambda: viewer.scroll_to(viewer.top + lines)

    def clear_search() -> None:
        find_text(viewer, '')
        viewer.message = ''
        viewer.build_keys()
        viewer.draw()

    down, up = by(1), by(-1)
    page_down, page_up = by(page), by(-page)
    start = functools.partial(viewer.scroll_to, 0)
    end = functools.partial(viewer.scroll_to, len(viewer.lines))
    is_audio = viewer.document.kind == 'audio'
    return {
        'q': viewer.terminal.end_run,
        'escape': clear_search if viewer.query else viewer.terminal.end_run,
        'ctrl+d': by(page // 2),
        'ctrl+u': by(-(page // 2)),
        'down': down,
        'enter': down,
        'j': down,
        'up': up,
        'k': up,
        'space': functools.partial(toggle_audio, viewer) if is_audio else page_down,
        'page_down': page_down,
        'f': page_down,
        'page_up': page_up,
        'b': page_up,
        'home': start,
        'g': start,
        'end': end,
        'G': end,
        '/': functools.partial(start_search, viewer),
        'n': functools.partial(next_match, viewer, 1),
        'N': functools.partial(next_match, viewer, -1),
        'o': functools.partial(toggle_outline, viewer),
        'r': viewer.toggle_source,
        'backspace': viewer.go_back,
    }


def search_key(viewer: _Viewer, key: str | None, text: str | None) -> None:
    """Take a key while the person types the text to find."""
    if viewer.typed is None:
        return
    if key == 'enter':
        finish_search(viewer)
        return
    if key == 'escape':
        viewer.typed = None
    elif key == 'backspace':
        viewer.typed = viewer.typed[:-1]
    elif text and text.isprintable():
        viewer.typed += text
    viewer.draw()


def outline_key(viewer: _Viewer, key: str | None, text: str | None) -> None:
    """Take a key while the list of headings is open."""
    choice = viewer.outline_choice
    if choice is None:
        return
    if key == 'q':
        viewer.terminal.end_run()
    elif key == 'escape' or text == 'o':
        toggle_outline(viewer)
    elif key == 'enter':
        choose_heading(viewer, choice)
    elif key in ('up', 'down') or text in ('j', 'k'):
        step = 1 if key == 'down' or text == 'j' else -1
        viewer.outline_choice = (choice + step) % len(viewer.headings)
        draw_outline(viewer)
