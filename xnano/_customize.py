"""
xnano._customize

TypedDict and dataclass specifications for styles, borders, blocks, padding, margins, pixels,
visual effects and audio effects, compiled through [`fx`][xnano.operations.fx].
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Literal,
    TypedDict,
    TypeVar,
    cast,
    overload,
)

import xnano_core as _core
from xnano._axes import to_rgb
from xnano._values import RGB, ColorValue, PixelEncoding

if TYPE_CHECKING:
    from typing_extensions import Required, Unpack
    from xnano_audio import TerminalAudioEffect

    from xnano.canvas import Canvas
    from xnano.placement import Placement

TargetT = TypeVar('TargetT')

HslShiftChannel = float | _core.Expression[int | float]
HslShiftTuple = tuple[HslShiftChannel, HslShiftChannel, HslShiftChannel]


class Customization(_core.Customization):
    """
    Base class for all customization dataclasses returned by [`fx`][xnano.operations.fx].

    Every customization is both a dataclass holding its typed parameters and a native
    [`Customization`][xnano_core.Customization] operation that can be piped with ``|`` or
    passed to ``add`` and ``update``. The parameters are read when it is applied, so editing a
    field changes what it does.

    Attributes:
        customization_kind: Identifier of the customization kind (such as ``'fill'`` or ``'effect.dissolve'``).
    """

    def apply_to(
        self,
        target: Canvas[object, object] | Placement[object, object] | _core.Surface,
    ) -> None:
        """
        Apply this customization to a canvas, placement or surface.

        It stays attached to the target: after this, assigning one of its fields applies it
        again, so a customization from ``fx`` is a live handle on what it changed. A running
        effect is stopped and started again with the new values.

        Args:
            target: The target to apply the customization to.
        """
        from xnano.canvas import Canvas
        from xnano.placement import Placement

        self._attach(target)
        if isinstance(target, (Placement, Canvas)):
            target._buffer.update(self)
            if self.customization_kind.startswith('effect.'):
                target._canvas._record_effect(self, target)
        elif isinstance(target, _core.Surface):
            target.update(self)

    def cancel(self) -> None:
        """
        Stop this effect on the target it was applied to.

        Does nothing for an effect that was never applied or has already finished, and for a
        customization that is not an effect.

        Examples:
            ```python
            import xnano
            from xnano.operations import fx

            with xnano.new('hi', width=4, height=1) as canvas:
                fade = fx('effect.fade_to', foreground='red', duration_milliseconds=5000)
                fade.apply_to(canvas)
                fade.cancel()
                fade.cancel()
            ```
        """
        target = self.__dict__.get('_target')
        key = getattr(self, 'key', None)
        if target is None or not isinstance(key, str):
            return
        if not self.customization_kind.startswith('effect.'):
            return
        surface = target._buffer if hasattr(target, '_buffer') else target
        surface.update(_core.CancelEffect(key))

    def _attach(self, target: object) -> None:
        """Remember the target, and give a running effect a key so it can be stopped."""
        if (
            self.customization_kind.startswith('effect.')
            and getattr(self, 'key', 1) is None
        ):
            object.__setattr__(self, 'key', f'xnano-effect-{id(self)}')
        object.__setattr__(self, '_target', target)

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        if name.startswith('_') or name not in getattr(self, '__dataclass_fields__', ()):
            return
        target = self.__dict__.get('_target')
        if target is None:
            return
        surface = target._buffer if hasattr(target, '_buffer') else target
        key = getattr(self, 'key', None)
        if self.customization_kind.startswith('effect.') and key is not None:
            surface.update(_core.CancelEffect(key))
        surface.update(self)


class FillArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('fill', ...)``.

    Attributes:
        cell: The character or cell used to fill the target.
    """

    cell: _core.Cell | str


@dataclass
class FillCustomization(Customization):
    """
    Dataclass customization that fills every cell with a character or [`Cell`][xnano_core.Cell] (``'fill'``).

    Attributes:
        cell: The character or cell used to fill the target.
    """

    customization_kind = 'fill'
    cell: _core.Cell | str = ' '


class WriteArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('write', ...)``.

    Attributes:
        text: Text or styled text to write.
        x: Starting column.
        y: Starting row.
        style: Optional style applied to the written text.
        mode: Write blending mode (``'replace'``, ``'preserve_background'``).
    """

    text: _core.TextContent
    x: int
    y: int
    style: _core.Style | None
    mode: _core.WriteMode


@dataclass
class WriteCustomization(Customization):
    """
    Dataclass customization that writes text into cells (``'write'``).

    Attributes:
        text: Text or styled text to write.
        x: Starting column.
        y: Starting row.
        style: Optional style applied to the written text.
        mode: Write blending mode (``'replace'``, ``'preserve_background'``).
    """

    customization_kind = 'write'
    text: _core.TextContent = ''
    x: int = 0
    y: int = 0
    style: _core.Style | None = None
    mode: _core.WriteMode = 'replace'


class LayoutArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('layout', ...)``.

    Attributes:
        arrangement: ``'row'``, ``'column'`` or ``'overlay'``.
        sizes: Size rules for each child along the main axis.
        spacing: Cells between adjacent children.
        padding: Cells inset from the parent's edges.
    """

    arrangement: Literal['row', 'column', 'overlay']
    sizes: Sequence[_core.SizeRule]
    spacing: int
    padding: int


@dataclass
class LayoutCustomization(Customization):
    """
    Dataclass customization that arranges attached children (``'layout'``).

    Attributes:
        arrangement: ``'row'``, ``'column'`` or ``'overlay'``.
        sizes: Size rules for each child along the main axis.
        spacing: Cells between adjacent children.
        padding: Cells inset from the parent's edges.
    """

    customization_kind = 'layout'
    arrangement: Literal['row', 'column', 'overlay'] = 'column'
    sizes: Sequence[_core.SizeRule] = ()
    spacing: int = 0
    padding: int = 0


class FuzzArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('fuzz', ...)``.

    Attributes:
        intensity: Percentage of glyphs to replace (``0`` to ``100``).
        seed: Optional random seed for repeatable noise.
    """

    intensity: int
    seed: int | None


@dataclass
class FuzzCustomization(Customization):
    """
    Dataclass customization that replaces a percentage of visible glyphs with noise (``'fuzz'``).

    Attributes:
        intensity: Percentage of glyphs to replace (``0`` to ``100``).
        seed: Optional random seed for repeatable noise.
    """

    customization_kind = 'fuzz'
    intensity: int = 10
    seed: int | None = None


class PixelsArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('pixels', ...)``.

    Attributes:
        shader: Optional function ``(column, row) -> color`` evaluated across the target's pixel grid.
        pixels: Optional explicit iterable of ``(column, row, (red, green, blue))`` pixels.
        encoding: ``'half_blocks'`` or ``'braille'``.
        clip: Whether out-of-bounds pixels are clipped instead of raising ``IndexError``.
        x: Column offset of the explicit pixels, or ``None``.
        y: Row offset of the explicit pixels, or ``None``.
    """

    shader: Callable[[int, int], ColorValue | None] | None
    pixels: Iterable[_core.PixelEntry] | None
    encoding: PixelEncoding
    clip: bool
    x: int | None
    y: int | None


@dataclass
class PixelsCustomization(Customization):
    """
    Dataclass customization that colors pixels from a shader function or iterable (``'pixels'``).

    Attributes:
        shader: Optional function ``(column, row) -> color`` evaluated across the target's pixel grid.
        pixels: Optional explicit iterable of ``(column, row, (red, green, blue))`` pixels.
        encoding: ``'half_blocks'`` or ``'braille'``.
        clip: Whether out-of-bounds pixels are clipped instead of raising ``IndexError``.
        x: Column offset of the explicit pixels, or ``None``.
        y: Row offset of the explicit pixels, or ``None``.
    """

    customization_kind = 'pixels'
    shader: Callable[[int, int], ColorValue | None] | None = None
    pixels: Iterable[_core.PixelEntry] | None = None
    encoding: PixelEncoding = 'half_blocks'
    clip: bool = True
    x: int | None = None
    y: int | None = None

    def apply_to_surface(self, surface: _core.Surface) -> None:
        """Shade or write pixels into ``surface``."""
        if self.pixels is not None:
            surface.update(
                _core.Pixels(
                    self.pixels,
                    encoding=self.encoding,
                    clip=self.clip,
                    x=self.x,
                    y=self.y,
                )
            )
        if self.shader is not None:
            view = surface.pixels(encoding=self.encoding)
            colored: list[tuple[int, int, RGB]] = []
            for row in range(view.height):
                for column in range(view.width):
                    color = self.shader(column, row)
                    if color is not None:
                        colored.append((column, row, to_rgb(color)))
            view.write(colored)


class RasterArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('raster', ...)``.

    Attributes:
        rgba: ``width * height * 4`` bytes of RGBA8 pixel data.
        width: Image width in pixels.
        height: Image height in pixels.
        x: Top-left pixel column.
        y: Top-left pixel row.
        encoding: ``'half_blocks'`` or ``'braille'``.
        mode: ``'over'`` or ``'replace'``.
    """

    rgba: bytes
    width: int
    height: int
    x: int
    y: int
    encoding: PixelEncoding
    mode: _core.RasterMode


@dataclass
class RasterCustomization(Customization):
    """
    Dataclass customization that draws a row-major RGBA8 buffer as pixels (``'raster'``).

    Attributes:
        rgba: ``width * height * 4`` bytes of RGBA8 pixel data.
        width: Image width in pixels.
        height: Image height in pixels.
        x: Top-left pixel column.
        y: Top-left pixel row.
        encoding: ``'half_blocks'`` or ``'braille'``.
        mode: ``'over'`` or ``'replace'``.
    """

    customization_kind = 'raster'
    rgba: bytes = b''
    width: int = 0
    height: int = 0
    x: int = 0
    y: int = 0
    encoding: PixelEncoding = 'half_blocks'
    mode: _core.RasterMode = 'over'


def _finalize_effect(
    effect: _core.Effect, key: str | _core.Expression[str] | None
) -> _core.Effect:
    if key is not None:
        return effect.with_key(key)
    return effect


class FadeToEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.fade_to', ...)``.

    Attributes:
        foreground: Target foreground color, or ``None``.
        background: Target background color, or ``None``.
        duration_milliseconds: Duration of the fade in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    foreground: ColorValue | _core.Expression[ColorValue] | None
    background: ColorValue | _core.Expression[ColorValue] | None
    duration_milliseconds: int | _core.Expression[int | float] | None
    interpolation: str | _core.Expression[str] | None
    key: str | _core.Expression[str] | None


@dataclass
class FadeToEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.fade_to`` (``'effect.fade_to'``).

    Attributes:
        foreground: Target foreground color, or ``None``.
        background: Target background color, or ``None``.
        duration_milliseconds: Duration of the fade in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.fade_to'
    foreground: ColorValue | _core.Expression[ColorValue] | None = None
    background: ColorValue | _core.Expression[ColorValue] | None = None
    duration_milliseconds: int | _core.Expression[int | float] | None = None
    interpolation: str | _core.Expression[str] | None = None
    key: str | _core.Expression[str] | None = None


class FadeFromEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.fade_from', ...)``.

    Attributes:
        foreground: Starting foreground color, or ``None``.
        background: Starting background color, or ``None``.
        duration_milliseconds: Duration of the fade in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    foreground: ColorValue | _core.Expression[ColorValue] | None
    background: ColorValue | _core.Expression[ColorValue] | None
    duration_milliseconds: int | _core.Expression[int | float] | None
    interpolation: str | _core.Expression[str] | None
    key: str | _core.Expression[str] | None


@dataclass
class FadeFromEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.fade_from`` (``'effect.fade_from'``).

    Attributes:
        foreground: Starting foreground color, or ``None``.
        background: Starting background color, or ``None``.
        duration_milliseconds: Duration of the fade in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.fade_from'
    foreground: ColorValue | _core.Expression[ColorValue] | None = None
    background: ColorValue | _core.Expression[ColorValue] | None = None
    duration_milliseconds: int | _core.Expression[int | float] | None = None
    interpolation: str | _core.Expression[str] | None = None
    key: str | _core.Expression[str] | None = None


class PaintEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.paint', ...)``.

    Attributes:
        foreground: Foreground color to paint, or ``None``.
        background: Background color to paint, or ``None``.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    foreground: ColorValue | _core.Expression[ColorValue] | None
    background: ColorValue | _core.Expression[ColorValue] | None
    duration_milliseconds: int | _core.Expression[int | float] | None
    interpolation: str | _core.Expression[str] | None
    key: str | _core.Expression[str] | None


@dataclass
class PaintEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.paint`` (``'effect.paint'``).

    Attributes:
        foreground: Foreground color to paint, or ``None``.
        background: Background color to paint, or ``None``.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.paint'
    foreground: ColorValue | _core.Expression[ColorValue] | None = None
    background: ColorValue | _core.Expression[ColorValue] | None = None
    duration_milliseconds: int | _core.Expression[int | float] | None = None
    interpolation: str | _core.Expression[str] | None = None
    key: str | _core.Expression[str] | None = None


class SaturateEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.saturate', ...)``.

    Attributes:
        foreground: Foreground saturation change, or ``None``.
        background: Background saturation change, or ``None``.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    foreground: float | _core.Expression[int | float] | None
    background: float | _core.Expression[int | float] | None
    duration_milliseconds: int | _core.Expression[int | float] | None
    interpolation: str | _core.Expression[str] | None
    key: str | _core.Expression[str] | None


@dataclass
class SaturateEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.saturate`` (``'effect.saturate'``).

    Attributes:
        foreground: Foreground saturation change, or ``None``.
        background: Background saturation change, or ``None``.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.saturate'
    foreground: float | _core.Expression[int | float] | None = None
    background: float | _core.Expression[int | float] | None = None
    duration_milliseconds: int | _core.Expression[int | float] | None = None
    interpolation: str | _core.Expression[str] | None = None
    key: str | _core.Expression[str] | None = None


class LightenEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.lighten', ...)``.

    Attributes:
        foreground: Foreground lightness increase, or ``None``.
        background: Background lightness increase, or ``None``.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    foreground: float | _core.Expression[int | float] | None
    background: float | _core.Expression[int | float] | None
    duration_milliseconds: int | _core.Expression[int | float] | None
    interpolation: str | _core.Expression[str] | None
    key: str | _core.Expression[str] | None


@dataclass
class LightenEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.lighten`` (``'effect.lighten'``).

    Attributes:
        foreground: Foreground lightness increase, or ``None``.
        background: Background lightness increase, or ``None``.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.lighten'
    foreground: float | _core.Expression[int | float] | None = None
    background: float | _core.Expression[int | float] | None = None
    duration_milliseconds: int | _core.Expression[int | float] | None = None
    interpolation: str | _core.Expression[str] | None = None
    key: str | _core.Expression[str] | None = None


class DarkenEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.darken', ...)``.

    Attributes:
        foreground: Foreground darkness increase, or ``None``.
        background: Background darkness increase, or ``None``.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    foreground: float | _core.Expression[int | float] | None
    background: float | _core.Expression[int | float] | None
    duration_milliseconds: int | _core.Expression[int | float] | None
    interpolation: str | _core.Expression[str] | None
    key: str | _core.Expression[str] | None


@dataclass
class DarkenEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.darken`` (``'effect.darken'``).

    Attributes:
        foreground: Foreground darkness increase, or ``None``.
        background: Background darkness increase, or ``None``.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.darken'
    foreground: float | _core.Expression[int | float] | None = None
    background: float | _core.Expression[int | float] | None = None
    duration_milliseconds: int | _core.Expression[int | float] | None = None
    interpolation: str | _core.Expression[str] | None = None
    key: str | _core.Expression[str] | None = None


class SweepInEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.sweep_in', ...)``.

    Attributes:
        direction: Sweep direction (such as ``'left_to_right'``).
        gradient_length: Length of the sweep gradient in cells.
        randomness: Random offset across rows or columns.
        color: Starting sweep color.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    direction: str | _core.Expression[str] | None
    gradient_length: int | _core.Expression[int | float] | None
    randomness: int | _core.Expression[int | float] | None
    color: ColorValue | _core.Expression[ColorValue] | None
    duration_milliseconds: int | _core.Expression[int | float] | None
    interpolation: str | _core.Expression[str] | None
    key: str | _core.Expression[str] | None


@dataclass
class SweepInEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.sweep_in`` (``'effect.sweep_in'``).

    Attributes:
        direction: Sweep direction (such as ``'left_to_right'``).
        gradient_length: Length of the sweep gradient in cells.
        randomness: Random offset across rows or columns.
        color: Starting sweep color.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.sweep_in'
    direction: str | _core.Expression[str] | None = None
    gradient_length: int | _core.Expression[int | float] | None = None
    randomness: int | _core.Expression[int | float] | None = None
    color: ColorValue | _core.Expression[ColorValue] | None = None
    duration_milliseconds: int | _core.Expression[int | float] | None = None
    interpolation: str | _core.Expression[str] | None = None
    key: str | _core.Expression[str] | None = None


class SweepOutEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.sweep_out', ...)``.

    Attributes:
        direction: Sweep direction (such as ``'left_to_right'``).
        gradient_length: Length of the sweep gradient in cells.
        randomness: Random offset across rows or columns.
        color: Ending sweep color.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    direction: str | _core.Expression[str] | None
    gradient_length: int | _core.Expression[int | float] | None
    randomness: int | _core.Expression[int | float] | None
    color: ColorValue | _core.Expression[ColorValue] | None
    duration_milliseconds: int | _core.Expression[int | float] | None
    interpolation: str | _core.Expression[str] | None
    key: str | _core.Expression[str] | None


@dataclass
class SweepOutEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.sweep_out`` (``'effect.sweep_out'``).

    Attributes:
        direction: Sweep direction (such as ``'left_to_right'``).
        gradient_length: Length of the sweep gradient in cells.
        randomness: Random offset across rows or columns.
        color: Ending sweep color.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.sweep_out'
    direction: str | _core.Expression[str] | None = None
    gradient_length: int | _core.Expression[int | float] | None = None
    randomness: int | _core.Expression[int | float] | None = None
    color: ColorValue | _core.Expression[ColorValue] | None = None
    duration_milliseconds: int | _core.Expression[int | float] | None = None
    interpolation: str | _core.Expression[str] | None = None
    key: str | _core.Expression[str] | None = None


class SlideInEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.slide_in', ...)``.

    Attributes:
        direction: Slide direction (such as ``'left_to_right'``).
        gradient_length: Length of the gradient trail in cells.
        randomness: Random offset across rows or columns.
        color: Color behind the sliding cells.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    direction: str | _core.Expression[str] | None
    gradient_length: int | _core.Expression[int | float] | None
    randomness: int | _core.Expression[int | float] | None
    color: ColorValue | _core.Expression[ColorValue] | None
    duration_milliseconds: int | _core.Expression[int | float] | None
    interpolation: str | _core.Expression[str] | None
    key: str | _core.Expression[str] | None


@dataclass
class SlideInEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.slide_in`` (``'effect.slide_in'``).

    Attributes:
        direction: Slide direction (such as ``'left_to_right'``).
        gradient_length: Length of the gradient trail in cells.
        randomness: Random offset across rows or columns.
        color: Color behind the sliding cells.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.slide_in'
    direction: str | _core.Expression[str] | None = None
    gradient_length: int | _core.Expression[int | float] | None = None
    randomness: int | _core.Expression[int | float] | None = None
    color: ColorValue | _core.Expression[ColorValue] | None = None
    duration_milliseconds: int | _core.Expression[int | float] | None = None
    interpolation: str | _core.Expression[str] | None = None
    key: str | _core.Expression[str] | None = None


class SlideOutEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.slide_out', ...)``.

    Attributes:
        direction: Slide direction (such as ``'left_to_right'``).
        gradient_length: Length of the gradient trail in cells.
        randomness: Random offset across rows or columns.
        color: Color left behind the sliding cells.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    direction: str | _core.Expression[str] | None
    gradient_length: int | _core.Expression[int | float] | None
    randomness: int | _core.Expression[int | float] | None
    color: ColorValue | _core.Expression[ColorValue] | None
    duration_milliseconds: int | _core.Expression[int | float] | None
    interpolation: str | _core.Expression[str] | None
    key: str | _core.Expression[str] | None


@dataclass
class SlideOutEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.slide_out`` (``'effect.slide_out'``).

    Attributes:
        direction: Slide direction (such as ``'left_to_right'``).
        gradient_length: Length of the gradient trail in cells.
        randomness: Random offset across rows or columns.
        color: Color left behind the sliding cells.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.slide_out'
    direction: str | _core.Expression[str] | None = None
    gradient_length: int | _core.Expression[int | float] | None = None
    randomness: int | _core.Expression[int | float] | None = None
    color: ColorValue | _core.Expression[ColorValue] | None = None
    duration_milliseconds: int | _core.Expression[int | float] | None = None
    interpolation: str | _core.Expression[str] | None = None
    key: str | _core.Expression[str] | None = None


class HslShiftEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.hsl_shift', ...)``.

    Attributes:
        foreground: ``(hue, saturation, lightness)`` shift for foreground colors.
        background: ``(hue, saturation, lightness)`` shift for background colors.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    foreground: HslShiftTuple | None
    background: HslShiftTuple | None
    duration_milliseconds: int | _core.Expression[int | float] | None
    interpolation: str | _core.Expression[str] | None
    key: str | _core.Expression[str] | None


@dataclass
class HslShiftEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.hsl_shift`` (``'effect.hsl_shift'``).

    Attributes:
        foreground: ``(hue, saturation, lightness)`` shift for foreground colors.
        background: ``(hue, saturation, lightness)`` shift for background colors.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.hsl_shift'
    foreground: HslShiftTuple | None = None
    background: HslShiftTuple | None = None
    duration_milliseconds: int | _core.Expression[int | float] | None = None
    interpolation: str | _core.Expression[str] | None = None
    key: str | _core.Expression[str] | None = None


class DissolveEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.dissolve', ...)``.

    Attributes:
        style: Style dissolved into.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    style: _core.Style | _core.DynamicStyle | None
    duration_milliseconds: int | _core.Expression[int | float] | None
    interpolation: str | _core.Expression[str] | None
    key: str | _core.Expression[str] | None


@dataclass
class DissolveEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.dissolve`` (``'effect.dissolve'``).

    Attributes:
        style: Style dissolved into.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.dissolve'
    style: _core.Style | _core.DynamicStyle | None = None
    duration_milliseconds: int | _core.Expression[int | float] | None = None
    interpolation: str | _core.Expression[str] | None = None
    key: str | _core.Expression[str] | None = None


class CoalesceEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.coalesce', ...)``.

    Attributes:
        style: Style coalesced from.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    style: _core.Style | _core.DynamicStyle | None
    duration_milliseconds: int | _core.Expression[int | float] | None
    interpolation: str | _core.Expression[str] | None
    key: str | _core.Expression[str] | None


@dataclass
class CoalesceEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.coalesce`` (``'effect.coalesce'``).

    Attributes:
        style: Style coalesced from.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.coalesce'
    style: _core.Style | _core.DynamicStyle | None = None
    duration_milliseconds: int | _core.Expression[int | float] | None = None
    interpolation: str | _core.Expression[str] | None = None
    key: str | _core.Expression[str] | None = None


class GlitchEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.glitch', ...)``.

    Attributes:
        ratio: Fraction of cells affected by the glitch.
        duration_milliseconds: Duration in milliseconds.
        start_delay_milliseconds: ``(minimum, maximum)`` delay before a cell glitches.
        action_milliseconds: ``(minimum, maximum)`` duration of each cell glitch.
        key: Optional effect key for replacement or cancellation.
    """

    ratio: float | _core.Expression[int | float] | None
    duration_milliseconds: int | _core.Expression[int | float] | None
    start_delay_milliseconds: tuple[int, int]
    action_milliseconds: tuple[int, int]
    key: str | _core.Expression[str] | None


@dataclass
class GlitchEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.glitch`` (``'effect.glitch'``).

    Attributes:
        ratio: Fraction of cells affected by the glitch.
        duration_milliseconds: Duration in milliseconds.
        start_delay_milliseconds: ``(minimum, maximum)`` delay before a cell glitches.
        action_milliseconds: ``(minimum, maximum)`` duration of each cell glitch.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.glitch'
    ratio: float | _core.Expression[int | float] | None = None
    duration_milliseconds: int | _core.Expression[int | float] | None = None
    start_delay_milliseconds: tuple[int, int] = (0, 0)
    action_milliseconds: tuple[int, int] = (50, 150)
    key: str | _core.Expression[str] | None = None


class SleepEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.sleep', ...)``.

    Attributes:
        duration_milliseconds: Pause duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    duration_milliseconds: int | _core.Expression[int | float]
    interpolation: str | _core.Expression[str] | None
    key: str | _core.Expression[str] | None


@dataclass
class SleepEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.sleep`` (``'effect.sleep'``).

    Attributes:
        duration_milliseconds: Pause duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.sleep'
    duration_milliseconds: int | _core.Expression[int | float] = 500
    interpolation: str | _core.Expression[str] | None = None
    key: str | _core.Expression[str] | None = None


class EvolveEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.evolve', ...)``.

    Attributes:
        symbols: Named symbol progression (such as ``'circles'``, ``'blocks'`` or ``'shaded'``).
        style: Optional style applied to the evolving symbols.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    symbols: _core.EvolveSymbolSet | _core.Expression[str] | None
    style: _core.Style | _core.DynamicStyle | None
    duration_milliseconds: int | _core.Expression[int | float] | None
    interpolation: str | _core.Expression[str] | None
    key: str | _core.Expression[str] | None


@dataclass
class EvolveEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.evolve`` (``'effect.evolve'``).

    Attributes:
        symbols: Named symbol progression (such as ``'circles'``, ``'blocks'`` or ``'shaded'``).
        style: Optional style applied to the evolving symbols.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.evolve'
    symbols: _core.EvolveSymbolSet | _core.Expression[str] | None = None
    style: _core.Style | _core.DynamicStyle | None = None
    duration_milliseconds: int | _core.Expression[int | float] | None = None
    interpolation: str | _core.Expression[str] | None = None
    key: str | _core.Expression[str] | None = None


class EvolveIntoEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.evolve_into', ...)``.

    Attributes:
        symbols: Named symbol progression (such as ``'circles'``, ``'blocks'`` or ``'shaded'``).
        style: Optional style applied to the evolving symbols.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    symbols: _core.EvolveSymbolSet | _core.Expression[str] | None
    style: _core.Style | _core.DynamicStyle | None
    duration_milliseconds: int | _core.Expression[int | float] | None
    interpolation: str | _core.Expression[str] | None
    key: str | _core.Expression[str] | None


@dataclass
class EvolveIntoEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.evolve_into`` (``'effect.evolve_into'``).

    Attributes:
        symbols: Named symbol progression (such as ``'circles'``, ``'blocks'`` or ``'shaded'``).
        style: Optional style applied to the evolving symbols.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.evolve_into'
    symbols: _core.EvolveSymbolSet | _core.Expression[str] | None = None
    style: _core.Style | _core.DynamicStyle | None = None
    duration_milliseconds: int | _core.Expression[int | float] | None = None
    interpolation: str | _core.Expression[str] | None = None
    key: str | _core.Expression[str] | None = None


class EvolveFromEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.evolve_from', ...)``.

    Attributes:
        symbols: Named symbol progression (such as ``'circles'``, ``'blocks'`` or ``'shaded'``).
        style: Optional style applied to the evolving symbols.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    symbols: _core.EvolveSymbolSet | _core.Expression[str] | None
    style: _core.Style | _core.DynamicStyle | None
    duration_milliseconds: int | _core.Expression[int | float] | None
    interpolation: str | _core.Expression[str] | None
    key: str | _core.Expression[str] | None


@dataclass
class EvolveFromEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.evolve_from`` (``'effect.evolve_from'``).

    Attributes:
        symbols: Named symbol progression (such as ``'circles'``, ``'blocks'`` or ``'shaded'``).
        style: Optional style applied to the evolving symbols.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.evolve_from'
    symbols: _core.EvolveSymbolSet | _core.Expression[str] | None = None
    style: _core.Style | _core.DynamicStyle | None = None
    duration_milliseconds: int | _core.Expression[int | float] | None = None
    interpolation: str | _core.Expression[str] | None = None
    key: str | _core.Expression[str] | None = None


class ExpandEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.expand', ...)``.

    Attributes:
        direction: ``'horizontal'`` or ``'vertical'``.
        style: Style expanded outward from the center.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    direction: Literal['horizontal', 'vertical'] | _core.Expression[str] | None
    style: _core.Style | _core.DynamicStyle | None
    duration_milliseconds: int | _core.Expression[int | float] | None
    interpolation: str | _core.Expression[str] | None
    key: str | _core.Expression[str] | None


@dataclass
class ExpandEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.expand`` (``'effect.expand'``).

    Attributes:
        direction: ``'horizontal'`` or ``'vertical'``.
        style: Style expanded outward from the center.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.expand'
    direction: Literal['horizontal', 'vertical'] | _core.Expression[str] | None = None
    style: _core.Style | _core.DynamicStyle | None = None
    duration_milliseconds: int | _core.Expression[int | float] | None = None
    interpolation: str | _core.Expression[str] | None = None
    key: str | _core.Expression[str] | None = None


class StretchEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.stretch', ...)``.

    Attributes:
        direction: ``'left_to_right'``, ``'right_to_left'``, ``'up_to_down'`` or ``'down_to_up'``.
        style: Style stretched across the area.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    direction: (
        Literal['left_to_right', 'right_to_left', 'up_to_down', 'down_to_up']
        | _core.Expression[str]
        | None
    )
    style: _core.Style | _core.DynamicStyle | None
    duration_milliseconds: int | _core.Expression[int | float] | None
    interpolation: str | _core.Expression[str] | None
    key: str | _core.Expression[str] | None


@dataclass
class StretchEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.stretch`` (``'effect.stretch'``).

    Attributes:
        direction: ``'left_to_right'``, ``'right_to_left'``, ``'up_to_down'`` or ``'down_to_up'``.
        style: Style stretched across the area.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.stretch'
    direction: (
        Literal['left_to_right', 'right_to_left', 'up_to_down', 'down_to_up']
        | _core.Expression[str]
        | None
    ) = None
    style: _core.Style | _core.DynamicStyle | None = None
    duration_milliseconds: int | _core.Expression[int | float] | None = None
    interpolation: str | _core.Expression[str] | None = None
    key: str | _core.Expression[str] | None = None


class ExplodeEffectArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('effect.explode', ...)``.

    Attributes:
        force: Outward force throwing the cells.
        randomness: Variation in force from cell to cell.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    force: float | _core.Expression[int | float] | None
    randomness: float | _core.Expression[int | float] | None
    duration_milliseconds: int | _core.Expression[int | float] | None
    interpolation: str | _core.Expression[str] | None
    key: str | _core.Expression[str] | None


@dataclass
class ExplodeEffectCustomization(Customization):
    """
    Dataclass customization for ``Effect.explode`` (``'effect.explode'``).

    Attributes:
        force: Outward force throwing the cells.
        randomness: Variation in force from cell to cell.
        duration_milliseconds: Duration in milliseconds.
        interpolation: Easing curve name.
        key: Optional effect key for replacement or cancellation.
    """

    customization_kind = 'effect.explode'
    force: float | _core.Expression[int | float] | None = None
    randomness: float | _core.Expression[int | float] | None = None
    duration_milliseconds: int | _core.Expression[int | float] | None = None
    interpolation: str | _core.Expression[str] | None = None
    key: str | _core.Expression[str] | None = None


class AudioCustomization(Customization):
    """
    Base dataclass for audio effect customizations (``'audio.<name>'``).

    Attributes:
        customization_kind: Identifier of the audio effect customization kind.
    """

    if TYPE_CHECKING:

        def to_audio_effect(self) -> TerminalAudioEffect:
            """The [`TerminalAudioEffect`][xnano_audio.TerminalAudioEffect] this customization builds."""
            ...


class BitCrushAudioArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('audio.bit_crush', ...)``.

    Attributes:
        bits: Quantization resolution in bits (``1`` to ``16``).
        downsample: Sample-hold factor (``1`` to ``256``).
    """

    bits: int
    downsample: int


@dataclass
class BitCrushAudioCustomization(AudioCustomization):
    """
    Dataclass customization for ``TerminalAudioEffect.bit_crush`` (``'audio.bit_crush'``).

    Attributes:
        bits: Quantization resolution in bits (``1`` to ``16``).
        downsample: Sample-hold factor (``1`` to ``256``).
    """

    customization_kind = 'audio.bit_crush'
    bits: int = 8
    downsample: int = 4


class DistortionAudioArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('audio.distortion', ...)``.

    Attributes:
        drive: Input gain before soft-clipping (``0.1`` to ``100.0``).
    """

    drive: float


@dataclass
class DistortionAudioCustomization(AudioCustomization):
    """
    Dataclass customization for ``TerminalAudioEffect.distortion`` (``'audio.distortion'``).

    Attributes:
        drive: Input gain before soft-clipping (``0.1`` to ``100.0``).
    """

    customization_kind = 'audio.distortion'
    drive: float = 4.0


class LowPassAudioArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('audio.low_pass', ...)``.

    Attributes:
        cutoff: Corner frequency in hertz (``20.0`` to ``20000.0``).
        resonance: Filter resonance Q (``0.1`` to ``20.0``).
    """

    cutoff: float
    resonance: float


@dataclass
class LowPassAudioCustomization(AudioCustomization):
    """
    Dataclass customization for ``TerminalAudioEffect.low_pass`` (``'audio.low_pass'``).

    Attributes:
        cutoff: Corner frequency in hertz (``20.0`` to ``20000.0``).
        resonance: Filter resonance Q (``0.1`` to ``20.0``).
    """

    customization_kind = 'audio.low_pass'
    cutoff: float = 1200.0
    resonance: float = 0.707


class HighPassAudioArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('audio.high_pass', ...)``.

    Attributes:
        cutoff: Corner frequency in hertz (``20.0`` to ``20000.0``).
        resonance: Filter resonance Q (``0.1`` to ``20.0``).
    """

    cutoff: float
    resonance: float


@dataclass
class HighPassAudioCustomization(AudioCustomization):
    """
    Dataclass customization for ``TerminalAudioEffect.high_pass`` (``'audio.high_pass'``).

    Attributes:
        cutoff: Corner frequency in hertz (``20.0`` to ``20000.0``).
        resonance: Filter resonance Q (``0.1`` to ``20.0``).
    """

    customization_kind = 'audio.high_pass'
    cutoff: float = 400.0
    resonance: float = 0.707


class DelayAudioArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('audio.delay', ...)``.

    Attributes:
        time_milliseconds: Delay time between echoes in milliseconds (``1.0`` to ``2000.0``).
        feedback: Echo feedback ratio (``0.0`` to ``0.95``).
        mix: Wet/dry mix ratio (``0.0`` to ``1.0``).
    """

    time_milliseconds: float
    feedback: float
    mix: float


@dataclass
class DelayAudioCustomization(AudioCustomization):
    """
    Dataclass customization for ``TerminalAudioEffect.delay`` (``'audio.delay'``).

    Attributes:
        time_milliseconds: Delay time between echoes in milliseconds (``1.0`` to ``2000.0``).
        feedback: Echo feedback ratio (``0.0`` to ``0.95``).
        mix: Wet/dry mix ratio (``0.0`` to ``1.0``).
    """

    customization_kind = 'audio.delay'
    time_milliseconds: float = 250.0
    feedback: float = 0.4
    mix: float = 0.35


class ReverbAudioArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('audio.reverb', ...)``.

    Attributes:
        room: Room size (``0.0`` to ``1.0``).
        damping: High-frequency damping (``0.0`` to ``1.0``).
        mix: Wet/dry mix ratio (``0.0`` to ``1.0``).
    """

    room: float
    damping: float
    mix: float


@dataclass
class ReverbAudioCustomization(AudioCustomization):
    """
    Dataclass customization for ``TerminalAudioEffect.reverb`` (``'audio.reverb'``).

    Attributes:
        room: Room size (``0.0`` to ``1.0``).
        damping: High-frequency damping (``0.0`` to ``1.0``).
        mix: Wet/dry mix ratio (``0.0`` to ``1.0``).
    """

    customization_kind = 'audio.reverb'
    room: float = 0.5
    damping: float = 0.5
    mix: float = 0.25


class TremoloAudioArguments(TypedDict, total=False):
    """
    Keyword arguments for ``fx('audio.tremolo', ...)``.

    Attributes:
        rate_hertz: Modulation rate in hertz (``0.1`` to ``40.0``).
        depth: Modulation depth (``0.0`` to ``1.0``).
    """

    rate_hertz: float
    depth: float


@dataclass
class TremoloAudioCustomization(AudioCustomization):
    """
    Dataclass customization for ``TerminalAudioEffect.tremolo`` (``'audio.tremolo'``).

    Attributes:
        rate_hertz: Modulation rate in hertz (``0.1`` to ``40.0``).
        depth: Modulation depth (``0.0`` to ``1.0``).
    """

    customization_kind = 'audio.tremolo'
    rate_hertz: float = 5.0
    depth: float = 0.5


CustomizationKind = Literal[
    'fill',
    'write',
    'layout',
    'fuzz',
    'pixels',
    'raster',
    'effect.fade_to',
    'effect.fade_from',
    'effect.paint',
    'effect.saturate',
    'effect.lighten',
    'effect.darken',
    'effect.sweep_in',
    'effect.sweep_out',
    'effect.slide_in',
    'effect.slide_out',
    'effect.hsl_shift',
    'effect.dissolve',
    'effect.coalesce',
    'effect.glitch',
    'effect.sleep',
    'effect.evolve',
    'effect.evolve_into',
    'effect.evolve_from',
    'effect.expand',
    'effect.stretch',
    'effect.explode',
    'audio.bit_crush',
    'audio.distortion',
    'audio.low_pass',
    'audio.high_pass',
    'audio.delay',
    'audio.reverb',
    'audio.tremolo',
]

_CUSTOMIZATION_TYPES: dict[str, type[Customization]] = {
    'fill': FillCustomization,
    'write': WriteCustomization,
    'layout': LayoutCustomization,
    'fuzz': FuzzCustomization,
    'pixels': PixelsCustomization,
    'raster': RasterCustomization,
    'effect.fade_to': FadeToEffectCustomization,
    'effect.fade_from': FadeFromEffectCustomization,
    'effect.paint': PaintEffectCustomization,
    'effect.saturate': SaturateEffectCustomization,
    'effect.lighten': LightenEffectCustomization,
    'effect.darken': DarkenEffectCustomization,
    'effect.sweep_in': SweepInEffectCustomization,
    'effect.sweep_out': SweepOutEffectCustomization,
    'effect.slide_in': SlideInEffectCustomization,
    'effect.slide_out': SlideOutEffectCustomization,
    'effect.hsl_shift': HslShiftEffectCustomization,
    'effect.dissolve': DissolveEffectCustomization,
    'effect.coalesce': CoalesceEffectCustomization,
    'effect.glitch': GlitchEffectCustomization,
    'effect.sleep': SleepEffectCustomization,
    'effect.evolve': EvolveEffectCustomization,
    'effect.evolve_into': EvolveIntoEffectCustomization,
    'effect.evolve_from': EvolveFromEffectCustomization,
    'effect.expand': ExpandEffectCustomization,
    'effect.stretch': StretchEffectCustomization,
    'effect.explode': ExplodeEffectCustomization,
    'audio.bit_crush': BitCrushAudioCustomization,
    'audio.distortion': DistortionAudioCustomization,
    'audio.low_pass': LowPassAudioCustomization,
    'audio.high_pass': HighPassAudioCustomization,
    'audio.delay': DelayAudioCustomization,
    'audio.reverb': ReverbAudioCustomization,
    'audio.tremolo': TremoloAudioCustomization,
}

RenderableEffectKind = Literal[
    'effect.fade_to',
    'effect.fade_from',
    'effect.paint',
    'effect.saturate',
    'effect.lighten',
    'effect.darken',
    'effect.sweep_in',
    'effect.sweep_out',
    'effect.slide_in',
    'effect.slide_out',
    'effect.hsl_shift',
    'effect.dissolve',
    'effect.coalesce',
    'effect.glitch',
    'effect.sleep',
    'effect.evolve',
    'effect.evolve_into',
    'effect.evolve_from',
    'effect.expand',
    'effect.stretch',
    'effect.explode',
]
"""The kinds of effect that change how a buffer looks: ``fx`` kinds that start with ``'effect.'``."""

PlayableEffectKind = Literal[
    'audio.bit_crush',
    'audio.distortion',
    'audio.low_pass',
    'audio.high_pass',
    'audio.delay',
    'audio.reverb',
    'audio.tremolo',
]
"""The kinds of effect that change how a sound plays: ``fx`` kinds that start with ``'audio.'``."""

RenderableEffectArguments = (
    FadeToEffectArguments
    | FadeFromEffectArguments
    | PaintEffectArguments
    | SaturateEffectArguments
    | LightenEffectArguments
    | DarkenEffectArguments
    | SweepInEffectArguments
    | SweepOutEffectArguments
    | SlideInEffectArguments
    | SlideOutEffectArguments
    | HslShiftEffectArguments
    | DissolveEffectArguments
    | CoalesceEffectArguments
    | GlitchEffectArguments
    | SleepEffectArguments
    | EvolveEffectArguments
    | EvolveIntoEffectArguments
    | EvolveFromEffectArguments
    | ExpandEffectArguments
    | StretchEffectArguments
    | ExplodeEffectArguments
)
"""The keyword arguments of ``fx(kind, ...)`` and ``context.fx(kind, ...)`` for a visual effect."""

PlayableEffectArguments = (
    BitCrushAudioArguments
    | DistortionAudioArguments
    | LowPassAudioArguments
    | HighPassAudioArguments
    | DelayAudioArguments
    | ReverbAudioArguments
    | TremoloAudioArguments
)
"""The keyword arguments of ``fx(kind, ...)`` and ``context.fx(kind, ...)`` for a sound effect."""


class FadeToEffectSpecification(FadeToEffectArguments):
    """
    The dictionary form of the ``'effect.fade_to'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.fade_to'``.
    """

    kind: Required[Literal['effect.fade_to']]


class FadeFromEffectSpecification(FadeFromEffectArguments):
    """
    The dictionary form of the ``'effect.fade_from'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.fade_from'``.
    """

    kind: Required[Literal['effect.fade_from']]


class PaintEffectSpecification(PaintEffectArguments):
    """
    The dictionary form of the ``'effect.paint'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.paint'``.
    """

    kind: Required[Literal['effect.paint']]


class SaturateEffectSpecification(SaturateEffectArguments):
    """
    The dictionary form of the ``'effect.saturate'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.saturate'``.
    """

    kind: Required[Literal['effect.saturate']]


class LightenEffectSpecification(LightenEffectArguments):
    """
    The dictionary form of the ``'effect.lighten'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.lighten'``.
    """

    kind: Required[Literal['effect.lighten']]


class DarkenEffectSpecification(DarkenEffectArguments):
    """
    The dictionary form of the ``'effect.darken'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.darken'``.
    """

    kind: Required[Literal['effect.darken']]


class SweepInEffectSpecification(SweepInEffectArguments):
    """
    The dictionary form of the ``'effect.sweep_in'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.sweep_in'``.
    """

    kind: Required[Literal['effect.sweep_in']]


class SweepOutEffectSpecification(SweepOutEffectArguments):
    """
    The dictionary form of the ``'effect.sweep_out'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.sweep_out'``.
    """

    kind: Required[Literal['effect.sweep_out']]


class SlideInEffectSpecification(SlideInEffectArguments):
    """
    The dictionary form of the ``'effect.slide_in'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.slide_in'``.
    """

    kind: Required[Literal['effect.slide_in']]


class SlideOutEffectSpecification(SlideOutEffectArguments):
    """
    The dictionary form of the ``'effect.slide_out'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.slide_out'``.
    """

    kind: Required[Literal['effect.slide_out']]


class HslShiftEffectSpecification(HslShiftEffectArguments):
    """
    The dictionary form of the ``'effect.hsl_shift'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.hsl_shift'``.
    """

    kind: Required[Literal['effect.hsl_shift']]


class DissolveEffectSpecification(DissolveEffectArguments):
    """
    The dictionary form of the ``'effect.dissolve'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.dissolve'``.
    """

    kind: Required[Literal['effect.dissolve']]


class CoalesceEffectSpecification(CoalesceEffectArguments):
    """
    The dictionary form of the ``'effect.coalesce'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.coalesce'``.
    """

    kind: Required[Literal['effect.coalesce']]


class GlitchEffectSpecification(GlitchEffectArguments):
    """
    The dictionary form of the ``'effect.glitch'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.glitch'``.
    """

    kind: Required[Literal['effect.glitch']]


class SleepEffectSpecification(SleepEffectArguments):
    """
    The dictionary form of the ``'effect.sleep'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.sleep'``.
    """

    kind: Required[Literal['effect.sleep']]


class EvolveEffectSpecification(EvolveEffectArguments):
    """
    The dictionary form of the ``'effect.evolve'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.evolve'``.
    """

    kind: Required[Literal['effect.evolve']]


class EvolveIntoEffectSpecification(EvolveIntoEffectArguments):
    """
    The dictionary form of the ``'effect.evolve_into'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.evolve_into'``.
    """

    kind: Required[Literal['effect.evolve_into']]


class EvolveFromEffectSpecification(EvolveFromEffectArguments):
    """
    The dictionary form of the ``'effect.evolve_from'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.evolve_from'``.
    """

    kind: Required[Literal['effect.evolve_from']]


class ExpandEffectSpecification(ExpandEffectArguments):
    """
    The dictionary form of the ``'effect.expand'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.expand'``.
    """

    kind: Required[Literal['effect.expand']]


class StretchEffectSpecification(StretchEffectArguments):
    """
    The dictionary form of the ``'effect.stretch'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.stretch'``.
    """

    kind: Required[Literal['effect.stretch']]


class ExplodeEffectSpecification(ExplodeEffectArguments):
    """
    The dictionary form of the ``'effect.explode'`` visual effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'effect.explode'``.
    """

    kind: Required[Literal['effect.explode']]


class BitCrushAudioSpecification(BitCrushAudioArguments):
    """
    The dictionary form of the ``'audio.bit_crush'`` sound effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'audio.bit_crush'``.
    """

    kind: Required[Literal['audio.bit_crush']]


class DistortionAudioSpecification(DistortionAudioArguments):
    """
    The dictionary form of the ``'audio.distortion'`` sound effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'audio.distortion'``.
    """

    kind: Required[Literal['audio.distortion']]


class LowPassAudioSpecification(LowPassAudioArguments):
    """
    The dictionary form of the ``'audio.low_pass'`` sound effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'audio.low_pass'``.
    """

    kind: Required[Literal['audio.low_pass']]


class HighPassAudioSpecification(HighPassAudioArguments):
    """
    The dictionary form of the ``'audio.high_pass'`` sound effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'audio.high_pass'``.
    """

    kind: Required[Literal['audio.high_pass']]


class DelayAudioSpecification(DelayAudioArguments):
    """
    The dictionary form of the ``'audio.delay'`` sound effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'audio.delay'``.
    """

    kind: Required[Literal['audio.delay']]


class ReverbAudioSpecification(ReverbAudioArguments):
    """
    The dictionary form of the ``'audio.reverb'`` sound effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'audio.reverb'``.
    """

    kind: Required[Literal['audio.reverb']]


class TremoloAudioSpecification(TremoloAudioArguments):
    """
    The dictionary form of the ``'audio.tremolo'`` sound effect in ``effects=[...]``.

    Attributes:
        kind: Always ``'audio.tremolo'``.
    """

    kind: Required[Literal['audio.tremolo']]


RenderableEffectSpecification = (
    FadeToEffectSpecification
    | FadeFromEffectSpecification
    | PaintEffectSpecification
    | SaturateEffectSpecification
    | LightenEffectSpecification
    | DarkenEffectSpecification
    | SweepInEffectSpecification
    | SweepOutEffectSpecification
    | SlideInEffectSpecification
    | SlideOutEffectSpecification
    | HslShiftEffectSpecification
    | DissolveEffectSpecification
    | CoalesceEffectSpecification
    | GlitchEffectSpecification
    | SleepEffectSpecification
    | EvolveEffectSpecification
    | EvolveIntoEffectSpecification
    | EvolveFromEffectSpecification
    | ExpandEffectSpecification
    | StretchEffectSpecification
    | ExplodeEffectSpecification
)
"""One visual effect as a dictionary for ``effects=[...]``: its ``kind`` and its keywords."""

PlayableEffectSpecification = (
    BitCrushAudioSpecification
    | DistortionAudioSpecification
    | LowPassAudioSpecification
    | HighPassAudioSpecification
    | DelayAudioSpecification
    | ReverbAudioSpecification
    | TremoloAudioSpecification
)
"""One sound effect as a dictionary for ``effects=[...]``: its ``kind`` and its keywords."""

RenderableEffect = (
    FadeToEffectCustomization
    | FadeFromEffectCustomization
    | PaintEffectCustomization
    | SaturateEffectCustomization
    | LightenEffectCustomization
    | DarkenEffectCustomization
    | SweepInEffectCustomization
    | SweepOutEffectCustomization
    | SlideInEffectCustomization
    | SlideOutEffectCustomization
    | HslShiftEffectCustomization
    | DissolveEffectCustomization
    | CoalesceEffectCustomization
    | GlitchEffectCustomization
    | SleepEffectCustomization
    | EvolveEffectCustomization
    | EvolveIntoEffectCustomization
    | EvolveFromEffectCustomization
    | ExpandEffectCustomization
    | StretchEffectCustomization
    | ExplodeEffectCustomization
)
"""A visual effect as ``fx(...)`` and ``context.fx(...)`` return it."""

PlayableEffect = (
    BitCrushAudioCustomization
    | DistortionAudioCustomization
    | LowPassAudioCustomization
    | HighPassAudioCustomization
    | DelayAudioCustomization
    | ReverbAudioCustomization
    | TremoloAudioCustomization
)
"""A sound effect as ``fx(...)`` and ``context.fx(...)`` return it."""

Effect = RenderableEffect | PlayableEffect
"""Any visual or sound effect."""


@overload
def fx(
    kind: Literal['fill'], /, **parameters: Unpack[FillArguments]
) -> FillCustomization: ...
@overload
def fx(
    kind: Literal['write'], /, **parameters: Unpack[WriteArguments]
) -> WriteCustomization: ...
@overload
def fx(
    kind: Literal['layout'], /, **parameters: Unpack[LayoutArguments]
) -> LayoutCustomization: ...
@overload
def fx(
    kind: Literal['fuzz'], /, **parameters: Unpack[FuzzArguments]
) -> FuzzCustomization: ...
@overload
def fx(
    kind: Literal['pixels'], /, **parameters: Unpack[PixelsArguments]
) -> PixelsCustomization: ...
@overload
def fx(
    kind: Literal['raster'], /, **parameters: Unpack[RasterArguments]
) -> RasterCustomization: ...
@overload
def fx(
    kind: Literal['effect.fade_to'], /, **parameters: Unpack[FadeToEffectArguments]
) -> FadeToEffectCustomization: ...
@overload
def fx(
    kind: Literal['effect.fade_from'], /, **parameters: Unpack[FadeFromEffectArguments]
) -> FadeFromEffectCustomization: ...
@overload
def fx(
    kind: Literal['effect.paint'], /, **parameters: Unpack[PaintEffectArguments]
) -> PaintEffectCustomization: ...
@overload
def fx(
    kind: Literal['effect.saturate'], /, **parameters: Unpack[SaturateEffectArguments]
) -> SaturateEffectCustomization: ...
@overload
def fx(
    kind: Literal['effect.lighten'], /, **parameters: Unpack[LightenEffectArguments]
) -> LightenEffectCustomization: ...
@overload
def fx(
    kind: Literal['effect.darken'], /, **parameters: Unpack[DarkenEffectArguments]
) -> DarkenEffectCustomization: ...
@overload
def fx(
    kind: Literal['effect.sweep_in'], /, **parameters: Unpack[SweepInEffectArguments]
) -> SweepInEffectCustomization: ...
@overload
def fx(
    kind: Literal['effect.sweep_out'], /, **parameters: Unpack[SweepOutEffectArguments]
) -> SweepOutEffectCustomization: ...
@overload
def fx(
    kind: Literal['effect.slide_in'], /, **parameters: Unpack[SlideInEffectArguments]
) -> SlideInEffectCustomization: ...
@overload
def fx(
    kind: Literal['effect.slide_out'], /, **parameters: Unpack[SlideOutEffectArguments]
) -> SlideOutEffectCustomization: ...
@overload
def fx(
    kind: Literal['effect.hsl_shift'], /, **parameters: Unpack[HslShiftEffectArguments]
) -> HslShiftEffectCustomization: ...
@overload
def fx(
    kind: Literal['effect.dissolve'], /, **parameters: Unpack[DissolveEffectArguments]
) -> DissolveEffectCustomization: ...
@overload
def fx(
    kind: Literal['effect.coalesce'], /, **parameters: Unpack[CoalesceEffectArguments]
) -> CoalesceEffectCustomization: ...
@overload
def fx(
    kind: Literal['effect.glitch'], /, **parameters: Unpack[GlitchEffectArguments]
) -> GlitchEffectCustomization: ...
@overload
def fx(
    kind: Literal['effect.sleep'], /, **parameters: Unpack[SleepEffectArguments]
) -> SleepEffectCustomization: ...
@overload
def fx(
    kind: Literal['effect.evolve'], /, **parameters: Unpack[EvolveEffectArguments]
) -> EvolveEffectCustomization: ...
@overload
def fx(
    kind: Literal['effect.evolve_into'],
    /,
    **parameters: Unpack[EvolveIntoEffectArguments],
) -> EvolveIntoEffectCustomization: ...
@overload
def fx(
    kind: Literal['effect.evolve_from'],
    /,
    **parameters: Unpack[EvolveFromEffectArguments],
) -> EvolveFromEffectCustomization: ...
@overload
def fx(
    kind: Literal['effect.expand'], /, **parameters: Unpack[ExpandEffectArguments]
) -> ExpandEffectCustomization: ...
@overload
def fx(
    kind: Literal['effect.stretch'], /, **parameters: Unpack[StretchEffectArguments]
) -> StretchEffectCustomization: ...
@overload
def fx(
    kind: Literal['effect.explode'], /, **parameters: Unpack[ExplodeEffectArguments]
) -> ExplodeEffectCustomization: ...
@overload
def fx(
    kind: Literal['audio.bit_crush'], /, **parameters: Unpack[BitCrushAudioArguments]
) -> BitCrushAudioCustomization: ...
@overload
def fx(
    kind: Literal['audio.distortion'],
    /,
    **parameters: Unpack[DistortionAudioArguments],
) -> DistortionAudioCustomization: ...
@overload
def fx(
    kind: Literal['audio.low_pass'], /, **parameters: Unpack[LowPassAudioArguments]
) -> LowPassAudioCustomization: ...
@overload
def fx(
    kind: Literal['audio.high_pass'], /, **parameters: Unpack[HighPassAudioArguments]
) -> HighPassAudioCustomization: ...
@overload
def fx(
    kind: Literal['audio.delay'], /, **parameters: Unpack[DelayAudioArguments]
) -> DelayAudioCustomization: ...
@overload
def fx(
    kind: Literal['audio.reverb'], /, **parameters: Unpack[ReverbAudioArguments]
) -> ReverbAudioCustomization: ...
@overload
def fx(
    kind: Literal['audio.tremolo'], /, **parameters: Unpack[TremoloAudioArguments]
) -> TremoloAudioCustomization: ...
def fx(kind: CustomizationKind, /, **parameters: object) -> Customization:
    """
    Create a typed dataclass customization for a fill, layout,
    pixels, visual effect (``'effect.<name>'``) or audio effect (``'audio.<name>'``).

    Each ``kind`` overloads the keyword arguments with ``Unpack`` over its corresponding
    ``TypedDict`` and returns the matching [`Customization`][xnano._customize.Customization]
    dataclass. The returned dataclass can be inspected, mutated, returned from an
    [`hook`][xnano.operations.hook], piped with ``|``, or passed to ``add`` and
    ``update``.

    Args:
        kind: Which customization to create (such as ``'fill'``, ``'layout'``,
            ``'pixels'``, ``'effect.dissolve'``,
            ``'effect.fade_to'`` or ``'audio.reverb'``).
        parameters: Keyword arguments for the chosen customization kind.

    Raises:
        ValueError: ``kind`` is not a recognized customization kind.

    Examples:
        ```python
        import xnano

        from xnano.operations import fx

        sparkle = fx('fill', cell='*')
        assert sparkle.cell == '*'

        fade = fx('effect.fade_to', foreground='red', duration_milliseconds=200)
        assert fade.duration_milliseconds == 200

        with xnano.new(width=10, height=3) as canvas:
            canvas | sparkle
            assert '*' in canvas.render()
        ```
    """
    customization_class = _CUSTOMIZATION_TYPES.get(kind)
    if customization_class is None:
        valid = ', '.join(sorted(_CUSTOMIZATION_TYPES))
        raise ValueError(
            f'{kind!r} is not a known customization kind. Choose one of: {valid}.'
        )
    factory = cast('Callable[..., Customization]', customization_class)
    return factory(**parameters)


def normalize_effect(
    specification: object, expected: Literal['renderable', 'playable']
) -> Customization:
    """
    Turn one entry of an ``effects=[...]`` list into the effect it describes.

    Args:
        specification: A dictionary with a ``kind`` key and that effect's keywords, such as
            ``{'kind': 'effect.fade_to', 'foreground': 'red'}``.
        expected: ``'renderable'`` for a list that styles a buffer, ``'playable'`` for a list
            that styles a sound.

    Returns:
        The effect, not yet applied to anything.

    Raises:
        TypeError: The entry is not such a dictionary, or its ``kind`` belongs to the other
            list or is not an effect.
        ValueError: The ``kind`` looks like an effect but is not a known one.
    """
    is_renderable = expected == 'renderable'
    prefix = 'effect.' if is_renderable else 'audio.'
    sample = 'effect.fade_to' if is_renderable else 'audio.reverb'
    example = f"{{'kind': {sample!r}, ...}}"
    if not isinstance(specification, Mapping) or 'kind' not in specification:
        if not isinstance(specification, Customization):
            hint = "Write each effect as a dictionary with a 'kind' key."
        elif is_renderable:
            hint = (
                'An fx(...) object is applied with placement | fx(...) or '
                'placement.update(fx(...)).'
            )
        else:
            hint = 'An fx(...) object is not accepted here; write the effect as a dictionary.'
        raise TypeError(
            f'effects= takes dictionaries such as {example}, but got {specification!r}. {hint}'
        )
    parameters = dict(specification)
    kind = parameters.pop('kind')
    if not isinstance(kind, str):
        raise TypeError(
            f"The 'kind' of an effect is a string such as {sample!r}, but was {kind!r}."
        )
    if kind.startswith(prefix):
        return fx(cast('CustomizationKind', kind), **parameters)  # type: ignore[call-overload]
    if kind.startswith(('effect.', 'audio.')):
        if is_renderable:
            raise TypeError(
                f'{kind!r} is a sound effect; pass it to play(effects=...) or '
                f'note(effects=...), not to a visual list such as write(effects=...). '
                f"Visual effects have kinds that start with 'effect.', such as "
                f"'effect.fade_to'."
            )
        raise TypeError(
            f'{kind!r} is a visual effect; pass it to write(effects=...) or '
            f'draw(effects=...), not to a sound. Sound effects have kinds that start with '
            f"'audio.', such as 'audio.reverb'."
        )
    noun = 'a visual effect' if is_renderable else 'a sound effect'
    raise TypeError(
        f'{kind!r} is not {noun}, so it cannot be in effects=. Use a kind that starts with '
        f"'{prefix}', such as {sample!r}."
    )


def apply_effects(
    target: Canvas[object, object] | Placement[object, object],
    effects: Sequence[RenderableEffectSpecification],
) -> list[Customization]:
    """
    Start each effect of an ``effects=[...]`` list on ``target`` and return the live handles.

    Args:
        target: The canvas or placement the effects run on.
        effects: Dictionaries with a ``kind`` key naming a visual effect, such as
            ``{'kind': 'effect.fade_to', 'foreground': 'red'}``, and that effect's keywords.

    Raises:
        TypeError: An entry is not such a dictionary, or names something that is not a
            visual effect.
    """
    applied: list[Customization] = []
    for specification in effects:
        customization = normalize_effect(specification, 'renderable')
        customization.apply_to(target)
        applied.append(customization)
    return applied
