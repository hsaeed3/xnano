"""
xnano_core._xnano_core

Type stubs for the compiled module behind the ``xnano_core`` package.

Every class and function here is implemented in Rust. The compiled module is the package
initializer, so ``xnano_core._xnano_core._core_types`` sits next to it.
"""

from collections.abc import Awaitable, Callable, Iterable, Iterator, Mapping, Sequence
from types import TracebackType
from typing import ClassVar, Generic, Literal, NoReturn, TypeVar, overload

from typing_extensions import Self

from ._core_types import (
    BorderKind as BorderKind,
)
from ._core_types import (
    CanvasShape as CanvasShape,
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
    CursorShape as CursorShape,
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
    EvolveSymbolSet as EvolveSymbolSet,
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
    PasteMode as PasteMode,
)
from ._core_types import (
    PixelAnchor as PixelAnchor,
)
from ._core_types import (
    PixelEncoding as PixelEncoding,
)
from ._core_types import (
    PixelEntry as PixelEntry,
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
    ScalarExpression as ScalarExpression,
)
from ._core_types import (
    Side as Side,
)
from ._core_types import (
    StatePath as StatePath,
)
from ._core_types import (
    TailwindColorBinding as TailwindColorBinding,
)
from ._core_types import (
    TailwindColorName as TailwindColorName,
)
from ._core_types import (
    TailwindColorShade as TailwindColorShade,
)
from ._core_types import (
    TextContent as TextContent,
)
from ._core_types import (
    TriggerKind as TriggerKind,
)
from ._core_types import (
    UpdateContext as UpdateContext,
)
from ._core_types import (
    WriteMode as WriteMode,
)

__version__: str
is_optimized_build: bool
"""Whether the extension was built with optimizations and without coverage instrumentation. Timing any other build says nothing."""

ValueType = TypeVar('ValueType')
ValueType_co = TypeVar('ValueType_co', covariant=True)
ChoiceType = TypeVar('ChoiceType')
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

    Attributes:
        x: The column.
        y: The row.

    Examples:
        ```python
        point = Point(2, 3) + Point(1, 1)
        assert (point.x, point.y) == (3, 4)
        assert point - Point(3, 4) == Point(0, 0)
        ```
    """

    def __init__(self, x: int = 0, y: int = 0) -> None:
        """
        Create a Point.

        Args:
            x: ``int``. Defaults to ``0``.
            y: ``int``. Defaults to ``0``.
        """
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

    Attributes:
        width: The number of columns.
        height: The number of rows.

    Examples:
        ```python
        size = Size(80, 24)
        assert (size.width, size.height) == (80, 24)
        ```
    """

    def __init__(self, width: int = 0, height: int = 0) -> None:
        """
        Create a Size.

        Args:
            width: ``int``. Defaults to ``0``.
            height: ``int``. Defaults to ``0``.
        """
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

    Attributes:
        x: The left column.
        y: The top row.
        width: The number of columns.
        height: The number of rows.
        position: The top-left corner.
        size: The width and height.
        area: The number of cells, ``width * height``.
        is_empty: Whether the rectangle holds no cells.

    Examples:
        ```python
        area = Rectangle(2, 1, 10, 4)
        assert area.area == 40
        assert area.contains(Point(2, 1))
        assert not area.contains(Point(12, 1))
        ```
    """

    def __init__(self, x: int = 0, y: int = 0, width: int = 0, height: int = 0) -> None:
        """
        Create a Rectangle.

        Args:
            x: ``int``. Defaults to ``0``.
            y: ``int``. Defaults to ``0``.
            width: ``int``. Defaults to ``0``.
            height: ``int``. Defaults to ``0``.
        """
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

    def translate(self, x: int = 0, y: int = 0) -> Rectangle:
        """
        Move the rectangle by a number of columns and rows.

        Args:
            x: Columns to move right; negative values move left.
            y: Rows to move down; negative values move up.

        Examples:
            ```python
            assert Rectangle(0, 0, 4, 2).translate(2, 1) == Rectangle(2, 1, 4, 2)
            assert Rectangle(5, 5, 4, 2).translate(x=-1, y=-2) == Rectangle(4, 3, 4, 2)
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

    Attributes:
        black: The black terminal color.
        red: The red terminal color.
        green: The green terminal color.
        yellow: The yellow terminal color.
        blue: The blue terminal color.
        magenta: The magenta terminal color.
        cyan: The cyan terminal color.
        gray: The gray terminal color.
        dark_gray: The dark gray terminal color.
        light_red: The light red terminal color.
        light_green: The light green terminal color.
        light_yellow: The light yellow terminal color.
        light_blue: The light blue terminal color.
        light_magenta: The light magenta terminal color.
        light_cyan: The light cyan terminal color.
        white: The white terminal color.
        reset: The reset terminal color, which follows the terminal theme.
        is_reset: Whether this is the ``reset`` color.

    Raises:
        ValueError: ``value`` is not a recognized color.

    Examples:
        ```python
        assert Color('#ff8800').to_rgb() == (255, 136, 0)
        assert Color((1, 2, 3)) == Color.from_rgb(1, 2, 3)
        assert Color('red').to_rgb() is None
        ```
    """

    black: ClassVar[Color]
    """The black terminal color."""
    red: ClassVar[Color]
    """The red terminal color."""
    green: ClassVar[Color]
    """The green terminal color."""
    yellow: ClassVar[Color]
    """The yellow terminal color."""
    blue: ClassVar[Color]
    """The blue terminal color."""
    magenta: ClassVar[Color]
    """The magenta terminal color."""
    cyan: ClassVar[Color]
    """The cyan terminal color."""
    gray: ClassVar[Color]
    """The gray terminal color."""
    dark_gray: ClassVar[Color]
    """The dark gray terminal color."""
    light_red: ClassVar[Color]
    """The light red terminal color."""
    light_green: ClassVar[Color]
    """The light green terminal color."""
    light_yellow: ClassVar[Color]
    """The light yellow terminal color."""
    light_blue: ClassVar[Color]
    """The light blue terminal color."""
    light_magenta: ClassVar[Color]
    """The light magenta terminal color."""
    light_cyan: ClassVar[Color]
    """The light cyan terminal color."""
    white: ClassVar[Color]
    """The white terminal color."""
    reset: ClassVar[Color]
    """The reset terminal color, which follows the terminal theme."""

    def __init__(self, value: ColorName | str | tuple[int, int, int]) -> None:
        """
        Create a Color.

        Args:
            value: ``ColorName | str | tuple[int, int, int]``.
        """
    @classmethod
    def parse(cls, value: ColorName | str) -> Color:
        """
        Parse a color name, hex string or palette index string.

        Examples:
            ```python
            assert Color.parse('light_blue') == Color('light_blue')
            ```
        """

    @classmethod
    def from_tailwind(
        cls, palette: TailwindColorName, shade: TailwindColorShade
    ) -> Color:
        """
        A true color from a Tailwind palette and shade.

        ``Color`` does not read a name such as ``'slate-400'``. Pass the palette and the
        shade here.

        Args:
            palette: A palette such as ``'slate'`` or ``'red'``.
            shade: ``50``, ``100`` through ``900``, or ``950``.

        Raises:
            ValueError: ``palette`` is not a palette, or ``shade`` is not a shade.

        Examples:
            ```python
            assert Color.from_tailwind('red', 500).to_rgb() == (239, 68, 68)
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

    def to_hex(self) -> str:
        """
        The color as a ``'#rrggbb'`` string.

        Only a true color has one, as with [`to_rgb`][xnano_core._xnano_core.Color.to_rgb].

        Raises:
            ValueError: The color is named, indexed or ``reset``, which the terminal's theme
                chooses.

        Examples:
            ```python
            assert Color((255, 136, 0)).to_hex() == '#ff8800'
            assert Color('#FF8800').to_hex() == '#ff8800'
            ```
        """

    @classmethod
    def from_hsl(cls, hue: float, saturation: float, lightness: float) -> Color:
        """
        A true color from hue, saturation and lightness.

        Args:
            hue: Degrees from 0 to 360.
            saturation: A percentage from 0 to 100.
            lightness: A percentage from 0 to 100.

        Raises:
            ValueError: A value is out of range.

        Examples:
            ```python
            assert Color.from_hsl(0, 100, 50).to_hex() == '#ff0000'
            ```
        """

    @classmethod
    def from_hsv(cls, hue: float, saturation: float, value: float) -> Color:
        """
        A true color from hue, saturation and value.

        Args:
            hue: Degrees from 0 to 360.
            saturation: A percentage from 0 to 100.
            value: A percentage from 0 to 100.

        Raises:
            ValueError: A value is out of range.

        Examples:
            ```python
            assert Color.from_hsv(120, 100, 100).to_hex() == '#00ff00'
            ```
        """

    def to_hsl(self) -> tuple[float, float, float]:
        """
        The hue (degrees), saturation and lightness (percentages) of the color.

        Named and indexed colors use their standard values.

        Raises:
            ValueError: The color is ``reset``.

        Examples:
            ```python
            hue, saturation, lightness = Color('#ff0000').to_hsl()
            assert round(hue) == 0
            assert round(saturation) == 100
            assert round(lightness) == 50
            ```
        """

    def to_hsv(self) -> tuple[float, float, float]:
        """
        The hue (degrees), saturation and value (percentages) of the color.

        Named and indexed colors use their standard values.

        Raises:
            ValueError: The color is ``reset``.

        Examples:
            ```python
            hue, saturation, value = Color('#00ff00').to_hsv()
            assert round(hue) == 120
            assert round(saturation) == 100
            assert round(value) == 100
            ```
        """

    def lerp(
        self,
        other: Color | ColorName | str | tuple[int, int, int],
        ratio: float,
        *,
        color_space: Literal['rgb', 'hsl', 'hsv'] = 'hsl',
    ) -> Color:
        """
        The color between this one and ``other``.

        Args:
            other: The color to blend toward.
            ratio: ``0.0`` is this color and ``1.0`` is ``other``.
            color_space: The space the blend runs through. ``'hsl'`` and ``'hsv'`` keep colors
                vivid in the middle; ``'rgb'`` is the straight average.

        Raises:
            ValueError: A color is ``reset``, or ``color_space`` is not a color space.

        Examples:
            ```python
            middle = Color('#000000').lerp('#ffffff', 0.5, color_space='rgb')
            red, green, blue = middle.to_rgb()
            assert red == green == blue
            assert 126 <= red <= 129
            ```
        """

    def lighten(
        self, amount: float, *, color_space: Literal['rgb', 'hsl', 'hsv'] = 'hsl'
    ) -> Color:
        """
        A lighter color for a positive ``amount``, a darker one for a negative ``amount``.

        Args:
            amount: A fraction from -1.0 (black) to 1.0 (white).
            color_space: The space the change runs through.

        Raises:
            ValueError: The color is ``reset``, or ``color_space`` is not a color space.

        Examples:
            ```python
            base = Color('#336699')
            assert base.lighten(0.2).to_hsl()[2] > base.to_hsl()[2]
            assert base.lighten(-0.2).to_hsl()[2] < base.to_hsl()[2]
            ```
        """

    def darken(
        self, amount: float, *, color_space: Literal['rgb', 'hsl', 'hsv'] = 'hsl'
    ) -> Color:
        """
        A darker color.

        Args:
            amount: A fraction from 0.0 (unchanged) to 1.0 (black). Use
                [`lighten`][xnano_core._xnano_core.Color.lighten] to make a color lighter.
            color_space: The space the change runs through.

        Returns:
            The darkened color; the original is unchanged.

        Raises:
            ValueError: ``amount`` is outside 0.0 to 1.0, the color is ``reset``, or
                ``color_space`` is not a color space.

        Examples:
            ```python
            assert Color('#808080').darken(1.0).to_rgb() == (0, 0, 0)
            base = Color('#336699')
            assert base.darken(0.2).to_hsl()[2] < base.to_hsl()[2]
            assert base.darken(0.0) == base
            ```
        """

    def inverse(self) -> Color:
        """
        The color that has each red, green and blue channel inverted.

        Named and indexed colors are inverted through their standard values, so the result
        is always a true color.

        Returns:
            The inverted true color; the original is unchanged.

        Raises:
            ValueError: The color is ``reset``, which has no fixed value.

        Examples:
            ```python
            assert Color('#ff8000').inverse().to_hex() == '#007fff'
            assert Color('#ff8000').inverse().inverse() == Color('#ff8000')
            ```
        """

    def saturate(
        self, factor: float, *, color_space: Literal['rgb', 'hsl', 'hsv'] = 'hsl'
    ) -> Color:
        """
        The color with its saturation scaled.

        Args:
            factor: ``0.0`` removes the saturation, ``1.0`` keeps it and more than ``1.0``
                boosts it.
            color_space: The space the change runs through.

        Raises:
            ValueError: The color is ``reset``, or ``color_space`` is not a color space.

        Examples:
            ```python
            gray = Color('#336699').saturate(0.0)
            assert round(gray.to_hsl()[1]) == 0
            ```
        """

    @property
    def is_reset(self) -> bool:
        """Whether this is the ``reset`` color, which follows the terminal's theme."""

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

    Attributes:
        foreground: The text color, or ``None`` when unset.
        background: The background color, or ``None`` when unset.
        modifiers: The enabled text modifiers.

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
        rapid_blink: bool = False,
        underline_color: ColorValue | None = None,
    ) -> None:
        """
        Create a Style.

        Args:
            foreground: ``ColorValue | None``. Defaults to ``None``.
            background: ``ColorValue | None``. Defaults to ``None``.
            bold: ``bool``. Defaults to ``False``.
            dim: ``bool``. Defaults to ``False``.
            italic: ``bool``. Defaults to ``False``.
            underline: ``bool``. Defaults to ``False``.
            blink: ``bool``. Defaults to ``False``.
            reverse: ``bool``. Defaults to ``False``.
            hidden: ``bool``. Defaults to ``False``.
            crossed_out: ``bool``. Defaults to ``False``.
            rapid_blink: ``bool``. Defaults to ``False``.
            underline_color: ``ColorValue | None``. Defaults to ``None``.
        """
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
    The time source a runtime reads, either real or stepped by hand.

    A monotonic clock follows real time, so wall-clock adjustments never affect it. A
    manual clock moves only when you step it, which makes tests and replays exact. Either
    kind can be stopped; a stopped clock does not move until it is resumed or stepped by hand.

    Attributes:
        source: Whether the clock follows real time or is stepped by hand.
        elapsed_seconds: Seconds since the clock started.
        elapsed_milliseconds: Milliseconds since the clock started.
        delta_seconds: Seconds between the two most recent frames.
        delta_milliseconds: Milliseconds between the two most recent frames.
        frame: The number of frames the clock has counted.
        frames_per_second: The frame rate measured over recent frames.
        is_stopped: Whether the clock is stopped.

    Examples:
        ```python
        clock = Clock.manual()
        clock.step(1500)
        assert clock.elapsed_seconds == 1.5
        assert clock.source == 'manual'
        ```
    """

    @classmethod
    def monotonic(cls, *, elapsed_seconds: float = 0.0, frame: int = 0) -> Clock:
        """
        A clock that follows real elapsed time.

        Args:
            elapsed_seconds: The time the clock starts at, zero or more.
            frame: The number of frames the clock has already counted, zero or more.

        Returns:
            A running clock that follows real time.

        Raises:
            ValueError: ``elapsed_seconds`` is negative or not finite, or ``frame`` is
                negative.

        Examples:
            ```python
            clock = Clock.monotonic()
            assert clock.source == 'monotonic'

            continued = Clock.monotonic(elapsed_seconds=2.0, frame=120)
            assert continued.elapsed_seconds >= 2.0
            assert continued.frame == 120
            ```
        """

    @classmethod
    def manual(cls, *, elapsed_seconds: float = 0.0) -> Clock:
        """
        A clock that moves only through [`step`][xnano_core._xnano_core.Clock.step].

        Args:
            elapsed_seconds: The time the clock starts at, zero or more.

        Raises:
            ValueError: ``elapsed_seconds`` is negative or not finite.

        Examples:
            ```python
            clock = Clock.manual(elapsed_seconds=2.0)
            assert clock.elapsed_milliseconds == 2000.0
            ```
        """

    @property
    def source(self) -> Literal['monotonic', 'manual']:
        """Whether the clock follows real time or is stepped by hand."""

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
    def is_stopped(self) -> bool:
        """Whether the clock is stopped."""

    def stop(self) -> None:
        """
        Stop time from advancing.

        The time spent stopped is not counted in ``elapsed_seconds``.

        Examples:
            ```python
            clock = Clock.manual()
            clock.stop()
            assert clock.is_stopped
            ```
        """

    def resume(self) -> None:
        """
        Let time advance again after it was stopped.

        Examples:
            ```python
            clock = Clock.manual()
            clock.stop()
            clock.resume()
            assert not clock.is_stopped
            ```
        """

    def step(self, milliseconds: int) -> None:
        """
        Move time forward by exactly ``milliseconds``.

        A manual clock can always be stepped. A monotonic clock can be stepped only while it
        is stopped, which lets a stopped clock advance one frame at a time.

        Args:
            milliseconds: How far to move, zero or more.

        Raises:
            ValueError: ``milliseconds`` is negative, or the clock is a monotonic clock
                that is running.

        Examples:
            ```python
            clock = Clock.monotonic()
            clock.stop()
            before = clock.elapsed_milliseconds
            clock.step(250)
            assert abs(clock.elapsed_milliseconds - (before + 250.0)) < 1e-6

            manual = Clock.manual()
            manual.step(100)
            assert manual.elapsed_milliseconds == 100.0
            ```
        """

    def derive(self, *, rate: float = 1.0, is_stopped: bool = False) -> SimulationClock:
        """
        Create a clock that follows this one at a different speed.

        Args:
            rate: How fast the new clock runs compared to this one. Zero or more.
            is_stopped: Whether the new clock starts stopped.

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
    A clock derived from a parent clock, with its own rate and stopped state.

    Changing the rate keeps elapsed time continuous. Rates are finite and nonnegative.

    Attributes:
        parent: The clock this clock follows.
        rate: How fast this clock runs compared to its parent. Assign to change it.
        is_stopped: Whether this clock is stopped. Assign to stop or resume it.
        elapsed_seconds: Seconds of simulation time.
        delta_seconds: Seconds of simulation time between the two most recent calls to
            ``sample``.

    Examples:
        ```python
        simulation = Clock.manual().derive(rate=1.0)
        simulation.rate = 2.0
        simulation.is_stopped = True
        assert simulation.rate == 2.0
        assert simulation.is_stopped
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
    def is_stopped(self) -> bool:
        """Whether this clock is stopped. Assign to stop or resume it."""

    @is_stopped.setter
    def is_stopped(self, value: bool) -> None: ...
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
            parent.step(100)
            simulation.sample()
            assert simulation.delta_seconds == 0.2
            ```
        """

    def stop(self) -> None:
        """
        Stop this clock without affecting its parent.

        Examples:
            ```python
            simulation = Clock.manual().derive()
            simulation.stop()
            assert simulation.is_stopped
            ```
        """

    def resume(self) -> None:
        """
        Resume this clock after it was stopped.

        Examples:
            ```python
            simulation = Clock.manual().derive(is_stopped=True)
            simulation.resume()
            assert not simulation.is_stopped
            ```
        """

class TextSpan:
    """
    A run of text with one style.

    Maps to [`ratatui::text::Span`](https://docs.rs/ratatui/0.30.0/ratatui/text/struct.Span.html).

    Args:
        text: The text.
        style: The style of the whole run.

    Attributes:
        text: The text of the run.
        style: The style of the run.

    Examples:
        ```python
        span = TextSpan('warning', style=Style('yellow', bold=True))
        assert span.text == 'warning'
        assert 'bold' in span.style.modifiers
        ```
    """

    def __init__(self, text: str, *, style: Style | None = None) -> None:
        """
        Create a TextSpan.

        Args:
            text: ``str``.
            style: ``Style | None``. Defaults to ``None``.
        """
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

    Attributes:
        spans: The runs of text, in order.

    Examples:
        ```python
        text = StyledText([TextSpan('error: ', style=Style('red')), TextSpan('disk full')])
        assert str(text) == 'error: disk full'
        assert len(text.spans) == 2
        ```
    """

    def __init__(self, spans: Sequence[TextSpan]) -> None:
        """
        Create a StyledText.

        Args:
            spans: ``Sequence[TextSpan]``.
        """
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
    One wrapped line of a [`TextLayout`][xnano_core._xnano_core.TextLayout].

    Attributes:
        text: The text of the line.
        start_offset: Where the line starts in the original text, counted in Python string
            offsets.
        end_offset: Where the line ends in the original text, counted in Python string offsets.
        width: The number of cells the line occupies.

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

    Attributes:
        lines: The wrapped lines.
        cursor_cell: The ``(column, row)`` of the cursor, or ``None`` when no cursor was given.

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

    Draw it with [`Editor`][xnano_core._xnano_core.Editor].

    Args:
        text: The starting text.
        is_single_line: Whether line breaks are refused.

    Attributes:
        text: The current text.
        is_single_line: Whether line breaks are refused.
        cursor_offset: The cursor position, counted in Python string offsets.
        placeholder_text: The text shown while the editor is empty. Assign to change it.

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

    def __init__(self, text: str = '', *, is_single_line: bool = False) -> None:
        """
        Create a TextEditor.

        Args:
            text: ``str``. Defaults to ``''``.
            is_single_line: ``bool``. Defaults to ``False``.
        """
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
    Draw a [`TextEditor`][xnano_core._xnano_core.TextEditor] into a buffer.

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
    ) -> None:
        """
        Create a Editor.

        Args:
            editor: ``TextEditor``.
            area: ``Rectangle | None``. Defaults to ``None``.
            style: ``Style | None``. Defaults to ``None``.
            first_row: ``int``. Defaults to ``0``.
            should_wrap: ``bool``. Defaults to ``True``.
            should_show_cursor: ``bool``. Defaults to ``True``.
            mode: ``WriteMode``. Defaults to ``'preserve_background'``.
        """

class KeyEvent:
    """
    A key press, repeat or release.

    Get one from [`Event.key`][xnano_core._xnano_core.Event.key] or build an event with
    [`Event.key_press`][xnano_core._xnano_core.Event.key_press].

    Attributes:
        key: The key name, such as ``'a'``, ``'enter'`` or ``'page_up'``.
        text: The text the key types, or ``None`` for control keys and chords.
        modifiers: The modifier keys held.
        kind: Whether the key was pressed, repeated or released.

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

    Attributes:
        position: The cell under the pointer.
        column: The column under the pointer.
        row: The row under the pointer.
        kind: What the mouse did.
        button: The button involved, or ``None`` for moves and scrolls.
        scroll_x: Horizontal scroll steps, negative for left and positive for right.
        scroll_y: Vertical scroll steps, negative for up and positive for down.

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
    def scroll_x(self) -> int:
        """Horizontal scroll steps, negative for left and positive for right."""

    @property
    def scroll_y(self) -> int:
        """Vertical scroll steps, negative for up and positive for down."""

class Event:
    """
    Something that happened: input, a resize, a timer or a frame.

    Hooks and the runtime report everything as an event. Build events with the class
    methods to test code without a terminal.

    Attributes:
        kind: What the event reports.
        timestamp_seconds: Seconds on the runtime clock when the event happened.
        key: The key details of a key event, otherwise ``None``.
        mouse: The mouse details of a mouse event, otherwise ``None``.
        pasted_text: The pasted text of a paste event, otherwise ``None``.
        size: The new size of a resize event, otherwise ``None``.
        timer_key: The key of a timer event, otherwise ``None``.
        custom_name: The name of a custom event, otherwise ``None``.
        custom_data: The data of a custom event, otherwise ``None``.

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
        scroll_x: int = 0,
        scroll_y: int = 0,
    ) -> Event:
        """
        A mouse event.

        Args:
            column: The column under the pointer.
            row: The row under the pointer.
            kind: What the mouse did.
            button: The button involved in a press, release or drag.
            scroll_x: Horizontal scroll steps, negative for left and positive for right.
            scroll_y: Vertical scroll steps, negative for up and positive for down.

        Examples:
            ```python
            event = Event.mouse_event(column=0, row=0, kind='scroll', scroll_y=-1)
            assert event.mouse.scroll_y == -1

            sideways = Event.mouse_event(column=0, row=0, kind='scroll', scroll_x=2)
            assert (sideways.mouse.scroll_x, sideways.mouse.scroll_y) == (2, 0)
            ```
        """

    @classmethod
    def tick(cls) -> Event:
        """
        Create a tick event, as a runtime with a tick interval reports.

        Examples:
            ```python
            assert Event.tick().kind == 'tick'
            ```
        """

    @classmethod
    def timer(cls, key: str) -> Event:
        """
        Create a timer event for the timer called ``key``.

        Examples:
            ```python
            assert Event.timer('blink').timer_key == 'blink'
            ```
        """

    @classmethod
    def wake(cls) -> Event:
        """
        Create a wake event, which only makes a runtime run an iteration.

        Examples:
            ```python
            assert Event.wake().kind == 'wake'
            ```
        """

    @classmethod
    def exit_requested(cls) -> Event:
        """
        Create the event a runtime reports when the application is asked to exit.

        Examples:
            ```python
            assert Event.exit_requested().kind == 'exit_requested'
            ```
        """

    @classmethod
    def custom(cls, name: str, *, data: str | None = None) -> Event:
        """
        Create an event your application defines.

        Inject it with [`Runtime.inject`][xnano_core._xnano_core.Runtime.inject] and listen
        for it with a hook on ``'custom'`` events. Text such as JSON can travel in ``data``.

        Args:
            name: What the event is, such as ``'volume_changed'``.
            data: Optional text that travels with the event.

        Raises:
            ValueError: The name is empty.

        Examples:
            ```python
            event = Event.custom('volume_changed', data='40')
            assert event.kind == 'custom'
            assert (event.custom_name, event.custom_data) == ('volume_changed', '40')
            ```
        """

    @property
    def custom_name(self) -> str | None:
        """The name of a custom event, otherwise ``None``."""

    @property
    def custom_data(self) -> str | None:
        """The data of a custom event, otherwise ``None``."""

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

    Get one from [`Runtime.events`][xnano_core._xnano_core.Runtime.events]. Iterate it
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

    Get one from [`Runtime.waker`][xnano_core._xnano_core.Runtime.waker]. It is the only
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
    [`Surface.add_hook`][xnano_core._xnano_core.Surface.add_hook].

    Attributes:
        enabled: Whether the hook runs. Assign ``False`` to pause it and ``True`` to resume.
        priority: The hook's priority.
        is_cancelled: Whether the hook was cancelled.

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

    Attributes:
        is_cancelled: Whether the call was cancelled.

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

    Attributes:
        enhancement: Whether the enhanced keyboard protocol is available.
        disambiguates_keys: Whether keys such as ``escape`` and ``alt+key`` are told apart.
        reports_event_types: Whether key repeats and releases are reported.
        reports_all_keys: Whether modifier keys on their own are reported.
        unavailable_reason: Why the enhanced protocol is unavailable, or ``None``.
        enabled_features: The protocol features that are switched on.

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
        mouse: The requested mouse mode. Button and motion reports reach the runtime only when
            this is not ``'off'``.
        scroll: Whether mouse wheel reports reach the runtime. It is independent of ``mouse``:
            ``InputOptions(scroll=True)`` delivers the wheel and no button or motion reports.
        bracketed_paste: Whether pasted text arrives as one paste event.
        focus_reporting: Whether the terminal reports focus changes.
        keyboard: The requested keyboard mode. ``'off'`` drops key events that come from the
            terminal, except Ctrl+C when ``interrupt`` is ``'stop'``, so a runtime without a
            keyboard can still be stopped.
        capability_timeout_milliseconds: How long to wait for capability answers.
        interrupt: Whether Ctrl+C becomes an ``'event'`` or ``'stop'`` the runtime.

    Raises:
        ValueError: A mode is not one of the listed values.

    Attributes:
        mouse: The requested mouse mode.
        scroll: Whether mouse wheel reports are requested.
        bracketed_paste: Whether bracketed paste is requested.
        focus_reporting: Whether focus reporting is requested.
        keyboard: The requested keyboard mode.
        capability_timeout_milliseconds: How long capability queries wait.
        interrupt: How Ctrl+C is handled.

    Examples:
        ```python
        options = InputOptions(mouse='buttons', keyboard='release_events')
        assert options.mouse == 'buttons'
        terminal = TerminalOptions(input=options)

        wheel_only = InputOptions(scroll=True, keyboard='off', interrupt='stop')
        assert wheel_only.scroll and wheel_only.mouse == 'off'
        assert wheel_only.keyboard == 'off'
        ```
    """

    def __init__(
        self,
        *,
        mouse: Literal['off', 'buttons', 'motion'] = 'off',
        scroll: bool = False,
        bracketed_paste: bool = True,
        focus_reporting: bool = True,
        keyboard: Literal['off', 'basic', 'disambiguated', 'release_events'] = 'basic',
        capability_timeout_milliseconds: int = 200,
        interrupt: Literal['event', 'stop'] = 'event',
    ) -> None:
        """
        Create a InputOptions.

        Args:
            mouse: ``Literal['off', 'buttons', 'motion']``. Defaults to ``'off'``.
            scroll: ``bool``. Defaults to ``False``.
            bracketed_paste: ``bool``. Defaults to ``True``.
            focus_reporting: ``bool``. Defaults to ``True``.
            keyboard: ``Literal['off', 'basic', 'disambiguated', 'release_events']``. Defaults
                to ``'basic'``.
            capability_timeout_milliseconds: ``int``. Defaults to ``200``.
            interrupt: ``Literal['event', 'stop']``. Defaults to ``'event'``.
        """
    @property
    def mouse(self) -> Literal['off', 'buttons', 'motion']:
        """The requested mouse mode."""

    @property
    def scroll(self) -> bool:
        """Whether mouse wheel reports are requested."""

    @property
    def bracketed_paste(self) -> bool:
        """Whether bracketed paste is requested."""

    @property
    def focus_reporting(self) -> bool:
        """Whether focus reporting is requested."""

    @property
    def keyboard(self) -> Literal['off', 'basic', 'disambiguated', 'release_events']:
        """The requested keyboard mode."""

    @property
    def capability_timeout_milliseconds(self) -> int:
        """How long capability queries wait."""

    @property
    def interrupt(self) -> Literal['event', 'stop']:
        """How Ctrl+C is handled."""

    def __repr__(self) -> str:
        """
        Every option in keyword form.

        Examples:
            ```python
            assert repr(InputOptions(scroll=True)).startswith("InputOptions(mouse='off', scroll=True")
            ```
        """

    def __eq__(self, other: object) -> bool:
        """
        Whether ``other`` is an ``InputOptions`` with the same options.

        Examples:
            ```python
            assert InputOptions(scroll=True) == InputOptions(scroll=True)
            assert InputOptions(scroll=True) != InputOptions()
            ```
        """

    __hash__: ClassVar[None]  # type: ignore[assignment]

class TerminalOptions:
    """
    How a live runtime takes over the terminal.

    Args:
        input: The input modes to request.
        alternate_screen: Whether to draw on the alternate screen.
        raw_mode: Whether to put the terminal in raw mode.
        drain_reports_on_exit: Whether to discard pending terminal replies on exit.
        drain_timeout_milliseconds: How long to wait while discarding replies.
        should_clear_on_close: Whether the area the runtime drew in is erased when it
            closes, instead of staying on the screen. Applies when the alternate screen is
            not used, such as an inline runtime.
        should_capture_output: Whether text written to standard output and standard error
            while the session is open is held back instead of reaching the screen. It is
            printed to the stream it was written to when the runtime closes, or read earlier
            with [`Runtime.take_captured_output`][xnano_core._xnano_core.Runtime.take_captured_output].
            Captured on Unix only.

    Attributes:
        input: The requested input modes.
        alternate_screen: Whether the alternate screen is used.
        raw_mode: Whether raw mode is used.
        drain_reports_on_exit: Whether pending terminal replies are discarded on exit.
        drain_timeout_milliseconds: How long discarding replies may take.
        should_capture_output: Whether text printed during the session is held back from the
            screen.
        should_clear_on_close: Whether the runtime's area is erased when it closes.

    Examples:
        ```python
        options = TerminalOptions(alternate_screen=False)
        assert options.raw_mode
        assert not options.alternate_screen
        assert options.should_capture_output
        assert not options.should_clear_on_close
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
        should_capture_output: bool = True,
        should_clear_on_close: bool = False,
    ) -> None:
        """
        Create a TerminalOptions.

        Args:
            input: ``InputOptions | None``. Defaults to ``None``.
            alternate_screen: ``bool``. Defaults to ``True``.
            raw_mode: ``bool``. Defaults to ``True``.
            drain_reports_on_exit: ``bool``. Defaults to ``True``.
            drain_timeout_milliseconds: ``int``. Defaults to ``250``.
            should_capture_output: ``bool``. Defaults to ``True``.
            should_clear_on_close: ``bool``. Defaults to ``False``.
        """
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

    @property
    def should_capture_output(self) -> bool:
        """Whether text printed during the session is held back from the screen."""

    @property
    def should_clear_on_close(self) -> bool:
        """Whether the runtime's area is erased when it closes."""

class Cursor:
    """
    The one cursor a terminal has.

    A runtime has exactly one cursor, so it belongs to the runtime rather than to any
    buffer. It is hidden until it is given a position. Every property may be changed from
    any thread, and a change is drawn on the next frame even when no cell changed. A live
    runtime gives the user's own cursor back when it closes.

    Get it from [`Runtime.cursor`][xnano_core._xnano_core.Runtime.cursor].

    Attributes:
        position: The cell the cursor is at, counted from the top-left of the runtime's area.
        shape: ``'block'``, ``'bar'`` or ``'underline'``; ``None`` keeps the user's own shape.
        is_blinking: Whether the cursor blinks. Setting it without a shape uses a block.
        is_visible: Whether the cursor is shown when it has a position. ``True`` by default.

    Examples:
        ```python
        with Runtime.offscreen(width=10, height=3) as runtime:
            runtime.mount(Buffer(), geometry='inherit')
            runtime.cursor.position = (3, 1)
            runtime.cursor.shape = 'bar'
            frame = runtime.render()
            assert frame.cursor_position == Point(3, 1)
            runtime.cursor.is_visible = False
            assert not runtime.render().is_cursor_visible
        ```
    """

    @property
    def position(self) -> Point | None:
        """
        The cell the cursor is at, counted from the top-left of the runtime's area.

        Assign a ``Point``, a ``(column, row)`` pair or ``None`` to hide the cursor.
        Assigning a position stops the cursor following a buffer. A cursor outside the
        area is not shown.
        """

    @position.setter
    def position(self, value: Point | tuple[int, int] | None) -> None: ...
    @property
    def shape(self) -> CursorShape | None:
        """
        ``'block'``, ``'bar'`` or ``'underline'``; ``None`` keeps the user's own shape.

        Raises:
            ValueError: When assigned another name.
        """

    @shape.setter
    def shape(self, value: CursorShape | None) -> None: ...
    @property
    def is_blinking(self) -> bool:
        """Whether the cursor blinks. Setting it without a shape uses a block."""

    @is_blinking.setter
    def is_blinking(self, value: bool) -> None: ...
    @property
    def is_visible(self) -> bool:
        """Whether the cursor is shown when it has a position. ``True`` by default."""

    @is_visible.setter
    def is_visible(self, value: bool) -> None: ...
    def follow(self, buffer: Buffer | None, *, x: int = 0, y: int = 0) -> None:
        """
        Keep the cursor at a place inside a buffer, wherever the buffer is.

        The cursor is hidden while the buffer or any buffer above it is hidden.

        Args:
            buffer: The buffer to follow, or ``None`` to stop following.
            x: The column inside the buffer.
            y: The row inside the buffer.

        Examples:
            ```python
            with Runtime.offscreen(width=10, height=3) as runtime:
                field = Buffer(width=6, height=1, x=2, y=1)
                runtime.mount(field)
                runtime.cursor.follow(field, x=4)
                assert runtime.render().cursor_position == Point(6, 1)
                field.x = 3
                assert runtime.render().cursor_position == Point(7, 1)
            ```
        """

class InputState:
    """
    The keys and pointer position a runtime currently sees.

    Reliable pressed keys require negotiated release reporting. In reliable mode keys are
    cleared on focus loss, unmount and shutdown. When release reporting is unavailable,
    ``pressed_keys`` is empty and the opt-in timeout estimates appear in
    ``estimated_pressed_keys`` instead, so an estimate never passes as a real held key.

    Attributes:
        held_keys_available: Whether the terminal reports key releases.
        pressed_keys: The keys currently held, when releases are reported, and the held mouse
            buttons as ``'mouse_left'``, ``'mouse_right'`` and ``'mouse_middle'``.
        estimated_pressed_keys: The keys guessed to be held from a timeout, when estimates are
            enabled.
        pointer_cell: The ``(column, row)`` under the pointer, or ``None``.
        last_key: The key of the latest key event, or ``None`` while the latest input was not a
            key.
        last_key_kind: ``'press'``, ``'repeat'`` or ``'release'`` for the latest key event, or
            ``None``.
        last_chord: The latest key event with its modifiers as text such as ``'ctrl+s'``, or
            ``None``. Modifiers come in the order ``ctrl``, ``alt``, ``shift``, ``super``,
            ``meta``, ``hyper``.
        last_mouse_button: ``'left'``, ``'right'`` or ``'middle'`` for the latest button or
            motion report, or ``None``.
        last_mouse_kind: ``'press'``, ``'release'``, ``'drag'`` or ``'move'`` for the latest
            button or motion report. ``None`` for a wheel report and while the latest input was
            not a mouse event.
        last_mouse_position: The ``(column, row)`` of the latest button or motion report, or
            ``None``. Unlike ``pointer_cell`` it is cleared by any other kind of input.
        scroll_x: The horizontal steps of the latest wheel report of the current step (right is
            positive), ``0`` when no wheel report arrived or any other input followed it.
        scroll_y: The vertical steps of the latest wheel report of the current step (down is
            positive, so scrolling up is ``-1``), ``0`` when no wheel report arrived or any
            other input followed it.
        is_mouse_down: Whether any mouse button is held.
        last_pasted_text: The text of the latest paste, or ``None`` while the latest input was
            not a paste.

    Each kind of input clears the "latest" values of the other kinds, so a value is ``None``
    unless the latest input was of its kind. Held mouse buttons are named ``'mouse_left'``,
    ``'mouse_right'`` and ``'mouse_middle'`` in ``pressed_keys``.

    Examples:
        ```python
        with Runtime.offscreen(width=10, height=3) as runtime:
            state = runtime.input
            assert state.pressed_keys == frozenset()
            assert state.pointer_cell is None

            runtime.inject(Event.key_press('ctrl+s'))
            runtime.step()
            assert state.last_key == 's' and state.last_chord == 'ctrl+s'

            runtime.inject(Event.mouse_event(column=4, row=1, kind='press', button='left'))
            runtime.step()
            assert state.is_mouse_down and 'mouse_left' in state.pressed_keys
            assert state.last_mouse_position == (4, 1) and state.last_key is None

            runtime.inject(Event.mouse_event(column=4, row=1, kind='release', button='left'))
            runtime.inject(Event.mouse_event(column=4, row=1, kind='scroll', scroll_y=-1))
            runtime.step()
            assert not state.is_mouse_down
            assert state.scroll_y == -1 and state.last_mouse_kind is None

            runtime.step()
            assert state.scroll_y == 0
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

    @property
    def last_key(self) -> str | None:
        """The key of the latest key event, or ``None``."""

    @property
    def last_key_kind(self) -> Literal['press', 'repeat', 'release'] | None:
        """Whether the latest key event was a press, repeat or release."""

    @property
    def last_chord(self) -> str | None:
        """The latest key event with its modifiers, such as ``'ctrl+s'``."""

    @property
    def last_mouse_button(self) -> MouseButton | None:
        """The button of the latest button or motion report."""

    @property
    def last_mouse_kind(self) -> Literal['press', 'release', 'drag', 'move'] | None:
        """The kind of the latest button or motion report; ``None`` for a wheel report."""

    @property
    def last_mouse_position(self) -> tuple[int, int] | None:
        """The ``(column, row)`` of the latest button or motion report."""

    @property
    def scroll_x(self) -> int:
        """The horizontal steps of the latest wheel report of the current step."""

    @property
    def scroll_y(self) -> int:
        """The vertical steps of the latest wheel report of the current step."""

    @property
    def is_mouse_down(self) -> bool:
        """Whether any mouse button is held."""

    @property
    def last_pasted_text(self) -> str | None:
        """The text of the latest paste."""

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

    Attributes:
        backend: Whether output goes to a real terminal or an in-memory screen.
        size: The size of the display in cells.
        window_size_in_pixels: The size of the window in pixels, or ``None`` when unknown.
        capabilities: What the terminal can display.
        keyboard: What the keyboard protocol can report.
        is_focused: Whether the terminal window has focus.
        is_inline: Whether the runtime draws inline instead of taking the whole screen.
        is_raw_mode_enabled: Whether raw mode is on.
        is_mouse_capture_enabled: Whether mouse capture is on.
        is_bracketed_paste_enabled: Whether bracketed paste is on.
        is_focus_reporting_enabled: Whether focus reporting is on.
        is_alternate_screen_enabled: Whether the alternate screen is on.

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

    Create one with [`InputRouter.hit_area`][xnano_core._xnano_core.InputRouter.hit_area].

    Attributes:
        key: The name the hit area was registered with.
        bounds: The rectangle, relative to the target. Assign to move or resize it.

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

    Attributes:
        is_active: Whether the scope is open.

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

    Get it from [`Runtime.router`][xnano_core._xnano_core.Runtime.router].

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

    Attributes:
        is_terminal: Whether standard output is a terminal.
        is_live_terminal_available: Whether a live terminal runtime can run here.
        color_profile: How many colors the terminal displays.
        graphics_protocol: The best image protocol the terminal supports.
        cell_size_in_pixels: The ``(width, height)`` of one cell in pixels, or ``None`` when
            unknown.
        synchronized_output: Whether the terminal supports synchronized output.

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

class Expression(Generic[ValueType_co]):
    """
    A value or action described now and evaluated later against a buffer or runtime.

    Evaluation is explicit. Using an expression where Python wants a truth value raises
    ``TypeError``; combine conditions with ``&``, ``|`` and ``~`` instead.

    Examples:
        ```python
        from xnano_core._xnano_core import _reference

        width = _reference('Width', 'numeric_property')
        buffer = Buffer(width=8, height=1)
        assert buffer.inspect(width + 2) == 10
        assert (width + 2).evaluate(EvaluationContext(buffer=buffer)) == 10
        ```
    """

    def evaluate(self, context: EvaluationContext) -> ValueType_co:
        """
        Compute the expression's value.

        Examples:
            ```python
            from xnano_core._xnano_core import _reference

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
    ``==`` and ``!=`` also build predicates, so ``(Width > 4) == False`` is a condition and not
    a ``bool``.

    Examples:
        ```python
        from xnano_core._xnano_core import _reference

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
            from xnano_core._xnano_core import _reference

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
            from xnano_core._xnano_core import _reference

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
            from xnano_core._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            buffer = Buffer(width=8, height=1)
            assert buffer.inspect(~(width < 4))
            ```
        """

    def __eq__(self, other: object) -> Predicate:  # type: ignore[override]  # pyright: ignore[reportIncompatibleMethodOverride]
        """
        A predicate that is true when this condition has the same truth value as ``other``.

        Examples:
            ```python
            from xnano_core._xnano_core import Width

            wide = Width > 4
            assert Buffer(width=2, height=1).inspect(wide == False)  # noqa: E712
            ```
        """

    def __ne__(self, other: object) -> Predicate:  # type: ignore[override]  # pyright: ignore[reportIncompatibleMethodOverride]
        """
        A predicate that is true when this condition has a different truth value than ``other``.

        Examples:
            ```python
            from xnano_core._xnano_core import Width

            wide = Width > 4
            assert Buffer(width=2, height=1).inspect(wide != True)  # noqa: E712
            ```
        """

    def __hash__(self) -> int:
        """The identity hash, which keeps predicates usable in sets and dictionaries."""

    @overload
    def choose(
        self, when_true: NumberType, when_false: NumberType
    ) -> NumericValue[NumberType]: ...
    @overload
    def choose(
        self,
        when_true: NumericValue[NumberType],
        when_false: NumericValue[NumberType] | NumberType,
    ) -> NumericValue[NumberType]: ...
    @overload
    def choose(
        self,
        when_true: ChoiceType | Value[ChoiceType],
        when_false: ChoiceType | Value[ChoiceType],
    ) -> Value[ChoiceType]: ...
    def choose(self, when_true: object, when_false: object) -> Value[object]:
        """
        A value that is ``when_true`` while the condition holds and ``when_false`` otherwise.

        Numbers give a [`NumericValue`][xnano_core._xnano_core.NumericValue], so the result
        supports arithmetic and ordering. Raises ``TypeError`` when evaluated if the predicate
        is not a condition.

        Examples:
            ```python
            from xnano_core._xnano_core import Width

            wide = Width > 10
            assert Buffer(width=20, height=1).inspect(wide.choose(1, 2)) == 1
            assert Buffer(width=4, height=1).inspect(wide.choose(1, 2)) == 2
            assert Buffer(width=4, height=1).inspect(wide.choose(Width, 0) + 1) == 1
            ```
        """

class Value(Expression[ValueType]):
    """
    An expression that evaluates to a value.

    ``==`` and ``!=`` build conditions, as ``equals`` and ``not_equals`` do. A comparison with a
    value that has not been seen yet, such as the key before any key was pressed, is false
    (``!=`` included) and never an error. Comparing with the literal ``None`` raises ``TypeError``
    because that condition could never hold; to test that a key arrived, compare with the key
    itself or register the hook for the ``'key'`` event. A value is hashed by identity, so expressions stay usable
    in sets and dictionaries. Because ``==`` builds a condition, ``in`` and ``.index()`` on a list
    or tuple of expressions raise ``TypeError`` as soon as they compare an expression with a
    different item; look an expression up by identity (``any(item is value for item in items)``)
    or keep expressions in a set or dictionary. Comparing an expression with an object that cannot
    be an expression, such as ``object()``, gives ``False`` for ``==`` and ``True`` for ``!=``.

    Attributes:
        x: The column of a ``Point`` or the left edge of a ``Rectangle``.
        y: The row of a ``Point`` or the top edge of a ``Rectangle``.
        width: The width of a ``Size`` or a ``Rectangle``.
        height: The height of a ``Size`` or a ``Rectangle``.
        right: The first column after a ``Rectangle``.
        bottom: The first row after a ``Rectangle``.

    Examples:
        ```python
        from xnano_core._xnano_core import _reference

        bounds = _reference('Bounds', 'value')
        assert isinstance(bounds, Value)
        buffer = Buffer(width=4, height=1)
        assert buffer.inspect(bounds.equals(Rectangle(0, 0, 4, 1)))
        assert buffer.inspect(bounds == Rectangle(0, 0, 4, 1))
        ```
    """

    def equals(self, other: ValueType | Value[ValueType]) -> Predicate:
        """
        A predicate that is true when the value equals ``other``.

        Examples:
            ```python
            from xnano_core._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            assert Buffer(width=20, height=1).inspect(width.equals(20))
            ```
        """

    def not_equals(self, other: ValueType | Value[ValueType]) -> Predicate:
        """
        A predicate that is true when the value differs from ``other``.

        Examples:
            ```python
            from xnano_core._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            assert Buffer(width=20, height=1).inspect(width.not_equals(5))
            ```
        """

    def contains(
        self: Value[Rectangle],
        other: Point | Value[Point] | Value[Point | None],
    ) -> Predicate:
        """
        A condition that is true while this rectangle contains the point ``other``.

        It is false, never an error, while either side has no value yet, such as a mouse
        position before any mouse event.

        Args:
            other: The ``Point`` (or an expression that produces one) to look for.

        Examples:
            ```python
            from xnano_core._xnano_core import Bounds, Point

            buffer = Buffer(width=4, height=2)
            assert buffer.inspect(Bounds.contains(Point(3, 1)))
            assert not buffer.inspect(Bounds.contains(Point(4, 1)))
            ```
        """

    def __eq__(self, other: object) -> Predicate:  # type: ignore[override]  # pyright: ignore[reportIncompatibleMethodOverride]
        """
        A predicate that is true when the value equals ``other``; the same as ``equals``.

        Examples:
            ```python
            from xnano_core._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            assert Buffer(width=20, height=1).inspect(width == 20)
            ```
        """

    def __ne__(self, other: object) -> Predicate:  # type: ignore[override]  # pyright: ignore[reportIncompatibleMethodOverride]
        """
        A predicate that is true when the value differs from ``other``; the same as ``not_equals``.

        Examples:
            ```python
            from xnano_core._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            assert Buffer(width=20, height=1).inspect(width != 5)
            ```
        """

    def __hash__(self) -> int:
        """The identity hash, which keeps expressions usable in sets and dictionaries."""

    @property
    def x(self: Value[Point] | Value[Rectangle]) -> NumericValue[int]:
        """
        The column of a ``Point`` or the left edge of a ``Rectangle``.

        Examples:
            ```python
            from xnano_core._xnano_core import Position

            assert Buffer(width=4, height=1, x=3, y=2).inspect(Position.x) == 3
            ```
        """

    @property
    def y(self: Value[Point] | Value[Rectangle]) -> NumericValue[int]:
        """
        The row of a ``Point`` or the top edge of a ``Rectangle``.

        Examples:
            ```python
            from xnano_core._xnano_core import Position

            assert Buffer(width=4, height=1, x=3, y=2).inspect(Position.y) == 2
            ```
        """

    @property
    def width(self: Value[Size] | Value[Rectangle]) -> NumericValue[int]:
        """
        The width of a ``Size`` or a ``Rectangle``.

        Examples:
            ```python
            from xnano_core._xnano_core import BufferSize

            assert Buffer(width=6, height=2).inspect(BufferSize.width) == 6
            ```
        """

    @property
    def height(self: Value[Size] | Value[Rectangle]) -> NumericValue[int]:
        """
        The height of a ``Size`` or a ``Rectangle``.

        Examples:
            ```python
            from xnano_core._xnano_core import BufferSize

            assert Buffer(width=6, height=2).inspect(BufferSize.height) == 2
            ```
        """

    @property
    def right(self: Value[Rectangle]) -> NumericValue[int]:
        """
        The first column after a ``Rectangle``.

        Examples:
            ```python
            from xnano_core._xnano_core import Bounds

            assert Buffer(width=6, height=2, x=1).inspect(Bounds.right) == 7
            ```
        """

    @property
    def bottom(self: Value[Rectangle]) -> NumericValue[int]:
        """
        The first row after a ``Rectangle``.

        Examples:
            ```python
            from xnano_core._xnano_core import Bounds

            assert Buffer(width=6, height=2, y=1).inspect(Bounds.bottom) == 3
            ```
        """

class NumericValue(Value[NumberType]):
    """
    A numeric expression that supports comparisons and arithmetic.

    Arithmetic and comparisons build new expressions instead of computing right away.

    Examples:
        ```python
        from xnano_core._xnano_core import _reference

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
            from xnano_core._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            assert Buffer(width=3, height=1).inspect(width < 4)
            ```
        """

    def __le__(self, other: float | NumericValue[int] | NumericValue[float]) -> Predicate:
        """
        A predicate that is true when the value is at most ``other``.

        Examples:
            ```python
            from xnano_core._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            assert Buffer(width=4, height=1).inspect(width <= 4)
            ```
        """

    def __gt__(self, other: float | NumericValue[int] | NumericValue[float]) -> Predicate:
        """
        A predicate that is true when the value is greater than ``other``.

        Examples:
            ```python
            from xnano_core._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            assert Buffer(width=5, height=1).inspect(width > 4)
            ```
        """

    def __ge__(self, other: float | NumericValue[int] | NumericValue[float]) -> Predicate:
        """
        A predicate that is true when the value is at least ``other``.

        Examples:
            ```python
            from xnano_core._xnano_core import _reference

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
            from xnano_core._xnano_core import _reference

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
            from xnano_core._xnano_core import _reference

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
            from xnano_core._xnano_core import _reference

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
            from xnano_core._xnano_core import _reference

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
            from xnano_core._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            assert Buffer(width=8, height=1).inspect(width % 3) == 2
            ```
        """

    def __neg__(self) -> NumericValue[NumberType]:
        """
        The value with its sign flipped.

        Examples:
            ```python
            from xnano_core._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            assert Buffer(width=8, height=1).inspect(-width) == -8
            ```
        """

    def __rtruediv__(self, other: float) -> NumericValue[float]:
        """
        ``other`` divided by the value.

        Examples:
            ```python
            from xnano_core._xnano_core import Width

            assert Buffer(width=8, height=1).inspect(16 / Width) == 2.0
            ```
        """

    def __rmod__(self, other: float) -> NumericValue[float]:
        """
        The remainder of dividing ``other`` by the value.

        Examples:
            ```python
            from xnano_core._xnano_core import Width

            assert Buffer(width=3, height=1).inspect(10 % Width) == 1
            ```
        """

    def __floordiv__(
        self, other: float | NumericValue[int] | NumericValue[float]
    ) -> NumericValue[int | float]:
        """
        The value divided by ``other``, rounded toward negative infinity like Python's ``//``.

        Dividing by zero raises ``ZeroDivisionError`` when the expression is evaluated.

        Examples:
            ```python
            from xnano_core._xnano_core import Width

            assert Buffer(width=7, height=1).inspect(Width // 2) == 3
            assert Buffer(width=7, height=1).inspect(-Width // 2) == -4
            ```
        """

    def __rfloordiv__(self, other: float) -> NumericValue[int | float]:
        """
        ``other`` divided by the value, rounded toward negative infinity.

        Examples:
            ```python
            from xnano_core._xnano_core import Width

            assert Buffer(width=4, height=1).inspect(9 // Width) == 2
            ```
        """

    def __pow__(
        self, other: float | NumericValue[int] | NumericValue[float], modulo: None = None
    ) -> NumericValue[int | float]:
        """
        The value raised to the power ``other``.

        Whole-number results stay integers; a negative or fractional exponent gives a float.

        Examples:
            ```python
            from xnano_core._xnano_core import Width

            assert Buffer(width=3, height=1).inspect(Width**2) == 9
            assert Buffer(width=4, height=1).inspect(Width**0.5) == 2.0
            ```
        """

    def __rpow__(self, other: float, modulo: None = None) -> NumericValue[int | float]:
        """
        ``other`` raised to the power of the value.

        Examples:
            ```python
            from xnano_core._xnano_core import Width

            assert Buffer(width=3, height=1).inspect(2**Width) == 8
            ```
        """

    def __abs__(self) -> NumericValue[NumberType]:
        """
        The absolute value.

        Examples:
            ```python
            from xnano_core._xnano_core import X

            assert Buffer(width=1, height=1, x=-5).inspect(abs(X)) == 5
            ```
        """

    def __floor__(self) -> NumericValue[int]:
        """
        The value rounded down to a whole number, used by ``math.floor``.

        Examples:
            ```python
            import math

            from xnano_core._xnano_core import Width

            assert Buffer(width=7, height=1).inspect(math.floor(Width / 2)) == 3
            ```
        """

    def __ceil__(self) -> NumericValue[int]:
        """
        The value rounded up to a whole number, used by ``math.ceil``.

        Examples:
            ```python
            import math

            from xnano_core._xnano_core import Width

            assert Buffer(width=7, height=1).inspect(math.ceil(Width / 2)) == 4
            ```
        """

    def __round__(self, digits: None = None) -> NumericValue[int]:
        """
        The value rounded to the nearest whole number, halves away from zero.

        Unlike Python's ``round``, a half rounds away from zero, so ``2.5`` becomes ``3``.
        Passing a number of digits raises ``TypeError``.

        Examples:
            ```python
            from xnano_core._xnano_core import Width

            assert Buffer(width=5, height=1).inspect(round(Width / 2)) == 3
            ```
        """

    def minimum(
        self, other: float | NumericValue[int] | NumericValue[float]
    ) -> NumericValue[NumberType]:
        """
        The smaller of the value and ``other``.

        Examples:
            ```python
            from xnano_core._xnano_core import Width

            assert Buffer(width=20, height=1).inspect(Width.minimum(8)) == 8
            ```
        """

    def maximum(
        self, other: float | NumericValue[int] | NumericValue[float]
    ) -> NumericValue[NumberType]:
        """
        The larger of the value and ``other``.

        Examples:
            ```python
            from xnano_core._xnano_core import Width

            assert Buffer(width=2, height=1).inspect(Width.maximum(8)) == 8
            ```
        """

    def clamp(
        self,
        lowest: float | NumericValue[int] | NumericValue[float],
        highest: float | NumericValue[int] | NumericValue[float],
    ) -> NumericValue[NumberType]:
        """
        The value limited to the range from ``lowest`` to ``highest``.

        Raises ``TypeError`` when evaluated if ``lowest`` is greater than ``highest``.

        Examples:
            ```python
            from xnano_core._xnano_core import Width

            assert Buffer(width=50, height=1).inspect(Width.clamp(0, 10)) == 10
            assert Buffer(width=5, height=1).inspect(Width.clamp(8, 10)) == 8
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
            from xnano_core._xnano_core import _reference

            width = _reference('Width', 'numeric_property')
            buffer = Buffer(width=6, height=1)
            buffer.update(Write('wide').when(width > 4))
            assert buffer.text.startswith('wide')
            ```
        """

    def __or__(self, other: Operation) -> Operation:
        """
        Combine this operation with ``other`` so both run in sequence.

        Examples:
            ```python
            buffer = Buffer(width=6, height=1)
            buffer.update(Write('ab') | Write('c', x=2))
            assert buffer.text.startswith('abc')
            ```
        """

class Property(Value[ValueType]):
    """
    A reference to a concrete property of a buffer or runtime.

    Reading it gives the current value. Calling it creates an assignment operation.

    Attributes:
        name: The name of the referenced property.

    Examples:
        ```python
        from xnano_core._xnano_core import _reference

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
            from xnano_core._xnano_core import _reference

            size = _reference('Size', 'property')
            buffer = Buffer(width=4, height=1)
            buffer.update(size(Size(6, 2)))
            assert buffer.width == 6
            ```
        """

class NumericProperty(NumericValue[NumberType]):
    """
    A reference to a numeric property that can be read, computed with and assigned.

    Attributes:
        name: The name of the referenced property.

    Examples:
        ```python
        from xnano_core._xnano_core import _reference

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
            from xnano_core._xnano_core import _reference

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
        from xnano_core._xnano_core import _reference

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
    ) -> None:
        """
        Create a SetValue.

        Args:
            property: ``Property[ValueType] | NumericProperty[int] | NumericProperty[float]``.
            value: ``ValueType | Value[ValueType]``.
        """

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

    def __init__(self, *operations: Operation) -> None:
        """
        Create a SequenceOperation.
        """

class Conditional(Operation):
    """
    Apply one operation when a condition is true and optionally another when it is not.

    Args:
        condition: The predicate to test each time the operation applies.
        operation: Applied when the condition is true.
        otherwise: Applied when the condition is false.

    Examples:
        ```python
        from xnano_core._xnano_core import _reference

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
    ) -> None:
        """
        Create a Conditional.

        Args:
            condition: ``Predicate``.
            operation: ``Operation``.
            otherwise: ``Operation | None``. Defaults to ``None``.
        """

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

    def __init__(self, width: int, height: int) -> None:
        """
        Create a Resize.

        Args:
            width: ``int``.
            height: ``int``.
        """

class Move(Operation):
    """
    Move the target buffer relative to its current position in its parent.

    Args:
        x: Columns to move right; negative values move left.
        y: Rows to move down; negative values move up.

    Examples:
        ```python
        buffer = Buffer(width=4, height=1, x=2, y=1)
        buffer.update(Move(1, 1))
        assert (buffer.x, buffer.y) == (3, 2)
        buffer.update(Move(x=-2, y=-1))
        assert (buffer.x, buffer.y) == (1, 1)
        ```
    """

    def __init__(self, x: int = 0, y: int = 0) -> None:
        """
        Create a Move.

        Args:
            x: ``int``. Defaults to ``0``.
            y: ``int``. Defaults to ``0``.
        """

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

    def __init__(self, x: int, y: int) -> None:
        """
        Create a Place.

        Args:
            x: ``int``.
            y: ``int``.
        """

class Write(Operation):
    """
    Write text into the target at a cell position.

    Text is clipped by display columns, whole graphemes are preserved and wide
    characters repair their continuation cells.

    Args:
        text: A string, a [`StyledText`][xnano_core._xnano_core.StyledText] or a sequence of both.
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
    ) -> None:
        """
        Create a Write.

        Args:
            text: ``TextContent``.
            x: ``int``. Defaults to ``0``.
            y: ``int``. Defaults to ``0``.
            style: ``Style | None``. Defaults to ``None``.
            mode: ``WriteMode``. Defaults to ``'replace'``.
        """

class WriteCellText(Write):
    """
    Write text addressed by ``column`` and ``row`` instead of ``x`` and ``y``.

    It behaves exactly like [`Write`][xnano_core._xnano_core.Write]; use it when the position
    is a cell index rather than a coordinate.

    Args:
        text: A string, a [`StyledText`][xnano_core._xnano_core.StyledText] or a sequence of both.
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
    ) -> None:
        """
        Create a WriteCellText.

        Args:
            text: ``TextContent``.
            column: ``int``. Defaults to ``0``.
            row: ``int``. Defaults to ``0``.
            style: ``Style | None``. Defaults to ``None``.
            mode: ``WriteMode``. Defaults to ``'replace'``.
        """

class Fill(Operation):
    """
    Fill every cell of the target with one cell.

    Args:
        cell: A [`Cell`][xnano_core._xnano_core.Cell] or a one-grapheme string.

    Examples:
        ```python
        buffer = Buffer(width=3, height=2)
        buffer.update(Fill('#'))
        assert buffer.text == '###\\n###'
        ```
    """

    def __init__(self, cell: Cell | str = ' ') -> None:
        """
        Create a Fill.

        Args:
            cell: ``Cell | str``. Defaults to ``' '``.
        """

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

    Attributes:
        symbol: The symbol used to erase each cell; a space leaves the area blank.
        style: The colors and text modifiers applied to the cleared cells.

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
    ) -> None:
        """
        Create a Clear.

        Args:
            symbol: ``str | Expression[str] | None``. Defaults to ``None``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            width: ``int | None``. Defaults to ``None``.
            height: ``int | None``. Defaults to ``None``.
            x: ``int``. Defaults to ``0``.
            y: ``int``. Defaults to ``0``.
        """
    @property
    def symbol(self) -> str | Expression[str]:
        """The symbol used to erase each cell; a space leaves the area blank."""
    @symbol.setter
    def symbol(self, value: str | Expression[str]) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle:
        """The colors and text modifiers applied to the cleared cells."""
    @style.setter
    def style(self, value: Style | DynamicStyle | None) -> None: ...
    def copy(self) -> Clear: ...
    def __copy__(self) -> Clear: ...
    def __deepcopy__(self, memo: object) -> Clear: ...

class Foreground(Operation):
    """
    Set the foreground color of every cell of the target.

    Args:
        color: A [`Color`][xnano_core._xnano_core.Color], a color name, a hex string or an
            ``(red, green, blue)`` tuple.

    Examples:
        ```python
        buffer = Buffer(width=3, height=1)
        buffer.update(Write('abc'), Foreground('red'))
        assert str(buffer[0, 0].foreground) == "Color('red')"
        ```
    """

    def __init__(self, color: ColorValue) -> None:
        """
        Create a Foreground.

        Args:
            color: ``ColorValue``.
        """

class Background(Operation):
    """
    Set the background color of every cell of the target.

    Args:
        color: A [`Color`][xnano_core._xnano_core.Color], a color name, a hex string or an
            ``(red, green, blue)`` tuple.

    Examples:
        ```python
        buffer = Buffer(width=3, height=1)
        buffer.update(Background((0, 0, 255)))
        assert buffer[0, 0].background.to_rgb() == (0, 0, 255)
        ```
    """

    def __init__(self, color: ColorValue) -> None:
        """
        Create a Background.

        Args:
            color: ``ColorValue``.
        """

class ApplyStyle(Operation):
    """
    Patch a [`Style`][xnano_core._xnano_core.Style] onto every cell of the target.

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

    def __init__(self, style: Style) -> None:
        """
        Create a ApplyStyle.

        Args:
            style: ``Style``.
        """

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
    ) -> None:
        """
        Create a Border.

        Args:
            kind: ``BorderKind``. Defaults to ``'plain'``.
            style: ``Style | None``. Defaults to ``None``.
        """

class Paste(Operation):
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
        target.update(Fill('.'), Paste(source, x=1))
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
    ) -> None:
        """
        Create a Paste.

        Args:
            source: ``Buffer | Region``.
            x: ``int``. Defaults to ``0``.
            y: ``int``. Defaults to ``0``.
            mode: ``WriteMode``. Defaults to ``'replace'``.
        """

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
        pixels: Iterable[PixelEntry],
        *,
        encoding: PixelEncoding = 'half_blocks',
        clip: bool = True,
        x: int | None = None,
        y: int | None = None,
    ) -> None:
        """
        Create a Pixels.

        Args:
            pixels: ``Iterable[PixelEntry]``.
            encoding: ``PixelEncoding``. Defaults to ``'half_blocks'``.
            clip: ``bool``. Defaults to ``True``.
            x: ``int | None``. Defaults to ``None``.
            y: ``int | None``. Defaults to ``None``.
        """

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
    ) -> None:
        """
        Create a Raster.

        Args:
            rgba: ``bytes``.
            width: ``int``.
            height: ``int``.
            x: ``int``. Defaults to ``0``.
            y: ``int``. Defaults to ``0``.
            encoding: ``PixelEncoding``. Defaults to ``'half_blocks'``.
            mode: ``RasterMode``. Defaults to ``'over'``.
        """

class SetState(Operation):
    """
    Assign a state branch and publish one validated commit.

    Args:
        reference: A state reference exposing ``path``, ``native_store`` and
            ``schema`` (see [`StateReference`][xnano_core._xnano_core.StateReference]).
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
    ) -> None:
        """
        Create a SetState.

        Args:
            reference: ``StateReference[StateType]``.
            value: ``StateType``.
            expected_revision: ``int | None``. Defaults to ``None``.
        """

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
    ) -> None:
        """
        Create a ApplyStatePatch.

        Args:
            reference: ``StateReference[StateType]``.
            patch: ``TerminalStatePatch``.
            expected_revision: ``int | None``. Defaults to ``None``.
        """

class Effect(Operation):
    """
    A composable animation with editable and bindable settings.

    Attributes:
        foreground: The text color, or ``None`` to leave the foreground unchanged.
        duration_milliseconds: The timer length in milliseconds, or ``None`` for an effect without its own timer.
        kind: The constructor name describing what this effect does.
        interpolation: The easing curve of this effect, or ``None`` when it has no timer of its own.
        key: The optional name under which a running effect can be replaced or cancelled.
        background: The background color, or ``None`` to leave the background unchanged.
        children: The effects combined or wrapped by this effect, in execution order.

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
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
        key: str | Expression[str] | None = None,
    ) -> None:
        """
        Create a Effect.

        Args:
            duration_milliseconds: ``int | Expression[int | float] | None``. Defaults to ``None``.
            interpolation: ``str | Expression[str] | None``. Defaults to ``None``.
            key: ``str | Expression[str] | None``. Defaults to ``None``.
        """
    def __repr__(self, /) -> str: ...
    def __eq__(self, value: object, /) -> bool: ...
    def repeat(
        self, /, *, times: int | Expression[int | float] | None = None
    ) -> Effect: ...
    @staticmethod
    def fade_to(
        foreground: ColorValue | Expression[ColorValue] | None = None,
        background: ColorValue | Expression[ColorValue] | None = None,
        *,
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def fade_from(
        foreground: ColorValue | Expression[ColorValue] | None = None,
        background: ColorValue | Expression[ColorValue] | None = None,
        *,
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def paint(
        foreground: ColorValue | Expression[ColorValue] | None = None,
        background: ColorValue | Expression[ColorValue] | None = None,
        *,
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def saturate(
        foreground: float | Expression[int | float] | None = None,
        background: float | Expression[int | float] | None = None,
        *,
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def lighten(
        foreground: float | Expression[int | float] | None = None,
        background: float | Expression[int | float] | None = None,
        *,
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def darken(
        foreground: float | Expression[int | float] | None = None,
        background: float | Expression[int | float] | None = None,
        *,
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def sweep_in(
        direction: str | Expression[str] | None = None,
        *,
        gradient_length: int | Expression[int | float] | None = None,
        randomness: int | Expression[int | float] | None = None,
        color: ColorValue | Expression[ColorValue] | None = None,
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def sweep_out(
        direction: str | Expression[str] | None = None,
        *,
        gradient_length: int | Expression[int | float] | None = None,
        randomness: int | Expression[int | float] | None = None,
        color: ColorValue | Expression[ColorValue] | None = None,
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def slide_in(
        direction: str | Expression[str] | None = None,
        *,
        gradient_length: int | Expression[int | float] | None = None,
        randomness: int | Expression[int | float] | None = None,
        color: ColorValue | Expression[ColorValue] | None = None,
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def slide_out(
        direction: str | Expression[str] | None = None,
        *,
        gradient_length: int | Expression[int | float] | None = None,
        randomness: int | Expression[int | float] | None = None,
        color: ColorValue | Expression[ColorValue] | None = None,
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def hsl_shift(
        foreground: tuple[
            float | Expression[int | float],
            float | Expression[int | float],
            float | Expression[int | float],
        ]
        | None = None,
        background: tuple[
            float | Expression[int | float],
            float | Expression[int | float],
            float | Expression[int | float],
        ]
        | None = None,
        *,
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def dissolve(
        *,
        style: Style | DynamicStyle | None = None,
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def coalesce(
        *,
        style: Style | DynamicStyle | None = None,
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def glitch(
        *,
        ratio: float | Expression[int | float] | None = None,
        duration_milliseconds: int | Expression[int | float] | None = None,
        start_delay_milliseconds: tuple[int, int] = ...,
        action_milliseconds: tuple[int, int] = ...,
    ) -> Effect: ...
    @staticmethod
    def sleep(
        duration_milliseconds: int | Expression[int | float],
        *,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect: ...
    @staticmethod
    def evolve(
        symbols: EvolveSymbolSet | Expression[str] | None = None,
        *,
        style: Style | DynamicStyle | None = None,
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect:
        """
        Step every cell through a set of symbols, from empty to full.

        Maps to [`tachyonfx::fx::evolve`](https://docs.rs/tachyonfx/0.25.2/tachyonfx/fx/fn.evolve.html).

        Args:
            symbols: The symbol set; ``'circles'`` by default.
            style: A style applied to the symbols.
            duration_milliseconds: How long the effect lasts.
            interpolation: The easing curve.

        Examples:
            ```python
            effect = Effect.evolve('shaded', duration_milliseconds=200)
            assert effect.kind == 'evolve'
            ```
        """
    @staticmethod
    def evolve_into(
        symbols: EvolveSymbolSet | Expression[str] | None = None,
        *,
        style: Style | DynamicStyle | None = None,
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect:
        """
        Step cells through a set of symbols until the content underneath shows.

        Maps to [`tachyonfx::fx::evolve_into`](https://docs.rs/tachyonfx/0.25.2/tachyonfx/fx/fn.evolve_into.html).
        Takes the same arguments as [`evolve`][xnano_core._xnano_core.Effect.evolve].
        """
    @staticmethod
    def evolve_from(
        symbols: EvolveSymbolSet | Expression[str] | None = None,
        *,
        style: Style | DynamicStyle | None = None,
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect:
        """
        Step cells through a set of symbols, starting from the content underneath.

        Maps to [`tachyonfx::fx::evolve_from`](https://docs.rs/tachyonfx/0.25.2/tachyonfx/fx/fn.evolve_from.html).
        Takes the same arguments as [`evolve`][xnano_core._xnano_core.Effect.evolve].
        """
    @staticmethod
    def expand(
        direction: Literal['horizontal', 'vertical'] | Expression[str] | None = None,
        *,
        style: Style | DynamicStyle | None = None,
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect:
        """
        Grow a style outward from the center, horizontally or vertically.

        Maps to [`tachyonfx::fx::expand`](https://docs.rs/tachyonfx/0.25.2/tachyonfx/fx/fn.expand.html).

        Examples:
            ```python
            effect = Effect.expand('vertical', duration_milliseconds=200)
            assert effect.kind == 'expand'
            ```
        """
    @staticmethod
    def stretch(
        direction: Literal['left_to_right', 'right_to_left', 'up_to_down', 'down_to_up']
        | Expression[str]
        | None = None,
        *,
        style: Style | DynamicStyle | None = None,
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect:
        """
        Stretch a style across the area in a direction.

        Maps to [`tachyonfx::fx::stretch`](https://docs.rs/tachyonfx/0.25.2/tachyonfx/fx/fn.stretch.html).

        Examples:
            ```python
            effect = Effect.stretch('up_to_down', duration_milliseconds=200)
            assert effect.kind == 'stretch'
            ```
        """
    @staticmethod
    def explode(
        *,
        force: float | Expression[int | float] | None = None,
        randomness: float | Expression[int | float] | None = None,
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect:
        """
        Blow the cells outward and away.

        Maps to [`tachyonfx::fx::explode`](https://docs.rs/tachyonfx/0.25.2/tachyonfx/fx/fn.explode.html).

        Args:
            force: How hard the cells are thrown; 10 by default.
            randomness: How much the force varies from cell to cell; 3 by default.
            duration_milliseconds: How long the effect lasts; 800 by default.
            interpolation: The easing curve.

        Examples:
            ```python
            effect = Effect.explode(force=5.0)
            assert effect.kind == 'explode'
            ```
        """
    def translated(
        self,
        /,
        *,
        x: int | Expression[int | float] | None = None,
        y: int | Expression[int | float] | None = None,
        duration_milliseconds: int | Expression[int | float] | None = None,
        interpolation: str | Expression[str] | None = None,
    ) -> Effect:
        """
        Move everything this effect draws by an offset over time.

        Maps to [`tachyonfx::fx::translate`](https://docs.rs/tachyonfx/0.25.2/tachyonfx/fx/fn.translate.html).

        Args:
            x: Columns to move by.
            y: Rows to move by.
            duration_milliseconds: How long the move lasts; 500 by default.
            interpolation: The easing curve.

        Examples:
            ```python
            effect = Effect.dissolve().translated(y=-2)
            assert effect.kind == 'translate'
            ```
        """
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
        times: int | Expression[int | float] | None = None,
        *,
        milliseconds: int | Expression[int | float] | None = None,
    ) -> Effect: ...
    def ping_pong(self, /) -> Effect: ...
    def delayed(self, /, milliseconds: int | Expression[int | float]) -> Effect: ...
    def prolong_start(self, /, milliseconds: int | Expression[int | float]) -> Effect: ...
    def prolong_end(self, /, milliseconds: int | Expression[int | float]) -> Effect: ...
    def freeze_at(
        self,
        /,
        alpha: float | Expression[int | float],
        *,
        should_set_raw_alpha: bool | Expression[bool] = False,
    ) -> Effect: ...
    def remap_alpha(
        self,
        /,
        start: float | Expression[int | float],
        end: float | Expression[int | float],
    ) -> Effect: ...
    def with_duration(self, /, milliseconds: int | Expression[int | float]) -> Effect: ...
    def timed_never_complete(
        self, /, milliseconds: int | Expression[int | float]
    ) -> Effect: ...
    def run_once(self, /) -> Effect: ...
    def never_complete(self, /) -> Effect: ...
    def with_filter(self, /, filter: CellFilter) -> Effect: ...
    def with_area(self, /, area: Rectangle | Expression[Rectangle]) -> Effect:
        """
        Limit the effect to a rectangle relative to its target.

        An expression is evaluated each frame. Moving or resizing its rectangle
        preserves the effect's elapsed time.

        Maps to [`tachyonfx::fx::dynamic_area`](https://docs.rs/tachyonfx/0.25.2/tachyonfx/fx/fn.dynamic_area.html).

        Args:
            area: Fixed rectangle or expression giving the affected cells.

        Returns:
            A copy of the effect restricted to ``area``.

        Examples:
            >>> effect = Effect.dissolve().with_area(Rectangle(0, 0, 3, 1))
            >>> effect.kind
            'dissolve'
        """
    def reversed(
        self, /, is_reversed: bool | Expression[bool] | None = None
    ) -> Effect: ...
    def with_interpolation(self, /, interpolation: str | Expression[str]) -> Effect: ...
    def with_seed(self, /, seed: int | Expression[int | float]) -> Effect: ...
    def with_color_space(self, /, color_space: str | Expression[str]) -> Effect: ...
    def with_key(self, /, key: str | Expression[str]) -> Effect: ...
    def copy(self, /) -> Effect: ...
    def __copy__(self, /) -> Effect: ...
    def __deepcopy__(self, /, _memo: dict[int, object]) -> Effect: ...
    @property
    def foreground(self) -> ColorValue | Expression[ColorValue] | None:
        """The text color, or ``None`` to leave the foreground unchanged."""
    @foreground.setter
    def foreground(self, value: ColorValue | Expression[ColorValue] | None) -> None: ...
    @property
    def duration_milliseconds(self) -> int | Expression[int | float]:
        """The timer length in milliseconds, or ``None`` for an effect without its own timer."""
    @duration_milliseconds.setter
    def duration_milliseconds(self, value: int | Expression[int | float]) -> None: ...
    @property
    def kind(self) -> str | Expression[str]:
        """The constructor name describing what this effect does."""
    @property
    def interpolation(self) -> str | Expression[str]:
        """The easing curve of this effect, or ``None`` when it has no timer of its own."""
    @interpolation.setter
    def interpolation(self, value: str | Expression[str]) -> None: ...
    @property
    def key(self) -> str | Expression[str] | None:
        """The optional name under which a running effect can be replaced or cancelled."""
    @key.setter
    def key(self, value: str | Expression[str] | None) -> None: ...
    @property
    def background(self) -> ColorValue | Expression[ColorValue] | None:
        """The background color, or ``None`` to leave the background unchanged."""
    @background.setter
    def background(self, value: ColorValue | Expression[ColorValue] | None) -> None: ...
    @property
    def children(self) -> Sequence[Effect]:
        """The effects combined or wrapped by this effect, in execution order."""

class Fade(Effect):
    """
    Fade the colors of the target toward a foreground and background color.

    Maps to [`tachyonfx::fx::fade_to`](https://docs.rs/tachyonfx/0.25.0/tachyonfx/fx/fn.fade_to.html).

    Args:
        foreground: The color the foreground fades to, or ``None`` to leave it.
        background: The color the background fades to, or ``None`` to leave it.
        duration_milliseconds: How long the fade plays.
        interpolation: How progress eases over the duration.
        key: A name that [`CancelEffect`][xnano_core._xnano_core.CancelEffect] can target.

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
    ) -> None:
        """
        Create a Fade.

        Args:
            foreground: ``ColorValue | None``. Defaults to ``None``.
            background: ``ColorValue | None``. Defaults to ``None``.
            duration_milliseconds: ``int``. Defaults to ``500``.
            interpolation: ``Interpolation``. Defaults to ``'linear'``.
            key: ``str | None``. Defaults to ``None``.
        """

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
        key: A name that [`CancelEffect`][xnano_core._xnano_core.CancelEffect] can target.

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
    ) -> None:
        """
        Create a Dissolve.

        Args:
            duration_milliseconds: ``int``. Defaults to ``500``.
            should_reverse: ``bool``. Defaults to ``False``.
            seed: ``int | None``. Defaults to ``None``.
            key: ``str | None``. Defaults to ``None``.
        """

class Glitch(Effect):
    """
    Randomly corrupt and displace glyphs of the target.

    Maps to [`tachyonfx::fx::Glitch`](https://docs.rs/tachyonfx/0.25.0/tachyonfx/fx/struct.Glitch.html).

    Args:
        intensity: Fraction of cells affected, from ``0.0`` to ``1.0``.
        duration_milliseconds: How long the effect plays.
        seed: Seed for a repeatable result; ``None`` is random.
        key: A name that [`CancelEffect`][xnano_core._xnano_core.CancelEffect] can target.

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
    ) -> None:
        """
        Create a Glitch.

        Args:
            intensity: ``float``. Defaults to ``0.1``.
            duration_milliseconds: ``int``. Defaults to ``500``.
            seed: ``int | None``. Defaults to ``None``.
            key: ``str | None``. Defaults to ``None``.
        """

class Fuzz(Operation):
    """
    Replace a percentage of the visible glyphs of the target with noise glyphs, once.

    Unlike an [`Effect`][xnano_core._xnano_core.Effect] it changes the cells immediately and
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

    def __init__(self, intensity: int, *, seed: int | None = None) -> None:
        """
        Create a Fuzz.

        Args:
            intensity: ``int``.
            seed: ``int | None``. Defaults to ``None``.
        """

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

    def __init__(self, key: str) -> None:
        """
        Create a CancelEffect.

        Args:
            key: ``str``.
        """

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
        sizes: One [`SizeRule`][xnano_core._xnano_core.SizeRule] per child along the main axis.
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
    ) -> None:
        """
        Create a Layout.

        Args:
            arrangement: ``Literal['row', 'column', 'overlay']``. Defaults to ``'column'``.
            sizes: ``Sequence[SizeRule]``. Defaults to ``()``.
            spacing: ``int``. Defaults to ``0``.
            padding: ``int``. Defaults to ``0``.
        """
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

    Attributes:
        scroll_padding: The number of items kept visible above and below the selection while scrolling.
        highlight_style: The colors and text modifiers applied to the selected item.
        selected: The zero-based selected item index, or ``None`` when nothing is selected.
        style: The default colors and text modifiers applied to the cells.
        repeat_highlight_symbol: Whether the highlight symbol appears on every line of a selected multiline item.
        highlight_spacing: When space is reserved for the highlight symbol: ``always``, ``when_selected`` or ``never``.
        offset: The zero-based index of the first item shown when scrolling.
        highlight_symbol: The text displayed beside the selected item.
        visible_range: The first visible index and the exclusive end index from the most recent render, or ``None`` before rendering.
        direction: The order in which items fill the area: ``top_to_bottom`` or ``bottom_to_top``.
        items: The styled items displayed in their list order.
        block: The optional border, titles and padding around the content.

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
        selected: int | Expression[int | float] | None = None,
        offset: int | Expression[int | float] | None = None,
        style: Style | DynamicStyle | None = None,
        highlight_style: Style | DynamicStyle | None = None,
        highlight_symbol: str | Expression[str] | None = None,
        repeat_highlight_symbol: bool | Expression[bool] | None = None,
        highlight_spacing: str | Expression[str] | None = None,
        direction: str | Expression[str] | None = None,
        scroll_padding: int | Expression[int | float] | None = None,
        block: Block | None = None,
        width: int | Expression[int | float] | None = None,
        height: int | Expression[int | float] | None = None,
        x: int | Expression[int | float] = 0,
        y: int | Expression[int | float] = 0,
    ) -> None:
        """
        Create a ItemList.

        Args:
            items: ``Sequence[ListItem | TextContent] | None``. Defaults to ``None``.
            selected: ``int | Expression[int | float] | None``. Defaults to ``None``.
            offset: ``int | Expression[int | float] | None``. Defaults to ``None``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            highlight_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            highlight_symbol: ``str | Expression[str] | None``. Defaults to ``None``.
            repeat_highlight_symbol: ``bool | Expression[bool] | None``. Defaults to ``None``.
            highlight_spacing: ``str | Expression[str] | None``. Defaults to ``None``.
            direction: ``str | Expression[str] | None``. Defaults to ``None``.
            scroll_padding: ``int | Expression[int | float] | None``. Defaults to ``None``.
            block: ``Block | None``. Defaults to ``None``.
            width: ``int | Expression[int | float] | None``. Defaults to ``None``.
            height: ``int | Expression[int | float] | None``. Defaults to ``None``.
            x: ``int | Expression[int | float]``. Defaults to ``0``.
            y: ``int | Expression[int | float]``. Defaults to ``0``.
        """
    def __repr__(self, /) -> str: ...
    def append(self, /, item: ListItem | TextContent) -> None: ...
    def extend(self, /, items: Sequence[ListItem | TextContent]) -> None: ...
    def insert(
        self, /, index: int | Expression[int | float], item: ListItem | TextContent
    ) -> None: ...
    def set_item(
        self, /, index: int | Expression[int | float], item: ListItem | TextContent
    ) -> None: ...
    def pop(self, /, index: int | Expression[int | float] | None = None) -> ListItem: ...
    def clear(self, /) -> None: ...
    def select_next(self, /) -> None: ...
    def select_previous(self, /) -> None: ...
    def select_first(self, /) -> None: ...
    def select_last(self, /) -> None: ...
    def scroll_down_by(self, /, amount: int | Expression[int | float]) -> None: ...
    def scroll_up_by(self, /, amount: int | Expression[int | float]) -> None: ...
    def copy(self, /) -> ItemList: ...
    def __copy__(self, /) -> ItemList: ...
    def __deepcopy__(self, /, _memo: dict[int, object]) -> ItemList: ...
    @property
    def scroll_padding(self) -> int | Expression[int | float]:
        """The number of items kept visible above and below the selection while scrolling."""
    @scroll_padding.setter
    def scroll_padding(self, value: int | Expression[int | float]) -> None: ...
    @property
    def highlight_style(self) -> Style | DynamicStyle:
        """The colors and text modifiers applied to the selected item."""
    @highlight_style.setter
    def highlight_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def selected(self) -> int | Expression[int | float] | None:
        """The zero-based selected item index, or ``None`` when nothing is selected."""
    @selected.setter
    def selected(self, value: int | Expression[int | float] | None) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the cells."""
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def repeat_highlight_symbol(self) -> bool | Expression[bool]:
        """Whether the highlight symbol appears on every line of a selected multiline item."""
    @repeat_highlight_symbol.setter
    def repeat_highlight_symbol(self, value: bool | Expression[bool]) -> None: ...
    @property
    def highlight_spacing(self) -> str | Expression[str]:
        """When space is reserved for the highlight symbol: ``always``, ``when_selected`` or ``never``."""
    @highlight_spacing.setter
    def highlight_spacing(self, value: str | Expression[str]) -> None: ...
    @property
    def offset(self) -> int | Expression[int | float]:
        """The zero-based index of the first item shown when scrolling."""
    @offset.setter
    def offset(self, value: int | Expression[int | float]) -> None: ...
    @property
    def highlight_symbol(self) -> str | Expression[str]:
        """The text displayed beside the selected item."""
    @highlight_symbol.setter
    def highlight_symbol(self, value: str | Expression[str]) -> None: ...
    @property
    def visible_range(self) -> tuple[int, int]:
        """The first visible index and the exclusive end index from the most recent render, or ``None`` before rendering."""
    @property
    def direction(self) -> str | Expression[str]:
        """The order in which items fill the area: ``top_to_bottom`` or ``bottom_to_top``."""
    @direction.setter
    def direction(self, value: str | Expression[str]) -> None: ...
    @property
    def items(self) -> Sequence[ListItem | TextContent]:
        """The styled items displayed in their list order."""
    @items.setter
    def items(self, value: Sequence[ListItem | TextContent]) -> None: ...
    @property
    def block(self) -> Block | None:
        """The optional border, titles and padding around the content."""
    @block.setter
    def block(self, value: Block | None) -> None: ...

class Gauge(Widget):
    """
    A filled progress bar that repaints when its ratio changes.

    Attributes:
        label: The text displayed as the label, or ``None`` to omit it.
        style: The default colors and text modifiers applied to the cells.
        use_unicode: Whether fractional cells are drawn with Unicode block symbols.
        ratio: The filled fraction, from ``0.0`` (empty) to ``1.0`` (full).
        block: The optional border, titles and padding around the content.
        gauge_style: The colors and text modifiers applied to the filled portion.

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
        ratio: float | Expression[int | float] | None = None,
        *,
        label: TextContent | Expression[str] | None = None,
        style: Style | DynamicStyle | None = None,
        gauge_style: Style | DynamicStyle | None = None,
        use_unicode: bool | Expression[bool] | None = None,
        block: Block | None = None,
        width: int | Expression[int | float] | None = None,
        height: int | Expression[int | float] | None = None,
        x: int | Expression[int | float] = 0,
        y: int | Expression[int | float] = 0,
    ) -> None:
        """
        Create a Gauge.

        Args:
            ratio: ``float | Expression[int | float] | None``. Defaults to ``None``.
            label: ``TextContent | Expression[str] | None``. Defaults to ``None``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            gauge_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            use_unicode: ``bool | Expression[bool] | None``. Defaults to ``None``.
            block: ``Block | None``. Defaults to ``None``.
            width: ``int | Expression[int | float] | None``. Defaults to ``None``.
            height: ``int | Expression[int | float] | None``. Defaults to ``None``.
            x: ``int | Expression[int | float]``. Defaults to ``0``.
            y: ``int | Expression[int | float]``. Defaults to ``0``.
        """
    def __repr__(self, /) -> str: ...
    @property
    def label(self) -> TextContent | Expression[str] | None:
        """The text displayed as the label, or ``None`` to omit it."""
    @label.setter
    def label(self, value: TextContent | Expression[str] | None) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the cells."""
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def use_unicode(self) -> bool | Expression[bool]:
        """Whether fractional cells are drawn with Unicode block symbols."""
    @use_unicode.setter
    def use_unicode(self, value: bool | Expression[bool]) -> None: ...
    @property
    def ratio(self) -> float | Expression[int | float]:
        """The filled fraction, from ``0.0`` (empty) to ``1.0`` (full)."""
    @ratio.setter
    def ratio(self, value: float | Expression[int | float]) -> None: ...
    @property
    def block(self) -> Block | None:
        """The optional border, titles and padding around the content."""
    @block.setter
    def block(self, value: Block | None) -> None: ...
    @property
    def gauge_style(self) -> Style | DynamicStyle:
        """The colors and text modifiers applied to the filled portion."""
    @gauge_style.setter
    def gauge_style(self, value: Style | DynamicStyle) -> None: ...

class LineGauge(Widget):
    """
    A progress indicator drawn with line symbols.

    Attributes:
        block: The optional border, titles and padding around the content.
        unfilled_style: The colors and text modifiers applied to the unfilled line.
        ratio: The filled fraction, from ``0.0`` (empty) to ``1.0`` (full).
        filled_symbol: The symbol drawn for each filled cell.
        filled_style: The colors and text modifiers applied to the filled line.
        style: The default colors and text modifiers applied to the cells.
        unfilled_symbol: The symbol drawn for each unfilled cell.
        label: The text displayed as the label, or ``None`` to omit it.
        line_set: The named line-symbol set used when explicit filled or unfilled symbols are omitted.

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
        ratio: float | Expression[int | float] | None = None,
        *,
        label: TextContent | Expression[str] | None = None,
        line_set: str | Expression[str] | None = None,
        filled_symbol: str | Expression[str] | None = None,
        unfilled_symbol: str | Expression[str] | None = None,
        style: Style | DynamicStyle | None = None,
        filled_style: Style | DynamicStyle | None = None,
        unfilled_style: Style | DynamicStyle | None = None,
        block: Block | None = None,
        width: int | Expression[int | float] | None = None,
        height: int | Expression[int | float] | None = None,
        x: int | Expression[int | float] = 0,
        y: int | Expression[int | float] = 0,
    ) -> None:
        """
        Create a LineGauge.

        Args:
            ratio: ``float | Expression[int | float] | None``. Defaults to ``None``.
            label: ``TextContent | Expression[str] | None``. Defaults to ``None``.
            line_set: ``str | Expression[str] | None``. Defaults to ``None``.
            filled_symbol: ``str | Expression[str] | None``. Defaults to ``None``.
            unfilled_symbol: ``str | Expression[str] | None``. Defaults to ``None``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            filled_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            unfilled_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            block: ``Block | None``. Defaults to ``None``.
            width: ``int | Expression[int | float] | None``. Defaults to ``None``.
            height: ``int | Expression[int | float] | None``. Defaults to ``None``.
            x: ``int | Expression[int | float]``. Defaults to ``0``.
            y: ``int | Expression[int | float]``. Defaults to ``0``.
        """
    def __repr__(self, /) -> str: ...
    def copy(self, /) -> LineGauge: ...
    def __copy__(self, /) -> LineGauge: ...
    def __deepcopy__(self, /, _memo: dict[int, object]) -> LineGauge: ...
    @property
    def block(self) -> Block | None:
        """The optional border, titles and padding around the content."""
    @block.setter
    def block(self, value: Block | None) -> None: ...
    @property
    def unfilled_style(self) -> Style | DynamicStyle:
        """The colors and text modifiers applied to the unfilled line."""
    @unfilled_style.setter
    def unfilled_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def ratio(self) -> float | Expression[int | float]:
        """The filled fraction, from ``0.0`` (empty) to ``1.0`` (full)."""
    @ratio.setter
    def ratio(self, value: float | Expression[int | float]) -> None: ...
    @property
    def filled_symbol(self) -> str | Expression[str]:
        """The symbol drawn for each filled cell."""
    @filled_symbol.setter
    def filled_symbol(self, value: str | Expression[str]) -> None: ...
    @property
    def filled_style(self) -> Style | DynamicStyle:
        """The colors and text modifiers applied to the filled line."""
    @filled_style.setter
    def filled_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the cells."""
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def unfilled_symbol(self) -> str | Expression[str]:
        """The symbol drawn for each unfilled cell."""
    @unfilled_symbol.setter
    def unfilled_symbol(self, value: str | Expression[str]) -> None: ...
    @property
    def label(self) -> TextContent | Expression[str] | None:
        """The text displayed as the label, or ``None`` to omit it."""
    @label.setter
    def label(self, value: TextContent | Expression[str] | None) -> None: ...
    @property
    def line_set(self) -> str | Expression[str]:
        """The named line-symbol set used when explicit filled or unfilled symbols are omitted."""
    @line_set.setter
    def line_set(self, value: str | Expression[str]) -> None: ...

class Sparkline(Widget):
    """
    A compact history of numeric samples.

    Attributes:
        values: The sequence of values to draw; ``None`` entries represent missing samples.
        bars: The styled samples used to draw the sparkline.
        maximum: The value represented by a full bar, or ``None`` to use the largest value.
        bar_set: The named set of symbols used to draw partial and full bars.
        direction: The drawing direction: ``left_to_right`` or ``right_to_left``.
        absent_value_style: The colors and text modifiers used for missing samples.
        style: The default colors and text modifiers applied to the cells.
        absent_value_symbol: The symbol drawn where a sample is missing.
        block: The optional border, titles and padding around the content.

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
        values: Sequence[int | Expression[int | float] | SparklineBar | None]
        | None = None,
        *,
        maximum: int | Expression[int | float] | None = None,
        style: Style | DynamicStyle | None = None,
        absent_value_style: Style | DynamicStyle | None = None,
        absent_value_symbol: str | Expression[str] | None = None,
        direction: str | Expression[str] | None = None,
        bar_set: str | Expression[str] | None = None,
        block: Block | None = None,
        width: int | Expression[int | float] | None = None,
        height: int | Expression[int | float] | None = None,
        x: int | Expression[int | float] = 0,
        y: int | Expression[int | float] = 0,
    ) -> None:
        """
        Create a Sparkline.

        Args:
            values: ``Sequence[int | Expression[int | float] | SparklineBar | None] | None``. Defaults
                to ``None``.
            maximum: ``int | Expression[int | float] | None``. Defaults to ``None``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            absent_value_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            absent_value_symbol: ``str | Expression[str] | None``. Defaults to ``None``.
            direction: ``str | Expression[str] | None``. Defaults to ``None``.
            bar_set: ``str | Expression[str] | None``. Defaults to ``None``.
            block: ``Block | None``. Defaults to ``None``.
            width: ``int | Expression[int | float] | None``. Defaults to ``None``.
            height: ``int | Expression[int | float] | None``. Defaults to ``None``.
            x: ``int | Expression[int | float]``. Defaults to ``0``.
            y: ``int | Expression[int | float]``. Defaults to ``0``.
        """
    def __repr__(self, /) -> str: ...
    def __len__(self, /) -> int: ...
    def append(
        self,
        /,
        value: int | Expression[int | float],
        *,
        maximum_length: int | Expression[int | float] | None = None,
    ) -> None: ...
    def extend(
        self,
        /,
        values: Sequence[int | Expression[int | float] | SparklineBar | None],
        *,
        maximum_length: int | Expression[int | float] | None = None,
    ) -> None: ...
    def clear(self, /) -> None: ...
    def copy(self, /) -> Sparkline: ...
    def __copy__(self, /) -> Sparkline: ...
    def __deepcopy__(self, /, _memo: dict[int, object]) -> Sparkline: ...
    @property
    def values(self) -> Sequence[int | Expression[int | float] | SparklineBar | None]:
        """The sequence of values to draw; ``None`` entries represent missing samples."""
    @values.setter
    def values(
        self, value: Sequence[int | Expression[int | float] | SparklineBar | None]
    ) -> None: ...
    @property
    def bars(self) -> Sequence[SparklineBar]:
        """The styled samples used to draw the sparkline."""
    @property
    def maximum(self) -> int | Expression[int | float] | None:
        """The value represented by a full bar, or ``None`` to use the largest value."""
    @maximum.setter
    def maximum(self, value: int | Expression[int | float] | None) -> None: ...
    @property
    def bar_set(self) -> str | Expression[str]:
        """The named set of symbols used to draw partial and full bars."""
    @bar_set.setter
    def bar_set(self, value: str | Expression[str]) -> None: ...
    @property
    def direction(self) -> str | Expression[str]:
        """The drawing direction: ``left_to_right`` or ``right_to_left``."""
    @direction.setter
    def direction(self, value: str | Expression[str]) -> None: ...
    @property
    def absent_value_style(self) -> Style | DynamicStyle:
        """The colors and text modifiers used for missing samples."""
    @absent_value_style.setter
    def absent_value_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the cells."""
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def absent_value_symbol(self) -> str | Expression[str]:
        """The symbol drawn where a sample is missing."""
    @absent_value_symbol.setter
    def absent_value_symbol(self, value: str | Expression[str]) -> None: ...
    @property
    def block(self) -> Block | None:
        """The optional border, titles and padding around the content."""
    @block.setter
    def block(self, value: Block | None) -> None: ...

class Bar:
    """
    One labelled value in a bar chart.

    Attributes:
        label: The text displayed as the label, or ``None`` to omit it.
        style: The default colors and text modifiers applied to the cells.
        value: The nonnegative numeric value represented by the bar.
        text_value: The text drawn for the value, or ``None`` to display the numeric value.
        value_style: The colors and text modifiers applied to the displayed value.

    Examples:
        ```python
        bar = Bar(3, 'A')
        assert bar.value == 3
        ```
    """

    def __init__(
        self,
        /,
        value: int | Expression[int | float],
        label: TextContent | Expression[str] | None = None,
        *,
        text_value: str | Expression[str] | None = None,
        style: Style | DynamicStyle | None = None,
        value_style: Style | DynamicStyle | None = None,
    ) -> None:
        """
        Create a Bar.

        Args:
            value: ``int | Expression[int | float]``.
            label: ``TextContent | Expression[str] | None``. Defaults to ``None``.
            text_value: ``str | Expression[str] | None``. Defaults to ``None``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            value_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
        """
    def __repr__(self, /) -> str: ...
    def __hash__(self, /) -> int: ...
    def __eq__(self, value: object, /) -> bool: ...
    def __copy__(self, /) -> Bar: ...
    def __deepcopy__(self, /, _memo: dict[int, object]) -> Bar: ...
    @property
    def label(self) -> TextContent | Expression[str] | None:
        """The text displayed as the label, or ``None`` to omit it."""
    @property
    def style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the cells."""
    @property
    def value(self) -> int | Expression[int | float]:
        """The nonnegative numeric value represented by the bar."""
    @property
    def text_value(self) -> str | Expression[str]:
        """The text drawn for the value, or ``None`` to display the numeric value."""
    @property
    def value_style(self) -> Style | DynamicStyle:
        """The colors and text modifiers applied to the displayed value."""

class BarGroup:
    """
    A labelled group of bars.

    Attributes:
        label: The text displayed as the label, or ``None`` to omit it.
        bars: The bars displayed in their sequence order.

    Examples:
        ```python
        group = BarGroup([Bar(3, 'A')], 'Group')
        assert len(group.bars) == 1
        ```
    """

    def __init__(
        self, /, bars: Sequence[Bar], label: TextContent | Expression[str] | None = None
    ) -> None:
        """
        Create a BarGroup.

        Args:
            bars: ``Sequence[Bar]``.
            label: ``TextContent | Expression[str] | None``. Defaults to ``None``.
        """
    def __repr__(self, /) -> str: ...
    def __hash__(self, /) -> int: ...
    def __eq__(self, value: object, /) -> bool: ...
    def __copy__(self, /) -> BarGroup: ...
    def __deepcopy__(self, /, _memo: dict[int, object]) -> BarGroup: ...
    @property
    def label(self) -> TextContent | Expression[str] | None:
        """The text displayed as the label, or ``None`` to omit it."""
    @property
    def bars(self) -> Sequence[Bar]:
        """The bars displayed in their sequence order."""

class BarChart(Widget):
    """
    Grouped bars with editable values and styles.

    Attributes:
        label_style: The colors and text modifiers applied to bar and group labels.
        group_gap: The number of empty cells between groups of bars.
        bar_gap: The number of empty cells between adjacent bars.
        block: The optional border, titles and padding around the content.
        style: The default colors and text modifiers applied to the cells.
        bar_width: The thickness of each bar, in cells.
        direction: The orientation of the bars: ``vertical`` or ``horizontal``.
        maximum: The value represented by a full bar, or ``None`` to use the largest value.
        groups: The groups of bars displayed in sequence order.
        bar_set: The named set of symbols used to draw partial and full bars.
        bar_style: The default colors and text modifiers applied to the bars.
        value_style: The colors and text modifiers applied to the displayed value.

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
        data: Sequence[Bar | BarGroup | int] | None = None,
        *,
        bar_width: int | Expression[int | float] | None = None,
        bar_gap: int | Expression[int | float] | None = None,
        group_gap: int | Expression[int | float] | None = None,
        maximum: int | Expression[int | float] | None = None,
        direction: str | Expression[str] | None = None,
        bar_style: Style | DynamicStyle | None = None,
        value_style: Style | DynamicStyle | None = None,
        label_style: Style | DynamicStyle | None = None,
        style: Style | DynamicStyle | None = None,
        bar_set: str | Expression[str] | None = None,
        block: Block | None = None,
        width: int | Expression[int | float] | None = None,
        height: int | Expression[int | float] | None = None,
        x: int | Expression[int | float] = 0,
        y: int | Expression[int | float] = 0,
    ) -> None:
        """
        Create a BarChart.

        Args:
            data: ``Sequence[Bar | BarGroup | int] | None``. Defaults to ``None``.
            bar_width: ``int | Expression[int | float] | None``. Defaults to ``None``.
            bar_gap: ``int | Expression[int | float] | None``. Defaults to ``None``.
            group_gap: ``int | Expression[int | float] | None``. Defaults to ``None``.
            maximum: ``int | Expression[int | float] | None``. Defaults to ``None``.
            direction: ``str | Expression[str] | None``. Defaults to ``None``.
            bar_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            value_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            label_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            bar_set: ``str | Expression[str] | None``. Defaults to ``None``.
            block: ``Block | None``. Defaults to ``None``.
            width: ``int | Expression[int | float] | None``. Defaults to ``None``.
            height: ``int | Expression[int | float] | None``. Defaults to ``None``.
            x: ``int | Expression[int | float]``. Defaults to ``0``.
            y: ``int | Expression[int | float]``. Defaults to ``0``.
        """
    def __repr__(self, /) -> str: ...
    def append(
        self,
        /,
        bar: Bar | int,
        *,
        maximum_bars: int | Expression[int | float] | None = None,
    ) -> None: ...
    def clear(self, /) -> None: ...
    def copy(self, /) -> BarChart: ...
    def __copy__(self, /) -> BarChart: ...
    def __deepcopy__(self, /, _memo: dict[int, object]) -> BarChart: ...
    @property
    def label_style(self) -> Style | DynamicStyle:
        """The colors and text modifiers applied to bar and group labels."""
    @label_style.setter
    def label_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def group_gap(self) -> int | Expression[int | float]:
        """The number of empty cells between groups of bars."""
    @group_gap.setter
    def group_gap(self, value: int | Expression[int | float]) -> None: ...
    @property
    def bar_gap(self) -> int | Expression[int | float]:
        """The number of empty cells between adjacent bars."""
    @bar_gap.setter
    def bar_gap(self, value: int | Expression[int | float]) -> None: ...
    @property
    def block(self) -> Block | None:
        """The optional border, titles and padding around the content."""
    @block.setter
    def block(self, value: Block | None) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the cells."""
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def bar_width(self) -> int | Expression[int | float]:
        """The thickness of each bar, in cells."""
    @bar_width.setter
    def bar_width(self, value: int | Expression[int | float]) -> None: ...
    @property
    def direction(self) -> str | Expression[str]:
        """The orientation of the bars: ``vertical`` or ``horizontal``."""
    @direction.setter
    def direction(self, value: str | Expression[str]) -> None: ...
    @property
    def maximum(self) -> int | Expression[int | float] | None:
        """The value represented by a full bar, or ``None`` to use the largest value."""
    @maximum.setter
    def maximum(self, value: int | Expression[int | float] | None) -> None: ...
    @property
    def groups(self) -> Sequence[BarGroup]:
        """The groups of bars displayed in sequence order."""
    @groups.setter
    def groups(self, value: Sequence[BarGroup]) -> None: ...
    @property
    def bar_set(self) -> str | Expression[str]:
        """The named set of symbols used to draw partial and full bars."""
    @bar_set.setter
    def bar_set(self, value: str | Expression[str]) -> None: ...
    @property
    def bar_style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the bars."""
    @bar_style.setter
    def bar_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def value_style(self) -> Style | DynamicStyle:
        """The colors and text modifiers applied to the displayed value."""
    @value_style.setter
    def value_style(self, value: Style | DynamicStyle) -> None: ...

class TableCell:
    """
    Styled content displayed in a table cell.

    Attributes:
        column_span: The number of adjacent table columns occupied by this cell.
        content: The styled text displayed by this item.
        style: The default colors and text modifiers applied to the cells.

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
        column_span: int = 1,
    ) -> None:
        """
        Create a TableCell.

        Args:
            content: ``TextContent | Expression[str]``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            column_span: ``int``. Defaults to ``1``.
        """
    def __repr__(self, /) -> str: ...
    def __hash__(self, /) -> int: ...
    def __eq__(self, value: object, /) -> bool: ...
    def __copy__(self, /) -> TableCell: ...
    def __deepcopy__(self, /, _memo: dict[int, object]) -> TableCell: ...
    @property
    def column_span(self) -> int:
        """The number of adjacent table columns occupied by this cell."""
    @property
    def content(self) -> TextContent | Expression[str]:
        """The styled text displayed by this item."""
    @property
    def style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the cells."""

class TableRow:
    """
    A row of cells with height and spacing.

    Attributes:
        style: The default colors and text modifiers applied to the cells.
        height: The height of the row content, in terminal cells.
        bottom_margin: The number of empty lines after this row.
        top_margin: The number of empty lines before this row.
        cells: The cells displayed from the first column to the last.

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
        height: int | Expression[int | float] = 1,
        top_margin: int | Expression[int | float] = 0,
        bottom_margin: int | Expression[int | float] = 0,
        style: Style | DynamicStyle | None = None,
    ) -> None:
        """
        Create a TableRow.

        Args:
            cells: ``Sequence[TableCell | TextContent]``.
            height: ``int | Expression[int | float]``. Defaults to ``1``.
            top_margin: ``int | Expression[int | float]``. Defaults to ``0``.
            bottom_margin: ``int | Expression[int | float]``. Defaults to ``0``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
        """
    def __repr__(self, /) -> str: ...
    def __hash__(self, /) -> int: ...
    def __eq__(self, value: object, /) -> bool: ...
    def __copy__(self, /) -> TableRow: ...
    def __deepcopy__(self, /, _memo: dict[int, object]) -> TableRow: ...
    @property
    def style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the cells."""
    @property
    def height(self) -> int | Expression[int | float]:
        """The height of the row content, in terminal cells."""
    @property
    def bottom_margin(self) -> int | Expression[int | float]:
        """The number of empty lines after this row."""
    @property
    def top_margin(self) -> int | Expression[int | float]:
        """The number of empty lines before this row."""
    @property
    def cells(self) -> Sequence[TableCell | TextContent]:
        """The cells displayed from the first column to the last."""

class Table(Widget):
    """
    A retained table with row, column and cell selection.

    Attributes:
        flex: The layout policy that distributes unused horizontal space among columns.
        widths: The width constraints for columns, in cells or proportional size rules.
        highlight_symbol: The text displayed beside the selected row.
        block: The optional border, titles and padding around the content.
        row_highlight_style: The colors and text modifiers applied to the selected row.
        selected_cell: The zero-based row and column indexes of the selected cell, or ``None``.
        selected_row: The zero-based selected row index, or ``None`` when no row is selected.
        offset: The zero-based index of the first data row shown when scrolling.
        style: The default colors and text modifiers applied to the cells.
        column_highlight_style: The colors and text modifiers applied to the selected column.
        selected_column: The zero-based selected column index, or ``None`` when no column is selected.
        visible_range: The first visible data-row index and the exclusive end index from the most recent render, or ``None`` before rendering.
        rows: The data rows displayed between the header and footer.
        cell_highlight_style: The colors and text modifiers applied where the selected row and column intersect.
        header: The optional row displayed above the scrolling data rows.
        footer: The optional row displayed below the scrolling data rows.
        column_spacing: The number of empty cells between adjacent columns.
        highlight_spacing: When space is reserved for the highlight symbol: ``always``, ``when_selected`` or ``never``.

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
        column_spacing: int | Expression[int | float] | None = None,
        flex: str | None = None,
        selected_row: int | Expression[int | float] | None = None,
        selected_column: int | Expression[int | float] | None = None,
        offset: int | Expression[int | float] | None = None,
        style: Style | DynamicStyle | None = None,
        row_highlight_style: Style | DynamicStyle | None = None,
        column_highlight_style: Style | DynamicStyle | None = None,
        cell_highlight_style: Style | DynamicStyle | None = None,
        highlight_symbol: str | Expression[str] | None = None,
        highlight_spacing: str | Expression[str] | None = None,
        block: Block | None = None,
        width: int | Expression[int | float] | None = None,
        height: int | Expression[int | float] | None = None,
        x: int | Expression[int | float] = 0,
        y: int | Expression[int | float] = 0,
    ) -> None:
        """
        Create a Table.

        Args:
            rows: ``Sequence[TableRow | Sequence[TableCell | TextContent]] | None``. Defaults to
                ``None``.
            header: ``TableRow | Sequence[TableCell | TextContent] | None``. Defaults to
                ``None``.
            footer: ``TableRow | Sequence[TableCell | TextContent] | None``. Defaults to
                ``None``.
            widths: ``Sequence[int | SizeRule | tuple[int, int]] | None``. Defaults to ``None``.
            column_spacing: ``int | Expression[int | float] | None``. Defaults to ``None``.
            flex: ``str | None``. Defaults to ``None``.
            selected_row: ``int | Expression[int | float] | None``. Defaults to ``None``.
            selected_column: ``int | Expression[int | float] | None``. Defaults to ``None``.
            offset: ``int | Expression[int | float] | None``. Defaults to ``None``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            row_highlight_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            column_highlight_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            cell_highlight_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            highlight_symbol: ``str | Expression[str] | None``. Defaults to ``None``.
            highlight_spacing: ``str | Expression[str] | None``. Defaults to ``None``.
            block: ``Block | None``. Defaults to ``None``.
            width: ``int | Expression[int | float] | None``. Defaults to ``None``.
            height: ``int | Expression[int | float] | None``. Defaults to ``None``.
            x: ``int | Expression[int | float]``. Defaults to ``0``.
            y: ``int | Expression[int | float]``. Defaults to ``0``.
        """
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
    def scroll_down_by(self, /, amount: int | Expression[int | float]) -> None: ...
    def scroll_up_by(self, /, amount: int | Expression[int | float]) -> None: ...
    def scroll_right_by(self, /, amount: int | Expression[int | float]) -> None: ...
    def scroll_left_by(self, /, amount: int | Expression[int | float]) -> None: ...
    def copy(self, /) -> Table: ...
    def __copy__(self, /) -> Table: ...
    def __deepcopy__(self, /, _memo: dict[int, object]) -> Table: ...
    @property
    def flex(self) -> str:
        """The layout policy that distributes unused horizontal space among columns."""
    @flex.setter
    def flex(self, value: str) -> None: ...
    @property
    def widths(self) -> Sequence[int | SizeRule | tuple[int, int]]:
        """The width constraints for columns, in cells or proportional size rules."""
    @widths.setter
    def widths(self, value: Sequence[int | SizeRule | tuple[int, int]]) -> None: ...
    @property
    def highlight_symbol(self) -> str | Expression[str]:
        """The text displayed beside the selected row."""
    @highlight_symbol.setter
    def highlight_symbol(self, value: str | Expression[str]) -> None: ...
    @property
    def block(self) -> Block | None:
        """The optional border, titles and padding around the content."""
    @block.setter
    def block(self, value: Block | None) -> None: ...
    @property
    def row_highlight_style(self) -> Style | DynamicStyle:
        """The colors and text modifiers applied to the selected row."""
    @row_highlight_style.setter
    def row_highlight_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def selected_cell(self) -> tuple[int, int] | None:
        """The zero-based row and column indexes of the selected cell, or ``None``."""
    @property
    def selected_row(self) -> int | Expression[int | float] | None:
        """The zero-based selected row index, or ``None`` when no row is selected."""
    @selected_row.setter
    def selected_row(self, value: int | Expression[int | float] | None) -> None: ...
    @property
    def offset(self) -> int | Expression[int | float]:
        """The zero-based index of the first data row shown when scrolling."""
    @offset.setter
    def offset(self, value: int | Expression[int | float]) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the cells."""
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def column_highlight_style(self) -> Style | DynamicStyle:
        """The colors and text modifiers applied to the selected column."""
    @column_highlight_style.setter
    def column_highlight_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def selected_column(self) -> int | Expression[int | float] | None:
        """The zero-based selected column index, or ``None`` when no column is selected."""
    @selected_column.setter
    def selected_column(self, value: int | Expression[int | float] | None) -> None: ...
    @property
    def visible_range(self) -> tuple[int, int]:
        """The first visible data-row index and the exclusive end index from the most recent render, or ``None`` before rendering."""
    @property
    def rows(self) -> Sequence[TableRow | Sequence[TableCell | TextContent]]:
        """The data rows displayed between the header and footer."""
    @rows.setter
    def rows(
        self, value: Sequence[TableRow | Sequence[TableCell | TextContent]]
    ) -> None: ...
    @property
    def cell_highlight_style(self) -> Style | DynamicStyle:
        """The colors and text modifiers applied where the selected row and column intersect."""
    @cell_highlight_style.setter
    def cell_highlight_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def header(self) -> TableRow | Sequence[TableCell | TextContent] | None:
        """The optional row displayed above the scrolling data rows."""
    @header.setter
    def header(
        self, value: TableRow | Sequence[TableCell | TextContent] | None
    ) -> None: ...
    @property
    def footer(self) -> TableRow | Sequence[TableCell | TextContent] | None:
        """The optional row displayed below the scrolling data rows."""
    @footer.setter
    def footer(
        self, value: TableRow | Sequence[TableCell | TextContent] | None
    ) -> None: ...
    @property
    def column_spacing(self) -> int | Expression[int | float]:
        """The number of empty cells between adjacent columns."""
    @column_spacing.setter
    def column_spacing(self, value: int | Expression[int | float]) -> None: ...
    @property
    def highlight_spacing(self) -> str | Expression[str]:
        """When space is reserved for the highlight symbol: ``always``, ``when_selected`` or ``never``."""
    @highlight_spacing.setter
    def highlight_spacing(self, value: str | Expression[str]) -> None: ...

class Scrollbar(Widget):
    """
    A scrollbar showing position within content.

    Attributes:
        content_length: The total length of the scrollable content, in the same units as ``content_position``.
        is_transparent: Whether cells not drawn by the scrollbar let the content below show through.
        end_style: The colors and text modifiers applied to the end symbol.
        thumb_symbol: The symbol drawn for the movable scroll indicator.
        track_style: The colors and text modifiers applied to the track.
        end_symbol: The symbol drawn at the end of the track, or ``None`` to omit it.
        thumb_style: The colors and text modifiers applied to the movable scroll indicator.
        style: The default colors and text modifiers applied to the cells.
        orientation: The edge holding the scrollbar: ``vertical_left``, ``vertical_right``, ``horizontal_top`` or ``horizontal_bottom``.
        content_position: The current position within the scrollable content.
        begin_style: The colors and text modifiers applied to the beginning symbol.
        viewport_content_length: The amount of content visible at once, or ``None`` to derive it from the area.
        symbols: The symbol preset name, or ``None`` when the symbols do not match a preset.
        begin_symbol: The symbol drawn at the beginning of the track, or ``None`` to omit it.
        track_symbol: The symbol drawn behind the indicator, or ``None`` to omit the track.

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
        content_length: int | Expression[int | float] | None = None,
        position: int | Expression[int | float] | None = None,
        *,
        orientation: str | Expression[str] | None = None,
        viewport_content_length: int | Expression[int | float] | None = None,
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
        width: int | Expression[int | float] | None = None,
        height: int | Expression[int | float] | None = None,
        x: int | Expression[int | float] = 0,
        y: int | Expression[int | float] = 0,
    ) -> None:
        """
        Create a Scrollbar.

        Args:
            content_length: ``int | Expression[int | float] | None``. Defaults to ``None``.
            position: ``int | Expression[int | float] | None``. Defaults to ``None``.
            orientation: ``str | Expression[str] | None``. Defaults to ``None``.
            viewport_content_length: ``int | Expression[int | float] | None``. Defaults to ``None``.
            symbols: ``str | Sequence[str] | None``. Defaults to ``None``.
            thumb_symbol: ``str | Expression[str] | None``. Defaults to ``None``.
            track_symbol: ``str | Expression[str] | None``. Defaults to ``None``.
            begin_symbol: ``str | Expression[str] | None``. Defaults to ``None``.
            end_symbol: ``str | Expression[str] | None``. Defaults to ``None``.
            has_track: ``bool | Expression[bool]``. Defaults to ``True``.
            has_begin: ``bool | Expression[bool]``. Defaults to ``True``.
            has_end: ``bool | Expression[bool]``. Defaults to ``True``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            thumb_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            track_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            begin_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            end_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            is_transparent: ``bool | Expression[bool] | None``. Defaults to ``None``.
            width: ``int | Expression[int | float] | None``. Defaults to ``None``.
            height: ``int | Expression[int | float] | None``. Defaults to ``None``.
            x: ``int | Expression[int | float]``. Defaults to ``0``.
            y: ``int | Expression[int | float]``. Defaults to ``0``.
        """
    def __repr__(self, /) -> str: ...
    def first(self, /) -> None: ...
    def last(self, /) -> None: ...
    def next(self, /) -> None: ...
    def previous(self, /) -> None: ...
    def scroll(self, /, direction: str | Expression[str]) -> None: ...
    def copy(self, /) -> Scrollbar: ...
    def __copy__(self, /) -> Scrollbar: ...
    def __deepcopy__(self, /, _memo: dict[int, object]) -> Scrollbar: ...
    @property
    def content_length(self) -> int | Expression[int | float]:
        """The total length of the scrollable content, in the same units as ``content_position``."""
    @content_length.setter
    def content_length(self, value: int | Expression[int | float]) -> None: ...
    @property
    def is_transparent(self) -> bool | Expression[bool]:
        """Whether cells not drawn by the scrollbar let the content below show through."""
    @is_transparent.setter
    def is_transparent(self, value: bool | Expression[bool]) -> None: ...
    @property
    def end_style(self) -> Style | DynamicStyle:
        """The colors and text modifiers applied to the end symbol."""
    @end_style.setter
    def end_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def thumb_symbol(self) -> str | Expression[str]:
        """The symbol drawn for the movable scroll indicator."""
    @thumb_symbol.setter
    def thumb_symbol(self, value: str | Expression[str]) -> None: ...
    @property
    def track_style(self) -> Style | DynamicStyle:
        """The colors and text modifiers applied to the track."""
    @track_style.setter
    def track_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def end_symbol(self) -> str | Expression[str]:
        """The symbol drawn at the end of the track, or ``None`` to omit it."""
    @end_symbol.setter
    def end_symbol(self, value: str | Expression[str]) -> None: ...
    @property
    def thumb_style(self) -> Style | DynamicStyle:
        """The colors and text modifiers applied to the movable scroll indicator."""
    @thumb_style.setter
    def thumb_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the cells."""
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def orientation(self) -> str | Expression[str]:
        """The edge holding the scrollbar: ``vertical_left``, ``vertical_right``, ``horizontal_top`` or ``horizontal_bottom``."""
    @orientation.setter
    def orientation(self, value: str | Expression[str]) -> None: ...
    @property
    def content_position(self) -> int | Expression[int | float]:
        """The current position within the scrollable content."""
    @content_position.setter
    def content_position(self, value: int | Expression[int | float]) -> None: ...
    @property
    def begin_style(self) -> Style | DynamicStyle:
        """The colors and text modifiers applied to the beginning symbol."""
    @begin_style.setter
    def begin_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def viewport_content_length(self) -> int | Expression[int | float]:
        """The amount of content visible at once, or ``None`` to derive it from the area."""
    @viewport_content_length.setter
    def viewport_content_length(self, value: int | Expression[int | float]) -> None: ...
    @property
    def symbols(self) -> str | Sequence[str]:
        """The symbol preset name, or ``None`` when the symbols do not match a preset."""
    @symbols.setter
    def symbols(self, value: str | Sequence[str]) -> None: ...
    @property
    def begin_symbol(self) -> str | Expression[str]:
        """The symbol drawn at the beginning of the track, or ``None`` to omit it."""
    @begin_symbol.setter
    def begin_symbol(self, value: str | Expression[str]) -> None: ...
    @property
    def track_symbol(self) -> str | Expression[str]:
        """The symbol drawn behind the indicator, or ``None`` to omit the track."""
    @track_symbol.setter
    def track_symbol(self, value: str | Expression[str]) -> None: ...

class Tabs(Widget):
    """
    Selectable titles with editable padding, divider and styles.

    Attributes:
        padding_right: The number of empty cells after each tab title.
        selected: The zero-based selected tab index, or ``None`` when no tab is selected.
        highlight_style: The colors and text modifiers applied to the selected item.
        titles: The tab titles displayed from left to right.
        style: The default colors and text modifiers applied to the cells.
        block: The optional border, titles and padding around the content.
        padding_left: The number of empty cells before each tab title.
        divider: The text drawn between adjacent tab titles.

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
        selected: int | Expression[int | float] | None = None,
        style: Style | DynamicStyle | None = None,
        highlight_style: Style | DynamicStyle | None = None,
        divider: str | Expression[str] | None = None,
        padding_left: int | Expression[int | float] | None = None,
        padding_right: int | Expression[int | float] | None = None,
        block: Block | None = None,
        width: int | Expression[int | float] | None = None,
        height: int | Expression[int | float] | None = None,
        x: int | Expression[int | float] = 0,
        y: int | Expression[int | float] = 0,
    ) -> None:
        """
        Create a Tabs.

        Args:
            titles: ``Sequence[TextContent] | None``. Defaults to ``None``.
            selected: ``int | Expression[int | float] | None``. Defaults to ``None``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            highlight_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            divider: ``str | Expression[str] | None``. Defaults to ``None``.
            padding_left: ``int | Expression[int | float] | None``. Defaults to ``None``.
            padding_right: ``int | Expression[int | float] | None``. Defaults to ``None``.
            block: ``Block | None``. Defaults to ``None``.
            width: ``int | Expression[int | float] | None``. Defaults to ``None``.
            height: ``int | Expression[int | float] | None``. Defaults to ``None``.
            x: ``int | Expression[int | float]``. Defaults to ``0``.
            y: ``int | Expression[int | float]``. Defaults to ``0``.
        """
    def __repr__(self, /) -> str: ...
    def append(self, /, title: str | Expression[str]) -> None: ...
    def pop(
        self, /, index: int | Expression[int | float] | None = None
    ) -> TextContent: ...
    def clear(self, /) -> None: ...
    def select_next(self, /, *, should_wrap: bool | Expression[bool] = True) -> None: ...
    def select_previous(
        self, /, *, should_wrap: bool | Expression[bool] = True
    ) -> None: ...
    def select_first(self, /) -> None: ...
    def select_last(self, /) -> None: ...
    def copy(self, /) -> Tabs: ...
    def __copy__(self, /) -> Tabs: ...
    def __deepcopy__(self, /, _memo: dict[int, object]) -> Tabs: ...
    @property
    def padding_right(self) -> int | Expression[int | float]:
        """The number of empty cells after each tab title."""
    @padding_right.setter
    def padding_right(self, value: int | Expression[int | float]) -> None: ...
    @property
    def selected(self) -> int | Expression[int | float] | None:
        """The zero-based selected tab index, or ``None`` when no tab is selected."""
    @selected.setter
    def selected(self, value: int | Expression[int | float] | None) -> None: ...
    @property
    def highlight_style(self) -> Style | DynamicStyle:
        """The colors and text modifiers applied to the selected item."""
    @highlight_style.setter
    def highlight_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def titles(self) -> Sequence[TextContent]:
        """The tab titles displayed from left to right."""
    @titles.setter
    def titles(self, value: Sequence[TextContent]) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the cells."""
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def block(self) -> Block | None:
        """The optional border, titles and padding around the content."""
    @block.setter
    def block(self, value: Block | None) -> None: ...
    @property
    def padding_left(self) -> int | Expression[int | float]:
        """The number of empty cells before each tab title."""
    @padding_left.setter
    def padding_left(self, value: int | Expression[int | float]) -> None: ...
    @property
    def divider(self) -> str | Expression[str]:
        """The text drawn between adjacent tab titles."""
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
        kind: Whether the drawing holds terminal glyphs or palette pixels.
        palette: For palette drawings, the color of each symbol.

    Attributes:
        kind: Whether the drawing holds terminal glyphs or palette pixels.
        rows: The raw rows of the drawing.
        width: Display columns for text; grapheme-token columns for palette pixels.
        height: The number of rows.
        palette: The color of each palette symbol; empty for text drawings.

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
    ) -> None:
        """
        Create a Drawing.

        Args:
            rows: ``Sequence[str]``.
            kind: ``Literal['text', 'palette']``. Defaults to ``'text'``.
            palette: ``Mapping[str, tuple[int, int, int] | None] | None``. Defaults to ``None``.
        """
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
    One frame of a [`DrawingAnimation`][xnano_core._xnano_core.DrawingAnimation].

    Args:
        drawing: The picture shown during this frame.
        duration_milliseconds: How long the frame stays on screen.

    Attributes:
        drawing: The picture shown during this frame.
        duration_milliseconds: How long the frame stays on screen.

    Examples:
        ```python
        frame = DrawingFrame(Drawing(['a']), duration_milliseconds=50)
        assert frame.duration_milliseconds == 50
        assert frame.drawing.rows == ('a',)
        ```
    """

    def __init__(self, drawing: Drawing, *, duration_milliseconds: int = 100) -> None:
        """
        Create a DrawingFrame.

        Args:
            drawing: ``Drawing``.
            duration_milliseconds: ``int``. Defaults to ``100``.
        """
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

    Attributes:
        frames: The frames in display order.
        should_loop: Whether the animation starts again after the last frame.

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
    ) -> None:
        """
        Create a DrawingAnimation.

        Args:
            frames: ``Sequence[DrawingFrame]``.
            should_loop: ``bool``. Defaults to ``True``.
        """
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
    Draw a [`Drawing`][xnano_core._xnano_core.Drawing] into the target.

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
    ) -> None:
        """
        Create a Draw.

        Args:
            drawing: ``Drawing``.
            x: ``int``. Defaults to ``0``.
            y: ``int``. Defaults to ``0``.
            encoding: ``PixelEncoding``. Defaults to ``'half_blocks'``.
        """

class AnimateDrawing(Operation):
    """
    Play a [`DrawingAnimation`][xnano_core._xnano_core.DrawingAnimation] on a mounted buffer.

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
    ) -> None:
        """
        Create a AnimateDrawing.

        Args:
            animation: ``DrawingAnimation``.
            x: ``int``. Defaults to ``0``.
            y: ``int``. Defaults to ``0``.
            encoding: ``PixelEncoding``. Defaults to ``'half_blocks'``.
            start_milliseconds: ``int``. Defaults to ``0``.
        """

class Cell:
    """
    A detached grapheme with its style, copied out of or written into a surface.

    Reading ``buffer[column, row]`` returns a ``Cell`` snapshot; changing it does not
    change the buffer until it is written back with ``buffer[column, row] = cell``.
    A transparent cell lets the content below it show through when buffers are
    composited with the ``'transparent'`` paste mode.

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
        foreground: The text color of this cell.
        background: The background color of this cell.
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
    """The grapheme drawn in the cell."""
    style: Style
    """The cell's style."""
    is_transparent: bool
    """Whether the cell lets lower layers show through."""

    def __init__(
        self,
        symbol: str = ' ',
        *,
        style: Style | None = None,
        foreground: ColorValue | None = None,
        background: ColorValue | None = None,
        modifiers: Sequence[Modifier] = (),
        is_transparent: bool = False,
    ) -> None:
        """
        Create a Cell.

        Args:
            symbol: ``str``. Defaults to ``' '``.
            style: ``Style | None``. Defaults to ``None``.
            foreground: ``ColorValue | None``. Defaults to ``None``.
            background: ``ColorValue | None``. Defaults to ``None``.
            modifiers: ``Sequence[Modifier]``. Defaults to ``()``.
            is_transparent: ``bool``. Defaults to ``False``.
        """
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

    Get one from [`Surface.pixels`][xnano_core._xnano_core.Surface.pixels].

    Attributes:
        surface: The surface the pixels are drawn into.
        encoding: How pixels are packed into cells: ``'half_blocks'`` or ``'braille'``.
        width: The width of the view in pixels.
        height: The height of the view in pixels.

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

    def write(self, pixels: Iterable[PixelEntry], *, clip: bool = True) -> None:
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

    def draw_rgba(
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
            buffer.pixels().draw_rgba(red, width=2, height=2)
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

    [`Buffer`][xnano_core._xnano_core.Buffer] and [`Region`][xnano_core._xnano_core.Region] are
    surfaces. Index with ``surface[column, row]`` for a
    [`Cell`][xnano_core._xnano_core.Cell] or ``surface[columns, rows]`` with two slices for
    a [`Region`][xnano_core._xnano_core.Region]. Indexes start at ``(0, 0)`` in the top-left
    corner.

    Attributes:
        width: The surface width in cells.
        height: The surface height in cells.

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

    def set_background_colors(
        self,
        colors: Sequence[ColorValue | None],
        *,
        width: int,
        x: int = 0,
        y: int = 0,
    ) -> None:
        """
        Set the background color of a block of cells in one pass.

        Symbols and foreground colors are kept, and the whole block counts as one change (the
        revision grows by one).

        Args:
            colors: A flat, row-major sequence of colors (names, ``(r, g, b)`` tuples or
                [`Color`][xnano_core._xnano_core.Color] values). ``None`` leaves a cell alone.
            width: The number of colors in one row of ``colors``.
            x: The column of the block's top-left cell in this surface.
            y: The row of the block's top-left cell in this surface.

        Raises:
            ValueError: ``width`` is below 1, ``len(colors)`` is not a multiple of ``width``, or
                the block does not fit inside the surface, or an entry is not a color.
            TypeError: ``colors`` is a single string instead of a sequence of colors, or an
                entry has no color meaning.

        Examples:
            ```python
            buffer = Buffer(width=3, height=2)
            buffer.write('abc')
            buffer.set_background_colors(['red', None, (0, 0, 255), 'green'], width=2, x=1)
            assert buffer[1, 0].background == Color('red')
            assert buffer[2, 0].background == Color.reset
            assert buffer[1, 1].background == Color('#0000ff')
            assert buffer[2, 1].background == Color('green')
            assert buffer[1, 0].symbol == 'b'
            ```
        """

    def set_foreground_colors(
        self,
        colors: Sequence[ColorValue | None],
        *,
        width: int,
        x: int = 0,
        y: int = 0,
    ) -> None:
        """
        Set the foreground color of a block of cells in one pass.

        Symbols and background colors are kept, and the whole block counts as one change (the
        revision grows by one).

        Args:
            colors: A flat, row-major sequence of colors (names, ``(r, g, b)`` tuples or
                [`Color`][xnano_core._xnano_core.Color] values). ``None`` leaves a cell alone.
            width: The number of colors in one row of ``colors``.
            x: The column of the block's top-left cell in this surface.
            y: The row of the block's top-left cell in this surface.

        Raises:
            ValueError: ``width`` is below 1, ``len(colors)`` is not a multiple of ``width``, or
                the block does not fit inside the surface, or an entry is not a color.
            TypeError: ``colors`` is a single string instead of a sequence of colors, or an
                entry has no color meaning.

        Examples:
            ```python
            buffer = Buffer(width=3, height=2)
            buffer.write('abc')
            buffer.set_foreground_colors(['red', None, (0, 0, 255), 'green'], width=2, x=1)
            assert buffer[1, 0].foreground == Color('red')
            assert buffer[2, 0].foreground == Color.reset
            assert buffer[1, 1].foreground == Color('#0000ff')
            assert buffer[2, 1].foreground == Color('green')
            assert buffer[1, 0].symbol == 'b'
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

    def __or__(self, operation: Operation | Style) -> Self:
        """
        Apply ``operation`` to this surface and return the surface.

        Examples:
            ```python
            buffer = Buffer(width=6, height=1) | Write('abc')
            assert buffer.text.startswith('abc')
            ```
        """

class Region(Surface):
    """
    A fixed rectangle of a buffer that shares the buffer's cells.

    Indexes into a region are relative to its top-left corner. After the buffer is
    resized, the region stays usable only while its whole rectangle still fits;
    otherwise access raises ``InvalidRegionError``. Use ``copy()`` for an
    independent buffer.

    Attributes:
        buffer: The buffer the region belongs to.
        bounds: The region's rectangle in its buffer.
        is_valid: Whether the whole rectangle still fits inside the buffer.

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

    Attributes:
        x: The column of the buffer in its parent. Assigning moves the buffer.
        y: The row of the buffer in its parent. Assigning moves the buffer.
        width: The width in cells. Assigning resizes the buffer.
        height: The height in cells. Assigning resizes the buffer.
        position: The ``Point`` of the buffer in its parent. Assigning moves the buffer.
        size: The ``Size`` of the buffer. Assigning resizes the buffer.
        bounds: The buffer's rectangle in its parent.
        layer: The stacking order among siblings; higher layers are drawn on top.
        is_visible: Whether the buffer is drawn. Hidden buffers still keep their content.
        is_focusable: Whether the buffer can receive input focus.
        content: The whole buffer as a region. Assigning text replaces the content.
        cells: The same view as ``content``; there is only one store of cells.
        text: The plain text of the buffer's own cells, without mounted children.
        revision: A number that increases every time the buffer's cells or geometry change.
        children: The attached child buffers in attachment order.
        registry: The registry that decides which operations this buffer can apply.

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
    ) -> None:
        """
        Create a Buffer.

        Args:
            content: ``TextContent | None``. Defaults to ``None``.
            width: ``int | None``. Defaults to ``None``.
            height: ``int | None``. Defaults to ``None``.
            x: ``int``. Defaults to ``0``.
            y: ``int``. Defaults to ``0``.
            style: ``Style | None``. Defaults to ``None``.
            registry: ``Registry | None``. Defaults to ``None``.
        """
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

    def paste(
        self,
        source: Buffer | Region,
        *,
        x: int = 0,
        y: int = 0,
        mode: PasteMode = 'replace',
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
            canvas.paste(sprite, x=2)
            assert canvas.text == '  ab'
            ```
        """

    def attach(
        self,
        child: Buffer,
        *,
        geometry: GeometryMode = 'explicit',
        mode: PasteMode = 'replace',
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

    Attributes:
        events_processed: The number of events dispatched to hooks.
        updates_processed: The number of simulation updates run.
        did_render: Whether a frame was drawn.
        is_running: Whether the runtime is still running after the step.

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
    [`Waker`][xnano_core._xnano_core.Waker] may be used from other threads.

    Attributes:
        registry: The runtime's own copy of the operation registry.
        clock: The clock all schedules and timers run on.
        device: The output device: its size and capabilities.
        cursor: The runtime's cursor.
        input: The pressed keys and pointer position.
        router: The input router that decides which buffer receives each event.
        frame_metrics: Timing of the frames drawn so far.
        is_running: Whether the runtime has been entered and not stopped.
        is_closed: Whether ``close()`` has run.
        buffers: The mounted root buffers.
        needs_frame: Whether the next step will draw a frame.
        title: Window title last set on this runtime; ``None`` clears the title.
        is_output_captured: Whether a live runtime is holding back standard output and standard
            error.
        effects: The running effects, with controls to start, inspect and cancel them.

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
        inline_width: int | None = None,
        should_handle_exit_signals: bool = True,
        options: TerminalOptions | None = None,
        clock: Clock | None = None,
        registry: Registry | None = None,
    ) -> Runtime:
        """
        Create a runtime that draws to the terminal and reads its input.

        Live runtimes use a new monotonic clock unless you pass one. Terminal modes the
        runtime turns on are restored on every exit path.

        Args:
            tick_interval_milliseconds: How often ``'tick'`` events fire, or ``None``
                for no ticks.
            frame_interval_milliseconds: The shortest time between frames.
            inline_height: Draw this many rows inline instead of taking over the
                whole screen.
            inline_width: Draw no wider than this many columns (never wider than the
                terminal). Without ``inline_height`` this has no effect.
            should_handle_exit_signals: Whether interrupt and terminate signals
                request an exit.
            options: Raw mode, alternate screen and input negotiation settings.
            clock: The clock the runtime reads, for example a
                [`Clock`][xnano_core._xnano_core.Clock] that continues from the time of an
                earlier runtime. ``None`` creates a monotonic clock.
            registry: The operation registry for the runtime.

        Examples:
            ```python
            runtime = Runtime.live(frame_interval_milliseconds=33)
            assert not runtime.is_closed
            runtime.close()

            continued = Runtime.live(clock=Clock.monotonic(elapsed_seconds=5.0))
            assert continued.clock.elapsed_seconds >= 5.0
            continued.close()
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
    def cursor(self) -> Cursor:
        """The runtime's cursor."""

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

    @property
    def title(self) -> str | None:
        """
        Window title last set on this runtime.

        Set printable text to change a live terminal's title, or ``None`` to clear it.
        Offscreen runtimes store the value without terminal output. Control characters
        raise ``ValueError``. Setting a title on a closed runtime raises ``RuntimeError``.

        Maps to [`crossterm::terminal::SetTitle`](https://docs.rs/crossterm/0.29.0/crossterm/terminal/struct.SetTitle.html).
        """
    @title.setter
    def title(self, value: str | None) -> None: ...
    @property
    def is_output_captured(self) -> bool:
        """
        Whether a live runtime is holding back standard output and standard error.

        It is ``False`` for an offscreen runtime, when capturing was not asked for, and on
        platforms where output cannot be captured.
        """

    def take_captured_output(self) -> str:
        """
        Return the text written to standard output and standard error during a live session.

        A live runtime holds back anything printed or logged while it is open, so it cannot
        corrupt the screen; use this to show it in the interface, for example in a log panel.
        Each call returns what arrived since the previous one. Text that is never taken is
        printed to the stream it was written to when the runtime closes. Text from one stream
        keeps its order; text from the two streams is joined in the order it was read.

        Returns an empty string for an offscreen runtime, for a live runtime created with
        ``should_capture_output=False`` and on Windows.

        Examples:
            ```python
            with Runtime.offscreen(width=10, height=2) as runtime:
                assert runtime.take_captured_output() == ''
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
    def effects(self) -> EffectManager:
        """The running effects, with controls to start, inspect and cancel them."""
    def watch_state(self, reference: StateReference | TerminalStateStore) -> None: ...
    def provide(self, name: str, function: Callable[[], int | float]) -> None:
        """
        Provide the value of a named external expression.

        Extensions such as audio expose values (a microphone level, a musical beat) to the
        expression language by name. ``function`` is called with no arguments, on the
        runtime's own thread, each time an expression that reads ``name`` is evaluated.

        Args:
            name: The name the expression reads.
            function: Returns the current value as an ``int`` or ``float``.
        """

class FrameMetrics:
    """
    Timing of the frames a runtime has drawn.

    Attributes:
        frames: The number of frames drawn.
        last_frame_microseconds: How long the last frame took to draw, in microseconds.
        average_frame_microseconds: The mean frame time, in microseconds.

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

    Attributes:
        size: The size of the frame in cells.
        revision: A number that increases with every committed frame.
        cursor_position: Where the cursor is, or ``None`` when no cursor is placed.
        is_cursor_visible: Whether the cursor is shown.
        text: The frame's plain text rows joined by newlines.
        ansi: The frame as text with styling escape sequences.

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

    Attributes:
        format_version: The version of the cell grid byte format.
        columns: The width in cells.
        rows: The height in cells.
        has_graphics_protocol_cells: Whether the grid carries cells for a terminal graphics
            protocol.
        required_protocol: The graphics protocol the grid needs, or ``None`` for plain cells.

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

    Attributes:
        format_version: The version of the cell animation byte format.
        columns: The width of every frame in cells.
        rows: The height of every frame in cells.
        frame_count: The number of frames.
        duration_milliseconds: The total duration of one pass in milliseconds.
        should_loop: Whether the animation repeats.

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

    Attributes:
        maximum_cells: The most cells accepted.
        maximum_frames: The most frames accepted.
        maximum_payload_bytes: The most graphics payload bytes accepted.

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
    ) -> None:
        """
        Create a DecodeLimits.

        Args:
            maximum_cells: ``int``. Defaults to ``16000000``.
            maximum_frames: ``int``. Defaults to ``10000``.
            maximum_payload_bytes: ``int``. Defaults to ``268435456``.
        """
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

    Attributes:
        issues: Every problem found, each with its path, message and failing keyword.

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

    Attributes:
        expected_revision: The revision the change was prepared against.
        actual_revision: The revision the store was at when the change was applied.

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

    Attributes:
        path: Where the problem is: object keys are ``str`` and array indexes are ``int``.
        message: A sentence describing the problem and what was expected.
        constraint: The schema keyword that failed, such as ``type`` or ``minimum``.

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

    Attributes:
        revision: The revision of the commit this snapshot was taken at.
        schema: The schema that applies to this snapshot's branch.

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

    Attributes:
        revision: The revision all selected values were read at.
        paths: The paths that were selected, in the order they were requested.

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

    Attributes:
        before_revision: The store revision before the commit.
        revision: The store revision after the commit.
        paths: The paths the commit changed.
        patch: The edits that were applied.
        before: A snapshot of the state before the commit.
        after: A snapshot of the state after the commit.

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

    Attributes:
        is_cancelled: Whether the subscription has been cancelled.

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

    Attributes:
        base_revision: The store revision this transaction started from.

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

    Attributes:
        identity: A number that identifies this store; observations are valid only for their own
            store.
        revision: The number of changes committed to the store so far.
        schema: The schema every commit is validated against.

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
    def __init__(self, value: JSONValue, *, schema: TerminalStateSchema) -> None:
        """
        Create a TerminalStateStore.

        Args:
            value: ``JSONValue``.
            schema: ``TerminalStateSchema``.
        """
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

    Attributes:
        schemas: The schema at each observed path, keyed by JSON Pointer.
        read: The paths that were read.
        write: The paths that may be written.
        revision: The store revision at the time of the observation.
        selection: The values that were read.

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

@overload
def _reference(name: str, kind: Literal['numeric_property']) -> NumericProperty[int]: ...
@overload
def _reference(name: str, kind: Literal['numeric']) -> NumericValue[int | float]: ...
@overload
def _reference(name: str, kind: Literal['property']) -> Property[object]: ...
@overload
def _reference(name: str, kind: Literal['value']) -> Value[JSONValue]: ...
@overload
def _external(name: str, is_numeric: Literal[True]) -> NumericValue[int | float]: ...
@overload
def _external(name: str, is_numeric: Literal[False]) -> Value[JSONValue]: ...
@overload
def _state_expression(
    store: TerminalStateStore, path: StatePath, is_numeric: Literal[True]
) -> NumericValue[int | float]: ...
@overload
def _state_expression(
    store: TerminalStateStore, path: StatePath, is_numeric: Literal[False]
) -> Value[JSONValue]: ...

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
        alignment: The horizontal alignment: ``left``, ``center`` or ``right``.
        should_wrap: Whether long rows wrap at the widget's width.
        should_trim: Whether wrapped rows lose their leading whitespace.
        scroll: A ``(row, column)`` pair of the first row and column shown.
        block: A ``Block`` framing the paragraph. The paragraph follows later edits of the block.
        width: The widget's width in cells. Defaults to 20.
        height: The widget's height in cells. Defaults to 3.
        x: The column in the parent.
        y: The row in the parent.

    Attributes:
        text: The text as it was set, which can be styled or an expression.
        style: The default colors and text modifiers applied to the cells.
        alignment: The horizontal alignment: ``left``, ``center`` or ``right``.
        should_wrap: Whether lines that exceed the available width continue on following rows.
        should_trim: Whether leading whitespace is removed from wrapped lines.
        scroll_row: The first row shown, counted in displayed rows.
        scroll_column: The horizontal scroll offset, in terminal cells.
        block: The optional border, titles and padding around the content.

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
        scroll: tuple[int | Expression[int | float], int | Expression[int | float]]
        | None = None,
        block: Block | None = None,
        width: int | None = None,
        height: int | None = None,
        x: int = 0,
        y: int = 0,
    ) -> None:
        """
        Create a Paragraph.

        Args:
            text: ``TextContent | Expression[str] | None``. Defaults to ``None``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            alignment: ``str | Expression[str] | None``. Defaults to ``None``.
            should_wrap: ``bool | Expression[bool] | None``. Defaults to ``None``.
            should_trim: ``bool | Expression[bool] | None``. Defaults to ``None``.
            scroll: ``tuple[int | Expression[int | float], int | Expression[int | float]] | None``. Defaults to
                ``None``.
            block: ``Block | None``. Defaults to ``None``.
            width: ``int | None``. Defaults to ``None``.
            height: ``int | None``. Defaults to ``None``.
            x: ``int``. Defaults to ``0``.
            y: ``int``. Defaults to ``0``.
        """
    @property
    def text(self) -> TextContent | Expression[str]:  # pyright: ignore[reportIncompatibleMethodOverride]
        """The text as it was set, which can be styled or an expression."""

    @text.setter
    def text(self, value: TextContent | Expression[str]) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the cells."""
    @style.setter
    def style(self, value: Style | DynamicStyle | None) -> None: ...
    @property
    def alignment(self) -> str | Expression[str]:
        """The horizontal alignment: ``left``, ``center`` or ``right``."""
    @alignment.setter
    def alignment(self, value: str | Expression[str]) -> None: ...
    @property
    def should_wrap(self) -> bool | Expression[bool]:
        """Whether lines that exceed the available width continue on following rows."""
    @should_wrap.setter
    def should_wrap(self, value: bool | Expression[bool]) -> None: ...
    @property
    def should_trim(self) -> bool | Expression[bool]:
        """Whether leading whitespace is removed from wrapped lines."""
    @should_trim.setter
    def should_trim(self, value: bool | Expression[bool]) -> None: ...
    @property
    def scroll_row(self) -> int | Expression[int | float]:
        """The first row shown, counted in displayed rows."""

    @scroll_row.setter
    def scroll_row(self, value: int | Expression[int | float]) -> None: ...
    @property
    def scroll_column(self) -> int | Expression[int | float]:
        """The horizontal scroll offset, in terminal cells."""
    @scroll_column.setter
    def scroll_column(self, value: int | Expression[int | float]) -> None: ...
    @property
    def block(self) -> Block | None:
        """The optional border, titles and padding around the content."""
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
    def __deepcopy__(self, memo: object) -> Paragraph: ...

class CustomWidget(Widget):
    """
    A widget drawn by a Python function.

    The function is called as ``render(context, region)`` with an ``EvaluationContext`` and
    a writable ``Buffer`` the size of the widget. Operations applied to ``region`` become the
    widget's cells. It runs again after ``invalidate()``, a resize, a change of a watched
    expression, or every frame when ``redraw`` is ``"always"``.

    Args:
        render: The drawing function.
        redraw: When the drawing function runs: ``on_change`` for changed inputs or ``always`` for every frame.
        watch: Expressions whose changes redraw the widget.
        width: The widget's width in cells. Defaults to 10.
        height: The widget's height in cells. Defaults to 3.
        x: The column in the parent.
        y: The row in the parent.

    Raises:
        RenderError: Raised when the widget is drawn if ``render`` raises; the original
            exception is the ``__cause__``.

    Attributes:
        callback: The drawing function called with the current evaluation context and destination buffer.
        redraw: When the drawing function runs: ``on_change`` for changed inputs or ``always`` for every frame.
        watch: The expressions whose changing values request another draw.

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
        watch: Iterable[ScalarExpression] | None = None,
        width: int | None = None,
        height: int | None = None,
        x: int = 0,
        y: int = 0,
    ) -> None:
        """
        Create a CustomWidget.

        Args:
            render: ``Callable[[EvaluationContext, Buffer], None]``.
            redraw: ``Literal['on_change', 'always']``. Defaults to ``'on_change'``.
            watch: ``Iterable[ScalarExpression] | None``. Defaults to ``None``.
            width: ``int | None``. Defaults to ``None``.
            height: ``int | None``. Defaults to ``None``.
            x: ``int``. Defaults to ``0``.
            y: ``int``. Defaults to ``0``.
        """
    @property
    def callback(self) -> Callable[[EvaluationContext, Buffer], None]:
        """The drawing function called with the current evaluation context and destination buffer."""
    @callback.setter
    def callback(self, value: Callable[[EvaluationContext, Buffer], None]) -> None: ...
    @property
    def redraw(self) -> Literal['on_change', 'always']:
        """When the drawing function runs: ``on_change`` for changed inputs or ``always`` for every frame."""
    @redraw.setter
    def redraw(self, value: Literal['on_change', 'always']) -> None: ...
    @property
    def watch(self) -> tuple[ScalarExpression, ...]:
        """The expressions whose changing values request another draw."""
    @watch.setter
    def watch(self, value: Iterable[ScalarExpression]) -> None: ...
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
    def __deepcopy__(self, memo: object) -> CustomWidget: ...

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

    Attributes:
        operations: The operations applied in order whenever this widget redraws.
        watch: The expressions whose changing values request another draw.

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
        watch: Iterable[ScalarExpression] | None = None,
        width: int | None = None,
        height: int | None = None,
        x: int = 0,
        y: int = 0,
    ) -> None:
        """
        Create a Live.

        Args:
            watch: ``Iterable[ScalarExpression] | None``. Defaults to ``None``.
            width: ``int | None``. Defaults to ``None``.
            height: ``int | None``. Defaults to ``None``.
            x: ``int``. Defaults to ``0``.
            y: ``int``. Defaults to ``0``.
        """
    @property
    def operations(self) -> tuple[Operation, ...]:
        """The operations applied in order whenever this widget redraws."""
    @operations.setter
    def operations(self, value: Iterable[Operation]) -> None: ...
    @property
    def watch(self) -> tuple[ScalarExpression, ...]:
        """The expressions whose changing values request another draw."""
    @watch.setter
    def watch(self, value: Iterable[ScalarExpression]) -> None: ...
    def invalidate(self, area: Rectangle | None = None) -> None: ...
    def copy(self) -> Live: ...
    def __copy__(self) -> Live: ...
    def __deepcopy__(self, memo: object) -> Live: ...

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

    Attributes:
        x1: The horizontal coordinate of the starting point.
        y1: The vertical coordinate of the starting point.
        x2: The horizontal coordinate of the ending point.
        y2: The vertical coordinate of the ending point.
        color: The color of the line.
        fill_to_y: The vertical coordinate to fill toward, or ``None`` to draw only the line.

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
    ) -> None:
        """
        Create a CanvasLine.

        Args:
            x1: ``float | Value[float]``.
            y1: ``float | Value[float]``.
            x2: ``float | Value[float]``.
            y2: ``float | Value[float]``.
            color: ``ColorValue | None``. Defaults to ``None``.
            fill_to_y: ``float | Value[float] | None``. Defaults to ``None``.
        """
    x1: float | Value[float]
    """The horizontal coordinate of the starting point."""
    y1: float | Value[float]
    """The vertical coordinate of the starting point."""
    x2: float | Value[float]
    """The horizontal coordinate of the ending point."""
    y2: float | Value[float]
    """The vertical coordinate of the ending point."""
    color: Color | Value[Color]
    """The color of the line."""
    fill_to_y: float | Value[float] | None
    """The vertical coordinate to fill toward, or ``None`` to draw only the line."""
    def __copy__(self) -> CanvasLine: ...
    def __deepcopy__(self, memo: object) -> CanvasLine: ...

class CanvasRectangle:
    """
    An axis-aligned rectangle outline.

    Args:
        x: Horizontal position of the lower-left corner.
        y: Vertical position of the lower-left corner.
        width: Width in canvas units.
        height: Height in canvas units.
        color: A color name, ``Color`` or expression.

    Attributes:
        x: The horizontal coordinate of the left edge.
        y: The vertical coordinate of the bottom edge.
        width: The width in canvas coordinates.
        height: The height in canvas coordinates.
        color: The color of the rectangle outline.

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
    ) -> None:
        """
        Create a CanvasRectangle.

        Args:
            x: ``float | Value[float]``.
            y: ``float | Value[float]``.
            width: ``float | Value[float]``.
            height: ``float | Value[float]``.
            color: ``ColorValue | None``. Defaults to ``None``.
        """
    x: float | Value[float]
    """The horizontal coordinate of the left edge."""
    y: float | Value[float]
    """The vertical coordinate of the bottom edge."""
    width: float | Value[float]
    """The width in canvas coordinates."""
    height: float | Value[float]
    """The height in canvas coordinates."""
    color: Color | Value[Color]
    """The color of the rectangle outline."""
    def __copy__(self) -> CanvasRectangle: ...
    def __deepcopy__(self, memo: object) -> CanvasRectangle: ...

class CanvasCircle:
    """
    A circle outline.

    Args:
        x: Horizontal position of the center.
        y: Vertical position of the center.
        radius: Radius in canvas units.
        color: A color name, ``Color`` or expression.

    Attributes:
        x: The horizontal coordinate of the center.
        y: The vertical coordinate of the center.
        radius: The radius in canvas coordinates.
        color: The color of the circle outline.

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
    ) -> None:
        """
        Create a CanvasCircle.

        Args:
            x: ``float | Value[float]``.
            y: ``float | Value[float]``.
            radius: ``float | Value[float]``.
            color: ``ColorValue | None``. Defaults to ``None``.
        """
    x: float | Value[float]
    """The horizontal coordinate of the center."""
    y: float | Value[float]
    """The vertical coordinate of the center."""
    radius: float | Value[float]
    """The radius in canvas coordinates."""
    color: Color | Value[Color]
    """The color of the circle outline."""
    def __copy__(self) -> CanvasCircle: ...
    def __deepcopy__(self, memo: object) -> CanvasCircle: ...

class CanvasPoints:
    """
    A set of single points.

    Args:
        coordinates: The horizontal and vertical coordinate pairs to draw.
        color: A color name, ``Color`` or expression.

    Raises:
        ValueError: A coordinate is not finite.

    Attributes:
        coordinates: The horizontal and vertical coordinate pairs to draw.
        color: The color of the points.

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
    ) -> None:
        """
        Create a CanvasPoints.

        Args:
            coordinates: ``Iterable[tuple[float, float]]``.
            color: ``ColorValue | None``. Defaults to ``None``.
        """
    coordinates: list[tuple[float, float]]
    """The horizontal and vertical coordinate pairs to draw."""
    color: Color | Value[Color]
    """The color of the points."""
    def __len__(self) -> int: ...
    def __copy__(self) -> CanvasPoints: ...
    def __deepcopy__(self, memo: object) -> CanvasPoints: ...

class CanvasMap:
    """
    The world map, in longitude and latitude (use bounds ``(-180, 180)`` and ``(-90, 90)``).

    Args:
        resolution: The detail level of the world map: ``low`` or ``high``.
        color: A color name, ``Color`` or expression.

    Raises:
        ValueError: The resolution is not ``'low'`` or ``'high'``.

    Attributes:
        resolution: The detail level of the world map: ``low`` or ``high``.
        color: The color of the map outline.

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
    ) -> None:
        """
        Create a CanvasMap.

        Args:
            resolution: ``Literal['low', 'high'] | str | Value[str] | None``. Defaults to
                ``None``.
            color: ``ColorValue | None``. Defaults to ``None``.
        """
    resolution: str | Value[str]
    """The detail level of the world map: ``low`` or ``high``."""
    color: Color | Value[Color]
    """The color of the map outline."""
    def __copy__(self) -> CanvasMap: ...
    def __deepcopy__(self, memo: object) -> CanvasMap: ...

class CanvasLabel:
    """
    Text printed at a position, always on top of the shapes.

    Args:
        x: Horizontal position of the text start.
        y: Vertical position of the text.
        text: The text, or an expression producing it.
        style: A ``Style`` or ``DynamicStyle``.

    Attributes:
        x: The horizontal coordinate where the label starts.
        y: The vertical coordinate where the label starts.
        text: The styled text displayed at the given canvas position.
        style: The default colors and text modifiers applied to the cells.

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
    ) -> None:
        """
        Create a CanvasLabel.

        Args:
            x: ``float | Value[float]``.
            y: ``float | Value[float]``.
            text: ``str | Value[str]``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
        """
    x: float | Value[float]
    """The horizontal coordinate where the label starts."""
    y: float | Value[float]
    """The vertical coordinate where the label starts."""
    text: str | Value[str]
    """The styled text displayed at the given canvas position."""
    style: Style | DynamicStyle
    """The default colors and text modifiers applied to the cells."""
    def __copy__(self) -> CanvasLabel: ...
    def __deepcopy__(self, memo: object) -> CanvasLabel: ...

class CanvasLayer:
    """
    Saves what was drawn so far as a layer; the shapes after it draw on top.

    Examples:
        ```python
        canvas = Canvas((0, 10), (0, 10), shapes=[CanvasPoints([(1, 1)]), CanvasLayer(), CanvasPoints([(9, 9)])])
        assert CanvasLayer() == CanvasLayer()
        ```
    """

    def __init__(self) -> None:
        """
        Create a CanvasLayer.
        """
    def __hash__(self) -> int: ...
    def __copy__(self) -> CanvasLayer: ...
    def __deepcopy__(self, memo: object) -> CanvasLayer: ...

class CanvasMarker:
    """
    Switches the marker the shapes after it are drawn with.

    Args:
        marker: A marker name (``'dot'``, ``'block'``, ``'bar'``, ``'braille'``, ``'half_block'``,
            ``'quadrant'``, ``'sextant'``, ``'octant'``) or any single character.

    Raises:
        ValueError: The marker is not a known name or a single character.

    Attributes:
        marker: The named cell marker used for subsequent shapes.

    Examples:
        ```python
        canvas = Canvas((0, 10), (0, 10), shapes=[CanvasMarker('block'), CanvasRectangle(0, 0, 10, 10)], width=10, height=5)
        assert '█' in canvas.render(format='text')
        ```
    """

    def __init__(self, marker: str | Value[str]) -> None:
        """
        Create a CanvasMarker.

        Args:
            marker: ``str | Value[str]``.
        """
    marker: str | Value[str]
    """The named cell marker used for subsequent shapes."""
    def __copy__(self) -> CanvasMarker: ...
    def __deepcopy__(self, memo: object) -> CanvasMarker: ...

class Canvas(Widget):
    """
    A coordinate plane that shapes, points and labels are drawn on.

    Maps to [`ratatui::widgets::canvas::Canvas`](https://docs.rs/ratatui/0.30.0/ratatui/widgets/canvas/struct.Canvas.html).

    Args:
        x_bounds: The lower and upper horizontal coordinates visible on the canvas.
        y_bounds: The lower and upper vertical coordinates visible on the canvas.
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

    Attributes:
        x_bounds: The lower and upper horizontal coordinates visible on the canvas.
        y_bounds: The lower and upper vertical coordinates visible on the canvas.
        marker: The default cell marker used to draw shapes.
        background_color: The color filling the canvas behind its shapes.
        shapes: The shapes and labels drawn in sequence order.
        block: The optional border, titles and padding around the content.

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
    ) -> None:
        """
        Create a Canvas.

        Args:
            x_bounds: ``Sequence[float | Value[float]] | None``. Defaults to ``None``.
            y_bounds: ``Sequence[float | Value[float]] | None``. Defaults to ``None``.
            marker: ``str | Value[str] | None``. Defaults to ``None``.
            background_color: ``ColorValue | None``. Defaults to ``None``.
            shapes: ``Iterable[CanvasLine | CanvasRectangle | CanvasCircle | CanvasPoints |
                CanvasMap | CanvasLabel | CanvasLayer | CanvasMarker] | None``. Defaults to
                ``None``.
            block: ``Block | None``. Defaults to ``None``.
            width: ``int | None``. Defaults to ``None``.
            height: ``int | None``. Defaults to ``None``.
            x: ``int``. Defaults to ``0``.
            y: ``int``. Defaults to ``0``.
        """
    x_bounds: tuple[float | Value[float], float | Value[float]]
    """The lower and upper horizontal coordinates visible on the canvas."""
    y_bounds: tuple[float | Value[float], float | Value[float]]
    """The lower and upper vertical coordinates visible on the canvas."""
    marker: str | Value[str]
    """The default cell marker used to draw shapes."""
    background_color: Color | Value[Color] | None
    """The color filling the canvas behind its shapes."""
    shapes: list[CanvasShape]
    """The shapes and labels drawn in sequence order."""
    block: Block | None
    """The optional border, titles and padding around the content."""
    def add_shape(self, shape: CanvasShape) -> None:
        """
        Draw ``shape`` after the shapes already on the canvas.

        Examples:
            ```python
            canvas = Canvas((0, 10), (0, 10), width=10, height=5)
            canvas.add_shape(CanvasCircle(5, 5, 2))
            assert len(canvas.shapes) == 1
            ```
        """

    def extend_shapes(self, shapes: Iterable[CanvasShape]) -> None:
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

    Attributes:
        style: The default colors and text modifiers applied to the cells.
        alignment: The horizontal title alignment, or ``None`` to use the block setting.
        text: The text displayed on the block border.
        position: The border holding this title: ``top`` or ``bottom``.

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
    ) -> None:
        """
        Create a BlockTitle.

        Args:
            text: ``TextContent | Expression[str]``.
            position: ``str``. Defaults to ``'top'``.
            alignment: ``str | Expression[str] | None``. Defaults to ``None``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
        """
    @property
    def style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the cells."""
    @property
    def alignment(self) -> str | Expression[str]:
        """The horizontal title alignment, or ``None`` to use the block setting."""
    @property
    def text(self) -> TextContent | Expression[str]:
        """The text displayed on the block border."""
    @property
    def position(self) -> int | Expression[int | float]:
        """The border holding this title: ``top`` or ``bottom``."""

class Block(Widget):
    """
    Borders, titles and padding shared by retained widgets.

    Attributes:
        border_type: The named border-symbol style, such as ``plain``, ``rounded`` or ``double``.
        title_alignment: The default horizontal alignment of titles: ``left``, ``center`` or ``right``.
        border_style: The colors and text modifiers applied to the border.
        title_style: The default colors and text modifiers applied to titles.
        padding: The inner spacing in cells: one value for every edge or a tuple of left, right, top and bottom values.
        merge: The border-merging policy used where this block meets another border.
        style: The default colors and text modifiers applied to the cells.
        titles: The titles placed on the block border, in sequence order.
        borders: The edges on which borders are drawn.

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
        | Expression[int | float]
        | tuple[
            int | Expression[int | float],
            int | Expression[int | float],
            int | Expression[int | float],
            int | Expression[int | float],
        ]
        | None = None,
        merge: str | Expression[str] | None = None,
        width: int | Expression[int | float] | None = None,
        height: int | Expression[int | float] | None = None,
        x: int | Expression[int | float] = 0,
        y: int | Expression[int | float] = 0,
    ) -> None:
        """
        Create a Block.

        Args:
            title: ``str | Expression[str] | None``. Defaults to ``None``.
            borders: ``str | Sequence[str] | None``. Defaults to ``None``.
            border_type: ``str | Expression[str] | None``. Defaults to ``None``.
            border_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            title_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            title_alignment: ``str``. Defaults to ``'left'``.
            padding: ``int | Expression[int | float] | tuple[int | Expression[int | float], int |
                Expression[int | float], int | Expression[int | float], int | Expression[int | float]] | None``.
                Defaults to ``None``.
            merge: ``str | Expression[str] | None``. Defaults to ``None``.
            width: ``int | Expression[int | float] | None``. Defaults to ``None``.
            height: ``int | Expression[int | float] | None``. Defaults to ``None``.
            x: ``int | Expression[int | float]``. Defaults to ``0``.
            y: ``int | Expression[int | float]``. Defaults to ``0``.
        """
    def __repr__(self, /) -> str: ...
    @property
    def border_type(self) -> str | Expression[str]:
        """The named border-symbol style, such as ``plain``, ``rounded`` or ``double``."""
    @border_type.setter
    def border_type(self, value: str | Expression[str]) -> None: ...
    @property
    def title_alignment(self) -> str | Expression[str]:
        """The default horizontal alignment of titles: ``left``, ``center`` or ``right``."""
    @title_alignment.setter
    def title_alignment(self, value: str | Expression[str]) -> None: ...
    @property
    def border_style(self) -> Style | DynamicStyle:
        """The colors and text modifiers applied to the border."""
    @border_style.setter
    def border_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def title_style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to titles."""
    @title_style.setter
    def title_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def padding(
        self,
    ) -> (
        int
        | Expression[int | float]
        | tuple[
            int | Expression[int | float],
            int | Expression[int | float],
            int | Expression[int | float],
            int | Expression[int | float],
        ]
    ):
        """The inner spacing in cells: one value for every edge or a tuple of left, right, top and bottom values."""
    @padding.setter
    def padding(
        self,
        value: int
        | Expression[int | float]
        | tuple[
            int | Expression[int | float],
            int | Expression[int | float],
            int | Expression[int | float],
            int | Expression[int | float],
        ],
    ) -> None: ...
    @property
    def merge(self) -> str | Expression[str]:
        """The border-merging policy used where this block meets another border."""
    @merge.setter
    def merge(self, value: str | Expression[str]) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the cells."""
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def titles(self) -> Sequence[BlockTitle | str]:
        """The titles placed on the block border, in sequence order."""
    @titles.setter
    def titles(self, value: Sequence[BlockTitle | str]) -> None: ...
    @property
    def borders(self) -> str | Sequence[str]:
        """The edges on which borders are drawn."""
    @borders.setter
    def borders(self, value: str | Sequence[str]) -> None: ...

class DynamicStyle:
    """
    A style whose colors may follow expressions.

    Attributes:
        foreground: The text color, or ``None`` to leave the foreground unchanged.
        background: The background color, or ``None`` to leave the background unchanged.

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
    ) -> None:
        """
        Create a DynamicStyle.

        Args:
            foreground: ``ColorValue | Expression[ColorValue] | None``. Defaults to ``None``.
            background: ``ColorValue | Expression[ColorValue] | None``. Defaults to ``None``.
            underline_color: ``ColorValue | Expression[ColorValue] | None``. Defaults to
                ``None``.
            modifiers: ``Sequence[str] | None``. Defaults to ``None``.
        """
    def __repr__(self, /) -> str: ...
    @property
    def foreground(self) -> ColorValue | Expression[ColorValue] | None:
        """The text color, or ``None`` to leave the foreground unchanged."""
    @foreground.setter
    def foreground(self, value: ColorValue | Expression[ColorValue] | None) -> None: ...
    @property
    def background(self) -> ColorValue | Expression[ColorValue] | None:
        """The background color, or ``None`` to leave the background unchanged."""
    @background.setter
    def background(self, value: ColorValue | Expression[ColorValue] | None) -> None: ...

class ListItem:
    """
    Styled content displayed by an item list.

    Attributes:
        height: The number of terminal rows occupied by this item.
        style: The default colors and text modifiers applied to the cells.
        content: The styled text displayed by this item.

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
    ) -> None:
        """
        Create a ListItem.

        Args:
            content: ``TextContent | Expression[str]``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
        """
    def __repr__(self, /) -> str: ...
    def __hash__(self, /) -> int: ...
    def __eq__(self, value: object, /) -> bool: ...
    def __copy__(self, /) -> ListItem: ...
    def __deepcopy__(self, /, _memo: dict[int, object]) -> ListItem: ...
    @property
    def height(self) -> int | Expression[int | float]:
        """The number of terminal rows occupied by this item."""
    @height.setter
    def height(self, value: int | Expression[int | float]) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the cells."""
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def content(self) -> TextContent | Expression[str]:
        """The styled text displayed by this item."""
    @content.setter
    def content(self, value: TextContent | Expression[str]) -> None: ...

class SparklineBar:
    """
    A sample with an optional individual style.

    Attributes:
        value: The nonnegative numeric value represented by the bar.
        style: The default colors and text modifiers applied to the cells.

    Examples:
        ```python
        bar = SparklineBar(3)
        assert bar.value == 3
        ```
    """

    def __init__(
        self,
        /,
        value: int | Expression[int | float],
        style: Style | DynamicStyle | None = None,
    ) -> None:
        """
        Create a SparklineBar.

        Args:
            value: ``int | Expression[int | float]``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
        """
    def __repr__(self, /) -> str: ...
    def __hash__(self, /) -> int: ...
    def __eq__(self, value: object, /) -> bool: ...
    def __copy__(self, /) -> SparklineBar: ...
    def __deepcopy__(self, /, _memo: dict[int, object]) -> SparklineBar: ...
    @property
    def value(self) -> int | Expression[int | float]:
        """The nonnegative numeric value represented by the bar."""
    @property
    def style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the cells."""

class ChartAxis:
    """
    An editable axis with bounds, labels and a title.

    Attributes:
        labels: The text labels spaced across the axis range.
        style: The default colors and text modifiers applied to the cells.
        labels_alignment: The horizontal alignment used when drawing axis labels.
        title: The optional text displayed as the axis title.
        bounds: The lower and upper coordinate values represented by the axis.

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
        bounds: tuple[float | Expression[int | float], float | Expression[int | float]]
        | None = None,
        labels: Sequence[str | Expression[str]] | None = None,
        style: Style | DynamicStyle | None = None,
        labels_alignment: str | Expression[str] | None = None,
    ) -> None:
        """
        Create a ChartAxis.

        Args:
            title: ``str | Expression[str] | None``. Defaults to ``None``.
            bounds: ``tuple[float | Expression[int | float], float | Expression[int | float]] | None``.
                Defaults to ``None``.
            labels: ``Sequence[str | Expression[str]] | None``. Defaults to ``None``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            labels_alignment: ``str | Expression[str] | None``. Defaults to ``None``.
        """
    def __repr__(self, /) -> str: ...
    def __eq__(self, value: object, /) -> bool: ...
    def __copy__(self, /) -> ChartAxis: ...
    def __deepcopy__(self, /, _memo: dict[int, object]) -> ChartAxis: ...
    @property
    def labels(self) -> Sequence[str | Expression[str]]:
        """The text labels spaced across the axis range."""
    @labels.setter
    def labels(self, value: Sequence[str | Expression[str]]) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the cells."""
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def labels_alignment(self) -> str | Expression[str]:
        """The horizontal alignment used when drawing axis labels."""
    @labels_alignment.setter
    def labels_alignment(self, value: str | Expression[str]) -> None: ...
    @property
    def title(self) -> str | Expression[str] | None:
        """The optional text displayed as the axis title."""
    @title.setter
    def title(self, value: str | Expression[str] | None) -> None: ...
    @property
    def bounds(
        self,
    ) -> tuple[float | Expression[int | float], float | Expression[int | float]]:
        """The lower and upper coordinate values represented by the axis."""
    @bounds.setter
    def bounds(
        self,
        value: tuple[float | Expression[int | float], float | Expression[int | float]],
    ) -> None: ...

class ChartDataset:
    """
    An editable series of points displayed by a chart.

    Attributes:
        marker: The named cell marker used to plot points.
        style: The default colors and text modifiers applied to the cells.
        fill_to_y: The vertical coordinate to which area plots are filled.
        data: The horizontal and vertical coordinate pairs to plot.
        graph_type: The way the points are drawn: ``scatter``, ``line`` or ``area``.
        name: The optional dataset label displayed in the legend.

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
        fill_to_y: float | Expression[int | float] | None = None,
    ) -> None:
        """
        Create a ChartDataset.

        Args:
            name: ``str | Expression[str] | None``. Defaults to ``None``.
            data: ``Sequence[tuple[float, float]] | None``. Defaults to ``None``.
            marker: ``str | Expression[str] | None``. Defaults to ``None``.
            graph_type: ``str | Expression[str] | None``. Defaults to ``None``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            fill_to_y: ``float | Expression[int | float] | None``. Defaults to ``None``.
        """
    def __repr__(self, /) -> str: ...
    def __eq__(self, value: object, /) -> bool: ...
    def __copy__(self, /) -> ChartDataset: ...
    def __deepcopy__(self, /, _memo: dict[int, object]) -> ChartDataset: ...
    @property
    def marker(self) -> str | Expression[str]:
        """The named cell marker used to plot points."""
    @marker.setter
    def marker(self, value: str | Expression[str]) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the cells."""
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def fill_to_y(self) -> float | Expression[int | float]:
        """The vertical coordinate to which area plots are filled."""
    @fill_to_y.setter
    def fill_to_y(self, value: float | Expression[int | float]) -> None: ...
    @property
    def data(self) -> Sequence[tuple[float, float]]:
        """The horizontal and vertical coordinate pairs to plot."""
    @data.setter
    def data(self, value: Sequence[tuple[float, float]]) -> None: ...
    @property
    def graph_type(self) -> str | Expression[str]:
        """The way the points are drawn: ``scatter``, ``line`` or ``area``."""
    @graph_type.setter
    def graph_type(self, value: str | Expression[str]) -> None: ...
    @property
    def name(self) -> str | Expression[str] | None:
        """The optional dataset label displayed in the legend."""
    @name.setter
    def name(self, value: str | Expression[str] | None) -> None: ...

class Chart(Widget):
    """
    Point series drawn against shared editable axes.

    Attributes:
        datasets: The datasets plotted against the chart axes.
        style: The default colors and text modifiers applied to the cells.
        y_axis: The vertical axis and its bounds, labels and title.
        block: The optional border, titles and padding around the content.
        legend_position: The named position of the legend, or ``None`` to omit it.
        x_axis: The horizontal axis and its bounds, labels and title.

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
        legend_position: str | Expression[str] | None = None,
        block: Block | None = None,
        width: int | Expression[int | float] | None = None,
        height: int | Expression[int | float] | None = None,
        x: int | Expression[int | float] = 0,
        y: int | Expression[int | float] = 0,
    ) -> None:
        """
        Create a Chart.

        Args:
            datasets: ``Sequence[ChartDataset] | None``. Defaults to ``None``.
            x_axis: ``ChartAxis | None``. Defaults to ``None``.
            y_axis: ``ChartAxis | None``. Defaults to ``None``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            legend_position: ``str | Expression[str] | None``. Defaults to ``None``.
            block: ``Block | None``. Defaults to ``None``.
            width: ``int | Expression[int | float] | None``. Defaults to ``None``.
            height: ``int | Expression[int | float] | None``. Defaults to ``None``.
            x: ``int | Expression[int | float]``. Defaults to ``0``.
            y: ``int | Expression[int | float]``. Defaults to ``0``.
        """
    def __repr__(self, /) -> str: ...
    @property
    def datasets(self) -> Sequence[ChartDataset]:
        """The datasets plotted against the chart axes."""
    @datasets.setter
    def datasets(self, value: Sequence[ChartDataset]) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the cells."""
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def y_axis(self) -> ChartAxis:
        """The vertical axis and its bounds, labels and title."""
    @y_axis.setter
    def y_axis(self, value: ChartAxis) -> None: ...
    @property
    def block(self) -> Block | None:
        """The optional border, titles and padding around the content."""
    @block.setter
    def block(self, value: Block | None) -> None: ...
    @property
    def legend_position(self) -> str | Expression[str] | None:
        """The named position of the legend, or ``None`` to omit it."""
    @legend_position.setter
    def legend_position(self, value: str | Expression[str] | None) -> None: ...
    @property
    def x_axis(self) -> ChartAxis:
        """The horizontal axis and its bounds, labels and title."""
    @x_axis.setter
    def x_axis(self, value: ChartAxis) -> None: ...

class Calendar(Widget):
    """
    A monthly calendar with editable dates and styles for events.

    Attributes:
        weekdays_header_style: The colors and text modifiers applied to the weekday headings.
        events: The styles applied to dates, keyed by year, month and day.
        day: The day of the month selected by the calendar date.
        year: The year of the displayed calendar month.
        month_header_style: The colors and text modifiers applied to the month heading.
        block: The optional border, titles and padding around the content.
        style: The default colors and text modifiers applied to the cells.
        surrounding_style: The colors and text modifiers applied to dates outside the displayed month.
        month: The displayed month number, from ``1`` for January to ``12`` for December.

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
        year: int | Expression[int | float],
        month: int | Expression[int | float],
        day: int | Expression[int | float] | None = None,
        *,
        events: Mapping[tuple[int, int, int], Style | DynamicStyle] | None = None,
        style: Style | DynamicStyle | None = None,
        surrounding_style: Style | DynamicStyle | None = None,
        weekdays_header_style: Style | DynamicStyle | None = None,
        month_header_style: Style | DynamicStyle | None = None,
        block: Block | None = None,
        width: int | Expression[int | float] | None = None,
        height: int | Expression[int | float] | None = None,
        x: int | Expression[int | float] = 0,
        y: int | Expression[int | float] = 0,
    ) -> None:
        """
        Create a Calendar.

        Args:
            year: ``int | Expression[int | float]``.
            month: ``int | Expression[int | float]``.
            day: ``int | Expression[int | float] | None``. Defaults to ``None``.
            events: ``Mapping[tuple[int, int, int], Style | DynamicStyle] | None``. Defaults to
                ``None``.
            style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            surrounding_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            weekdays_header_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            month_header_style: ``Style | DynamicStyle | None``. Defaults to ``None``.
            block: ``Block | None``. Defaults to ``None``.
            width: ``int | Expression[int | float] | None``. Defaults to ``None``.
            height: ``int | Expression[int | float] | None``. Defaults to ``None``.
            x: ``int | Expression[int | float]``. Defaults to ``0``.
            y: ``int | Expression[int | float]``. Defaults to ``0``.
        """
    def __repr__(self, /) -> str: ...
    def copy(self, /) -> Calendar: ...
    def __copy__(self, /) -> Calendar: ...
    def __deepcopy__(self, /, _memo: dict[int, object]) -> Calendar: ...
    @property
    def weekdays_header_style(self) -> Style | DynamicStyle:
        """The colors and text modifiers applied to the weekday headings."""
    @weekdays_header_style.setter
    def weekdays_header_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def events(self) -> Mapping[tuple[int, int, int], Style | DynamicStyle]:
        """The styles applied to dates, keyed by year, month and day."""
    @events.setter
    def events(
        self, value: Mapping[tuple[int, int, int], Style | DynamicStyle]
    ) -> None: ...
    @property
    def day(self) -> int | Expression[int | float]:
        """The day of the month selected by the calendar date."""
    @day.setter
    def day(self, value: int | Expression[int | float]) -> None: ...
    @property
    def year(self) -> int | Expression[int | float]:
        """The year of the displayed calendar month."""
    @year.setter
    def year(self, value: int | Expression[int | float]) -> None: ...
    @property
    def month_header_style(self) -> Style | DynamicStyle:
        """The colors and text modifiers applied to the month heading."""
    @month_header_style.setter
    def month_header_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def block(self) -> Block | None:
        """The optional border, titles and padding around the content."""
    @block.setter
    def block(self, value: Block | None) -> None: ...
    @property
    def style(self) -> Style | DynamicStyle:
        """The default colors and text modifiers applied to the cells."""
    @style.setter
    def style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def surrounding_style(self) -> Style | DynamicStyle:
        """The colors and text modifiers applied to dates outside the displayed month."""
    @surrounding_style.setter
    def surrounding_style(self, value: Style | DynamicStyle) -> None: ...
    @property
    def month(self) -> int | Expression[int | float]:
        """The displayed month number, from ``1`` for January to ``12`` for December."""
    @month.setter
    def month(self, value: int | Expression[int | float]) -> None: ...

class StateReference(Generic[StateType]):
    """
    A branch of a state store that can be read, written or bound.

    Attributes:
        value: An expression that reads the value at this state path.
        store: The state store containing this branch.
        revision: The current revision of the whole state store.
        branch_revision: The most recent revision affecting this branch.
        number: A numeric expression reading this branch, for arithmetic and comparisons.
        native_store: The state store containing this branch.
        schema: The validation schema for the state store.
        path: The sequence of object keys and array indexes locating this branch.

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
    ) -> None:
        """
        Create a StateReference.

        Args:
            store: ``TerminalStateStore``.
            path: ``StatePath | None``. Defaults to ``None``.
        """
    def __repr__(self, /) -> str: ...
    def __hash__(self, /) -> int: ...
    def __eq__(self, value: object, /) -> bool: ...
    def __copy__(self, /) -> StateReference: ...
    def __deepcopy__(self, /, _memo: dict[int, object]) -> StateReference: ...
    def exists(self, /) -> bool: ...
    def get(self, /) -> JSONValue: ...
    def set(
        self,
        /,
        value: JSONValue,
        *,
        expected_revision: int | Expression[int | float] | None = None,
    ) -> TerminalStateChange | None: ...
    def update(
        self,
        /,
        patch: TerminalStatePatch,
        *,
        expected_revision: int | Expression[int | float] | None = None,
    ) -> TerminalStateChange | None: ...
    @property
    def value(self) -> Value[JSONValue]:
        """An expression that reads the value at this state path."""
    @property
    def store(self) -> TerminalStateStore:
        """The state store containing this branch."""
    @property
    def revision(self) -> int:
        """The current revision of the whole state store."""
    @property
    def branch_revision(self) -> int:
        """The most recent revision affecting this branch."""
    @property
    def number(self) -> NumericValue[int | float]:
        """A numeric expression reading this branch, for arithmetic and comparisons."""
    @property
    def native_store(self) -> TerminalStateStore:
        """The state store containing this branch."""
    @property
    def schema(self) -> TerminalStateSchema:
        """The validation schema for the state store."""
    @property
    def path(self) -> StatePath:
        """The sequence of object keys and array indexes locating this branch."""
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
    def __eq__(self, value: object, /) -> bool: ...
    def __invert__(self, /) -> CellFilter: ...
    def __and__(self, value: CellFilter, /) -> CellFilter: ...
    def __or__(self, value: CellFilter, /) -> CellFilter: ...
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
        horizontal: int | Expression[int | float] = 1,
        vertical: int | Expression[int | float] = 1,
    ) -> CellFilter: ...
    @staticmethod
    def outer(
        horizontal: int | Expression[int | float] = 1,
        vertical: int | Expression[int | float] = 1,
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
    def __deepcopy__(self, /, _memo: dict[int, object]) -> CellFilter: ...

class RunningEffect:
    """
    Playback controls and progress for a started animation.

    Attributes:
        progress: The timer progress from ``0.0`` to ``1.0``, or ``None`` when the effect has no timer.
        is_paused: Whether the effect is paused without advancing its elapsed time.
        effect: The effect whose settings control this running animation.
        error: The reason the effect failed, or ``None`` when it has not failed.
        elapsed_milliseconds: The amount of time the effect has advanced, in milliseconds.
        is_done: Whether the effect has finished or been cancelled.
        key: The optional name under which this running effect can be found or cancelled.

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
    def progress(self) -> float | Expression[int | float] | None:
        """The timer progress from ``0.0`` to ``1.0``, or ``None`` when the effect has no timer."""
    @property
    def is_paused(self) -> bool | Expression[bool]:
        """Whether the effect is paused without advancing its elapsed time."""
    @property
    def effect(self) -> Effect:
        """The effect whose settings control this running animation."""
    @property
    def error(self) -> str | None:
        """The reason the effect failed, or ``None`` when it has not failed."""
    @property
    def elapsed_milliseconds(self) -> int:
        """The amount of time the effect has advanced, in milliseconds."""
    @property
    def is_done(self) -> bool | Expression[bool]:
        """Whether the effect has finished or been cancelled."""
    @property
    def key(self) -> str | None:
        """The optional name under which this running effect can be found or cancelled."""

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

    Attributes:
        y: The vertical displacement, in terminal cells.
        x: The horizontal displacement, in terminal cells.

    Examples:
        ```python
        assert Offset(1, 2) == Offset(1, 2)
        ```
    """

    def __init__(
        self,
        /,
        x: int | Expression[int | float] = 0,
        y: int | Expression[int | float] = 0,
    ) -> None:
        """
        Create a Offset.

        Args:
            x: ``int | Expression[int | float]``. Defaults to ``0``.
            y: ``int | Expression[int | float]``. Defaults to ``0``.
        """
    def __repr__(self, /) -> str: ...
    def __hash__(self, /) -> int: ...
    def __eq__(self, value: object, /) -> bool: ...
    def __len__(self, /) -> int: ...
    def __copy__(self, /) -> Offset: ...
    def __deepcopy__(self, /, _memo: dict[int, object]) -> Offset: ...
    @property
    def y(self) -> int:
        """The vertical displacement, in terminal cells."""
    @property
    def x(self) -> int:
        """The horizontal displacement, in terminal cells."""
    def __add__(self, other: Offset) -> Offset: ...
    def __sub__(self, other: Offset) -> Offset: ...
    def __neg__(self) -> Offset: ...
    def __mul__(self, factor: int) -> Offset: ...
    def __rmul__(self, factor: int) -> Offset: ...

class Margin:
    """
    Horizontal and vertical inset distances.

    Attributes:
        vertical: The number of cells inset from the top and bottom edges.
        horizontal: The number of cells inset from the left and right edges.

    Examples:
        ```python
        assert Margin(1, 2).horizontal == 1
        ```
    """

    def __init__(
        self,
        /,
        horizontal: int | Expression[int | float] = 0,
        vertical: int | Expression[int | float] = 0,
    ) -> None:
        """
        Create a Margin.

        Args:
            horizontal: ``int | Expression[int | float]``. Defaults to ``0``.
            vertical: ``int | Expression[int | float]``. Defaults to ``0``.
        """
    def __repr__(self, /) -> str: ...
    def __hash__(self, /) -> int: ...
    def __eq__(self, value: object, /) -> bool: ...
    def __len__(self, /) -> int: ...
    def __copy__(self, /) -> Margin: ...
    def __deepcopy__(self, /, _memo: dict[int, object]) -> Margin: ...
    @property
    def vertical(self) -> int:
        """The number of cells inset from the top and bottom edges."""
    @property
    def horizontal(self) -> int:
        """The number of cells inset from the left and right edges."""

class Customization(Operation):
    """
    A named, typed set of parameters that is also an operation.

    ``Customization('style', bold=True)`` names what to change and how. It applies like any
    other operation (``buffer.update(customization)``, ``buffer | customization``) and
    sequences with other operations through ``|`` and ``then``. Its parameters are read when it
    is used, so a subclass that keeps them as attributes can be edited after it is created.

    The kinds are ``'style'``, ``'border'``, ``'block'``, ``'padding'``, ``'margin'``,
    ``'fill'``, ``'foreground'``, ``'background'``, ``'write'``, ``'layout'``, ``'fuzz'``,
    ``'pixels'``, ``'raster'``, one ``'effect.<name>'`` for each [`Effect`][xnano_core.Effect]
    constructor and one ``'audio.<name>'`` for each audio effect. [`kinds`][xnano_core.Customization.kinds]
    lists them and [`defaults`][xnano_core.Customization.defaults] shows the parameters of one.

    Attributes:
        customization_kind: The kind, such as ``'style'`` or ``'effect.fade_to'``.
        parameters: The parameters by name, with defaults filled in.

    Raises:
        ValueError: The kind is not a customization kind.
        TypeError: A parameter does not belong to the kind.

    Examples:
        ```python
        buffer = Buffer(width=8, height=1)
        buffer | Customization('fill', cell='.')
        assert buffer.text.startswith('........')
        ```
    """

    def __init__(self, kind: str, /, **parameters: object) -> None: ...
    customization_kind: str
    """The kind, such as ``'style'`` or ``'effect.fade_to'``."""
    @property
    def parameters(self) -> dict[str, object]:
        """The parameters by name, with defaults filled in."""
    @staticmethod
    def kinds() -> list[str]:
        """
        The name of every kind of customization.

        Examples:
            ```python
            assert 'style' in Customization.kinds()
            ```
        """
    @staticmethod
    def defaults(kind: str) -> dict[str, object]:
        """
        The parameter names of a kind with their defaults, in order.

        Raises:
            ValueError: ``kind`` is not a customization kind.

        Examples:
            ```python
            assert Customization.defaults('margin') == {'horizontal': 0, 'vertical': 0}
            ```
        """
    def build(self) -> object:
        """
        The core object this customization stands for: a ``Style``, ``Border``, ``Effect``,
        ``Block``, ``Margin``, audio effect and so on, with all of its own methods.

        Examples:
            ```python
            assert isinstance(Customization('style', bold=True).build(), Style)
            ```
        """
    def to_operation(self) -> Operation:
        """
        The core operation that applies this customization.

        Raises:
            TypeError: The kind is not applied as an operation, such as ``'block'``.
        """
    def to_audio_effect(self) -> object:
        """
        The audio effect behind an ``'audio.*'`` customization.

        Raises:
            TypeError: The kind is not an audio effect.
        """
    def apply_to_surface(self, surface: Surface) -> None:
        """Apply this customization to a buffer, widget or region."""
    def __or__(self, other: Operation | Style) -> Operation: ...

class OperationChain(Operation):
    """
    Operations applied one after another when they cannot become one native sequence.

    ``a | b`` makes one automatically when a step needs more than the native sequence can
    hold. ``steps`` lists the operations in order.

    Attributes:
        steps: The operations applied in order.

    Examples:
        ```python
        chain = OperationChain(Fill('.'), Write('hi'))
        buffer = Buffer(width=4, height=1)
        buffer.update(chain)
        assert buffer.text.startswith('hi..')
        ```
    """

    def __init__(self, /, *steps: Operation) -> None: ...
    @property
    def steps(self) -> tuple[Operation, ...]:
        """The operations applied in order."""
    def __len__(self) -> int: ...

class Trigger:
    """
    When something runs, and which events count.

    The event triggers (``key``, ``key_release``, ``click``, ``drag``, ``mouse``, ``paste``,
    ``resize`` and ``state_change``) decide for one event with
    [`matches`][xnano_core.Trigger.matches]; a trigger is also callable with a hook context
    and answers for its ``event``. ``every`` and ``after`` carry the seconds a clock waits,
    and ``immediate``, ``frame`` and ``update`` name moments of the loop.

    Attributes:
        kind: The name of the trigger.
        seconds: The interval or delay of ``every`` and ``after``, else ``None``.
        keys: The key bindings a key trigger reacts to; empty means every key.
        is_event_trigger: Whether one event decides the trigger.

    Raises:
        ValueError: A trigger name, a number of seconds or a key binding is not valid.

    Examples:
        ```python
        press = Event.key_press('q')
        assert Trigger.key('q', 'escape').matches(press)
        assert not Trigger.click().matches(press)
        assert Trigger.every(0.5).seconds == 0.5
        ```
    """

    @property
    def kind(self) -> TriggerKind:
        """The name of the trigger, such as ``'click'`` or ``'every'``."""
    @property
    def seconds(self) -> float | None:
        """The interval or delay in seconds of ``every`` and ``after``, else ``None``."""
    @property
    def keys(self) -> list[str]:
        """The key bindings a key trigger reacts to; empty means every key."""
    @property
    def is_event_trigger(self) -> bool:
        """Whether one event decides the trigger."""
    @staticmethod
    def named(
        kind: TriggerKind, *, seconds: float | None = None, keys: Sequence[str] = ()
    ) -> Trigger:
        """
        Build a trigger from its name.

        Examples:
            ```python
            assert Trigger.named('every', seconds=1.0) == Trigger.every(1.0)
            ```
        """
    @staticmethod
    def immediate() -> Trigger:
        """Run once, as soon as it is attached."""
    @staticmethod
    def frame() -> Trigger:
        """Run before every frame."""
    @staticmethod
    def update() -> Trigger:
        """Run on every update of the loop."""
    @staticmethod
    def key(*keys: str) -> Trigger:
        """React to key presses and repeats of the given bindings, or of every key."""
    @staticmethod
    def key_release(*keys: str) -> Trigger:
        """React to key releases of the given bindings, or of every key."""
    @staticmethod
    def click() -> Trigger:
        """React to a mouse button press."""
    @staticmethod
    def drag() -> Trigger:
        """React to the pointer moving with a button held down."""
    @staticmethod
    def mouse() -> Trigger:
        """React to any mouse event."""
    @staticmethod
    def paste() -> Trigger:
        """React to pasted text."""
    @staticmethod
    def resize() -> Trigger:
        """React to a change of the terminal's size."""
    @staticmethod
    def state_change() -> Trigger:
        """React to a change of the terminal's state."""
    @staticmethod
    def every(seconds: float) -> Trigger:
        """Run at a steady interval on the clock."""
    @staticmethod
    def after(seconds: float) -> Trigger:
        """Run once, after a delay on the clock."""
    def matches(self, event: Event | TerminalStateChange | None) -> bool:
        """Whether ``event`` counts. Time and loop triggers never match an event."""
    def __call__(self, context: object) -> bool:
        """Whether the event of a hook ``context`` counts."""
    def __eq__(self, other: object) -> bool: ...

class ExpressionScope:
    """
    A named group of expressions, such as the parent's size or the terminal's clock.

    Reading an attribute the scope does not provide raises ``AttributeError`` that lists the
    ones it does.

    Examples:
        ```python
        try:
            ParentScope.depth
        except AttributeError as error:
            assert 'width' in str(error)
        ```
    """

class ParentExpressionScope(ExpressionScope):
    """
    The geometry of the enclosing buffer, as expressions.

    Attributes:
        width: The parent's width in cells.
        height: The parent's height in cells.
        size: The parent's size in cells.

    Examples:
        ```python
        assert ParentScope.width is ParentWidth
        ```
    """

    @property
    def width(self) -> NumericValue[int]:
        """The parent's width in cells."""
    @property
    def height(self) -> NumericValue[int]:
        """The parent's height in cells."""
    @property
    def size(self) -> Value[Size]:
        """The parent's size in cells."""

class RootExpressionScope(ExpressionScope):
    """
    The geometry and clock of the root terminal, as expressions.

    Attributes:
        width: The terminal's width in cells.
        height: The terminal's height in cells.
        time: Seconds elapsed on the terminal's clock.
        delta: Seconds since the previous frame.
        fps: Measured frames per second.

    Examples:
        ```python
        assert RootScope.time is TimeElapsed
        ```
    """

    @property
    def width(self) -> NumericValue[int | float]:
        """The terminal's width in cells."""
    @property
    def height(self) -> NumericValue[int | float]:
        """The terminal's height in cells."""
    @property
    def time(self) -> NumericValue[int | float]:
        """Seconds elapsed on the terminal's clock."""
    @property
    def delta(self) -> NumericValue[int | float]:
        """Seconds since the previous frame."""
    @property
    def fps(self) -> NumericValue[int | float]:
        """Measured frames per second."""

class BufferExpressionScope(ExpressionScope):
    """
    A buffer's own position and size, as expressions.

    Attributes:
        x: The column in the parent.
        y: The row in the parent.
        position: The position in the parent.
        width: The width in cells.
        height: The height in cells.
        size: The size in cells.
        region: The rectangle on the screen, counting every parent offset.

    Examples:
        ```python
        assert BufferScope.width is Width
        assert BufferScope.region is BufferRegion
        ```
    """

    @property
    def x(self) -> NumericValue[int | float]:
        """The column in the parent."""
    @property
    def y(self) -> NumericValue[int | float]:
        """The row in the parent."""
    @property
    def position(self) -> Value[Point]:
        """The position in the parent."""
    @property
    def width(self) -> NumericValue[int | float]:
        """The width in cells."""
    @property
    def height(self) -> NumericValue[int | float]:
        """The height in cells."""
    @property
    def size(self) -> Value[Size]:
        """The size in cells."""
    @property
    def region(self) -> Value[Rectangle]:
        """The rectangle on the screen, counting every parent offset."""

class KeyboardExpressionScope(ExpressionScope):
    """
    The latest key event, as expressions.

    Every member has no value while the latest input was not a key event, so a condition on a
    key is false for mouse, wheel and paste events. Comparing a member with ``None`` raises
    ``TypeError``; compare it with the key you wait for, such as ``KeyboardScope.key == 'q'``.

    Attributes:
        key: The key name, such as ``'q'`` or ``'enter'``.
        kind: ``'press'``, ``'repeat'`` or ``'release'``.
        chord: The key with its modifiers, such as ``'ctrl+s'``.

    Examples:
        ```python
        with Runtime.offscreen(width=10, height=3) as runtime:
            buffer = Buffer(width=10, height=3)
            runtime.mount(buffer)
            seen = []
            buffer.add_hook(
                lambda context: seen.append('quit'),
                events=('key',),
                condition=KeyboardScope.key == 'q',
            )
            for key in ('w', 'q'):
                runtime.inject(Event.key_press(key))
                runtime.step()
            assert seen == ['quit']
            assert buffer.inspect(KeyboardScope.chord) == 'q'
        ```
    """

    @property
    def key(self) -> Value[str | None]:
        """The key name of the latest key event."""
    @property
    def kind(self) -> Value[Literal['press', 'repeat', 'release'] | None]:
        """Whether the latest key event was a press, repeat or release."""
    @property
    def chord(self) -> Value[str | None]:
        """The latest key event with its modifiers, such as ``'ctrl+s'``."""

class MouseExpressionScope(ExpressionScope):
    """
    The latest mouse button or motion report, as expressions.

    ``position``, ``button`` and ``kind`` describe the event being handled and have no value
    while the latest input was a key, a paste or a wheel report, so a condition on them is false
    (comparing with ``None`` raises ``TypeError``); ``is_down`` is the held state
    and stays true between events while a button is held. Wheel reports belong to
    [`ScrollScope`][xnano_core._xnano_core.ScrollScope].

    Attributes:
        position: The cell of the event.
        button: ``'left'``, ``'right'`` or ``'middle'``.
        kind: ``'press'``, ``'release'``, ``'drag'`` or ``'move'``.
        is_down: Whether any button is held.

    Examples:
        ```python
        with Runtime.offscreen(width=10, height=3) as runtime:
            buffer = Buffer(width=4, height=2, x=1, y=1)
            runtime.mount(buffer)
            clicks = []
            buffer.add_hook(
                lambda context: clicks.append('inside'),
                events=('mouse',),
                condition=BufferScope.region.contains(MouseScope.position),
            )
            runtime.inject(Event.mouse_event(column=2, row=2, kind='move'))
            runtime.inject(Event.mouse_event(column=8, row=2, kind='move'))
            runtime.step()
            assert clicks == ['inside']
            assert buffer.inspect(MouseScope.position.x) == 8
        ```
    """

    @property
    def position(self) -> Value[Point | None]:
        """The cell of the latest button or motion report."""
    @property
    def button(self) -> Value[MouseButton | None]:
        """The button of the latest button or motion report."""
    @property
    def kind(self) -> Value[Literal['press', 'release', 'drag', 'move'] | None]:
        """The kind of the latest button or motion report."""
    @property
    def is_down(self) -> Predicate:
        """Whether any mouse button is held."""

class ScrollExpressionScope(ExpressionScope):
    """
    The mouse wheel steps of the current step, as expressions.

    Each member holds the steps of the latest wheel report of the step; reports of one step do
    not add up, and a key, paste, button or motion report that follows a wheel report in the same
    step clears them. Both are ``0`` when no wheel report arrived in the step. Scrolling up gives
    a negative ``y`` and scrolling left a negative ``x``.

    Attributes:
        x: Horizontal steps (right is positive).
        y: Vertical steps (down is positive).

    Examples:
        ```python
        with Runtime.offscreen(width=10, height=3) as runtime:
            buffer = Buffer(width=10, height=3)
            runtime.mount(buffer)
            seen = []
            buffer.add_hook(
                lambda context: seen.append('up'),
                events=('mouse',),
                condition=ScrollScope.y < 0,
            )
            runtime.inject(Event.mouse_event(column=1, row=1, kind='scroll', scroll_y=-1))
            runtime.step()
            assert seen == ['up'] and buffer.inspect(ScrollScope.y) == -1
        ```
    """

    @property
    def x(self) -> NumericValue[int]:
        """Horizontal steps of the latest wheel report of the current step."""
    @property
    def y(self) -> NumericValue[int]:
        """Vertical steps of the latest wheel report of the current step."""

ParentScope: ParentExpressionScope
"""The parent's geometry: ``ParentScope.width``, ``ParentScope.height``, ``ParentScope.size``."""
RootScope: RootExpressionScope
"""The terminal's geometry and clock: ``RootScope.width``, ``RootScope.time``, ..."""
BufferScope: BufferExpressionScope
"""A buffer's own geometry: ``BufferScope.x``, ``BufferScope.width``, ..."""
KeyboardScope: KeyboardExpressionScope
"""The latest key event: ``KeyboardScope.key``, ``KeyboardScope.kind``, ``KeyboardScope.chord``."""
MouseScope: MouseExpressionScope
"""The latest mouse button or motion report: ``MouseScope.position``, ``MouseScope.is_down``, ..."""
ScrollScope: ScrollExpressionScope
"""The latest wheel report of the current step: ``ScrollScope.x`` and ``ScrollScope.y``."""

X: NumericValue[int | float]
"""The horizontal position of a buffer or region, in terminal cells."""
Y: NumericValue[int | float]
"""The vertical position of a buffer or region, in terminal cells."""
Width: NumericValue[int | float]
"""The width of a buffer or region, in terminal cells."""
Height: NumericValue[int | float]
"""The height of a buffer or region, in terminal cells."""
TimeElapsed: NumericValue[int | float]
"""The elapsed runtime time, in seconds."""
TimeDelta: NumericValue[int | float]
"""The elapsed time since the previous runtime frame, in seconds."""
TimeElapsedMilliseconds: NumericValue[int | float]
"""The elapsed runtime time, in milliseconds."""
TimeDeltaMilliseconds: NumericValue[int | float]
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
ParentSize: Value[Size]
"""The size of the parent buffer, or of the buffer a region belongs to.

Evaluating it raises ``TypeError`` for a buffer without a parent.
"""
ParentWidth: NumericValue[int]
"""The width of the parent buffer, in cells."""
ParentHeight: NumericValue[int]
"""The height of the parent buffer, in cells."""
ScreenPosition: Value[Point]
"""The top-left cell of a buffer or region on the screen, counting every parent offset."""
ScreenBounds: Value[Rectangle]
"""The rectangle of a buffer or region on the screen, counting every parent offset."""
PointerPosition: Value[Point | None]
"""The cell under the pointer, or ``None`` until the runtime has seen the pointer.

It is the last known cell, held between events. ``MousePosition`` is the cell of the event
being handled. Reading it needs a mounted runtime.
"""
KeyboardKey: Value[str | None]
"""The key of the latest key event, or ``None`` while the latest input was not a key."""
KeyboardKind: Value[Literal['press', 'repeat', 'release'] | None]
"""Whether the latest key event was a press, repeat or release, or ``None``."""
KeyboardChord: Value[str | None]
"""The latest key event with its modifiers, such as ``'ctrl+s'``, or ``None``."""
MouseButtonValue: Value[MouseButton | None]
"""The button of the latest button or motion report, or ``None``."""
MouseKind: Value[Literal['press', 'release', 'drag', 'move'] | None]
"""The kind of the latest button or motion report, or ``None`` (also for a wheel report)."""
MousePosition: Value[Point | None]
"""The cell of the latest button or motion report, or ``None``.

``PointerPosition`` is the last cell the pointer was seen at, whatever came since; this one
belongs to the event being handled.
"""
MouseIsDown: Predicate
"""Whether any mouse button is held."""
ScrollX: NumericValue[int]
"""Horizontal steps of the latest wheel report of the current step (right is positive)."""
ScrollY: NumericValue[int]
"""Vertical steps of the latest wheel report of the step (down is positive, up is ``-1``)."""
BufferRegion: Value[Rectangle]
"""The rectangle of a buffer on the screen, counting every parent offset."""
Layer: NumericProperty[int]
"""The paint order of a buffer among its siblings. Assign it with ``Layer(2)``."""
IsVisible: Property[bool]
"""Whether a buffer is drawn. Assign it with ``IsVisible(False)``."""
