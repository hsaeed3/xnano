---
title: "Getting Started"
icon: "fontawesome/solid/bolt"
---

# Getting Started

## Install

```bash
pip install xnano                # the terminal, widgets, effects and events
pip install "xnano[audio]"       # adds notes, melodies and sounds
pip install "xnano[image]"       # adds images and animations
```

## Put something on the terminal

[`open`][xnano.open] gives you a [`Terminal`][xnano.terminal.Terminal]. Anything you
[`write`][xnano.canvas.Canvas.write] appears at once, and a `with` block gives the screen back.

```python
import xnano

with xnano.open(width=40, height=5) as terminal:
    terminal.write('Hello, world!', x='center', y='center', border='rounded')
    terminal.run(quit_on='q')
```

Positions take numbers, percentages (`'50%'`), words (`'left'`, `'center'`, `'right'`, `'top'`,
`'bottom'`) or formulas.

## Make it move

A formula of time is evaluated again on every frame, so there is no loop to write:

```python
import xnano
from xnano.expressions import ParentWidth, TimeElapsed, Width

with xnano.open(width=40, height=3) as terminal:
    ball = terminal.write('●', y=1)
    ball.x = (ParentWidth - Width) * (TimeElapsed % 2 / 2)
    terminal.run(quit_on='q')
```

## React to the keyboard, the mouse and the clock

Decorators are named for what happens:

```python
import xnano

with xnano.open(width=30, height=3) as terminal:
    terminal.write('press space', y=1)
    elapsed = terminal.write('  0.0s')

    @terminal.on_key('space')
    def toggle(context: xnano.context.Context) -> None:
        if terminal.time.is_stopped:
            terminal.time.resume()
        else:
            terminal.time.stop()

    @terminal.every(1.0)
    def tick(context: xnano.context.Context) -> None:
        elapsed.text = f'{context.time.elapsed:5.1f}s'

    terminal.run(quit_on='q')
```

`on_click`, `on_drag`, `after` and `every(beats=1)` work the same way, and `terminal.input`
tells a game which keys are held right now.

## Draw pixels, build a world, play a sound

`terminal.pixels` draws two pixels to a cell, `terminal.scene(...)` adds sprites, a camera and
collision on top of it, and `terminal.play('C4 E4 G4:2')` plays a melody written as text. The
[examples](https://github.com/hsaeed3/xnano/tree/main/examples) show each of them, ending with a
playable world.

## Where everything lives

The top-level `xnano` holds the main API. Everything else is in a module named for what it
holds: [`xnano.widgets`][xnano.widgets], [`xnano.expressions`][xnano.expressions],
[`xnano.effects`][xnano.effects], [`xnano.styles`][xnano.styles],
[`xnano.events`][xnano.events], [`xnano.scene`][xnano.scene] and so on, with the optional
`xnano.audio` and `xnano.image`.
