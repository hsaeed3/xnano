"""
xnano.audio

[`xnano-audio`](https://github.com/hsaeed3/xnano/tree/main/packages/xnano-audio) based components and
utilities for sound playback and composition. Needs the optional ``audio`` extra:
``pip install "xnano[audio]"``.
"""

from __future__ import annotations

import collections
import collections.abc
import dataclasses
import math
import threading
import time
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Final, TypeAlias, cast

from xnano import _optional, symbols
from xnano._customize import normalize_effect
from xnano._media import Audio
from xnano.music import Note, PlayHandle

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
    from xnano._customize import AudioCustomization
    from xnano.canvas import Canvas
    from xnano.types import Playable, PlayableEffectSpecification

__all__ = [
    'Audio',
    'AudioDevice',
    'InstrumentName',
    'NoteName',
    'Pitch',
    'PlaySource',
    'TerminalAudioEffect',
    'TerminalAudioError',
    'TerminalAudioUnavailableError',
    'TerminalMelody',
    'TerminalNote',
    'TerminalSound',
    'instrument_names',
]

PlaySource: TypeAlias = (
    'Playable | int | float | TerminalSound | TerminalNote | TerminalMelody'
)
"""
Anything [`AudioDevice.play`][xnano.audio.AudioDevice.play] accepts: a
[`Playable`][xnano.types.Playable] (a [`Note`][xnano.Note], an [`Audio`][xnano.Audio], a symbol name, a
note name such as ``'C#4'``, melody text, or a sequence of those), a MIDI note number such as
``60``, a frequency in hertz, or a rendered sound, note or melody from ``xnano-audio``.
"""


def _parse_melody(
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
    beats: float | None,
    bpm: float,
    pan: float,
    at_beat: int | None,
    volume: float,
) -> None:
    """Raise the error a bad ``play()`` argument deserves, where ``play()`` was called."""
    if not -1.0 <= pan <= 1.0:
        raise ValueError(
            f'pan must be between -1.0 (left) and 1.0 (right), but was {pan!r}. Use 0.0 for '
            f'the center.'
        )
    if at_beat is not None and (
        isinstance(at_beat, bool) or not isinstance(at_beat, int)
    ):
        raise TypeError(
            f'at_beat must be a whole number of beats, but was {at_beat!r}. Pass the beat of '
            f'the musical clock to start on, such as at_beat=4, or remove at_beat to start '
            f'now.'
        )
    if at_beat is not None and at_beat < 0:
        raise ValueError(
            f'at_beat must be 0 or more, but was {at_beat!r}. Pass the beat of the musical '
            f'clock to start on, or remove at_beat to start now.'
        )
    if not 0.0 <= volume <= 1.0:
        raise ValueError(
            f'volume must be from 0.0 to 1.0, but was {volume!r}. Use 1.0 for full volume.'
        )
    if beats is not None:
        _milliseconds(beats, bpm)
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


def _milliseconds(beats: float, bpm: float) -> int:
    """The length in milliseconds of ``beats`` at ``bpm``, or the error that explains why not."""
    if (
        isinstance(beats, bool)
        or not isinstance(beats, (int, float))
        or not math.isfinite(beats)
    ):
        raise ValueError(
            f'beats must be a number of beats such as 1.0, but was {beats!r}. Use 0.5 for '
            f'half a beat.'
        )
    milliseconds = round(beats * 60000.0 / bpm)
    if not 1 <= milliseconds <= _LONGEST_NOTE_MILLISECONDS:
        longest = _LONGEST_NOTE_MILLISECONDS / 60000.0 * bpm
        raise ValueError(
            f'beats must be a length from a thousandth of a second to a minute, but {beats!r} '
            f'beats at {bpm:g} bpm is {milliseconds} milliseconds. Use more than 0 and at '
            f'most {longest:g} beats at this tempo.'
        )
    return milliseconds


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


@dataclasses.dataclass(frozen=True, slots=True)
class _Options:
    """The options of one ``play()`` call that override what a note carries."""

    instrument: InstrumentName | None
    beats: float | None
    velocity: float | None
    effects: tuple[TerminalAudioEffect, ...] | None
    extra_effects: tuple[TerminalAudioEffect, ...] = ()
    """Effects of the running hook, added to a note's own effects or to the call's."""


@dataclasses.dataclass(frozen=True, slots=True)
class _Planned:
    """One sound that a ``play()`` call will make: when it starts and how to make it."""

    offset_seconds: float
    length_seconds: float
    key: tuple[object, ...]
    anchor: object | None
    synthesize: Callable[[], TerminalSound]


_INSTRUMENTS: Final = frozenset(instrument_names())
"""Every built-in instrument name, read once."""


def _check_instrument(instrument: str) -> None:
    if instrument not in _INSTRUMENTS:
        raise ValueError(
            f'{instrument!r} is not an instrument. Use one of: '
            f'{", ".join(instrument_names())}.'
        )


def _check_velocity(velocity: float) -> None:
    if not 0.0 <= velocity <= 1.0:
        raise ValueError(
            f'velocity must be from 0.0 to 1.0, but was {velocity!r}. Use 0.8 for an '
            f'ordinary note.'
        )


def resolve_effects(
    effects: Sequence[PlayableEffectSpecification] | None,
) -> tuple[TerminalAudioEffect, ...]:
    """
    Turn the effects of a ``play()`` call or a note into ``TerminalAudioEffect`` objects.

    Args:
        effects: Dictionaries with a ``kind`` key such as ``{'kind': 'audio.reverb', 'mix':
            0.4}``.

    Raises:
        TypeError: An element is not such a dictionary, or names a visual effect.
    """
    if not effects:
        return ()
    resolved: list[TerminalAudioEffect] = []
    for effect in effects:
        if isinstance(effect, TerminalAudioEffect):
            resolved.append(effect)
            continue
        built = normalize_effect(effect, 'playable')
        resolved.append(cast('AudioCustomization', built).to_audio_effect())
    return tuple(resolved)


def hook_effects(canvas: Canvas[object, object]) -> tuple[TerminalAudioEffect, ...]:
    """
    The sound effects of the hook that is running right now on this thread.

    These are the effects the hook set with ``context.fx``; a sound it plays gets them too.
    Returns an empty tuple when no hook is running or the running hook set none.
    """
    run = canvas._active_run
    if run is None or not run.is_active or run.thread != threading.get_ident():
        return ()
    handle = run.handle
    state = None if handle is None else handle._effect_state
    return () if state is None else state.audio_effects()


_STANDARD_SAMPLE_RATE: Final = 44100
"""The sample rate of every synthesized sound, which a mix needs all its layers to have."""


def _at_standard_rate(sound: TerminalSound) -> TerminalSound:
    """``sound`` at 44100 Hz, so it can be mixed with synthesized sounds."""
    rate = sound.sample_rate
    if rate == _STANDARD_SAMPLE_RATE:
        return sound
    samples = sound.samples()
    count = max(1, round(len(samples) * _STANDARD_SAMPLE_RATE / rate))
    scale = (len(samples) - 1) / max(1, count - 1)
    converted: list[float] = []
    for index in range(count):
        position = index * scale
        before = int(position)
        after = min(before + 1, len(samples) - 1)
        share = position - before
        converted.append(samples[before] * (1.0 - share) + samples[after] * share)
    return TerminalSound.from_samples(converted, sample_rate=_STANDARD_SAMPLE_RATE)


def mix_planned(planned: list[_Planned]) -> TerminalSound:
    """Synthesize the sounds of a ``play()`` call and mix them on their timeline."""
    sounds = [(item.synthesize(), item.offset_seconds) for item in planned]
    if len(sounds) > 1:
        sounds = [(_at_standard_rate(sound), offset) for sound, offset in sounds]
    if len(sounds) == 1:
        return sounds[0][0]
    end = max(offset + sound.duration_milliseconds / 1000.0 for sound, offset in sounds)
    return TerminalSound.mix(
        [(sound, offset, 1.0) for sound, offset in sounds], duration_seconds=end
    )


def _known_sound_names() -> str:
    names = sorted(
        name
        for name, value in symbols._registry.items()
        if isinstance(value, (Note, Audio))
    )
    return ', '.join(repr(name) for name in names) if names else 'none yet'


def plan_call(
    source: object,
    *,
    bpm: float,
    instrument: InstrumentName | None,
    beats: float | None,
    velocity: float | None,
    effects: Sequence[PlayableEffectSpecification] | None,
    volume: float,
    pan: float,
    at_beat: int | None,
    extra_effects: tuple[TerminalAudioEffect, ...] = (),
) -> list[_Planned]:
    """
    Check the arguments of a ``play()`` call and work out every sound it makes.

    Returns:
        The sounds, with their start times in seconds from the start of the call.
    """
    _check_play_arguments(
        source, beats=beats, bpm=bpm, pan=pan, at_beat=at_beat, volume=volume
    )
    if instrument is not None:
        _check_instrument(instrument)
    if velocity is not None:
        _check_velocity(velocity)
    options = _Options(
        instrument,
        beats,
        velocity,
        None if effects is None else resolve_effects(effects),
        extra_effects,
    )
    planned: list[_Planned] = []
    _plan_into(planned, source, options, bpm, 0.0)
    return planned


def _plan_into(
    planned: list[_Planned], source: object, options: _Options, bpm: float, offset: float
) -> float:
    """Add the sounds of ``source`` starting ``offset`` seconds in; return where it ends."""
    if isinstance(source, str):
        registered = symbols._registry.get(source)
        if registered is not None:
            if not isinstance(registered, (Note, Audio)):
                raise TypeError(
                    f'{source!r} is a {type(registered).__name__} symbol, and play() makes '
                    f'sound from a Note or an Audio. Known sound symbols: '
                    f'{_known_sound_names()}.'
                )
            return _plan_into(planned, registered, options, bpm, offset)
    if isinstance(source, Note):
        return _plan_pitches(
            planned,
            source.pitch if isinstance(source.pitch, tuple) else (source.pitch,),
            options,
            bpm,
            offset,
            beats=source.beats,
            instrument=source.instrument,
            velocity=source.velocity,
            effects=resolve_effects(source.effects),
        )
    if isinstance(source, Audio):
        return _plan_into(planned, source.sound, options, bpm, offset)
    if isinstance(source, TerminalSound):
        sound = source
        effects = (options.effects or ()) + options.extra_effects
        length = sound.duration_milliseconds / 1000.0
        planned.append(
            _Planned(
                offset,
                length,
                (id(sound), tuple(repr(effect) for effect in effects)),
                sound,
                lambda: sound.with_effects(list(effects)) if effects else sound,
            )
        )
        return offset + length
    if isinstance(source, TerminalNote):
        melody = TerminalMelody(
            [source.with_start_beats(0.0)], tempo_map=TerminalTempoMap(bpm)
        )
        return _plan_melody(planned, melody, source, options, bpm, offset, source)
    if isinstance(source, TerminalMelody):
        return _plan_melody(planned, source, source, options, bpm, offset, source)
    if isinstance(source, str) and _is_melody_text(source):
        beats = options.beats if options.beats is not None else 1.0
        melody = _parse_melody(source, bpm, beats)
        return _plan_melody(planned, melody, source, options, bpm, offset, None, beats)
    if isinstance(source, (str, int, float)):
        _check_pitch_text(source)
        return _plan_pitches(planned, (source,), options, bpm, offset)
    if isinstance(source, collections.abc.Sequence) and not isinstance(
        source, (bytes, bytearray)
    ):
        if len(source) == 0:
            raise ValueError(
                'play() was given an empty sequence, so there is nothing to play. Pass '
                'notes such as [note("C4"), note("E4")].'
            )
        for element in source:
            offset = _plan_into(planned, element, options, bpm, offset)
        return offset
    if hasattr(source, '__xnano_play__'):
        raise TypeError(
            f'Cannot play a {type(source).__name__} here. It has an __xnano_play__ method, '
            f'which needs a canvas to run in, and this call has none. Play it with '
            f'canvas.play(component), or call xnano.play(component) while a canvas is '
            f'running.'
        )
    missing = (
        ' It has an __xnano_render__ method but no __xnano_play__ method, so it can be '
        'written with canvas.write() but not played.'
        if hasattr(source, '__xnano_render__')
        else ' It has no __xnano_play__ method.'
    )
    raise TypeError(
        f'Cannot play a {type(source).__name__}.{missing} Play a Note, an Audio, an object '
        f'with __xnano_play__, a symbol name, a note name such as "C4", melody text such as '
        f'"C4 E4 G4:2", a MIDI number, a frequency, or a sequence of those.'
    )


def _check_pitch_text(source: str | int | float) -> None:
    """Raise the error for a ``str`` that is no symbol, note name or melody text."""
    if isinstance(source, (int, float)) or source.strip().lower().endswith('hz'):
        return
    try:
        TerminalNote(cast('Pitch', source))
    except ValueError:
        raise ValueError(
            f'{source!r} is not a known sound symbol, a note name or melody text. '
            f'Known sound symbols: {_known_sound_names()}. A note name is a letter, an '
            f'optional # or b, and an octave, such as "C4" or "Bb3"; melody text is notes '
            f'separated by spaces, such as "C4 E4 G4:2"; register a sound with '
            f'symbol={source!r} when you create it.'
        ) from None


def _plan_pitches(
    planned: list[_Planned],
    pitches: tuple[object, ...],
    options: _Options,
    bpm: float,
    offset: float,
    *,
    beats: float = 1.0,
    instrument: InstrumentName = 'piano',
    velocity: float = 0.8,
    effects: tuple[TerminalAudioEffect, ...] = (),
) -> float:
    """Add one note, or one chord when there are several pitches."""
    beats = options.beats if options.beats is not None else beats
    instrument = options.instrument if options.instrument is not None else instrument
    velocity = options.velocity if options.velocity is not None else velocity
    effects = (
        options.effects if options.effects is not None else effects
    ) + options.extra_effects
    _check_instrument(instrument)
    _check_velocity(velocity)
    milliseconds = _milliseconds(beats, bpm)
    effect_names = tuple(repr(effect) for effect in effects)
    key = ('pitches', pitches, instrument, velocity, milliseconds, effect_names)

    def synthesize() -> TerminalSound:
        sounds = [
            render_note(
                instrument,
                cast('Pitch', pitch),
                duration_milliseconds=milliseconds,
                velocity=velocity,
                effects=list(effects) or None,
            )
            for pitch in pitches
        ]
        if len(sounds) == 1:
            return sounds[0]
        longest = max(sound.duration_milliseconds for sound in sounds) / 1000.0
        gain = 1.0 / math.sqrt(len(sounds))
        return TerminalSound.mix(
            [(sound, 0.0, gain) for sound in sounds], duration_seconds=longest
        )

    length = milliseconds / 1000.0
    planned.append(_Planned(offset, length + _RELEASE_SECONDS, key, None, synthesize))
    return offset + length


def _plan_melody(
    planned: list[_Planned],
    melody: TerminalMelody,
    identity: object,
    options: _Options,
    bpm: float,
    offset: float,
    anchor: object | None,
    default_beats: float = 1.0,
) -> float:
    """Add a melody, which plays its own notes at their own lengths."""
    instrument = options.instrument if options.instrument is not None else 'piano'
    _check_instrument(instrument)
    effects = (options.effects or ()) + options.extra_effects
    effect_names = tuple(repr(effect) for effect in effects)
    key = (
        'melody',
        id(identity) if anchor is not None else identity,
        instrument,
        bpm,
        default_beats,
        effect_names,
    )
    length = melody.duration_seconds
    planned.append(
        _Planned(
            offset,
            length + _RELEASE_SECONDS,
            key,
            anchor,
            lambda: melody.render(instrument, effects=list(effects) or None),
        )
    )
    return offset + length


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
        self._pruned_at = canvas.time.elapsed
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
        """
        Whether this canvas records sound instead of playing it on a device.

        It is the opposite of [`Time.is_realtime`][xnano.time.Time.is_realtime]: a canvas that
        runs on the wall clock plays on a device, and one whose clock you move records.
        """
        return not self._canvas._is_realtime

    @property
    def is_available(self) -> bool:
        """Whether sound can be played: always without a device, otherwise when one exists."""
        return self.is_offline or TerminalAudioPlayer.is_available()

    # -- playing ------------------------------------------------------------------------

    def play(
        self,
        source: PlaySource,
        *,
        instrument: InstrumentName | None = None,
        beats: float | None = None,
        velocity: float | None = None,
        effects: Sequence[PlayableEffectSpecification] | None = None,
        volume: float = 1.0,
        pan: float = 0.0,
        at_beat: int | None = None,
    ) -> PlayHandle:
        """
        Play something that makes sound, and return at once.

        ``source`` is a [`Note`][xnano.Note], an [`Audio`][xnano.Audio], the name of a
        registered symbol, a note name such as ``'C#4'``, a MIDI number such as ``60``, a
        frequency in hertz, melody text, or a sequence of those that plays one after another.
        A ``str`` is a symbol name first; if no symbol has that name it is a note name, a
        frequency such as ``'440hz'`` or melody text. Melody text has spaces, ``:2`` holds a
        note for two beats, ``rest`` is a silence, ``+`` joins a chord and ``|`` marks a bar:
        ``'C4 E4 G4:2 rest C5+E5+G5'``. An option you pass here replaces the same value on a
        ``Note``, so ``play(note('C4'), instrument='violin')`` plays the violin.

        On a canvas without a device the sound is recorded at the canvas's current time and
        nothing is synthesized until [`render_sound`][xnano.audio.AudioDevice.render_sound]
        asks for it; the arguments are still checked here.

        Args:
            source: What to play.
            instrument: A built-in instrument for notes and melodies, from
                [`instrument_names`][xnano_audio.instrument_names]; ``'piano'`` unless a
                ``Note`` says otherwise. A sound is played as it is.
            beats: How long a note name, number, frequency or ``Note`` is held, in beats at
                the canvas's tempo, and how long melody text holds a note that gives no length
                of its own. ``1.0`` unless a ``Note`` says otherwise.
            velocity: How hard a note is played, 0.0 to 1.0; ``0.8`` unless a ``Note`` says
                otherwise.
            effects: Effects applied after the instrument, or to a sound as it is played,
                as dictionaries such as ``{'kind': 'audio.reverb'}``. A hook that called
                ``context.fx`` with a sound effect adds its effects to every sound it
                plays.
            volume: Playback gain, 0.0 to 1.0.
            pan: Stereo position from -1.0 (left) to 1.0 (right). A recording is mono.
            at_beat: Start when the musical clock reaches this beat. The clock is started if
                it is not running.

        Returns:
            A [`PlayHandle`][xnano.music.PlayHandle] that tells when the sound is over.

        Raises:
            TerminalAudioUnavailableError: The canvas plays on a device, and this computer has
                no sound output device.
            ValueError: An argument is out of range, the instrument is unknown, or a ``str``
                is neither a symbol, a note name nor melody text. The message lists the known
                sound symbols.
            TypeError: ``source`` cannot be played, or an effect is not an audio effect.

        Examples:
            ```python
            import xnano

            with xnano.new(width=8, height=1) as canvas:
                canvas.audio.play('C4')
                canvas.audio.play(64, instrument='bell')
                canvas.audio.play(xnano.note('G4', beats=0.5))
                canvas.audio.play('C4 E4 G4:2 rest C5+E5+G5')
                canvas.step(delta_seconds=0.5)
                assert canvas.audio.render_sound().duration_milliseconds == 500.0
            ```
        """
        canvas = self._canvas
        canvas._require_open()
        planned = plan_call(
            source,
            bpm=canvas.bpm,
            instrument=instrument,
            beats=beats,
            velocity=velocity,
            effects=effects,
            volume=volume,
            pan=pan,
            at_beat=at_beat,
            extra_effects=hook_effects(canvas),
        )
        if self.is_offline:
            return self._record(planned, volume=volume, at_beat=at_beat)
        if not TerminalAudioPlayer.is_available():
            raise TerminalAudioUnavailableError(
                'AudioDevice.play needs a sound output device, but this computer has none that '
                'can be opened. Check canvas.audio.is_available before playing, or play on a '
                'canvas from xnano.new(), which records the sound for render_sound().'
            )
        sound = mix_planned(planned)
        handle = PlayHandle(
            clock=time.monotonic,
            end_seconds=time.monotonic() + sound.duration_milliseconds / 1000.0,
        )
        canvas._host.post(
            lambda: handle._is_removed or self._play_on_loop(sound, volume, pan, at_beat)
        )
        return handle

    def _record(
        self, planned: list[_Planned], *, volume: float, at_beat: int | None
    ) -> PlayHandle:
        """Remember what was played and when, without synthesizing it."""
        canvas = self._canvas
        now = canvas.time.elapsed
        start = now
        if at_beat is not None:
            if self._clock_origin_seconds is None:
                self._start_offline_clock(now)
            origin = cast('float', self._clock_origin_seconds)
            start = max(now, origin + at_beat * 60.0 / self._clock_bpm)
        recordings = [
            _Recording(
                start + item.offset_seconds,
                start + item.offset_seconds + item.length_seconds,
                item.key,
                item.anchor,
                item.synthesize,
                volume,
            )
            for item in planned
        ]
        with self._lock:
            if not 0.0 <= now - self._pruned_at < 1.0:
                horizon = now - _RETENTION_SECONDS
                self._recordings = [
                    item for item in self._recordings if item.end_seconds >= horizon
                ]
                self._pruned_at = now
            self._recordings.extend(recordings)
            if len(self._recordings) > _MOST_RECORDINGS:
                del self._recordings[: len(self._recordings) - _MOST_RECORDINGS]
        return PlayHandle(
            clock=lambda: canvas.time.elapsed,
            end_seconds=max(recording.end_seconds for recording in recordings),
            cancel=lambda: self._forget(recordings),
        )

    def _forget(self, recordings: list[_Recording]) -> None:
        """Drop recordings that have not finished, so the rest of them is never rendered."""
        forgotten = {id(recording) for recording in recordings}
        with self._lock:
            self._recordings = [
                item for item in self._recordings if id(item) not in forgotten
            ]

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
            start = max(self._rendered_until, now - _RETENTION_SECONDS)
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
        sound = _at_standard_rate(recording.synthesize())
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
                if canvas._time_source.is_stopped:
                    self._hold()
            return
        canvas._host.post(self._start_on_loop)

    def _start_on_loop(self) -> None:
        player = self._open_player()
        if player is not None and not player.is_clock_running:
            player.start_clock()
            if self._canvas._time_source.is_stopped:
                self._hold()

    def resume(self) -> None:
        """Let the musical clock run on from where [`pause`][xnano.audio.AudioDevice.pause] left it."""
        self.start()

    def _hold(self) -> None:
        """Pause the musical clock because the canvas stopped. Runs on the canvas's loop."""
        if self.is_offline:
            if self._clock_origin_seconds is not None:
                self._is_held = True
                self._pause_offline_clock()
            return
        player = self._player
        if player is not None and player.is_clock_running:
            self._is_held = True
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
        """
        Stop the musical clock and return it to the first beat.

        This rewinds only the musical clock. To freeze the whole canvas, including this
        clock, use [`Canvas.stop`][xnano.canvas.Canvas.stop]; it resumes from where it stood
        with [`Canvas.resume`][xnano.canvas.Canvas.resume].
        """
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
