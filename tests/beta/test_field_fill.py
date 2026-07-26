"""tests.beta.test_field_fill

---

Field/Text background fill: a set ``background`` fills the whole slot by
default, ``fill=False`` reverts to accent-behind-glyphs.
"""

from __future__ import annotations

from typing import Any

from xnano.beta.core import Runtime
from xnano.beta.fields import Field
from xnano.beta.grids import BaseGrid
from xnano.beta.types import frame_from_field


def test_background_fills_slot_by_default() -> None:
    field = Field(default="", background="blue")
    frame = frame_from_field(field)
    assert frame is not None
    assert frame.background == "blue"


def test_fill_false_reverts_to_accent() -> None:
    field = Field(default="", background="blue", fill=False)
    assert frame_from_field(field) is None


def test_fill_true_without_chrome_produces_frame() -> None:
    field = Field(default="", background="red", fill=True)
    frame = frame_from_field(field)
    assert frame is not None and frame.background == "red"


def test_grid_update_field_toggles_fill() -> None:
    class App(BaseGrid):
        body: Any = Field(default="hi", background="blue")

    runtime = Runtime.offscreen(20, 6)
    try:
        app = App()
        runtime.set_root(app)
        runtime.render()
        # Full-slot fill: painting cannot raise and the frame carries bg.
        assert app._grid_field_frame("body", app._grid_field_info("body"))
        app.grid_update_field("body", fill=False)
        runtime.render()
        assert (
            app._grid_field_frame("body", app._grid_field_info("body")) is None
        )
    finally:
        runtime.close()
