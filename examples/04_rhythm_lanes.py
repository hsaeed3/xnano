"""
Lanes: notes fall down four lanes, and each is hit with its lane's key at the line.

``d f j k`` play the lanes. A press near a note scores great, good or fair, and a note
that passes the line is a miss. After 30 seconds the result stays until ``q`` quits.
"""

import xnano

KEYS = 'dfjk'
COLORS = ('#e8768a', '#946ce6', '#6098ec', '#e4a03e')  # pink, purple, blue and amber
PITCHES = ('C4', 'E4', 'G4', 'C5')  # the note each lane plays when it is hit
# the map: a lane's key, or '.' for a rest, on each half beat, with a space between bars
PATTERN = 'd.f.j.k. j.f.d... d.j.f.k. dfjk.kjf k.j.f.d. f.j.dk.. djfkdjfk'
STEP_SECONDS, START_SECONDS, TIME_LIMIT = 0.25, 1.5, 30
MAP = [  # each note's time and lane: the pattern twice, about 28 seconds
    (START_SECONDS + index * STEP_SECONDS, KEYS.index(key))
    for index, key in enumerate(PATTERN.replace(' ', '') * 2)
    if key != '.'
]
JUDGEMENTS = (  # the seconds a press may be from its note, its word, color and points
    (0.08, 'great', 'green', 300),
    (0.16, 'good', 'yellow', 150),
    (0.25, 'fair', 'reset', 50),
)
MISS = (0.25, 'miss', 'red', 0)  # a note this many seconds past the line is missed
LANE_WIDTH, LINE_ROW, SPEED = 8, 17, 16  # cells, the judgement line's row, rows a second

game = xnano.new(width=80, height=24)  # the game keeps to 80 by 24 cells in any window
game.screen.write('Lanes', x=2, y=0, bold=True)
status = game.screen.write('', x=43, y=0)
field = xnano.new(width=4 * LANE_WIDTH + 1, height=LINE_ROW + 2)  # notes end at its edges
field.screen.write('\n'.join(['│       ' * 4 + '│'] * LINE_ROW), x=0, y=0, dim=True)
field.screen.write('┷' + '━━━━━━━┷' * 4, x=0, y=LINE_ROW)  # the judgement line
notes = [{} for key in KEYS]  # each lane's notes not judged yet, by their time
for seconds, lane in MAP:  # a note's y is an expression, so it falls with the clock
    column, row = 2 + lane * LANE_WIDTH, LINE_ROW - (seconds - field.clock) * SPEED
    notes[lane][seconds] = field.screen.write(
        '▄' * 5, x=column, y=row, foreground=COLORS[lane]
    )
pads = []  # the key under each lane, lit while it is pressed and drawn over passing notes
for lane, key in enumerate(KEYS):
    column = 1 + lane * LANE_WIDTH
    pads.append(field.screen.write(f'   {key}   ', x=column, y=LINE_ROW + 1, bold=True))
    pads[lane].color.fg = COLORS[lane]
game.screen.write(field, x='center', y=2)
word = game.screen.write('', x='center', y=21, bold=True)
hint = 'd f j k hit the notes on the line · q quit'
game.screen.write(hint, x='center', y='bottom', dim=True)
score = combo = 0
judged_at, pressed_at = -9.0, [-9.0] * 4


def next_note(lane: int) -> float:
    """The time of the lane's next note, or infinity when it has none left."""
    return min(notes[lane], default=float('inf'))


def judge(lane: int, judgement: tuple[float, str, str, int], now: float) -> None:
    """Take the lane's next note off the field, add its points and show its word."""
    global score, combo, judged_at
    _, text, color, points = judgement
    notes[lane].pop(next_note(lane)).remove()
    score, combo = score + points, combo + 1 if points else 0
    word.text, word.color.fg, judged_at = text, color, now


with xnano.open(title='lanes') as terminal:
    terminal.screen.write(game, x='center', y='center')

    @terminal.hook(on='key', keys=list(KEYS))
    def hit(context: xnano.Context) -> None:
        """Light the lane, and judge its next note when the press is near enough to it."""
        now, lane = context.clock.elapsed_seconds, KEYS.index(str(context.keyboard.key))
        pressed_at[lane] = now
        offset = abs(next_note(lane) - now)
        tier = next((tier for tier in JUDGEMENTS if offset <= tier[0]), None)
        if tier is not None:
            judge(lane, tier, now)
            if context.speaker.is_available:
                context.speaker.play(PITCHES[lane], instrument='electric_piano')

    @terminal.hook(on='frame')
    def update(context: xnano.Context) -> None:
        """Miss the notes past the line, light the pads and the word, and count down."""
        now = context.clock.elapsed_seconds
        for lane, pad in enumerate(pads):
            if next_note(lane) < now - MISS[0]:
                judge(lane, MISS, now)
            pad.is_reversed = now - pressed_at[lane] < 0.15
        word.is_visible = now - judged_at < 0.5
        seconds_left = max(0, TIME_LIMIT - int(now))
        status.text = f'score {score:>5}   combo {combo:>3}   {seconds_left:>2} s left'
        if seconds_left == 0:  # time is up: the keys stop and the result stays until q
            word.text = f'time · score {score} · accuracy {score / (300 * len(MAP)):.0%}'
            word.color.fg, word.is_visible = 'reset', True
            hit.remove()
            context.hook.remove()

    terminal.run(stop_on='q')
