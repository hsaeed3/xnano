"""
Form: three questions, one on the screen at a time, and then the answers.

Each question is one ``terminal.run()``: ``enter`` ends the run and the terminal stays open,
so the program reads the choice and shows the next question. The up and down arrows move
the choice, and ``q`` quits at any step.
"""

import xnano

QUESTIONS = [
    ('What are you building?', ['a dashboard', 'a game', 'a command line tool']),
    ('How large is the window?', ['the whole window', 'a few rows below the prompt']),
    ('Which extras do you need?', ['none', 'images', 'sound', 'images and sound']),
]
choices: list[str] = []  # the choices of the question on the screen
chosen = 0  # the place in `choices` of the highlighted one

with xnano.open(title='form') as terminal:
    progress = terminal.write('', x=2, y=1, dim=True)
    question = terminal.write('', x=2, y=3, bold=True)
    rows = [terminal.write('', x=2, y=5 + index) for index in range(4)]
    hint = terminal.write('↑ ↓ choose · enter next · q quit', x=2, y='bottom', dim=True)

    def show_choices() -> None:
        """Draw the choices, with a marker and bold text on the highlighted one."""
        for index, row in enumerate(rows):
            is_chosen = index == chosen
            row.text = (
                ('› ' if is_chosen else '  ') + choices[index]
                if index < len(choices)
                else ''
            )
            row.bold(is_chosen)

    @terminal.hook(on='key', keys=['up', 'down'])
    def move_choice(context: xnano.Context) -> None:
        """Move the highlighted choice up or down, around the ends."""
        global chosen
        if choices:
            step = 1 if context.keyboard.key == 'down' else -1
            chosen = (chosen + step) % len(choices)
            show_choices()

    answers = []
    for number, (text, choices) in enumerate(QUESTIONS, 1):
        chosen = 0
        progress.text = f'question {number} of {len(QUESTIONS)}'
        question.text = text
        show_choices()
        # `enter` ends this run and keeps the terminal open: `q` stops the terminal
        terminal.run(stop_on='q', end_on='enter')
        if not terminal.is_running:
            break
        answers.append(choices[chosen])

    if terminal.is_running:
        choices = []
        show_choices()
        progress.text = 'done'
        question.text = 'Your answers'
        for row, (text, _), answer in zip(rows, QUESTIONS, answers, strict=False):
            row.text = f'✓ {text} {answer}'
        hint.text = 'q quit'
        terminal.run(stop_on='q')
