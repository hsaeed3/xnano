"""Tests for xnano Grid field initialization."""

from __future__ import annotations

from xnano.fields import Field
from xnano.grid import Grid
from xnano.components.text import Text
from xnano_core.core import CoreSession
from xnano_core.rust import native
from xnano.core.controllers.terminal import TerminalController
from xnano.types import Area as GridArea


class Leaf(Grid):
    label: str = Field(default="hello")


class Root(Grid, direction="horizontal"):
    left: Leaf = Field(default_factory=Leaf)
    right: Leaf = Field(default_factory=Leaf)


def test_default_factory_creates_instances() -> None:
    root = Root()
    assert isinstance(root.left, Leaf)
    assert isinstance(root.right, Leaf)
    assert root.left is not root.right
    assert root.left.label == "hello"


class OptionalPanel(Grid, direction="vertical"):
    body: Text = Field(default=Text("visible"))
    overlay: Text | None = Field(
        default=None, border="rounded", title="Overlay"
    )


def test_nullable_layout_field_hidden_when_none() -> None:
    grid = OptionalPanel()
    core = CoreSession.offscreen(width=40, height=10)
    session = TerminalController(
        core,
        terminal_width=40,
        terminal_height=10,
        is_offscreen=True,
    )
    grid._grid_build_frame(GridArea(x=0, y=0, width=40, height=10), session)
    session.commit_requests()
    output = session.get_core_session_output_text()
    assert "visible" in output
    assert "Overlay" not in output


def test_nullable_layout_field_renders_when_set() -> None:
    grid = OptionalPanel()
    grid.overlay = Text("shown")
    core = CoreSession.offscreen(width=40, height=10)
    session = TerminalController(
        core,
        terminal_width=40,
        terminal_height=10,
        is_offscreen=True,
    )
    grid._grid_build_frame(GridArea(x=0, y=0, width=40, height=10), session)
    session.commit_requests()
    output = session.get_core_session_output_text()
    assert "shown" in output
    assert "Overlay" in output


def test_grid_play_effect_targets_layout_field_area() -> None:
    class EffectGrid(Grid):
        body: Text = Field(default=Text("hello"))

    grid = EffectGrid()
    core = CoreSession.offscreen(width=40, height=8)
    session = TerminalController(
        core,
        terminal_width=40,
        terminal_height=8,
        is_offscreen=True,
    )
    grid._grid_build_frame(GridArea(x=0, y=0, width=40, height=8), session)
    session.commit_requests()
    from xnano.effects import resolve_effect

    assert session.play_effect(
        resolve_effect("dissolve", duration_ms=200),
        fields=["body"],
    )
    assert core.is_animating()


def test_field_text_background_does_not_paint_frame() -> None:
    class App(Grid, direction="vertical"):
        header: str = Field(
            default="My App",
            height=1,
            color="white",
            background="violet",
        )
        body: str = Field(default="Hello, world!")

    grid = App()
    core = CoreSession.offscreen(width=40, height=6)
    session = TerminalController(
        core,
        terminal_width=40,
        terminal_height=6,
        is_offscreen=True,
    )
    grid._grid_build_frame(GridArea(x=0, y=0, width=40, height=6), session)
    session.commit_requests()
    output = session.get_core_session_output_text()
    lines = output.splitlines()
    assert lines[0] == "My App"
    assert lines[1] == "Hello, world!"
    assert "┌" not in output


def test_field_background_covers_text_span_only() -> None:
    # A field background should paint behind the text glyphs only, not flood
    # the whole slot to the right edge. "violet" == #ee82ee.
    class App(Grid, direction="vertical"):
        header: str = Field(
            default="My App",
            height=1,
            color="white",
            background="violet",
        )
        body: str = Field(default="Hello, world!")

    grid = App()
    core = CoreSession.offscreen(width=40, height=6)
    session = TerminalController(
        core,
        terminal_width=40,
        terminal_height=6,
        is_offscreen=True,
    )
    grid._grid_build_frame(GridArea(x=0, y=0, width=40, height=6), session)
    session.commit_requests()

    buffer = core.buffer_snapshot()
    violet = native.Color.rgb(238, 130, 238)
    # "My App" is 6 cells: every glyph cell carries the accent background.
    for x in range(len("My App")):
        assert buffer.cell_bg(x, 0) == violet
    # Trailing cells stay unpainted rather than a full-width bar.
    for x in (len("My App"), 20, 39):
        assert buffer.cell_bg(x, 0) != violet


def test_field_defaults_render_offscreen() -> None:
    root = Root()
    core = CoreSession.offscreen(width=40, height=8)
    session = TerminalController(
        core,
        terminal_width=40,
        terminal_height=8,
        is_offscreen=True,
    )
    root._grid_build_frame(GridArea(x=0, y=0, width=40, height=8), session)
    session.commit_requests()
    output = session.get_core_session_output_text()
    assert output.count("hello") == 2
