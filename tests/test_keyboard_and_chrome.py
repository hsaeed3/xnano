"""tests.test_keyboard_and_chrome

---

Bare-modifier keyboard bindings and the chrome-owns-the-border rule for
nested grids.
"""

from __future__ import annotations

from typing import Any

from xnano.core import Runtime
from xnano.events import KeyboardEventData
from xnano.fields import Field
from xnano.grids import BaseGrid


def test_bare_modifier_binding_matches_modifier_press() -> None:
    assert KeyboardEventData.from_binding("shift").matches("shift")
    assert KeyboardEventData.from_binding("ctrl").matches("ctrl")
    assert not KeyboardEventData.from_binding("shift").matches("ctrl")


def test_bare_modifier_does_not_match_modified_key() -> None:
    event = KeyboardEventData.from_binding("shift+a")
    assert not event.matches("shift")
    assert event.matches("shift+a")


def test_plain_key_unaffected_by_bare_modifier_support() -> None:
    event = KeyboardEventData.from_binding("a")
    assert event.matches("a")
    assert not event.matches("shift")


def test_chrome_owns_border_suppresses_nested_double_border() -> None:
    class Inner(BaseGrid, border="double"):
        label: Any = Field(default="X")

    class App(BaseGrid):
        inner: Any = Field(default_factory=Inner, border="rounded")

    runtime = Runtime.offscreen(14, 4)
    try:
        app = App()
        runtime.set_root(app)
        text = runtime.render().text
        assert "╭" in text  # field's rounded border is drawn
        assert "╔" not in text  # nested double border suppressed
    finally:
        runtime.close()


def test_nested_border_kept_without_field_border() -> None:
    class Inner(BaseGrid, border="double"):
        label: Any = Field(default="X")

    class App(BaseGrid):
        inner: Any = Field(default_factory=Inner)

    runtime = Runtime.offscreen(14, 4)
    try:
        app = App()
        runtime.set_root(app)
        text = runtime.render().text
        assert "╔" in text  # nested grid keeps its own border
    finally:
        runtime.close()
