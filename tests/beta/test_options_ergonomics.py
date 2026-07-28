"""tests.beta.test_options_ergonomics

---

Options filter modes, submission accept policy, stable value selection, and
the reserved-slot layout pattern.
"""

from __future__ import annotations

from typing import Any

from xnano.beta.components.options import Option, Options
from xnano.beta.core import Runtime
from xnano.beta.fields import Field
from xnano.beta.grids import BaseGrid


def test_filter_modes() -> None:
    opts = Options(items=("apple", "apricot", "banana"), query="ap")
    opts.filter = "prefix"
    assert opts.visible_items == ("apple", "apricot")
    opts.filter = "none"
    assert opts.visible_items == ("apple", "apricot", "banana")
    opts.filter = lambda query, text: text.startswith("b")
    assert opts.visible_items == ("banana",)
    opts.filter = False
    assert opts.visible_items == ("apple", "apricot", "banana")


def test_accept_policies() -> None:
    opts = Options(items=("/model", "/memory"), query="/mod")
    opts.selected = 0
    opts.accept = "if_prefix_only"
    assert opts.resolve_submission("/mod") == "/model"
    assert opts.resolve_submission("/model gpt") == "/model gpt"
    opts.accept = "replace"
    assert opts.resolve_submission("/mod") == "/model"
    opts.accept = "extend"
    assert opts.resolve_submission("/mod") == "/mod"


def test_select_value_survives_rebuild() -> None:
    opts = Options(items=(Option("A", value="a"), Option("B", value="b")))
    opts.selected = 1
    assert opts.selected_value == "b"
    opts.items = (
        Option("X", value="x"),
        Option("B", value="b"),
        Option("A", value="a"),
    )
    assert opts.select_value("b") is True
    assert opts.selected_value == "b"


def test_reserved_slot_keeps_layout_stable() -> None:
    class App(BaseGrid, direction="vertical"):
        header: Any = Field(default="HEADER", height=1)
        palette: Any = Field(default=None, visible=True, height=4)
        footer: Any = Field(default="FOOTER", height=1)

    runtime = Runtime.offscreen(20, 8)
    try:
        app = App()
        runtime.set_root(app)
        runtime.render()
        first_footer = runtime.stage.get_area("footer")
        assert first_footer is not None
        footer_y = first_footer.y
        app.palette = Options(items=("one", "two"))
        runtime.render()
        second_footer = runtime.stage.get_area("footer")
        assert second_footer is not None
        assert second_footer.y == footer_y
    finally:
        runtime.close()
