"""
xnano.audio

What is heard: [`Note`][xnano.Note], [`Melody`][xnano.audio.Melody], [`Audio`][xnano.Audio]
and [`load_audio`][xnano.load_audio], [`play`][xnano.play], and the
[`Microphone`][xnano.audio.Microphone]. A canvas plays through its
[`Speaker`][xnano.devices.Speaker]. Making a Note needs nothing; playing, melodies, audio and
the microphone need the optional ``audio`` extra: ``pip install "xnano[audio]"``.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Final

from xnano._internal import _optional
from xnano.audio._audio import Audio as Audio
from xnano.audio._audio import load_audio as load_audio
from xnano.audio._notes import Note as Note
from xnano.audio._notes import PlayHandle as PlayHandle
from xnano.audio._notes import note as note
from xnano.audio._notes import play as play

if TYPE_CHECKING:
    from xnano_audio import InstrumentName as _AudioInstrumentName
    from xnano_audio import NoteName as _AudioNoteName
    from xnano_audio import Pitch as _AudioPitch
    from xnano_audio import TerminalAudioError as _AudioTerminalAudioError
    from xnano_audio import (
        TerminalAudioUnavailableError as _AudioTerminalAudioUnavailableError,
    )
    from xnano_audio import instrument_names as _audio_instrument_names

    from xnano.audio._melodies import Melody as Melody
    from xnano.audio._microphone import Microphone as Microphone

    InstrumentName = _AudioInstrumentName
    """
    The name of a built-in instrument, such as ``'piano'``, ``'bell'`` or ``'kick'``.

    Maps to [`xnano_audio.InstrumentName`][xnano_audio.InstrumentName].
    """

    NoteName = _AudioNoteName
    """
    A note name: a letter, an optional ``#`` or ``b``, and an octave from 0 to 8, such as ``'C4'`` or ``'Bb3'``.

    Maps to [`xnano_audio.NoteName`][xnano_audio.NoteName].
    """

    Pitch = _AudioPitch
    """
    A pitch: a note name such as ``'C#4'`` or a MIDI number from 0 to 127.

    Maps to [`xnano_audio.Pitch`][xnano_audio.Pitch].
    """

    TerminalAudioError = _AudioTerminalAudioError
    """
    Raised when a sound device or stream fails.

    Maps to [`xnano_audio.TerminalAudioError`][xnano_audio.TerminalAudioError].
    """

    TerminalAudioUnavailableError = _AudioTerminalAudioUnavailableError
    """
    Raised when this computer has no sound device, or this build has no device support.

    Maps to [`xnano_audio.TerminalAudioUnavailableError`][xnano_audio.TerminalAudioUnavailableError].
    """

    instrument_names = _audio_instrument_names
    """
    The name of every built-in instrument, in catalog order.

    Maps to [`xnano_audio.instrument_names`][xnano_audio.instrument_names].
    """

__all__ = [
    'Audio',
    'InstrumentName',
    'Melody',
    'Microphone',
    'Note',
    'NoteName',
    'Pitch',
    'PlayHandle',
    'TerminalAudioError',
    'TerminalAudioUnavailableError',
    'instrument_names',
    'load_audio',
    'note',
    'play',
]

_LAZY_NAMES: Final[dict[str, str]] = {
    'InstrumentName': 'xnano_audio',
    'Melody': 'xnano.audio._melodies',
    'Microphone': 'xnano.audio._microphone',
    'NoteName': 'xnano_audio',
    'Pitch': 'xnano_audio',
    'TerminalAudioError': 'xnano_audio',
    'TerminalAudioUnavailableError': 'xnano_audio',
    'instrument_names': 'xnano_audio',
}
"""The module each name that needs the ``audio`` extra comes from."""


def __getattr__(name: str) -> object:
    """Import a name that needs the ``audio`` extra the first time it is read, then keep it."""
    module_name = _LAZY_NAMES.get(name)
    if module_name is None:
        raise AttributeError(
            f'xnano.audio has no name {name!r}. Its names are {", ".join(__all__)}.'
        )
    _optional.require('audio', needed_for=f'xnano.audio.{name}')
    value = getattr(importlib.import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """The public names of the module, including the ones that are imported when first read."""
    return sorted(__all__)
