"""
tests.actual_terminal

Drive an isolated Kitty terminal through its socket protocol using Python's standard library.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
import uuid
from collections.abc import Callable
from typing import cast

JSONValue = str | int | float | bool | None | list['JSONValue'] | dict[str, 'JSONValue']


def kitty_executable() -> str | None:
    """Find the native terminal, including Homebrew's macOS application bundle."""
    configured = os.environ.get('XNANO_KITTY')
    if configured:
        return shutil.which(configured)
    executable = shutil.which('kitty')
    if executable:
        return executable
    application = pathlib.Path('/Applications/kitty.app/Contents/MacOS/kitty')
    return str(application) if application.is_file() else None


def without_environment(value: JSONValue) -> JSONValue:
    """Remove environment dictionaries from native metadata before saving artifacts."""
    if isinstance(value, dict):
        return {
            name: without_environment(item)
            for name, item in value.items()
            if name != 'env'
        }
    if isinstance(value, list):
        return [without_environment(item) for item in value]
    return value


class ActualTerminal:
    """
    Run a Python program inside a separate, real terminal window.

    Kitty owns the PTY, answers capability queries, processes input and draws the
    screen. No escape-sequence parser or terminal responses are supplied here.
    Each instance owns its socket and process; user terminals are never selected.
    """

    def __init__(self, body: str, *, columns: int = 80, rows: int = 24) -> None:
        executable = kitty_executable()
        if executable is None:
            raise RuntimeError(
                'Cannot start an actual terminal. Install Kitty with make install-terminal and try again.'
            )
        # macOS's default temporary directory can exceed Unix socket path limits.
        self._temporary = tempfile.TemporaryDirectory(
            prefix='xnano-terminal-', dir='/tmp'
        )
        self.directory = pathlib.Path(self._temporary.name)
        self._socket = self.directory / 'control'
        self._result = self.directory / 'result'
        self._log = self.directory / 'kitty.log'
        source = self.directory / 'program.py'
        source.write_text('import time\nimport xnano\n' + textwrap.dedent(body))
        # Keep the window alive after the program exits so its restored main screen
        # and exit status remain inspectable. Cleanup closes this owned window.
        wrapper = self.directory / 'run.py'
        # The wrapper ends the program, and itself, as soon as Kitty goes away, so a failed
        # test never leaves a program running.
        wrapper.write_text(
            'import os, pathlib, subprocess, sys, time\n'
            'kitty = os.getppid()\n'
            'program = subprocess.Popen([sys.executable, sys.argv[1]])\n'
            'while program.poll() is None:\n'
            '    if os.getppid() != kitty:\n'
            '        program.kill()\n'
            '        sys.exit(1)\n'
            '    time.sleep(0.1)\n'
            'pathlib.Path(sys.argv[2]).write_text(str(program.returncode))\n'
            'while os.getppid() == kitty:\n'
            '    time.sleep(0.1)\n'
        )
        environment = {
            name: value
            for name, value in os.environ.items()
            if name
            in {
                'PATH',
                'HOME',
                'USER',
                'LOGNAME',
                'LANG',
                'LC_ALL',
                'DISPLAY',
                'XAUTHORITY',
                'XDG_RUNTIME_DIR',
                'DBUS_SESSION_BUS_ADDRESS',
                'LIBGL_ALWAYS_SOFTWARE',
            }
        }
        self._log_stream = self._log.open('wb')
        self.process = subprocess.Popen(
            [
                executable,
                '--config',
                'NONE',
                # Windows start minimized, so a test run never opens in front of the user.
                # Set XNANO_TERMINAL_VISIBLE=1 to watch them.
                f'--start-as={"normal" if os.environ.get("XNANO_TERMINAL_VISIBLE") else "minimized"}',
                '--listen-on',
                f'unix:{self._socket}',
                '--override',
                'allow_remote_control=socket-only',
                '--override',
                'remember_window_size=no',
                '--override',
                f'initial_window_width={columns}c',
                '--override',
                f'initial_window_height={rows}c',
                '--override',
                'window_padding_width=0',
                '--override',
                'window_margin_width=0',
                '--override',
                'font_size=12',
                '--override',
                'shell_integration=disabled',
                sys.executable,
                str(wrapper),
                str(source),
                str(self._result),
            ],
            cwd=pathlib.Path(__file__).resolve().parents[1],
            env=environment,
            stdout=self._log_stream,
            stderr=subprocess.STDOUT,
        )
        try:
            self.wait_until(lambda: self._socket.exists(), timeout=15)
            self.wait_until(lambda: bool(self.command('ls')), timeout=15)
        except BaseException:
            self.close()
            raise

    def command(self, name: str, **payload: JSONValue) -> JSONValue:
        """Send one documented Kitty remote-control command to this instance."""
        request_fields: dict[str, JSONValue] = {
            'cmd': name,
            'version': [0, 26, 0],
            'payload': payload,
        }
        if name == 'screenshot':
            request_fields['async'] = str(uuid.uuid4())
        request = json.dumps(request_fields).encode()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(5)
            connection.connect(str(self._socket))
            connection.sendall(b'\x1bP@kitty-cmd' + request + b'\x1b\\')
            response = bytearray()
            while not response.endswith(b'\x1b\\'):
                chunk = connection.recv(65536)
                if not chunk:
                    raise RuntimeError(
                        f'Kitty closed the control socket during {name}. Inspect the terminal log and retry.'
                    )
                response.extend(chunk)
        decoded = cast(dict[str, JSONValue], json.loads(response[12:-2]))
        if not decoded.get('ok'):
            raise RuntimeError(
                f'Kitty could not perform {name}: {decoded.get("error")}. Check the command and Kitty version.'
            )
        return decoded.get('data')

    def text(self, *, ansi: bool = False) -> str:
        """Read the actual terminal's current screen, optionally with its styles."""
        return cast(str, self.command('get-text', ansi=ansi, extent='screen'))

    def title(self) -> str:
        """Read the active pane's title as maintained by Kitty."""
        windows = cast(
            list[dict[str, JSONValue]], json.loads(cast(str, self.command('ls')))
        )
        tabs = cast(list[dict[str, JSONValue]], windows[0]['tabs'])
        panes = cast(list[dict[str, JSONValue]], tabs[0]['windows'])
        return cast(str, panes[0]['title'])

    def press(self, *keys: str) -> None:
        """Deliver keys through Kitty's keyboard encoder, such as ``ctrl+c``."""
        self.command('send-key', keys=list(keys))

    def paste(self, text: str) -> None:
        """Paste text using the bracketed-paste mode requested by the program."""
        self.command('send-text', data='text:' + text, bracketed_paste='auto')

    def resize(self, *, columns: int, rows: int) -> None:
        """Resize the real window in cells, allowing Kitty to notify its child PTY."""
        self.command(
            'resize-os-window', width=columns, height=rows, unit='cells', action='resize'
        )

    def screenshot(self, path: pathlib.Path) -> None:
        """Save Kitty's rendered pixels as a PNG (requires Kitty 0.49 or newer)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        self.command('screenshot', output_path=str(path.resolve()))

    def wait_until(self, condition: Callable[[], bool], *, timeout: float = 5) -> None:
        """Wait for observed terminal state, failing with the native process log."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(
                    f'Kitty exited with {self.process.returncode}: {self._log.read_text(errors="replace")}. Check that a graphical display is available.'
                )
            try:
                if condition():
                    return
            except (FileNotFoundError, ConnectionRefusedError):
                pass
            if self._result.exists() and self._result.read_text() not in {'', '0'}:
                raise RuntimeError(
                    f'The terminal program exited with {self._result.read_text()}. Screen: {self.text()}. Correct the program before continuing.'
                )
            time.sleep(0.02)
        raise AssertionError(
            f'Terminal condition was not met in {timeout} seconds. Kitty log: {self._log.read_text(errors="replace")}'
        )

    def wait_for(self, text: str, *, timeout: float = 5) -> None:
        """Wait until text appears in Kitty's screen."""
        self.wait_until(lambda: text in self.text(), timeout=timeout)

    def finish(self, *, timeout: float = 5) -> int:
        """Wait for the program's actual exit status while leaving its window open."""
        self.wait_until(self._result.exists, timeout=timeout)
        return int(self._result.read_text())

    def save_artifacts(self, directory: pathlib.Path) -> None:
        """Save screen text, styles, metadata, native logs and rendered pixels."""
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'screen.txt').write_text(self.text())
        (directory / 'screen.ansi').write_text(self.text(ansi=True))
        metadata = cast(JSONValue, json.loads(cast(str, self.command('ls'))))
        (directory / 'windows.json').write_text(
            json.dumps(without_environment(metadata), indent=2)
        )
        shutil.copyfile(self._log, directory / 'kitty.log')
        try:
            self.screenshot(directory / 'screen.png')
        except RuntimeError as error:
            # Distribution-provided versions can precede the screenshot command.
            (directory / 'screenshot-error.txt').write_text(str(error))

    def close(self) -> None:
        """Close only this instance and remove its private socket and temporary files."""
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self._log_stream.close()
        self._temporary.cleanup()
