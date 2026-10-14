"""
xnano.input

Which keys are held down right now, for programs that poll instead of listening.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import xnano_core as _core

if TYPE_CHECKING:
    from xnano.terminal import Terminal

__all__ = ['Input']

# How long after the last key repeat a key still counts as held, on a terminal that does not
# report key releases. It has to outlast the operating system's pause before a held key repeats.
_ESTIMATED_HOLD_SECONDS = 0.45

KeyNames = str | Sequence[str]
"""One key name, or several that count the same, such as ``('a', 'left')``."""


def _names(keys: KeyNames) -> tuple[str, ...]:
    return (keys,) if isinstance(keys, str) else tuple(keys)


class Input:
    """
    The keys held down right now.

    A hook hears each key press once. A game wants the opposite: ask every step which keys
    are down. Get one from [`Terminal.input`][xnano.terminal.Terminal.input] and read it inside a
    hook or an update, such as one registered with
    [`loop.on_update`][xnano.loop.Loop.on_update].

    A terminal that reports key releases (kitty, ghostty and wezterm, when opened with
    ``keyboard='release_events'``) tells exactly when a key is let go. Any other terminal
    only sends repeats while a key is held, so a key counts as held for a short time after
    its last repeat.

    Attributes:
        held_keys: The names of the keys held down right now.
        pointer: The ``(column, row)`` under the pointer, or ``None`` before it has moved.

    Examples:
        ```python
        import xnano

        with xnano.iter(offscreen=True, width=20, height=3) as terminal:
            hero = terminal.write('@')

            @terminal.loop.on_update(fixed_step_seconds=1 / 30)
            def walk(update: xnano.context.Update) -> None:
                step_x, step_y = terminal.input.direction()
                hero.x += step_x
                hero.y += step_y
        ```
    """

    def __init__(self, terminal: Terminal[object]) -> None:
        """
        Create the terminal's input. Use ``terminal.input`` instead of calling this.

        Args:
            terminal: The terminal the input belongs to.
        """
        self._state: _core.InputState = terminal._runtime.input
        self._state.estimate_holds(timeout_seconds=_ESTIMATED_HOLD_SECONDS)

    @property
    def held_keys(self) -> frozenset[str]:
        """The names of the keys held down right now."""
        return self._state.pressed_keys | self._state.estimated_pressed_keys

    def is_down(self, keys: KeyNames) -> bool:
        """
        Whether any of the keys is held down.

        Args:
            keys: One key name such as ``'space'``, or several such as ``('a', 'left')``.
        """
        held = self.held_keys
        return any(name in held for name in _names(keys))

    def axis(self, negative: KeyNames, positive: KeyNames) -> int:
        """
        ``-1``, ``0`` or ``1`` from a pair of keys: the negative one, neither or both, the
        positive one.

        Args:
            negative: The key or keys that push toward ``-1``.
            positive: The key or keys that push toward ``1``.
        """
        return int(self.is_down(positive)) - int(self.is_down(negative))

    def direction(
        self,
        *,
        left: KeyNames = ('a', 'left'),
        right: KeyNames = ('d', 'right'),
        up: KeyNames = ('w', 'up'),
        down: KeyNames = ('s', 'down'),
    ) -> tuple[int, int]:
        """
        The way the arrow keys or ``wasd`` point, as ``(step_x, step_y)``.

        Each step is ``-1``, ``0`` or ``1``; ``y`` grows downward, like the screen.

        Args:
            left: The key or keys that mean left.
            right: The key or keys that mean right.
            up: The key or keys that mean up.
            down: The key or keys that mean down.
        """
        return self.axis(left, right), self.axis(up, down)

    @property
    def pointer(self) -> tuple[int, int] | None:
        """The ``(column, row)`` under the pointer, or ``None`` before it has moved."""
        return self._state.pointer_cell
