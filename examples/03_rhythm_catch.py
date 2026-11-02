"""
Catch: move the basket left and right to catch the notes that fall in time with the music.

The left and right arrows (or ``a`` and ``d``) move the basket, twice as far with ``shift``
held. A note that lands in the basket plays its pitch and adds to the combo, and a note that
falls past breaks it. After thirty seconds the score stays on screen until ``q`` quits.
"""

import xnano

NOTE_COLORS = ['#e8768a', '#946ce6', '#6098ec']  # pink, purple and blue, in turn
NOTE = '..##. ..#.# ..#.. ###.. ###..'  # an eighth note, five by five pixels
BASKET = (  # fourteen by eight amber pixels: a handle, a rim and a woven body
    '....AAAAAA.... ...A......A... ..A........A.. AAAAAAAAAAAAAA '
    '.A.AA.AA.AA.A. .AAAAAAAAAAAA. ..AA.AA.AA.A.. ...AAAAAAAA...'
)
SCALE = ['C4', 'D4', 'E4', 'G4', 'A4', 'C5', 'D5', 'E5', 'G5', 'A5']  # left to right
# one character a beat: the place in SCALE of the note that falls on it, or . for a rest
TUNE = '4545 4.56 5432 3... 4545 4.67 8765 6... 3232 3.21 0123 4... 5.4. 5...'
FIRST_NOTE_SECONDS, BEAT_SECONDS, TIME_LIMIT = 2.0, 0.5, 30
MAP = [  # when each note lands, and its column: each pitch falls down its own 8 columns
    (FIRST_NOTE_SECONDS + beat * BEAT_SECONDS, int(pitch) * 8 + 2)
    for beat, pitch in enumerate(TUNE.replace(' ', ''))
    if pitch != '.'
]
LANDING_Y, FALL_SPEED = 30, 16  # in pixels: where a note meets the rim, and its speed
STEP = 2  # the columns the basket moves for each key press
score = combo = caught = judged = 0  # judged counts the notes that reached the basket
judged_at = -1.0

field = xnano.pixel_art(None, width=80, height=44)  # 80 by 22 cells, two pixels a cell
basket = field.add(xnano.pixel_art(BASKET.split(), 'A=#e4a03e'), x=33, y=LANDING_Y + 2)
basket.layer = 1  # over the notes, which fall in behind its handle
falling = []  # every note of the map, waiting above the field until its turn
for index, (seconds, column) in enumerate(MAP):
    note = xnano.pixel_art(NOTE.split(), f'#={NOTE_COLORS[index % 3]}')
    falling.append(field.add(note, x=column, y=LANDING_Y - seconds * FALL_SPEED))


def judge(context: xnano.Context) -> None:
    """Catch the next note if its stem lands inside the basket, or else break the combo."""
    global score, combo, caught, judged, judged_at
    column = MAP[judged][1]
    if basket.x - 1 <= column + 2 <= basket.x + basket.width:
        caught, combo = caught + 1, combo + 1
        score += 100 + 10 * combo
        falling[judged].remove()
        word.text, word.color.fg = 'great', 'green'
        if context.speaker.is_available:
            context.speaker.play(SCALE[column // 8], instrument='marimba', beats=0.5)
    else:
        combo = 0
        word.text, word.color.fg = 'miss', 'red'
    word.x = int(basket.x) + 5
    judged, judged_at = judged + 1, context.clock.elapsed_seconds


# the game keeps to 80 by 24 cells, in the middle of a larger window
with xnano.open(title='catch') as terminal, xnano.new(width=80, height=24) as game:
    terminal.screen.write(game, x='center', y='center')
    game.screen.write(field, y=1)
    game.screen.write('Catch', x=2, y=0, bold=True)
    status = game.screen.write('', x=43, y=0)
    word = game.screen.write('', y=21, bold=True)
    result = game.screen.write('', x='center', y=10, bold=True)
    hint = '← → or a d move · shift dash · q quit'
    game.screen.write(hint, x='center', y='bottom', dim=True)

    @terminal.hook(on='key')
    def move(context: xnano.Context) -> None:
        """Move the basket a step, or two with shift, keeping it inside the field."""
        direction = context.keyboard.axis(('left', 'a'), ('right', 'd'))
        step = STEP * 2 if 'shift' in context.keyboard.modifiers else STEP
        basket.x = min(max(basket.x + direction * step, 0), field.width - basket.width)

    @terminal.hook(on='frame')
    def fall(context: xnano.Context) -> None:
        """Let the notes fall, judge each one that reaches the basket and end the game."""
        now = context.clock.elapsed_seconds
        for index, note in enumerate(falling):  # each note follows the clock
            note.y = LANDING_Y + (now - MAP[index][0]) * FALL_SPEED
        while judged < len(MAP) and MAP[judged][0] <= now:
            judge(context)
        word.is_visible = now - judged_at < 0.4
        seconds_left = max(0, TIME_LIMIT - int(now))
        status.text = f'score {score:>5}   combo {combo:>3}   {seconds_left:>2} s left'
        if now >= TIME_LIMIT:
            result.text = f'time · score {score} · caught {caught / len(MAP):.0%}'
            move.remove()
            context.hook.remove()

    terminal.run(stop_on='q')
