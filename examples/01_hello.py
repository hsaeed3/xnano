"""
Hello, world: the smallest xnano program.

Run it with ``python examples/01_hello.py``. A small region opens below your prompt, the
text appears at once, and pressing ``q`` (or ``Ctrl-C``) gives the terminal back.
"""

import xnano

with xnano.open(width=40, height=3) as terminal:
    terminal.add('Hello, world!', x='center')
    terminal.add('press q to quit', y='bottom')

    terminal.run(quit_on='q')
