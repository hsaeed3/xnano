"""
How things look: colors, borders, padding, margin and effects.

Every canvas, placement and region has the same four properties. ``color.fg`` and ``color.bg``
are the text and background colors, and ``color.bg.darken(0.1)`` changes the owner in place.
``border`` takes a kind (``'plain'``, ``'rounded'``, ``'double'``, ``'thick'``) or ``False``,
and each side has its own: ``border.top = 'double'``. ``padding`` and ``margin`` can be set one
edge at a time. Several assignments in a row are drawn together, once per frame. The card starts
with an effect from ``effects=[...]``, and ``context.fx`` starts another while a hook runs.
Press ``b`` for the next border, ``t`` for a double top, ``c`` for the next text color, ``d`` and
``l`` to darken and lighten, ``p`` to widen the padding, ``f`` to start the fade and again to
clear it with ``context.fx.clear()``, and ``q`` to quit.
"""

import xnano
from xnano.context import Context

BORDERS = ('plain', 'rounded', 'double', 'thick')
COLORS = ('white', 'yellow', 'green', 'cyan', 'magenta')

with xnano.open(width=70, height=12) as terminal:
    terminal.write('b border  t top  c color  d darker  l lighter  p pad  f fade  q quit')
    card = terminal.write(
        'a card with a look',
        y=2,
        x=3,
        border='rounded',
        background='#335577',
        padding={'horizontal': 2, 'vertical': 1},
        effects=[{'kind': 'effect.coalesce', 'duration_milliseconds': 600}],
    )
    status = terminal.write('', y=11)
    chosen = [0]
    is_fading = [False]

    def describe() -> None:
        status.text = (
            f'border {card.border.kind}   padding {card.padding.left}   '
            f'text {COLORS[chosen[0]]}   fade {"on" if is_fading[0] else "off"}'.ljust(70)
        )

    describe()

    @terminal.hook(on='key', keys='b')
    def next_border(context: Context) -> None:
        card.border = BORDERS[(BORDERS.index(card.border.kind) + 1) % len(BORDERS)]
        card.border.color = 'cyan'
        describe()

    @terminal.hook(on='key', keys='t')
    def double_top(context: Context) -> None:
        card.border.top = 'double'

    @terminal.hook(on='key', keys='c')
    def next_color(context: Context) -> None:
        chosen[0] = (chosen[0] + 1) % len(COLORS)
        card.color.fg = COLORS[chosen[0]]
        describe()

    @terminal.hook(on='key', keys='d')
    def darker(context: Context) -> None:
        card.color.bg.darken(0.15)

    @terminal.hook(on='key', keys='l')
    def lighter(context: Context) -> None:
        card.color.bg.lighten(0.15)

    @terminal.hook(on='key', keys='p')
    def wider(context: Context) -> None:
        card.padding.left = card.padding.left + 1
        card.padding.right = card.padding.right + 1
        describe()

    @terminal.hook(on='key', keys='f')
    def fade(context: Context) -> None:
        if is_fading[0]:
            context.fx.clear()
        else:
            context.fx('effect.fade_to', foreground='red', duration_milliseconds=500)
        is_fading[0] = not is_fading[0]
        describe()

    terminal.run(quit_on='q')
