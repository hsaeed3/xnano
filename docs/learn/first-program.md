---
title: Your First Program
icon: lucide/terminal
---

# Your First Program

The best way to understand xnano is to build something with it. In this guide
we'll build a focus timer: it counts down 25 minutes, shows its progress, pauses
with the space bar and rings a bell when the time is up.

It's a small program, but it uses every idea xnano is made of: a canvas on the
screen, placements you change, hooks that run on keys and time, a widget and a
sound. Make a file called `focus.py` and follow along.

## Open a terminal

Every xnano program draws on a **canvas**. `xnano.open()` creates one and puts
it on your screen, and the `with` block gives the screen back when the program
ends.

<!-- @code-block name="learn-first-program-open" type="image" height=5 -->
```python title="focus.py"
import xnano

with xnano.open(height=5) as terminal:  # >> [open]
    terminal.screen.write('Focus', bold=True)  # >> [write]
    terminal.screen.write('25:00', foreground='cyan')  # >> [write]
    terminal.run(stop_on='q')  # >> [run]
```

<comments>
<tag name="open" color="blue">
Draws in a region five rows tall, right below your prompt. Leave `height` out
and the canvas takes over the whole window instead.
</tag>

<tag name="write" color="pink">
Writes text on the canvas's screen. With no position given, each write goes on
the next line, the way a terminal prints.

<definition term="write" kind="method">
Puts text, a widget, an image or another canvas on the screen.
</definition>
</tag>

<tag name="run" color="green">
Keeps the terminal alive, drawing and listening, until `q` is pressed.
</tag>
</comments>

<!-- @code-block-asset name="learn-first-program-open" -->

![learn-first-program-open](../assets/examples/learn-first-program-open-light.png#only-light)
![learn-first-program-open](../assets/examples/learn-first-program-open-dark.png#only-dark)

<!-- /@code-block-asset -->

Run it with `python focus.py`, and press `q` to quit.

## Count down

`write()` returns a **placement**: a live handle on what you wrote. Assign its
`text` and the screen changes on the next frame. Nothing else to call, nothing
to redraw.

To change it every second, we add a **hook**: a function that xnano calls when
something happens. `on='tick'` with `every=1.0` calls it once a second.

```python title="focus.py" hl_lines="3-4 8 10-14"
import xnano

MINUTES = 25
SECONDS = MINUTES * 60

with xnano.open(height=5) as terminal:
    terminal.screen.write('Focus', bold=True)
    countdown = terminal.screen.write(f'{MINUTES:02}:00', foreground='cyan')

    @terminal.hook(on='tick', every=1.0)  # >> [hook]
    def count_down(context: xnano.Context):  # >> [hook]
        remaining = max(0, SECONDS - round(context.clock.elapsed_seconds))  # >> [clock]
        minutes, seconds = divmod(remaining, 60)
        countdown.text = f'{minutes:02}:{seconds:02}'  # >> [placement]

    terminal.run(stop_on='q')
```

<comments>
<tag name="placement" color="pink">
`countdown` is the placement of the time. Setting its `text` replaces what it
shows.
</tag>

<tag name="hook" color="blue">
Runs `count_down` once every second for as long as the terminal is open.

<definition term="Context" kind="class">
What a hook is called with: the event, and the canvas's devices.
</definition>
</tag>

<tag name="clock" color="amber">
The canvas's clock counts the seconds since it started.
</tag>
</comments>

## Pause with a key

A key hook runs when a key is pressed. `keys='space'` narrows it to the space
bar. The clock can `pause()` and `resume()`, and while it's paused, everything
that follows it stands still, our tick hook included.

While the timer is paused, we dim the time so it's clear at a glance, and a hint
at the bottom says which keys do what.

```python title="focus.py" hl_lines="9 17-23"
import xnano

MINUTES = 25
SECONDS = MINUTES * 60

with xnano.open(height=5) as terminal:
    terminal.screen.write('Focus', bold=True)
    countdown = terminal.screen.write(f'{MINUTES:02}:00', foreground='cyan')
    terminal.screen.write('space pause · q quit', y='bottom', dim=True)  # >> [hint]

    @terminal.hook(on='tick', every=1.0)
    def count_down(context: xnano.Context):
        remaining = max(0, SECONDS - round(context.clock.elapsed_seconds))
        minutes, seconds = divmod(remaining, 60)
        countdown.text = f'{minutes:02}:{seconds:02}'

    @terminal.hook(on='key', keys='space')  # >> [key]
    def pause_or_resume(context: xnano.Context):
        if context.clock.is_paused:
            context.clock.resume()
        else:
            context.clock.pause()
        countdown.dim(context.clock.is_paused)  # >> [dim]

    terminal.run(stop_on='q')
```

<comments>
<tag name="hint" color="green">
`y='bottom'` puts the hint on the last row. A line given its own position stays
out of the flow, so it never moves the lines above it.
</tag>

<tag name="key" color="blue">
Runs when the space bar is pressed, and again while it repeats.
</tag>

<tag name="dim" color="pink">
`dim(True)` dims the text and `dim(False)` brings it back.
</tag>
</comments>

## Show the progress

Widgets draw richer things than text: gauges, charts, tables and lists. A
`Gauge` fills up to a ratio between 0 and 1.

We could update the gauge in the tick hook, but there's a shorter way.
Arithmetic on the clock, like `terminal.clock / SECONDS`, gives an
**expression**: a value xnano works out again on every frame. Hand it to the
gauge, and the gauge follows the clock by itself, pauses included.

```python title="focus.py" hl_lines="2 10"
import xnano
from xnano.widgets import Gauge

MINUTES = 25
SECONDS = MINUTES * 60

with xnano.open(height=5) as terminal:
    terminal.screen.write('Focus', bold=True)
    countdown = terminal.screen.write(f'{MINUTES:02}:00', foreground='cyan')
    terminal.screen.write(Gauge(terminal.clock / SECONDS), width='100%')  # >> [gauge]
    terminal.screen.write('space pause · q quit', y='bottom', dim=True)

    @terminal.hook(on='tick', every=1.0)
    def count_down(context: xnano.Context):
        remaining = max(0, SECONDS - round(context.clock.elapsed_seconds))
        minutes, seconds = divmod(remaining, 60)
        countdown.text = f'{minutes:02}:{seconds:02}'

    @terminal.hook(on='key', keys='space')
    def pause_or_resume(context: xnano.Context):
        if context.clock.is_paused:
            context.clock.resume()
        else:
            context.clock.pause()
        countdown.dim(context.clock.is_paused)

    terminal.run(stop_on='q')
```

<comments>
<tag name="gauge" color="amber">
A gauge as wide as the screen, filled by the share of the time that has passed.
The gauge stops at full, so the expression needs no limit.

<definition term="Gauge" kind="class">
A bar filled to a ratio, with the percentage on it.
</definition>
</tag>
</comments>

## Ring the bell

Last, the timer should say when it's done. When no time remains, the hook turns
the time green, removes itself so it stops counting, and plays three notes on a
bell.

Sound needs the `audio` extra from
[Installation](installation.md#optional-extras). On a computer with no sound
device, `speaker.is_available` is `False`, and the timer finishes quietly.

<!-- @code-block name="learn-first-program-finished" type="gif" height=5
wait 2.4
press space
wait 1.6
press space
wait 1.4
-->
```python title="focus.py" hl_lines="18-23"
import xnano
from xnano.widgets import Gauge

MINUTES = 25
SECONDS = MINUTES * 60

with xnano.open(height=5) as terminal:
    terminal.screen.write('Focus', bold=True)
    countdown = terminal.screen.write(f'{MINUTES:02}:00', foreground='cyan')
    terminal.screen.write(Gauge(terminal.clock / SECONDS), width='100%')
    terminal.screen.write('space pause · q quit', y='bottom', dim=True)

    @terminal.hook(on='tick', every=1.0)
    def count_down(context: xnano.Context):
        remaining = max(0, SECONDS - round(context.clock.elapsed_seconds))
        minutes, seconds = divmod(remaining, 60)
        countdown.text = f'{minutes:02}:{seconds:02}'
        if remaining == 0:
            countdown.text = 'done'
            countdown.color.fg = 'green'
            context.hook.remove()  # >> [remove]
            if context.speaker.is_available:
                context.speaker.play('C5 E5 G5:2', instrument='bell')  # >> [bell]

    @terminal.hook(on='key', keys='space')
    def pause_or_resume(context: xnano.Context):
        if context.clock.is_paused:
            context.clock.resume()
        else:
            context.clock.pause()
        countdown.dim(context.clock.is_paused)

    terminal.run(stop_on='q')
```

<comments>
<tag name="remove" color="pink">
`context.hook` is the hook that is running, and `remove()` stops it.
</tag>

<tag name="bell" color="green">
Melody text: three notes, the last held for two beats.
</tag>
</comments>

<!-- @code-block-asset name="learn-first-program-finished" -->

![learn-first-program-finished](../assets/examples/learn-first-program-finished-light.gif#only-light)
![learn-first-program-finished](../assets/examples/learn-first-program-finished-dark.gif#only-dark)

<!-- /@code-block-asset -->

That's the whole timer. Set `MINUTES = 1` to watch it finish.

## Where to next

The rest of the guides go deeper into each piece you just used:

- [Writing Content](content.md): positions, sizes, boxes and layers.
- [Styling](styling.md): colors and text modifiers, and changing them later.
- [Hooks & Input](input.md): keys, the mouse, dragging and pasting.
- [Time & Effects](time.md): timers, expressions and animated effects.
- [Widgets](widgets.md), [Images & Pixel Art](images.md) and [Sound](sound.md).
