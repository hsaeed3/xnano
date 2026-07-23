"""xnano.beta.terminal

---

Run beta grids and components in live or offscreen terminal sessions.
"""

from __future__ import annotations

import sys
from typing import Any, Generic, Sequence, TypeVar

from xnano.beta.colors import ColorLike
from xnano.beta.core.frame import Frame
from xnano.beta.core.runtime import Runtime
from xnano.beta.types import (
    Alignment,
    Border,
    CharacterModifier,
    Direction,
    FrameTitlePosition,
    PaddingLike,
    Side,
)

StateT = TypeVar("StateT")


class Terminal(Generic[StateT]):
    """Paint and interact with an application in a terminal.

    ``Terminal`` selects a live session when one is available and otherwise
    uses an offscreen buffer. Use :meth:`offscreen` explicitly in tests.

    Attributes:
        runtime: Runtime owned by the terminal.
        state: Application state shared with event hooks.
        device: Display controls for the active session.
        cursor: Cursor controls for the active session.
        actions: Synthetic action performer.
        stage: Layout stage for the current root.
        size: Viewport width and height in cells.
        focused_group: Name of the focused field group.
        surface: Active presentation surface.

    Example:
        >>> terminal = Terminal.offscreen(cols=24, rows=3)
        >>> frame = terminal.render("Hello, xnano")
        >>> "Hello, xnano" in frame.text
        True
        >>> terminal.close()
    """

    def __init__(
        self,
        *,
        state: StateT | None = None,
        title: str | None = None,
        tick_interval: int = 16,
    ) -> None:
        self._state = state
        self._title = title
        self._tick_interval = tick_interval
        self._runtime: Runtime[StateT] | None = None
        self.surface = "terminal"

    @classmethod
    def offscreen(
        cls,
        *,
        cols: int = 40,
        rows: int = 12,
        state: StateT | None = None,
        title: str | None = None,
    ) -> "Terminal[StateT]":
        """Create a terminal backed by an in-memory cell buffer."""
        terminal = cls(state=state, title=title)
        terminal._runtime = Runtime.offscreen(
            cols,
            rows,
            state=state,
            title=title,
        )
        terminal.surface = "offscreen"
        return terminal

    @staticmethod
    def supports_live_terminal() -> bool:
        """Return whether interactive terminal sessions are available."""
        return Runtime.supports_live_terminal()

    def _ensure_runtime(self, *, live: bool | None = None) -> Runtime[StateT]:
        if self._runtime is not None:
            return self._runtime
        use_live = (
            self.supports_live_terminal() and sys.stdout.isatty()
            if live is None
            else live
        )
        if use_live:
            self._runtime = Runtime.live(
                state=self._state,
                title=self._title,
                tick_interval=self._tick_interval,
            ).enter()
        else:
            self._runtime = Runtime.offscreen(
                state=self._state,
                title=self._title,
            )
            self.surface = "offscreen"
        return self._runtime

    def __enter__(self) -> "Terminal[StateT]":
        self._ensure_runtime(live=True)
        return self

    def __exit__(self, *exception: Any) -> None:
        self.close()

    @property
    def runtime(self) -> Runtime[StateT]:
        """Runtime owned by this terminal."""
        return self._ensure_runtime()

    @property
    def state(self) -> StateT | None:
        """Application state shared with event hooks."""
        return self.runtime.state if self._runtime is not None else self._state

    @state.setter
    def state(self, value: StateT | None) -> None:
        self._state = value
        if self._runtime is not None:
            self._runtime.state = value

    @property
    def device(self):
        """Display controls."""
        return self.runtime.device

    @property
    def cursor(self):
        """Caret controls."""
        return self.runtime.cursor

    @property
    def actions(self):
        """Synthetic action performer."""
        return self.runtime.actions

    @property
    def stage(self):
        """Layout stage for the current root."""
        return self.runtime.stage

    @property
    def size(self) -> tuple[int, int]:
        """Viewport width and height in cells."""
        return self.runtime.size

    @property
    def focused_group(self) -> str | None:
        """Name of the focused field group."""
        return self.runtime.focused_group

    def attach_grid(self, grid: Any) -> None:
        """Set the grid used by subsequent renders and dispatch."""
        self.runtime.set_root(grid)

    def render(
        self,
        *renderables: Any,
        color: ColorLike | None = None,
        background: ColorLike | None = None,
        modifiers: Sequence[CharacterModifier] | None = None,
        align: Alignment | None = None,
        border: Border | None = None,
        border_sides: Sequence[Side] | None = None,
        border_color: ColorLike | None = None,
        title: str | None = None,
        title_position: FrameTitlePosition | None = None,
        padding: PaddingLike | None = None,
        gap: int = 0,
        direction: Direction = "vertical",
    ) -> Frame:
        """Paint one frame and return its immutable snapshot.

        Args:
            *renderables: Grids, components, content primitives, or plain
                values to paint.
            color: Foreground color applied to plain values.
            background: Background color for the rendered area.
            modifiers: Character modifiers applied to plain values.
            align: Horizontal alignment applied to plain values.
            border: Border style around the rendered area.
            border_sides: Border sides to draw.
            border_color: Border foreground color.
            title: Optional border title.
            title_position: Border edge that holds the title.
            padding: Space between the border and content.
            gap: Cells between multiple renderables.
            direction: Direction used to lay out multiple renderables.

        Returns:
            A snapshot of the rendered terminal frame.
        """
        runtime = self._ensure_runtime()
        if renderables:
            runtime.set_root(renderables[0] if len(renderables) == 1 else None)
        return runtime.render(
            *renderables,
            color=color,
            background=background,
            modifiers=modifiers,
            align=align,
            border=border,
            border_sides=border_sides,
            border_color=border_color,
            title=title,
            title_position=title_position,
            padding=padding,
            gap=gap,
            direction=direction,
        )

    def run(
        self,
        *renderables: Any,
        color: ColorLike | None = None,
        background: ColorLike | None = None,
        modifiers: Sequence[CharacterModifier] | None = None,
        align: Alignment | None = None,
        border: Border | None = None,
        border_sides: Sequence[Side] | None = None,
        border_color: ColorLike | None = None,
        title: str | None = None,
        title_position: FrameTitlePosition | None = None,
        padding: PaddingLike | None = None,
        gap: int = 0,
        direction: Direction = "vertical",
    ) -> None:
        """Render and dispatch events until an exit is requested.

        Args:
            *renderables: Grids, components, content primitives, or plain
                values to paint.
            color: Foreground color applied to plain values.
            background: Background color for the rendered area.
            modifiers: Character modifiers applied to plain values.
            align: Horizontal alignment applied to plain values.
            border: Border style around the rendered area.
            border_sides: Border sides to draw.
            border_color: Border foreground color.
            title: Optional border title.
            title_position: Border edge that holds the title.
            padding: Space between the border and content.
            gap: Cells between multiple renderables.
            direction: Direction used to lay out multiple renderables.
        """
        runtime = self._ensure_runtime(live=True)
        if renderables:
            runtime.set_root(renderables[0] if len(renderables) == 1 else None)
        try:
            while True:
                runtime.render(
                    *renderables,
                    color=color,
                    background=background,
                    modifiers=modifiers,
                    align=align,
                    border=border,
                    border_sides=border_sides,
                    border_color=border_color,
                    title=title,
                    title_position=title_position,
                    padding=padding,
                    gap=gap,
                    direction=direction,
                )
                if not runtime.pump():
                    break
        finally:
            self.close()

    def request_exit(self) -> None:
        """Stop the active run loop."""
        if self._runtime is not None:
            self._runtime.request_exit()

    def focus(self, group: str) -> bool:
        """Focus a named field group."""
        return self.runtime.focus(group)

    focus_group = focus

    def blur(self) -> None:
        """Clear field focus."""
        self.runtime.blur()

    blur_field = blur

    def focus_next(self) -> bool:
        """Move focus forward."""
        return self.runtime.focus_next()

    def focus_previous(self) -> bool:
        """Move focus backward."""
        return self.runtime.focus_previous()

    def get_output(self) -> str:
        """Return the current cell buffer as plain text."""
        return self.runtime.get_output()

    def get_output_as_ansi(self) -> str:
        """Return the current cell buffer with ANSI styling."""
        return self.runtime.get_output_as_ansi()

    def copy_to_clipboard(self, text: str) -> bool:
        """Copy text when the active platform supports clipboard writes."""
        return self.runtime.device.copy_to_clipboard(text)

    def close(self) -> None:
        """Restore and release the owned runtime."""
        if self._runtime is not None:
            self._runtime.close()
            self._runtime = None


__all__ = ("Terminal",)
