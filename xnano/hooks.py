"""xnano.hooks

---

Single import location for every ``@on_*`` event hook decorator from
``xnano.events``. HTTP request hooks (``@on_get_request``,
``@on_post_request``, …) live in ``xnano.requests``.

Stable hook decorators are deprecated for removal in v1.2. Use
``xnano.beta.hooks``.

Example:

    ```python
    from xnano.hooks import on_keyboard, on_field
    ```
"""

from typing_extensions import deprecated

from xnano.events import (
    on_action,
    on_click,
    on_clipboard,
    on_event,
    on_field,
    on_focus,
    on_keyboard,
    on_mouse,
    on_poll,
    on_resize,
    on_state,
    on_tick,
)


@deprecated(
    "'xnano.hooks.Hooks' is deprecated and will be removed in v1.2; use "
    "the 'xnano.beta.hooks' module instead.",
    category=DeprecationWarning,
    stacklevel=2,
)
class Hooks:
    """Convenience class for accessing event hooks."""

    on_action = on_action
    on_click = on_click
    on_clipboard = on_clipboard
    on_event = on_event
    on_field = on_field
    on_focus = on_focus
    on_keyboard = on_keyboard
    on_mouse = on_mouse
    on_poll = on_poll
    on_resize = on_resize
    on_state = on_state
    on_tick = on_tick


__all__ = (
    "Hooks",
    "on_action",
    "on_click",
    "on_clipboard",
    "on_event",
    "on_field",
    "on_focus",
    "on_keyboard",
    "on_mouse",
    "on_poll",
    "on_resize",
    "on_state",
    "on_tick",
)
