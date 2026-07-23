"""tests.beta.test_markdown"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest

from xnano.beta.events import Event, KeyboardEventData, MouseEventData
from xnano.beta.markdown import (
    MarkdownViewport,
    _create_markdown_document,
    is_markdown_path,
    load_markdown_source,
    render_markdown,
    run_markdown,
)
from xnano.beta.terminal import Terminal


def test_load_literal_markdown() -> None:
    text, base = load_markdown_source("# Hello\n\nworld")
    assert "Hello" in text
    assert base is None


def test_load_long_literal_markdown_is_not_probed_as_path() -> None:
    """A long literal document is not a filename; the path probe must not
    raise ``OSError`` (File name too long) and drop the content."""
    source = "# Doc\n\n" + "\n\n".join(f"paragraph {i}" for i in range(500))
    text, base = load_markdown_source(source)
    assert text == source
    assert base is None


def test_load_path_markdown(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "readme.md"
    path.write_text("# Title\n\nbody", encoding="utf-8")
    assert is_markdown_path(path)
    text, base = load_markdown_source(path)
    assert "Title" in text
    assert base == tmp_path


def test_run_markdown_offscreen(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "doc.md"
    path.write_text("# Doc\n\nhello markdown", encoding="utf-8")
    terminal = Terminal.offscreen(cols=40, rows=12)
    run_markdown(path, terminal=terminal)
    output = terminal.get_output()
    assert "hello markdown" in output or "Doc" in output


def test_render_markdown_returns_frame() -> None:
    terminal = Terminal.offscreen(cols=40, rows=12)
    try:
        frame = render_markdown("# Doc\n\nhello markdown", terminal=terminal)
        assert frame.contains("hello markdown") or frame.contains("Doc")
    finally:
        terminal.close()


def _tall_document(sections: int = 40) -> str:
    return "\n\n".join(
        f"# Heading {index}\n\nBody line for section {index}."
        for index in range(sections)
    )


def _viewer(
    text: str, *, cols: int = 50, rows: int = 10
) -> tuple[Any, Terminal]:
    document = _create_markdown_document(text)
    terminal = Terminal.offscreen(cols=cols, rows=rows)
    terminal.attach_grid(document)
    return document, terminal


def _press(terminal: Terminal, binding: str) -> None:
    terminal.runtime.dispatch(
        Event.from_data(KeyboardEventData.from_binding(binding))
    )


def test_pager_starts_at_top() -> None:
    document, terminal = _viewer(_tall_document())
    try:
        frame = terminal.render(document)
        assert frame.contains("Heading 0")
        assert not frame.contains("Heading 30")
        assert document.body.offset == 0
    finally:
        terminal.close()


def test_pager_page_down_reveals_later_content() -> None:
    document, terminal = _viewer(_tall_document())
    try:
        terminal.render(document)
        _press(terminal, "pagedown")
        frame = terminal.render(document)
        assert document.body.offset > 0
        assert not frame.contains("Heading 0")
    finally:
        terminal.close()


def test_pager_line_down_and_up_are_inverse() -> None:
    document, terminal = _viewer(_tall_document())
    try:
        terminal.render(document)
        _press(terminal, "down")
        _press(terminal, "down")
        assert document.body.offset == 2
        _press(terminal, "up")
        assert document.body.offset == 1
    finally:
        terminal.close()


def test_pager_end_shows_last_page_then_home_returns() -> None:
    document, terminal = _viewer(_tall_document())
    try:
        terminal.render(document)
        _press(terminal, "end")
        frame_end = terminal.render(document)
        assert document.body.scroll_percentage() == 100
        assert frame_end.contains("Heading 39")
        _press(terminal, "home")
        frame_home = terminal.render(document)
        assert document.body.offset == 0
        assert frame_home.contains("Heading 0")
    finally:
        terminal.close()


def test_pager_does_not_scroll_past_bounds() -> None:
    document, terminal = _viewer(_tall_document())
    try:
        terminal.render(document)
        for _ in range(200):
            _press(terminal, "down")
        assert document.body.offset == document.body.max_offset()
        for _ in range(400):
            _press(terminal, "up")
        assert document.body.offset == 0
    finally:
        terminal.close()


def test_pager_mouse_wheel_scrolls() -> None:
    document, terminal = _viewer(_tall_document())
    try:
        terminal.render(document)
        terminal.runtime.dispatch(
            Event.from_data(
                MouseEventData(kind="scroll_down", x=1, y=1, button="unknown")
            )
        )
        assert document.body.offset == 3
    finally:
        terminal.close()


def test_pager_quit_requests_exit() -> None:
    document, terminal = _viewer("# Hi\n\ntext")
    try:
        terminal.render(document)
        _press(terminal, "q")
        assert terminal.runtime._should_exit is True
    finally:
        terminal.close()


def test_pager_status_line_shows_percentage() -> None:
    document, terminal = _viewer(_tall_document(), cols=60)
    try:
        frame = terminal.render(document)
        assert "%" in frame.rows[-1]
    finally:
        terminal.close()


def test_code_block_has_gutter_and_keeps_inner_indent() -> None:
    text = "intro\n\n```python\ndef f():\n    return 1\n```\n\nafter"
    document, terminal = _viewer(text, cols=40, rows=12)
    try:
        frame = terminal.render(document)
        def_row = next(row for row in frame.rows if "def f" in row)
        return_row = next(row for row in frame.rows if "return 1" in row)
        # Every code line carries the gutter glyph...
        assert def_row.startswith("▎")
        assert return_row.startswith("▎")
        # ...and the code's own inner indentation survives.
        assert "    return 1" in return_row
    finally:
        terminal.close()


def test_missing_image_falls_back_to_placeholder() -> None:
    document, terminal = _viewer(
        "# Pic\n\n![a cat](does-not-exist.png)\n\nafter",
        rows=14,
    )
    try:
        frame = terminal.render(document)
        assert frame.contains("Pic")
        assert frame.contains("a cat")
        assert frame.contains("after")
        assert [block.kind for block in document.body._blocks()] == [
            "text",
            "text",
            "text",
        ]
    finally:
        terminal.close()


def test_remote_image_is_not_fetched() -> None:
    viewport = MarkdownViewport("![x](https://example.com/x.png)")
    assert viewport._resolve_image("https://example.com/x.png") is None


def test_real_image_renders_as_native_thumbnail(
    tmp_path: pathlib.Path,
) -> None:
    """Small images stay at native half-block size (never full-width upscale)."""
    pytest.importorskip("PIL")
    from PIL import Image as PillowImage

    PillowImage.new("RGB", (24, 24), (200, 40, 40)).save(tmp_path / "red.png")
    (tmp_path / "doc.md").write_text(
        "# Picture\n\n![red](red.png)\n\nafter image",
        encoding="utf-8",
    )
    document = _create_markdown_document(tmp_path / "doc.md")
    terminal = Terminal.offscreen(cols=40, rows=20)
    terminal.attach_grid(document)
    try:
        frame = terminal.render(document)
        ansi = terminal.get_output_as_ansi()
        kinds = [block.kind for block in document.body._blocks()]
        image_block = next(
            block for block in document.body._blocks() if block.kind == "image"
        )
        image = image_block.image
        assert "image" in kinds
        # 24×24 source → 24 cols × 12 body rows + caption + gap.
        assert image_block.rows == 14
        assert image._cached_canvas.width == 24
        assert image._cached_canvas.height == 12
        assert frame.contains("Picture")
        assert frame.contains("red")
        assert frame.contains("hover/i expand")
        # The rendered image contributes truecolor cells to the buffer.
        assert "38;2;" in ansi or "48;2;" in ansi
    finally:
        terminal.close()


def test_large_image_is_downscaled_to_thumbnail_budget(
    tmp_path: pathlib.Path,
) -> None:
    """Large sources are LANCZOS-downscaled into the thumb budget, not full width."""
    pytest.importorskip("PIL")
    from PIL import Image as PillowImage

    PillowImage.new("RGB", (800, 600), (40, 120, 200)).save(
        tmp_path / "wide.png"
    )
    (tmp_path / "doc.md").write_text(
        "![wide](wide.png)\n",
        encoding="utf-8",
    )
    document = _create_markdown_document(tmp_path / "doc.md")
    terminal = Terminal.offscreen(cols=100, rows=40)
    terminal.attach_grid(document)
    try:
        terminal.render(document)
        image_block = next(
            block for block in document.body._blocks() if block.kind == "image"
        )
        image = image_block.image
        # Collapsed thumb is capped well below terminal width / native size.
        assert image._cached_canvas.width <= document.body.thumb_max_cols
        assert image._cached_canvas.height <= document.body.thumb_max_rows
        assert image._cached_canvas.width < 100
    finally:
        terminal.close()


def test_image_expand_toggle_increases_clarity(
    tmp_path: pathlib.Path,
) -> None:
    """Pinning / ``i`` expands a large image toward native cell resolution."""
    pytest.importorskip("PIL")
    from PIL import Image as PillowImage

    PillowImage.new("RGB", (200, 120), (10, 200, 80)).save(
        tmp_path / "green.png"
    )
    (tmp_path / "doc.md").write_text(
        "![green](green.png)\n",
        encoding="utf-8",
    )
    document = _create_markdown_document(tmp_path / "doc.md")
    terminal = Terminal.offscreen(cols=80, rows=40)
    terminal.attach_grid(document)
    try:
        terminal.render(document)
        image_block = next(
            block for block in document.body._blocks() if block.kind == "image"
        )
        collapsed_width = image_block.image._cached_canvas.width
        collapsed_height = image_block.image._cached_canvas.height

        assert document.body.toggle_expand() is True
        terminal.render(document)
        expanded_width = image_block.image._cached_canvas.width
        expanded_height = image_block.image._cached_canvas.height

        assert expanded_width >= collapsed_width
        assert expanded_height >= collapsed_height
        # Expanded still never exceeds native half-block mapping (200×60).
        assert expanded_width <= 200
        assert expanded_height <= 60
        assert document.body.active_image_key() is not None

        # Toggle again collapses.
        assert document.body.toggle_expand() is True
        assert document.body.active_image_key() is None
    finally:
        terminal.close()


def test_image_hover_expands_and_clears(
    tmp_path: pathlib.Path,
) -> None:
    """Pointer hover expands a thumbnail; leaving clears hover expand."""
    pytest.importorskip("PIL")
    from PIL import Image as PillowImage

    PillowImage.new("RGB", (64, 64), (200, 200, 40)).save(
        tmp_path / "yellow.png"
    )
    (tmp_path / "doc.md").write_text(
        "intro\n\n![yellow](yellow.png)\n\nafter\n",
        encoding="utf-8",
    )
    document = _create_markdown_document(tmp_path / "doc.md")
    terminal = Terminal.offscreen(cols=60, rows=30)
    terminal.attach_grid(document)
    try:
        terminal.render(document)
        # Image follows the intro text block; hit near the top of the image.
        regions = document.body._image_hit_regions
        assert regions
        region = regions[0]
        y = max(0, region.start_row - document.body.offset)
        assert document.body.update_pointer(1, y) is True
        assert document.body.active_image_key() == region.key
        terminal.render(document)
        assert document.body._is_image_expanded(region.key)

        assert document.body.clear_pointer() is True
        assert document.body._hovered_image_key is None
    finally:
        terminal.close()
