"""
Notes as values, rendered without a device and played on the keyboard.

``xnano.note`` makes a note that needs no sound device, and ``symbol='kick'`` registers it so
``xnano.play('kick')`` plays it by name. The first part of this program plays a short melody
on a canvas whose clock you move, and ``render_sound()`` returns the sound of those seconds, so
the numbers it prints are the same on every run. ``xnano.from_audio`` loads a PCM WAV file or
bytes (here a tone built in memory) and registers it as ``'clip'``. ``@xnano.playable`` makes a
function that returns a note, and ``xnano.play(arpeggio())`` plays what it returns.
Then the screen opens: ``k`` plays the kick, ``c`` the clip, ``m`` the melody, ``p`` the
arpeggio, and ``q`` quits.
"""

import io
import math
import struct
import wave

import xnano
from xnano.context import Context


def tone(frequency: float, seconds: float) -> bytes:
    """A mono 16-bit WAV file of one sine tone."""
    rate = 8000
    frames = b''.join(
        struct.pack('<h', round(12000 * math.sin(math.tau * frequency * index / rate)))
        for index in range(round(rate * seconds))
    )
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(rate)
        file.writeframes(frames)
    return buffer.getvalue()


xnano.note('C2', instrument='kick', symbol='kick')
xnano.from_audio(tone(440, 0.4), symbol='clip')
melody = [
    xnano.note(name, beats=0.5, instrument='bell') for name in ('C4', 'E4', 'G4', 'C5')
]


@xnano.playable
def arpeggio(context: Context) -> list[xnano.Note]:
    """Three notes that climb."""
    return [
        xnano.note(name, beats=0.25, instrument='bell') for name in ('C4', 'E4', 'G4')
    ]


with xnano.new(width=20, height=1, bpm=120, fps=10) as offline:
    offline.play(melody)
    offline.play('kick')
    offline.step(delta_seconds=2.0)
    sound = offline.audio.render_sound()
    seconds = sound.duration_milliseconds / 1000
    print(f'offline: {seconds:.1f} seconds, peak {sound.peak:.2f}')  # noqa: T201

with xnano.open(width=50, height=3, bpm=120) as terminal:
    terminal.write('k kick   c clip   m melody   p arpeggio   q quit')
    message = terminal.write('nothing played yet', y=2)

    @terminal.hook(on='key', keys='k')
    def kick(context: Context) -> None:
        xnano.play('kick')
        message.text = 'played the kick by name'

    @terminal.hook(on='key', keys='c')
    def clip(context: Context) -> None:
        xnano.play('clip')
        message.text = 'played the clip loaded with from_audio'

    @terminal.hook(on='key', keys='m')
    def tune(context: Context) -> None:
        xnano.play(melody)
        message.text = f'played {len(melody)} notes at {context.canvas.bpm:g} bpm'

    @terminal.hook(on='key', keys='p')
    def climb(context: Context) -> None:
        xnano.play(arpeggio())
        message.text = 'played the arpeggio, a playable function'

    terminal.run(quit_on='q')
