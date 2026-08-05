# Components

## Use built-ins first

Import built-ins from their concrete modules inside library code. The main
families are:

- `Text`, `Input`, and `Markdown` for text and editing.
- `Button`, `Link`, `Dropdown`, and `Options`/`Select` for interaction.
- `Table`, `Chart`, `Bar`, `Loader`, `Scrollbar`, and `Image` for data and
  feedback.

Check the component's module and tests before inventing a wrapper. Components
are dataclasses with live attributes; changing an attribute changes the next
frame.

## Custom components

Subclass `Component` and implement the smallest relevant method:

```python
from xnano.components.component import Component, ComponentRenderContext
from xnano.core.content import TextBlock


class Status(Component):
    text: str = "Ready"

    def compose(self, ctx: ComponentRenderContext) -> TextBlock:
        return TextBlock(text=self.text)
```

`compose()` returns interface-neutral `Content` or `None`. Use
`ComponentRenderContext` for the assigned area, runtime, state, and component.
Use `get_size()` when natural size matters, `before_render()`/`after_render()`
for paint hooks, and `handle_keyboard()` or `handle_paste()` only for focused
interactive behavior. The `focused`, `visible`, and `z` attributes are runtime
state; `fit_content` controls natural-size preference.

For responsive components, override only the needed `compose_extra_small`,
`compose_small`, `compose_medium`, `compose_large`, or `compose_extra_large`
variant. Keep shared logic in `compose()`.

Use `Field` to place a component in a grid. Components do not own terminal
initialization, event polling, or HTTP serving.
