"""xnano.beta

Beta implementation of the complete ``xnano`` framework used
as a staging ground until the first stable ``1.0.0``
release.

All exports and components currently within ``xnano`` are all
within this submodule.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # [@target]
    # The exports within this module were reduced purely on `v0.99.6` for
    # ergonomics and readability purposes.
    # The current set of exports that xnano exports at the top level are still very open
    # for intepretation.
    from xnano.beta.core.renderable import render
    from xnano.beta.context import Context
    from xnano.beta.fields import Field
    from xnano.beta.grid import Grid, GridSettings
    from xnano.beta.sizing import Sizing
    from xnano.beta.hooks import (
        on_event,
        on_resize,
        on_focus,
        on_clipboard,
        on_state,
        on_field,
        on_poll,
        on_keyboard,
        on_mouse,
        on_click,
        on_tick,
    )
    from xnano.beta.terminal import Terminal


def __getattr__(name: str):
    if name == "render":
        from xnano.beta.core.renderable import render

        return render

    if name == "Context":
        from xnano.beta.context import Context

        return Context

    if name == "Field":
        from xnano.beta.fields import Field

        return Field

    if name == "Grid":
        from xnano.beta.grid import Grid

        return Grid

    if name == "GridSettings":
        from xnano.beta.grid import GridSettings

        return GridSettings

    if name == "Sizing":
        from xnano.beta.sizing import Sizing

        return Sizing

    if name == "on_event":
        from xnano.beta.hooks import on_event

        return on_event

    if name == "on_resize":
        from xnano.beta.hooks import on_resize

        return on_resize

    if name == "on_focus":
        from xnano.beta.hooks import on_focus

        return on_focus

    if name == "on_clipboard":
        from xnano.beta.hooks import on_clipboard

        return on_clipboard

    if name == "on_state":
        from xnano.beta.hooks import on_state

        return on_state

    if name == "on_field":
        from xnano.beta.hooks import on_field

        return on_field

    if name == "on_poll":
        from xnano.beta.hooks import on_poll

        return on_poll

    if name == "on_keyboard":
        from xnano.beta.hooks import on_keyboard

        return on_keyboard

    if name == "on_mouse":
        from xnano.beta.hooks import on_mouse

        return on_mouse

    if name == "on_click":
        from xnano.beta.hooks import on_click

        return on_click

    if name == "on_tick":
        from xnano.beta.hooks import on_tick

        return on_tick

    if name == "Terminal":
        from xnano.beta.terminal import Terminal

        return Terminal

    raise AttributeError(f"module 'xnano.beta' has no attribute {name!r}")


__all__ = (
    "render",
    "Context",
    "Field",
    "Grid",
    "GridSettings",
    "Sizing",
    "on_event",
    "on_resize",
    "on_focus",
    "on_clipboard",
    "on_state",
    "on_field",
    "on_poll",
    "on_keyboard",
    "on_mouse",
    "on_click",
    "on_tick",
    "Terminal",
)
