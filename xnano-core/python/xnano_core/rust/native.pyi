"""xnano_core.rust.native

Type stubs for the ``rust`` ported primitives derived from the ``ratatui`` and ``tachyonfx``
creates.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from enum import IntEnum
from types import ModuleType
from typing import Any, Optional, Tuple, Type, overload

from xnano_core.rust.engine import (
    CoreEvent as CoreEvent,
    CoreTickEvent as CoreTickEvent,
    CoreTerminalEventKind as CoreTerminalEventKind,
)

engine: ModuleType
"""Stateful engine submodule (:mod:`xnano_core.rust.engine`)."""

class Rect:
    """Axis-aligned rectangle.

    Maps to :class:`ratatui::layout::Rect`.
    See https://docs.rs/ratatui/0.29.0/ratatui/layout/struct.Rect.html
    """

    def __init__(
        self, x: int = 0, y: int = 0, width: int = 0, height: int = 0
    ) -> None: ...
    @staticmethod
    def zero() -> Rect: ...
    @property
    def x(self) -> int: ...
    @property
    def y(self) -> int: ...
    @property
    def width(self) -> int: ...
    @property
    def height(self) -> int: ...
    def area(self) -> int: ...
    def is_empty(self) -> bool: ...
    def inner(self, margin: Margin) -> Rect: ...
    def left(self) -> int: ...
    def right(self) -> int: ...
    def top(self) -> int: ...
    def bottom(self) -> int: ...
    def offset(self, offset: Offset) -> Rect: ...
    def union(self, other: Rect) -> Rect: ...
    def intersection(self, other: Rect) -> Rect: ...
    def intersects(self, other: Rect) -> bool: ...
    def contains(self, x: int, y: int) -> bool: ...
    def __repr__(self) -> str: ...
    def __str__(self) -> str: ...

class Margin:
    """Layout margin.

    Maps to :class:`ratatui::layout::Margin`.
    See https://docs.rs/ratatui/0.29.0/ratatui/layout/struct.Margin.html
    """

    def __init__(self, horizontal: int = 0, vertical: int = 0) -> None: ...
    @property
    def horizontal(self) -> int: ...
    @property
    def vertical(self) -> int: ...
    def __repr__(self) -> str: ...

class Direction(IntEnum):
    """Layout direction.

    Maps to :class:`ratatui::layout::Direction`.
    See https://docs.rs/ratatui/0.29.0/ratatui/layout/enum.Direction.html
    """

    Horizontal = ...
    Vertical = ...

class Alignment(IntEnum):
    """Text alignment.

    Maps to :class:`ratatui::layout::Alignment`.
    See https://docs.rs/ratatui/0.29.0/ratatui/layout/enum.Alignment.html
    """

    Left = ...
    Center = ...
    Right = ...

class Flex(IntEnum):
    """Flex distribution mode for layout constraints.

    Maps to :class:`ratatui::layout::Flex`.
    See https://docs.rs/ratatui/0.29.0/ratatui/layout/enum.Flex.html
    """

    Legacy = ...
    Start = ...
    End = ...
    Center = ...
    SpaceBetween = ...
    SpaceAround = ...

class Constraint:
    """Layout size constraint.

    Maps to :class:`ratatui::layout::Constraint`.
    See https://docs.rs/ratatui/0.29.0/ratatui/layout/enum.Constraint.html
    """

    @staticmethod
    def min(value: int) -> Constraint: ...
    @staticmethod
    def max(value: int) -> Constraint: ...
    @staticmethod
    def length(value: int) -> Constraint: ...
    @staticmethod
    def percentage(value: int) -> Constraint: ...
    @staticmethod
    def ratio(numerator: int, denominator: int) -> Constraint: ...
    @staticmethod
    def fill(value: int) -> Constraint: ...
    @staticmethod
    def from_lengths(values: Sequence[int]) -> list[Constraint]: ...
    @staticmethod
    def from_percentages(values: Sequence[int]) -> list[Constraint]: ...
    @staticmethod
    def from_ratios(values: Sequence[Tuple[int, int]]) -> list[Constraint]: ...
    @staticmethod
    def from_mins(values: Sequence[int]) -> list[Constraint]: ...
    @staticmethod
    def from_maxes(values: Sequence[int]) -> list[Constraint]: ...
    @staticmethod
    def from_fills(values: Sequence[int]) -> list[Constraint]: ...
    def apply(self, length: int) -> int: ...
    def __repr__(self) -> str: ...

class Offset:
    """Signed offset.

    Maps to :class:`ratatui::layout::Offset`.
    See https://docs.rs/ratatui/0.29.0/ratatui/layout/struct.Offset.html
    """

    def __init__(self, x: int = 0, y: int = 0) -> None: ...
    @property
    def x(self) -> int: ...
    @property
    def y(self) -> int: ...

class Size:
    """Terminal size.

    Maps to :class:`ratatui::layout::Size`.
    See https://docs.rs/ratatui/0.29.0/ratatui/layout/struct.Size.html
    """

    def __init__(self, width: int, height: int) -> None: ...
    @property
    def width(self) -> int: ...
    @property
    def height(self) -> int: ...
    def __repr__(self) -> str: ...

class Layout:
    """Constraint-based layout splitter.

    Maps to :class:`ratatui::layout::Layout`.
    See https://docs.rs/ratatui/0.29.0/ratatui/layout/struct.Layout.html
    """

    @staticmethod
    def default() -> Layout: ...
    @staticmethod
    def new(
        direction: Direction, constraints: Sequence[Constraint]
    ) -> Layout: ...
    @staticmethod
    def vertical(constraints: Sequence[Constraint]) -> Layout: ...
    @staticmethod
    def horizontal(constraints: Sequence[Constraint]) -> Layout: ...
    def direction(self, direction: Direction) -> Layout: ...
    def constraints(self, constraints: Sequence[Constraint]) -> Layout: ...
    def margin(self, value: int) -> Layout: ...
    def margin_xy(self, margin: Margin) -> Layout: ...
    def horizontal_margin(self, value: int) -> Layout: ...
    def vertical_margin(self, value: int) -> Layout: ...
    def flex(self, flex: Flex) -> Layout: ...
    def spacing(self, value: int) -> Layout: ...
    def split(self, area: Rect) -> list[Rect]: ...
    def __repr__(self) -> str: ...

class LayoutSpacing:
    """Layout child spacing mode."""

    @staticmethod
    def space(value: int) -> LayoutSpacing: ...
    @staticmethod
    def overlap(value: int) -> LayoutSpacing: ...

class Color:
    """Terminal color.

    Maps to :class:`ratatui::style::Color`.
    See https://docs.rs/ratatui/0.29.0/ratatui/style/enum.Color.html
    """

    RESET: Color
    BLACK: Color
    RED: Color
    GREEN: Color
    YELLOW: Color
    BLUE: Color
    MAGENTA: Color
    CYAN: Color
    GRAY: Color
    DARK_GRAY: Color
    LIGHT_RED: Color
    LIGHT_GREEN: Color
    LIGHT_YELLOW: Color
    LIGHT_BLUE: Color
    LIGHT_MAGENTA: Color
    LIGHT_CYAN: Color
    WHITE: Color

    @staticmethod
    def parse(value: str) -> Color: ...
    @staticmethod
    def indexed(value: int) -> Color: ...
    @staticmethod
    def rgb(r: int, g: int, b: int) -> Color: ...
    @staticmethod
    def from_u32(value: int) -> Color: ...
    @staticmethod
    def from_hsl(h: float, s: float, l: float) -> Color: ...
    def to_u32(self) -> int: ...
    def __repr__(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...
    def __hash__(self) -> int: ...

class Modifier:
    """Text style modifier flags.

    Maps to :class:`ratatui::style::Modifier`.
    See https://docs.rs/ratatui/0.29.0/ratatui/style/struct.Modifier.html
    """

    BOLD: Modifier
    DIM: Modifier
    ITALIC: Modifier
    UNDERLINED: Modifier
    SLOW_BLINK: Modifier
    RAPID_BLINK: Modifier
    REVERSED: Modifier
    HIDDEN: Modifier
    CROSSED_OUT: Modifier
    EMPTY: Modifier

    def __or__(self, other: Modifier) -> Modifier: ...
    def __repr__(self) -> str: ...

class Style:
    """Combined foreground, background, and modifier style.

    Maps to :class:`ratatui::style::Style`.
    See https://docs.rs/ratatui/0.29.0/ratatui/style/struct.Style.html
    """

    @staticmethod
    def default() -> Style: ...
    @staticmethod
    def new() -> Style: ...
    @staticmethod
    def reset() -> Style: ...
    def fg(self, color: Color) -> Style: ...
    def bg(self, color: Color) -> Style: ...
    def add_modifier(self, modifier: Modifier) -> Style: ...
    def remove_modifier(self, modifier: Modifier) -> Style: ...
    def patch(self, other: Style) -> Style: ...
    def __repr__(self) -> str: ...

def color_from_hsl(h: float, s: float, l: float) -> Color:
    """Create a color from HSL components.

    Uses the ``palette`` crate; see also
    https://docs.rs/ratatui/0.29.0/ratatui/style/enum.Color.html#method.from_hsl
    """

def color_from_hex(value: str) -> Color:
    """Parse a hex color string (``#RGB`` or ``#RRGGBB``)."""

def color_lerp(a: Color, b: Color, t: float) -> Color:
    """Linearly interpolate between two colors."""

def color_to_hsl(color: Color) -> tuple[float, float, float]:
    """Convert a color to HSL components (hue in degrees, saturation, lightness)."""

def color_to_srgb(color: Color) -> tuple[float, float, float]:
    """Convert a color to normalized sRGB components (0.0–1.0)."""

def interpolate_colors(
    a: Color,
    b: Color,
    t: float,
    space: str = "rgb",
) -> Color:
    """Interpolate between two colors in RGB or HSL space."""

def tailwind_color(name: str, shade: int) -> Color:
    """Look up a Tailwind CSS palette color.

    Maps to :class:`ratatui::style::palette::tailwind`.
    See https://docs.rs/ratatui/0.29.0/ratatui/style/palette/tailwind/index.html
    """

class Span:
    """Styled text span.

    Maps to :class:`ratatui::text::Span`.
    See https://docs.rs/ratatui/0.29.0/ratatui/text/struct.Span.html
    """

    @staticmethod
    def default() -> Span: ...
    @staticmethod
    def raw(content: str) -> Span: ...
    @staticmethod
    def styled(content: str, style: Style) -> Span: ...
    def content(self, value: str) -> Span: ...
    def style(self, style: Style) -> Span: ...
    def patch_style(self, style: Style) -> Span: ...
    def reset_style(self) -> Span: ...
    def width(self) -> int: ...
    @property
    def text(self) -> str: ...
    def __repr__(self) -> str: ...

class Line:
    """A line of styled spans.

    Maps to :class:`ratatui::text::Line`.
    See https://docs.rs/ratatui/0.29.0/ratatui/text/struct.Line.html
    """

    @staticmethod
    def raw(content: str) -> Line: ...
    @staticmethod
    def styled(content: str, style: Style) -> Line: ...
    @staticmethod
    def from_spans(spans: Sequence[Span]) -> Line: ...
    def style(self, style: Style) -> Line: ...
    def patch_style(self, style: Style) -> Line: ...
    def reset_style(self) -> Line: ...
    def width(self) -> int: ...
    def alignment(self, alignment: Alignment) -> Line: ...
    def left_aligned(self) -> Line: ...
    def centered(self) -> Line: ...
    def right_aligned(self) -> Line: ...
    def spans(self, spans: Sequence[Span]) -> Line: ...
    def __repr__(self) -> str: ...

class Text:
    """Multi-line styled text.

    Maps to :class:`ratatui::text::Text`.
    See https://docs.rs/ratatui/0.29.0/ratatui/text/struct.Text.html
    """

    @staticmethod
    def raw(content: str) -> Text: ...
    @staticmethod
    def styled(content: str, style: Style) -> Text: ...
    @staticmethod
    def from_lines(lines: Sequence[Line]) -> Text: ...
    def style(self, style: Style) -> Text: ...
    def patch_style(self, style: Style) -> Text: ...
    def reset_style(self) -> Text: ...
    def width(self) -> int: ...
    def height(self) -> int: ...
    def alignment(self, alignment: Alignment) -> Text: ...
    def left_aligned(self) -> Text: ...
    def centered(self) -> Text: ...
    def right_aligned(self) -> Text: ...
    def __repr__(self) -> str: ...

def styled_span(
    content: str,
    fg: Optional[Color] = None,
    bg: Optional[Color] = None,
    modifiers: Optional[Modifier] = None,
) -> Span:
    """Convenience helper to build a :class:`Span` from style shorthand."""

class Borders:
    """Border flag set.

    Maps to :class:`ratatui::widgets::Borders`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.Borders.html
    """

    NONE: Borders
    TOP: Borders
    RIGHT: Borders
    BOTTOM: Borders
    LEFT: Borders
    ALL: Borders

    def __or__(self, other: Borders) -> Borders: ...
    def __repr__(self) -> str: ...

class BorderType(IntEnum):
    """Border rendering style.

    Maps to :class:`ratatui::widgets::BorderType`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/enum.BorderType.html
    """

    Plain = ...
    Rounded = ...
    Double = ...
    Thick = ...
    QuadrantInside = ...
    QuadrantOutside = ...

class TitlePosition(IntEnum):
    """Block title position.

    Maps to :class:`ratatui::widgets::block::Position`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/block/enum.Position.html
    """

    Top = ...
    Bottom = ...

class HighlightSpacing(IntEnum):
    """Highlight spacing for list/table widgets.

    Maps to :class:`ratatui::widgets::HighlightSpacing`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/enum.HighlightSpacing.html
    """

    Always = ...
    WhenSelected = ...
    Never = ...

class Wrap:
    """Paragraph word-wrap settings.

    Maps to :class:`ratatui::widgets::Wrap`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.Wrap.html
    """

    def __init__(self, trim: bool = False) -> None: ...

class BorderSet:
    """Border glyph set for :class:`Block`."""

    PLAIN: BorderSet
    ROUNDED: BorderSet
    DOUBLE: BorderSet
    THICK: BorderSet

    @staticmethod
    def new(
        top_left: str,
        top_right: str,
        bottom_left: str,
        bottom_right: str,
        vertical_left: str,
        vertical_right: str,
        horizontal_top: str,
        horizontal_bottom: str,
    ) -> BorderSet: ...
    def __repr__(self) -> str: ...

class Block:
    """Decorative block with optional borders and title.

    Maps to :class:`ratatui::widgets::Block`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.Block.html
    """

    @staticmethod
    def new() -> Block: ...
    @staticmethod
    def default() -> Block: ...
    @staticmethod
    def bordered() -> Block: ...
    def borders(self, borders: Borders) -> Block: ...
    def border_style(self, style: Style) -> Block: ...
    def border_type(self, border_type: BorderType) -> Block: ...
    def style(self, style: Style) -> Block: ...
    def title(self, title: Any) -> Block: ...
    def title_alignment(self, alignment: Alignment) -> Block: ...
    def title_style(self, style: Style) -> Block: ...
    def title_top(self, title: Any) -> Block: ...
    def title_bottom(self, title: Any) -> Block: ...
    def title_position(self, position: TitlePosition) -> Block: ...
    def title_at(self, title: Any, position: TitlePosition) -> Block: ...
    def inner(self, area: Rect) -> Rect: ...
    def padding(self, padding: Padding) -> Block: ...
    def __repr__(self) -> str: ...

class Paragraph:
    """Multi-line text widget.

    Maps to :class:`ratatui::widgets::Paragraph`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.Paragraph.html
    """

    @staticmethod
    def new(content: Any) -> Paragraph: ...
    def block(self, block: Block) -> Paragraph: ...
    def style(self, style: Style) -> Paragraph: ...
    def wrap(self, wrap: Wrap) -> Paragraph: ...
    def alignment(self, alignment: Alignment) -> Paragraph: ...
    def left_aligned(self) -> Paragraph: ...
    def centered(self) -> Paragraph: ...
    def right_aligned(self) -> Paragraph: ...
    def scroll(self, x: int, y: int) -> Paragraph: ...
    def __repr__(self) -> str: ...

class ListItem:
    """Single list entry.

    Maps to :class:`ratatui::widgets::ListItem`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.ListItem.html
    """

    @staticmethod
    def new(content: Any) -> ListItem: ...
    def style(self, style: Style) -> ListItem: ...
    def __repr__(self) -> str: ...

class ListDirection(IntEnum):
    """List rendering direction.

    Maps to :class:`ratatui::widgets::ListDirection`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/enum.ListDirection.html
    """

    TopToBottom = ...
    BottomToTop = ...

class RatList:
    """Selectable list widget.

    Python name ``RatList`` maps to :class:`ratatui::widgets::List`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.List.html
    """

    @staticmethod
    def new(items: Sequence[Any]) -> RatList: ...
    def block(self, block: Block) -> RatList: ...
    def style(self, style: Style) -> RatList: ...
    def highlight_style(self, style: Style) -> RatList: ...
    def direction(self, direction: ListDirection) -> RatList: ...
    def highlight_symbol(self, symbol: str) -> RatList: ...
    def items(self, items: Sequence[Any]) -> RatList: ...
    def repeat_highlight_symbol(self, repeat: bool) -> RatList: ...
    def highlight_spacing(self, spacing: HighlightSpacing) -> RatList: ...
    def scroll_padding(self, padding: int) -> RatList: ...
    def len(self) -> int: ...
    def is_empty(self) -> bool: ...
    def __repr__(self) -> str: ...

class ListState:
    """Mutable state for :class:`RatList`.

    Maps to :class:`ratatui::widgets::ListState`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.ListState.html
    """

    def __init__(self) -> None: ...
    def select(self, index: Optional[int] = None) -> None: ...
    @property
    def selected(self) -> Optional[int]: ...
    def select_next(self) -> None: ...
    def select_previous(self) -> None: ...
    def select_first(self) -> None: ...
    def select_last(self) -> None: ...
    @property
    def offset(self) -> int: ...
    def set_offset(self, value: int) -> None: ...
    def scroll_down_by(self, amount: int) -> None: ...
    def scroll_up_by(self, amount: int) -> None: ...
    def __repr__(self) -> str: ...

class Gauge:
    """Progress gauge widget.

    Maps to :class:`ratatui::widgets::Gauge`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.Gauge.html
    """

    @staticmethod
    def new() -> Gauge: ...
    @staticmethod
    def default() -> Gauge: ...
    def block(self, block: Block) -> Gauge: ...
    def style(self, style: Style) -> Gauge: ...
    def gauge_style(self, style: Style) -> Gauge: ...
    def percent(self, value: int) -> Gauge: ...
    def ratio(self, value: float) -> Gauge: ...
    def label(self, label: Any) -> Gauge: ...
    def use_unicode(self, value: bool) -> Gauge: ...
    def __repr__(self) -> str: ...

class Clear:
    """Widget that clears the render area.

    Maps to :class:`ratatui::widgets::Clear`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.Clear.html
    """

    @staticmethod
    def new() -> Clear: ...

class Padding:
    """Block inner padding.

    Maps to :class:`ratatui::widgets::block::Padding`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/block/struct.Padding.html
    """

    @staticmethod
    def zero() -> Padding: ...
    @staticmethod
    def uniform(value: int) -> Padding: ...
    @staticmethod
    def horizontal(value: int) -> Padding: ...
    @staticmethod
    def vertical(value: int) -> Padding: ...
    @staticmethod
    def symmetric(horizontal: int, vertical: int) -> Padding: ...
    @staticmethod
    def new(left: int, right: int, top: int, bottom: int) -> Padding: ...

class Position:
    """Cursor position.

    Maps to :class:`ratatui::layout::Position`.
    See https://docs.rs/ratatui/0.29.0/ratatui/layout/struct.Position.html
    """

    ORIGIN: Position

    def __init__(self, x: int, y: int) -> None: ...
    @property
    def x(self) -> int: ...
    @property
    def y(self) -> int: ...

class Cell:
    """Table cell.

    Maps to :class:`ratatui::widgets::Cell`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.Cell.html
    """

    @staticmethod
    def new(content: Any) -> Cell: ...
    def style(self, style: Style) -> Cell: ...
    def content(self, value: Any) -> Cell: ...

class Row:
    """Table row.

    Maps to :class:`ratatui::widgets::Row`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.Row.html
    """

    @staticmethod
    def new(cells: Sequence[Any]) -> Row: ...
    def style(self, style: Style) -> Row: ...
    def height(self, value: int) -> Row: ...
    def top_margin(self, value: int) -> Row: ...
    def bottom_margin(self, value: int) -> Row: ...
    def cells(self, cells: Sequence[Any]) -> Row: ...

class RatTable:
    """Table widget.

    Python name ``RatTable`` maps to :class:`ratatui::widgets::Table`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.Table.html
    """

    @staticmethod
    def new(rows: Sequence[Row], widths: Sequence[Constraint]) -> RatTable: ...
    def header(self, row: Row) -> RatTable: ...
    def footer(self, row: Row) -> RatTable: ...
    def block(self, block: Block) -> RatTable: ...
    def style(self, style: Style) -> RatTable: ...
    def row_highlight_style(self, style: Style) -> RatTable: ...
    def column_highlight_style(self, style: Style) -> RatTable: ...
    def cell_highlight_style(self, style: Style) -> RatTable: ...
    def highlight_symbol(self, symbol: Any) -> RatTable: ...
    def highlight_spacing(self, spacing: HighlightSpacing) -> RatTable: ...
    def rows(self, rows: Sequence[Row]) -> RatTable: ...
    def widths(self, widths: Sequence[Constraint]) -> RatTable: ...
    def column_spacing(self, value: int) -> RatTable: ...

class TableState:
    """Mutable state for :class:`RatTable`.

    Maps to :class:`ratatui::widgets::TableState`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.TableState.html
    """

    def __init__(self) -> None: ...
    def select(self, index: Optional[int] = None) -> None: ...
    @property
    def selected(self) -> Optional[int]: ...
    @property
    def selected_column(self) -> Optional[int]: ...
    def selected_cell(self) -> Optional[Tuple[int, int]]: ...
    @property
    def offset(self) -> int: ...
    def select_column(self, index: Optional[int] = None) -> None: ...
    def select_cell(
        self, indexes: Optional[Tuple[int, int]] = None
    ) -> None: ...
    def select_next(self) -> None: ...
    def select_previous(self) -> None: ...
    def select_next_column(self) -> None: ...
    def select_previous_column(self) -> None: ...
    def select_first(self) -> None: ...
    def select_last(self) -> None: ...
    def select_first_column(self) -> None: ...
    def select_last_column(self) -> None: ...
    def scroll_down_by(self, amount: int) -> None: ...
    def scroll_up_by(self, amount: int) -> None: ...
    def scroll_right_by(self, amount: int) -> None: ...
    def scroll_left_by(self, amount: int) -> None: ...

class ScrollbarOrientation(IntEnum):
    """Scrollbar orientation.

    Maps to :class:`ratatui::widgets::ScrollbarOrientation`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/enum.ScrollbarOrientation.html
    """

    VerticalRight = ...
    VerticalLeft = ...
    HorizontalBottom = ...
    HorizontalTop = ...

class Scrollbar:
    """Scrollbar widget.

    Maps to :class:`ratatui::widgets::Scrollbar`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.Scrollbar.html
    """

    @staticmethod
    def new(orientation: ScrollbarOrientation) -> Scrollbar: ...
    def style(self, style: Style) -> Scrollbar: ...
    def thumb_style(self, style: Style) -> Scrollbar: ...
    def track_style(self, style: Style) -> Scrollbar: ...
    def begin_style(self, style: Style) -> Scrollbar: ...
    def end_style(self, style: Style) -> Scrollbar: ...
    def begin_symbol(self, symbol: Optional[str] = None) -> Scrollbar: ...
    def end_symbol(self, symbol: Optional[str] = None) -> Scrollbar: ...

class ScrollDirection(IntEnum):
    """Scrollbar scroll direction.

    Maps to :class:`ratatui::widgets::ScrollDirection`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/enum.ScrollDirection.html
    """

    Forward = ...
    Backward = ...

class ScrollbarState:
    """Mutable state for :class:`Scrollbar`.

    Maps to :class:`ratatui::widgets::ScrollbarState`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.ScrollbarState.html
    """

    def __init__(self, content_length: int) -> None: ...
    def set_position(self, value: int) -> None: ...
    def set_content_length(self, value: int) -> None: ...
    def viewport_content_length(self, value: int) -> ScrollbarState: ...
    def prev(self) -> None: ...
    def next(self) -> None: ...
    def first(self) -> None: ...
    def last(self) -> None: ...
    def scroll(self, direction: ScrollDirection) -> None: ...

class Tabs:
    """Tab bar widget.

    Maps to :class:`ratatui::widgets::Tabs`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.Tabs.html
    """

    @staticmethod
    def new(titles: Sequence[Any]) -> Tabs: ...
    def block(self, block: Block) -> Tabs: ...
    def style(self, style: Style) -> Tabs: ...
    def highlight_style(self, style: Style) -> Tabs: ...
    def titles(self, titles: Sequence[Any]) -> Tabs: ...
    def select(self, index: Optional[int] = None) -> Tabs: ...
    def padding(self, left: str, right: str) -> Tabs: ...
    def padding_left(self, value: str) -> Tabs: ...
    def padding_right(self, value: str) -> Tabs: ...
    def divider(self, symbol: str) -> Tabs: ...

class SparklineBar:
    """Single bar in a sparkline chart.

    Maps to :class:`ratatui::widgets::SparklineBar`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.SparklineBar.html
    """

    @staticmethod
    def new(value: int) -> SparklineBar: ...
    def style(self, style: Style) -> SparklineBar: ...

class Sparkline:
    """Sparkline chart widget.

    Maps to :class:`ratatui::widgets::Sparkline`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.Sparkline.html
    """

    @staticmethod
    def default() -> Sparkline: ...
    @staticmethod
    def new(data: Sequence[int]) -> Sparkline: ...
    @staticmethod
    def from_bars(bars: Sequence[SparklineBar]) -> Sparkline: ...
    def data(self, data: Sequence[int]) -> Sparkline: ...
    def bars(self, bars: Sequence[SparklineBar]) -> Sparkline: ...
    def block(self, block: Block) -> Sparkline: ...
    def style(self, style: Style) -> Sparkline: ...
    def max(self, value: int) -> Sparkline: ...
    def absent_value_style(self, style: Style) -> Sparkline: ...
    def absent_value_symbol(self, symbol: str) -> Sparkline: ...

class LineGauge:
    """Horizontal line gauge widget.

    Maps to :class:`ratatui::widgets::LineGauge`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.LineGauge.html
    """

    @staticmethod
    def new() -> LineGauge: ...
    def ratio(self, value: float) -> LineGauge: ...
    def label(self, label: Any) -> LineGauge: ...
    def block(self, block: Block) -> LineGauge: ...
    def style(self, style: Style) -> LineGauge: ...
    def filled_style(self, style: Style) -> LineGauge: ...
    def unfilled_style(self, style: Style) -> LineGauge: ...

class Bar:
    """Single bar in a bar chart.

    Maps to :class:`ratatui::widgets::Bar`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.Bar.html
    """

    @staticmethod
    def default() -> Bar: ...
    @staticmethod
    def new(value: int, label: str) -> Bar: ...
    def value(self, value: int) -> Bar: ...
    def label(self, label: Any) -> Bar: ...
    def text_value(self, value: str) -> Bar: ...
    def style(self, style: Style) -> Bar: ...
    def value_style(self, style: Style) -> Bar: ...

class BarGroup:
    """Group of bars in a bar chart.

    Maps to :class:`ratatui::widgets::BarGroup`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.BarGroup.html
    """

    @staticmethod
    def new(bars: Sequence[Bar]) -> BarGroup: ...

class BarChart:
    """Bar chart widget.

    Maps to :class:`ratatui::widgets::BarChart`.
    See https://docs.rs/ratatui/0.29.0/ratatui/widgets/struct.BarChart.html
    """

    @staticmethod
    def new(groups: Sequence[BarGroup]) -> BarChart: ...
    def block(self, block: Block) -> BarChart: ...
    def style(self, style: Style) -> BarChart: ...
    def bar_width(self, value: int) -> BarChart: ...
    def max(self, value: int) -> BarChart: ...
    def bar_gap(self, value: int) -> BarChart: ...
    def group_gap(self, value: int) -> BarChart: ...
    def bar_style(self, style: Style) -> BarChart: ...
    def value_style(self, style: Style) -> BarChart: ...
    def label_style(self, style: Style) -> BarChart: ...
    def direction(self, direction: Direction) -> BarChart: ...

class GraphType(IntEnum):
    Scatter = ...
    Line = ...
    Bar = ...

class LegendPosition(IntEnum):
    Top = ...
    TopRight = ...
    TopLeft = ...
    Left = ...
    Right = ...
    Bottom = ...
    BottomRight = ...
    BottomLeft = ...

class Marker(IntEnum):
    Dot = ...
    Block = ...
    Bar = ...
    Braille = ...
    HalfBlock = ...

class Dataset:
    @staticmethod
    def default() -> Dataset: ...
    def name(self, value: Any) -> Dataset: ...
    def data(self, values: Sequence[tuple[float, float]]) -> Dataset: ...
    def marker(self, value: Marker) -> Dataset: ...
    def graph_type(self, value: GraphType) -> Dataset: ...
    def style(self, value: Style) -> Dataset: ...

class Axis:
    @staticmethod
    def default() -> Axis: ...
    def title(self, value: Any) -> Axis: ...
    def bounds(self, bounds: tuple[float, float]) -> Axis: ...
    def labels(self, values: Sequence[Any]) -> Axis: ...
    def style(self, value: Style) -> Axis: ...
    def labels_alignment(self, alignment: Alignment) -> Axis: ...

class Chart:
    @staticmethod
    def new(datasets: Sequence[Dataset]) -> Chart: ...
    def block(self, block: Block) -> Chart: ...
    def style(self, value: Style) -> Chart: ...
    def x_axis(self, axis: Axis) -> Chart: ...
    def y_axis(self, axis: Axis) -> Chart: ...
    def hidden_legend_constraints(
        self, width: Constraint, height: Constraint
    ) -> Chart: ...
    def legend_position(
        self, position: Optional[LegendPosition] = None
    ) -> Chart: ...

class Canvas:
    @staticmethod
    def default() -> Canvas: ...
    def block(self, block: Block) -> Canvas: ...
    def x_bounds(self, bounds: tuple[float, float]) -> Canvas: ...
    def y_bounds(self, bounds: tuple[float, float]) -> Canvas: ...
    def background_color(self, color: Color) -> Canvas: ...
    def marker(self, value: Marker) -> Canvas: ...
    def line(
        self, x1: float, y1: float, x2: float, y2: float, color: Color
    ) -> Canvas: ...
    def points(
        self, coords: Sequence[tuple[float, float]], color: Color
    ) -> Canvas: ...
    def rectangle(
        self, x: float, y: float, width: float, height: float, color: Color
    ) -> Canvas: ...
    def circle(
        self, x: float, y: float, radius: float, color: Color
    ) -> Canvas: ...
    def print(self, x: float, y: float, content: Any) -> Canvas: ...

class BufferCell:
    """Single buffer cell.

    Maps to :class:`ratatui::buffer::Cell`.
    See https://docs.rs/ratatui/0.29.0/ratatui/buffer/struct.Cell.html
    """

    EMPTY: BufferCell

    @staticmethod
    def new(symbol: str) -> BufferCell: ...
    @property
    def symbol(self) -> str: ...
    @property
    def fg(self) -> Color: ...
    @property
    def bg(self) -> Color: ...
    @property
    def modifier(self) -> Modifier: ...
    @property
    def style(self) -> Style: ...
    def reset(self) -> None: ...
    def set_symbol(self, symbol: str) -> BufferCell: ...
    def set_style(self, style: Style) -> BufferCell: ...
    def __repr__(self) -> str: ...

class Buffer:
    """Off-screen render buffer.

    Maps to :class:`ratatui::buffer::Buffer`.
    See https://docs.rs/ratatui/0.29.0/ratatui/buffer/struct.Buffer.html
    """

    @staticmethod
    def empty(area: Rect) -> Buffer: ...
    @staticmethod
    def filled(area: Rect, cell: BufferCell) -> Buffer: ...
    @staticmethod
    def with_lines(lines: Sequence[str | Line]) -> Buffer: ...
    @property
    def area(self) -> Rect: ...
    def render_widget(self, widget: Any, area: Rect) -> None: ...
    def render_stateful_widget(
        self, widget: Any, area: Rect, state: Any
    ) -> None: ...
    def cell(self, x: int, y: int) -> Optional[BufferCell]: ...
    def set_cell(self, x: int, y: int, symbol: str, style: Style) -> None: ...
    def set_line(
        self,
        y: int,
        line: str | Line,
        x: int = 0,
        max_width: Optional[int] = None,
    ) -> Tuple[int, int]: ...
    def set_style(self, area: Rect, style: Style) -> None: ...
    def set_span(
        self,
        x: int,
        y: int,
        span: Span,
        max_width: Optional[int] = None,
    ) -> Tuple[int, int]: ...
    def resize(self, area: Rect) -> None: ...
    def index_of(self, x: int, y: int) -> int: ...
    def pos_of(self, index: int) -> Position: ...
    def content(self) -> list[BufferCell]: ...
    def cell_symbol(self, x: int, y: int) -> str: ...
    def cell_fg(self, x: int, y: int) -> Color: ...
    def cell_bg(self, x: int, y: int) -> Color: ...
    def cell_modifier(self, x: int, y: int) -> Modifier: ...
    def set_string(
        self, x: int, y: int, string: str, style: Style
    ) -> None: ...
    def to_string_lines(self) -> list[str]: ...
    def to_ansi_lines(self, clip_bottom: bool = False) -> list[str]: ...
    def __repr__(self) -> str: ...

class BufferMutView:
    """Mutable view onto a live buffer during a drawable callback."""

    def get_area(self) -> Rect: ...
    def area(self) -> Rect: ...
    def get_cell(self, x: int, y: int) -> Optional[BufferCell]: ...
    def set_cell(self, x: int, y: int, symbol: str, style: Style) -> None: ...
    def set_string(
        self, x: int, y: int, string: str, style: Style
    ) -> None: ...
    def set_style(self, area: Rect, style: Style) -> None: ...

def render_widget(widget: Any, area: Rect, buffer: Buffer) -> None:
    """Render a supported widget into a buffer region."""

def render_stateful_widget(
    widget: Any, area: Rect, state: Any, buffer: Buffer
) -> None:
    """Render a supported stateful widget into a buffer region."""

class CompletedFrame:
    """Terminal state after a successful draw.

    Maps to :class:`ratatui::CompletedFrame`.
    See https://docs.rs/ratatui/0.29.0/ratatui/terminal/struct.CompletedFrame.html
    """

    buffer: Buffer
    area: Rect
    count: int

class Frame:
    """Per-frame render context.

    Valid only for the duration of a :meth:`Terminal.draw` callback.
    Not thread-safe (``unsendable``).

    Maps to :class:`ratatui::Frame`.
    See https://docs.rs/ratatui/0.29.0/ratatui/terminal/struct.Frame.html
    """

    def area(self) -> Rect: ...
    def render_widget(self, widget: Any, area: Rect) -> None: ...
    def render_stateful_widget(
        self, widget: Any, area: Rect, state: Any
    ) -> None: ...
    def set_cursor_position(self, position: Position) -> None: ...
    def hide_cursor(self) -> None:
        """Hide the terminal cursor for this frame draw pass."""
        ...
    def process_effects(
        self, manager: EffectManager, duration_ms: int, area: Rect
    ) -> None: ...
    def count(self) -> int: ...
    def buffer(self) -> Buffer: ...
    def get_buffer(self) -> Buffer: ...
    def size(self) -> Size: ...
    def viewport(self) -> Rect: ...

class KeyEventKind(IntEnum):
    """Key event phase.

    Maps to :class:`crossterm::event::KeyEventKind`.
    """

    Press = ...
    Repeat = ...
    Release = ...

class KeyEventState:
    """Extra keyboard event state flags.

    Maps to :class:`crossterm::event::KeyEventState`.
    """

    NONE: KeyEventState
    KEYPAD: KeyEventState
    CAPS_LOCK: KeyEventState
    NUM_LOCK: KeyEventState
    bits: int

    def keypad(self) -> bool: ...
    def caps_lock(self) -> bool: ...
    def num_lock(self) -> bool: ...
    def __repr__(self) -> str: ...

class KeyModifiers:
    """Keyboard modifier flags.

    Maps to :class:`crossterm::event::KeyModifiers`.
    """

    NONE: KeyModifiers
    SHIFT: KeyModifiers
    CONTROL: KeyModifiers
    ALT: KeyModifiers
    SUPER: KeyModifiers
    HYPER: KeyModifiers
    META: KeyModifiers
    bits: int

    def contains(self, other: KeyModifiers) -> bool: ...
    def control(self) -> bool: ...
    def shift(self) -> bool: ...
    def alt(self) -> bool: ...
    def super_(self) -> bool: ...
    def meta(self) -> bool: ...
    def hyper(self) -> bool: ...
    def __or__(self, other: KeyModifiers) -> KeyModifiers: ...
    def __repr__(self) -> str: ...

class KeyCode(IntEnum):
    """Key code category.

    Maps to :class:`crossterm::event::KeyCode`.
    """

    Char = ...
    Enter = ...
    Esc = ...
    Backspace = ...
    Tab = ...
    BackTab = ...
    Up = ...
    Down = ...
    Left = ...
    Right = ...
    Home = ...
    End = ...
    PageUp = ...
    PageDown = ...
    Insert = ...
    Delete = ...
    F = ...
    Null = ...
    CapsLock = ...
    ScrollLock = ...
    NumLock = ...
    PrintScreen = ...
    Pause = ...
    Menu = ...
    KeypadBegin = ...
    Media = ...
    Modifier = ...
    Other = ...

class MouseButton(IntEnum):
    """Mouse button identifier.

    Maps to :class:`crossterm::event::MouseButton`.
    """

    Left = ...
    Right = ...
    Middle = ...
    NoButton = ...

class MouseEventKind(IntEnum):
    """Mouse event kind.

    Maps to :class:`crossterm::event::MouseEventKind`.
    """

    Down = ...
    Up = ...
    Drag = ...
    Moved = ...
    ScrollDown = ...
    ScrollUp = ...
    ScrollLeft = ...
    ScrollRight = ...

class MouseEvent:
    """Mouse event data.

    Maps to :class:`crossterm::event::MouseEvent`.
    """

    kind: str
    button: str
    event_kind: MouseEventKind
    mouse_button: MouseButton
    x: int
    y: int
    column: int
    row: int
    modifiers: KeyModifiers

class KeyEvent:
    """Keyboard event data.

    Maps to :class:`crossterm::event::KeyEvent`.
    """

    kind: KeyEventKind
    modifiers: KeyModifiers
    code_name: KeyCode
    state: KeyEventState

    def char_value(self) -> Optional[str]: ...
    def function_number(self) -> Optional[int]: ...
    def is_char(self, ch: str) -> bool: ...
    def char(self) -> Optional[str]: ...
    def is_up(self) -> bool: ...
    def is_down(self) -> bool: ...
    def is_left(self) -> bool: ...
    def is_right(self) -> bool: ...
    def is_enter(self) -> bool: ...
    def is_esc(self) -> bool: ...
    def is_backspace(self) -> bool: ...
    def is_tab(self) -> bool: ...
    def is_page_up(self) -> bool: ...
    def is_page_down(self) -> bool: ...
    def is_home(self) -> bool: ...
    def is_end(self) -> bool: ...
    def is_insert(self) -> bool: ...
    def is_delete(self) -> bool: ...
    def is_null(self) -> bool: ...
    def is_back_tab(self) -> bool: ...
    def is_function_key(self) -> bool: ...
    def is_caps_lock(self) -> bool: ...
    def is_scroll_lock(self) -> bool: ...
    def is_num_lock(self) -> bool: ...
    def __repr__(self) -> str: ...

class Terminal:
    """Ratatui terminal handle.

    Not thread-safe (``unsendable``).

    Maps to :class:`ratatui::DefaultTerminal`.
    See https://docs.rs/ratatui/0.29.0/ratatui/struct.DefaultTerminal.html
    """

    @staticmethod
    def init() -> Terminal: ...
    def draw(self, callback: Callable[[Frame], Any]) -> None: ...
    def try_draw(self, callback: Callable[[Frame], Any]) -> CompletedFrame: ...
    def flush(self) -> None: ...
    def clear(self) -> None: ...
    def size(self) -> Size: ...
    def __enter__(self) -> Terminal: ...
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Any,
    ) -> None: ...

def restore_terminal() -> None:
    """Restore the terminal to its pre-ratatui state."""

def poll_event(timeout_ms: int) -> Optional[CoreEvent]:
    """Poll for a terminal event with a timeout in milliseconds."""

def read_event() -> CoreEvent:
    """Block until a terminal event is available."""

class CursorStyle(IntEnum):
    """Terminal cursor shape.

    Maps to :class:`crossterm::cursor::SetCursorStyle`.
    """

    DefaultUserShape = ...
    BlinkingBlock = ...
    SteadyBlock = ...
    BlinkingUnderline = ...
    SteadyUnderline = ...
    BlinkingBar = ...
    SteadyBar = ...

def show_cursor() -> None:
    """Show the terminal cursor."""

def hide_cursor() -> None:
    """Hide the terminal cursor."""

def save_cursor_position() -> None:
    """Save the current cursor position."""

def restore_cursor_position() -> None:
    """Restore the saved cursor position."""

def move_cursor_to(x: int, y: int) -> None:
    """Move the cursor to ``(x, y)``."""

def move_cursor_to_column(x: int) -> None:
    """Move the cursor to column ``x`` on the current row."""

def move_cursor_to_row(y: int) -> None:
    """Move the cursor to row ``y`` on the current column."""

def move_cursor_up(count: int = 1) -> None:
    """Move the cursor up by ``count`` cells."""

def move_cursor_down(count: int = 1) -> None:
    """Move the cursor down by ``count`` cells."""

def move_cursor_left(count: int = 1) -> None:
    """Move the cursor left by ``count`` cells."""

def move_cursor_right(count: int = 1) -> None:
    """Move the cursor right by ``count`` cells."""

def move_cursor_to_next_line(count: int = 1) -> None:
    """Move the cursor to the next line."""

def move_cursor_to_previous_line(count: int = 1) -> None:
    """Move the cursor to the previous line."""

def enable_cursor_blinking() -> None:
    """Enable cursor blinking."""

def disable_cursor_blinking() -> None:
    """Disable cursor blinking."""

def set_cursor_style(style: CursorStyle) -> None:
    """Set the terminal cursor style."""

def get_cursor_position() -> Position:
    """Query the current cursor position."""

class ClearType(IntEnum):
    """Terminal clear mode.

    Maps to :class:`crossterm::terminal::ClearType`.
    """

    All = ...
    Purge = ...
    FromCursorDown = ...
    FromCursorUp = ...
    CurrentLine = ...
    UntilNewLine = ...

def enable_raw_mode() -> None:
    """Enable terminal raw mode."""

def disable_raw_mode() -> None:
    """Disable terminal raw mode."""

def is_raw_mode_enabled() -> bool:
    """Return whether raw mode is enabled."""

def terminal_size() -> Size:
    """Return the terminal size in columns and rows."""

def terminal_window_size() -> Size:
    """Return the terminal window size in columns and rows."""

def scroll_up(count: int = 1) -> None:
    """Scroll the terminal buffer up."""

def scroll_down(count: int = 1) -> None:
    """Scroll the terminal buffer down."""

def clear_terminal(clear_type: ClearType) -> None:
    """Clear the terminal using the given clear type."""

def enter_alternate_screen() -> None:
    """Switch to the alternate screen buffer."""

def leave_alternate_screen() -> None:
    """Leave the alternate screen buffer."""

def set_terminal_title(title: str) -> None:
    """Set the terminal window title."""

def enable_line_wrap() -> None:
    """Enable terminal line wrapping."""

def disable_line_wrap() -> None:
    """Disable terminal line wrapping."""

def begin_synchronized_update() -> None:
    """Begin a synchronized terminal update."""

def end_synchronized_update() -> None:
    """End a synchronized terminal update."""

def supports_keyboard_enhancement() -> bool:
    """Return whether the terminal supports keyboard enhancement."""

class KeyboardEnhancementFlags:
    """Keyboard enhancement protocol flags.

    Maps to :class:`crossterm::event::KeyboardEnhancementFlags`.
    """

    DISAMBIGUATE_ESCAPE_CODES: KeyboardEnhancementFlags
    REPORT_EVENT_TYPES: KeyboardEnhancementFlags
    REPORT_ALTERNATE_KEYS: KeyboardEnhancementFlags
    REPORT_ALL_KEYS_AS_ESCAPE_CODES: KeyboardEnhancementFlags
    bits: int

    def __or__(
        self, other: KeyboardEnhancementFlags
    ) -> KeyboardEnhancementFlags: ...
    def __repr__(self) -> str: ...

def enable_mouse_capture() -> None:
    """Enable mouse event capture."""

def disable_mouse_capture() -> None:
    """Disable mouse event capture."""

def enable_bracketed_paste() -> None:
    """Enable bracketed paste mode."""

def disable_bracketed_paste() -> None:
    """Disable bracketed paste mode."""

def enable_focus_change() -> None:
    """Enable focus change events."""

def disable_focus_change() -> None:
    """Disable focus change events."""

def push_keyboard_enhancement_flags(flags: KeyboardEnhancementFlags) -> None:
    """Push keyboard enhancement flags."""

def pop_keyboard_enhancement_flags() -> None:
    """Pop keyboard enhancement flags."""

class ConsoleColor(IntEnum):
    """Console foreground/background color.

    Maps to :class:`crossterm::style::Color`.
    """

    Reset = ...
    Black = ...
    DarkGrey = ...
    Red = ...
    DarkRed = ...
    Green = ...
    DarkGreen = ...
    Yellow = ...
    DarkYellow = ...
    Blue = ...
    DarkBlue = ...
    Magenta = ...
    DarkMagenta = ...
    Cyan = ...
    DarkCyan = ...
    White = ...
    Grey = ...
    AnsiValue = ...
    Rgb = ...

class ConsoleAttribute(IntEnum):
    """Console text attribute.

    Maps to :class:`crossterm::style::Attribute`.
    """

    Reset = ...
    Bold = ...
    Dim = ...
    Italic = ...
    Underlined = ...
    DoubleUnderlined = ...
    Undercurled = ...
    Underdotted = ...
    Underdashed = ...
    SlowBlink = ...
    RapidBlink = ...
    Reverse = ...
    Hidden = ...
    CrossedOut = ...
    Fraktur = ...
    NoBold = ...
    NormalIntensity = ...
    NoItalic = ...
    NoUnderline = ...
    NoBlink = ...
    NoReverse = ...
    NoHidden = ...
    NotCrossedOut = ...
    Framed = ...
    Encircled = ...
    OverLined = ...
    NotFramedOrEncircled = ...
    NotOverLined = ...

def set_foreground_color(
    color: ConsoleColor,
    *,
    ansi_value: Optional[int] = None,
    rgb: Optional[Tuple[int, int, int]] = None,
) -> None:
    """Set the console foreground color."""

def set_background_color(
    color: ConsoleColor,
    *,
    ansi_value: Optional[int] = None,
    rgb: Optional[Tuple[int, int, int]] = None,
) -> None:
    """Set the console background color."""

def reset_color() -> None:
    """Reset console colors to default."""

def set_attribute(attribute: ConsoleAttribute) -> None:
    """Set a console text attribute."""

def print_styled_content(
    text: str,
    *,
    foreground: Optional[ConsoleColor] = None,
    background: Optional[ConsoleColor] = None,
    attribute: Optional[ConsoleAttribute] = None,
    foreground_ansi: Optional[int] = None,
    background_ansi: Optional[int] = None,
    foreground_rgb: Optional[Tuple[int, int, int]] = None,
    background_rgb: Optional[Tuple[int, int, int]] = None,
) -> None:
    """Print styled text to stdout."""

def print_text(text: str) -> None:
    """Print plain text to stdout."""

def flush_stdout_buffer() -> None:
    """Flush queued stdout commands."""

class Motion(IntEnum):
    """Effect motion direction.

    Maps to :class:`tachyonfx::Motion`.
    See https://docs.rs/tachyonfx/0.25.0/tachyonfx/enum.Motion.html
    """

    UpToDown = ...
    DownToUp = ...
    LeftToRight = ...
    RightToLeft = ...

class Interpolation(IntEnum):
    """Effect interpolation curve.

    Maps to :class:`tachyonfx::Interpolation`.
    See https://docs.rs/tachyonfx/0.25.0/tachyonfx/enum.Interpolation.html
    """

    BackIn = ...
    BackOut = ...
    BackInOut = ...
    BounceIn = ...
    BounceOut = ...
    BounceInOut = ...
    CircIn = ...
    CircOut = ...
    CircInOut = ...
    CubicIn = ...
    CubicOut = ...
    CubicInOut = ...
    ElasticIn = ...
    ElasticOut = ...
    ElasticInOut = ...
    ExpoIn = ...
    ExpoOut = ...
    ExpoInOut = ...
    Linear = ...
    QuadIn = ...
    QuadOut = ...
    QuadInOut = ...
    QuartIn = ...
    QuartOut = ...
    QuartInOut = ...
    QuintIn = ...
    QuintOut = ...
    QuintInOut = ...
    Reverse = ...
    SmoothStep = ...
    Spring = ...
    SineIn = ...
    SineOut = ...
    SineInOut = ...

class ColorSpace(IntEnum):
    """Color interpolation space.

    Maps to :class:`tachyonfx::ColorSpace`.
    See https://docs.rs/tachyonfx/0.25.0/tachyonfx/enum.ColorSpace.html
    """

    Rgb = ...
    Hsl = ...
    Hsv = ...

class Duration:
    """Effect duration.

    Maps to :class:`tachyonfx::Duration`.
    See https://docs.rs/tachyonfx/0.25.0/tachyonfx/struct.Duration.html
    """

    ZERO: Duration

    @staticmethod
    def from_millis(milliseconds: int) -> Duration: ...
    @staticmethod
    def from_secs(seconds: int) -> Duration: ...
    def as_millis(self) -> int: ...
    def is_zero(self) -> bool: ...
    def __repr__(self) -> str: ...

class EffectTimer:
    """Effect timing and interpolation state.

    Maps to :class:`tachyonfx::EffectTimer`.
    See https://docs.rs/tachyonfx/0.25.0/tachyonfx/struct.EffectTimer.html
    """

    @staticmethod
    def from_ms(
        duration_ms: int, interpolation: Interpolation
    ) -> EffectTimer: ...
    def remaining_ms(self) -> int: ...
    def duration_ms(self) -> int: ...
    def alpha(self) -> float: ...
    def is_reversed(self) -> bool: ...
    def started(self) -> bool: ...
    def is_done(self) -> bool: ...
    def reset(self) -> None: ...
    def __repr__(self) -> str: ...

class RepeatMode(IntEnum):
    """Effect repeat mode.

    Maps to :class:`tachyonfx::fx::RepeatMode`.
    """

    Forever = ...
    Times = ...
    Duration = ...

class RefRect:
    """Mutable reference to a rectangle area.

    Not thread-safe (``unsendable``).

    Maps to :class:`tachyonfx::RefRect`.
    """

    @staticmethod
    def new(rect: Rect) -> RefRect: ...
    @staticmethod
    def default() -> RefRect: ...
    def get(self) -> Rect: ...
    def set(self, rect: Rect) -> None: ...
    def contains(self, x: int, y: int) -> bool: ...
    def __repr__(self) -> str: ...

class RadialPattern:
    """Radial spatial pattern for effects.

    Maps to :class:`tachyonfx::pattern::RadialPattern`.
    """

    @staticmethod
    def center() -> RadialPattern: ...
    @staticmethod
    def new(center_x: float, center_y: float) -> RadialPattern: ...
    @staticmethod
    def with_transition(
        center_x: float, center_y: float, transition_width: float
    ) -> RadialPattern: ...
    def with_transition_width(self, width: float) -> RadialPattern: ...
    def with_center(
        self, center_x: float, center_y: float
    ) -> RadialPattern: ...

class ExpandDirection(IntEnum):
    """Bidirectional expand direction.

    Maps to :class:`tachyonfx::fx::ExpandDirection`.
    """

    Horizontal = ...
    Vertical = ...

class EvolveSymbolSet(IntEnum):
    """Symbol progression set for evolve effects.

    Maps to :class:`tachyonfx::fx::EvolveSymbolSet`.
    """

    BlocksHorizontal = ...
    BlocksVertical = ...
    CircleFill = ...
    Circles = ...
    Quadrants = ...
    Shaded = ...
    Squares = ...

class CellFilter:
    """Cell selection filter for effects.

    Not thread-safe (``unsendable``).

    Maps to :class:`tachyonfx::CellFilter`.
    See https://docs.rs/tachyonfx/0.25.0/tachyonfx/struct.CellFilter.html
    """

    ALL: CellFilter
    TEXT: CellFilter
    NON_EMPTY: CellFilter

    @staticmethod
    def fg_color(color: Color) -> CellFilter: ...
    @staticmethod
    def bg_color(color: Color) -> CellFilter: ...
    @staticmethod
    def inner(margin: Margin) -> CellFilter: ...
    @staticmethod
    def outer(margin: Margin) -> CellFilter: ...
    @staticmethod
    def area(rect: Rect) -> CellFilter: ...
    @staticmethod
    def all_of(filters: Sequence[CellFilter]) -> CellFilter: ...
    @staticmethod
    def any_of(filters: Sequence[CellFilter]) -> CellFilter: ...
    @staticmethod
    def not_(filter: CellFilter) -> CellFilter: ...
    @staticmethod
    def none_of(filters: Sequence[CellFilter]) -> CellFilter: ...
    @staticmethod
    def ref_area(ref_rect: RefRect) -> CellFilter: ...
    @staticmethod
    def layout(layout: Layout, index: int) -> CellFilter: ...
    @staticmethod
    def position_fn(callback: Callable[[int, int], bool]) -> CellFilter: ...
    @staticmethod
    def eval_cell(
        callback: Callable[[str, Color, Color], bool],
    ) -> CellFilter: ...
    def negated(self) -> CellFilter: ...
    def into_static(self) -> CellFilter: ...

class Effect:
    """Terminal visual effect.

    Not thread-safe (``unsendable``).

    Maps to :class:`tachyonfx::Effect`.
    See https://docs.rs/tachyonfx/0.25.0/tachyonfx/struct.Effect.html
    """

    def with_area(self, area: Rect) -> Effect: ...
    def with_filter(self, filter: CellFilter) -> Effect: ...
    def with_color_space(self, color_space: ColorSpace) -> Effect: ...
    def with_rng(self, seed: int) -> Effect: ...
    def reversed(self) -> Effect: ...
    def name(self) -> str: ...
    def is_done(self) -> bool: ...
    def is_running(self) -> bool: ...
    def reset(self) -> None: ...
    def get_area(self) -> Optional[Rect]: ...
    def set_area(self, area: Rect) -> None: ...
    def get_filter(self) -> Optional[CellFilter]: ...
    def set_filter(self, filter: CellFilter) -> None: ...
    def reverse(self) -> None: ...
    def timer(self) -> Optional[EffectTimer]: ...
    def get_timer(self) -> Optional[EffectTimer]: ...
    def reset_timer(self) -> None: ...
    def set_color_space(self, color_space: ColorSpace) -> None: ...
    def with_pattern(self, pattern: RadialPattern) -> Effect: ...
    def to_dsl(self) -> str: ...
    def process(
        self, duration_ms: int, buffer: Buffer, area: Rect
    ) -> Optional[int]: ...

class EffectManager:
    """Effect scheduler and processor.

    Not thread-safe (``unsendable``).

    Maps to :class:`tachyonfx::EffectManager`.
    See https://docs.rs/tachyonfx/0.25.0/tachyonfx/struct.EffectManager.html
    """

    def __init__(self) -> None: ...
    def add(self, effect: Effect) -> None: ...
    def add_unique(self, key: str, effect: Effect) -> None: ...
    def unique(self, key: str, effect: Effect) -> Effect: ...
    def cancel(self, key: str) -> None: ...
    def is_running(self) -> bool: ...
    def process(
        self, duration_ms: int, buffer: Buffer, area: Rect
    ) -> None: ...

def fade_to_fg(
    color: Color,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Fade foreground to a color. See :func:`tachyonfx::fx::fade_to_fg`."""

def fade_from_fg(
    color: Color,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Fade foreground from a color. See :func:`tachyonfx::fx::fade_from_fg`."""

def fade_to(
    fg: Color,
    bg: Color,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Fade to foreground and background colors. See :func:`tachyonfx::fx::fade_to`."""

def fade_from(
    fg: Color,
    bg: Color,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Fade from foreground and background colors. See :func:`tachyonfx::fx::fade_from`."""

def paint(
    fg: Color,
    bg: Color,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Paint cells to colors. See :func:`tachyonfx::fx::paint`."""

def paint_fg(
    fg: Color,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Paint foreground color. See :func:`tachyonfx::fx::paint_fg`."""

def paint_bg(
    bg: Color,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Paint background color. See :func:`tachyonfx::fx::paint_bg`."""

def slide_in(
    direction: Motion,
    gradient_length: int,
    randomness: int,
    color: Color,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Slide effect in. See :func:`tachyonfx::fx::slide_in`."""

def slide_out(
    direction: Motion,
    gradient_length: int,
    randomness: int,
    color: Color,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Slide effect out. See :func:`tachyonfx::fx::slide_out`."""

def sweep_in(
    direction: Motion,
    gradient_length: int,
    randomness: int,
    color: Color,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Sweep effect in. See :func:`tachyonfx::fx::sweep_in`."""

def sweep_out(
    direction: Motion,
    gradient_length: int,
    randomness: int,
    color: Color,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Sweep effect out. See :func:`tachyonfx::fx::sweep_out`."""

def dissolve(
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Dissolve effect. See :func:`tachyonfx::fx::dissolve`."""

def dissolve_to(
    style: Style,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Dissolve to a style. See :func:`tachyonfx::fx::dissolve_to`."""

def coalesce(
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Coalesce effect. See :func:`tachyonfx::fx::coalesce`."""

def coalesce_from(
    style: Style,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Coalesce from a style. See :func:`tachyonfx::fx::coalesce_from`."""

def sleep_effect(duration_ms: int) -> Effect:
    """No-op delay effect. See :func:`tachyonfx::fx::sleep`."""

def sequence_effects(effects: Sequence[Effect]) -> Effect:
    """Run effects in sequence. See :func:`tachyonfx::fx::sequence`."""

def parallel_effects(effects: Sequence[Effect]) -> Effect:
    """Run effects in parallel. See :func:`tachyonfx::fx::parallel`."""

def repeating_effect(effect: Effect) -> Effect:
    """Repeat an effect forever. See :func:`tachyonfx::fx::repeating`."""

def ping_pong_effect(effect: Effect) -> Effect:
    """Ping-pong an effect. See :func:`tachyonfx::fx::ping_pong`."""

@overload
def repeat_effect(effect: Effect, *, times: int) -> Effect: ...
@overload
def repeat_effect(effect: Effect, *, duration_ms: int) -> Effect: ...
@overload
def repeat_effect(effect: Effect) -> Effect: ...
def repeat_effect(
    effect: Effect,
    times: Optional[int] = None,
    duration_ms: Optional[int] = None,
) -> Effect:
    """Repeat an effect. See :func:`tachyonfx::fx::repeat`."""

def delay_effect(duration_ms: int, effect: Effect) -> Effect:
    """Delay before starting an effect. See :func:`tachyonfx::fx::delay`."""

def prolong_start_effect(duration_ms: int, effect: Effect) -> Effect:
    """Hold the start state. See :func:`tachyonfx::fx::prolong_start`."""

def prolong_end_effect(duration_ms: int, effect: Effect) -> Effect:
    """Hold the end state. See :func:`tachyonfx::fx::prolong_end`."""

def saturate(
    duration_ms: int,
    fg: Optional[float] = None,
    bg: Optional[float] = None,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Adjust saturation. See :func:`tachyonfx::fx::saturate`."""

def saturate_fg(
    fg: float,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Adjust foreground saturation. See :func:`tachyonfx::fx::saturate_fg`."""

def saturate_bg(
    bg: float,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Adjust background saturation. Convenience wrapper around :func:`saturate`."""

def lighten(
    duration_ms: int,
    fg: Optional[float] = None,
    bg: Optional[float] = None,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Lighten colors. See :func:`tachyonfx::fx::lighten`."""

def lighten_fg(
    fg: float,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Lighten foreground. See :func:`tachyonfx::fx::lighten_fg`."""

def lighten_bg(
    bg: float,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Lighten background. Convenience wrapper around :func:`lighten`."""

def darken(
    duration_ms: int,
    fg: Optional[float] = None,
    bg: Optional[float] = None,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Darken colors. See :func:`tachyonfx::fx::darken`."""

def darken_fg(
    fg: float,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Darken foreground. See :func:`tachyonfx::fx::darken_fg`."""

def darken_bg(
    bg: float,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Darken background. Convenience wrapper around :func:`darken`."""

def hsl_shift(
    duration_ms: int,
    fg_h: Optional[float] = None,
    fg_s: Optional[float] = None,
    fg_l: Optional[float] = None,
    bg_h: Optional[float] = None,
    bg_s: Optional[float] = None,
    bg_l: Optional[float] = None,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Shift HSL values. See :func:`tachyonfx::fx::hsl_shift`."""

def hsl_shift_fg(
    h: float,
    s: float,
    l: float,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Shift foreground HSL. See :func:`tachyonfx::fx::hsl_shift_fg`."""

def hsl_shift_bg(
    h: float,
    s: float,
    l: float,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Shift background HSL. Convenience wrapper around :func:`hsl_shift`."""

def evolve_effect(
    symbols: EvolveSymbolSet,
    duration_ms: int,
    style: Optional[Style] = None,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Evolve cell symbols. See :func:`tachyonfx::fx::evolve`."""

def evolve_into_effect(
    symbols: EvolveSymbolSet,
    duration_ms: int,
    style: Optional[Style] = None,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Evolve symbols into target style. See :func:`tachyonfx::fx::evolve_into`."""

def evolve_from_effect(
    symbols: EvolveSymbolSet,
    duration_ms: int,
    style: Optional[Style] = None,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Evolve symbols from source style. See :func:`tachyonfx::fx::evolve_from`."""

def explode_effect(
    force: float,
    force_rng_factor: float,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Explode cells outward. See :func:`tachyonfx::fx::explode`."""

def glitch_effect(
    cell_glitch_ratio: float,
    action_start_delay_min_ms: int,
    action_start_delay_max_ms: int,
    action_min_ms: int,
    action_max_ms: int,
    filter: Optional[CellFilter] = None,
    seed: Optional[int] = None,
) -> Effect:
    """Glitch effect with randomized cell mutations. See :class:`tachyonfx::fx::Glitch`."""

def translate_effect(
    effect: Effect,
    translate_by: Offset,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Translate an effect's area. See :func:`tachyonfx::fx::translate`."""

def expand_effect(
    direction: ExpandDirection,
    style: Style,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Bidirectional expand using block characters. See :func:`tachyonfx::fx::expand`."""

def stretch_effect(
    direction: Motion,
    style: Style,
    duration_ms: int,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Unidirectional stretch/shrink using block characters. See :func:`tachyonfx::fx::stretch`."""

def resize_area_effect(
    initial_size: Size,
    duration_ms: int,
    effect: Optional[Effect] = None,
    interpolation: Optional[Interpolation] = None,
) -> Effect:
    """Resize effect area over time. See :func:`tachyonfx::fx::resize_area`."""

def freeze_at_effect(
    alpha: float, set_raw_alpha: bool, effect: Effect
) -> Effect:
    """Freeze an effect at a given alpha. See :func:`tachyonfx::fx::freeze_at`."""

def remap_alpha_effect(
    alpha_start: float, alpha_end: float, effect: Effect
) -> Effect:
    """Remap effect alpha range. See :func:`tachyonfx::fx::remap_alpha`."""

def never_complete_effect(effect: Effect) -> Effect:
    """Prevent effect from completing. See :func:`tachyonfx::fx::never_complete`."""

def run_once_effect(effect: Effect) -> Effect:
    """Run effect only once. See :func:`tachyonfx::fx::run_once`."""

def consume_tick_effect() -> Effect:
    """Consume one tick without visual change. See :func:`tachyonfx::fx::consume_tick`."""

def with_duration_effect(duration_ms: int, effect: Effect) -> Effect:
    """Override effect duration. See :func:`tachyonfx::fx::with_duration`."""

def timed_never_complete_effect(duration_ms: int, effect: Effect) -> Effect:
    """Never complete for a bounded duration. See :func:`tachyonfx::fx::timed_never_complete`."""

__all__ = (
    "Alignment",
    "Bar",
    "Axis",
    "BarChart",
    "BarGroup",
    "BorderSet",
    "BufferMutView",
    "Canvas",
    "Chart",
    "Dataset",
    "GraphType",
    "LegendPosition",
    "LayoutSpacing",
    "Marker",
    "CoreEvent",
    "CoreTickEvent",
    "CoreTerminalEventKind",
    "engine",
    "begin_synchronized_update",
    "Block",
    "BorderType",
    "Borders",
    "Buffer",
    "BufferCell",
    "Cell",
    "CellFilter",
    "Clear",
    "ClearType",
    "clear_terminal",
    "Color",
    "ColorSpace",
    "CompletedFrame",
    "ConsoleAttribute",
    "ConsoleColor",
    "Constraint",
    "consume_tick_effect",
    "coalesce",
    "coalesce_from",
    "color_from_hex",
    "color_from_hsl",
    "color_lerp",
    "color_to_hsl",
    "color_to_srgb",
    "CursorStyle",
    "darken",
    "darken_bg",
    "darken_fg",
    "delay_effect",
    "disable_bracketed_paste",
    "disable_cursor_blinking",
    "disable_focus_change",
    "disable_line_wrap",
    "disable_mouse_capture",
    "disable_raw_mode",
    "Direction",
    "dissolve",
    "dissolve_to",
    "Duration",
    "Effect",
    "EffectManager",
    "EffectTimer",
    "enable_bracketed_paste",
    "enable_cursor_blinking",
    "enable_focus_change",
    "enable_line_wrap",
    "enable_mouse_capture",
    "enable_raw_mode",
    "end_synchronized_update",
    "enter_alternate_screen",
    "EvolveSymbolSet",
    "evolve_effect",
    "evolve_from_effect",
    "evolve_into_effect",
    "expand_effect",
    "ExpandDirection",
    "explode_effect",
    "fade_from",
    "fade_from_fg",
    "fade_to",
    "fade_to_fg",
    "Flex",
    "flush_stdout_buffer",
    "Frame",
    "freeze_at_effect",
    "Gauge",
    "get_cursor_position",
    "glitch_effect",
    "hide_cursor",
    "HighlightSpacing",
    "hsl_shift",
    "hsl_shift_bg",
    "hsl_shift_fg",
    "Interpolation",
    "interpolate_colors",
    "is_raw_mode_enabled",
    "KeyboardEnhancementFlags",
    "KeyCode",
    "KeyEvent",
    "KeyEventKind",
    "KeyEventState",
    "KeyModifiers",
    "Layout",
    "leave_alternate_screen",
    "lighten",
    "lighten_bg",
    "lighten_fg",
    "Line",
    "LineGauge",
    "ListDirection",
    "ListItem",
    "ListState",
    "Margin",
    "Modifier",
    "Motion",
    "MouseButton",
    "MouseEvent",
    "MouseEventKind",
    "move_cursor_down",
    "move_cursor_left",
    "move_cursor_right",
    "move_cursor_to",
    "move_cursor_to_column",
    "move_cursor_to_next_line",
    "move_cursor_to_previous_line",
    "move_cursor_to_row",
    "move_cursor_up",
    "never_complete_effect",
    "Offset",
    "Padding",
    "paint",
    "paint_bg",
    "paint_fg",
    "parallel_effects",
    "Paragraph",
    "ping_pong_effect",
    "poll_event",
    "pop_keyboard_enhancement_flags",
    "Position",
    "print_styled_content",
    "print_text",
    "prolong_end_effect",
    "prolong_start_effect",
    "push_keyboard_enhancement_flags",
    "RadialPattern",
    "RatList",
    "RatTable",
    "read_event",
    "Rect",
    "RefRect",
    "remap_alpha_effect",
    "render_stateful_widget",
    "render_widget",
    "repeat_effect",
    "RepeatMode",
    "repeating_effect",
    "resize_area_effect",
    "reset_color",
    "restore_cursor_position",
    "restore_terminal",
    "Row",
    "run_once_effect",
    "save_cursor_position",
    "saturate",
    "saturate_bg",
    "saturate_fg",
    "scroll_down",
    "scroll_up",
    "ScrollDirection",
    "Scrollbar",
    "ScrollbarOrientation",
    "ScrollbarState",
    "sequence_effects",
    "set_attribute",
    "set_background_color",
    "set_cursor_style",
    "set_foreground_color",
    "set_terminal_title",
    "show_cursor",
    "Size",
    "sleep_effect",
    "slide_in",
    "slide_out",
    "Span",
    "Sparkline",
    "stretch_effect",
    "Style",
    "styled_span",
    "supports_keyboard_enhancement",
    "sweep_in",
    "sweep_out",
    "TableState",
    "Tabs",
    "tailwind_color",
    "Terminal",
    "terminal_size",
    "terminal_window_size",
    "Text",
    "timed_never_complete_effect",
    "TitlePosition",
    "translate_effect",
    "with_duration_effect",
    "Wrap",
)
