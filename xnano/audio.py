"""
xnano.audio

[`xnano-audio`](https://github.com/hsaeed3/xnano/tree/main/packages/xnano-audio) based components and
utilities for sound playback and composition. Needs the optional ``audio`` extra:
``pip install "xnano[audio]"``.
"""

from __future__ import annotations

import collections
import dataclasses
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Final, TypeAlias, cast

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
    from xnano.canvas import Canvas

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


_MOST_MIDI_NUMBER: Final = 127
_LOWEST_HERTZ: Final = 8.0
_HIGHEST_HERTZ: Final = 20000.0
_LONGEST_NOTE_MILLISECONDS: Final = 60000


def _check_play_arguments(
    source: object,
    *,
    duration_milliseconds: int,
    effects: list[TerminalAudioEffect] | None,
    pan: float,
    at_beat: int | None,
) -> None:
    """Raise the error a bad ``play()`` argument deserves, where ``play()`` was called."""
    if not -1.0 <= pan <= 1.0:
        raise ValueError(
            f'pan must be between -1.0 (left) and 1.0 (right), but was {pan!r}. Use 0.0 for '
            f'the center.'
        )
    if at_beat is not None and at_beat < 0:
        raise ValueError(
            f'at_beat must be 0 or more, but was {at_beat!r}. Pass the beat of the musical '
            f'clock to start on, or remove at_beat to start now.'
        )
    if not 1 <= duration_milliseconds <= _LONGEST_NOTE_MILLISECONDS:
        raise ValueError(
            f'duration_milliseconds must be between 1 and {_LONGEST_NOTE_MILLISECONDS}, but '
            f'was {duration_milliseconds!r}. Use 500 for half a second.'
        )
    for effect in effects or ():
        if not isinstance(effect, TerminalAudioEffect):
            raise TypeError(
                f'effects must hold audio effects, but one was {effect!r}. Build effects '
                f'with xnano_audio.TerminalAudioEffect, for example '
                f'TerminalAudioEffect.reverb().'
            )
    if isinstance(source, bool):
        return
    if isinstance(source, int):
        if not 0 <= source <= _MOST_MIDI_NUMBER:
            raise ValueError(
                f'MIDI pitch {source} is outside the supported range (0 to '
                f'{_MOST_MIDI_NUMBER}). Use a MIDI number from 0 to {_MOST_MIDI_NUMBER}, a '
                f'note name such as "C4", or a frequency in hertz.'
            )
    elif isinstance(source, float):
        _check_hertz(source)
    elif (
        isinstance(source, str)
        and not _is_melody_text(source)
        and source.strip().lower().endswith('hz')
    ):
        try:
            hertz = float(source.strip()[:-2])
        except ValueError:
            raise ValueError(
                f'{source!r} is not a frequency. Write a number followed by hz, such as '
                f'"440hz", or use a note name such as "C4".'
            ) from None
        _check_hertz(hertz)


def _check_hertz(hertz: float) -> None:
    if not _LOWEST_HERTZ <= hertz <= _HIGHEST_HERTZ:
        raise ValueError(
            f'note frequency {hertz} Hz is outside the supported range ({_LOWEST_HERTZ:g} Hz '
            f'to {_HIGHEST_HERTZ / 1000:g} kHz). Use a frequency in that range, a MIDI number '
            f'or a note name such as "C4".'
        )


_LEVEL_NAME = 'audio.level'
_BEAT_NAME = 'audio.beat'

_RETENTION_SECONDS: Final = 60.0
"""How long after a recorded sound ends it is kept for a ``render_sound()`` that is late."""

_MOST_RECORDINGS: Final = 10000
"""The most recorded sounds kept at once; the oldest go first."""

_CACHED_SOUNDS: Final = 32
"""How many synthesized sounds a canvas without a device keeps for the next render."""

_RELEASE_SECONDS: Final = 1.0
"""How long an instrument may ring on after a note ends, for deciding what a window holds."""


@dataclasses.dataclass(frozen=True, slots=True)
class _Recording:
    """One sound played on a canvas without a device: a description, not samples."""

    start_seconds: float
    end_seconds: float
    key: tuple[object, ...]
    # The object whose identity is part of the key, kept so a cached sound is only reused
    # for that same object and never for a later one that happens to get its address.
    source: object
    synthesize: Callable[[], TerminalSound]
    volume: float


class AudioDevice:
    """
    The canvas's sound: notes, melodies and sounds to play, a musical clock, and the
    microphone.

    Get it from [`Canvas.audio`][xnano.canvas.Canvas.audio]. Playing never waits. Pitches are
    MIDI note numbers or names everywhere, and the length of a beat follows the canvas's
    [`bpm`][xnano.canvas.Canvas.bpm].

    Where the sound goes depends on the canvas. A canvas that runs by itself (on the screen,
    or created with ``realtime=True``) plays on this computer's sound output: the sound is
    rendered on your thread and handed to the canvas's own loop, which owns the device. A
    canvas from ``new()`` has no device and a clock you move, so it records what is played
    instead, and [`render_sound`][xnano.audio.AudioDevice.render_sound] turns the recording
    into a sound, step by step, the same on every run.

    The microphone level and the musical beat are expressions, so they drive anything an
    expression can: a position, a size, a color, an effect.

    Attributes:
        is_available: Whether sound can be played: always on a canvas without a device, and
            when this computer has a sound output device otherwise.
        is_offline: Whether this canvas records sound instead of playing it on a device.
        beat: The musical clock's position in beats, as an expression.
        level: The microphone's current level from 0.0 to 1.0, as an expression.

    Examples:
        ```python
        import xnano

        with xnano.new(width=20, height=3) as canvas:
            meter = canvas.write('#', y=1)
            meter.x = canvas.audio.level * 19
            level = canvas.inspect(canvas.audio.level)
            assert 0.0 <= level <= 1.0
            assert canvas.audio.is_offline
        ```
    """

    def __init__(self, canvas: Canvas[object, object]) -> None:
        """
        Create the canvas's audio. Use ``canvas.audio`` instead of calling this.

        Args:
            canvas: The canvas the audio belongs to.
        """
        self._canvas = canvas
        self._lock = threading.Lock()
        self._player: TerminalAudioPlayer | None = None
        self._microphone: TerminalMicrophone | None = None
        self._unavailable: set[str] = set()
        self._is_held = False
        self._level = _external(_LEVEL_NAME, True)
        self._beat = _external(_BEAT_NAME, True)
        self._recordings: list[_Recording] = []
        self._rendered_until = canvas.time.elapsed
        self._synthesized: collections.OrderedDict[
            tuple[object, ...], tuple[object, TerminalSound]
        ] = collections.OrderedDict()
        # The musical clock of a canvas without a device: where it started, at what tempo,
        # and the beat it stood at while it was paused.
        self._clock_origin_seconds: float | None = None
        self._clock_bpm = canvas.bpm
        self._paused_beat = 0.0

    # -- availability -------------------------------------------------------------------

    @property
    def is_offline(self) -> bool:
        """Whether this canvas records sound instead of playing it on a device."""
        return not self._canvas._is_realtime

    @property
    def is_available(self) -> bool:
        """Whether sound can be played: always without a device, otherwise when one exists."""
        return self.is_offline or TerminalAudioPlayer.is_available()

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

        On a canvas without a device the sound is recorded at the canvas's current time and
        nothing is synthesized until [`render_sound`][xnano.audio.AudioDevice.render_sound]
        asks for it; the arguments are still checked here.

        Args:
            source: What to play: an [`Audio`][xnano.Audio], a
                [`TerminalSound`][xnano_audio.TerminalSound], a
                [`TerminalNote`][xnano_audio.TerminalNote], a
                [`TerminalMelody`][xnano_audio.TerminalMelody], a note name (``'C#4'``),
                a MIDI note number (``60``) or a frequency in hertz. Text with spaces is a
                melody at the canvas's tempo: ``'C4 E4 G4:2 rest C5+E5+G5'`` plays notes one
                beat each, ``:2`` holds one for two beats, ``rest`` is a silence, ``+``
                joins a chord and ``|`` marks a bar.
            instrument: A built-in instrument for notes and melodies, from
                [`instrument_names`][xnano_audio.instrument_names]. A sound is played as
                it is.
            duration_milliseconds: How long a note name, number or frequency is held.
            velocity: How hard a note name, number or frequency is played, 0.0 to 1.0.
            effects: Effects applied after the instrument, or to a sound as it is played.
            volume: Playback gain, 0.0 to 1.0.
            pan: Stereo position from -1.0 (left) to 1.0 (right). A recording is mono.
            at_beat: Start when the musical clock reaches this beat. The clock is started if
                it is not running.

        Raises:
            TerminalAudioUnavailableError: The canvas plays on a device, and this computer has
                no sound output device.
            ValueError: An argument is out of range, or the instrument is unknown.

        Examples:
            ```python
            import xnano
            from xnano_audio import TerminalNote

            with xnano.new(width=8, height=1) as canvas:
                canvas.audio.play('C4')
                canvas.audio.play(64, instrument='bell')
                canvas.audio.play(TerminalNote('G4', duration_beats=0.5))
                canvas.audio.play('C4 E4 G4:2 rest C5+E5+G5')
                canvas.step(delta_seconds=0.5)
                assert canvas.audio.render_sound().duration_milliseconds == 500.0
            ```
        """
        canvas = self._canvas
        canvas._require_open()
        _check_play_arguments(
            source,
            duration_milliseconds=duration_milliseconds,
            effects=effects,
            pan=pan,
            at_beat=at_beat,
        )
        if self.is_offline:
            self._record(
                source,
                instrument=instrument,
                duration_milliseconds=duration_milliseconds,
                velocity=velocity,
                effects=effects,
                volume=volume,
                at_beat=at_beat,
            )
            return
        if not TerminalAudioPlayer.is_available():
            raise TerminalAudioUnavailableError(
                'AudioDevice.play needs a sound output device, but this computer has none that '
                'can be opened. Check canvas.audio.is_available before playing, or play on a '
                'canvas from xnano.new(), which records the sound for render_sound().'
            )
        sound = self._sound(
            source,
            instrument=instrument,
            duration_milliseconds=duration_milliseconds,
            velocity=velocity,
            effects=effects,
        )
        canvas._host.post(lambda: self._play_on_loop(sound, volume, pan, at_beat))

    def _sound(
        self,
        source: Playable,
        *,
        instrument: InstrumentName,
        duration_milliseconds: int,
        velocity: float,
        effects: list[TerminalAudioEffect] | None,
    ) -> TerminalSound:
        bpm = self._canvas.bpm
        if isinstance(source, Audio):
            source = source.sound
        if isinstance(source, TerminalSound):
            return source.with_effects(effects) if effects else source
        if isinstance(source, TerminalNote):
            melody = TerminalMelody(
                [source.with_start_beats(0.0)],
                tempo_map=TerminalTempoMap(bpm),
            )
            return melody.render(instrument, effects=effects)
        if isinstance(source, TerminalMelody):
            return source.render(instrument, effects=effects)
        if isinstance(source, str) and _is_melody_text(source):
            return _parse_melody(source, bpm).render(instrument, effects=effects)
        return render_note(
            instrument,
            source,
            duration_milliseconds=duration_milliseconds,
            velocity=velocity,
            effects=effects,
        )

    def _record(
        self,
        source: Playable,
        *,
        instrument: InstrumentName,
        duration_milliseconds: int,
        velocity: float,
        effects: list[TerminalAudioEffect] | None,
        volume: float,
        at_beat: int | None,
    ) -> None:
        """Remember what was played and when, without synthesizing it."""
        if instrument not in instrument_names():
            raise ValueError(
                f'{instrument!r} is not an instrument. Use one of: '
                f'{", ".join(instrument_names())}.'
            )
        if not 0.0 <= velocity <= 1.0:
            raise ValueError(
                f'velocity must be from 0.0 to 1.0, but was {velocity!r}. Use 0.8 for an '
                f'ordinary note.'
            )
        if not 0.0 <= volume <= 1.0:
            raise ValueError(
                f'volume must be from 0.0 to 1.0, but was {volume!r}. Use 1.0 for full volume.'
            )
        bpm = self._canvas.bpm
        if isinstance(source, Audio):
            source = source.sound
        # Melody text and plain pitches are keyed by their value; objects by their identity.
        key_source: object = source
        if isinstance(source, TerminalSound):
            length = source.duration_milliseconds / 1000.0
        elif isinstance(source, TerminalNote):
            length = source.duration_beats * 60.0 / bpm + _RELEASE_SECONDS
        elif isinstance(source, TerminalMelody):
            length = source.duration_seconds + _RELEASE_SECONDS
        elif isinstance(source, str) and _is_melody_text(source):
            source = _parse_melody(source, bpm)
            length = source.duration_seconds + _RELEASE_SECONDS
        else:
            # A note name: building a note checks it. Numbers were checked by play().
            if isinstance(source, str) and not source.strip().lower().endswith('hz'):
                TerminalNote(cast('Pitch', source))
            length = duration_milliseconds / 1000.0 + _RELEASE_SECONDS
        effect_names = tuple(repr(effect) for effect in effects or ())
        is_keyed_by_identity = isinstance(
            key_source, (TerminalSound, TerminalNote, TerminalMelody)
        )
        key: tuple[object, ...] = (
            id(key_source) if is_keyed_by_identity else key_source,
            instrument,
            velocity,
            duration_milliseconds,
            bpm,
            effect_names,
        )
        captured = source

        def synthesize() -> TerminalSound:
            return self._sound(
                captured,
                instrument=instrument,
                duration_milliseconds=duration_milliseconds,
                velocity=velocity,
                effects=effects,
            )

        now = self._canvas.time.elapsed
        start = now
        if at_beat is not None:
            if self._clock_origin_seconds is None:
                self._start_offline_clock(now)
            origin = cast('float', self._clock_origin_seconds)
            start = max(now, origin + at_beat * 60.0 / self._clock_bpm)
        recording = _Recording(
            start,
            start + length,
            key,
            key_source if is_keyed_by_identity else None,
            synthesize,
            volume,
        )
        with self._lock:
            horizon = now - _RETENTION_SECONDS
            recordings = [
                item for item in self._recordings if item.end_seconds >= horizon
            ]
            recordings.append(recording)
            if len(recordings) > _MOST_RECORDINGS:
                recordings = recordings[-_MOST_RECORDINGS:]
            self._recordings = recordings

    def render_sound(self) -> TerminalSound:
        """
        Turn what was played since the previous call into one sound, and forget it.

        The sound covers the canvas time from the previous ``render_sound()`` (or from when
        the audio was first used) up to now, so calling it after every
        [`step`][xnano.canvas.Canvas.step] gives the sound of each step. Everything played in
        that time is synthesized and mixed (limited to -1.0 to 1.0, mono); a note that rings
        on past the end continues in the next call. A second call at the same time returns
        an empty instant of silence, because the first one took the sound. Sounds that
        ended more than 60 seconds of canvas time ago are not kept, so a canvas that has not
        been asked for longer than that returns the last 60 seconds.

        Returns:
            The [`TerminalSound`][xnano_audio.TerminalSound] of that time.

        Raises:
            TerminalError: The canvas plays on a device, which does not record.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=1, fps=10) as canvas:
                canvas.audio.play('C4', instrument='bell')
                canvas.step()
                sound = canvas.audio.render_sound()
                assert sound.duration_milliseconds == 100.0
                assert max(abs(sample) for sample in sound.samples()) > 0.0
            ```
        """
        from xnano.errors import TerminalError

        canvas = self._canvas
        canvas._require_open()
        if not self.is_offline:
            raise TerminalError(
                'This canvas plays sound on a device, so there is no recording to render. '
                'render_sound() reads the sound of a canvas from xnano.new(), whose clock you '
                'move.'
            )
        now = canvas.time.elapsed
        with self._lock:
            start = self._rendered_until
            self._rendered_until = now
            playing = [
                item
                for item in self._recordings
                if item.start_seconds < now and item.end_seconds > start
            ]
            self._recordings = [
                item for item in self._recordings if item.end_seconds > now
            ]
        duration = now - start
        if duration <= 0.0:
            return TerminalSound.from_samples([0.0])
        layers = [
            (self._synthesized_sound(item), item.start_seconds, item.volume)
            for item in playing
        ]
        return TerminalSound.mix(layers, duration_seconds=duration, start_seconds=start)

    def _synthesized_sound(self, recording: _Recording) -> TerminalSound:
        cached = self._synthesized.get(recording.key)
        if cached is not None and cached[0] is recording.source:
            self._synthesized.move_to_end(recording.key)
            return cached[1]
        sound = recording.synthesize()
        self._synthesized[recording.key] = (recording.source, sound)
        self._synthesized.move_to_end(recording.key)
        if len(self._synthesized) > _CACHED_SOUNDS:
            self._synthesized.popitem(last=False)
        return sound

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

    def _apply_tempo(self) -> None:
        """Follow a change of the canvas's bpm. Runs on the canvas's loop."""
        bpm = self._canvas.bpm
        origin = self._clock_origin_seconds
        if origin is not None:
            now = self._canvas.time.elapsed
            beat = (now - origin) * self._clock_bpm / 60.0
            self._clock_origin_seconds = now - beat * 60.0 / bpm
        self._clock_bpm = bpm
        player = self._player
        if player is not None:
            player.set_tempo(bpm)

    @property
    def beat(self) -> NumericExpression:
        """
        The musical clock's position in beats, as an expression.

        It stays at ``0`` until the clock is started with
        [`start`][xnano.audio.AudioDevice.start] or a sound is played with ``at_beat``.

        Examples:
            ```python
            import xnano

            with xnano.new(width=20, height=2) as canvas:
                ball = canvas.write('o')
                ball.x = (canvas.audio.beat % 1) * 19
                canvas.audio.start()
                canvas.step(delta_seconds=0.25)
                assert canvas.inspect(canvas.audio.beat) == 0.5
            ```
        """
        return self._beat

    def _start_offline_clock(self, now: float) -> None:
        self._clock_bpm = self._canvas.bpm
        self._clock_origin_seconds = now - self._paused_beat * 60.0 / self._clock_bpm

    def start(self) -> None:
        """Start the musical clock."""
        canvas = self._canvas
        canvas._require_open()
        if self.is_offline:
            if self._clock_origin_seconds is None:
                self._start_offline_clock(canvas.time.elapsed)
            return
        canvas._host.post(self._start_on_loop)

    def _start_on_loop(self) -> None:
        player = self._open_player()
        if player is not None and not player.is_clock_running:
            player.start_clock()

    def resume(self) -> None:
        """Let the musical clock run on from where [`pause`][xnano.audio.AudioDevice.pause] left it."""
        self.start()

    def _hold(self) -> None:
        """Pause the musical clock because the canvas stopped. Runs on the canvas's loop."""
        if self.is_offline:
            self._is_held = self._clock_origin_seconds is not None
            if self._is_held:
                self._pause_offline_clock()
            return
        player = self._player
        self._is_held = player is not None and player.is_clock_running
        if self._is_held and player is not None:
            player.pause_clock()

    def _release(self) -> None:
        """Run the musical clock again if [`_hold`][xnano.audio.AudioDevice._hold] paused it."""
        if self._is_held:
            if self.is_offline:
                self._start_offline_clock(self._canvas.time.elapsed)
            elif self._player is not None:
                self._player.start_clock()
        self._is_held = False

    def _pause_offline_clock(self) -> None:
        origin = self._clock_origin_seconds
        if origin is not None:
            now = self._canvas.time.elapsed
            self._paused_beat = (now - origin) * self._clock_bpm / 60.0
            self._clock_origin_seconds = None

    def pause(self) -> None:
        """Pause the musical clock, keeping its position."""
        canvas = self._canvas
        canvas._require_open()
        if self.is_offline:
            self._pause_offline_clock()
            return
        canvas._host.post(lambda: self._player and self._player.pause_clock())

    def stop(self) -> None:
        """Stop the musical clock and return it to the first beat."""
        canvas = self._canvas
        canvas._require_open()
        if self.is_offline:
            self._clock_origin_seconds = None
            self._paused_beat = 0.0
            return
        canvas._host.post(lambda: self._player and self._player.stop_clock())

    # -- the microphone -----------------------------------------------------------------

    @property
    def level(self) -> NumericExpression:
        """
        The microphone's current level from 0.0 to 1.0, as an expression.

        Reading it opens the default input device the first time a frame evaluates it.
        Without an input device, without permission, or on a canvas without a device, the
        level is ``0``.
        """
        return self._level

    def level_history(self, count: int) -> list[float]:
        """
        Return the last ``count`` microphone levels, oldest first.

        Args:
            count: How many levels to return.
        """
        canvas = self._canvas
        canvas._require_open()

        def read() -> list[float]:
            microphone = self._open_microphone()
            return [] if microphone is None else microphone.level_history(count)

        return canvas._host.call(read)

    # -- devices, on the canvas's loop --------------------------------------------------

    def _open_player(self) -> TerminalAudioPlayer | None:
        if self._player is None and 'player' not in self._unavailable:
            try:
                self._player = TerminalAudioPlayer(beats_per_minute=self._canvas.bpm)
            except TerminalAudioError:
                self._unavailable.add('player')
        return self._player

    def _open_microphone(self) -> TerminalMicrophone | None:
        if self.is_offline:
            return None
        if self._microphone is None and 'microphone' not in self._unavailable:
            try:
                self._microphone = TerminalMicrophone()
            except TerminalAudioError:
                self._unavailable.add('microphone')
        return self._microphone

    def _bind(self, runtime: _core.Runtime) -> None:
        """Let expressions read the level and the beat. Runs on the canvas's loop."""
        runtime.provide(_LEVEL_NAME, self._read_level)
        runtime.provide(_BEAT_NAME, self._read_beat)

    def _read_level(self) -> float:
        microphone = self._open_microphone()
        return 0.0 if microphone is None else microphone.level

    def _read_beat(self) -> float:
        if self.is_offline:
            origin = self._clock_origin_seconds
            if origin is None:
                return self._paused_beat
            return (self._canvas.time.elapsed - origin) * self._clock_bpm / 60.0
        player = self._player
        return 0.0 if player is None else player.beat

    def _close(self) -> None:
        """Release the devices. Runs on the canvas's loop."""
        for device in (self._player, self._microphone):
            if device is not None:
                device.close()
        self._player = None
        self._microphone = None
