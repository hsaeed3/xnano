"""xnano

>>> import xnano.beta as x
>>> from xnano.beta import Grid, Field, Terminal
"""

__version__ = "1.0.0"

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xnano.context import Context
    from xnano.fields import Field
    from xnano.grid import Grid, GridSettings
    from xnano.hooks import (
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
    from xnano.terminal import Terminal


__all__ = (
    "Context",
    "Field",
    "Grid",
    "GridSettings",
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
    "Terminal",
)


def __getattr__(name: str):
    if name == "Context":
        from xnano.context import Context

        return Context

    elif name == "Field":
        from xnano.fields import Field

        return Field

    elif name == "Grid":
        from xnano.grid import Grid

        return Grid

    elif name == "GridSettings":
        from xnano.grid import GridSettings

        return GridSettings

    elif name == "on_click":
        from xnano.hooks import on_click

        return on_click

    elif name == "on_clipboard":
        from xnano.hooks import on_clipboard

        return on_clipboard

    elif name == "on_event":
        from xnano.hooks import on_event

        return on_event

    elif name == "on_field":
        from xnano.hooks import on_field

        return on_field

    elif name == "on_focus":
        from xnano.hooks import on_focus

        return on_focus

    elif name == "on_keyboard":
        from xnano.hooks import on_keyboard

        return on_keyboard

    elif name == "on_mouse":
        from xnano.hooks import on_mouse

        return on_mouse

    elif name == "on_poll":
        from xnano.hooks import on_poll

        return on_poll

    elif name == "on_resize":
        from xnano.hooks import on_resize

        return on_resize

    elif name == "on_state":
        from xnano.hooks import on_state

        return on_state

    elif name == "on_tick":
        from xnano.hooks import on_tick

        return on_tick

    elif name == "Terminal":
        from xnano.terminal import Terminal

        return Terminal

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> list[str]:
    return list(__all__)
