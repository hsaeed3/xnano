"""Integration tests that require a real TTY."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import threading
import time

import pytest
from conftest import requires_tty
from xnano_core.rust.engine import (
    CoreRenderContent,
    CoreRenderNode,
    CoreSession,
    CoreTerminalEventKind,
)


requires_pty = pytest.mark.skipif(
    not hasattr(os, "openpty"),
    reason="requires os.openpty (POSIX pseudo-terminals)",
)


@requires_tty
def test_session_init_context_manager() -> None:
    with CoreSession.init(tick_rate_ms=0) as session:
        assert session.is_raw_mode_enabled()
        assert session.is_alternate_screen_enabled()
        assert not session.is_inline()
        assert session.get_inline_height() is None
        session.render(CoreRenderNode.leaf(CoreRenderContent.empty()))
    # Exiting restores the terminal without raising.


@requires_tty
def test_session_init_inline_viewport() -> None:
    with CoreSession.init(tick_rate_ms=0, inline_height=3) as session:
        assert session.is_raw_mode_enabled()
        # Inline sessions stay on the main screen buffer.
        assert not session.is_alternate_screen_enabled()
        assert session.is_inline()
        assert session.get_inline_height() == 3
        session.render(CoreRenderNode.leaf(CoreRenderContent.empty()))
    # Exiting restores the terminal without raising.


@requires_tty
def test_poll_event_synthesizes_tick() -> None:
    with CoreSession.init(tick_rate_ms=30) as session:
        # Drain any immediate resize/key noise first.
        for _ in range(5):
            session.poll_event(timeout_ms=1)

        seen_tick = False
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            ev = session.poll_event(timeout_ms=50)
            if ev is not None and ev.kind == CoreTerminalEventKind.Tick:
                seen_tick = True
                assert ev.tick is not None
                assert ev.tick.elapsed_ms >= 0
                break
        assert seen_tick, "expected a synthetic Tick event within 2 seconds"


@requires_tty
def test_poll_event_releases_gil() -> None:
    counter = {"n": 0}
    done = threading.Event()

    def spin() -> None:
        while not done.is_set():
            counter["n"] += 1

    with CoreSession.init(tick_rate_ms=0) as session:
        worker = threading.Thread(target=spin, daemon=True)
        worker.start()
        session.poll_event(timeout_ms=100)
        done.set()
        worker.join(timeout=1.0)

    assert counter["n"] > 0, (
        "background thread should run while poll_event blocks"
    )


@requires_tty
def test_read_event_keyboard_interrupt_subprocess() -> None:
    """Ctrl+C during read_event must surface as KeyboardInterrupt in Python."""
    script = textwrap.dedent(
        """
        import os
        import signal
        import threading
        import time

        from xnano_core.rust.engine import CoreSession

        def deliver_sigint() -> None:
            time.sleep(0.3)
            os.kill(os.getpid(), signal.SIGINT)

        threading.Thread(target=deliver_sigint, daemon=True).start()
        with CoreSession.init(tick_rate_ms=5000) as session:
            try:
                session.read_event()
            except KeyboardInterrupt:
                print("KEYBOARD_INTERRUPT")
                raise SystemExit(0)
        raise SystemExit("NO_INTERRUPT")
        """
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0
    assert "KEYBOARD_INTERRUPT" in proc.stdout


@requires_pty
def test_inline_viewport_renders_at_cursor_offset() -> None:
    """An inline viewport offset from the screen top renders without panicking.

    Runs the child under a pseudo-terminal, replies to the cursor-position
    query with a non-zero row so the inline viewport is offset from ``(0, 0)``,
    and asserts the content is drawn and the alternate screen is never entered.
    """
    import pty
    import re
    import select
    import struct

    script = textwrap.dedent(
        """
        from xnano_core.rust.native import Paragraph
        from xnano_core.rust.engine import (
            CoreRenderContent,
            CoreRenderNode,
            CoreSession,
        )

        with CoreSession.init(tick_rate_ms=0, inline_height=1) as session:
            node = CoreRenderNode.leaf(
                CoreRenderContent.widget(Paragraph.new("HELLO"))
            )
            session.render(node)
        """
    )

    pid, fd = pty.fork()
    if pid == 0:
        os.execv(sys.executable, [sys.executable, "-c", script])
        os._exit(127)  # unreachable

    import fcntl
    import termios

    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
    out = b""
    while True:
        readable, _, _ = select.select([fd], [], [], 5.0)
        if not readable:
            break
        try:
            chunk = os.read(fd, 4096)
        except OSError:
            break
        if not chunk:
            break
        out += chunk
        # Reply to the cursor-position query (ESC[6n) with row 18, col 1 so
        # the inline viewport is placed away from the screen origin.
        if b"\x1b[6n" in chunk:
            os.write(fd, b"\x1b[18;1R")
    _, status = os.waitpid(pid, 0)

    text = out.decode(errors="replace")
    assert "panicked" not in text
    assert "Traceback" not in text
    # Never switches to the alternate screen buffer.
    assert "?1049h" not in text
    # All content glyphs are emitted in order.
    stripped = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", text)
    assert "HELLO" in stripped.replace("\r", "").replace("\n", "")
    assert os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0
