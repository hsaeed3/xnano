"""Execute every runnable ``pyodide`` cell across ``docs/``.

The docs site renders ``pyodide`` fences as galleries visitors run in the
browser. Pyodide imports the same pure-Python ``xnano`` these tests do (only
the ``xnano-core`` build differs), so if a cell drifts from the current API —
a renamed import, a dropped keyword, a removed component — it breaks silently
on the docs site. This module extracts each fence and executes it under the
desktop build, turning "the docs still run" into a checked invariant.

Pages are discovered by globbing ``docs/**/*.md`` rather than naming files,
so reorganising the docs cannot silently disable this suite — the same
approach ``scripts/set_version.py`` takes for its version pins. The
``test_docs_have_runnable_cells`` floor is what catches a glob that stops
matching.

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

_DOCS = pathlib.Path(__file__).resolve().parents[1] / "docs"
_FENCE = re.compile(r"^```pyodide[^\n]*\n(.*?)^```", re.MULTILINE | re.DOTALL)


def _extract_page_cells(path: pathlib.Path) -> list[tuple[str, str]]:
    """Return ``(test_id, code)`` for one page's fences, in page order.

    Each id is the page stem plus the nearest preceding ``##`` heading
    (slugged) and a counter, so a failing cell points straight at its
    section on the site.
    """
    text = path.read_text(encoding="utf-8")
    headings: dict[int, str] = {
        match.start(): match.group(1).strip()
        for match in re.finditer(r"^## (.+)$", text, re.MULTILINE)
    }
    cells: list[tuple[str, str]] = []
    for index, fence in enumerate(_FENCE.finditer(text)):
        prior = [pos for pos in headings if pos < fence.start()]
        section = headings[max(prior)] if prior else "intro"
        slug = re.sub(r"[^a-z0-9]+", "-", section.lower()).strip("-")
        cells.append((f"{path.stem}-{index}-{slug}", fence.group(1)))
    return cells


def _extract_cells() -> list[tuple[str, str]]:
    """Return ``(test_id, code)`` for every pyodide fence under ``docs/``."""
    cells: list[tuple[str, str]] = []
    for path in sorted(_DOCS.rglob("*.md")):
        cells.extend(_extract_page_cells(path))
    return cells


_CELLS = _extract_cells()


def test_docs_have_runnable_cells() -> None:
    # Guard against a silently empty extraction (moved docs, changed fence).
    assert len(_CELLS) >= 8


@pytest.mark.parametrize(
    "code", [code for _, code in _CELLS], ids=[cid for cid, _ in _CELLS]
)
def test_docs_cell_executes(code: str) -> None:
    namespace: dict[str, Any] = {"__name__": "__sandbox__"}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(code, "<docs>", "exec"), namespace)
