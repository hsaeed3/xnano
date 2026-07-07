"""xnano.beta

Beta implementation of the complete ``xnano`` framework used
as a staging ground until the first stable ``1.0.0``
release.

All exports and components currently within ``xnano`` are all
within this submodule.
"""

from xnano.beta.core.renderable import Renderable, render
from xnano.beta.color import Color
from xnano.beta.components import (
    AbstractComponent,
    ComponentRenderContext,
    Text,
)
from xnano.beta.effects import (
    AbstractEffect,
    Effect,
)
from xnano.beta.context import Context
from xnano.beta.exceptions import Exit
from xnano.beta.fields import Field
from xnano.beta.grid import Grid, GridSettings
from xnano.beta.hooks import (
    on_event,
    on_resize,
    on_focus,
    on_clipboard,
    on_state,
    on_keyboard,
    on_mouse,
    on_click,
    on_tick,
)
from xnano.beta.terminal import Terminal


__all__ = (
    "Renderable",
    "Color",
    "AbstractComponent",
    "AbstractEffect",
    "ComponentRenderContext",
    "Context",
    "Effect",
    "Exit",
    "Field",
    "Grid",
    "GridSettings",
    "on_event",
    "on_resize",
    "on_focus",
    "on_clipboard",
    "on_state",
    "on_keyboard",
    "on_mouse",
    "on_click",
    "on_tick",
    "Terminal",
    "Text",
    "render",
)
