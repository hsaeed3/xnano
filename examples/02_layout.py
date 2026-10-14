"""
Positions and sizes are formulas.

Every ``x``, ``y``, ``width`` and ``height`` is a number of cells, a percentage of the
parent, or an expression that is evaluated again on every frame. Resize the window and the
layout follows without a single line of code to handle it. Press ``q`` to quit.
"""

import xnano
from xnano.expressions import ParentHeight, ParentWidth, Width
from xnano.widgets import Block

with xnano.iter() as terminal:
    terminal.write('top left')
    terminal.write('top right', x=ParentWidth - Width)
    terminal.write('bottom left', y=ParentHeight - 1)
    terminal.write('centered', x=(ParentWidth - Width) // 2, y=ParentHeight // 2 + 4)

    # A Block draws its border at whatever size it has, so it follows the window.
    terminal.write(
        Block('half as wide as the window', border_type='rounded'),
        x='25%',
        y=3,
        width='50%',
        height=3,
    )

    terminal.write('press q to quit', x=ParentWidth - 15, y=ParentHeight - 1)

    terminal.run(quit_on='q')
