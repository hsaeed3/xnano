"""tests.beta.test_responsive_render

---

Optional ``grid_render_<size>`` / ``compose_<size>`` variants run for the
matching viewport breakpoint, and classes that override none stay
zero-cost (empty override map, no per-frame dispatch).
"""

from __future__ import annotations

import dataclasses

from xnano.beta.components.component import Component, TextBlock
from xnano.beta.fields import Field
from xnano.beta.grids import BaseGrid
from xnano.beta.terminal import Terminal
from xnano.beta.utils.responsive import breakpoint_for_width


def test_breakpoint_thresholds() -> None:
    assert breakpoint_for_width(20) == "extra_small"
    assert breakpoint_for_width(39) == "extra_small"
    assert breakpoint_for_width(40) == "small"
    assert breakpoint_for_width(79) == "small"
    assert breakpoint_for_width(80) == "medium"
    assert breakpoint_for_width(119) == "medium"
    assert breakpoint_for_width(120) == "large"
    assert breakpoint_for_width(159) == "large"
    assert breakpoint_for_width(160) == "extra_large"
    assert breakpoint_for_width(400) == "extra_large"


def test_grid_without_variants_has_empty_override_map() -> None:
    class Plain(BaseGrid):
        label: str = Field(default="")

    assert Plain._grid_responsive_renders == {}


def test_grid_render_variant_runs_for_matching_breakpoint() -> None:
    class App(BaseGrid):
        label: str = Field(default="")

        def grid_render_small(self) -> None:
            self.label = "compact"

        def grid_render_large(self) -> None:
            self.label = "wide"

    assert App._grid_responsive_renders == {
        "small": "grid_render_small",
        "large": "grid_render_large",
    }

    small = App()
    terminal = Terminal.offscreen(cols=60, rows=4)
    terminal.attach_grid(small)
    terminal.render()
    assert small.label == "compact"
    terminal.close()

    large = App()
    terminal = Terminal.offscreen(cols=140, rows=4)
    terminal.attach_grid(large)
    terminal.render()
    assert large.label == "wide"
    terminal.close()

    # Medium tier has no override — the base no-op leaves label untouched.
    medium = App()
    terminal = Terminal.offscreen(cols=90, rows=4)
    terminal.attach_grid(medium)
    terminal.render()
    assert medium.label == ""
    terminal.close()


def test_grid_render_variant_runs_after_grid_render() -> None:
    calls: list[str] = []

    class App(BaseGrid):
        label: str = Field(default="")

        def grid_render(self) -> None:
            calls.append("render")

        def grid_render_small(self) -> None:
            calls.append("small")

    app = App()
    terminal = Terminal.offscreen(cols=50, rows=4)
    terminal.attach_grid(app)
    terminal.render()
    assert calls == ["render", "small"]
    terminal.close()


def test_grid_render_variant_fires_once_per_breakpoint_not_per_frame() -> None:
    # The size variant runs on the opening resize, then stays quiet while
    # the window holds the same breakpoint — so it does not clobber a
    # per-frame mutation such as an ``@on_tick`` append.
    from xnano.beta.actions import Action
    from xnano.beta.hooks import on_tick

    size_calls: list[str] = []

    class App(BaseGrid):
        name: str = Field(default="")

        @on_tick(0)
        def tick(self) -> None:
            self.name = self.name + "a"

        def grid_render_large(self) -> None:
            size_calls.append("large")
            self.name = "base"

    app = App()
    terminal = Terminal.offscreen(cols=140, rows=4)
    terminal.attach_grid(app)
    terminal.render()
    assert size_calls == ["large"]
    assert app.name == "base"
    for _ in range(3):
        terminal.runtime.perform(Action.tick(interval_ms=1))
        terminal.render()
    # Variant fired only on the first render; the ticks accumulated.
    assert size_calls == ["large"]
    assert app.name == "baseaaa"
    terminal.close()


def test_component_without_variants_has_empty_override_map() -> None:
    @dataclasses.dataclass
    class Plain(Component):
        def compose(self, ctx):
            return TextBlock(text="plain")

    assert Plain._component_responsive_composes == {}


def test_compose_variant_replaces_compose_for_breakpoint() -> None:
    @dataclasses.dataclass
    class Adaptive(Component):
        def compose(self, ctx):
            return TextBlock(text="DEFAULT")

        def compose_small(self, ctx):
            return TextBlock(text="SMALL")

        def compose_large(self, ctx):
            return TextBlock(text="LARGE")

    assert Adaptive._component_responsive_composes == {
        "small": "compose_small",
        "large": "compose_large",
    }

    class Host(BaseGrid):
        body: Adaptive = Field(default_factory=Adaptive)

    terminal = Terminal.offscreen(cols=60, rows=3)
    terminal.attach_grid(Host())
    assert "SMALL" in terminal.render().text
    terminal.close()

    terminal = Terminal.offscreen(cols=140, rows=3)
    terminal.attach_grid(Host())
    assert "LARGE" in terminal.render().text
    terminal.close()

    # Medium tier falls back to the base compose.
    terminal = Terminal.offscreen(cols=90, rows=3)
    terminal.attach_grid(Host())
    assert "DEFAULT" in terminal.render().text
    terminal.close()
