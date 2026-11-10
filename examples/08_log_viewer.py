"""
Log viewer: lines arrive a few times a second, colored by their level.

The view follows the newest line. The up and down arrows scroll back and forward, and
``f`` follows the newest line again. ``e`` shows only warnings and errors, ``space``
pauses the lines, and ``q`` quits.
"""

import xnano

VISIBLE_ROWS = 20
LEVELS = {  # the color of each level: the word in the line carries the meaning too
    'info': 'reset',  # the terminal's own color
    'warning': 'yellow',
    'error': 'red',
}
MESSAGES = {
    'info': ['request served', 'cache refreshed', 'worker started', 'session opened'],
    'warning': ['slow response', 'retrying the upload', 'disk is 85% full'],
    'error': ['connection refused', 'payment failed', 'worker stopped'],
}
lines: list[tuple[str, str]] = []  # every line so far, as its level and its text
offset = 0  # how many lines the view is scrolled back from the newest one
is_filtered = False


def visible_lines() -> list[tuple[str, str]]:
    """The lines the view shows: all of them, or only the warnings and errors."""
    if is_filtered:
        return [line for line in lines if line[0] != 'info']
    return lines


with xnano.open(title='log viewer') as terminal:
    terminal.write('logs', bold=True)
    status = terminal.write('', x='right', y=0, dim=True)
    rows = [
        terminal.write('', y=2 + index, width='100%') for index in range(VISIBLE_ROWS)
    ]
    terminal.write(
        '↑ ↓ scroll · f follow · e errors · space pause · q quit', y='bottom', dim=True
    )

    def show() -> None:
        """Draw the rows that end ``offset`` lines before the newest line."""
        shown = visible_lines()
        last = len(shown) - offset
        window = shown[max(0, last - VISIBLE_ROWS) : last]
        for index, row in enumerate(rows):
            level, text = window[index] if index < len(window) else ('info', '')
            row.text = text
            row.color.fg = LEVELS[level]
        view = 'following' if offset == 0 else f'{offset} lines back'
        status.text = f'{len(shown)} lines · {view}'

    @terminal.hook(on='tick', every=0.25)
    def add_line(context: xnano.Context) -> None:
        """Add one line, four times a second."""
        global offset
        # every eleventh line is an error and every fourth a warning: the rest inform
        number = len(lines) + 1
        level = 'error' if number % 11 == 0 else 'warning' if number % 4 == 0 else 'info'
        message = MESSAGES[level][number % len(MESSAGES[level])]
        text = f'{context.clock.elapsed_seconds:7.2f}  {level:<7}  {message}'
        lines.append((level, text))
        # a view that is scrolled back keeps showing the same lines
        if offset and (level != 'info' or not is_filtered):
            offset += 1
        show()

    @terminal.hook(on='key', keys=['up', 'down', 'f'])
    def scroll(context: xnano.Context) -> None:
        """Scroll one line back or forward, or follow the newest line again."""
        global offset
        furthest = max(0, len(visible_lines()) - VISIBLE_ROWS)
        step = {'up': 1, 'down': -1}.get(context.keyboard.key or '', -offset)
        offset = max(0, min(offset + step, furthest))
        show()

    @terminal.hook(on='key', keys='e')
    def filter_levels(context: xnano.Context) -> None:
        """Show only warnings and errors, or every line again."""
        global is_filtered, offset
        is_filtered, offset = not is_filtered, 0
        show()

    @terminal.hook(on='key', keys='space')
    def pause(context: xnano.Context) -> None:
        """Pause the clock, and the lines with it, or resume it."""
        if context.clock.is_paused:
            context.clock.resume()
        else:
            context.clock.pause()

    show()
    terminal.run(stop_on='q')
