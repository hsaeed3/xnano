"""Tests for xnano._types — Frame."""

from __future__ import annotations

import pytest

from xnano._types import Frame, frame_from_field
from xnano.fields import GridFieldInfo


def test_frame_default_is_empty() -> None:
    assert Frame().is_empty()


def test_frame_with_border_is_not_empty() -> None:
    assert not Frame(border="rounded").is_empty()


def test_frame_with_background_is_not_empty() -> None:
    assert not Frame(background="red").is_empty()


def test_frame_with_title_is_not_empty() -> None:
    assert not Frame(title="hello").is_empty()


def test_frame_with_padding_is_not_empty() -> None:
    assert not Frame(padding=1).is_empty()


def test_frame_with_border_color_is_not_empty() -> None:
    assert not Frame(border_color="blue").is_empty()


def test_frame_with_border_sides_is_not_empty() -> None:
    assert not Frame(border_sides=["top", "bottom"]).is_empty()


def test_frame_with_title_position_is_not_empty() -> None:
    assert not Frame(title_position="bottom").is_empty()


def test_frame_is_frozen() -> None:
    f = Frame(border="plain")
    with pytest.raises((AttributeError, TypeError)):
        f.border = "rounded"  # ty: ignore[invalid-assignment]


def test_frame_from_field_background_only_is_none() -> None:
    assert frame_from_field(GridFieldInfo(background="violet")) is None


def test_frame_from_field_background_with_border() -> None:
    frame = frame_from_field(
        GridFieldInfo(background="slate-800", border="rounded")
    )
    assert frame is not None
    assert frame.background == "slate-800"
    assert frame.border == "rounded"


def test_frame_all_attrs_set() -> None:
    f = Frame(
        background="black",
        border="rounded",
        border_color="white",
        border_sides=["top"],
        title="box",
        title_position="top",
        padding=2,
    )
    assert not f.is_empty()
    assert f.border == "rounded"
    assert f.title == "box"
