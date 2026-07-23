"""xnano.beta.core.demo

---

Entry point for the bundled showcase and the Markdown document viewer.

With no arguments this runs the framework's flagship feature tour. That
showcase is intentionally shared with ``xnano._demo`` rather than
reimplemented here — it is the one place the beta surface deliberately
reuses the stable demo instead of owning a parallel copy (the decoupling
rule in ``tests/beta/test_decoupling.py`` exempts this module).
"""

from __future__ import annotations

import pathlib
from typing import Sequence


def run_demo(arguments: Sequence[str] | None = None) -> None:
    """Run the feature showcase, or view a Markdown document.

    Args:
        arguments: Optional command arguments. When the first value is a
            path, it is opened in the Markdown viewer; otherwise the
            interactive feature tour runs.
    """
    values = list(arguments or ())
    if values:
        from xnano.beta.markdown import run_markdown

        run_markdown(pathlib.Path(values[0]))
        return
    from xnano._demo import run_demo as run_feature_demo

    run_feature_demo()


__all__ = ("run_demo",)
