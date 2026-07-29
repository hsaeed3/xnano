"""tests.test_reactivity_threading

---

Thread-safe UI updates (ctx.call_soon / grid.schedule_update), non-raising
optional style patches, and inline Loader frames.
"""

from __future__ import annotations

import threading
from typing import Any

from xnano.components.loader import Loader
from xnano.core import Runtime
from xnano.fields import Field
from xnano.grids import BaseGrid


def test_call_soon_applies_worker_update_on_ui_thread() -> None:
    class App(BaseGrid):
        status: Any = Field(default="init")

    runtime = Runtime.offscreen(20, 3)
    try:
        app = App()
        runtime.set_root(app)

        def worker() -> None:
            runtime.call_soon(lambda: setattr(app, "status", "from-worker"))

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()
        assert app.status == "init"  # not applied until pump drains
        runtime.pump(0.0)
        assert app.status == "from-worker"
    finally:
        runtime.close()


def test_schedule_update_runs_callback_and_marks_dirty() -> None:
    class App(BaseGrid):
        body: Any = Field(default="a")

    runtime = Runtime.offscreen(20, 3)
    try:
        app = App()
        runtime.set_root(app)
        runtime.enter()
        app.schedule_update(lambda: setattr(app, "body", "b"), field="body")
        runtime.pump(0.0)
        assert app.body == "b"
    finally:
        runtime.close()


def test_grid_update_field_missing_is_noop() -> None:
    class App(BaseGrid):
        body: Any = Field(default="a")
        count: int = Field(default=1, state=True)

    app = App()
    # Missing field, and a state field: both are no-ops, no exception.
    app.grid_update_field("does_not_exist", color="red")
    app.grid_update_field("count", color="red")


def test_loader_inline_frame_is_a_glyph() -> None:
    loader = Loader(style="spinner", symbols="line")
    assert loader.current_frame() in ("-", "\\", "|", "/")
    assert loader.inline_text() == loader.current_frame()


def test_loader_visible_false_hides() -> None:
    class App(BaseGrid):
        spin: Any = Field(
            default_factory=lambda: Loader(style="spinner", visible=False)
        )

    runtime = Runtime.offscreen(10, 1)
    try:
        app = App()
        runtime.set_root(app)
        assert runtime.render().text.strip() == ""
    finally:
        runtime.close()
