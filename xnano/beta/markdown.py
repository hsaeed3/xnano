"""xnano.beta.markdown

---

Load Markdown from text or a file, render one frame, or page through it
interactively.

The interactive viewer is a pager, not a one-shot render: it windows the
rendered lines to the viewport and moves that window in response to the
keyboard (arrows, ``j``/``k``, ``PageUp``/``PageDown``, ``space``,
``Home``/``End``, ``g``/``G``) and the mouse wheel, with ``q`` to quit.
A document taller than the screen can therefore be scrolled, which a
plain render cannot do.

Inline images paint as compact, never-upscaled half-block thumbnails.
Hovering (or pressing ``i`` / clicking) expands the active image toward
native cell resolution for a clearer look without paying full-size
decode cost for every picture on every frame.
"""

from __future__ import annotations

import dataclasses
import math
import pathlib
import sys
from typing import TYPE_CHECKING, Any

from xnano.beta.components.markdown import Markdown
from xnano.beta.core.content import CellSpan, Run, TextBlock

if TYPE_CHECKING:
    from xnano.beta.components.component import ComponentRenderContext
    from xnano.beta.core.frame import Frame

_MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdown", ".mkd", ".mkdn"}
_STATUS_ROWS = 1
"""Rows the viewer reserves at the bottom for its status line."""

_IMAGE_CAPTION_ROWS = 1
"""Rows reserved under every image for its caption strip."""

_THUMB_MAX_COLS = 40
"""Maximum terminal columns for a collapsed image thumbnail."""

_THUMB_MAX_ROWS = 12
"""Maximum terminal rows for a collapsed image thumbnail body."""

_EXPAND_MAX_COLS = 80
"""Maximum terminal columns for a hover/pin expanded preview."""

_EXPAND_MAX_ROWS = 28
"""Maximum terminal rows for a hover/pin expanded preview body."""

_IMAGE_GAP_ROWS = 1
"""Blank row after an image block so consecutive pictures breathe."""


@dataclasses.dataclass(frozen=True, slots=True)
class _ImageHitRegion:
    """Document-space hit target for one inline image block.

    Attributes:
        key: Stable identity for the image (resolved path string).
        start_row: First document row occupied by the block.
        end_row: Exclusive end document row of the block.
        width: Painted thumbnail/expanded width in cells.
    """

    key: str
    start_row: int
    end_row: int
    width: int


def load_markdown_source(
    source: str | bytes | pathlib.Path,
) -> tuple[str, pathlib.Path | None]:
    """Load UTF-8 markdown text and optional base path.

    Args:
        source: Filesystem path, literal markdown string, or bytes.

    Returns:
        ``(text, base_path)`` where ``base_path`` is the parent directory
        when ``source`` was a path.
    """
    if isinstance(source, pathlib.Path):
        text = source.read_text(encoding="utf-8")
        return text, source.parent
    if isinstance(source, bytes):
        return source.decode("utf-8"), None
    # ``source`` may be literal markdown rather than a path. A long or
    # otherwise invalid document raises ``OSError`` (e.g. "File name too
    # long") or ``ValueError`` (embedded NUL) from the path probe — that
    # just means it is not a filename, so fall through to treating it as
    # text instead of letting the probe crash the caller.
    try:
        path = pathlib.Path(source)
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8"), path.parent
    except (OSError, ValueError):
        pass
    return source, None


def is_markdown_path(path: str | pathlib.Path) -> bool:
    """Return whether ``path`` exists and has a supported Markdown suffix."""
    candidate = pathlib.Path(path)
    return (
        candidate.exists()
        and candidate.is_file()
        and candidate.suffix.lower() in _MARKDOWN_SUFFIXES
    )


def _native_cell_size(
    pixel_width: int,
    pixel_height: int,
) -> tuple[int, int]:
    """Map source pixels to half-block terminal cells without scaling.

    One cell is one source column wide and two source rows tall (upper /
    lower half-block colors), which is the sharpest mapping the cell
    renderer can express.
    """
    cols = max(1, int(pixel_width))
    rows = max(1, math.ceil(max(1, int(pixel_height)) / 2))
    return cols, rows


def _fit_cell_size(
    pixel_width: int,
    pixel_height: int,
    *,
    max_cols: int,
    max_rows: int,
) -> tuple[int, int]:
    """Return a cell size that never upscales past native half-blocks.

    Large sources are downscaled with LANCZOS by the ``Image`` component
    when composed into this box; small sources keep a 1:1 pixel→cell map
    so they stay crisp instead of becoming blocky full-width enlargements.
    """
    native_cols, native_rows = _native_cell_size(pixel_width, pixel_height)
    budget_cols = max(1, max_cols)
    budget_rows = max(1, max_rows)
    scale = min(
        1.0,
        budget_cols / native_cols,
        budget_rows / native_rows,
    )
    cols = max(1, round(native_cols * scale))
    rows = max(1, round(native_rows * scale))
    return cols, rows


def _truncate_label(text: str, width: int) -> str:
    """Return ``text`` clipped to ``width`` cells with an ellipsis if needed."""
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width == 1:
        return "…"
    return text[: width - 1] + "…"


@dataclasses.dataclass
class _ViewportBlock:
    """One laid-out block in the viewer's flattened row model.

    Attributes:
        kind: ``"text"`` or ``"image"``.
        lines: Styled run lines for a text block.
        image: Lazy ``(path, alt)`` tuple or decoded ``Image`` component.
        rows: Height of the block in terminal rows (body + caption + gap).
        image_width: Source pixel width when known.
        image_height: Source pixel height when known.
        image_key: Stable path string used for hover / pin targeting.
        alt: Accessible / caption label for an image block.
    """

    kind: str
    lines: tuple[tuple[Any, ...], ...]
    image: Any
    rows: int
    image_width: int = 0
    image_height: int = 0
    image_key: str = ""
    alt: str = ""


@dataclasses.dataclass
class MarkdownViewport(Markdown):
    """Block-aware Markdown windowed to a scroll offset.

    The document is parsed into an ordered run of text and image blocks
    (see ``markdown_blocks``); each frame composes only the blocks that
    fall inside ``[offset : offset + viewport]``. Text blocks paint their
    visible line slice and image blocks paint through the real
    :class:`~xnano.beta.components.image.Image` component, so a picture or
    GIF renders inline rather than being dropped.

    Images default to compact, never-upscaled thumbnails with a one-line
    caption. Hovering the pointer over a thumbnail (or pinning with a
    click / ``i``) expands that one image toward native cell resolution
    for a clearer view — only the active image pays the larger compose
    cost.

    Attributes:
        offset: First document row shown at the top of the view.
        reserved_rows: Rows the owning viewer reserves below the body.
        image_rows: Fallback thumbnail height when dimensions are unknown.
        thumb_max_cols: Collapse-mode column budget for image bodies.
        thumb_max_rows: Collapse-mode row budget for image bodies.
        expand_max_cols: Expanded-mode column budget for image bodies.
        expand_max_rows: Expanded-mode row budget for image bodies.
    """

    offset: int = 0
    """First document row shown at the top of the view."""
    reserved_rows: int = _STATUS_ROWS
    """Rows the owning viewer reserves below the body (its status line)."""
    image_rows: int = _THUMB_MAX_ROWS
    """Fallback thumbnail rows when image dimensions cannot be read."""
    thumb_max_cols: int = _THUMB_MAX_COLS
    """Maximum columns for collapsed image thumbnails."""
    thumb_max_rows: int = _THUMB_MAX_ROWS
    """Maximum body rows for collapsed image thumbnails."""
    expand_max_cols: int = _EXPAND_MAX_COLS
    """Maximum columns for the hover/pin expanded preview."""
    expand_max_rows: int = _EXPAND_MAX_ROWS
    """Maximum body rows for the hover/pin expanded preview."""

    _block_cache_key: Any = dataclasses.field(
        default=None, init=False, repr=False, compare=False
    )
    _block_cache: list[_ViewportBlock] | None = dataclasses.field(
        default=None, init=False, repr=False, compare=False
    )
    _image_cache: dict[str, Any] = dataclasses.field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _hovered_image_key: str | None = dataclasses.field(
        default=None, init=False, repr=False, compare=False
    )
    _pinned_image_key: str | None = dataclasses.field(
        default=None, init=False, repr=False, compare=False
    )
    _image_hit_regions: tuple[_ImageHitRegion, ...] = dataclasses.field(
        default=(), init=False, repr=False, compare=False
    )
    _layout_width: int = dataclasses.field(
        default=80, init=False, repr=False, compare=False
    )

    def _resolve_image_path(self, source: str) -> pathlib.Path | None:
        """Return the local path for an image source when it exists."""
        if not source or "://" in source:
            return None
        path = pathlib.Path(source)
        if not path.is_absolute() and self.base_path is not None:
            path = self.base_path / path
        if not path.is_file():
            return None
        return path

    def _resolve_image(self, source: str) -> Any:
        """Return a cached ``Image`` for ``source``, or ``None``."""
        path = self._resolve_image_path(source)
        if path is None:
            return None
        key = str(path)
        cached = self._image_cache.get(key)
        if cached is not None:
            return cached
        try:
            from xnano.beta.components.image import Image

            # ``contain`` + never-upscaled target boxes keep small assets
            # crisp and large assets LANCZOS-downscaled into the budget.
            # ``horizontal_pixels_per_cell=1`` is the sharpest half-block
            # mapping (one source column per cell).
            image = Image(
                source=str(path),
                fit="contain",
                horizontal_pixels_per_cell=1,
                correct_terminal_aspect=False,
            )
        except Exception:
            return None
        self._image_cache[key] = image
        return image

    def _get_image_size(self, path: pathlib.Path) -> tuple[int, int] | None:
        """Read image dimensions without decoding its frames."""
        try:
            from PIL import Image as pillow_image

            with pillow_image.open(path) as image:
                return image.size
        except Exception:
            return None

    def _is_image_expanded(self, key: str) -> bool:
        """Return whether ``key`` should paint at expanded clarity."""
        if not key:
            return False
        return key == self._pinned_image_key or key == self._hovered_image_key

    def _image_body_size(
        self,
        block: _ViewportBlock,
        *,
        terminal_width: int,
        viewport_rows: int,
    ) -> tuple[int, int]:
        """Return ``(cols, rows)`` for an image body in the current mode."""
        expanded = self._is_image_expanded(block.image_key)
        if block.image_width > 0 and block.image_height > 0:
            if expanded:
                max_cols = min(
                    terminal_width,
                    self.expand_max_cols,
                )
                max_rows = min(
                    max(1, viewport_rows - _IMAGE_CAPTION_ROWS - 1),
                    self.expand_max_rows,
                )
            else:
                max_cols = min(terminal_width, self.thumb_max_cols)
                max_rows = self.thumb_max_rows
            return _fit_cell_size(
                block.image_width,
                block.image_height,
                max_cols=max_cols,
                max_rows=max_rows,
            )
        # Unknown dimensions: keep a modest square-ish placeholder box.
        fallback_rows = (
            min(self.expand_max_rows, max(1, viewport_rows // 2))
            if expanded
            else self.image_rows
        )
        fallback_cols = min(
            terminal_width,
            self.expand_max_cols if expanded else self.thumb_max_cols,
            max(8, fallback_rows * 2),
        )
        return max(1, fallback_cols), max(1, fallback_rows)

    def _image_block_rows(
        self,
        block: _ViewportBlock,
        *,
        terminal_width: int,
        viewport_rows: int,
    ) -> int:
        """Return total rows for an image block (body + caption + gap)."""
        _, body_rows = self._image_body_size(
            block,
            terminal_width=terminal_width,
            viewport_rows=viewport_rows,
        )
        return body_rows + _IMAGE_CAPTION_ROWS + _IMAGE_GAP_ROWS

    def _blocks(self) -> list[_ViewportBlock]:
        """Return the parsed, image-resolved blocks for the document."""
        from xnano.beta.utils.markup import markdown_blocks

        key = (
            self.value,
            str(self.base_path),
            self.image_rows,
            self.thumb_max_cols,
            self.thumb_max_rows,
        )
        if self._block_cache is not None and self._block_cache_key == key:
            return self._block_cache

        resolved: list[_ViewportBlock] = []
        for block in markdown_blocks(self.value):
            if block[0] == "text":
                lines = block[1]
                resolved.append(
                    _ViewportBlock("text", lines, None, len(lines))
                )
                continue
            _, source, alt = block
            path = self._resolve_image_path(source)
            label = (alt or source or "image").strip() or "image"
            if path is None:
                placeholder = (
                    Run(
                        text=f"🖼  {label}",
                        modifiers=("dim", "italic"),
                    ),
                )
                resolved.append(
                    _ViewportBlock("text", (placeholder, ()), None, 2)
                )
            else:
                size = self._get_image_size(path)
                pixel_width, pixel_height = size or (0, 0)
                # Placeholder height until compose assigns the live size
                # for the current terminal / hover state.
                if pixel_width > 0:
                    _, body_rows = _fit_cell_size(
                        pixel_width,
                        pixel_height,
                        max_cols=self.thumb_max_cols,
                        max_rows=self.thumb_max_rows,
                    )
                else:
                    body_rows = self.image_rows
                resolved.append(
                    _ViewportBlock(
                        "image",
                        (),
                        (path, label),
                        body_rows + _IMAGE_CAPTION_ROWS + _IMAGE_GAP_ROWS,
                        pixel_width,
                        pixel_height,
                        str(path),
                        label,
                    )
                )
        self._block_cache_key = key
        self._block_cache = resolved
        return resolved

    def _sync_image_block_rows(
        self,
        *,
        terminal_width: int,
        viewport_rows: int,
    ) -> None:
        """Refresh each image block's row count for the active display mode."""
        for block in self._blocks():
            if block.kind != "image":
                continue
            block.rows = self._image_block_rows(
                block,
                terminal_width=terminal_width,
                viewport_rows=viewport_rows,
            )

    def viewport_height(self) -> int:
        """Return the visible row count for the current terminal size."""
        from xnano.beta.core.runtime import get_active_runtime

        runtime = get_active_runtime()
        height = runtime.size[1] if runtime is not None else 24
        return max(1, height - self.reserved_rows)

    def total_rows(self) -> int:
        """Return the document height in rows across all blocks."""
        width = self._layout_width
        viewport = self.viewport_height()
        self._sync_image_block_rows(
            terminal_width=width,
            viewport_rows=viewport,
        )
        return sum(block.rows for block in self._blocks())

    def max_offset(self) -> int:
        """Return the largest useful offset — the last full page of rows."""
        return max(0, self.total_rows() - self.viewport_height())

    def page_rows(self) -> int:
        """Return the offset delta for a page-sized jump (one row overlap)."""
        return max(1, self.viewport_height() - 1)

    def scroll_percentage(self) -> int:
        """Return how far the view has scrolled, from 0 to 100."""
        maximum = self.max_offset()
        if maximum <= 0:
            return 100
        return round(min(self.offset, maximum) / maximum * 100)

    def scroll_by(self, delta: int) -> None:
        """Move the view by ``delta`` rows, clamped to the document."""
        self.offset = min(self.max_offset(), max(0, self.offset + delta))

    def scroll_to_top(self) -> None:
        """Move the view to the first row."""
        self.offset = 0

    def scroll_to_bottom(self) -> None:
        """Move the view to the last page."""
        self.offset = self.max_offset()

    def has_expandable_image(self) -> bool:
        """Return whether the document contains at least one local image."""
        return any(block.kind == "image" for block in self._blocks())

    def active_image_key(self) -> str | None:
        """Return the pinned or hovered image key, if any."""
        return self._pinned_image_key or self._hovered_image_key

    def update_pointer(self, x: int, y: int) -> bool:
        """Update hover from body-local cell coordinates.

        Args:
            x: Column within the body field.
            y: Row within the body field (0 = top of the viewport).

        Returns:
            ``True`` when the hovered image identity changed.
        """
        document_row = min(self.offset, self.max_offset()) + max(0, y)
        previous = self._hovered_image_key
        hit_key: str | None = None
        for region in self._image_hit_regions:
            if (
                region.start_row <= document_row < region.end_row
                and 0 <= x < max(1, region.width + 2)
            ):
                hit_key = region.key
                break
        self._hovered_image_key = hit_key
        return previous != hit_key

    def clear_pointer(self) -> bool:
        """Clear hover state.

        Returns:
            ``True`` when a hovered image was cleared.
        """
        if self._hovered_image_key is None:
            return False
        self._hovered_image_key = None
        return True

    def toggle_pin_at(self, x: int, y: int) -> bool:
        """Pin or unpin the image under body-local coordinates.

        Args:
            x: Column within the body field.
            y: Row within the body field.

        Returns:
            ``True`` when pin state changed.
        """
        document_row = min(self.offset, self.max_offset()) + max(0, y)
        for region in self._image_hit_regions:
            if (
                region.start_row <= document_row < region.end_row
                and 0 <= x < max(1, region.width + 2)
            ):
                if self._pinned_image_key == region.key:
                    self._pinned_image_key = None
                else:
                    self._pinned_image_key = region.key
                    self._hovered_image_key = region.key
                return True
        return False

    def toggle_expand(self) -> bool:
        """Toggle expand on the hovered, pinned, or first visible image.

        Returns:
            ``True`` when pin state changed.
        """
        if self._pinned_image_key is not None:
            self._pinned_image_key = None
            return True
        if self._hovered_image_key is not None:
            self._pinned_image_key = self._hovered_image_key
            return True
        # Fall back to the first image currently intersecting the viewport.
        top = min(self.offset, self.max_offset())
        bottom = top + self.viewport_height()
        for region in self._image_hit_regions:
            if region.end_row > top and region.start_row < bottom:
                self._pinned_image_key = region.key
                return True
        for block in self._blocks():
            if block.kind == "image" and block.image_key:
                self._pinned_image_key = block.image_key
                return True
        return False

    def _build_image_caption(
        self,
        block: _ViewportBlock,
        *,
        width: int,
        body_cols: int,
        expanded: bool,
    ) -> tuple[tuple[Any, ...], ...]:
        """Return caption run-lines under an image body."""
        label = block.alt or pathlib.Path(block.image_key).name or "image"
        if block.image_width > 0 and block.image_height > 0:
            dims = f"{block.image_width}×{block.image_height}"
        else:
            dims = f"{body_cols}c"
        if expanded:
            hint = (
                "click/i collapse"
                if self._pinned_image_key == block.image_key
                else "expanded"
            )
            icon = "▣"
        else:
            hint = "hover/i expand"
            icon = "▸"
        # Prefer the human label; keep dims + hint when there is room.
        prefix = f" {icon} "
        suffix = f"  {dims}  ·  {hint}"
        available = max(0, width - len(prefix) - len(suffix))
        if available < 4:
            text = _truncate_label(f"{prefix}{label}", width)
        else:
            text = f"{prefix}{_truncate_label(label, available)}{suffix}"
        return (
            (
                Run(
                    text=text,
                    modifiers=("dim",),
                    color=self.color,
                    background=self.background,
                ),
            ),
        )

    def _compose_image_block(
        self,
        block: _ViewportBlock,
        *,
        terminal_width: int,
        viewport_rows: int,
        first_row: int,
        visible_rows: int,
    ) -> Any:
        """Compose one image block's visible slice (body + caption + gap)."""
        from xnano.beta.components.component import ComponentRenderContext
        from xnano.beta.core.content import CellCanvas
        from xnano.beta.core.rendering import lower_content
        from xnano.beta.types import Area

        body_cols, body_rows = self._image_body_size(
            block,
            terminal_width=terminal_width,
            viewport_rows=viewport_rows,
        )
        expanded = self._is_image_expanded(block.image_key)
        caption_lines = self._build_image_caption(
            block,
            width=terminal_width,
            body_cols=body_cols,
            expanded=expanded,
        )

        # Resolve / reuse the Image component once per path.
        if isinstance(block.image, tuple):
            source, alt = block.image
            image = self._resolve_image(str(source))
            if image is None:
                return lower_content(
                    TextBlock(
                        lines=(
                            (
                                Run(
                                    text=f"🖼  {alt}",
                                    modifiers=("dim", "italic"),
                                ),
                            ),
                        ),
                    )
                )
            block.image = image
            block.alt = alt

        canvas = block.image.compose(
            ComponentRenderContext(
                area=Area(
                    x=0,
                    y=0,
                    width=body_cols,
                    height=body_rows,
                )
            )
        )
        # Pad the body to the terminal width so the column slot is full
        # width while the picture itself stays left-aligned and sharp.
        padded_rows: list[tuple[CellSpan, ...]] = []
        for row_spans in canvas.rows:
            used = sum(len(span.text) for span in row_spans)
            if used < terminal_width:
                pad = terminal_width - used
                padded_rows.append((*row_spans, CellSpan(text=" " * pad)))
            else:
                padded_rows.append(tuple(row_spans))
        while len(padded_rows) < body_rows:
            padded_rows.append((CellSpan(text=" " * terminal_width),))

        # Flatten body rows + caption + trailing gap into one canvas so a
        # partial scroll window can slice across the caption cleanly.
        gap_row = (CellSpan(text=" " * terminal_width),)
        flat_rows: list[tuple[CellSpan, ...]] = list(padded_rows)
        caption_text = ""
        if caption_lines and caption_lines[0]:
            first = caption_lines[0][0]
            caption_text = getattr(first, "text", str(first))
        caption_text = _truncate_label(caption_text, terminal_width)
        pad = max(0, terminal_width - len(caption_text))
        flat_rows.append(
            (
                CellSpan(
                    text=caption_text + (" " * pad),
                    modifiers=("dim",),
                ),
            )
        )
        flat_rows.append(gap_row)

        window = tuple(flat_rows[first_row : first_row + visible_rows])
        return lower_content(
            CellCanvas(
                rows=window,
                width=terminal_width,
                height=visible_rows,
                z=self.z,
                visible=self.visible,
            )
        )

    def compose(self, ctx: "ComponentRenderContext[Any]") -> Any:
        """Compose the blocks currently inside the viewport."""
        import xnano_core.core as core
        from xnano_core.rust import native

        from xnano.beta.core.content import Native
        from xnano.beta.core.rendering import lower_content
        from xnano.beta.core.runtime import get_active_runtime

        del ctx  # area comes from the active runtime / field slot
        viewport = self.viewport_height()
        runtime = get_active_runtime()
        width = runtime.size[0] if runtime is not None else 80
        self._layout_width = width
        self._sync_image_block_rows(
            terminal_width=width,
            viewport_rows=viewport,
        )
        top = min(self.offset, self.max_offset())
        bottom = top + viewport

        children: list[Any] = []
        constraints: list[Any] = []
        hit_regions: list[_ImageHitRegion] = []
        row = 0
        for block in self._blocks():
            start, end = row, row + block.rows
            row = end
            if block.kind == "image" and block.image_key:
                body_cols, _ = self._image_body_size(
                    block,
                    terminal_width=width,
                    viewport_rows=viewport,
                )
                hit_regions.append(
                    _ImageHitRegion(
                        key=block.image_key,
                        start_row=start,
                        end_row=end,
                        width=body_cols,
                    )
                )
            if end <= top or start >= bottom:
                continue
            visible_rows = min(end, bottom) - max(start, top)
            if visible_rows <= 0:
                continue
            if block.kind == "text":
                first = max(start, top) - start
                window = block.lines[first : first + visible_rows]
                node = lower_content(
                    TextBlock(
                        lines=tuple(window),
                        color=self.color,
                        background=self.background,
                        modifiers=self.modifiers,
                        align=self.align,
                        wrap=self.wrap,
                    )
                )
            else:
                first = max(start, top) - start
                node = self._compose_image_block(
                    block,
                    terminal_width=width,
                    viewport_rows=viewport,
                    first_row=first,
                    visible_rows=visible_rows,
                )
            children.append(node)
            constraints.append(native.Constraint.length(visible_rows))

        self._image_hit_regions = tuple(hit_regions)

        if not children:
            return TextBlock(lines=(), visible=self.visible)
        column = core.CoreRenderNode.column(
            children, constraints=constraints, gap=0
        )
        return Native(interface_kind="terminal", payload=column)


def _build_status_text(viewport: MarkdownViewport) -> str:
    """Return the status line for the viewer's current scroll position.

    The scroll percentage leads so it survives truncation on a narrow
    terminal; the navigation hints follow.
    """
    if viewport.has_expandable_image():
        if viewport._pinned_image_key is not None:
            image_hint = "i collapse image"
        elif viewport._hovered_image_key is not None:
            image_hint = "i pin image"
        else:
            image_hint = "hover/i image"
        hints = f"q quit · ↑/↓ scroll · space page · {image_hint}"
    else:
        hints = "q quit · ↑/↓ scroll · space page · home/end jump"
    return f" {viewport.scroll_percentage():>3}%  ·  {hints} "


def _create_markdown_document(
    source: str | bytes | pathlib.Path,
) -> Any:
    """Build the interactive pager grid shared by render and run."""
    from xnano.beta import hooks
    from xnano.beta.components.text import Text
    from xnano.beta.fields import Field
    from xnano.beta.grids import BaseGrid

    text, base_path = load_markdown_source(source)

    class MarkdownViewer(BaseGrid):
        """Interactive, scrollable Markdown pager.

        Attributes:
            body: Windowed Markdown content in view.
            status: Footer showing position and key hints.
        """

        body: MarkdownViewport = Field(
            default=MarkdownViewport(text, base_path=base_path),
        )
        """Windowed Markdown content currently in view."""
        status: Text = Field(
            default=Text("", modifiers=("dim", "reversed")),
            height=1,
        )
        """Footer showing scroll position and navigation hints."""

        @hooks.on_poll("frame")
        def _refresh_status(self) -> None:
            self.status.content = _build_status_text(self.body)

        @hooks.on_keyboard("down", "j")
        def _line_down(self) -> None:
            self.body.scroll_by(1)

        @hooks.on_keyboard("up", "k")
        def _line_up(self) -> None:
            self.body.scroll_by(-1)

        @hooks.on_keyboard("pagedown", "space", "ctrl+f")
        def _page_down(self) -> None:
            self.body.scroll_by(self.body.page_rows())

        @hooks.on_keyboard("pageup", "b", "ctrl+b")
        def _page_up(self) -> None:
            self.body.scroll_by(-self.body.page_rows())

        @hooks.on_keyboard("home", "g")
        def _go_top(self) -> None:
            self.body.scroll_to_top()

        @hooks.on_keyboard("end", "shift+g")
        def _go_bottom(self) -> None:
            self.body.scroll_to_bottom()

        @hooks.on_keyboard("i")
        def _toggle_image(self) -> None:
            self.body.toggle_expand()

        @hooks.on_mouse(kind="scroll_down")
        def _wheel_down(self) -> None:
            self.body.scroll_by(3)

        @hooks.on_mouse(kind="scroll_up")
        def _wheel_up(self) -> None:
            self.body.scroll_by(-3)

        @hooks.on_mouse(kind="move")
        def _pointer_move(self, ctx: Any) -> None:
            # Absolute cell coordinates: body is the full viewport minus
            # the reserved status row. Field-scoped mouse.field tagging is
            # not guaranteed on every host, so hit-test by geometry.
            mouse = ctx.mouse
            if mouse is None:
                return
            height = ctx.terminal.size[1]
            if mouse.y >= max(0, height - _STATUS_ROWS):
                self.body.clear_pointer()
                return
            self.body.update_pointer(mouse.x, mouse.y)

        @hooks.on_mouse(kind="press")
        def _pointer_click(self, ctx: Any) -> None:
            mouse = ctx.mouse
            if mouse is None:
                return
            height = ctx.terminal.size[1]
            if mouse.y >= max(0, height - _STATUS_ROWS):
                return
            self.body.toggle_pin_at(mouse.x, mouse.y)

        @hooks.on_keyboard("q", "esc", "ctrl+c")
        def _quit(self, ctx: Any) -> None:
            # Esc collapses a pinned image first; a second press quits.
            keyboard = getattr(ctx, "keyboard", None)
            if (
                keyboard is not None
                and keyboard.matches("esc")
                and self.body._pinned_image_key is not None
            ):
                self.body._pinned_image_key = None
                return
            ctx.terminal.request_exit()

    return MarkdownViewer()


def run_markdown(
    source: str | bytes | pathlib.Path,
    *,
    terminal: Any | None = None,
) -> None:
    """Load and page through a Markdown document interactively.

    Uses ``Terminal.run`` when a live terminal is available so the
    document can be scrolled; otherwise renders a single frame.

    Args:
        source: Path, literal markdown, or bytes.
        terminal: Optional terminal instance to reuse.
    """
    from xnano.beta.terminal import Terminal

    document = _create_markdown_document(source)
    host = terminal if terminal is not None else Terminal()
    # An explicitly offscreen terminal (``Terminal.offscreen(...)``) must
    # never be run through the live loop — it has no real input source to
    # poll and ``.run()`` would block forever waiting for it. Only fall
    # back to the build-capability check when the caller didn't already
    # tell us which kind of terminal this is.
    if getattr(host, "surface", None) == "offscreen":
        live = False
    else:
        live = Terminal.supports_live_terminal() and sys.stdout.isatty()
    if live and hasattr(host, "run"):
        # Enable the wheel + hover tracking for scroll / image expand.
        try:
            host.device.mouse_capture = True
        except Exception:
            pass
        host.run(document)
    else:
        host.render(document)


def render_markdown(
    source: str | bytes | pathlib.Path,
    *,
    terminal: Any | None = None,
) -> "Frame":
    """Render a Markdown document and return its frame.

    Args:
        source: Path, literal markdown, or bytes.
        terminal: Optional terminal instance to reuse.

    Returns:
        The immutable frame produced by the terminal.
    """
    from xnano.beta.terminal import Terminal

    host = terminal if terminal is not None else Terminal()
    try:
        return host.render(_create_markdown_document(source))
    finally:
        if terminal is None:
            host.close()


__all__ = (
    "MarkdownViewport",
    "is_markdown_path",
    "load_markdown_source",
    "render_markdown",
    "run_markdown",
)
