"""xnano

>>> import xnano as x
>>> from xnano import BaseGrid, Field, Terminal
"""

__version__ = "1.0.0"

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from xnano._styles import Style
    from xnano.context import Context
    from xnano.core.actions import Action
    from xnano.events import (
        on,
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
    from xnano.fields import Field
    from xnano.grid import BaseGrid, Grid, GridSettings
    from xnano.tui.terminal import Terminal


__all__ = (
    "Action",
    "Context",
    "Field",
    "BaseGrid",
    "Grid",
    "GridSettings",
    "Style",
    "on",
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
    if name == "Action":
        from xnano.core.actions import Action

        return Action

    elif name == "Context":
        from xnano.context import Context

        return Context

    elif name == "Field":
        from xnano.fields import Field

        return Field

    elif name == "BaseGrid":
        from xnano.grid import BaseGrid

        return BaseGrid

    elif name == "Grid":
        from xnano.grid import Grid

        return Grid

    elif name == "GridSettings":
        from xnano.grid import GridSettings

        return GridSettings

    elif name == "Style":
        from xnano._styles import Style

        return Style

    elif name == "on":
        from xnano.events import on

        return on

    elif name == "on_click":
        from xnano.events import on_click

        return on_click

    elif name == "on_clipboard":
        from xnano.events import on_clipboard

        return on_clipboard

    elif name == "on_event":
        from xnano.events import on_event

        return on_event

    elif name == "on_field":
        from xnano.events import on_field

        return on_field

    elif name == "on_focus":
        from xnano.events import on_focus

        return on_focus

    elif name == "on_keyboard":
        from xnano.events import on_keyboard

        return on_keyboard

    elif name == "on_mouse":
        from xnano.events import on_mouse

        return on_mouse

    elif name == "on_poll":
        from xnano.events import on_poll

        return on_poll

    elif name == "on_resize":
        from xnano.events import on_resize

        return on_resize

    elif name == "on_state":
        from xnano.events import on_state

        return on_state

    elif name == "on_tick":
        from xnano.events import on_tick

        return on_tick

    elif name == "Terminal":
        from xnano.tui.terminal import Terminal

        return Terminal

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> list[str]:
    return list(__all__)
