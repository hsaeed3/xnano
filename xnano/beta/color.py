"""xnano.beta.color

Functional color types and utilities. This module ports many of it's
primitives directly from the ``pydantic_extra_types.Color`` module.

You can view the original source code here:

[Color](https://github.com/pydantic/pydantic-extra-types/blob/main/pydantic_extra_types/color.py)
"""

from __future__ import annotations

import dataclasses
import re
from typing import Any, ClassVar, Literal, TypeAlias, Union, cast


_TAILWIND_CACHE: dict[tuple[str, int], Color] = {}


ColorLike: TypeAlias = Union["ColorName", str, "ColorTuple", "Color"]
"""A color-like input.

This can be any one of:
    - A known color name.
    - A hex color string
    - A tuple of 3 or 4 integers representing RGB or RGBA components
    - A ``Color`` instance

Example:
    >>> ColorLike = "red" | "aliceblue" | "black"
    >>> ColorLike = "#FF0000"
    >>> ColorLike = (255, 0, 0)
    >>> ColorLike = (255, 0, 0, 1.0)
    >>> ColorLike = Color(r=255, g=0, b=0)
"""


ColorTuple = Union[tuple[int, int, int], tuple[int, int, int, float]]
"""A tuple of either three or four integers representing the
RGB (red, green, blue) or RGBA (red, green, blue, alpha) components
of a color.
"""


ColorName: TypeAlias = Literal[
    "aliceblue",
    "antiquewhite",
    "aqua",
    "aquamarine",
    "azure",
    "beige",
    "bisque",
    "black",
    "blanchedalmond",
    "blue",
    "blueviolet",
    "brown",
    "burlywood",
    "cadetblue",
    "chartreuse",
    "chocolate",
    "coral",
    "cornflowerblue",
    "cornsilk",
    "crimson",
    "cyan",
    "darkblue",
    "darkcyan",
    "darkgoldenrod",
    "darkgray",
    "darkgreen",
    "darkgrey",
    "darkkhaki",
    "darkmagenta",
    "darkolivegreen",
    "darkorange",
    "darkorchid",
    "darkred",
    "darksalmon",
    "darkseagreen",
    "darkslateblue",
    "darkslategray",
    "darkslategrey",
    "darkturquoise",
    "darkviolet",
    "deeppink",
    "deepskyblue",
    "dimgray",
    "dimgrey",
    "dodgerblue",
    "firebrick",
    "floralwhite",
    "forestgreen",
    "fuchsia",
    "gainsboro",
    "ghostwhite",
    "gold",
    "goldenrod",
    "gray",
    "green",
    "greenyellow",
    "grey",
    "honeydew",
    "hotpink",
    "indianred",
    "indigo",
    "ivory",
    "khaki",
    "lavender",
    "lavenderblush",
    "lawngreen",
    "lemonchiffon",
    "lightblue",
    "lightcoral",
    "lightcyan",
    "lightgoldenrodyellow",
    "lightgray",
    "lightgreen",
    "lightgrey",
    "lightpink",
    "lightsalmon",
    "lightseagreen",
    "lightskyblue",
    "lightslategray",
    "lightslategrey",
    "lightsteelblue",
    "lightyellow",
    "lime",
    "limegreen",
    "linen",
    "magenta",
    "maroon",
    "mediumaquamarine",
    "mediumblue",
    "mediumorchid",
    "mediumpurple",
    "mediumseagreen",
    "mediumslateblue",
    "mediumspringgreen",
    "mediumturquoise",
    "mediumvioletred",
    "midnightblue",
    "mintcream",
    "mistyrose",
    "moccasin",
    "navajowhite",
    "navy",
    "oldlace",
    "olive",
    "olivedrab",
    "orange",
    "orangered",
    "orchid",
    "palegoldenrod",
    "palegreen",
    "paleturquoise",
    "palevioletred",
    "papayawhip",
    "peachpuff",
    "peru",
    "pink",
    "plum",
    "powderblue",
    "purple",
    "red",
    "rosybrown",
    "royalblue",
    "saddlebrown",
    "salmon",
    "sandybrown",
    "seagreen",
    "seashell",
    "sienna",
    "silver",
    "skyblue",
    "slateblue",
    "slategray",
    "slategrey",
    "snow",
    "springgreen",
    "steelblue",
    "tan",
    "teal",
    "thistle",
    "tomato",
    "turquoise",
    "violet",
    "wheat",
    "white",
    "whitesmoke",
    "yellow",
    "yellowgreen",
]
"""Known color names ported from ``pydantic_extra_types.Color``."""


TailwindColorName: TypeAlias = Literal[
    "amber",
    "black",
    "blue",
    "cyan",
    "emerald",
    "fuchsia",
    "gray",
    "green",
    "indigo",
    "lime",
    "neutral",
    "orange",
    "pink",
    "purple",
    "red",
    "rose",
    "sky",
    "slate",
    "stone",
    "teal",
    "violet",
    "white",
    "yellow",
    "zinc",
]
"""Known color palette names from Tailwind CSS."""


TailwindColorShade: TypeAlias = Literal[
    50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950
]
"""Accepted color shade values for setting tailwind colors, including all officially supported
Tailwind CSS shade values."""


@dataclasses.dataclass(frozen=True, slots=True, repr=False)
class Color:
    """A color in the RGBA space that can be defined from a variety
    of formats. This can be initialized with an RGB or RGBA
    color value, or through one of the factory class methods
    that parse a variety of formats.

    Many implementation details within this class are ported directly from
    the ``pydantic_extra_types.Color`` module. You can view the original
    source code here:

    [Color](https://github.com/pydantic/pydantic-extra-types/blob/main/pydantic_extra_types/color.py)

    Attributes:
        r: The red component of this color.
        g: The green component of this color.
        b: The blue component of this color.
        a: The alpha component of this color. (Defaults to 255.0
            if not provided.)
    """

    COLORS_BY_NAME: ClassVar[dict[ColorName, ColorTuple]] = {
        "aliceblue": (240, 248, 255),
        "antiquewhite": (250, 235, 215),
        "aqua": (0, 255, 255),
        "aquamarine": (127, 255, 212),
        "azure": (240, 255, 255),
        "beige": (245, 245, 220),
        "bisque": (255, 228, 196),
        "black": (0, 0, 0),
        "blanchedalmond": (255, 235, 205),
        "blue": (0, 0, 255),
        "blueviolet": (138, 43, 226),
        "brown": (165, 42, 42),
        "burlywood": (222, 184, 135),
        "cadetblue": (95, 158, 160),
        "chartreuse": (127, 255, 0),
        "chocolate": (210, 105, 30),
        "coral": (255, 127, 80),
        "cornflowerblue": (100, 149, 237),
        "cornsilk": (255, 248, 220),
        "crimson": (220, 20, 60),
        "cyan": (0, 255, 255),
        "darkblue": (0, 0, 139),
        "darkcyan": (0, 139, 139),
        "darkgoldenrod": (184, 134, 11),
        "darkgray": (169, 169, 169),
        "darkgreen": (0, 100, 0),
        "darkgrey": (169, 169, 169),
        "darkkhaki": (189, 183, 107),
        "darkmagenta": (139, 0, 139),
        "darkolivegreen": (85, 107, 47),
        "darkorange": (255, 140, 0),
        "darkorchid": (153, 50, 204),
        "darkred": (139, 0, 0),
        "darksalmon": (233, 150, 122),
        "darkseagreen": (143, 188, 143),
        "darkslateblue": (72, 61, 139),
        "darkslategray": (47, 79, 79),
        "darkslategrey": (47, 79, 79),
        "darkturquoise": (0, 206, 209),
        "darkviolet": (148, 0, 211),
        "deeppink": (255, 20, 147),
        "deepskyblue": (0, 191, 255),
        "dimgray": (105, 105, 105),
        "dimgrey": (105, 105, 105),
        "dodgerblue": (30, 144, 255),
        "firebrick": (178, 34, 34),
        "floralwhite": (255, 250, 240),
        "forestgreen": (34, 139, 34),
        "fuchsia": (255, 0, 255),
        "gainsboro": (220, 220, 220),
        "ghostwhite": (248, 248, 255),
        "gold": (255, 215, 0),
        "goldenrod": (218, 165, 32),
        "gray": (128, 128, 128),
        "green": (0, 128, 0),
        "greenyellow": (173, 255, 47),
        "grey": (128, 128, 128),
        "honeydew": (240, 255, 240),
        "hotpink": (255, 105, 180),
        "indianred": (205, 92, 92),
        "indigo": (75, 0, 130),
        "ivory": (255, 255, 240),
        "khaki": (240, 230, 140),
        "lavender": (230, 230, 250),
        "lavenderblush": (255, 240, 245),
        "lawngreen": (124, 252, 0),
        "lemonchiffon": (255, 250, 205),
        "lightblue": (173, 216, 230),
        "lightcoral": (240, 128, 128),
        "lightcyan": (224, 255, 255),
        "lightgoldenrodyellow": (250, 250, 210),
        "lightgray": (211, 211, 211),
        "lightgreen": (144, 238, 144),
        "lightgrey": (211, 211, 211),
        "lightpink": (255, 182, 193),
        "lightsalmon": (255, 160, 122),
        "lightseagreen": (32, 178, 170),
        "lightskyblue": (135, 206, 250),
        "lightslategray": (119, 136, 153),
        "lightslategrey": (119, 136, 153),
        "lightsteelblue": (176, 196, 222),
        "lightyellow": (255, 255, 224),
        "lime": (0, 255, 0),
        "limegreen": (50, 205, 50),
        "linen": (250, 240, 230),
        "magenta": (255, 0, 255),
        "maroon": (128, 0, 0),
        "mediumaquamarine": (102, 205, 170),
        "mediumblue": (0, 0, 205),
        "mediumorchid": (186, 85, 211),
        "mediumpurple": (147, 112, 219),
        "mediumseagreen": (60, 179, 113),
        "mediumslateblue": (123, 104, 238),
        "mediumspringgreen": (0, 250, 154),
        "mediumturquoise": (72, 209, 204),
        "mediumvioletred": (199, 21, 133),
        "midnightblue": (25, 25, 112),
        "mintcream": (245, 255, 250),
        "mistyrose": (255, 228, 225),
        "moccasin": (255, 228, 181),
        "navajowhite": (255, 222, 173),
        "navy": (0, 0, 128),
        "oldlace": (253, 245, 230),
        "olive": (128, 128, 0),
        "olivedrab": (107, 142, 35),
        "orange": (255, 165, 0),
        "orangered": (255, 69, 0),
        "orchid": (218, 112, 214),
        "palegoldenrod": (238, 232, 170),
        "palegreen": (152, 251, 152),
        "paleturquoise": (175, 238, 238),
        "palevioletred": (219, 112, 147),
        "papayawhip": (255, 239, 213),
        "peachpuff": (255, 218, 185),
        "peru": (205, 133, 63),
        "pink": (255, 192, 203),
        "plum": (221, 160, 221),
        "powderblue": (176, 224, 230),
        "purple": (128, 0, 128),
        "red": (255, 0, 0),
        "rosybrown": (188, 143, 143),
        "royalblue": (65, 105, 225),
        "saddlebrown": (139, 69, 19),
        "salmon": (250, 128, 114),
        "sandybrown": (244, 164, 96),
        "seagreen": (46, 139, 87),
        "seashell": (255, 245, 238),
        "sienna": (160, 82, 45),
        "silver": (192, 192, 192),
        "skyblue": (135, 206, 235),
        "slateblue": (106, 90, 205),
        "slategray": (112, 128, 144),
        "slategrey": (112, 128, 144),
        "snow": (255, 250, 250),
        "springgreen": (0, 255, 127),
        "steelblue": (70, 130, 180),
        "tan": (210, 180, 140),
        "teal": (0, 128, 128),
        "thistle": (216, 191, 216),
        "tomato": (255, 99, 71),
        "turquoise": (64, 224, 208),
        "violet": (238, 130, 238),
        "wheat": (245, 222, 179),
        "white": (255, 255, 255),
        "whitesmoke": (245, 245, 245),
        "yellow": (255, 255, 0),
        "yellowgreen": (154, 205, 50),
    }

    r: int
    g: int
    b: int
    a: float = dataclasses.field(default=255.0)

    @classmethod
    def from_name(cls, color: ColorName, alpha: float = 255.0) -> Color:
        """Creates a color from a known color name. All color names and
        their associated RGB representations are ported directly from the
        ``pydantic_extra_types.Color.COLORS_BY_NAME`` dictionary.

        Args:
            color: The name of the color to create.
            alpha: The alpha component of the color. (Defaults to 255.0
                if not provided.)

        Returns:
            The color created from the name.
        """
        return cls(
            r=cls.COLORS_BY_NAME[color][0],
            g=cls.COLORS_BY_NAME[color][1],
            b=cls.COLORS_BY_NAME[color][2],
            a=alpha,
        )

    @classmethod
    def from_rgba(cls, color: ColorTuple) -> Color:
        """Creates a color from an RGB or RGBA tuple.

        Args:
            color: The RGB or RGBA tuple to create the color from.

        Returns:
            The color created from the tuple.
        """
        if not len(color) in (3, 4):
            raise ValueError("Color tuple must be 3 or 4 elements long")

        r, g, b = color[0], color[1], color[2]
        if len(color) == 3:
            a = 255.0
        else:
            a = color[3]
        return cls(r=r, g=g, b=b, a=a)

    @classmethod
    def from_hex(cls, color: str, alpha: float = 255.0) -> Color:
        """Creates a color from a hexadecimal string.

        Args:
            value: The hexadecimal string to create the color from.
            alpha: The alpha component of the color. (Defaults to 255.0
                if not provided.)

        Returns:
            The color created from the hexadecimal string.
        """
        color = color.strip().lower()
        hex_match = re.fullmatch(
            r"#?([0-9a-f]{6}|[0-9a-f]{3,4}|[0-9a-f]{8})", color
        )
        if not hex_match:
            raise ValueError(
                f"Invalid hex color string '{color}': must be 3, 4, 6, or 8 hex digits (optionally with leading #)"
            )

        hex_value = hex_match.group(1)
        if len(hex_value) in (3, 4):
            hex_value = "".join(2 * ch for ch in hex_value)
        r = int(hex_value[0:2], 16)
        g = int(hex_value[2:4], 16)
        b = int(hex_value[4:6], 16)
        a = 255
        if len(hex_value) == 8:
            a = int(hex_value[6:8], 16)
        return cls(r=r, g=g, b=b, a=a)

    @classmethod
    def parse(
        cls, color: ColorName | str | ColorTuple | Color, alpha: float = 255.0
    ) -> Color:
        """Parses a color from a color-like input.

        Args:
            color: The color-like input to parse.
                This can be any of the following:
                    - A known color name.
                    - A hex color string
                    - A tuple of 3 or 4 integers representing RGB or RGBA components
                    - A ``Color`` instance
            alpha: The alpha component of the color. (Defaults to 255.0
                if not provided.)

                NOTE: This is not applied if the input is a ``Color``
                or RGBA tuple.

        Returns:
            The color created from the input.
        """
        if isinstance(color, Color):
            return color
        if isinstance(color, tuple):
            return Color.from_rgba(color)
        if isinstance(color, str):
            if color.startswith("#"):
                try:
                    return Color.from_hex(color, alpha)
                except Exception as e:
                    raise ValueError(
                        f"Error parsing hex-like string `{repr(color)}` into a color: {e}"
                    ) from e
            else:
                try:
                    return Color.from_name(color, alpha)  # type: ignore
                except Exception as e:
                    raise ValueError(
                        f"{color!r} is not a known color name: {e}.\n"
                        "You can refer to ``xnano.theme.color.ColorName`` for a list of valid"
                        "color names."
                    ) from e
        else:
            raise ValueError(
                f"Expected a color-like input (accepted: color name, hex string, RGB(A) tuple, "
                "or Color instance), got {type(color).__name__} instead."
            )


def pydantic_color(color: ColorName) -> Color:
    """Creates a new ``Color`` instance from a known color name derived
    from the ``pydantic_extra_types.Color.COLORS_BY_NAME`` dictionary.

    Example:
        ```python
        from xnano import pydantic_color

        c = pydantic_color("blue")
        ```

    Args:
        color: The name of the color to create.

    Returns:
        The color created from the name.
    """
    return Color.from_name(color)


def tailwind_color(
    palette: TailwindColorName, shade: TailwindColorShade = 500
) -> Color:
    """Resolve a Tailwind CSS palette swatch to an xnano ``Color`` instance.

    Calls the ``xnano_core`` native ``tailwind_color`` function internally and
    converts the result to an xnano ``Color`` — no native types are
    exposed to the caller.

    Example:

        ```python
        from xnano import tailwind, Field

        class MyGrid(Grid):
            header = Field(background=tailwind("blue", 600))
            body = Field(color=tailwind("slate", 200))
        ```

    Args:
        palette: Tailwind palette name, e.g. ``"blue"``, ``"slate"``,
            ``"emerald"``.
        shade: Shade level: ``50``, ``100``, ``200``, …, ``900``, ``950``.

    Returns:
        The resolved ``Color`` for the given palette swatch.
    """
    key = (palette, shade)
    cached = _TAILWIND_CACHE.get(key)
    if cached is not None:
        return cached

    from xnano_core.rust.native import tailwind_color as _native_tailwind

    native_c: Any = _native_tailwind(palette, shade)

    # Try direct attribute access (pyo3 binding may expose .r/.g/.b).
    try:
        r, g, b = int(native_c.r), int(native_c.g), int(native_c.b)
    except AttributeError:
        import re as _re

        s = repr(native_c)
        # "Rgb(59, 130, 246)" or "Color::Rgb { r: 59, g: 130, b: 246 }"
        m = _re.search(r"Rgb\((\d+),\s*(\d+),\s*(\d+)\)", s)
        if not m:
            m = _re.search(r"r:\s*(\d+),\s*g:\s*(\d+),\s*b:\s*(\d+)", s)
        if m:
            r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        else:
            raise ValueError(
                f"Cannot extract RGB components from tailwind color {palette!r}/{shade}: "
                f"{native_c!r}"
            )

    result = Color(r=r, g=g, b=b)
    _TAILWIND_CACHE[key] = result
    return result


__all__ = (
    "ColorLike",
    "ColorTuple",
    "ColorName",
    "Color",
    "pydantic_color",
    "tailwind_color",
)
