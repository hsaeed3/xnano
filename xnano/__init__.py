"""xnano

---

Build terminal and web interfaces with grids, fields, components,
hooks, actions, and runtimes.
"""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING, Any

try:
    __version__ = importlib.metadata.version("xnano")
except (
    importlib.metadata.PackageNotFoundError
):  # pragma: no cover - editable / source trees
    __version__ = "1.2.2"

if TYPE_CHECKING:
    from xnano import cli, components, core, events, hooks, requests
    from xnano.actions import Action
    from xnano.cli import Command
    from xnano.components import Component
    from xnano.context import Context
    from xnano.core import Frame, Runtime
    from xnano.fields import Field
    from xnano.grids import BaseGrid, GridSettings
    from xnano.hooks import (
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
    from xnano.rendering import render
    from xnano.tailwind import Style
    from xnano.terminal import Terminal
    from xnano.web import Web

__all__ = [
    "__version__",
    "render",
    "Action",
    "BaseGrid",
    "Command",
    "Component",
    "Context",
    "Field",
    "Frame",
    "GridSettings",
    "Runtime",
    "Style",
    "Terminal",
    "Web",
    "hooks",
    "requests",
    "cli",
    "components",
    "core",
    "events",
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
]


def __getattr__(name: str) -> Any:
    import importlib

    if name == "render":
        from xnano.rendering import render

        return render
    if name == "Action":
        from xnano.actions import Action

        return Action
    if name == "Context":
        from xnano.context import Context

        return Context
    if name == "Field":
        from xnano.fields import Field

        return Field
    if name == "BaseGrid":
        from xnano.grids import BaseGrid

        return BaseGrid
    if name == "GridSettings":
        from xnano.grids import GridSettings

        return GridSettings
    if name == "Style":
        from xnano.tailwind import Style

        return Style
    if name == "Terminal":
        from xnano.terminal import Terminal

        return Terminal
    if name == "Web":
        from xnano.web import Web

        return Web
    if name == "Runtime":
        from xnano.core.runtime import Runtime

        return Runtime
    if name == "Frame":
        from xnano.core.frame import Frame

        return Frame
    if name == "Component":
        from xnano.components.component import Component

        return Component
    if name == "Command":
        from xnano.cli.command import Command

        return Command
    if name in {
        "hooks",
        "requests",
        "cli",
        "components",
        "core",
        "events",
    }:
        return importlib.import_module(f"xnano.{name}")
    if name in {
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
    }:
        hooks_module = importlib.import_module("xnano.hooks")
        return getattr(hooks_module, name)
    raise AttributeError(f"module 'xnano' has no attribute {name!r}")


def __dir__() -> list[str]:
    return list(__all__)
