"""tests.helpers"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, cast

from xnano.fields import Field, UNSET

if TYPE_CHECKING:
    from xnano.components.abstract import AbstractComponent
    from xnano.core.nodes.terminal import AbstractTerminalNode
    from xnano.grid import Grid
    from xnano.terminal import Terminal


def invalid_field(default: Any) -> Any:
    """Mark an intentionally invalid ``Field(default=...)`` for negative tests."""
    return cast(Any, Field(default=default))  # type: ignore


def assign_attr(instance: object, name: str, value: object) -> None:
    """Assign an attribute while bypassing static type checks in tests."""
    setattr(instance, name, value)


# ---------------------------------------------------------------------------
# Usage-test harness — fake input events + offscreen terminal helpers
# ---------------------------------------------------------------------------


class FakeKeyboard:
    """Duck-typed keyboard payload accepted by dispatch/focus paths."""

    def __init__(
        self,
        *,
        character: str | None = None,
        matches: Iterable[str] = (),
        kind: str = "press",
    ) -> None:
        self.character = character
        self.kind = kind
        self._matches = set(matches)

    def matches(self, *bindings: str) -> bool:
        return any(binding in self._matches for binding in bindings)


class FakeEvent:
    """Minimal event shell for ``dispatch_hooks`` / ``Context`` tests."""

    def __init__(
        self,
        *,
        keyboard: FakeKeyboard | None = None,
        clipboard_text: str | None = None,
        focus_kind: str | None = None,
        focus_field: str | None = None,
    ) -> None:
        self._keyboard = keyboard
        self._clipboard_text = clipboard_text
        self._focus_kind = focus_kind
        self._focus_field = focus_field

    def is_keyboard_event(self) -> bool:
        return self._keyboard is not None

    def is_mouse_event(self) -> bool:
        return False

    def is_resize_event(self) -> bool:
        return False

    def is_clipboard_event(self) -> bool:
        return self._clipboard_text is not None

    def is_focus_event(self) -> bool:
        return self._focus_kind is not None

    @property
    def keyboard_event(self) -> FakeKeyboard | None:
        return self._keyboard

    @property
    def clipboard_event(self) -> Any:
        if self._clipboard_text is None:
            return None

        class _Clip:
            text: str

            def __init__(self, text: str) -> None:
                self.text = text

        return _Clip(self._clipboard_text)

    @property
    def focus_event(self) -> Any:
        if self._focus_kind is None:
            return None

        class _Focus:
            kind: str | None
            field: str | None

            def __init__(self, kind: str, field: str | None) -> None:
                self.kind = kind
                self.field = field

        return _Focus(self._focus_kind, self._focus_field)

    @property
    def mouse_event(self) -> None:
        return None


def key_char(character: str) -> FakeKeyboard:
    """Printable character keypress."""
    return FakeKeyboard(character=character)


def key_binding(*names: str) -> FakeKeyboard:
    """Named key (enter, tab, backspace, …)."""
    return FakeKeyboard(matches=names)


def open_offscreen_app(
    grid: "Grid",
    *,
    cols: int = 48,
    rows: int = 14,
    state: Any = None,
) -> "Terminal[Any]":
    """Open an offscreen terminal, attach ``grid``, paint one frame.

    Caller should call :func:`close_offscreen_app` when finished.
    """
    from xnano.terminal import Terminal

    terminal = Terminal.offscreen(cols=cols, rows=rows, state=state)
    terminal.attach_grid(grid)
    terminal._render_frame(grid)
    return terminal


def close_offscreen_app(terminal: "Terminal[Any]") -> None:
    """Reset the active-terminal context var for an offscreen session."""
    import xnano.terminal as terminal_mod

    token = getattr(terminal, "_terminal_token", None)
    if token is not None:
        terminal_mod._ACTIVE_TERMINAL.reset(token)
        terminal._terminal_token = None
    terminal._is_live = False
    terminal._session = None


def paint(terminal: "Terminal[Any]", grid: "Grid") -> str:
    """Re-render ``grid`` and return the offscreen buffer text."""
    terminal._render_frame(grid)
    return terminal.get_output()


def dispatch_key(terminal: "Terminal[Any]", keyboard: FakeKeyboard) -> None:
    """Run the full keyboard dispatch path for ``keyboard``."""
    from xnano.context import Context
    from xnano.core.dispatch import dispatch_hooks

    event = FakeEvent(keyboard=keyboard)
    ctx = Context(
        event=cast(Any, event), terminal=terminal, state=terminal.state
    )
    dispatch_hooks(terminal, ctx)


def type_text(terminal: "Terminal[Any]", text: str) -> None:
    """Type each character of ``text`` through dispatch."""
    for character in text:
        dispatch_key(terminal, key_char(character))


def press(terminal: "Terminal[Any]", *bindings: str) -> None:
    """Press a named key (or chord label) through dispatch."""
    dispatch_key(terminal, key_binding(*bindings))


def render_node_to_text(
    node: "AbstractTerminalNode",
    *,
    width: int = 40,
    height: int = 10,
) -> str:
    """Render a single terminal render node offscreen and return the buffer text.

    Args:
        node: The ``AbstractTerminalNode`` to lower and render.
        width: Offscreen viewport width in cells.
        height: Offscreen viewport height in cells.

    Returns:
        The rendered buffer as a newline-joined string.
    """
    from xnano_core.core import CoreSession

    from xnano.core.controllers.terminal import TerminalController
    from xnano.types import Area

    core = CoreSession.offscreen(width=width, height=height)
    session = TerminalController(
        core,
        terminal_width=width,
        terminal_height=height,
        is_offscreen=True,
    )
    session.begin_viewport_frame()
    session.paint_node(node, Area(x=0, y=0, width=width, height=height))
    session.commit_requests()
    return session.get_core_session_output_text()


def render_component_to_text(
    component: "AbstractComponent",
    *,
    width: int = 40,
    height: int = 10,
) -> str:
    """Render a component offscreen via ``get_terminal_node`` and return the
    buffer text.

    Args:
        component: The ``AbstractComponent`` to render.
        width: Offscreen viewport width in cells.
        height: Offscreen viewport height in cells.

    Returns:
        The rendered buffer as a newline-joined string. Empty when the
        component yields no node (e.g. ``visible=False``).
    """
    from xnano.components.abstract import ComponentRenderContext
    from xnano.types import Area

    area = Area(x=0, y=0, width=width, height=height)
    ctx = ComponentRenderContext(area=area)
    node = component.get_terminal_node(ctx)
    if node is None:
        return ""
    return render_node_to_text(node, width=width, height=height)
