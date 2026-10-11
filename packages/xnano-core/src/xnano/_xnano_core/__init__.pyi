"""
xnano._xnano_core

Type stubs for the compiled module behind the ``xnano`` package.

Every class and function here is implemented in Rust. The compiled module is the package
initializer, so ``xnano._xnano_core._core_types`` sits next to it.
"""

from collections.abc import Awaitable, Callable, Iterable, Iterator, Mapping, Sequence
from types import TracebackType
from typing import Any, Generic, Literal, NoReturn, TypeVar, overload

from ._core_types import (
    BlitMode as BlitMode,
)
from ._core_types import (
    BorderKind as BorderKind,
)
from ._core_types import (
    CapabilityStatus as CapabilityStatus,
)
from ._core_types import (
    ColorName as ColorName,
)
from ._core_types import (
    ColorProfile as ColorProfile,
)
from ._core_types import (
    ColorValue as ColorValue,
)
from ._core_types import (
    Coordinate as Coordinate,
)
from ._core_types import (
    CoreContext as CoreContext,
)
from ._core_types import (
    EvaluationContext as EvaluationContext,
)
from ._core_types import (
    EventContext as EventContext,
)
from ._core_types import (
    EventKind as EventKind,
)
from ._core_types import (
    FrameContext as FrameContext,
)
from ._core_types import (
    GeometryMode as GeometryMode,
)
from ._core_types import (
    GraphicsProtocol as GraphicsProtocol,
)
from ._core_types import (
    HookCallback as HookCallback,
)
from ._core_types import (
    HookDecorator as HookDecorator,
)
from ._core_types import (
    HookEventKind as HookEventKind,
)
from ._core_types import (
    Interpolation as Interpolation,
)
from ._core_types import (
    JSONSchema as JSONSchema,
)
from ._core_types import (
    JSONValue as JSONValue,
)
from ._core_types import (
    KeyBindingText as KeyBindingText,
)
from ._core_types import (
    KeyEventKind as KeyEventKind,
)
from ._core_types import (
    KeyModifier as KeyModifier,
)
from ._core_types import (
    KeyName as KeyName,
)
from ._core_types import (
    Modifier as Modifier,
)
from ._core_types import (
    MouseButton as MouseButton,
)
from ._core_types import (
    MouseEventKind as MouseEventKind,
)
from ._core_types import (
    Orientation as Orientation,
)
from ._core_types import (
    Pixel as Pixel,
)
from ._core_types import (
    PixelAnchor as PixelAnchor,
)
from ._core_types import (
    PixelEncoding as PixelEncoding,
)
from ._core_types import (
    RasterMode as RasterMode,
)
from ._core_types import (
    Registry as Registry,
)
from ._core_types import (
    RenderFormat as RenderFormat,
)
from ._core_types import (
    Rendering as Rendering,
)
from ._core_types import (
    Side as Side,
)
from ._core_types import (
    StatePath as StatePath,
)
from ._core_types import (
    TextContent as TextContent,
)
from ._core_types import (
    UpdateContext as UpdateContext,
)
from ._core_types import (
    WriteMode as WriteMode,
)

__version__: str

ValueType = TypeVar('ValueType')
NumberType = TypeVar('NumberType', int, float)
CallbackType = TypeVar('CallbackType')
StateType = TypeVar('StateType')

class Point:
    """
    A cell position, counted in columns (``x``) and rows (``y``) from the top-left.

    Maps to [`ratatui::layout::Position`](https://docs.rs/ratatui/0.30.0/ratatui/layout/struct.Position.html).

    Args:
        x: The column.
        y: The row.

    Examples:
        ```python
        point = Point(2, 3) + Point(1, 1)
        assert (point.x, point.y) == (3, 4)
        assert point - Point(3, 4) == Point(0, 0)
        ```
    """

    def __init__(self, x: int = 0, y: int = 0) -> None: ...
    @property
    def x(self) -> int:
        """The column."""

    @property
    def y(self) -> int:
        """The row."""

    def __add__(self, other: Point | Offset) -> Point:
        """
        Add two positions component by component.

        Examples:
            ```python
            assert Point(1, 2) + Point(3, 4) == Point(4, 6)
            ```
        """

    def __sub__(self, other: Point | Offset) -> Point:
        """
        Subtract two positions component by component.

        Examples:
            ```python
            assert Point(4, 6) - Point(3, 4) == Point(1, 2)
            ```
        """

    def __neg__(self) -> Point: ...
    def __mul__(self, factor: int) -> Point: ...
    def __rmul__(self, factor: int) -> Point: ...

class Size:
    """
    A width and a height, counted in cells.

    Maps to [`ratatui::layout::Size`](https://docs.rs/ratatui/0.30.0/ratatui/layout/struct.Size.html).

    Args:
        width: The number of columns.
        height: The number of rows.

    Examples:
        ```python
        size = Size(80, 24)
        assert (size.width, size.height) == (80, 24)
        ```
    """

    def __init__(self, width: int = 0, height: int = 0) -> None: ...
    @property
    def width(self) -> int:
        """The number of columns."""

    @property
    def height(self) -> int:
        """The number of rows."""

    def __add__(self, other: Size) -> Size: ...
    def __sub__(self, other: Size) -> Size: ...
    def __mul__(self, factor: int) -> Size: ...
    def __rmul__(self, factor: int) -> Size: ...

class Rectangle:
    """
    A rectangle of cells with half-open bounds.

    The left and top edges are inclusive, and the right and bottom edges are exclusive.

    Maps to [`ratatui::layout::Rect`](https://docs.rs/ratatui/0.30.0/ratatui/layout/struct.Rect.html).

    Args:
        x: The left column.
        y: The top row.
        width: The number of columns.
        height: The number of rows.

    Examples:
        ```python
        area = Rectangle(2, 1, 10, 4)
        assert area.area == 40
        assert area.contains(Point(2, 1))
        assert not area.contains(Point(12, 1))
        ```
    """

    def __init__(
        self, x: int = 0, y: int = 0, width: int = 0, height: int = 0
    ) -> None: ...
    @property
    def x(self) -> int:
        """The left column."""

    @property
    def y(self) -> int:
        """The top row."""

    @property
    def width(self) -> int:
        """The number of columns."""

    @property
    def height(self) -> int:
        """The number of rows."""

    @property
    def position(self) -> Point:
        """The top-left corner."""

    @property
    def size(self) -> Size:
        """The width and height."""

    @property
    def area(self) -> int:
        """The number of cells, ``width * height``."""

    @property
    def is_empty(self) -> bool:
        """Whether the rectangle holds no cells."""

    def contains(self, point: Point) -> bool:
        """
        Whether ``point`` lies inside the rectangle.

        Examples:
            ```python
            area = Rectangle(0, 0, 4, 2)
            assert area.contains(Point(3, 1))
            assert not area.contains(Point(4, 1))
            ```
        """

    def intersects(self, other: Rectangle) -> bool:
        """
        Whether the two rectangles share at least one cell.

        Examples:
            ```python
            assert Rectangle(0, 0, 4, 4).intersects(Rectangle(3, 3, 4, 4))
            assert not Rectangle(0, 0, 4, 4).intersects(Rectangle(4, 0, 4, 4))
            ```
        """

    def intersection(self, other: Rectangle) -> Rectangle:
        """
        The cells both rectangles share. The result is empty when they do not overlap.

        Examples:
            ```python
            shared = Rectangle(0, 0, 10, 5).intersection(Rectangle(5, 2, 10, 10))
            assert shared == Rectangle(5, 2, 5, 3)
            ```
        """

    def union(self, other: Rectangle) -> Rectangle:
        """
        The smallest rectangle that holds both rectangles.

        Examples:
            ```python
            joined = Rectangle(0, 0, 10, 5).union(Rectangle(8, 8, 4, 4))
            assert joined == Rectangle(0, 0, 12, 12)
            ```
        """

    def translate(self, horizontal: int = 0, vertical: int = 0) -> Rectangle:
        """
        Move the rectangle by a number of columns and rows.

        Examples:
            ```python
            assert Rectangle(0, 0, 4, 2).translate(2, 1) == Rectangle(2, 1, 4, 2)
            ```
        """

    def inset(self, horizontal: int = 0, vertical: int = 0) -> Rectangle:
        """
        Shrink the rectangle by a margin on every side.

        Examples:
            ```python
            assert Rectangle(0, 0, 10, 5).inset(1, 1) == Rectangle(1, 1, 8, 3)
            ```
        """

    def __contains__(self, point: Point) -> bool: ...
    def __and__(self, other: Rectangle) -> Rectangle: ...
    def __or__(self, other: Rectangle) -> Rectangle: ...

class Color:
    """
    A terminal color: a named palette color, a palette index or a true color.

    Maps to [`ratatui::style::Color`](https://docs.rs/ratatui/0.30.0/ratatui/style/enum.Color.html).

    Args:
        value: A color name such as ``'red'`` or ``'light_blue'``, a hex string such as
            ``'#ff8800'``, a palette index string such as ``'4'``, or a
            ``(red, green, blue)`` tuple.

    Raises:
        ValueError: ``value`` is not a recognized color.

    Examples:
        ```python
        assert Color('#ff8800').to_rgb() == (255, 136, 0)
        assert Color((1, 2, 3)) == Color.from_rgb(1, 2, 3)
        assert Color('red').to_rgb() is None
        ```
    """

    def __init__(self, value: str | tuple[int, int, int]) -> None: ...
    @classmethod
    def parse(cls, value: str) -> Color:
        """
        Parse a color name, hex string or palette index string.

        Examples:
            ```python
            assert Color.parse('light_blue') == Color('light_blue')
            ```
        """

    @classmethod
    def indexed(cls, index: int) -> Color:
        """
        A color from the 256-color palette.

        Examples:
            ```python
            color = Color.indexed(202)
            assert color.to_rgb() is None
            ```
        """

    @classmethod
    def from_rgb(cls, red: int, green: int, blue: int) -> Color:
        """
        A true color from red, green and blue values between 0 and 255.

        Examples:
            ```python
            assert Color.from_rgb(255, 0, 0).to_rgb() == (255, 0, 0)
            ```
        """

    def to_rgb(self) -> tuple[int, int, int] | None:
        """
        The ``(red, green, blue)`` values of a true color, or ``None`` for named and indexed colors.

        Examples:
            ```python
            assert Color('#010203').to_rgb() == (1, 2, 3)
            assert Color.indexed(4).to_rgb() is None
            ```
        """

class Style:
    """
    A foreground color, a background color and text modifiers.

    Maps to [`ratatui::style::Style`](https://docs.rs/ratatui/0.30.0/ratatui/style/struct.Style.html).

    Args:
        foreground: The text color.
        background: The cell background color.
        bold: Whether text is bold.
        dim: Whether text is dimmed.
        italic: Whether text is italic.
        underline: Whether text is underlined.
        blink: Whether text blinks.
        reverse: Whether foreground and background swap.
        hidden: Whether text is hidden.
        crossed_out: Whether text is struck through.

    Examples:
        ```python
        style = Style('red', 'black', bold=True)
        assert style.foreground == Color('red')
        assert 'bold' in style.modifiers
        ```
    """

    def __init__(
        self,
        foreground: ColorValue | None = None,
        background: ColorValue | None = None,
        *,
        bold: bool = False,
        dim: bool = False,
        italic: bool = False,
        underline: bool = False,
        blink: bool = False,
        reverse: bool = False,
        hidden: bool = False,
        crossed_out: bool = False,
    ) -> None: ...
    @property
    def foreground(self) -> Color | None:
        """The text color, or ``None`` when unset."""

    @property
    def background(self) -> Color | None:
        """The background color, or ``None`` when unset."""

    @property
    def modifiers(self) -> frozenset[Modifier]:
        """The enabled text modifiers."""

    def patch(self, other: Style) -> Style:
        """
        A style where every value ``other`` sets replaces this style's value.

        Examples:
            ```python
            base = Style('red', bold=True)
            patched = base.patch(Style(italic=True))
            assert patched.foreground == Color('red')
            assert patched.modifiers == {'bold', 'italic'}
            ```
        """

    def __or__(self, other: Style) -> Style: ...

class Clock:
    """
    The time source a runtime reads, either real or manually advanced.

    A monotonic clock follows real time, so wall-clock adjustments never affect it. A
    manual clock moves only when you advance it, which makes tests and replays exact.

    Examples:
        ```python
        clock = Clock.manual()
        clock.advance(1500)
        assert clock.elapsed_seconds == 1.5
        assert clock.source == 'manual'
        ```
    """

    @classmethod
    def monotonic(cls) -> Clock:
        """
        A clock that follows real elapsed time.

        Examples:
            ```python
            clock = Clock.monotonic()
            assert clock.source == 'monotonic'
            ```
        """

    @classmethod
    def manual(cls, *, elapsed_seconds: float = 0.0) -> Clock:
        """
        A clock that moves only through [`advance`][xnano._xnano_core.Clock.advance].

        Args:
            elapsed_seconds: The time the clock starts at.

        Examples:
            ```python
            clock = Clock.manual(elapsed_seconds=2.0)
            assert clock.elapsed_milliseconds == 2000.0
            ```
        """

    @property
    def source(self) -> Literal['monotonic', 'manual']:
        """Whether the clock follows real time or is advanced by hand."""

    @property
    def elapsed_seconds(self) -> float:
        """Seconds since the clock started."""

    @property
    def elapsed_milliseconds(self) -> float:
        """Milliseconds since the clock started."""

    @property
    def delta_seconds(self) -> float:
        """Seconds between the two most recent frames."""

    @property
    def delta_milliseconds(self) -> float:
        """Milliseconds between the two most recent frames."""

    @property
    def frame(self) -> int:
        """The number of frames the clock has counted."""

    @property
    def frames_per_second(self) -> float:
        """The frame rate measured over recent frames."""

    @property
    def is_paused(self) -> bool:
        """Whether the clock is paused."""

    def pause(self) -> None:
        """
        Stop time from advancing.

        Examples:
            ```python
            clock = Clock.manual()
            clock.pause()
            assert clock.is_paused
            ```
        """

    def resume(self) -> None:
        """
        Let time advance again after a pause.

        Examples:
            ```python
            clock = Clock.manual()
            clock.pause()
            clock.resume()
            assert not clock.is_paused
            ```
        """

    def advance(self, milliseconds: int) -> None:
        """
        Move a manual clock forward.

        Args:
            milliseconds: How far to move, zero or more.

        Raises:
            ValueError: The clock is monotonic, or ``milliseconds`` is negative.

        Examples:
            ```python
            clock = Clock.manual()
            clock.advance(250)
            assert clock.elapsed_milliseconds == 250.0
            ```
        """

    def derive(self, *, rate: float = 1.0, paused: bool = False) -> SimulationClock:
        """
        Create a clock that follows this one at a different speed.

        Args:
            rate: How fast the new clock runs compared to this one. Zero or more.
            paused: Whether the new clock starts paused.

        Examples:
            ```python
            clock = Clock.manual()
            slow_motion = clock.derive(rate=0.5)
            assert slow_motion.rate == 0.5
            assert slow_motion.parent.source == 'manual'
            ```
        """

class SimulationClock:
    """
    A clock derived from a parent clock, with its own rate and pause state.

    Changing the rate keeps elapsed time continuous. Rates are finite and nonnegative.

    Examples:
        ```python
        simulation = Clock.manual().derive(rate=1.0)
        simulation.rate = 2.0
        simulation.paused = True
        assert simulation.rate == 2.0
        assert simulation.paused
        ```
    """

    @property
    def parent(self) -> Clock:
        """The clock this clock follows."""

    @property
    def rate(self) -> float:
        """How fast this clock runs compared to its parent. Assign to change it."""

    @rate.setter
    def rate(self, value: float) -> None: ...
    @property
    def paused(self) -> bool:
        """Whether this clock is paused. Assign to pause or resume it."""

    @paused.setter
    def paused(self, value: bool) -> None: ...
    @property
    def elapsed_seconds(self) -> float:
        """Seconds of simulation time."""

    @property
    def delta_seconds(self) -> float:
        """Seconds of simulation time between the two most recent calls to ``sample``."""

    def sample(self) -> None:
        """
        Record the current elapsed time so ``delta_seconds`` reports time since this sample.

        Call once for each simulation frame whose elapsed time you want to measure.

        Examples:
            ```python
            parent = Clock.manual()
            simulation = parent.derive(rate=2.0)
            simulation.sample()
            parent.advance(100)
            simulation.sample()
            assert simulation.delta_seconds == 0.2
            ```
        """

    def pause(self) -> None:
        """
        Pause this clock without affecting its parent.

        Examples:
            ```python
            simulation = Clock.manual().derive()
            simulation.pause()
            assert simulation.paused
            ```
        """

    def resume(self) -> None:
        """
        Resume this clock after a pause.

        Examples:
            ```python
            simulation = Clock.manual().derive(paused=True)
            simulation.resume()
            assert not simulation.paused
            ```
        """

class TextSpan:
    """
    A run of text with one style.

    Maps to [`ratatui::text::Span`](https://docs.rs/ratatui/0.30.0/ratatui/text/struct.Span.html).

    Args:
        text: The text.
        style: The style of the whole run.

    Examples:
        ```python
        span = TextSpan('warning', style=Style('yellow', bold=True))
        assert span.text == 'warning'
        assert 'bold' in span.style.modifiers
        ```
    """

    def __init__(self, text: str, *, style: Style | None = None) -> None: ...
    @property
    def text(self) -> str:
        """The text of the run."""

    @property
    def style(self) -> Style:
        """The style of the run."""

class StyledText:
    """
    Text made of differently styled spans.

    Args:
        spans: The runs of text, in order.

    Examples:
        ```python
        text = StyledText([TextSpan('error: ', style=Style('red')), TextSpan('disk full')])
        assert str(text) == 'error: disk full'
        assert len(text.spans) == 2
        ```
    """

    def __init__(self, spans: Sequence[TextSpan]) -> None: ...
    @property
    def spans(self) -> tuple[TextSpan, ...]:
        """The runs of text, in order."""

    def __str__(self) -> str:
        """
        The text without styles.

        Examples:
            ```python
            assert str(StyledText([TextSpan('a'), TextSpan('b')])) == 'ab'
            ```
        """

    def __add__(self, other: str | TextSpan | StyledText) -> StyledText: ...

class TextLine:
    """
    One wrapped line of a [`TextLayout`][xnano._xnano_core.TextLayout].

    Examples:
        ```python
        layout = layout_text('hello world', width=6)
        line = layout.lines[0]
        assert line.text == 'hello '
        assert (line.start_offset, line.end_offset, line.width) == (0, 6, 6)
        ```
    """

    @property
    def text(self) -> str:
        """The text of the line."""

    @property
    def start_offset(self) -> int:
        """Where the line starts in the original text, counted in Python string offsets."""

    @property
    def end_offset(self) -> int:
        """Where the line ends in the original text, counted in Python string offsets."""

    @property
    def width(self) -> int:
        """The number of cells the line occupies."""

class TextLayout:
    """
    Text wrapped to a width, with conversions between cells and string offsets.

    Cell positions and Python string offsets agree at grapheme boundaries.

    Examples:
        ```python
        layout = layout_text('hello world foo', width=8, cursor_offset=3)
        assert [line.text for line in layout.lines] == ['hello ', 'world ', 'foo']
        assert layout.cursor_cell == (3, 0)
        ```
    """

    @property
    def lines(self) -> tuple[TextLine, ...]:
        """The wrapped lines."""

    @property
    def cursor_cell(self) -> tuple[int, int] | None:
        """The ``(column, row)`` of the cursor, or ``None`` when no cursor was given."""

    def text_offset_at(self, column: int, row: int) -> int:
        """
        The string offset under a cell.

        Examples:
            ```python
            layout = layout_text('hello world', width=6)
            assert layout.text_offset_at(2, 1) == 8
            ```
        """

    def cell_at_text_offset(self, offset: int) -> tuple[int, int]:
        """
        The ``(column, row)`` of a string offset.

        Examples:
            ```python
            layout = layout_text('hello world', width=6)
            assert layout.cell_at_text_offset(8) == (2, 1)
            ```
        """

class TextEditor:
    """
    An editable text buffer with a cursor and undo history.

    Draw it with [`Editor`][xnano._xnano_core.Editor].

    Args:
        text: The starting text.
        is_single_line: Whether line breaks are refused.

    Examples:
        ```python
        editor = TextEditor('abc')
        editor.move_cursor(3)
        editor.insert_text('d')
        assert editor.text == 'abcd'
        assert editor.undo()
        assert editor.text == 'abc'
        ```
    """

    def __init__(self, text: str = '', *, is_single_line: bool = False) -> None: ...
    @property
    def text(self) -> str:
        """The current text."""

    @property
    def is_single_line(self) -> bool:
        """Whether line breaks are refused."""

    @property
    def cursor_offset(self) -> int:
        """The cursor position, counted in Python string offsets."""

    @property
    def placeholder_text(self) -> str:
        """The text shown while the editor is empty. Assign to change it."""

    @placeholder_text.setter
    def placeholder_text(self, value: str) -> None: ...
    def set_text(self, text: str) -> None:
        """
        Replace all text.

        Examples:
            ```python
            editor = TextEditor('old')
            editor.set_text('new')
            assert editor.text == 'new'
            ```
        """

    def insert_text(self, text: str) -> None:
        """
        Insert text at the cursor.

        Examples:
            ```python
            editor = TextEditor('ac')
            editor.move_cursor(1)
            editor.insert_text('b')
            assert editor.text == 'abc'
            ```
        """

    def handle_key(self, key: KeyEvent) -> bool:
        """
        Apply a key press to the text and cursor.

        Args:
            key: The key event.

        Returns:
            Whether the editor used the key.

        Examples:
            ```python
            editor = TextEditor()
            assert editor.handle_key(Event.key_press('x').key)
            assert editor.text == 'x'
            ```
        """

    def move_cursor(self, offset: int) -> None:
        """
        Move the cursor to a string offset.

        Examples:
            ```python
            editor = TextEditor('hello')
            editor.move_cursor(2)
            assert editor.cursor_offset == 2
            ```
        """

    def undo(self) -> bool:
        """
        Undo the most recent edit.

        Returns:
            Whether there was an edit to undo.

        Examples:
            ```python
            editor = TextEditor('a')
            editor.insert_text('b')
            assert editor.undo()
            assert not TextEditor().undo()
            ```
        """

    def redo(self) -> bool:
        """
        Redo the most recently undone edit.

        Returns:
            Whether there was an edit to redo.

        Examples:
            ```python
            editor = TextEditor('a')
            editor.insert_text('b')
            editor.undo()
            assert editor.redo()
            assert editor.text == 'ab'
            ```
        """

    def layout(self, *, width: int, should_wrap: bool = True) -> TextLayout:
        """
        Wrap the text to a width and locate the cursor.

        Examples:
            ```python
            editor = TextEditor('hello world')
            layout = editor.layout(width=6)
            assert len(layout.lines) == 2
            ```
        """

def layout_text(
    text: str, *, width: int, cursor_offset: int | None = None, should_wrap: bool = True
) -> TextLayout:
    """
    Wrap text to a width.

    Args:
        text: The text to wrap.
        width: The number of columns available.
        cursor_offset: A string offset to locate in the result.
        should_wrap: Whether lines longer than ``width`` wrap onto new rows.

    Returns:
        The wrapped lines and, when ``cursor_offset`` is given, the cursor cell.

    Examples:
        ```python
        layout = layout_text('hello world', width=6, cursor_offset=7)
        assert [line.text for line in layout.lines] == ['hello ', 'world']
        assert layout.cursor_cell == (1, 1)
        ```
    """

def display_width(text: str) -> int:
    """
    The number of terminal cells a string occupies.

    Wide characters such as CJK ideographs take two cells.

    Examples:
        ```python
        assert display_width('abc') == 3
        assert display_width('日本') == 4
        ```
    """

class Editor(Operation):
    """
    Draw a [`TextEditor`][xnano._xnano_core.TextEditor] into a buffer.

    Args:
        editor: The editor to draw.
        area: The region to draw into. Defaults to the whole target.
        style: The style of the text.
        first_row: The first wrapped row to show, for scrolling.
        should_wrap: Whether long lines wrap.
        should_show_cursor: Whether the cursor cell is highlighted.
        mode: How text treats the background already in the cells.

    Examples:
        ```python
        editor = TextEditor('hi')
        buffer = Buffer(width=5, height=1)
        buffer.update(Editor(editor, area=Rectangle(0, 0, 5, 1)))
        assert buffer.text.startswith('hi')
        ```
    """

    def __init__(
        self,
        editor: TextEditor,
        *,
        area: Rectangle | None = None,
        style: Style | None = None,
        first_row: int = 0,
        should_wrap: bool = True,
        should_show_cursor: bool = True,
        mode: WriteMode = 'preserve_background',
    ) -> None: ...

class KeyEvent:
    """
    A key press, repeat or release.

    Get one from [`Event.key`][xnano._xnano_core.Event.key] or build an event with
    [`Event.key_press`][xnano._xnano_core.Event.key_press].

    Examples:
        ```python
        key = Event.key_press('ctrl+c').key
        assert key.key == 'c'
        assert key.modifiers == {'control'}
        assert key.matches('ctrl+c')
        ```
    """

    @property
    def key(self) -> str:
        """The key name, such as ``'a'``, ``'enter'`` or ``'page_up'``."""

    @property
    def text(self) -> str | None:
        """The text the key types, or ``None`` for control keys and chords."""

    @property
    def modifiers(self) -> frozenset[KeyModifier]:
        """The modifier keys held."""

    @property
    def kind(self) -> KeyEventKind:
        """Whether the key was pressed, repeated or released."""

    def matches(self, binding: str | KeyBinding) -> bool:
        """
        Whether this event is the key and modifiers of ``binding``.

        Examples:
            ```python
            key = Event.key_press('shift+tab').key
            assert key.matches('shift+tab')
            assert not key.matches('tab')
            ```
        """

class MouseEvent:
    """
    A mouse press, release, drag, move or scroll.

    Examples:
        ```python
        mouse = Event.mouse_event(column=4, row=2, kind='press', button='left').mouse
        assert (mouse.column, mouse.row) == (4, 2)
        assert mouse.button == 'left'
        ```
    """

    @property
    def position(self) -> Point:
        """The cell under the pointer."""

    @property
    def column(self) -> int:
        """The column under the pointer."""

    @property
    def row(self) -> int:
        """The row under the pointer."""

    @property
    def kind(self) -> MouseEventKind:
        """What the mouse did."""

    @property
    def button(self) -> MouseButton | None:
        """The button involved, or ``None`` for moves and scrolls."""

    @property
    def scroll_horizontal(self) -> int:
        """Horizontal scroll steps, negative for left."""

    @property
    def scroll_vertical(self) -> int:
        """Vertical scroll steps, negative for up."""

class Event:
    """
    Something that happened: input, a resize, a timer or a frame.

    Hooks and the runtime report everything as an event. Build events with the class
    methods to test code without a terminal.

    Examples:
        ```python
        event = Event.key_press('q')
        assert event.kind == 'key'
        assert event.key.key == 'q'
        assert Event.resize(width=80, height=24).size == Size(80, 24)
        ```
    """

    @property
    def kind(self) -> EventKind:
        """What the event reports."""

    @property
    def timestamp_seconds(self) -> float:
        """Seconds on the runtime clock when the event happened."""

    @property
    def key(self) -> KeyEvent | None:
        """The key details of a key event, otherwise ``None``."""

    @property
    def mouse(self) -> MouseEvent | None:
        """The mouse details of a mouse event, otherwise ``None``."""

    @property
    def pasted_text(self) -> str | None:
        """The pasted text of a paste event, otherwise ``None``."""

    @property
    def size(self) -> Size | None:
        """The new size of a resize event, otherwise ``None``."""

    @property
    def timer_key(self) -> str | None:
        """The key of a timer event, otherwise ``None``."""

    @classmethod
    def key_press(cls, binding: str, *, kind: KeyEventKind = 'press') -> Event:
        """
        A key event for a key name with optional ``+``-joined modifiers.

        Args:
            binding: The key, such as ``'q'``, ``'enter'`` or ``'ctrl+c'``.
            kind: Whether the key is pressed, repeated or released.

        Raises:
            ValueError: ``binding`` is not a valid key or ``kind`` is unknown.

        Examples:
            ```python
            event = Event.key_press('alt+enter')
            assert event.key.key == 'enter'
            assert event.key.modifiers == {'alt'}
            ```
        """

    @classmethod
    def paste(cls, text: str) -> Event:
        """
        A paste event.

        Examples:
            ```python
            assert Event.paste('hello').pasted_text == 'hello'
            ```
        """

    @classmethod
    def resize(cls, *, width: int, height: int) -> Event:
        """
        A resize event.

        Examples:
            ```python
            assert Event.resize(width=3, height=2).size.height == 2
            ```
        """

    @classmethod
    def mouse_event(
        cls,
        *,
        column: int,
        row: int,
        kind: MouseEventKind,
        button: MouseButton | None = None,
        scroll_horizontal: int = 0,
        scroll_vertical: int = 0,
    ) -> Event:
        """
        A mouse event.

        Args:
            column: The column under the pointer.
            row: The row under the pointer.
            kind: What the mouse did.
            button: The button involved in a press, release or drag.
            scroll_horizontal: Horizontal scroll steps.
            scroll_vertical: Vertical scroll steps.

        Examples:
            ```python
            event = Event.mouse_event(column=0, row=0, kind='scroll', scroll_vertical=-1)
            assert event.mouse.scroll_vertical == -1
            ```
        """

    @classmethod
    def focus_gained(cls) -> Event:
        """
        An event reporting that the terminal window gained focus.

        Examples:
            ```python
            assert Event.focus_gained().kind == 'focus_gained'
            ```
        """

    @classmethod
    def focus_lost(cls) -> Event:
        """
        An event reporting that the terminal window lost focus.

        Examples:
            ```python
            assert Event.focus_lost().kind == 'focus_lost'
            ```
        """

class KeyBinding:
    """
    A key and modifiers to match against key events.

    Examples:
        ```python
        binding = KeyBinding.parse('ctrl+q')
        assert binding.matches(Event.key_press('ctrl+q'))
        assert not binding.matches(Event.key_press('q'))
        ```
    """

    @classmethod
    def parse(cls, binding: str) -> KeyBinding:
        """
        Parse text such as ``'q'``, ``'ctrl+c'``, ``'shift+tab'`` or ``'alt+enter'``.

        Raises:
            ValueError: ``binding`` is empty or names an unknown key or modifier.

        Examples:
            ```python
            assert KeyBinding.parse('ctrl+shift+z').matches(Event.key_press('ctrl+shift+z'))
            ```
        """

    def matches(self, event: Event | KeyEvent) -> bool:
        """
        Whether ``event`` is this key with exactly these modifiers.

        Examples:
            ```python
            assert KeyBinding.parse('enter').matches(Event.key_press('enter'))
            ```
        """

class EventStream:
    """
    The events a runtime reports, as an iterator.

    Get one from [`Runtime.events`][xnano._xnano_core.Runtime.events]. Iterate it
    synchronously with ``for`` or asynchronously with ``async for``.

    Examples:
        ```python
        with Runtime.offscreen(width=10, height=3) as runtime:
            runtime.mount(Buffer(), geometry='inherit')
            stream = runtime.events()
            runtime.inject(Event.key_press('q'))
            runtime.step()
            assert next(stream).key.key == 'q'
        ```
    """

    def _poll(self) -> Event | None: ...
    @property
    def _runtime(self) -> Runtime: ...
    def __iter__(self) -> Iterator[Event]: ...
    def __next__(self) -> Event: ...
    def __aiter__(self) -> EventStream: ...
    def __anext__(self) -> Awaitable[Event]: ...

class Waker:
    """
    A handle other threads use to wake a runtime and run code on its thread.

    Get one from [`Runtime.waker`][xnano._xnano_core.Runtime.waker]. It is the only
    object besides ``call_soon_threadsafe`` that is safe to use from another thread.

    Examples:
        ```python
        calls = []
        with Runtime.offscreen(width=10, height=3) as runtime:
            waker = runtime.waker()
            waker.call_soon(calls.append, 'woken')
            runtime.step()
        assert calls == ['woken']
        ```
    """

    def call_soon(self, callback: Callable[..., object], *arguments: object) -> None:
        """
        Run ``callback`` with ``arguments`` on the runtime's thread at its next step.

        Examples:
            ```python
            results = []
            with Runtime.offscreen(width=10, height=3) as runtime:
                runtime.waker().call_soon(results.append, 1)
                runtime.step()
            assert results == [1]
            ```
        """

    def wake(self) -> None:
        """
        Wake the runtime so its next step does not wait.

        Examples:
            ```python
            with Runtime.offscreen(width=10, height=3) as runtime:
                runtime.waker().wake()
            ```
        """

class Hook:
    """
    A registered callback that can be paused, reprioritized or cancelled.

    Higher priorities run first, and ties keep registration order. Register hooks with
    [`Surface.add_hook`][xnano._xnano_core.Surface.add_hook].

    Examples:
        ```python
        seen = []
        with Runtime.offscreen(width=10, height=3) as runtime:
            buffer = Buffer()
            runtime.mount(buffer, geometry='inherit')
            hook = buffer.add_hook(lambda context: seen.append('key'), events=('key',))
            runtime.inject(Event.key_press('a'))
            runtime.step()
            hook.enabled = False
            runtime.inject(Event.key_press('b'))
            runtime.step()
            hook.cancel()
        assert seen == ['key']
        assert hook.is_cancelled
        ```
    """

    @classmethod
    def _detached(cls, cancel: Callable[[], None] | None = None) -> Hook: ...
    @property
    def enabled(self) -> bool:
        """Whether the hook runs. Assign ``False`` to pause it and ``True`` to resume."""

    @enabled.setter
    def enabled(self, value: bool) -> None: ...
    @property
    def priority(self) -> int:
        """The hook's priority."""

    @property
    def is_cancelled(self) -> bool:
        """Whether the hook was cancelled."""

    def cancel(self) -> None:
        """
        Remove the hook permanently.

        Examples:
            ```python
            buffer = Buffer()
            hook = buffer.add_hook(lambda context: None)
            hook.cancel()
            assert hook.is_cancelled
            ```
        """

class ScheduledCall:
    """
    A callback scheduled on a clock with ``call_later`` or ``call_every``.

    Examples:
        ```python
        calls = []
        with Runtime.offscreen(width=10, height=3) as runtime:
            scheduled = runtime.call_later(1.0, lambda: calls.append('done'))
            runtime.advance_clock(1000)
            runtime.step()
        assert calls == ['done']
        assert not scheduled.is_cancelled
        ```
    """

    @property
    def is_cancelled(self) -> bool:
        """Whether the call was cancelled."""

    def cancel(self) -> None:
        """
        Stop the call from running.

        Examples:
            ```python
            with Runtime.offscreen(width=10, height=3) as runtime:
                scheduled = runtime.call_later(5.0, lambda: None)
                scheduled.cancel()
                assert scheduled.is_cancelled
            ```
        """

class KeyboardCapabilities:
    """
    What the terminal's keyboard protocol can report.

    Examples:
        ```python
        with Runtime.offscreen(width=10, height=3) as runtime:
            capabilities = runtime.device.keyboard
            assert capabilities.enhancement in ('supported', 'unsupported', 'unknown')
        ```
    """

    @property
    def enhancement(self) -> CapabilityStatus:
        """Whether the enhanced keyboard protocol is available."""

    @property
    def disambiguates_keys(self) -> bool:
        """Whether keys such as ``escape`` and ``alt+key`` are told apart."""

    @property
    def reports_event_types(self) -> bool:
        """Whether key repeats and releases are reported."""

    @property
    def reports_all_keys(self) -> bool:
        """Whether modifier keys on their own are reported."""

    @property
    def unavailable_reason(self) -> str | None:
        """Why the enhanced protocol is unavailable, or ``None``."""

    @property
    def enabled_features(
        self,
    ) -> frozenset[Literal['disambiguate', 'event_types', 'all_keys']]:
        """The protocol features that are switched on."""

def query_keyboard_capabilities(
    *, timeout_milliseconds: int = 200
) -> KeyboardCapabilities:
    """
    Ask the terminal which keyboard protocol features it supports.

    Returns an ``'unknown'`` status when the terminal does not answer. Querying alone
    enables no reporting mode.

    Args:
        timeout_milliseconds: How long to wait for an answer.

    Examples:
        ```python
        capabilities = query_keyboard_capabilities(timeout_milliseconds=10)
        assert capabilities.enhancement in ('supported', 'unsupported', 'unknown')
        ```
    """

class InputOptions:
    """
    The input modes a live terminal asks for.

    Requested modes are negotiated with the terminal and restored when the runtime closes.

    Args:
        mouse: ``'off'``, ``'buttons'`` for clicks and drags, or ``'motion'`` for all movement.
        bracketed_paste: Whether pasted text arrives as one paste event.
        focus_reporting: Whether the terminal reports focus changes.
        keyboard: ``'basic'``, ``'disambiguated'`` or ``'release_events'``.
        capability_timeout_milliseconds: How long to wait for capability answers.
        interrupt: Whether Ctrl+C becomes an ``'event'`` or ``'stop'`` the runtime.

    Raises:
        ValueError: A mode is not one of the listed values.

    Examples:
        ```python
        options = InputOptions(mouse='buttons', keyboard='release_events')
        assert options.mouse == 'buttons'
        terminal = TerminalOptions(input=options)
        ```
    """

    def __init__(
        self,
        *,
        mouse: Literal['off', 'buttons', 'motion'] = 'off',
        bracketed_paste: bool = True,
        focus_reporting: bool = True,
        keyboard: Literal['basic', 'disambiguated', 'release_events'] = 'basic',
        capability_timeout_milliseconds: int = 200,
        interrupt: Literal['event', 'stop'] = 'event',
    ) -> None: ...
    @property
    def mouse(self) -> Literal['off', 'buttons', 'motion']:
        """The requested mouse mode."""

    @property
    def bracketed_paste(self) -> bool:
        """Whether bracketed paste is requested."""

    @property
    def focus_reporting(self) -> bool:
        """Whether focus reporting is requested."""

    @property
    def keyboard(self) -> Literal['basic', 'disambiguated', 'release_events']:
        """The requested keyboard mode."""

    @property
    def capability_timeout_milliseconds(self) -> int:
        """How long capability queries wait."""

    @property
    def interrupt(self) -> Literal['event', 'stop']:
        """How Ctrl+C is handled."""

class TerminalOptions:
    """
    How a live runtime takes over the terminal.

    Args:
        input: The input modes to request.
        alternate_screen: Whether to draw on the alternate screen.
        raw_mode: Whether to put the terminal in raw mode.
        drain_reports_on_exit: Whether to discard pending terminal replies on exit.
        drain_timeout_milliseconds: How long to wait while discarding replies.

    Examples:
        ```python
        options = TerminalOptions(alternate_screen=False)
        assert options.raw_mode
        assert not options.alternate_screen
        ```
    """

    def __init__(
        self,
        *,
        input: InputOptions | None = None,
        alternate_screen: bool = True,
        raw_mode: bool = True,
        drain_reports_on_exit: bool = True,
        drain_timeout_milliseconds: int = 250,
    ) -> None: ...
    @property
    def input(self) -> InputOptions:
        """The requested input modes."""

    @property
    def alternate_screen(self) -> bool:
        """Whether the alternate screen is used."""

    @property
    def raw_mode(self) -> bool:
        """Whether raw mode is used."""

    @property
    def drain_reports_on_exit(self) -> bool:
        """Whether pending terminal replies are discarded on exit."""

    @property
    def drain_timeout_milliseconds(self) -> int:
        """How long discarding replies may take."""

class InputState:
    """
    The keys and pointer position a runtime currently sees.

    Reliable pressed keys require negotiated release reporting. In reliable mode keys are
    cleared on focus loss, unmount and shutdown. When release reporting is unavailable,
    ``pressed_keys`` is empty and the opt-in timeout estimates appear in
    ``estimated_pressed_keys`` instead, so an estimate never passes as a real held key.

    Examples:
        ```python
        with Runtime.offscreen(width=10, height=3) as runtime:
            state = runtime.input
            assert state.pressed_keys == frozenset()
            assert state.pointer_cell is None
        ```
    """

    @property
    def held_keys_available(self) -> bool:
        """Whether the terminal reports key releases."""

    @property
    def pressed_keys(self) -> frozenset[str]:
        """The keys currently held, when releases are reported."""

    @property
    def estimated_pressed_keys(self) -> frozenset[str]:
        """The keys guessed to be held from a timeout, when estimates are enabled."""

    @property
    def pointer_cell(self) -> tuple[int, int] | None:
        """The ``(column, row)`` under the pointer, or ``None``."""

    def estimate_holds(self, *, timeout_seconds: float | None = None) -> None:
        """
        Guess held keys from key repeats when releases are not reported.

        Args:
            timeout_seconds: How long after the last repeat a key counts as held. Positive.
                ``None`` turns estimates off. The timeout cannot account for the operating
                system's initial repeat delay.

        Examples:
            ```python
            with Runtime.offscreen(width=10, height=3) as runtime:
                runtime.input.estimate_holds(timeout_seconds=0.5)
                runtime.input.estimate_holds(timeout_seconds=None)
            ```
        """

class Device:
    """
    The display and terminal a runtime draws on.

    Examples:
        ```python
        with Runtime.offscreen(width=40, height=10) as runtime:
            device = runtime.device
            assert device.backend == 'offscreen'
            assert device.size == Size(40, 10)
        ```
    """

    @property
    def backend(self) -> Literal['terminal', 'offscreen']:
        """Whether output goes to a real terminal or an in-memory screen."""

    @property
    def size(self) -> Size:
        """The size of the display in cells."""

    @property
    def window_size_in_pixels(self) -> Size | None:
        """The size of the window in pixels, or ``None`` when unknown."""

    @property
    def capabilities(self) -> TerminalCapabilities:
        """What the terminal can display."""

    @property
    def keyboard(self) -> KeyboardCapabilities:
        """What the keyboard protocol can report."""

    @property
    def is_focused(self) -> bool:
        """Whether the terminal window has focus."""

    @property
    def is_inline(self) -> bool:
        """Whether the runtime draws inline instead of taking the whole screen."""

    @property
    def is_raw_mode_enabled(self) -> bool:
        """Whether raw mode is on."""

    @property
    def is_mouse_capture_enabled(self) -> bool:
        """Whether mouse capture is on."""

    @property
    def is_bracketed_paste_enabled(self) -> bool:
        """Whether bracketed paste is on."""

    @property
    def is_focus_reporting_enabled(self) -> bool:
        """Whether focus reporting is on."""

    @property
    def is_alternate_screen_enabled(self) -> bool:
        """Whether the alternate screen is on."""

class HitArea:
    """
    A named rectangle that receives mouse hits without needing painted text.

    Create one with [`InputRouter.hit_area`][xnano._xnano_core.InputRouter.hit_area].

    Examples:
        ```python
        with Runtime.offscreen(width=20, height=5) as runtime:
            buffer = Buffer()
            runtime.mount(buffer, geometry='inherit')
            area = runtime.router.hit_area('button', target=buffer, bounds=Rectangle(2, 1, 4, 2))
            assert area.key == 'button'
            area.bounds = Rectangle(0, 0, 2, 2)
            area.remove()
        ```
    """

    @property
    def key(self) -> str:
        """The name the hit area was registered with."""

    @property
    def bounds(self) -> Rectangle:
        """The rectangle, relative to the target. Assign to move or resize it."""

    @bounds.setter
    def bounds(self, value: Rectangle) -> None: ...
    def remove(self) -> None:
        """
        Unregister the hit area.

        Examples:
            ```python
            with Runtime.offscreen(width=20, height=5) as runtime:
                buffer = Buffer()
                runtime.mount(buffer, geometry='inherit')
                area = runtime.router.hit_area('x', target=buffer, bounds=Rectangle(0, 0, 2, 2))
                area.remove()
                assert runtime.router.hit_test(0, 0) == ()
            ```
        """

class FocusScope:
    """
    A group of input targets, optionally modal.

    Modal scopes receive input first. Scopes change routing only, never application state.
    Use it as a context manager to close it automatically.

    Examples:
        ```python
        with Runtime.offscreen(width=20, height=5) as runtime:
            dialog = Buffer(width=10, height=3)
            runtime.mount(dialog)
            with runtime.router.scope(dialog, modal=True) as scope:
                assert scope.is_active
            assert not scope.is_active
        ```
    """

    @property
    def is_active(self) -> bool:
        """Whether the scope is open."""

    def close(self) -> None:
        """
        Close the scope.

        Examples:
            ```python
            with Runtime.offscreen(width=20, height=5) as runtime:
                dialog = Buffer(width=10, height=3)
                runtime.mount(dialog)
                scope = runtime.router.scope(dialog)
                scope.close()
                assert not scope.is_active
            ```
        """

    def __enter__(self) -> FocusScope: ...
    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]: ...

class InputRouter:
    """
    Routes input events to buffers: handlers, hit areas, focus and scopes.

    Get it from [`Runtime.router`][xnano._xnano_core.Runtime.router].

    Examples:
        ```python
        seen = []
        with Runtime.offscreen(width=20, height=5) as runtime:
            buffer = Buffer()
            runtime.mount(buffer, geometry='inherit')
            runtime.router.on(lambda context: seen.append(context.event.key.key), target=buffer, events=('key',))
            runtime.inject(Event.key_press('z'))
            runtime.step()
        assert seen == ['z']
        ```
    """

    def on(
        self,
        callback: Callable[[EventContext], None],
        *,
        target: Buffer | Region,
        events: Sequence[EventKind] = ('key', 'mouse', 'paste'),
        binding: KeyBinding | str | None = None,
        priority: int = 0,
    ) -> Hook:
        """
        Call ``callback`` when an event reaches ``target``.

        Args:
            callback: Called with an ``EventContext``.
            target: The buffer or region that receives the events.
            events: Which kinds of events to handle.
            binding: Only handle key events matching this binding.
            priority: Higher priorities run first.

        Returns:
            A hook to pause or cancel the handler.

        Examples:
            ```python
            with Runtime.offscreen(width=20, height=5) as runtime:
                buffer = Buffer()
                runtime.mount(buffer, geometry='inherit')
                hook = runtime.router.on(lambda context: context.consume(), target=buffer, binding='ctrl+q')
                hook.cancel()
            ```
        """

    def hit_area(
        self, key: str, *, target: Buffer | Region, bounds: Rectangle, layer: int = 0
    ) -> HitArea:
        """
        Register target-local geometry without requiring painted glyphs.

        Args:
            key: A name for the hit area.
            target: The buffer or region the bounds are relative to.
            bounds: The hit rectangle.
            layer: Higher layers are hit first.

        Examples:
            ```python
            with Runtime.offscreen(width=20, height=5) as runtime:
                buffer = Buffer()
                runtime.mount(buffer, geometry='inherit')
                runtime.router.hit_area('button', target=buffer, bounds=Rectangle(2, 1, 4, 2))
                assert runtime.router.hit_test(3, 1)[0].key == 'button'
            ```
        """

    def hit_test(self, column: int, row: int) -> tuple[HitArea, ...]:
        """
        The hit areas under a cell, topmost first.

        Examples:
            ```python
            with Runtime.offscreen(width=20, height=5) as runtime:
                assert runtime.router.hit_test(0, 0) == ()
            ```
        """

    def scope(self, target: Buffer, *, modal: bool = False) -> FocusScope:
        """
        Open a focus scope around ``target``.

        Args:
            target: The buffer whose subtree forms the scope.
            modal: Whether the scope receives input before everything else.

        Examples:
            ```python
            with Runtime.offscreen(width=20, height=5) as runtime:
                dialog = Buffer(width=10, height=3)
                runtime.mount(dialog)
                with runtime.router.scope(dialog, modal=True) as scope:
                    assert scope.is_active
            ```
        """

    def focus(self, target: Buffer) -> bool:
        """
        Give ``target`` input focus.

        Returns:
            Whether the buffer could take focus.

        Examples:
            ```python
            with Runtime.offscreen(width=20, height=5) as runtime:
                buffer = Buffer()
                runtime.mount(buffer, geometry='inherit')
                assert runtime.router.focus(buffer) in (True, False)
            ```
        """

    def clear_focus(self) -> None:
        """
        Remove input focus from every buffer.

        Examples:
            ```python
            with Runtime.offscreen(width=20, height=5) as runtime:
                runtime.router.clear_focus()
            ```
        """

class TerminalCapabilities:
    """
    What a terminal can display.

    Examples:
        ```python
        capabilities = detect_terminal_capabilities(timeout_milliseconds=10)
        assert capabilities.graphics_protocol in ('half_blocks', 'kitty', 'sixel', 'iterm2')
        ```
    """

    @property
    def is_terminal(self) -> bool:
        """Whether standard output is a terminal."""

    @property
    def is_live_terminal_available(self) -> bool:
        """Whether a live terminal runtime can run here."""

    @property
    def color_profile(
        self,
    ) -> ColorProfile:
        """How many colors the terminal displays."""

    @property
    def graphics_protocol(self) -> Literal['half_blocks', 'kitty', 'sixel', 'iterm2']:
        """The best image protocol the terminal supports."""

    @property
    def cell_size_in_pixels(self) -> tuple[int, int] | None:
        """The ``(width, height)`` of one cell in pixels, or ``None`` when unknown."""

    @property
    def synchronized_output(self) -> CapabilityStatus:
        """Whether the terminal supports synchronized output."""

def detect_terminal_capabilities(
    *, timeout_milliseconds: int = 200
) -> TerminalCapabilities:
    """
    Inspect the environment and ask the terminal what it can display.

    Args:
        timeout_milliseconds: How long to wait for the terminal's answers.

    Examples:
        ```python
        capabilities = detect_terminal_capabilities(timeout_milliseconds=10)
        assert isinstance(capabilities.is_terminal, bool)
        ```
    """

class Expression(Generic[ValueType]):
    """
    A value or action described now and evaluated later against a buffer or runtime.

    Evaluation is explicit. Using an expression where Python wants a truth value raises
    ``TypeError``; combine conditions with ``&``, ``|`` and ``~`` instead.

    Examples:
        ```python
        from xnano._xnano_core import _reference

        width = _reference('Width', 'numeric_property')
        buffer = Buffer(width=8, height=1)
        assert buffer.inspect(width + 2) == 10
        assert (width + 2).evaluate(EvaluationContext(buffer=buffer)) == 10
        ```
    """

    def evaluate(self, context: EvaluationContext) -> ValueType:
        """
        Compute the expression's value.

        Examples:
            ```python
            from xnano._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            context = EvaluationContext(buffer=Buffer(width=5, height=1))
            assert (width * 2).evaluate(context) == 10
            ```
        """

    def __bool__(self) -> NoReturn: ...

class Predicate(Expression[bool]):
    """
    A condition that evaluates to ``True`` or ``False``.

    Build predicates by comparing values, then combine them with ``&``, ``|`` and ``~``.

    Examples:
        ```python
        from xnano._xnano_core import _reference

        width = _reference('Width', 'numeric_property')
        height = _reference('Height', 'numeric_property')
        buffer = Buffer(width=8, height=2)
        assert buffer.inspect((width > 4) & (height < 3))
        assert not buffer.inspect(~(width > 4))
        ```
    """

    def __and__(self, other: Predicate) -> Predicate:
        """
        True when both predicates are true.

        Examples:
            ```python
            from xnano._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            buffer = Buffer(width=8, height=1)
            assert buffer.inspect((width > 4) & (width < 10))
            ```
        """

    def __or__(self, other: Predicate) -> Predicate:
        """
        True when either predicate is true.

        Examples:
            ```python
            from xnano._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            buffer = Buffer(width=8, height=1)
            assert buffer.inspect((width < 4) | (width > 6))
            ```
        """

    def __invert__(self) -> Predicate:
        """
        True when the predicate is false.

        Examples:
            ```python
            from xnano._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            buffer = Buffer(width=8, height=1)
            assert buffer.inspect(~(width < 4))
            ```
        """

class Value(Expression[ValueType]):
    """
    An expression that evaluates to a value.

    Use ``eq`` and ``ne`` for symbolic equality; ``==`` stays ordinary Python equality.

    Examples:
        ```python
        from xnano._xnano_core import _reference

        bounds = _reference('Bounds', 'value')
        assert isinstance(bounds, Value)
        buffer = Buffer(width=4, height=1)
        assert buffer.inspect(bounds.eq(Rectangle(0, 0, 4, 1)))
        ```
    """

    def eq(self, other: ValueType | Value[ValueType]) -> Predicate:
        """
        A predicate that is true when the value equals ``other``.

        Examples:
            ```python
            from xnano._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            assert Buffer(width=20, height=1).inspect(width.eq(20))
            ```
        """

    def ne(self, other: ValueType | Value[ValueType]) -> Predicate:
        """
        A predicate that is true when the value differs from ``other``.

        Examples:
            ```python
            from xnano._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            assert Buffer(width=20, height=1).inspect(width.ne(5))
            ```
        """

class NumericValue(Value[NumberType]):
    """
    A numeric expression that supports comparisons and arithmetic.

    Arithmetic and comparisons build new expressions instead of computing right away.

    Examples:
        ```python
        from xnano._xnano_core import _reference

        width = _reference('Width', 'numeric_property')
        buffer = Buffer(width=8, height=3)
        assert buffer.inspect(width + 2) == 10
        assert buffer.inspect(10 - width) == 2
        assert buffer.inspect(width > 4)
        assert buffer.inspect(-width) == -8
        ```
    """

    def __lt__(self, other: float | NumericValue[int] | NumericValue[float]) -> Predicate:
        """
        A predicate that is true when the value is less than ``other``.

        Examples:
            ```python
            from xnano._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            assert Buffer(width=3, height=1).inspect(width < 4)
            ```
        """

    def __le__(self, other: float | NumericValue[int] | NumericValue[float]) -> Predicate:
        """
        A predicate that is true when the value is at most ``other``.

        Examples:
            ```python
            from xnano._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            assert Buffer(width=4, height=1).inspect(width <= 4)
            ```
        """

    def __gt__(self, other: float | NumericValue[int] | NumericValue[float]) -> Predicate:
        """
        A predicate that is true when the value is greater than ``other``.

        Examples:
            ```python
            from xnano._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            assert Buffer(width=5, height=1).inspect(width > 4)
            ```
        """

    def __ge__(self, other: float | NumericValue[int] | NumericValue[float]) -> Predicate:
        """
        A predicate that is true when the value is at least ``other``.

        Examples:
            ```python
            from xnano._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            assert Buffer(width=4, height=1).inspect(width >= 4)
            ```
        """

    def __add__(
        self, other: float | NumericValue[int] | NumericValue[float]
    ) -> NumericValue[float]:
        """
        The sum of the value and ``other``.

        Examples:
            ```python
            from xnano._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            assert Buffer(width=4, height=1).inspect(width + 1) == 5
            ```
        """

    def __radd__(self, other: float) -> NumericValue[float]: ...
    def __sub__(
        self, other: float | NumericValue[int] | NumericValue[float]
    ) -> NumericValue[float]:
        """
        The value minus ``other``.

        Examples:
            ```python
            from xnano._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            assert Buffer(width=4, height=1).inspect(width - 1) == 3
            ```
        """

    def __rsub__(self, other: float) -> NumericValue[float]: ...
    def __mul__(
        self, other: float | NumericValue[int] | NumericValue[float]
    ) -> NumericValue[float]:
        """
        The product of the value and ``other``.

        Examples:
            ```python
            from xnano._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            height = _reference('Height', 'numeric_property')
            assert Buffer(width=4, height=3).inspect(width * height) == 12
            ```
        """

    def __rmul__(self, other: float) -> NumericValue[float]: ...
    def __truediv__(
        self, other: float | NumericValue[int] | NumericValue[float]
    ) -> NumericValue[float]:
        """
        The value divided by ``other``.

        Examples:
            ```python
            from xnano._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            assert Buffer(width=8, height=1).inspect(width / 2) == 4.0
            ```
        """

    def __mod__(
        self, other: float | NumericValue[int] | NumericValue[float]
    ) -> NumericValue[float]:
        """
        The remainder of dividing the value by ``other``.

        Examples:
            ```python
            from xnano._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            assert Buffer(width=8, height=1).inspect(width % 3) == 2
            ```
        """

    def __neg__(self) -> NumericValue[NumberType]:
        """
        The value with its sign flipped.

        Examples:
            ```python
            from xnano._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            assert Buffer(width=8, height=1).inspect(-width) == -8
            ```
        """

class Operation(Expression[None]):
    """
    An action that changes a buffer, applied with ``Buffer.update``.

    Operations apply in argument order. ``update`` accepts operations only, not query
    expressions. Combine operations with ``then`` and ``when``.

    Examples:
        ```python
        buffer = Buffer(width=8, height=1)
        buffer.update(Write('hi'), Foreground('red'))
        assert buffer.text.startswith('hi')
        ```
    """

    def then(self, other: Operation) -> Operation:
        """
        An operation that applies this operation, then ``other``.

        Examples:
            ```python
            buffer = Buffer(width=6, height=1)
            buffer.update(Write('ab').then(Write('c', x=2)))
            assert buffer.text.startswith('abc')
            ```
        """

    def when(self, condition: Predicate) -> Operation:
        """
        An operation that applies only while ``condition`` is true.

        Examples:
            ```python
            from xnano._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            buffer = Buffer(width=6, height=1)
            buffer.update(Write('wide').when(width > 4))
            assert buffer.text.startswith('wide')
            ```
        """

class Property(Value[ValueType]):
    """
    A reference to a concrete property of a buffer or runtime.

    Reading it gives the current value. Calling it creates an assignment operation.

    Examples:
        ```python
        from xnano._xnano_core import _reference

        position = _reference('Position', 'property')
        buffer = Buffer(width=4, height=1)
        buffer.update(position(Point(3, 2)))
        assert buffer.inspect(position) == Point(3, 2)
        assert position.name == 'Position'
        ```
    """

    @property
    def name(self) -> str:
        """The name of the referenced property."""

    def __call__(self, value: ValueType | Value[ValueType]) -> SetValue[ValueType]:
        """
        An operation that assigns ``value`` to the property.

        Examples:
            ```python
            from xnano._xnano_core import _reference

            size = _reference('Size', 'property')
            buffer = Buffer(width=4, height=1)
            buffer.update(size(Size(6, 2)))
            assert buffer.width == 6
            ```
        """

class NumericProperty(NumericValue[NumberType]):
    """
    A reference to a numeric property that can be read, computed with and assigned.

    Examples:
        ```python
        from xnano._xnano_core import _reference

        width = _reference('Width', 'numeric_property')
        buffer = Buffer(width=4, height=1)
        buffer.update(width(10))
        assert buffer.width == 10
        buffer.update(width(width * 2))
        assert buffer.width == 20
        ```
    """

    @property
    def name(self) -> str:
        """The name of the referenced property."""

    def __call__(self, value: NumberType | Value[NumberType]) -> SetValue[NumberType]:
        """
        An operation that assigns ``value`` to the property.

        Examples:
            ```python
            from xnano._xnano_core import _reference

            height = _reference('Height', 'numeric_property')
            buffer = Buffer(width=4, height=1)
            buffer.update(height(3))
            assert buffer.height == 3
            ```
        """

class SetValue(Operation, Generic[ValueType]):
    """
    Assign a value to a property.

    Calling a property creates the same operation, so ``width(10)`` and
    ``SetValue(width, 10)`` are equivalent.

    Args:
        property: The property to assign.
        value: The new value, or an expression that computes it.

    Examples:
        ```python
        from xnano._xnano_core import _reference

        width = _reference('Width', 'numeric_property')
        buffer = Buffer(width=4, height=1)
        buffer.update(SetValue(width, 9))
        assert buffer.width == 9
        ```
    """

    def __init__(
        self,
        property: Property[ValueType] | NumericProperty[int] | NumericProperty[float],
        value: ValueType | Value[ValueType],
    ) -> None: ...

class SequenceOperation(Operation):
    """
    Apply several operations in order as one operation.

    Args:
        *operations: The operations to apply.

    Examples:
        ```python
        buffer = Buffer(width=6, height=1)
        buffer.update(SequenceOperation(Clear(), Write('seq')))
        assert buffer.text.startswith('seq')
        ```
    """

    def __init__(self, *operations: Operation) -> None: ...

class Conditional(Operation):
    """
    Apply one operation when a condition is true and optionally another when it is not.

    Args:
        condition: The predicate to test each time the operation applies.
        operation: Applied when the condition is true.
        otherwise: Applied when the condition is false.

    Examples:
        ```python
        from xnano._xnano_core import _reference

        width = _reference('Width', 'numeric_property')
        buffer = Buffer(width=6, height=1)
        buffer.update(Conditional(width > 100, Write('big'), otherwise=Write('small')))
        assert buffer.text.startswith('small')
        ```
    """

    def __init__(
        self,
        condition: Predicate,
        operation: Operation,
        *,
        otherwise: Operation | None = None,
    ) -> None: ...

class Resize(Operation):
    """
    Resize the target buffer to ``width`` by ``height`` cells.

    Existing content is kept where it still fits and cleared where the buffer grows.

    Args:
        width: The new width in cells.
        height: The new height in cells.

    Examples:
        ```python
        buffer = Buffer(width=10, height=3)
        buffer.update(Resize(6, 2))
        assert (buffer.width, buffer.height) == (6, 2)
        ```
    """

    def __init__(self, width: int, height: int) -> None: ...

class Move(Operation):
    """
    Move the target buffer relative to its current position in its parent.

    Args:
        horizontal: Columns to move right; negative values move left.
        vertical: Rows to move down; negative values move up.

    Examples:
        ```python
        buffer = Buffer(width=4, height=1, x=2, y=1)
        buffer.update(Move(1, 1))
        assert (buffer.x, buffer.y) == (3, 2)
        ```
    """

    def __init__(self, horizontal: int = 0, vertical: int = 0) -> None: ...

class Place(Operation):
    """
    Move the target buffer to an absolute position in its parent.

    Args:
        x: The column in the parent.
        y: The row in the parent.

    Examples:
        ```python
        buffer = Buffer(width=4, height=1)
        buffer.update(Place(5, 2))
        assert (buffer.x, buffer.y) == (5, 2)
        ```
    """

    def __init__(self, x: int, y: int) -> None: ...

class Write(Operation):
    """
    Write text into the target at a cell position.

    Text is clipped by display columns, whole graphemes are preserved and wide
    characters repair their continuation cells.

    Args:
        text: A string, a [`StyledText`][xnano._xnano_core.StyledText] or a sequence of both.
        x: The first column to write to.
        y: The row to write to.
        style: The style applied to the written cells.
        mode: ``'replace'`` overwrites the cell style; ``'preserve_background'`` keeps the
            background that is already in the cell.

    Examples:
        ```python
        buffer = Buffer(width=8, height=2)
        buffer.update(Write('hi', x=1, y=1, style=Style('red')))
        assert buffer.render(format='text').split('\\n')[1].strip() == 'hi'
        assert buffer[1, 1].foreground.to_rgb() is None
        assert str(buffer[1, 1].foreground) == "Color('red')"

        painted = Buffer(width=3, height=1)
        painted.update(Write('a', style=Style('red', 'blue')))
        painted.update(Write('b', mode='preserve_background', style=Style('green')))
        assert str(painted[0, 0].background) == "Color('blue')"
        ```
    """

    def __init__(
        self,
        text: TextContent,
        *,
        x: int = 0,
        y: int = 0,
        style: Style | None = None,
        mode: WriteMode = 'replace',
    ) -> None: ...

class WriteCellText(Write):
    """
    Write text addressed by ``column`` and ``row`` instead of ``x`` and ``y``.

    It behaves exactly like [`Write`][xnano._xnano_core.Write]; use it when the position
    is a cell index rather than a coordinate.

    Args:
        text: A string, a [`StyledText`][xnano._xnano_core.StyledText] or a sequence of both.
        column: The first column to write to.
        row: The row to write to.
        style: The style applied to the written cells.
        mode: ``'replace'`` or ``'preserve_background'``.

    Examples:
        ```python
        buffer = Buffer(width=6, height=1)
        buffer.update(WriteCellText('ab', column=2))
        assert buffer.text.strip() == 'ab'
        assert buffer[2, 0].symbol == 'a'
        ```
    """

    def __init__(
        self,
        text: TextContent,
        *,
        column: int = 0,
        row: int = 0,
        style: Style | None = None,
        mode: WriteMode = 'replace',
    ) -> None: ...

class Fill(Operation):
    """
    Fill every cell of the target with one cell.

    Args:
        cell: A [`Cell`][xnano._xnano_core.Cell] or a one-grapheme string.

    Examples:
        ```python
        buffer = Buffer(width=3, height=2)
        buffer.update(Fill('#'))
        assert buffer.text == '###\\n###'
        ```
    """

    def __init__(self, cell: Cell | str = ' ') -> None: ...

class Clear(Widget):
    """
    Blank cells that hide whatever is behind them.

    Maps to [`ratatui::widgets::Clear`](https://docs.rs/ratatui/0.30.0/ratatui/widgets/struct.Clear.html).

    Args:
        symbol: The one-column symbol every cell shows. Defaults to a space.
        style: The style of every cell.
        width: The widget's width in cells. Defaults to 10.
        height: The widget's height in cells. Defaults to 3.
        x: The column in the parent.
        y: The row in the parent.

    Raises:
        ValueError: ``symbol`` is not exactly one column wide.

    Examples:
        ```python
        clear = Clear(symbol='.', width=4, height=1)
        assert clear.render(format='text') == '....'
        clear.symbol = '#'
        assert clear.render(format='text') == '####'
        ```
    """

    def __init__(
        self,
        *,
        symbol: str | Expression[str] | None = None,
        style: Style | DynamicStyle | None = None,
        width: int | None = None,
        height: int | None = None,
        x: int = 0,
        y: int = 0,
    ) -> None: ...
    @property
    def symbol(self) -> str | Expression[str]: ...
    @symbol.setter
    def symbol(self, value: str | Expression[str]) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle: ...
    @style.setter
    def style(self, value: Style | DynamicStyle | None) -> None: ...
    def copy(self) -> Clear: ...
    def __copy__(self) -> Clear: ...
    def __deepcopy__(self, memo: Any) -> Clear: ...

class Foreground(Operation):
    """
    Set the foreground color of every cell of the target.

    Args:
        color: A [`Color`][xnano._xnano_core.Color], a color name, a hex string or an
            ``(red, green, blue)`` tuple.

    Examples:
        ```python
        buffer = Buffer(width=3, height=1)
        buffer.update(Write('abc'), Foreground('red'))
        assert str(buffer[0, 0].foreground) == "Color('red')"
        ```
    """

    def __init__(self, color: ColorValue) -> None: ...

class Background(Operation):
    """
    Set the background color of every cell of the target.

    Args:
        color: A [`Color`][xnano._xnano_core.Color], a color name, a hex string or an
            ``(red, green, blue)`` tuple.

    Examples:
        ```python
        buffer = Buffer(width=3, height=1)
        buffer.update(Background((0, 0, 255)))
        assert buffer[0, 0].background.to_rgb() == (0, 0, 255)
        ```
    """

    def __init__(self, color: ColorValue) -> None: ...

class ApplyStyle(Operation):
    """
    Patch a [`Style`][xnano._xnano_core.Style] onto every cell of the target.

    Colors and modifiers the style leaves unset are kept.

    Args:
        style: The style to patch onto each cell.

    Examples:
        ```python
        buffer = Buffer(width=3, height=1)
        buffer.update(Write('abc'), ApplyStyle(Style('green', bold=True)))
        assert 'bold' in buffer[0, 0].style.modifiers
        ```
    """

    def __init__(self, style: Style) -> None: ...

class Border(Operation):
    """
    Draw a border around the edge of the target.

    Maps to [`ratatui::widgets::Block`](https://docs.rs/ratatui/0.30.0/ratatui/widgets/struct.Block.html)
    with [`BorderType`](https://docs.rs/ratatui/0.30.0/ratatui/widgets/enum.BorderType.html).

    Args:
        kind: ``'plain'``, ``'rounded'``, ``'double'`` or ``'thick'``.
        style: The style of the border cells.

    Examples:
        ```python
        buffer = Buffer(width=6, height=3)
        buffer.update(Border('rounded'))
        assert buffer.render(format='text').split('\\n')[0] == '╭────╮'
        ```
    """

    def __init__(
        self,
        kind: BorderKind = 'plain',
        *,
        style: Style | None = None,
    ) -> None: ...

class Blit(Operation):
    """
    Copy the cells of another buffer or region into the target.

    The source is snapshotted when the operation is created, so the operation can be
    applied repeatedly and always copies the same cells.

    Args:
        source: The buffer or region to copy from.
        x: The destination column of the source's top-left cell.
        y: The destination row of the source's top-left cell.
        mode: How copied cells combine with the destination.

    Examples:
        ```python
        source = Buffer(width=2, height=1)
        source.update(Write('ab'))
        target = Buffer(width=4, height=1)
        target.update(Fill('.'), Blit(source, x=1))
        assert target.text == '.ab.'
        ```
    """

    def __init__(
        self,
        source: Buffer | Region,
        *,
        x: int = 0,
        y: int = 0,
        mode: WriteMode = 'replace',
    ) -> None: ...

class Pixels(Operation):
    """
    Draw ordered RGB pixels into the target.

    The input is read once when the operation is created and applied in one batch.
    Half blocks give one pixel column and two pixel rows per cell; braille gives two
    columns and four rows per cell.

    Args:
        pixels: ``(column, row, (red, green, blue))`` pixels.
        encoding: ``'half_blocks'`` or ``'braille'``.
        clip: Skip pixels outside the target. When ``False`` an outside pixel raises
            ``IndexError`` and nothing is drawn.

    Examples:
        ```python
        buffer = Buffer(width=2, height=1)
        buffer.update(Pixels([(0, 0, (255, 0, 0)), (0, 1, (0, 0, 255))]))
        assert buffer[0, 0].symbol == '▀'
        assert buffer[0, 0].foreground.to_rgb() == (255, 0, 0)
        assert buffer[0, 0].background.to_rgb() == (0, 0, 255)
        ```
    """

    def __init__(
        self,
        pixels: Iterable[Pixel],
        *,
        encoding: PixelEncoding = 'half_blocks',
        clip: bool = True,
    ) -> None: ...

class Raster(Operation):
    """
    Draw a row-major RGBA8 image into the target as pixels.

    Args:
        rgba: ``width * height * 4`` bytes of red, green, blue and alpha.
        width: The image width in pixels.
        height: The image height in pixels.
        x: The pixel column of the image's top-left pixel.
        y: The pixel row of the image's top-left pixel.
        encoding: ``'half_blocks'`` or ``'braille'``.
        mode: ``'over'`` alpha-blends against what is there; ``'replace'`` overwrites it.

    Examples:
        ```python
        red = bytes([255, 0, 0, 255])
        buffer = Buffer(width=2, height=1)
        buffer.update(Raster(red * 4, width=2, height=2))
        assert buffer[0, 0].background.to_rgb() == (255, 0, 0)
        ```
    """

    def __init__(
        self,
        rgba: bytes,
        *,
        width: int,
        height: int,
        x: int = 0,
        y: int = 0,
        encoding: PixelEncoding = 'half_blocks',
        mode: RasterMode = 'over',
    ) -> None: ...

class SetState(Operation):
    """
    Assign a state branch and publish one validated commit.

    Args:
        reference: A state reference exposing ``path``, ``native_store`` and
            ``schema`` (see [`StateReference`][xnano._xnano_core.StateReference]).
        value: The new value of the branch.
        expected_revision: Fail with a conflict error unless the store is at this revision.

    Examples:
        ```python
        schema = TerminalStateSchema.compile(
            {'type': 'object', 'properties': {'score': {'type': 'integer'}}}
        )
        store = TerminalStateStore({'score': 1}, schema=schema)

        class Reference:
            path = ('score',)
            native_store = store
            schema = type('Encoder', (), {'to_value': lambda self, value: value})()

        Buffer().update(SetState(Reference(), 5))
        assert store.snapshot().to_value() == {'score': 5}
        ```
    """

    def __init__(
        self,
        reference: StateReference[StateType],
        value: StateType,
        *,
        expected_revision: int | None = None,
    ) -> None: ...

class ApplyStatePatch(Operation):
    """
    Apply a JSON patch to a state branch in one validated commit.

    Patch paths are relative to the reference.

    Args:
        reference: A state reference exposing ``path`` and ``native_store``.
        patch: The patch to apply below the reference's path.
        expected_revision: Fail with a conflict error unless the store is at this revision.

    Examples:
        ```python
        schema = TerminalStateSchema.compile(
            {
                'type': 'object',
                'properties': {
                    'player': {'type': 'object', 'properties': {'x': {'type': 'integer'}}}
                },
            }
        )
        store = TerminalStateStore({'player': {'x': 0}}, schema=schema)

        class Reference:
            path = ('player',)
            native_store = store
            schema = None

        patch = TerminalStatePatch.from_value(
            [{'op': 'replace', 'path': '/x', 'value': 9}]
        )
        Buffer().update(ApplyStatePatch(Reference(), patch))
        assert store.snapshot().to_value() == {'player': {'x': 9}}
        ```
    """

    def __init__(
        self,
        reference: StateReference[StateType],
        patch: TerminalStatePatch,
        *,
        expected_revision: int | None = None,
    ) -> None: ...

class Effect(Operation):
    """
    A composable animation with editable and bindable settings.

    Examples:
        ```python
        effect = Effect.fade_to('red', duration_milliseconds=100)
        effect.foreground = 'blue'
        assert effect.foreground == Color('blue')
        assert isinstance(effect.then(Effect.dissolve()), Effect)
        ```
    """

    def __init__(
        self,
        /,
        *,
        duration_milliseconds: int | Expression[int] | None = None,
        interpolation: str | Expression[str] | None = None,
        key: str | Expression[str] | None = None,
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    def __eq__(self, value: Any, /) -> bool: ...
    def repeat(self, /, *, times: int | Expression[int] | None = None) -> Effect: ...
    @staticmethod
    def fade_to(
        foreground: ColorValue | Expression[ColorValue] | None = None,
        background: ColorValue | Expression[ColorValue] | None = None,
        *,
        duration_milliseconds: int | Expression[int] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def fade_from(
        foreground: ColorValue | Expression[ColorValue] | None = None,
        background: ColorValue | Expression[ColorValue] | None = None,
        *,
        duration_milliseconds: int | Expression[int] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def paint(
        foreground: ColorValue | Expression[ColorValue] | None = None,
        background: ColorValue | Expression[ColorValue] | None = None,
        *,
        duration_milliseconds: int | Expression[int] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def saturate(
        foreground: float | Expression[float] | None = None,
        background: float | Expression[float] | None = None,
        *,
        duration_milliseconds: int | Expression[int] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def lighten(
        foreground: float | Expression[float] | None = None,
        background: float | Expression[float] | None = None,
        *,
        duration_milliseconds: int | Expression[int] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def darken(
        foreground: float | Expression[float] | None = None,
        background: float | Expression[float] | None = None,
        *,
        duration_milliseconds: int | Expression[int] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def sweep_in(
        direction: str | Expression[str] | None = None,
        *,
        gradient_length: int | Expression[int] | None = None,
        randomness: int | Expression[int] | None = None,
        color: ColorValue | Expression[ColorValue] | None = None,
        duration_milliseconds: int | Expression[int] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def sweep_out(
        direction: str | Expression[str] | None = None,
        *,
        gradient_length: int | Expression[int] | None = None,
        randomness: int | Expression[int] | None = None,
        color: ColorValue | Expression[ColorValue] | None = None,
        duration_milliseconds: int | Expression[int] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def slide_in(
        direction: str | Expression[str] | None = None,
        *,
        gradient_length: int | Expression[int] | None = None,
        randomness: int | Expression[int] | None = None,
        color: ColorValue | Expression[ColorValue] | None = None,
        duration_milliseconds: int | Expression[int] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def slide_out(
        direction: str | Expression[str] | None = None,
        *,
        gradient_length: int | Expression[int] | None = None,
        randomness: int | Expression[int] | None = None,
        color: ColorValue | Expression[ColorValue] | None = None,
        duration_milliseconds: int | Expression[int] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def hsl_shift(
        foreground: tuple[
            float | Expression[float],
            float | Expression[float],
            float | Expression[float],
        ]
        | None = None,
        background: tuple[
            float | Expression[float],
            float | Expression[float],
            float | Expression[float],
        ]
        | None = None,
        *,
        duration_milliseconds: int | Expression[int] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def dissolve(
        *,
        style: Style | DynamicStyle | None = None,
        duration_milliseconds: int | Expression[int] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def coalesce(
        *,
        style: Style | DynamicStyle | None = None,
        duration_milliseconds: int | Expression[int] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def glitch(
        *,
        ratio: float | Expression[float] | None = None,
        duration_milliseconds: int | Expression[int] | None = None,
        start_delay_milliseconds: tuple[int, int] = ...,
        action_milliseconds: tuple[int, int] = ...,
    ) -> Effect: ...
    @staticmethod
    def sleep(
        duration_milliseconds: int | Expression[int],
        *,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def term256_colors() -> Effect: ...
    @staticmethod
    def consume_tick() -> Effect: ...
    @staticmethod
    def sequence(effects: Sequence[Effect]) -> Effect: ...
    @staticmethod
    def parallel(effects: Sequence[Effect]) -> Effect: ...
    @overload
    def then(self, other: Effect) -> Effect: ...
    @overload
    def then(self, other: Operation) -> Operation: ...
    def alongside(self, /, other: Effect) -> Effect: ...
    def repeated(
        self,
        /,
        times: int | Expression[int] | None = None,
        *,
        milliseconds: int | Expression[int] | None = None,
    ) -> Effect: ...
    def ping_pong(self, /) -> Effect: ...
    def delayed(self, /, milliseconds: int | Expression[int]) -> Effect: ...
    def prolong_start(self, /, milliseconds: int | Expression[int]) -> Effect: ...
    def prolong_end(self, /, milliseconds: int | Expression[int]) -> Effect: ...
    def freeze_at(
        self,
        /,
        alpha: float | Expression[float],
        *,
        should_set_raw_alpha: bool | Expression[bool] = False,
    ) -> Effect: ...
    def remap_alpha(
        self, /, start: float | Expression[float], end: float | Expression[float]
    ) -> Effect: ...
    def with_duration(self, /, milliseconds: int | Expression[int]) -> Effect: ...
    def timed_never_complete(self, /, milliseconds: int | Expression[int]) -> Effect: ...
    def run_once(self, /) -> Effect: ...
    def never_complete(self, /) -> Effect: ...
    def with_filter(self, /, filter: CellFilter) -> Effect: ...
    def with_area(self, /, area: Rectangle) -> Effect: ...
    def reversed(
        self, /, is_reversed: bool | Expression[bool] | None = None
    ) -> Effect: ...
    def with_interpolation(self, /, interpolation: str | Expression[str]) -> Effect: ...
    def with_seed(self, /, seed: int | Expression[int]) -> Effect: ...
    def with_color_space(self, /, color_space: str | Expression[str]) -> Effect: ...
    def with_key(self, /, key: str | Expression[str]) -> Effect: ...
    def copy(self, /) -> Effect: ...
    def __copy__(self, /) -> Effect: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> Effect: ...
    @property
    def foreground(self) -> ColorValue | Expression[ColorValue] | None: ...
    @foreground.setter
    def foreground(self, value: ColorValue | Expression[ColorValue] | None) -> None: ...
    @property
    def duration_milliseconds(self) -> int | Expression[int]: ...
    @duration_milliseconds.setter
    def duration_milliseconds(self, value: int | Expression[int]) -> None: ...
    @property
    def kind(self) -> str | Expression[str]: ...
    @property
    def interpolation(self) -> str | Expression[str]: ...
    @interpolation.setter
    def interpolation(self, value: str | Expression[str]) -> None: ...
    @property
    def key(self) -> str | Expression[str] | None: ...
    @key.setter
    def key(self, value: str | Expression[str] | None) -> None: ...
    @property
    def background(self) -> ColorValue | Expression[ColorValue] | None: ...
    @background.setter
    def background(self, value: ColorValue | Expression[ColorValue] | None) -> None: ...
    @property
    def children(self) -> Sequence[Effect]: ...

class Fade(Effect):
    """
    Fade the colors of the target toward a foreground and background color.

    Maps to [`tachyonfx::fx::fade_to`](https://docs.rs/tachyonfx/0.25.0/tachyonfx/fx/fn.fade_to.html).

    Args:
        foreground: The color the foreground fades to, or ``None`` to leave it.
        background: The color the background fades to, or ``None`` to leave it.
        duration_milliseconds: How long the fade plays.
        interpolation: How progress eases over the duration.
        key: A name that [`CancelEffect`][xnano._xnano_core.CancelEffect] can target.

    Examples:
        ```python
        runtime = Runtime.offscreen(width=10, height=1)
        buffer = Buffer(width=10, height=1)
        buffer.update(Write('hello', style=Style('white', 'black')))
        runtime.mount(buffer, geometry='inherit')
        runtime.step()

        buffer.update(Fade(foreground='red', duration_milliseconds=100))
        runtime.step()
        runtime.advance_clock(100)
        runtime.step()
        assert '31' in runtime.snapshot().ansi
        ```
    """

    def __init__(
        self,
        *,
        foreground: ColorValue | None = None,
        background: ColorValue | None = None,
        duration_milliseconds: int = 500,
        interpolation: Interpolation = 'linear',
        key: str | None = None,
    ) -> None: ...

class Dissolve(Effect):
    """
    Dissolve the glyphs of the target away cell by cell.

    With ``should_reverse`` the glyphs instead appear cell by cell.

    Maps to [`tachyonfx::fx::dissolve`](https://docs.rs/tachyonfx/0.25.0/tachyonfx/fx/fn.dissolve.html)
    and [`tachyonfx::fx::coalesce`](https://docs.rs/tachyonfx/0.25.0/tachyonfx/fx/fn.coalesce.html).

    Args:
        duration_milliseconds: How long the effect plays.
        should_reverse: Make glyphs appear instead of disappear.
        seed: Seed for a repeatable cell order; ``None`` is random.
        key: A name that [`CancelEffect`][xnano._xnano_core.CancelEffect] can target.

    Examples:
        ```python
        runtime = Runtime.offscreen(width=10, height=1)
        buffer = Buffer(width=10, height=1)
        buffer.update(Write('hello'))
        runtime.mount(buffer, geometry='inherit')
        runtime.step()

        buffer.update(Dissolve(duration_milliseconds=100, seed=1))
        runtime.step()
        runtime.advance_clock(100)
        runtime.step()
        assert runtime.snapshot().lines()[0].strip() == ''
        ```
    """

    def __init__(
        self,
        *,
        duration_milliseconds: int = 500,
        should_reverse: bool = False,
        seed: int | None = None,
        key: str | None = None,
    ) -> None: ...

class Glitch(Effect):
    """
    Randomly corrupt and displace glyphs of the target.

    Maps to [`tachyonfx::fx::Glitch`](https://docs.rs/tachyonfx/0.25.0/tachyonfx/fx/struct.Glitch.html).

    Args:
        intensity: Fraction of cells affected, from ``0.0`` to ``1.0``.
        duration_milliseconds: How long the effect plays.
        seed: Seed for a repeatable result; ``None`` is random.
        key: A name that [`CancelEffect`][xnano._xnano_core.CancelEffect] can target.

    Examples:
        ```python
        runtime = Runtime.offscreen(width=10, height=1)
        buffer = Buffer(width=10, height=1)
        buffer.update(Write('hello'))
        runtime.mount(buffer, geometry='inherit')
        runtime.step()

        buffer.update(Glitch(intensity=1.0, duration_milliseconds=100, seed=1))
        runtime.step()
        runtime.advance_clock(50)
        runtime.step()
        assert runtime.snapshot().lines()[0] != 'hello'
        ```
    """

    def __init__(
        self,
        *,
        intensity: float = 0.1,
        duration_milliseconds: int = 500,
        seed: int | None = None,
        key: str | None = None,
    ) -> None: ...

class Fuzz(Operation):
    """
    Replace a percentage of the visible glyphs of the target with noise glyphs, once.

    Unlike an [`Effect`][xnano._xnano_core.Effect] it changes the cells immediately and
    does not need a runtime. Blank and wide cells are left alone.

    Args:
        intensity: Percentage of glyphs to replace, from ``0`` to ``100``.
        seed: Seed for a repeatable result; ``None`` is random.

    Examples:
        ```python
        buffer = Buffer(width=5, height=1)
        buffer.update(Write('hello'), Fuzz(100, seed=1))
        assert buffer.text != 'hello' and len(buffer.text) == 5
        ```
    """

    def __init__(self, intensity: int, *, seed: int | None = None) -> None: ...

class CancelEffect(Operation):
    """
    Stop the running effect that was started with ``key``.

    Args:
        key: The ``key`` the effect was created with.

    Examples:
        ```python
        runtime = Runtime.offscreen(width=10, height=1)
        buffer = Buffer(width=10, height=1)
        buffer.update(Write('hello'))
        runtime.mount(buffer, geometry='inherit')
        runtime.step()

        buffer.update(Dissolve(duration_milliseconds=100, key='fade-out'))
        buffer.update(CancelEffect('fade-out'))
        runtime.step()
        runtime.advance_clock(100)
        runtime.step()
        assert runtime.snapshot().lines()[0] == 'hello'
        ```
    """

    def __init__(self, key: str) -> None: ...

class SizeRule:
    """
    How much space one child takes along a layout's main axis.

    Maps to [`ratatui::layout::Constraint`](https://docs.rs/ratatui/0.30.0/ratatui/layout/enum.Constraint.html).

    Examples:
        ```python
        rules = [SizeRule.cells(4), SizeRule.fill()]
        parent = Buffer(width=12, height=3)
        first, second = Buffer(), Buffer()
        parent.attach(first, geometry='inherit')
        parent.attach(second, geometry='inherit')
        parent.update(Layout('row', sizes=rules))
        assert (first.width, second.width) == (4, 8)
        ```
    """

    @classmethod
    def cells(cls, count: int) -> SizeRule:
        """
        Take exactly ``count`` cells.

        Examples:
            ```python
            assert repr(SizeRule.cells(4)) == 'SizeRule.cells(4)'
            ```
        """

    @classmethod
    def percent(cls, percentage: int) -> SizeRule:
        """
        Take ``percentage`` percent of the available space.

        Examples:
            ```python
            assert repr(SizeRule.percent(50)) == 'SizeRule.percent(50)'
            ```
        """

    @classmethod
    def fill(cls, weight: int = 1) -> SizeRule:
        """
        Share the remaining space with other fill rules in proportion to ``weight``.

        Examples:
            ```python
            assert repr(SizeRule.fill(2)) == 'SizeRule.fill(2)'
            ```
        """

    @classmethod
    def fit(cls) -> SizeRule:
        """
        Take the size of the child's own content.

        Examples:
            ```python
            assert repr(SizeRule.fit()) == 'SizeRule.fit()'
            ```
        """

    @classmethod
    def minimum(cls, count: int) -> SizeRule:
        """
        Take at least ``count`` cells.

        Examples:
            ```python
            assert repr(SizeRule.minimum(2)) == 'SizeRule.minimum(2)'
            ```
        """

    @classmethod
    def maximum(cls, count: int) -> SizeRule:
        """
        Take at most ``count`` cells.

        Examples:
            ```python
            assert repr(SizeRule.maximum(3)) == 'SizeRule.maximum(3)'
            ```
        """

class Layout(Operation):
    """
    Arrange attached children within the parent's content area.

    Overlay children inherit that area unless explicitly positioned. Row and column
    children default to equal fill; missing size rules never mean zero-sized children.
    All output is clipped to the authoritative frame.

    Maps to [`ratatui::layout::Layout`](https://docs.rs/ratatui/0.30.0/ratatui/layout/struct.Layout.html)
    for ``'row'`` and ``'column'``.

    Args:
        arrangement: ``'row'``, ``'column'`` or ``'overlay'``.
        sizes: One [`SizeRule`][xnano._xnano_core.SizeRule] per child along the main axis.
        spacing: Cells between children.
        padding: Cells between the parent's edge and its children.

    Examples:
        ```python
        parent = Buffer(width=12, height=3)
        left, right = Buffer(), Buffer()
        parent.attach(left, geometry='inherit')
        parent.attach(right, geometry='inherit')
        parent.update(
            Layout('row', sizes=[SizeRule.cells(4), SizeRule.fill()], spacing=1)
        )
        assert (left.width, right.x, right.width) == (4, 5, 7)
        ```
    """

    def __init__(
        self,
        arrangement: Literal['row', 'column', 'overlay'] = 'column',
        *,
        sizes: Sequence[SizeRule] = (),
        spacing: int = 0,
        padding: int = 0,
    ) -> None: ...
    @staticmethod
    def split(
        rectangle: Rectangle,
        *,
        arrangement: Literal['row', 'column'] = 'column',
        constraints: Sequence[tuple[str, int, int]],
        spacing: int = 0,
    ) -> list[Rectangle]: ...

class ItemList(Widget):
    """
    Selectable styled items with editable selection and scrolling.

    Examples:
        ```python
        items = ItemList(['one', 'two'], width=10, height=2)
        items.select_first()
        items.select_next()
        assert items.selected == 1
        ```
    """

    def __init__(
        self,
        /,
        items: Sequence[ListItem | TextContent] | None = None,
        *,
        selected: int | Expression[int] | None = None,
        offset: int | Expression[int] | None = None,
        style: Style | DynamicStyle | None = None,
        highlight_style: Style | DynamicStyle | None = None,
        highlight_symbol: str | Expression[str] | None = None,
        repeat_highlight_symbol: bool | Expression[bool] | None = None,
        highlight_spacing: str | Expression[str] | None = None,
        direction: str | Expression[str] | None = None,
        scroll_padding: int | Expression[int] | None = None,
        block: Block | None = None,
        width: int | Expression[int] | None = None,
        height: int | Expression[int] | None = None,
        x: int | Expression[int] = 0,
        y: int | Expression[int] = 0,
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    def append(self, /, item: ListItem | TextContent) -> None: ...
    def extend(self, /, items: Sequence[ListItem | TextContent]) -> None: ...
    def insert(
        self, /, index: int | Expression[int], item: ListItem | TextContent
    ) -> None: ...
    def set_item(
        self, /, index: int | Expression[int], item: ListItem | TextContent
    ) -> None: ...
    def pop(self, /, index: int | Expression[int] | None = None) -> ListItem: ...
    def clear(self, /) -> None: ...
    def select_next(self, /) -> None: ...
    def select_previous(self, /) -> None: ...
    def select_first(self, /) -> None: ...
    def select_last(self, /) -> None: ...
    def scroll_down_by(self, /, amount: int | Expression[int]) -> None: ...
    def scroll_up_by(self, /, amount: int | Expression[int]) -> None: ...
    def copy(self, /) -> ItemList: ...
    def __copy__(self, /) -> ItemList: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> ItemList: ...
    @property
    def scroll_padding(self) -> int | Expression[int]: ...
    @scroll_padding.setter
    def scroll_padding(self, value: int | Expression[int]) -> None: ...
    @property
    def highlight_style(self) -> Style | DynamicStyle: ...
    @highlight_style.setter
    def highlight_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def selected(self) -> int | Expression[int] | None: ...
    @selected.setter
    def selected(self, value: int | Expression[int] | None) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle: ...
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def repeat_highlight_symbol(self) -> bool | Expression[bool]: ...
    @repeat_highlight_symbol.setter
    def repeat_highlight_symbol(self, value: bool | Expression[bool]) -> None: ...
    @property
    def highlight_spacing(self) -> str | Expression[str]: ...
    @highlight_spacing.setter
    def highlight_spacing(self, value: str | Expression[str]) -> None: ...
    @property
    def offset(self) -> int | Expression[int]: ...
    @offset.setter
    def offset(self, value: int | Expression[int]) -> None: ...
    @property
    def highlight_symbol(self) -> str | Expression[str]: ...
    @highlight_symbol.setter
    def highlight_symbol(self, value: str | Expression[str]) -> None: ...
    @property
    def visible_range(self) -> tuple[int, int]: ...
    @property
    def direction(self) -> str | Expression[str]: ...
    @direction.setter
    def direction(self, value: str | Expression[str]) -> None: ...
    @property
    def items(self) -> Sequence[ListItem | TextContent]: ...
    @items.setter
    def items(self, value: Sequence[ListItem | TextContent]) -> None: ...
    @property
    def block(self) -> Block | None: ...
    @block.setter
    def block(self, value: Block | None) -> None: ...

class Gauge(Widget):
    """
    A filled progress bar that repaints when its ratio changes.

    Examples:
        ```python
        gauge = Gauge(0.5, width=10, height=1)
        gauge.ratio = 0.75
        assert gauge.ratio == 0.75
        ```
    """

    def __init__(
        self,
        /,
        ratio: float | Expression[float] | None = None,
        *,
        label: TextContent | Expression[str] | None = None,
        style: Style | DynamicStyle | None = None,
        gauge_style: Style | DynamicStyle | None = None,
        use_unicode: bool | Expression[bool] | None = None,
        block: Block | None = None,
        width: int | Expression[int] | None = None,
        height: int | Expression[int] | None = None,
        x: int | Expression[int] = 0,
        y: int | Expression[int] = 0,
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    @property
    def label(self) -> TextContent | Expression[str] | None: ...
    @label.setter
    def label(self, value: TextContent | Expression[str] | None) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle: ...
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def use_unicode(self) -> bool | Expression[bool]: ...
    @use_unicode.setter
    def use_unicode(self, value: bool | Expression[bool]) -> None: ...
    @property
    def ratio(self) -> float | Expression[float]: ...
    @ratio.setter
    def ratio(self, value: float | Expression[float]) -> None: ...
    @property
    def block(self) -> Block | None: ...
    @block.setter
    def block(self, value: Block | None) -> None: ...
    @property
    def gauge_style(self) -> Style | DynamicStyle: ...
    @gauge_style.setter
    def gauge_style(self, value: Style | DynamicStyle) -> None: ...

class LineGauge(Widget):
    """
    A progress indicator drawn with line symbols.

    Examples:
        ```python
        gauge = LineGauge(0.5, width=10, height=1)
        gauge.ratio = 0.8
        assert gauge.ratio == 0.8
        ```
    """

    def __init__(
        self,
        /,
        ratio: float | Expression[float] | None = None,
        *,
        label: TextContent | Expression[str] | None = None,
        line_set: str | Expression[str] | None = None,
        filled_symbol: Any | None = None,
        unfilled_symbol: Any | None = None,
        style: Style | DynamicStyle | None = None,
        filled_style: Style | DynamicStyle | None = None,
        unfilled_style: Style | DynamicStyle | None = None,
        block: Block | None = None,
        width: int | Expression[int] | None = None,
        height: int | Expression[int] | None = None,
        x: int | Expression[int] = 0,
        y: int | Expression[int] = 0,
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    def copy(self, /) -> LineGauge: ...
    def __copy__(self, /) -> LineGauge: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> LineGauge: ...
    @property
    def block(self) -> Block | None: ...
    @block.setter
    def block(self, value: Block | None) -> None: ...
    @property
    def unfilled_style(self) -> Style | DynamicStyle: ...
    @unfilled_style.setter
    def unfilled_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def ratio(self) -> float | Expression[float]: ...
    @ratio.setter
    def ratio(self, value: float | Expression[float]) -> None: ...
    @property
    def filled_symbol(self) -> Any: ...
    @filled_symbol.setter
    def filled_symbol(self, value: Any) -> None: ...
    @property
    def filled_style(self) -> Style | DynamicStyle: ...
    @filled_style.setter
    def filled_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle: ...
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def unfilled_symbol(self) -> Any: ...
    @unfilled_symbol.setter
    def unfilled_symbol(self, value: Any) -> None: ...
    @property
    def label(self) -> TextContent | Expression[str] | None: ...
    @label.setter
    def label(self, value: TextContent | Expression[str] | None) -> None: ...
    @property
    def line_set(self) -> str | Expression[str]: ...
    @line_set.setter
    def line_set(self, value: str | Expression[str]) -> None: ...

class Sparkline(Widget):
    """
    A compact history of numeric samples.

    Examples:
        ```python
        sparkline = Sparkline([1, 3, 2], width=3, height=1)
        sparkline.append(4)
        assert len(sparkline.values) == 4
        ```
    """

    def __init__(
        self,
        /,
        values: Sequence[int | Expression[int] | SparklineBar | None] | None = None,
        *,
        maximum: int | Expression[int] | None = None,
        style: Style | DynamicStyle | None = None,
        absent_value_style: Style | DynamicStyle | None = None,
        absent_value_symbol: str | Expression[str] | None = None,
        direction: str | Expression[str] | None = None,
        bar_set: str | Expression[str] | None = None,
        block: Block | None = None,
        width: int | Expression[int] | None = None,
        height: int | Expression[int] | None = None,
        x: int | Expression[int] = 0,
        y: int | Expression[int] = 0,
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    def __len__(self, /) -> int: ...
    def append(
        self,
        /,
        value: int | Expression[int],
        *,
        maximum_length: int | Expression[int] | None = None,
    ) -> None: ...
    def extend(
        self,
        /,
        values: Sequence[int | Expression[int] | SparklineBar | None],
        *,
        maximum_length: int | Expression[int] | None = None,
    ) -> None: ...
    def clear(self, /) -> None: ...
    def copy(self, /) -> Sparkline: ...
    def __copy__(self, /) -> Sparkline: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> Sparkline: ...
    @property
    def values(self) -> Sequence[int | Expression[int] | SparklineBar | None]: ...
    @values.setter
    def values(
        self, value: Sequence[int | Expression[int] | SparklineBar | None]
    ) -> None: ...
    @property
    def bars(self) -> Sequence[SparklineBar]: ...
    @property
    def maximum(self) -> int | Expression[int] | None: ...
    @maximum.setter
    def maximum(self, value: int | Expression[int] | None) -> None: ...
    @property
    def bar_set(self) -> str | Expression[str]: ...
    @bar_set.setter
    def bar_set(self, value: str | Expression[str]) -> None: ...
    @property
    def direction(self) -> str | Expression[str]: ...
    @direction.setter
    def direction(self, value: str | Expression[str]) -> None: ...
    @property
    def absent_value_style(self) -> Style | DynamicStyle: ...
    @absent_value_style.setter
    def absent_value_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle: ...
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def absent_value_symbol(self) -> str | Expression[str]: ...
    @absent_value_symbol.setter
    def absent_value_symbol(self, value: str | Expression[str]) -> None: ...
    @property
    def block(self) -> Block | None: ...
    @block.setter
    def block(self, value: Block | None) -> None: ...

class Bar:
    """
    One labelled value in a bar chart.

    Examples:
        ```python
        bar = Bar(3, 'A')
        assert bar.value == 3
        ```
    """

    def __init__(
        self,
        /,
        value: int | Expression[int],
        label: TextContent | Expression[str] | None = None,
        *,
        text_value: str | Expression[str] | None = None,
        style: Style | DynamicStyle | None = None,
        value_style: Style | DynamicStyle | None = None,
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    def __hash__(self, /) -> int: ...
    def __eq__(self, value: object, /) -> bool: ...
    def __copy__(self, /) -> Bar: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> Bar: ...
    @property
    def label(self) -> TextContent | Expression[str] | None: ...
    @property
    def style(self) -> Style | DynamicStyle: ...
    @property
    def value(self) -> int | Expression[int]: ...
    @property
    def text_value(self) -> str | Expression[str]: ...
    @property
    def value_style(self) -> Style | DynamicStyle: ...

class BarGroup:
    """
    A labelled group of bars.

    Examples:
        ```python
        group = BarGroup([Bar(3, 'A')], 'Group')
        assert len(group.bars) == 1
        ```
    """

    def __init__(
        self, /, bars: Sequence[Bar], label: TextContent | Expression[str] | None = None
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    def __hash__(self, /) -> int: ...
    def __eq__(self, value: Any, /) -> bool: ...
    def __copy__(self, /) -> BarGroup: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> BarGroup: ...
    @property
    def label(self) -> TextContent | Expression[str] | None: ...
    @property
    def bars(self) -> Sequence[Bar]: ...

class BarChart(Widget):
    """
    Grouped bars with editable values and styles.

    Examples:
        ```python
        chart = BarChart([Bar(3, 'A')], width=12, height=4)
        chart.maximum = 6
        assert chart.maximum == 6
        ```
    """

    def __init__(
        self,
        /,
        data: Sequence[Bar | BarGroup | tuple[str, int]] | None = None,
        *,
        bar_width: int | Expression[int] | None = None,
        bar_gap: int | Expression[int] | None = None,
        group_gap: int | Expression[int] | None = None,
        maximum: int | Expression[int] | None = None,
        direction: str | Expression[str] | None = None,
        bar_style: Style | DynamicStyle | None = None,
        value_style: Style | DynamicStyle | None = None,
        label_style: Style | DynamicStyle | None = None,
        style: Style | DynamicStyle | None = None,
        bar_set: str | Expression[str] | None = None,
        block: Block | None = None,
        width: int | Expression[int] | None = None,
        height: int | Expression[int] | None = None,
        x: int | Expression[int] = 0,
        y: int | Expression[int] = 0,
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    def append(
        self, /, bar: Any, *, maximum_bars: int | Expression[int] | None = None
    ) -> None: ...
    def clear(self, /) -> None: ...
    def copy(self, /) -> BarChart: ...
    def __copy__(self, /) -> BarChart: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> BarChart: ...
    @property
    def label_style(self) -> Style | DynamicStyle: ...
    @label_style.setter
    def label_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def group_gap(self) -> int | Expression[int]: ...
    @group_gap.setter
    def group_gap(self, value: int | Expression[int]) -> None: ...
    @property
    def bar_gap(self) -> int | Expression[int]: ...
    @bar_gap.setter
    def bar_gap(self, value: int | Expression[int]) -> None: ...
    @property
    def block(self) -> Block | None: ...
    @block.setter
    def block(self, value: Block | None) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle: ...
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def bar_width(self) -> int | Expression[int]: ...
    @bar_width.setter
    def bar_width(self, value: int | Expression[int]) -> None: ...
    @property
    def direction(self) -> str | Expression[str]: ...
    @direction.setter
    def direction(self, value: str | Expression[str]) -> None: ...
    @property
    def maximum(self) -> int | Expression[int] | None: ...
    @maximum.setter
    def maximum(self, value: int | Expression[int] | None) -> None: ...
    @property
    def groups(self) -> Sequence[BarGroup]: ...
    @groups.setter
    def groups(self, value: Sequence[BarGroup]) -> None: ...
    @property
    def bar_set(self) -> str | Expression[str]: ...
    @bar_set.setter
    def bar_set(self, value: str | Expression[str]) -> None: ...
    @property
    def bar_style(self) -> Style | DynamicStyle: ...
    @bar_style.setter
    def bar_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def value_style(self) -> Style | DynamicStyle: ...
    @value_style.setter
    def value_style(self, value: Style | DynamicStyle) -> None: ...

class TableCell:
    """
    Styled content displayed in a table cell.

    Examples:
        ```python
        cell = TableCell('hello')
        assert 'hello' in repr(cell)
        ```
    """

    def __init__(
        self,
        /,
        content: TextContent | Expression[str],
        *,
        style: Style | DynamicStyle | None = None,
        column_span: Any = 1,
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    def __hash__(self, /) -> int: ...
    def __eq__(self, value: Any, /) -> bool: ...
    def __copy__(self, /) -> TableCell: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> TableCell: ...
    @property
    def column_span(self) -> Any: ...
    @property
    def content(self) -> TextContent | Expression[str]: ...
    @property
    def style(self) -> Style | DynamicStyle: ...

class TableRow:
    """
    A row of cells with height and spacing.

    Examples:
        ```python
        row = TableRow(['one', 'two'])
        assert len(row.cells) == 2
        ```
    """

    def __init__(
        self,
        /,
        cells: Sequence[TableCell | TextContent],
        *,
        height: int | Expression[int] = 1,
        top_margin: int | Expression[int] = 0,
        bottom_margin: int | Expression[int] = 0,
        style: Style | DynamicStyle | None = None,
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    def __hash__(self, /) -> int: ...
    def __eq__(self, value: Any, /) -> bool: ...
    def __copy__(self, /) -> TableRow: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> TableRow: ...
    @property
    def style(self) -> Style | DynamicStyle: ...
    @property
    def height(self) -> int | Expression[int]: ...
    @property
    def bottom_margin(self) -> int | Expression[int]: ...
    @property
    def top_margin(self) -> int | Expression[int]: ...
    @property
    def cells(self) -> Sequence[TableCell | TextContent]: ...

class Table(Widget):
    """
    A retained table with row, column and cell selection.

    Examples:
        ```python
        table = Table([TableRow(['one', 'two'])], widths=[5, 5], width=12, height=2)
        assert 'one' in table.render(format='text')
        table.select_first()
        assert table.selected_row == 0
        ```
    """

    def __init__(
        self,
        /,
        rows: Sequence[TableRow | Sequence[TableCell | TextContent]] | None = None,
        *,
        header: TableRow | Sequence[TableCell | TextContent] | None = None,
        footer: TableRow | Sequence[TableCell | TextContent] | None = None,
        widths: Sequence[int | SizeRule | tuple[int, int]] | None = None,
        column_spacing: int | Expression[int] | None = None,
        flex: Any | None = None,
        selected_row: int | Expression[int] | None = None,
        selected_column: int | Expression[int] | None = None,
        offset: int | Expression[int] | None = None,
        style: Style | DynamicStyle | None = None,
        row_highlight_style: Style | DynamicStyle | None = None,
        column_highlight_style: Style | DynamicStyle | None = None,
        cell_highlight_style: Style | DynamicStyle | None = None,
        highlight_symbol: str | Expression[str] | None = None,
        highlight_spacing: str | Expression[str] | None = None,
        block: Block | None = None,
        width: int | Expression[int] | None = None,
        height: int | Expression[int] | None = None,
        x: int | Expression[int] = 0,
        y: int | Expression[int] = 0,
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    def append_row(
        self, /, row: TableRow | Sequence[TableCell | TextContent]
    ) -> None: ...
    def clear_rows(self, /) -> None: ...
    def select_next(self, /) -> None: ...
    def select_previous(self, /) -> None: ...
    def select_first(self, /) -> None: ...
    def select_last(self, /) -> None: ...
    def select_next_column(self, /) -> None: ...
    def select_previous_column(self, /) -> None: ...
    def select_first_column(self, /) -> None: ...
    def select_last_column(self, /) -> None: ...
    def scroll_down_by(self, /, amount: int | Expression[int]) -> None: ...
    def scroll_up_by(self, /, amount: int | Expression[int]) -> None: ...
    def scroll_right_by(self, /, amount: int | Expression[int]) -> None: ...
    def scroll_left_by(self, /, amount: int | Expression[int]) -> None: ...
    def copy(self, /) -> Table: ...
    def __copy__(self, /) -> Table: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> Table: ...
    @property
    def flex(self) -> Any: ...
    @flex.setter
    def flex(self, value: Any) -> None: ...
    @property
    def widths(self) -> Sequence[int | SizeRule | tuple[int, int]]: ...
    @widths.setter
    def widths(self, value: Sequence[int | SizeRule | tuple[int, int]]) -> None: ...
    @property
    def highlight_symbol(self) -> str | Expression[str]: ...
    @highlight_symbol.setter
    def highlight_symbol(self, value: str | Expression[str]) -> None: ...
    @property
    def block(self) -> Block | None: ...
    @block.setter
    def block(self, value: Block | None) -> None: ...
    @property
    def row_highlight_style(self) -> Style | DynamicStyle: ...
    @row_highlight_style.setter
    def row_highlight_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def selected_cell(self) -> tuple[int, int] | None: ...
    @property
    def selected_row(self) -> int | Expression[int] | None: ...
    @selected_row.setter
    def selected_row(self, value: int | Expression[int] | None) -> None: ...
    @property
    def offset(self) -> int | Expression[int]: ...
    @offset.setter
    def offset(self, value: int | Expression[int]) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle: ...
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def column_highlight_style(self) -> Style | DynamicStyle: ...
    @column_highlight_style.setter
    def column_highlight_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def selected_column(self) -> int | Expression[int] | None: ...
    @selected_column.setter
    def selected_column(self, value: int | Expression[int] | None) -> None: ...
    @property
    def visible_range(self) -> tuple[int, int]: ...
    @property
    def rows(self) -> Sequence[TableRow | Sequence[TableCell | TextContent]]: ...
    @rows.setter
    def rows(
        self, value: Sequence[TableRow | Sequence[TableCell | TextContent]]
    ) -> None: ...
    @property
    def cell_highlight_style(self) -> Style | DynamicStyle: ...
    @cell_highlight_style.setter
    def cell_highlight_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def header(self) -> TableRow | Sequence[TableCell | TextContent] | None: ...
    @header.setter
    def header(
        self, value: TableRow | Sequence[TableCell | TextContent] | None
    ) -> None: ...
    @property
    def footer(self) -> TableRow | Sequence[TableCell | TextContent] | None: ...
    @footer.setter
    def footer(
        self, value: TableRow | Sequence[TableCell | TextContent] | None
    ) -> None: ...
    @property
    def column_spacing(self) -> int | Expression[int]: ...
    @column_spacing.setter
    def column_spacing(self, value: int | Expression[int]) -> None: ...
    @property
    def highlight_spacing(self) -> str | Expression[str]: ...
    @highlight_spacing.setter
    def highlight_spacing(self, value: str | Expression[str]) -> None: ...

class Scrollbar(Widget):
    """
    A scrollbar showing position within content.

    Examples:
        ```python
        scrollbar = Scrollbar(10, 0, viewport_content_length=3, width=1, height=5)
        scrollbar.next()
        assert scrollbar.content_position == 1
        ```
    """

    def __init__(
        self,
        /,
        content_length: int | Expression[int] | None = None,
        position: int | Expression[int] | None = None,
        *,
        orientation: str | Expression[str] | None = None,
        viewport_content_length: int | Expression[int] | None = None,
        symbols: str | Sequence[str] | None = None,
        thumb_symbol: str | Expression[str] | None = None,
        track_symbol: str | Expression[str] | None = None,
        begin_symbol: str | Expression[str] | None = None,
        end_symbol: str | Expression[str] | None = None,
        has_track: bool | Expression[bool] = True,
        has_begin: bool | Expression[bool] = True,
        has_end: bool | Expression[bool] = True,
        style: Style | DynamicStyle | None = None,
        thumb_style: Style | DynamicStyle | None = None,
        track_style: Style | DynamicStyle | None = None,
        begin_style: Style | DynamicStyle | None = None,
        end_style: Style | DynamicStyle | None = None,
        is_transparent: bool | Expression[bool] | None = None,
        width: int | Expression[int] | None = None,
        height: int | Expression[int] | None = None,
        x: int | Expression[int] = 0,
        y: int | Expression[int] = 0,
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    def first(self, /) -> None: ...
    def last(self, /) -> None: ...
    def next(self, /) -> None: ...
    def previous(self, /) -> None: ...
    def scroll(self, /, direction: str | Expression[str]) -> None: ...
    def copy(self, /) -> Scrollbar: ...
    def __copy__(self, /) -> Scrollbar: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> Scrollbar: ...
    @property
    def content_length(self) -> int | Expression[int]: ...
    @content_length.setter
    def content_length(self, value: int | Expression[int]) -> None: ...
    @property
    def is_transparent(self) -> bool | Expression[bool]: ...
    @is_transparent.setter
    def is_transparent(self, value: bool | Expression[bool]) -> None: ...
    @property
    def end_style(self) -> Style | DynamicStyle: ...
    @end_style.setter
    def end_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def thumb_symbol(self) -> str | Expression[str]: ...
    @thumb_symbol.setter
    def thumb_symbol(self, value: str | Expression[str]) -> None: ...
    @property
    def track_style(self) -> Style | DynamicStyle: ...
    @track_style.setter
    def track_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def end_symbol(self) -> str | Expression[str]: ...
    @end_symbol.setter
    def end_symbol(self, value: str | Expression[str]) -> None: ...
    @property
    def thumb_style(self) -> Style | DynamicStyle: ...
    @thumb_style.setter
    def thumb_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle: ...
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def orientation(self) -> str | Expression[str]: ...
    @orientation.setter
    def orientation(self, value: str | Expression[str]) -> None: ...
    @property
    def content_position(self) -> int | Expression[int]: ...
    @content_position.setter
    def content_position(self, value: int | Expression[int]) -> None: ...
    @property
    def begin_style(self) -> Style | DynamicStyle: ...
    @begin_style.setter
    def begin_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def viewport_content_length(self) -> int | Expression[int]: ...
    @viewport_content_length.setter
    def viewport_content_length(self, value: int | Expression[int]) -> None: ...
    @property
    def symbols(self) -> str | Sequence[str]: ...
    @symbols.setter
    def symbols(self, value: str | Sequence[str]) -> None: ...
    @property
    def begin_symbol(self) -> str | Expression[str]: ...
    @begin_symbol.setter
    def begin_symbol(self, value: str | Expression[str]) -> None: ...
    @property
    def track_symbol(self) -> str | Expression[str]: ...
    @track_symbol.setter
    def track_symbol(self, value: str | Expression[str]) -> None: ...

class Tabs(Widget):
    """
    Selectable titles with editable padding, divider and styles.

    Examples:
        ```python
        tabs = Tabs(['one', 'two'], selected=0, width=20, height=1)
        tabs.select_next()
        assert tabs.selected == 1
        ```
    """

    def __init__(
        self,
        /,
        titles: Sequence[TextContent] | None = None,
        *,
        selected: int | Expression[int] | None = None,
        style: Style | DynamicStyle | None = None,
        highlight_style: Style | DynamicStyle | None = None,
        divider: str | Expression[str] | None = None,
        padding_left: int | Expression[int] | None = None,
        padding_right: int | Expression[int] | None = None,
        block: Block | None = None,
        width: int | Expression[int] | None = None,
        height: int | Expression[int] | None = None,
        x: int | Expression[int] = 0,
        y: int | Expression[int] = 0,
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    def append(self, /, title: str | Expression[str]) -> None: ...
    def pop(self, /, index: int | Expression[int] | None = None) -> TextContent: ...
    def clear(self, /) -> None: ...
    def select_next(self, /, *, should_wrap: bool | Expression[bool] = True) -> None: ...
    def select_previous(
        self, /, *, should_wrap: bool | Expression[bool] = True
    ) -> None: ...
    def select_first(self, /) -> None: ...
    def select_last(self, /) -> None: ...
    def copy(self, /) -> Tabs: ...
    def __copy__(self, /) -> Tabs: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> Tabs: ...
    @property
    def padding_right(self) -> int | Expression[int]: ...
    @padding_right.setter
    def padding_right(self, value: int | Expression[int]) -> None: ...
    @property
    def selected(self) -> int | Expression[int] | None: ...
    @selected.setter
    def selected(self, value: int | Expression[int] | None) -> None: ...
    @property
    def highlight_style(self) -> Style | DynamicStyle: ...
    @highlight_style.setter
    def highlight_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def titles(self) -> Sequence[TextContent]: ...
    @titles.setter
    def titles(self, value: Sequence[TextContent]) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle: ...
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def block(self) -> Block | None: ...
    @block.setter
    def block(self, value: Block | None) -> None: ...
    @property
    def padding_left(self) -> int | Expression[int]: ...
    @padding_left.setter
    def padding_left(self, value: int | Expression[int]) -> None: ...
    @property
    def divider(self) -> str | Expression[str]: ...
    @divider.setter
    def divider(self, value: str | Expression[str]) -> None: ...

class Drawing:
    """
    An immutable picture made of rows of text or palette pixels.

    A ``'text'`` drawing holds terminal glyphs. A ``'palette'`` drawing holds one symbol per
    logical pixel and maps each symbol to a color, or to ``None`` for transparency. Drawings
    serialize to JSON and can be regenerated from their value.

    Args:
        rows: The rows of the drawing.
        kind: ``'text'`` or ``'palette'``.
        palette: For palette drawings, the color of each symbol.

    Examples:
        ```python
        art = Drawing(['/\\\\', '\\\\/'])
        assert (art.width, art.height) == (2, 2)

        sprite = Drawing(
            ['#.', '.#'], kind='palette', palette={'#': (255, 0, 0), '.': None}
        )
        assert sprite.to_buffer().width == 2
        assert Drawing.from_value(sprite.to_value()) == sprite
        ```
    """

    @classmethod
    def from_value(cls, value: JSONValue) -> Drawing:
        """
        Build a drawing from the value that ``to_value`` produced.

        Examples:
            ```python
            art = Drawing(['ab'])
            assert Drawing.from_value(art.to_value()) == art
            ```
        """

    def __init__(
        self,
        rows: Sequence[str],
        *,
        kind: Literal['text', 'palette'] = 'text',
        palette: Mapping[str, tuple[int, int, int] | None] | None = None,
    ) -> None: ...
    @property
    def kind(self) -> Literal['text', 'palette']:
        """Whether the drawing holds terminal glyphs or palette pixels."""

    @property
    def rows(self) -> tuple[str, ...]:
        """The raw rows of the drawing."""

    @property
    def width(self) -> int:
        """Display columns for text; grapheme-token columns for palette pixels."""

    @property
    def height(self) -> int:
        """The number of rows."""

    @property
    def palette(self) -> Mapping[str, tuple[int, int, int] | None]:
        """The color of each palette symbol; empty for text drawings."""

    def to_value(self) -> dict[str, JSONValue]:
        """
        Return the drawing as JSON-compatible data.

        Examples:
            ```python
            assert Drawing(['ab']).to_value() == {'kind': 'text', 'rows': ['ab']}
            ```
        """

    def to_json(self) -> str:
        """
        Return the drawing as a JSON string.

        Examples:
            ```python
            assert Drawing(['ab']).to_json() == '{"kind":"text","rows":["ab"]}'
            ```
        """

    def to_buffer(self, *, encoding: PixelEncoding = 'half_blocks') -> Buffer:
        """
        Draw the picture into a new buffer.

        Args:
            encoding: How palette pixels pack into cells.

        Examples:
            ```python
            assert Drawing(['ab', 'cd']).to_buffer().text == 'ab\\ncd'
            ```
        """

    def to_cell_grid(self, *, encoding: PixelEncoding = 'half_blocks') -> bytes:
        """
        Pack the picture into the shared cell grid byte format.

        Args:
            encoding: How palette pixels pack into cells.

        Examples:
            ```python
            packed = Drawing(['ab', 'cd']).to_cell_grid()
            assert cell_grid_to_text(packed) == ['ab', 'cd']
            ```
        """

class DrawingFrame:
    """
    One frame of a [`DrawingAnimation`][xnano._xnano_core.DrawingAnimation].

    Args:
        drawing: The picture shown during this frame.
        duration_milliseconds: How long the frame stays on screen.

    Examples:
        ```python
        frame = DrawingFrame(Drawing(['a']), duration_milliseconds=50)
        assert frame.duration_milliseconds == 50
        assert frame.drawing.rows == ('a',)
        ```
    """

    def __init__(self, drawing: Drawing, *, duration_milliseconds: int = 100) -> None: ...
    @property
    def drawing(self) -> Drawing:
        """The picture shown during this frame."""

    @property
    def duration_milliseconds(self) -> int:
        """How long the frame stays on screen."""

class DrawingAnimation:
    """
    A sequence of timed drawings.

    Args:
        frames: The frames, shown in order. At least one frame is required.
        should_loop: Start again after the last frame.

    Examples:
        ```python
        animation = DrawingAnimation(
            [
                DrawingFrame(Drawing(['a']), duration_milliseconds=50),
                DrawingFrame(Drawing(['b']), duration_milliseconds=50),
            ]
        )
        assert len(animation.frames) == 2 and animation.should_loop
        ```
    """

    def __init__(
        self, frames: Sequence[DrawingFrame], *, should_loop: bool = True
    ) -> None: ...
    @property
    def frames(self) -> tuple[DrawingFrame, ...]:
        """The frames in display order."""

    @property
    def should_loop(self) -> bool:
        """Whether the animation starts again after the last frame."""

    def to_cell_animation(self, *, encoding: PixelEncoding = 'half_blocks') -> bytes:
        """
        Pack the animation into the shared cell animation byte format.

        Args:
            encoding: How palette pixels pack into cells.

        Examples:
            ```python
            animation = DrawingAnimation([DrawingFrame(Drawing(['a']))])
            info = inspect_cell_animation(animation.to_cell_animation())
            assert info.frame_count == 1
            ```
        """

class Draw(Operation):
    """
    Draw a [`Drawing`][xnano._xnano_core.Drawing] into the target.

    Args:
        drawing: The picture to draw.
        x: The column of the picture's top-left cell.
        y: The row of the picture's top-left cell.
        encoding: How palette pixels pack into cells.

    Examples:
        ```python
        buffer = Buffer(width=4, height=3)
        buffer.update(Draw(Drawing(['/\\\\', '\\\\/']), x=1, y=1))
        assert buffer.render(format='text').split('\\n')[1].strip() == '/\\\\'
        ```
    """

    def __init__(
        self,
        drawing: Drawing,
        *,
        x: int = 0,
        y: int = 0,
        encoding: PixelEncoding = 'half_blocks',
    ) -> None: ...

class AnimateDrawing(Operation):
    """
    Play a [`DrawingAnimation`][xnano._xnano_core.DrawingAnimation] on a mounted buffer.

    The animation runs on the runtime clock, so applying it needs a runtime.

    Args:
        animation: The animation to play.
        x: The column of the picture's top-left cell.
        y: The row of the picture's top-left cell.
        encoding: How palette pixels pack into cells.
        start_milliseconds: Where in the animation to start.

    Examples:
        ```python
        runtime = Runtime.offscreen(width=4, height=1)
        buffer = Buffer(width=4, height=1)
        runtime.mount(buffer, geometry='inherit')
        animation = DrawingAnimation(
            [
                DrawingFrame(Drawing(['a']), duration_milliseconds=50),
                DrawingFrame(Drawing(['b']), duration_milliseconds=50),
            ]
        )
        buffer.update(AnimateDrawing(animation))
        runtime.step()
        assert runtime.snapshot().lines()[0].strip() == 'a'
        runtime.advance_clock(50)
        runtime.step()
        assert runtime.snapshot().lines()[0].strip() == 'b'
        ```
    """

    def __init__(
        self,
        animation: DrawingAnimation,
        *,
        x: int = 0,
        y: int = 0,
        encoding: PixelEncoding = 'half_blocks',
        start_milliseconds: int = 0,
    ) -> None: ...

class Cell:
    """
    A detached grapheme with its style, copied out of or written into a surface.

    Reading ``buffer[column, row]`` returns a ``Cell`` snapshot; changing it does not
    change the buffer until it is written back with ``buffer[column, row] = cell``.
    A transparent cell lets the content below it show through when buffers are
    composited with the ``'transparent'`` blit mode.

    Maps to [`ratatui::buffer::Cell`](https://docs.rs/ratatui/0.30.0/ratatui/buffer/struct.Cell.html).

    Args:
        symbol: A single grapheme cluster. Defaults to one space.
        style: A complete style for the cell. Combined with the color and modifier
            arguments below, which take precedence.
        foreground: The foreground color.
        background: The background color.
        modifiers: Text modifiers such as ``'bold'`` or ``'underline'``.
        is_transparent: Whether the cell lets lower layers show through.

    Attributes:
        symbol: The grapheme drawn in the cell.
        style: The cell's style.
        is_transparent: Whether the cell lets lower layers show through.

    Raises:
        ValueError: ``symbol`` is not exactly one grapheme.

    Examples:
        ```python
        cell = Cell('x', foreground='red', modifiers=['bold'])
        assert cell.symbol == 'x'
        assert cell.foreground == Color('red')

        buffer = Buffer(width=3, height=1)
        buffer[1, 0] = cell
        assert buffer[1, 0].symbol == 'x'
        ```
    """

    symbol: str
    style: Style
    is_transparent: bool

    def __init__(
        self,
        symbol: str = ' ',
        *,
        style: Style | None = None,
        foreground: ColorValue | None = None,
        background: ColorValue | None = None,
        modifiers: Sequence[Modifier] = (),
        is_transparent: bool = False,
    ) -> None: ...
    @property
    def foreground(self) -> Color:
        """The foreground color of the cell."""

    @property
    def background(self) -> Color:
        """The background color of the cell."""

    def copy(self) -> Cell:
        """
        Return an independent copy of the cell.

        Examples:
            ```python
            original = Cell('a')
            duplicate = original.copy()
            duplicate.symbol = 'b'
            assert original.symbol == 'a'
            ```
        """

class PixelView:
    """
    A raster view that draws logical pixels into the cells of a surface.

    Half-block pixels have one column and two rows per cell. Braille pixels have
    two columns and four rows per cell, with one color per cell. The view owns no
    pixel store: every write reads the destination cells, changes the pixel and
    encodes the result back into those cells, so pixels share storage with text and
    styles. Overlapping writes follow input order. Pixels outside the view are
    clipped unless ``clip=False``, which raises ``IndexError`` before any cell is
    changed.

    Get one from [`Surface.pixels`][xnano._xnano_core.Surface.pixels].

    Examples:
        ```python
        buffer = Buffer(width=4, height=2)
        pixels = buffer.pixels()
        assert (pixels.width, pixels.height) == (4, 4)

        pixels.write([(0, 0, (255, 0, 0)), (0, 1, (0, 0, 255))])
        assert buffer[0, 0].symbol == '▀'
        assert buffer[0, 0].foreground == Color('#ff0000')
        assert buffer[0, 0].background == Color('#0000ff')
        ```
    """

    @property
    def surface(self) -> Surface:
        """The surface the pixels are drawn into."""

    @property
    def encoding(self) -> PixelEncoding:
        """How pixels are packed into cells: ``'half_blocks'`` or ``'braille'``."""

    @property
    def width(self) -> int:
        """The width of the view in pixels."""

    @property
    def height(self) -> int:
        """The height of the view in pixels."""

    def write(self, pixels: Iterable[Pixel], *, clip: bool = True) -> None:
        """
        Draw pixels in order.

        Args:
            pixels: ``(column, row, (red, green, blue))`` tuples.
            clip: Whether to skip pixels outside the view. With ``False`` a pixel
                outside the view raises ``IndexError`` and nothing is drawn.

        Raises:
            IndexError: ``clip`` is ``False`` and a pixel is outside the view.

        Examples:
            ```python
            pixels = Buffer(width=2, height=1).pixels(encoding='braille')
            pixels.write([(0, 0, (0, 255, 0)), (1, 3, (0, 255, 0))])
            assert pixels.surface[0, 0].symbol == '⢁'

            try:
                pixels.write([(99, 99, (0, 0, 0))], clip=False)
            except IndexError:
                pass
            ```
        """

    def blit_rgba(
        self,
        data: bytes,
        *,
        width: int,
        height: int,
        x: int = 0,
        y: int = 0,
        mode: RasterMode = 'over',
        clip: bool = True,
    ) -> None:
        """
        Draw a row-major RGBA8 image with its top-left pixel at ``(x, y)``.

        Args:
            data: ``width * height * 4`` bytes of red, green, blue and alpha.
            width: The image width in pixels.
            height: The image height in pixels.
            x: The pixel column of the image's left edge.
            y: The pixel row of the image's top edge.
            mode: ``'over'`` blends by alpha against what is already drawn;
                ``'replace'`` overwrites, and fully transparent pixels erase.
            clip: Whether to skip pixels outside the view.

        Raises:
            IndexError: ``clip`` is ``False`` and the image extends outside the view.

        Examples:
            ```python
            buffer = Buffer(width=2, height=1)
            red = bytes([255, 0, 0, 255]) * 4
            buffer.pixels().blit_rgba(red, width=2, height=2)
            assert buffer[0, 0].background == Color('#ff0000')
            ```
        """

    def cell_at(self, pixel_column: int, pixel_row: int) -> Coordinate:
        """
        Return the ``(column, row)`` of the cell that holds a pixel.

        Examples:
            ```python
            pixels = Buffer(width=4, height=2).pixels()
            assert pixels.cell_at(2, 3) == (2, 1)
            ```
        """

    def pixel_at(
        self,
        column: int,
        row: int,
        *,
        anchor: PixelAnchor = 'center',
    ) -> Coordinate:
        """
        Return the pixel at an anchor of a cell.

        Terminal mouse input reports cells, so this picks one logical pixel of the
        cell the pointer is over.

        Args:
            column: The cell column.
            row: The cell row.
            anchor: ``'top_left'``, ``'center'`` or ``'bottom_right'``.

        Examples:
            ```python
            pixels = Buffer(width=4, height=2).pixels()
            assert pixels.pixel_at(1, 1, anchor='top_left') == (1, 2)
            ```
        """

class Surface:
    """
    A grid of cells that text, styles, pixels and operations can be applied to.

    [`Buffer`][xnano._xnano_core.Buffer] and [`Region`][xnano._xnano_core.Region] are
    surfaces. Index with ``surface[column, row]`` for a
    [`Cell`][xnano._xnano_core.Cell] or ``surface[columns, rows]`` with two slices for
    a [`Region`][xnano._xnano_core.Region]. Indexes start at ``(0, 0)`` in the top-left
    corner.

    Examples:
        ```python
        buffer = Buffer(width=8, height=3)
        buffer.write('hello', x=1, y=1)
        assert buffer[1, 1].symbol == 'h'

        corner = buffer[slice(0, 4), slice(0, 2)]
        corner.fill('.')
        assert buffer[0, 0].symbol == '.'
        ```
    """

    @property
    def width(self) -> int:
        """The surface width in cells."""

    @property
    def height(self) -> int:
        """The surface height in cells."""

    @overload
    def __getitem__(self, key: Coordinate) -> Cell: ...
    @overload
    def __getitem__(self, key: tuple[slice, slice]) -> Region: ...
    def __setitem__(self, key: Coordinate, value: Cell | str) -> None:
        """
        Replace one cell with a ``Cell`` or a single grapheme.

        Examples:
            ```python
            buffer = Buffer(width=3, height=1)
            buffer[2, 0] = 'z'
            buffer[0, 0] = Cell('a', foreground='green')
            assert buffer.text == 'a z'
            ```
        """

    def write(
        self,
        text: TextContent,
        *,
        x: int = 0,
        y: int = 0,
        style: Style | None = None,
        mode: WriteMode = 'replace',
    ) -> None:
        """
        Write text starting at a cell.

        Text is clipped by display columns, whole graphemes are kept together and the
        continuation cells of wide characters are repaired.

        Args:
            text: A string or styled text.
            x: The starting column.
            y: The starting row.
            style: A style applied to the written cells.
            mode: ``'replace'`` overwrites the cell; ``'preserve_background'`` keeps
                the background already there.

        Examples:
            ```python
            buffer = Buffer(width=6, height=2)
            buffer.write('hi', x=1, y=0, style=Style(foreground='red'))
            assert buffer[1, 0].foreground == Color('red')
            assert buffer.text.split('\\n')[0] == ' hi'
            ```
        """

    def fill(self, cell: Cell | str = ' ') -> None:
        """
        Set every cell of the surface.

        Examples:
            ```python
            buffer = Buffer(width=3, height=1)
            buffer.fill('#')
            assert buffer.text == '###'
            ```
        """

    def pixels(self, *, encoding: PixelEncoding = 'half_blocks') -> PixelView:
        """
        Return a pixel view that draws into this surface.

        Args:
            encoding: ``'half_blocks'`` for one column and two rows per cell or
                ``'braille'`` for two columns and four rows per cell.

        Examples:
            ```python
            buffer = Buffer(width=3, height=2)
            assert (buffer.pixels().width, buffer.pixels().height) == (3, 4)
            assert (buffer.pixels(encoding='braille').width) == 6
            ```
        """

    def update(self, *operations: Operation) -> None:
        """
        Apply operations in argument order.

        Raises:
            UnsupportedOperationError: The surface's registry cannot apply an operation.
            RuntimeRequiredError: An operation needs a mounted buffer on a runtime.

        Examples:
            ```python
            buffer = Buffer(width=8, height=3)
            buffer.update(Border('rounded'), Write('hi', x=1, y=1))
            assert buffer[0, 0].symbol == '╭'
            assert buffer[1, 1].symbol == 'h'
            ```
        """

    def inspect(self, expression: Expression[ValueType]) -> ValueType:
        """
        Evaluate an expression against this surface and return its value.

        Examples:
            ```python
            width = _reference('Width', 'numeric_property')
            height = _reference('Height', 'numeric_property')
            buffer = Buffer(width=8, height=3)
            assert buffer.inspect(width) == 8
            assert buffer.inspect(width * height) == 24
            ```
        """

    def supports(self, operation: type[Operation]) -> bool:
        """
        Return whether the surface's registry can apply an operation type.

        Examples:
            ```python
            assert Buffer(width=1, height=1).supports(Write)
            ```
        """

    def add_hook(
        self,
        callback: HookCallback,
        *,
        condition: Predicate | None = None,
        events: Sequence[HookEventKind] = ('tick',),
        priority: int = 0,
        once: bool = False,
    ) -> Hook:
        """
        Run a callback when the runtime reports matching events for this surface.

        Args:
            callback: Called with a context for the event.
            condition: An expression that must be true for the callback to run.
            events: The event kinds to listen to.
            priority: Hooks with higher priority run first.
            once: Whether to remove the hook after its first run.

        Returns:
            The registered hook, which can be cancelled.

        Examples:
            ```python
            keys = []
            with Runtime.offscreen(width=10, height=2) as runtime:
                buffer = Buffer()
                runtime.mount(buffer, geometry='inherit')
                buffer.add_hook(lambda context: keys.append(context.event.key.key), events=['key'])
                runtime.dispatch(Event.key_press('a'))
                runtime.step()
            assert keys == ['a']
            ```
        """

    def invalidate(self, area: Rectangle | None = None) -> None:
        """
        Ask the runtime to redraw an area, or the whole surface.

        Examples:
            ```python
            buffer = Buffer(width=4, height=2)
            buffer.invalidate(Rectangle(0, 0, 2, 1))
            ```
        """

    def to_cell_grid(self) -> bytes:
        """
        Pack the surface into the cell grid byte format.

        Examples:
            ```python
            packed = Buffer.with_text('abc').to_cell_grid()
            assert cell_grid_to_text(packed) == ['abc']
            ```
        """

class Region(Surface):
    """
    A fixed rectangle of a buffer that shares the buffer's cells.

    Indexes into a region are relative to its top-left corner. After the buffer is
    resized, the region stays usable only while its whole rectangle still fits;
    otherwise access raises ``InvalidRegionError``. Use ``copy()`` for an
    independent buffer.

    Examples:
        ```python
        buffer = Buffer(width=6, height=2)
        region = buffer.region(Rectangle(2, 0, 3, 2))
        region.fill('*')
        assert buffer[2, 0].symbol == '*'
        assert buffer[1, 0].symbol == ' '

        buffer.resize(3, 2)
        assert not region.is_valid
        ```
    """

    @property
    def buffer(self) -> Buffer:
        """The buffer the region belongs to."""

    @property
    def bounds(self) -> Rectangle:
        """The region's rectangle in its buffer."""

    @property
    def is_valid(self) -> bool:
        """Whether the whole rectangle still fits inside the buffer."""

    def copy(self) -> Buffer:
        """
        Copy the region's cells into a new buffer.

        Examples:
            ```python
            buffer = Buffer(width=4, height=1)
            buffer.write('abcd')
            copy = buffer.region(Rectangle(1, 0, 2, 1)).copy()
            assert copy.text == 'bc'
            ```
        """

class Buffer(Surface):
    """
    A layer of cells with a position, a size and the hooks that animate it.

    A buffer owns its cells, its geometry, its hook registrations and its place in a
    tree: it has at most one parent and is mounted on at most one runtime. Direct
    writes and operations share validation and revision tracking. Changing
    ``width`` or ``height`` keeps the cells that still fit and blanks new ones.
    Moving a mounted buffer redraws both its old and new area.

    Args:
        content: Text to start with. Without ``width`` and ``height`` the buffer is
            sized to fit it.
        width: The width in cells.
        height: The height in cells.
        x: The column of the buffer in its parent.
        y: The row of the buffer in its parent.
        style: A style applied to the initial content.
        registry: The operation registry; defaults to the shared default registry.

    Examples:
        ```python
        card = Buffer(width=12, height=3, x=2, y=1)
        card.update(Border('rounded'))
        card.write('hello', x=1, y=1)
        print(card.render(format='text'))

        sized = Buffer('two\\nlines')
        assert (sized.width, sized.height) == (5, 2)
        ```
    """

    @property
    def _absolute_bounds(self) -> Rectangle: ...
    def __init__(
        self,
        content: TextContent | None = None,
        *,
        width: int | None = None,
        height: int | None = None,
        x: int = 0,
        y: int = 0,
        style: Style | None = None,
        registry: Registry | None = None,
    ) -> None: ...
    @property
    def x(self) -> int:
        """The column of the buffer in its parent. Assigning moves the buffer."""

    @x.setter
    def x(self, value: int) -> None: ...
    @property
    def y(self) -> int:
        """The row of the buffer in its parent. Assigning moves the buffer."""

    @y.setter
    def y(self, value: int) -> None: ...
    @property
    def width(self) -> int:
        """The width in cells. Assigning resizes the buffer."""

    @width.setter
    def width(self, value: int) -> None: ...
    @property
    def height(self) -> int:
        """The height in cells. Assigning resizes the buffer."""

    @height.setter
    def height(self, value: int) -> None: ...
    @property
    def position(self) -> Point:
        """The ``Point`` of the buffer in its parent. Assigning moves the buffer."""

    @position.setter
    def position(self, value: Point) -> None: ...
    @property
    def size(self) -> Size:
        """The ``Size`` of the buffer. Assigning resizes the buffer."""

    @size.setter
    def size(self, value: Size) -> None: ...
    @property
    def bounds(self) -> Rectangle:
        """The buffer's rectangle in its parent."""

    @property
    def layer(self) -> int:
        """
        The stacking order among siblings; higher layers are drawn on top.

        Examples:
            ```python
            parent = Buffer(width=6, height=1)
            below = Buffer('a')
            above = Buffer('b')
            parent.attach(below)
            parent.attach(above)
            below.layer = 1
            assert parent.render(format='text') == 'a'
            ```
        """

    @layer.setter
    def layer(self, value: int) -> None: ...
    @property
    def is_visible(self) -> bool:
        """Whether the buffer is drawn. Hidden buffers still keep their content."""

    @is_visible.setter
    def is_visible(self, value: bool) -> None: ...
    @property
    def is_focusable(self) -> bool:
        """Whether the buffer can receive input focus."""

    @is_focusable.setter
    def is_focusable(self, value: bool) -> None: ...
    @property
    def content(self) -> Region:
        """The whole buffer as a region. Assigning text replaces the content."""

    @content.setter
    def content(self, value: TextContent) -> None: ...
    @property
    def cells(self) -> Region:
        """The same view as ``content``; there is only one store of cells."""

    @property
    def text(self) -> str:
        """The plain text of the buffer's own cells, without mounted children."""

    @property
    def revision(self) -> int:
        """A number that increases every time the buffer's cells or geometry change."""

    @property
    def children(self) -> tuple[Buffer, ...]:
        """The attached child buffers in attachment order."""

    @classmethod
    def with_text(cls, text: TextContent, *, style: Style | None = None) -> Buffer:
        """
        Create a buffer sized to fit some text.

        Examples:
            ```python
            buffer = Buffer.with_text('abc')
            assert (buffer.width, buffer.height) == (3, 1)
            ```
        """

    @classmethod
    def with_size(cls, width: int, height: int) -> Buffer:
        """
        Create a blank buffer of a given size.

        Examples:
            ```python
            assert Buffer.with_size(5, 2).width == 5
            ```
        """

    @classmethod
    def with_cells(cls, cells: Sequence[Cell], *, width: int, height: int) -> Buffer:
        """
        Create a buffer from cells in row-major order.

        Examples:
            ```python
            buffer = Buffer.with_cells([Cell('a'), Cell('b')], width=2, height=1)
            assert buffer.text == 'ab'
            ```
        """

    @classmethod
    def from_cell_grid(cls, packed: bytes) -> Buffer:
        """
        Create a buffer from the cell grid byte format.

        Raises:
            CellGridError: The bytes are not a valid cell grid.

        Examples:
            ```python
            packed = Buffer.with_text('hi').to_cell_grid()
            assert Buffer.from_cell_grid(packed).text == 'hi'
            ```
        """

    @classmethod
    def from_cell_animation(cls, packed: bytes, *, start_milliseconds: int = 0) -> Buffer:
        """
        Create a buffer showing one frame of a packed cell animation.

        Args:
            packed: The cell animation bytes.
            start_milliseconds: The point in the animation to show.

        Raises:
            CellGridError: The bytes are not a valid cell animation.

        Examples:
            ```python
            frames = [Buffer.with_text('a').to_cell_grid(), Buffer.with_text('b').to_cell_grid()]
            packed = pack_cell_animation(frames, frame_durations_milliseconds=[50, 50])
            assert Buffer.from_cell_animation(packed, start_milliseconds=60).text == 'b'
            ```
        """

    def region(self, bounds: Rectangle) -> Region:
        """
        Return a region covering a rectangle of the buffer.

        Examples:
            ```python
            buffer = Buffer(width=4, height=2)
            assert buffer.region(Rectangle(1, 0, 2, 2)).bounds == Rectangle(1, 0, 2, 2)
            ```
        """

    def resize(self, width: int, height: int) -> None:
        """
        Change the size, keeping the cells that still fit.

        Examples:
            ```python
            buffer = Buffer.with_text('abcd')
            buffer.resize(2, 1)
            assert buffer.text == 'ab'
            ```
        """

    def blit(
        self,
        source: Buffer | Region,
        *,
        x: int = 0,
        y: int = 0,
        mode: BlitMode = 'replace',
    ) -> None:
        """
        Copy the cells of another buffer or region into this one.

        Args:
            source: The cells to copy.
            x: The destination column of the source's left edge.
            y: The destination row of the source's top edge.
            mode: ``'replace'`` copies every cell, ``'preserve_background'`` keeps
                the destination background and ``'transparent'`` skips cells that
                are marked transparent.

        Examples:
            ```python
            sprite = Buffer.with_text('ab')
            canvas = Buffer(width=5, height=1)
            canvas.blit(sprite, x=2)
            assert canvas.text == '  ab'
            ```
        """

    def attach(
        self,
        child: Buffer,
        *,
        geometry: GeometryMode = 'explicit',
        mode: BlitMode = 'replace',
    ) -> None:
        """
        Attach a child buffer as a retained layer of this one.

        The child keeps its own cells and is composited when this buffer is drawn,
        ordered by ``layer`` and then by attachment order. A child with
        ``geometry='inherit'`` always fills the parent's content rectangle. The
        ``'transparent'`` mode skips cells explicitly marked transparent, not spaces.

        Raises:
            ValueError: The child already has a parent.

        Examples:
            ```python
            parent = Buffer(width=8, height=3)
            child = Buffer('hi', x=2, y=1)
            parent.attach(child)
            assert parent.children == (child,)
            assert parent.render(format='text').split('\\n')[1] == '  hi'
            ```
        """

    def detach(self, child: Buffer) -> None:
        """
        Remove an attached child.

        Examples:
            ```python
            parent = Buffer(width=4, height=1)
            child = Buffer('x')
            parent.attach(child)
            parent.detach(child)
            assert parent.children == ()
            ```
        """

    def copy(self) -> Buffer:
        """
        Copy the cells, geometry and children into a new, independent buffer.

        Hooks and runtime state are not copied.

        Examples:
            ```python
            original = Buffer.with_text('a')
            duplicate = original.copy()
            duplicate.write('b')
            assert original.text == 'a'
            ```
        """

    @property
    def registry(self) -> Registry:
        """The registry that decides which operations this buffer can apply."""

    def supports(self, operation: type[Operation]) -> bool:
        """
        Return whether the buffer's registry can apply an operation type.

        Examples:
            ```python
            assert Buffer(width=1, height=1).supports(Fill)
            ```
        """

    def __call__(self, *, runtime: Runtime | None = None) -> Rendering:
        """
        Return a lazy render of the buffer.

        ``str(rendering)`` serializes the buffer without touching a terminal. Using
        the result as a context manager mounts the buffer on ``runtime`` (or opens a
        live runtime) and unmounts it on exit.

        Examples:
            ```python
            buffer = Buffer.with_text('hi')
            assert 'hi' in str(buffer())

            with Runtime.offscreen(width=8, height=2) as runtime:
                with buffer(runtime=runtime) as context:
                    assert context.runtime is runtime
            ```
        """

    def render(self, *, format: RenderFormat = 'ansi') -> str:
        """
        Compose the visible children and serialize the buffer.

        No terminal or device is opened.

        Args:
            format: ``'text'`` for plain rows or ``'ansi'`` for text with styling
                escape sequences.

        Examples:
            ```python
            buffer = Buffer.with_text('hi', style=Style(foreground='red'))
            assert buffer.render(format='text') == 'hi'
            assert '\\x1b[' in buffer.render(format='ansi')
            ```
        """

class StepResult:
    """
    What one ``Runtime.step()`` did.

    Examples:
        ```python
        with Runtime.offscreen(width=8, height=2) as runtime:
            runtime.mount(Buffer.with_text('hi'))
            result = runtime.step()
            assert result.did_render and result.is_running
        ```
    """

    @property
    def events_processed(self) -> int:
        """The number of events dispatched to hooks."""

    @property
    def updates_processed(self) -> int:
        """The number of simulation updates run."""

    @property
    def did_render(self) -> bool:
        """Whether a frame was drawn."""

    @property
    def is_running(self) -> bool:
        """Whether the runtime is still running after the step."""

class Runtime:
    """
    A session that mounts buffers, runs hooks and schedules, and draws frames.

    A runtime is either live, drawing to the terminal with input negotiated and
    restored for you, or offscreen, drawing into memory with a manual clock so tests
    and tools are deterministic. Construction is lazy: entering the runtime as a
    context manager (or calling ``run()``) opens the session on the owning thread.
    Frames are drawn only when something changed; timers, effects, resizes and
    animation deadlines wake the runtime. Only ``call_soon_threadsafe`` and
    [`Waker`][xnano._xnano_core.Waker] may be used from other threads.

    Examples:
        ```python
        with Runtime.offscreen(width=20, height=3) as runtime:
            buffer = Buffer()
            runtime.mount(buffer, geometry='inherit')
            buffer.write('hello')
            runtime.step()
            assert runtime.snapshot().lines()[0].startswith('hello')
        ```
    """

    def _animate(
        self,
        target: Buffer | Region,
        packed: bytes,
        *,
        x: int = 0,
        y: int = 0,
        start_milliseconds: int = 0,
        key: str | None = None,
    ) -> None: ...
    def _stop_animation(self, key: str) -> None: ...
    @property
    def registry(self) -> Registry:
        """The runtime's own copy of the operation registry."""

    def _register_store(self, store: TerminalStateStore) -> None: ...
    def _add_notifier(self, notifier: Callable[[], object]) -> int: ...
    def _remove_notifier(self, token: int) -> None: ...
    def _next_deadline_seconds(self) -> float | None: ...
    def _has_pending(self) -> bool: ...
    def _nudge(self) -> None: ...
    def _consume_pointer(self, buffer: Buffer, should_capture: bool) -> None: ...
    def _focus(self, buffer: Buffer) -> bool: ...
    def _is_focused(self, buffer: Buffer) -> bool: ...
    def _fire(
        self, buffer: Buffer, kind: str, state_change: TerminalStateChange | None
    ) -> None: ...
    @classmethod
    def live(
        cls,
        *,
        tick_interval_milliseconds: int | None = None,
        frame_interval_milliseconds: int = 16,
        inline_height: int | None = None,
        should_handle_exit_signals: bool = True,
        options: TerminalOptions | None = None,
        registry: Registry | None = None,
    ) -> Runtime:
        """
        Create a runtime that draws to the terminal and reads its input.

        Live runtimes use a monotonic clock. Terminal modes the runtime turns on are
        restored on every exit path.

        Args:
            tick_interval_milliseconds: How often ``'tick'`` events fire, or ``None``
                for no ticks.
            frame_interval_milliseconds: The shortest time between frames.
            inline_height: Draw this many rows inline instead of taking over the
                whole screen.
            should_handle_exit_signals: Whether interrupt and terminate signals
                request an exit.
            options: Raw mode, alternate screen and input negotiation settings.
            registry: The operation registry for the runtime.

        Examples:
            ```python
            runtime = Runtime.live(frame_interval_milliseconds=33)
            assert not runtime.is_closed
            runtime.close()
            ```
        """

    @classmethod
    def offscreen(
        cls,
        *,
        width: int,
        height: int,
        tick_interval_milliseconds: int | None = None,
        frame_interval_milliseconds: int = 16,
        clock: Clock | None = None,
        registry: Registry | None = None,
    ) -> Runtime:
        """
        Create a runtime that draws into memory.

        Offscreen runtimes default to a manual clock that only moves with
        ``advance_clock`` and never negotiate terminal capabilities.

        Examples:
            ```python
            runtime = Runtime.offscreen(width=40, height=10)
            assert runtime.clock.source == 'manual'
            assert runtime.device.size == Size(40, 10)
            runtime.close()
            ```
        """

    @property
    def clock(self) -> Clock:
        """The clock all schedules and timers run on."""

    @property
    def device(self) -> Device:
        """The output device: its size and capabilities."""

    @property
    def input(self) -> InputState:
        """The pressed keys and pointer position."""

    @property
    def router(self) -> InputRouter:
        """The input router that decides which buffer receives each event."""

    @property
    def frame_metrics(self) -> FrameMetrics:
        """Timing of the frames drawn so far."""

    @property
    def is_running(self) -> bool:
        """Whether the runtime has been entered and not stopped."""

    @property
    def is_closed(self) -> bool:
        """Whether ``close()`` has run."""

    @property
    def buffers(self) -> tuple[Buffer, ...]:
        """The mounted root buffers."""

    @property
    def needs_frame(self) -> bool:
        """Whether the next step will draw a frame."""

    def mount(
        self,
        buffer: Buffer,
        *,
        key: str | None = None,
        geometry: GeometryMode = 'explicit',
    ) -> CoreContext:
        """
        Mount a root buffer so it is drawn and receives events.

        Args:
            buffer: The buffer to mount. It must not have a parent.
            key: A name for the mount.
            geometry: ``'inherit'`` fits the buffer to the viewport on every frame;
                ``'explicit'`` keeps its own position and size and clips it.

        Returns:
            A context for the buffer on this runtime.

        Examples:
            ```python
            with Runtime.offscreen(width=10, height=2) as runtime:
                buffer = Buffer()
                context = runtime.mount(buffer, geometry='inherit')
                assert buffer.width == 10
                assert context.runtime is runtime
            ```
        """

    def unmount(self, buffer: Buffer) -> None:
        """
        Stop drawing a mounted buffer.

        Examples:
            ```python
            with Runtime.offscreen(width=10, height=2) as runtime:
                buffer = Buffer.with_text('x')
                runtime.mount(buffer)
                runtime.unmount(buffer)
                assert runtime.buffers == ()
            ```
        """

    def dispatch(self, event: Event) -> None:
        """
        Deliver an event to the hooks as if the terminal had reported it.

        Examples:
            ```python
            seen = []
            with Runtime.offscreen(width=10, height=2) as runtime:
                buffer = Buffer()
                runtime.mount(buffer, geometry='inherit')
                buffer.add_hook(lambda context: seen.append(context.event.key.key), events=['key'])
                runtime.dispatch(Event.key_press('q'))
                runtime.step()
            assert seen == ['q']
            ```
        """

    def inject(self, event: Event) -> None:
        """
        Queue an event for the runtime's event stream and hooks.

        Examples:
            ```python
            with Runtime.offscreen(width=10, height=2) as runtime:
                stream = runtime.events()
                runtime.inject(Event.key_press('x'))
                assert next(stream).key.key == 'x'
            ```
        """

    def events(self) -> EventStream:
        """
        Return a stream of the events the runtime dispatches.

        The stream is iterable and async-iterable; each step of the loop that waits
        for an event also drives the runtime.

        Examples:
            ```python
            with Runtime.offscreen(width=10, height=2) as runtime:
                stream = runtime.events()
                runtime.inject(Event.focus_gained())
                assert next(stream).kind == 'focus_gained'
            ```
        """

    def waker(self) -> Waker:
        """
        Return a handle that other threads can use to wake the runtime.

        Examples:
            ```python
            with Runtime.offscreen(width=10, height=2) as runtime:
                waker = runtime.waker()
                waker.wake()
                runtime.step()
            ```
        """

    def on_update(
        self,
        callback: Callable[[UpdateContext], None],
        *,
        target: Buffer,
        clock: Clock | SimulationClock | None = None,
        fixed_step_seconds: float | None = None,
        maximum_delta_seconds: float | None = None,
        maximum_catch_up_steps: int = 4,
        overflow: Literal['drop', 'retain'] = 'drop',
    ) -> Hook:
        """
        Run simulation updates separately from display frames.

        With variable steps the callback receives the time since the last update,
        optionally clamped by ``maximum_delta_seconds`` without changing the raw
        clock. With ``fixed_step_seconds`` the callback runs once per whole step
        elapsed, at most ``maximum_catch_up_steps`` per iteration; ``overflow``
        decides whether the time beyond that is dropped or kept for later.

        Examples:
            ```python
            deltas = []
            with Runtime.offscreen(width=10, height=2) as runtime:
                buffer = Buffer()
                runtime.mount(buffer)
                runtime.on_update(
                    lambda context: deltas.append(round(context.delta_seconds, 2)),
                    target=buffer,
                    fixed_step_seconds=0.05,
                )
                runtime.advance_clock(100)
                runtime.step()
            assert deltas == [0.05, 0.05]
            ```
        """

    def on_frame(
        self, callback: Callable[[FrameContext], None], *, target: Buffer
    ) -> Hook:
        """
        Run a callback before each display frame with that frame's area.

        Examples:
            ```python
            areas = []
            with Runtime.offscreen(width=10, height=2) as runtime:
                buffer = Buffer()
                runtime.mount(buffer, geometry='inherit')
                runtime.on_frame(lambda context: areas.append(context.area), target=buffer)
                runtime.request_frame()
                runtime.step()
            assert areas[0] == Rectangle(0, 0, 10, 2)
            ```
        """

    def on_render_error(self, callback: Callable[[RenderError], None]) -> Hook:
        """
        Handle recoverable render errors.

        A failed frame is not committed and the last good frame stays. Interrupts and
        unknown failures still propagate.

        Examples:
            ```python
            errors = []
            with Runtime.offscreen(width=10, height=2) as runtime:
                runtime.on_render_error(errors.append)
            ```
        """

    def call_later(
        self,
        seconds: float,
        callback: Callable[[], None],
        *,
        clock: Clock | SimulationClock | None = None,
    ) -> ScheduledCall:
        """
        Run a callback once after a delay on a clock.

        Args:
            seconds: The delay.
            callback: Called with no arguments.
            clock: The clock to schedule on; defaults to the runtime's clock.

        Examples:
            ```python
            calls = []
            with Runtime.offscreen(width=10, height=2) as runtime:
                runtime.call_later(0.05, lambda: calls.append('later'))
                runtime.advance_clock(50)
                runtime.step()
            assert calls == ['later']
            ```
        """

    def call_every(
        self,
        seconds: float,
        callback: Callable[[], None],
        *,
        clock: Clock | SimulationClock | None = None,
    ) -> ScheduledCall:
        """
        Run a callback repeatedly at an interval on a clock.

        Examples:
            ```python
            calls = []
            with Runtime.offscreen(width=10, height=2) as runtime:
                schedule = runtime.call_every(0.1, lambda: calls.append(1))
                runtime.advance_clock(100)
                runtime.step()
                schedule.cancel()
            assert calls == [1]
            ```
        """

    def call_soon_threadsafe(self, callback: Callable[[], None]) -> None:
        """
        Run a callback on the runtime's thread at its next step.

        This is safe to call from any thread.

        Examples:
            ```python
            calls = []
            with Runtime.offscreen(width=10, height=2) as runtime:
                runtime.call_soon_threadsafe(lambda: calls.append('ran'))
                runtime.step()
            assert calls == ['ran']
            ```
        """

    def start_timer(
        self, key: str, *, interval_milliseconds: int, should_repeat: bool = True
    ) -> None:
        """
        Start a named timer that emits ``'timer'`` events.

        Examples:
            ```python
            with Runtime.offscreen(width=10, height=2) as runtime:
                runtime.start_timer('blink', interval_milliseconds=500)
                assert runtime.stop_timer('blink')
            ```
        """

    def stop_timer(self, key: str) -> bool:
        """
        Stop a named timer. Returns whether a timer with that name was running.

        Examples:
            ```python
            with Runtime.offscreen(width=10, height=2) as runtime:
                assert not runtime.stop_timer('missing')
            ```
        """

    def request_frame(self) -> None:
        """
        Ask for a frame at the next step even if nothing changed.

        Examples:
            ```python
            with Runtime.offscreen(width=10, height=2) as runtime:
                runtime.request_frame()
                assert runtime.needs_frame
            ```
        """

    def step(self, *, timeout_milliseconds: int | None = 0) -> StepResult:
        """
        Run one iteration of the loop.

        Waits at most ``timeout_milliseconds`` (or until the next deadline) for
        work, then processes a bounded number of events so input cannot starve
        drawing.

        Examples:
            ```python
            with Runtime.offscreen(width=10, height=2) as runtime:
                runtime.mount(Buffer.with_text('hi'))
                assert runtime.step().did_render
            ```
        """

    def advance_clock(self, milliseconds: int) -> None:
        """
        Move a manual clock forward.

        Raises:
            ValueError: The runtime's clock is not a manual clock.

        Examples:
            ```python
            with Runtime.offscreen(width=10, height=2) as runtime:
                runtime.advance_clock(250)
                assert runtime.clock.elapsed_seconds == 0.25
            ```
        """

    def resize(self, *, width: int, height: int) -> None:
        """
        Resize an offscreen destination and queue a matching resize event.

        Examples:
            ```python
            with Runtime.offscreen(width=10, height=2) as runtime:
                runtime.resize(width=20, height=4)
                assert runtime.device.size == Size(20, 4)
            ```
        """

    def render(self) -> FrameSnapshot:
        """
        Draw a frame now and return it.

        Only a frame that renders successfully replaces the last snapshot.

        Examples:
            ```python
            with Runtime.offscreen(width=10, height=2) as runtime:
                runtime.mount(Buffer.with_text('hi'))
                assert runtime.render().lines()[0].startswith('hi')
            ```
        """

    def snapshot(self) -> FrameSnapshot:
        """
        Return the last successfully drawn frame.

        Examples:
            ```python
            with Runtime.offscreen(width=10, height=2) as runtime:
                runtime.mount(Buffer.with_text('hi'))
                runtime.step()
                assert runtime.snapshot().text.startswith('hi')
            ```
        """

    def run(self) -> None:
        """
        Run the loop until the runtime is stopped.

        Examples:
            ```python
            runtime = Runtime.offscreen(width=10, height=2)
            runtime.call_later(0.01, runtime.stop)
            runtime.advance_clock(10)
            runtime.run()
            assert not runtime.is_running
            runtime.close()
            ```
        """

    def stop(self) -> None:
        """
        Ask the loop to stop after the current step.

        Examples:
            ```python
            with Runtime.offscreen(width=10, height=2) as runtime:
                runtime.stop()
                assert not runtime.is_running
            ```
        """

    def close(self) -> None:
        """
        Close the session and restore every terminal mode the runtime turned on.

        Examples:
            ```python
            runtime = Runtime.offscreen(width=10, height=2)
            runtime.close()
            assert runtime.is_closed
            ```
        """

    def __enter__(self) -> Runtime: ...
    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]: ...
    @property
    def effects(self) -> EffectManager: ...
    def watch_state(self, reference: StateReference | TerminalStateStore) -> None: ...

class FrameMetrics:
    """
    Timing of the frames a runtime has drawn.

    Examples:
        ```python
        with Runtime.offscreen(width=10, height=2) as runtime:
            runtime.mount(Buffer.with_text('hi'))
            runtime.step()
            metrics = runtime.frame_metrics
            assert metrics.frames == 1
            assert metrics.last_frame_microseconds >= 0
        ```
    """

    @property
    def frames(self) -> int:
        """The number of frames drawn."""

    @property
    def last_frame_microseconds(self) -> int:
        """How long the last frame took to draw, in microseconds."""

    @property
    def average_frame_microseconds(self) -> int:
        """The mean frame time, in microseconds."""

class FrameSnapshot:
    """
    An immutable copy of a drawn frame.

    Examples:
        ```python
        with Runtime.offscreen(width=10, height=2) as runtime:
            runtime.mount(Buffer.with_text('hi'))
            frame = runtime.render()
            assert frame.size == Size(10, 2)
            assert frame.lines()[0].startswith('hi')
            assert cell_grid_size(frame.to_cell_grid()) == (10, 2)
        ```
    """

    @property
    def size(self) -> Size:
        """The size of the frame in cells."""

    @property
    def revision(self) -> int:
        """A number that increases with every committed frame."""

    @property
    def cursor_position(self) -> Point | None:
        """Where the cursor is, or ``None`` when no cursor is placed."""

    @property
    def is_cursor_visible(self) -> bool:
        """Whether the cursor is shown."""

    @property
    def text(self) -> str:
        """The frame's plain text rows joined by newlines."""

    @property
    def ansi(self) -> str:
        """The frame as text with styling escape sequences."""

    def lines(self) -> list[str]:
        """
        Return the plain text rows of the frame.

        Examples:
            ```python
            with Runtime.offscreen(width=4, height=2) as runtime:
                runtime.mount(Buffer.with_text('ab'))
                assert runtime.render().lines()[0].startswith('ab')
            ```
        """

    def to_cell_grid(self) -> bytes:
        """
        Pack the frame into the cell grid byte format.

        Examples:
            ```python
            with Runtime.offscreen(width=4, height=2) as runtime:
                runtime.mount(Buffer.with_text('ab'))
                packed = runtime.render().to_cell_grid()
                assert cell_grid_size(packed) == (4, 2)
            ```
        """

class RenderError(RuntimeError):
    """
    A recoverable failure while drawing a frame; the failed frame is not committed.

    Examples:
        ```python
        assert issubclass(RenderError, RuntimeError)
        ```
    """

class UnsupportedOperationError(TypeError):
    """
    The registry of the target cannot apply the operation it was given.

    Examples:
        ```python
        class Unknown(Operation):
            pass

        try:
            Buffer(width=1, height=1).update(Unknown())
        except UnsupportedOperationError as error:
            assert 'registry.install' in str(error)
        ```
    """

class RuntimeRequiredError(RuntimeError):
    """
    An operation needs a buffer mounted on an active runtime.

    Examples:
        ```python
        assert issubclass(RuntimeRequiredError, RuntimeError)
        ```
    """

class InvalidRegionError(RuntimeError):
    """
    A region no longer fits inside its resized buffer.

    Examples:
        ```python
        buffer = Buffer(width=6, height=1)
        region = buffer.region(Rectangle(3, 0, 3, 1))
        buffer.resize(4, 1)
        try:
            region.fill('x')
        except InvalidRegionError:
            pass
        ```
    """

class CellGridError(ValueError):
    """
    Packed cell data is malformed, incompatible or over a resource limit.

    Examples:
        ```python
        try:
            inspect_cell_grid(b'not a cell grid')
        except CellGridError as error:
            assert 'cell grid' in str(error)
        ```
    """

class CellGridInfo:
    """
    The header of a packed cell grid.

    Examples:
        ```python
        info = inspect_cell_grid(Buffer.with_text('abc').to_cell_grid())
        assert (info.columns, info.rows) == (3, 1)
        assert info.required_protocol is None
        ```
    """

    @property
    def format_version(self) -> int:
        """The version of the cell grid byte format."""

    @property
    def columns(self) -> int:
        """The width in cells."""

    @property
    def rows(self) -> int:
        """The height in cells."""

    @property
    def has_graphics_protocol_cells(self) -> bool:
        """Whether the grid carries cells for a terminal graphics protocol."""

    @property
    def required_protocol(self) -> GraphicsProtocol | None:
        """The graphics protocol the grid needs, or ``None`` for plain cells."""

class CellAnimationInfo:
    """
    The header of a packed cell animation.

    Examples:
        ```python
        frames = [Buffer.with_text('a').to_cell_grid(), Buffer.with_text('b').to_cell_grid()]
        packed = pack_cell_animation(frames, frame_durations_milliseconds=[40, 60])
        info = inspect_cell_animation(packed)
        assert info.frame_count == 2
        assert info.duration_milliseconds == 100
        assert info.should_loop
        ```
    """

    @property
    def format_version(self) -> int:
        """The version of the cell animation byte format."""

    @property
    def columns(self) -> int:
        """The width of every frame in cells."""

    @property
    def rows(self) -> int:
        """The height of every frame in cells."""

    @property
    def frame_count(self) -> int:
        """The number of frames."""

    @property
    def duration_milliseconds(self) -> int:
        """The total duration of one pass in milliseconds."""

    @property
    def should_loop(self) -> bool:
        """Whether the animation repeats."""

class DecodeLimits:
    """
    Upper bounds checked before packed cell data is accepted.

    The limits are enforced before memory is allocated, so untrusted data cannot
    exhaust it.

    Args:
        maximum_cells: The most cells in a grid or in one animation frame.
        maximum_frames: The most frames in an animation.
        maximum_payload_bytes: The most bytes of graphics protocol payload.

    Examples:
        ```python
        limits = DecodeLimits(maximum_cells=10)
        packed = Buffer(width=4, height=4).to_cell_grid()
        try:
            validate_cell_grid(packed, limits=limits)
        except CellGridError:
            pass
        ```
    """

    def __init__(
        self,
        *,
        maximum_cells: int = 16000000,
        maximum_frames: int = 10000,
        maximum_payload_bytes: int = 268435456,
    ) -> None: ...
    @property
    def maximum_cells(self) -> int:
        """The most cells accepted."""

    @property
    def maximum_frames(self) -> int:
        """The most frames accepted."""

    @property
    def maximum_payload_bytes(self) -> int:
        """The most graphics payload bytes accepted."""

def inspect_cell_grid(
    packed: bytes, *, limits: DecodeLimits | None = None
) -> CellGridInfo:
    """
    Read the header of a packed cell grid without decoding its cells.

    Raises:
        CellGridError: The bytes are malformed or exceed the limits.

    Examples:
        ```python
        info = inspect_cell_grid(Buffer(width=3, height=2).to_cell_grid())
        assert (info.columns, info.rows) == (3, 2)
        ```
    """

def inspect_cell_animation(
    packed: bytes, *, limits: DecodeLimits | None = None
) -> CellAnimationInfo:
    """
    Read the header of a packed cell animation without decoding its frames.

    Raises:
        CellGridError: The bytes are malformed or exceed the limits.

    Examples:
        ```python
        grid = Buffer.with_text('a').to_cell_grid()
        packed = pack_cell_animation([grid], frame_durations_milliseconds=[10])
        assert inspect_cell_animation(packed).frame_count == 1
        ```
    """

def validate_cell_grid(packed: bytes, *, limits: DecodeLimits | None = None) -> None:
    """
    Check that packed bytes are a complete, valid cell grid.

    Raises:
        CellGridError: The bytes are malformed or exceed the limits.

    Examples:
        ```python
        validate_cell_grid(Buffer.with_text('a').to_cell_grid())
        ```
    """

def validate_cell_animation(packed: bytes, *, limits: DecodeLimits | None = None) -> None:
    """
    Check that packed bytes are a complete, valid cell animation.

    Raises:
        CellGridError: The bytes are malformed or exceed the limits.

    Examples:
        ```python
        grid = Buffer.with_text('a').to_cell_grid()
        validate_cell_animation(pack_cell_animation([grid], frame_durations_milliseconds=[10]))
        ```
    """

def cell_grid_size(cell_grid: bytes) -> tuple[int, int]:
    """
    Return the ``(columns, rows)`` of a packed cell grid.

    Examples:
        ```python
        assert cell_grid_size(Buffer(width=3, height=2).to_cell_grid()) == (3, 2)
        ```
    """

def cell_grid_to_text(cell_grid: bytes) -> list[str]:
    """
    Return the plain text rows of a packed cell grid.

    Examples:
        ```python
        assert cell_grid_to_text(Buffer.with_text('abc').to_cell_grid()) == ['abc']
        ```
    """

def cell_grid_to_ansi(cell_grid: bytes) -> str:
    """
    Return a packed cell grid as text with styling escape sequences.

    Examples:
        ```python
        ansi = cell_grid_to_ansi(Buffer.with_text('abc').to_cell_grid())
        assert 'abc' in ansi
        ```
    """

def pack_cell_animation(
    frames: Sequence[bytes],
    *,
    frame_durations_milliseconds: Sequence[int],
    should_loop: bool = True,
) -> bytes:
    """
    Pack cell grids into a cell animation.

    Args:
        frames: Packed cell grids, all with the same dimensions.
        frame_durations_milliseconds: How long each frame shows; one positive
            duration per frame.
        should_loop: Whether the animation repeats.

    Raises:
        CellGridError: The frames differ in size, a duration is not positive or the
            counts do not match.

    Examples:
        ```python
        frames = [Buffer.with_text('a').to_cell_grid(), Buffer.with_text('b').to_cell_grid()]
        packed = pack_cell_animation(frames, frame_durations_milliseconds=[50, 50])
        assert inspect_cell_animation(packed).frame_count == 2
        ```
    """

def animation_frame_at(packed: bytes, *, elapsed_milliseconds: float) -> bytes:
    """
    Return the packed cell grid shown at a time in an animation.

    Looping animations wrap around; others hold their last frame.

    Examples:
        ```python
        frames = [Buffer.with_text('a').to_cell_grid(), Buffer.with_text('b').to_cell_grid()]
        packed = pack_cell_animation(frames, frame_durations_milliseconds=[50, 50])
        assert cell_grid_to_text(animation_frame_at(packed, elapsed_milliseconds=60)) == ['b']
        ```
    """

class TerminalStateValidationError(ValueError):
    """
    Raised when a value or a change does not satisfy a state schema.

    Nothing is published when this error is raised. The error message names the failing
    path and keyword, and ``issues`` lists every problem that was found.

    Examples:
        ```python
        schema = TerminalStateSchema.compile({'type': 'integer', 'minimum': 0})
        try:
            schema.validate(-1)
        except TerminalStateValidationError as error:
            assert error.issues[0].constraint == 'minimum'
        ```
    """

    @property
    def issues(self) -> tuple[TerminalStateIssue, ...]:
        """Every problem found, each with its path, message and failing keyword."""

class TerminalStateConflictError(RuntimeError):
    """
    Raised when a change was prepared against a revision that is no longer current.

    Re-read the state, rebuild the change and try again.

    Examples:
        ```python
        schema = TerminalStateSchema.compile({})
        store = TerminalStateStore({'count': 0}, schema=schema)
        stale = store.revision
        store.apply(TerminalStatePatch.from_value([{'op': 'replace', 'path': '/count', 'value': 1}]))
        try:
            store.apply(
                TerminalStatePatch.from_value([{'op': 'replace', 'path': '/count', 'value': 2}]),
                expected_revision=stale,
            )
        except TerminalStateConflictError as error:
            assert error.expected_revision == stale
            assert error.actual_revision == store.revision
        ```
    """

    @property
    def expected_revision(self) -> int:
        """The revision the change was prepared against."""
    @property
    def actual_revision(self) -> int:
        """The revision the store was at when the change was applied."""

class TerminalStateAccessError(PermissionError):
    """
    Raised when a change touches a path that an observation did not grant for writing.

    Examples:
        ```python
        store = TerminalStateStore({'a': 1, 'b': 2}, schema=TerminalStateSchema.compile({}))
        observation = store.observe(read=[('a',)], write=[('a',)])
        patch = TerminalStatePatch.from_value([{'op': 'replace', 'path': '/b', 'value': 3}])
        try:
            store.apply_observed(patch, observation)
        except TerminalStateAccessError:
            pass
        ```
    """

class TerminalStateIssue:
    """
    One problem found while validating a value against a schema.

    Examples:
        ```python
        schema = TerminalStateSchema.compile(
            {'type': 'object', 'properties': {'x': {'type': 'integer'}}}
        )
        try:
            schema.validate({'x': 'one'})
        except TerminalStateValidationError as error:
            issue = error.issues[0]
            assert issue.path == ('x',)
            assert issue.constraint == 'type'
            assert isinstance(issue.message, str)
        ```
    """

    @property
    def path(self) -> StatePath:
        """Where the problem is: object keys are ``str`` and array indexes are ``int``."""
    @property
    def message(self) -> str:
        """A sentence describing the problem and what was expected."""
    @property
    def constraint(self) -> str:
        """The schema keyword that failed, such as ``type`` or ``minimum``."""

class TerminalStateSchema:
    """
    A compiled schema that validates state values.

    Schemas use a documented subset of JSON Schema. Unsupported keywords fail compilation
    instead of being ignored. Recursive definitions use ``$ref``, and validation has an
    explicit depth limit. Recognized ``x-xnano`` drawing rules compile to semantic
    validators. Schemas contain no executable code and values are never coerced.

    Examples:
        ```python
        schema = TerminalStateSchema.compile(
            {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'score': {'type': 'integer', 'minimum': 0},
                },
                'required': ['name'],
            }
        )
        schema.validate({'name': 'ada', 'score': 3})
        try:
            schema.validate({'score': -1})
        except TerminalStateValidationError as error:
            assert len(error.issues) >= 1
        ```
    """

    @classmethod
    def compile(
        cls, schema: JSONSchema, *, maximum_depth: int = 256
    ) -> TerminalStateSchema:
        """
        Compile a JSON Schema document.

        Args:
            schema: The schema document.
            maximum_depth: How deeply nested a validated value may be.

        Raises:
            TerminalStateValidationError: The schema uses an unsupported keyword or is malformed.

        Examples:
            ```python
            schema = TerminalStateSchema.compile({'type': 'array', 'items': {'type': 'integer'}})
            schema.validate([1, 2, 3])
            ```
        """
    def to_json_schema(self) -> JSONSchema:
        """
        Return the schema document this schema was compiled from.

        Examples:
            ```python
            document = {'type': 'string', 'minLength': 1}
            assert TerminalStateSchema.compile(document).to_json_schema() == document
            ```
        """
    def validate(self, value: JSONValue) -> None:
        """
        Check a value against the schema.

        Raises:
            TerminalStateValidationError: The value does not satisfy the schema.

        Examples:
            ```python
            schema = TerminalStateSchema.compile({'type': 'boolean'})
            schema.validate(True)
            try:
                schema.validate('yes')
            except TerminalStateValidationError:
                pass
            ```
        """
    def validate_json(self, data: str | bytes) -> None:
        """
        Parse JSON text and check it against the schema.

        Raises:
            TerminalStateValidationError: The text is not valid JSON or does not satisfy the schema.

        Examples:
            ```python
            schema = TerminalStateSchema.compile({'type': 'object', 'required': ['id']})
            schema.validate_json('{"id": 7}')
            ```
        """
    def at(self, path: StatePath) -> TerminalStateSchema:
        """
        Return the schema that applies to the branch at ``path``.

        Examples:
            ```python
            schema = TerminalStateSchema.compile(
                {'type': 'object', 'properties': {'age': {'type': 'integer'}}}
            )
            assert schema.at(('age',)).to_json_schema()['type'] == 'integer'
            ```
        """

class TerminalStateSnapshot:
    """
    An immutable view of a state tree, or of one branch of it, at one revision.

    A snapshot never changes after it is taken. Values are copied into Python only when
    you call ``to_value``.

    Examples:
        ```python
        store = TerminalStateStore(
            {'player': {'x': 1, 'y': 2}}, schema=TerminalStateSchema.compile({})
        )
        snapshot = store.snapshot()
        assert snapshot.at(('player', 'x')).to_value() == 1
        assert snapshot.exists(('player', 'y'))
        assert not snapshot.exists(('player', 'z'))
        ```
    """

    @property
    def revision(self) -> int:
        """The revision of the commit this snapshot was taken at."""
    @property
    def schema(self) -> TerminalStateSchema:
        """The schema that applies to this snapshot's branch."""
    def at(self, path: StatePath) -> TerminalStateSnapshot:
        """
        Return a snapshot of the branch at ``path``.

        Examples:
            ```python
            store = TerminalStateStore({'items': [10, 20]}, schema=TerminalStateSchema.compile({}))
            assert store.snapshot().at(('items', 1)).to_value() == 20
            ```
        """
    def exists(self, path: StatePath) -> bool:
        """
        Whether a value exists at ``path``.

        Examples:
            ```python
            store = TerminalStateStore({'a': None}, schema=TerminalStateSchema.compile({}))
            assert store.snapshot().exists(('a',))
            assert not store.snapshot().exists(('b',))
            ```
        """
    def to_value(self) -> JSONValue:
        """
        Copy this snapshot's branch into detached Python data.

        Examples:
            ```python
            store = TerminalStateStore({'a': [1, 2]}, schema=TerminalStateSchema.compile({}))
            assert store.snapshot().to_value() == {'a': [1, 2]}
            ```
        """
    def to_json(self) -> str:
        """
        Serialize this snapshot's branch as JSON text.

        Examples:
            ```python
            store = TerminalStateStore([1, 2], schema=TerminalStateSchema.compile({}))
            assert store.snapshot().to_json() == '[1,2]'
            ```
        """
    def select(self, paths: Sequence[StatePath]) -> TerminalStateSelection:
        """
        Read several paths at this snapshot's revision.

        Examples:
            ```python
            store = TerminalStateStore({'a': 1, 'b': 2}, schema=TerminalStateSchema.compile({}))
            selection = store.snapshot().select([('a',), ('b',)])
            assert selection.to_value() == {'/a': 1, '/b': 2}
            ```
        """

class TerminalStateSelection:
    """
    Values read from several paths at one consistent revision.

    A selection is keyed by JSON Pointer, for example ``/player/x``.

    Examples:
        ```python
        store = TerminalStateStore(
            {'player': {'x': 1}, 'level': 3}, schema=TerminalStateSchema.compile({})
        )
        selection = store.snapshot().select([('player', 'x'), ('level',)])
        assert selection.paths == (('player', 'x'), ('level',))
        assert selection.to_value() == {'/player/x': 1, '/level': 3}
        ```
    """

    @property
    def revision(self) -> int:
        """The revision all selected values were read at."""
    @property
    def paths(self) -> tuple[StatePath, ...]:
        """The paths that were selected, in the order they were requested."""
    def to_value(self) -> dict[str, JSONValue]:
        """Copy the selected values into a ``dict`` keyed by JSON Pointer."""
    def to_json(self) -> str:
        """Serialize the selected values as a JSON object keyed by JSON Pointer."""

class TerminalStatePatch:
    """
    A list of edits to a state tree, in the JSON Patch format (RFC 6902).

    Each edit is a ``dict`` with an ``op`` of ``add``, ``remove``, ``replace``, ``move``,
    ``copy`` or ``test`` and a JSON Pointer ``path``. Parsing checks the structure of each
    edit. The schema is checked when the patch is applied to a store.

    Examples:
        ```python
        patch = TerminalStatePatch.from_value(
            [
                {'op': 'replace', 'path': '/score', 'value': 10},
                {'op': 'add', 'path': '/tags/-', 'value': 'new'},
            ]
        )
        assert len(patch) == 2
        store = TerminalStateStore(
            {'score': 0, 'tags': []}, schema=TerminalStateSchema.compile({})
        )
        store.apply(patch)
        assert store.snapshot().to_value() == {'score': 10, 'tags': ['new']}
        ```
    """

    def __len__(self) -> int:
        """The number of edits."""
    @classmethod
    def from_json(cls, data: str | bytes) -> TerminalStatePatch:
        """
        Parse a JSON Patch document.

        Raises:
            ValueError: The text is not a valid JSON Patch.

        Examples:
            ```python
            patch = TerminalStatePatch.from_json('[{"op": "remove", "path": "/old"}]')
            assert len(patch) == 1
            ```
        """
    @classmethod
    def from_value(cls, operations: Sequence[dict[str, JSONValue]]) -> TerminalStatePatch:
        """
        Build a patch from a list of edit ``dict`` values.

        Raises:
            ValueError: An edit is missing a field or uses an unknown ``op``.

        Examples:
            ```python
            patch = TerminalStatePatch.from_value(
                [{'op': 'move', 'from': '/a', 'path': '/b'}]
            )
            assert patch.to_value()[0]['op'] == 'move'
            ```
        """
    def to_value(self) -> list[dict[str, JSONValue]]:
        """
        Return the edits as a list of ``dict`` values.

        Examples:
            ```python
            edits = [{'op': 'test', 'path': '/a', 'value': 1}]
            assert TerminalStatePatch.from_value(edits).to_value() == edits
            ```
        """
    def to_json(self) -> str:
        """
        Serialize the patch as a JSON Patch document.

        Examples:
            ```python
            patch = TerminalStatePatch.from_value([{'op': 'remove', 'path': '/a'}])
            assert TerminalStatePatch.from_json(patch.to_json()).to_value() == patch.to_value()
            ```
        """

class TerminalStateChange:
    """
    The result of one committed change: what changed and the state before and after.

    A change is returned when a commit alters the store and is passed to subscription
    callbacks. A commit that alters nothing returns ``None`` instead.

    Examples:
        ```python
        store = TerminalStateStore({'x': 1}, schema=TerminalStateSchema.compile({}))
        change = store.apply(
            TerminalStatePatch.from_value([{'op': 'replace', 'path': '/x', 'value': 2}])
        )
        assert change.paths == (('x',),)
        assert change.before.to_value() == {'x': 1}
        assert change.after.to_value() == {'x': 2}
        assert change.revision == change.before_revision + 1
        ```
    """

    @property
    def before_revision(self) -> int:
        """The store revision before the commit."""
    @property
    def revision(self) -> int:
        """The store revision after the commit."""
    @property
    def paths(self) -> tuple[StatePath, ...]:
        """The paths the commit changed."""
    @property
    def patch(self) -> TerminalStatePatch:
        """The edits that were applied."""
    @property
    def before(self) -> TerminalStateSnapshot:
        """A snapshot of the state before the commit."""
    @property
    def after(self) -> TerminalStateSnapshot:
        """A snapshot of the state after the commit."""

class TerminalStateSubscription:
    """
    A registration that delivers state changes until it is cancelled.

    Examples:
        ```python
        store = TerminalStateStore({'x': 0}, schema=TerminalStateSchema.compile({}))
        subscription = store.subscribe([('x',)], lambda change: None)
        assert not subscription.is_cancelled
        subscription.cancel()
        assert subscription.is_cancelled
        ```
    """

    @property
    def is_cancelled(self) -> bool:
        """Whether the subscription has been cancelled."""
    def cancel(self) -> None:
        """Stop delivering changes. Calling this again does nothing."""

class TerminalStateTransaction:
    """
    Staged edits that publish together or not at all.

    Edits made inside a transaction are visible only to the transaction until
    ``commit``. A failed validation or a revision conflict publishes nothing, and an
    exception inside a ``with`` block rolls the edits back. Rules that relate several
    fields are checked at commit, not after each staged edit.

    Examples:
        ```python
        store = TerminalStateStore(
            {'a': 1, 'b': 2}, schema=TerminalStateSchema.compile({})
        )
        with store.transaction() as transaction:
            transaction.set(('a',), 10)
            transaction.set(('b',), 20)
        assert store.snapshot().to_value() == {'a': 10, 'b': 20}
        ```
    """

    @property
    def base_revision(self) -> int:
        """The store revision this transaction started from."""
    def snapshot(self) -> TerminalStateSnapshot:
        """
        Return a snapshot that includes the staged edits.

        Examples:
            ```python
            store = TerminalStateStore({'a': 1}, schema=TerminalStateSchema.compile({}))
            with store.transaction() as transaction:
                transaction.set(('a',), 2)
                assert transaction.snapshot().to_value() == {'a': 2}
                assert store.snapshot().to_value() == {'a': 1}
            ```
        """
    def set(self, path: StatePath, value: JSONValue) -> None:
        """
        Stage a value at ``path``.

        Examples:
            ```python
            store = TerminalStateStore({'items': [1, 2]}, schema=TerminalStateSchema.compile({}))
            with store.transaction() as transaction:
                transaction.set(('items', 0), 9)
            assert store.snapshot().at(('items',)).to_value() == [9, 2]
            ```
        """
    def remove(self, path: StatePath) -> None:
        """
        Stage the removal of the value at ``path``.

        Examples:
            ```python
            store = TerminalStateStore({'a': 1, 'b': 2}, schema=TerminalStateSchema.compile({}))
            with store.transaction() as transaction:
                transaction.remove(('a',))
            assert store.snapshot().to_value() == {'b': 2}
            ```
        """
    def apply(self, patch: TerminalStatePatch) -> None:
        """
        Stage every edit of ``patch``.

        Examples:
            ```python
            store = TerminalStateStore({'n': 0}, schema=TerminalStateSchema.compile({}))
            patch = TerminalStatePatch.from_value([{'op': 'replace', 'path': '/n', 'value': 5}])
            with store.transaction() as transaction:
                transaction.apply(patch)
            assert store.snapshot().to_value() == {'n': 5}
            ```
        """
    def commit(self) -> TerminalStateChange | None:
        """
        Validate and publish the staged edits.

        Returns:
            The change, or ``None`` when the edits alter nothing.

        Raises:
            TerminalStateValidationError: The result does not satisfy the schema.
            TerminalStateConflictError: The store changed since the transaction started
                and the transaction was opened with ``expected_revision``.

        Examples:
            ```python
            store = TerminalStateStore({'a': 1}, schema=TerminalStateSchema.compile({}))
            transaction = store.transaction()
            transaction.set(('a',), 2)
            change = transaction.commit()
            assert change.after.to_value() == {'a': 2}
            ```
        """
    def rollback(self) -> None:
        """
        Discard the staged edits.

        Examples:
            ```python
            store = TerminalStateStore({'a': 1}, schema=TerminalStateSchema.compile({}))
            transaction = store.transaction()
            transaction.set(('a',), 2)
            transaction.rollback()
            assert store.snapshot().to_value() == {'a': 1}
            ```
        """
    def __enter__(self) -> TerminalStateTransaction:
        """Start a ``with`` block. Leaving the block commits, or rolls back on an exception."""
    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        """Commit the transaction, or roll it back when an exception is leaving the block."""

class TerminalStateStore:
    """
    Thread-safe state storage with schema validation, revisions and notifications.

    Every commit is validated against the schema and published atomically. Each commit
    advances the store ``revision`` and the revision of every path it touched. A commit
    that changes nothing advances nothing and publishes no change.

    Subscriptions queue their changes. Python callbacks run only when
    ``drain_notifications`` is called, on the calling thread, never while the store is
    locked and never on an audio or device thread.

    Args:
        value: The initial state. It must satisfy ``schema``.
        schema: The schema every commit is validated against.

    Raises:
        TerminalStateValidationError: ``value`` does not satisfy ``schema``.

    Examples:
        ```python
        schema = TerminalStateSchema.compile(
            {
                'type': 'object',
                'properties': {'score': {'type': 'integer', 'minimum': 0}},
            }
        )
        store = TerminalStateStore({'score': 0}, schema=schema)
        seen = []
        store.subscribe([('score',)], lambda change: seen.append(change.after.to_value()))
        store.apply(TerminalStatePatch.from_value([{'op': 'replace', 'path': '/score', 'value': 5}]))
        assert store.drain_notifications() == 1
        assert seen == [{'score': 5}]
        ```

    State drives a buffer through the ``SetState`` and ``ApplyStatePatch`` operations,
    which take a reference exposing ``path``, ``native_store`` and ``schema``:

        ```python
        store = TerminalStateStore(
            {'score': 0}, schema=TerminalStateSchema.compile({})
        )

        class Reference:
            path = ('score',)
            native_store = store

            class schema:
                @staticmethod
                def to_value(value):
                    return value

        Buffer(width=4, height=1).update(SetState(Reference, 8))
        assert store.snapshot().at(('score',)).to_value() == 8
        ```
    """

    @property
    def identity(self) -> int:
        """A number that identifies this store; observations are valid only for their own store."""
    def __init__(self, value: JSONValue, *, schema: TerminalStateSchema) -> None: ...
    @property
    def revision(self) -> int:
        """The number of changes committed to the store so far."""
    @property
    def schema(self) -> TerminalStateSchema:
        """The schema every commit is validated against."""
    def snapshot(self, path: StatePath = ()) -> TerminalStateSnapshot:
        """
        Take an immutable snapshot of the whole state, or of the branch at ``path``.

        Examples:
            ```python
            store = TerminalStateStore({'a': {'b': 1}}, schema=TerminalStateSchema.compile({}))
            assert store.snapshot(('a', 'b')).to_value() == 1
            ```
        """
    def revision_at(self, path: StatePath) -> int:
        """
        The revision of the most recent commit that touched ``path`` or a branch around it.

        Examples:
            ```python
            store = TerminalStateStore({'a': 1, 'b': 2}, schema=TerminalStateSchema.compile({}))
            store.apply(TerminalStatePatch.from_value([{'op': 'replace', 'path': '/a', 'value': 5}]))
            assert store.revision_at(('a',)) == store.revision
            assert store.revision_at(('b',)) == 0
            ```
        """
    def apply(
        self, patch: TerminalStatePatch, *, expected_revision: int | None = None
    ) -> TerminalStateChange | None:
        """
        Validate and publish ``patch``.

        Args:
            patch: The edits to apply.
            expected_revision: When given, the store must still be at this revision.

        Returns:
            The change, or ``None`` when the patch alters nothing.

        Raises:
            TerminalStateValidationError: The result does not satisfy the schema.
            TerminalStateConflictError: The store is not at ``expected_revision``.

        Examples:
            ```python
            store = TerminalStateStore({'n': 1}, schema=TerminalStateSchema.compile({}))
            patch = TerminalStatePatch.from_value([{'op': 'replace', 'path': '/n', 'value': 2}])
            change = store.apply(patch, expected_revision=store.revision)
            assert change.revision == store.revision
            assert store.apply(patch) is None
            ```
        """
    def transaction(
        self, *, expected_revision: int | None = None
    ) -> TerminalStateTransaction:
        """
        Start a transaction.

        Args:
            expected_revision: When given, the commit fails if the store has moved past it.

        Examples:
            ```python
            store = TerminalStateStore({'n': 0}, schema=TerminalStateSchema.compile({}))
            with store.transaction(expected_revision=store.revision) as transaction:
                transaction.set(('n',), 1)
            ```
        """
    def subscribe(
        self,
        paths: Sequence[StatePath],
        callback: Callable[[TerminalStateChange], None],
        *,
        include_descendants: bool = True,
    ) -> TerminalStateSubscription:
        """
        Queue changes that touch ``paths`` for ``callback``.

        Args:
            paths: The paths to watch. An empty path ``()`` watches the whole state.
            callback: Called with each change when ``drain_notifications`` runs.
            include_descendants: Whether changes below a watched path also notify.

        Examples:
            ```python
            store = TerminalStateStore({'a': {'b': 1}}, schema=TerminalStateSchema.compile({}))
            seen = []
            store.subscribe([('a',)], seen.append)
            store.apply(TerminalStatePatch.from_value([{'op': 'replace', 'path': '/a/b', 'value': 2}]))
            store.drain_notifications()
            assert len(seen) == 1
            ```
        """
    def attach_waker(self, wake: Callable[[], None]) -> TerminalStateSubscription:
        """
        Call ``wake`` whenever a change is queued, from whichever thread committed it.

        ``wake`` is only a signal. It must not read or change Python UI objects.

        Examples:
            ```python
            store = TerminalStateStore({'a': 1}, schema=TerminalStateSchema.compile({}))
            wakes = []
            store.attach_waker(lambda: wakes.append(True))
            store.apply(TerminalStatePatch.from_value([{'op': 'replace', 'path': '/a', 'value': 2}]))
            assert wakes
            ```
        """
    def observe(
        self, *, read: Sequence[StatePath], write: Sequence[StatePath] = ()
    ) -> TerminalStateObservation:
        """
        Record what is read now and which paths may be written later.

        Examples:
            ```python
            store = TerminalStateStore({'a': 1, 'b': 2}, schema=TerminalStateSchema.compile({}))
            observation = store.observe(read=[('a',), ('b',)], write=[('a',)])
            assert observation.selection.to_value() == {'/a': 1, '/b': 2}
            ```
        """
    def validate_observed(
        self, patch: TerminalStatePatch, observation: TerminalStateObservation
    ) -> None:
        """
        Check that ``patch`` could be applied now using ``observation``, without publishing it.

        Raises:
            TerminalStateAccessError: The patch writes outside the observation's grants.
            TerminalStateConflictError: A path the observation read has changed.
            TerminalStateValidationError: The result does not satisfy the schema.

        Examples:
            ```python
            store = TerminalStateStore({'a': 1}, schema=TerminalStateSchema.compile({}))
            observation = store.observe(read=[('a',)], write=[('a',)])
            patch = TerminalStatePatch.from_value([{'op': 'replace', 'path': '/a', 'value': 2}])
            store.validate_observed(patch, observation)
            assert store.snapshot().to_value() == {'a': 1}
            ```
        """
    def apply_observed(
        self, patch: TerminalStatePatch, observation: TerminalStateObservation
    ) -> TerminalStateChange | None:
        """
        Apply ``patch`` only if nothing the observation read has changed and the patch stays within its write grants.

        Raises:
            TerminalStateAccessError: The patch writes outside the observation's grants.
            TerminalStateConflictError: A path the observation read has changed.
            TerminalStateValidationError: The result does not satisfy the schema.

        Examples:
            ```python
            store = TerminalStateStore({'a': 1, 'b': 1}, schema=TerminalStateSchema.compile({}))
            observation = store.observe(read=[('a',)], write=[('a',)])
            store.apply(TerminalStatePatch.from_value([{'op': 'replace', 'path': '/b', 'value': 9}]))
            patch = TerminalStatePatch.from_value([{'op': 'replace', 'path': '/a', 'value': 2}])
            store.apply_observed(patch, observation)
            assert store.snapshot().to_value() == {'a': 2, 'b': 9}
            ```
        """
    def drain_notifications(self, *, maximum_changes: int = 1024) -> int:
        """
        Run queued subscription callbacks on this thread.

        Args:
            maximum_changes: The most changes to deliver in one call.

        Returns:
            The number of changes delivered.

        Examples:
            ```python
            store = TerminalStateStore({'a': 1}, schema=TerminalStateSchema.compile({}))
            store.subscribe([()], lambda change: None)
            store.apply(TerminalStatePatch.from_value([{'op': 'replace', 'path': '/a', 'value': 2}]))
            assert store.drain_notifications() == 1
            assert store.drain_notifications() == 0
            ```
        """

    def reference(self, path: StatePath | None = None) -> StateReference: ...

class TerminalStateObservation:
    """
    A record of what was read from a store, and which paths may be written.

    An observation holds the revisions of everything it read, including the absence of
    missing keys, together with the schemas and write grants. It stays valid while
    nothing it read has changed: replacing an ancestor of a read path invalidates it,
    while changes elsewhere do not. An observation works only with the store that made it.

    Examples:
        ```python
        store = TerminalStateStore(
            {'player': {'x': 1}, 'score': 0}, schema=TerminalStateSchema.compile({})
        )
        observation = store.observe(read=[('player', 'x')], write=[('player', 'x')])
        assert observation.read == (('player', 'x'),)
        assert observation.write == (('player', 'x'),)
        assert observation.selection.to_value() == {'/player/x': 1}
        ```
    """

    @property
    def schemas(self) -> Mapping[str, JSONSchema]:
        """The schema at each observed path, keyed by JSON Pointer."""
    @property
    def read(self) -> tuple[StatePath, ...]:
        """The paths that were read."""
    @property
    def write(self) -> tuple[StatePath, ...]:
        """The paths that may be written."""
    @property
    def revision(self) -> int:
        """The store revision at the time of the observation."""
    @property
    def selection(self) -> TerminalStateSelection:
        """The values that were read."""

def _reference(name: str, kind: str) -> Any: ...
def _external(name: str, is_numeric: bool) -> Any: ...
def _state_expression(
    store: TerminalStateStore, path: StatePath, is_numeric: bool
) -> Any: ...

class Paragraph(Widget):
    """
    Styled text that can wrap, align and scroll.

    Every setting is a property that accepts a plain value or an expression, so the
    paragraph repaints when a bound value changes.

    Maps to [`ratatui::widgets::Paragraph`](https://docs.rs/ratatui/0.30.0/ratatui/widgets/struct.Paragraph.html).

    Args:
        text: A ``str``, a ``StyledText``, a sequence of those, or an expression that
            produces text.
        style: A ``Style`` or ``DynamicStyle`` for the whole paragraph.
        alignment: ``"left"``, ``"center"`` or ``"right"``.
        should_wrap: Whether long rows wrap at the widget's width.
        should_trim: Whether wrapped rows lose their leading whitespace.
        scroll: A ``(row, column)`` pair of the first row and column shown.
        block: A ``Block`` framing the paragraph. The paragraph follows later edits of the block.
        width: The widget's width in cells. Defaults to 20.
        height: The widget's height in cells. Defaults to 3.
        x: The column in the parent.
        y: The row in the parent.

    Examples:
        ```python
        paragraph = Paragraph('hello brave new world', width=10, height=3, should_wrap=True)
        assert paragraph.render(format='text').split('\\n') == ['hello', 'brave new', 'world']
        paragraph.alignment = 'right'
        assert paragraph.render(format='text').split('\\n')[0] == '     hello'
        assert paragraph.line_count() == 3
        ```
    """

    def __init__(
        self,
        text: TextContent | Expression[str] | None = None,
        *,
        style: Style | DynamicStyle | None = None,
        alignment: str | Expression[str] | None = None,
        should_wrap: bool | Expression[bool] | None = None,
        should_trim: bool | Expression[bool] | None = None,
        scroll: tuple[int | Expression[int], int | Expression[int]] | None = None,
        block: Block | None = None,
        width: int | None = None,
        height: int | None = None,
        x: int = 0,
        y: int = 0,
    ) -> None: ...
    @property
    def text(self) -> Any:
        """The text as it was set."""

    @text.setter
    def text(self, value: TextContent | Expression[str]) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle: ...
    @style.setter
    def style(self, value: Style | DynamicStyle | None) -> None: ...
    @property
    def alignment(self) -> str | Expression[str]: ...
    @alignment.setter
    def alignment(self, value: str | Expression[str]) -> None: ...
    @property
    def should_wrap(self) -> bool | Expression[bool]: ...
    @should_wrap.setter
    def should_wrap(self, value: bool | Expression[bool]) -> None: ...
    @property
    def should_trim(self) -> bool | Expression[bool]: ...
    @should_trim.setter
    def should_trim(self, value: bool | Expression[bool]) -> None: ...
    @property
    def scroll_row(self) -> int | Expression[int]:
        """The first row shown, counted in displayed rows."""

    @scroll_row.setter
    def scroll_row(self, value: int | Expression[int]) -> None: ...
    @property
    def scroll_column(self) -> int | Expression[int]: ...
    @scroll_column.setter
    def scroll_column(self, value: int | Expression[int]) -> None: ...
    @property
    def block(self) -> Block | None: ...
    @block.setter
    def block(self, value: Block | None) -> None: ...
    def line_count(self, width: int | None = None) -> int:
        """
        How many rows the text takes when drawn ``width`` columns wide.

        Examples:
            ```python
            assert Paragraph('one two', should_wrap=True).line_count(4) == 2
            ```
        """

    def line_width(self) -> int:
        """
        The width in columns of the widest row.

        Examples:
            ```python
            assert Paragraph('hello').line_width() == 5
            ```
        """

    def copy(self) -> Paragraph:
        """
        A new paragraph with the same settings. A shared ``Block`` stays shared.

        Examples:
            ```python
            original = Paragraph('a')
            clone = original.copy()
            clone.text = 'b'
            assert original.text == 'a'
            ```
        """

    def __copy__(self) -> Paragraph: ...
    def __deepcopy__(self, memo: Any) -> Paragraph: ...

class CustomWidget(Widget):
    """
    A widget drawn by a Python function.

    The function is called as ``render(context, region)`` with an ``EvaluationContext`` and
    a writable ``Buffer`` the size of the widget. Operations applied to ``region`` become the
    widget's cells. It runs again after ``invalidate()``, a resize, a change of a watched
    expression, or every frame when ``redraw`` is ``"always"``.

    Args:
        render: The drawing function.
        redraw: ``"on_change"`` (default) or ``"always"``.
        watch: Expressions whose changes redraw the widget.
        width: The widget's width in cells. Defaults to 10.
        height: The widget's height in cells. Defaults to 3.
        x: The column in the parent.
        y: The row in the parent.

    Raises:
        RenderError: Raised when the widget is drawn if ``render`` raises; the original
            exception is the ``__cause__``.

    Examples:
        ```python
        def draw(context, region):
            region.update(Write('hi', x=1))

        widget = CustomWidget(draw, width=5, height=1)
        assert widget.render(format='text') == ' hi'
        ```
    """

    def __init__(
        self,
        render: Callable[[EvaluationContext, Buffer], None],
        *,
        redraw: Literal['on_change', 'always'] = 'on_change',
        watch: Iterable[Expression[Any]] | None = None,
        width: int | None = None,
        height: int | None = None,
        x: int = 0,
        y: int = 0,
    ) -> None: ...
    @property
    def callback(self) -> Callable[[EvaluationContext, Buffer], None]: ...
    @callback.setter
    def callback(self, value: Callable[[EvaluationContext, Buffer], None]) -> None: ...
    @property
    def redraw(self) -> Literal['on_change', 'always']: ...
    @redraw.setter
    def redraw(self, value: Literal['on_change', 'always']) -> None: ...
    @property
    def watch(self) -> tuple[Expression[Any], ...]: ...
    @watch.setter
    def watch(self, value: Iterable[Expression[Any]]) -> None: ...
    def invalidate(self, area: Rectangle | None = None) -> None:
        """
        Ask for a redraw on the next frame.

        Examples:
            ```python
            calls = []
            widget = CustomWidget(lambda context, region: calls.append(1), width=2, height=1)
            widget.render(format='text')
            widget.invalidate()
            widget.render(format='text')
            assert len(calls) == 2
            ```
        """

    def copy(self) -> CustomWidget: ...
    def __copy__(self) -> CustomWidget: ...
    def __deepcopy__(self, memo: Any) -> CustomWidget: ...

class Live(Widget):
    """
    Operations that are applied again whenever something they show changes.

    The widget clears itself and applies its operations in order after ``invalidate()``, a
    resize, a change of ``operations`` or a change of a watched expression.

    Args:
        operations: The operations to apply, such as ``Write`` or ``Border``.
        watch: Expressions whose changes redraw the widget.
        width: The widget's width in cells. Defaults to 10.
        height: The widget's height in cells. Defaults to 3.
        x: The column in the parent.
        y: The row in the parent.

    Raises:
        TypeError: An item of ``operations`` is not an operation.

    Examples:
        ```python
        live = Live(Write('a'), width=4, height=1)
        assert live.render(format='text') == 'a'
        live.operations = [Write('b'), Write('c', x=1)]
        assert live.render(format='text') == 'bc'
        ```
    """

    def __init__(
        self,
        *operations: Operation,
        watch: Iterable[Expression[Any]] | None = None,
        width: int | None = None,
        height: int | None = None,
        x: int = 0,
        y: int = 0,
    ) -> None: ...
    @property
    def operations(self) -> tuple[Operation, ...]: ...
    @operations.setter
    def operations(self, value: Iterable[Operation]) -> None: ...
    @property
    def watch(self) -> tuple[Expression[Any], ...]: ...
    @watch.setter
    def watch(self, value: Iterable[Expression[Any]]) -> None: ...
    def invalidate(self, area: Rectangle | None = None) -> None: ...
    def copy(self) -> Live: ...
    def __copy__(self) -> Live: ...
    def __deepcopy__(self, memo: Any) -> Live: ...

class CanvasLine:
    """
    A straight line between two points, optionally filled down to a baseline.

    Every coordinate and the color accept a plain value or an expression, so a line can follow state.
    A shape can be edited after it is created; widgets that draw it repaint immediately.

    Args:
        x1: Horizontal position of the start.
        y1: Vertical position of the start.
        x2: Horizontal position of the end.
        y2: Vertical position of the end.
        color: A color name, ``Color`` or expression. Defaults to the terminal default.
        fill_to_y: When set, the area between the line and this vertical position is filled.

    Examples:
        ```python
        line = CanvasLine(0, 0, 10, 10, 'green')
        canvas = Canvas((0, 10), (0, 10), marker='block', shapes=[line], width=10, height=5)
        assert '█' in canvas.render(format='text')
        line.x2 = 0
        assert line.x2 == 0.0
        ```
    """

    def __init__(
        self,
        x1: float | Value[float],
        y1: float | Value[float],
        x2: float | Value[float],
        y2: float | Value[float],
        color: ColorValue | None = None,
        *,
        fill_to_y: float | Value[float] | None = None,
    ) -> None: ...
    x1: float | Value[float]
    y1: float | Value[float]
    x2: float | Value[float]
    y2: float | Value[float]
    color: Color | Value[Color]
    fill_to_y: float | Value[float] | None
    def __copy__(self) -> CanvasLine: ...
    def __deepcopy__(self, memo: Any) -> CanvasLine: ...

class CanvasRectangle:
    """
    An axis-aligned rectangle outline.

    Args:
        x: Horizontal position of the lower-left corner.
        y: Vertical position of the lower-left corner.
        width: Width in canvas units.
        height: Height in canvas units.
        color: A color name, ``Color`` or expression.

    Examples:
        ```python
        shape = CanvasRectangle(0, 0, 10, 10, 'red')
        canvas = Canvas((0, 10), (0, 10), marker='block', shapes=[shape], width=10, height=5)
        assert '█' in canvas.render(format='text')
        ```
    """

    def __init__(
        self,
        x: float | Value[float],
        y: float | Value[float],
        width: float | Value[float],
        height: float | Value[float],
        color: ColorValue | None = None,
    ) -> None: ...
    x: float | Value[float]
    y: float | Value[float]
    width: float | Value[float]
    height: float | Value[float]
    color: Color | Value[Color]
    def __copy__(self) -> CanvasRectangle: ...
    def __deepcopy__(self, memo: Any) -> CanvasRectangle: ...

class CanvasCircle:
    """
    A circle outline.

    Args:
        x: Horizontal position of the center.
        y: Vertical position of the center.
        radius: Radius in canvas units.
        color: A color name, ``Color`` or expression.

    Examples:
        ```python
        circle = CanvasCircle(5, 5, 3, 'blue')
        canvas = Canvas((0, 10), (0, 10), marker='block', shapes=[circle], width=20, height=10)
        assert '█' in canvas.render(format='text')
        circle.radius = 1
        ```
    """

    def __init__(
        self,
        x: float | Value[float],
        y: float | Value[float],
        radius: float | Value[float],
        color: ColorValue | None = None,
    ) -> None: ...
    x: float | Value[float]
    y: float | Value[float]
    radius: float | Value[float]
    color: Color | Value[Color]
    def __copy__(self) -> CanvasCircle: ...
    def __deepcopy__(self, memo: Any) -> CanvasCircle: ...

class CanvasPoints:
    """
    A set of single points.

    Args:
        coordinates: ``(x, y)`` pairs of finite numbers.
        color: A color name, ``Color`` or expression.

    Raises:
        ValueError: A coordinate is not finite.

    Examples:
        ```python
        points = CanvasPoints([(1, 1), (5, 5)], 'yellow')
        canvas = Canvas((0, 10), (0, 10), marker='block', shapes=[points], width=10, height=5)
        points.coordinates = [(1, 1), (9, 9)]
        assert len(points) == 2 and '█' in canvas.render(format='text')
        ```
    """

    def __init__(
        self, coordinates: Iterable[tuple[float, float]], color: ColorValue | None = None
    ) -> None: ...
    coordinates: list[tuple[float, float]]
    color: Color | Value[Color]
    def __len__(self) -> int: ...
    def __copy__(self) -> CanvasPoints: ...
    def __deepcopy__(self, memo: Any) -> CanvasPoints: ...

class CanvasMap:
    """
    The world map, in longitude and latitude (use bounds ``(-180, 180)`` and ``(-90, 90)``).

    Args:
        resolution: ``'low'`` or ``'high'``.
        color: A color name, ``Color`` or expression.

    Raises:
        ValueError: The resolution is not ``'low'`` or ``'high'``.

    Examples:
        ```python
        world = CanvasMap('low', 'white')
        canvas = Canvas((-180, 180), (-90, 90), shapes=[world], width=40, height=12)
        assert canvas.render(format='text').strip()
        ```
    """

    def __init__(
        self,
        resolution: Literal['low', 'high'] | str | Value[str] | None = None,
        color: ColorValue | None = None,
    ) -> None: ...
    resolution: str | Value[str]
    color: Color | Value[Color]
    def __copy__(self) -> CanvasMap: ...
    def __deepcopy__(self, memo: Any) -> CanvasMap: ...

class CanvasLabel:
    """
    Text printed at a position, always on top of the shapes.

    Args:
        x: Horizontal position of the text start.
        y: Vertical position of the text.
        text: The text, or an expression producing it.
        style: A ``Style`` or ``DynamicStyle``.

    Examples:
        ```python
        label = CanvasLabel(1, 5, 'hello')
        canvas = Canvas((0, 10), (0, 10), shapes=[label], width=10, height=5)
        assert 'hello' in canvas.render(format='text')
        label.text = 'bye'
        assert 'bye' in canvas.render(format='text')
        ```
    """

    def __init__(
        self,
        x: float | Value[float],
        y: float | Value[float],
        text: str | Value[str],
        style: Style | DynamicStyle | None = None,
    ) -> None: ...
    x: float | Value[float]
    y: float | Value[float]
    text: str | Value[str]
    style: Style | DynamicStyle
    def __copy__(self) -> CanvasLabel: ...
    def __deepcopy__(self, memo: Any) -> CanvasLabel: ...

class CanvasLayer:
    """
    Saves what was drawn so far as a layer; the shapes after it draw on top.

    Examples:
        ```python
        canvas = Canvas((0, 10), (0, 10), shapes=[CanvasPoints([(1, 1)]), CanvasLayer(), CanvasPoints([(9, 9)])])
        assert CanvasLayer() == CanvasLayer()
        ```
    """

    def __init__(self) -> None: ...
    def __hash__(self) -> int: ...
    def __copy__(self) -> CanvasLayer: ...
    def __deepcopy__(self, memo: Any) -> CanvasLayer: ...

class CanvasMarker:
    """
    Switches the marker the shapes after it are drawn with.

    Args:
        marker: A marker name (``'dot'``, ``'block'``, ``'bar'``, ``'braille'``, ``'half_block'``,
            ``'quadrant'``, ``'sextant'``, ``'octant'``) or any single character.

    Raises:
        ValueError: The marker is not a known name or a single character.

    Examples:
        ```python
        canvas = Canvas((0, 10), (0, 10), shapes=[CanvasMarker('block'), CanvasRectangle(0, 0, 10, 10)], width=10, height=5)
        assert '█' in canvas.render(format='text')
        ```
    """

    def __init__(self, marker: str | Value[str]) -> None: ...
    marker: str | Value[str]
    def __copy__(self) -> CanvasMarker: ...
    def __deepcopy__(self, memo: Any) -> CanvasMarker: ...

class Canvas(Widget):
    """
    A coordinate plane that shapes, points and labels are drawn on.

    Maps to [`ratatui::widgets::canvas::Canvas`](https://docs.rs/ratatui/0.30.0/ratatui/widgets/canvas/struct.Canvas.html).

    Args:
        x_bounds: ``(lower, upper)`` of the horizontal axis; numbers or expressions.
        y_bounds: ``(lower, upper)`` of the vertical axis.
        marker: How points are drawn; see ``CanvasMarker``. Defaults to ``'braille'``.
        background_color: Color behind the shapes, or ``None``.
        shapes: Shapes drawn in order.
        block: A ``Block`` framing the canvas.
        width: Width in cells. Defaults to 20.
        height: Height in cells. Defaults to 10.
        x: Column in the parent.
        y: Row in the parent.

    Raises:
        ValueError: A bound pair does not have two numbers, or the marker is unknown.
        TypeError: A shape is not one of the Canvas shape classes.

    Examples:
        ```python
        canvas = Canvas((0, 10), (0, 10), marker='block', width=10, height=5)
        canvas.add_shape(CanvasRectangle(0, 0, 10, 10, 'red'))
        assert '█' in canvas.render(format='text')
        canvas.clear_shapes()
        assert '█' not in canvas.render(format='text')
        ```
    """

    def __init__(
        self,
        x_bounds: Sequence[float | Value[float]] | None = None,
        y_bounds: Sequence[float | Value[float]] | None = None,
        *,
        marker: str | Value[str] | None = None,
        background_color: ColorValue | None = None,
        shapes: Iterable[
            CanvasLine
            | CanvasRectangle
            | CanvasCircle
            | CanvasPoints
            | CanvasMap
            | CanvasLabel
            | CanvasLayer
            | CanvasMarker
        ]
        | None = None,
        block: Block | None = None,
        width: int | None = None,
        height: int | None = None,
        x: int = 0,
        y: int = 0,
    ) -> None: ...
    x_bounds: tuple[float | Value[float], float | Value[float]]
    y_bounds: tuple[float | Value[float], float | Value[float]]
    marker: str | Value[str]
    background_color: Color | Value[Color] | None
    shapes: list[Any]
    block: Block | None
    def add_shape(self, shape: Any) -> None:
        """
        Draw ``shape`` after the shapes already on the canvas.

        Examples:
            ```python
            canvas = Canvas((0, 10), (0, 10), width=10, height=5)
            canvas.add_shape(CanvasCircle(5, 5, 2))
            assert len(canvas.shapes) == 1
            ```
        """

    def extend_shapes(self, shapes: Iterable[Any]) -> None:
        """
        Draw every shape of ``shapes`` after the shapes already on the canvas.

        Examples:
            ```python
            canvas = Canvas((0, 10), (0, 10), width=10, height=5)
            canvas.extend_shapes([CanvasCircle(5, 5, 2), CanvasLabel(0, 0, 'x')])
            assert len(canvas.shapes) == 2
            ```
        """

    def clear_shapes(self) -> None:
        """
        Remove every shape.

        Examples:
            ```python
            canvas = Canvas((0, 10), (0, 10), shapes=[CanvasCircle(5, 5, 2)], width=10, height=5)
            canvas.clear_shapes()
            assert canvas.shapes == []
            ```
        """

class Widget(Buffer):
    """
    A buffer painted from editable settings or bound expressions.

    Examples:
        ```python
        assert issubclass(Widget, Buffer)
        ```
    """

class BlockTitle:
    """
    A styled title positioned on the top or bottom border of a block.

    Examples:
        ```python
        title = BlockTitle('Status')
        assert title.text == 'Status'
        ```
    """

    def __init__(
        self,
        /,
        text: TextContent | Expression[str],
        *,
        position: str = 'top',
        alignment: str | Expression[str] | None = None,
        style: Style | DynamicStyle | None = None,
    ) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle: ...
    @property
    def alignment(self) -> str | Expression[str]: ...
    @property
    def text(self) -> TextContent | Expression[str]: ...
    @property
    def position(self) -> int | Expression[int]: ...

class Block(Widget):
    """
    Borders, titles and padding shared by retained widgets.

    Examples:
        ```python
        block = Block('Status', width=12, height=3)
        assert 'Status' in block.render(format='text')
        block.border_type = 'double'
        assert '╔' in block.render(format='text')
        ```
    """

    def __init__(
        self,
        /,
        title: str | Expression[str] | None = None,
        *,
        borders: str | Sequence[str] | None = None,
        border_type: str | Expression[str] | None = None,
        border_style: Style | DynamicStyle | None = None,
        style: Style | DynamicStyle | None = None,
        title_style: Style | DynamicStyle | None = None,
        title_alignment: str = 'left',
        padding: int
        | Expression[int]
        | tuple[
            int | Expression[int],
            int | Expression[int],
            int | Expression[int],
            int | Expression[int],
        ]
        | None = None,
        merge: str | Expression[str] | None = None,
        width: int | Expression[int] | None = None,
        height: int | Expression[int] | None = None,
        x: int | Expression[int] = 0,
        y: int | Expression[int] = 0,
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    @property
    def border_type(self) -> str | Expression[str]: ...
    @border_type.setter
    def border_type(self, value: str | Expression[str]) -> None: ...
    @property
    def title_alignment(self) -> str | Expression[str]: ...
    @title_alignment.setter
    def title_alignment(self, value: str | Expression[str]) -> None: ...
    @property
    def border_style(self) -> Style | DynamicStyle: ...
    @border_style.setter
    def border_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def title_style(self) -> Style | DynamicStyle: ...
    @title_style.setter
    def title_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def padding(
        self,
    ) -> (
        int
        | Expression[int]
        | tuple[
            int | Expression[int],
            int | Expression[int],
            int | Expression[int],
            int | Expression[int],
        ]
    ): ...
    @padding.setter
    def padding(
        self,
        value: int
        | Expression[int]
        | tuple[
            int | Expression[int],
            int | Expression[int],
            int | Expression[int],
            int | Expression[int],
        ],
    ) -> None: ...
    @property
    def merge(self) -> str | Expression[str]: ...
    @merge.setter
    def merge(self, value: str | Expression[str]) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle: ...
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def titles(self) -> Sequence[BlockTitle | str]: ...
    @titles.setter
    def titles(self, value: Sequence[BlockTitle | str]) -> None: ...
    @property
    def borders(self) -> str | Sequence[str]: ...
    @borders.setter
    def borders(self, value: str | Sequence[str]) -> None: ...

class DynamicStyle:
    """
    A style whose colors may follow expressions.

    Examples:
        ```python
        style = DynamicStyle(foreground='red')
        style.background = 'blue'
        assert style.foreground == Color('red')
        ```
    """

    def __init__(
        self,
        /,
        foreground: ColorValue | Expression[ColorValue] | None = None,
        background: ColorValue | Expression[ColorValue] | None = None,
        *,
        underline_color: ColorValue | Expression[ColorValue] | None = None,
        modifiers: Sequence[str] | None = None,
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    @property
    def foreground(self) -> ColorValue | Expression[ColorValue] | None: ...
    @foreground.setter
    def foreground(self, value: ColorValue | Expression[ColorValue] | None) -> None: ...
    @property
    def background(self) -> ColorValue | Expression[ColorValue] | None: ...
    @background.setter
    def background(self, value: ColorValue | Expression[ColorValue] | None) -> None: ...

class ListItem:
    """
    Styled content displayed by an item list.

    Examples:
        ```python
        item = ListItem('hello')
        assert 'hello' in repr(item)
        ```
    """

    def __init__(
        self,
        /,
        content: TextContent | Expression[str],
        *,
        style: Style | DynamicStyle | None = None,
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    def __hash__(self, /) -> int: ...
    def __eq__(self, value: Any, /) -> bool: ...
    def __copy__(self, /) -> ListItem: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> ListItem: ...
    @property
    def height(self) -> int | Expression[int]: ...
    @height.setter
    def height(self, value: int | Expression[int]) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle: ...
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def content(self) -> TextContent | Expression[str]: ...
    @content.setter
    def content(self, value: TextContent | Expression[str]) -> None: ...

class SparklineBar:
    """
    A sample with an optional individual style.

    Examples:
        ```python
        bar = SparklineBar(3)
        assert bar.value == 3
        ```
    """

    def __init__(
        self, /, value: int | Expression[int], style: Style | DynamicStyle | None = None
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    def __hash__(self, /) -> int: ...
    def __eq__(self, value: object, /) -> bool: ...
    def __copy__(self, /) -> SparklineBar: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> SparklineBar: ...
    @property
    def value(self) -> int | Expression[int]: ...
    @property
    def style(self) -> Style | DynamicStyle: ...

class ChartAxis:
    """
    An editable axis with bounds, labels and a title.

    Examples:
        ```python
        axis = ChartAxis(bounds=(0, 10), labels=['0', '10'])
        axis.bounds = (0, 20)
        assert axis.bounds == (0.0, 20.0)
        ```
    """

    def __init__(
        self,
        /,
        *,
        title: str | Expression[str] | None = None,
        bounds: tuple[float | Expression[float], float | Expression[float]] | None = None,
        labels: Sequence[str | Expression[str]] | None = None,
        style: Style | DynamicStyle | None = None,
        labels_alignment: str | Expression[str] | None = None,
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    def __eq__(self, value: Any, /) -> bool: ...
    def __copy__(self, /) -> ChartAxis: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> ChartAxis: ...
    @property
    def labels(self) -> Sequence[str | Expression[str]]: ...
    @labels.setter
    def labels(self, value: Sequence[str | Expression[str]]) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle: ...
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def labels_alignment(self) -> str | Expression[str]: ...
    @labels_alignment.setter
    def labels_alignment(self, value: str | Expression[str]) -> None: ...
    @property
    def title(self) -> str | Expression[str] | None: ...
    @title.setter
    def title(self, value: str | Expression[str] | None) -> None: ...
    @property
    def bounds(self) -> tuple[float | Expression[float], float | Expression[float]]: ...
    @bounds.setter
    def bounds(
        self, value: tuple[float | Expression[float], float | Expression[float]]
    ) -> None: ...

class ChartDataset:
    """
    An editable series of points displayed by a chart.

    Examples:
        ```python
        dataset = ChartDataset(data=[(0, 0), (1, 1)], graph_type='line')
        dataset.data = [(0, 1), (1, 0)]
        assert dataset.data[0] == (0.0, 1.0)
        ```
    """

    def __init__(
        self,
        /,
        *,
        name: str | Expression[str] | None = None,
        data: Sequence[tuple[float, float]] | None = None,
        marker: str | Expression[str] | None = None,
        graph_type: str | Expression[str] | None = None,
        style: Style | DynamicStyle | None = None,
        fill_to_y: float | Expression[float] | None = None,
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    def __eq__(self, value: Any, /) -> bool: ...
    def __copy__(self, /) -> ChartDataset: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> ChartDataset: ...
    @property
    def marker(self) -> str | Expression[str]: ...
    @marker.setter
    def marker(self, value: str | Expression[str]) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle: ...
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def fill_to_y(self) -> float | Expression[float]: ...
    @fill_to_y.setter
    def fill_to_y(self, value: float | Expression[float]) -> None: ...
    @property
    def data(self) -> Sequence[tuple[float, float]]: ...
    @data.setter
    def data(self, value: Sequence[tuple[float, float]]) -> None: ...
    @property
    def graph_type(self) -> str | Expression[str]: ...
    @graph_type.setter
    def graph_type(self, value: str | Expression[str]) -> None: ...
    @property
    def name(self) -> str | Expression[str] | None: ...
    @name.setter
    def name(self, value: str | Expression[str] | None) -> None: ...

class Chart(Widget):
    """
    Point series drawn against shared editable axes.

    Examples:
        ```python
        chart = Chart([ChartDataset(data=[(0, 0), (1, 1)])], width=20, height=8)
        assert chart.render(format='text')
        ```
    """

    def __init__(
        self,
        /,
        datasets: Sequence[ChartDataset] | None = None,
        *,
        x_axis: ChartAxis | None = None,
        y_axis: ChartAxis | None = None,
        style: Style | DynamicStyle | None = None,
        legend_position: Any | None = None,
        block: Block | None = None,
        width: int | Expression[int] | None = None,
        height: int | Expression[int] | None = None,
        x: int | Expression[int] = 0,
        y: int | Expression[int] = 0,
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    @property
    def datasets(self) -> Sequence[ChartDataset]: ...
    @datasets.setter
    def datasets(self, value: Sequence[ChartDataset]) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle: ...
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def y_axis(self) -> ChartAxis: ...
    @y_axis.setter
    def y_axis(self, value: ChartAxis) -> None: ...
    @property
    def block(self) -> Block | None: ...
    @block.setter
    def block(self, value: Block | None) -> None: ...
    @property
    def legend_position(self) -> Any | None: ...
    @legend_position.setter
    def legend_position(self, value: Any | None) -> None: ...
    @property
    def x_axis(self) -> ChartAxis: ...
    @x_axis.setter
    def x_axis(self, value: ChartAxis) -> None: ...

class Calendar(Widget):
    """
    A monthly calendar with editable dates and styles for events.

    Examples:
        ```python
        calendar = Calendar(2026, 10, month_header_style=Style(), width=22, height=8)
        assert 'October' in calendar.render(format='text')
        calendar.month = 11
        assert 'November' in calendar.render(format='text')
        ```
    """

    def __init__(
        self,
        /,
        year: int | Expression[int],
        month: int | Expression[int],
        day: int | Expression[int] | None = None,
        *,
        events: Mapping[tuple[int, int, int], Style | DynamicStyle] | None = None,
        style: Style | DynamicStyle | None = None,
        surrounding_style: Style | DynamicStyle | None = None,
        weekdays_header_style: Style | DynamicStyle | None = None,
        month_header_style: Style | DynamicStyle | None = None,
        block: Block | None = None,
        width: int | Expression[int] | None = None,
        height: int | Expression[int] | None = None,
        x: int | Expression[int] = 0,
        y: int | Expression[int] = 0,
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    def copy(self, /) -> Calendar: ...
    def __copy__(self, /) -> Calendar: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> Calendar: ...
    @property
    def weekdays_header_style(self) -> Style | DynamicStyle: ...
    @weekdays_header_style.setter
    def weekdays_header_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def events(self) -> Mapping[tuple[int, int, int], Style | DynamicStyle]: ...
    @events.setter
    def events(
        self, value: Mapping[tuple[int, int, int], Style | DynamicStyle]
    ) -> None: ...
    @property
    def day(self) -> int | Expression[int]: ...
    @day.setter
    def day(self, value: int | Expression[int]) -> None: ...
    @property
    def year(self) -> int | Expression[int]: ...
    @year.setter
    def year(self, value: int | Expression[int]) -> None: ...
    @property
    def month_header_style(self) -> Style | DynamicStyle: ...
    @month_header_style.setter
    def month_header_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def block(self) -> Block | None: ...
    @block.setter
    def block(self, value: Block | None) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle: ...
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def surrounding_style(self) -> Style | DynamicStyle: ...
    @surrounding_style.setter
    def surrounding_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def month(self) -> int | Expression[int]: ...
    @month.setter
    def month(self, value: int | Expression[int]) -> None: ...

class StateReference(Generic[StateType]):
    """
    A branch of a state store that can be read, written or bound.

    Examples:
        ```python
        store = TerminalStateStore({'count': 1}, schema=TerminalStateSchema.compile({}))
        reference = store.reference()['count']
        reference.set(2)
        assert Buffer().inspect(reference.number + 1) == 3
        ```
    """

    def __init__(
        self, /, store: TerminalStateStore, path: StatePath | None = None
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    def __hash__(self, /) -> int: ...
    def __eq__(self, value: Any, /) -> bool: ...
    def __copy__(self, /) -> StateReference: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> StateReference: ...
    def exists(self, /) -> bool: ...
    def get(self, /) -> Any: ...
    def set(
        self, /, value: Any, *, expected_revision: int | Expression[int] | None = None
    ) -> TerminalStateChange | None: ...
    def update(
        self,
        /,
        patch: TerminalStatePatch,
        *,
        expected_revision: int | Expression[int] | None = None,
    ) -> TerminalStateChange | None: ...
    @property
    def value(self) -> Value[Any]: ...
    @property
    def store(self) -> TerminalStateStore: ...
    @property
    def revision(self) -> int: ...
    @property
    def branch_revision(self) -> int: ...
    @property
    def number(self) -> NumericValue[int | float]: ...
    @property
    def native_store(self) -> TerminalStateStore: ...
    @property
    def schema(self) -> TerminalStateSchema: ...
    @property
    def path(self) -> StatePath: ...
    def __getitem__(self, key: str | int) -> StateReference: ...

class CellFilter:
    """
    A composable selection of cells affected by an animation.

    Examples:
        ```python
        filter = CellFilter.text() & ~CellFilter.background_color('blue')
        assert isinstance(filter, CellFilter)
        ```
    """

    def __repr__(self, /) -> str: ...
    def __hash__(self, /) -> int: ...
    def __eq__(self, value: Any, /) -> bool: ...
    def __invert__(self, /) -> CellFilter: ...
    def __and__(self, value: Any, /) -> CellFilter: ...
    def __or__(self, value: Any, /) -> CellFilter: ...
    @staticmethod
    def all() -> CellFilter: ...
    @staticmethod
    def text() -> CellFilter: ...
    @staticmethod
    def non_empty() -> CellFilter: ...
    @staticmethod
    def background() -> CellFilter: ...
    @staticmethod
    def background_only() -> CellFilter: ...
    @staticmethod
    def foreground_color(color: ColorValue | Expression[ColorValue]) -> CellFilter: ...
    @staticmethod
    def background_color(color: ColorValue | Expression[ColorValue]) -> CellFilter: ...
    @staticmethod
    def area(area: Rectangle) -> CellFilter: ...
    @staticmethod
    def inner(
        horizontal: int | Expression[int] = 1, vertical: int | Expression[int] = 1
    ) -> CellFilter: ...
    @staticmethod
    def outer(
        horizontal: int | Expression[int] = 1, vertical: int | Expression[int] = 1
    ) -> CellFilter: ...
    @staticmethod
    def all_of(*filters: CellFilter) -> CellFilter: ...
    @staticmethod
    def any_of(*filters: CellFilter) -> CellFilter: ...
    @staticmethod
    def none_of(*filters: CellFilter) -> CellFilter: ...
    @staticmethod
    def not_(filter: CellFilter) -> CellFilter: ...
    def __copy__(self, /) -> CellFilter: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> CellFilter: ...

class RunningEffect:
    """
    Playback controls and progress for a started animation.

    Examples:
        ```python
        with Runtime.offscreen(width=5, height=1) as runtime:
            buffer = Buffer('hello')
            runtime.mount(buffer)
            running = runtime.effects.start(Effect.dissolve(), buffer)
            running.pause()
            assert running.is_paused
            running.resume()
            running.cancel()
            assert running.is_done
        ```
    """

    def __repr__(self, /) -> str: ...
    def pause(self, /) -> None: ...
    def resume(self, /) -> None: ...
    def cancel(self, /) -> None: ...
    def restart(self, /) -> None: ...
    def reverse(self, /) -> None: ...
    def on_complete(self, /, callback: Callable[[], None]) -> None: ...
    @property
    def progress(self) -> float | Expression[float] | None: ...
    @property
    def is_paused(self) -> bool | Expression[bool]: ...
    @property
    def effect(self) -> Effect: ...
    @property
    def error(self) -> str | None: ...
    @property
    def elapsed_milliseconds(self) -> Any: ...
    @property
    def is_done(self) -> bool | Expression[bool]: ...
    @property
    def key(self) -> str | None: ...

class EffectManager:
    """
    Start, replace, inspect and cancel animations on a runtime.

    Examples:
        ```python
        with Runtime.offscreen(width=5, height=1) as runtime:
            buffer = Buffer('hello')
            runtime.mount(buffer)
            running = runtime.effects.start(Effect.fade_to('red'), buffer, key='fade')
            assert runtime.effects.is_running('fade')
            running.cancel()
        ```
    """

    def __repr__(self, /) -> str: ...
    def __len__(self, /) -> int: ...
    def start(
        self,
        /,
        effect: Effect,
        target: Buffer | Region,
        *,
        key: str | Expression[str] | None = None,
        area: Rectangle | None = None,
        filter: CellFilter | None = None,
    ) -> RunningEffect: ...
    def cancel(self, /, key: str | Expression[str]) -> None: ...
    def cancel_all(self, /) -> None: ...
    def is_running(self, /, key: str | Expression[str]) -> bool: ...
    def get(self, /, key: str | Expression[str]) -> RunningEffect | None: ...
    def running(self, /) -> list[RunningEffect]: ...

class Offset:
    """
    A displacement in terminal columns and rows.

    Examples:
        ```python
        assert Offset(1, 2) == Offset(1, 2)
        ```
    """

    def __init__(
        self, /, x: int | Expression[int] = 0, y: int | Expression[int] = 0
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    def __hash__(self, /) -> int: ...
    def __eq__(self, value: Any, /) -> bool: ...
    def __len__(self, /) -> int: ...
    def __copy__(self, /) -> Offset: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> Offset: ...
    @property
    def y(self) -> int: ...
    @property
    def x(self) -> int: ...
    def __add__(self, other: Offset) -> Offset: ...
    def __sub__(self, other: Offset) -> Offset: ...
    def __neg__(self) -> Offset: ...
    def __mul__(self, factor: int) -> Offset: ...
    def __rmul__(self, factor: int) -> Offset: ...

class Margin:
    """
    Horizontal and vertical inset distances.

    Examples:
        ```python
        assert Margin(1, 2).horizontal == 1
        ```
    """

    def __init__(
        self,
        /,
        horizontal: int | Expression[int] = 0,
        vertical: int | Expression[int] = 0,
    ) -> None: ...
    def __repr__(self, /) -> str: ...
    def __hash__(self, /) -> int: ...
    def __eq__(self, value: Any, /) -> bool: ...
    def __len__(self, /) -> int: ...
    def __copy__(self, /) -> Margin: ...
    def __deepcopy__(self, /, _memo: dict[int, Any]) -> Margin: ...
    @property
    def vertical(self) -> int: ...
    @property
    def horizontal(self) -> int: ...

X: NumericValue[int | float]
"""The horizontal position of a buffer or region, in terminal cells."""
Y: NumericValue[int | float]
"""The vertical position of a buffer or region, in terminal cells."""
Width: NumericValue[int | float]
"""The width of a buffer or region, in terminal cells."""
Height: NumericValue[int | float]
"""The height of a buffer or region, in terminal cells."""
Elapsed: NumericValue[int | float]
"""The elapsed runtime time, in seconds."""
Delta: NumericValue[int | float]
"""The elapsed time since the previous runtime frame, in seconds."""
ElapsedMilliseconds: NumericValue[int | float]
"""The elapsed runtime time, in milliseconds."""
DeltaMilliseconds: NumericValue[int | float]
"""The elapsed time since the previous runtime frame, in milliseconds."""
Frame: NumericValue[int | float]
"""The current runtime frame number."""
FPS: NumericValue[int | float]
"""The runtime's estimated frames per second."""
DeviceWidth: NumericValue[int | float]
"""The terminal width, in cells."""
DeviceHeight: NumericValue[int | float]
"""The terminal height, in cells."""
Position: Value[Point]
"""The position of a buffer or region as a ``Point``."""
Bounds: Value[Rectangle]
"""The full bounds of a buffer or region as a ``Rectangle``."""
BufferSize: Value[Size]
"""The dimensions of a buffer as a ``Size``."""
Focused: Value[bool]
"""Whether the runtime has focus."""
Running: Value[bool]
"""Whether the runtime is running."""
