"""xnano.beta.components.scrollbar

---

Display the position and visible range of scrollable content.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from xnano.beta.components.component import Component
from xnano.beta.core.content import Scrollbar as ScrollbarContent
from xnano.beta.types import ScrollbarOrientationLike

if TYPE_CHECKING:
    from xnano.beta.colors import ColorLike
    from xnano.beta.components.component import ComponentRenderContext
    from xnano.beta.types import ScrollHandle


@dataclasses.dataclass
class Scrollbar(Component):
    """Display the visible range of scrollable content.

    Lengths and position are clamped on every frame, so live updates cannot
    move the thumb outside the track.

    Example:
        ``Scrollbar(content_length=200, viewport_length=25, position=50)``

    Attributes:
        content_length: Total scrollable content size.
        position: Current scroll offset within ``content_length``.
        viewport_length: Visible window size; drives thumb proportion.
        orientation: Which edge the scrollbar is drawn on.
        thumb: Optional thumb glyph.
        track: Optional track glyph.
        begin: Arrow symbol at the start; ``None`` omits it.
        end: Arrow symbol at the end; ``None`` omits it.
        color: Overall track and thumb style.
        thumb_color: Thumb foreground color.
        track_color: Track foreground color.
        begin_color: Begin-arrow color.
        end_color: End-arrow color.
    """

    content_length: int = 0
    """Total scrollable content size."""
    position: int = 0
    """Current scroll offset within ``content_length``."""
    viewport_length: int = 0
    """Visible window size; drives thumb proportion."""
    orientation: ScrollbarOrientationLike = "vertical_right"
    """Which edge the scrollbar is drawn on."""
    thumb: str | None = None
    """Optional thumb glyph."""
    track: str | None = None
    """Optional track glyph."""
    begin: str | None = None
    """Arrow symbol at the start; ``None`` omits it."""
    end: str | None = None
    """Arrow symbol at the end; ``None`` omits it."""
    color: "ColorLike | None" = None
    """Overall track and thumb style."""
    thumb_color: "ColorLike | None" = None
    """Thumb foreground color."""
    track_color: "ColorLike | None" = None
    """Track foreground color."""
    begin_color: "ColorLike | None" = None
    """Begin-arrow color."""
    end_color: "ColorLike | None" = None
    """End-arrow color."""

    _scroll_handle: "ScrollHandle | None" = dataclasses.field(
        default=None, init=False, repr=False, compare=False
    )
    _handle_content_length: int | None = dataclasses.field(
        default=None, init=False, repr=False, compare=False
    )
    _handle_viewport_length: int | None = dataclasses.field(
        default=None, init=False, repr=False, compare=False
    )

    def component_post_init(self) -> None:
        """Clamp initial lengths and position."""
        self._clamp_state()

    def _clamp_state(self) -> None:
        self.content_length = max(0, int(self.content_length))
        self.viewport_length = max(0, int(self.viewport_length))
        if self.viewport_length > 0:
            max_position = max(0, self.content_length - self.viewport_length)
        else:
            max_position = max(0, self.content_length)
        self.position = max(0, min(int(self.position), max_position))

    @classmethod
    def from_scroll_handle(
        cls,
        handle: "ScrollHandle",
        *,
        content_length: int | None = None,
        viewport_length: int | None = None,
        orientation: ScrollbarOrientationLike = "vertical_right",
        thumb: str | None = None,
        track: str | None = None,
        begin: str | None = None,
        end: str | None = None,
        color: "ColorLike | None" = None,
        thumb_color: "ColorLike | None" = None,
        track_color: "ColorLike | None" = None,
        begin_color: "ColorLike | None" = None,
        end_color: "ColorLike | None" = None,
        visible: bool = True,
        z: int = 0,
        fit_content: bool = True,
    ) -> "Scrollbar":
        """Build a scrollbar bound to a field scroll handle.

        The handle owns offset / follow mode. Callers (or the field
        controller) should pass the measured content and viewport lengths;
        the component never reaches into grid private dictionaries.

        Args:
            handle: Resolved ``ScrollHandle`` for a scrolled field.
            content_length: Total scrollable content size when known.
            viewport_length: Visible window size when known.
            orientation: Scrollbar edge placement.
            thumb: Optional thumb glyph.
            track: Optional track glyph.
            begin: Optional leading glyph.
            end: Optional trailing glyph.
            color: Overall foreground color.
            thumb_color: Thumb foreground color.
            track_color: Track foreground color.
            begin_color: Leading glyph color.
            end_color: Trailing glyph color.
            visible: Whether the scrollbar paints.
            z: Paint order relative to siblings.
            fit_content: Whether layout uses the natural scrollbar size.

        Returns:
            A ``Scrollbar`` that reads ``position`` from ``handle``.
        """
        instance = cls(
            content_length=content_length or 0,
            position=int(getattr(handle, "offset", 0) or 0),
            viewport_length=viewport_length or 0,
            orientation=orientation,
            thumb=thumb,
            track=track,
            begin=begin,
            end=end,
            color=color,
            thumb_color=thumb_color,
            track_color=track_color,
            begin_color=begin_color,
            end_color=end_color,
            visible=visible,
            z=z,
            fit_content=fit_content,
        )
        instance._scroll_handle = handle
        instance._handle_content_length = content_length
        instance._handle_viewport_length = viewport_length
        return instance

    def _sync_from_handle(self) -> None:
        handle = self._scroll_handle
        if handle is None:
            return
        if self._handle_content_length is not None:
            self.content_length = self._handle_content_length
        if self._handle_viewport_length is not None:
            self.viewport_length = self._handle_viewport_length
        self.position = int(getattr(handle, "offset", 0) or 0)
        self._clamp_state()

    def _compose_content(self) -> ScrollbarContent:
        self._sync_from_handle()
        self._clamp_state()
        return ScrollbarContent(
            content_length=self.content_length,
            position=self.position,
            viewport_length=max(0, self.viewport_length),
            orientation=self.orientation,
            color=self.color,
            thumb_color=self.thumb_color,
            track_color=self.track_color,
            begin_symbol=self.begin,
            end_symbol=self.end,
            z=self.z,
            visible=self.visible,
        )

    def compose(self, ctx: "ComponentRenderContext"):
        """Compose scrollbar content with a native paint fallback.

        Returns:
            Interface-neutral content for this scrollbar.
        """
        return self._compose_content()


__all__ = ("Scrollbar",)
