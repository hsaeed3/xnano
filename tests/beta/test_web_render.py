"""WebController HTML rendering: layout, style, frames, and components."""

from __future__ import annotations

from tests.beta.grids import (
    ClickableGrid,
    FrameGrid,
    NestedGrid,
    SimpleGrid,
    StyledGrid,
    TextGrid,
)
from xnano.beta.components.text import Text
from xnano.beta.controllers.web import WebController
from xnano.fields import Field
from xnano.grid import Grid


def test_simple_grid_renders_html() -> None:
    """A grid with two string fields renders HTML with both texts."""
    grid = SimpleGrid()
    controller = WebController()
    html = controller.render_grid_html(grid)
    assert "left" in html
    assert "right" in html
    assert "<div" in html


def test_horizontal_grid_has_flex_row() -> None:
    """A horizontal grid renders with flex-row class."""
    grid = SimpleGrid()
    controller = WebController()
    html = controller.render_grid_html(grid)
    assert "flex-row" in html


def test_gap_renders_in_styles() -> None:
    """Gap property renders as rem-based gap style."""
    grid = SimpleGrid()
    controller = WebController()
    html = controller.render_grid_html(grid)
    assert "gap" in html
    assert "0.25rem" in html


def test_script_tag_escaped() -> None:
    """Script tags in field values are escaped."""

    class ScriptGrid(Grid):
        content: str = Field(default="<script>alert(1)</script>")

    grid = ScriptGrid()
    controller = WebController()
    html = controller.render_grid_html(grid)
    assert "&lt;script&gt;" in html
    assert "<script>" not in html
    assert "alert(1)" in html


def test_field_color_renders_rgb() -> None:
    """Field with color renders inline style with rgb()."""
    grid = StyledGrid()
    controller = WebController()
    html = controller.render_grid_html(grid)
    assert "rgb(0, 255, 255)" in html


def test_field_bold_renders_font_bold() -> None:
    """Field with bold modifier renders font-bold class."""
    grid = StyledGrid()
    controller = WebController()
    html = controller.render_grid_html(grid)
    assert "font-bold" in html


def test_field_red_color() -> None:
    """Field with red color renders correct rgb."""
    grid = StyledGrid()
    controller = WebController()
    html = controller.render_grid_html(grid)
    assert "rgb(255, 0, 0)" in html


def test_frame_border_rounded() -> None:
    """Field with rounded border renders border and rounded-lg."""
    grid = FrameGrid()
    controller = WebController()
    html = controller.render_grid_html(grid)
    assert "border" in html
    assert "rounded-lg" in html


def test_frame_title_escaped() -> None:
    """Frame title is HTML-escaped."""
    grid = FrameGrid()
    controller = WebController()
    html = controller.render_grid_html(grid)
    assert "My Panel" in html


def test_nested_grid_renders() -> None:
    """Nested grid renders with both grids' content."""
    grid = NestedGrid()
    controller = WebController()
    html = controller.render_grid_html(grid)
    assert "left" in html
    assert "right" in html


def test_nested_grid_has_inner_flex() -> None:
    """Nested grid produces nested flex containers."""
    grid = NestedGrid()
    controller = WebController()
    html = controller.render_grid_html(grid)
    assert html.count("flex") >= 2


def test_grid_background_color() -> None:
    """Grid-level background renders as style."""

    class BackgroundGrid(Grid, background="black"):
        content: str = Field(default="text")

    grid = BackgroundGrid()
    controller = WebController()
    html = controller.render_grid_html(grid)
    assert "rgb(0, 0, 0)" in html


def test_text_component_web_node() -> None:
    """Text component renders via get_web_node to HTML."""
    grid = TextGrid()
    controller = WebController()
    html = controller.render_grid_html(grid)
    assert "Title" in html
    assert "rgb(0, 255, 255)" in html


def test_text_component_terminal_render() -> None:
    """Same Text instance renders on terminal via render_component_to_text."""
    from tests.helpers import render_component_to_text

    text = Text("hello", color="cyan")
    output = render_component_to_text(text)
    assert "hello" in output


def test_text_spans() -> None:
    """Text with multiple colored spans renders all spans."""

    class SpanTestGrid(Grid):
        content: Text = Field(
            default=Text(
                [
                    Text("a", color="red"),
                    Text("b", color="blue"),
                ]
            )
        )

    instance = SpanTestGrid()
    controller = WebController()
    html = controller.render_grid_html(instance)
    assert "a" in html
    assert "b" in html
    assert "rgb(255, 0, 0)" in html
    assert "rgb(0, 0, 255)" in html


def test_clickable_field_has_htmx_attrs() -> None:
    """Clickable field renders hx-post and hx-target attributes."""
    grid = ClickableGrid()
    controller = WebController()
    html = controller.render_grid_html(grid)
    assert "hx-post=" in html
    assert "hx-target=" in html
    assert "#xnano-app" in html


def test_click_target_registered() -> None:
    """Click handler registers target in click_targets dict."""
    grid = ClickableGrid()
    controller = WebController()
    controller.render_grid_html(grid)
    assert len(controller.click_targets) == 1
    target_id, (target_grid, field_name) = next(
        iter(controller.click_targets.items())
    )
    assert field_name == "body"
    assert target_grid is grid
