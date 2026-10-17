"""
Effects on what you wrote, started from a key.

``placement.fx`` has one method for each visual effect, named after it, so a hook can start an
effect on any placement: ``content.fx.fade_to(foreground='red')`` or ``content.fx.glitch()``.
An effect starts at once, a second one of the same kind replaces the first, and
``content.fx.clear()`` stops them. ``canvas.fx`` does the same for the whole canvas and
``canvas.audio.fx`` for the sound of everything the canvas plays. The canvas fills the window,
asked for as ``width='100%', height='100%'``, and a hook written without parameters is called
without the context.
Press any key to give the text a new color, ``e`` to fade it to red, ``g`` to glitch it, ``x``
to clear the effects, and ``q`` to quit.
"""

import random

import xnano

colors = random.Random(4)


def random_rgb_color() -> tuple[int, int, int]:
    return (colors.randint(80, 255), colors.randint(80, 255), colors.randint(80, 255))


with xnano.open(width='100%', height='100%') as terminal:
    content = terminal.write(
        'Press any key to change the color of this text', x='center', y='center'
    )
    terminal.write('e fade   g glitch   x clear   q quit')
    status = terminal.write('effects: none', y='bottom')

    def describe() -> None:
        running = ', '.join(effect.customization_kind for effect in content.fx.active)
        status.text = f'effects: {running or "none"}'

    @terminal.hook(on='key')
    def change_color(context: xnano.Context) -> None:
        key = context.keyboard.key
        if key == 'e':
            content.fx.fade_to(
                foreground='red', duration_milliseconds=600, interpolation='quad_in_out'
            )
        elif key == 'g':
            content.fx.glitch(duration_milliseconds=800)
        elif key not in ('x', 'q'):
            content.color.fg = random_rgb_color()
        describe()

    @terminal.hook(on='key', keys='x')
    def clear():
        content.fx.clear()
        describe()

    terminal.run(quit_on='q')
