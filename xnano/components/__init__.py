"""xnano.components

---

Components for text, input, data display, navigation, and feedback.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xnano.components.bar import (
        Bar,
        BarDirection,
        BarGlyphPreset,
        BarGlyphs,
    )
    from xnano.components.button import Button
    from xnano.components.chart import Chart, Series
    from xnano.components.component import (
        Bars,
        Canvas,
        CellCanvas,
        Clear,
        Component,
        ComponentRenderContext,
        Content,
        Gauge,
        Items,
        LineGauge,
        Panel,
        Plot,
        Run,
        ScrollbarContent,
        Sparkline,
        Stack,
        TableGrid,
        TextBlock,
    )
    from xnano.components.dropdown import Dropdown
    from xnano.components.image import (
        Image,
        ImageData,
        ImageFit,
        ImageFrame,
        ImageSource,
    )
    from xnano.components.input import Input
    from xnano.components.link import Link
    from xnano.components.loader import Loader, LoaderStyle
    from xnano.components.markdown import Markdown
    from xnano.components.options import Option, Options, Select
    from xnano.components.scrollbar import Scrollbar
    from xnano.components.table import Column, Table
    from xnano.components.text import Text

__all__ = (
    "Bar",
    "BarDirection",
    "BarGlyphPreset",
    "BarGlyphs",
    "Bars",
    "Button",
    "Canvas",
    "CellCanvas",
    "Chart",
    "Clear",
    "Column",
    "Component",
    "ComponentRenderContext",
    "Content",
    "Dropdown",
    "Gauge",
    "Image",
    "ImageData",
    "ImageFit",
    "ImageFrame",
    "ImageSource",
    "Input",
    "Items",
    "LineGauge",
    "Link",
    "Loader",
    "LoaderStyle",
    "Markdown",
    "Option",
    "Options",
    "Panel",
    "Plot",
    "Run",
    "Scrollbar",
    "ScrollbarContent",
    "Select",
    "Series",
    "Sparkline",
    "Stack",
    "Table",
    "TableGrid",
    "Text",
    "TextBlock",
)


def __getattr__(name: str) -> Any:
    if name in {
        "Bars",
        "Canvas",
        "CellCanvas",
        "Clear",
        "Component",
        "ComponentRenderContext",
        "Content",
        "Gauge",
        "Items",
        "LineGauge",
        "Panel",
        "Plot",
        "Run",
        "ScrollbarContent",
        "Sparkline",
        "Stack",
        "TableGrid",
        "TextBlock",
    }:
        from xnano.components import component

        return getattr(component, name)
    if name in {"Bar", "BarDirection", "BarGlyphPreset", "BarGlyphs"}:
        from xnano.components import bar

        return getattr(bar, name)
    if name == "Button":
        from xnano.components.button import Button

        return Button
    if name in {"Chart", "Series"}:
        from xnano.components import chart

        return getattr(chart, name)
    if name == "Dropdown":
        from xnano.components.dropdown import Dropdown

        return Dropdown
    if name in {"Image", "ImageData", "ImageFit", "ImageFrame", "ImageSource"}:
        from xnano.components import image

        return getattr(image, name)
    if name == "Input":
        from xnano.components.input import Input

        return Input
    if name == "Link":
        from xnano.components.link import Link

        return Link
    if name in {"Loader", "LoaderStyle"}:
        from xnano.components import loader

        return getattr(loader, name)
    if name == "Markdown":
        from xnano.components.markdown import Markdown

        return Markdown
    if name in {"Option", "Options", "Select"}:
        from xnano.components import options

        return getattr(options, name)
    if name == "Scrollbar":
        from xnano.components.scrollbar import Scrollbar

        return Scrollbar
    if name in {"Column", "Table"}:
        from xnano.components import table

        return getattr(table, name)
    if name == "Text":
        from xnano.components.text import Text

        return Text
    raise AttributeError(
        f"module 'xnano.components' has no attribute {name!r}"
    )


def __dir__() -> list[str]:
    return list(__all__)
