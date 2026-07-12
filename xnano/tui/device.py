"""xnano.tui.device"""

from __future__ import annotations

from typing import Any, Literal, TypeAlias, TYPE_CHECKING

from xnano_core.rust import native

from xnano.core.device import AbstractDevice
from xnano._types import Size

if TYPE_CHECKING:
    from xnano.tui.terminal import Terminal


ClearType: TypeAlias = Literal[
    "all",
    "purge",
    "from_cursor_down",
    "from_cursor_up",
    "current_line",
    "until_new_line",
]


_NATIVE_CLEAR_TYPES: dict[ClearType, Any] = {
    "all": native.ClearType.All,
    "purge": native.ClearType.Purge,
    "from_cursor_down": native.ClearType.FromCursorDown,
    "from_cursor_up": native.ClearType.FromCursorUp,
    "current_line": native.ClearType.CurrentLine,
    "until_new_line": native.ClearType.UntilNewLine,
}


class TerminalDevice(AbstractDevice):
    """Accessor/controller to the terminal device settings during an
    active session.

    NOTE: This class should not be initialized on its own and is
    instead accessible through a live ``Terminal`` session.
    """

    __slots__ = (
        "_terminal",
        "_raw_mode",
        "_alternate_screen",
        "_line_wrap",
        "_mouse_capture",
        "_bracketed_paste",
        "_focus_change",
        "_synchronized_updates",
    )

    def __init__(self, _terminal: "Terminal[Any]") -> None:
        from xnano.tui.terminal import Terminal

        if not isinstance(_terminal, Terminal):
            raise TypeError("`_terminal` must be a live `Terminal` session.")
        self._terminal = _terminal
        self._raw_mode: bool = False
        self._alternate_screen: bool = False
        self._line_wrap: bool = True
        self._mouse_capture: bool = False
        self._bracketed_paste: bool = False
        self._focus_change: bool = False
        self._synchronized_updates: bool = False

    @property
    def raw_mode(self) -> bool:
        return self._raw_mode

    @raw_mode.setter
    def raw_mode(self, value: bool) -> None:
        from xnano.core.controllers.tui import SESSION_DEVICE_LOCK

        with SESSION_DEVICE_LOCK:
            self._raw_mode = value
            if value:
                native.enable_raw_mode()
            else:
                native.disable_raw_mode()

    @property
    def alternate_screen(self) -> bool:
        return self._alternate_screen

    @alternate_screen.setter
    def alternate_screen(self, value: bool) -> None:
        from xnano.core.controllers.tui import SESSION_DEVICE_LOCK

        with SESSION_DEVICE_LOCK:
            self._alternate_screen = value
            if value:
                native.enter_alternate_screen()
            else:
                native.leave_alternate_screen()

    @property
    def line_wrap(self) -> bool:
        return self._line_wrap

    @line_wrap.setter
    def line_wrap(self, value: bool) -> None:
        from xnano.core.controllers.tui import SESSION_DEVICE_LOCK

        with SESSION_DEVICE_LOCK:
            self._line_wrap = value
            if value:
                native.enable_line_wrap()
            else:
                native.disable_line_wrap()

    @property
    def mouse_capture(self) -> bool:
        return self._mouse_capture

    @mouse_capture.setter
    def mouse_capture(self, value: bool) -> None:
        from xnano.core.controllers.tui import SESSION_DEVICE_LOCK

        with SESSION_DEVICE_LOCK:
            self._mouse_capture = value
            if value:
                native.enable_mouse_capture()
            else:
                native.disable_mouse_capture()

    @property
    def bracketed_paste(self) -> bool:
        return self._bracketed_paste

    @bracketed_paste.setter
    def bracketed_paste(self, value: bool) -> None:
        from xnano.core.controllers.tui import SESSION_DEVICE_LOCK

        with SESSION_DEVICE_LOCK:
            self._bracketed_paste = value
            if value:
                native.enable_bracketed_paste()
            else:
                native.disable_bracketed_paste()

    @property
    def focus_change(self) -> bool:
        return self._focus_change

    @focus_change.setter
    def focus_change(self, value: bool) -> None:
        from xnano.core.controllers.tui import SESSION_DEVICE_LOCK

        with SESSION_DEVICE_LOCK:
            self._focus_change = value
            if value:
                native.enable_focus_change()
            else:
                native.disable_focus_change()

    @property
    def synchronized_updates(self) -> bool:
        return self._synchronized_updates

    @synchronized_updates.setter
    def synchronized_updates(self, value: bool) -> None:
        from xnano.core.controllers.tui import SESSION_DEVICE_LOCK

        with SESSION_DEVICE_LOCK:
            self._synchronized_updates = value
            if value:
                native.begin_synchronized_update()
            else:
                native.end_synchronized_update()

    def set_title(self, title: str) -> None:
        """Set the terminal window title."""
        from xnano.core.controllers.tui import SESSION_DEVICE_LOCK

        with SESSION_DEVICE_LOCK:
            native.set_terminal_title(title)

    def clear(self, kind: ClearType = "all") -> None:
        """Clear the terminal display."""
        from xnano.core.controllers.tui import SESSION_DEVICE_LOCK

        with SESSION_DEVICE_LOCK:
            native.clear_terminal(_NATIVE_CLEAR_TYPES[kind])

    def scroll_up(self, n: int = 1) -> None:
        """Scroll the terminal up by ``n`` lines."""
        from xnano.core.controllers.tui import SESSION_DEVICE_LOCK

        with SESSION_DEVICE_LOCK:
            native.scroll_up(n)

    def scroll_down(self, n: int = 1) -> None:
        """Scroll the terminal down by ``n`` lines."""
        from xnano.core.controllers.tui import SESSION_DEVICE_LOCK

        with SESSION_DEVICE_LOCK:
            native.scroll_down(n)

    @property
    def title(self) -> str | None:
        """Window title last set on this device, if any."""
        return getattr(self, "_title", None)

    @title.setter
    def title(self, value: str | None) -> None:
        self._title = value
        if value is not None:
            self.set_title(value)

    @property
    def size(self) -> Size:
        """Current terminal viewport size in cells."""
        width, height = self._terminal.size
        return Size(width=width, height=height)

    def copy_to_clipboard(self, text: str) -> None:
        """Copy ``text`` via the host terminal's clipboard path."""
        self._terminal.copy_to_clipboard(text)



__all__ = ("TerminalDevice", "ClearType")
