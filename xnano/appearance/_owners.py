"""
xnano.appearance._owners

The look of a canvas, a placement or a region: the color, border, padding and margin properties,
the text modifiers, and the drawing of a changed look once per frame.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import xnano_core as _core
from xnano._internal._attributes import _SealedAttributes
from xnano._schema._appearance import ColorValue, Spacing
from xnano.appearance import BorderAppearance, Colors, MarginAppearance, PaddingAppearance
from xnano.appearance._look import Appearance

if TYPE_CHECKING:
    from typing_extensions import Self

    from xnano.canvas import Canvas
    from xnano.region import Region


class _Looked(_SealedAttributes):
    """
    The owner of a look: a canvas, a placement or a region.

    The mixin gives its subclass ``color``, ``border``, ``padding`` and ``margin``, and
    the machinery that draws a changed look once per frame. A subclass says where its look is
    kept (``_appearance``), how it is drawn (``_redraw_look``) and which canvas draws its
    frames (``_look_canvas``).
    """

    _appearance: Appearance | None = None
    _look_is_dirty: bool = False
    _applied_colors: tuple[ColorValue | None, ColorValue | None] = (None, None)

    if TYPE_CHECKING:

        @property
        def region(self) -> Region[int]:
            """The cells of the owner."""
            ...

    # -- what an owner provides ----------------------------------------------------------

    def _ensure_look(self) -> Appearance:
        """The look of this owner, created when it has none."""
        if self._appearance is None:
            self._appearance = Appearance(text=self._look_text())
        return self._appearance

    def _look_text(self) -> str:
        """The text this owner shows, for the look of a text owner."""
        return ''

    def _look_canvas(self) -> Canvas[object, object] | None:
        """The canvas whose frames draw this owner, or ``None`` when it has none."""
        return None

    def _look_size(self) -> tuple[int, int]:
        """The width and height that a percentage of padding or margin is a share of."""
        return (0, 0)

    def _redraw_look(self) -> None:
        """Draw the current look. Called once per change, before the next frame."""

    def _apply_content_colors(self, look: Appearance, surface: _core.Buffer) -> None:
        """Color and style cells that are not text, and undo a color that was cleared."""
        style = look.text_style()
        foreground, background = self._applied_colors
        if foreground is not None and look.foreground is None:
            surface.update(_core.ApplyStyle(_core.Style(foreground='reset')))
        if background is not None and look.background is None:
            surface.update(_core.ApplyStyle(_core.Style(background='reset')))
        if style is not None:
            surface.update(_core.ApplyStyle(style))
        self._applied_colors = (look.foreground, look.background)

    # -- drawing once per frame ----------------------------------------------------------

    def _look_changed(self) -> None:
        """Remember that the look changed; it is drawn once, before the next frame."""
        look = self._appearance
        if look is not None:
            look.revision += 1
        if self._look_is_dirty:
            return
        self._look_is_dirty = True
        canvas = self._look_canvas()
        if canvas is not None and not canvas._is_closed:
            canvas._look_is_dirty_for(self)

    def _flush_look(self) -> None:
        """Draw the look now if it changed since it was last drawn."""
        if not self._look_is_dirty:
            return
        self._look_is_dirty = False
        try:
            self._redraw_look()
        finally:
            canvas = self._look_canvas()
            if canvas is not None and not canvas._is_closed:
                canvas._look_was_drawn(self)

    # -- the appearance objects ----------------------------------------------------------

    @property
    def color(self) -> Colors:
        """
        The colors: ``color.fg`` for the text and ``color.bg`` for what is behind it.

        Each is a [`ColorSlot`][xnano.appearance.ColorSlot]. Assign a color name,
        an ``(red, green, blue)`` tuple, a [`Color`][xnano_core.Color] or another slot;
        ``'reset'`` clears the color.

        Examples:
            ```python
            import xnano

            with xnano.new(width=10, height=3) as canvas:
                label = canvas.write('hi')
                label.color.fg = 'red'
                label.color.bg = (0, 0, 80)
                label.color.bg.lighten(0.1)
                assert label.color.fg.value == xnano.Color('red')
            ```
        """
        return Colors(self)

    @property
    def border(self) -> BorderAppearance:
        """
        The border: its ``kind``, a setting for each side, its ``color`` and its ``title``.

        Assign ``'plain'``, ``'rounded'``, ``'double'`` or ``'thick'`` to draw a border
        on every side, ``True`` for ``'plain'`` and ``False`` to remove it. It works on any
        content, not only on text.

        The border, padding and margin are drawn around the content, so the placement grows
        by the cells they take. A widget with no size of its own is shrunk to fit its parent,
        border included.

        Examples:
            ```python
            import xnano

            with xnano.new(width=12, height=5) as canvas:
                card = canvas.write('hi', border='rounded')
                card.border.top = 'double'
                card.border.left = False
                card.border.color = 'cyan'
                card.border = False
                assert not card.border
            ```
        """
        return BorderAppearance(self)

    @border.setter
    def border(self, value: _core.BorderKind | bool) -> None:
        BorderAppearance(self)._assign_all(value)

    @property
    def padding(self) -> PaddingAppearance:
        """
        The space between the border and the content, edge by edge.

        Assign a number of cells, a percentage such as ``'10%'`` or a dictionary such as
        ``{'vertical': 1, 'horizontal': 2}``, or set one edge with ``padding.left = 2``.
        """
        return PaddingAppearance(self)

    @padding.setter
    def padding(self, value: Spacing) -> None:
        PaddingAppearance(self)._assign_all(value)

    @property
    def margin(self) -> MarginAppearance:
        """The transparent space outside the border, edge by edge, set like ``padding``."""
        return MarginAppearance(self)

    @margin.setter
    def margin(self, value: Spacing) -> None:
        MarginAppearance(self)._assign_all(value)


class _TextModifiers(_Looked):
    """
    The text modifiers of a canvas or a placement: bold, dim, italic and the rest.

    Each modifier is a property (``is_bold``) and a method that sets it and returns the owner
    (``bold()``), so a modifier can be read, assigned or chained.
    """

    @property
    def is_bold(self) -> bool:
        """Whether the text is bold."""
        look = self._appearance
        return False if look is None else look.is_bold

    @is_bold.setter
    def is_bold(self, value: bool) -> None:
        self._ensure_look().is_bold = value
        self._look_changed()

    @property
    def is_dim(self) -> bool:
        """Whether the text is dimmed."""
        look = self._appearance
        return False if look is None else look.is_dim

    @is_dim.setter
    def is_dim(self, value: bool) -> None:
        self._ensure_look().is_dim = value
        self._look_changed()

    @property
    def is_italic(self) -> bool:
        """Whether the text is italic."""
        look = self._appearance
        return False if look is None else look.is_italic

    @is_italic.setter
    def is_italic(self, value: bool) -> None:
        self._ensure_look().is_italic = value
        self._look_changed()

    @property
    def is_underlined(self) -> bool:
        """Whether the text is underlined."""
        look = self._appearance
        return False if look is None else look.is_underlined

    @is_underlined.setter
    def is_underlined(self, value: bool) -> None:
        self._ensure_look().is_underlined = value
        self._look_changed()

    @property
    def is_blinking(self) -> bool:
        """Whether the text blinks."""
        look = self._appearance
        return False if look is None else look.is_blinking

    @is_blinking.setter
    def is_blinking(self, value: bool) -> None:
        self._ensure_look().is_blinking = value
        self._look_changed()

    @property
    def is_reversed(self) -> bool:
        """Whether foreground and background are swapped."""
        look = self._appearance
        return False if look is None else look.is_reversed

    @is_reversed.setter
    def is_reversed(self, value: bool) -> None:
        self._ensure_look().is_reversed = value
        self._look_changed()

    @property
    def is_hidden(self) -> bool:
        """Whether the text is hidden."""
        look = self._appearance
        return False if look is None else look.is_hidden

    @is_hidden.setter
    def is_hidden(self, value: bool) -> None:
        self._ensure_look().is_hidden = value
        self._look_changed()

    @property
    def is_crossed_out(self) -> bool:
        """Whether the text is struck through."""
        look = self._appearance
        return False if look is None else look.is_crossed_out

    @is_crossed_out.setter
    def is_crossed_out(self, value: bool) -> None:
        self._ensure_look().is_crossed_out = value
        self._look_changed()

    def bold(self, value: bool = True) -> Self:
        """
        Make the text bold, or undo it with ``False``; the same as setting ``is_bold``.

        Args:
            value: Whether the text is bold.

        Returns:
            This canvas or placement, so calls can chain.

        Raises:
            TypeError: ``value`` is not ``True`` or ``False``.

        Examples:
            ```python
            import xnano

            with xnano.new(width=12, height=1) as canvas:
                title = canvas.write('Ready').bold().underline()
                assert title.is_bold and title.is_underlined
                title.bold(False)
                assert not title.is_bold
            ```
        """
        self.is_bold = value
        return self

    def dim(self, value: bool = True) -> Self:
        """
        Dim the text, or undo it with ``False``; the same as setting ``is_dim``.

        Args:
            value: Whether the text is dimmed.

        Returns:
            This canvas or placement, so calls can chain.

        Raises:
            TypeError: ``value`` is not ``True`` or ``False``.
        """
        self.is_dim = value
        return self

    def italic(self, value: bool = True) -> Self:
        """
        Make the text italic, or undo it with ``False``; the same as setting ``is_italic``.

        Args:
            value: Whether the text is italic.

        Returns:
            This canvas or placement, so calls can chain.

        Raises:
            TypeError: ``value`` is not ``True`` or ``False``.
        """
        self.is_italic = value
        return self

    def underline(self, value: bool = True) -> Self:
        """
        Underline the text, or undo it with ``False``; the same as setting ``is_underlined``.

        Args:
            value: Whether the text is underlined.

        Returns:
            This canvas or placement, so calls can chain.

        Raises:
            TypeError: ``value`` is not ``True`` or ``False``.
        """
        self.is_underlined = value
        return self

    def blink(self, value: bool = True) -> Self:
        """
        Make the text blink, or undo it with ``False``; the same as setting ``is_blinking``.

        Args:
            value: Whether the text blinks.

        Returns:
            This canvas or placement, so calls can chain.

        Raises:
            TypeError: ``value`` is not ``True`` or ``False``.
        """
        self.is_blinking = value
        return self

    def reverse(self, value: bool = True) -> Self:
        """
        Swap the foreground and background, or undo it with ``False``; the same as setting ``is_reversed``.

        Args:
            value: Whether foreground and background are swapped.

        Returns:
            This canvas or placement, so calls can chain.

        Raises:
            TypeError: ``value`` is not ``True`` or ``False``.
        """
        self.is_reversed = value
        return self

    def hidden(self, value: bool = True) -> Self:
        """
        Hide the text, or undo it with ``False``; the same as setting ``is_hidden``.

        Args:
            value: Whether the text is hidden.

        Returns:
            This canvas or placement, so calls can chain.

        Raises:
            TypeError: ``value`` is not ``True`` or ``False``.
        """
        self.is_hidden = value
        return self

    def crossed_out(self, value: bool = True) -> Self:
        """
        Strike the text through, or undo it with ``False``; the same as setting ``is_crossed_out``.

        Args:
            value: Whether the text is struck through.

        Returns:
            This canvas or placement, so calls can chain.

        Raises:
            TypeError: ``value`` is not ``True`` or ``False``.
        """
        self.is_crossed_out = value
        return self
