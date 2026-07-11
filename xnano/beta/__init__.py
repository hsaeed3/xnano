"""xnano.beta

Prototype surface for xnano APIs that will move into the main namespace
once stabilized. Import concrete modules directly (for example
``xnano.beta.web`` or ``xnano.beta.requests``) rather than this package
root.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xnano.beta.commands import Command
    from xnano.beta.requests import on_get_request, on_post_request
    from xnano.beta.tailwind import (
        TailwindClass,
        TailwindStyle,
        register_tailwind_class_group,
        resolve_tailwind_classes,
    )
    from xnano.beta.web import Web


__all__ = (
    "Command",
    "TailwindClass",
    "TailwindStyle",
    "on_get_request",
    "on_post_request",
    "register_tailwind_class_group",
    "resolve_tailwind_classes",
    "Web",
)


_TAILWIND_EXPORTS = frozenset(
    {
        "TailwindClass",
        "TailwindStyle",
        "register_tailwind_class_group",
        "resolve_tailwind_classes",
    }
)


def __getattr__(name: str):
    if name == "Command":
        from xnano.beta.commands import Command

        return Command

    elif name in _TAILWIND_EXPORTS:
        from xnano.beta import tailwind

        return getattr(tailwind, name)

    elif name == "on_get_request":
        from xnano.beta.requests import on_get_request

        return on_get_request

    elif name == "on_post_request":
        from xnano.beta.requests import on_post_request

        return on_post_request

    elif name == "Web":
        from xnano.beta.web import Web

        return Web

    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
