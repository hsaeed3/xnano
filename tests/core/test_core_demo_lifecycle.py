"""Tests for showcase entry and runtime lifecycle workflows."""

from __future__ import annotations

import pathlib

import xnano.core.demo as demo
import xnano.markdown
import xnano.terminal
from xnano.actions import Action
from xnano.core.demo import Demo, IntroSplash, Showcase
from xnano.core.runtime import Runtime


def test_demo_advances_from_intro_to_interactive_showcase() -> None:
    runtime = Runtime.offscreen(80, 24)
    try:
        app = Demo()
        runtime.set_root(app)
        intro = runtime.render()
        assert isinstance(app.view, IntroSplash)
        assert intro.width == 80
        assert intro.height == 24

        runtime.perform(Action.tick(1000))
        runtime.perform(Action.tick(1000))
        runtime.perform(Action.tick(1100))
        showcase = runtime.render()
        assert isinstance(app.view, Showcase)
        assert showcase.contains("xnano")
        assert showcase.revision > intro.revision
    finally:
        runtime.close()


def test_runtime_schedules_showcase_updates_before_next_pump() -> None:
    runtime = Runtime.offscreen(80, 24)
    try:
        app = Showcase()
        runtime.set_root(app)
        runtime.render()
        runtime.call_soon(setattr, app, "header", app.header)
        assert runtime.pump()
        frame = runtime.render()
        assert frame.contains("showcase")
        runtime.request_exit()
        assert not runtime.pump()
    finally:
        runtime.close()


def test_demo_entry_routes_documents_and_showcase(
    monkeypatch,
    tmp_path: pathlib.Path,
) -> None:
    opened: list[pathlib.Path] = []
    launched: list[bool] = []
    monkeypatch.setattr(xnano.markdown, "run_markdown", opened.append)
    monkeypatch.setattr(demo, "run_showcase", lambda: launched.append(True))

    document = tmp_path / "guide.md"
    demo.run_demo([str(document)])
    demo.run_demo()

    assert opened == [document]
    assert launched == [True]


def test_showcase_entry_uses_viewport_size_for_paint_cadence(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeTerminal:
        def __init__(self, **settings: object) -> None:
            captured.update(settings)

        def run(self, root: object) -> None:
            captured["root"] = root

    monkeypatch.setattr(xnano.terminal, "Terminal", FakeTerminal)
    monkeypatch.setattr(
        demo.shutil if hasattr(demo, "shutil") else __import__("shutil"),
        "get_terminal_size",
        lambda fallback: (400, 100),
    )
    demo.run_showcase()

    assert captured["title"] == "xnano · showcase"
    assert captured["tick_interval"] == 100
    assert isinstance(captured["root"], Demo)
