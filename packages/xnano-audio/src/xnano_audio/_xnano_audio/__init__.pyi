"""
xnano_audio._xnano_audio

Type stubs for `xnano_audio`'s native rust-extension.

Synthesize, play and capture sound. The extension has independent synthesis, playback, capture, and streaming parts:

* **Synthesis** ([`render_note`][xnano_audio.render_note],
  [`TerminalSound`][xnano_audio.TerminalSound],
  [`TerminalAudioEffect`][xnano_audio.TerminalAudioEffect]): built-in instruments
  and effects rendered to plain samples. Needs no audio device, so it works
  everywhere (including CI).
* **Playback** ([`TerminalAudioPlayer`][xnano_audio.TerminalAudioPlayer]): plays
  sounds and instruments on the default output device, with a musical clock
  for sample-accurate timing.
* **Capture** ([`TerminalMicrophone`][xnano_audio.TerminalMicrophone]): reads the
  level of the default input device.

Synthesized sounds are computed; TerminalAudioStream decodes audio files lazily. Use
[`detect_audio_capabilities`][xnano_audio.detect_audio_capabilities] to
find out which devices this machine and build offer before opening one.

Built-in instruments:

| Pitched | Technique |
| --- | --- |
| ``piano`` | additive, stiff-string inharmonic partials |
| ``electric_piano`` | FM (Rhodes-style tine) |
| ``organ`` | additive drawbars |
| ``bell`` | FM with an inharmonic ratio; rings after release |
| ``marimba`` | sine body plus a fast overtone |
| ``guitar`` | Karplus-Strong string with a body low-pass |
| ``electric_guitar`` | Karplus-Strong through soft-clip drive |
| ``pluck`` | bright, short Karplus-Strong string |
| ``bass`` | saw + sub sine through a swept low-pass |
| ``synth`` | detuned saws, resonant filter, vibrato |
| ``pad`` | slow, wide detuned saws |
| ``strings`` | ensemble of four detuned saws |
| ``sine``, ``square``, ``saw``, ``triangle`` | plain band-limited waveforms |

| Percussive | Technique |
| --- | --- |
| ``kick`` | pitch-swept sine plus click |
| ``snare`` | tone plus high-passed noise |
| ``hihat``, ``open_hat`` | six metallic squares through a high-pass |
| ``clap`` | noise bursts through a band-pass |
| ``tom`` | pitch-swept sine landing on ``note`` |
| ``cowbell`` | two squares through a band-pass |

Percussive instruments ring for their own natural length and ignore
``duration_milliseconds``. Only ``tom`` uses ``note`` (try ``"A2"``).

Instruments are loudness-matched: at the same velocity most sit at a similar
level (about 0.12 RMS). Transient-heavy sounds (hats, cowbell, plucks) are
capped by their peaks and stay a little quieter. Velocity 1.0 never exceeds a
peak of 0.9 before effects.
"""

from collections.abc import Iterator, Sequence
from os import PathLike
from types import TracebackType
from typing import Literal, Protocol, final, overload

from xnano_audio._audio_types import InstrumentName as InstrumentName
from xnano_audio._audio_types import NoteName as NoteName
from xnano_audio._audio_types import Pitch as Pitch

__version__: str
is_optimized_build: bool
"""Whether the extension was built with optimizations. Timing a debug build says nothing."""

# Rust binding
class TerminalAudioError(RuntimeError):
    """
    Raised when an audio device or stream fails.

    Treat this (and a failed import of the package) as "audio is not
    available": SSH sessions, containers and CI usually have no audio device.
    """

# Rust binding
class TerminalAudioUnavailableError(TerminalAudioError):
    """
    Raised when an audio device is missing, or this build has no device support.

    The message says which of the two it is and how to fix it.
    """

# Rust binding
@final
class TerminalAudioCapabilities:
    """
    What audio support this build and machine offer.

    Returned by
    [`detect_audio_capabilities`][xnano_audio.detect_audio_capabilities].

    Attributes:
        has_device_support: Whether this build was compiled with audio device support.
        is_output_available: Whether a default output device exists.
        is_input_available: Whether a default input device (microphone) exists.
        output_unavailable_reason: Why output is unavailable, or ``None`` when it is available.
        input_unavailable_reason: Why input is unavailable, or ``None`` when it is available.
    """
    # Rust binding
    def __repr__(self) -> str: ...
    # Rust binding
    @property
    def has_device_support(self) -> bool:
        """
        Whether this build was compiled with audio device support.

        Builds made without the system audio libraries (for example, Linux
        without the ALSA development headers) can still synthesize sound but
        cannot play or capture it.
        """
    # Rust binding
    @property
    def is_output_available(self) -> bool:
        """Whether a default output device exists."""
    # Rust binding
    @property
    def is_input_available(self) -> bool:
        """Whether a default input device (microphone) exists."""
    # Rust binding
    @property
    def output_unavailable_reason(self) -> str | None:
        """Why output is unavailable, or ``None`` when it is available."""
    # Rust binding
    @property
    def input_unavailable_reason(self) -> str | None:
        """Why input is unavailable, or ``None`` when it is available."""
    # Rust binding
    def __eq__(self, other: object) -> bool: ...

# Rust binding
def detect_audio_capabilities() -> TerminalAudioCapabilities:
    """
    Report what audio support is available, without opening any device.

    Examples:
        ```python
        capabilities = detect_audio_capabilities()
        if capabilities.is_output_available:
            TerminalAudioPlayer().play_note("bell", "C6")
        else:
            print(capabilities.output_unavailable_reason)
        ```
    """

# Rust binding
@final
class TerminalAudioEffect:
    """
    An immutable audio effect description.

    Build one with a static constructor and pass it, in order, to
    [`render_note`][xnano_audio.render_note],
    [`TerminalSound.with_effects`][xnano_audio.TerminalSound.with_effects] or
    [`TerminalAudioPlayer.play_note`][xnano_audio.TerminalAudioPlayer.play_note].
    Effects hold no state, so one instance can be reused for any number of
    sounds.

    Every constructor raises ``ValueError`` when an argument is out of
    range.

    Attributes:
        name: The effect's kind, such as ``"reverb"``.
    """
    # Rust binding
    def __repr__(self) -> str: ...
    # Rust binding
    @staticmethod
    def bit_crush(*, bits: int = 8, downsample: int = 4) -> TerminalAudioEffect:
        """
        Lo-fi: quantize to ``bits`` and hold every ``downsample``-th sample.

        Args:
            bits: Resolution, 1 to 16. Lower is crunchier.
            downsample: Hold each value for this many samples, 1 to 256.
        """
    # Rust binding
    @staticmethod
    def distortion(*, drive: float = 4.0) -> TerminalAudioEffect:
        """
        Soft-clip (tanh) distortion.

        Args:
            drive: Input gain before clipping, 0.1 to 100. Around 1 is nearly
                clean; higher is harsher. The output is normalized.
        """
    # Rust binding
    @staticmethod
    def low_pass(
        *, cutoff: float = 1200.0, resonance: float = 0.707
    ) -> TerminalAudioEffect:
        """
        Remove frequencies above ``cutoff``.

        Args:
            cutoff: Corner frequency in hertz, 20 to 20000.
            resonance: Filter Q, 0.1 to 20. The default is flat.
        """
    # Rust binding
    @staticmethod
    def high_pass(
        *, cutoff: float = 400.0, resonance: float = 0.707
    ) -> TerminalAudioEffect:
        """
        Remove frequencies below ``cutoff``.

        Args:
            cutoff: Corner frequency in hertz, 20 to 20000.
            resonance: Filter Q, 0.1 to 20. The default is flat.
        """
    # Rust binding
    @staticmethod
    def delay(
        *, time_milliseconds: float = 250.0, feedback: float = 0.4, mix: float = 0.35
    ) -> TerminalAudioEffect:
        """
        Echoes.

        The result is longer than the input so the echoes ring out.

        Args:
            time_milliseconds: Time between echoes, 1 to 2000.
            feedback: How much of each echo is fed back, 0.0 to 0.95.
            mix: Level of the echoes against the dry sound, 0.0 to 1.0.
        """
    # Rust binding
    @staticmethod
    def reverb(
        *, room: float = 0.5, damping: float = 0.5, mix: float = 0.25
    ) -> TerminalAudioEffect:
        """
        Room reverb (Freeverb-style).

        The result is longer than the input so the tail rings out.

        Args:
            room: Room size, 0.0 to 1.0. Larger rooms ring longer.
            damping: How quickly high frequencies fade, 0.0 to 1.0.
            mix: Wet level against the dry sound, 0.0 to 1.0.
        """
    # Rust binding
    @staticmethod
    def tremolo(*, rate_hertz: float = 5.0, depth: float = 0.5) -> TerminalAudioEffect:
        """
        Amplitude wobble.

        Args:
            rate_hertz: Wobbles per second, 0.1 to 40.
            depth: 0.0 (none) to 1.0 (silent at each trough).
        """
    # Rust binding
    @property
    def name(self) -> str:
        """The effect's kind, such as ``"reverb"``."""
    # Rust binding
    def __eq__(self, other: object) -> bool: ...
    # Rust binding
    def __hash__(self) -> int: ...
    # Rust binding
    def __copy__(self) -> TerminalAudioEffect: ...
    # Rust binding
    def __deepcopy__(self, memo: object) -> TerminalAudioEffect: ...

# Rust binding
@final
class TerminalSound:
    """
    A rendered mono sound: raw samples plus their sample rate.

    Immutable. Create one with [`render_note`][xnano_audio.render_note],
    then inspect it, run it through more effects, or play it with
    [`TerminalAudioPlayer.play_sound`][xnano_audio.TerminalAudioPlayer.play_sound].
    ``len(sound)`` is the number of samples.

    Attributes:
        sample_rate: Samples per second.
        duration_milliseconds: Length in milliseconds, including any effect tail.
        peak: Largest absolute sample value, from 0.0 to 1.0.
        root_mean_square: Root-mean-square level, from 0.0 to 1.0.
    """
    # Rust binding
    def __repr__(self) -> str: ...
    # Rust binding
    @staticmethod
    def from_samples(samples: list[float], *, sample_rate: int = 44100) -> TerminalSound:
        """
        Build a sound from your own mono floats.

        This is how to add a custom instrument or waveform: generate the
        samples in Python (from numpy, call ``.tolist()``), then process and
        play them like any built-in sound.

        Args:
            samples: Values from -1.0 to 1.0; they are not rescaled.
            sample_rate: Samples per second, 8000 to 192000.

        Raises:
            ValueError: If ``samples`` is empty or contains NaN or infinity,
                or the rate is out of range.
        """
    # Rust binding
    @staticmethod
    def from_bytes(data: bytes, *, sample_rate: int = 44100) -> TerminalSound:
        """
        Build a sound from little-endian 32-bit float bytes.

        The inverse of [`to_bytes`][xnano_audio.TerminalSound.to_bytes].

        Raises:
            ValueError: If ``data`` is empty or its length is not a multiple
                of 4, it contains NaN or infinity, or the rate is out of range.
        """
    # Rust binding
    @property
    def sample_rate(self) -> int:
        """Samples per second."""
    # Rust binding
    @property
    def duration_milliseconds(self) -> float:
        """Length in milliseconds, including any effect tail."""
    # Rust binding
    @property
    def peak(self) -> float:
        """Largest absolute sample value, from 0.0 to 1.0."""
    # Rust binding
    @property
    def root_mean_square(self) -> float:
        """Root-mean-square level, from 0.0 to 1.0."""
    # Rust binding
    def to_bytes(self) -> bytes:
        """The samples as little-endian 32-bit floats."""
    # Rust binding
    def samples(self) -> list[float]:
        """The samples as a list of floats."""
    # Rust binding
    def envelope(self, points: int) -> list[float]:
        """
        The loudness outline of the sound: ``points`` peak levels from 0.0 to 1.0.

        Each value is the largest absolute sample in one equal slice of the
        sound, ready to draw as a waveform or a sparkline.

        Raises:
            ValueError: If ``points`` is not between 1 and 100000.
        """
    # Rust binding
    def with_effects(self, effects: list[TerminalAudioEffect]) -> TerminalSound:
        """
        A new sound with ``effects`` applied in order.

        Echo and reverb tails make the result longer than the original. The
        peak is kept below 0.98 and the added tail is capped at 30 seconds.
        The GIL is released while processing.

        Raises:
            ValueError: If more than 32 effects are given.
            TypeError: If an item is not a
                [`TerminalAudioEffect`][xnano_audio.TerminalAudioEffect].
        """
    # Rust binding
    def __len__(self) -> int: ...
    # Rust binding
    def __eq__(self, other: object) -> bool: ...
    # Rust binding
    def __hash__(self) -> int: ...
    # Rust binding
    def __copy__(self) -> TerminalSound: ...
    # Rust binding
    def __deepcopy__(self, memo: object) -> TerminalSound: ...

# Rust binding
@final
class TerminalNote:
    """
    One note on a beat timeline.

    Immutable. Pitches are MIDI numbers (60 is middle C); a name such as ``"C#4"``
    is accepted wherever a pitch is. Times are measured in quarter-note beats from the
    start of the melody. Every ``with_*`` method returns a new note.

    Attributes:
        pitch: The MIDI pitch, 0 to 127.
        name: The sharp-spelled note name, such as ``"C#4"``.
        frequency_hertz: The pitch in hertz.
        velocity: The strength, 0.0 to 1.0.
        start_beats: Where the note starts, in beats.
        duration_beats: How long the key is held, in beats.
        end_beats: Where the note ends, in beats.

    Examples:
        ```python
        note = TerminalNote("C4", start_beats=1.0, duration_beats=0.5)
        assert note.pitch == 60 and note.end_beats == 1.5
        ```
    """
    # Rust binding
    def __init__(
        self,
        pitch: Pitch,
        *,
        start_beats: float = 0.0,
        duration_beats: float = 1.0,
        velocity: float = 0.8,
    ) -> None:
        """
        Create a note.

        Args:
            pitch: A [`NoteName`][xnano_audio.NoteName] such as ``"C4"`` or ``"Db5"``, or a
                MIDI number from 0 to 127. Lower case and a missing octave (``"c#"`` is
                ``"C#4"``) are accepted too.
            start_beats: Where the note starts, zero or more.
            duration_beats: How long the key is held, greater than zero.
            velocity: Strength from 0.0 to 1.0.

        Raises:
            ValueError: If an argument is out of range or the pitch name is not recognized.
            TypeError: If ``pitch`` is not an ``int`` or ``str``.
        """
    # Rust binding
    @property
    def pitch(self) -> int:
        """The MIDI pitch, 0 to 127."""
    # Rust binding
    @property
    def name(self) -> NoteName:
        """The sharp-spelled note name, such as ``"C#4"``."""
    # Rust binding
    @property
    def frequency_hertz(self) -> float:
        """The pitch in hertz."""
    # Rust binding
    @property
    def velocity(self) -> float:
        """The strength, 0.0 to 1.0."""
    # Rust binding
    @property
    def start_beats(self) -> float:
        """Where the note starts, in beats."""
    # Rust binding
    @property
    def duration_beats(self) -> float:
        """How long the key is held, in beats."""
    # Rust binding
    @property
    def end_beats(self) -> float:
        """Where the note ends, in beats."""
    # Rust binding
    def with_pitch(self, pitch: Pitch) -> TerminalNote:
        """Return the note with another pitch."""
    # Rust binding
    def with_start_beats(self, start_beats: float) -> TerminalNote:
        """Return the note starting at another beat."""
    # Rust binding
    def with_duration_beats(self, duration_beats: float) -> TerminalNote:
        """Return the note held for another number of beats."""
    # Rust binding
    def with_velocity(self, velocity: float) -> TerminalNote:
        """Return the note with another strength."""
    # Rust binding
    def transposed(self, semitones: int) -> TerminalNote:
        """
        Return the note moved by ``semitones``.

        Raises:
            ValueError: If the result leaves the MIDI range 0 to 127.
        """
    # Rust binding
    @overload
    def __add__(self, other: int) -> TerminalNote: ...
    @overload
    def __add__(self, other: TerminalNote | TerminalMelody) -> TerminalMelody: ...
    def __add__(
        self, other: int | TerminalNote | TerminalMelody
    ) -> TerminalNote | TerminalMelody:
        """
        Move the note up by semitones, or play something after it.

        ``note + 1`` is the note one semitone higher, ``note + 12`` an octave higher.
        Adding a note or a melody makes a [`TerminalMelody`][xnano_audio.TerminalMelody]
        that plays them one after the other.

        Raises:
            ValueError: If the result leaves the MIDI range 0 to 127.

        Examples:
            ```python
            assert TerminalNote("C4") + 1 == TerminalNote("C#4")
            assert 12 + TerminalNote("C4") == TerminalNote("C5")
            melody = TerminalNote("C4") + TerminalNote("E4")
            assert [note.name for note in melody] == ["C4", "E4"]
            ```
        """
    # Rust binding
    def __radd__(self, other: int) -> TerminalNote: ...
    # Rust binding
    @overload
    def __sub__(self, other: int) -> TerminalNote: ...
    @overload
    def __sub__(self, other: TerminalNote) -> int: ...
    def __sub__(self, other: int | TerminalNote) -> TerminalNote | int:
        """
        Move the note down by semitones, or measure the distance to another note.

        Examples:
            ```python
            assert TerminalNote("C4") - 1 == TerminalNote("B3")
            assert TerminalNote("E4") - TerminalNote("C4") == 4
            ```
        """
    # Rust binding
    def __or__(self, other: TerminalNote | TerminalMelody) -> TerminalMelody:
        """
        Play notes together, as a chord.

        Examples:
            ```python
            chord = TerminalNote("C4") | TerminalNote("E4") | TerminalNote("G4")
            assert {note.start_beats for note in chord} == {0.0}
            ```
        """
    # Rust binding
    def __int__(self) -> int:
        """The MIDI pitch, so ``int(TerminalNote("C4"))`` is ``60``."""
    # Rust binding
    def __lt__(self, other: TerminalNote) -> bool:
        """Notes are ordered by pitch, then by where they start."""
    def __le__(self, other: TerminalNote) -> bool: ...
    def __gt__(self, other: TerminalNote) -> bool: ...
    def __ge__(self, other: TerminalNote) -> bool: ...
    # Rust binding
    def __hash__(self) -> int: ...
    # Rust binding
    def __eq__(self, other: object) -> bool: ...
    # Rust binding
    def __repr__(self) -> str: ...
    # Rust binding
    def __copy__(self) -> TerminalNote: ...
    # Rust binding
    def __deepcopy__(self, memo: object) -> TerminalNote: ...

# Rust binding
@final
class TerminalTimeSignature:
    """
    How many beats make a bar.

    Melodies are measured in quarter-note beats, so ``TerminalTimeSignature(6, 8)`` is a
    bar of three beats.

    Attributes:
        numerator: Beat units per bar.
        denominator: The note value of one beat unit.
        bar_length_beats: The length of one bar in quarter-note beats.
    """
    # Rust binding
    def __init__(self, numerator: int = 4, denominator: int = 4) -> None:
        """
        Create a time signature.

        Args:
            numerator: Beat units per bar, 1 to 64.
            denominator: The note value of one beat unit: 1, 2, 4, 8, 16 or 32.

        Raises:
            ValueError: If an argument is out of range.
        """
    # Rust binding
    @property
    def numerator(self) -> int:
        """Beat units per bar."""
    # Rust binding
    @property
    def denominator(self) -> int:
        """The note value of one beat unit."""
    # Rust binding
    @property
    def bar_length_beats(self) -> float:
        """The length of one bar in quarter-note beats."""
    # Rust binding
    def bar_and_beat(self, beats: float) -> tuple[int, float]:
        """
        Return the zero-based bar and the beat inside it that ``beats`` falls on.

        Raises:
            ValueError: If ``beats`` is negative or not finite.
        """
    # Rust binding
    def __hash__(self) -> int: ...
    # Rust binding
    def __eq__(self, other: object) -> bool: ...
    # Rust binding
    def __repr__(self) -> str: ...
    # Rust binding
    def __copy__(self) -> TerminalTimeSignature: ...
    # Rust binding
    def __deepcopy__(self, memo: object) -> TerminalTimeSignature: ...

# Rust binding
@final
class TerminalTempoMap:
    """
    Maps beats to seconds. The tempo is constant between changes.

    Immutable. Use it to find when a beat sounds on a clock, or which beat a clock
    reading falls on, even across tempo changes.

    Attributes:
        initial_beats_per_minute: The tempo before any change.
        changes: The tempo changes as ``(beat, beats_per_minute)`` pairs in beat order.
    """
    # Rust binding
    def __init__(self, beats_per_minute: float = 120.0) -> None:
        """
        Create a map with one constant tempo.

        Args:
            beats_per_minute: Quarter-note beats per minute, 1 to 1000.

        Raises:
            ValueError: If the tempo is out of range.
        """
    # Rust binding
    @property
    def initial_beats_per_minute(self) -> float:
        """The tempo before any change."""
    # Rust binding
    @property
    def changes(self) -> list[tuple[float, float]]:
        """The tempo changes as ``(beat, beats_per_minute)`` pairs in beat order."""
    # Rust binding
    def with_change(self, beat: float, beats_per_minute: float) -> TerminalTempoMap:
        """
        Return the map with a change to ``beats_per_minute`` at ``beat``.

        A change at beat 0 replaces the initial tempo; a change at an existing beat
        replaces that change.

        Raises:
            ValueError: If an argument is out of range.
        """
    # Rust binding
    def scaled(self, factor: float) -> TerminalTempoMap:
        """
        Return the map with every tempo multiplied by ``factor``; 2.0 plays twice as fast.

        Raises:
            ValueError: If ``factor`` is not positive or a tempo leaves its range.
        """
    # Rust binding
    def beats_per_minute_at(self, beat: float) -> float:
        """Return the tempo in effect at ``beat``."""
    # Rust binding
    def beats_to_seconds(self, beat: float) -> float:
        """
        Return the seconds from beat zero to ``beat``.

        Raises:
            ValueError: If ``beat`` is negative or not finite.
        """
    # Rust binding
    def seconds_to_beats(self, seconds: float) -> float:
        """
        Return the beat reached after ``seconds``.

        Raises:
            ValueError: If ``seconds`` is negative or not finite.
        """
    # Rust binding
    def __hash__(self) -> int: ...
    # Rust binding
    def __eq__(self, other: object) -> bool: ...
    # Rust binding
    def __repr__(self) -> str: ...
    # Rust binding
    def __copy__(self) -> TerminalTempoMap: ...
    # Rust binding
    def __deepcopy__(self, memo: object) -> TerminalTempoMap: ...

# Rust binding
@final
class TerminalScheduledNote:
    """
    A note placed on an external clock.

    Returned by [`TerminalMelody.scheduled_between`][xnano_audio.TerminalMelody.scheduled_between].
    Its times are seconds on the clock that was passed in, such as the terminal runtime's
    clock.

    Attributes:
        note: The note, in melody beats.
        start_seconds: When the note starts, in seconds on the external clock.
        duration_seconds: How long the key is held, in seconds.
        end_seconds: When the key is released, in seconds on the external clock.
        iteration: How many times the melody had looped before this note, starting at zero.
    """
    # Rust binding
    @property
    def note(self) -> TerminalNote:
        """The note, in melody beats."""
    # Rust binding
    @property
    def start_seconds(self) -> float:
        """When the note starts, in seconds on the external clock."""
    # Rust binding
    @property
    def duration_seconds(self) -> float:
        """How long the key is held, in seconds."""
    # Rust binding
    @property
    def end_seconds(self) -> float:
        """When the key is released, in seconds on the external clock."""
    # Rust binding
    @property
    def iteration(self) -> int:
        """How many times the melody had looped before this note, starting at zero."""
    # Rust binding
    def __eq__(self, other: object) -> bool: ...
    # Rust binding
    def __repr__(self) -> str: ...
    # Rust binding
    def __copy__(self) -> TerminalScheduledNote: ...
    # Rust binding
    def __deepcopy__(self, memo: object) -> TerminalScheduledNote: ...

# Rust binding
@final
class TerminalMelody:
    """
    Notes on a beat timeline with a tempo map and a time signature.

    Immutable: every method that changes the melody returns a new one. Notes can start
    together to form chords. Ask which notes are due between two readings of any clock with
    [`scheduled_between`][xnano_audio.TerminalMelody.scheduled_between], or render the
    melody to a [`TerminalSound`][xnano_audio.TerminalSound] with
    [`render`][xnano_audio.TerminalMelody.render]. ``len(melody)`` is the number of notes
    and iterating yields the notes in start order.

    Attributes:
        notes: The notes in start order.
        tempo_map: The tempo map.
        time_signature: The time signature.
        length_beats: The end of the last note, or the explicit length when that is longer, in
            beats.
        duration_seconds: The melody's length in seconds.

    Examples:
        ```python
        melody = (
            TerminalMelody(tempo_map=TerminalTempoMap(100))
            .appended_note("C4")
            .appended_chord(["E4", "G4"], duration_beats=2)
            .appended_rest(1)
        )
        sound = melody.render("piano")
        due = melody.scheduled_between(0.0, 1.0)
        ```
    """
    # Rust binding
    def __init__(
        self,
        notes: list[TerminalNote] | None = None,
        *,
        tempo_map: TerminalTempoMap | None = None,
        time_signature: TerminalTimeSignature | None = None,
        length_beats: float = 0.0,
    ) -> None:
        """
        Create a melody.

        Args:
            notes: The notes, in any order.
            tempo_map: Defaults to a constant 120 beats per minute.
            time_signature: Defaults to 4/4.
            length_beats: A minimum length that adds trailing silence after the last note.

        Raises:
            ValueError: If there are more than 100000 notes or ``length_beats`` is negative.
        """
    # Rust binding
    @property
    def notes(self) -> list[TerminalNote]:
        """The notes in start order."""
    # Rust binding
    @property
    def tempo_map(self) -> TerminalTempoMap:
        """The tempo map."""
    # Rust binding
    @property
    def time_signature(self) -> TerminalTimeSignature:
        """The time signature."""
    # Rust binding
    @property
    def length_beats(self) -> float:
        """The end of the last note, or the explicit length when that is longer, in beats."""
    # Rust binding
    @property
    def duration_seconds(self) -> float:
        """The melody's length in seconds."""
    # Rust binding
    def with_notes(self, notes: list[TerminalNote]) -> TerminalMelody:
        """Return the melody with ``notes`` added."""
    # Rust binding
    def with_tempo_map(self, tempo_map: TerminalTempoMap) -> TerminalMelody:
        """Return the melody with another tempo map."""
    # Rust binding
    def with_time_signature(
        self, time_signature: TerminalTimeSignature
    ) -> TerminalMelody:
        """Return the melody with another time signature."""
    # Rust binding
    def with_length_beats(self, length_beats: float) -> TerminalMelody:
        """Return the melody lasting at least ``length_beats``, which adds trailing silence."""
    # Rust binding
    def appended_note(
        self, pitch: Pitch, *, duration_beats: float = 1.0, velocity: float = 0.8
    ) -> TerminalMelody:
        """Return the melody with one note appended at its end."""
    # Rust binding
    def appended_chord(
        self,
        pitches: Sequence[Pitch],
        *,
        duration_beats: float = 1.0,
        velocity: float = 0.8,
    ) -> TerminalMelody:
        """Return the melody with notes that sound together appended at its end."""
    # Rust binding
    def appended_rest(self, duration_beats: float = 1.0) -> TerminalMelody:
        """Return the melody with silence appended at its end."""
    # Rust binding
    def transposed(self, semitones: int) -> TerminalMelody:
        """
        Return the melody with every pitch moved by ``semitones``.

        Raises:
            ValueError: If a pitch would leave the MIDI range 0 to 127.
        """
    # Rust binding
    def shifted(self, beats: float) -> TerminalMelody:
        """
        Return the melody moved later by ``beats``, or earlier when negative.

        Raises:
            ValueError: If a note would start before beat zero.
        """
    # Rust binding
    def stretched(self, factor: float) -> TerminalMelody:
        """
        Return the melody with every start, duration and tempo change multiplied by ``factor``.

        The tempo values are unchanged, so 2.0 makes the melody twice as long in time.
        """
    # Rust binding
    def repeated(self, count: int) -> TerminalMelody:
        """
        Return the melody played ``count`` times in a row.

        Raises:
            ValueError: If ``count`` is zero or the result would hold too many notes.
        """
    # Rust binding
    def followed_by(self, other: TerminalMelody) -> TerminalMelody:
        """Return the melody followed by ``other``, keeping this melody's tempo map."""
    # Rust binding
    def layered_with(self, other: TerminalMelody) -> TerminalMelody:
        """Return the notes of both melodies played together, keeping this tempo map."""
    # Rust binding
    @overload
    def __add__(self, other: int) -> TerminalMelody: ...
    @overload
    def __add__(self, other: TerminalMelody | TerminalNote) -> TerminalMelody: ...
    def __add__(self, other: int | TerminalMelody | TerminalNote) -> TerminalMelody:
        """
        Play something after the melody, or raise it by semitones.

        Examples:
            ```python
            phrase = TerminalNote("C4") + TerminalNote("E4")
            assert len((phrase + TerminalNote("G4")).notes) == 3
            assert [note.name for note in phrase + 2] == ["D4", "F#4"]
            ```
        """
    # Rust binding
    def __radd__(self, other: int) -> TerminalMelody: ...
    # Rust binding
    def __sub__(self, other: int) -> TerminalMelody:
        """Lower every note by semitones."""
    # Rust binding
    def __mul__(self, other: int) -> TerminalMelody:
        """
        Play the melody several times in a row.

        Examples:
            ```python
            phrase = TerminalNote("C4") + TerminalNote("E4")
            assert len((phrase * 3).notes) == 6
            ```
        """
    # Rust binding
    def __rmul__(self, other: int) -> TerminalMelody: ...
    # Rust binding
    def __or__(self, other: TerminalMelody | TerminalNote) -> TerminalMelody:
        """Play two melodies together."""
    # Rust binding
    def __rshift__(self, other: float) -> TerminalMelody:
        """
        Start the melody later by beats.

        Examples:
            ```python
            phrase = TerminalNote("C4") + TerminalNote("E4")
            assert [note.start_beats for note in phrase >> 2] == [2.0, 3.0]
            ```
        """
    # Rust binding
    def __lshift__(self, other: float) -> TerminalMelody:
        """Start the melody earlier by beats."""
    # Rust binding
    def notes_between_beats(
        self, from_beats: float, to_beats: float
    ) -> list[TerminalNote]:
        """Return the notes that start in ``[from_beats, to_beats)``."""
    # Rust binding
    def notes_between_seconds(
        self, from_seconds: float, to_seconds: float
    ) -> list[TerminalNote]:
        """Return the notes that start in ``[from_seconds, to_seconds)`` of melody time."""
    # Rust binding
    def scheduled_between(
        self,
        from_elapsed_seconds: float,
        to_elapsed_seconds: float,
        *,
        start_seconds: float = 0.0,
        should_loop: bool = False,
    ) -> list[TerminalScheduledNote]:
        """
        Return the notes due on an external clock between two readings.

        The melody begins when the clock reads ``start_seconds``. Notes that start in
        ``[from_elapsed_seconds, to_elapsed_seconds)`` are returned with their times on
        that same clock, so consecutive windows never repeat or skip a note. Call it every
        frame with the previous and current reading of a manual or monotonic clock.

        Args:
            from_elapsed_seconds: The previous clock reading (inclusive).
            to_elapsed_seconds: The current clock reading (exclusive).
            start_seconds: The clock reading at which the melody begins.
            should_loop: Restart the melody every time it reaches its length.

        Raises:
            ValueError: If a reading is not finite or ``to_elapsed_seconds`` is earlier than
                ``from_elapsed_seconds``.
        """
    # Rust binding
    def render(
        self,
        instrument: InstrumentName = 'piano',
        *,
        sample_rate: int = 44100,
        effects: list[TerminalAudioEffect] | None = None,
        from_seconds: float = 0.0,
        to_seconds: float | None = None,
    ) -> TerminalSound:
        """
        Render the melody, or the notes starting inside a window, to a sound.

        Notes are placed sample-accurately from the tempo map and mixed; the result is
        limited to stay below clipping. The first sample is the instant ``from_seconds``.
        Notes ring past the window with their natural tail.

        Args:
            instrument: One of [`instrument_names`][xnano_audio.instrument_names].
            sample_rate: Output rate in hertz, 8000 to 192000.
            effects: Effects applied in order to the mixed result (at most 32).
            from_seconds: Melody time of the first sample.
            to_seconds: Melody time at which the window ends; defaults to the melody's end.

        Raises:
            ValueError: If the instrument is unknown, an argument is out of range or the
                window is longer than 600 seconds.
        """
    # Rust binding
    def __len__(self) -> int: ...
    # Rust binding
    def __iter__(self) -> Iterator[TerminalNote]: ...
    # Rust binding
    def __eq__(self, other: object) -> bool: ...
    # Rust binding
    def __repr__(self) -> str: ...
    # Rust binding
    def __copy__(self) -> TerminalMelody: ...
    # Rust binding
    def __deepcopy__(self, memo: object) -> TerminalMelody: ...

# Rust binding
def instrument_names() -> list[InstrumentName]:
    """Names of every built-in instrument, in catalog order."""

# Rust binding
def is_percussive(instrument: InstrumentName) -> bool:
    """
    Whether an instrument rings for its own length and ignores duration.

    Raises:
        ValueError: If the instrument name is unknown (the message lists the
            valid names).
    """

# Rust binding
def note_to_hertz(note: NoteName | float | str) -> float:
    """
    Convert a note to hertz.

    Args:
        note: A name such as ``"C4"``, ``"c#3"``, ``"Db5"`` (the octave
            defaults to 4; ``C4`` is middle C, MIDI 60), a MIDI note number
            as an ``int``, or a frequency in hertz as a ``float``. Strings may
            also be a plain number (MIDI) or end in ``hz`` (``"440hz"``).

    Raises:
        ValueError: If the note is not recognized or is outside 8 Hz to
            20 kHz.
        TypeError: If ``note`` is not a string or number.
    """

# Rust binding
def render_note(
    instrument: InstrumentName,
    note: NoteName | float | str | None = None,
    *,
    duration_milliseconds: int = 500,
    velocity: float = 0.8,
    effects: list[TerminalAudioEffect] | None = None,
    sample_rate: int = 44100,
) -> TerminalSound:
    """
    Render a note with a built-in instrument. Needs no audio device.

    The output is deterministic: the same arguments always give identical
    samples. The GIL is released while rendering.

    Args:
        instrument: One of
            [`instrument_names`][xnano_audio.instrument_names]. Case,
            spaces and hyphens are forgiving (``"Electric Piano"`` works).
        note: What to play; see
            [`note_to_hertz`][xnano_audio.note_to_hertz]. Defaults to
            ``"C4"``.
        duration_milliseconds: How long the note is held, 1 to 60000. The
            release or natural decay is added on top, so the sound is longer.
            Ignored by percussive instruments.
        velocity: Strength from 0.0 to 1.0 (clamped; NaN raises
            ``ValueError``). Louder notes are also brighter on
            instruments that model it (piano, synth, ...).
        effects: Effects applied in order after the instrument (at most 32).
        sample_rate: Output rate in hertz, 8000 to 192000.

    Raises:
        ValueError: If the instrument is unknown (the message lists the valid
            names) or an argument is out of range.
        TypeError: If ``note`` is not a string or number.

    Examples:
        ```python
        ding = render_note("bell", "C6", effects=[TerminalAudioEffect.reverb()])
        assert ding.peak <= 0.98
        ```
    """

# Rust binding
@final
class TerminalAudioPlayer:
    """
    Plays sounds on the default output device, with one musical clock.

    Not thread-safe (``unsendable``): use it from the thread that created it.

    Sounds can start immediately or on a clock beat. The clock runs at a
    tempo in beats per minute (120 by default), and a sound scheduled with
    ``at_beat`` starts sample-accurately when the clock reaches that beat, so
    sequences do not drift with Python's timing.

    Attributes:
        is_clock_running: Whether the clock is currently running.
        tempo: The clock tempo in beats per minute.
        beat: The clock position in beats, including the fraction of the current beat.
        clock_position_milliseconds: The clock position in milliseconds at the current tempo.

    Examples:
        ```python
        player = TerminalAudioPlayer()
        player.play_note("bell", "C6")  # a "ding", right now
        player.start_clock()
        for index, note in enumerate(["C4", "E4", "G4"]):
            player.play_note("piano", note, at_beat=int(player.beat) + 1 + index)
        ```
    """

    # Rust binding
    def __init__(self, *, beats_per_minute: float = 120.0) -> None:
        """
        Open the default output device.

        Args:
            beats_per_minute: Initial clock tempo, greater than 0 and at most
                600000.

        Raises:
            TerminalAudioUnavailableError: If no output device is available, or
                this build has no device support.
            ValueError: If ``beats_per_minute`` is out of range.
        """
    # Rust binding
    @staticmethod
    def is_available() -> bool:
        """Whether an output device exists, without opening it."""
    # Rust binding
    def play_note(
        self,
        instrument: InstrumentName,
        note: NoteName | float | str | None = None,
        *,
        duration_milliseconds: int = 500,
        velocity: float = 0.8,
        effects: list[TerminalAudioEffect] | None = None,
        volume: float = 1.0,
        pan: float = 0.0,
        at_beat: int | None = None,
    ) -> None:
        """
        Render a built-in instrument note and play it.

        See [`render_note`][xnano_audio.render_note] for ``instrument``,
        ``note``, ``duration_milliseconds``, ``velocity`` and ``effects``.
        Rendering takes a few milliseconds and releases the GIL.

        Args:
            volume: Playback gain, 0.0 to 1.0 (values outside are clamped;
                NaN and infinity raise ``ValueError``).
            pan: Stereo position from -1.0 (left) to 1.0 (right). The centre
                keeps full level; panning only quiets the far side.
            at_beat: If set, start sample-accurately when the clock reaches
                this beat; otherwise start immediately.

        Raises:
            TerminalAudioError: If the mixer cannot accept the sound.
            ValueError: If an argument is out of range (including ``pan``).
        """
    # Rust binding
    def play_sound(
        self,
        sound: TerminalSound,
        *,
        volume: float = 1.0,
        pan: float = 0.0,
        at_beat: int | None = None,
    ) -> None:
        """
        Play an already rendered sound, optionally on a clock beat.

        Render once and play many times to avoid re-rendering.

        Args:
            sound: From [`render_note`][xnano_audio.render_note] or
                [`TerminalSound.with_effects`][xnano_audio.TerminalSound.with_effects].
            volume: Playback gain, as in
                [`play_note`][xnano_audio.TerminalAudioPlayer.play_note].
            pan: Stereo position from -1.0 to 1.0.
            at_beat: As in
                [`play_note`][xnano_audio.TerminalAudioPlayer.play_note].

        Raises:
            TerminalAudioError: If the mixer cannot accept the sound.
            ValueError: If ``pan`` is outside -1.0 to 1.0.
        """
    # Rust binding
    def start_clock(self) -> None:
        """
        Start the clock.

        Clock commands (start, pause, stop, tempo) are applied by the audio
        thread on its next buffer, so [`beat`][xnano_audio.TerminalAudioPlayer.beat]
        can lag a call by a few milliseconds.
        """
    # Rust binding
    def pause_clock(self) -> None:
        """Pause the clock, keeping its position."""
    # Rust binding
    def stop_clock(self) -> None:
        """Stop the clock and reset it to beat zero."""
    # Rust binding
    @property
    def is_clock_running(self) -> bool:
        """Whether the clock is currently running."""
    # Rust binding
    @property
    def tempo(self) -> float:
        """The clock tempo in beats per minute."""
    # Rust binding
    def set_tempo(self, beats_per_minute: float) -> None:
        """
        Change the clock tempo.

        Raises:
            ValueError: If ``beats_per_minute`` is not greater than 0 and at
                most 600000.
        """
    # Rust binding
    @property
    def beat(self) -> float:
        """
        The clock position in beats, including the fraction of the current beat.

        Use it to keep animations in time with music.
        """
    # Rust binding
    @property
    def clock_position_milliseconds(self) -> float:
        """The clock position in milliseconds at the current tempo."""

    # Rust binding
    def close(self) -> None:
        """Close owned audio output; repeated calls are safe."""
    # Rust binding
    def __enter__(self) -> TerminalAudioPlayer: ...
    # Rust binding
    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]: ...

# Rust binding
@final
class TerminalMicrophone:
    """
    Microphone capture that tracks the input level.

    Capture runs on the audio thread; Python only reads levels, so the GIL is
    never involved. Not thread-safe (``unsendable``). Usable as a context
    manager, which closes the device on exit.

    On macOS the terminal application needs microphone permission; without it
    the stream opens but delivers silence (a level of exactly 0.0).

    Attributes:
        level: Root-mean-square level of the most recent audio buffer, from 0.0 to 1.0.
        peak_level: The highest level since opening or the last ``reset_peak_level``.
        last_error: The most recent stream error reported by the device, if any.
        sample_rate: The device's sample rate in hertz.
        channels: The device's channel count.
        is_open: Whether the stream is still capturing.

    Examples:
        ```python
        with TerminalMicrophone() as microphone:
            levels = microphone.level_history(60)  # ready for a sparkline
        ```
    """

    # Rust binding
    def __init__(self) -> None:
        """
        Open the default input device and start capturing.

        Raises:
            TerminalAudioUnavailableError: If there is no input device, the sample
                format is unsupported, or this build has no device support.
            TerminalAudioError: If the stream cannot be opened.
        """
    # Rust binding
    @staticmethod
    def is_available() -> bool:
        """Whether an input device exists, without opening a stream."""
    # Rust binding
    @property
    def level(self) -> float:
        """Root-mean-square level of the most recent audio buffer, from 0.0 to 1.0."""
    # Rust binding
    @property
    def peak_level(self) -> float:
        """The highest level since opening or the last ``reset_peak_level``."""
    # Rust binding
    def reset_peak_level(self) -> None:
        """Forget the peak level, so ``peak_level`` tracks from now on."""
    # Rust binding
    def level_history(self, count: int) -> list[float]:
        """
        The most recent ``count`` levels, oldest first, one per audio buffer.

        At most 4096 levels are kept.

        Raises:
            ValueError: If ``count`` is greater than 4096.
        """
    # Rust binding
    @property
    def last_error(self) -> str | None:
        """The most recent stream error reported by the device, if any."""
    # Rust binding
    @property
    def sample_rate(self) -> int:
        """The device's sample rate in hertz."""
    # Rust binding
    @property
    def channels(self) -> int:
        """The device's channel count."""
    # Rust binding
    @property
    def is_open(self) -> bool:
        """Whether the stream is still capturing."""
    # Rust binding
    def close(self) -> None:
        """Stop capturing and release the device. Safe to call repeatedly."""
    # Rust binding
    def __enter__(self) -> TerminalMicrophone: ...
    # Rust binding
    def __exit__(
        self,
        exception_type: object = None,
        exception_value: object = None,
        traceback: object = None,
    ) -> bool: ...

__all__ = (
    'TerminalAudioCapabilities',
    'TerminalAudioEffect',
    'TerminalAudioError',
    'TerminalAudioPlayer',
    'TerminalAudioSource',
    'TerminalAudioStream',
    'TerminalAudioUnavailableError',
    'TerminalMicrophone',
    'TerminalPCMFormat',
    'TerminalPlayback',
    'TerminalSound',
    'TerminalStreamingAudioPlayer',
    'detect_audio_capabilities',
    'instrument_names',
    'is_percussive',
    'note_to_hertz',
    'render_note',
)

# Proposed independent streaming additions. Existing synthesis signatures remain.

# Rust binding
class TerminalPCMFormat:
    """
    Explicit PCM sample representation; audio bytes are not cell-grid bytes.

    Attributes:
        sample_rate: Frames per second.
        channels: Samples per frame: 1 (mono) or 2 (stereo).
        sample_type: How each sample is stored: ``'f32le'`` or ``'s16le'``.
        bytes_per_frame: Bytes in one interleaved frame.
    """
    # Rust binding
    def __init__(
        self,
        *,
        sample_rate: int = 44100,
        channels: int = 2,
        sample_type: Literal['f32le', 's16le'] = 'f32le',
    ) -> None:
        """
        Create a TerminalPCMFormat.

        Args:
            sample_rate: ``int``. Defaults to ``44100``.
            channels: ``int``. Defaults to ``2``.
            sample_type: ``Literal['f32le', 's16le']``. Defaults to ``'f32le'``.
        """
    # Rust binding
    @property
    def sample_rate(self) -> int:
        """Frames per second."""
    # Rust binding
    @property
    def channels(self) -> int:
        """Samples per frame: 1 (mono) or 2 (stereo)."""
    # Rust binding
    @property
    def sample_type(self) -> Literal['f32le', 's16le']:
        """How each sample is stored: ``'f32le'`` or ``'s16le'``."""
    # Rust binding
    @property
    def bytes_per_frame(self) -> int:
        """Bytes in one interleaved frame."""

# Python implementation
class TerminalAudioSource(Protocol):
    """
    Producer-worker source. Python callbacks never execute on the device thread.

    Attributes:
        format: The layout of the bytes ``read`` returns.
    """
    # Python implementation — Python source protocol consumed by the native audio stream.
    @property
    def format(self) -> TerminalPCMFormat:
        """The layout of the bytes ``read`` returns."""
        ...
    # Python implementation — Python source protocol consumed by the native audio stream.
    def read(self, frames: int) -> bytes:
        """Return up to frames complete interleaved PCM frames; empty bytes means end."""
        ...
    # Python implementation — Python source protocol consumed by the native audio stream.
    def close(self) -> None:
        """Release whatever the source holds."""
        ...

# Rust binding
class TerminalAudioStream:
    """
    Lazy decoded file source; no whole-file TerminalSound allocation is required.

    Attributes:
        format: The layout of the bytes ``read`` returns.
        is_closed: Whether the stream has been closed.
    """
    # Rust binding
    @classmethod
    def open(
        cls, path: str | PathLike[str], *, format: TerminalPCMFormat | None = None
    ) -> TerminalAudioStream:
        """
        Open an audio file (WAV, FLAC, Ogg Vorbis, MP3 or MP4/AAC); decoding starts on the first read.

        Args:
            path: The audio file.
            format: The layout to decode into. Defaults to the file's own rate and channels as ``f32le``.

        Raises:
            TerminalAudioError: The file cannot be opened or decoded.
        """
    # Rust binding
    @property
    def format(self) -> TerminalPCMFormat:
        """The layout of the bytes ``read`` returns."""
    # Rust binding
    @property
    def is_closed(self) -> bool:
        """Whether the stream has been closed."""
    # Rust binding
    def read(self, frames: int) -> bytes:
        """Decode up to ``frames`` frames; empty bytes mean the end of the file."""
    # Rust binding
    def seek(self, frame: int) -> None:
        """Move to ``frame``, counted in frames of this stream's ``format``."""
    # Rust binding
    def close(self) -> None:
        """Release the file; repeated calls are safe."""
    # Rust binding
    def __enter__(self) -> TerminalAudioStream: ...
    # Rust binding
    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]: ...

# Rust binding
class TerminalPlayback:
    """
    One independently controlled voice or stream; setters are owner-thread commands.

    Attributes:
        is_playing: Whether the voice is producing sound (not finished and not paused).
        is_paused: Whether the voice is paused.
        volume: Playback gain from 0.0 to 1.0; assigning it ramps over a few milliseconds.
        pan: Stereo position from -1.0 (left) to 1.0 (right).
        position_frames: Frames of this voice played so far.
        buffered_frames: Frames decoded ahead and waiting to play.
        underruns: How many times the buffer ran dry before the source ended.
        last_error: The message of the last source failure, or ``None``.
    """
    # Rust binding
    @property
    def is_playing(self) -> bool:
        """Whether the voice is producing sound (not finished and not paused)."""
    # Rust binding
    @property
    def is_paused(self) -> bool:
        """Whether the voice is paused."""
    # Rust binding
    @property
    def volume(self) -> float:
        """Playback gain from 0.0 to 1.0; assigning it ramps over a few milliseconds."""
    # Rust binding
    @volume.setter
    def volume(self, value: float) -> None:
        """Playback gain from 0.0 to 1.0; assigning it ramps over a few milliseconds."""
    # Rust binding
    @property
    def pan(self) -> float:
        """Stereo position from -1.0 (left) to 1.0 (right)."""
    # Rust binding
    @pan.setter
    def pan(self, value: float) -> None:
        """Stereo position from -1.0 (left) to 1.0 (right)."""
    # Rust binding
    @property
    def position_frames(self) -> int:
        """Frames of this voice played so far."""
    # Rust binding
    @property
    def buffered_frames(self) -> int:
        """Frames decoded ahead and waiting to play."""
    # Rust binding
    @property
    def underruns(self) -> int:
        """How many times the buffer ran dry before the source ended."""
    # Rust binding
    @property
    def last_error(self) -> str | None:
        """The message of the last source failure, or ``None``."""
    # Rust binding
    def pause(self) -> None:
        """Pause the voice, keeping its position."""
    # Rust binding
    def resume(self) -> None:
        """Resume a paused voice."""
    # Rust binding
    def fade_to(self, volume: float, *, seconds: float) -> None:
        """Ramp the volume to ``volume`` over ``seconds``."""
    # Rust binding
    def stop(self, *, fade_seconds: float = 0.0) -> None:
        """Stop the voice, optionally fading out first."""

# Rust binding
class TerminalStreamingAudioPlayer:
    """
    Device owner for buffered streams and sample-count timing.

    Construct on its owner thread. A producer worker reads/decodes sources
    ahead; the device callback consumes native buffered samples only.
    Underruns emit silence and increment counters. Source failure affects its
    playback handle rather than the terminal runtime. A failed start closes
    any resources opened by that start operation.

    Attributes:
        format: The layout of audio this player mixes.
        is_closed: Whether the player has been closed.
        sample_position: Output frames consumed; render-ahead frames do not advance this
            counter.
    """
    # Rust binding
    def __init__(
        self,
        *,
        format: TerminalPCMFormat | None = None,
        lookahead_milliseconds: int = 300,
        backend: Literal['default', 'null'] = 'default',
    ) -> None:
        """
        Create a TerminalStreamingAudioPlayer.

        Args:
            format: ``TerminalPCMFormat | None``. Defaults to ``None``.
            lookahead_milliseconds: ``int``. Defaults to ``300``.
            backend: ``Literal['default', 'null']``. Defaults to ``'default'``.
        """
    # Rust binding
    @property
    def format(self) -> TerminalPCMFormat:
        """The layout of audio this player mixes."""
    # Rust binding
    @property
    def is_closed(self) -> bool:
        """Whether the player has been closed."""
    # Rust binding
    @property
    def sample_position(self) -> int:
        """Output frames consumed; render-ahead frames do not advance this counter."""
    # Rust binding
    def play_stream(
        self,
        source: TerminalAudioSource,
        *,
        volume: float = 1.0,
        pan: float = 0.0,
        should_close_source: bool = True,
    ) -> TerminalPlayback:
        """
        Play a stream or any object with ``format``, ``read(frames)`` and ``close()``.

        Args:
            source: The audio source.
            volume: Gain from 0.0 to 1.0.
            pan: Stereo position from -1.0 to 1.0.
            should_close_source: Whether the voice closes the source when it ends.
        """
    # Rust binding
    def play_sound(
        self, sound: TerminalSound, *, volume: float = 1.0, pan: float = 0.0
    ) -> TerminalPlayback:
        """Play a rendered [`TerminalSound`][xnano_audio.TerminalSound] as an independent voice."""
    # Rust binding
    def crossfade(
        self,
        outgoing: TerminalPlayback,
        incoming: TerminalPlayback,
        *,
        seconds: float = 3.0,
    ) -> None:
        """Fade ``outgoing`` out and ``incoming`` in over ``seconds``."""
    # Rust binding
    def advance(self, frames: int) -> bytes:
        """Deterministic null-backend consumption only; rejects live-device advancement."""
    # Rust binding
    def close(self, *, fade_seconds: float = 0.04, timeout_seconds: float = 0.25) -> None:
        """Idempotent bounded shutdown; stop the device before releasing its callback storage."""
    # Rust binding
    def __enter__(self) -> TerminalStreamingAudioPlayer: ...
    # Rust binding
    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]: ...
