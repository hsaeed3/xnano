"""
xnano.audio

[`xnano-audio`](https://github.com/hsaeed3/xnano/tree/main/packages/xnano-audio) based components and
utilities for sound playback and composition. Needs the optional ``audio`` extra:
``pip install "xnano[audio]"``.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, TypeAlias, cast

from xnano import _optional
from xnano._media import Audio

_optional.require('audio', needed_for='xnano.audio')

from xnano_audio import (  # noqa: E402
    InstrumentName,
    NoteName,
    Pitch,
    TerminalAudioEffect,
    TerminalAudioError,
    TerminalAudioPlayer,
    TerminalAudioUnavailableError,
    TerminalMelody,
    TerminalMicrophone,
    TerminalNote,
    TerminalSound,
    TerminalTempoMap,
    instrument_names,
    render_note,
)

import xnano_core as _core  # noqa: E402
from xnano._values import NumericExpression  # noqa: E402
from xnano_core._xnano_core import _external  # the hook for values an extension provides  # noqa: E402

if TYPE_CHECKING:
    from xnano.terminal import Terminal

__all__ = [
    'Audio',
    'AudioDevice',
    'InstrumentName',
    'NoteName',
    'Pitch',
    'Playable',
    'TerminalAudioEffect',
    'TerminalAudioError',
    'TerminalAudioUnavailableError',
    'TerminalMelody',
    'TerminalNote',
    'TerminalSound',
    'instrument_names',
]

Playable: TypeAlias = (
    Audio | TerminalSound | TerminalNote | TerminalMelody | NoteName | int | float | str
)
"""
Anything [`AudioDevice.play`][xnano.audio.AudioDevice.play] accepts: an [`Audio`][xnano.Audio], a rendered sound, a note, a melody, a
[`NoteName`][xnano.audio.NoteName] such as ``'C#4'``, a MIDI note number such as ``60``, a frequency
in hertz, or text: ``'440hz'``, or a melody such as ``'C4 E4 G4:2 rest C5+E5+G5'`` (see
[`AudioDevice.play`][xnano.audio.AudioDevice.play]).
"""


def _parse_melody(text: str, beats_per_minute: float) -> TerminalMelody:
    """
    Read a melody written as text: notes separated by spaces, one beat each.

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
            beats = float(length) if length else 1.0
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


def _is_melody_text(source: object) -> bool:
    return isinstance(source, str) and (
        any(mark in source for mark in ' :+') or source.strip().lower() in ('rest', '-')
    )


_LEVEL_NAME = 'audio.level'
_BEAT_NAME = 'audio.beat'


class AudioDevice:
    """
    The terminal's sound: notes, melodies and sounds to play, a musical clock, and the
    microphone.

    Get it from [`Terminal.audio`][xnano.terminal.Terminal.audio]. Playing never waits: the sound
    is rendered on your thread without a device, then handed to the terminal's own loop,
    which owns the audio device. Pitches are MIDI note numbers or names everywhere.

    The microphone level and the musical beat are expressions, so they drive anything an
    expression can: a position, a size, a color, an effect.

    Attributes:
        is_available: Whether this computer has a sound output device.
        tempo: The tempo of the musical clock in beats per minute.
        beat: The musical clock's position in beats, as an expression.
        level: The microphone's current level from 0.0 to 1.0, as an expression.

    Examples:
        ```python
        import xnano

        with xnano.open(offscreen=True, width=20, height=3) as terminal:
            meter = terminal.write('#', y=1)
            meter.x = terminal.audio.level * 19
            level = terminal.inspect(terminal.audio.level)
            assert 0.0 <= level <= 1.0
        ```
    """

    def __init__(self, terminal: Terminal[object]) -> None:
        """
        Create the terminal's audio. Use ``terminal.audio`` instead of calling this.

        Args:
            terminal: The terminal the audio belongs to.
        """
        self._terminal = terminal
        self._lock = threading.Lock()
        self._tempo = 120.0
        self._player: TerminalAudioPlayer | None = None
        self._microphone: TerminalMicrophone | None = None
        self._unavailable: set[str] = set()
        self._is_held = False
        self._level = _external(_LEVEL_NAME, True)
        self._beat = _external(_BEAT_NAME, True)

    # -- availability -------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """Whether this computer has a sound output device."""
        return TerminalAudioPlayer.is_available()

    # -- playing ------------------------------------------------------------------------

    def play(
        self,
        source: Playable,
        *,
        instrument: InstrumentName = 'piano',
        duration_milliseconds: int = 500,
        velocity: float = 0.8,
        effects: list[TerminalAudioEffect] | None = None,
        volume: float = 1.0,
        pan: float = 0.0,
        at_beat: int | None = None,
    ) -> None:
        """
        Play a sound, a note or a melody, and return at once.

        Args:
            source: What to play: an [`Audio`][xnano.Audio], a
                [`TerminalSound`][xnano_audio.TerminalSound], a
                [`TerminalNote`][xnano_audio.TerminalNote], a
                [`TerminalMelody`][xnano_audio.TerminalMelody], a note name (``'C#4'``),
                a MIDI note number (``60``) or a frequency in hertz. Text with spaces is a
                melody at the terminal's tempo: ``'C4 E4 G4:2 rest C5+E5+G5'`` plays notes one
                beat each, ``:2`` holds one for two beats, ``rest`` is a silence, ``+``
                joins a chord and ``|`` marks a bar.
            instrument: A built-in instrument for notes and melodies, from
                [`instrument_names`][xnano_audio.instrument_names]. A sound is played as
                it is.
            duration_milliseconds: How long a note name, number or frequency is held.
            velocity: How hard a note name, number or frequency is played, 0.0 to 1.0.
            effects: Effects applied after the instrument, or to a sound as it is played.
            volume: Playback gain, 0.0 to 1.0.
            pan: Stereo position from -1.0 (left) to 1.0 (right).
            at_beat: Start sample-accurately when the musical clock reaches this beat.
                The clock is started if it is not running.

        Raises:
            TerminalAudioUnavailableError: This computer has no sound output device.
            ValueError: An argument is out of range, or the instrument is unknown.

        Examples:
            ```python
            import xnano
            from xnano_audio import TerminalNote

            with xnano.open(offscreen=True, width=8, height=1) as terminal:
                if terminal.audio.is_available:
                    terminal.audio.play('C4')
                    terminal.audio.play(64, instrument='bell')
                    terminal.audio.play(TerminalNote('G4', duration_beats=0.5))
                    terminal.audio.play('C4 E4 G4:2 rest C5+E5+G5')
            ```
        """
        terminal = self._terminal
        terminal._require_open()
        if not self.is_available:
            raise TerminalAudioUnavailableError(
                'AudioDevice.play needs a sound output device, but this computer has none that '
                'can be opened. Check xnano.audio.is_available before playing, or render '
                'sounds without a device with xnano_audio.render_note.'
            )
        sound = self._sound(
            source,
            instrument=instrument,
            duration_milliseconds=duration_milliseconds,
            velocity=velocity,
            effects=effects,
        )
        terminal._host.post(lambda: self._play_on_loop(sound, volume, pan, at_beat))

    def note(
        self,
        pitch: Pitch,
        beats: float = 1.0,
        *,
        instrument: InstrumentName = 'piano',
        velocity: float = 0.8,
        effects: list[TerminalAudioEffect] | None = None,
        volume: float = 1.0,
        pan: float = 0.0,
        at_beat: int | None = None,
    ) -> None:
        """
        Play one note held for a number of beats, and return at once.

        The length follows the terminal's [`tempo`][xnano.audio.AudioDevice.tempo]: at 120 beats
        per minute a beat is half a second, so a faster tempo plays shorter notes.

        Args:
            pitch: A note name such as ``'C#4'``, or a MIDI note number.
            beats: How long the note is held, in beats.
            instrument: A built-in instrument.
            velocity: How hard the note is played, 0.0 to 1.0.
            effects: Effects applied after the instrument.
            volume: Playback gain, 0.0 to 1.0.
            pan: Stereo position from -1.0 (left) to 1.0 (right).
            at_beat: Start sample-accurately when the musical clock reaches this beat.

        Examples:
            ```python
            import xnano

            with xnano.open(offscreen=True, width=8, height=1) as terminal:
                if terminal.audio.is_available:
                    terminal.audio.tempo = 140
                    terminal.audio.note('E4', beats=0.5, instrument='bell')
            ```
        """
        self.play(
            TerminalNote(pitch, duration_beats=beats, velocity=velocity),
            instrument=instrument,
            effects=effects,
            volume=volume,
            pan=pan,
            at_beat=at_beat,
        )

    def _sound(
        self,
        source: Playable,
        *,
        instrument: InstrumentName,
        duration_milliseconds: int,
        velocity: float,
        effects: list[TerminalAudioEffect] | None,
    ) -> TerminalSound:
        if isinstance(source, Audio):
            source = source.sound
        if isinstance(source, TerminalSound):
            return source.with_effects(effects) if effects else source
        if isinstance(source, TerminalNote):
            melody = TerminalMelody(
                [source.with_start_beats(0.0)],
                tempo_map=TerminalTempoMap(self._tempo),
            )
            return melody.render(instrument, effects=effects)
        if isinstance(source, TerminalMelody):
            return source.render(instrument, effects=effects)
        if isinstance(source, str) and _is_melody_text(source):
            return _parse_melody(source, self._tempo).render(instrument, effects=effects)
        return render_note(
            instrument,
            source,
            duration_milliseconds=duration_milliseconds,
            velocity=velocity,
            effects=effects,
        )

    def _play_on_loop(
        self, sound: TerminalSound, volume: float, pan: float, at_beat: int | None
    ) -> None:
        player = self._open_player()
        if player is None:
            return
        if at_beat is not None and not player.is_clock_running:
            player.start_clock()
        player.play_sound(sound, volume=volume, pan=pan, at_beat=at_beat)

    # -- the musical clock --------------------------------------------------------------

    @property
    def tempo(self) -> float:
        """The tempo of the musical clock in beats per minute."""
        return self._tempo

    @tempo.setter
    def tempo(self, beats_per_minute: float) -> None:
        if not 0 < beats_per_minute <= 600000:
            raise ValueError(
                f'The tempo {beats_per_minute} is out of range. Use a number of beats per '
                f'minute above 0 and at most 600000.'
            )
        self._tempo = float(beats_per_minute)
        self._terminal._host.post(self._apply_tempo)

    def _apply_tempo(self) -> None:
        player = self._player
        if player is not None:
            player.set_tempo(self._tempo)

    @property
    def beat(self) -> NumericExpression:
        """
        The musical clock's position in beats, as an expression.

        It stays at ``0`` until the clock is started with
        [`start`][xnano.audio.AudioDevice.start] or a sound is played with ``at_beat``.

        Examples:
            ```python
            import xnano

            with xnano.open(offscreen=True, width=20, height=2) as terminal:
                ball = terminal.write('o')
                ball.x = (terminal.audio.beat % 1) * 19
            ```
        """
        return self._beat

    def start(self) -> None:
        """Start the musical clock."""
        self._terminal._require_open()
        self._terminal._host.post(self._start_on_loop)

    def _start_on_loop(self) -> None:
        player = self._open_player()
        if player is not None and not player.is_clock_running:
            player.start_clock()

    def resume(self) -> None:
        """Let the musical clock run on from where [`pause`][xnano.audio.AudioDevice.pause] left it."""
        self._terminal._require_open()
        self._terminal._host.post(self._start_on_loop)

    def _hold(self) -> None:
        """Pause the musical clock because the terminal paused. Runs on the terminal's loop."""
        player = self._player
        self._is_held = player is not None and player.is_clock_running
        if self._is_held and player is not None:
            player.pause_clock()

    def _release(self) -> None:
        """Run the musical clock again if [`_hold`][xnano.audio.AudioDevice._hold] paused it."""
        player = self._player
        if self._is_held and player is not None:
            player.start_clock()
        self._is_held = False

    def pause(self) -> None:
        """Pause the musical clock, keeping its position."""
        self._terminal._require_open()
        self._terminal._host.post(lambda: self._player and self._player.pause_clock())

    def stop(self) -> None:
        """Stop the musical clock and return it to the first beat."""
        self._terminal._require_open()
        self._terminal._host.post(lambda: self._player and self._player.stop_clock())

    # -- the microphone -----------------------------------------------------------------

    @property
    def level(self) -> NumericExpression:
        """
        The microphone's current level from 0.0 to 1.0, as an expression.

        Reading it opens the default input device the first time a frame evaluates it.
        Without an input device, or without permission, the level is ``0``.
        """
        return self._level

    def level_history(self, count: int) -> list[float]:
        """
        Return the last ``count`` microphone levels, oldest first.

        Args:
            count: How many levels to return.
        """
        self._terminal._require_open()

        def read() -> list[float]:
            microphone = self._open_microphone()
            return [] if microphone is None else microphone.level_history(count)

        return self._terminal._host.call(read)

    # -- devices, on the terminal's loop ------------------------------------------------

    def _open_player(self) -> TerminalAudioPlayer | None:
        if self._player is None and 'player' not in self._unavailable:
            try:
                self._player = TerminalAudioPlayer(beats_per_minute=self._tempo)
            except TerminalAudioError:
                self._unavailable.add('player')
        return self._player

    def _open_microphone(self) -> TerminalMicrophone | None:
        if self._microphone is None and 'microphone' not in self._unavailable:
            try:
                self._microphone = TerminalMicrophone()
            except TerminalAudioError:
                self._unavailable.add('microphone')
        return self._microphone

    def _provide(self, runtime: _core.Runtime) -> None:
        """Let expressions read the level and the beat. Runs on the terminal's loop."""
        runtime.provide(_LEVEL_NAME, self._read_level)
        runtime.provide(_BEAT_NAME, self._read_beat)

    def _read_level(self) -> float:
        microphone = self._open_microphone()
        return 0.0 if microphone is None else microphone.level

    def _read_beat(self) -> float:
        player = self._player
        return 0.0 if player is None else player.beat

    def _close(self) -> None:
        """Release the devices. Runs on the terminal's loop."""
        for device in (self._player, self._microphone):
            if device is not None:
                device.close()
        self._player = None
        self._microphone = None
