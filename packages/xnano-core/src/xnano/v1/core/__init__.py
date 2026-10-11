"""
xnano.v1.core

---

Run interfaces live or offscreen and inspect their rendered frames.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xnano.v1.core.exceptions import (
        Exit,
        HookError,
        ValidationError,
        XnanoError,
    )
    from xnano.v1.core.frame import Frame
    from xnano.v1.core.runtime import Runtime, get_active_runtime
    from xnano.v1.cursor import Cursor
    from xnano.v1.device import Device

__all__ = (
    'Cursor',
    'Device',
    'Exit',
    'Frame',
    'HookError',
    'Runtime',
    'ValidationError',
    'XnanoError',
    'get_active_runtime',
)


def __getattr__(name: str) -> Any:
    if name in {'Runtime', 'get_active_runtime'}:
        from xnano.v1.core import runtime as _runtime

        return getattr(_runtime, name)
    if name == 'Frame':
        from xnano.v1.core.frame import Frame

        return Frame
    if name == 'Cursor':
        from xnano.v1.cursor import Cursor

        return Cursor
    if name == 'Device':
        from xnano.v1.device import Device

        return Device
    if name in {'Exit', 'HookError', 'ValidationError', 'XnanoError'}:
        from xnano.v1.core import exceptions as _exceptions

        return getattr(_exceptions, name)
    raise AttributeError(f"module 'xnano.v1.core' has no attribute {name!r}")


def __dir__() -> list[str]:
    return list(__all__)
