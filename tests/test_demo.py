"""tests.test_demo"""

from __future__ import annotations

import pathlib

from xnano.core import demo


def test_no_argument_runs_showcase(monkeypatch) -> None:
    """With no path, the entry point runs the native feature showcase."""
    calls: list[str] = []
    monkeypatch.setattr(demo, "run_showcase", lambda: calls.append("showcase"))
    demo.run_demo()
    assert calls == ["showcase"]


def test_path_argument_opens_markdown_viewer(
    monkeypatch, tmp_path: pathlib.Path
) -> None:
    document = tmp_path / "doc.md"
    document.write_text("# Doc\n\nbody", encoding="utf-8")
    opened: list[pathlib.Path] = []
    import xnano.markdown as markdown

    monkeypatch.setattr(
        markdown, "run_markdown", lambda source: opened.append(source)
    )
    demo.run_demo([str(document)])
    assert opened == [document]
