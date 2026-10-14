"""
Hello, world: the smallest xnano program.

Run it with ``uv run python examples/01_hello.py``. A small region opens below your prompt, the
text appears at once, and pressing ``q`` (or ``Ctrl-C``) gives the terminal back.
"""

import xnano

with xnano.iter(width=40, height=3) as terminal:
    terminal.write('Hello, world!', x='center')
    terminal.write('press q to quit', y='bottom')

    terminal.run(quit_on='q')
