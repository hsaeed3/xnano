"""
Drums: hit the amber center notes with ``d`` or ``k`` and the purple rim notes with ``f``
or ``j`` as they scroll into the frame. A note that slips past breaks the combo.
"""

import xnano

COLORS = {'center': '#e4a03e', 'rim': '#946ce6'}  # amber and purple
ART = {  # eight by eight pixels: a solid disc for the center, a ring for the rim
    'center': '..XXXX.. .XXXXXX. XXXXXXXX XXXXXXXX XXXXXXXX XXXXXXXX .XXXXXX. ..XXXX..',
    'rim': '..XXXX.. .XXXXXX. XXX..XXX XX....XX XX....XX XXX..XXX .XXXXXX. ..XXXX..',
}
CENTER_KEYS, RIM_KEYS = ('d', 'k'), ('f', 'j')  # either hand plays either kind
GROOVE = 'c.r.c.r. c.rcc.r. c.r.c.r. ccr.ccr. '  # c a center hit, r a rim hit, . a rest
SHEET = 'c...r... c...r... c.r.c.r. c.c.r... ' + GROOVE * 2 + 'c.r.c.r. ccr.c...'
MAP = [  # when each note reaches the frame, a letter being an eighth note (0.25 s)
    (2.0 + step * 0.25, 'center' if letter == 'c' else 'rim')
    for step, letter in enumerate(SHEET.replace(' ', ''))
    if letter != '.'
]
WINDOW = 0.25  # a key press this many seconds from a note's time hits it
JUDGEMENTS = [  # how far a hit is from its note, the word, its color and the points
    (0.08, 'great', 'green', 300),
    (0.16, 'good', 'yellow', 150),
    (WINDOW, 'fair', 'reset', 50),
    (float('inf'), 'miss', 'red', 0),  # the note slipped past
]
FRAME_X, RAIL_Y, SPEED = 2, 9, 40  # the frame's corner, and how many cells a second
TIME_LIMIT = 30
score, combo, judged_at = 0, 0, -1.0


def judge(error: float, now: float) -> None:
    """Score a note hit ``error`` seconds from its time, and show the word for it."""
    global score, combo, judged_at
    word, color, points = next(tier[1:] for tier in JUDGEMENTS if error <= tier[0])
    score += points
    combo = combo + 1 if points else 0
    judgement.text = f'{word:^10}'
    judgement.color.fg = frame.color.fg = color  # the frame lights up with the word
    judged_at = now


with xnano.open(title='drums') as terminal, xnano.new(width=80, height=24) as game:
    terminal.screen.write(game, x='center', y='center')  # the game stays 80 by 24 cells
    game.screen.write('Drums', x=2, y=0, bold=True)
    status = game.screen.write('', x=43, y=0)
    game.screen.write('d k center ●  ·  f j rim ○  ·  q quit', x='center', y=23, dim=True)
    for row in (RAIL_Y, RAIL_Y + 5):  # the rails above and below the notes
        game.screen.write('─' * 80, x=0, y=row, dim=True)
    frame = game.screen.write(xnano.box(10, 6, border='rounded'), x=FRAME_X, y=RAIL_Y)
    judgement = game.screen.write('', x=FRAME_X, y=RAIL_Y - 2, bold=True)
    pending = []  # the notes still to judge, in time order: time, kind and placement
    for seconds, kind in MAP:  # written last, so they pass over the rails and the frame
        art = xnano.pixel_art(ART[kind].split(), {'X': COLORS[kind]})
        column = FRAME_X + 1 + (seconds - terminal.clock) * SPEED  # in the frame on time
        pending.append((seconds, kind, game.screen.write(art, x=column, y=RAIL_Y + 1)))

    @terminal.hook(on='key', keys=[*CENTER_KEYS, *RIM_KEYS])
    def hit(context: xnano.Context) -> None:
        """Play the drum, and judge the next note of its kind in reach."""
        now = context.clock.elapsed_seconds
        kind = 'center' if context.keyboard.key in CENTER_KEYS else 'rim'
        if context.speaker.is_available:
            instrument = 'tom' if kind == 'center' else 'clap'
            context.speaker.play(xnano.Note('C3', beats=0.25, instrument=instrument))
        for seconds, note_kind, placement in pending:
            if note_kind == kind and abs(now - seconds) <= WINDOW:
                judge(abs(now - seconds), now)
                pending.remove((seconds, note_kind, placement))
                placement.remove()
                break

    @terminal.hook(on='frame')
    def follow(context: xnano.Context) -> None:
        """Judge the notes that slipped past, update the status and end the game."""
        now = context.clock.elapsed_seconds
        while pending and now - pending[0][0] > WINDOW:  # the first note slipped past
            seconds, kind, placement = pending.pop(0)
            placement.remove()
            judge(float('inf'), now)
        judgement.is_visible = now - judged_at < 0.4
        if not judgement.is_visible:
            frame.color.fg = 'reset'
        seconds_left = max(0, TIME_LIMIT - int(now))
        status.text = f'score {score:>5}   combo {combo:>3}   {seconds_left:>2} s left'
        if now >= TIME_LIMIT:
            result = f'time · score {score} · accuracy {score / (300 * len(MAP)):.0%}'
            game.screen.write(result, x='center', y=RAIL_Y + 8, bold=True)
            context.hook.remove()

    terminal.run(stop_on='q')
