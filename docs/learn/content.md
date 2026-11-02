---
title: Writing Content
icon: lucide/layout-dashboard
---

# Writing Content

Everything that you see in an xnano program comes from one call:
`canvas.write()`, which is the same as `canvas.screen.write()`. This guide shows
how to:

- set the position and the size of content,
- put a box around content,
- share the space of a canvas between pieces of content,
- put content over other content with layers,
- change content after you write it,
- put content next to other content,
- ask if an area holds a cell or overlaps other content.

## A frame without a terminal

The examples on this page draw one frame and print it, so you can run them
anywhere, for example in a notebook. They use a canvas from `xnano.new()`,
which stays in memory and does not show in your terminal window.

<!-- @code-block name="learn-content-frame" type="image" height=5 -->
```python
import xnano

with xnano.new(width=40, height=4) as canvas:  # >> [new]
    canvas.write('Deploy', bold=True)
    canvas.write('3 services, 2 regions')
    canvas.write('ready', x='right', y='bottom', foreground='green')  # >> [corner]
    print(canvas.render(format='ansi'))  # >> [render]
```

<comments>
<tag name="new" color="blue">
Makes a canvas in memory, 40 cells wide and 4 rows tall. Without `width` and
`height`, a canvas is 80 cells wide and 24 rows tall.
</tag>

<tag name="corner" color="green">
`x='right'` and `y='bottom'` put the text in the bottom-right corner.
</tag>

<tag name="render" color="pink">
`render()` returns what the canvas shows, as text. It is the same as
`canvas.screen.render()`. With `format='ansi'`, the text keeps its colors and
modifiers as escape codes. Without it, you get only the characters.
</tag>
</comments>

<!-- @code-block-asset name="learn-content-frame" -->

![learn-content-frame](../assets/examples/learn-content-frame-light.png#only-light)
![learn-content-frame](../assets/examples/learn-content-frame-dark.png#only-dark)

<!-- /@code-block-asset -->

A canvas from `xnano.open()` has the same screen, so all of this page also works
in a live program.

## Write on the canvas that runs

[`xnano.write()`][xnano.write] writes on the canvas that runs now. It takes the
same arguments as `canvas.write()`. Use it in a function that does not get the
canvas.

```python
import xnano


def show_status(text: str) -> None:
    xnano.write(text, x='right', foreground='green')  # >> [write]


with xnano.new(width=20, height=1) as canvas:
    show_status('ready')
    assert canvas.render().strip() == 'ready'
```

<comments>
<tag name="write" color="green">
Writes on the canvas of the `with` block that runs now, here `canvas`.
</tag>
</comments>

The canvas that runs now is the canvas of a `with xnano.open()` block or a
`with xnano.new()` block. In the block of a canvas inside another canvas, it is
the outer canvas. Outside these blocks, `xnano.write()` raises a
[`TerminalClosedError`][xnano.errors.TerminalClosedError]. A hook gets a context
and not the canvas. Thus, in a hook, write with `context.screen.write()`.

## Positions

Content without a position goes on the next line, as in a terminal that prints
lines. To put content somewhere else, give an `x`, a `y` or both. `x` is the
column of the left edge, and `y` is the row of the top edge. Both accept these
forms:

- A number of cells. The count starts at `0` in the top-left corner.
- A percentage of the screen, such as `'25%'`.
- A word. `x` accepts `'left'`, `'center'` and `'right'`, and `y` accepts
  `'top'`, `'center'` and `'bottom'`. The word aligns the content with that part
  of the screen.

<!-- @code-block name="learn-content-positions" type="image" height=6 -->
```python
import xnano

with xnano.new(width=40, height=5) as canvas:
    canvas.write('top left', x='left', y='top')
    canvas.write('top right', x='right', y='top')
    canvas.write('center', x='center', y='center')
    canvas.write('25% in', x='25%', y=3)
    canvas.write('bottom right', x='right', y='bottom')
    print(canvas.render(format='ansi'))
```

<!-- @code-block-asset name="learn-content-positions" -->

![learn-content-positions](../assets/examples/learn-content-positions-light.png#only-light)
![learn-content-positions](../assets/examples/learn-content-positions-dark.png#only-dark)

<!-- /@code-block-asset -->

xnano calculates percentages and words again when the size of the screen
changes. For example, `'center'` stays in the center when the user makes the
window larger. To keep the first position and size, give `lock=True` to
`write()`.

## Sizes

Content gets the size that it needs, unless you give a `width` or a `height`. A
size is a number of cells or a percentage of the screen, such as `'50%'`.

If text is wider than its `width`, xnano does not draw the part after the edge.
The same is true for content that goes past the edge of the screen. To continue
the text on more lines, write it in a [`Paragraph`][xnano.widgets.Paragraph]
widget with `should_wrap=True`:

<!-- @code-block name="learn-content-wrap" type="image" height=5 -->
```python
import xnano
from xnano.widgets import Paragraph

with xnano.new(width=40, height=4) as canvas:
    text = 'Text wider than its placement wraps onto the next line.'
    canvas.write(Paragraph(text, should_wrap=True), width=20, height=3)
    print(canvas.render(format='ansi'))
```

<!-- @code-block-asset name="learn-content-wrap" -->

![learn-content-wrap](../assets/examples/learn-content-wrap-light.png#only-light)
![learn-content-wrap](../assets/examples/learn-content-wrap-dark.png#only-dark)

<!-- /@code-block-asset -->

The paragraph breaks the lines between words. Without a `height`, the paragraph
is as tall as its lines. With a `height`, xnano shows only the lines that fit.

## Boxes

`border` puts a box around the content. Its value is the kind of line:
`'plain'`, `'rounded'`, `'double'` or `'thick'`. `border=True` gives a
`'plain'` border. `title` writes a title on the top edge of the border, and a
`title` without a `border` gives a plain border. `padding` adds space between
the border and the content.

<!-- @code-block name="learn-content-boxes" type="image" height=6 -->
```python
import xnano

with xnano.new(width=48, height=5) as canvas:
    canvas.write('plain', border='plain')
    canvas.write('rounded', border='rounded', title='title', x=10, y=0)
    canvas.write('double', border='double', x=22, y=0)
    canvas.write(
        'thick', border='thick', padding={'horizontal': 2, 'vertical': 1}, x=33, y=0
    )
    print(canvas.render(format='ansi'))
```

<!-- @code-block-asset name="learn-content-boxes" -->

![learn-content-boxes](../assets/examples/learn-content-boxes-light.png#only-light)
![learn-content-boxes](../assets/examples/learn-content-boxes-dark.png#only-dark)

<!-- /@code-block-asset -->

A border uses one cell on each side of the content. `padding` accepts a number
of cells for all four sides. It also accepts a dictionary with the keys `top`,
`right`, `bottom`, `left`, `vertical` and `horizontal`.

A cell is about two times as tall as it is wide. Padding looks equal on all sides
when it has two columns for each row, as in the `thick` box.

## Layouts

By default, each piece of content on a canvas has its own position. A canvas
made with `layout='row'` puts the pieces side by side, from left to right, in
the order that you write them. Each piece gets an equal part of the width, and
`width='100%'` makes a piece fill its part. `layout='column'` does the same from
top to bottom.

<!-- @code-block name="learn-content-row" type="image" height=4 -->
```python
import xnano

with xnano.new(width=48, height=3, layout='row') as canvas:
    for name in ('logs', 'metrics', 'alerts'):
        canvas.write(name, border='rounded', width='100%')
    print(canvas.render(format='ansi'))
```

<!-- @code-block-asset name="learn-content-row" -->

![learn-content-row](../assets/examples/learn-content-row-light.png#only-light)
![learn-content-row](../assets/examples/learn-content-row-dark.png#only-dark)

<!-- /@code-block-asset -->

A piece with a `width` in cells keeps that width, and the other pieces share the
remaining space.

For a layout of your own, put a canvas in another canvas. If you make a canvas
in the `with` block of another canvas, xnano measures its size in the outer
canvas. For example, `'50%'` is half of the outer canvas. The inner canvas shows
only after you write it on the outer screen. Write it at the position where you
want it:

<!-- @code-block name="learn-content-nested" type="image" height=5 -->
```python
import xnano

with xnano.new(width=48, height=4) as window:
    with xnano.new(width='50%', height='100%', border='rounded', title='files') as files:  # >> [inner]
        files.write('notes.md')
        files.write('todo.md')
    window.write(files)  # >> [show]

    with xnano.new(  # >> [inner]
        width='50%', height='100%', border='rounded', title='preview'
    ) as preview:
        preview.write('# Notes')
    window.write(preview, x='50%', y=0)  # >> [show]

    print(window.render(format='ansi'))
```

<comments>
<tag name="inner" color="blue">
This canvas is half as wide as `window` and as tall as `window`. On
`xnano.new()`, `border` puts a box around the full inner canvas, and `title`
writes a title on that box.
</tag>

<tag name="show" color="pink">
The inner canvas shows on `window` only after this call. `x='50%'` puts
`preview` in the right half.
</tag>
</comments>

<!-- @code-block-asset name="learn-content-nested" -->

![learn-content-nested](../assets/examples/learn-content-nested-light.png#only-light)
![learn-content-nested](../assets/examples/learn-content-nested-dark.png#only-dark)

<!-- /@code-block-asset -->

[`Screen.new`][xnano.devices.Screen.new] makes an inner canvas and writes it at
the top-left corner in one call.

## Layers

xnano draws content on a higher `layer` over content on a lower layer. The
default layer is `0`. On the same layer, the content that you write last is on
top. Give a popup its own `background`, so that it looks separate from the
content below it.

<!-- @code-block name="learn-content-layers" type="image" height=6 -->
```python
import xnano

with xnano.new(width=40, height=5) as canvas:
    for row in range(5):
        canvas.write('the content underneath ' * 2, y=row, dim=True)
    canvas.write(
        'Saved',
        x='center',
        y='center',
        border='rounded',
        padding={'horizontal': 2},
        foreground='white',
        background='black',
        layer=1,
    )
    print(canvas.render(format='ansi'))
```

<!-- @code-block-asset name="learn-content-layers" -->

![learn-content-layers](../assets/examples/learn-content-layers-light.png#only-light)
![learn-content-layers](../assets/examples/learn-content-layers-dark.png#only-dark)

<!-- /@code-block-asset -->

## Change what you wrote

`write()` returns a placement. When you change a placement, the screen shows the
change on the next frame. You can also read the position and the size of a
placement, and use them to put other content next to it.

```python
import xnano

with xnano.new(width=30, height=4) as canvas:
    box = canvas.write('box', border='rounded')  # >> [write]
    assert (box.x, box.y, box.width, box.height) == (0, 0, 5, 3)

    box.move(5, 1)  # >> [move]
    assert (box.x, box.y) == (5, 1)

    box.x = 'right'  # >> [assign]
    box.text = 'moved'  # >> [assign]
    canvas.write('<- here', x=box.x - 8, y=box.y + 1)  # >> [read]

    box.is_visible = False  # >> [visible]
    box.is_visible = True
    print(canvas.render(format='ansi'))

    box.remove()  # >> [remove]
```

<comments>
<tag name="write">
`x`, `y`, `width` and `height` give the position and the size of the placement,
in cells. The border is part of the size.
</tag>

<tag name="move">
`move(5, 1)` moves the placement 5 columns to the right and 1 row down. A
negative number moves it to the left or up. `up()`, `down()`, `left()` and
`right()` move it in one direction.
</tag>

<tag name="assign">
You can set a position or the text directly, and a position accepts words and
percentages here too. New text changes the size of the placement to fit the
text, unless you gave the placement a size.
</tag>

<tag name="read">
A position reads back as a number of cells, also after you set a word. Use the
number to calculate the position of other content. The number does not change
when the placement moves later.
</tag>

<tag name="visible">
`is_visible = False` hides the placement, and `True` shows it again. A hidden
placement keeps its content and its position.
</tag>

<tag name="remove">
`remove()` removes the placement from the screen permanently. To show the
content again, write it again.
</tag>
</comments>

You can write more than text:

- A list of strings writes one line for each string.
- [Widgets](widgets.md), [images and pixel art](images.md) and other canvases
  use the same `write()` call.

The [`Screen.write`][xnano.devices.Screen.write] reference gives all the
keywords.

## Put content next to other content

`right_edge` is the first column after a placement, and `bottom_edge` is the
first row below it. Use them to put content directly to the right of a
placement, or directly below it.

```python
import xnano

with xnano.new(width=30, height=4) as canvas:
    card = canvas.write('card', border='rounded')
    assert (card.right_edge, card.bottom_edge) == (6, 3)  # >> [edges]
    canvas.write('● ready', x=card.right_edge + 1, y=card.y + 1, foreground='green')
    canvas.write('3 items', y=card.bottom_edge, dim=True)
    print(canvas.render(format='ansi'))
```

<comments>
<tag name="edges" color="blue">
`right_edge` is `x + width`, and `bottom_edge` is `y + height`. The card is 6
cells wide and 3 rows tall, because the border is part of its size.
</tag>
</comments>

A screen has the same two properties. For example, `canvas.screen.right_edge`
is the first column after the canvas.

## Ask what an area holds

`in` tells you if a cell or an area is inside another area. A cell is a pair of
numbers, `(column, row)`, on the screen. `overlaps()` tells you if two areas
have at least one cell in the same position. Areas that only touch at an edge do
not overlap.

```python
import xnano

with xnano.new(width=20, height=6) as canvas:
    basket = canvas.write('[___]', x=5, y=5)
    apple = canvas.write('o', x=7, y=3)
    assert (7, 3) in apple  # >> [cell]
    assert apple in canvas  # >> [area]
    assert not basket.overlaps(apple)

    apple.down(2)  # >> [overlap]
    assert basket.overlaps(apple)
```

<comments>
<tag name="cell" color="blue">
The cell in column 7 and row 3 is inside the apple.
</tag>

<tag name="area" color="green">
All of the apple is inside the canvas. `item in canvas` is the same as
`item in canvas.screen`.
</tag>

<tag name="overlap" color="pink">
The apple moves down 2 rows, to row 5. It then has a cell in the same position
as the basket.
</tag>
</comments>

A placement counts all of its cells, with its border, padding and margin. Its
mouse hooks receive the mouse in the same cells. A screen and a
[`Region`][xnano.layout.Region] accept `in` and `overlaps()` too, so you can
compare all of these areas with each other.
