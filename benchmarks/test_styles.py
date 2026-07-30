"""benchmarks.test_styles

---

Style lowering: the tailwind class grammar every ``class_name=`` is parsed
with, the four accepted color spellings, and the bridge that turns a python
color into the native ``xnano-core`` representation.
"""

from __future__ import annotations

from xnano.colors import Color, get_native_color
from xnano.tailwind import resolve_tailwind_classes

_CLASS_STRINGS = (
    "flex flex-col gap-2 p-4 px-2 mt-1 mb-3 w-full h-24 border border-t "
    "rounded-lg text-slate-200 bg-slate-900 border-blue-500 font-bold "
    "italic underline opacity-50 text-center cursor-pointer shadow-lg "
    "hover:bg-blue-600 transition-all duration-150",
    "flex-row gap-1 p-2 w-1/2 rounded text-red-500 bg-black",
    "text-center font-bold underline m-2 border-b border-emerald-400",
) * 10

_COLOR_INPUTS = (
    "#ff0000",
    "#00ff88",
    "red",
    "blue",
    "aliceblue",
    "slate-400",
    "violet-900",
    "emerald-500",
    (12, 34, 56),
    (200, 100, 50, 128),
) * 20

_NATIVE_INPUTS = (
    "red",
    "#00ff88",
    "slate-400",
    "blue",
    "#123456",
    "violet-900",
    (10, 20, 30),
)


def _resolve_classes() -> list[object]:
    """Lower a batch of tailwind class strings into styles."""
    return [resolve_tailwind_classes(value) for value in _CLASS_STRINGS]


def _parse_colors() -> list[Color]:
    """Parse hex, css-name, tailwind and rgb/rgba spellings."""
    return [Color.parse(value) for value in _COLOR_INPUTS]


def _native_colors() -> list[object]:
    """Cross the python to native color boundary from a cold cache."""
    get_native_color.cache_clear()
    return [get_native_color(value) for value in _NATIVE_INPUTS]


def test_resolve_tailwind_classes(benchmark) -> None:
    """Spacing math, sizing parsing and dedup for 30 class strings."""
    styles = benchmark(_resolve_classes)
    assert len(styles) == len(_CLASS_STRINGS)
    assert styles[0].color == "slate-200"
    assert styles[0].background == "slate-900"


def test_color_parse(benchmark) -> None:
    """Every accepted color spelling, 200 parses per round."""
    colors = benchmark(_parse_colors)
    assert len(colors) == len(_COLOR_INPUTS)
    assert colors[0].as_rgb_tuple() == (255, 0, 0)


def test_get_native_color(benchmark) -> None:
    """The cold cost of the boundary crossed for every styled cell."""
    natives = benchmark(_native_colors)
    assert all(native is not None for native in natives)
