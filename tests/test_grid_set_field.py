"""Tests for BaseGrid.grid_set_field and grid-slot component positioning."""

from __future__ import annotations

from typing import Any

import pytest

from xnano.components.text import Text
from xnano.core.exceptions import FieldValidationError
from xnano.fields import UNSET, Field
from xnano.grid import BaseGrid
from xnano.terminal import Terminal


class LayoutGrid(BaseGrid):
    body: str = Field(default="hello")


class StatefulGrid(BaseGrid):
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
    set_field: Any = grid.grid_set_field
    with pytest.raises(TypeError, match="default"):
        set_field("body", default="nope")


def test_set_field_validates_when_strict() -> None:
    grid = LayoutGrid()
    with pytest.raises(FieldValidationError, match="body"):
        grid.grid_set_field("body", 123)


def test_update_field_changes_style_without_value_param() -> None:
    grid = LayoutGrid()
    grid.grid_update_field("body", color="red", modifiers=["bold"])
    field = grid._grid_field_info("body")
    assert field.color == "red"
    assert field.modifiers == ["bold"]
    assert grid.body == "hello"


def test_update_field_rejects_state_fields() -> None:
    grid = StatefulGrid()
    with pytest.raises(TypeError, match="state field"):
        grid.grid_update_field("count", color="red")


def test_update_field_rejects_unknown_field() -> None:
    grid = LayoutGrid()
    with pytest.raises(AttributeError, match="missing"):
        grid.grid_update_field("missing", color="red")


def test_set_field_is_noop_when_value_unchanged() -> None:
    grid = LayoutGrid()
    grid.grid_set_field("body", visible=False)
    assert grid._grid_has_field_overrides()
    grid.grid_set_field("body", visible=False)
    override_after_first_change = grid._grid_field_info("body")
    grid.grid_set_field("body", visible=False)
    assert grid._grid_field_info("body") is override_after_first_change


def test_set_field_creates_override_when_value_changes() -> None:
    grid = LayoutGrid()
    grid.grid_set_field("body", visible=False)
    assert grid._grid_has_field_overrides()


def test_update_field_has_no_value_or_position_parameters() -> None:
    grid = LayoutGrid()
    update_field: Any = grid.grid_update_field
    with pytest.raises(TypeError):
        update_field("body", value="nope")
    with pytest.raises(TypeError):
        update_field("body", position=(1, 1))


def test_grid_slot_renders_text_component_offscreen() -> None:
    class TextGrid(BaseGrid):
        body: Text = Field(default_factory=lambda: Text(content="hello"))

    terminal = Terminal.offscreen(cols=40, rows=8)
    grid = TextGrid()
    terminal.run.__func__  # verify it's a callable
    from xnano._types import Area

    terminal._track_frame_grid(grid)
    sess = terminal.session
    sess.begin_viewport_frame()
    grid._grid_build_frame(Area(x=0, y=0, width=40, height=8), sess)
    sess.commit_requests()
    output = sess.get_core_session_output_text()
    assert "hello" in output


def test_set_field_accepts_text_component() -> None:
    class TextGrid(BaseGrid):
        body: Text = Field(default_factory=lambda: Text(content="init"))

    grid = TextGrid()
    grid.grid_set_field("body", Text(content="updated"))
    assert isinstance(grid.body, Text)
    assert grid.body.content == "updated"
