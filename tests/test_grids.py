"""tests.test_grids

---

Grid construction (the closure-based ``__init__``) and expression hooks
firing through the safe evaluator.
"""

from __future__ import annotations

import inspect

import pytest

from xnano import hooks
from xnano.components.text import Text
from xnano.core.runtime import Runtime
from xnano.fields import Field
from xnano.grids import BaseGrid


def test_grid_init_applies_defaults_and_factories() -> None:
    made: list[int] = []

    class App(BaseGrid):
        title: Text = Field(default_factory=lambda: Text("t"))
        body: str = Field(default="hello")
        count: int = Field(default=0, state=True)

    class WithFactory(BaseGrid):
        made_marker: Text = Field(
            default_factory=lambda: (made.append(1), Text("x"))[1]
        )

    app = App()
    assert app.body == "hello"
    assert app.count == 0
    assert isinstance(app.title, Text)

    # A default factory runs once per instance.
    WithFactory()
    WithFactory()
    assert made == [1, 1]


def test_grid_init_overrides_and_rejects_unknown_kwargs() -> None:
    class App(BaseGrid):
        body: str = Field(default="hello")

    assert App(body="custom").body == "custom"
    try:
        App(nope=1)  # ty: ignore[unknown-argument]
    except TypeError as error:
        assert "nope" in str(error)
    else:  # pragma: no cover - the guard must raise
        raise AssertionError("unexpected keyword should raise TypeError")


def test_grid_init_preserves_keyword_only_signature() -> None:
    class App(BaseGrid):
        body: str = Field(default="hello")

    signature = inspect.signature(App.__init__)
    assert "body" in signature.parameters
    assert signature.parameters["body"].kind is inspect.Parameter.KEYWORD_ONLY


def test_on_state_expression_fires_via_safe_evaluator() -> None:
    class AppState:
        def __init__(self) -> None:
            self.ready = False

    class App(BaseGrid):
        status: str = Field(default="idle", state=True)

        @hooks.on_state("ready")
        def _on_ready(self) -> None:
            self.status = "ready"

    state = AppState()
    runtime = Runtime.offscreen(20, 4, state=state)
    try:
        app = App()
        runtime.set_root(app)
        runtime.render()
        assert app.status == "idle"
        state.ready = True
        runtime.render()
        assert app.status == "ready"
    finally:
        runtime.close()


def test_on_field_expression_fires_via_safe_evaluator() -> None:
    class App(BaseGrid):
        count: int = Field(default=0, state=True)
        label: str = Field(default="", state=True)

        @hooks.on_field("count > 0")
        def _show_count(self) -> None:
            self.label = f"count={self.count}"

    runtime = Runtime.offscreen(20, 4)
    try:
        app = App()
        runtime.set_root(app)
        runtime.render()
        assert app.label == ""
        app.count = 3
        runtime.render()
        assert app.label == "count=3"
    finally:
        runtime.close()


def test_grid_combines_component_fields_state_and_hooks() -> None:
    class Dashboard(BaseGrid):
        title: Text = Field(default_factory=lambda: Text("Build queue"))
        status: Text = Field(default_factory=lambda: Text("idle"))
        jobs: int = Field(default=0, state=True)

        @hooks.on_field("jobs > 0")
        def _show_jobs(self) -> None:
            self.status = Text(f"{self.jobs} jobs running")

    runtime = Runtime.offscreen(30, 6)
    try:
        dashboard = Dashboard()
        runtime.set_root(dashboard)
        assert "idle" in runtime.render().text

        dashboard.jobs = 3
        frame = runtime.render()

        assert frame.contains("Build queue")
        assert frame.contains("3 jobs running")
        assert isinstance(dashboard.status, Text)
    finally:
        runtime.close()


def test_grid_non_init_fields_follow_constructor_contract() -> None:
    class App(BaseGrid):
        title: str = Field(default="hello")
        generated: str = Field(default_factory=lambda: "system", init=False)
        empty: str = Field(init=False)

    with pytest.raises(TypeError, match="unexpected keyword"):
        App(generated="override")  # ty: ignore[unknown-argument]

    app = App()
    assert app.title == "hello"
    assert app.generated == "system"
    assert app.empty is None


def test_grid_settings_merge_across_inheritance_and_body_override() -> None:
    class Parent(BaseGrid, direction="horizontal", border="plain"):
        label: str = Field(default="parent")

    class Child(Parent, gap=2):
        grid_settings = {"direction": "vertical", "padding": 1}

    child = Child()
    assert child.grid_settings["border"] == "plain"
    assert child.grid_settings["gap"] == 2
    assert child.grid_settings["direction"] == "vertical"
    assert child.grid_settings["padding"] == 1


def test_runtime_field_patch_combines_style_sizing_and_slide() -> None:
    class App(BaseGrid):
        body: str = Field(default="ready", slide=("x", "y"))
        count: int = Field(default=1, state=True)

    runtime = Runtime.offscreen(30, 8)
    try:
        app = App()
        runtime.set_root(app)
        runtime.render()

        app.grid_set_field(
            "body",
            "updated",
            position=(999, 999),
            class_name="text-red-500 bg-slate-900 p-1 rounded",
            width=16,
            height=6,
            bold=True,
        )
        frame = runtime.render()
        info = app._grid_field_info("body")

        assert frame.contains("updated")
        assert info.width is not None and info.width.value == 16
        assert info.height is not None and info.height.value == 6
        assert info.modifiers == ("bold",)
        assert info.border == "rounded"
        assert app.grid_field_position("body") != (999, 999)

        with pytest.raises(TypeError, match="state field"):
            app.grid_set_field("count", 2)
        with pytest.raises(AttributeError, match="no layout field"):
            app.grid_set_field("missing", "value")
    finally:
        runtime.close()
