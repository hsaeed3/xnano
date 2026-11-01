---
title: Images & Pixel Art
icon: lucide/image
---

# Images & Pixel Art

xnano draws pictures in terminal cells. Pixel art is written as text, right in
your code, and comes with the core package. Loading picture files needs the
`image` extra from [Installation](installation.md#optional-extras).

## Pixel art

`xnano.pixel_art()` paints rows of text, one character per pixel. The `palette`
says what color each character is, and any character it doesn't name, such as
`.`, is transparent.

<!-- @code-block name="learn-images-pixel-art" type="image" height=4 -->
```python
import xnano

heart = xnano.pixel_art(
    """
    .RR.RR.
    RRRRRRR
    RRRRRRR
    .RRRRR.
    ..RRR..
    ...R...
    """,
    palette={'R': '#e03050'},
)

with xnano.new(width=20, height=4) as canvas:
    canvas.screen.write(heart, x='center')
    print(canvas.screen.render(format='ansi'))
```

Each cell holds two pixels, one above the other, so this heart of 7 by 6 pixels
takes 7 columns and 3 rows. Art is a value like a string: make it once, and
write it as many times, in as many places, as you like.

A palette can also be one string of `character=color` pairs, which reads well
for small sprites:

<!-- @code-block name="learn-images-palette" type="image" height=3 -->
```python
import xnano

ship = xnano.pixel_art(
    """
    ...W...
    ..WBW..
    .WBBBW.
    WWBBBWW
    W.R.R.W
    """,
    palette='W=white B=#5a85ff R=#e8768a',
)

with xnano.new(width=20, height=3) as canvas:
    canvas.screen.write(ship)
    print(canvas.screen.render(format='ansi'))
```

`encoding='braille'` packs two by four pixels into each cell, in one color, for
a finer, drawing-like look.

## Pictures

`xnano.load_image()` reads PNG, JPEG, GIF, WebP and XNI files. Its `width` and
`height` take cells or a percentage, and when you give only one, the other keeps
the picture's proportions. Write the result like anything else.

```python
import xnano

with xnano.open() as terminal:
    picture = xnano.load_image('photo.png', width='100%')
    terminal.screen.write(picture)
    terminal.run(stop_on='q')
```

A picture sized by a percentage is sized again when the window is resized. An
animated GIF or WebP plays on the canvas's clock, so pausing the clock pauses it
too, and `speed=2.0` plays it twice as fast.

## Printing without a terminal

`xnano.region()` draws content into cells with no canvas at all, ready to print.
This one uses the picture that ships with xnano, so it runs anywhere the `image`
extra is installed:

<!-- @code-block name="learn-images-region" type="image" height=15 -->
```python
import pathlib

import xnano

path = pathlib.Path(xnano.__file__).parent / 'assets' / 'dusk.png'
picture = xnano.load_image(path, width=48)
print(xnano.region(picture).render(format='ansi'))
```

The [`xnano.art`][xnano.art] reference covers the rest: cameras that look into
larger pixel worlds, single pixels, and how images are fitted and resampled.
