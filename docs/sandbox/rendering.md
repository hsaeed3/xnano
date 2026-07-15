---
title: "Rendering"
icon: "lucide/terminal"
---

# Rendering Sandbox

This page covers every option on [`xnano.render()`][render] and the additional
static-rendering controls on [`Terminal.render()`][terminal]. All examples are
single-frame or buffer-backed and are safe in Pyodide.

## Render Style and Frame

One call below exercises every content/style keyword shared by `render()` and
`Terminal.render()`: `direction`, `color`, `background`, `modifiers`, `align`,
`border`, `border_sides`, `border_color`, `title`, `title_position`, and
`padding`.

```pyodide install="xnano>=1.0.10" height="18"
from xnano import render

direction = "horizontal"       # horizontal | vertical
align = "center"               # left | center | right | None
border = "rounded"             # see the Styling sandbox for every style
border_sides = ["top", "bottom", "left", "right"]

render(
    "alpha",
    "beta",
    direction=direction,
    color="amber-300",
    background="#312e81",
    modifiers=("bold", "underline"),
    align=align,
    border=border,
    border_sides=border_sides,
    border_color="violet-400",
    title="render frame",
    title_position="bottom",   # top | bottom | None
    padding=(1, 3),             # all | (vertical, horizontal) | four sides
    sep="  ·  ",
)
```

??? example "Render Style and Frame"

    - **`direction` options.** Use `"horizontal"` or `"vertical"`. See [Direction]{data-preview}.
    - **`align` options.** Use `"left"`, `"center"`, `"right"`, or `None`. See [Alignment]{data-preview}.
    - **`border` options.** Use `"plain"`, `"rounded"`, `"double"`, `"thick"`, `"quadrant_inside"`, `"quadrant_outside"`, or `None`. See [Border]{data-preview}.
    - **`border_sides` options.** Pass any sequence of `"top"`, `"bottom"`, `"left"`, and `"right"`. See [Side]{data-preview}.
    - **`modifiers` options.** Pass any sequence of `"bold"`, `"dim"`, `"italic"`, `"underline"`, `"slow_blink"`, `"rapid_blink"`, and `"reversed"`. See [CharacterModifier]{data-preview}.
    - **`title_position` options.** Use `"top"`, `"bottom"`, or `None`. See [FrameTitlePosition]{data-preview}.
    - **`color` options.** Pass a named, Tailwind, hexadecimal, RGB tuple, or `Color` value, or use `None`. See [ColorLike]{data-preview}.
    - **`background` options.** Pass a named, Tailwind, hexadecimal, RGB tuple, or `Color` value, or use `None`. See [ColorLike]{data-preview}.
    - **`border_color` options.** Pass a named, Tailwind, hexadecimal, RGB tuple, or `Color` value, or use `None`. See [ColorLike]{data-preview}.
    - **`padding` options.** Pass one integer, `(vertical, horizontal)`, `(top, right, bottom, left)`, a `Padding`, or `None`. See [PaddingLike]{data-preview}.

## Multiple Values and Direction

`direction="horizontal"` places values beside one another and uses `sep` as
the column gap. `direction="vertical"` stacks their rendered blocks.

```pyodide install="xnano>=1.0.10" height="13"
from xnano import render

render("one", "two", "three", direction="horizontal", sep=" | ")
render("one", "two", "three", direction="vertical")
```

??? example "Multiple Values and Direction"

    - **`direction` options.** `"horizontal"` joins rendered rows and `"vertical"` stacks rendered blocks. See [Direction]{data-preview} and the full [render]{data-preview} API.

## Print-Compatible Options

`sep`, `end`, `file`, and `flush` match `print()`. A non-stdout `file` always
uses the text/ANSI path, which makes captured output useful in tests and logs.
`None` for `sep` or `end` restores xnano's normal default.

```pyodide install="xnano>=1.0.10" height="15"
import io

from xnano import render

capture = io.StringIO()
render(
    "left",
    "right",
    direction="horizontal",
    color="cyan",
    sep=" <-> ",
    end=" [done]",
    file=capture,
    flush=True,
)

print("Captured repr:", repr(capture.getvalue()))
```

??? example "Print-Compatible Options"

    - **`sep` options.** Pass a string separator, or `None` to restore xnano's default. See [render]{data-preview}.
    - **`end` options.** Pass a string ending, or `None` to restore xnano's default. See [render]{data-preview}.
    - **`file` options.** Pass a writable text stream, or `None` for standard output. See [render]{data-preview}.
    - **`flush` options.** Use `True` to flush the destination after writing or `False` to leave it buffered. See [render]{data-preview}.

## Append and Replace Streams

Set `stream=True` for the default stream or pass a name. Calls append unless
`update=True`, which replaces that stream's complete current value. `stream`
and `update` are also accepted by `Terminal.render()`.

```pyodide install="xnano>=1.0.10" height="16" session="render-streams"
from xnano import render
from xnano._renderable import clear_stream, get_stream_content

clear_stream("download")
render("chunk 1", stream="download", end="\n")
render("chunk 2", stream="download", end="\n")
print("After append:", repr(get_stream_content("download")))

render("complete", stream="download", update=True, end="\n")
print("After update:", repr(get_stream_content("download")))
```

??? example "Append and Replace Streams"

    - **`stream` options.** Use `None` to disable stream storage, `True` for the default stream, or a string for a named stream. See [render]{data-preview} and [Terminal.render]{data-preview}.
    - **`update` options.** `False` appends to the selected stream; `True` replaces its current content. See [render]{data-preview} and [Terminal.render]{data-preview}.

## Terminal Viewport and Gap

`Terminal.render()` adds `gap` between native renderables. `Terminal` itself
accepts `width` and `height` using the same sizing grammar as fields. Fixed
cell sizes are the most predictable browser viewport; `fit` measures ordinary
content, while a grid root uses the available buffer.

```pyodide install="xnano>=1.0.10" height="18"
from xnano import Terminal
from xnano.components.text import Text

terminal = Terminal(
    title="Pyodide frame",       # session/window title metadata
    width=52,                     # cells; also accepts %, ratio, fr, fit
    height=9,
    tick_interval=16,             # used by a live loop, harmless here
    mouse_events=False,
    bracketed_paste=False,
    synchronized_updates=False,
    debug_wireframe=False,
)
terminal.render(
    Text("first", color="cyan"),
    Text("second", color="amber-300"),
    direction="vertical",
    gap=1,
    border="double",
    title="Terminal.render",
    padding=1,
)
```

The three live-device flags and `tick_interval` configure a live OS session;
they do not create browser input polling. `state`, `title`, `width`, `height`,
and `debug_wireframe` are also accepted by `Terminal.offscreen()` where
applicable.

??? example "Terminal Viewport and Gap"

    - **`width` options.** Pass any [SizingLike]{data-preview} value to size the terminal viewport horizontally. See the [Terminal class]{data-preview}.
    - **`height` options.** Pass any [SizingLike]{data-preview} value to size the terminal viewport vertically. See the [Terminal class]{data-preview}.
    - **`tick_interval` options.** Pass the live-loop interval in milliseconds as an integer. See the [Terminal class]{data-preview}.
    - **`mouse_events` options.** Use `True` to request mouse capture in a live terminal or `False` to disable it. See the [Terminal class]{data-preview}.
    - **`bracketed_paste` options.** Use `True` to request bracketed-paste mode in a live terminal or `False` to disable it. See the [Terminal class]{data-preview}.
    - **`synchronized_updates` options.** Use `True` to request synchronized terminal updates or `False` to disable them. See the [Terminal class]{data-preview}.
    - **`debug_wireframe` options.** Use `True` to paint layout diagnostics or `False` for normal rendering. See the [Terminal class]{data-preview}.
    - **`gap` options.** Pass an integer cell count between native renderables. See [Terminal.render]{data-preview}.

## Explicit Offscreen Buffer

`Terminal.offscreen()` exposes exact `cols` and `rows`, the rendered plain
text, and ANSI-preserving output. This is the lowest-level WASM-safe terminal
surface.

```pyodide install="xnano>=1.0.10" height="20"
from xnano import Terminal

terminal = Terminal.offscreen(
    cols=46,
    rows=7,
    state={"source": "sandbox"},
    title="offscreen",
    debug_wireframe=False,
)
try:
    terminal.render(
        "buffer-backed",
        color="emerald-300",
        border="thick",
        border_color="emerald-500",
        title="46 × 7",
        padding=1,
    )
    print(terminal.get_output_as_ansi())
finally:
    terminal.__exit__(None, None, None)
```

??? example "Explicit Offscreen Buffer"

    - **`cols` options.** Pass the offscreen buffer width as an exact integer cell count. See [Terminal.offscreen]{data-preview}.
    - **`rows` options.** Pass the offscreen buffer height as an exact integer cell count. See [Terminal.offscreen]{data-preview}.
    - **`state` options.** Pass any application-state object or omit it. See [Terminal.offscreen]{data-preview}.
    - **`title` options.** Pass terminal title metadata as a string or omit it. See [Terminal.offscreen]{data-preview}.
    - **Offscreen `debug_wireframe` options.** Use `True` to paint layout diagnostics or `False` for normal rendering. See [Terminal.offscreen]{data-preview}.

## Action-Driven Frames Without `run()`

Synthetic actions use the same dispatch path as live input. Render a grid once
to attach its hooks, perform an action, and render the changed state again.
This gives browser examples real behavior without starting an OS event loop.

```pyodide install="xnano>=1.0.10" height="24"
from xnano import Action, BaseGrid, Field, Terminal, on_action

INCREMENT = Action.keyboard("right")

class Counter(BaseGrid, border="rounded", title="synthetic action", padding=1):
    label: str = Field(default="count: 0", align="center")
    count: int = Field(default=0, state=True)

    @on_action(INCREMENT)
    def increment(self) -> None:
        self.count += 1
        self.label = f"count: {self.count}"

counter = Counter()
terminal = Terminal.offscreen(cols=42, rows=7)
try:
    terminal.render(counter)       # attaches hooks and paints frame zero
    terminal.perform(INCREMENT)    # synthetic input; no polling loop
    terminal.perform(INCREMENT)
    terminal.render(counter)       # paints the mutated frame
    print(terminal.get_output_as_ansi())
finally:
    terminal.__exit__(None, None, None)
```

??? example "Action-Driven Frames Without `run()`"

    - **Action options.** `Action.keyboard()` accepts a key-binding string such as `"right"`; `Terminal.perform()` dispatches the resulting action without polling. See [Action]{data-preview} and [Terminal.perform]{data-preview}.

!!! warning "WASM boundary"

    Do not replace these calls with `Terminal.run()`. xnano will
    intentionally raise an error as `run()` requires ownership of a live OS terminal.

[render]: ../api/xnano/_renderable.md
[terminal]: ../api/xnano/tui/terminal.md
[Direction]: ../api/xnano/_types.md#xnano._types.Direction
[Alignment]: ../api/xnano/_types.md#xnano._types.Alignment
[Border]: ../api/xnano/_types.md#xnano._types.Border
[Side]: ../api/xnano/_types.md#xnano._types.Side
[CharacterModifier]: ../api/xnano/_types.md#xnano._types.CharacterModifier
[FrameTitlePosition]: ../api/xnano/_types.md#xnano._types.FrameTitlePosition
[PaddingLike]: ../api/xnano/_types.md#xnano._types.PaddingLike
[SizingLike]: ../api/xnano/_types.md#xnano._types.SizingLike
[ColorLike]: ../api/xnano/color.md#xnano.color.ColorLike
[Terminal class]: ../api/xnano/tui/terminal.md#xnano.tui.terminal.Terminal
[Terminal.render]: ../api/xnano/tui/terminal.md#xnano.tui.terminal.Terminal.render
[Terminal.offscreen]: ../api/xnano/tui/terminal.md#xnano.tui.terminal.Terminal.offscreen
[Action]: ../api/xnano/core/actions.md#xnano.core.actions.Action
[Terminal.perform]: ../api/xnano/tui/terminal.md#xnano.tui.terminal.Terminal.perform
