# Hooks and Actions

Hooks are decorators on methods of a `BaseGrid` subclass. A handler may be
defined as `method(self)` or `method(self, ctx)`; `ctx` is the current
`Context`, including event data, shared state, runtime controls, focus, stage,
and viewport information.

## Event hooks

Use the narrowest hook that expresses the behavior:

- `@on_keyboard("ctrl+s", kind="press")` for key bindings.
- `@on_mouse(button="left", kind="press", field="name")` for mouse events.
- `@on_click("name")` or `@on_click(group="toolbar")` for activation.
- `@on_focus(field=..., group=..., kind="gained"|"lost")` for focus changes.
- `@on_clipboard`, `@on_resize`, and `@on_event` for their corresponding events.
- `@on_tick(1000)` for periodic work in milliseconds.
- `@on_poll(when="idle"|"frame")` for polling at the selected runtime point.

Keyboard and mouse filters accept multiple bindings/buttons where supported.
Enable `Terminal(mouse_events=True)` when clicks, drags, hover, or wheel input
must be received; mouse capture is off by default.

## State and field watchers

`@on_state("count > 0")` fires while the expression is truthy against shared
state. A bare reference such as `@on_state("count")` fires when that value
changes. `@on_field` applies the same rule to fields on the grid:

```python
@on_field("count")
def refresh_label(self):
    self.label = f"Count: {self.count}"
```

Keep watcher work small and idempotent; mutations can cause another render.

## Actions

Use `Action` when the trigger should be named, reused, or synthesized:

```python
from xnano import Action
from xnano.hooks import on_action

SAVE = Action.keyboard("ctrl+s")


@on_action(SAVE)
def save(self, ctx):
    ...
```

Available action constructors cover keyboard, mouse, click, focus, clipboard,
tick, resize, and request events. Runtime code can synthesize supported input
with `ctx.actions` or `terminal.actions`; event matching remains centralized in
`Action.matches`.

Prefer one hook per behavior. Do not mix HTTP request handling with terminal
event hooks; use the request decorators described in [server](server.md).
