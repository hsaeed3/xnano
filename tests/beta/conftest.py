"""tests.beta.conftest"""

from __future__ import annotations

import pytest


@pytest.fixture
def offscreen_runtime():
    """Yield a short-lived offscreen beta Runtime."""
    from xnano.beta.core import Runtime

    runtime = Runtime.offscreen(40, 12)
    try:
        yield runtime
    finally:
        runtime.close()
