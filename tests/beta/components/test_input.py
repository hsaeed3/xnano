"""Tests for beta Input component."""

from __future__ import annotations

from typing import Any, cast

from xnano.beta.components.component import ComponentRenderContext
from xnano.beta.components.input import Input
from xnano.beta.components.text import Text
from xnano.beta.core import Runtime
from xnano.beta.core.content import TextBlock
from xnano.beta.types import Area


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


def test_offscreen_render_smoke() -> None:
    runtime = Runtime.offscreen(40, 10)
    try:
        frame = runtime.render(Input("typed", placeholder="Name"))
        assert "typed" in frame.text
    finally:
        runtime.close()
