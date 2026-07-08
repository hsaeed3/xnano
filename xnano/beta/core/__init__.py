"""xnano.beta.core"""

from typing import TYPE_CHECKING

# version constraint check happens on first import
# of xnano.beta.core
from xnano.beta.core.version import _ensure_xnano_core_version

_ensure_xnano_core_version()
del _ensure_xnano_core_version


if TYPE_CHECKING:
    # The demo module pulls in the whole rendering stack and is only ever
    # needed when the showcase is launched, so it is exposed lazily rather
    # than imported eagerly here.
    from xnano.beta.core.demo import run_demo


def __getattr__(name: str):
    if name == "run_demo":
        from xnano.beta.core.demo import run_demo

        return run_demo

    raise AttributeError(f"module 'xnano.beta.core' has no attribute {name!r}")


__all__ = ("run_demo",)
