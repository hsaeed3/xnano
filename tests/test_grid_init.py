"""Tests for xnano Grid field initialization."""

from __future__ import annotations

from xnano.beta import Field, Grid, Text
from xnano_core.core import CoreSession
from xnano_core.rust import native
from xnano.beta.core.session import Session
from xnano.beta.types import Area as GridArea


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
    session = Session(
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
    session = Session(
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
    session = Session(
        core,
        terminal_width=40,
        terminal_height=8,
        is_offscreen=True,
    )
    grid._grid_build_frame(GridArea(x=0, y=0, width=40, height=8), session)
    session.commit_requests()
    from xnano.beta.effects import resolve_native_effect

    assert session.grid_play_effect(
        resolve_native_effect("dissolve", duration_ms=200),
        fields=["body"],
    )
    assert core.is_animating()


def test_field_defaults_render_offscreen() -> None:
    root = Root()
    core = CoreSession.offscreen(width=40, height=8)
    session = Session(
        core,
        terminal_width=40,
        terminal_height=8,
        is_offscreen=True,
    )
    root._grid_build_frame(GridArea(x=0, y=0, width=40, height=8), session)
    session.commit_requests()
    output = session.get_core_session_output_text()
    assert output.count("hello") == 2
