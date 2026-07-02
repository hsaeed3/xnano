"""xnano.hooks"""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from xnano.keyboard import KeyboardBinding
from xnano.mouse import MouseEventKind

F = TypeVar("F", bound=Callable[..., Any])


def on_keyboard(*bindings: KeyboardBinding) -> Callable[[F], F]:
    """Decorator that marks a component method as a keyboard event hook."""

    def decorator(function: F) -> F:
        setattr(function, "__xnano_keyboard_bindings__", list(bindings))
        return function

    return decorator


def on_mouse(*kinds: MouseEventKind) -> Callable[[F], F]:
    """Decorator that marks a component method as a mouse event hook."""

    def decorator(function: F) -> F:
        setattr(function, "__xnano_mouse_kinds__", list(kinds))
        return function

    return decorator
