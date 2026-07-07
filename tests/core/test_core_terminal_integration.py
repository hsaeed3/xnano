"""Integration tests that require a real TTY."""

from __future__ import annotations

import subprocess
import sys
import textwrap
import threading
import time

from xnano_core.rust.engine import (
    CoreRenderContent,
    CoreRenderNode,
    CoreSession,
    CoreTerminalEventKind,
)

from conftest import requires_tty


@requires_tty
def test_session_init_context_manager() -> None:
    with CoreSession.init(tick_rate_ms=0) as session:
        assert session.is_raw_mode_enabled()
        assert session.is_alternate_screen_enabled()
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
