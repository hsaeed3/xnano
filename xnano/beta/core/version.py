"""xnano.beta.core.version"""

from __future__ import annotations

import sys

from xnano_core.rust.native import __version__ as __xnano_core_version__

__all__ = ("VERSION", "check_xnano_core_version")

VERSION = "1.0.0b4"
"""The version of xnano.

This version specifier is guaranteed to be compliant with the [specification],
introduced by [PEP 440].

[specification]: https://packaging.python.org/en/latest/specifications/version-specifiers/
[PEP 440]: https://peps.python.org/pep-0440/
"""

# !! THIS MUST MATCH THE VERSION CONSTRAINT IN THE `pyproject.toml`
# !! DEPENDENCIES
_COMPATIBLE_XNANO_CORE_VERSION = "0.0.7"


def check_xnano_core_version() -> bool:
    """Check that the installed ``xnano-core`` dependency is compatible."""
    return __xnano_core_version__ == _COMPATIBLE_XNANO_CORE_VERSION


def _ensure_xnano_core_version() -> None:  # pragma: no cover
    if not check_xnano_core_version():
        raise_error = True
        if sys.version_info >= (3, 13):
            from importlib.metadata import distribution

            dist = distribution("xnano")
            if getattr(
                getattr(dist.origin, "dir_info", None), "editable", False
            ):
                raise_error = False

        if raise_error:
            raise SystemError(
                f"The installed xnano-core version ({__xnano_core_version__}) is "
                f"incompatible with the current xnano version, which requires "
                f"{_COMPATIBLE_XNANO_CORE_VERSION}. If you encounter this error, "
                "make sure that you haven't upgraded xnano-core manually."
            )
