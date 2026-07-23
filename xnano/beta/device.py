"""xnano.beta.device

---

Control the title, display modes, clipboard, and viewport of a runtime.

Flags and title are always tracked locally, so ``device`` behaves the
same for a live or an offscreen runtime (tests, and every web visitor's
session). Only a *live* runtime issues the real terminal escape codes;
an offscreen runtime must not, or it would write control sequences to
whatever process owns stdout (wrong for a headless web server) — and
``enable_raw_mode`` raises ``OSError`` outright when there is no real
terminal to configure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, TypeAlias

from xnano_core.rust import native

from xnano.beta.types import Size

if TYPE_CHECKING:
    from xnano.beta.core.runtime import Runtime


ClearType: TypeAlias = Literal[
    "all",
    "purge",
    "from_cursor_down",
    "from_cursor_up",
    "current_line",
    "until_new_line",
]
"""How much of the terminal display ``Device.clear`` should erase.

Values:
    ``"all"``: The entire visible screen.
    ``"purge"``: The screen and its scrollback history.
    ``"from_cursor_down"``: From the caret to the bottom of the screen.
    ``"from_cursor_up"``: From the top of the screen to the caret.
    ``"current_line"``: Only the caret's current line.
    ``"until_new_line"``: From the caret to the end of its line.
"""


_NATIVE_CLEAR_TYPES: dict[ClearType, Any] = {
    "all": native.ClearType.All,
    "purge": native.ClearType.Purge,
    "from_cursor_down": native.ClearType.FromCursorDown,
    "from_cursor_up": native.ClearType.FromCursorUp,
    "current_line": native.ClearType.CurrentLine,
    "until_new_line": native.ClearType.UntilNewLine,
}


class Device:
    """Control device settings for a ``Runtime`` session.

    Title, clear, size, scroll, clipboard, raw mode, alternate screen,
    mouse capture, and related flags. Obtained from ``runtime.device``
    — do not construct this class yourself.

    Attributes:
        raw_mode: Whether raw input mode is enabled.
        alternate_screen: Whether the alternate screen buffer is active.
        line_wrap: Whether automatic line wrapping is enabled.
        mouse_capture: Whether mouse events are captured.
        bracketed_paste: Whether bracketed paste mode is enabled.
        focus_change: Whether terminal focus events are enabled.
        synchronized_updates: Whether synchronized updates are enabled.
        title: Window or page title.
        size: Current viewport size in cells.

    Example:
        >>> from xnano.beta.core.runtime import Runtime
        >>> runtime = Runtime.offscreen(20, 4, title="Example")
        >>> runtime.device.size.width
        20
        >>> runtime.close()
    """

    __slots__ = (
        "_runtime",
        "_raw_mode",
        "_alternate_screen",
        "_line_wrap",
        "_mouse_capture",
        "_bracketed_paste",
        "_focus_change",
        "_synchronized_updates",
        "_title",
    )

    def __init__(self, runtime: "Runtime") -> None:
        self._runtime = runtime
        self._raw_mode = False
        self._alternate_screen = False
        self._line_wrap = True
        self._mouse_capture = False
        self._bracketed_paste = False
        self._focus_change = False
        self._synchronized_updates = False
        self._title: str | None = None

    def _is_live(self) -> bool:
        """Whether the owning runtime drives a real terminal session."""
        return self._runtime.is_live

    @property
    def _session(self):
        """Native session controlled by this device."""
        return self._runtime.session

    @property
    def raw_mode(self) -> bool:
        """Whether raw input mode is enabled."""
        return self._raw_mode

    @raw_mode.setter
    def raw_mode(self, value: bool) -> None:
        self._raw_mode = value
        if self._is_live():
            if value:
                self._session.enable_raw_mode()
            else:
                self._session.disable_raw_mode()

    @property
    def alternate_screen(self) -> bool:
        """Whether the alternate screen buffer is active."""
        return self._alternate_screen

    @alternate_screen.setter
    def alternate_screen(self, value: bool) -> None:
        self._alternate_screen = value
        if self._is_live():
            if value:
                self._session.enter_alternate_screen()
            else:
                self._session.leave_alternate_screen()

    @property
    def line_wrap(self) -> bool:
        """Whether automatic line wrapping is enabled."""
        return self._line_wrap

    @line_wrap.setter
    def line_wrap(self, value: bool) -> None:
        self._line_wrap = value
        if self._is_live():
            function = (
                native.enable_line_wrap if value else native.disable_line_wrap
            )
            function()

    @property
    def mouse_capture(self) -> bool:
        """Whether mouse events are captured."""
        return self._mouse_capture

    @mouse_capture.setter
    def mouse_capture(self, value: bool) -> None:
        self._mouse_capture = value
        if self._is_live():
            if value:
                self._session.enable_mouse_capture()
            else:
                self._session.disable_mouse_capture()

    @property
    def bracketed_paste(self) -> bool:
        """Whether bracketed paste mode is enabled."""
        return self._bracketed_paste

    @bracketed_paste.setter
    def bracketed_paste(self, value: bool) -> None:
        self._bracketed_paste = value
        if self._is_live():
            if value:
                self._session.enable_bracketed_paste()
            else:
                self._session.disable_bracketed_paste()

    @property
    def focus_change(self) -> bool:
        """Whether OS-level terminal focus change events are enabled."""
        return self._focus_change

    @focus_change.setter
    def focus_change(self, value: bool) -> None:
        self._focus_change = value
        if self._is_live():
            if value:
                self._session.enable_focus_change()
            else:
                self._session.disable_focus_change()

    @property
    def synchronized_updates(self) -> bool:
        """Whether synchronized output updates are enabled."""
        return self._synchronized_updates

    @synchronized_updates.setter
    def synchronized_updates(self, value: bool) -> None:
        self._synchronized_updates = value
        if self._is_live():
            if value:
                self._session.begin_synchronized_update()
            else:
                self._session.end_synchronized_update()

    @property
    def title(self) -> str | None:
        """Window/page title last set on this device, if any."""
        return self._title

    @title.setter
    def title(self, value: str | None) -> None:
        self._title = value
        if value is not None and self._is_live():
            self._session.set_title(value)

    @property
    def size(self) -> Size:
        """Current terminal viewport size in cells."""
        width, height = self._runtime.size
        return Size(width=width, height=height)

    def clear(self, kind: ClearType = "all") -> None:
        """Clear the terminal display."""
        if self._is_live():
            self._session.clear(_NATIVE_CLEAR_TYPES[kind])

    def scroll_up(self, lines: int = 1) -> None:
        """Scroll the viewport up by ``lines``."""
        if self._is_live():
            self._session.scroll_up(lines)

    def scroll_down(self, lines: int = 1) -> None:
        """Scroll the viewport down by ``lines``."""
        if self._is_live():
            self._session.scroll_down(lines)

    def copy_to_clipboard(self, text: str) -> bool:
        """Copy ``text`` to the clipboard when supported."""
        return False


__all__ = ("ClearType", "Device")
