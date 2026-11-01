---
title: Hooks & Input
icon: lucide/keyboard
---

# Hooks & Input

A **hook** is a function xnano calls when something happens. You attach one with
the `hook` decorator, say what it listens for with `on=`, and xnano calls it
with a [`Context`][xnano.hooks.Context]: the event that happened, and the
canvas's devices.

This guide covers the keyboard and the mouse. Hooks that run on time, such as
`on='tick'`, are in [Time & Effects](time.md).

## Keys

`on='key'` runs a hook on every key press, and again while a key repeats.
`keys=` narrows it to one key, or a list of keys.

<!-- @code-block name="learn-input-keys" type="gif" height=3
wait 0.6
press space
wait 0.3
press space
wait 0.3
press space
wait 1.0
-->
```python
import xnano

with xnano.open(height=3) as terminal:
    count = terminal.screen.write('pressed 0 times')
    terminal.screen.write('space count · q quit', y='bottom', dim=True)
    presses = 0

    @terminal.hook(on='key', keys='space')
    def add_one(context: xnano.Context):
        global presses
        presses += 1
        count.text = f'pressed {presses} times'

    terminal.run(stop_on='q')
```

Leave out `keys=` to hear every key. `context.keyboard.key` names the key that
was pressed: a character such as `'a'`, or a name such as `'enter'`, `'escape'`,
`'backspace'`, `'tab'`, `'up'` or `'f1'`.

<!-- @code-block name="learn-input-any-key" type="gif" height=2
wait 0.6
type xnano
wait 0.4
press up
wait 0.6
-->
```python
import xnano

with xnano.open(height=2) as terminal:
    last = terminal.screen.write('press any key')
    terminal.screen.write('q quit', y='bottom', dim=True)

    @terminal.hook(on='key')
    def show_key(context: xnano.Context):
        last.text = f'you pressed {context.keyboard.key}'

    terminal.run(stop_on='q')
```

## Shortcuts

A key with modifiers is written with `+`: `'ctrl+s'`, `'alt+enter'`,
`'shift+tab'`. Give `keys=` a list to run one hook for several bindings.

```python
import xnano

with xnano.open(height=2) as terminal:
    status = terminal.screen.write('ctrl+s save · escape cancel · q quit')

    @terminal.hook(on='key', keys='ctrl+s')
    def save(context: xnano.Context):
        status.text = 'saved'

    @terminal.hook(on='key', keys=['escape', 'ctrl+z'])
    def cancel(context: xnano.Context):
        status.text = 'cancelled'

    terminal.run(stop_on='q')
```

## Moving with the arrow keys

`context.keyboard.direction()` reads the arrow keys, and `w`, `a`, `s` and `d`,
as a step along each axis: `(-1, 0)` for left, `(0, 1)` for down. `move()` takes
that step. `edges='stop'` keeps everything inside the canvas, however far it's
pushed.

<!-- @code-block name="learn-input-arrows" type="gif" height=6
wait 0.6
press right right right right right right right right
wait 0.3
press down down
wait 0.3
press left left left
wait 0.8
-->
```python
import xnano

with xnano.open(height=6, edges='stop') as terminal:
    player = terminal.screen.write('@', x='center', y='center', foreground='yellow')
    terminal.screen.write('arrows or wasd move · q quit', y='bottom', dim=True)

    @terminal.hook(on='key')
    def move(context: xnano.Context):
        step_x, step_y = context.keyboard.direction()
        player.move(step_x, step_y)

    terminal.run(stop_on='q')
```

## The mouse

Terminals report the mouse only when asked, so open the terminal with
`mouse=True`. A hook on a **placement** hears the pointer only while it's over
that placement, which makes any placement a button.

`context.mouse` describes the event: its `kind` (`'press'`, `'release'`,
`'drag'`, `'move'` or `'scroll'`), the `button`, and the `position` in cells.

<!-- @code-block name="learn-input-mouse" type="gif" height=4
wait 0.6
click 4 1
wait 0.5
click 4 1
wait 0.5
click 4 1
wait 0.8
-->
```python
import xnano

with xnano.open(height=4, mouse=True) as terminal:
    button = terminal.screen.write(' off ', border='rounded')
    terminal.screen.write('click the switch · q quit', y='bottom', dim=True)
    is_on = False

    @button.hook(on='mouse')
    def toggle(context: xnano.Context):
        global is_on
        if context.mouse.kind == 'press':
            is_on = not is_on
            button.text = ' on ' if is_on else ' off '
            button.color.fg = 'green' if is_on else 'reset'

    terminal.run(stop_on='q')
```

## Dragging

A drag hook can be a **generator**: each bare `yield` waits for the pointer's
next movement and hands back a fresh context. The loop runs for as long as the
button is held.

A range such as `x=(0, 29)` limits how far a placement can travel, so the thumb
of this slider stays on its track.

<!-- @code-block name="learn-input-drag" type="gif" height=3
wait 0.6
drag 0 1 20 1
wait 0.6
drag 20 1 8 1
wait 1.0
-->
```python
import xnano

with xnano.open(height=3, mouse=True) as terminal:
    terminal.screen.write('─' * 30, y=1, dim=True)
    label = terminal.screen.write('drag the ●', y=2)
    thumb = terminal.screen.write('●', x=(0, 29), y=1)

    @thumb.hook(on='drag')
    def slide(context: xnano.Context):
        while context.mouse.is_down:
            thumb.x = context.parent.local(context.mouse.position).x  # >> [local]
            context = yield  # >> [yield]
        label.text = f'dropped at {thumb.x}'

    terminal.run(stop_on='q')
```

<comments>
<tag name="local">
`local()` turns a position on the screen into a position inside the thumb's
parent, so the slider works wherever it's drawn.
</tag>

<tag name="yield">
Waits for the next movement, then carries on with its context.
</tag>
</comments>

The wheel works the same way: open with `scroll=True`, use `on='scroll'`, and
read the steps from `context.mouse.scroll`.

## Pasting

`on='paste'` runs when the user pastes text, all at once instead of key by key.
The text is in `context.keyboard.pasted`.

```python
import xnano

with xnano.open(height=2) as terminal:
    received = terminal.screen.write('paste something')

    @terminal.hook(on='paste')
    def show_paste(context: xnano.Context):
        received.text = f'{len(context.keyboard.pasted)} characters pasted'

    terminal.run(stop_on='q')
```

## Stopping

`terminal.run()` keeps the program running until one of its `stop_on` keys is
pressed: `'ctrl+c'` when you give none, and any key or list of keys you choose.
A hook can end the program itself with `context.canvas.stop()`.

A hook keeps running until you remove it. The decorator returns the hook, so
either keep that and call `remove()` on it, or call `context.hook.remove()` from
inside.

```python
import xnano

with xnano.open(height=2) as terminal:
    terminal.screen.write('press enter three times')
    presses = 0

    @terminal.hook(on='key', keys='enter')
    def count(context: xnano.Context):
        global presses
        presses += 1
        if presses == 3:
            context.canvas.stop()

    terminal.run()
```

Every kind of hook and its options are listed in the [`hook`][xnano.hook]
reference.
