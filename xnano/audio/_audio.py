"""
xnano.audio._audio

Audio to play: recordings loaded from files, samples, and what a canvas played.
"""

from __future__ import annotations

import array
import dataclasses
import io
import os
import pathlib
import sys
import tempfile
from collections.abc import Sequence
from typing import TYPE_CHECKING, Final

from xnano import symbols
from xnano._internal._optional import require

if TYPE_CHECKING:
    from types import ModuleType

    from xnano_audio import TerminalSound

    from xnano.layout._region import Region

__all__ = ['Audio', 'load_audio']

AUDIO_PITCH_ROW: Final = 60
"""The MIDI number of middle C: the row of the timeline audio, which has no pitch of its own, is placed on."""


@dataclasses.dataclass(frozen=True, slots=True, init=False)
class Audio:
    """
    Audio to play: a recording loaded from a file, samples you made, or what a canvas played.

    Load a WAV, MP3, FLAC, Ogg Vorbis or MP4/AAC file with [`load_audio`][xnano.load_audio],
    make audio from samples with [`from_samples`][xnano.Audio.from_samples], or take what a
    canvas from ``new()`` played with [`Speaker.render`][xnano.devices.Speaker.render]. Play it
    with [`Speaker.play`][xnano.devices.Speaker.play] or [`play`][xnano.play], or give it a
    ``symbol`` and play it by name. Audio is mono, and all of it is kept in memory, so a long
    song takes memory in proportion to its length.

    Attributes:
        terminal_sound: The audio as an ``xnano-audio`` sound, for the functions of that
            package. Maps to [`xnano_audio.TerminalSound`][xnano_audio.TerminalSound].
        symbol: The name the audio is registered under in [`symbols`][xnano.symbols], or
            ``None``. ``play('kick')`` plays the audio registered as ``'kick'``.
        sample_rate: How many samples it has per second.
        duration_milliseconds: How long it lasts, in milliseconds.
        peak: The largest absolute sample: ``0.0`` for silence, above ``1.0`` when it clips.
        region: The audio on the timeline as a piano roll: a
            [`Region`][xnano.layout.Region] that starts at beat 0, lasts as long as the
            audio at 120 beats per minute and covers the single row of middle C, because
            audio has no pitch of its own.

    Examples:
        ```python
        import xnano

        audio = xnano.Audio.from_samples([0.0, 0.5, -0.5, 0.0])
        assert (audio.sample_rate, audio.peak) == (44100, 0.5)
        assert (audio.region.y, audio.region.height) == (60, 1)
        ```
    """

    terminal_sound: TerminalSound
    """The audio as an ``xnano-audio`` sound. Maps to [`xnano_audio.TerminalSound`][xnano_audio.TerminalSound]."""
    symbol: str | None
    """The registered symbol name, or ``None``."""

    def __init__(
        self, terminal_sound: TerminalSound, /, *, symbol: str | None = None
    ) -> None:
        """
        Make audio from a sound made with ``xnano-audio``.

        For a file use [`load_audio`][xnano.load_audio], and for samples
        [`from_samples`][xnano.Audio.from_samples].

        Args:
            terminal_sound: A [`TerminalSound`][xnano_audio.TerminalSound], such as one
                that an ``xnano-audio`` function rendered.
            symbol: A name to register the audio under in [`symbols`][xnano.symbols], so
                ``play(name)`` plays it.

        Raises:
            ImportError: ``xnano-audio`` is not installed. Install it with
                ``pip install "xnano[audio]"``.
            TypeError: ``terminal_sound`` is not a ``TerminalSound``.
            ValueError: ``symbol`` cannot be a symbol name, or another kind of value
                already has it.
        """
        module = require('audio', needed_for='xnano.Audio')
        if not isinstance(terminal_sound, module.TerminalSound):
            raise TypeError(
                f'Audio wraps an xnano_audio.TerminalSound, but got '
                f'{type(terminal_sound).__name__}. Load a file with '
                f'xnano.load_audio("song.mp3"), or make audio from samples with '
                f'xnano.Audio.from_samples([0.0, 0.5, -0.5]).'
            )
        object.__setattr__(self, 'terminal_sound', terminal_sound)
        object.__setattr__(self, 'symbol', symbol)
        if symbol is not None:
            symbols.register(symbol, self)

    @classmethod
    def from_samples(
        cls,
        samples: Sequence[float],
        /,
        *,
        sample_rate: int = 44100,
        symbol: str | None = None,
    ) -> Audio:
        """
        Make audio from samples: numbers from ``-1.0`` to ``1.0``, one per instant.

        Args:
            samples: The samples, in order.
            sample_rate: How many samples there are per second.
            symbol: A name to register the audio under in [`symbols`][xnano.symbols], so
                ``play(name)`` plays it.

        Returns:
            The [`Audio`][xnano.Audio].

        Raises:
            ImportError: ``xnano-audio`` is not installed. Install it with
                ``pip install "xnano[audio]"``.
            ValueError: ``samples`` is empty, or ``sample_rate`` is not above 0.

        Examples:
            ```python
            import math

            import xnano

            tone = [math.sin(index / 10) for index in range(44100)]
            audio = xnano.Audio.from_samples(tone, symbol='tone')
            assert audio.duration_milliseconds == 1000.0
            ```
        """
        module = require('audio', needed_for='xnano.Audio.from_samples')
        values = samples if isinstance(samples, list) else list(samples)
        return cls(
            module.TerminalSound.from_samples(values, sample_rate=sample_rate),
            symbol=symbol,
        )

    @property
    def sample_rate(self) -> int:
        """How many samples the audio has per second."""
        return self.terminal_sound.sample_rate

    @property
    def duration_milliseconds(self) -> float:
        """How long the audio lasts, in milliseconds."""
        return self.terminal_sound.duration_milliseconds

    @property
    def peak(self) -> float:
        """The largest absolute sample: ``0.0`` for silence, above ``1.0`` when it clips."""
        return self.terminal_sound.peak

    def samples(self) -> list[float]:
        """A copy of the samples, in order."""
        return self.terminal_sound.samples()

    @property
    def region(self) -> Region[float]:
        """
        The audio on the timeline as a piano roll.

        The region starts at beat 0 and lasts as long as the audio does at 120 beats per
        minute, the tempo of [`play`][xnano.play] when no canvas is running, so its
        ``milliseconds`` view is the duration of the audio. Audio has no pitch of its own,
        so the region covers the one row of middle C (60). ``context.region`` of a hook on
        a playable measures at the tempo of the canvas instead.

        Examples:
            ```python
            import xnano

            audio = xnano.Audio.from_samples([0.0] * 44100)
            assert audio.region.milliseconds.width == 1000.0
            assert (audio.region.y, audio.region.height) == (60, 1)
            ```
        """
        from xnano.audio._notes import _DEFAULT_BPM
        from xnano.layout._region import _timeline_region

        duration_seconds = self.terminal_sound.duration_milliseconds / 1000.0
        return _timeline_region(
            start_beats=0.0,
            length_beats=duration_seconds * _DEFAULT_BPM / 60.0,
            pitches=(AUDIO_PITCH_ROW,),
            tempo_changes=((0.0, _DEFAULT_BPM),),
        )


_UNREADABLE_AUDIO: Final = (
    'load_audio could not read this audio{where}{detail}. xnano reads WAV, MP3, FLAC, Ogg '
    'Vorbis and MP4/AAC files. Convert the audio to one of them, or make it from samples '
    'with xnano.Audio.from_samples().'
)


def _is_wave(head: bytes) -> bool:
    """Whether ``head``, the first bytes of a file, starts a RIFF WAVE container."""
    return head[:4] == b'RIFF' and head[8:12] == b'WAVE'


def _decode_audio_path(module: ModuleType, path: pathlib.Path) -> TerminalSound:
    """Decode the audio file at ``path``, choosing the decoder by its content."""
    with path.open('rb') as file:
        head = file.read(12)
    if _is_wave(head):
        return _decode_wave(module, path.read_bytes())
    return _decode_stream(module, path, where=f' file {str(path)!r}')


def _decode_audio_bytes(module: ModuleType, data: bytes) -> TerminalSound:
    """Decode the bytes of an audio file, choosing the decoder by their content."""
    if _is_wave(data[:12]):
        return _decode_wave(module, data)
    if not data:
        raise ValueError(_UNREADABLE_AUDIO.format(where=' data', detail=' (it is empty)'))
    # The decoder opens files only, so the bytes go through a temporary one.
    with tempfile.NamedTemporaryFile(delete=False) as file:
        file.write(data)
    path = pathlib.Path(file.name)
    try:
        return _decode_stream(module, path, where=' data')
    finally:
        path.unlink(missing_ok=True)


_STREAM_CHUNK_FRAMES: Final = 1 << 18
"""Frames decoded per read when a compressed file is loaded."""


def _decode_stream(
    module: ModuleType, path: pathlib.Path, *, where: str
) -> TerminalSound:
    """Decode an MP3, FLAC, Ogg Vorbis or MP4/AAC file into mono samples at 44100 Hz."""
    from xnano.audio._player import _STANDARD_SAMPLE_RATE

    layout = module.TerminalPCMFormat(
        sample_rate=_STANDARD_SAMPLE_RATE, channels=1, sample_type='f32le'
    )
    chunks: list[bytes] = []
    try:
        with module.TerminalAudioStream.open(path, format=layout) as stream:
            while chunk := stream.read(_STREAM_CHUNK_FRAMES):
                chunks.append(chunk)
    except module.TerminalAudioError as error:
        detail = f' ({error})' if str(error) else ''
        raise ValueError(_UNREADABLE_AUDIO.format(where=where, detail=detail)) from None
    if not chunks:
        raise ValueError(
            f'The audio{where} holds no samples. Pass a recording that is not empty.'
        )
    return module.TerminalSound.from_bytes(
        b''.join(chunks), sample_rate=_STANDARD_SAMPLE_RATE
    )


def _decode_wave(module: ModuleType, data: bytes) -> TerminalSound:
    """Decode the bytes of a WAV file into mono samples."""
    import wave  # only loading a WAV file needs it

    try:
        with wave.open(io.BytesIO(data), 'rb') as reader:
            channels = reader.getnchannels()
            sample_width = reader.getsampwidth()
            sample_rate = reader.getframerate()
            frames = reader.readframes(reader.getnframes())
    except (wave.Error, EOFError) as error:
        detail = f' ({error})' if str(error) else ''
        raise ValueError(_UNREADABLE_AUDIO.format(where='', detail=detail)) from None
    if sample_width == 1:
        values = [(byte - 128) / 128.0 for byte in frames]
    elif sample_width == 3:
        values = [
            int.from_bytes(frames[index : index + 3], 'little', signed=True) / 8388608.0
            for index in range(0, len(frames) - 2, 3)
        ]
    else:
        kind = {2: 'h', 4: 'i'}[sample_width]
        decoded = array.array(kind)
        decoded.frombytes(frames[: len(frames) - len(frames) % sample_width])
        if sys.byteorder == 'big':
            decoded.byteswap()
        scale = float(1 << (8 * sample_width - 1))
        values = [value / scale for value in decoded]
    if channels > 1:
        usable = len(values) - len(values) % channels
        values = [
            sum(values[index : index + channels]) / channels
            for index in range(0, usable, channels)
        ]
    if not values:
        raise ValueError(
            'This WAV file holds no samples. Pass a recording that is not empty.'
        )
    return module.TerminalSound.from_samples(values, sample_rate=sample_rate)


def load_audio(
    file: os.PathLike[str] | str | bytes,
    /,
    *,
    symbol: str | None = None,
) -> Audio:
    """
    Load audio from an audio file: its path, or its bytes.

    WAV, MP3, FLAC, Ogg Vorbis and MP4/AAC files are read, and the format is recognised from
    the content of the file, whatever its name. The whole file is decoded into mono audio.
    Play the result with ``canvas.speaker.play(audio)``, or give it a ``symbol`` and play it
    by name.

    Args:
        file: The path of an audio file, or the bytes of one.
        symbol: A name to register the audio under in [`symbols`][xnano.symbols], so
            ``play(name)`` plays it.

    Returns:
        The [`Audio`][xnano.Audio].

    Raises:
        ImportError: ``xnano-audio`` is not installed. Install it with
            ``pip install "xnano[audio]"``.
        TypeError: ``file`` is neither a path nor bytes.
        FileNotFoundError: No file exists at the path.
        ValueError: The file is not a WAV, MP3, FLAC, Ogg Vorbis or MP4/AAC file that xnano
            can read, or ``symbol`` cannot be a symbol name, or another kind of value
            already has it.

    Examples:
        ```python
        import io
        import wave

        import xnano

        data = io.BytesIO()
        with wave.open(data, 'wb') as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(8000)
            writer.writeframes(bytes([0, 64]) * 800)
        beep = xnano.load_audio(data.getvalue(), symbol='beep')
        assert beep.duration_milliseconds == 100.0
        with xnano.new(width=8, height=1) as canvas:
            canvas.speaker.play('beep')
            canvas.clock.step(delta_seconds=0.1)
            assert canvas.speaker.render().peak > 0.0
        ```
    """
    module = require('audio', needed_for='xnano.load_audio')
    if isinstance(file, bytes):
        terminal_sound = _decode_audio_bytes(module, file)
    elif isinstance(file, (str, os.PathLike)):
        path = pathlib.Path(file)
        if not path.is_file():
            raise FileNotFoundError(
                f'load_audio could not load {str(path)!r}, because no audio file exists '
                f'there. Check the path, or pass the bytes of the file.'
            )
        terminal_sound = _decode_audio_path(module, path)
    else:
        raise TypeError(
            f'load_audio needs the path of an audio file or the bytes of one, but got '
            f'{type(file).__name__}. Pass xnano.load_audio("song.mp3"); for samples use '
            f'xnano.Audio.from_samples(), and for an xnano_audio.TerminalSound use '
            f'xnano.Audio(terminal_sound).'
        )
    return Audio(terminal_sound, symbol=symbol)
