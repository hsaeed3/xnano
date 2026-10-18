"""
Effects: some tachyonfx effects, one after another.

``placement.fx`` has one method for each effect, so ``banner.fx.dissolve()`` starts a
dissolve on the banner at once. The terminal cycles through some of them every two seconds.
Press ``q`` to quit.
"""

import itertools

import xnano

with xnano.open(width=50, height=7) as terminal:
    heading = terminal.write('')
    banner = terminal.write('xnano  xnano  xnano  xnano  xnano\n' * 4, y=3)

    effects = itertools.cycle(
        [
            ('fade_to', lambda: banner.fx.fade_to(foreground=(255, 80, 80))),
            ('dissolve', banner.fx.dissolve),
            ('coalesce', banner.fx.coalesce),
            ('evolve', lambda: banner.fx.evolve(symbols='shaded')),
            ('sweep_in', lambda: banner.fx.sweep_in(direction='left_to_right')),
            ('slide_in', lambda: banner.fx.slide_in(direction='up_to_down')),
            ('expand', lambda: banner.fx.expand(direction='horizontal')),
            ('explode', lambda: banner.fx.explode(force=6.0)),
            ('hsl_shift', lambda: banner.fx.hsl_shift(foreground=(180.0, 0.0, 0.0))),
        ]
    )

    def show_next_effect() -> None:
        name, start = next(effects)
        heading.text = f'effect: {name}'
        banner.fx.clear()
        start()

    show_next_effect()
    terminal.hook(show_next_effect, on='tick', every=2.0)
    terminal.run(quit_on='q')
