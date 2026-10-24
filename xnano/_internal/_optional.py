"""
xnano._internal._optional

The parts of `xnano` that need the optional `xnano-audio`, `xnano-image`, `pydantic-monty` and
`pydantic-ai-slim` packages, and the message that says how to install them.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from types import ModuleType

from xnano._schema._media import Extra

__all__ = ['is_installed', 'is_image', 'require']

_PACKAGES: dict[Extra, str] = {
    'audio': 'xnano_audio',
    'image': 'xnano_image',
    'monty': 'pydantic_monty',
    'ai': 'pydantic_ai',
}
_PURPOSE: dict[Extra, str] = {
    'audio': 'sound, notes and melodies',
    'image': 'images',
    'monty': 'a sandbox for running untrusted Python',
    'ai': 'language models, decision models and agents',
}


def is_installed(extra: Extra) -> bool:
    """Whether the package behind an extra can be imported."""
    return importlib.util.find_spec(_PACKAGES[extra]) is not None


def require(extra: Extra, *, needed_for: str) -> ModuleType:
    """
    Import the package behind an extra, or say how to install it.

    Args:
        extra: ``'audio'``, ``'image'``, ``'monty'`` or ``'ai'``.
        needed_for: What was being done, such as ``'Canvas.audio'``, for the message.

    Raises:
        ImportError: The package is not installed. The message names the extra to install.
    """
    try:
        return importlib.import_module(_PACKAGES[extra])
    except ModuleNotFoundError as error:
        if error.name != _PACKAGES[extra]:
            raise
        package = (
            'pydantic-ai-slim' if extra == 'ai' else _PACKAGES[extra].replace('_', '-')
        )
        raise ImportError(
            f'{needed_for} needs {_PURPOSE[extra]}, which is provided by the optional '
            f'package {package}. Install it with: pip install "xnano[{extra}]"'
        ) from None


def is_image(content: object) -> bool:
    """
    Whether ``content`` is a ``TerminalImage``.

    An image cannot exist unless its package was imported, so this never imports it.
    """
    module = sys.modules.get(_PACKAGES['image'])
    return module is not None and isinstance(content, module.TerminalImage)
