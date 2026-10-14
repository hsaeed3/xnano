"""
Write a melody as text, and keep time with the beat.

``terminal.play`` takes a melody written like ``'E4:0.5 G4 rest C5+E5'``: a note name, an
optional length in beats after a colon, ``rest`` for silence and ``+`` for a chord. Lengths are
beats, so ``terminal.tempo`` speeds the whole tune up or slows it down, and
``@terminal.every(beats=1)`` runs a function on every beat of that tempo, ticking a metronome
here. Without a sound device the screen still keeps time.

``m`` plays the tune, ``up`` and ``down`` change the tempo, ``space`` stops and starts time,
``q`` quits.
"""

import xnano
from xnano.context import Context

TUNE = 'E4:0.5 E4:0.5 rest:0.5 E4:0.5 rest:0.5 C4:0.5 E4 G4:2 rest G3:2'


class Beats:
    """How many beats have passed."""

    def __init__(self) -> None:
        self.count = 0


def main() -> None:
    """Show the tempo and the beat, and play the tune on request."""
    beats = Beats()
    with xnano.open(width=56, height=5) as terminal:
        terminal.tempo = 120
        terminal.write('m: play   up/down: tempo   space: pause   q: quit')

        tempo_line = terminal.write('', y=2)
        dot = terminal.write('○', y=3)
        beat_line = terminal.write('', x=3, y=3)

        def show() -> None:
            state = 'paused' if terminal.time.is_paused else 'playing'
            tempo_line.text = f'{terminal.tempo:>5.0f} beats per minute   {state}'
            dot.text = '●' if beats.count % 2 else '○'
            beat_line.text = f'beat {beats.count}'

        show()

        @terminal.every(beats=1)
        def metronome(context: Context) -> None:
            beats.count += 1
            show()
            if terminal.audio.is_available:
                terminal.note(
                    'C6' if beats.count % 4 == 1 else 'G5', beats=0.1, volume=0.3
                )

        @terminal.on_key('m')
        def play_tune(context: Context) -> None:
            if terminal.audio.is_available:
                terminal.play(TUNE, instrument='bell')

        @terminal.on_key('up')
        def faster(context: Context) -> None:
            terminal.tempo = min(240, terminal.tempo + 10)
            show()

        @terminal.on_key('down')
        def slower(context: Context) -> None:
            terminal.tempo = max(40, terminal.tempo - 10)
            show()

        @terminal.on_key('space')
        def toggle_time(context: Context) -> None:
            if terminal.time.is_paused:
                terminal.time.resume()
            else:
                terminal.time.pause()
            show()

        terminal.run(quit_on='q')


if __name__ == '__main__':
    main()
