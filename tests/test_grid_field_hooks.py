"""Tests for grid field-bound mouse hooks."""

from __future__ import annotations

import types
from typing import cast

import pytest

from xnano.beta import Context, on_click, on_mouse, Field, Grid
from xnano.beta.grid import _resolve_grid_mouse_handler


class Panel(Grid):
    body: str = Field(default="hello")

    @on_click("body")
    def highlight_body(self, ctx: Context) -> None:
        self.body = "clicked"


class HeaderPanel(Grid):
    header: str = Field(default="title")

    @on_mouse(field="header", button="left", kind="press")
    def on_header_click(self, ctx: Context) -> None:
        self.header = "clicked"


def test_on_click_registers_field_handler_by_name() -> None:
    panel = Panel()
    handler = _resolve_grid_mouse_handler(panel, "body")
    assert handler is not None
    assert cast(types.FunctionType, handler).__name__ == "highlight_body"


def test_on_click_binds_at_class_level() -> None:
    assert (
        cast(types.FunctionType, Panel._grid_field_handlers["body"]).__name__
        == "highlight_body"
    )


def test_on_mouse_field_param_registers_handler() -> None:
    assert (
        cast(
            types.FunctionType,
            HeaderPanel._grid_field_handlers["header"],
        ).__name__
        == "on_header_click"
    )


def test_unknown_field_raises_at_class_creation() -> None:
    with pytest.raises(TypeError, match="not a layout field"):

        class Bad(Grid):  # noqa: N801
            @on_click("missing")
            def handler(self, ctx: Context) -> None:
                pass
