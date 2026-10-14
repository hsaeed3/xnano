"""
Play notes on every instrument.

The list shows every built-in instrument. ``up`` and ``down`` choose one (``left`` and
``right`` jump a column), and the keys ``a`` to ``k`` play a major scale on it, ``space`` a
chord and ``m`` a short tune. Notes are values you can do arithmetic on: ``root + 4`` is four
semitones above ``root``, ``a + b`` plays one after the other, ``a | b`` plays together and
``phrase * 2`` repeats. The dot follows the musical clock. Sounds are rendered without a device
and played on the terminal's own loop, so nothing here ever waits for sound. Press ``q`` to quit.
"""

import dataclasses

import xnano
from xnano.audio import InstrumentName, TerminalNote, instrument_names
from xnano.context import Context
from xnano.expressions import ParentWidth, Width

root = TerminalNote('C4')
major_scale = (0, 2, 4, 5, 7, 9, 11, 12)
KEYS = {key: root + steps for key, steps in zip('asdfghjk', major_scale, strict=True)}
CHORD = root | (root + 4) | (root + 7)
TUNE = ((root + (root + 4) + (root + 7)) * 2) + (root + 12)
INSTRUMENTS: list[InstrumentName] = instrument_names()
ROWS = 8  # instruments per column of the list
COLUMN_WIDTH = 22


@dataclasses.dataclass
class Keyboard:
    """Which instrument the keyboard plays."""

    index: int = 0
    """The position of the chosen instrument in the list."""


def instrument_position(index: int) -> tuple[int, int]:
    """The column and row where an instrument is listed."""
    column, row = divmod(index, ROWS)
    return column * COLUMN_WIDTH, 2 + row


def instrument_label(name: str) -> str:
    """The text that lists an instrument."""
    return f' {name:<{COLUMN_WIDTH - 3}} '


def main() -> None:
    """Choose an instrument and play on it."""
    with xnano.iter(width=66, height=13, state=Keyboard()) as terminal:
        terminal.write('up/down: instrument  a-k: scale  space: chord  m: tune  q: quit')
        if not terminal.audio.is_available:
            terminal.write('(no sound device here: the keys still light up)', y=12)
        for position, name in enumerate(INSTRUMENTS):
            column, row = instrument_position(position)
            terminal.write(instrument_label(name), x=column, y=row)
        chosen_x, chosen_y = instrument_position(0)
        highlight = terminal.write(
            instrument_label(INSTRUMENTS[0]),
            x=chosen_x,
            y=chosen_y,
            layer=1,
            is_reversed=True,
        )
        message = terminal.write('', y=11)

        metronome = terminal.write('•', y=10)
        metronome.x = (ParentWidth - Width) * (terminal.audio.beat % 1.0)
        terminal.audio.tempo = 90
        if terminal.audio.is_available:
            terminal.audio.start()

        def choose(context: Context[Keyboard], step: int) -> None:
            state = context.state
            state.index = (state.index + step) % len(INSTRUMENTS)
            highlight.text = instrument_label(INSTRUMENTS[state.index])
            highlight.x, highlight.y = instrument_position(state.index)
            message.text = f'instrument: {INSTRUMENTS[state.index]}'

        @terminal.on_key('up')
        def previous(context: Context[Keyboard]) -> None:
            choose(context, -1)

        @terminal.on_key('down')
        def following(context: Context[Keyboard]) -> None:
            choose(context, 1)

        @terminal.on_key('left')
        def column_back(context: Context[Keyboard]) -> None:
            choose(context, -ROWS)

        @terminal.on_key('right')
        def column_forward(context: Context[Keyboard]) -> None:
            choose(context, ROWS)

        @terminal.on_key(*KEYS)
        def play_note(context: Context[Keyboard]) -> None:
            if context.keyboard is None:
                return
            note = KEYS[context.keyboard.key]
            instrument = INSTRUMENTS[context.state.index]
            message.text = f'{note.name:<4} on {instrument}'
            if terminal.audio.is_available:
                terminal.play(note, instrument=instrument)

        @terminal.on_key('space')
        def play_chord(context: Context[Keyboard]) -> None:
            instrument = INSTRUMENTS[context.state.index]
            message.text = (
                f'chord {" ".join(note.name for note in CHORD)} on {instrument}'
            )
            if terminal.audio.is_available:
                terminal.play(CHORD, instrument=instrument)

        @terminal.on_key('m')
        def play_tune(context: Context[Keyboard]) -> None:
            instrument = INSTRUMENTS[context.state.index]
            message.text = f'tune of {len(TUNE)} notes on {instrument}'
            if terminal.audio.is_available:
                terminal.play(TUNE, instrument=instrument)

        terminal.run(quit_on='q')


if __name__ == '__main__':
    main()
