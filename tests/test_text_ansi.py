"""Tests for Text(ansi=True) ANSI escape ingestion."""

from __future__ import annotations

import pytest

from xnano._markup import parse_ansi_lines, strip_ansi_escapes
from xnano._types import Area
from xnano.components.abstract import ComponentRenderContext
from xnano.components.text import Text
from xnano.core.content import TextBlock


def _ctx() -> ComponentRenderContext:
    return ComponentRenderContext(area=Area(x=0, y=0, width=40, height=4))


# ---------------------------------------------------------------------------
# parse_ansi_lines
# ---------------------------------------------------------------------------


def test_basic_color_run() -> None:
    lines = parse_ansi_lines("\x1b[31mred\x1b[0m plain")
    assert len(lines) == 1
    runs = lines[0]
    assert runs[0].text == "red"
    assert runs[0].color == "#cd0000"
    assert runs[1].text == " plain"
    assert runs[1].color is None


def test_bright_and_background_colors() -> None:
    (runs,) = parse_ansi_lines("\x1b[91;44mwarn\x1b[0m")
    assert runs[0].color == "#ff0000"
    assert runs[0].background == "#0000ee"


def test_256_color_mapping() -> None:
    (runs,) = parse_ansi_lines("\x1b[38;5;196mhot\x1b[0m")
    assert runs[0].color == "#ff0000"
    (runs,) = parse_ansi_lines("\x1b[38;5;244mgray\x1b[0m")
    assert runs[0].color == "#808080"


def test_truecolor_mapping() -> None:
    (runs,) = parse_ansi_lines("\x1b[38;2;1;2;3mrgb\x1b[0m")
    assert runs[0].color == "#010203"


def test_modifiers_set_and_clear() -> None:
    (runs,) = parse_ansi_lines("\x1b[1;4mstrong\x1b[22m rest\x1b[0m")
    assert runs[0].modifiers == ("bold", "underline")
    assert runs[1].modifiers == ("underline",)


def test_style_carries_across_lines() -> None:
    lines = parse_ansi_lines("\x1b[32mone\ntwo\x1b[0m")
    assert lines[0][0].color == "#00cd00"
    assert lines[1][0].color == "#00cd00"


def test_non_sgr_escapes_are_stripped() -> None:
    (runs,) = parse_ansi_lines("a\x1b[2Kb")
    assert "".join(run.text for run in runs) == "ab"


def test_strip_ansi_escapes() -> None:
    assert strip_ansi_escapes("\x1b[31mred\x1b[0m \x1b[2K!") == "red !"


# ---------------------------------------------------------------------------
# Text integration
# ---------------------------------------------------------------------------


def test_text_ansi_composes_styled_text_block() -> None:
    text = Text("\x1b[31mred\x1b[0m plain", ansi=True, wrap=False)
    content = text.compose(_ctx())
    assert isinstance(content, TextBlock)
    assert content.lines[0][0].color == "#cd0000"
    assert content.lines[0][1].text == " plain"


def test_text_ansi_web_spans() -> None:
    from xnano.web.nodes import WebParagraphNode

    text = Text("\x1b[31mred\x1b[0m", ansi=True)
    node = text.get_web_node(_ctx())
    assert isinstance(node, WebParagraphNode)
    assert node.lines[0][0].color == "#cd0000"


def test_ansi_and_input_are_mutually_exclusive() -> None:
    with pytest.raises(ValueError):
        Text("x", ansi=True, input=True)
