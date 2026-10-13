"""
Play notes from the keyboard, and let the beat move the screen.

Notes are values you can do arithmetic on: ``root + 4`` is four semitones above ``root``,
``a + b`` plays one after the other, ``a | b`` plays together and ``phrase * 2`` repeats. The
keys ``a`` to ``k`` play a major scale from the root, ``space`` a chord, ``m`` a short tune,
``1`` to ``3`` change the instrument, and the dot follows the musical clock. Sounds are
rendered without a device and played on the terminal's own loop, so nothing here ever waits
for sound. Press ``q`` to quit.
"""

import dataclasses

import xnano
from xnano.audio import InstrumentName, TerminalNote
from xnano.expressions import ParentWidth, Width

root = TerminalNote('C4')
major_scale = (0, 2, 4, 5, 7, 9, 11, 12)
KEYS = {key: root + steps for key, steps in zip('asdfghjk', major_scale, strict=True)}
CHORD = root | (root + 4) | (root + 7)
TUNE = ((root + (root + 4) + (root + 7)) * 2) + (root + 12)
INSTRUMENTS: dict[str, InstrumentName] = {'1': 'piano', '2': 'bell', '3': 'synth'}


@dataclasses.dataclass
class Keyboard:
    """What the keyboard plays with."""

    instrument: str = 'piano'
    """The instrument every note and chord is played on."""


def instrument_of(keyboard: Keyboard) -> InstrumentName:
    """The state's instrument, as a name the audio accepts."""
    names: dict[str, InstrumentName] = {name: name for name in INSTRUMENTS.values()}
    return names[keyboard.instrument]


with xnano.open(width=60, height=6, state=Keyboard()) as terminal:
    terminal.add(
        'a s d f g h j k  scale   space  chord   m  tune   1 2 3  instrument   q  quit'
    )
    if not terminal.audio.is_available:
        terminal.add('(no sound device here: the keys still light up)', y=2)

    metronome = terminal.add('•', y=4)
    metronome.x = (ParentWidth - Width) * (terminal.audio.beat % 1.0)
    terminal.audio.tempo = 90
    if terminal.audio.is_available:
        terminal.audio.start()

    def say(text: str) -> None:
        terminal.write(f'{text:<60}', y=3)

    @terminal.on_key(*KEYS)
    def play_note(context: xnano.Context[Keyboard]) -> None:
        if context.keyboard is None:
            return
        note = KEYS[context.keyboard.key]
        say(f'{note.name:<4} on {context.state.instrument}')
        if context.audio.is_available:
            context.audio.play(note, instrument=instrument_of(context.state))

    @terminal.on_key('space')
    def play_chord(context: xnano.Context[Keyboard]) -> None:
        say(
            f'chord {" ".join(note.name for note in CHORD)} on {context.state.instrument}'
        )
        if context.audio.is_available:
            context.audio.play(CHORD, instrument=instrument_of(context.state))

    @terminal.on_key('m')
    def play_tune(context: xnano.Context[Keyboard]) -> None:
        say(f'tune of {len(TUNE)} notes on {context.state.instrument}')
        if context.audio.is_available:
            context.audio.play(TUNE, instrument=instrument_of(context.state))

    @terminal.on_key(*INSTRUMENTS)
    def choose_instrument(context: xnano.Context[Keyboard]) -> None:
        if context.keyboard is None:
            return
        context.state.instrument = INSTRUMENTS[context.keyboard.key]
        say(f'instrument: {context.state.instrument}')

    terminal.run(quit_on='q')
