"""Private terminal commands for v1 display controls."""

from __future__ import annotations

import sys
from types import SimpleNamespace

CrosstermClearType = SimpleNamespace(
    All='2J',
    Purge='3J',
    FromCursorDown='0J',
    FromCursorUp='1J',
    CurrentLine='2K',
    UntilNewLine='0K',
)
CrosstermCursorStyle = SimpleNamespace(
    DefaultUserShape=0,
    BlinkingBlock=1,
    SteadyBlock=2,
    BlinkingUnderline=3,
    SteadyUnderline=4,
    BlinkingBar=5,
    SteadyBar=6,
)


def emit(sequence):
    sys.stdout.write(sequence)
    sys.stdout.flush()


def crossterm_save_cursor_position():
    emit('\x1b7')


def crossterm_restore_cursor_position():
    emit('\x1b8')


def crossterm_enable_line_wrap():
    emit('\x1b[?7h')


def crossterm_disable_line_wrap():
    emit('\x1b[?7l')


def crossterm_clear_terminal(kind):
    emit(f'\x1b[{kind}')


def crossterm_scroll_up(lines):
    if lines < 0:
        raise ValueError('scroll lines must be nonnegative')
    emit(f'\x1b[{lines}S')


def crossterm_scroll_down(lines):
    if lines < 0:
        raise ValueError('scroll lines must be nonnegative')
    emit(f'\x1b[{lines}T')
