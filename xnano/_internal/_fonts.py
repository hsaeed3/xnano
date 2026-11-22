"""
xnano._internal._fonts

The ``font=`` keyword: a font, the name of a built-in font, or a name registered with
``xnano.symbols.register``, and the text it writes.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, cast, get_args

import xnano_core as _core

if TYPE_CHECKING:
    from xnano.styles._core_styles import FontValue


def resolve_font(value: FontValue) -> _core.Font:
    """The font that ``value`` stands for."""
    if isinstance(value, _core.Font):
        return value
    if not isinstance(value, str):
        raise TypeError(
            f'font must be a Font or the name of a font, but got {type(value).__name__}. '
            f"Pass a name such as font='small', or a Font such as Font.from_file(path)."
        )
    from xnano import symbols

    if value in symbols.names():
        registered = symbols.lookup(value)
        if isinstance(registered, _core.Font):
            return registered
        raise ValueError(
            f'The symbol {value!r} is a {type(registered).__name__}, not a Font, so it cannot '
            f'be a font. Register a font under another name with '
            f'xnano.symbols.register(name, Font.from_file(path)).'
        )
    builtin = get_args(_core.BuiltinFontName)
    if value in builtin:
        return _core.Font(cast('_core.BuiltinFontName', value))
    registered_fonts = [
        name for name in symbols.names() if isinstance(symbols.lookup(name), _core.Font)
    ]
    known = ', '.join(repr(name) for name in (*builtin, *registered_fonts))
    raise ValueError(
        f'There is no font called {value!r}. The fonts are {known}. Register another font with '
        f'xnano.symbols.register({value!r}, Font.from_file(path)).'
    )


def font_text(font: _core.Font, content: object) -> str:
    """The rows that write ``content``, which must be text, in ``font``."""
    if isinstance(content, (list, tuple)) and all(
        isinstance(line, str) for line in content
    ):
        content = '\n'.join(cast('Sequence[str]', content))
    if not isinstance(content, str):
        raise TypeError(
            f'font= writes text, but the content is {type(content).__name__}. Pass a string, '
            f'or leave font out to write this content.'
        )
    return font.render(content)
