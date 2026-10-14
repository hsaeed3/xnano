"""tests.conftest"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / 'scripts'))

import resource_logging


def pytest_addoption(parser, pluginmanager):
    """Make the ``--resource-log`` options available."""
    resource_logging.register(pluginmanager)


collect_ignore_glob = ['v1/*']

from xnano_core._xnano_core import Buffer, Runtime


@pytest.fixture
def runtime():
    """A short-lived offscreen runtime, 40 columns by 10 rows."""
    with Runtime.offscreen(width=40, height=10) as offscreen:
        yield offscreen


@pytest.fixture
def mounted(runtime):
    """A buffer mounted on an offscreen runtime with inherited geometry."""
    buffer = Buffer()
    context = runtime.mount(buffer, geometry='inherit')
    return buffer, context
