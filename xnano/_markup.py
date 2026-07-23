"""xnano._markup

---

Pre-styled text ingestion: ANSI escapes, syntax highlighting, and
markdown, all parsed into ``Run`` lines.

Everything here returns interface-neutral ``Run`` tuples, so the same
parse feeds terminal rendering (through ``TextBlock``) and web spans.
Pygments and markdown-it-py are imported inside the helpers to keep
them off the package import path.
"""

from __future__ import annotations

import functools
import re
from typing import Any

from xnano._types import CharacterModifier
from xnano.core.content import Run

_ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_SGR_PATTERN = re.compile(r"\x1b\[([0-9;]*)m")

# Standard xterm palette for the 16 base colors (30-37 / 90-97).
_BASE_COLORS = (
    "#000000",
    "#cd0000",
    "#00cd00",
    "#cdcd00",
    "#0000ee",
    "#cd00cd",
    "#00cdcd",
    "#e5e5e5",
)
_BRIGHT_COLORS = (
    "#7f7f7f",
    "#ff0000",
    "#00ff00",
    "#ffff00",
    "#5c5cff",
    "#ff00ff",
    "#00ffff",
    "#ffffff",
)

_SGR_MODIFIERS: dict[int, CharacterModifier] = {
    1: "bold",
    2: "dim",
    3: "italic",
    4: "underline",
    5: "slow_blink",
    6: "rapid_blink",
    7: "reversed",
}

_CUBE_STEPS = (0, 95, 135, 175, 215, 255)


def _color_from_256(index: int) -> str:
    """Resolve an xterm 256-color index to a hex color."""
    if index < 8:
        return _BASE_COLORS[index]
    if index < 16:
        return _BRIGHT_COLORS[index - 8]
    if index < 232:
        cube = index - 16
        red = _CUBE_STEPS[cube // 36]
        green = _CUBE_STEPS[(cube // 6) % 6]
        blue = _CUBE_STEPS[cube % 6]
        return f"#{red:02x}{green:02x}{blue:02x}"
    gray = 8 + (index - 232) * 10
    return f"#{gray:02x}{gray:02x}{gray:02x}"


def strip_ansi_escapes(content: str) -> str:
    """Return ``content`` with all ANSI escape sequences removed."""
    return _ANSI_ESCAPE_PATTERN.sub("", content)


def _consume_extended_color(codes: list[int]) -> str | None:
    """Consume a 38/48 extended-color parameter list, returning hex."""
    if not codes:
        return None
    mode = codes.pop(0)
    if mode == 5 and codes:
        return _color_from_256(codes.pop(0) % 256)
    if mode == 2 and len(codes) >= 3:
        red = codes.pop(0) % 256
        green = codes.pop(0) % 256
        blue = codes.pop(0) % 256
        return f"#{red:02x}{green:02x}{blue:02x}"
    return None


_MODIFIER_CLEAR_CODES: dict[int, tuple[CharacterModifier, ...]] = {
    22: ("bold", "dim"),
    23: ("italic",),
    24: ("underline",),
    25: ("slow_blink", "rapid_blink"),
    27: ("reversed",),
}

_SgrState = tuple["str | None", "str | None", tuple[CharacterModifier, ...]]
"""Carried SGR style: ``(color, background, modifiers)``."""


def _apply_sgr_codes(codes: list[int], state: _SgrState) -> _SgrState:
    """Fold a parameter list from one SGR sequence into ``state``."""
    color, background, modifiers = state
    while codes:
        code = codes.pop(0)
        if code == 0:
            color = background = None
            modifiers = ()
        elif code in _SGR_MODIFIERS:
            modifier = _SGR_MODIFIERS[code]
            if modifier not in modifiers:
                modifiers = (*modifiers, modifier)
        elif code in _MODIFIER_CLEAR_CODES:
            cleared = _MODIFIER_CLEAR_CODES[code]
            modifiers = tuple(
                modifier for modifier in modifiers if modifier not in cleared
            )
        elif 30 <= code <= 37:
            color = _BASE_COLORS[code - 30]
        elif 90 <= code <= 97:
            color = _BRIGHT_COLORS[code - 90]
        elif 40 <= code <= 47:
            background = _BASE_COLORS[code - 40]
        elif 100 <= code <= 107:
            background = _BRIGHT_COLORS[code - 100]
        elif code == 38:
            color = _consume_extended_color(codes) or color
        elif code == 48:
            background = _consume_extended_color(codes) or background
        elif code == 39:
            color = None
        elif code == 49:
            background = None
    return (color, background, modifiers)


@functools.lru_cache(maxsize=128)
def parse_ansi_lines(content: str) -> tuple[tuple[Run, ...], ...]:
    """Parse ANSI-escaped content into styled ``Run`` lines.

    SGR (color/style) sequences become run styles carried across
    lines; all other escape sequences are stripped, not emulated —
    this is a log view, not a terminal emulator.

    Args:
        content: Raw text containing ANSI escape sequences.

    Returns:
        One tuple of ``Run`` spans per source line.
    """
    # ponytail: full-buffer re-parse per append; Rust fast path if
    # streamed logs ever get huge.
    state: _SgrState = (None, None, ())
    lines: list[tuple[Run, ...]] = []
    runs: list[Run] = []

    def emit(text: str) -> None:
        color, background, modifiers = state
        for index, segment in enumerate(text.split("\n")):
            if index > 0:
                lines.append(tuple(runs))
                runs.clear()
            if segment:
                runs.append(
                    Run(
                        text=segment,
                        color=color,
                        background=background,
                        modifiers=modifiers,
                    )
                )

    position = 0
    for match in _SGR_PATTERN.finditer(content):
        emit(strip_ansi_escapes(content[position : match.start()]))
        position = match.end()
        codes = [
            int(part) if part else 0
            for part in (match.group(1) or "0").split(";")
        ]
        state = _apply_sgr_codes(codes, state)
    emit(strip_ansi_escapes(content[position:]))
    lines.append(tuple(runs))
    return tuple(lines)


# Fixed terminal-friendly theme: Pygments token types to run styles.
# Colors are the same base-16 hex palette the ANSI parser emits.
_TOKEN_STYLES: tuple[
    tuple[str, str | None, tuple[CharacterModifier, ...]], ...
] = (
    ("Token.Keyword", "#cd00cd", ()),
    ("Token.Name.Function", "#0000ee", ("bold",)),
    ("Token.Name.Class", "#0000ee", ("bold",)),
    ("Token.Name.Decorator", "#00cdcd", ()),
    ("Token.Name.Builtin", "#00cdcd", ()),
    ("Token.Literal.String", "#00cd00", ()),
    ("Token.Literal.Number", "#cdcd00", ()),
    ("Token.Operator", None, ()),
    ("Token.Comment", "#7f7f7f", ("italic",)),
)


def _style_for_token(
    token_type: Any,
) -> tuple[str | None, tuple[CharacterModifier, ...]]:
    name = str(token_type)
    for prefix, color, modifiers in _TOKEN_STYLES:
        if name.startswith(prefix):
            return (color, modifiers)
    return (None, ())


@functools.lru_cache(maxsize=64)
def highlight_lines(
    content: str,
    language: str,
) -> tuple[tuple[Run, ...], ...]:
    """Syntax-highlight ``content`` into styled ``Run`` lines.

    Args:
        content: Source code to highlight.
        language: A Pygments lexer name (``"python"``, ``"rust"``, …).
            Unknown names fall back to plain text.

    Returns:
        One tuple of ``Run`` spans per source line.
    """
    import pygments.lexers
    import pygments.util

    try:
        lexer = pygments.lexers.get_lexer_by_name(language)
    except pygments.util.ClassNotFound:
        return tuple(
            (Run(text=line),) if line else () for line in content.split("\n")
        )

    lines: list[tuple[Run, ...]] = []
    runs: list[Run] = []
    for token_type, token_text in lexer.get_tokens(content):
        color, modifiers = _style_for_token(token_type)
        for index, segment in enumerate(token_text.split("\n")):
            if index > 0:
                lines.append(tuple(runs))
                runs.clear()
            if segment:
                runs.append(
                    Run(text=segment, color=color, modifiers=modifiers)
                )
    if runs:
        lines.append(tuple(runs))
    # Pygments always terminates output with a newline; drop the
    # resulting phantom empty last line unless the source had one.
    if lines and not content.endswith("\n") and lines[-1] == ():
        lines.pop()
    return tuple(lines)


_HEADING_COLOR = "#00cdcd"
_BULLET = "• "

_INLINE_MODIFIER_OPENERS: dict[str, CharacterModifier] = {
    "strong_open": "bold",
    "em_open": "italic",
}
_INLINE_MODIFIER_CLOSERS: dict[str, CharacterModifier] = {
    "strong_close": "bold",
    "em_close": "italic",
}


def _markdown_inline_runs(
    token: Any,
    *,
    color: str | None = None,
    modifiers: tuple[CharacterModifier, ...] = (),
) -> tuple[Run, ...]:
    """Flatten one markdown ``inline`` token into styled runs."""
    runs: list[Run] = []
    active = list(modifiers)
    for child in token.children or ():
        if child.type in _INLINE_MODIFIER_OPENERS:
            active.append(_INLINE_MODIFIER_OPENERS[child.type])
        elif child.type in _INLINE_MODIFIER_CLOSERS:
            active.remove(_INLINE_MODIFIER_CLOSERS[child.type])
        elif child.type == "code_inline":
            runs.append(
                Run(
                    text=child.content,
                    color=color,
                    modifiers=(*active, "reversed"),
                )
            )
        elif child.type in ("text", "softbreak"):
            text = child.content if child.type == "text" else " "
            if text:
                runs.append(
                    Run(
                        text=text,
                        color=color,
                        modifiers=tuple(dict.fromkeys(active)),
                    )
                )
    return tuple(runs)


def _markdown_inline_line(
    token: Any,
    *,
    heading_level: int,
    quote_depth: int,
    list_depth: int,
) -> tuple[Run, ...]:
    """Render one ``inline`` token as a line, prefixed by its block
    context (heading marker, quote marker, or list bullet)."""
    if heading_level:
        return (
            Run(
                text="#" * heading_level + " ",
                color=_HEADING_COLOR,
                modifiers=("dim",),
            ),
            *_markdown_inline_runs(
                token, color=_HEADING_COLOR, modifiers=("bold",)
            ),
        )
    if quote_depth:
        return (
            Run(text="> " * quote_depth, modifiers=("dim",)),
            *_markdown_inline_runs(token, modifiers=("dim",)),
        )
    if list_depth:
        return (
            Run(text="  " * (list_depth - 1) + _BULLET, modifiers=("dim",)),
            *_markdown_inline_runs(token),
        )
    return _markdown_inline_runs(token)


def _markdown_fence_lines(token: Any) -> list[tuple[Run, ...]]:
    """Render a fenced/indented code block, highlighting by its tag."""
    language = (token.info or "").strip().split(" ")[0]
    code = token.content.rstrip("\n")
    if language:
        return list(highlight_lines(code, language))
    return [
        (Run(text=line, modifiers=("dim",)),) if line else ()
        for line in code.split("\n")
    ]


@functools.lru_cache(maxsize=64)
def markdown_lines(content: str) -> tuple[tuple[Run, ...], ...]:
    """Parse markdown ``content`` into styled ``Run`` lines.

    Headings render bold in an accent color, emphasis/strong map to
    italic/bold, list items get bullets, blockquotes render dim,
    inline code renders reversed, and fenced code blocks are
    syntax-highlighted by their fence language tag. Tables and images
    are out of scope and render as their plain text.

    Args:
        content: Markdown source.

    Returns:
        One tuple of ``Run`` spans per rendered line.
    """
    import markdown_it

    lines: list[tuple[Run, ...]] = []
    quote_depth = 0
    list_depth = 0
    heading_level = 0

    for token in markdown_it.MarkdownIt("commonmark").parse(content):
        if token.type == "blockquote_open":
            quote_depth += 1
        elif token.type == "blockquote_close":
            quote_depth -= 1
        elif token.type in ("bullet_list_open", "ordered_list_open"):
            list_depth += 1
        elif token.type in ("bullet_list_close", "ordered_list_close"):
            list_depth -= 1
            if list_depth == 0:
                lines.append(())
        elif token.type == "heading_open":
            heading_level = int(token.tag[1:])
        elif token.type == "heading_close":
            heading_level = 0
            lines.append(())
        elif token.type == "paragraph_close":
            if quote_depth == 0 and list_depth == 0:
                lines.append(())
        elif token.type == "inline":
            lines.append(
                _markdown_inline_line(
                    token,
                    heading_level=heading_level,
                    quote_depth=quote_depth,
                    list_depth=list_depth,
                )
            )
        elif token.type in ("fence", "code_block"):
            lines.extend(_markdown_fence_lines(token))
            lines.append(())
        elif token.type == "hr":
            lines.append((Run(text="─" * 24, modifiers=("dim",)),))
            lines.append(())

    while lines and lines[-1] == ():
        lines.pop()
    return tuple(lines)


__all__ = (
    "highlight_lines",
    "markdown_lines",
    "parse_ansi_lines",
    "strip_ansi_escapes",
)
