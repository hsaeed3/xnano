"""Shared fixtures for xnano-core tests."""

from __future__ import annotations

import sys

import pytest

from xnano_core.rust.native import (
    Block,
    BufferMutView,
    Constraint,
    Paragraph,
    Rect,
    Style,
)
from xnano_core.rust.engine import CoreRenderContent, CoreRenderNode, CoreSession


def draw_glyph_content(symbol: str) -> CoreRenderContent:
    """Build drawable content that paints a single glyph at the cell origin."""

    def draw(buffer: BufferMutView, rect: Rect) -> None:
        buffer.set_string(0, 0, symbol, Style.default())

    return CoreRenderContent.drawable(draw)


def glyph_at(session: CoreSession, x: int, y: int) -> str:
    """Return the symbol at a buffer coordinate after render."""
    cell = session.buffer_snapshot().cell(x, y)
    return cell.symbol if cell else " "


def has_tty() -> bool:
    """Return True when stdin is attached to a real terminal."""
    return sys.stdin.isatty()


requires_tty = pytest.mark.skipif(
    not has_tty(),
    reason="requires an interactive terminal (stdin is not a TTY)",
)

# crossterm event polling fails without a real TTY backend.
requires_input = requires_tty


@pytest.fixture
def offscreen_session() -> CoreSession:
    """Offscreen session sized for typical widget tests."""
    return CoreSession.offscreen(40, 12)


@pytest.fixture
def sample_paragraph() -> Paragraph:
    """Paragraph with a bordered block."""
    return Paragraph.new("hello, xnano-core").block(
        Block.bordered().title("demo")
    )


@pytest.fixture
def sample_leaf(sample_paragraph: Paragraph) -> CoreRenderNode:
    """Single leaf node wrapping a sample paragraph."""
    return CoreRenderNode.leaf(CoreRenderContent.widget(sample_paragraph))


@pytest.fixture
def column_tree(sample_paragraph: Paragraph) -> CoreRenderNode:
    """Two-row column layout used in several render tests."""
    return CoreRenderNode.column(
        constraints=[Constraint.length(3), Constraint.min(0)],
        children=[
            CoreRenderNode.leaf(CoreRenderContent.widget(sample_paragraph)),
            CoreRenderNode.leaf(CoreRenderContent.empty()),
        ],
    )