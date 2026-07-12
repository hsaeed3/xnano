"""Buffer and BufferMutView tests."""

from __future__ import annotations

from xnano_core.rust.engine import (
    CoreRenderContent,
    CoreRenderNode,
    CoreSession,
)
from xnano_core.rust.native import (
    Buffer,
    BufferCell,
    Paragraph,
    Rect,
    Style,
    render_widget,
)


def test_buffer_empty_and_filled() -> None:
    area = Rect(0, 0, 5, 3)
    empty = Buffer.empty(area)
    assert empty.area.width == 5
    filled = Buffer.filled(area, BufferCell.new("x"))
    assert filled.cell_symbol(0, 0) == "x"


def test_render_widget_into_buffer() -> None:
    area = Rect(0, 0, 20, 5)
    buffer = Buffer.empty(area)
    widget = Paragraph.new("buffered")
    render_widget(widget, area, buffer)
    assert any("buffered" in line for line in buffer.to_string_lines())


def test_buffer_mut_view_via_drawable(offscreen_session: CoreSession) -> None:
    seen: dict[str, object] = {}

    def draw(buffer: Buffer, rect: Rect) -> None:
        seen["area"] = (rect.width, rect.height)
        buffer.set_string(0, 0, "!", Style.default())

    offscreen_session.render(
        CoreRenderNode.leaf(CoreRenderContent.drawable(draw))
    )
    assert seen["area"] == (40, 12)
    lines = offscreen_session.buffer_snapshot().to_string_lines()
    assert lines[0].startswith("!")
