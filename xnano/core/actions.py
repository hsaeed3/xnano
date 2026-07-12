"""xnano.core.actions

---

An **Action** is the functional/object representation of an event trigger.

``events.py`` answers *"what happened"* (past tense, produced by device
adapters). ``actions.py`` answers *"what triggers / what to do"*
(declarative + imperative, produced by users and the framework).

Hooks bind Actions to handlers; a host performs Actions; devices are
just one source of Actions. Matching is centralized on
``Action.matches`` so terminal, web, and offscreen hosts share one
implementation.
"""

from __future__ import annotations

import abc
import dataclasses
from typing import Any, ClassVar, TypeAlias

from xnano._types import KeyboardBinding, MouseButton


KeyboardEventKindLike: TypeAlias = str
"""Keyboard event kind filter (``"press"`` / ``"release"`` / ``"repeat"``).

Typed as ``str`` at runtime to avoid an import cycle with ``events``;
call sites should pass ``KeyboardEventKind`` literals.
"""


MouseEventKindLike: TypeAlias = str
"""Mouse event kind filter (``"press"`` / ``"release"`` / ``"drag"``, ...).

Typed as ``str`` at runtime to avoid an import cycle with ``events``;
call sites should pass ``MouseEventKind`` literals.
"""


FocusEventKindLike: TypeAlias = str
"""Focus kind filter (``"gained"`` / ``"lost"`` / field variants).

Typed as ``str`` at runtime to avoid an import cycle with ``events``;
call sites should pass ``FocusEventKind`` or ``FocusHookKind``
literals.
"""


_KEY_ALIASES: dict[str, str] = {
    "escape": "esc",
    "return": "enter",
    " ": "space",
}
"""Aliases applied while normalizing ``ctrl+k`` style bindings."""


NormalizedBinding: TypeAlias = tuple[frozenset[str], str]
"""A normalized keyboard binding as ``(modifiers, key)``."""


def normalize_binding(binding: str) -> NormalizedBinding | None:
    """Normalize a ``ctrl+shift+k`` style binding for comparison.

    Shared by terminal, web, and synthetic keyboard matching so every
    host uses one grammar. Space is aliased to ``"space"``; only
    ``ctrl``, ``alt``, and ``shift`` are treated as modifiers.

    Args:
        binding: The binding string to normalize.

    Returns:
        A ``(modifiers, key)`` pair, or ``None`` for an empty binding.
    """
    parts = [part.strip().lower() for part in binding.split("+")]
    parts = [part for part in parts if part]
    if not parts:
        return None
    key = parts[-1]
    key = _KEY_ALIASES.get(key, key)
    modifiers = frozenset(
        part for part in parts[:-1] if part in ("ctrl", "alt", "shift")
    )
    return (modifiers, key)


def _event_keyboard_normalized(
    keyboard: Any,
) -> NormalizedBinding | None:
    """Resolve a keyboard payload to a normalized binding, if possible.

    Prefers an explicit ``binding`` property, then reconstructs from
    ``key`` + ``modifiers`` (or the private web synthetic fields).
    """
    binding = getattr(keyboard, "binding", None)
    if binding is not None:
        try:
            return normalize_binding(str(binding))
        except Exception:
            pass

    key = getattr(keyboard, "key", None)
    if key is None:
        key = getattr(keyboard, "_key", None)
    if key is None:
        return None

    mods = getattr(keyboard, "modifiers", None)
    if mods is None:
        mods = getattr(keyboard, "_modifiers", frozenset())
    if isinstance(mods, frozenset):
        mod_set = frozenset(
            str(part).lower()
            for part in mods
            if part is not None
            and str(part).lower() in ("ctrl", "alt", "shift")
        )
    else:
        mod_set = frozenset(
            str(part).lower()
            for part in (mods or ())
            if part is not None
            and str(part).lower() in ("ctrl", "alt", "shift")
        )

    key_text = str(key).strip().lower()
    key_text = _KEY_ALIASES.get(key_text, key_text)
    return (mod_set, key_text)


def _is_keyboard_event(event: Any) -> bool:
    checker = getattr(event, "is_keyboard_event", None)
    if callable(checker):
        return bool(checker())
    return getattr(event, "type", None) == "keyboard"


def _is_mouse_event(event: Any) -> bool:
    checker = getattr(event, "is_mouse_event", None)
    if callable(checker):
        return bool(checker())
    return getattr(event, "type", None) == "mouse"


def _is_resize_event(event: Any) -> bool:
    checker = getattr(event, "is_resize_event", None)
    if callable(checker):
        return bool(checker())
    return getattr(event, "type", None) == "resize"


def _is_clipboard_event(event: Any) -> bool:
    checker = getattr(event, "is_clipboard_event", None)
    if callable(checker):
        return bool(checker())
    return getattr(event, "type", None) == "clipboard"


def _is_focus_event(event: Any) -> bool:
    checker = getattr(event, "is_focus_event", None)
    if callable(checker):
        return bool(checker())
    return getattr(event, "type", None) == "focus"


def _synthesize_event(data: Any, *, kind: str | None = None) -> Any:
    """Build an event shell for ``to_event``.

    Prefers ``Event.from_data`` for terminal event families (keyboard,
    mouse, resize, clipboard, focus). Tick and request shells are not
    real ``Event`` types — force the duck-typed shell so
    ``is_tick_event`` / ``is_request_event`` and ``type`` stay honest.
    """
    terminal_kinds = {
        "keyboard",
        "mouse",
        "resize",
        "clipboard",
        "focus",
    }
    resolved_kind = kind
    if resolved_kind is None and data is not None:
        resolved_kind = getattr(data, "type", None)
    if resolved_kind not in terminal_kinds:
        return _SyntheticEvent(data, kind=kind)

    try:
        from xnano.events import Event as EventClass
    except Exception:
        return _SyntheticEvent(data, kind=kind)

    for name in ("synthesize", "from_data"):
        factory = getattr(EventClass, name, None)
        if callable(factory):
            try:
                return factory(data)
            except Exception:
                pass

    return _SyntheticEvent(data, kind=kind)


# ---------------------------------------------------------------------------
# Synthetic event shells (to_event until Event gains synthesize/from_data)
# ---------------------------------------------------------------------------


class _SyntheticKeyboardEventData:
    """Duck-typed keyboard payload produced by ``KeyboardAction.to_event``.

    Mirrors the surface hooks read from ``KeyboardEventData``: ``kind``,
    ``key``, ``modifiers``, ``character``, ``binding``, and ``matches``.
    """

    type: ClassVar[str] = "keyboard"

    def __init__(
        self,
        binding: str,
        *,
        kind: KeyboardEventKindLike | None = None,
    ) -> None:
        normalized = normalize_binding(binding) or (frozenset(), "")
        self._modifiers, self._key = normalized
        self.key: str = self._key
        self.modifiers: list[str] = sorted(self._modifiers)
        self.kind: str = kind if kind is not None else "press"
        if len(self._key) == 1:
            self.character: str | None = self._key
        elif self._key == "space":
            self.character = " "
        else:
            self.character = None

    @property
    def binding(self) -> str:
        """The ``xnano`` style keyboard binding for this synthetic event."""
        if self._modifiers:
            return f"{'+'.join(sorted(self._modifiers))}+{self._key}"
        return self._key

    def matches(self, *bindings: KeyboardBinding) -> bool:
        """Return whether this event matches any of ``bindings``."""
        for binding in bindings:
            if binding is None:
                return True
            if normalize_binding(str(binding)) == (
                self._modifiers,
                self._key,
            ):
                return True
        return False


class _SyntheticEvent:
    """Duck-typed ``Event`` shell carrying one synthesized sub-event.

    Handlers and shared dispatch only need ``is_*`` predicates plus the
    corresponding ``*_event`` properties — this shell provides that
    surface without requiring a live ``CoreEvent``.
    """

    def __init__(
        self,
        data: Any = None,
        *,
        kind: str | None = None,
    ) -> None:
        self._data = data
        if kind is not None:
            self._type = kind
        elif data is not None and hasattr(data, "type"):
            self._type = str(data.type)
        else:
            self._type = "other"

    @property
    def type(self) -> str:
        """Event data classification (``keyboard``, ``mouse``, ...)."""
        return self._type

    @property
    def data(self) -> Any:
        """Sub-event payload, when one was provided."""
        return self._data

    def is_clipboard_event(self) -> bool:
        """Return whether this is a clipboard event."""
        return self._type == "clipboard"

    def is_focus_event(self) -> bool:
        """Return whether this is a focus event."""
        return self._type == "focus"

    def is_keyboard_event(self) -> bool:
        """Return whether this is a keyboard event."""
        return self._type == "keyboard"

    def is_mouse_event(self) -> bool:
        """Return whether this is a mouse event."""
        return self._type == "mouse"

    def is_resize_event(self) -> bool:
        """Return whether this is a resize event."""
        return self._type == "resize"

    def is_tick_event(self) -> bool:
        """Return whether this is a synthetic tick event."""
        return self._type == "tick"

    def is_request_event(self) -> bool:
        """Return whether this is a synthetic HTTP request event."""
        return self._type == "request"

    @property
    def clipboard_event(self) -> Any | None:
        """Clipboard payload when ``type`` is ``"clipboard"``."""
        return self._data if self._type == "clipboard" else None

    @property
    def clipboard_text(self) -> str | None:
        """Pasted text when this is a clipboard event."""
        clip = self.clipboard_event
        if clip is None:
            return None
        return getattr(clip, "text", None)

    @property
    def focus_event(self) -> Any | None:
        """Focus payload when ``type`` is ``"focus"``."""
        return self._data if self._type == "focus" else None

    @property
    def keyboard_event(self) -> Any | None:
        """Keyboard payload when ``type`` is ``"keyboard"``."""
        return self._data if self._type == "keyboard" else None

    @property
    def mouse_event(self) -> Any | None:
        """Mouse payload when ``type`` is ``"mouse"``."""
        return self._data if self._type == "mouse" else None

    @property
    def resize_event(self) -> Any | None:
        """Resize payload when ``type`` is ``"resize"``."""
        return self._data if self._type == "resize" else None

    @property
    def request_event(self) -> Any | None:
        """Request payload when ``type`` is ``"request"``."""
        return self._data if self._type == "request" else None

    @property
    def tick_event(self) -> Any | None:
        """Tick payload when ``type`` is ``"tick"``."""
        return self._data if self._type == "tick" else None

    @property
    def mouse_button(self) -> MouseButton | None:
        """Mouse button when this is a mouse event."""
        mouse = self.mouse_event
        if mouse is None:
            return None
        return getattr(mouse, "button", None)

    @property
    def mouse_event_kind(self) -> str | None:
        """Mouse event kind when this is a mouse event."""
        mouse = self.mouse_event
        if mouse is None:
            return None
        return getattr(mouse, "kind", None)

    @property
    def mouse_position(self) -> tuple[int, int] | None:
        """Mouse coordinates when this is a mouse event."""
        mouse = self.mouse_event
        if mouse is None:
            return None
        x = getattr(mouse, "x", None)
        y = getattr(mouse, "y", None)
        if x is None or y is None:
            return None
        return (int(x), int(y))

    @property
    def resize_size(self) -> tuple[int, int] | None:
        """New terminal size when this is a resize event."""
        resize = self.resize_event
        if resize is None:
            return None
        width = getattr(resize, "width", None)
        height = getattr(resize, "height", None)
        if width is None or height is None:
            return None
        return (int(width), int(height))

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"type={self._type!r}, "
            f"data={self._data!r})"
        )


@dataclasses.dataclass(slots=True, frozen=True)
class _SyntheticTickData:
    """Payload carried by a synthetic tick event."""

    type: ClassVar[str] = "tick"
    interval_ms: int = 0
    """Tick interval in milliseconds (0 means every tick)."""


@dataclasses.dataclass(slots=True, frozen=True)
class _SyntheticRequestData:
    """Payload carried by a synthetic HTTP request event."""

    type: ClassVar[str] = "request"
    method: str
    """HTTP method (``GET`` / ``POST`` / …)."""
    path: str
    """Request path (e.g. ``"/save"``)."""


# ---------------------------------------------------------------------------
# Action hierarchy
# ---------------------------------------------------------------------------


@dataclasses.dataclass(slots=True, frozen=True)
class Action(abc.ABC):
    """Functional representation of an event trigger.

    Subclasses mirror event families and carry the filters that
    ``@on_*`` hooks already express as decorator arguments. Factory
    classmethods keep construction readable:

        SAVE = Action.keyboard("ctrl+s")
        CLICK = Action.click("save_button")
        POST = Action.request("POST", "/save")
    """

    @classmethod
    def keyboard(
        cls,
        *bindings: KeyboardBinding,
        kind: KeyboardEventKindLike | None = None,
    ) -> KeyboardAction:
        """Build a keyboard action for one or more bindings.

        Args:
            *bindings: Key bindings (e.g. ``"ctrl+s"``). Empty means
                any keyboard event.
            kind: Optional press/release/repeat filter.

        Returns:
            A frozen ``KeyboardAction``.
        """
        return KeyboardAction(bindings=bindings, kind=kind)

    @classmethod
    def mouse(
        cls,
        *buttons: MouseButton,
        kind: MouseEventKindLike | None = None,
    ) -> MouseAction:
        """Build a mouse action for one or more buttons.

        Args:
            *buttons: Mouse buttons to match. Empty means any button.
            kind: Optional mouse event kind filter.

        Returns:
            A frozen ``MouseAction``.
        """
        return MouseAction(buttons=buttons, kind=kind)

    @classmethod
    def click(
        cls,
        field: str | None = None,
        button: MouseButton = "left",
    ) -> ClickAction:
        """Build a click action (mouse press on a button).

        Args:
            field: Optional layout field name (host-side scope metadata).
            button: Mouse button; defaults to ``"left"``.

        Returns:
            A frozen ``ClickAction``.
        """
        return ClickAction(field=field, button=button)

    @classmethod
    def focus(
        cls,
        field: str | None = None,
        kind: FocusEventKindLike | None = None,
    ) -> FocusAction:
        """Build a focus action for window or field focus changes.

        Args:
            field: Optional layout field name for field-level focus.
            kind: Optional ``"gained"`` / ``"lost"`` (or field variant).

        Returns:
            A frozen ``FocusAction``.
        """
        return FocusAction(field=field, kind=kind)

    @classmethod
    def clipboard(cls, text: str | None = None) -> ClipboardAction:
        """Build a clipboard (paste) action.

        Args:
            text: Optional exact paste text to match. ``None`` matches
                any clipboard event.

        Returns:
            A frozen ``ClipboardAction``.
        """
        return ClipboardAction(text=text)

    @classmethod
    def tick(cls, interval_ms: int = 0) -> TickAction:
        """Build a tick action.

        Args:
            interval_ms: Interval in milliseconds; ``0`` means every
                host tick.

        Returns:
            A frozen ``TickAction``.
        """
        return TickAction(interval_ms=interval_ms)

    @classmethod
    def resize(
        cls,
        width: int | None = None,
        height: int | None = None,
    ) -> ResizeAction:
        """Build a terminal resize action.

        Args:
            width: Optional exact width filter in cells.
            height: Optional exact height filter in cells.

        Returns:
            A frozen ``ResizeAction``.
        """
        return ResizeAction(width=width, height=height)

    @classmethod
    def request(cls, method: str, path: str) -> RequestAction:
        """Build an HTTP request action (web host routes).

        Args:
            method: HTTP method (``"GET"``, ``"POST"``, …).
            path: Request path (e.g. ``"/save"``).

        Returns:
            A frozen ``RequestAction``.
        """
        return RequestAction(method=method, path=path)

    @abc.abstractmethod
    def matches(self, event: Any) -> bool:
        """Return whether ``event`` satisfies this action's filters.

        Args:
            event: A real ``Event`` or a duck-typed synthetic shell.

        Returns:
            ``True`` when the event matches this action.
        """

    @abc.abstractmethod
    def to_event(self) -> Any:
        """Synthesize an event shell equivalent to this action.

        Returns:
            An ``Event`` when a synthesize path exists, otherwise a
            duck-typed shell with the same ``is_*`` / ``*_event``
            surface handlers already consume.
        """


@dataclasses.dataclass(slots=True, frozen=True)
class KeyboardAction(Action):
    """Keyboard trigger — bindings and optional press/release/repeat kind.

    Attributes:
        bindings: Key bindings to match. Empty matches any keyboard
            event (same semantics as an unfiltered ``@on_keyboard``).
        kind: Optional ``"press"`` / ``"release"`` / ``"repeat"`` filter.
    """

    bindings: tuple[KeyboardBinding, ...] = ()
    """Key bindings (``"ctrl+s"``, ``"enter"``, …). Empty = any key."""
    kind: KeyboardEventKindLike | None = None
    """Optional keyboard event kind filter."""

    def matches(self, event: Any) -> bool:
        """Match keyboard events using native or normalized bindings.

        Empty ``bindings`` match any keyboard event. Otherwise each
        binding is tried via ``keyboard_event.matches`` (native
        ``CoreKeyBinding`` path) and, when that fails (synthetic web /
        ``to_event`` shells), via ``normalize_binding`` equality.

        Args:
            event: Event or duck-typed shell to test.

        Returns:
            Whether the event is a matching keyboard event.
        """
        if not _is_keyboard_event(event):
            return False
        keyboard = getattr(event, "keyboard_event", None)
        if keyboard is None:
            return False
        if self.kind is not None and getattr(keyboard, "kind", None) != (
            self.kind
        ):
            return False
        if not self.bindings:
            return True

        actual = _event_keyboard_normalized(keyboard)
        for binding in self.bindings:
            if binding is None:
                return True
            try:
                if keyboard.matches(binding):
                    return True
            except Exception:
                pass
            wanted = normalize_binding(str(binding))
            if wanted is not None and actual is not None and wanted == actual:
                return True
        return False

    def to_event(self) -> Any:
        """Synthesize a keyboard event for the first binding.

        Returns:
            A real ``Event`` built via ``KeyboardEventData.from_binding``
            when possible; falls back to a synthetic shell.
        """
        binding = str(self.bindings[0]) if self.bindings else ""
        kind = self.kind if self.kind is not None else "press"
        try:
            from typing import cast

            from xnano.events import (
                Event,
                KeyboardEventData,
                KeyboardEventKind,
            )

            kind_value = cast(
                KeyboardEventKind,
                kind if kind in ("press", "release", "repeat") else "press",
            )
            data = KeyboardEventData.from_binding(binding, kind=kind_value)
            return Event.from_data(data)
        except Exception:
            data = _SyntheticKeyboardEventData(binding, kind=self.kind)
            return _synthesize_event(data, kind="keyboard")


@dataclasses.dataclass(slots=True, frozen=True)
class MouseAction(Action):
    """Mouse trigger — buttons and optional event kind.

    Attributes:
        buttons: Buttons to match. Empty matches any button.
        kind: Optional mouse event kind filter.
    """

    buttons: tuple[MouseButton, ...] = ()
    """Mouse buttons (``"left"``, ``"right"``, ``"middle"``, ...)."""
    kind: MouseEventKindLike | None = None
    """Optional mouse event kind filter."""

    def matches(self, event: Any) -> bool:
        """Match mouse events by button and optional kind.

        Mirrors ``_dispatch.mouse_matches``: empty ``buttons`` match any
        button; ``kind`` filters when set.

        Args:
            event: Event or duck-typed shell to test.

        Returns:
            Whether the event is a matching mouse event.
        """
        if not _is_mouse_event(event):
            return False
        mouse = getattr(event, "mouse_event", None)
        if mouse is None:
            return False
        if self.kind is not None and getattr(mouse, "kind", None) != (
            self.kind
        ):
            return False
        if not self.buttons:
            return True
        return getattr(mouse, "button", None) in self.buttons

    def to_event(self) -> Any:
        """Synthesize a mouse event for the first button (or left).

        Returns:
            An event shell carrying ``MouseEventData``.
        """
        from typing import cast

        from xnano.events import MouseEventData, MouseEventKind

        button: MouseButton = self.buttons[0] if self.buttons else "left"
        raw_kind: MouseEventKindLike = (
            self.kind if self.kind is not None else "press"
        )
        data = MouseEventData(
            kind=cast(MouseEventKind, raw_kind),
            x=0,
            y=0,
            button=button,
        )
        return _synthesize_event(data, kind="mouse")


@dataclasses.dataclass(slots=True, frozen=True)
class ClickAction(Action):
    """Click trigger — mouse press on a button, optional field scope.

    ``field`` is host-side metadata (which layout region was clicked).
    ``matches`` only checks button + press kind; resolving the field
    hit-test remains the host's responsibility.

    Attributes:
        field: Optional layout field name.
        button: Mouse button; defaults to ``"left"``.
        kind: Mouse kind; defaults to ``"press"``.
    """

    field: str | None = None
    """Layout field name for host-side click targeting."""
    button: MouseButton = "left"
    """Mouse button that constitutes the click."""
    kind: MouseEventKindLike = "press"
    """Mouse event kind; clicks are presses by default."""

    def matches(self, event: Any) -> bool:
        """Match a mouse press on this action's button.

        Field scoping is intentionally ignored here — the host maps
        coordinates / target ids onto ``field`` before dispatch.

        Args:
            event: Event or duck-typed shell to test.

        Returns:
            Whether the event is a matching button press.
        """
        if not _is_mouse_event(event):
            return False
        mouse = getattr(event, "mouse_event", None)
        if mouse is None:
            return False
        if getattr(mouse, "kind", None) != self.kind:
            return False
        return getattr(mouse, "button", None) == self.button

    def to_event(self) -> Any:
        """Synthesize a mouse press event for this click.

        Returns:
            An event shell carrying ``MouseEventData``.
        """
        from typing import cast

        from xnano.events import MouseEventData, MouseEventKind

        data = MouseEventData(
            kind=cast(MouseEventKind, self.kind),
            x=0,
            y=0,
            button=self.button,
        )
        return _synthesize_event(data, kind="mouse")


@dataclasses.dataclass(slots=True, frozen=True)
class FocusAction(Action):
    """Focus trigger — terminal window or grid field focus changes.

    Attributes:
        field: Optional layout field name for field-level focus.
        kind: Optional ``"gained"`` / ``"lost"`` (also accepts
            ``"field_gained"`` / ``"field_lost"``).
    """

    field: str | None = None
    """Layout field name for field-level focus; ``None`` is any/window."""
    kind: FocusEventKindLike | None = None
    """Optional focus transition kind filter."""

    def matches(self, event: Any) -> bool:
        """Match focus events by optional field and kind filters.

        ``"gained"`` / ``"lost"`` also accept the field-scoped
        ``"field_gained"`` / ``"field_lost"`` event kinds (and vice
        versa) so hook filters and raw event kinds interoperate.

        Args:
            event: Event or duck-typed shell to test.

        Returns:
            Whether the event is a matching focus event.
        """
        if not _is_focus_event(event):
            return False
        focus = getattr(event, "focus_event", None)
        if focus is None:
            return False

        event_field = getattr(focus, "field", None)
        event_kind = getattr(focus, "kind", None)

        if self.field is not None and event_field != self.field:
            return False

        if self.kind is None:
            return True

        return _focus_kinds_compatible(self.kind, event_kind)

    def to_event(self) -> Any:
        """Synthesize a focus event for this action.

        Returns:
            An event shell carrying ``FocusEventData``.
        """
        from typing import cast

        from xnano.events import FocusEventData, FocusEventKind

        kind: str | None = self.kind
        if kind is None:
            if self.field is not None:
                kind = "field_gained"
            else:
                kind = "gained"
        elif self.field is not None and kind in ("gained", "lost"):
            kind = f"field_{kind}"

        data = FocusEventData(
            kind=cast(FocusEventKind | None, kind),
            field=self.field,
        )
        return _synthesize_event(data, kind="focus")


def _focus_kinds_compatible(
    wanted: str,
    actual: str | None,
) -> bool:
    """Return whether a focus kind filter accepts an event kind."""
    if actual is None:
        return False
    if wanted == actual:
        return True
    if wanted == "gained" and actual in ("gained", "field_gained"):
        return True
    if wanted == "lost" and actual in ("lost", "field_lost"):
        return True
    if wanted == "field_gained" and actual in ("gained", "field_gained"):
        return True
    if wanted == "field_lost" and actual in ("lost", "field_lost"):
        return True
    return False


@dataclasses.dataclass(slots=True, frozen=True)
class ClipboardAction(Action):
    """Clipboard (paste) trigger.

    Attributes:
        text: Optional exact paste text. ``None`` matches any paste.
    """

    text: str | None = None
    """Paste text filter; ``None`` matches any clipboard event."""

    def matches(self, event: Any) -> bool:
        """Match clipboard events, optionally by exact paste text.

        Args:
            event: Event or duck-typed shell to test.

        Returns:
            Whether the event is a matching clipboard event.
        """
        if not _is_clipboard_event(event):
            return False
        if self.text is None:
            return True
        clip = getattr(event, "clipboard_event", None)
        if clip is None:
            text = getattr(event, "clipboard_text", None)
            return text == self.text
        return getattr(clip, "text", None) == self.text

    def to_event(self) -> Any:
        """Synthesize a clipboard paste event.

        Returns:
            An event shell carrying ``ClipboardEventData``.
        """
        from xnano.events import ClipboardEventData

        data = ClipboardEventData(text=self.text)
        return _synthesize_event(data, kind="clipboard")


@dataclasses.dataclass(slots=True, frozen=True)
class TickAction(Action):
    """Tick trigger — interval-gated host clock callbacks.

    Ticks are not terminal ``Event`` values. ``matches`` returns
    ``False`` for ordinary events unless the shell advertises tick
    metadata (``is_tick_event`` / ``type == "tick"``).

    Attributes:
        interval_ms: Interval in milliseconds; ``0`` means every tick.
    """

    interval_ms: int = 0
    """Tick interval in milliseconds (0 = every host tick)."""

    def matches(self, event: Any) -> bool:
        """Match only synthetic/tick-aware shells, never plain Events.

        Args:
            event: Event or duck-typed shell to test.

        Returns:
            ``True`` only when the payload is tick-shaped.
        """
        if event is None:
            return False
        checker = getattr(event, "is_tick_event", None)
        if callable(checker) and checker():
            tick = getattr(event, "tick_event", None)
            if tick is None:
                return True
            interval = getattr(tick, "interval_ms", None)
            if interval is None:
                return True
            # 0 on either side means "any / every tick".
            if self.interval_ms == 0 or interval == 0:
                return True
            return int(interval) == self.interval_ms
        return getattr(event, "type", None) == "tick"

    def to_event(self) -> Any:
        """Synthesize a tick-shaped event shell.

        Returns:
            A duck-typed shell with ``type == "tick"``. Hosts that pump
            ticks outside the event path may ignore this.
        """
        data = _SyntheticTickData(interval_ms=self.interval_ms)
        return _synthesize_event(data, kind="tick")


@dataclasses.dataclass(slots=True, frozen=True)
class ResizeAction(Action):
    """Terminal resize trigger — optional exact size filters.

    Attributes:
        width: Optional exact width in cells.
        height: Optional exact height in cells.
    """

    width: int | None = None
    """Optional exact width filter in character cells."""
    height: int | None = None
    """Optional exact height filter in character cells."""

    def matches(self, event: Any) -> bool:
        """Match resize events, optionally by exact dimensions.

        Args:
            event: Event or duck-typed shell to test.

        Returns:
            Whether the event is a matching resize event.
        """
        if not _is_resize_event(event):
            return False
        if self.width is None and self.height is None:
            return True

        resize = getattr(event, "resize_event", None)
        if resize is not None:
            width = getattr(resize, "width", None)
            height = getattr(resize, "height", None)
        else:
            size = getattr(event, "resize_size", None)
            if size is None:
                return False
            width, height = size

        if self.width is not None and width != self.width:
            return False
        if self.height is not None and height != self.height:
            return False
        return True

    def to_event(self) -> Any:
        """Synthesize a resize event.

        Returns:
            An event shell carrying ``ResizeEventData``. Unspecified
            dimensions default to ``80x24``.
        """
        from xnano.events import ResizeEventData

        data = ResizeEventData(
            width=self.width if self.width is not None else 80,
            height=self.height if self.height is not None else 24,
        )
        return _synthesize_event(data, kind="resize")


@dataclasses.dataclass(slots=True, frozen=True)
class RequestAction(Action):
    """HTTP request trigger for web host routes.

    Not produced by terminal ``Event`` adapters. ``matches`` returns
    ``False`` for ordinary events unless the shell advertises request
    metadata.

    Attributes:
        method: HTTP method (``"GET"``, ``"POST"``, …).
        path: Request path (e.g. ``"/save"``).
    """

    method: str
    """HTTP method string."""
    path: str
    """Request path."""

    def matches(self, event: Any) -> bool:
        """Match only request-shaped shells, never plain terminal Events.

        Args:
            event: Event or duck-typed shell to test.

        Returns:
            ``True`` only when the payload is an HTTP request shell
            with compatible method and path.
        """
        if event is None:
            return False
        checker = getattr(event, "is_request_event", None)
        if not (callable(checker) and checker()):
            if getattr(event, "type", None) != "request":
                return False
        request = getattr(event, "request_event", None)
        if request is None:
            request = getattr(event, "data", None)
        if request is None:
            return False
        method = getattr(request, "method", None)
        path = getattr(request, "path", None)
        if method is not None and str(method).upper() != self.method.upper():
            return False
        if path is not None and path != self.path:
            return False
        return True

    def to_event(self) -> Any:
        """Synthesize a request-shaped event shell.

        Returns:
            A duck-typed shell with ``type == "request"``. Web hosts
            dispatch requests outside the terminal event path.
        """
        data = _SyntheticRequestData(
            method=self.method.upper(),
            path=self.path,
        )
        return _synthesize_event(data, kind="request")


# ---------------------------------------------------------------------------
# Hook-entry helpers (registry fields → Action)
# ---------------------------------------------------------------------------


def keyboard_action_from_filter(
    bindings: tuple[KeyboardBinding, ...] | list[KeyboardBinding],
    kind: KeyboardEventKindLike | None = None,
) -> KeyboardAction:
    """Build a ``KeyboardAction`` from an ``@on_keyboard`` filter tuple.

    Args:
        bindings: Binding strings from the hook registry entry.
        kind: Optional keyboard kind filter from the registry.

    Returns:
        The corresponding ``KeyboardAction``.
    """
    return KeyboardAction(bindings=tuple(bindings), kind=kind)


def mouse_action_from_filter(
    buttons: tuple[MouseButton, ...] | list[MouseButton],
    kind: MouseEventKindLike | None = None,
) -> MouseAction:
    """Build a ``MouseAction`` from an ``@on_mouse`` filter tuple.

    Args:
        buttons: Button names from the hook registry entry.
        kind: Optional mouse kind filter from the registry.

    Returns:
        The corresponding ``MouseAction``.
    """
    return MouseAction(buttons=tuple(buttons), kind=kind)


def click_action_from_filter(
    field: str | None,
    button: MouseButton = "left",
    kind: MouseEventKindLike = "press",
) -> ClickAction:
    """Build a ``ClickAction`` from field mouse-handler metadata.

    Args:
        field: Layout field name bound to the handler.
        button: Mouse button filter.
        kind: Mouse kind filter (default ``"press"``).

    Returns:
        The corresponding ``ClickAction``.
    """
    return ClickAction(field=field, button=button, kind=kind)


def focus_action_from_filter(
    field: str | None = None,
    kind: FocusEventKindLike | None = None,
) -> FocusAction:
    """Build a ``FocusAction`` from an ``@on_focus`` registry entry.

    Args:
        field: Optional field name from the registry.
        kind: Optional ``"gained"`` / ``"lost"`` filter.

    Returns:
        The corresponding ``FocusAction``.
    """
    return FocusAction(field=field, kind=kind)


def tick_action_from_filter(interval_ms: int = 0) -> TickAction:
    """Build a ``TickAction`` from an ``@on_tick`` interval.

    Args:
        interval_ms: Tick interval in milliseconds.

    Returns:
        The corresponding ``TickAction``.
    """
    return TickAction(interval_ms=interval_ms)


def request_action_from_filter(method: str, path: str) -> RequestAction:
    """Build a ``RequestAction`` from an ``@on_*_request`` entry.

    Args:
        method: HTTP method.
        path: Request path.

    Returns:
        The corresponding ``RequestAction``.
    """
    return RequestAction(method=method, path=path)


# ---------------------------------------------------------------------------
# Host-bound helpers
# ---------------------------------------------------------------------------


class Actions:
    """Perform actions against a live host from hooks or app code.

    Available as ``ctx.actions`` / ``host.actions``. ``perform``
    delegates to ``host.perform(action)`` — hosts synthesize the event
    and run the shared dispatch pump (queuing re-entrant performs until
    the current pass completes).
    """

    def __init__(self, host: Any) -> None:
        """Bind this helper to a live host.

        Args:
            host: Terminal, web session, or any object implementing
                ``perform(action)``.
        """
        self._host = host

    @property
    def host(self) -> Any:
        """The bound host actions are performed against."""
        return self._host

    def perform(self, action: Action) -> None:
        """Perform ``action`` on the bound host.

        Args:
            action: The action to perform.

        Raises:
            RuntimeError: If the host does not implement ``perform``.
        """
        perform = getattr(self._host, "perform", None)
        if not callable(perform):
            raise RuntimeError(
                f"Host {self._host!r} does not implement "
                "perform(action). Actions require a host that "
                "synthesizes events and runs the shared dispatch "
                "pump."
            )
        perform(action)

    def press(
        self,
        *bindings: KeyboardBinding,
        kind: KeyboardEventKindLike | None = None,
    ) -> None:
        """Perform a keyboard action for ``bindings``.

        Args:
            *bindings: Key bindings to press (e.g. ``"ctrl+s"``).
            kind: Optional press/release/repeat kind.
        """
        self.perform(Action.keyboard(*bindings, kind=kind))

    def click(
        self,
        field: str | None = None,
        button: MouseButton = "left",
    ) -> None:
        """Perform a click action on an optional field.

        Args:
            field: Optional layout field name.
            button: Mouse button; defaults to ``"left"``.
        """
        self.perform(Action.click(field, button=button))

    def request(self, method: str, path: str) -> None:
        """Perform an HTTP request action.

        Args:
            method: HTTP method.
            path: Request path.
        """
        self.perform(Action.request(method, path))

    def focus(
        self,
        field: str | None = None,
        kind: FocusEventKindLike | None = None,
    ) -> None:
        """Perform a focus action.

        Args:
            field: Optional layout field name.
            kind: Optional focus kind filter.
        """
        self.perform(Action.focus(field=field, kind=kind))

    def paste(self, text: str | None = None) -> None:
        """Perform a clipboard paste action.

        Args:
            text: Optional paste payload.
        """
        self.perform(Action.clipboard(text=text))

    def resize(
        self,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """Perform a resize action.

        Args:
            width: Optional width in cells.
            height: Optional height in cells.
        """
        self.perform(Action.resize(width=width, height=height))

    def tick(self, interval_ms: int = 0) -> None:
        """Perform a tick action.

        Args:
            interval_ms: Interval in milliseconds.
        """
        self.perform(Action.tick(interval_ms=interval_ms))


__all__ = (
    "Action",
    "Actions",
    "KeyboardAction",
    "MouseAction",
    "ClickAction",
    "FocusAction",
    "ClipboardAction",
    "TickAction",
    "ResizeAction",
    "RequestAction",
    "NormalizedBinding",
    "normalize_binding",
    "keyboard_action_from_filter",
    "mouse_action_from_filter",
    "click_action_from_filter",
    "focus_action_from_filter",
    "tick_action_from_filter",
    "request_action_from_filter",
)
