"""tests.beta.test_grids

---

Grid construction (the closure-based ``__init__``) and expression hooks
firing through the safe evaluator.
"""

from __future__ import annotations

import inspect

from xnano.beta import hooks
from xnano.beta.components.text import Text
from xnano.beta.core.runtime import Runtime
from xnano.beta.fields import Field
from xnano.beta.grids import BaseGrid


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
