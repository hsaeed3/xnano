"""xnano.color"""

from __future__ import annotations

import dataclasses
import re
from typing import Literal, TypeAlias

from xnano import _core


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

COLORS_BY_NAME = {
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

_RGB_RE = re.compile(r"^Rgb\((\d+),\s*(\d+),\s*(\d+)\)$")

_NATIVE_COLOR: dict[str, ColorName] = {
    "Black": "black",
    "Red": "red",
    "Green": "green",
    "Yellow": "yellow",
    "Blue": "blue",
    "Magenta": "magenta",
    "Cyan": "cyan",
    "Gray": "gray",
    "DarkGray": "darkgray",
    "LightRed": "lightcoral",
    "LightGreen": "lightgreen",
    "LightYellow": "lightyellow",
    "LightBlue": "lightblue",
    "LightMagenta": "lightpink",
    "LightCyan": "lightcyan",
    "White": "white",
}


@dataclasses.dataclass(frozen=True, slots=True, repr=False)
class Color:
    """A color in the RGBA space that can be defined from a variety
    of formats.

    Attributes:
        r: The red component of this color.
        g: The green component of this color.
        b: The blue component of this color.
        a: The alpha component of this color.
    """

    r: int
    g: int
    b: int
    a: int

    @classmethod
    def from_native(cls, native: _core.Color) -> Color:
        text = repr(native)
        match = _RGB_RE.match(text)
        if match:
            return cls(
                r=int(match.group(1)),
                g=int(match.group(2)),
                b=int(match.group(3)),
                a=255,
            )
        name = _NATIVE_COLOR.get(text)
        if name is not None:
            return cls.from_name(name)
        if text == "Reset":
            return cls(r=0, g=0, b=0, a=0)
        raise ValueError(f"unsupported native color: {text}")

    def _to_core(self) -> _core.Color:
        """Gets the ``ratatui`` ``Color`` primitive that represents this
        current color.

        Returns:
            The ``ratatui`` ``Color`` primitive that represents this
            current color.
        """
        return _core.Color.rgb(self.r, self.g, self.b)

    @classmethod
    def from_name(cls, name: ColorName) -> Color:
        """Creates a color from a known color name. All color names and
        associated RGBA representations are ported directly from the
        ``pydantic_extra_types.color.COLORS_BY_NAME`` dictionary.

        Args:
            name: The name of the color to create.

        Returns:
            The color created from the name.
        """
        return cls(
            r=COLORS_BY_NAME[name][0],
            g=COLORS_BY_NAME[name][1],
            b=COLORS_BY_NAME[name][2],
            a=255,
        )

    @classmethod
    def from_hex(cls, value: str) -> Color:
        """Parses a hex color string and creates a color from it.

        Args:
            value: The hex color string to parse.

        Returns:
            The color created from the hex string.
        """
        value = value.strip().lower()
        hex_match = re.fullmatch(
            r"#?([0-9a-f]{6}|[0-9a-f]{3,4}|[0-9a-f]{8})", value
        )
        if not hex_match:
            raise ValueError(
                f"Invalid hex color string '{value}': must be 3, 4, 6, or 8 hex digits (optionally with leading #)"
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
        rgba = (r, g, b, a)

        return cls(
            r=rgba[0],
            g=rgba[1],
            b=rgba[2],
            a=int(rgba[3]) if len(rgba) > 3 and rgba[3] is not None else 255,
        )

    @classmethod
    def from_hsl(cls, h: float, s: float, l: float) -> Color:
        """Creates a color from HSL components.

        Args:
            h: The hue component of the color.
            s: The saturation component of the color.
            l: The lightness component of the color.
        """
        try:
            native = _core.color_from_hsl(h, s, l)
        except Exception as e:
            raise ValueError(
                f"Invalid HSL components: h={h}, s={s}, l={l}: {e}"
            ) from e
        return cls.from_native(native)

    @classmethod
    def lerp(cls, a: Color, b: Color, t: float) -> Color:
        """Linearly interpolates between two colors.

        Args:
            a: The first color to interpolate between.
            b: The second color to interpolate between.
            t: The interpolation factor.
        """
        t = max(0.0, min(1.0, t))
        return cls(
            r=round(a.r * (1 - t) + b.r * t),
            g=round(a.g * (1 - t) + b.g * t),
            b=round(a.b * (1 - t) + b.b * t),
            a=round(a.a * (1 - t) + b.a * t),
        )

    def __repr__(self) -> str:
        return f"Color(r={self.r}, g={self.g}, b={self.b}, a={self.a})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Color):
            return NotImplemented
        return (
            self.r == other.r
            and self.g == other.g
            and self.b == other.b
            and self.a == other.a
        )

    def __hash__(self) -> int:
        return hash((self.r, self.g, self.b, self.a))


__all__ = ("Color", "ColorName", "COLORS_BY_NAME")
