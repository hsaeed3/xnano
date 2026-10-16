"""
Pixel art written as text.

``from_art`` turns a block of characters into an image, one character per pixel. The palette is
one short string of ``character=color`` pairs, any character it does not name (here ``.``) is
transparent, and the same palette serves every sprite. Added to a terminal with a width twice
its own, a sprite is enlarged by a whole number with hard edges, and a list of frames becomes an
animation with ``TerminalImage.from_frames``. Press ``q`` to quit.
"""

import xnano
from xnano.image import TerminalImage, from_art
from xnano.styles import Style

PALETTE = (
    'K=#2b1b33 R=#e03040 W=#fff3e0 P=#ff9aa8 Y=#ffd23f O=#f08a24 C=#f4d9a6 '
    'B=#4aa3ff L=#b8e2ff E=#14101c'
)

HEART = from_art(
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

STAR = from_art(
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

MUSHROOM = from_art(
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

SLIME = TerminalImage.from_frames(
    [
        from_art(
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
            PALETTE,
        ),
        from_art(
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
            PALETTE,
        ),
    ]
).with_frames_per_second(3)


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
            terminal.write(xnano.Image(sprite), x=column, y=2, width=sprite.width * 2)
            terminal.write(name.center(20), x=column - 1, y=11, style=Style(dim=True))
        terminal.run(quit_on='q')


if __name__ == '__main__':
    main()
