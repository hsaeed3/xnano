"""tests.beta.test_field_scroll

---

Field(scroll=) paints a windowed offset, reserves slot height, follows the
tail, and moves on the mouse wheel.
"""

from __future__ import annotations

from typing import Any

from xnano.beta.components.text import Text
from xnano.beta.core import Runtime
from xnano.beta.events import Event, MouseEventData
from xnano.beta.fields import Field
from xnano.beta.grids import BaseGrid


def _make_app() -> type[BaseGrid]:
    class App(BaseGrid):
        body: Any = Field(
            default_factory=lambda: Text(
                content="\n".join(f"line{i}" for i in range(20)),
                wrap=False,
            ),
            height=5,
            scroll=True,
        )

    return App


def test_scroll_windows_and_reserves_height() -> None:
    runtime = Runtime.offscreen(20, 5)
    try:
        app = _make_app()()
        runtime.set_root(app)
        top = runtime.render().text
        assert "line0" in top and "line4" in top and "line5" not in top
        handle = app._grid_scroll_handle("body")
        handle.scroll(7)
        mid = runtime.render().text
        assert "line7" in mid and "line0" not in mid
    finally:
        runtime.close()


def test_scroll_follow_tail() -> None:
    runtime = Runtime.offscreen(20, 5)
    try:
        app = _make_app()()
        runtime.set_root(app)
        runtime.render()
        app._grid_scroll_handle("body").scroll_to_end()
        tail = runtime.render().text
        assert "line19" in tail and "line15" in tail and "line14" not in tail
    finally:
        runtime.close()


def test_scroll_short_content_reserves_full_height() -> None:
    class App(BaseGrid):
        body: Any = Field(
            default_factory=lambda: Text(content="only\ntwo", wrap=False),
            height=5,
            scroll=True,
        )

    runtime = Runtime.offscreen(20, 5)
    try:
        app = App()
        runtime.set_root(app)
        frame = runtime.render()
        assert frame.height == 5
        assert app._grid_scroll_handle("body").offset == 0
    finally:
        runtime.close()


def test_mouse_wheel_moves_scroll() -> None:
    runtime = Runtime.offscreen(20, 5)
    try:
        app = _make_app()()
        runtime.set_root(app)
        runtime.render()
        for _ in range(3):
            runtime.dispatch(
                Event.from_data(MouseEventData(kind="scroll_down", x=2, y=2))
            )
        assert app._grid_scroll_handle("body").offset == 9
        wheeled = runtime.render().text
        assert "line9" in wheeled
    finally:
        runtime.close()
