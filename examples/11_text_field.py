"""
Ask a question, and wait for the answer.

``terminal.prompt`` works like ``input()``: the prompt appears with the terminal's cursor, your
program waits while the person types, and the answer comes back as a string. ``Enter``
submits and ``Backspace`` deletes. ``terminal.wait_for_key`` waits the same way for one key.
"""

import xnano
from xnano.styles import Style

with xnano.iter(width=50, height=5) as terminal:
    name = terminal.prompt('Your name: ')
    terminal.write(f'Hello, {name}!', y=2, style=Style('green', bold=True))
    terminal.write('press escape to leave', y=4, style=Style(dim=True))
    terminal.wait_for_key('escape')
