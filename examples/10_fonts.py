"""
Fonts: a scoreboard with its title and score written in pixel fonts, and a picture of it.

``space`` adds ten points to the score, which is written in the built-in ``'large'`` pixel
font. ``s`` saves the screen as ``scoreboard.png`` in the current directory, and ``q`` quits.
Text in a font is still text: it is placed, colored and changed like any other text.
"""

import pathlib

import xnano

score = 0

with xnano.open(title='fonts') as terminal:
    terminal.write('SCORE', font='small', foreground='yellow')
    points = terminal.write('0', font='large', foreground='cyan', y=5)
    status = terminal.write('', y=13, dim=True)
    terminal.write('space score · s save image · q quit', y='bottom', dim=True)

    @terminal.hook(on='key', keys='space')
    def add_points(context: xnano.Context) -> None:
        """Add ten points, and write the new score in the large font."""
        global score
        score += 10
        points.text = str(score)

    @terminal.hook(on='key', keys='s')
    def save_image(context: xnano.Context) -> None:
        """Save the screen as a PNG image, each cell drawn with the built-in large font."""
        path = pathlib.Path('scoreboard.png')
        path.write_bytes(terminal.render(format='png'))
        status.text = f'saved {path}'

    terminal.run(stop_on='q')
