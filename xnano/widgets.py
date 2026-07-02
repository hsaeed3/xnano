"""xnano.widgets"""

from __future__ import annotations

import dataclasses
from typing import Any, Literal, Sequence, TypeAlias

from xnano import _core
from xnano._convert import Content, as_line, as_span, as_text, unwrap
from xnano.layout import Alignment, Rectangle, _core_alignment
from xnano.style import (
    Borders,
    BorderSide,
    BorderTypeName,
    HighlightSpacingName,
    Padding,
    Style,
    TitlePositionName,
    Wrap,
    _core_border_type,
    _core_highlight_spacing,
    _core_title_position,
)


ListDirectionName: TypeAlias = Literal["top_to_bottom", "bottom_to_top"]
"""The rendering direction of a list."""


_LIST_DIRECTION: dict[ListDirectionName, _core.ListDirection] = {
    "top_to_bottom": _core.ListDirection.TopToBottom,
    "bottom_to_top": _core.ListDirection.BottomToTop,
}


def _core_list_direction(value: ListDirectionName) -> _core.ListDirection:
    return _LIST_DIRECTION[value]


def _merge_tailwind(
    class_name: str | None,
    style: Style | None,
    width: int | None,
    height: int | None,
    block: Block | None = None,
) -> tuple[Style | None, int | None, int | None, Block | None]:
    if not class_name:
        return style, width, height, block

    from xnano.tailwind import parse_tailwind

    tw = parse_tailwind(class_name)

    if "style" in tw:
        if style is not None:
            style = tw["style"].patch(style)
        else:
            style = tw["style"]

    if width is None:
        width = tw.get("width")
    if height is None:
        height = tw.get("height")

    has_block_opts = any(
        k in tw for k in ("borders", "border_type", "border_style", "padding")
    )
    if has_block_opts:
        if block is None:
            block = Block(
                borders=tw.get("borders"),
                border_type=tw.get("border_type"),
                border_style=tw.get("border_style"),
                padding=tw.get("padding"),
            )

    return style, width, height, block


def _merge_tailwind_block(
    class_name: str | None,
    style: Style | None,
    borders: Borders | Literal["all", "none"] | None,
    border_type: BorderTypeName | None,
    border_style: Style | None,
    padding: Padding | int | None,
    width: int | None,
    height: int | None,
) -> tuple[
    Style | None,
    Borders | Literal["all", "none"] | None,
    BorderTypeName | None,
    Style | None,
    Padding | int | None,
    int | None,
    int | None,
]:
    if not class_name:
        return (
            style,
            borders,
            border_type,
            border_style,
            padding,
            width,
            height,
        )

    from xnano.tailwind import parse_tailwind

    tw = parse_tailwind(class_name)

    if "style" in tw:
        if style is not None:
            style = tw["style"].patch(style)
        else:
            style = tw["style"]

    if borders is None:
        borders = tw.get("borders")
    if border_type is None:
        border_type = tw.get("border_type")
    if border_style is None:
        border_style = tw.get("border_style")
    if padding is None:
        padding = tw.get("padding")
    if width is None:
        width = tw.get("width")
    if height is None:
        height = tw.get("height")

    return style, borders, border_type, border_style, padding, width, height


class Block:
    """A decorative panel container with optional borders, titles, and padding.

    ``Block`` is commonly used as a background or border container for other
    widgets like ``Paragraph`` or ``ListView``.

    Example::

        block = Block(
            title="Panel Title",
            borders="all",
            border_type="rounded",
            padding=1
        )
    """

    __slots__ = ("_inner", "width", "height")
    _inner: _core.Block
    width: int | None
    height: int | None

    def __init__(
        self,
        *,
        title: Content | None = None,
        title_alignment: Alignment | None = None,
        title_position: TitlePositionName | None = None,
        title_style: Style | None = None,
        borders: Borders | Literal["all", "none"] | None = None,
        border_type: BorderTypeName | None = None,
        border_style: Style | None = None,
        style: Style | None = None,
        padding: Padding | int | None = None,
        width: int | None = None,
        height: int | None = None,
        class_name: str | None = None,
    ) -> None:
        """Create a new Block.

        Args:
            title: The title content to display.
            title_alignment: Horizontal title alignment.
            title_position: Edge to display the title (``"top"`` or ``"bottom"``).
            title_style: Style for the title text.
            borders: Borders to enable. Can be a ``Borders`` instance, ``"all"``,
                or ``"none"``.
            border_type: The visual style of the border characters.
            border_style: Style for the border lines.
            style: Background and default style for the entire block.
            padding: Inner padding spacing. Can be an integer or a ``Padding`` instance.
            width: Optional fixed width constraint.
            height: Optional fixed height constraint.
            class_name: Optional space-separated Tailwind utility classes.
        """
        style, borders, border_type, border_style, padding, width, height = (
            _merge_tailwind_block(
                class_name,
                style,
                borders,
                border_type,
                border_style,
                padding,
                width,
                height,
            )
        )
        inner = _core.Block.new()

        if borders is not None:
            if borders == "all":
                inner = inner.borders(Borders.all()._to_core())
            elif borders == "none":
                inner = inner.borders(Borders.none()._to_core())
            elif isinstance(borders, Borders):
                inner = inner.borders(borders._to_core())

        if border_type is not None:
            inner = inner.border_type(_core_border_type(border_type))

        if border_style is not None:
            inner = inner.border_style(border_style._to_core())

        if style is not None:
            inner = inner.style(style._to_core())

        if title is not None:
            inner = inner.title(as_line(title))

        if title_alignment is not None:
            inner = inner.title_alignment(_core_alignment(title_alignment))

        if title_position is not None:
            inner = inner.title_position(_core_title_position(title_position))

        if title_style is not None:
            inner = inner.title_style(title_style._to_core())

        if padding is not None:
            if isinstance(padding, int):
                inner = inner.padding(Padding.uniform(padding)._to_core())
            elif isinstance(padding, Padding):
                inner = inner.padding(padding._to_core())

        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "width", width)
        object.__setattr__(self, "height", height)

    @classmethod
    def _from_core(cls, inner: _core.Block) -> Block:
        """Construct from a native ``_core.Block``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.Block:
        """Return the native block."""
        return self._inner

    def inner(self, area: Rectangle) -> Rectangle:
        """Return the inner content area within a block layout area,
        excluding borders and padding.
        """
        inner = self._inner.inner(area._to_core())
        return Rectangle(
            x=inner.x, y=inner.y, width=inner.width, height=inner.height
        )

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Block is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Block is immutable")


class Paragraph:
    """A multi-line text display widget with optional wrapping and alignment.

    Example::

        paragraph = Paragraph("This is some text.", alignment="center")
    """

    __slots__ = ("_inner", "width", "height")
    _inner: _core.Paragraph
    width: int | None
    height: int | None

    def __init__(
        self,
        content: Content = "",
        *,
        block: Block | None = None,
        style: Style | None = None,
        wrap: Wrap | bool | None = None,
        alignment: Alignment | None = None,
        scroll: tuple[int, int] | None = None,
        width: int | None = None,
        height: int | None = None,
        class_name: str | None = None,
    ) -> None:
        """Create a new Paragraph.

        Args:
            content: The text content of the paragraph.
            block: An optional decorative ``Block`` container to draw around the text.
            style: The base style for the paragraph text.
            wrap: Word-wrap settings. If ``True``, word wrapping is enabled.
            alignment: Horizontal text alignment.
            scroll: Optional ``(scroll_x, scroll_y)`` viewport offset tuple.
            width: Optional fixed width constraint.
            height: Optional fixed height constraint.
            class_name: Optional space-separated Tailwind utility classes.
        """
        style, width, height, block = _merge_tailwind(
            class_name, style, width, height, block
        )
        inner = _core.Paragraph.new(as_text(content))

        if block is not None:
            inner = inner.block(block._to_core())

        if style is not None:
            inner = inner.style(style._to_core())

        if wrap is not None:
            if isinstance(wrap, bool):
                if wrap:
                    inner = inner.wrap(Wrap(trim=False)._to_core())
            else:
                inner = inner.wrap(wrap._to_core())

        if alignment is not None:
            inner = inner.alignment(_core_alignment(alignment))

        if scroll is not None:
            inner = inner.scroll(scroll[0], scroll[1])

        if width is None and block is not None:
            width = getattr(block, "width", None)
        if height is None and block is not None:
            height = getattr(block, "height", None)

        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "width", width)
        object.__setattr__(self, "height", height)

    @classmethod
    def _from_core(cls, inner: _core.Paragraph) -> Paragraph:
        """Construct from a native ``_core.Paragraph``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.Paragraph:
        """Return the native paragraph."""
        return self._inner

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Paragraph is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Paragraph is immutable")


class ListItem:
    """A single entry in a selectable ListView widget."""

    __slots__ = ("_inner",)
    _inner: _core.ListItem

    def __init__(
        self, content: Content, *, style: Style | None = None
    ) -> None:
        """Create a new List item.

        Args:
            content: The text content of this item.
            style: Optional styling for this item.
        """
        inner = _core.ListItem.new(as_line(content))
        if style is not None:
            inner = inner.style(style._to_core())
        object.__setattr__(self, "_inner", inner)

    @classmethod
    def _from_core(cls, inner: _core.ListItem) -> ListItem:
        """Construct from a native ``_core.ListItem``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.ListItem:
        """Return the native list item."""
        return self._inner

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("ListItem is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("ListItem is immutable")


class ListView:
    """A selectable list widget for displaying a list of items.

    Example::

        my_list = ListView(
            ["Item 1", "Item 2", "Item 3"],
            highlight_symbol="> ",
            highlight_style=Style(foreground="yellow")
        )
    """

    __slots__ = ("_inner", "width", "height")
    _inner: _core.RatList

    def __init__(
        self,
        items: Sequence[ListItem | Content],
        *,
        block: Block | None = None,
        style: Style | None = None,
        highlight_style: Style | None = None,
        highlight_symbol: str | None = None,
        direction: ListDirectionName | None = None,
        repeat_highlight_symbol: bool | None = None,
        highlight_spacing: HighlightSpacingName | None = None,
        scroll_padding: int | None = None,
        width: int | None = None,
        height: int | None = None,
        class_name: str | None = None,
    ) -> None:
        """Create a new selectable ListView.

        Args:
            items: A list of items to display (can be strings, Spans,
                or explicit ``ListItem`` instances).
            block: Optional background/border Block around the list.
            style: The default style for list items.
            highlight_style: Style applied to the selected item.
            highlight_symbol: Symbol drawn next to the selected item.
            direction: Direction the list items stack (``"top_to_bottom"``
                or ``"bottom_to_top"``).
            repeat_highlight_symbol: Wrap lines highlight repeat toggle.
            highlight_spacing: Highlight spacing mode.
            scroll_padding: Threshold buffer rows before scrolling viewport.
            width: Optional fixed width constraint.
            height: Optional fixed height constraint.
            class_name: Optional space-separated Tailwind utility classes.
        """
        style, width, height, block = _merge_tailwind(
            class_name, style, width, height, block
        )
        native_items = [
            item._to_core() if isinstance(item, ListItem) else as_line(item)
            for item in items
        ]
        inner = _core.RatList.new(native_items)

        if block is not None:
            inner = inner.block(block._to_core())
        if style is not None:
            inner = inner.style(style._to_core())
        if highlight_style is not None:
            inner = inner.highlight_style(highlight_style._to_core())
        if highlight_symbol is not None:
            inner = inner.highlight_symbol(highlight_symbol)
        if direction is not None:
            inner = inner.direction(_core_list_direction(direction))
        if repeat_highlight_symbol is not None:
            inner = inner.repeat_highlight_symbol(repeat_highlight_symbol)
        if highlight_spacing is not None:
            inner = inner.highlight_spacing(
                _core_highlight_spacing(highlight_spacing)
            )
        if scroll_padding is not None:
            inner = inner.scroll_padding(scroll_padding)

        if width is None and block is not None:
            width = getattr(block, "width", None)
        if height is None and block is not None:
            height = getattr(block, "height", None)

        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "width", width)
        object.__setattr__(self, "height", height)

    @classmethod
    def _from_core(cls, inner: _core.RatList) -> ListView:
        """Construct from a native ``_core.RatList``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.RatList:
        """Return the native list."""
        return self._inner

    def len(self) -> int:
        """Return the number of items in the list."""
        return self._inner.len()

    def is_empty(self) -> bool:
        """Return ``True`` if the list has zero items."""
        return self._inner.is_empty()

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("ListView is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("ListView is immutable")


class ListState:
    """Mutable selection and scroll state for a ``ListView`` widget.

    Example::

        state = ListState()
        state.select(0)
    """

    __slots__ = ("_inner",)
    _inner: _core.ListState

    def __init__(self, *, selected: int | None = None) -> None:
        """Create a new mutable list selection state.

        Args:
            selected: Optional initial selected index.
        """
        inner = _core.ListState()
        if selected is not None:
            inner.select(selected)
        object.__setattr__(self, "_inner", inner)

    @classmethod
    def _from_core(cls, inner: _core.ListState) -> ListState:
        """Construct from a native ``_core.ListState``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.ListState:
        """Return the native list state."""
        return self._inner

    def select(self, index: int | None = None) -> None:
        """Select the item at the specified index, or clear selection."""
        self._inner.select(index)

    @property
    def selected(self) -> int | None:
        """The currently selected item index, or ``None``."""
        return self._inner.selected

    def select_next(self) -> None:
        """Select the next item in the list."""
        self._inner.select_next()

    def select_previous(self) -> None:
        """Select the previous item in the list."""
        self._inner.select_previous()

    def select_first(self) -> None:
        """Select the first item in the list."""
        self._inner.select_first()

    def select_last(self) -> None:
        """Select the last item in the list."""
        self._inner.select_last()

    @property
    def offset(self) -> int:
        """The scroll offset index of the viewport."""
        return self._inner.offset

    def set_offset(self, value: int) -> None:
        """Set the scroll offset index of the viewport."""
        self._inner.set_offset(value)

    def scroll_down_by(self, amount: int) -> None:
        """Scroll the viewport down by *amount* items."""
        self._inner.scroll_down_by(amount)

    def scroll_up_by(self, amount: int) -> None:
        """Scroll the viewport up by *amount* items."""
        self._inner.scroll_up_by(amount)

    def __repr__(self) -> str:
        return repr(self._inner)


class Gauge:
    """A progress bar gauge widget.

    Example::

        gauge = Gauge(percent=45, label="Loading...")
    """

    __slots__ = ("_inner", "width", "height")
    _inner: _core.Gauge

    def __init__(
        self,
        *,
        percent: int | None = None,
        ratio: float | None = None,
        label: Content | None = None,
        block: Block | None = None,
        style: Style | None = None,
        gauge_style: Style | None = None,
        use_unicode: bool = False,
        width: int | None = None,
        height: int | None = None,
        class_name: str | None = None,
    ) -> None:
        """Create a progress Gauge.

        Args:
            percent: Completion percentage (0 to 100).
            ratio: Completion ratio (0.0 to 1.0).
            label: Text label drawn inside the gauge.
            block: Optional background/border Block around the gauge.
            style: Overall default style.
            gauge_style: Style for the progress filled portion.
            use_unicode: Enable unicode blocks for smoother progress rendering.
            width: Optional fixed width constraint.
            height: Optional fixed height constraint.
            class_name: Optional space-separated Tailwind utility classes.
        """
        style, width, height, block = _merge_tailwind(
            class_name, style, width, height, block
        )
        inner = _core.Gauge.new()

        if percent is not None:
            inner = inner.percent(percent)
        if ratio is not None:
            inner = inner.ratio(ratio)
        if label is not None:
            inner = inner.label(as_span(label))
        if block is not None:
            inner = inner.block(block._to_core())
        if style is not None:
            inner = inner.style(style._to_core())
        if gauge_style is not None:
            inner = inner.gauge_style(gauge_style._to_core())
        if use_unicode:
            inner = inner.use_unicode(use_unicode)

        if width is None and block is not None:
            width = getattr(block, "width", None)
        if height is None and block is not None:
            height = getattr(block, "height", None)

        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "width", width)
        object.__setattr__(self, "height", height)

    @classmethod
    def _from_core(cls, inner: _core.Gauge) -> Gauge:
        """Construct from a native ``_core.Gauge``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.Gauge:
        """Return the native gauge."""
        return self._inner

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Gauge is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Gauge is immutable")


class Clear:
    """A helper widget that clears the area it is rendered into, filling
    it with default empty background cells.
    """

    __slots__ = ("_inner",)
    _inner: _core.Clear

    def __init__(self) -> None:
        """Create a Clear widget."""
        object.__setattr__(self, "_inner", _core.Clear.new())

    @classmethod
    def _from_core(cls, inner: _core.Clear) -> Clear:
        """Construct from a native ``_core.Clear``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.Clear:
        """Return the native clear widget."""
        return self._inner

    def __repr__(self) -> str:
        return "Clear()"

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Clear is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Clear is immutable")


class Tabs:
    """A tab bar widget for multi-screen navigation.

    Example::

        tabs = Tabs(["Dashboard", "Settings", "Help"], selected=0)
    """

    __slots__ = ("_inner",)
    _inner: _core.Tabs

    def __init__(
        self,
        titles: Sequence[Content],
        *,
        block: Block | None = None,
        style: Style | None = None,
        highlight_style: Style | None = None,
        selected: int | None = None,
        padding: tuple[str, str] | None = None,
        divider: str | None = None,
    ) -> None:
        """Create a tab bar widget.

        Args:
            titles: List of tab titles.
            block: Optional background/border Block surrounding the tab bar.
            style: Base style for unselected tabs.
            highlight_style: Style for the active/selected tab.
            selected: The active tab index.
            padding: Optional ``(padding_left, padding_right)`` tab text spacing.
            divider: Divider symbol drawn between tabs.
        """
        inner = _core.Tabs.new([as_line(title) for title in titles])

        if block is not None:
            inner = inner.block(block._to_core())
        if style is not None:
            inner = inner.style(style._to_core())
        if highlight_style is not None:
            inner = inner.highlight_style(highlight_style._to_core())
        if selected is not None:
            inner = inner.select(selected)
        if padding is not None:
            inner = inner.padding(padding[0], padding[1])
        if divider is not None:
            inner = inner.divider(divider)

        object.__setattr__(self, "_inner", inner)

    @classmethod
    def _from_core(cls, inner: _core.Tabs) -> Tabs:
        """Construct from a native ``_core.Tabs``."""
        obj = object.__new__(cls)
        object.__setattr__(obj, "_inner", inner)
        return obj

    def _to_core(self) -> _core.Tabs:
        """Return the native tabs widget."""
        return self._inner

    def __repr__(self) -> str:
        return repr(self._inner)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Tabs is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Tabs is immutable")


__all__ = (
    "Block",
    "Clear",
    "Gauge",
    "ListView",
    "ListDirectionName",
    "ListItem",
    "ListState",
    "Paragraph",
    "Tabs",
)
