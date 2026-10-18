"""
xnano.audio._melodies

Melodies written as text.
"""

from __future__ import annotations

import dataclasses
import math
from typing import TYPE_CHECKING, cast

from xnano import symbols
from xnano._internal import _optional

_optional.require('audio', needed_for='xnano.audio.Melody')

from xnano_audio import Pitch, TerminalMelody, TerminalTempoMap  # noqa: E402

if TYPE_CHECKING:
    from xnano.region import Region

__all__ = ['Melody', 'is_melody_text', 'parse_melody_text']


def _check_positive_number(name: str, value: object, *, example: str) -> float:
    """``value`` as a ``float``, or the error that says a ``name`` is a number above 0."""
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError(
            f'Melody needs {name} to be a finite number above 0, but got {value!r}. {example}'
        )
    return float(value)


@dataclasses.dataclass(frozen=True, slots=True, init=False)
class Melody:
    """
    Notes in order, written as text and parsed: ``'C4 E4 G4:2 rest C5+E5+G5'``.

    A melody is the parsed form of the melody text that [`play`][xnano.play] also accepts.
    Make one when you want to look at the notes, reuse the same melody many times, or give it
    a ``symbol`` so ``play('theme')`` plays it. A melody plays at its own ``bpm``, whatever the
    tempo of the canvas it is played on.

    In the text, ``C4`` is a note, ``C4:0.5`` holds it for half a beat, ``C4+E4+G4`` is a
    chord, ``rest`` (or ``-``) is a silence that takes ``:beats`` the same way, and ``|`` is a
    bar line that only makes the text easier to read.

    Maps to [`xnano_audio.TerminalMelody`][xnano_audio.TerminalMelody].

    Attributes:
        text: The melody text it was made from.
        bpm: The tempo it plays at, in beats per minute.
        beats: The length in beats of a note that gives none.
        score: The parsed melody: its notes, tempo map and time signature.
        symbol: The name the melody is registered under in [`symbols`][xnano.symbols], or
            ``None``.
        length_beats: The length of the melody in beats.
        duration_seconds: The length of the melody in seconds, at its tempo.
        region: The melody on the timeline as a piano roll: a
            [`Region`][xnano.region.Region] that starts at beat 0, lasts ``length_beats``
            and spans the semitones from its lowest to its highest pitch. Its
            ``milliseconds`` view follows the tempo of the melody.

    Examples:
        ```python
        import xnano

        melody = xnano.audio.Melody('C4 E4 G4:2', bpm=120)
        assert melody.length_beats == 4.0
        assert melody.region.width == 4.0
        assert melody.region.height == 8
        with xnano.new(width=8, height=1) as canvas:
            canvas.play(melody)
            canvas.step(delta_seconds=1.0)
            assert canvas.audio.render_sound().peak > 0.0
        ```
    """

    text: str
    """The melody text it was made from."""
    bpm: float
    """The tempo it plays at, in beats per minute."""
    beats: float
    """The length in beats of a note that gives none."""
    score: TerminalMelody = dataclasses.field(compare=False, hash=False)
    """
    The parsed melody: its notes, tempo map and time signature.

    Maps to [`xnano_audio.TerminalMelody`][xnano_audio.TerminalMelody].
    """
    symbol: str | None
    """The registered symbol name, or ``None``."""

    def __init__(
        self,
        text: str,
        *,
        bpm: float = 120.0,
        beats: float = 1.0,
        symbol: str | None = None,
    ) -> None:
        """
        Parse melody text.

        Args:
            text: Notes separated by spaces, such as ``'C4 E4 G4:2 rest C5+E5+G5'``.
            bpm: The tempo the melody plays at, in beats per minute.
            beats: The length in beats of a note that gives none of its own.
            symbol: A name to register the melody under in [`symbols`][xnano.symbols], so
                ``play(name)`` plays it.

        Raises:
            ImportError: ``xnano-audio`` is not installed. Install it with
                ``pip install "xnano[audio]"``.
            TypeError: ``text`` is not a ``str``.
            ValueError: ``bpm`` or ``beats`` is not a finite number above 0, an entry of the
                text is not a note, a length, a chord or a rest, or ``symbol`` cannot be a
                symbol name, or another kind of value already has it.
        """
        if not isinstance(text, str):
            raise TypeError(
                f'Melody needs melody text such as "C4 E4 G4:2", but got {text!r}. Pass notes '
                f'separated by spaces.'
            )
        tempo = _check_positive_number(
            'bpm', bpm, example='Use 120.0 for an ordinary tempo.'
        )
        length = _check_positive_number(
            'beats', beats, example='Use 1.0 for a note that lasts one beat.'
        )
        score = parse_melody_text(text, tempo, length)
        object.__setattr__(self, 'text', text)
        object.__setattr__(self, 'bpm', tempo)
        object.__setattr__(self, 'beats', length)
        object.__setattr__(self, 'score', score)
        object.__setattr__(self, 'symbol', symbol)
        if symbol is not None:
            symbols.register(symbol, self)

    @property
    def length_beats(self) -> float:
        """The length of the melody in beats, from the start of the first note to the end of the last."""
        return self.score.length_beats

    @property
    def duration_seconds(self) -> float:
        """The length of the melody in seconds at its ``bpm``."""
        return self.score.duration_seconds

    @property
    def region(self) -> Region[float]:
        """
        The melody on the timeline as a piano roll.

        The region starts at beat 0 and lasts ``length_beats``. Its ``y`` is the lowest pitch
        as a MIDI number and its ``height`` the semitones from the lowest to the highest
        pitch; a melody of only rests spans none. Its ``milliseconds`` view follows the
        tempo of the melody, including any change of tempo in it.

        Examples:
            ```python
            import xnano

            region = xnano.audio.Melody('C4 rest E4:2', bpm=60).region
            assert (region.width, region.y, region.height) == (4.0, 60, 5)
            assert region.milliseconds.width == 4000.0
            ```
        """
        from xnano.region import _timeline_region

        tempo_map = self.score.tempo_map
        return _timeline_region(
            start_beats=0.0,
            length_beats=self.score.length_beats,
            pitches=[note.pitch for note in self.score.notes],
            tempo_changes=(
                (0.0, tempo_map.initial_beats_per_minute),
                *tempo_map.changes,
            ),
        )


def parse_melody_text(
    text: str, beats_per_minute: float, default_beats: float = 1.0
) -> TerminalMelody:
    """
    Read a melody written as text: notes separated by spaces, ``default_beats`` each.

    ``C4`` is a note, ``C4:0.5`` holds it for half a beat, ``C4+E4+G4`` is a chord, and
    ``rest`` (or ``-``) is a silence, which takes ``:beats`` the same way, and ``|`` is a bar line
    that only makes the text easier to read.
    """
    melody = TerminalMelody(tempo_map=TerminalTempoMap(beats_per_minute))
    for entry in text.split():
        if entry == '|':
            continue
        name, _, length = entry.partition(':')
        try:
            beats = float(length) if length else default_beats
            if name.lower() in ('rest', '-'):
                melody = melody.appended_rest(beats)
            else:
                pitches = name.split('+')
                if len(pitches) == 1:
                    melody = melody.appended_note(
                        cast('Pitch', pitches[0]), duration_beats=beats
                    )
                else:
                    melody = melody.appended_chord(
                        cast('list[Pitch]', pitches), duration_beats=beats
                    )
        except ValueError as error:
            raise ValueError(
                f'{entry!r} is not a note in the melody {text!r}. Write notes like "C4", '
                f'a length after a colon like "C4:0.5", chords like "C4+E4+G4", and '
                f'silences as "rest" or "rest:2". {error}'
            ) from error
    return melody


def is_melody_text(source: object) -> bool:
    """Whether ``source`` is text with more than one note, a length, a chord or a rest."""
    return isinstance(source, str) and (
        any(mark in source for mark in ' :+') or source.strip().lower() in ('rest', '-')
    )
