"""
tests.emulator

Run a program on a pseudo-terminal and read its screen the way a user sees it.

The child process gets a real terminal device. Everything it writes goes through ``pyte``,
a terminal emulator, which keeps a screen of cells and answers the questions a terminal is
asked (where is the cursor, what are you) from its own state. Tests send keys, mouse
reports and window resizes the way a terminal would, and assert on what is on the screen.
"""

from __future__ import annotations

import fcntl
import os
import re
import select
import signal
import struct
import subprocess
import sys
import termios
import textwrap
import time

import pyte

# The emulator does not draw graphics queries (APC), and it does not know the keyboard
# protocol or soft-reset sequences a real terminal silently handles, so they are removed.
_UNKNOWN = re.compile(rb'\x1b_.*?\x1b\\|\x1b\[[<>=?]?[0-9;]*u|\x1b\[!p', re.DOTALL)


_ENTER_ALTERNATE = (b'\x1b[?1049h', b'\x1b[?1047h', b'\x1b[?47h')
_LEAVE_ALTERNATE = (b'\x1b[?1049l', b'\x1b[?1047l', b'\x1b[?47l')
_ALTERNATE_SCREEN = re.compile(rb'(\x1b\[\?(?:1049|1047|47)[hl])')


def _become_session_leader() -> None:
    """Make the pseudo-terminal the child's own terminal, so ``/dev/tty`` is the emulator."""
    os.setsid()
    fcntl.ioctl(0, termios.TIOCSCTTY, 0)


class Screen:
    """A live program and the terminal screen it draws on."""

    def __init__(
        self,
        body: str | None = None,
        *,
        command: list[str] | None = None,
        rows: int = 24,
        columns: int = 80,
    ) -> None:
        self.rows = rows
        self.columns = columns
        self.main_screen = self._new_screen()
        self.alternate_screen = self._new_screen()
        self.screen = self.main_screen
        self.is_alternate = False
        self._stream = pyte.ByteStream(self.screen)
        self.raw = b''
        self.master, slave = os.openpty()
        self._set_window_size(slave, rows, columns)
        if command is None:
            assert body is not None, 'give the program as source text or as a command'
            script = 'import time\nimport xnano\n' + textwrap.dedent(body)
            command = [sys.executable, '-c', script]
        self.process = subprocess.Popen(
            command,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            close_fds=True,
            env={
                name: value
                for name, value in os.environ.items()
                if name not in {'NO_COLOR', 'FORCE_COLOR'}
            },
            preexec_fn=_become_session_leader,  # noqa: PLW1509
        )
        os.close(slave)

    # -- the emulator ----------------------------------------------------------------

    def _new_screen(self) -> pyte.Screen:
        screen = pyte.Screen(self.columns, self.rows)
        screen.write_process_input = self._reply  # type: ignore[method-assign]
        return screen

    def _switch_screen(self, *, to_alternate: bool) -> None:
        self.is_alternate = to_alternate
        if to_alternate:
            self.alternate_screen = self._new_screen()
        self.screen = self.alternate_screen if to_alternate else self.main_screen
        self._stream = pyte.ByteStream(self.screen)

    @staticmethod
    def _set_window_size(descriptor: int, rows: int, columns: int) -> None:
        fcntl.ioctl(
            descriptor, termios.TIOCSWINSZ, struct.pack('HHHH', rows, columns, 0, 0)
        )

    def _reply(self, data: str) -> None:
        try:
            os.write(self.master, data.encode())
        except OSError:
            pass

    def pump(self, timeout: float = 0.05) -> None:
        """Read what the program wrote and draw it on the screen."""
        ready, _, _ = select.select([self.master], [], [], timeout)
        if not ready:
            return
        try:
            data = os.read(self.master, 65536)
        except OSError:
            return
        self.raw += data
        for part in _ALTERNATE_SCREEN.split(_UNKNOWN.sub(b'', data)):
            if part in _ENTER_ALTERNATE:
                self._switch_screen(to_alternate=True)
            elif part in _LEAVE_ALTERNATE:
                self._switch_screen(to_alternate=False)
            else:
                self._stream.feed(part)

    def settle(self, seconds: float = 0.3) -> None:
        """Keep reading for a while, so everything in flight is drawn."""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.pump(0.02)

    # -- reading the screen ----------------------------------------------------------

    def lines(self) -> list[str]:
        """Every row of the screen without trailing spaces."""
        return [line.rstrip() for line in self.screen.display]

    @property
    def text(self) -> str:
        """The whole screen as text."""
        return '\n'.join(self.lines()).rstrip('\n')

    def find(self, needle: str) -> tuple[int, int] | None:
        """The ``(column, row)`` where ``needle`` first appears on the screen."""
        for row, line in enumerate(self.lines()):
            column = line.find(needle)
            if column >= 0:
                return column, row
        return None

    def cell(self, column: int, row: int) -> pyte.screens.Char:
        """The character, colors and attributes at a cell."""
        return self.screen.buffer[row][column]

    @property
    def cursor(self) -> tuple[int, int, bool]:
        """The cursor's ``(column, row, is_visible)``."""
        cursor = self.screen.cursor
        return cursor.x, cursor.y, not cursor.hidden

    def wait_for(self, needle: str, timeout: float = 10.0) -> bool:
        """Wait until ``needle`` is on the screen."""
        return self.wait_until(lambda: self.find(needle) is not None, timeout)

    def wait_until(self, condition, timeout: float = 10.0) -> bool:
        """Wait until ``condition()`` is true."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.pump(0.02)
            if condition():
                return True
            if self.process.poll() is not None:
                self.settle(0.1)
                return bool(condition())
        return bool(condition())

    # -- sending input ---------------------------------------------------------------

    def send(self, data: bytes | str) -> None:
        """Type raw bytes, exactly as a terminal would send them."""
        os.write(self.master, data.encode() if isinstance(data, str) else data)

    def press(self, key: str) -> None:
        """Press a key by name (``'q'``, ``'enter'``, ``'up'``, ``'ctrl+c'``)."""
        named = {
            'enter': b'\r',
            'escape': b'\x1b',
            'up': b'\x1b[A',
            'down': b'\x1b[B',
            'right': b'\x1b[C',
            'left': b'\x1b[D',
            'tab': b'\t',
            'ctrl+c': b'\x03',
        }
        self.send(named.get(key, key.encode()))

    def click(self, column: int, row: int, *, button: int = 0) -> None:
        """Press and release a mouse button at a cell (``button`` 0, 1, 2 = left, middle, right)."""
        self.send(
            f'\x1b[<{button};{column + 1};{row + 1}M\x1b[<{button};{column + 1};{row + 1}m'
        )

    def drag(self, start: tuple[int, int], end: tuple[int, int]) -> None:
        """Press at ``start``, move to ``end`` holding the button, and release."""
        (c0, r0), (c1, r1) = start, end
        self.send(f'\x1b[<0;{c0 + 1};{r0 + 1}M')
        steps = max(abs(c1 - c0), abs(r1 - r0), 1)
        for step in range(1, steps + 1):
            c = c0 + round((c1 - c0) * step / steps)
            r = r0 + round((r1 - r0) * step / steps)
            self.send(f'\x1b[<32;{c + 1};{r + 1}M')
            time.sleep(0.01)
        self.send(f'\x1b[<0;{c1 + 1};{r1 + 1}m')

    def scroll(self, column: int, row: int, *, direction: str = 'down') -> None:
        """Turn the mouse wheel one step at a cell (``'up'``, ``'down'``, ``'left'``, ``'right'``)."""
        button = {'up': 64, 'down': 65, 'left': 66, 'right': 67}[direction]
        self.send(f'\x1b[<{button};{column + 1};{row + 1}M')

    def paste(self, text: str) -> None:
        """Paste text, with the markers of bracketed paste."""
        self.send(f'\x1b[200~{text}\x1b[201~')

    def resize(self, rows: int, columns: int) -> None:
        """Change the size of the window, as dragging its corner does."""
        self.rows, self.columns = rows, columns
        self._set_window_size(self.master, rows, columns)
        self.main_screen.resize(rows, columns)
        self.alternate_screen.resize(rows, columns)
        os.killpg(self.process.pid, signal.SIGWINCH)

    # -- ending ----------------------------------------------------------------------

    def finish(self, timeout: float = 15.0) -> int:
        """Wait for the program to exit and draw the rest of its output."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and self.process.poll() is None:
            self.pump(0.02)
        code = self._stop(timeout=5)
        self.settle(0.2)
        return code

    def _stop(self, timeout: float) -> int:
        """Kill the program if it is still running and wait for it.

        A program blocked on writing to a full terminal cannot be killed until someone reads
        what it wrote, so the output keeps being read while waiting.
        """
        if self.process.poll() is None:
            self.process.kill()
        deadline = time.monotonic() + timeout
        while self.process.poll() is None and time.monotonic() < deadline:
            self.pump(0.02)
        return self.process.wait(timeout=1)

    def close(self) -> None:
        self._stop(timeout=5)
        try:
            os.close(self.master)
        except OSError:
            pass
