"""A live runtime inside a pseudo-terminal: open, draw, resize, quit and restore."""

from __future__ import annotations

import os
import select
import signal
import struct
import sys
import textwrap
import time

import pytest

fcntl = pytest.importorskip('fcntl', reason='needs a POSIX pseudo-terminal')
termios = pytest.importorskip('termios', reason='needs a POSIX pseudo-terminal')
pty = pytest.importorskip('pty', reason='needs a POSIX pseudo-terminal')

CHILD = textwrap.dedent(
    """
    from xnano_core._xnano_core import (
        Canvas,
        CanvasLabel,
        InputOptions,
        Runtime,
        TerminalOptions,
    )
    from xnano_core._xnano_core._core_types import Stop

    buffer = Canvas(
        (0, 40),
        (0, 20),
        shapes=[CanvasLabel(0, 20, 'hello live')],
        width=40,
        height=10,
    )
    seen = []

    @buffer.hook(events=('key',))
    def on_key(context):
        seen.append(context.event.key.key)
        if context.event.key.key == 'q':
            raise Stop

    @buffer.hook(events=('resize',))
    def on_resize(context):
        seen.append('resize')

    runtime = Runtime.live(options=TerminalOptions(input=InputOptions(mouse='buttons')))
    runtime.mount(buffer, geometry='inherit')
    runtime.run()
    print('DONE', runtime.is_closed, ','.join(seen), runtime.device.size.width)
    """
)


class Terminal:
    def __init__(self) -> None:
        self.output = b''
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.environ['TERM'] = 'xterm-256color'
            os.execv(sys.executable, [sys.executable, '-c', CHILD])
        self.resize(10, 40)

    def resize(self, rows: int, columns: int) -> None:
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack('HHHH', rows, columns, 0, 0))
        os.kill(self.pid, signal.SIGWINCH)

    def read(self, seconds: float) -> None:
        end = time.time() + seconds
        while time.time() < end:
            ready, _, _ = select.select([self.fd], [], [], 0.05)
            if ready:
                try:
                    self.output += os.read(self.fd, 65536)
                except OSError:
                    return

    def wait_for(self, marker: bytes, seconds: float = 5.0) -> bool:
        end = time.time() + seconds
        while time.time() < end:
            self.read(0.1)
            if marker in self.output:
                return True
        return False


def test_a_live_runtime_draws_resizes_quits_and_restores_the_terminal():
    terminal = Terminal()
    try:
        assert terminal.wait_for(b'live'), terminal.output
        assert b'\x1b[?1049h' in terminal.output, 'it entered the alternate screen'
        assert b'\x1b[?1000h' in terminal.output, 'it turned mouse capture on'
        terminal.resize(6, 20)
        terminal.read(0.5)
        os.write(terminal.fd, b'x')
        terminal.read(0.3)
        os.write(terminal.fd, b'q')
        assert terminal.wait_for(b'DONE True'), terminal.output
    finally:
        try:
            os.kill(terminal.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        os.waitpid(terminal.pid, 0)
    output = terminal.output
    assert b'\x1b[?1049l' in output, 'it left the alternate screen'
    assert output.rfind(b'\x1b[?1000l') > output.rfind(b'\x1b[?1000h'), (
        'mouse capture was turned off'
    )
    assert output.rfind(b'\x1b[?25h') > output.rfind(b'\x1b[?25l'), (
        'the cursor is visible again'
    )
    assert b'resize' in output and b'x,q' in output
    assert b' 20' in output.split(b'DONE')[1], (
        'the device followed the window to 20 columns'
    )
