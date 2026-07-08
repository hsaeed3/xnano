---
title: "Sizing"
icon: "lucide/ruler"
---

# Sizing

`width=` and `height=` on any `Field` (and on `Terminal` itself) control how much space it occupies. All values go through the same resolution pipeline: fixed amounts are allocated first, then percentages, then fractions divide up what's left.

---

## Fixed

Fixed sizes are integers — rows for `height`, columns for `width`. They are allocated before any other field, regardless of the terminal dimensions. Use them for things that have a known height: status bars, headers, footers, single-line labels.

```python
Field(default="Header", height=1)    # always 1 row
Field(default="Footer", height=3)    # always 3 rows
Field(default="Panel",  width=20)    # always 20 columns
```

---

## Percentage

Percentages are strings like `"25%"`. They are computed from the total available space after gaps are subtracted, before fixed fields are removed. Two fields at `"50%"` each split the space evenly; if you also have fixed fields on the same axis, percentages are taken from the total and may over-allocate — be careful when mixing.

```python
Field(default="Left",  width="25%")
Field(default="Right", width="75%")
```

---

## Fractions

Fractions are strings like `"1fr"` or `"2fr"`. After fixed and percentage fields are resolved, the remaining space is divided among fraction fields proportionally. A field with `"2fr"` gets twice the space of a field with `"1fr"`. `"grow"` is a shorthand alias for `"1fr"`.

```python
Field(default="A", width="1fr")   # 1 share
Field(default="B", width="2fr")   # 2 shares — twice as wide as A
Field(default="C", width="1fr")   # 1 share
```

---

## Fit

`"fit"` measures the field's content and sizes the field to exactly that width or height. It's useful for items whose natural size should drive the layout: a tab bar where tabs vary in length, a badge that wraps a label, a panel that shows a fixed-size chart.

```python
Field(default=Text("Hello"), width="fit")   # content width
Field(default=Text("Hello"), height="fit")  # content height
```

---

## Mixing units on the same axis

You can combine all four units in a single grid. The resolution order is always: fixed → fit → percentage → fractions. This means fractions always absorb the true remainder after everything else is placed.

```python title="Mixing all units — vertical"
class App(Grid, direction="vertical", gap=1):
    header:  str = Field(default="  fixed: height=1",     height=1,     color="white", background="violet-900")
    quarter: str = Field(default="  percent: height=25%", height="25%", border="rounded", border_color="sky-500")
    fill:    str = Field(default="  fraction: height=1fr", height="1fr", border="rounded", border_color="teal-500")
    footer:  str = Field(default="  fixed: height=2",     height=2,     color="white", background="violet-900")
```

<div class="xnano-demo" markdown>
![sizing mix dark](../../assets/concepts/sizing_mix-dark.gif){.demo-dark}
![sizing mix light](../../assets/concepts/sizing_mix-light.gif){.demo-light}
</div>

A common pattern is a fixed header and footer with a fraction-filled body:

```python
class Layout(Grid, direction="vertical"):
    header: str = Field(default="Header", height=1)       # fixed
    body:   str = Field(default="Body",   height="1fr")   # fills rest
    footer: str = Field(default="Footer", height=3)       # fixed
```

And a sidebar layout with a fixed aside column:

```python
class Layout(Grid, direction="horizontal"):
    sidebar: str = Field(default="Sidebar", width="25%")
    main:    str = Field(default="Main",    width="1fr")
    aside:   str = Field(default="Aside",   width=20)
```

---

## Bounds

You can clamp a field's size with `min_width`, `max_width`, `min_height`, and `max_height`. This is especially useful for percentage and fraction fields that should not shrink below a usable size.

```python
Field(default="Nav", width="20%", min_width=15, max_width=40)
```

---

## On `Terminal`

`Terminal` also accepts `width=` and `height=`. These apply to the inline rendering area in `render()` mode, not to the alternate screen used by `run()`.

```python
Terminal(width="fit",  height=10)    # fit width, 10-row inline block
Terminal(width="50%",  height="fit") # 50% of columns, fit height
```

!!! warning
    `Terminal(height="fit")` has no effect when the root is a `Grid`. Grids always fill the alternate screen. xnano will warn you if you combine them.
