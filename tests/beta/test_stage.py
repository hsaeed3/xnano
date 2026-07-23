"""tests.beta.test_stage"""

from __future__ import annotations

from xnano.beta.core.stage import LayoutMap, Stage
from xnano.beta.types import Area


def test_stage_registers_and_returns_areas() -> None:
    stage = Stage()
    area = Area(x=1, y=2, width=3, height=4)
    stage.areas["body"] = area
    assert stage.get_area("body") is area
    assert stage.get_area("missing") is None


def test_stage_queues_paint_commands() -> None:
    stage = Stage()
    stage.paint_cell(2, 1, "!", color="yellow", modifiers=("bold",))
    stage.paint_cell(0, 0, "x")
    assert len(stage._commands) == 2
    first = stage._commands[0]
    assert first["x"] == 2
    assert first["y"] == 1
    assert first["value"] == "!"
    assert first["color"] == "yellow"
    assert first["modifiers"] == ("bold",)


def test_layout_map_alias() -> None:
    layout: LayoutMap = {"a": Area(x=0, y=0, width=1, height=1)}
    assert isinstance(layout["a"], Area)
