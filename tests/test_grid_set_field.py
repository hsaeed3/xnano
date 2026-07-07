"""Tests for Grid.grid_set_field and grid-slot component positioning."""

from __future__ import annotations

import pytest

from xnano.beta import Field, Grid, Terminal
from xnano.beta.components import Text
from xnano.beta.exceptions import FieldValidationError
from xnano.beta.fields import UNSET
from xnano.beta.types import Area


class LayoutGrid(Grid):
    body: str = Field(default="hello")


class StatefulGrid(Grid):
    body: str = Field(default="hello")
    count: int = Field(default=0, state=True)


def test_set_field_updates_value() -> None:
    grid = LayoutGrid()
    grid.grid_set_field("body", "world")
    assert grid.body == "world"


def test_set_field_updates_field_metadata() -> None:
    grid = LayoutGrid()
    grid.grid_set_field("body", visible=False, color="red")
    field = grid._grid_field_info("body")
    assert field.visible is False
    assert field.color == "red"
    assert grid.body == "hello"


def test_set_field_metadata_only() -> None:
    grid = LayoutGrid()
    grid.grid_set_field("body", value=UNSET, border="rounded")
    assert grid._grid_field_info("body").border == "rounded"
    assert grid.body == "hello"


def test_set_field_rejects_state_fields() -> None:
    grid = StatefulGrid()
    with pytest.raises(TypeError, match="state field"):
        grid.grid_set_field("count", 1)


def test_set_field_rejects_unknown_field() -> None:
    grid = LayoutGrid()
    with pytest.raises(AttributeError, match="missing"):
        grid.grid_set_field("missing", "x")


def test_set_field_rejects_immutable_keys() -> None:
    grid = LayoutGrid()
    with pytest.raises(TypeError, match="default"):
        grid.grid_set_field("body", default="nope")


def test_set_field_validates_when_strict() -> None:
    grid = LayoutGrid()
    with pytest.raises(FieldValidationError, match="body"):
        grid.grid_set_field("body", 123)


def test_grid_slot_renders_text_component_offscreen() -> None:
    class TextGrid(Grid):
        body: Text = Field(default_factory=lambda: Text(content="hello"))

    terminal = Terminal.offscreen(cols=40, rows=8)
    grid = TextGrid()
    terminal.run.__func__  # verify it's a callable
    from xnano.beta.types import Area

    terminal._track_frame_grid(grid)
    sess = terminal.session
    sess.begin_frame()
    grid._grid_build_frame(Area(x=0, y=0, width=40, height=8), sess)
    sess.commit_requests()
    output = sess.get_core_session_output_text()
    assert "hello" in output


def test_set_field_accepts_text_component() -> None:
    class TextGrid(Grid):
        body: Text = Field(default_factory=lambda: Text(content="init"))

    grid = TextGrid()
    grid.grid_set_field("body", Text(content="updated"))
    assert isinstance(grid.body, Text)
    assert grid.body.content == "updated"
