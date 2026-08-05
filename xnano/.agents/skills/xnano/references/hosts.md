# Hosts and Rendering

## One-shot rendering

Use `from xnano import render` for print-like output with no event loop. It is
not a terminal host and does not dispatch hooks.

## Terminal

`Terminal` owns a `Runtime` and selects a live session when a usable TTY is
available; otherwise it uses an offscreen session. Use `Terminal.offscreen(cols,
rows, state=...)` in tests and inspect the returned immutable `Frame` (`text`,
`ansi`, `width`, `height`, `rows`, and `contains()`).

```python
from xnano.terminal import Terminal

terminal = Terminal.offscreen(cols=40, rows=12)
frame = terminal.render("Ready")
terminal.close()
```

Use `with Terminal(...) as terminal` for live ownership. `Terminal.run(...)`
paints and pumps events until exit. It does not accept `host` or `port`.
`Runtime` is the lower-level choice when explicit session ownership, state,
focus, cursor, device, actions, or stage access is required.

Never initialize or restore crossterm directly in application code.

## Web

`Web` serves the same grid/component through an offscreen runtime and the
native cell-frame browser server:

```python
from xnano.web import Web

Web(title="Status", width=80, height=24).run(App, port=8000)
```

`Web.run()` accepts a grid/component instance, a `BaseGrid` class, or a factory.
The shared DSL and hook dispatch are reused; only presentation and input
transport differ. Web request routes are handled by `xnano.server`.

Keep rendering policy in grids/components, frame lowering in
`TerminalController`/`xnano.core`, and session mechanics in `Runtime` and
`xnano-core`.
