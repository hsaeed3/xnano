"""tests.beta.test_focus_navigation

---

Autofocus enables arrow-key spatial navigation and click-to-focus, computed
from live layout geometry. Input(auto_height) grows a fit slot with content.
"""

from __future__ import annotations

from typing import Any

from xnano.beta.components.button import Button
from xnano.beta.components.input import Input
from xnano.beta.core import Runtime
from xnano.beta.events import Event, KeyboardEventData, MouseEventData
from xnano.beta.fields import Field
from xnano.beta.grids import BaseGrid
from xnano.beta.utils.focus import ensure_default_field_focus


def _vertical_buttons() -> type[BaseGrid]:
    class App(BaseGrid, direction="vertical"):
        a: Any = Field(
            default_factory=lambda: Button(label="A"),
            group="a",
            autofocus=True,
            height=1,
        )
        b: Any = Field(
            default_factory=lambda: Button(label="B"), group="b", height=1
        )
        c: Any = Field(
            default_factory=lambda: Button(label="C"), group="c", height=1
        )

    return App


def test_autofocus_selects_declared_field() -> None:
    runtime = Runtime.offscreen(20, 3)
    try:
        app = _vertical_buttons()()
        runtime.set_root(app)
        runtime.render()
        ensure_default_field_focus(runtime)
        assert runtime.focused_group == "a"
    finally:
        runtime.close()


def test_arrow_keys_move_focus_spatially() -> None:
    runtime = Runtime.offscreen(20, 3)
    try:
        app = _vertical_buttons()()
        runtime.set_root(app)
        runtime.render()
        ensure_default_field_focus(runtime)
        runtime.dispatch(
            Event.from_data(KeyboardEventData.from_binding("down"))
        )
        assert runtime.focused_group == "b"
        runtime.dispatch(
            Event.from_data(KeyboardEventData.from_binding("down"))
        )
        assert runtime.focused_group == "c"
        runtime.dispatch(Event.from_data(KeyboardEventData.from_binding("up")))
        assert runtime.focused_group == "b"
    finally:
        runtime.close()


def test_click_moves_focus() -> None:
    runtime = Runtime.offscreen(20, 3)
    try:
        app = _vertical_buttons()()
        runtime.set_root(app)
        runtime.render()
        ensure_default_field_focus(runtime)
        # Row 2 holds button C.
        runtime.dispatch(
            Event.from_data(
                MouseEventData(kind="press", x=1, y=2, button="left")
            )
        )
        assert runtime.focused_group == "c"
    finally:
        runtime.close()


def test_arrow_focus_disabled_without_autofocus() -> None:
    class App(BaseGrid, direction="vertical"):
        a: Any = Field(
            default_factory=lambda: Button(label="A"), group="a", height=1
        )
        b: Any = Field(
            default_factory=lambda: Button(label="B"), group="b", height=1
        )

    runtime = Runtime.offscreen(20, 2)
    try:
        app = App()
        runtime.set_root(app)
        runtime.render()
        from xnano.beta.utils.focus import (
            collect_focusable_fields,
            set_field_focus,
        )

        set_field_focus(runtime, collect_focusable_fields(runtime)[0])
        # Arrow keys are not hijacked when no field declares autofocus.
        consumed_before = runtime.focused_group
        runtime.dispatch(
            Event.from_data(KeyboardEventData.from_binding("down"))
        )
        assert runtime.focused_group == consumed_before
    finally:
        runtime.close()


def test_input_auto_height_grows_and_clamps() -> None:
    class App(BaseGrid, direction="vertical"):
        history: Any = Field(default="top", height="1fr")
        composer: Any = Field(
            default_factory=lambda: Input(
                content="",
                auto_height=True,
                min_rows=1,
                max_rows=5,
                wrap=True,
            ),
            height="fit",
            border="rounded",
        )

    runtime = Runtime.offscreen(20, 12)
    try:
        app = App()
        runtime.set_root(app)
        runtime.render()

        def composer_height() -> int:
            area = runtime.stage.get_area("composer")
            assert area is not None
            return area.height

        assert composer_height() == 3  # 1 row + rounded border
        app.composer.value = "x" * 40
        runtime.render()
        assert composer_height() > 3
        app.composer.value = "y" * 400
        runtime.render()
        assert composer_height() == 7  # max_rows 5 + border 2
    finally:
        runtime.close()
