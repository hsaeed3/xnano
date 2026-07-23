"""Tests for list/tuple container fields (BaseGrid.paint_field_slot)."""

from __future__ import annotations

from xnano._types import Area
from xnano.components.text import Text
from xnano.core.controllers.tui import TerminalController
from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano_core.core import CoreSession


def _render(grid: BaseGrid, *, width: int = 40, height: int = 12) -> str:
    core = CoreSession.offscreen(width=width, height=height)
    session = TerminalController(
        core, terminal_width=width, terminal_height=height, is_offscreen=True
    )
    grid._grid_build_frame(Area(x=0, y=0, width=width, height=height), session)
    session.commit_requests()
    return session.get_core_session_output_text()


def test_list_of_strings_renders_each_on_its_own_line() -> None:
    class G(BaseGrid, direction="vertical"):
        items: list = Field(default_factory=list, direction="vertical")

    grid = G()
    grid.items = ["a", "b", "c"]
    output = _render(grid)
    assert "a" in output
    assert "b" in output
    assert "c" in output
    # Must not fall back to the raw Python repr.
    assert "[" not in output


def test_list_of_text_components_renders_each_item() -> None:
    class G(BaseGrid, direction="vertical"):
        items: list = Field(default_factory=list, direction="vertical")

    grid = G()
    grid.items = [Text("hello"), Text("world")]
    output = _render(grid)
    assert "hello" in output
    assert "world" in output


def test_nested_list_falls_through_to_str_one_level_only() -> None:
    class G(BaseGrid, direction="vertical"):
        items: list = Field(default_factory=list, direction="vertical")

    grid = G()
    grid.items = ["a", ["b", "c"], "d"]
    output = _render(grid)
    assert "a" in output
    assert "d" in output
    # The inner list is NOT expanded — it renders as its Python repr.
    assert "['b', 'c']" in output


def test_empty_list_renders_nothing() -> None:
    class G(BaseGrid, direction="vertical"):
        items: list = Field(default_factory=list, direction="vertical")

    grid = G()
    grid.items = []
    output = _render(grid)
    assert output.strip() == ""


def test_gap_inserts_blank_space_between_items() -> None:
    class GNoGap(BaseGrid, direction="vertical"):
        items: list = Field(default_factory=list, direction="vertical", gap=0)

    class GWithGap(BaseGrid, direction="vertical"):
        items: list = Field(default_factory=list, direction="vertical", gap=2)

    no_gap = GNoGap()
    no_gap.items = ["a", "b"]
    with_gap = GWithGap()
    with_gap.items = ["a", "b"]

    no_gap_output = _render(no_gap)
    gap_output = _render(with_gap)
    assert no_gap_output.index("b") < gap_output.index("b")


def test_container_direction_defaults_to_vertical_when_unset() -> None:
    class G(BaseGrid, direction="vertical"):
        items: list = Field(default_factory=list)

    grid = G()
    grid.items = ["a", "b"]
    output = _render(grid)
    assert "a" in output
    assert "b" in output
