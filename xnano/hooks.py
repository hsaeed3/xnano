"""xnano.hooks

---

Single import location for every ``@on_*`` event hook decorator from
``xnano.events``. HTTP request hooks (``@on_get_request``,
``@on_post_request``, …) live in ``xnano.requests``.

Example:

    ```python
    from xnano.hooks import on_keyboard, on_field
    ```
"""

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
