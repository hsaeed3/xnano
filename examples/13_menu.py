"""
A menu: pick one item with the keyboard.

The highlighted row lives in the terminal's typed state, and ``terminal.ref`` turns it into an
expression the list follows, so the hooks only change a number. ``up`` and ``down`` move,
``enter`` chooses, and choosing ``Quit`` (or pressing ``q``) leaves.
"""

from dataclasses import dataclass

import xnano
from xnano.context import Context
from xnano.styles import Style
from xnano.widgets import Block, ItemList

CHOICES = ('New game', 'Continue', 'Options', 'Quit')


@dataclass
class Menu:
    """What the menu remembers."""

    selected: int = 0
    """The index of the highlighted choice."""

    chosen: str = ''
    """The choice made with ``enter``, or an empty string before one is made."""


def selected_of(menu: Menu) -> int:
    """The field the list follows."""
    return menu.selected


def main() -> None:
    """Show the menu and react to the keyboard."""
    with xnano.open(width=30, height=8, state=Menu()) as terminal:
        selection = terminal.ref(selected_of)
        terminal.write(
            ItemList(
                list(CHOICES),
                selected=selection.number,
                highlight_symbol='> ',
                highlight_style=Style(foreground='black', background='cyan'),
                block=Block('menu', border_type='rounded'),
            ),
            width=30,
            height=6,
        )
        terminal.write('up/down, enter, q', y=7)
        result = terminal.write('', y=6)

        @terminal.on_key('up')
        def previous(context: Context[Menu]) -> None:
            context.state.selected = max(0, context.state.selected - 1)

        @terminal.on_key('down')
        def following(context: Context[Menu]) -> None:
            context.state.selected = min(len(CHOICES) - 1, context.state.selected + 1)

        @terminal.on_key('enter')
        def choose(context: Context[Menu]) -> None:
            context.state.chosen = CHOICES[context.state.selected]
            if context.state.chosen == 'Quit':
                context.terminal.stop()
            else:
                result.text = f'chose {context.state.chosen}'

        terminal.run(quit_on='q')


if __name__ == '__main__':
    main()
