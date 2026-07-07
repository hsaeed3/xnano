"""Tests for xnano.beta.frame — Frame."""

from __future__ import annotations

import pytest

from xnano.beta.frame import Frame


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
        f.border = "rounded"  # type: ignore[misc]


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
