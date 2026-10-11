"""tests.conftest"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

collect_ignore_glob = ['v1/*']

from xnano._xnano_core import Buffer, Runtime


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
