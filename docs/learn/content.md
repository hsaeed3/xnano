---
title: Writing Content
icon: lucide/layout-dashboard
---

# Writing Content

Everything you see in an xnano program gets onto the screen the same way:
through `screen.write()`. This guide covers where things go, how big they are,
how to put them in boxes and on top of each other, and how to change them once
they're there.

## A frame without a terminal

The examples on this page draw a single frame and print it, so you can run them
anywhere, even in a notebook. `xnano.new()` creates a canvas in memory, with no
screen of its own, and `render()` turns its screen into text. `format='ansi'`
keeps the colors.

<!-- @code-block name="learn-content-frame" type="image" height=4 -->
```python
import xnano

with xnano.new(width=40, height=4) as canvas:
    canvas.screen.write('Deploy', bold=True)
    canvas.screen.write('3 services, 2 regions')
    canvas.screen.write('ready', x='right', y='bottom', foreground='green')
    print(canvas.screen.render(format='ansi'))
```

A canvas from `xnano.open()` has exactly the same screen, so everything here
works the same way in a live program.

## Positions

Content with no position goes on the next line, the way a terminal prints. Give
it an `x` or a `y`, and it goes there instead. Both take:

- a number of cells, counted from `0` at the top-left corner;
- a percentage of the screen, such as `'25%'`;
- a word: `'left'`, `'center'` or `'right'` for `x`, and `'top'`, `'center'` or
  `'bottom'` for `y`.

<!-- @code-block name="learn-content-positions" type="image" height=5 -->
```python
import xnano

with xnano.new(width=40, height=5) as canvas:
    screen = canvas.screen
    screen.write('top left', x='left', y='top')
    screen.write('top right', x='right', y='top')
    screen.write('center', x='center', y='center')
    screen.write('25% in', x='25%', y=3)
    screen.write('bottom right', x='right', y='bottom')
    print(screen.render(format='ansi'))
```

Percentages and words are worked out again whenever the screen changes size, so
`'center'` stays in the center when the user resizes the window.

## Sizes

Content is as big as it needs to be, unless you give it a `width` or a `height`.
Sizes take the same forms as positions: cells, or a percentage such as `'50%'`.

Text that doesn't fit its width is cut off at the edge. To wrap it onto more
lines, write it as a `Paragraph` widget:

<!-- @code-block name="learn-content-wrap" type="image" height=4 -->
```python
import xnano
from xnano.widgets import Paragraph

with xnano.new(width=40, height=4) as canvas:
    text = 'Text wider than its placement wraps onto the next line.'
    canvas.screen.write(Paragraph(text, should_wrap=True), width=20, height=3)
    print(canvas.screen.render(format='ansi'))
```

## Boxes

`border` draws a box around what you write: `'plain'`, `'rounded'`, `'double'`
or `'thick'`. A `title` sits on the top edge of the border, and `padding` puts
space between the border and the content, in cells.

<!-- @code-block name="learn-content-boxes" type="image" height=5 -->
```python
import xnano

with xnano.new(width=48, height=5) as canvas:
    screen = canvas.screen
    screen.write('plain', border='plain')
    screen.write('rounded', border='rounded', title='title', x=10, y=0)
    screen.write('double', border='double', x=22, y=0)
    screen.write(
        'thick', border='thick', padding={'horizontal': 2, 'vertical': 1}, x=33, y=0
    )
    print(screen.render(format='ansi'))
```

A terminal cell is about twice as tall as it is wide, so padding looks even when
it has twice as many columns as rows, like the `thick` box above.

## Sharing space

A canvas made with `layout='row'` shares its width between everything written on
it, side by side. Each piece gets an equal share, and a `width` of `'100%'`
fills it. `layout='column'` does the same from top to bottom.

<!-- @code-block name="learn-content-row" type="image" height=3 -->
```python
import xnano

with xnano.new(width=48, height=3, layout='row') as canvas:
    for name in ('logs', 'metrics', 'alerts'):
        canvas.screen.write(name, border='rounded', width='100%')
    print(canvas.screen.render(format='ansi'))
```

For a layout of your own, put a canvas inside another one. A canvas created
inside the `with` block of another is measured in it, so `'50%'` is half of the
outer canvas. Write it where you want it to show:

<!-- @code-block name="learn-content-nested" type="image" height=4 -->
```python
import xnano

with xnano.new(width=48, height=4) as window:
    with xnano.new(width='50%', height='100%', border='rounded', title='files') as files:
        files.screen.write('notes.md')
        files.screen.write('todo.md')
    window.screen.write(files)

    with xnano.new(
        width='50%', height='100%', border='rounded', title='preview'
    ) as preview:
        preview.screen.write('# Notes')
    window.screen.write(preview, x='50%', y=0)

    print(window.screen.render(format='ansi'))
```

## Layers

Content on a higher `layer` is drawn over content on a lower one. Everything
starts on layer `0`. Give a popup its own `background`, so the text behind it
doesn't show through.

<!-- @code-block name="learn-content-layers" type="image" height=5 -->
```python
import xnano

with xnano.new(width=40, height=5) as canvas:
    for row in range(5):
        canvas.screen.write('the content underneath ' * 2, y=row, dim=True)
    canvas.screen.write(
        'Saved',
        x='center',
        y='center',
        border='rounded',
        padding={'horizontal': 2},
        background='black',
        layer=1,
    )
    print(canvas.screen.render(format='ansi'))
```

## Changing what you wrote

`write()` returns a placement, and a placement is live: change it and the screen
follows. You can read it back too, so one placement can be positioned against
another.

```python
import xnano

with xnano.new(width=30, height=4) as canvas:
    box = canvas.screen.write('box', border='rounded')  # >> [write]
    assert (box.x, box.y, box.width, box.height) == (0, 0, 5, 3)

    box.move(5, 1)  # >> [move]
    assert (box.x, box.y) == (5, 1)

    box.x = 'right'  # >> [assign]
    box.text = 'moved'  # >> [assign]
    canvas.screen.write('<- here', x=box.x - 8, y=box.y + 1)  # >> [read]

    box.is_visible = False  # >> [visible]
    box.is_visible = True
    print(canvas.screen.render(format='ansi'))

    box.remove()  # >> [remove]
```

<comments>
<tag name="write">
A placement knows its position and its size in cells.
</tag>

<tag name="move">
`move()` shifts the placement by a number of columns and rows.
</tag>

<tag name="assign">
Assign a position or new text directly. Words and percentages work here as well.
</tag>

<tag name="read">
Positions read back as numbers, so they can place something else.
</tag>

<tag name="visible">
Hide a placement and show it again without losing it.
</tag>

<tag name="remove">
`remove()` takes it off the screen for good.
</tag>
</comments>

What you can write is wider than text: a list of strings writes several lines,
and [widgets](widgets.md), [images and pixel art](images.md) and other canvases
are written the same way. The [`Screen.write`][xnano.devices.Screen.write]
reference lists every option.
