"""Tests for TerminalCursor/TerminalDevice offscreen safety.

Offscreen sessions (tests, and every ``Web`` visitor under the hood — see
``xnano.web.render.WebRenderer``) must never issue real OS terminal escape
codes: there's no live terminal attached to receive them, and doing so
would write to whatever process happens to own stdout.
"""

from __future__ import annotations

from xnano.terminal import Terminal


def test_offscreen_cursor_tracks_position_locally() -> None:
    terminal = Terminal.offscreen()
    terminal.cursor.move_to(5, 7)
    assert terminal.cursor.get_position() == (5, 7)


def test_offscreen_cursor_visible_toggle_tracked() -> None:
    terminal = Terminal.offscreen()
    terminal.cursor.visible = False
    assert terminal.cursor.visible is False
    terminal.cursor.visible = True
    assert terminal.cursor.visible is True


def test_offscreen_cursor_relative_moves() -> None:
    terminal = Terminal.offscreen()
    terminal.cursor.move_to(5, 5)
    terminal.cursor.move_up(2)
    terminal.cursor.move_right(3)
    assert terminal.cursor.get_position() == (8, 3)


def test_offscreen_cursor_save_restore() -> None:
    terminal = Terminal.offscreen()
    terminal.cursor.move_to(4, 4)
    terminal.cursor.save_position()
    terminal.cursor.move_to(0, 0)
    terminal.cursor.restore_position()
    assert terminal.cursor.get_position() == (4, 4)


def test_offscreen_cursor_never_calls_native(monkeypatch) -> None:
    import xnano.terminal.cursor as cursor_module

    calls: list[str] = []
    for name in dir(cursor_module.native):
        if name.startswith("_"):
            continue
        try:
            monkeypatch.setattr(
                cursor_module.native,
                name,
                lambda *a, name=name, **k: calls.append(name),
            )
        except (AttributeError, TypeError):
            pass

    terminal = Terminal.offscreen()
    cursor = terminal.cursor
    cursor.move_to(1, 1)
    cursor.move_to_column(2)
    cursor.move_to_row(3)
    cursor.move_up()
    cursor.move_down()
    cursor.move_left()
    cursor.move_right()
    cursor.move_to_next_line()
    cursor.move_to_previous_line()
    cursor.save_position()
    cursor.restore_position()
    cursor.visible = False
    cursor.visible = True
    cursor.style = "steady_block"
    cursor.enable_blinking()
    cursor.disable_blinking()
    assert calls == []


def test_offscreen_device_title_tracked_locally() -> None:
    terminal = Terminal.offscreen()
    terminal.device.title = "hello"
    assert terminal.device.title == "hello"


def test_offscreen_device_flags_tracked_locally() -> None:
    terminal = Terminal.offscreen()
    terminal.device.raw_mode = True
    assert terminal.device.raw_mode is True
    terminal.device.mouse_capture = True
    assert terminal.device.mouse_capture is True


def test_offscreen_device_never_calls_native(monkeypatch) -> None:
    import xnano.terminal.device as device_module

    calls: list[str] = []
    for name in dir(device_module.native):
        if name.startswith("_"):
            continue
        try:
            monkeypatch.setattr(
                device_module.native,
                name,
                lambda *a, name=name, **k: calls.append(name),
            )
        except (AttributeError, TypeError):
            pass

    terminal = Terminal.offscreen()
    device = terminal.device
    device.raw_mode = True
    device.alternate_screen = True
    device.line_wrap = False
    device.mouse_capture = True
    device.bracketed_paste = True
    device.focus_change = True
    device.synchronized_updates = True
    device.title = "x"
    device.clear()
    device.scroll_up()
    device.scroll_down()
    assert calls == []


def test_offscreen_device_copy_to_clipboard_returns_false() -> None:
    terminal = Terminal.offscreen()
    assert terminal.device.copy_to_clipboard("text") is None
    assert terminal.copy_to_clipboard("text") is False
