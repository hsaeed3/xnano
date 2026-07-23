"""xnano.beta.colors

---

Parse, convert, and resolve colors shared by terminal and web rendering.
"""

from __future__ import annotations

import dataclasses
import re
from typing import (
    Any,
    ClassVar,
    Literal,
    TypeAlias,
    Union,
    cast,
)

_TAILWIND_CACHE: dict[tuple[str, int], Color] = {}


ColorLike: TypeAlias = Union[
    "ColorName", "TailwindColorBinding", str, "ColorTuple", "Color"
]
"""A color-like input.

This can be any one of:
    - A known color name (e.g. ``"red"``, ``"aliceblue"``).
    - A Tailwind CSS binding string (e.g. ``"slate-400"``, ``"violet-900"``).
    - A hex color string (e.g. ``"#FF0000"``).
    - A tuple of 3 or 4 integers representing RGB or RGBA components.
    - A ``Color`` instance.

Example:
    >>> ColorLike = "red" | "aliceblue" | "black"
    >>> ColorLike = "slate-400"
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


TailwindColorBinding: TypeAlias = Literal[
    "amber-50",
    "amber-100",
    "amber-200",
    "amber-300",
    "amber-400",
    "amber-500",
    "amber-600",
    "amber-700",
    "amber-800",
    "amber-900",
    "amber-950",
    "black-50",
    "black-100",
    "black-200",
    "black-300",
    "black-400",
    "black-500",
    "black-600",
    "black-700",
    "black-800",
    "black-900",
    "black-950",
    "blue-50",
    "blue-100",
    "blue-200",
    "blue-300",
    "blue-400",
    "blue-500",
    "blue-600",
    "blue-700",
    "blue-800",
    "blue-900",
    "blue-950",
    "cyan-50",
    "cyan-100",
    "cyan-200",
    "cyan-300",
    "cyan-400",
    "cyan-500",
    "cyan-600",
    "cyan-700",
    "cyan-800",
    "cyan-900",
    "cyan-950",
    "emerald-50",
    "emerald-100",
    "emerald-200",
    "emerald-300",
    "emerald-400",
    "emerald-500",
    "emerald-600",
    "emerald-700",
    "emerald-800",
    "emerald-900",
    "emerald-950",
    "fuchsia-50",
    "fuchsia-100",
    "fuchsia-200",
    "fuchsia-300",
    "fuchsia-400",
    "fuchsia-500",
    "fuchsia-600",
    "fuchsia-700",
    "fuchsia-800",
    "fuchsia-900",
    "fuchsia-950",
    "gray-50",
    "gray-100",
    "gray-200",
    "gray-300",
    "gray-400",
    "gray-500",
    "gray-600",
    "gray-700",
    "gray-800",
    "gray-900",
    "gray-950",
    "green-50",
    "green-100",
    "green-200",
    "green-300",
    "green-400",
    "green-500",
    "green-600",
    "green-700",
    "green-800",
    "green-900",
    "green-950",
    "indigo-50",
    "indigo-100",
    "indigo-200",
    "indigo-300",
    "indigo-400",
    "indigo-500",
    "indigo-600",
    "indigo-700",
    "indigo-800",
    "indigo-900",
    "indigo-950",
    "lime-50",
    "lime-100",
    "lime-200",
    "lime-300",
    "lime-400",
    "lime-500",
    "lime-600",
    "lime-700",
    "lime-800",
    "lime-900",
    "lime-950",
    "neutral-50",
    "neutral-100",
    "neutral-200",
    "neutral-300",
    "neutral-400",
    "neutral-500",
    "neutral-600",
    "neutral-700",
    "neutral-800",
    "neutral-900",
    "neutral-950",
    "orange-50",
    "orange-100",
    "orange-200",
    "orange-300",
    "orange-400",
    "orange-500",
    "orange-600",
    "orange-700",
    "orange-800",
    "orange-900",
    "orange-950",
    "pink-50",
    "pink-100",
    "pink-200",
    "pink-300",
    "pink-400",
    "pink-500",
    "pink-600",
    "pink-700",
    "pink-800",
    "pink-900",
    "pink-950",
    "purple-50",
    "purple-100",
    "purple-200",
    "purple-300",
    "purple-400",
    "purple-500",
    "purple-600",
    "purple-700",
    "purple-800",
    "purple-900",
    "purple-950",
    "red-50",
    "red-100",
    "red-200",
    "red-300",
    "red-400",
    "red-500",
    "red-600",
    "red-700",
    "red-800",
    "red-900",
    "red-950",
    "rose-50",
    "rose-100",
    "rose-200",
    "rose-300",
    "rose-400",
    "rose-500",
    "rose-600",
    "rose-700",
    "rose-800",
    "rose-900",
    "rose-950",
    "sky-50",
    "sky-100",
    "sky-200",
    "sky-300",
    "sky-400",
    "sky-500",
    "sky-600",
    "sky-700",
    "sky-800",
    "sky-900",
    "sky-950",
    "slate-50",
    "slate-100",
    "slate-200",
    "slate-300",
    "slate-400",
    "slate-500",
    "slate-600",
    "slate-700",
    "slate-800",
    "slate-900",
    "slate-950",
    "stone-50",
    "stone-100",
    "stone-200",
    "stone-300",
    "stone-400",
    "stone-500",
    "stone-600",
    "stone-700",
    "stone-800",
    "stone-900",
    "stone-950",
    "teal-50",
    "teal-100",
    "teal-200",
    "teal-300",
    "teal-400",
    "teal-500",
    "teal-600",
    "teal-700",
    "teal-800",
    "teal-900",
    "teal-950",
    "violet-50",
    "violet-100",
    "violet-200",
    "violet-300",
    "violet-400",
    "violet-500",
    "violet-600",
    "violet-700",
    "violet-800",
    "violet-900",
    "violet-950",
    "white-50",
    "white-100",
    "white-200",
    "white-300",
    "white-400",
    "white-500",
    "white-600",
    "white-700",
    "white-800",
    "white-900",
    "white-950",
    "yellow-50",
    "yellow-100",
    "yellow-200",
    "yellow-300",
    "yellow-400",
    "yellow-500",
    "yellow-600",
    "yellow-700",
    "yellow-800",
    "yellow-900",
    "yellow-950",
    "zinc-50",
    "zinc-100",
    "zinc-200",
    "zinc-300",
    "zinc-400",
    "zinc-500",
    "zinc-600",
    "zinc-700",
    "zinc-800",
    "zinc-900",
    "zinc-950",
]
"""Tailwind CSS color binding strings in ``"{palette}-{shade}"`` form, e.g. ``"slate-400"``.

These are accepted anywhere a ``ColorLike`` is expected and resolve via
``tailwind_color(palette, shade)`` at parse time.
"""

_TAILWIND_NAMES: frozenset[str] = frozenset(
    [
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
)
_TAILWIND_SHADES: frozenset[int] = frozenset(
    [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]
)


@dataclasses.dataclass(frozen=True, slots=True, repr=False)
class Color:
    """An RGBA color accepted by components, fields, and styles.

    Construct a color from channel values or use a factory for names, hex
    strings, and tuples.

    Attributes:
        COLORS_BY_NAME: Named CSS colors accepted by ``from_name``.
        r: The red component of this color.
        g: The green component of this color.
        b: The blue component of this color.
        a: The alpha component of this color. (Defaults to 255.0
            if not provided.)

    Examples:
        ```python
        red = Color(255, 0, 0)
        accent = Color.from_hex("#7c3aed")
        ```
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
    """Named CSS colors accepted by ``Color.from_name``."""

    r: int
    """Red channel from 0 to 255."""
    g: int
    """Green channel from 0 to 255."""
    b: int
    """Blue channel from 0 to 255."""
    a: float = dataclasses.field(default=255.0)
    """Alpha channel from 0 to 255."""

    @classmethod
    def from_name(
        cls, color: "ColorName | TailwindColorBinding", alpha: float = 255.0
    ) -> "Color":
        """Creates a color from a known color name or Tailwind binding string.

        Accepts CSS named colors (``"red"``, ``"aliceblue"``, …) and
        Tailwind ``"{palette}-{shade}"`` strings (``"slate-400"``,
        ``"violet-900"``, …).

        Args:
            color: The name or Tailwind binding to resolve.
            alpha: The alpha component of the color. (Defaults to 255.0
                if not provided.)

        Returns:
            The color created from the name.
        """
        if "-" in color:
            parts = color.rsplit("-", 1)
            if len(parts) == 2 and parts[0] in _TAILWIND_NAMES:
                try:
                    shade = int(parts[1])
                except ValueError:
                    pass
                else:
                    if shade in _TAILWIND_SHADES:
                        return tailwind_color(
                            cast("TailwindColorName", parts[0]),
                            cast("TailwindColorShade", shade),
                        )
        name = cast("ColorName", color)
        return cls(
            r=cls.COLORS_BY_NAME[name][0],
            g=cls.COLORS_BY_NAME[name][1],
            b=cls.COLORS_BY_NAME[name][2],
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
        cls,
        color: "ColorName | TailwindColorBinding | str | ColorTuple | Color",
        alpha: float = 255.0,
    ) -> "Color":
        """Parses a color from a color-like input.

        Args:
            color: The color-like input to parse. Accepted forms:
                - A known CSS color name (``"red"``, ``"aliceblue"``).
                - A Tailwind binding string (``"slate-400"``, ``"violet-900"``).
                - A hex string (``"#FF0000"``).
                - An RGB or RGBA tuple.
                - A ``Color`` instance.
            alpha: Alpha component, 0–255. Not applied to ``Color`` or RGBA tuple inputs.

        Returns:
            The resolved ``Color``.
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
            if "-" in color:
                parts = color.rsplit("-", 1)
                if len(parts) == 2 and parts[0] in _TAILWIND_NAMES:
                    try:
                        shade = int(parts[1])
                    except ValueError:
                        pass
                    else:
                        if shade in _TAILWIND_SHADES:
                            return tailwind_color(
                                cast("TailwindColorName", parts[0]),
                                cast("TailwindColorShade", shade),
                            )
            try:
                return Color.from_name(cast("ColorName", color), alpha)
            except Exception as e:
                raise ValueError(
                    f"{color!r} is not a known color name or Tailwind binding: {e}.\n"
                    'Valid forms: CSS name ("red"), Tailwind binding ("slate-400"), hex ("#ff0000").'
                ) from e
        raise ValueError(
            f"Expected a color-like input (color name, Tailwind binding, hex string, RGB(A) tuple, "
            f"or Color instance), got {type(color).__name__!r} instead."
        )

    def as_hex(self, *, include_alpha: bool = False) -> str:
        """Return this color as a ``#rrggbb`` (or ``#rrggbbaa``) hex string.

        Args:
            include_alpha: When ``True``, append the alpha channel as a
                two-digit hex suffix.

        Returns:
            A lowercase, leading-``#`` hex color string.
        """
        hex_str = f"#{self.r:02x}{self.g:02x}{self.b:02x}"
        if include_alpha:
            hex_str += f"{round(self.a):02x}"
        return hex_str

    def as_rgb_tuple(
        self, *, include_alpha: bool = False
    ) -> "tuple[int, int, int] | tuple[int, int, int, float]":
        """Return this color as an ``(r, g, b)`` or ``(r, g, b, a)`` tuple.

        Args:
            include_alpha: When ``True``, include the alpha channel as the
                fourth tuple element.
        """
        if include_alpha:
            return (self.r, self.g, self.b, self.a)
        return (self.r, self.g, self.b)


def pydantic_color(color: ColorName) -> Color:
    """Creates a new ``Color`` instance from a known color name derived
    from the ``pydantic_extra_types.Color.COLORS_BY_NAME`` dictionary.

    Example:
        ```python
        from xnano.beta.colors import pydantic_color

        c = pydantic_color("blue")
        ```

    Args:
        color: The name of the color to create.

    Returns:
        The color created from the name.
    """
    return Color.from_name(color)


def get_native_color(color: ColorLike | None) -> Any:
    """Convert a public color value to the native renderer color.

    Args:
        color: Color name, tuple, hex value, ``Color``, or ``None``.

    Returns:
        The native color value, or ``None``.
    """
    if color is None:
        return None
    import xnano_core.rust.native as native

    parsed = Color.parse(color)
    return native.Color.rgb(parsed.r, parsed.g, parsed.b)


def tailwind_color(
    palette: TailwindColorName, shade: TailwindColorShade = 500
) -> Color:
    """Resolve a Tailwind CSS palette swatch to an xnano ``Color`` instance.

    Calls the ``xnano_core`` native ``tailwind_color`` function internally and
    converts the result to an xnano ``Color`` — no native types are
    exposed to the caller.

    Example:

        ```python
        from xnano.beta import BaseGrid, Field
        from xnano.beta.colors import tailwind_color

        class MyGrid(BaseGrid):
            header = Field(background=tailwind_color("blue", 600))
            body = Field(color=tailwind_color("slate", 200))
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
    "TailwindColorName",
    "TailwindColorShade",
    "TailwindColorBinding",
    "Color",
    "pydantic_color",
    "tailwind_color",
    "get_native_color",
)
