"""xnano.beta.actions

---

Describe keyboard, mouse, focus, clipboard, resize, tick, and request actions.
"""

from __future__ import annotations

import abc
import dataclasses
import functools
from typing import Any, Literal, TypeAlias

from xnano.beta.types import KeyboardBinding, MouseButton

KeyboardEventKind: TypeAlias = Literal["press", "release", "repeat"]
"""Keyboard event phase."""

MouseEventKind: TypeAlias = Literal[
    "press",
    "release",
    "drag",
    "move",
    "scroll_up",
    "scroll_down",
    "scroll_left",
    "scroll_right",
]
"""Mouse event phase."""

FocusEventKind: TypeAlias = Literal[
    "gained",
    "lost",
    "field_gained",
    "field_lost",
]
"""Focus transition."""

NormalizedBinding: TypeAlias = tuple[frozenset[str], str]
"""Normalized keyboard binding as ``(modifiers, key)``."""

_KEY_ALIASES = {"escape": "esc", "return": "enter", " ": "space"}


@functools.lru_cache(maxsize=512)
def normalize_binding(binding: str) -> NormalizedBinding | None:
    """Normalize a ``ctrl+shift+k`` style binding."""
    parts = [
        part.strip().lower() for part in binding.split("+") if part.strip()
    ]
    if not parts:
        return None
    return (
        frozenset(
            part for part in parts[:-1] if part in ("ctrl", "alt", "shift")
        ),
        _KEY_ALIASES.get(parts[-1], parts[-1]),
    )


def _keyboard_binding(event: Any) -> NormalizedBinding | None:
    binding = getattr(event, "binding", None)
    if binding is not None:
        return normalize_binding(str(binding))
    key = getattr(event, "key", getattr(event, "_key", None))
    if key is None:
        return None
    modifiers = getattr(event, "modifiers", getattr(event, "_modifiers", ()))
    return (
        frozenset(str(value).lower() for value in modifiers or ()),
        _KEY_ALIASES.get(str(key).lower(), str(key).lower()),
    )


@dataclasses.dataclass(frozen=True, slots=True)
class Action(abc.ABC):
    """Declarative event trigger.

    Examples:
        ```python
        save = Action.keyboard("ctrl+s")

        @on_action(save)
        def save_document(self) -> None:
            ...

        terminal.actions.perform(save)
        ```
    """

    @classmethod
    def keyboard(
        cls,
        *bindings: KeyboardBinding,
        kind: KeyboardEventKind | None = None,
    ) -> "KeyboardAction":
        """Match one or more keyboard bindings."""
        return KeyboardAction(bindings=bindings, kind=kind)

    @classmethod
    def mouse(
        cls,
        *buttons: MouseButton,
        kind: MouseEventKind | None = None,
    ) -> "MouseAction":
        """Match a mouse event."""
        return MouseAction(buttons=buttons, kind=kind)

    @classmethod
    def click(
        cls,
        field: str | None = None,
        button: MouseButton = "left",
    ) -> "ClickAction":
        """Match a button press on a field."""
        return ClickAction(field=field, button=button)

    @classmethod
    def focus(
        cls,
        field: str | None = None,
        kind: FocusEventKind | None = None,
    ) -> "FocusAction":
        """Match a focus transition."""
        return FocusAction(field=field, kind=kind)

    @classmethod
    def clipboard(cls, text: str | None = None) -> "ClipboardAction":
        """Match pasted text."""
        return ClipboardAction(text=text)

    @classmethod
    def tick(cls, interval_ms: int = 0) -> "TickAction":
        """Match a clock tick."""
        return TickAction(interval_ms=interval_ms)

    @classmethod
    def resize(
        cls,
        width: int | None = None,
        height: int | None = None,
    ) -> "ResizeAction":
        """Match a resize event."""
        return ResizeAction(width=width, height=height)

    @classmethod
    def request(cls, method: str, path: str = "/") -> "RequestAction":
        """Match an HTTP request."""
        return RequestAction(method=method.upper(), path=path)

    @abc.abstractmethod
    def matches(self, event: Any) -> bool:
        """Return whether ``event`` satisfies this action."""


@dataclasses.dataclass(frozen=True, slots=True)
class KeyboardAction(Action):
    """Match keyboard bindings and an optional transition.

    Attributes:
        bindings: Accepted keyboard bindings.
        kind: Required keyboard transition, or any transition.
    """

    bindings: tuple[KeyboardBinding, ...] = ()
    """Accepted keyboard bindings."""
    kind: KeyboardEventKind | None = None
    """Required keyboard transition."""

    def matches(self, event: Any) -> bool:
        """Return whether an event matches this keyboard action."""
        keyboard = getattr(event, "keyboard_event", event)
        if keyboard is None:
            return False
        if (
            self.kind is not None
            and getattr(keyboard, "kind", None) != self.kind
        ):
            return False
        actual = _keyboard_binding(keyboard)
        return not self.bindings or any(
            normalize_binding(str(binding)) == actual
            for binding in self.bindings
        )


@dataclasses.dataclass(frozen=True, slots=True)
class MouseAction(Action):
    """Match mouse buttons and an optional transition.

    Attributes:
        buttons: Accepted mouse buttons.
        kind: Required mouse transition, or any transition.
    """

    buttons: tuple[MouseButton, ...] = ()
    """Accepted mouse buttons."""
    kind: MouseEventKind | None = None
    """Required mouse transition."""

    def matches(self, event: Any) -> bool:
        """Return whether an event matches this mouse action."""
        mouse = getattr(event, "mouse_event", event)
        if mouse is None:
            return False
        return (
            self.kind is None or getattr(mouse, "kind", None) == self.kind
        ) and (
            not self.buttons or getattr(mouse, "button", None) in self.buttons
        )


@dataclasses.dataclass(frozen=True, slots=True)
class ClickAction(Action):
    """Match a field click.

    Attributes:
        field: Required field name, or any field.
        button: Required mouse button.
    """

    field: str | None = None
    """Required field name."""
    button: MouseButton = "left"
    """Required mouse button."""

    def matches(self, event: Any) -> bool:
        """Return whether an event matches this click action."""
        mouse = getattr(event, "mouse_event", event)
        return bool(
            mouse is not None
            and getattr(mouse, "kind", None) == "press"
            and getattr(mouse, "button", None) == self.button
            and (
                self.field is None
                or getattr(event, "field", getattr(mouse, "field", None))
                == self.field
            )
        )


@dataclasses.dataclass(frozen=True, slots=True)
class FocusAction(Action):
    """Match a focus transition.

    Attributes:
        field: Required field name, or any field.
        kind: Required focus transition, or any transition.
    """

    field: str | None = None
    """Required field name."""
    kind: FocusEventKind | None = None
    """Required focus transition."""

    def matches(self, event: Any) -> bool:
        """Return whether an event matches this focus action."""
        focus = getattr(event, "focus_event", event)
        return bool(
            focus is not None
            and (
                self.kind is None or getattr(focus, "kind", None) == self.kind
            )
            and (
                self.field is None
                or getattr(focus, "field", None) == self.field
            )
        )


@dataclasses.dataclass(frozen=True, slots=True)
class ClipboardAction(Action):
    """Match clipboard text.

    Attributes:
        text: Required clipboard text, or any text.
    """

    text: str | None = None
    """Required clipboard text."""

    def matches(self, event: Any) -> bool:
        """Return whether an event matches this clipboard action."""
        clipboard = getattr(event, "clipboard_event", event)
        return bool(
            clipboard is not None
            and (
                self.text is None
                or getattr(clipboard, "text", None) == self.text
            )
        )


@dataclasses.dataclass(frozen=True, slots=True)
class TickAction(Action):
    """Match a runtime tick.

    Attributes:
        interval_ms: Requested tick interval in milliseconds.
    """

    interval_ms: int = 0
    """Requested tick interval in milliseconds."""

    def matches(self, event: Any) -> bool:
        """Return whether an event is a runtime tick."""
        tick = getattr(event, "tick_event", event)
        return tick is not None and getattr(tick, "type", None) == "tick"


@dataclasses.dataclass(frozen=True, slots=True)
class ResizeAction(Action):
    """Match viewport dimensions.

    Attributes:
        width: Required viewport width, or any width.
        height: Required viewport height, or any height.
    """

    width: int | None = None
    """Required viewport width."""
    height: int | None = None
    """Required viewport height."""

    def matches(self, event: Any) -> bool:
        """Return whether an event matches these viewport dimensions."""
        resize = getattr(event, "resize_event", event)
        return bool(
            resize is not None
            and (
                self.width is None
                or getattr(resize, "width", None) == self.width
            )
            and (
                self.height is None
                or getattr(resize, "height", None) == self.height
            )
        )


@dataclasses.dataclass(frozen=True, slots=True)
class RequestAction(Action):
    """Match an HTTP method and path.

    Attributes:
        method: Required uppercase HTTP method.
        path: Required normalized request path.
    """

    method: str
    """Required uppercase HTTP method."""
    path: str = "/"
    """Required normalized request path."""

    def matches(self, event: Any) -> bool:
        """Return whether an event matches this request route."""
        request = getattr(event, "request", event)
        return bool(
            request is not None
            and str(getattr(request, "method", "")).upper() == self.method
            and getattr(request, "path", None) == self.path
        )


class Actions:
    """Perform actions through a runtime.

    Attributes:
        runtime: Runtime that receives performed actions.

    Examples:
        ```python
        terminal.actions.keyboard("ctrl+s")
        terminal.actions.click("submit")
        ```
    """

    def __init__(self, runtime: Any) -> None:
        self._runtime = runtime

    def perform(self, action: Action) -> None:
        """Queue or dispatch an action."""
        self._runtime.perform(action)

    def keyboard(
        self,
        *bindings: KeyboardBinding,
        kind: KeyboardEventKind = "press",
    ) -> None:
        """Perform keyboard actions."""
        for binding in bindings:
            self.perform(Action.keyboard(binding, kind=kind))

    def click(
        self,
        field: str | None = None,
        button: MouseButton = "left",
    ) -> None:
        """Perform a click action."""
        self.perform(Action.click(field, button))

    def request(self, method: str, path: str = "/") -> None:
        """Perform an HTTP request action."""
        self.perform(Action.request(method, path))


__all__ = (
    "Action",
    "Actions",
    "ClickAction",
    "ClipboardAction",
    "FocusAction",
    "FocusEventKind",
    "KeyboardAction",
    "KeyboardEventKind",
    "MouseAction",
    "MouseEventKind",
    "NormalizedBinding",
    "RequestAction",
    "ResizeAction",
    "TickAction",
    "normalize_binding",
)
