"""xnano.core.controllers.webui

---

HTML/flexbox controller for rendering grids as web markup. Translates
layout intent (flex direction, sizing, framing) into HTML, Tailwind,
and htmx attributes. The ``Web`` host that owns sessions and routes
lives in ``xnano.webui``.
"""

from __future__ import annotations

import dataclasses
import html
from typing import TYPE_CHECKING, Any, Callable, Sequence

from xnano._types import Area
from xnano.core.controllers.abstract import (
    AbstractController,
    AbstractControllerCapabilities,
)


if TYPE_CHECKING:
    from xnano._styles import TailwindStyle
    from xnano._types import Direction, Frame
    from xnano.core.controllers.abstract import AbstractLayoutConstraint
    from xnano.fields import GridFieldInfo


@dataclasses.dataclass
class _HtmlElement:
    """A single HTML element tree node.

    Attributes:
        tag: The HTML tag name (default "div").
        classes: CSS class names to apply.
        styles: Inline CSS style properties (key-value pairs).
        attrs: HTML attributes (values escaped at render time).
        children: Child elements or pre-rendered HTML strings.
    """

    tag: str = "div"
    """The HTML tag name."""
    classes: list[str] = dataclasses.field(default_factory=list)
    """CSS class names to apply."""
    styles: dict[str, str] = dataclasses.field(default_factory=dict)
    """Inline CSS style properties (key-value pairs)."""
    attrs: dict[str, str] = dataclasses.field(default_factory=dict)
    """HTML attributes (values escaped at render time)."""
    children: list[_HtmlElement | str] = dataclasses.field(
        default_factory=list
    )
    """Child elements or pre-rendered HTML strings."""

    def to_html(self) -> str:
        """Render this element tree to an HTML string.

        Returns:
            The complete HTML representation of this element and its
            children.
        """
        tag = html.escape(self.tag)
        parts: list[str] = [f"<{tag}"]

        if self.classes:
            # De-duplicate (first occurrence wins) — raw Tailwind
            # classes and frame-derived classes can overlap.
            class_attr = " ".join(dict.fromkeys(self.classes))
            parts.append(f' class="{html.escape(class_attr, quote=True)}"')

        if self.styles:
            style_pairs = [f"{k}: {v}" for k, v in self.styles.items()]
            style_attr = "; ".join(style_pairs)
            parts.append(f' style="{html.escape(style_attr, quote=True)}"')

        for attr_name, attr_value in self.attrs.items():
            escaped = html.escape(attr_value, quote=True)
            parts.append(f' {attr_name}="{escaped}"')

        parts.append(">")

        for child in self.children:
            if isinstance(child, str):
                parts.append(child)
            else:
                parts.append(child.to_html())

        parts.append(f"</{tag}>")
        return "".join(parts)


class WebController(AbstractController):
    """HTML/Flexbox-based controller for web rendering.

    Renders grids to an HTML element tree by translating layout intent
    (direction, gap, sizing, framing) into Tailwind CSS and flexbox,
    with click handlers and editable inputs wired via htmx endpoints.

    State and life cycle:
        - `_root`: The root HTML element for the frame.
        - `_stack`: Open container stack; top is current append target.
        - `_grid_stack`: Stack of grids; top grid is current field owner.
        - `_pending_frame`: Frame chrome waiting for next paint_field_slot
          (field frame, as opposed to grid frame which decorates
          immediately).
        - `_split_container_ids`: Set of `id()` values for elements already
          receiving flex split styling (avoids double-styling).
        - `click_targets`: Map of target ID → (grid, field_name) for click
          dispatch.
        - `input_targets`: Map of target ID → (grid, field_name) for
          editable ``Text`` inputs.
        - `grid_observer`: Optional callback fired once per grid painted
          in a frame — a web session uses it to register grid hooks the
          same way the terminal's ``track_frame_grid`` does.
    """

    def __init__(self) -> None:
        self._root: _HtmlElement | None = None
        self._stack: list[_HtmlElement] = []
        self._grid_stack: list[Any] = []
        self._pending_frame: Frame | None = None
        self._split_container_ids: set[int] = set()
        self.click_targets: dict[str, tuple[Any, str]] = {}
        self.input_targets: dict[str, tuple[Any, str]] = {}
        self._target_counter: int = 0
        self.grid_observer: Callable[[Any], None] | None = None

    @classmethod
    def get_capabilities(cls) -> AbstractControllerCapabilities:
        """Return web controller capabilities.

        Returns:
            Capabilities with no effects, movement, or absolute geometry
            support (flexbox handles layout).
        """
        return AbstractControllerCapabilities(
            supports_effects=False,
            supports_movement=False,
            supports_absolute_geometry=False,
        )

    def begin_viewport_frame(self) -> None:
        """Reset state for a new frame render."""
        self._root = None
        self._stack.clear()
        self._grid_stack.clear()
        self._pending_frame = None
        self._split_container_ids.clear()
        self.click_targets.clear()
        self.input_targets.clear()
        self._target_counter = 0

    def get_viewport_area(self) -> Area:
        """Return a dummy viewport area.

        The browser handles actual layout via flexbox; this exists for
        contract compliance. Returns a 1000×1000 area.

        Returns:
            A fixed dummy area (browser will resize via CSS).
        """
        return Area(x=0, y=0, width=1000, height=1000)

    def commit_requests(self) -> None:
        """No-op for web controller (immediate tree building)."""
        return None

    def measure_field_slot(
        self, value: Any, direction: "Direction", field: "GridFieldInfo"
    ) -> int:
        """Measure field slot size (browser measures; return 0).

        Returns:
            Always 0 (browser measures intrinsic size via CSS).
        """
        return 0

    def split_layout(
        self,
        area: Area,
        direction: "Direction",
        gap: int,
        constraints: Sequence["AbstractLayoutConstraint"],
    ) -> list[Area]:
        """Style current container as a flex layout.

        Appends flexbox styling (flex, flex-row/flex-col) to the current
        container in `_stack`, then returns an area per constraint (the
        browser divides the actual space).

        Args:
            area: The parent area (unused; browser lays out).
            direction: "horizontal" or "vertical" (maps to flex-row/col).
            gap: Gap in cells (converted to rem: `gap * 0.25`).
            constraints: Layout constraints per child.

        Returns:
            List of areas matching constraint count (all identical; the
            browser reflows).
        """
        if not self._stack:
            return []

        current = self._stack[-1]
        current.classes.append("flex")

        if direction == "horizontal":
            current.classes.append("flex-row")
        else:
            current.classes.append("flex-col")

        if gap > 0:
            current.styles["gap"] = f"{gap * 0.25}rem"

        self._split_container_ids.add(id(current))

        # Return one area per constraint; browser divides space.
        return [area] * len(constraints)

    def paint_frame(self, area: Area, frame: "Frame", *, z: int = 0) -> Area:
        """Paint frame chrome (border, title, padding).

        Implements a state machine:
          - If current container is not yet split (not in
            `_split_container_ids`), apply frame directly to it (grid's
            own frame, which always arrives before the split).
          - Otherwise, store in `_pending_frame` (field frame, consumed
            by the next `paint_field_slot`).

        Args:
            area: The area being framed (returned unchanged).
            frame: Frame with border, title, padding, etc.
            z: Z-index (unused in web).

        Returns:
            The area unchanged.
        """
        if self._stack and id(self._stack[-1]) not in (
            self._split_container_ids
        ):
            # BaseGrid's own frame: apply immediately to current container.
            self._apply_frame(self._stack[-1], frame)
        else:
            # Field frame: store for next paint_field_slot.
            self._pending_frame = frame

        return area

    def _apply_frame(
        self,
        element: _HtmlElement,
        frame: "Frame",
        resolved: "TailwindStyle | None" = None,
    ) -> None:
        """Apply frame chrome (border, title, padding) to an element.

        Args:
            element: The HTML element to decorate.
            frame: Frame with border, title, padding, etc.
            resolved: The field's lowered Tailwind classes, when it has
                any — frame values the classes already cover are
                skipped because the raw classes style them natively.
        """
        border_covered = (
            resolved is not None
            and resolved.border is not None
            and frame.border == resolved.border
        )
        if frame.border is not None and not border_covered:
            element.classes.append("border")
            if frame.border == "rounded":
                element.classes.append("rounded-lg")
            elif frame.border == "double":
                element.classes.remove("border")
                element.classes.append("border-4")
                element.classes.append("border-double")
            elif frame.border == "thick":
                element.classes.append("border-2")

        if frame.border is not None:
            border_color_covered = (
                resolved is not None
                and resolved.border_color is not None
                and frame.border_color == resolved.border_color
            )
            if frame.border_color is None:
                if not border_covered:
                    element.classes.append("border-zinc-600")
            elif not border_color_covered:
                from xnano.color import Color

                try:
                    color = Color.parse(frame.border_color)
                    element.styles["border-color"] = (
                        f"rgb({color.r}, {color.g}, {color.b})"
                    )
                except Exception:
                    pass

        background_covered = (
            resolved is not None
            and resolved.background is not None
            and frame.background == resolved.background
        )
        if frame.background is not None and not background_covered:
            from xnano.color import Color

            try:
                color = Color.parse(frame.background)
                element.styles["background-color"] = (
                    f"rgb({color.r}, {color.g}, {color.b})"
                )
            except Exception:
                pass

        if frame.padding is not None:
            from xnano._types import Padding

            padding = Padding.parse(frame.padding)
            padding_covered = (
                resolved is not None
                and resolved.padding is not None
                and padding == resolved.padding
            )
            if not padding_covered:
                element.styles["padding"] = (
                    f"{padding.top * 0.25}rem "
                    f"{padding.right * 0.5}rem "
                    f"{padding.bottom * 0.25}rem "
                    f"{padding.left * 0.5}rem"
                )

        if frame.title is not None:
            element.classes.append("relative")
            title_html = html.escape(frame.title)
            pos_class = (
                "-bottom-3" if (frame.title_position == "bottom") else "-top-3"
            )
            title_element = (
                f'<span class="absolute {pos_class} left-2 px-1 '
                f'text-xs bg-zinc-900">{title_html}</span>'
            )
            element.children.insert(0, title_element)

    def _apply_field_sizing(
        self,
        element: _HtmlElement,
        field: "GridFieldInfo | None",
        resolved: "TailwindStyle | None" = None,
    ) -> None:
        """Apply width/height sizing to a field wrapper element.

        Prototype-grade: sizing is approximate and may not match terminal
        exactly (e.g., `cells` in rem via line-height estimate).

        Args:
            element: The HTML element to size.
            field: The field with width/height sizing info (or None).
            resolved: The field's lowered Tailwind classes, when it has
                any — sizing the classes already cover is skipped
                because the raw classes size the element natively.
        """
        if field is None:
            return

        width_covered = (
            resolved is not None
            and resolved.width is not None
            and field.width == resolved.width
        )
        height_covered = (
            resolved is not None
            and resolved.height is not None
            and field.height == resolved.height
        )

        if field.width is not None and not width_covered:
            sizing = field.width
            if sizing.kind == "fraction":
                element.styles["flex-grow"] = str(sizing.value)
                element.classes.append("basis-0")
            elif sizing.kind == "percent":
                element.styles["flex-basis"] = f"{sizing.value}%"
            elif sizing.kind == "cells":
                element.styles["width"] = f"{sizing.value}ch"
                element.classes.append("flex-none")
            elif sizing.kind == "fit":
                element.classes.append("flex-none")

        if field.height is not None and not height_covered:
            sizing = field.height
            if sizing.kind == "cells":
                element.styles["height"] = f"{sizing.value * 1.5}rem"
            elif sizing.kind == "percent":
                element.styles["flex-basis"] = f"{sizing.value}%"
            elif sizing.kind == "fraction":
                element.styles["flex-grow"] = str(sizing.value)

        if field.width is None and field.height is None:
            element.classes.append("flex-1")

    def _render_input_text(
        self,
        wrapper: _HtmlElement,
        value: Any,
        grid: Any,
        field_name: str,
    ) -> None:
        """Render an editable ``Text`` as a real ``<input>`` element.

        The input syncs its value back through ``/xnano/input/{id}``
        with ``hx-swap="none"`` so the browser keeps the caret; the
        server-side ``Text.content`` updates and the next full render
        reflects it.
        """
        from xnano.webui.nodes import build_style_attrs

        target_id = f"i{self._target_counter}"
        self._target_counter += 1
        self.input_targets[target_id] = (grid, field_name)

        content = value.content if isinstance(value.content, str) else ""
        placeholder = value._placeholder_string() or ""
        classes, styles = build_style_attrs(
            color=value.color,
            background=value.background,
            modifiers=tuple(value.modifiers) if value.modifiers else None,
            align=value.align,
        )
        classes = [
            "bg-transparent",
            "border-b",
            "border-zinc-600",
            "outline-none",
            "w-full",
            *classes,
        ]
        style_attr = "; ".join(f"{k}: {v}" for k, v in styles.items())
        parts = [
            '<input type="text" name="value"',
            f' value="{html.escape(content, quote=True)}"',
            f' placeholder="{html.escape(placeholder, quote=True)}"',
            f' class="{html.escape(" ".join(classes), quote=True)}"',
        ]
        if style_attr:
            parts.append(f' style="{html.escape(style_attr, quote=True)}"')
        parts.append(
            f' hx-post="/xnano/input/{target_id}"'
            ' hx-trigger="input changed delay:300ms"'
            ' hx-swap="none"/>'
        )
        wrapper.children.append("".join(parts))

    def paint_field_slot(
        self,
        value: Any,
        area: Area,
        field: "GridFieldInfo | None",
        *,
        parent_z: int = 0,
        effect_key: str | None = None,
    ) -> None:
        """Paint a field slot (grid field value) to HTML.

        Dispatches on value type (BaseGrid, editable Text, AbstractComponent,
        AbstractWebNode, or plain value) and renders appropriately.
        Handles click wiring, pending frame chrome, and sizing.

        Args:
            value: The value to render (BaseGrid, component, string, etc.).
            area: The area being painted (unused; browser lays out).
            field: Field metadata (sizing, styling).
            parent_z: Parent z-index (unused).
            effect_key: Field name for click/input handler lookup.
        """
        if value is None:
            return

        wrapper = _HtmlElement()

        resolved: "TailwindStyle | None" = None
        if field is not None and field.class_name:
            from xnano._styles import resolve_tailwind_classes

            resolved = resolve_tailwind_classes(field.class_name)
            # Raw classes go out verbatim — the browser's Tailwind
            # runtime honors every one, including classes the terminal
            # cannot lower (shadow-*, hover:*, ...).
            wrapper.classes.extend(field.class_name)

        if field is not None:
            self._apply_field_sizing(wrapper, field, resolved)

        if field is not None:
            from xnano.webui.nodes import build_style_attrs

            # A derived inline style is skipped when the merged field
            # value equals the class-derived one (the raw class already
            # covers it); a differing value means an explicit kwarg
            # overrode the class, and inline styles beat classes.
            def _covered(field_value: Any, derived_value: Any) -> bool:
                return (
                    resolved is not None
                    and derived_value is not None
                    and field_value == derived_value
                )

            derived_modifiers = resolved.modifiers if resolved else None
            classes, styles = build_style_attrs(
                color=(
                    None
                    if _covered(field.color, resolved and resolved.color)
                    else field.color
                ),
                background=(
                    None
                    if _covered(
                        field.background, resolved and resolved.background
                    )
                    else field.background
                ),
                modifiers=(
                    None
                    if (
                        field.modifiers
                        and derived_modifiers
                        and tuple(field.modifiers) == derived_modifiers
                    )
                    else (tuple(field.modifiers) if field.modifiers else None)
                ),
                align=(
                    None
                    if _covered(field.align, resolved and resolved.align)
                    else field.align
                ),
            )
            wrapper.classes.extend(classes)
            wrapper.styles.update(styles)

        if self._pending_frame is not None:
            self._apply_frame(wrapper, self._pending_frame, resolved)
            self._pending_frame = None

        if effect_key is not None and self._grid_stack:
            from xnano.grid import _resolve_grid_mouse_handler

            grid = self._grid_stack[-1]
            handler = _resolve_grid_mouse_handler(grid, effect_key)
            if handler is not None:
                target_id = f"t{self._target_counter}"
                self._target_counter += 1
                self.click_targets[target_id] = (grid, effect_key)
                wrapper.attrs["hx-post"] = f"/xnano/click/{target_id}"
                wrapper.attrs["hx-target"] = "#xnano-app"
                wrapper.attrs["hx-swap"] = "innerHTML"
                wrapper.classes.append("cursor-pointer")
                wrapper.classes.append("select-none")

        if not self._stack:
            raise RuntimeError(
                "paint_field_slot called with empty stack; use "
                "render_grid_html to set up root and grid stack"
            )

        self._stack[-1].children.append(wrapper)

        from xnano.components.abstract import AbstractComponent
        from xnano.grid import BaseGrid

        if isinstance(value, BaseGrid):
            self._stack.append(wrapper)
            self._grid_stack.append(value)
            if self.grid_observer is not None:
                self.grid_observer(value)
            value._grid_build_frame(area, self)
            self._stack.pop()
            self._grid_stack.pop()
            return

        # Editable inputs render as real <input> elements (an input Text
        # is also an AbstractComponent, so this check comes first).
        from xnano._types import is_input_text

        if (
            is_input_text(value)
            and effect_key is not None
            and self._grid_stack
        ):
            self._render_input_text(
                wrapper, value, self._grid_stack[-1], effect_key
            )
            return

        if isinstance(value, AbstractComponent):
            if not value.visible:
                return
            from xnano.components.abstract import ComponentRenderContext
            from xnano.webui.nodes import AbstractWebNode

            ctx = ComponentRenderContext(area=area)
            content = value.compose(ctx) if hasattr(value, "compose") else None
            node = None
            if content is not None:
                from xnano.core.content import Native, Run, TextBlock

                if (
                    isinstance(content, Native)
                    and content.interface_kind == "webui"
                ):
                    node = content.payload
                elif isinstance(content, TextBlock):
                    # Best-effort HTML from TextBlock
                    from xnano.webui.nodes import WebParagraphNode, WebSpanNode

                    if content.lines:
                        lines = []
                        for line in content.lines:
                            spans = []
                            for run in line:
                                if isinstance(run, Run):
                                    spans.append(
                                        WebSpanNode(
                                            content=run.text,
                                            color=run.color,
                                            background=run.background,
                                            modifiers=run.modifiers,
                                        )
                                    )
                            lines.append(tuple(spans))
                        node = WebParagraphNode(
                            lines=tuple(lines),
                            color=content.color,
                            background=content.background,
                            modifiers=content.modifiers,
                            align=content.align,
                            wrap=content.wrap,
                        )
                    else:
                        node = WebParagraphNode(
                            text=content.text or "",
                            color=content.color,
                            background=content.background,
                            modifiers=content.modifiers,
                            align=content.align,
                            wrap=content.wrap,
                        )
            if node is None:
                node = value.get_web_node(ctx)
            if isinstance(node, AbstractWebNode):
                wrapper.children.append(node.to_html())
            else:
                from xnano.components.text import Text as TerminalText

                if isinstance(value, TerminalText) and isinstance(
                    value.content, str
                ):
                    wrapper.children.append(html.escape(value.content))
                else:
                    wrapper.children.append(html.escape(str(value)))
            return

        from xnano.webui.nodes import AbstractWebNode

        if isinstance(value, AbstractWebNode):
            wrapper.children.append(value.to_html())
        else:
            wrapper.children.append(html.escape(str(value)))

    def render_grid_html(self, grid: Any) -> str:
        """Render a grid to an HTML string.

        Args:
            grid: The BaseGrid instance to render.

        Returns:
            The complete HTML string representation of the grid.
        """
        self.begin_viewport_frame()

        # The grid's own ``split_layout`` call adds the flex direction
        # classes; the root only carries the full-height anchor.
        root = _HtmlElement(classes=["h-full"])
        self._root = root
        self._stack.append(root)
        self._grid_stack.append(grid)
        if self.grid_observer is not None:
            self.grid_observer(grid)

        grid._grid_build_frame(self.get_viewport_area(), self)

        self._stack.pop()
        self._grid_stack.pop()

        return root.to_html()


__all__ = ("WebController",)
