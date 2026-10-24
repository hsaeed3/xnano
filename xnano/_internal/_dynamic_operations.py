"""
xnano._internal._dynamic_operations

The base of the operations whose fields can be edited after they are applied.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import TYPE_CHECKING, cast

import xnano_core as _core

if TYPE_CHECKING:
    from typing_extensions import Self

    from xnano.canvas import Canvas
    from xnano.effects._properties import EffectParameters
    from xnano.layout._placement import Placement


class DynamicOperation(_core.Customization):
    """
    An operation whose parameters are dataclass fields, read when it is applied, so assigning a field re-applies it to its target.

    It is both a dataclass holding its typed parameters and a native
    [`Customization`][xnano_core.Customization] operation that can be piped with ``|`` or
    passed to ``add`` and ``update``.

    Attributes:
        customization_kind: Identifier of the operation kind (such as ``'fill'`` or ``'effect.dissolve'``).

    Raises:
        TypeError: A keyword is not a setting of the operation. The message lists its settings.
    """

    def __new__(cls, *arguments: object, **settings: object) -> Self:
        if is_dataclass(cls):
            accepted = [field.name for field in fields(cls) if field.init]
            for name in settings:
                if name not in accepted:
                    listed = ', '.join(accepted) if accepted else 'none'
                    raise TypeError(
                        f'{cls.__name__} has no setting called {name!r}. Its settings are: '
                        f'{listed}.'
                    )
        return super().__new__(cls, *arguments, **settings)

    def apply_to(
        self,
        target: Canvas[object, object] | Placement[object, object] | _core.Surface,
    ) -> None:
        """
        Apply this operation to a canvas, placement or surface.

        It stays attached to the target: after this, assigning one of its fields applies it
        again, so the operation is a live handle on what it changed. A running effect is
        stopped and started again with the new values.

        Args:
            target: The target to apply the operation to.
        """
        from xnano.canvas import Canvas
        from xnano.layout._placement import Placement

        self._attach(target)
        if isinstance(target, (Placement, Canvas)):
            target._buffer.update(self)
            if self.customization_kind.startswith('effect.'):
                target._canvas._record_effect(cast('EffectParameters', self), target)
        elif isinstance(target, _core.Surface):
            target.update(self)

    def _attach(self, target: object) -> None:
        """Remember the target, and give a running effect a key so it can be stopped."""
        if (
            self.customization_kind.startswith('effect.')
            and getattr(self, 'key', 1) is None
        ):
            object.__setattr__(self, 'key', f'xnano-effect-{id(self)}')
        object.__setattr__(self, '_target', target)

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        if name.startswith('_') or name not in getattr(self, '__dataclass_fields__', ()):
            return
        target = self.__dict__.get('_target')
        if target is None:
            return
        surface = target._buffer if hasattr(target, '_buffer') else target
        key = getattr(self, 'key', None)
        if self.customization_kind.startswith('effect.') and key is not None:
            surface.update(_core.CancelEffect(key))
        surface.update(self)
