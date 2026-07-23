"""xnano.beta

---

Build terminal and web interfaces with beta-owned grids, fields, components,
hooks, actions, and runtimes.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

try:
    __version__ = version("xnano")
except PackageNotFoundError:  # pragma: no cover - editable / source trees
    __version__ = "1.1.1"

if TYPE_CHECKING:
    from xnano.beta import cli, components, core, events, hooks, requests
    from xnano.beta.actions import Action
    from xnano.beta.cli import Command
    from xnano.beta.components import Component
    from xnano.beta.context import Context
    from xnano.beta.core import Frame, Runtime
    from xnano.beta.fields import Field
    from xnano.beta.grids import BaseGrid, GridSettings
    from xnano.beta.hooks import (
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
    from xnano.beta.rendering import render
    from xnano.beta.tailwind import Style
    from xnano.beta.terminal import Terminal
    from xnano.beta.web import Web

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
        from xnano.beta.rendering import render

        return render
    if name == "Action":
        from xnano.beta.actions import Action

        return Action
    if name == "Context":
        from xnano.beta.context import Context

        return Context
    if name == "Field":
        from xnano.beta.fields import Field

        return Field
    if name == "BaseGrid":
        from xnano.beta.grids import BaseGrid

        return BaseGrid
    if name == "GridSettings":
        from xnano.beta.grids import GridSettings

        return GridSettings
    if name == "Style":
        from xnano.beta.tailwind import Style

        return Style
    if name == "Terminal":
        from xnano.beta.terminal import Terminal

        return Terminal
    if name == "Web":
        from xnano.beta.web import Web

        return Web
    if name == "Runtime":
        from xnano.beta.core.runtime import Runtime

        return Runtime
    if name == "Frame":
        from xnano.beta.core.frame import Frame

        return Frame
    if name == "Component":
        from xnano.beta.components.component import Component

        return Component
    if name == "Command":
        from xnano.beta.cli.command import Command

        return Command
    if name in {
        "hooks",
        "requests",
        "cli",
        "components",
        "core",
        "events",
    }:
        return importlib.import_module(f"xnano.beta.{name}")
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
        hooks_module = importlib.import_module("xnano.beta.hooks")
        return getattr(hooks_module, name)
    raise AttributeError(f"module 'xnano.beta' has no attribute {name!r}")


def __dir__() -> list[str]:
    return list(__all__)
