"""
xnano._schema._state

The aliases of the state store.
"""

from __future__ import annotations

from typing import TypeAlias

StatePath: TypeAlias = tuple[str | int, ...]
"""A path in the state store: object keys and array indexes, outermost first."""
