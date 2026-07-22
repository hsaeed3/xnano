"""Tests for Text(markdown=True) and Text(language=...)."""

from __future__ import annotations

import pytest

from xnano._markup import highlight_lines, markdown_lines
from xnano._types import Area
from xnano.components.abstract import ComponentRenderContext
from xnano.components.text import Text
from xnano.core.content import TextBlock


def _ctx() -> ComponentRenderContext:
    return ComponentRenderContext(area=Area(x=0, y=0, width=60, height=20))


def _plain(line: tuple) -> str:
    return "".join(run.text for run in line)


# ---------------------------------------------------------------------------
# highlight_lines
# ---------------------------------------------------------------------------


def test_python_keywords_are_colored() -> None:
    lines = highlight_lines("def greet():\n    return 1", "python")
    assert _plain(lines[0]) == "def greet():"
    keyword_run = lines[0][0]
    assert keyword_run.text == "def"
    assert keyword_run.color is not None


def test_unknown_language_falls_back_to_plain() -> None:
    lines = highlight_lines("hello world", "not-a-language")
    assert _plain(lines[0]) == "hello world"
    assert lines[0][0].color is None


def test_line_count_matches_source() -> None:
    source = "a = 1\nb = 2\nc = 3"
    assert len(highlight_lines(source, "python")) == 3


# ---------------------------------------------------------------------------
# markdown_lines
# ---------------------------------------------------------------------------


def test_heading_is_bold_and_accented() -> None:
    lines = markdown_lines("# Title")
    heading = lines[0]
    assert _plain(heading) == "# Title"
    body_run = heading[-1]
    assert "bold" in body_run.modifiers
    assert body_run.color is not None


def test_emphasis_and_strong() -> None:
    lines = markdown_lines("plain *soft* **hard**")
    runs = lines[0]
    styles = {run.text: run.modifiers for run in runs}
    assert styles["soft"] == ("italic",)
    assert styles["hard"] == ("bold",)


def test_inline_code_is_reversed() -> None:
    (line, *_rest) = markdown_lines("run `pytest` now")
    code_run = next(run for run in line if run.text == "pytest")
    assert "reversed" in code_run.modifiers


def test_list_items_get_bullets() -> None:
    lines = markdown_lines("- one\n- two")
    assert _plain(lines[0]).startswith("• ")
    assert _plain(lines[1]).startswith("• ")


def test_blockquote_is_dim() -> None:
    lines = markdown_lines("> quoted")
    assert _plain(lines[0]) == "> quoted"
    assert all("dim" in run.modifiers for run in lines[0])


def test_fenced_python_block_is_highlighted() -> None:
    lines = markdown_lines("```python\ndef f():\n    pass\n```")
    code_line = next(line for line in lines if _plain(line).startswith("def"))
    assert code_line[0].color is not None


# ---------------------------------------------------------------------------
# Text integration
# ---------------------------------------------------------------------------


def test_text_markdown_composes_text_block() -> None:
    text = Text("# Hi\n\nbody", markdown=True)
    content = text.compose(_ctx())
    assert isinstance(content, TextBlock)
    assert _plain(content.lines[0]) == "# Hi"


def test_text_language_composes_text_block() -> None:
    text = Text("x = 1", language="python")
    content = text.compose(_ctx())
    assert isinstance(content, TextBlock)
    assert _plain(content.lines[0]) == "x = 1"


def test_text_markdown_web_spans() -> None:
    from xnano.webui.nodes import WebParagraphNode

    node = Text("**bold**", markdown=True).get_web_node(_ctx())
    assert isinstance(node, WebParagraphNode)
    assert node.lines[0][0].modifiers == ("bold",)


def test_display_modes_are_mutually_exclusive() -> None:
    with pytest.raises(ValueError):
        Text("x", markdown=True, language="python")
    with pytest.raises(ValueError):
        Text("x", markdown=True, ansi=True)
    with pytest.raises(ValueError):
        Text("x", language="python", input=True)
