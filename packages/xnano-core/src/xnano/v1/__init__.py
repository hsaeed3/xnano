"""
xnano

---

Build terminal and web interfaces with grids, fields, components,
hooks, actions, and runtimes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xnano.v1 import cli, components, core, events, hooks, requests
    from xnano.v1.actions import Action
    from xnano.v1.cli import Command
    from xnano.v1.components import Component
    from xnano.v1.context import Context
    from xnano.v1.core import Frame, Runtime
    from xnano.v1.fields import Field
    from xnano.v1.grids import BaseGrid, GridSettings
    from xnano.v1.hooks import (
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
    from xnano.v1.rendering import render
    from xnano.v1.tailwind import Style
    from xnano.v1.terminal import Terminal
    from xnano.v1.web import Web

__all__ = [
    'Action',
    'BaseGrid',
    'Command',
    'Component',
    'Context',
    'Field',
    'Frame',
    'GridSettings',
    'Runtime',
    'Style',
    'Terminal',
    'Web',
    'cli',
    'components',
    'core',
    'events',
    'hooks',
    'on_action',
    'on_click',
    'on_clipboard',
    'on_event',
    'on_field',
    'on_focus',
    'on_keyboard',
    'on_mouse',
    'on_poll',
    'on_resize',
    'on_state',
    'on_tick',
    'render',
    'requests',
]


def __getattr__(name: str) -> Any:
    import importlib

    if name == 'render':
        from xnano.v1.rendering import render

        return render
    if name == 'Action':
        from xnano.v1.actions import Action

        return Action
    if name == 'Context':
        from xnano.v1.context import Context

        return Context
    if name == 'Field':
        from xnano.v1.fields import Field

        return Field
    if name == 'BaseGrid':
        from xnano.v1.grids import BaseGrid

        return BaseGrid
    if name == 'GridSettings':
        from xnano.v1.grids import GridSettings

        return GridSettings
    if name == 'Style':
        from xnano.v1.tailwind import Style

        return Style
    if name == 'Terminal':
        from xnano.v1.terminal import Terminal

        return Terminal
    if name == 'Web':
        from xnano.v1.web import Web

        return Web
    if name == 'Runtime':
        from xnano.v1.core.runtime import Runtime

        return Runtime
    if name == 'Frame':
        from xnano.v1.core.frame import Frame

        return Frame
    if name == 'Component':
        from xnano.v1.components.component import Component

        return Component
    if name == 'Command':
        from xnano.v1.cli.command import Command

        return Command
    if name in {
        'hooks',
        'requests',
        'cli',
        'components',
        'core',
        'events',
    }:
        return importlib.import_module(f'xnano.v1.{name}')
    if name in {
        'on_action',
        'on_click',
        'on_clipboard',
        'on_event',
        'on_field',
        'on_focus',
        'on_keyboard',
        'on_mouse',
        'on_poll',
        'on_resize',
        'on_state',
        'on_tick',
    }:
        hooks_module = importlib.import_module('xnano.v1.hooks')
        return getattr(hooks_module, name)
    raise AttributeError(f"module 'xnano' has no attribute {name!r}")


def __dir__() -> list[str]:
    return list(__all__)
