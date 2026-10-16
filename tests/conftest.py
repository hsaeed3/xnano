"""
tests.conftest

Fail a test at the moment it leaves something behind that the garbage collector must clean up.
"""

from __future__ import annotations

import gc
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))


def pytest_addoption(parser: pytest.Parser) -> None:
    """Make launching native terminal windows an explicit development test choice."""
    parser.addoption(
        '--actual-terminal',
        action='store_true',
        help='Run tests in isolated Kitty windows (requires Kitty and a graphical display).',
    )


@pytest.fixture(autouse=True)
def symbols_are_restored():
    """Give every test the symbols registered before it, since the registry is shared."""
    import xnano.symbols

    registered = dict(xnano.symbols._registry)
    yield
    xnano.symbols._registry.clear()
    xnano.symbols._registry.update(registered)


@pytest.fixture(autouse=True)
def no_garbage_left_behind():
    """Collect garbage after every test, so a leak is reported by the test that caused it.

    A runtime may only be dropped on the thread that created it. If a canvas leaves a
    reference to its runtime alive after it closed, the drop happens later on whichever
    thread collects it, and Python reports it as an ignored exception.
    """
    yield
    gc.collect()
