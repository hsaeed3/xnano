"""
Pixel art written as text.

``xnano.draw`` turns a block of characters into pixel art, one character per pixel. The palette
is one short string of ``character=color`` pairs, any character it does not name (here ``.``)
is transparent, and the same palette serves every sprite. Written to a terminal, a sprite takes
half as many rows as it has pixel rows, and an animation is one art whose pixels ``replace`` swaps
for the next frame on a timer. Press ``q`` to quit.
"""

import xnano
from xnano.styles import Style

PALETTE = (
    'K=#2b1b33 R=#e03040 W=#fff3e0 P=#ff9aa8 Y=#ffd23f O=#f08a24 C=#f4d9a6 '
    'B=#4aa3ff L=#b8e2ff E=#14101c'
)

HEART = xnano.draw(
    """
    .KKK.KKK.
    KRRRKRRRK
    KRPPRRRRK
    KRPRRRRRK
    .KRRRRRK.
    ..KRRRK..
    ...KRK...
    ....K....
    """,
    PALETTE,
)

STAR = xnano.draw(
    """
    ....K....
    ...KYK...
    ...KYK...
    KKKKYKKKK
    KYYWYYYYK
    .KYYYYYK.
    .KYYKYYK.
    KYYK.KYYK
    KKK...KKK
    """,
    PALETTE,
)

MUSHROOM = xnano.draw(
    """
    ...KKKK...
    .KKRRRRKK.
    KRRWWRRRRK
    KRWWWRRWWK
    KRRRRRRWWK
    KKKKKKKKKK
    ..KCCCCK..
    ..KCCCCK..
    ...KKKK...
    """,
    PALETTE,
)

SLIME_FRAMES = (
    """
    ..........
    ..........
    ...KKKK...
    .KKBBBBKK.
    KBBLLBBBBK
    KBLBBBBBBK
    KBBEBBEBBK
    .KKKKKKKK.
    """,
    """
    ...KKKK...
    ..KBBBBK..
    .KBLLBBBK.
    .KBLBBBBK.
    .KBEBBEBK.
    .KBBBBBBK.
    .KBBBBBBK.
    ..KKKKKK..
    """,
)
SLIME = xnano.draw(SLIME_FRAMES[0], PALETTE)


def main() -> None:
    """Show each sprite, enlarged, with its name under it."""
    with xnano.open(width=84, height=13) as terminal:
        terminal.write(
            'pixel art, written as text', x='center', y=0, style=Style(bold=True)
        )
        for sprite, name, column in (
            (HEART, 'heart', 3),
            (STAR, 'star', 24),
            (MUSHROOM, 'mushroom', 45),
            (SLIME, 'slime', 66),
        ):
            terminal.write(sprite, x=column, y=2)
            terminal.write(name.center(20), x=column - 5, y=11, style=Style(dim=True))
        frames = {'index': 0}

        @terminal.hook(on='tick', every=1 / 3)
        def animate() -> None:
            frames['index'] = (frames['index'] + 1) % len(SLIME_FRAMES)
            SLIME.replace(SLIME_FRAMES[frames['index']], PALETTE)

        terminal.run(quit_on='q')


if __name__ == '__main__':
    main()
