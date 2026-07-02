import pytest
from xnano.tailwind import tailwind
from xnano.color import Color


def test_tailwind_colors():
    red_500 = tailwind("red", 500)
    assert isinstance(red_500, Color)

    slate_900 = tailwind("slate", 900)
    assert isinstance(slate_900, Color)

    with pytest.raises(Exception):
        # Invalid color name or shade should raise an exception from Rust
        tailwind("invalid-color", 500)


def test_parse_tailwind():
    from xnano.tailwind import parse_tailwind

    res = parse_tailwind(
        "bg-blue-900 text-yellow-300 font-bold w-40 h-5 p-2 border rounded"
    )
    assert "style" in res
    assert res["width"] == 40
    assert res["height"] == 5
    assert res["borders"] == "all"
    assert res["border_type"] == "rounded"
    assert res["padding"] == 2


def test_widget_tailwind_integration():
    from xnano.widgets import Paragraph, Block

    # Check that Paragraph parses class_name and constructs a Block automatically
    p = Paragraph(
        "hello",
        class_name="w-50 h-3 border rounded p-1 text-white bg-blue-900",
    )
    assert p.width == 50
    assert p.height == 3

    # Check Block integration
    b = Block(class_name="w-30 h-10 border rounded")
    assert b.width == 30
    assert b.height == 10
