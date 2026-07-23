"""Tests for beta ``Bar`` (sparkline replacement)."""

from __future__ import annotations

from typing import Any

import pytest

from xnano.beta.components.bar import (
    Bar,
    Sparkline,
    resolve_bar_glyphs,
)
from xnano.beta.components.component import ComponentRenderContext
from xnano.beta.core import Runtime
from xnano.beta.core.content import CellCanvas
from xnano.beta.core.content import Sparkline as SparklineContent
from xnano.beta.types import Area


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


def test_component_post_init_resolves_glyphs() -> None:
    bar = Bar(data=[1, 2, 3], glyphs="ascii")
    assert bar.resolved_glyphs == resolve_bar_glyphs("ascii")


def test_colors_length_must_match_data() -> None:
    with pytest.raises(ValueError, match="one entry per data"):
        Bar(data=[1, 2], colors=("red",))


def test_default_blocks_compose_sparkline_content() -> None:
    bar = Bar(data=[1, 3, 2], color="cyan")
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


def test_fit_content_defaults_false() -> None:
    assert Bar(data=[1]).fit_content is False


def test_deprecated_sparkline_alias() -> None:
    assert Sparkline is Bar


def test_runtime_offscreen_render_smoke() -> None:
    runtime = Runtime.offscreen(30, 5)
    try:
        frame = runtime.render(Bar(data=[1, 4, 2, 8, 3], color="green"))
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
