"""
A pixel-art piano: press a key and it goes down, sounds its note and sends a note floating up.

The keys ``a s d f g h j k`` play the white keys from C4 to C5 and ``w e t y u`` play the
black keys. A key stays down for as long as it is held (in terminals that report key
releases, such as Kitty) and for a moment after a quick tap. Notes play through
``context.speaker`` on the electric piano. Run it with ``python sound.py`` and press ``q``
to quit.
"""

import math

import xnano
from xnano.art import Art
from xnano.audio import Pitch
from xnano.styles import Style
from xnano.widgets import Paragraph

WIDTH, HEIGHT = 80, 46  # in pixels: a cell holds two, one above the other
WHITE_PITCHES: tuple[Pitch, ...] = ("C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5")
BLACK_PITCHES: tuple[Pitch, ...] = ("C#4", "D#4", "F#4", "G#4", "A#4")
WHITE_KEYS = dict(zip("asdfghjk", WHITE_PITCHES, strict=True))
BLACK_KEYS = dict(zip("wetyu", BLACK_PITCHES, strict=True))
# the white key that each black key sits just before
BLACK_KEY_PLACES = dict(zip("wetyu", [1, 2, 4, 5, 6], strict=True))
NOTES = WHITE_KEYS | BLACK_KEYS
TAP_SECONDS = 0.15  # how long a key shows down after a tap that sends no release
FLOAT_SECONDS = 1.3  # how long a note floats up after its key is pressed

KEYS_LEFT, KEYS_TOP, KEY_SPACING = 4, 20, 9  # each white key is 8 pixels and a gap
WHITE_HEIGHT, BLACK_WIDTH, BLACK_HEIGHT = 24, 5, 15
CASE, CASE_EDGE, FELT = (108, 92, 168), (140, 124, 200), (232, 118, 170)
BACKING = (52, 44, 88)  # the dark wood between and behind the keys
WHITE, WHITE_SIDE, WHITE_LIP = (246, 242, 236), (222, 214, 204), (200, 190, 178)
BLACK, BLACK_SHINE, BLACK_LIP = (44, 40, 62), (74, 68, 100), (92, 86, 120)
COLORS = (
    (232, 118, 170),  # pastel pink
    (96, 152, 236),  # pastel blue
    (148, 108, 230),  # purple
    (228, 160, 62),  # light amber
)
NOTE_SPRITE = ("...##.", "...#.#", "...#..", "...#..", ".###..", "####..", ".##...")
SPARKLE_SPRITE = (".#.", "###", ".#.")
HINT = "a s d f g h j k  white keys  ·  w e t y u  black keys"

pressed_at: dict[str, float] = {}  # each key, and when it was last pressed
# each note in the air: the key that sent it up and when
floating_notes: list[tuple[str, float]] = []


def fill(
    pixels: bytearray,
    left: int,
    top: int,
    width: int,
    height: int,
    color: tuple[int, ...],
) -> None:
    """Paint a rectangle of pixels in one color."""
    for row in range(top, top + height):
        start = (row * WIDTH + left) * 4
        pixels[start : start + width * 4] = bytes((*color, 255)) * width


def stamp(
    pixels: bytearray,
    sprite: tuple[str, ...],
    left: int,
    top: int,
    color: tuple[int, ...],
) -> None:
    """Paint the ``#`` pixels of a sprite, skipping any that fall outside the picture."""
    for row, line in enumerate(sprite):
        for column, character in enumerate(line):
            is_inside = 0 <= top + row < HEIGHT and 0 <= left + column < WIDTH
            if character == "#" and is_inside:
                fill(pixels, left + column, top + row, 1, 1, color)


def key_color(key: str) -> tuple[int, int, int]:
    """The color a key lights up in, and the color of the notes it sends up."""
    return COLORS[list(NOTES).index(key) % len(COLORS)]


def key_center(key: str) -> int:
    """The pixel column in the middle of a key."""
    if key in WHITE_KEYS:
        return KEYS_LEFT + list(WHITE_KEYS).index(key) * KEY_SPACING + 4
    return KEYS_LEFT + BLACK_KEY_PLACES[key] * KEY_SPACING - 1


def is_down(context: xnano.Context, key: str) -> bool:
    """Whether a key is held right now, or was tapped a moment ago."""
    since_press = context.clock.elapsed_seconds - pressed_at.get(key, -TAP_SECONDS)
    return since_press < TAP_SECONDS or context.keyboard.is_down(key)


def draw_white_key(pixels: bytearray, key: str, is_pressed: bool) -> None:
    """A white key: lit and one pixel lower, with a thinner front edge, while pressed."""
    left = KEYS_LEFT + list(WHITE_KEYS).index(key) * KEY_SPACING
    if is_pressed:
        color = key_color(key)
        lip = tuple(channel * 3 // 4 for channel in color)
        fill(pixels, left, KEYS_TOP + 1, 8, WHITE_HEIGHT - 2, color)
        fill(pixels, left, KEYS_TOP + WHITE_HEIGHT - 1, 8, 1, lip)
    else:
        fill(pixels, left, KEYS_TOP, 8, WHITE_HEIGHT - 2, WHITE)
        fill(pixels, left + 7, KEYS_TOP, 1, WHITE_HEIGHT - 2, WHITE_SIDE)
        fill(pixels, left, KEYS_TOP + WHITE_HEIGHT - 2, 8, 2, WHITE_LIP)


def draw_black_key(pixels: bytearray, key: str, is_pressed: bool) -> None:
    """A black key, drawn over the edges of the white keys on either side of it."""
    left = key_center(key) - BLACK_WIDTH // 2
    fill(pixels, left, KEYS_TOP, BLACK_WIDTH, BLACK_HEIGHT + 1, BACKING)
    if is_pressed:
        fill(pixels, left, KEYS_TOP + 1, BLACK_WIDTH, BLACK_HEIGHT - 2, key_color(key))
        fill(pixels, left, KEYS_TOP + BLACK_HEIGHT - 1, BLACK_WIDTH, 1, BLACK_LIP)
    else:
        fill(pixels, left, KEYS_TOP, BLACK_WIDTH, BLACK_HEIGHT - 2, BLACK)
        fill(pixels, left, KEYS_TOP, 1, BLACK_HEIGHT - 2, BLACK_SHINE)
        fill(pixels, left, KEYS_TOP + BLACK_HEIGHT - 2, BLACK_WIDTH, 2, BLACK_LIP)


@xnano.writable
def piano(context: xnano.Context) -> Art:
    """The piano with every key as it is now, and the notes floating above it."""
    now = context.clock.elapsed_seconds
    # red, green, blue and alpha for every pixel, all transparent to begin with
    pixels = bytearray(WIDTH * HEIGHT * 4)
    keys_width = len(WHITE_KEYS) * KEY_SPACING + 1
    case_left, case_top, case_width = KEYS_LEFT - 3, KEYS_TOP - 6, keys_width + 4
    fill(pixels, case_left, case_top, case_width, WHITE_HEIGHT + 8, CASE)
    fill(pixels, case_left + 1, case_top, case_width - 2, 1, CASE_EDGE)
    for corner_x in (case_left, case_left + case_width - 1):  # round off the corners
        for corner_y in (case_top, case_top + WHITE_HEIGHT + 7):
            start = (corner_y * WIDTH + corner_x) * 4
            pixels[start : start + 4] = bytes(4)  # transparent again
    fill(pixels, KEYS_LEFT - 1, KEYS_TOP - 2, keys_width, 1, FELT)
    fill(pixels, KEYS_LEFT - 1, KEYS_TOP - 1, keys_width, WHITE_HEIGHT + 1, BACKING)
    for key in WHITE_KEYS:
        draw_white_key(pixels, key, is_down(context, key))
    for key in BLACK_KEYS:
        draw_black_key(pixels, key, is_down(context, key))
    floating_notes[:] = [
        (key, start) for key, start in floating_notes if now - start < FLOAT_SECONDS
    ]
    for key, start in floating_notes:
        progress = (now - start) / FLOAT_SECONDS
        left = key_center(key) + round(math.sin(progress * math.tau))
        top = round(8 - progress * 10)
        if progress < 0.8:
            stamp(pixels, NOTE_SPRITE, left - 3, top, key_color(key))
        else:
            stamp(pixels, SPARKLE_SPRITE, left - 1, top + 2, key_color(key))
    return xnano.pixel_art(bytes(pixels), width=WIDTH, height=HEIGHT)


@xnano.writable
def caption(context: xnano.Context) -> Paragraph:
    """The notes being played, or how to play when nothing is."""
    held = [NOTES[key] for key in NOTES if is_down(context, key)]
    if held:
        text, style = "♪ " + "  ".join(held), Style(bold=True)
    else:
        text, style = HINT, Style(dim=True)
    return Paragraph(text, style=style, width=len(text), height=1)


with xnano.open(title="piano", keyboard="release_events") as terminal:
    terminal.screen.write(piano, x="center", y=0)
    terminal.screen.write(caption, x="center", y="bottom")

    @terminal.hook(on="key", keys=list(NOTES))
    def play(context: xnano.Context) -> None:
        """Press a key down, play its note and send a note floating up."""
        key = context.keyboard.key
        if key is None or context.keyboard.kind != "press":
            return
        pressed_at[key] = context.clock.elapsed_seconds
        floating_notes.append((key, context.clock.elapsed_seconds))
        note = xnano.Note(NOTES[key], beats=1.5, instrument="electric_piano")
        context.speaker.play(note)

    terminal.run(stop_on="q")
