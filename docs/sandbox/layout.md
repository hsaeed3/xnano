---
title: "Layout & Fields"
icon: "lucide/layout-grid"
---

# Layout & Fields Sandbox

These examples cover every grid layout setting and every `Field` option that
affects a static terminal frame. Styling-specific choices have their own
[Styling sandbox](styling.md).

## Grid Direction and Gap

Grid `direction` is `"vertical"` or `"horizontal"`; `gap` is a number of
terminal cells inserted between visible fields.

```pyodide install="xnano>=1.0.10" height="21"
from xnano import BaseGrid, Field, Terminal

direction = "horizontal"  # horizontal | vertical

class DirectionDemo(BaseGrid, direction=direction, gap=2, border="rounded", padding=1):
    first: str = Field(default="first", border="plain", align="center")
    second: str = Field(default="second", border="plain", align="center")
    third: str = Field(default="third", border="plain", align="center")

Terminal(width=64, height=9).render(DirectionDemo())
```

??? example "Grid Direction and Gap"

    - **`direction` options.** Use `"horizontal"` or `"vertical"`. See [Direction]{data-preview} and [GridSettings]{data-preview}.
    - **`gap` options.** Pass a non-negative terminal cell count. See [GridSettings]{data-preview}.

## Sizing

`width` and `height` accept fixed cells, a fractional float, a percentage,
ratio, fraction/fill weight, content sizing, or an explicit `Sizing` with
bounds.

| Form | Meaning |
|---|---|
| `12` or `"12"` | 12 cells |
| `0.5` or `"50%"` | 50 percent |
| `"1/3"` | ratio of available space |
| `"1fr"`, `"2fr"`, `"fill"`, `"grow"` | weighted leftover space |
| `"fit"`, `"auto"`, `"content"` | measured content size |
| `Sizing.fit(minimum=…, maximum=…)` | measured and clamped |

```pyodide install="xnano>=1.0.10" height="24"
from xnano import BaseGrid, Field, Terminal
from xnano._types import Sizing

class SizingDemo(BaseGrid, direction="horizontal", gap=1, border="double", padding=1):
    fixed: str = Field(default="12 cells", width=12, border="plain")
    ratio: str = Field(default="1/4", width="1/4", border="plain")
    weighted: str = Field(default="2fr", width="2fr", border="plain")
    fitted: str = Field(
        default="bounded fit",
        width=Sizing.fit(minimum=8, maximum=14),
        border="plain",
    )

Terminal(width=76, height=8).render(SizingDemo())
```

You can build the same values explicitly with `Sizing.cells()`, `.percent()`,
`.ratio()`, `.fraction()`, `.fit()`, and add clamps to any value with
`.with_bounds(minimum=..., maximum=...)`.

```pyodide install="xnano>=1.0.10" height="13"
from xnano._types import Sizing

sizes = [
    Sizing.cells(12),
    Sizing.percent(50),
    Sizing.ratio(1, 3),
    Sizing.fraction(2),
    Sizing.fit(minimum=4, maximum=20),
    Sizing.cells(40).with_bounds(maximum=16),
]
for size in sizes:
    print(size, "=>", size.resolve(available=60, content=9))
```

??? example "Sizing"

    - **`SizingLike` options.** [SizingLike]{data-preview} accepts an integer, float, string, or [Sizing]{data-preview}. Strings may be cell counts (`"12"`), percentages (`"50%"`), ratios (`"1/3"`), fraction weights (`"1fr"`, `"2fr"`, `"fill"`, `"grow"`), or intrinsic sizes (`"fit"`, `"auto"`, `"content"`).
    - **`SizingKind` options.** Normalized sizes use `"cells"`, `"percent"`, `"ratio"`, `"fraction"`, or `"fit"`. See [SizingKind]{data-preview}.
    - **`Sizing` constructors.** [Sizing]{data-preview} provides `cells()`, `percent()`, `ratio()`, `fraction()`, and `fit()`. Apply optional `minimum` and `maximum` clamps while constructing a fit size or through `with_bounds()`.

## Alignment

A field's main-axis size participates in the grid split. Its cross-axis size
shrinks the paint area inside that slot; `align` places it left, center, or
right. Vertical placement stays centered when a fixed height is smaller than
the slot.

```pyodide install="xnano>=1.0.10" height="22"
from xnano import BaseGrid, Field, Terminal

class AlignmentDemo(BaseGrid, direction="vertical", gap=1, border="rounded", padding=1):
    left: str = Field(default="left", width=18, height=1, align="left", background="red-900")
    center: str = Field(default="center", width=18, height=1, align="center", background="blue-900")
    right: str = Field(default="right", width=18, height=1, align="right", background="green-900")

Terminal(width=58, height=10).render(AlignmentDemo())
```

??? example "Cross-Axis Size and Alignment"

    - **`align` options.** Use `"left"`, `"center"`, `"right"`, or `None`. See [Alignment]{data-preview} and [Field]{data-preview}.

## Padding and Margin

Both accept an integer, `(vertical, horizontal)`, `(top, right, bottom, left)`,
or a `Padding` object. `None` inside a four-tuple is treated as zero. Padding
insets content inside its frame; margin insets the whole field within its slot.

```pyodide install="xnano>=1.0.10" height="22"
from xnano import BaseGrid, Field, Terminal
from xnano._types import Padding

class SpacingDemo(BaseGrid, direction="horizontal", gap=1, border="double"):
    scalar: str = Field(default="padding=1", padding=1, border="plain")
    pair: str = Field(default="(1, 3)", padding=(1, 3), border="rounded")
    four: str = Field(
        default="four sides",
        padding=(0, 2, 1, 4),
        margin=Padding(top=1, right=1, bottom=0, left=1),
        border="thick",
    )

Terminal(width=76, height=10).render(SpacingDemo())
```

??? example "Padding and Margin Forms"

    - **`padding` options.** Pass one integer for every side, `(vertical, horizontal)`, `(top, right, bottom, left)`, or a [Padding]{data-preview}. Four-tuples may use `None` for a zero-valued side. See [PaddingLike]{data-preview}.
    - **`margin` options.** Pass one integer for every side, `(vertical, horizontal)`, `(top, right, bottom, left)`, or a [Padding]{data-preview}. Four-tuples may use `None` for a zero-valued side. See [PaddingLike]{data-preview}.

## Nested Grids and Field Direction

Grids can be field values. A field can also provide `direction` and `gap` for
multi-value content; a nested grid is usually clearer when children need their
own fields or state.

```pyodide install="xnano>=1.0.10" height="25"
from xnano import BaseGrid, Field, Terminal

class Sidebar(BaseGrid, direction="vertical", gap=1, border="rounded", title="nav"):
    home: str = Field(default="Home", height=1)
    search: str = Field(default="Search", height=1)
    settings: str = Field(default="Settings", height=1)

class App(BaseGrid, direction="horizontal", gap=2, border="double", title="nested grids", padding=1):
    sidebar: Sidebar = Field(default_factory=Sidebar, width="1/3")
    content: list[str] = Field(
        default_factory=lambda: ["overview", "metrics", "activity"],
        direction="vertical",
        gap=1,
        width="2fr",
        border="plain",
        title="content",
    )

Terminal(width=72, height=13).render(App())
```

??? example "Nested Grids and Field Direction"

    - **Nested layout options.** Use `"horizontal"` or `"vertical"` for [Direction]{data-preview}, non-negative cell counts for `gap`, and any [SizingLike]{data-preview} value for field width or height. See [Field]{data-preview} and [GridSettings]{data-preview}.

## Visibility, Defaults, Init, and State

`visible=False` removes a layout field from the frame; `visible=None` makes
visibility dynamic (`None` values are hidden). `default` and `default_factory`
provide values. `init=False` omits a field from the generated constructor.
`state=True` stores application data without creating a layout slot, and
`strict=True` validates assignments to that state field.

```pyodide install="xnano>=1.0.10" height="22"
from xnano import BaseGrid, Field, Terminal

class FieldModes(BaseGrid, direction="vertical", gap=1, border="rounded", padding=1):
    defaulted: str = Field(default="static default", height=1)
    factory: str = Field(default_factory=lambda: "factory default", height=1)
    hidden: str = Field(default="you cannot see me", visible=False, init=False)
    optional: str | None = Field(default=None, visible=None)
    count: int = Field(default=2, state=True, strict=True)

demo = FieldModes()
demo.optional = f"state count = {demo.count}"
Terminal(width=52, height=9).render(demo)
```

Grid classes also accept `strict=False` to disable constructor validation for
all declared values. A grid instance's own `visible` and `z` attributes control
whether it paints and its stacking order; `columns` and `rows` are populated by
the renderer for the current frame.

??? example "Visibility, Defaults, Init, and State"

    - **`default` options.** Pass the field's static initial value. It is mutually exclusive with `default_factory`. See [Field]{data-preview}.
    - **`default_factory` options.** Pass a zero-argument callable that creates the initial value. It is mutually exclusive with `default`. See [Field]{data-preview}.
    - **`state` options.** Use `True` for application state without a layout slot or `False` for a rendered field. See [Field]{data-preview}.
    - **`strict` options.** Use `True` to validate assignments or `False` for normal assignment behavior. See [Field]{data-preview}.
    - **`init` options.** Use `True` to include the field in the generated constructor or `False` to omit it. See [Field]{data-preview}.
    - **`visible` options.** `True` always paints, `False` never paints, and `None` derives visibility from whether the value is `None`. See [Field]{data-preview}.

## Sliding Metadata in WASM

`slide=("x",)`, `("y",)`, or `("x", "y")` marks a field as draggable in a
live mouse-enabled terminal. Pyodide can construct and render that grid—and can
dispatch synthetic actions—but it has no continuous device polling loop. This
runnable cell shows the accepted declarations and resulting metadata.

```pyodide install="xnano>=1.0.10" height="20"
from xnano import BaseGrid, Field, Terminal

class Sliding(BaseGrid, border="rounded", title="slide metadata"):
    card: str = Field(
        default="drag on x + y in a live terminal",
        width=34,
        height=3,
        slide=("x", "y"),
        border="plain",
        align="center",
    )

print("slide axes:", Sliding._grid_fields["card"].slide)
Terminal(width=52, height=8).render(Sliding())
```

??? example "Sliding Metadata in WASM"

    - **`slide` options.** `slide` accepts a sequence containing `"x"`, `"y"`, or both, while `None` disables sliding. This metadata and every other field declaration option are documented on [Field]{data-preview}.

[Direction]: ../api/xnano/_types.md#xnano._types.Direction
[Alignment]: ../api/xnano/_types.md#xnano._types.Alignment
[PaddingLike]: ../api/xnano/_types.md#xnano._types.PaddingLike
[SizingLike]: ../api/xnano/_types.md#xnano._types.SizingLike
[SizingKind]: ../api/xnano/_types.md#xnano._types.SizingKind
[Padding]: ../api/xnano/_types.md#xnano._types.Padding
[Sizing]: ../api/xnano/_types.md#xnano._types.Sizing
[Field]: ../api/xnano/fields.md#xnano.fields.Field
[GridSettings]: ../api/xnano/grid.md#xnano.grid.GridSettings
