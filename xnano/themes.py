"""
xnano.themes

Themes: a set of colors for text, backgrounds, borders and widgets.

Give the name of a theme to [`new`][xnano.new], [`open`][xnano.open] or
[`write`][xnano.canvas.Canvas.write] as ``theme=``. Everything written under a theme gets its
colors, unless it is given its own. Without a theme, content uses the colors of the
terminal that it is drawn on, so it follows the theme that the person chose there.
"""

from __future__ import annotations

import dataclasses
import functools
from typing import TYPE_CHECKING, Literal, get_args

from xnano_core import Style, StyledText, TextSpan

if TYPE_CHECKING:
    from xnano.reader._lines import Run
    from xnano_core import Widget

__all__ = ['Theme', 'ThemeName', 'theme_of']

ThemeName = Literal[
    'xnano-day',
    'xnano-night',
    'zed-dark',
    'zed-light',
    'one-dark-pro',
    'one-dark',
    'one-light',
    'dracula',
    'monokai',
    'github-dark',
    'github-light',
    'anthropic-dark',
    'anthropic-light',
    'openai-dark',
    'openai-light',
]
"""
The name of a theme.

- ``'xnano-day'`` and ``'xnano-night'``: the themes of xnano. The background is wood: light
  birch by day and dark oak by night. The colors on it follow the way
  [Complementary Shaders](https://www.complementary.dev/) by EminGT lights a scene: a
  warm key light (the sun by day, a lantern by night) for text and accents, and a cool
  fill light (the sky) for links and numbers. The colors are xnano's own, with the light
  colors of Complementary Reimagined r5.9.2 as reference points.
- ``'zed-dark'`` and ``'zed-light'``: One Dark and One Light as the
  [Zed](https://github.com/zed-industries/zed/tree/main/assets/themes/one) editor ships
  them, by Zed Industries (MIT license).
- ``'one-dark-pro'``: [One Dark Pro](https://github.com/Binaryify/OneDark-Pro) by Binaryify
  (MIT license). It has no light theme: use ``'one-light'``.
- ``'one-dark'`` and ``'one-light'``: One Dark and One Light of the Atom editor
  ([one-dark-syntax](https://github.com/atom/one-dark-syntax),
  [one-light-syntax](https://github.com/atom/one-light-syntax)), by GitHub (MIT license).
- ``'dracula'``: [Dracula](https://github.com/dracula/dracula-theme) by Zeno Rocha and
  the Dracula Theme contributors (MIT license).
- ``'monokai'``: [Monokai](https://github.com/textmate/monokai.tmbundle) by Wimer
  Hazenberg, with the surface and border colors of the Monokai theme of Visual Studio Code.
- ``'github-dark'`` and ``'github-light'``: GitHub Dark Default and GitHub Light Default
  from [GitHub's theme for Visual Studio Code](https://github.com/primer/github-vscode-theme),
  by GitHub (MIT license).
- ``'anthropic-dark'`` and ``'anthropic-light'``: the brand colors of Anthropic, from its
  [brand guidelines skill](https://github.com/anthropics/skills/tree/main/skills/brand-guidelines)
  and its website. The brand gives no colors for links, code or data, so xnano
  chooses among the brand colors. In the light theme they are darker, so that text
  stays readable.
- ``'openai-dark'`` and ``'openai-light'``: the colors of OpenAI's
  [Apps SDK UI](https://github.com/openai/apps-sdk-ui), by OpenAI (MIT license). It gives
  no colors for links, code or data, so xnano chooses among its colors.

The names and the colors of these themes belong to their authors. xnano is not affiliated
with any of them, and none of them endorses xnano.
"""


@dataclasses.dataclass(frozen=True, slots=True)
class Theme:
    """
    The colors of the parts of a document.

    A color is a ``'#rrggbb'`` string, or the name of a terminal color such as ``'cyan'``.
    Without a theme, ``background`` and ``text`` are ``None``: the terminal draws them in
    its own colors, and secondary text is dim.

    Attributes:
        name: The name of the theme.
        background: The color behind the document, or ``None`` for the terminal's own.
        surface: The color behind what is on top of the background, such as a title line.
        text: The color of plain text, or ``None`` for the terminal's own.
        muted: The color of marks and secondary text, or ``None`` to draw them dim.
        border: The color of rules and borders, or ``None`` to draw them dim.
        accent: The color of what is chosen or filled in a widget, such as the chosen line of
            a list.
        link: The color of a link, which is also underlined.
        heading: The color of a heading, or ``None`` for the color of plain text.
        code: The color of code.
        string: The color of a text value in data such as JSON.
        number: The color of a number in data.
        keyword: The color of ``true``, ``false`` and ``null`` in data.
        warning: The color of a warning.
        error: The color of an error.
    """

    name: str
    """The name of the theme."""
    background: str | None
    """The color behind everything, or ``None`` for the terminal's own."""
    surface: str | None
    """The color behind what is on top of the background."""
    text: str | None
    """The color of plain text, or ``None`` for the terminal's own."""
    muted: str | None
    """The color of secondary text, or ``None`` to draw it dim."""
    border: str | None
    """The color of rules and borders, or ``None`` to draw them dim."""
    accent: str
    """The color of what is chosen or filled in a widget."""
    link: str
    """The color of a link."""
    heading: str | None
    """The color of a heading, or ``None`` for the color of plain text."""
    code: str
    """The color of code."""
    string: str
    """The color of a text value in data."""
    number: str
    """The color of a number in data."""
    keyword: str
    """The color of ``true``, ``false`` and ``null`` in data."""
    warning: str
    """The color of a warning."""
    error: str
    """The color of an error."""

    @property
    def is_terminal(self) -> bool:
        """Whether the theme leaves the background and the text to the terminal."""
        return self.background is None

    def style(
        self,
        *,
        role: str | None = None,
        bold: bool = False,
        italic: bool = False,
        dim: bool = False,
        underline: bool = False,
        reverse: bool = False,
        on_surface: bool = False,
    ) -> Style | None:
        """
        The style of text with a role and looks, in this theme.

        Args:
            role: What the text is: ``'accent'``, ``'link'``, ``'heading'``, ``'code'``,
                ``'string'``, ``'number'``, ``'keyword'``, ``'warning'``, ``'error'``,
                ``'border'``, or ``None`` for plain text.
            bold: Whether the text is bold.
            italic: Whether the text is italic.
            dim: Whether the text is secondary.
            underline: Whether the text is underlined.
            reverse: Whether the text and its background change places.
            on_surface: Whether the text is on the surface color, not on the background.

        Returns:
            The style, or ``None`` when the text has the look of plain text in the
            colors of the terminal.
        """
        looks = {
            'bold': bold,
            'italic': italic,
            'dim': dim,
            'underline': underline,
            'reverse': reverse,
        }
        return _style(
            self,
            role,
            frozenset(name for name, is_on in looks.items() if is_on),
            on_surface,
        )

    def style_of(self, run: Run) -> Style | None:
        """The style of a run of a document in this theme."""
        role = 'link' if run.target is not None else 'code' if run.code else run.role
        looks = {
            'bold': run.bold,
            'italic': run.italic,
            'dim': run.dim,
            'crossed_out': run.strike,
            'underline': run.target is not None,
        }
        return _style(
            self, role, frozenset(name for name, is_on in looks.items() if is_on), False
        )


@functools.cache
def _style(
    theme: Theme, role: str | None, looks: frozenset[str], on_surface: bool
) -> Style | None:
    """One style for each role and set of looks in each theme, made once."""
    color: str | None = getattr(theme, role) if role else None
    bold, italic = 'bold' in looks, 'italic' in looks
    strike, underline = 'crossed_out' in looks, 'underline' in looks
    if theme.is_terminal:
        is_dim = 'dim' in looks or role == 'border'
        is_reverse = 'reverse' in looks
        if not (color or is_dim or is_reverse or bold or italic or strike or underline):
            return None
        return Style(
            color,
            bold=bold,
            italic=italic,
            dim=is_dim,
            crossed_out=strike,
            underline=underline,
            reverse=is_reverse,
        )
    foreground = color or (theme.muted if 'dim' in looks else theme.text)
    background = theme.surface if on_surface else theme.background
    if 'reverse' in looks:
        foreground, background = background, foreground
    return Style(
        foreground,
        background,
        bold=bold,
        italic=italic,
        crossed_out=strike,
        underline=underline,
    )


UNSET = Style()


def themed_style(theme: Theme, style: Style | None) -> Style:
    """``style`` with the text and background colors of ``theme`` where it has none."""
    if style is None:
        return Style(theme.text, theme.background)
    foreground = style.foreground
    modifiers = style.modifiers
    is_dim = 'dim' in modifiers
    if foreground is None:
        foreground = theme.muted if is_dim else theme.text
        is_dim = False
    return Style(
        foreground,
        style.background or theme.background,
        bold='bold' in modifiers,
        italic='italic' in modifiers,
        dim=is_dim,
        underline='underline' in modifiers,
        reverse='reverse' in modifiers,
        crossed_out='crossed_out' in modifiers,
        blink='blink' in modifiers,
        hidden='hidden' in modifiers,
    )


def themed_text(theme: Theme, text: StyledText) -> StyledText:
    """``text`` with the colors of ``theme`` in every span that has none of its own."""
    return StyledText(
        [
            TextSpan(span.text, style=themed_style(theme, span.style))
            for span in text.spans
        ]
    )


def theme_widget(theme: Theme, widget: Widget) -> None:
    """Give ``widget`` the colors of ``theme`` in every style that it does not set."""
    plain = Style(theme.text, theme.background)
    accent = Style(theme.accent, theme.background)
    chosen = Style(theme.accent, theme.background, bold=True)
    border = Style(theme.border, theme.background)
    muted = Style(theme.muted, theme.background)
    styles = {
        'style': accent if type(widget).__name__ == 'Sparkline' else plain,
        'highlight_style': chosen,
        'row_highlight_style': chosen,
        'column_highlight_style': chosen,
        'cell_highlight_style': chosen,
        'border_style': border,
        'title_style': Style(theme.text, theme.background, bold=True),
        'thumb_style': accent,
        'track_style': border,
        'begin_style': border,
        'end_style': border,
        'filled_style': accent,
        'unfilled_style': border,
        'gauge_style': Style(theme.accent, theme.surface),
        'bar_style': accent,
        'value_style': Style(theme.background, theme.accent, bold=True),
        'label_style': plain,
        'absent_value_style': border,
        'month_header_style': Style(
            theme.heading or theme.text, theme.background, bold=True
        ),
        'weekdays_header_style': muted,
        'surrounding_style': muted,
    }
    for name, style in styles.items():
        if getattr(widget, name, None) == UNSET:
            setattr(widget, name, style)
    block = getattr(widget, 'block', None)
    if block is not None:
        theme_widget(theme, block)


def _theme(name: str, colors: str) -> Theme:
    """A theme from its colors, in the order of the attributes of ``Theme``."""
    return Theme(name, *colors.split())


TERMINAL = Theme(
    'terminal',
    background=None,
    surface=None,
    text=None,
    muted=None,
    border=None,
    accent='cyan',
    link='cyan',
    heading=None,
    code='cyan',
    string='green',
    number='cyan',
    keyword='magenta',
    warning='yellow',
    error='red',
)
"""The colors without a theme: the terminal's own, with its named colors for accents."""

THEMES: dict[str, Theme] = {
    'xnano-day': _theme(
        'xnano-day',
        '#f4f2e6 #e1ded2 #2e2216 #525551 #abb5b4 #a55611 #2867b0 '
        '#27170b #995016 #3c6829 #2867b0 #8f3f5d #91620a #ae391c',
    ),
    'xnano-night': _theme(
        'xnano-night',
        '#1a1410 #2a2018 #e8dfcc #a39683 #6b5640 #e0c67e #9fc9e5 '
        '#f3e6c8 #e0c67e #b5cf9f #9fc9e5 #dbb5c9 #e2b75a #e8917c',
    ),
    'zed-dark': _theme(
        'zed-dark',
        '#282c33 #2f343e #dce0e5 #a9afbc #464b57 #74ade8 #6eb4bf '
        '#d07277 #a1c181 #a1c181 #bf956a #b477cf #dec184 #d07277',
    ),
    'zed-light': _theme(
        'zed-light',
        '#fafafa #ebebec #242529 #58585a #c9c9ca #5c78e2 #3882b7 '
        '#d3604f #649f57 #649f57 #ad6e25 #a449ab #a48819 #d36151',
    ),
    'one-dark-pro': _theme(
        'one-dark-pro',
        '#282c34 #21252b #abb2bf #7f848e #3e4452 #528bff #61afef '
        '#e06c75 #98c379 #98c379 #d19a66 #c678dd #e5c07b #e06c75',
    ),
    'one-dark': _theme(
        'one-dark',
        '#282c34 #21252b #abb2bf #828997 #3e4451 #528bff #56b6c2 '
        '#e06c75 #98c379 #98c379 #d19a66 #c678dd #e5c07b #e06c75',
    ),
    'one-light': _theme(
        'one-light',
        '#fafafa #eaeaeb #383a42 #696c77 #dbdbdc #526fff #0184bc '
        '#e45649 #50a14f #50a14f #986801 #a626a4 #c18401 #e45649',
    ),
    'dracula': _theme(
        'dracula',
        '#282a36 #21222c #f8f8f2 #6272a4 #44475a #bd93f9 #8be9fd '
        '#bd93f9 #50fa7b #f1fa8c #ffb86c #ff79c6 #f1fa8c #ff5555',
    ),
    'monokai': _theme(
        'monokai',
        '#272822 #1e1f1c #f8f8f2 #88846f #414339 #f92672 #66d9ef '
        '#a6e22e #fd971f #e6db74 #ae81ff #f92672 #e6db74 #f92672',
    ),
    'github-dark': _theme(
        'github-dark',
        '#0d1117 #161b22 #e6edf3 #7d8590 #30363d #2f81f7 #2f81f7 '
        '#79c0ff #79c0ff #a5d6ff #79c0ff #ff7b72 #d29922 #f85149',
    ),
    'github-light': _theme(
        'github-light',
        '#ffffff #f6f8fa #1f2328 #656d76 #d0d7de #0969da #0969da '
        '#0550ae #0550ae #0a3069 #0550ae #cf222e #9a6700 #cf222e',
    ),
    'anthropic-dark': _theme(
        'anthropic-dark',
        '#141413 #30302e #faf9f5 #b0aea5 #5e5d59 #d97757 #6a9bcc '
        '#faf9f5 #d97757 #788c5d #6a9bcc #d97757 #d97757 #bf4d43',
    ),
    'anthropic-light': _theme(
        'anthropic-light',
        '#faf9f5 #e8e6dc #141413 #5e5d59 #d1cfc5 #d97757 #527598 '
        '#141413 #a85e46 #677850 #527598 #a85e46 #a85e46 #bf4d43',
    ),
    'openai-dark': _theme(
        'openai-dark',
        '#0d0d0d #181818 #ffffff #afafaf #4a4a4a #f3f3f3 #66b5ff '
        '#ffffff #04b84c #04b84c #e25507 #66b5ff #e25507 #e02e2a',
    ),
    'openai-light': _theme(
        'openai-light',
        '#ffffff #f9f9f9 #0d0d0d #5d5d5d #d8d8d8 #181818 #0169cc '
        '#0d0d0d #00692a #00692a #923b0f #0169cc #923b0f #911e1b',
    ),
}
"""Every theme, by its name."""


def theme_of(name: str | None) -> Theme:
    """
    The theme with a name.

    Args:
        name: One of the names of [`ThemeName`][xnano.themes.ThemeName], or ``None`` for
            the colors of the terminal.

    Returns:
        The theme.

    Raises:
        ValueError: No theme has the name.
    """
    if name is None:
        return TERMINAL
    try:
        return THEMES[name]
    except (KeyError, TypeError):
        names = ', '.join(repr(known) for known in get_args(ThemeName))
        raise ValueError(
            f'xnano has no theme named {name!r}. Give one of these names: {names}. '
            f'Leave theme out to use the colors of the terminal.'
        ) from None
