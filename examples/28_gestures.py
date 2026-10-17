"""
Gestures: drag, scroll and conditions on hooks.

A hook on ``'drag'`` or ``'scroll'`` hears the pointer only inside its own placement, and a
press inside it keeps the drag until the button is released. The drag hook below is a
generator: ``context = yield`` waits for the next movement, so the whole gesture is one
function. Hooks write what they learned with ``context.root.state.push(path, value)``, and the
readout hook on ``'state'`` runs again whenever a path it read changes. A ``when`` condition
may be a string (``"keyboard.key == 'r'"``), an expression (``Keyboard.key == 'z'``) or a
function. Drag or scroll in the box, press ``z`` to push a scroll step with the keyboard,
``r`` to reset, and ``q`` to quit.
"""

import xnano
from xnano.context import Context
from xnano.expressions import Keyboard
from xnano.types import HookGenerator

with xnano.open(width=56, height=10, mouse=True, scroll=True) as terminal:
    terminal.write('drag or scroll in the box   z push   r reset   q quit')
    lines = ('a box that hears gestures', '', '', '')
    panel = terminal.write(
        '\n'.join(line.ljust(28) for line in lines), y=2, border='rounded'
    )
    readout = terminal.write('zoom   0', y=8)
    dragging = terminal.write('drag none', y=9)

    @panel.hook(on='drag')
    def drag(context: Context) -> HookGenerator:
        state = context.root.state
        while context.mouse.is_down:
            pointer = context.mouse.position
            if pointer is not None:
                point = panel.local(pointer)
                state.push('drag', f'{point.x},{point.y}')
            context = yield
        state.push('drag', 'released')

    @panel.hook(on='scroll')
    def scroll(context: Context) -> None:
        state = context.root.state
        zoom = state.get('zoom', 0)
        if isinstance(zoom, int):
            state.push('zoom', zoom + context.scroll.y)

    @terminal.hook(on='state')
    def show(context: Context) -> None:
        state = context.root.state
        readout.text = f'zoom {state.get("zoom", 0):>3}'
        dragging.text = f'drag {state.get("drag", "none")}'

    @terminal.hook(on='key', when=Keyboard.key == 'z')
    def push_a_step(context: Context) -> None:
        context.mouse.push((panel.x + 3, panel.y + 2))
        context.scroll.push((0, 1))

    @terminal.hook(on='key', when="keyboard.key == 'r'")
    def reset(context: Context) -> None:
        context.root.state.push('zoom', 0)
        context.root.state.push('drag', 'none')

    terminal.run(quit_on='q')
