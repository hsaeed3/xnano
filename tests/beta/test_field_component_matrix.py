"""tests.beta.test_field_component_matrix

---

Exercise every public Field option and every concrete beta component through
the real offscreen grid renderer.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, cast

import pytest

from xnano.beta.components import (
    Bar,
    Button,
    Chart,
    Dropdown,
    Image,
    ImageData,
    ImageFrame,
    Input,
    Link,
    Loader,
    Markdown,
    Options,
    Scrollbar,
    Select,
    Table,
    Text,
)
from xnano.beta.core import Runtime
from xnano.beta.fields import Field, GridFieldInfo
from xnano.beta.grids import BaseGrid


_COMPONENTS: tuple[tuple[str, Callable[[], Any]], ...] = (
    ("bar", lambda: Bar(data=[1, 3, 2])),
    ("button", lambda: Button(label="Run")),
    ("chart", lambda: Chart(series={"cpu": [1, 3, 2]})),
    ("dropdown", lambda: Dropdown(items=("one", "two"))),
    (
        "image",
        lambda: Image(
            source=ImageData(
                width=1,
                height=2,
                frames=(ImageFrame(bytes((255, 0, 0, 0, 0, 0)), 50),),
            )
        ),
    ),
    ("input", lambda: Input("query")),
    ("link", lambda: Link("docs", url="https://example.com")),
    ("loader", lambda: Loader(value=0.5, style="bar")),
    ("markdown", lambda: Markdown("**ready**")),
    ("options", lambda: Options(items=("one", "two"))),
    ("scrollbar", lambda: Scrollbar(content_length=20, viewport_length=5)),
    ("select", lambda: Select(items=("one", "two"))),
    ("table", lambda: Table(data=[{"name": "api", "status": "ok"}])),
    ("text", lambda: Text("ready")),
)

_FIELD_PROFILES: tuple[tuple[str, dict[str, Any]], ...] = (
    ("plain", {}),
    (
        "chrome",
        {
            "border": "rounded",
            "border_sides": ("top", "right", "bottom", "left"),
            "border_color": "cyan",
            "title": "Field",
            "title_position": "top",
            "padding": 1,
            "margin": 1,
        },
    ),
    (
        "layout",
        {
            "width": "75%",
            "height": "75%",
            "gap": 1,
            "direction": "horizontal",
            "align": "center",
        },
    ),
    (
        "style",
        {
            "color": "yellow",
            "background": "blue",
            "modifiers": ("bold", "underline"),
            "class_name": "p-1 text-red-500 bg-slate-900",
        },
    ),
    (
        "interactive",
        {
            "slide": ("x", "y"),
            "group": "main",
            "autofocus": True,
            "scroll": True,
            "wireframe": True,
        },
    ),
)


@pytest.mark.parametrize(
    ("component_name", "factory"),
    _COMPONENTS,
    ids=[item[0] for item in _COMPONENTS],
)
@pytest.mark.parametrize(
    ("profile_name", "field_options"),
    _FIELD_PROFILES,
    ids=[item[0] for item in _FIELD_PROFILES],
)
def test_every_component_renders_in_every_field_profile(
    component_name: str,
    factory: Callable[[], Any],
    profile_name: str,
    field_options: dict[str, Any],
) -> None:
    class App(BaseGrid):
        content: Any = Field(default_factory=factory, **field_options)

    runtime = Runtime.offscreen(48, 12)
    try:
        app = App()
        runtime.set_root(app)
        frame = runtime.render()
        assert frame.width == 48, (component_name, profile_name)
        assert frame.height == 12, (component_name, profile_name)
        assert runtime.stage.get_area("content") is not None
    finally:
        runtime.close()


def test_every_field_parameter_is_explicitly_covered() -> None:
    covered = {
        "default",
        "default_factory",
        "state",
        "strict",
        "init",
        "visible",
        *{
            name
            for _, profile in _FIELD_PROFILES
            for name in profile
        },
    }
    parameters = set(inspect.signature(Field).parameters)
    assert covered == parameters

    hidden = cast(GridFieldInfo, Field(default="hidden", visible=False))
    state = cast(
        GridFieldInfo,
        Field(default=1, state=True, strict=True, init=False),
    )
    factory = cast(
        GridFieldInfo,
        Field(default_factory=lambda: "made"),
    )
    assert hidden.visible is False
    assert state.state is True and state.strict is True and state.init is False
    assert factory.default_factory is not None


def test_field_options_work_together_on_container_values() -> None:
    class App(BaseGrid):
        items: list[str] = Field(
            default_factory=lambda: ["one", "two", "three"],
            color="yellow",
            background="blue",
            width="fit",
            height="fit",
            gap=1,
            direction="vertical",
            align="center",
            border="double",
            border_color="cyan",
            title="Rows",
            padding=(1, 2),
            margin=1,
            slide=("x", "y"),
            group="rows",
            scroll=True,
            wireframe=True,
            class_name="font-bold",
        )

    runtime = Runtime.offscreen(32, 12)
    try:
        app = App()
        runtime.set_root(app)
        frame = runtime.render()
        assert "Rows" in frame.text
        assert "·" in frame.text
        assert runtime.stage.get_area("items") is not None
    finally:
        runtime.close()
