"""
xnano.music

Notes and sound: [`note`][xnano.note] makes a [`Note`][xnano.Note] you can define anywhere, and
[`play`][xnano.play] plays notes, sounds and melodies on the running canvas or on this
computer's sound output. Playing needs the optional ``audio`` extra:
``pip install "xnano[audio]"``.
"""

from __future__ import annotations

import atexit
import dataclasses
import math
import re
import threading
import time
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Final

from xnano import _optional, symbols
from xnano._customize import normalize_effect

if TYPE_CHECKING:
    from types import ModuleType

    from typing_extensions import Unpack
    from xnano_audio import InstrumentName, Pitch, TerminalAudioPlayer

    from xnano.context import Context
    from xnano.types import Playable, PlayableEffectSpecification, PlayOptions

__all__ = ['Note', 'PlayHandle', 'note', 'play']

_MOST_MIDI_NUMBER: Final = 127

# A note name such as ``C4``, ``c#4`` or ``Bb-1``, used to check a pitch when the audio
# package that knows every name is not installed.
_NOTE_NAME: Final = re.compile(r'^[A-Ga-g](#|b)?-?\d+$')


def _installed_audio() -> ModuleType | None:
    """The ``xnano_audio`` module when it is installed, otherwise ``None``."""
    try:
        return _optional.require('audio', needed_for='xnano.note')
    except ImportError:
        return None


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
            [`instrument_names`][xnano_audio.instrument_names].
        velocity: How hard the note is played, from 0.0 to 1.0.
        effects: Sound effects as dictionaries with a ``kind`` key, such as
            ``{'kind': 'audio.reverb', 'mix': 0.4}``.
        symbol: The name the note is registered under in [`symbols`][xnano.symbols], or
            ``None``.

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
        effects = tuple(self.effects)
        for effect in effects:
            normalize_effect(effect, 'playable')
        object.__setattr__(self, 'effects', effects)
        if self.symbol is not None:
            symbols.register(self.symbol, self)

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
            [`instrument_names`][xnano_audio.instrument_names].
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
        effects=tuple(effects),
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

    __slots__ = ('_cancel', '_clock', '_end_seconds', '_is_removed')

    def __init__(
        self,
        *,
        clock: Callable[[], float],
        end_seconds: float,
        cancel: Callable[[], None] | None = None,
    ) -> None:
        """
        Make a handle. Use the handle that ``play`` returns instead of calling this.

        Args:
            clock: Returns the current time in seconds.
            end_seconds: The time on that clock at which the sound is over.
            cancel: Called once by ``remove()``.
        """
        self._clock = clock
        self._end_seconds = end_seconds
        self._cancel = cancel
        self._is_removed = False

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


def play(playable: Playable, /, **options: Unpack[PlayOptions]) -> PlayHandle:
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
        A [`PlayHandle`][xnano.music.PlayHandle].

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
        from xnano import audio

        planned = audio.plan_call(
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
        sound = audio.mix_planned(planned)
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
            from xnano import audio

            try:
                self._player = audio.TerminalAudioPlayer(beats_per_minute=_DEFAULT_BPM)
            except audio.TerminalAudioError:
                raise audio.TerminalAudioUnavailableError(
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
