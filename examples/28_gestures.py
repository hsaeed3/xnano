"""
Gestures: drag, scroll and conditions on hooks.

A hook on ``'drag'`` or ``'scroll'`` hears the pointer only inside its own placement, and a
press inside it keeps the drag until the button is released. The canvas is built with
``xnano.new()`` and put on the screen with ``open()`` without ``mouse=`` or ``scroll=``,
because a hook that listens to the pointer turns the mouse and the wheel on. The expressions
``Mouse.button == 'left'`` and ``Scroll.y != 0`` limit the drag to the left button and the
scroll hook to the vertical wheel. The drag hook below is a generator: ``context = yield``
waits for the next movement, so the whole gesture is one function. Hooks write what they
learned with ``context.root.state.push(path, value)``, and the readout hook on ``'state'``
runs again whenever a path it read changes. ``context.input.is_down('mouse_left')`` asks
whether the left button is held, and ``context.buffer.state`` is the state of the box itself,
where the drag hook counts its movements. A ``when`` condition may be a string
(``"keyboard.key == 'r'"``), an expression (``Keyboard.key == 'z'``) or a function. Drag or
scroll in the box, press ``z`` to push a scroll step with the keyboard, ``r`` to reset, and
``q`` to quit.
"""

import xnano
from xnano.context import Context
from xnano.expressions import Keyboard, Mouse, Scroll
from xnano.types import HookGenerator

with xnano.new(width=56, height=10) as canvas:
    canvas.write('drag or scroll in the box   z push   r reset   q quit')
    lines = ('a box that hears gestures', '', '', '')
    panel = canvas.write(
        '\n'.join(line.ljust(28) for line in lines), y=2, border='rounded'
    )
    readout = canvas.write('zoom   0', y=8)
    dragging = canvas.write('drag none', y=9)

    @panel.hook(on='drag', when=Mouse.button == 'left')
    def drag(context: Context) -> HookGenerator:
        state = context.root.state
        while context.mouse.is_down:
            pointer = context.mouse.position
            if pointer is not None:
                point = panel.local(pointer)
                state.push('drag', f'{point.x},{point.y}')
                state.push('held', context.input.is_down('mouse_left'))
                moves = context.buffer.state.get('moves', 0)
                if isinstance(moves, int):
                    context.buffer.state.push('moves', moves + 1)
            context = yield
        state.push('drag', 'released')
        state.push('held', False)

    @panel.hook(on='scroll', when=Scroll.y != 0)
    def scroll(context: Context) -> None:
        state = context.root.state
        zoom = state.get('zoom', 0)
        if isinstance(zoom, int):
            state.push('zoom', zoom + context.scroll.y)

    @canvas.hook(on='state')
    def show(context: Context) -> None:
        state = context.root.state
        readout.text = f'zoom {state.get("zoom", 0):>3}'
        held = 'held' if state.get('held', False) else 'free'
        moves = panel.state.get('moves', 0)
        dragging.text = f'drag {state.get("drag", "none")}   left {held}   moves {moves}'

    @canvas.hook(on='key', when=Keyboard.key == 'z')
    def push_a_step(context: Context) -> None:
        context.mouse.push((panel.x + 3, panel.y + 2))
        context.scroll.push((0, 1))

    @canvas.hook(on='key', when="keyboard.key == 'r'")
    def reset(context: Context) -> None:
        context.root.state.push('zoom', 0)
        context.root.state.push('drag', 'none')
        panel.state.push('moves', 0)

    terminal = canvas.open()
    terminal.run(quit_on='q')
