"""
Write a song as text.

Each part of the song is a plain string. A note is its name, such as ``C4`` or ``F#5``; add a
colon and a number to hold it for that many beats (``E5:0.5`` is half a beat), and a note on its
own lasts one beat. ``rest`` is a silence and ``|`` just marks the end of a bar. To play a part,
give it to ``terminal.play`` with an instrument; to play several parts together, play them one
after another in the same function. ``terminal.tempo`` sets the beats per minute, and
``@terminal.every(beats=32)`` plays the song again every eight bars. Press ``space`` to stop and
restart time, and ``q`` to quit.

The tune is an original piece in the style of an old game's town theme.
"""

import xnano
from xnano.context import Context

# Eight bars of four beats each, in E minor.
LEAD = """
    E5:0.5 G5:0.5 B5 A5:0.5 G5:0.5 E5  |  F#5 E5 D5 E5  |
    G5:0.5 B5:0.5 D6 C6:0.5 B5:0.5 A5  |  G5:2 F#5 rest  |
    B5 B5:0.5 A5:0.5 G5 A5             |  B5 B5:0.5 A5:0.5 G5 E5  |
    C6 B5:0.5 A5:0.5 B5 G5             |  E5:3 rest
"""

BASS = """
    E3:0.5 E3:0.5 B3:0.5 E3:0.5  E3:0.5 E3:0.5 B3:0.5 E3:0.5  |
    D3:0.5 D3:0.5 A3:0.5 D3:0.5  D3:0.5 D3:0.5 A3:0.5 D3:0.5  |
    C3:0.5 C3:0.5 G3:0.5 C3:0.5  C3:0.5 C3:0.5 G3:0.5 C3:0.5  |
    B2:0.5 B2:0.5 F#3:0.5 B2:0.5  B2:0.5 B2:0.5 F#3:0.5 B2:0.5  |
    C3:0.5 C3:0.5 G3:0.5 C3:0.5  C3:0.5 C3:0.5 G3:0.5 C3:0.5  |
    D3:0.5 D3:0.5 A3:0.5 D3:0.5  D3:0.5 D3:0.5 A3:0.5 D3:0.5  |
    G2:0.5 G2:0.5 D3:0.5 G2:0.5  G2:0.5 G2:0.5 D3:0.5 G2:0.5  |
    B2:0.5 B2:0.5 F#3:0.5 B2:0.5  B2:0.5 B2:0.5 F#3:0.5 B2:0.5
"""

# The drums are the same bar eight times; in Python, a string can be repeated with ``*``.
KICK = 'C2 rest C2 rest | ' * 8
SNARE = 'rest C3 rest C3 | ' * 8
HIHAT = 'C5:0.5 C5:0.5 C5:0.5 C5:0.5 C5:0.5 C5:0.5 C5:0.5 C5:0.5 | ' * 8

with xnano.open(width=60, height=6) as terminal:
    terminal.tempo = 132
    terminal.write('A song written as text', x='center', y=0)
    where = terminal.write('bar 1   beat 1', y=2)
    terminal.write('space: stop time   q: quit', y=5)

    def play_song() -> None:
        if not terminal.audio.is_available:
            terminal.write('(no sound device here: the bars still count)', y=4)
            return
        terminal.play(LEAD, instrument='square', volume=0.55)
        terminal.play(BASS, instrument='triangle', volume=0.8)
        terminal.play(KICK, instrument='kick', volume=0.9)
        terminal.play(SNARE, instrument='snare', volume=0.5)
        terminal.play(HIHAT, instrument='hihat', volume=0.25)

    play_song()

    @terminal.every(beats=32)
    def repeat(context: Context) -> None:
        play_song()

    @terminal.every(beats=1)
    def show_the_beat(context: Context) -> None:
        beats_played = int(context.clock.elapsed_seconds * terminal.tempo / 60)
        bar, beat = divmod(beats_played % 32, 4)
        where.text = f'bar {bar + 1}   beat {beat + 1}'

    @terminal.on_key('space')
    def stop_or_start_time(context: Context) -> None:
        if terminal.is_paused:
            terminal.resume()
        else:
            terminal.pause()

    terminal.run(quit_on='q')
