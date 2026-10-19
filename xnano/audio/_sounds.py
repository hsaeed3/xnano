"""
xnano.audio._sounds

Sounds loaded from WAV files or built from samples.
"""

from __future__ import annotations

import array
import dataclasses
import io
import os
import pathlib
import sys
from typing import TYPE_CHECKING, Final

from xnano import symbols
from xnano._internal._optional import require

if TYPE_CHECKING:
    from types import ModuleType

    from xnano_audio import TerminalSound

    from xnano.region import Region

__all__ = ['Sound', 'load_sound']

SOUND_PITCH_ROW: Final = 60
"""The MIDI number of middle C: the row of the timeline a sound with no pitch of its own is placed on."""


@dataclasses.dataclass(frozen=True, slots=True, init=False)
class Sound:
    """
    A sound you can play with [`Canvas.play`][xnano.canvas.Canvas.play] or
    [`AudioDevice.play`][xnano.audio.AudioDevice.play].

    Make one from the path of a WAV file, the bytes of one, or a
    [`TerminalSound`][xnano_audio.TerminalSound].

    Maps to [`xnano_audio.TerminalSound`][xnano_audio.TerminalSound].

    Attributes:
        samples: The rendered samples.
        symbol: The name the sound is registered under in [`symbols`][xnano.symbols], or
            ``None``. ``play('kick')`` plays the sound registered as ``'kick'``.
        region: The sound on the timeline as a piano roll: a
            [`Region`][xnano.region.Region] that starts at beat 0, lasts as long as the
            sound at 120 beats per minute and covers the single row of middle C, because a
            sound has no pitch of its own.

    Examples:
        ```python
        import xnano
        from xnano_audio import TerminalSound

        sound = xnano.Sound(TerminalSound.from_samples([0.0, 0.5, -0.5, 0.0]))
        assert sound.samples.sample_rate == 44100
        assert (sound.region.y, sound.region.height) == (60, 1)
        ```
    """

    samples: TerminalSound
    """The rendered samples. Maps to [`xnano_audio.TerminalSound`][xnano_audio.TerminalSound]."""
    symbol: str | None
    """The registered symbol name, or ``None``."""

    def __init__(
        self,
        source: TerminalSound | os.PathLike[str] | str | bytes,
        *,
        symbol: str | None = None,
    ) -> None:
        """
        Load a sound.

        Args:
            source: The path of a WAV file, the bytes of one, or a sound.
            symbol: A name to register the sound under in [`symbols`][xnano.symbols], so
                ``play(name)`` plays it.

        Raises:
            ImportError: ``xnano-audio`` is not installed. Install it with
                ``pip install "xnano[audio]"``.
            TypeError: ``source`` is not a path, bytes or a sound.
            FileNotFoundError: ``source`` is a path to a file that does not exist.
            ValueError: The file is not a PCM WAV file that xnano can read, or ``symbol`` cannot
                be a symbol name, or another kind of value already has it.
        """
        module = require('audio', needed_for='xnano.Sound')
        if isinstance(source, module.TerminalSound):
            samples = source
        elif isinstance(source, bytes):
            samples = _decode_wave(module, source)
        elif isinstance(source, (str, os.PathLike)):
            path = pathlib.Path(source)
            if not path.is_file():
                raise FileNotFoundError(
                    f'Sound could not load {str(path)!r}, because no WAV file exists '
                    f'there. Check the path, or pass the bytes of the sound.'
                )
            samples = _decode_wave(module, path.read_bytes())
        else:
            raise TypeError(
                f'Sound needs the path of a WAV file, the bytes of one or a sound, but got '
                f'{type(source).__name__}. Pass xnano.load_sound("sound.wav").'
            )
        object.__setattr__(self, 'samples', samples)
        object.__setattr__(self, 'symbol', symbol)
        if symbol is not None:
            symbols.register(symbol, self)

    @property
    def region(self) -> Region[float]:
        """
        The sound on the timeline as a piano roll.

        The region starts at beat 0 and lasts as long as the sound does at 120 beats per
        minute, the tempo of [`play`][xnano.play] when no canvas is running, so its
        ``milliseconds`` view is the duration of the sound. A sound has no pitch of its
        own, so the region covers the one row of middle C (60). ``context.region`` of a hook
        on a playable measures at the tempo of the canvas instead.

        Examples:
            ```python
            import xnano
            from xnano_audio import TerminalSound

            sound = xnano.Sound(TerminalSound.from_samples([0.0] * 44100))
            assert sound.region.milliseconds.width == 1000.0
            assert (sound.region.y, sound.region.height) == (60, 1)
            ```
        """
        from xnano.audio._notes import _DEFAULT_BPM
        from xnano.region import _timeline_region

        duration_seconds = self.samples.duration_milliseconds / 1000.0
        return _timeline_region(
            start_beats=0.0,
            length_beats=duration_seconds * _DEFAULT_BPM / 60.0,
            pitches=(SOUND_PITCH_ROW,),
            tempo_changes=((0.0, _DEFAULT_BPM),),
        )


def _decode_wave(module: ModuleType, data: bytes) -> TerminalSound:
    """Decode the bytes of a PCM WAV file into a mono sound."""
    import wave  # only loading a sound file needs it

    try:
        with wave.open(io.BytesIO(data), 'rb') as reader:
            channels = reader.getnchannels()
            sample_width = reader.getsampwidth()
            sample_rate = reader.getframerate()
            frames = reader.readframes(reader.getnframes())
    except (wave.Error, EOFError) as error:
        detail = f' ({error})' if str(error) else ''
        raise ValueError(
            f'This is not a PCM WAV file that xnano can read{detail}. Convert the sound '
            f'to a 16-bit PCM WAV file, or build a sound with xnano_audio.TerminalSound.'
        ) from None
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


def load_sound(
    source: TerminalSound | os.PathLike[str] | str | bytes,
    /,
    *,
    symbol: str | None = None,
) -> Sound:
    """
    Load a sound from a WAV file path or from bytes.

    This is [`Sound`][xnano.Sound] with the same arguments. Play the result with
    ``canvas.play(sound)``, or give it a ``symbol`` and play it by name.

    Args:
        source: The path of a PCM WAV file, the bytes of one, or a
            [`TerminalSound`][xnano_audio.TerminalSound].
        symbol: A name to register the sound under in [`symbols`][xnano.symbols], so
            ``play(name)`` plays it.

    Returns:
        The [`Sound`][xnano.Sound].

    Raises:
        ImportError: ``xnano-audio`` is not installed. Install it with
            ``pip install "xnano[audio]"``.
        TypeError: ``source`` is not a path, bytes or a sound.
        ValueError: The file is not a PCM WAV file that xnano can read.
        FileNotFoundError: The path does not exist.

    Examples:
        ```python
        import xnano
        from xnano_audio import TerminalSound

        beep = xnano.load_sound(TerminalSound.from_samples([0.0, 0.5, -0.5, 0.0]), symbol='beep')
        with xnano.new(width=8, height=1) as canvas:
            canvas.play('beep')
            canvas.step(delta_seconds=0.1)
            assert canvas.audio.render_sound().peak > 0.0
        ```
    """
    require('audio', needed_for='xnano.load_sound')
    return Sound(source, symbol=symbol)
