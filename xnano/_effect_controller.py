"""
xnano._effect_controller

The effects a hook applies to its buffer through ``context.fx``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, final

if TYPE_CHECKING:
    from xnano.context import Context

__all__ = ['EffectController']


@final
class EffectController:
    """
    Applies effects to the buffer of the hook that is running.

    Get one from ``context.fx``.

    Attributes:
        context: The context of the hook that applies the effects.
    """

    __slots__ = ('_context',)

    def __init__(self, context: Context[object, object]) -> None:
        """
        Create the controller of a context. Use ``context.fx`` instead of calling this.

        Args:
            context: The context of the hook that applies the effects.
        """
        self._context = context

    @property
    def context(self) -> Context[object, object]:
        """The context of the hook that applies the effects."""
        return self._context
