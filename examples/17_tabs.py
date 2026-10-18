"""
Tabs: one screen, several pages.

``Tabs`` is the header; the page below it is whatever you put there. Every page is placed once and
switching only changes which placement is visible. ``left`` and ``right`` change the tab, ``q`` quits.
"""

import xnano
from xnano.styles import Style
from xnano.widgets import Block, Calendar, Paragraph, Table, Tabs

TITLES = ['About', 'Calendar', 'Table']


def pages() -> list[Paragraph | Calendar | Table]:
    """One widget for each tab, in the same order as ``TITLES``."""
    return [
        Paragraph(
            'xnano draws on a terminal with numbers and formulas.',
            should_wrap=True,
            block=Block(border_type='rounded'),
        ),
        Calendar(
            2026,
            10,
            12,
            month_header_style=Style(bold=True),
            weekdays_header_style=Style('cyan'),
            block=Block(border_type='rounded'),
        ),
        Table(
            [['ratatui', 'widgets'], ['tachyonfx', 'effects']],
            header=['crate', 'gives us'],
            widths=[12, 12],
            block=Block(border_type='rounded'),
        ),
    ]


class TabsState:
    """Which tab is showing."""

    def __init__(self) -> None:
        self.selected = 0


def main() -> None:
    """Show the tabs and switch pages with the arrow keys."""
    state = TabsState()
    with xnano.open(width=44, height=12) as terminal:
        tabs = Tabs(TITLES, selected=0, highlight_style=Style('black', 'cyan'))
        terminal.write(tabs, width=44, height=1)
        placements = [
            terminal.write(widget, y=2, width=44, height=10) for widget in pages()
        ]

        def show(index: int) -> None:
            state.selected = index % len(TITLES)
            tabs.selected = state.selected
            for position, placement in enumerate(placements):
                placement.is_visible = position == state.selected

        show(0)

        @terminal.hook(on='key', keys='left')
        def previous() -> None:
            show(state.selected - 1)

        @terminal.hook(on='key', keys='right')
        def following() -> None:
            show(state.selected + 1)

        terminal.run(quit_on='q')


if __name__ == '__main__':
    main()
