---
title: Time & Effects
icon: lucide/timer
---

# Time & Effects

Every canvas has a **clock**. It counts the time since the canvas started, sets
how many frames are drawn each second, and can stand still. Anything that
changes over time follows it: timers, values worked out on every frame, and
animated effects.

## The clock

`terminal.clock.elapsed_seconds` is the time since the canvas started, not
counting time spent paused. A live canvas draws up to 60 frames each second;
give `fps=` to `xnano.open()` for a different rate.

```python
import xnano

with xnano.open(height=2, fps=30) as terminal:
    elapsed = terminal.screen.write('')

    @terminal.hook(on='frame')
    def show_time(context: xnano.Context):
        elapsed.text = f'{context.clock.elapsed_seconds:.1f}s'

    terminal.run(stop_on='q')
```

`on='frame'` runs a hook once before every frame is drawn. That's the place for
work that must happen continuously; for anything slower, use a timer.

## Timers

`on='tick'` runs a hook on a timer: `every=` repeats it every so many seconds,
and `after=` runs it once.

<!-- @code-block name="learn-time-timers" type="gif" height=3
wait 4.5
-->
```python
import xnano

with xnano.open(height=3) as terminal:
    ticks = terminal.screen.write('tick 0')
    message = terminal.screen.write('')
    count = 0

    @terminal.hook(on='tick', every=1.0)
    def count_up(context: xnano.Context):
        global count
        count += 1
        ticks.text = f'tick {count}'

    @terminal.hook(on='tick', after=3.0)
    def say_hello(context: xnano.Context):
        message.text = 'three seconds have passed'

    terminal.run(stop_on='q')
```

<!-- @code-block-asset name="learn-time-timers" -->

![learn-time-timers](../assets/examples/learn-time-timers-light.gif#only-light)
![learn-time-timers](../assets/examples/learn-time-timers-dark.gif#only-dark)

<!-- /@code-block-asset -->

Timers follow the clock, so they stand still while it's paused. `clock.pause()`
freezes time, and `clock.resume()` lets it run on. The [focus
timer](first-program.md#pause-with-a-key) uses both.

## Values that follow the clock

Arithmetic on the clock gives an **expression**: a value that xnano works out
again on every frame. Assign one to a position, a size, or a number in a widget,
and it changes by itself, with no hook at all.

<!-- @code-block name="learn-time-expressions" type="gif" height=3
wait 4.0
-->
```python
import xnano
from xnano.expressions import ParentWidth

with xnano.open(height=3) as terminal:
    ball = terminal.screen.write('●', y=1, foreground='cyan')
    ball.x = (terminal.clock * 12) % ParentWidth  # >> [expression]
    terminal.screen.write('q quit', y='bottom', dim=True)
    terminal.run(stop_on='q')
```

<comments>
<tag name="expression" color="amber">
Twelve cells a second, wrapping around at the right edge. `terminal.clock` reads
as the elapsed seconds, and `ParentWidth` is the width of the screen the ball is
on, so the wrap follows the window when it's resized.
</tag>
</comments>

<!-- @code-block-asset name="learn-time-expressions" -->

![learn-time-expressions](../assets/examples/learn-time-expressions-light.gif#only-light)
![learn-time-expressions](../assets/examples/learn-time-expressions-dark.gif#only-dark)

<!-- /@code-block-asset -->

A canvas with an expression on it draws every frame, because time keeps moving.
A layout that only needs to follow the size of the window should use percentages
and words instead, which cost nothing while the window stays the same size.

## Effects

An **effect** animates how something looks: it fades, dissolves, sweeps, slides
or shifts its colors. Each placement has an `fx` with one method for each
effect, and calling one starts it. `duration_milliseconds` sets how long it
takes.

<!-- @code-block name="learn-time-effects" type="gif" height=6
wait 1.2
press 1
wait 1.2
press 2
wait 1.2
press 3
wait 1.4
-->
```python
import xnano

with xnano.open(height=6) as terminal:
    card = terminal.screen.write(
        'xnano',
        border='rounded',
        padding={'horizontal': 4, 'vertical': 1},
        foreground='magenta',
    )
    terminal.screen.write('1 sweep · 2 coalesce · 3 fade · q quit', y='bottom', dim=True)
    card.fx.fade_from(foreground='black', duration_milliseconds=800)  # >> [start]

    @terminal.hook(on='key', keys='1')
    def sweep(context: xnano.Context):
        card.fx.sweep_in(color='cyan', duration_milliseconds=600)

    @terminal.hook(on='key', keys='2')
    def coalesce(context: xnano.Context):
        card.fx.coalesce(duration_milliseconds=600)

    @terminal.hook(on='key', keys='3')
    def fade(context: xnano.Context):
        card.fx.fade_from(foreground='yellow', duration_milliseconds=600)

    terminal.run(stop_on='q')
```

<comments>
<tag name="start" color="pink">
Fades the card in from black as the program starts.
</tag>
</comments>

<!-- @code-block-asset name="learn-time-effects" -->

![learn-time-effects](../assets/examples/learn-time-effects-light.gif#only-light)
![learn-time-effects](../assets/examples/learn-time-effects-dark.gif#only-dark)

<!-- /@code-block-asset -->

The effects include `fade_to` and `fade_from`, `dissolve` and `coalesce`,
`sweep_in` and `sweep_out`, `slide_in` and `slide_out`, `hsl_shift`, `paint`,
`lighten`, `darken` and `glitch`. They come from
[tachyonfx](https://github.com/ratatui/tachyonfx), and the
[`xnano.effects`][xnano.effects] reference lists each one with its settings.

Keep effects purposeful. An effect that confirms a change, or draws the eye to
one, helps; an effect that stands between the user and what they asked for gets
in the way. An effect that answers a key press feels best short, between 150 and
300 milliseconds. The longer ones above suit an entrance, or a showcase like
this one.
