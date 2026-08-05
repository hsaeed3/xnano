"""tests.test_alignment

---

Covers ``horizontal_align``/``vertical_align`` on fields and the shared
`xnano.area.align_area` helper they route through, plus the deprecated
``align`` alias.
"""

from __future__ import annotations

import warnings

import pytest

from xnano.area import Alignment, Area, VerticalAlignment, align_area
from xnano.components.text import Text
from xnano.fields import Field
from xnano.grids import BaseGrid
from xnano.terminal import Terminal


def _row_of(text: str, needle: str) -> int:
    """Return the 0-indexed row containing ``needle``."""
    for index, line in enumerate(text.splitlines()):
        if needle in line:
            return index
    raise AssertionError(f"{needle!r} not found in frame:\n{text}")


def _column_of(text: str, needle: str) -> int:
    for line in text.splitlines():
        if needle in line:
            return line.index(needle)
    raise AssertionError(f"{needle!r} not found in frame:\n{text}")


def test_align_area_places_box_on_both_axes() -> None:
    outer = Area(x=0, y=0, width=10, height=9)
    assert align_area(outer, 4, 3) == Area(x=0, y=0, width=4, height=3)
    assert align_area(
        outer, 4, 3, horizontal="center", vertical="middle"
    ) == Area(x=3, y=3, width=4, height=3)
    assert align_area(
        outer, 4, 3, horizontal="right", vertical="bottom"
    ) == Area(x=6, y=6, width=4, height=3)


def test_align_area_clamps_to_the_outer_area() -> None:
    outer = Area(x=2, y=1, width=5, height=4)
    assert align_area(
        outer, 99, 99, horizontal="right", vertical="bottom"
    ) == (Area(x=2, y=1, width=5, height=4))


@pytest.mark.parametrize(
    ("vertical_align", "expected_row"),
    (("top", 0), ("middle", 5), ("bottom", 11)),
)
def test_vertical_align_moves_content_down_the_slot(
    vertical_align: VerticalAlignment, expected_row: int
) -> None:
    class App(BaseGrid):
        body: str = Field(
            default="MARK",
            vertical_align=vertical_align,
        )

    terminal = Terminal.offscreen(cols=20, rows=12)
    try:
        terminal.attach_grid(App())
        frame = terminal.render()
        assert _row_of(frame.text, "MARK") == expected_row
    finally:
        terminal.close()


@pytest.mark.parametrize(
    ("horizontal_align", "expected_column"),
    (("left", 0), ("center", 8), ("right", 16)),
)
def test_horizontal_align_moves_content_across_the_slot(
    horizontal_align: Alignment, expected_column: int
) -> None:
    class App(BaseGrid):
        body: str = Field(
            default="MARK",
            horizontal_align=horizontal_align,
        )

    terminal = Terminal.offscreen(cols=20, rows=4)
    try:
        terminal.attach_grid(App())
        frame = terminal.render()
        assert _column_of(frame.text, "MARK") == expected_column
    finally:
        terminal.close()


def test_both_axes_compose_independently() -> None:
    class App(BaseGrid):
        body: str = Field(
            default="MARK",
            horizontal_align="right",
            vertical_align="bottom",
        )

    terminal = Terminal.offscreen(cols=20, rows=8)
    try:
        terminal.attach_grid(App())
        frame = terminal.render()
        assert _row_of(frame.text, "MARK") == 7
        assert _column_of(frame.text, "MARK") == 16
    finally:
        terminal.close()


def test_vertical_align_never_clips_multiline_content() -> None:
    """Alignment only moves the origin; it must not shrink the slot.

    A value taller than its measured height would otherwise lose rows.
    """

    class App(BaseGrid):
        body: str = Field(default="A\nB\nC", vertical_align="middle")

    terminal = Terminal.offscreen(cols=12, rows=9)
    try:
        terminal.attach_grid(App())
        frame = terminal.render()
        for line in ("A", "B", "C"):
            assert line in frame.text
        assert _row_of(frame.text, "A") == 3
    finally:
        terminal.close()


def test_component_values_honor_field_vertical_align() -> None:
    """A component's height is measured from its text, not ``get_size``.

    ``Text.get_size`` reports 0 for the zero-height probe area, which
    would silently skip alignment for every component field.
    """

    class App(BaseGrid):
        header: str = Field(default="HEAD", height=1)
        body: Text = Field(
            default_factory=lambda: Text("MARK"),
            vertical_align="middle",
        )

    terminal = Terminal.offscreen(cols=20, rows=9)
    try:
        terminal.attach_grid(App())
        frame = terminal.render()
        # header owns row 0; the 8 remaining rows centre a 1-line body.
        assert _row_of(frame.text, "MARK") == 4
    finally:
        terminal.close()


def test_align_alias_warns_and_sets_horizontal_align() -> None:
    with pytest.warns(DeprecationWarning):
        field = Field(default="", align="center")
    assert getattr(field, "horizontal_align") == "center"

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        canonical = Field(default="", horizontal_align="right")
    assert getattr(canonical, "horizontal_align") == "right"


def test_horizontal_align_wins_over_deprecated_align() -> None:
    with pytest.warns(DeprecationWarning):
        field = Field(default="", horizontal_align="right", align="center")
    assert getattr(field, "horizontal_align") == "right"


def test_text_component_align_alias_round_trips() -> None:
    with pytest.warns(DeprecationWarning):
        text = Text("x", align="center")  # ty: ignore[unknown-argument]
    assert text.horizontal_align == "center"
    assert text.align == "center"  # ty: ignore[unresolved-attribute]


def test_grid_set_field_align_alias() -> None:
    class App(BaseGrid):
        body: str = Field(default="hi")

    grid = App()
    with pytest.warns(DeprecationWarning):
        grid.grid_set_field("body", align="center")
    overrides = grid._grid_field_overrides  # ty: ignore[unresolved-attribute]
    assert overrides["body"].horizontal_align == "center"


def test_wrapped_text_measures_its_real_row_count() -> None:
    """Wrapping makes a one-line string taller than ``splitlines()`` says."""
    from xnano.core.controller import wrapped_line_count

    assert wrapped_line_count("short", 20) == 1
    assert wrapped_line_count("a\nb\nc", 20) == 3
    assert wrapped_line_count("word " * 12, 20) > 1
    assert wrapped_line_count("x" * 45, 10) == 5
    assert wrapped_line_count("anything", 0) == 1


def test_vertical_align_accounts_for_wrapping() -> None:
    text = "lorem ipsum dolor sit amet consectetur adipiscing elit sed do"

    class App(BaseGrid):
        body: str = Field(default=text, vertical_align="bottom")

    terminal = Terminal.offscreen(cols=20, rows=12)
    try:
        terminal.attach_grid(App())
        frame = terminal.render()
        # Bottom-aligned wrapped text must still show its last word.
        assert "do" in frame.text
        assert _row_of(frame.text, "lorem") > 0
    finally:
        terminal.close()
