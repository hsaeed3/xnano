"""tests.beta.test_demo"""

from __future__ import annotations

import pathlib

import xnano._demo as stable_demo
from xnano.beta.core import demo


def test_no_argument_runs_stable_feature_showcase(monkeypatch) -> None:
    """With no path, the beta entry point runs the shared flagship tour
    from ``xnano._demo`` rather than a separate beta reimplementation."""
    calls: list[str] = []
    monkeypatch.setattr(
        stable_demo, "run_demo", lambda: calls.append("feature")
    )
    demo.run_demo()
    assert calls == ["feature"]


def test_path_argument_opens_markdown_viewer(
    monkeypatch, tmp_path: pathlib.Path
) -> None:
    document = tmp_path / "doc.md"
    document.write_text("# Doc\n\nbody", encoding="utf-8")
    opened: list[pathlib.Path] = []
    import xnano.beta.markdown as markdown

    monkeypatch.setattr(
        markdown, "run_markdown", lambda source: opened.append(source)
    )
    demo.run_demo([str(document)])
    assert opened == [document]
