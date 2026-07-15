---
title: "Hooks & Actions"
icon: "lucide/webhook"
---

# Hooks & Actions

Hooks are where a grid starts listening. Put an `@on_*` decorator on a method and xnano calls it when the matching event reaches that grid. Actions describe the other half of the exchange: a trigger you can name, reuse, and perform from code.

The specialized hooks are usually the nicest place to begin. `@on_keyboard("escape")` says exactly what it listens for; `@on_action(CLOSE)` becomes useful when that same trigger belongs in several places or needs to be emitted without a physical key press.

| Hook | What wakes it up | Associated action |
|---|---|---|
| [`@on_action`](on.md) | A reusable action | The action passed to it |
| [`@on_event`](on-event.md) | Any terminal event | — |
| [`@on_keyboard`](on-keyboard.md) | Key press, release, or repeat | `Action.keyboard(...)` |
| [`@on_mouse`](on-mouse.md) | Mouse input and movement | `Action.mouse(...)` |
| [`@on_click`](on-click.md) | A click in a field | `Action.click(...)` |
| [`@on_tick`](on-tick.md) | The host clock | `Action.tick(...)` |
| [`@on_resize`](on-resize.md) | Terminal resize | `Action.resize(...)` |
| [`@on_focus`](on-focus.md) | Window or field focus | `Action.focus(...)` |
| [`@on_clipboard`](on-clipboard.md) | Clipboard paste | `Action.clipboard(...)` |
| [`@on_state`](on-state.md) | A true shared-state expression | — |
| [`@on_field`](on-field.md) | A true grid-field expression | — |
| [`@on_poll`](on-poll.md) | An idle wait or every frame | — |

Web grids add request hooks of their own: [`@on_get_request`](web-requests/get.md) and [`@on_post_request`](web-requests/post.md).

## One Dispatch Path

A real event and a performed action meet the same hook. That makes actions particularly handy in tests, integrations, and browser examples where starting a live terminal loop would be the wrong shape of program.

??? example "Interactive Example"

    The following example performs an action and paints the resulting frame directly — no keyboard polling or `Terminal.run()` required.

    ```pyodide install="xnano>=1.0.10" height="24" hl_lines="3 9 16"
    from xnano import Action, BaseGrid, Field, Terminal, on_action

    OPEN = Action.keyboard("enter")

    class Notice(BaseGrid, border="rounded", title=" action ", padding=1):
        message: str = Field(default="closed", align="center")

        @on_action(OPEN)
        def open_notice(self) -> None:
            self.message = "open"

    notice = Notice()
    terminal = Terminal.offscreen(cols=36, rows=7)
    try:
        terminal.render(notice)
        terminal.perform(OPEN)
        terminal.render(notice)
        print(terminal.get_output_as_ansi())
    finally:
        terminal.__exit__(None, None, None)
    ```

<div class="xnano-demo" markdown>
![hooks and actions dark](../assets/hooks/overview-dark.gif){.demo-dark}
![hooks and actions light](../assets/hooks/overview-light.gif){.demo-light}
</div>

??? abstract "API"

    [`events`](../api/xnano/events.md){data-preview} · [`Action`](../api/xnano/core/actions.md#xnano.core.actions.Action){data-preview} · [`Context`](../api/xnano/context.md#xnano.context.Context){data-preview}
