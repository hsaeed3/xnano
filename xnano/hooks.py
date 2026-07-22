"""xnano.hooks

---

Single import location for every hook decorator: the ``@on_*`` event
hooks from ``xnano.events`` and the web request hooks from
``xnano.web.requests``.

Example:

    ```python
    from xnano.hooks import on_keyboard, on_field, on_get_request
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
from xnano.web.requests import (
    on_get_request,
    on_post_request,
)

__all__ = (
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
    "on_get_request",
    "on_post_request",
)
