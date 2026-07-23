"""tests.beta.test_cursor_device"""

from __future__ import annotations

import contextlib
import io

import pytest

from xnano.beta.core.runtime import Runtime
from xnano.beta.cursor import Cursor
from xnano.beta.device import Device


@pytest.fixture
def runtime():
    runtime = Runtime.offscreen(20, 6)
    try:
        yield runtime
    finally:
        runtime.close()


def test_cursor_tracks_position_locally(runtime: Runtime) -> None:
    cursor = runtime.cursor
    cursor.move(4, 2)
    assert cursor.position == (4, 2)
    assert cursor.get_position() == (4, 2)
    cursor.position = (7, 1)
    assert cursor.position == (7, 1)


def test_cursor_relative_moves_clamp_at_origin(runtime: Runtime) -> None:
    cursor = runtime.cursor
    cursor.move(1, 1)
    cursor.move_up()
    cursor.move_left()
    assert cursor.position == (0, 0)
    cursor.move_down(2)
    cursor.move_right(3)
    assert cursor.position == (3, 2)


def test_cursor_save_and_restore_round_trip(runtime: Runtime) -> None:
    cursor = runtime.cursor
    cursor.move(5, 3)
    cursor.save()
    cursor.move(0, 0)
    cursor.restore()
    assert cursor.position == (5, 3)


def test_cursor_style_and_visibility_track_locally(runtime: Runtime) -> None:
    cursor = runtime.cursor
    for style in (
        "blinking_block",
        "steady_underline",
        "steady_bar",
        "default",
    ):
        cursor.style = style
        assert cursor.style == style
    cursor.visible = False
    assert cursor.visible is False
    cursor.enable_blinking()
    cursor.disable_blinking()


def test_cursor_rejects_unknown_style(runtime: Runtime) -> None:
    with pytest.raises(ValueError):
        runtime.cursor.style = "sparkles"  # ty: ignore[invalid-assignment]


def test_offscreen_cursor_emits_no_escape_codes(runtime: Runtime) -> None:
    """An offscreen cursor tracks state but must never write terminal
    escape codes to stdout — every web visitor is served offscreen."""
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        runtime.cursor.move(3, 3)
        runtime.cursor.visible = False
        runtime.cursor.style = "steady_bar"
        runtime.cursor.save()
        runtime.cursor.restore()
    assert stream.getvalue() == ""


def test_offscreen_device_flags_never_raise_or_emit(runtime: Runtime) -> None:
    """``enable_raw_mode`` raises ``OSError`` on a session with no real
    terminal; the offscreen device must guard every such native call and
    still track the flag locally."""
    device = runtime.device
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        for name in (
            "raw_mode",
            "alternate_screen",
            "line_wrap",
            "mouse_capture",
            "bracketed_paste",
            "focus_change",
            "synchronized_updates",
        ):
            setattr(device, name, True)
            assert getattr(device, name) is True
            setattr(device, name, False)
            assert getattr(device, name) is False
        device.clear()
        device.clear("purge")
        device.scroll_up(2)
        device.scroll_down(2)
    assert stream.getvalue() == ""


def test_offscreen_device_title_tracks_without_emitting(
    runtime: Runtime,
) -> None:
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        runtime.device.title = "Report"
    assert runtime.device.title == "Report"
    assert stream.getvalue() == ""


def test_device_size_reflects_runtime(runtime: Runtime) -> None:
    assert runtime.device.size.width == 20
    assert runtime.device.size.height == 6


def test_cursor_and_device_report_not_live_offscreen(
    runtime: Runtime,
) -> None:
    assert Cursor(runtime)._is_live() is False
    assert Device(runtime)._is_live() is False
