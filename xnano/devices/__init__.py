"""
xnano.devices

The devices a terminal is made of: its [`Screen`][xnano.devices.Screen], its
[`Speaker`][xnano.devices.Speaker], its [`Microphone`][xnano.audio.Microphone], its
[`Keyboard`][xnano.devices.Keyboard], its [`Mouse`][xnano.devices.Mouse] and its
[`Clock`][xnano.devices.Clock].

A canvas has every device, on the screen or off it: ``canvas.screen``, ``canvas.speaker``,
``canvas.microphone``, ``canvas.keyboard``, ``canvas.mouse`` and ``canvas.clock``. Inside a hook
the context has the same devices, and its ``keyboard`` and ``mouse`` also read the event being
handled. You do not create these classes; they are what those attributes are.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from xnano._schema._hooks import KeyName as KeyName
from xnano._schema._hooks import KeyNames as KeyNames
from xnano._schema._media import PlayOptions as PlayOptions
from xnano.devices._clock import Beats as Beats
from xnano.devices._clock import Clock as Clock
from xnano.devices._cursor import Cursor as Cursor
from xnano.devices._keyboard import Keyboard as Keyboard
from xnano.devices._mouse import HeldButton as HeldButton
from xnano.devices._mouse import Mouse as Mouse
from xnano.devices._mouse import Scroll as Scroll
from xnano.devices._output import Output as Output
from xnano.devices._screen import Screen as Screen
from xnano.devices._speaker import Speaker as Speaker

if TYPE_CHECKING:
    from xnano.audio._microphone import Microphone as Microphone

__all__ = [
    'Beats',
    'Clock',
    'Cursor',
    'HeldButton',
    'KeyName',
    'KeyNames',
    'Keyboard',
    'Microphone',
    'Mouse',
    'Output',
    'PlayOptions',
    'Screen',
    'Scroll',
    'Speaker',
]


def __getattr__(name: str) -> object:
    """Import ``Microphone``, which needs the ``audio`` extra, the first time it is read."""
    if name != 'Microphone':
        raise AttributeError(
            f'xnano.devices has no name {name!r}. Its names are {", ".join(__all__)}.'
        )
    # Imported here so that `import xnano` works without the `audio` extra.
    from xnano.audio import Microphone

    globals()[name] = Microphone
    return Microphone


def __dir__() -> list[str]:
    """The public names of the module, including ``Microphone``."""
    return sorted(__all__)
