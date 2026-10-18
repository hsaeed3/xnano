"""
xnano.audio._notes

Notes and sound: [`note`][xnano.note] makes a [`Note`][xnano.Note] you can define anywhere, and
[`play`][xnano.play] plays notes, sounds and melodies on the running canvas or on this
computer's sound output. Playing needs the optional ``audio`` extra:
``pip install "xnano[audio]"``.
"""

from __future__ import annotations

import atexit
import contextlib
import dataclasses
import math
import re
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Final

from xnano import symbols
from xnano._internal import _optional
from xnano.effects._registry import effect_sequence, normalize_effect

if TYPE_CHECKING:
    from types import ModuleType

    from typing_extensions import Unpack
    from xnano_audio import InstrumentName, Pitch, TerminalAudioPlayer

    from xnano._schema._content import PlaySource
    from xnano._schema._media import PlayOptions
    from xnano.context import Context
    from xnano.region import Region
    from xnano.types import PlayableEffectSpecification

__all__ = ['Note', 'PlayHandle', 'note', 'play']

_MOST_MIDI_NUMBER: Final = 127

# A note name such as ``C4``, ``c#4`` or ``Bb-1``, used to check a pitch when the audio
# package that knows every name is not installed.
_NOTE_NAME: Final = re.compile(r'^[A-Ga-g](#|b)?-?\d+$')

# A note name read for its MIDI number: a letter, an optional ``#`` or ``b`` and an optional
# octave (``c#`` is C#4, as ``xnano_audio`` reads it).
_NOTE_PITCH: Final = re.compile(r'^([A-Ga-g])(#|b)?(-?\d+)?$')

# The semitones from C up to each note letter within an octave.
_LETTER_SEMITONES: Final = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}

_DEFAULT_OCTAVE: Final = 4
"""The octave of a note name that gives none, such as ``'c#'``."""


def _installed_audio() -> ModuleType | None:
    """The ``xnano_audio`` module when it is installed, otherwise ``None``."""
    try:
        return _optional.require('audio', needed_for='xnano.note')
    except ImportError:
        return None


def _midi_number(pitch: Pitch) -> int:
    """
    The MIDI number of a pitch: an integer is returned as it is, and a name such as ``'Bb3'``
    is read as a letter, an optional ``#`` or ``b`` and an octave (4 when it gives none), with
    ``'C4'`` being 60.
    """
    if isinstance(pitch, int):
        return pitch
    found = _NOTE_PITCH.match(pitch)
    if found is None:
        audio = _installed_audio()
        if audio is not None:
            with contextlib.suppress(ValueError):
                return int(audio.TerminalNote(pitch).pitch)
        raise ValueError(
            f'{pitch!r} is not a note name. Write a letter, an optional # or b, and an '
            f'octave, such as "C4" or "Bb3", or use a MIDI number from 0 to '
            f'{_MOST_MIDI_NUMBER}.'
        )
    letter, accidental, octave = found.groups()
    semitones = _LETTER_SEMITONES[letter.upper()]
    if accidental == '#':
        semitones += 1
    elif accidental == 'b':
        semitones -= 1
    return ((int(octave) if octave else _DEFAULT_OCTAVE) + 1) * 12 + semitones


def _hashable(value: object) -> object:
    """
    ``value`` as something that can be hashed: a mapping as a ``frozenset`` of its items, a list
    or a tuple as a tuple of hashable items, and anything else as it is.
    """
    if isinstance(value, Mapping):
        return frozenset((key, _hashable(item)) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return tuple(_hashable(item) for item in value)
    return value


def _check_pitch(pitch: object) -> None:
    """Raise the error a wrong pitch deserves."""
    if isinstance(pitch, bool) or not isinstance(pitch, (int, str)):
        raise TypeError(
            f'A pitch is a note name such as "C4" or a MIDI number such as 60, but got '
            f'{pitch!r}. Pass note("C4") or note(60); use a tuple such as ("C4", "E4", "G4") '
            f'for a chord.'
        )
    if isinstance(pitch, int):
        if not 0 <= pitch <= _MOST_MIDI_NUMBER:
            raise ValueError(
                f'MIDI pitch {pitch} is outside the supported range (0 to '
                f'{_MOST_MIDI_NUMBER}). Use a MIDI number from 0 to {_MOST_MIDI_NUMBER} or a '
                f'note name such as "C4".'
            )
        return
    audio = _installed_audio()
    if audio is not None:
        try:
            audio.TerminalNote(pitch)
        except ValueError:
            raise ValueError(
                f'{pitch!r} is not a note name. Write a letter, an optional # or b, and an '
                f'octave, such as "C4" or "Bb3", or use a MIDI number from 0 to '
                f'{_MOST_MIDI_NUMBER}.'
            ) from None
    elif not _NOTE_NAME.match(pitch):
        raise ValueError(
            f'{pitch!r} is not a note name. Write a letter, an optional # or b, and an '
            f'octave, such as "C4" or "Bb3", or use a MIDI number.'
        )


@dataclasses.dataclass(frozen=True, slots=True)
class Note:
    """
    A note, or a chord, to play: a pitch, how long it lasts and how it sounds.

    A note is a plain value. It needs no sound device, no canvas and not even the ``audio``
    extra to be created, so a song can be defined at the top of a module and played later
    with [`play`][xnano.play] or [`Canvas.play`][xnano.canvas.Canvas.play]. A sequence of
    notes plays one after another. ``symbol`` registers the note under a name, so
    ``play('kick')`` finds it.

    Attributes:
        pitch: A note name such as ``'C#4'``, a MIDI number from 0 to 127 (60 is middle C), or
            a tuple of them for a chord.
        beats: How long the note is held, in beats at the canvas's tempo. A beat is half a
            second at 120 beats per minute.
        instrument: A built-in instrument, from
            [`instrument_names`][xnano.audio.instrument_names].
        velocity: How hard the note is played, from 0.0 to 1.0.
        effects: Sound effects as dictionaries with a ``kind`` key, such as
            ``{'kind': 'audio.reverb', 'mix': 0.4}``.
        symbol: The name the note is registered under in [`symbols`][xnano.symbols], or
            ``None``.
        region: The note on the timeline as a piano roll: a
            [`Region`][xnano.region.Region] that starts at beat 0, lasts ``beats`` and spans
            the semitones from the lowest to the highest pitch.

    Raises:
        TypeError: The pitch is not a note name or a number, or an effect is not a dictionary.
        ValueError: The pitch is not valid, ``beats`` is not above 0, ``velocity`` is not from
            0.0 to 1.0, or the instrument is unknown (checked when the ``audio`` extra is
            installed, and otherwise when the note is played).

    Examples:
        ```python
        import xnano

        chord = xnano.Note(('C4', 'E4', 'G4'), beats=2.0, instrument='bell')
        assert chord.beats == 2.0
        assert chord.region.y == 60
        assert chord.region.height == 8
        assert chord.region.width == 2.0
        assert chord.region.ticks.width == 8.0
        assert chord.region.milliseconds.width == 1000.0
        with xnano.new(width=8, height=1) as canvas:
            canvas.play([chord, xnano.note('C5')])
            canvas.step(delta_seconds=1.0)
            assert canvas.audio.render_sound().duration_milliseconds == 1000.0
        ```
    """

    pitch: Pitch | tuple[Pitch, ...]
    """A note name, a MIDI number, or a tuple of them for a chord."""
    beats: float = 1.0
    """How long the note is held, in beats."""
    instrument: InstrumentName = 'piano'
    """The built-in instrument."""
    velocity: float = 0.8
    """How hard the note is played, from 0.0 to 1.0."""
    effects: tuple[PlayableEffectSpecification, ...] = ()
    """The sound effects, as dictionaries with a ``kind`` key."""
    symbol: str | None = None
    """The registered symbol name, or ``None``."""

    def __post_init__(self) -> None:
        """Check the values and register the symbol."""
        pitch = self.pitch
        if isinstance(pitch, (list, tuple)):
            if not pitch:
                raise ValueError(
                    'A chord needs at least one pitch, but got an empty one. Pass '
                    'note(("C4", "E4", "G4")) for a chord or note("C4") for one note.'
                )
            pitch = tuple(pitch)
            for each in pitch:
                _check_pitch(each)
            object.__setattr__(self, 'pitch', pitch)
        else:
            _check_pitch(pitch)
        if (
            isinstance(self.beats, bool)
            or not isinstance(self.beats, (int, float))
            or not math.isfinite(self.beats)
            or self.beats <= 0
        ):
            raise ValueError(
                f'beats must be a number above 0, but was {self.beats!r}. Use 1.0 for one '
                f'beat or 0.5 for half a beat.'
            )
        if isinstance(self.velocity, bool) or not isinstance(self.velocity, (int, float)):
            raise ValueError(
                f'velocity must be a number from 0.0 to 1.0, but was {self.velocity!r}. Use '
                f'0.8 for an ordinary note.'
            )
        if not isinstance(self.instrument, str):
            raise ValueError(
                f'instrument must be the name of a built-in instrument, such as "piano", '
                f'but was {self.instrument!r}.'
            )
        if not 0.0 <= self.velocity <= 1.0:
            raise ValueError(
                f'velocity must be from 0.0 to 1.0, but was {self.velocity!r}. Use 0.8 for '
                f'an ordinary note.'
            )
        audio = _installed_audio()
        if audio is not None:
            names = audio.instrument_names()
            if self.instrument not in names:
                raise ValueError(
                    f'{self.instrument!r} is not an instrument. Use one of: '
                    f'{", ".join(names)}.'
                )
        effects = effect_sequence(self.effects, 'playable')
        for effect in effects:
            normalize_effect(effect, 'playable')
        object.__setattr__(self, 'effects', effects)
        if self.symbol is not None:
            symbols.register(self.symbol, self)

    def __hash__(self) -> int:
        """Hash the note by its values, so notes that are equal hash equal."""
        return hash(
            (
                self.pitch,
                self.beats,
                self.instrument,
                self.velocity,
                _hashable(self.effects),
                self.symbol,
            )
        )

    @property
    def region(self) -> Region[float]:
        """
        The note on the timeline as a piano roll, on its own.

        The region starts at beat 0 and lasts ``beats``. Its ``y`` is the lowest pitch as a
        MIDI number and its ``height`` the semitones from the lowest to the highest pitch,
        so a chord spans several rows and a single note one. Its ``milliseconds`` view
        assumes 120 beats per minute, the tempo of [`play`][xnano.play] when no canvas is
        running; ``context.region`` of a hook on a playable measures at the tempo of the
        canvas instead.

        Examples:
            ```python
            import xnano

            region = xnano.note('A4', beats=0.5).region
            assert (region.x, region.width) == (0.0, 0.5)
            assert (region.y, region.height) == (69, 1)
            ```
        """
        from xnano.region import _timeline_region

        pitches = self.pitch if isinstance(self.pitch, tuple) else (self.pitch,)
        return _timeline_region(
            start_beats=0.0,
            length_beats=self.beats,
            pitches=[_midi_number(pitch) for pitch in pitches],
            tempo_changes=((0.0, _DEFAULT_BPM),),
        )

    def __xnano_play__(self, context: Context) -> Note:
        """Return this note, so a note is playable like any other component."""
        return self


def note(
    pitch: Pitch | Sequence[Pitch],
    *,
    beats: float = 1.0,
    instrument: InstrumentName = 'piano',
    velocity: float = 0.8,
    effects: Sequence[PlayableEffectSpecification] = (),
    symbol: str | None = None,
) -> Note:
    """
    Make a [`Note`][xnano.Note]: a pitch, or several for a chord, with its length and sound.

    Nothing is played and no sound device is needed. Play it with [`play`][xnano.play] or
    [`Canvas.play`][xnano.canvas.Canvas.play]. ``symbol='kick'`` registers the note, and then
    ``play('kick')`` plays it.

    Args:
        pitch: A note name such as ``'C#4'``, a MIDI number from 0 to 127, or a sequence of
            them for a chord.
        beats: How long the note is held, in beats.
        instrument: A built-in instrument, from
            [`instrument_names`][xnano.audio.instrument_names].
        velocity: How hard the note is played, from 0.0 to 1.0.
        effects: Sound effects as dictionaries with a ``kind`` key, such as
            ``{'kind': 'audio.reverb'}``.
        symbol: A name to register the note under in [`symbols`][xnano.symbols]. A ``str``
            given to [`play`][xnano.play] is looked up as a symbol name before it is read as a
            note name, so the name must not look like a note.

    Raises:
        TypeError: The pitch is not a note name or a number.
        ValueError: A value is out of range or the instrument is unknown.

    Examples:
        ```python
        import xnano

        kick = xnano.note('C2', instrument='kick', symbol='kick_drum')
        with xnano.new(width=8, height=1) as canvas:
            canvas.play('kick_drum')
            canvas.step(delta_seconds=0.5)
            assert canvas.audio.render_sound().peak > 0.0
        ```
    """
    chord = (
        tuple(pitch)
        if isinstance(pitch, Sequence) and not isinstance(pitch, str)
        else pitch
    )
    return Note(
        chord,  # type: ignore[arg-type]
        beats=beats,
        instrument=instrument,
        velocity=velocity,
        effects=effect_sequence(effects, 'playable'),  # type: ignore[arg-type]
        symbol=symbol,
    )


class PlayHandle:
    """
    What [`play`][xnano.play] returns: tells whether the sound is over and can cut it short.

    Attributes:
        is_finished: Whether the sound has ended or the handle was removed. On a canvas from
            [`new`][xnano.new] this follows the canvas's clock; on a device it follows
            the real time since the sound was handed over.

    Examples:
        ```python
        import xnano

        with xnano.new(width=8, height=1) as canvas:
            handle = canvas.play(xnano.note('C4', beats=1.0))
            assert not handle.is_finished
            handle.remove()
            assert handle.is_finished
        ```
    """

    __slots__ = ('_cancel', '_clock', '_end_seconds', '_is_removed', '_region')

    def __init__(
        self,
        *,
        clock: Callable[[], float],
        end_seconds: float,
        cancel: Callable[[], None] | None = None,
        region: Region[float] | None = None,
    ) -> None:
        """
        Make a handle. Use the handle that ``play`` returns instead of calling this.

        Args:
            clock: Returns the current time in seconds.
            end_seconds: The time on that clock at which the sound is over.
            cancel: Called once by ``remove()``.
            region: Where the sound is on the timeline of the canvas it plays on, which is
                what ``context.region`` of a playable reports; ``None`` when that is not
                known.
        """
        self._clock = clock
        self._end_seconds = end_seconds
        self._cancel = cancel
        self._is_removed = False
        self._region = region

    @property
    def is_finished(self) -> bool:
        """Whether the sound ended or the handle was removed."""
        return self._is_removed or self._clock() >= self._end_seconds

    def remove(self) -> None:
        """
        Stop the sound from playing any further, as far as it has not been heard yet.

        On a canvas from [`new`][xnano.new] the part that has not been rendered by
        [`render_sound`][xnano.audio.AudioDevice.render_sound] is dropped. On a device a sound
        that was already handed to the output plays to its end, and one still waiting for its
        beat never starts. Removing twice does nothing.
        """
        if self._is_removed:
            return
        self._is_removed = True
        if self._cancel is not None:
            self._cancel()


def play(playable: PlaySource, /, **options: Unpack[PlayOptions]) -> PlayHandle:
    """
    Play a note, a sound, a symbol name, a melody or a sequence of those.

    The sound goes to the running canvas (see [`active`][xnano.active]); with no canvas
    running it goes to this computer's sound output. On a canvas from [`new`][xnano.new],
    which has a clock you move, the sound is recorded and makes no noise: read it with
    ``canvas.audio.render_sound()``.

    A ``str`` is a symbol name first, so ``play('kick')`` plays the note or sound registered
    with ``symbol='kick'``. Any other ``str`` is a note name such as ``'C#4'``, a frequency such
    as ``'440hz'`` or melody text: notes separated by spaces, ``:2`` holds a note for two
    beats, ``rest`` is a silence, ``+`` joins a chord and ``|`` marks a bar, as in
    ``'C4 E4 G4:2 rest C5+E5+G5'``. A sequence plays one after another. An option replaces
    the same value on a [`Note`][xnano.Note], so ``play(note('C4'), instrument='violin')``
    plays the violin.

    Args:
        playable: What to play.
        **options: See [`PlayOptions`][xnano.types.PlayOptions]: ``instrument``, ``velocity``,
            ``effects``, ``volume``, ``pan``, ``at_beat`` and ``beats``, the length in beats
            of a note name, a number or a ``Note``.

    Returns:
        A [`PlayHandle`][xnano.audio.PlayHandle].

    Raises:
        ImportError: ``xnano-audio`` is not installed. Install it with
            ``pip install "xnano[audio]"``.
        TerminalAudioUnavailableError: No canvas is running and this computer has no sound
            output device.
        ValueError: An option is out of range, or a ``str`` is neither a symbol, a note name
            nor melody text. The message lists the known sound symbols.

    Examples:
        ```python
        import xnano

        with xnano.new(width=8, height=1) as canvas:
            xnano.play([xnano.note('C4'), xnano.note('E4'), xnano.note('G4')])
            canvas.step(delta_seconds=1.5)
            assert canvas.audio.render_sound().peak > 0.0
        ```
    """
    from xnano.canvas import active

    canvas = active(is_required=False)
    if canvas is not None:
        return canvas.play(playable, **options)
    return _default_player().play(playable, **options)


class _DefaultPlayer:
    """The sound output that ``play`` uses when no canvas is running."""

    def __init__(self) -> None:
        """Make a player that opens the sound output the first time it is used."""
        self._lock = threading.Lock()
        self._player: TerminalAudioPlayer | None = None

    def play(self, playable: object, **options: object) -> PlayHandle:
        _optional.require('audio', needed_for='xnano.play')
        from xnano.audio import _player

        planned = _player._plan_call(
            playable,
            bpm=_DEFAULT_BPM,
            instrument=options.get('instrument'),  # type: ignore[arg-type]
            beats=options.get('beats'),  # type: ignore[arg-type]
            velocity=options.get('velocity'),  # type: ignore[arg-type]
            effects=options.get('effects'),  # type: ignore[arg-type]
            volume=options.get('volume', 1.0),  # type: ignore[arg-type]
            pan=options.get('pan', 0.0),  # type: ignore[arg-type]
            at_beat=options.get('at_beat'),  # type: ignore[arg-type]
        )
        sound = _player._mix_planned(planned)
        with self._lock:
            player = self._open()
            at_beat = options.get('at_beat')
            if at_beat is not None and not player.is_clock_running:
                player.start_clock()
            player.play_sound(
                sound,
                volume=options.get('volume', 1.0),  # type: ignore[arg-type]
                pan=options.get('pan', 0.0),  # type: ignore[arg-type]
                at_beat=at_beat,  # type: ignore[arg-type]
            )
        return PlayHandle(
            clock=time.monotonic,
            end_seconds=time.monotonic() + sound.duration_milliseconds / 1000.0,
        )

    def _open(self) -> TerminalAudioPlayer:
        if self._player is None:
            from xnano.audio import _player

            try:
                self._player = _player.TerminalAudioPlayer(beats_per_minute=_DEFAULT_BPM)
            except _player.TerminalAudioError:
                raise _player.TerminalAudioUnavailableError(
                    'xnano.play needs a sound output device, but this computer has none that '
                    'can be opened. Play on a canvas from xnano.new(), which records the '
                    'sound for canvas.audio.render_sound().'
                ) from None
            atexit.register(self.close)
        return self._player

    def close(self) -> None:
        with self._lock:
            player, self._player = self._player, None
        if player is not None:
            player.close()


_DEFAULT_BPM: Final = 120.0
"""The tempo of the sound output ``play`` uses when no canvas is running."""

_default: _DefaultPlayer | None = None
_default_lock: Final = threading.Lock()


def _default_player() -> _DefaultPlayer:
    global _default
    with _default_lock:
        if _default is None:
            _default = _DefaultPlayer()
        return _default
