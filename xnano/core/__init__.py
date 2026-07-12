"""xnano.core

---

Shared framework contracts and engines that sit under the public DSL
surface (``grid``, ``fields``, ``events``, …) and above interface kinds
(``tui``, ``webui``, ``cli``).

Public names are re-exported from concrete modules; prefer importing
from those modules (``xnano.core.actions``, ``xnano.core.hosts``, …).
"""

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from xnano.core.actions import Action
    from xnano.core.content import Content
    from xnano.core.device import AbstractCursor, AbstractDevice
    from xnano.core.exceptions import (
        Exit,
        ExtraNotInstalledError,
        FieldValidationError,
        HookError,
        TerminalNotActiveError,
    )
    from xnano.core.hosts import AbstractHost, RouteTable, get_active_host
    from xnano.core.interface import AbstractInterface
    from xnano.core.stage import LayoutMap, Stage

__all__ = (
    "AbstractCursor",
    "AbstractDevice",
    "AbstractHost",
    "AbstractInterface",
    "Action",
    "Content",
    "Exit",
    "ExtraNotInstalledError",
    "FieldValidationError",
    "HookError",
    "LayoutMap",
    "RouteTable",
    "Stage",
    "TerminalNotActiveError",
    "get_active_host",
)


def __getattr__(name: str):
    if name == "Action":
        from xnano.core.actions import Action

        return Action
    if name == "Content":
        from xnano.core.content import Content

        return Content
    if name in ("AbstractDevice", "AbstractCursor"):
        from xnano.core import device as _device

        return getattr(_device, name)
    if name in ("AbstractHost", "RouteTable", "get_active_host"):
        from xnano.core import hosts as _hosts

        return getattr(_hosts, name)
    if name == "AbstractInterface":
        from xnano.core.interface import AbstractInterface

        return AbstractInterface
    if name in ("Stage", "LayoutMap"):
        from xnano.core import stage as _stage

        return getattr(_stage, name)
    if name in (
        "Exit",
        "HookError",
        "FieldValidationError",
        "TerminalNotActiveError",
        "ExtraNotInstalledError",
    ):
        from xnano.core import exceptions as _exc

        return getattr(_exc, name)
    raise AttributeError(f"module 'xnano.core' has no attribute {name!r}")
