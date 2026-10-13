"""
xnano

---

Build terminal and web interfaces with grids, fields, components,
hooks, actions, and runtimes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xnano.deprecated import cli, components, core, events, hooks, requests
    from xnano.deprecated.actions import Action
    from xnano.deprecated.cli import Command
    from xnano.deprecated.components import Component
    from xnano.deprecated.context import Context
    from xnano.deprecated.core import Frame, Runtime
    from xnano.deprecated.fields import Field
    from xnano.deprecated.grids import BaseGrid, GridSettings
    from xnano.deprecated.hooks import (
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
    from xnano.deprecated.rendering import render
    from xnano.deprecated.tailwind import Style
    from xnano.deprecated.terminal import Terminal
    from xnano.deprecated.web import Web

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
        from xnano.deprecated.rendering import render

        return render
    if name == 'Action':
        from xnano.deprecated.actions import Action

        return Action
    if name == 'Context':
        from xnano.deprecated.context import Context

        return Context
    if name == 'Field':
        from xnano.deprecated.fields import Field

        return Field
    if name == 'BaseGrid':
        from xnano.deprecated.grids import BaseGrid

        return BaseGrid
    if name == 'GridSettings':
        from xnano.deprecated.grids import GridSettings

        return GridSettings
    if name == 'Style':
        from xnano.deprecated.tailwind import Style

        return Style
    if name == 'Terminal':
        from xnano.deprecated.terminal import Terminal

        return Terminal
    if name == 'Web':
        from xnano.deprecated.web import Web

        return Web
    if name == 'Runtime':
        from xnano.deprecated.core.runtime import Runtime

        return Runtime
    if name == 'Frame':
        from xnano.deprecated.core.frame import Frame

        return Frame
    if name == 'Component':
        from xnano.deprecated.components.component import Component

        return Component
    if name == 'Command':
        from xnano.deprecated.cli.command import Command

        return Command
    if name in {
        'hooks',
        'requests',
        'cli',
        'components',
        'core',
        'events',
    }:
        return importlib.import_module(f'xnano.deprecated.{name}')
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
        hooks_module = importlib.import_module('xnano.deprecated.hooks')
        return getattr(hooks_module, name)
    raise AttributeError(f"module 'xnano.deprecated' has no attribute {name!r}")


def __dir__() -> list[str]:
    return list(__all__)
