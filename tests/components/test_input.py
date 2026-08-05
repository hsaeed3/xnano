"""Tests for Input component."""

from __future__ import annotations

from typing import Any, cast

import pytest

from xnano.area import Area
from xnano.components.component import ComponentRenderContext
from xnano.components.input import Input
from xnano.components.text import Text
from xnano.core import Runtime
from xnano.core.content import TextBlock


def test_input_forces_input_true() -> None:
    field = Input(placeholder="Name")
    assert field.input is True
    assert field.focusable is True
    assert field.multiline is False
    assert field.placeholder == "Name"
    assert tuple(field.submit_keys) == ("enter",)


def test_input_is_text_subclass() -> None:
    field = Input("hi")
    assert isinstance(field, Text)
    assert field.value == "hi"


def test_input_accepts_mask_and_max_length() -> None:
    field = Input(mask="*", max_length=8, read_only=False)
    field.value = "password123"
    assert field.value == "password"
    display, _, _ = field._input_display_content()
    assert display == "********"


def test_multiline_input_uses_editor() -> None:
    field = Input(multiline=True, rows=6)
    assert field.input is True
    assert field.multiline is True
    assert field._editor is not None
    ctx = ComponentRenderContext(area=Area(x=0, y=0, width=40, height=6))
    content = field.compose(ctx)
    assert isinstance(content, TextBlock)
    assert field.rows == 6


def test_submit_keys_not_consumed() -> None:
    field = Input("x")

    class _K:
        kind = "press"
        character = None

        def matches(self, *bindings: str) -> bool:
            return "enter" in bindings

    assert field.handle_keyboard(cast(Any, _K())) is False
    assert field.value == "x"


@pytest.mark.parametrize(
    ("content", "width", "minimum", "maximum", "expected"),
    (
        ("", 10, 2, None, 2),
        ("abcdefghij", 4, 1, None, 3),
        ("a\nb\nc", 20, 1, 2, 2),
        ("abc", 0, 1, None, 1),
    ),
)
def test_auto_height_tracks_wrapping_with_bounds(
    content: str,
    width: int,
    minimum: int,
    maximum: int | None,
    expected: int,
) -> None:
    field = Input(
        content,
        auto_height=True,
        min_rows=minimum,
        max_rows=maximum,
    )
    size = field.get_size(
        ComponentRenderContext(area=Area(x=0, y=0, width=width, height=10))
    )
    assert size.height == expected


def test_fixed_input_size_uses_rows_and_natural_width() -> None:
    explicit = Input("one\ntwo", multiline=True, rows=5)
    size = explicit.get_size(
        ComponentRenderContext(area=Area(x=0, y=0, width=0, height=8))
    )
    assert size == type(size)(width=3, height=5)

    unwrapped = Input("one two", auto_height=True, wrap=False, min_rows=1)
    size = unwrapped.get_size(
        ComponentRenderContext(area=Area(x=0, y=0, width=2, height=8))
    )
    assert size.height == 1


def test_offscreen_render_smoke() -> None:
    runtime = Runtime.offscreen(40, 10)
    try:
        frame = runtime.render(Input("typed", placeholder="Name"))
        assert "typed" in frame.text
    finally:
        runtime.close()
