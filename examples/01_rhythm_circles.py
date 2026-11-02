"""
Circles: click each numbered ring on its beat, as a dotted timing ring closes in on it.

The thick ring is the next to click, and the ring cursor follows the mouse. A click near
the beat scores and plays the ring's note, and a ring left unclicked is a miss that breaks
the combo.
"""

import math

import xnano
from xnano.art import Art

COLORS = ('#e8768a', '#946ce6', '#6098ec', '#e4a03e')  # pink, purple, blue and amber
PITCHES = ('C5', 'E5', 'G5', 'C6')  # the note each number plays when its ring is hit
SHAPES = (  # a group of four rings, as the (column, row) of each ring's middle
    ((40, 6), (64, 12), (40, 17), (16, 12)),  # a diamond
    ((12, 6), (30, 17), (48, 6), (66, 17)),  # a zigzag to the right
    ((66, 6), (48, 17), (30, 6), (12, 17)),  # a zigzag to the left
)
MAP = [  # the beat of each ring in seconds and its middle: four on the beat, then a rest
    (1.6 + group * 3.0 + number * 0.6, column, row)
    for group in range(9)
    for number, (column, row) in enumerate(SHAPES[group % len(SHAPES)])
]
RADIUS, TIMING_RADIUS, TIMING_SECONDS = 6, 10, 0.8  # in pixels, two to a cell's height
HIT_SECONDS, TIME_LIMIT = 0.26, 30  # a ring this many seconds past its beat is missed
# how far from its beat a click may be, in seconds, for each word, its color and points
JUDGEMENTS = [(0.1, 'great', 'green', 300), (0.18, 'good', 'yellow', 150)]
JUDGEMENTS += [(HIT_SECONDS, 'fair', 'reset', 50)]
CURSOR = xnano.pixel_art(  # a white ring with a pink rim, so it shows on any background
    '..PPP.. .PWWWP. PW...WP PW...WP .PWWWP. ..PPP..'.split(),
    {'P': '#e8768a', 'W': 'white'},
)
score, combo, judged_at = 0, 0, -1.0
rings = {}  # the rings on screen, by their place in the map
upcoming = list(range(len(MAP)))  # the rings not shown yet


@xnano.writable
def ring_art(context: xnano.Context, index: int) -> Art:
    """A ring, thick when it is the next to click, inside its dotted timing ring."""
    closing = max(0.0, MAP[index][0] - context.clock.elapsed_seconds) / TIMING_SECONDS
    timing_radius = RADIUS + (TIMING_RADIUS - RADIUS) * closing  # meets the ring on time
    inner_radius = RADIUS - 1 if index == min(rings, default=index) else RADIUS - 0.5
    pixels = []
    for pixel_y in range(-TIMING_RADIUS, TIMING_RADIUS + 1):
        line = ''
        for pixel_x in range(-TIMING_RADIUS, TIMING_RADIUS + 1):
            distance = math.hypot(pixel_x, pixel_y)
            is_dot = (pixel_x + pixel_y) % 2 == 0 and abs(distance - timing_radius) < 0.5
            line += '#' if inner_radius <= distance < RADIUS + 0.5 or is_dot else '.'
        pixels.append(line)
    return xnano.pixel_art(pixels, {'#': COLORS[index // 4 % 4]})


def judge(index: int, text: str, color: str, points: int, now: float) -> None:
    """Take the ring off the screen, add its points and show its word below the cursor."""
    global score, combo, judged_at
    rings.pop(index).remove()
    score, combo, judged_at = score + points, combo + 1 if points else 0, now
    _, column, row = MAP[index]
    word.text, word.color.fg = text, color
    word.x, word.y = column - len(text) // 2, row + 2  # two rows below the ring's middle


def show(index: int) -> None:
    """Write a ring with its number in the middle, and judge a press on it."""
    seconds, column, row = MAP[index]
    left, top = column - TIMING_RADIUS, row - TIMING_RADIUS // 2
    rings[index] = ring = game.screen.write(ring_art(index=index), x=left, y=top)
    ring.write(str(index % 4 + 1), x=TIMING_RADIUS, y=TIMING_RADIUS // 2, bold=True)

    @ring.hook(on='mouse')
    def click(context: xnano.Context) -> None:
        """Judge a press by how far it is from the beat, and play the ring's note."""
        offset = abs(context.clock.elapsed_seconds - seconds)
        if context.mouse.kind == 'press' and offset <= HIT_SECONDS:
            window = next(item for item in JUDGEMENTS if offset <= item[0])
            judge(index, *window[1:], context.clock.elapsed_seconds)
            if context.speaker.is_available:
                context.speaker.play(PITCHES[index % 4], beats=0.25, instrument='bell')


game = xnano.new(width=80, height=24)  # the game keeps to 80 by 24 cells in any window
game.screen.write('Circles', x=2, y=0, bold=True)
status = game.screen.write('', x=43, y=0)
hint = 'click the rings on the beat · q quit'
game.screen.write(hint, x='center', y='bottom', dim=True)
word = game.screen.write('', bold=True, layer=1)

with xnano.open(mouse='motion', title='circles') as terminal:
    terminal.screen.write(game, x='center', y='center')
    cursor = terminal.screen.write(CURSOR, layer=2)  # over the game and its rings

    @terminal.hook(on='frame')
    def play(context: xnano.Context) -> None:
        """Show each ring as its timing ring starts, miss the ones that pass, count down."""
        now = context.clock.elapsed_seconds
        while upcoming and MAP[upcoming[0]][0] - TIMING_SECONDS <= now:
            show(upcoming.pop(0))
        for index in [index for index in rings if now - MAP[index][0] > HIT_SECONDS]:
            judge(index, 'miss', 'red', 0, now)
        word.is_visible = now - judged_at < 0.4
        pointer = context.mouse.pointer  # None until the mouse moves over the window
        cursor.is_visible = pointer is not None
        if pointer is not None:  # the ring's middle cell is on the pointer
            cursor.x, cursor.y = pointer[0] - 3, pointer[1] - 1
        seconds_left = max(0, TIME_LIMIT - int(now))
        status.text = f'score {score:>5}   combo {combo:>3}   {seconds_left:>2} s left'
        if now >= TIME_LIMIT:  # time is up: the result stays until q
            result = f'time · score {score} · accuracy {score / (300 * len(MAP)):.0%}'
            game.screen.write(result, x='center', y='center', bold=True)
            context.hook.remove()

    terminal.run(stop_on='q')
