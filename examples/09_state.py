"""
Typed state that expressions can read.

``open(state=...)`` takes a dataclass. Hooks read and write it through ``context.state``, a
write is checked against the field's type, and ``terminal.ref`` turns a field into an
expression, so the gauge follows the number with no code that redraws it. The gauge's
label flips to the opposite colors where the bar passes under it.
Press ``up`` and ``down`` to change the volume, ``m`` to mute, ``q`` to quit.
"""

import dataclasses

import xnano
from xnano.context import Context, Frame
from xnano.styles import Style
from xnano.widgets import Gauge


@dataclasses.dataclass
class Settings:
    volume: int = 40
    is_muted: bool = False


def volume_of(settings: Settings) -> int:
    """The field the gauge follows."""
    return settings.volume


with xnano.open(width=40, height=4, state=Settings()) as terminal:
    terminal.write('up/down: volume   m: mute   q: quit')
    volume = terminal.ref(volume_of)
    # The gauge draws its label in the opposite colors wherever the bar passes under it.
    bar = Style(foreground=(0, 200, 0), background=(40, 40, 40))
    terminal.write(
        Gauge(volume.number / 100, label='volume', gauge_style=bar, width=40, height=1),
        y=2,
    )

    @terminal.on_key('up')
    def louder(context: Context[Settings]) -> None:
        context.state.volume = min(100, context.state.volume + 5)

    @terminal.on_key('down')
    def quieter(context: Context[Settings]) -> None:
        context.state.volume = max(0, context.state.volume - 5)

    @terminal.on_key('m')
    def mute(context: Context[Settings]) -> None:
        context.state.is_muted = not context.state.is_muted

    status = terminal.write('', y=1)

    @terminal.loop.on_frame
    def show(frame: Frame) -> None:
        state = terminal.state
        text = 'muted' if state.is_muted else f'volume {state.volume}'
        status.text = text

    terminal.run(quit_on='q')
