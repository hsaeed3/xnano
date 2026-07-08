"""Tests for unified per-axis ``Sizing`` on grid fields.

These build a grid frame against an offscreen session and assert the resolved
slot geometry, so no TTY is required.
"""

from __future__ import annotations

from xnano.beta import Field, Grid, Sizing, Terminal
from xnano.beta.types import Area


def _slot_areas(grid: Grid, width: int, height: int) -> dict[str, Area]:
    """Build ``grid`` into a ``width`` x ``height`` area and return slot areas."""
    terminal = Terminal.offscreen(cols=width, rows=height)
    terminal._track_frame_grid(grid)
    session = terminal.session
    session.begin_frame()
    grid._grid_build_frame(Area(x=0, y=0, width=width, height=height), session)
    session.commit_requests()
    return dict(grid._grid_last_slot_areas)


def test_vertical_height_cells() -> None:
    class App(Grid):
        header: str = Field(default="h", height=2)
        body: str = Field(default="b", height="1fr")

    areas = _slot_areas(App(), 20, 10)
    assert areas["header"].height == 2
    assert areas["body"].height == 8
    # Fields stack from the top.
    assert areas["header"].y == 0
    assert areas["body"].y == 2


def test_horizontal_width_percent() -> None:
    class Row(Grid, direction="horizontal"):
        left: str = Field(default="l", width="25%")
        right: str = Field(default="r", width="1fr")

    areas = _slot_areas(Row(), 80, 5)
    assert areas["left"].width == 20
    assert areas["right"].width == 60


def test_horizontal_width_ratio() -> None:
    class Row(Grid, direction="horizontal"):
        left: str = Field(default="l", width=Sizing.ratio(1, 4))
        right: str = Field(default="r", width="1fr")

    areas = _slot_areas(Row(), 80, 5)
    assert areas["left"].width == 20
    assert areas["right"].width == 60


def test_vertical_height_fit() -> None:
    class App(Grid):
        header: str = Field(default="one\ntwo", height="fit")
        body: str = Field(default="b", height="1fr")

    areas = _slot_areas(App(), 20, 10)
    # Two content lines → two rows.
    assert areas["header"].height == 2
    assert areas["body"].height == 8


def test_width_height_take_precedence_over_legacy_size() -> None:
    class App(Grid):
        # ``height`` should win over the legacy ``size`` knob.
        top: str = Field(default="t", height=3, size=0.9)
        rest: str = Field(default="r", height="1fr")

    areas = _slot_areas(App(), 20, 10)
    assert areas["top"].height == 3


# ---------------------------------------------------------------------------
# cross-axis sizing — the non-layout axis is also honored
# ---------------------------------------------------------------------------


def test_vertical_cross_axis_width_cells() -> None:
    class App(Grid):
        a: str = Field(default="x", width=10, height=2)

    area = _slot_areas(App(), 40, 6)["a"]
    # height is the layout axis; width constrains the cross axis.
    assert area.width == 10
    assert area.height == 2


def test_horizontal_cross_axis_height_cells() -> None:
    class Row(Grid, direction="horizontal"):
        a: str = Field(default="x", width="50%", height=3)
        b: str = Field(default="y", width="1fr")

    areas = _slot_areas(Row(), 40, 6)
    assert areas["a"].width == 20
    assert areas["a"].height == 3
    # A field without a cross sizing fills the cross axis.
    assert areas["b"].height == 6


def test_cross_axis_fit_measures_content() -> None:
    class App(Grid):
        a: str = Field(default="hello", width="fit")

    area = _slot_areas(App(), 40, 6)["a"]
    assert area.width == 5


def test_cross_axis_percent() -> None:
    class App(Grid):
        a: str = Field(default="x", width="25%")

    area = _slot_areas(App(), 40, 6)["a"]
    assert area.width == 10


def test_cross_axis_none_fills() -> None:
    class App(Grid):
        a: str = Field(default="x", height=2)

    area = _slot_areas(App(), 40, 6)["a"]
    # No width sizing → fills the cross axis.
    assert area.width == 40
