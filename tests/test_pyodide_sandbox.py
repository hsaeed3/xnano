"""Execute every runnable cell in ``docs/sandbox.md``.

The sandbox page is a gallery of ``pyodide`` fences that visitors run in the
browser. Pyodide imports the same pure-Python ``xnano`` these tests do (only
the ``xnano-core`` build differs), so if a cell drifts from the current API —
a renamed import, a dropped keyword, a removed component — it breaks silently
on the docs site. This module extracts each fence and executes it under the
desktop build, turning "the docs still run" into a checked invariant.

Only import/exec is asserted, not rendered output: these cells reach the same
offscreen buffer path Pyodide uses (no ``.run()``, no live loop), and any API
mismatch raises during exec. Cells stay independent — a fresh namespace each,
stdout suppressed — matching how a reader runs any one of them in isolation.
"""

from __future__ import annotations

import contextlib
import io
import pathlib
import re
from typing import Any

import pytest

_SANDBOX = pathlib.Path(__file__).resolve().parents[1] / "docs" / "sandbox.md"
_FENCE = re.compile(r"^```pyodide[^\n]*\n(.*?)^```", re.MULTILINE | re.DOTALL)


def _extract_cells() -> list[tuple[str, str]]:
    """Return ``(test_id, code)`` for every pyodide fence, in page order.

    Each id is the nearest preceding ``##`` heading (slugged) plus a counter,
    so a failing cell points straight at its section.
    """
    text = _SANDBOX.read_text(encoding="utf-8")
    headings: dict[int, str] = {
        match.start(): match.group(1).strip()
        for match in re.finditer(r"^## (.+)$", text, re.MULTILINE)
    }
    cells: list[tuple[str, str]] = []
    for index, fence in enumerate(_FENCE.finditer(text)):
        prior = [pos for pos in headings if pos < fence.start()]
        section = headings[max(prior)] if prior else "intro"
        slug = re.sub(r"[^a-z0-9]+", "-", section.lower()).strip("-")
        cells.append((f"{index}-{slug}", fence.group(1)))
    return cells


_CELLS = _extract_cells()


def test_sandbox_has_runnable_cells() -> None:
    # Guard against a silently empty extraction (moved file, changed fence).
    assert len(_CELLS) >= 8


@pytest.mark.parametrize(
    "code", [code for _, code in _CELLS], ids=[cid for cid, _ in _CELLS]
)
def test_sandbox_cell_executes(code: str) -> None:
    namespace: dict[str, Any] = {"__name__": "__sandbox__"}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(code, "<sandbox.md>", "exec"), namespace)
