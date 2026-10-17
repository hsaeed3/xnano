"""
xnano.pixel

One cell or dot of a region: a character with a foreground and a background color.
"""

from __future__ import annotations

import dataclasses
import difflib
from typing import TYPE_CHECKING, Final, Literal, TypeAlias, get_args

import xnano_core as _core
from xnano import symbols
from xnano._values import ColorValue

if TYPE_CHECKING:
    from xnano.context import Context

__all__ = ['Pixel', 'PixelPreset']

PixelPreset: TypeAlias = Literal[
    'block',
    'half_top',
    'half_bottom',
    'shade_light',
    'shade_medium',
    'shade_dark',
    'braille',
    'circle',
    'circle_outline',
    'dot',
    'diamond',
    'star',
    'line_horizontal',
    'line_vertical',
    'corner_top_left_rounded',
    'corner_top_right_rounded',
    'corner_bottom_left_rounded',
    'corner_bottom_right_rounded',
    'corner_top_left_square',
    'corner_top_right_square',
    'corner_bottom_left_square',
    'corner_bottom_right_square',
    'arrow_up',
    'arrow_down',
    'arrow_left',
    'arrow_right',
    'check',
    'cross',
]
"""The names of the characters ``Pixel`` knows: ``Pixel('diamond')`` draws ``◆``."""

_PRESET_CHARACTERS: Final[dict[str, str]] = {
    'block': '█',
    'half_top': '▀',
    'half_bottom': '▄',
    'shade_light': '░',
    'shade_medium': '▒',
    'shade_dark': '▓',
    'braille': '⠀',
    'circle': '●',
    'circle_outline': '○',
    'dot': '•',
    'diamond': '◆',
    'star': '★',
    'line_horizontal': '─',
    'line_vertical': '│',
    'corner_top_left_rounded': '╭',
    'corner_top_right_rounded': '╮',
    'corner_bottom_left_rounded': '╰',
    'corner_bottom_right_rounded': '╯',
    'corner_top_left_square': '┌',
    'corner_top_right_square': '┐',
    'corner_bottom_left_square': '└',
    'corner_bottom_right_square': '┘',
    'arrow_up': '↑',
    'arrow_down': '↓',
    'arrow_left': '←',
    'arrow_right': '→',
    'check': '✓',
    'cross': '✗',
}
assert set(_PRESET_CHARACTERS) == set(get_args(PixelPreset))


def _unknown_name_error(name: str) -> ValueError:
    """Say that a name is neither a preset nor a symbol, with the closest names first."""
    registered = symbols.names(kind=Pixel)
    known = [*_PRESET_CHARACTERS, *registered]
    close = difflib.get_close_matches(name, known, n=3)
    hint = f' Did you mean {" or ".join(repr(item) for item in close)}?' if close else ''
    listed = ', '.join(repr(item) for item in registered) if registered else 'none yet'
    return ValueError(
        f'{name!r} is not a pixel preset or a known symbol.{hint} Presets: '
        f'{", ".join(_PRESET_CHARACTERS)}. Pixel symbols: {listed}. A single character '
        f'is drawn as it is, and symbol={name!r} registers a pixel under that name when '
        f'you create it.'
    )


@dataclasses.dataclass(frozen=True, slots=True, init=False)
class Pixel:
    """
    One cell (or one dot, at half-block and braille resolution) of a region.

    The first argument is a preset name such as ``'diamond'``, the name of a registered
    symbol, or a single character that is drawn as it is. A pixel is a value: it compares by
    its fields, and ``region[x, y]`` returns one and accepts one.

    Args:
        preset_or_character: A [`PixelPreset`][xnano.pixel.PixelPreset], the name of a
            registered symbol, or one character.
        foreground: The color of the character.
        background: The color behind the character.
        symbol: A name to register this pixel under, so that ``Pixel('wall')`` finds it
            later. The name takes two characters or more; see
            [`register`][xnano.symbols.register].

    Attributes:
        character: The glyph drawn in the cell or dot.
        foreground: The color of the glyph, or ``None`` for the cell's own.
        background: The color behind the glyph, or ``None`` for the cell's own.
        symbol: The registered symbol name, or ``None``.

    Raises:
        ValueError: The name is not a preset or a registered symbol (the message lists both
            and the closest names first), or the character is empty.

    Examples:
        ```python
        import xnano
        from xnano import Pixel

        diamond = Pixel('diamond', foreground='red')
        assert diamond.character == '◆'
        assert Pixel('x').character == 'x'

        with xnano.new(width=4, height=1) as canvas:
            canvas.region[1, 0] = diamond
            assert canvas.region[1, 0].character == '◆'
        ```
    """

    character: str
    """The glyph drawn in the cell or dot."""
    foreground: ColorValue | None
    """The color of the glyph, or ``None`` for the cell's own."""
    background: ColorValue | None
    """The color behind the glyph, or ``None`` for the cell's own."""
    symbol: str | None
    """The registered symbol name, or ``None``."""
    _cell: _core.Cell | None = dataclasses.field(
        default=None, init=False, repr=False, compare=False
    )

    def __init__(
        self,
        preset_or_character: PixelPreset | str = 'block',
        foreground: ColorValue | None = None,
        background: ColorValue | None = None,
        symbol: str | None = None,
    ) -> None:
        """
        Make a pixel from a preset, a symbol name or a character.

        Args:
            preset_or_character: A preset name, a registered symbol name or one character.
            foreground: The color of the character.
            background: The color behind the character.
            symbol: A name to register this pixel under.
        """
        if not isinstance(preset_or_character, str) or not preset_or_character:
            raise ValueError(
                f'A pixel is made from a preset name, a symbol name or one character, but '
                f'got {preset_or_character!r}. Try Pixel("block") or Pixel("#").'
            )
        name = preset_or_character
        known_symbol: str | None = None
        if len(name) == 1:
            character = name
        elif name in _PRESET_CHARACTERS:
            character = _PRESET_CHARACTERS[name]
        elif name in symbols.names(kind=Pixel):
            registered = symbols.lookup(name, kind=Pixel)
            character = registered.character
            foreground = registered.foreground if foreground is None else foreground
            background = registered.background if background is None else background
            known_symbol = name
        else:
            raise _unknown_name_error(name)
        object.__setattr__(self, 'character', character)
        object.__setattr__(self, 'foreground', foreground)
        object.__setattr__(self, 'background', background)
        object.__setattr__(self, 'symbol', symbol if symbol is not None else known_symbol)
        object.__setattr__(self, '_cell', None)
        if symbol is not None:
            symbols.register(symbol, self)

    @classmethod
    def _of(
        cls,
        character: str,
        foreground: ColorValue | None = None,
        background: ColorValue | None = None,
    ) -> Pixel:
        """Make a pixel of exactly this character, whatever its length."""
        pixel = object.__new__(cls)
        object.__setattr__(pixel, 'character', character)
        object.__setattr__(pixel, 'foreground', foreground)
        object.__setattr__(pixel, 'background', background)
        object.__setattr__(pixel, 'symbol', None)
        object.__setattr__(pixel, '_cell', None)
        return pixel

    def cell(self) -> _core.Cell:
        """
        Return the core cell that draws this pixel.

        The cell is built once and kept, so writing the same pixel many times is cheap.
        """
        built = self._cell
        if built is None:
            built = _core.Cell(
                self.character,
                foreground=self.foreground,
                background=self.background,
            )
            object.__setattr__(self, '_cell', built)
        return built

    def __str__(self) -> str:
        """Return the character of the pixel, so ``print(pixel)`` shows what it draws."""
        return self.character

    def __xnano_render__(self, context: Context | None = None) -> _core.Buffer:
        """Return a buffer of one cell that shows the pixel."""
        buffer = _core.Buffer(width=1, height=1)
        buffer[0, 0] = self.cell()
        return buffer
