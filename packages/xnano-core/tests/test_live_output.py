"""Text printed or logged during a live session never reaches the screen."""

from __future__ import annotations

import os
import select
import subprocess
import sys
import textwrap
import time

import pytest

pty = pytest.importorskip('pty')

ENTER_ALTERNATE_SCREEN = '\x1b[?1049h'
LEAVE_ALTERNATE_SCREEN = '\x1b[?1049l'

PREAMBLE = """
import logging
import sys

from xnano_core._xnano_core import Buffer, Runtime

logging.basicConfig(level=logging.INFO)
"""


def run_in_terminal(body: str) -> str:
    """Run ``body`` in a child process whose standard streams are a pseudo-terminal."""
    master, slave = pty.openpty()
    script = PREAMBLE + textwrap.dedent(body)
    process = subprocess.Popen(
        [sys.executable, '-c', script],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        close_fds=True,
    )
    os.close(slave)
    chunks: list[bytes] = []
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        ready, _, _ = select.select([master], [], [], 0.1)
        if ready:
            try:
                data = os.read(master, 65536)
            except OSError:
                break
            if not data:
                break
            chunks.append(data)
        elif process.poll() is not None:
            break
    process.wait(timeout=10)
    os.close(master)
    assert process.returncode == 0, b''.join(chunks).decode('utf-8', 'replace')
    return b''.join(chunks).decode('utf-8', 'replace')


@pytest.mark.skipif(sys.platform == 'win32', reason='output is only captured on Unix')
class TestLiveOutput:
    def test_printed_and_logged_text_waits_until_the_session_ends(self):
        screen = run_in_terminal(
            """
            with Runtime.live() as runtime:
                runtime.mount(Buffer.with_text('hello'), geometry='inherit')
                print('STRAY-PRINT')
                logging.warning('STRAY-LOG')
                sys.stderr.write('STRAY-ERROR\\n')
                runtime.step()
                runtime.step()
            """
        )
        left = screen.rindex(LEAVE_ALTERNATE_SCREEN)
        assert screen.index(ENTER_ALTERNATE_SCREEN) < screen.index('hello') < left
        for stray in ('STRAY-PRINT', 'STRAY-LOG', 'STRAY-ERROR'):
            assert screen.count(stray) == 1, stray
            assert screen.index(stray) > left, f'{stray} was printed inside the session'

    def test_text_printed_before_the_session_is_not_delayed_into_it(self):
        screen = run_in_terminal(
            """
            print('BEFORE', end='')
            with Runtime.live() as runtime:
                runtime.mount(Buffer.with_text('hello'), geometry='inherit')
                runtime.step()
            print('AFTER')
            """
        )
        assert screen.index('BEFORE') < screen.index(ENTER_ALTERNATE_SCREEN)
        assert screen.index('AFTER') > screen.rindex(LEAVE_ALTERNATE_SCREEN)

    def test_taken_output_is_not_printed_again(self):
        screen = run_in_terminal(
            """
            with Runtime.live() as runtime:
                runtime.mount(Buffer.with_text('hello'), geometry='inherit')
                print('TAKEN-LINE')
                sys.stdout.flush()
                taken = ''
                for _ in range(100):
                    taken += runtime.take_captured_output()
                    if 'TAKEN-LINE' in taken:
                        break
                    import time
                    time.sleep(0.02)
                runtime.step()
            print('RESULT', 'TAKEN-LINE' in taken)
            """
        )
        assert 'RESULT True' in screen
        assert screen.count('TAKEN-LINE') == 0

    def test_output_can_be_left_to_reach_the_terminal(self):
        screen = run_in_terminal(
            """
            from xnano_core._xnano_core import TerminalOptions

            options = TerminalOptions(should_capture_output=False)
            with Runtime.live(options=options) as runtime:
                runtime.mount(Buffer.with_text('hello'), geometry='inherit')
                runtime.step()
                print('PASSED-THROUGH')
                sys.stdout.flush()
                assert runtime.take_captured_output() == ''
            """
        )
        assert screen.index('PASSED-THROUGH') < screen.rindex(LEAVE_ALTERNATE_SCREEN)

    def test_output_survives_an_error_that_ends_the_session(self):
        screen = run_in_terminal(
            """
            try:
                with Runtime.live() as runtime:
                    runtime.mount(Buffer.with_text('hello'), geometry='inherit')
                    runtime.step()
                    print('BEFORE-THE-ERROR')
                    raise RuntimeError('boom')
            except RuntimeError:
                print('RECOVERED')
            """
        )
        left = screen.rindex(LEAVE_ALTERNATE_SCREEN)
        assert screen.index('BEFORE-THE-ERROR') > left
        assert screen.index('RECOVERED') > screen.index('BEFORE-THE-ERROR')

    def test_heavy_output_is_kept_and_printed_after_the_session(self):
        screen = run_in_terminal(
            """
            with Runtime.live() as runtime:
                runtime.mount(Buffer.with_text('hello'), geometry='inherit')
                runtime.step()
                for number in range(2000):
                    print(f'LINE-{number:04d}')
                runtime.step()
            """
        )
        left = screen.rindex(LEAVE_ALTERNATE_SCREEN)
        assert screen.index('LINE-0000') > left
        assert screen.index('LINE-1999') > screen.index('LINE-0000')
