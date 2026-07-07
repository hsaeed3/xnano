"""Tests for xnano Grid field initialization."""

from __future__ import annotations

from xnano.beta import Field, Grid
from xnano_core.core import CoreSession
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
