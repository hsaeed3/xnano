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
