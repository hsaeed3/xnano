---
title: Testing
icon: lucide/flask-conical
---

# Testing

A program that draws on a terminal is hard to test on a terminal. With xnano
you do not need one. `xnano.new()` makes a canvas in memory that has the same
screen, keyboard, mouse and clock as a live terminal. A test writes on it,
presses its keys, moves its clock, and reads what it shows.

These examples use [pytest](https://docs.pytest.org/), but any test tool works.

## Write a program that you can test

Put the code that builds the screen in a function that takes a canvas. The
program gives it a live terminal, and a test gives it a canvas in memory.

```python
import xnano


def build(canvas: xnano.Canvas) -> None:
    counter = canvas.write('count 0')
    canvas.write('space add · q quit', y='bottom', dim=True)
    count = 0

    @canvas.hook(on='key', keys='space')
    def add(context: xnano.Context):
        nonlocal count
        count += 1
        counter.text = f'count {count}'
        if count == 3:
            counter.color.fg = 'green'


if __name__ == '__main__':
    with xnano.open(height=3) as terminal:  # >> [live]
        build(terminal)
        terminal.run(stop_on='q')
```

<comments>
<tag name="live" color="blue">
A terminal is a canvas, so `build()` takes it. A test calls `build()` with a
canvas from `xnano.new()`.
</tag>
</comments>

## Read the screen

`canvas.render()` returns the screen as text, one line for each row. Compare it
with the text that you expect.

```python
import xnano


def build(canvas: xnano.Canvas) -> None:
    canvas.write('count 0')
    canvas.write('space add · q quit', y='bottom', dim=True)


def test_the_counter_starts_at_zero():
    with xnano.new(width=24, height=3) as canvas:  # >> [size]
        build(canvas)
        lines = canvas.render().splitlines()
        assert lines[0] == 'count 0'
        assert lines[2] == 'space add · q quit'


test_the_counter_starts_at_zero()
```

<comments>
<tag name="size" color="pink">
Give the canvas the size of the window that you want to test. To test a small
window, make a small canvas.
</tag>
</comments>

`render()` gives the characters without their colors. To test a color, read the
placement, for example `counter.color.fg`, or use `canvas.render(format='ansi')`.

## Press keys

`canvas.push()` gives the canvas an event, and `canvas.deliver_events()` runs
the hooks that hear it. [`Event`][xnano.events.Event] makes the events: a key
press, a mouse press, pasted text, or an event of your own.

```python
import xnano
from xnano.events import Event

with xnano.new(width=24, height=3) as canvas:
    counter = canvas.write('count 0')

    @canvas.hook(on='key', keys='space')
    def add(context: xnano.Context):
        counter.text = f'count {int(counter.text.split()[1]) + 1}'

    for _ in range(3):
        canvas.push(Event.key_press('space'))  # >> [push]
    canvas.deliver_events()  # >> [deliver]
    assert counter.text == 'count 3'
```

<comments>
<tag name="push" color="blue">
Adds a press of the space bar. The hooks do not run yet.
</tag>

<tag name="deliver" color="green">
Runs the hooks for all the events that you pushed. It does not move the clock.
</tag>
</comments>

## Move the clock

A canvas from `xnano.new()` has a clock that moves only when you move it. A
test of a timer or an effect does not wait: it tells the clock how much time
passes. `canvas.clock.sleep(seconds)` moves the clock one frame at a time, and
the timers and effects in that time run. `canvas.clock.step()` moves one frame.

```python
import xnano

with xnano.new(width=24, height=1) as canvas:
    label = canvas.write('0 s')

    @canvas.hook(on='tick', every=1.0)
    def count_up(context: xnano.Context):
        label.text = f'{round(context.clock.elapsed_seconds)} s'

    canvas.clock.sleep(3)  # >> [sleep]
    assert canvas.render() == '3 s'
```

<comments>
<tag name="sleep" color="pink">
Three seconds pass on the clock of the canvas, and the test does not wait.
</tag>
</comments>

[Sound](sound.md#sound-in-tests) shows how to test a program that plays sound.
