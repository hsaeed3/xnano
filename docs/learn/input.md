---
title: Hooks & Input
icon: lucide/keyboard
---

# Hooks & Input

A **hook** is a function that xnano calls when something happens. Attach a hook
with the `hook` decorator. Its `on=` argument sets the kind of event that runs
it. xnano calls the hook with a [`Context`][xnano.hooks.Context], which holds
the event and the devices of the canvas.

This page is about the keyboard and the mouse. For hooks that run on time, such
as `on='tick'`, see [Time & Effects](time.md).

## Keys

`on='key'` runs a hook each time the user presses a key. While the user holds a
key, the terminal repeats it, and the hook runs again for each repeat. `keys=`
limits the hook to one key or to a list of keys.

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
    count = terminal.write('pressed 0 times')  # >> [placement]
    terminal.write('space count · q quit', y='bottom', dim=True)
    presses = 0

    @terminal.hook(on='key', keys='space')
    def add_one(context: xnano.Context):
        global presses  # >> [global]
        presses += 1
        count.text = f'pressed {presses} times'  # >> [placement]

    terminal.run(stop_on='q')
```

<comments>
<tag name="placement" color="blue">
`terminal.write()` is the same as `terminal.screen.write()`. It returns a
**placement**. Set its `text` to change what the screen shows.
</tag>

<tag name="global">
The hook changes `presses`, a variable outside the function, so the hook
declares it `global`.
</tag>
</comments>

<!-- @code-block-asset name="learn-input-keys" -->

![learn-input-keys](../assets/examples/learn-input-keys-light.gif#only-light)
![learn-input-keys](../assets/examples/learn-input-keys-dark.gif#only-dark)

<!-- /@code-block-asset -->

Leave out `keys=` to run the hook for every key. `context.keyboard.key` is the
name of the key that the user pressed. A key name is a character such as `'a'`,
or a word such as `'enter'`, `'escape'`, `'backspace'`, `'tab'`, `'up'` or
`'f1'`.

<!-- @code-block name="learn-input-any-key" type="gif" height=3
wait 0.6
type xnano
wait 0.4
press up
wait 0.6
-->
```python
import xnano

with xnano.open(height=2) as terminal:
    last = terminal.write('press any key')
    terminal.write('q quit', y='bottom', dim=True)

    @terminal.hook(on='key')
    def show_key(context: xnano.Context):
        last.text = f'you pressed {context.keyboard.key}'

    terminal.run(stop_on='q')
```

<!-- @code-block-asset name="learn-input-any-key" -->

![learn-input-any-key](../assets/examples/learn-input-any-key-light.gif#only-light)
![learn-input-any-key](../assets/examples/learn-input-any-key-dark.gif#only-dark)

<!-- /@code-block-asset -->

If `keys=` has a name that is not a key, `hook` raises a `ValueError`. The
message suggests the closest key names, for example `'space'` for `'spcae'`.

## Shortcuts

A key with modifiers is one string, with `+` between the parts, such as
`'ctrl+s'`, `'alt+enter'` or `'shift+tab'`. To run one hook for several keys,
give `keys=` a list.

```python
import xnano

with xnano.open(height=2) as terminal:
    status = terminal.write('ctrl+s save · escape cancel · q quit')

    @terminal.hook(on='key', keys='ctrl+s')
    def save(context: xnano.Context):
        status.text = 'saved'

    @terminal.hook(on='key', keys=['escape', 'ctrl+z'])
    def cancel(context: xnano.Context):
        status.text = 'cancelled'

    terminal.run(stop_on='q')
```

Some terminals send a key with `alt` as `escape` followed by the key. Then
xnano cannot always know which keys the user pressed. If your program uses
`escape` or `alt` keys, give `keyboard='disambiguated'` to `xnano.open()`.
Terminals that support this setting then send each key in its own form.

## Move with the arrow keys

`context.keyboard.direction()` reads the arrow keys and the `w`, `a`, `s` and
`d` keys. It returns one step on each axis, as `(step_x, step_y)`. Each step is
`-1`, `0` or `1`, and `y` increases downward. For example, left gives `(-1, 0)`
and down gives `(0, 1)`. Any other key gives `(0, 0)`.

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

with xnano.open(height=6, edges='stop') as terminal:  # >> [edges]
    player = terminal.write('@', x='center', y='center', foreground='yellow')
    terminal.write('arrows or wasd move · q quit', y='bottom', dim=True)

    @terminal.hook(on='key')
    def move(context: xnano.Context):
        step_x, step_y = context.keyboard.direction()
        player.move(step_x, step_y)  # >> [move]

    terminal.run(stop_on='q')
```

<comments>
<tag name="edges" color="amber">
`edges='stop'` keeps each placement inside the canvas when it moves. Without
it, a placement can move past an edge, and xnano does not draw the part outside.
</tag>

<tag name="move" color="blue">
Moves the placement by a number of columns and rows.
</tag>
</comments>

<!-- @code-block-asset name="learn-input-arrows" -->

![learn-input-arrows](../assets/examples/learn-input-arrows-light.gif#only-light)
![learn-input-arrows](../assets/examples/learn-input-arrows-dark.gif#only-dark)

<!-- /@code-block-asset -->

To use other keys, give them to `direction()`, for example
`direction(left='h', right='l', up='k', down='j')`. These keys replace the arrow
keys and `wasd`.

## The mouse

A terminal reports the mouse only when a program asks for it. Give `mouse=True`
to `xnano.open()` to receive presses, releases and drags. Without it, mouse
hooks do not run. To also receive each movement of the pointer, give
`mouse='motion'`.

A hook on a **placement** receives only the pointer events inside that
placement. With such a hook, any placement can be a button. `context.mouse`
describes the event:

- `kind` is `'press'`, `'release'`, `'drag'` or `'move'`.
- `button` is `'left'`, `'right'` or `'middle'`.
- `position` is the cell under the pointer, with `x` and `y`.

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
    button = terminal.write(' off ', border='rounded')
    terminal.write('click the switch · q quit', y='bottom', dim=True)
    is_on = False

    @button.hook(on='mouse')
    def toggle(context: xnano.Context):
        global is_on
        if context.mouse.kind == 'press':  # >> [press]
            is_on = not is_on
            button.text = ' on ' if is_on else ' off '
            button.color.fg = 'green' if is_on else 'reset'  # >> [reset]

    terminal.run(stop_on='q')
```

<comments>
<tag name="press" color="pink">
A click sends a press and then a release. The hook acts only on the press, so
one click changes the switch one time.
</tag>

<tag name="reset">
`'reset'` gives the text the default color of the terminal again.
</tag>
</comments>

<!-- @code-block-asset name="learn-input-mouse" -->

![learn-input-mouse](../assets/examples/learn-input-mouse-light.gif#only-light)
![learn-input-mouse](../assets/examples/learn-input-mouse-dark.gif#only-dark)

<!-- /@code-block-asset -->

## Drag with the mouse

A drag hook can be a **generator**. Each bare `yield` waits for the next
movement of the pointer, then gives the hook a new context. Write it as
`context = yield`. The loop runs while the user holds the button. After a press
inside the placement, the hook receives each movement until the user releases
the button, also outside the placement.

A range such as `x=(0, 29)` keeps a placement between two columns. Here, it
keeps the thumb of the slider on its track, from column 0 to column 29.

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
    terminal.write('─' * 30, y=1, dim=True)
    label = terminal.write('drag the ●', y=2)
    thumb = terminal.write('●', x=(0, 29), y=1)

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
`local()` changes a position on the screen into a position inside the parent of
the thumb. The slider then works at any position on the screen.
</tag>

<tag name="yield">
Waits for the next movement of the pointer. Then the hook continues with the
new context.
</tag>
</comments>

<!-- @code-block-asset name="learn-input-drag" -->

![learn-input-drag](../assets/examples/learn-input-drag-light.gif#only-light)
![learn-input-drag](../assets/examples/learn-input-drag-dark.gif#only-dark)

<!-- /@code-block-asset -->

## Follow the pointer

[`PointerPosition`][xnano.expressions.PointerPosition] is the cell that the
pointer was over in the last mouse report. It is an expression, as the clock is.
Give `PointerPosition.x` and `PointerPosition.y` to `write()`, and the placement
follows the pointer without a hook. Use `mouse='motion'`, so that the terminal
reports each movement of the pointer.

```python
import xnano
from xnano.expressions import PointerPosition

with xnano.open(height=6, mouse='motion') as terminal:
    terminal.write('move the mouse · q quit', y='bottom', dim=True)
    terminal.write('<+>', x=PointerPosition.x - 1, y=PointerPosition.y)  # >> [center]
    terminal.run(stop_on='q')
```

<comments>
<tag name="center" color="blue">
`- 1` puts the middle cell of `<+>` on the pointer. To put the center of a
placement on the pointer, subtract half of its width and half of its height.
</tag>
</comments>

Before the first mouse report, the position has no value, so xnano does not draw
the placement. After that, `PointerPosition` keeps its value, also after a key
press or another event. While the mouse does not move, the placement causes no
frames. The canvas draws a frame for it only when the pointer moves. These rules
apply to such a placement:

- `is_visible = False` hides it, as it hides other placements.
- Before the first mouse report, `write()` with `lock=True` raises a
  `TerminalError`, because the position has no value to keep.

`context.mouse.position` and the expression
[`MousePosition`][xnano.expressions.MousePosition] are different. They give the
cell of the mouse event that the hook receives now, so use them in a mouse hook.
The cursor of the
[Circles](https://github.com/hsaeed3/xnano/blob/main/examples/01_rhythm_circles.py)
game follows the pointer with `PointerPosition`.

## The mouse wheel

To receive the mouse wheel, give `scroll=True` to `xnano.open()`. Then attach a
hook with `on='scroll'`. `context.mouse.scroll.y` is the number of steps: `-1`
for one step up and `1` for one step down. `context.mouse.scroll.x` gives the
steps to the side, with positive steps to the right.

## Pasted text

`on='paste'` runs a hook when the user pastes text. The hook receives all of the
text at one time, not one key at a time. The text is in
`context.keyboard.pasted`.

```python
import xnano

with xnano.open(height=2) as terminal:
    received = terminal.write('paste something')

    @terminal.hook(on='paste')
    def show_paste(context: xnano.Context):
        received.text = f'{len(context.keyboard.pasted)} characters pasted'

    terminal.run(stop_on='q')
```

Paste events are on by default. If you give `paste=False` to `xnano.open()`,
pasted text arrives as key presses.

## Stop the program

`terminal.run()` keeps the program open until the user presses a stop key.
`stop_on=` sets the stop keys, as one key or a list of keys. Without
`stop_on=`, the stop key is `'ctrl+c'`. `ctrl+c` also stops the program when
you give other stop keys. A hook can stop the program with
`context.canvas.stop()`.

```python
import xnano

with xnano.open(height=2) as terminal:
    terminal.write('press enter three times')
    presses = 0

    @terminal.hook(on='key', keys='enter')
    def count(context: xnano.Context):
        global presses
        presses += 1
        if presses == 3:
            context.canvas.stop()  # >> [stop]

    terminal.run()
```

<comments>
<tag name="stop" color="green">
Ends the loop. `terminal.run()` returns, and the canvas closes.
</tag>
</comments>

## End a run and keep the terminal

A program with several steps needs `terminal.run()` to return while the
terminal stays open: a title screen before a game, or the pages of a form. Give
`end_on=` the key, or the keys, that end the run. When the user presses one,
`terminal.run()` returns, and the terminal goes on drawing and listening. Your
program can then change the screen and call `terminal.run()` again. A hook can
end the run with `context.canvas.end_run()`.

```python
import xnano

with xnano.open(height=2) as terminal:
    message = terminal.write('press enter to start')
    terminal.run(stop_on='q', end_on='enter')  # >> [end]

    if terminal.is_running:  # >> [is_running]
        message.text = 'loading...'

        @terminal.hook(on='tick', after=1.0)
        def loaded(context: xnano.Context):
            context.canvas.end_run()  # >> [end_run]

        terminal.run(stop_on='q')

    if terminal.is_running:
        message.text = 'ready: press q to quit'
        terminal.run(stop_on='q')
```

<comments>
<tag name="end" color="blue">
`enter` ends this run and leaves the terminal open. `q` still stops the
terminal.
</tag>

<tag name="is_running" color="pink">
`True` after the run ended, and `False` after the terminal stopped. A stopped
terminal is closed, and writing to it raises an error, so the program only
goes on while the terminal is running.
</tag>

<tag name="end_run" color="green">
Ends the run that is waiting. If no run is waiting, it does nothing.
</tag>
</comments>

The stop keys and the end keys belong to one call of `terminal.run()`. Give
them again to the next call.

A hook runs until you remove it. You can remove a hook in two ways:

- Outside the hook, call `remove()` on the name of the function, for example
  `count.remove()`. The decorator replaces the function with the hook, so the
  name refers to the hook.
- Inside the hook, call `context.hook.remove()`.

There are more kinds of hooks: `'focus'`, `'resize'`, `'state'` and `'custom'`.
The [`hook`][xnano.hook] reference lists every kind and all of the options.
