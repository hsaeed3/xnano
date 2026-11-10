"""
xnano.reader._viewer_find

Finding a place in the viewer: the search for text, and the list of headings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from xnano_core import display_width

if TYPE_CHECKING:
    from xnano.reader._viewer import _Viewer


def start_search(viewer: _Viewer) -> None:
    """Start to take the keys as the text to find."""
    viewer.typed = ''
    close_outline(viewer)
    viewer.draw()


def find_text(viewer: _Viewer, query: str) -> None:
    """Find the lines that hold ``query``, whatever its case."""
    viewer.query = query
    needle = query.lower()
    viewer.matches = [
        index
        for index, line in enumerate(viewer.lines)
        if needle and needle in line.text.lower()
    ]
    if viewer.table is not None:
        viewer.table.selected_row = None


def finish_search(viewer: _Viewer) -> None:
    """Take the typed text as the search, and go to the first line that holds it."""
    typed, viewer.typed = viewer.typed or '', None
    find_text(viewer, typed)
    viewer.build_keys()
    if not typed:
        viewer.message = ''
        viewer.draw()
    elif not viewer.matches:
        viewer.message = f'"{typed}" is not in this document'
        viewer.draw()
    else:
        next_match(viewer, 1, from_line=viewer.top - 1)


def next_match(viewer: _Viewer, step: int, *, from_line: int | None = None) -> None:
    """Go to the next line that holds the search, or the one before, around the ends."""
    if not viewer.matches:
        return
    start = viewer.top if from_line is None else from_line
    if viewer.table is not None and isinstance(viewer.table.selected_row, int):
        start = viewer.table.selected_row
    if step > 0:
        target = next(
            (index for index in viewer.matches if index > start), viewer.matches[0]
        )
    else:
        target = next(
            (index for index in reversed(viewer.matches) if index < start),
            viewer.matches[-1],
        )
    number = viewer.matches.index(target) + 1
    viewer.message = f'"{viewer.query}" {number} of {len(viewer.matches)}'
    if viewer.table is not None:
        viewer.table.selected_row = target
    viewer.scroll_to(target)


def toggle_outline(viewer: _Viewer) -> None:
    """Open the list of headings, or close it."""
    if viewer.outline_choice is not None:
        close_outline(viewer)
        viewer.message = ''
        viewer.draw()
    elif viewer.headings:
        viewer.outline_choice = max(
            (
                place
                for place, entry in enumerate(viewer.headings)
                if entry[0] <= viewer.top
            ),
            default=0,
        )
        draw_outline(viewer)


def close_outline(viewer: _Viewer) -> None:
    """Close the list of headings."""
    viewer.outline_choice = None
    viewer.panel.is_visible = False


def draw_outline(viewer: _Viewer) -> None:
    """Show the list of headings around the chosen one, on top of the document."""
    choice = viewer.outline_choice
    if choice is None:
        return
    rows = max(min(len(viewer.headings), viewer.height - 4), 1)
    width = max(min(viewer.width - 8, 56), 12)
    first = max(0, min(choice - rows // 2, len(viewer.headings) - rows))
    viewer.outline_first = first
    names: list[str] = []
    for _, level, text in viewer.headings[first : first + rows]:
        name = '  ' * (level - 1) + text
        while display_width(name) > width - 2:
            name = name[:-2] + '…'
        names.append(name)
    viewer.outline.clear()
    viewer.outline.extend(names)
    viewer.outline.selected = choice - first
    viewer.panel.width, viewer.panel.height = width + 2, rows + 2
    viewer.panel.is_visible = True
    viewer.message = '↑ ↓ choose · enter go · esc close'
    viewer.draw()


def choose_heading(viewer: _Viewer, place: int) -> None:
    """Go to the heading at ``place`` of the list, and close the list."""
    if 0 <= place < len(viewer.headings):
        close_outline(viewer)
        viewer.message = ''
        viewer.scroll_to(viewer.headings[place][0])
