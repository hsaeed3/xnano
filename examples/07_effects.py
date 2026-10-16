"""
Effects: some tachyonfx effects, one after another.

Each effect is described as data and applied to a buffer. The terminal cycles through some of
them every two seconds. Press ``q`` to quit.
"""

import functools
import itertools

import xnano
from xnano.context import Context
from xnano.effects import Effect

# Each entry builds a fresh effect, so one can run again after it has finished.
EFFECTS = {
    'fade_to': functools.partial(
        Effect.fade_to, (255, 80, 80), duration_milliseconds=1500
    ),
    'dissolve': functools.partial(Effect.dissolve, duration_milliseconds=1500),
    'coalesce': functools.partial(Effect.coalesce, duration_milliseconds=1500),
    'evolve': functools.partial(Effect.evolve, 'shaded', duration_milliseconds=1500),
    'sweep_in': functools.partial(
        Effect.sweep_in, 'left_to_right', duration_milliseconds=1500
    ),
    'slide_in': functools.partial(
        Effect.slide_in, 'up_to_down', duration_milliseconds=1500
    ),
    'expand': functools.partial(Effect.expand, 'horizontal', duration_milliseconds=1500),
    'explode': functools.partial(Effect.explode, force=6.0, duration_milliseconds=1500),
    'hsl_shift': functools.partial(
        Effect.hsl_shift, (180.0, 0.0, 0.0), duration_milliseconds=1500
    ),
}

with xnano.open(width=50, height=7) as terminal:
    banner = terminal.write('xnano  xnano  xnano  xnano  xnano\n' * 4, y=3)
    names = itertools.cycle(EFFECTS)
    heading = terminal.write('')

    def show_next_effect() -> None:
        name = next(names)
        heading.text = f'effect: {name}'
        banner.core_buffer.update(EFFECTS[name]())

    show_next_effect()

    @terminal.every(2.0)
    def cycle(context: Context) -> None:
        show_next_effect()

    terminal.run(quit_on='q')
