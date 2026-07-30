"""Tests for ``Bar`` (sparkline replacement)."""

from __future__ import annotations

from typing import Any, cast

import pytest

from xnano.components.bar import (
    Bar,
    Sparkline,
    resolve_bar_glyphs,
)
from xnano.components.component import ComponentRenderContext
from xnano.core import Runtime
from xnano.core.content import CellCanvas
from xnano.core.content import Sparkline as SparklineContent
from xnano.types import Area


def _ctx(width: int = 20, height: int = 3) -> ComponentRenderContext[Any]:
    return ComponentRenderContext(
        area=Area(x=0, y=0, width=width, height=height)
    )


def test_resolve_blocks_preset() -> None:
    glyphs = resolve_bar_glyphs("blocks")
    assert len(glyphs) >= 2
    assert glyphs[0] == " "
    assert glyphs[-1] == "█"


def test_resolve_braille_and_ascii_presets() -> None:
    assert len(resolve_bar_glyphs("braille")) >= 2
    assert len(resolve_bar_glyphs("ascii")) >= 2


def test_resolve_string_ladder() -> None:
    assert resolve_bar_glyphs(" .:#") == (" ", ".", ":", "#")


def test_resolve_rejects_single_glyph() -> None:
    with pytest.raises(ValueError, match="at least two"):
        resolve_bar_glyphs("█")


def test_resolve_rejects_wide_glyph() -> None:
    with pytest.raises(ValueError, match="single terminal cell"):
        resolve_bar_glyphs((" ", "😀"))


def test_combining_grapheme_is_one_terminal_cell() -> None:
    assert resolve_bar_glyphs((" ", "e\u0301")) == (" ", "e\u0301")


@pytest.mark.parametrize("invalid", ("", "ab", "a😀"))
def test_invalid_graphemes_are_rejected(invalid: str) -> None:
    with pytest.raises(ValueError, match="single terminal cell"):
        resolve_bar_glyphs((" ", invalid))


def test_component_post_init_resolves_glyphs() -> None:
    bar = Bar(data=[1, 2, 3], glyphs="ascii")
    assert bar.resolved_glyphs == resolve_bar_glyphs("ascii")


def test_invalid_direction_and_absent_glyph_are_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported bar direction"):
        Bar(data=[1], direction=cast(Any, "sideways"))
    with pytest.raises(ValueError, match="absent_glyph"):
        Bar(data=[0], absent_glyph="😀")


def test_colors_length_must_match_data() -> None:
    with pytest.raises(ValueError, match="one entry per data"):
        Bar(data=[1, 2], colors=("red",))


def test_default_blocks_compose_sparkline_content() -> None:
    bar = Bar(data=[1, 3, 2], foreground="cyan")
    content = bar.compose(_ctx())
    assert isinstance(content, SparklineContent)
    assert list(content.data) == [1, 3, 2]
    assert content.color == "cyan"


def test_per_bar_colors() -> None:
    bar = Bar(data=[1, 2], colors=("red", "blue"))
    content = bar.compose(_ctx())
    assert isinstance(content, SparklineContent)
    bars = content.bars
    assert bars is not None
    assert [item.color for item in bars] == ["red", "blue"]


def test_custom_glyphs_compose_cell_canvas() -> None:
    bar = Bar(data=[0, 5, 10], glyphs=" .:#", max_value=10)
    content = bar.compose(_ctx())
    assert isinstance(content, CellCanvas)
    assert content.height == 1
    text = "".join(span.text for span in content.rows[0])
    assert len(text) == 3
    assert text[0] in " ."
    assert text[-1] == "#"


def test_direction_down_inverts_samples() -> None:
    up = Bar(data=[0, 10], max_value=10, glyphs=" .:#")
    down = Bar(data=[0, 10], max_value=10, glyphs=" .:#", direction="down")
    up_text = "".join(
        span.text
        for span in up.compose(_ctx()).rows[0]  # type: ignore[union-attr]
    )
    down_text = "".join(
        span.text
        for span in down.compose(_ctx()).rows[0]  # type: ignore[union-attr]
    )
    assert up_text != down_text


def test_custom_distribution_handles_absent_colors_and_empty_data() -> None:
    bar = Bar(
        data=[0, 5],
        glyphs=(" ", "."),
        colors=("red", "green"),
        absent_color="gray",
        absent_glyph="-",
        max_value=5,
    )
    content = bar.compose(_ctx())
    assert isinstance(content, CellCanvas)
    assert [span.text for span in content.rows[0]] == ["-", "."]
    assert [span.color for span in content.rows[0]] == ["gray", "green"]

    empty = Bar(data=[], glyphs=(" ", ".")).compose(_ctx(width=7))
    assert isinstance(empty, CellCanvas)
    assert empty.width == 7
    assert empty.rows[0][0].text == " "


def test_downward_nonpositive_scale_stays_absent() -> None:
    bar = Bar(data=(-3, 0), direction="down", glyphs=(" ", "#"))
    content = bar.compose(_ctx())
    assert isinstance(content, CellCanvas)
    assert [span.text for span in content.rows[0]] == [" ", " "]


def test_fit_content_defaults_false() -> None:
    assert Bar(data=[1]).fit_content is False


def test_deprecated_sparkline_alias() -> None:
    assert Sparkline is Bar


def test_runtime_offscreen_render_smoke() -> None:
    runtime = Runtime.offscreen(30, 5)
    try:
        frame = runtime.render(Bar(data=[1, 4, 2, 8, 3], foreground="green"))
        assert isinstance(frame.text, str)
        assert len(frame.text) > 0
    finally:
        runtime.close()


def test_empty_data_is_safe() -> None:
    runtime = Runtime.offscreen(20, 3)
    try:
        frame = runtime.render(Bar(data=[]))
        assert isinstance(frame.text, str)
    finally:
        runtime.close()
