"""
xnano-audio

`xnano-audio` is the audio backend for `xnano`, as well as an easy way to synthesize,
play, and capture sound in Python without any audio files, system tooling, or additional
compilation steps. Every sound is computed on the fly; nothing is bundled or loaded from disk.

It is deliberately decoupled from `xnano-core`: this package owns the platform audio
libraries, so a missing audio device (or a build without device support) can never take
down the terminal core. Use `detect_audio_capabilities` to find out what is available
before opening a device.

Unlike `xnano-core`, everything is exported directly from this module rather than split
across submodules. The public API is made up of independent parts:

    - **Synthesis**: Built-in instruments and effects, rendered to plain samples. This needs
    no audio device, so it works everywhere (including CI).

        - `render_note`, `note_to_hertz`, `instrument_names`, `is_percussive`: Render a note
        from a built-in instrument, convert note names to frequencies, and inspect what is
        available.

        - `TerminalSound`: An immutable, rendered mono sound (raw samples plus their sample rate).

        - `TerminalAudioEffect`: An immutable, reusable effect description, applied in order when
        rendering or playing a sound.

    - **Melodies**: `TerminalNote`, `TerminalMelody`, `TerminalTempoMap`,
    `TerminalTimeSignature` and `TerminalScheduledNote` describe notes on a beat timeline.
    A melody reports which notes are due between two readings of any clock and renders to
    a `TerminalSound`.

    - **Playback**: `TerminalAudioPlayer` plays sounds and instruments on the default output
    device, with a musical clock for sample-accurate timing.

    - **Capture**: `TerminalMicrophone` reads the level of the default input device.

Device failures are raised as `TerminalAudioError`; a missing device, or a build without
device support, is raised as its subclass `TerminalAudioUnavailableError`.
"""

from typing import Protocol

from xnano_audio._audio_types import InstrumentName, NoteName, Pitch
from xnano_audio._xnano_audio import (
    TerminalAudioCapabilities,
    TerminalAudioEffect,
    TerminalAudioError,
    TerminalAudioPlayer,
    TerminalAudioStream,
    TerminalAudioUnavailableError,
    TerminalMelody,
    TerminalMicrophone,
    TerminalNote,
    TerminalPCMFormat,
    TerminalPlayback,
    TerminalScheduledNote,
    TerminalSound,
    TerminalStreamingAudioPlayer,
    TerminalTempoMap,
    TerminalTimeSignature,
    __version__,
    detect_audio_capabilities,
    instrument_names,
    is_optimized_build,
    is_percussive,
    note_to_hertz,
    render_note,
)


class TerminalAudioSource(Protocol):
    """
    A producer-worker audio source.

    Python callbacks never execute on the device thread: a worker thread calls ``read`` ahead
    of playback.
    """

    @property
    def format(self) -> TerminalPCMFormat:
        """The layout of the bytes ``read`` returns."""
        ...

    def read(self, frames: int) -> bytes:
        """Return up to ``frames`` complete interleaved PCM frames; empty bytes means the end."""
        ...

    def close(self) -> None:
        """Release whatever the source holds."""
        ...


__all__ = (
    'InstrumentName',
    'NoteName',
    'Pitch',
    'TerminalAudioCapabilities',
    'TerminalAudioEffect',
    'TerminalAudioError',
    'TerminalAudioPlayer',
    'TerminalAudioSource',
    'TerminalAudioStream',
    'TerminalAudioUnavailableError',
    'TerminalMelody',
    'TerminalMicrophone',
    'TerminalNote',
    'TerminalPCMFormat',
    'TerminalPlayback',
    'TerminalScheduledNote',
    'TerminalSound',
    'TerminalStreamingAudioPlayer',
    'TerminalTempoMap',
    'TerminalTimeSignature',
    '__version__',
    'detect_audio_capabilities',
    'instrument_names',
    'is_optimized_build',
    'is_percussive',
    'note_to_hertz',
    'render_note',
)
