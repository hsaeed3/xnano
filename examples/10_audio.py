"""
Play notes on every instrument.

The list shows every built-in instrument. ``up`` and ``down`` choose one (``left`` and
``right`` jump a column), and the keys ``a`` to ``k`` play a major scale on it, ``space`` a
chord and ``m`` a short tune. ``xnano.note('C4')`` is a value that needs no device, a list of
notes plays one after the other, and a note with several pitches is a chord. The dot follows
the musical clock. Sounds are rendered without a device
and played on the terminal's own loop, so nothing here ever waits for sound. Press ``q`` to quit.
"""

import dataclasses

import xnano
from xnano.audio import InstrumentName, instrument_names
from xnano.context import Context
from xnano.expressions import ParentWidth, Width

SCALE = ('C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5')
KEYS = {key: xnano.note(pitch) for key, pitch in zip('asdfghjk', SCALE, strict=True)}
CHORD_PITCHES = ('C4', 'E4', 'G4')
CHORD = xnano.note(CHORD_PITCHES)
TUNE = [xnano.note(pitch) for pitch in (*CHORD_PITCHES, *CHORD_PITCHES, 'C5')]
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
    with xnano.open(width=66, height=13, state=Keyboard()) as terminal:
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
        terminal.bpm = 90
        if terminal.audio.is_available:
            terminal.audio.start()

        def choose(context: Context[None, Keyboard], step: int) -> None:
            state = context.root.state
            state.index = (state.index + step) % len(INSTRUMENTS)
            highlight.text = instrument_label(INSTRUMENTS[state.index])
            highlight.x, highlight.y = instrument_position(state.index)
            message.text = f'instrument: {INSTRUMENTS[state.index]}'

        @terminal.hook(on='key', keys='up')
        def previous(context: Context[None, Keyboard]) -> None:
            choose(context, -1)

        @terminal.hook(on='key', keys='down')
        def following(context: Context[None, Keyboard]) -> None:
            choose(context, 1)

        @terminal.hook(on='key', keys='left')
        def column_back(context: Context[None, Keyboard]) -> None:
            choose(context, -ROWS)

        @terminal.hook(on='key', keys='right')
        def column_forward(context: Context[None, Keyboard]) -> None:
            choose(context, ROWS)

        @terminal.hook(on='key', keys=list(KEYS))
        def play_note(context: Context[None, Keyboard]) -> None:
            if context.keyboard.key is None:
                return
            chosen = KEYS[context.keyboard.key]
            instrument = INSTRUMENTS[context.root.state.index]
            message.text = f'{chosen.pitch!s:<4} on {instrument}'
            if terminal.audio.is_available:
                terminal.play(chosen, instrument=instrument)

        @terminal.hook(on='key', keys='space')
        def play_chord(context: Context[None, Keyboard]) -> None:
            instrument = INSTRUMENTS[context.root.state.index]
            message.text = f'chord {" ".join(CHORD_PITCHES)} on {instrument}'
            if terminal.audio.is_available:
                terminal.play(CHORD, instrument=instrument)

        @terminal.hook(on='key', keys='m')
        def play_tune(context: Context[None, Keyboard]) -> None:
            instrument = INSTRUMENTS[context.root.state.index]
            message.text = f'tune of {len(TUNE)} notes on {instrument}'
            if terminal.audio.is_available:
                terminal.play(TUNE, instrument=instrument)

        terminal.run(quit_on='q')


if __name__ == '__main__':
    main()
