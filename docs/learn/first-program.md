---
title: Your First Program
icon: lucide/terminal
---

# Your First Program

The best way to learn xnano is to build something with it. In this guide, we
will build a focus timer. The timer does these things:

- It counts down from 25 minutes.
- It shows its progress on a bar.
- It pauses and continues when you press the space bar.
- It plays a bell sound when no time remains.

The program is small, but it uses all the main ideas of xnano: a canvas,
placements, hooks, a widget and a sound. Make a file with the name `focus.py`.
From the second step, each step shows the full file, and the highlighted lines
are new.

## Open a terminal

Every xnano program draws on a **canvas**. `xnano.open()` makes a canvas, shows
it in your terminal window and returns it as a **terminal**. When the `with`
block ends, xnano closes the canvas and gives the window back to your shell.

<!-- @code-block name="learn-first-program-open" type="image" height=5 -->
```python title="focus.py"
import xnano

with xnano.open(height=5) as terminal:  # >> [open]
    terminal.write('Focus', bold=True)  # >> [write]
    terminal.write('25:00', foreground='cyan')  # >> [write]
    terminal.run(stop_on='q')  # >> [run]
```

<comments>
<tag name="open" color="blue">
The canvas uses a region of five rows, directly below your prompt. If you leave
out `height`, the canvas fills the whole window. When the canvas closes, xnano
erases the region.
</tag>

<tag name="write" color="pink">
Writes text on the screen of the canvas. `terminal.write()` is the same as
`terminal.screen.write()`. Without a position, each `write()` puts its text on
the next line. `bold` and `foreground` set the style of the text.

<definition term="write" kind="method">
Shows text, a widget, an image or another canvas on the screen. It returns a
placement.
</definition>
</tag>

<tag name="run" color="green">
Keeps the program open until you press `q`. During this time, the terminal
draws the screen and reads the keys by itself. Without `stop_on`, `ctrl+c` stops
the program.
</tag>
</comments>

<!-- @code-block-asset name="learn-first-program-open" -->

![learn-first-program-open](../assets/examples/learn-first-program-open-light.png#only-light)
![learn-first-program-open](../assets/examples/learn-first-program-open-dark.png#only-dark)

<!-- /@code-block-asset -->

Run the program with `python focus.py`. To stop it, press `q`.

## Count down

`write()` returns a **placement**, a live handle on the content that you wrote.
If you set the `text` of a placement, the screen shows the new text on the next
frame. You do not have to call anything else.

To change the time each second, we add a **hook**. A hook is a function that
xnano calls when something happens. xnano gives the hook a **context**, which
holds the event and the devices of the canvas, such as its clock.

```python title="focus.py" hl_lines="3-4 8 10-14"
import xnano

MINUTES = 25
SECONDS = MINUTES * 60

with xnano.open(height=5) as terminal:
    terminal.write('Focus', bold=True)
    countdown = terminal.write(f'{MINUTES:02}:00', foreground='cyan')

    @terminal.hook(on='tick', every=1.0)  # >> [hook]
    def count_down(context: xnano.Context):  # >> [hook]
        remaining = max(0, SECONDS - round(context.clock.elapsed_seconds))  # >> [clock]
        minutes, seconds = divmod(remaining, 60)
        countdown.text = f'{minutes:02}:{seconds:02}'  # >> [placement]

    terminal.run(stop_on='q')
```

<comments>
<tag name="placement" color="pink">
`countdown` is the placement of the time. When you set its `text`, the new text
replaces the old text.
</tag>

<tag name="hook" color="blue">
`@terminal.hook(...)` makes `count_down` a hook of the terminal. With
`on='tick'` and `every=1.0`, xnano calls it one time each second.

<definition term="Context" kind="class">
What xnano gives to a hook: the event, and the devices of the canvas, such as
`context.clock`.
</definition>
</tag>

<tag name="clock" color="amber">
`elapsed_seconds` is the time in seconds since the canvas started. `round()`
makes it a whole number, and `max(0, ...)` stops the count at zero.
</tag>
</comments>

## Pause with a key

A hook with `on='key'` runs when you press a key. `keys='space'` makes it run
only for the space bar. The clock has a `pause()` method and a `resume()`
method. While the clock is paused, everything that follows the clock stops. This
includes our tick hook.

While the timer is paused, we make the time dim, so you can see the pause
immediately. A hint on the last row tells you which keys to use.

```python title="focus.py" hl_lines="9 17-23"
import xnano

MINUTES = 25
SECONDS = MINUTES * 60

with xnano.open(height=5) as terminal:
    terminal.write('Focus', bold=True)
    countdown = terminal.write(f'{MINUTES:02}:00', foreground='cyan')
    terminal.write('space pause · q quit', y='bottom', dim=True)  # >> [hint]

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
`y='bottom'` puts the hint on the last row. A line with its own `y` stays at
that row. It does not move the other lines, and the other lines do not move it.
</tag>

<tag name="key" color="blue">
xnano calls this hook when you press the space bar. If you hold the key, xnano
calls the hook again each time the key repeats.
</tag>

<tag name="dim" color="pink">
`dim(True)` makes the text dim, and `dim(False)` makes it normal again. The
value here is `is_paused`, so the time is dim only while the clock is paused.
</tag>
</comments>

## Show the progress

A **widget** shows more than text, for example a gauge, a chart, a table or a
list. A [`Gauge`][xnano.widgets.Gauge] is a bar that fills to a ratio from 0 to
1.

We can change the gauge in the tick hook, but there is a shorter method.
Arithmetic on the clock, such as `terminal.clock / SECONDS`, gives an
**expression**. An expression is a value that xnano calculates again on each
frame. If you give an expression to the gauge, the gauge follows the clock
without a hook. The gauge also stops while the clock is paused.

```python title="focus.py" hl_lines="2 10"
import xnano
from xnano.widgets import Gauge

MINUTES = 25
SECONDS = MINUTES * 60

with xnano.open(height=5) as terminal:
    terminal.write('Focus', bold=True)
    countdown = terminal.write(f'{MINUTES:02}:00', foreground='cyan')
    terminal.write(Gauge(terminal.clock / SECONDS), width='100%')  # >> [gauge]
    terminal.write('space pause · q quit', y='bottom', dim=True)

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
`width='100%'` makes the gauge as wide as the screen. Its ratio is the elapsed
time divided by the full time. A gauge does not fill past 1, so the expression
needs no limit.

<definition term="Gauge" kind="class">
A bar that fills to a ratio and shows the percentage on it.
</definition>
</tag>
</comments>

## Ring the bell

Last, the timer must tell you that no time remains. When `remaining` is 0, the
tick hook does three things:

- It shows `done` in green.
- It removes itself, so the count stops.
- It plays three notes with a bell sound.

Sound needs the `audio` extra, and
[Installation](installation.md#optional-extras) shows how to install it. If the
extra is not installed, `context.speaker` raises an `ImportError` that tells you
what to install. On a computer without a sound device, `speaker.is_available` is
`False`, and the timer finishes without a sound.

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
    terminal.write('Focus', bold=True)
    countdown = terminal.write(f'{MINUTES:02}:00', foreground='cyan')
    terminal.write(Gauge(terminal.clock / SECONDS), width='100%')
    terminal.write('space pause · q quit', y='bottom', dim=True)

    @terminal.hook(on='tick', every=1.0)
    def count_down(context: xnano.Context):
        remaining = max(0, SECONDS - round(context.clock.elapsed_seconds))
        minutes, seconds = divmod(remaining, 60)
        countdown.text = f'{minutes:02}:{seconds:02}'
        if remaining == 0:
            countdown.text = 'done'  # >> [done]
            countdown.color.fg = 'green'  # >> [done]
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
<tag name="done" color="amber">
The time changes to `done`. `color.fg` is the text color of a placement, so the
word shows in green.
</tag>

<tag name="remove" color="pink">
`context.hook` is the hook that runs now. `remove()` stops it, so xnano does not
call it again.
</tag>

<tag name="bell" color="green">
The text is a melody of three notes, and `:2` makes the last note two beats
long. [Sound](sound.md) explains melody text.
</tag>
</comments>

<!-- @code-block-asset name="learn-first-program-finished" -->

![learn-first-program-finished](../assets/examples/learn-first-program-finished-light.gif#only-light)
![learn-first-program-finished](../assets/examples/learn-first-program-finished-dark.gif#only-dark)

<!-- /@code-block-asset -->

That is the full timer. To see the end sooner, set `MINUTES = 1`.

## Next steps

The other guides explain each part in more detail:

- [Writing Content](content.md): positions, sizes, boxes, layouts and layers.
- [Styling](styling.md): colors, text modifiers, and style changes after you
  write.
- [Hooks & Input](input.md): the keyboard, the mouse and pasted text.
- [Time & Effects](time.md): the clock, timers, expressions and effects.
- [Widgets](widgets.md): gauges, charts, tables and lists.
- [Images & Pixel Art](images.md): pixel art and pictures.
- [Sound](sound.md): notes, melodies and the microphone.
- [Testing](testing.md): tests for a program like this timer, without a
  terminal.
