---
title: "Sizing"
icon: "lucide/ruler"
---

# Sizing

`width=` and `height=` on any `Field` (and on `Terminal` itself) control how much space it occupies. All values go through the same resolution: fixed first, then percentages, then fractions divide up whatever's left.

---

## Fixed

```python
Field(default="Header", height=1)    # always 1 row
Field(default="Footer", height=3)    # always 3 rows
Field(default="Panel",  width=20)    # always 20 columns
```

---

## Percentage

```python
Field(default="Left",  width="25%")
Field(default="Right", width="75%")
```

Percentages are of the total available space before gaps are applied.

---

## Fractions

```python
Field(default="A", width="1fr")   # 1 share
Field(default="B", width="2fr")   # 2 shares — twice as wide as A
Field(default="C", width="1fr")   # 1 share
```

Fractions divide the space remaining after fixed and percentage fields are resolved. `"grow"` is an alias for `"1fr"`.

---

## Fit

```python
Field(default=Text("Hello"), width="fit")   # content width
Field(default=Text("Hello"), height="fit")  # content height
```

Measures the content and sizes accordingly. Useful for tab bars, status badges, anything whose natural size should drive its slot.

---

## Mixing

```python
class App(Grid, direction="vertical"):
    header: str = Field(default="Header", height=1)       # fixed
    body:   str = Field(default="Body",   height="1fr")   # fills rest
    footer: str = Field(default="Footer", height=3)       # fixed
```

```python
class Layout(Grid, direction="horizontal"):
    sidebar: str = Field(default="Sidebar", width="25%")
    main:    str = Field(default="Main",    width="1fr")
    aside:   str = Field(default="Aside",   width=20)
```

---

## Bounds

```python
Field(default="Nav", width="20%", min_width=15, max_width=40)
```

---

## On `Terminal`

```python
Terminal(width="fit",  height=10)    # fit width, 10-row inline block
Terminal(width="50%",  height="fit") # 50% of columns, fit height
```

!!! warning
    `Terminal(height="fit")` has no effect when the root is a `Grid`. xnano will warn you.
