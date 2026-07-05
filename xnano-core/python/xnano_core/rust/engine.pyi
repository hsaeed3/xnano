"""xnano_core.rust.engine

Type stubs for the stateful engine layer of ``xnano_core``.

This module owns the runtime primitives that sit **between** the raw ratatui
bindings in :mod:`xnano_core.rust.native` and the higher-level ``xnano``
framework. It exposes:

* :class:`CoreSession` — the singleton-per-app owner of the terminal, event
  loop, effects, tick clock, and device-state mirror. Only :class:`CoreSession`
  may call ``ratatui::init``/``ratatui::restore``.
* :class:`CoreRenderNode` — the scene-graph node type. Every node carries an
  optional absolute geometry, layout constraints for its children, a paint-order
  hint (``z``), a visibility flag (``visible``), and a :class:`CoreRenderContent`
  payload.
* :class:`CoreRenderContent` — a tagged content variant (empty, widget,
  stateful widget, or drawable callback) painted into a rect during traversal.
* :class:`CoreEvent`, :class:`CoreTickEvent`, :class:`CoreTerminalEventKind` —
  the unified input/tick event surface delivered by
  :meth:`CoreSession.poll_event` / :meth:`CoreSession.read_event`.
* :class:`CoreTerminalRef` — a scope-guarded escape hatch that hands the live
  ratatui ``DefaultTerminal`` to a Python callback for direct-draw use.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Optional

from xnano_core.rust.native import (
    Buffer,
    ClearType,
    CompletedFrame,
    Constraint,
    CursorStyle,
    Direction,
    Effect,
    KeyboardEnhancementFlags,
    KeyEvent,
    Margin,
    MouseEvent,
    Position,
    Rect,
    Size,
)


CoreDrawableCallback = Callable[[Buffer, Rect], None]
"""Signature for :meth:`CoreRenderContent.drawable` callbacks.

The callback receives a mutable :class:`~xnano_core.rust.native.Buffer` view
scoped to the node's rect plus the rect itself. The buffer view is valid only
for the duration of the callback; the engine invalidates it on return.

Any exception raised inside the callback is captured by the engine, propagated
back to the outer :meth:`CoreSession.render` call, and re-raised as a Python
exception without leaving the terminal in a broken state.
"""


class CoreTerminalEventKind:
    """Discriminator for :class:`CoreEvent`.

    Attributes:
        Key: The event carries a keyboard :class:`~xnano_core.rust.native.KeyEvent`.
        Resize: The terminal reports a new size. ``width`` and ``height`` on
            the event are populated.
        Paste: The terminal reports bracketed-paste content. ``paste`` on the
            event is populated.
        Mouse: The event carries a :class:`~xnano_core.rust.native.MouseEvent`.
        FocusGained: The terminal window received focus. No payload.
        FocusLost: The terminal window lost focus. No payload.
        Tick: The event was synthesized by the session tick clock. ``tick`` on
            the event is populated with a :class:`CoreTickEvent`.
    """

    Key: CoreTerminalEventKind
    Resize: CoreTerminalEventKind
    Paste: CoreTerminalEventKind
    Mouse: CoreTerminalEventKind
    FocusGained: CoreTerminalEventKind
    FocusLost: CoreTerminalEventKind
    Tick: CoreTerminalEventKind


class CoreTickEvent:
    """Synthetic clock tick emitted by :class:`CoreSession`.

    Ticks are only produced when the session was constructed with
    ``tick_rate_ms`` set. They are opt-in: a session with no configured tick
    interval never yields ``Tick`` events, so downstream consumers can rely on
    ``poll_event`` blocking purely on real input.

    Attributes:
        elapsed_ms: Milliseconds elapsed since the previous tick was emitted
            (or since :meth:`CoreSession.init` for the first tick).
    """

    elapsed_ms: int


class CoreEvent:
    """Unified event delivered by the session event loop.

    Exactly one of ``key``, ``paste``, ``mouse``, or ``tick`` is populated for
    each kind; on ``Resize`` events both ``width`` and ``height`` are set;
    ``FocusGained`` / ``FocusLost`` carry no payload. Consumers should
    dispatch on ``kind`` and read only the associated payload field.

    Attributes:
        kind: Which of the seven event kinds this event represents.
        key: Populated when ``kind == CoreTerminalEventKind.Key``.
        width: Populated when ``kind == CoreTerminalEventKind.Resize``.
        height: Populated when ``kind == CoreTerminalEventKind.Resize``.
        paste: Populated when ``kind == CoreTerminalEventKind.Paste``.
        mouse: Populated when ``kind == CoreTerminalEventKind.Mouse``.
        tick: Populated when ``kind == CoreTerminalEventKind.Tick``.
    """

    kind: CoreTerminalEventKind
    key: Optional[KeyEvent]
    width: Optional[int]
    height: Optional[int]
    paste: Optional[str]
    mouse: Optional[MouseEvent]
    tick: Optional[CoreTickEvent]


class CoreRenderContent:
    """Tagged payload that a :class:`CoreRenderNode` paints into its rect.

    Instances are opaque — construct via the four static constructors and
    inspect via the ``is_*`` predicates. Content values are cheaply cloneable
    (widget/state/callback references are ``Py<PyAny>`` handles, not deep
    copies).

    Attributes:
        __module__: Always ``"xnano_core.rust.engine"``.
    """

    @staticmethod
    def empty() -> CoreRenderContent:
        """Create a content variant that paints nothing.

        Empty content is the default when a node is used purely for layout or
        grouping — the engine skips the paint step entirely for these nodes.

        Returns:
            A ``CoreRenderContent`` whose :meth:`is_empty` returns ``True``.
        """
        ...

    @staticmethod
    def widget(widget: Any) -> CoreRenderContent:
        """Wrap a stateless widget for rendering.

        The engine will attempt, in order:

        1. If ``widget`` has a ``_to_core`` method, call it and use the result.
        2. Otherwise if ``widget`` has an ``_inner`` attribute, use that.
        3. Otherwise treat ``widget`` as one of the built-in native widget
           types (``Paragraph``, ``Block``, ``List``, ``Table``, ``Gauge``,
           ``Tabs``, ``Sparkline``, ``LineGauge``, ``BarChart``, ``Chart``,
           ``Canvas``, ``Clear``, ``Span``, ``Line``, ``Text``).
        4. Otherwise call ``widget.render(area)`` and recurse on the result.

        Args:
            widget: A native widget instance, a duck-typed object exposing
                ``_to_core`` or ``_inner``, or a callable Python object whose
                ``render(area)`` returns something in one of the above forms.

        Returns:
            A ``CoreRenderContent`` whose :meth:`is_empty` returns ``False``
            and whose :meth:`is_stateful` and :meth:`is_drawable` return
            ``False``.
        """
        ...

    @staticmethod
    def stateful(widget: Any, state: Any) -> CoreRenderContent:
        """Wrap a stateful widget together with its mutable state.

        Supports the three ratatui stateful widgets currently bridged:
        ``List``+``ListState``, ``Table``+``TableState``,
        ``Scrollbar``+``ScrollbarState``. Any other pairing raises
        ``TypeError`` at render time.

        Args:
            widget: A stateful native widget instance.
            state: The corresponding state instance. The engine borrows it
                mutably during render; do not mutate it from another thread
                during a render call.

        Returns:
            A ``CoreRenderContent`` whose :meth:`is_stateful` returns ``True``.
        """
        ...

    @staticmethod
    def drawable(callback: CoreDrawableCallback) -> CoreRenderContent:
        """Wrap a Python callback that draws directly into the buffer.

        The callback receives a scope-guarded mutable view onto the live
        buffer and the rect it should draw into. Use this for custom
        rendering that doesn't fit the built-in widget catalog.

        Args:
            callback: A callable ``(buffer, rect) -> None``. The buffer
                argument is a scope-guarded view (see
                :class:`~xnano_core.rust.native.BufferMutView`) that becomes
                invalid the instant the callback returns.

        Returns:
            A ``CoreRenderContent`` whose :meth:`is_drawable` returns ``True``.
        """
        ...

    def is_empty(self) -> bool:
        """Whether this content variant is :meth:`empty`.

        Returns:
            ``True`` if the variant is ``Empty``, ``False`` otherwise.
        """
        ...

    def is_stateful(self) -> bool:
        """Whether this content variant is :meth:`stateful`.

        Returns:
            ``True`` if the variant is ``Stateful``, ``False`` otherwise.
        """
        ...

    def is_drawable(self) -> bool:
        """Whether this content variant is :meth:`drawable`.

        Returns:
            ``True`` if the variant is ``Drawable``, ``False`` otherwise.
        """
        ...


class CoreRenderNode:
    """A single node in the render tree.

    Every node contributes to the frame in three ways:

    1. **Geometry**: either absolute (``x``/``y``/``width``/``height`` all set,
       which the tree walk treats as a stacking context anchor) or
       constraint-derived from the parent's ``direction``+``constraints``.
    2. **Paint**: a :class:`CoreRenderContent` painted into the resolved rect.
    3. **Children**: laid out under this node's direction/constraints/gap,
       optionally with a margin applied to the parent rect first.

    The engine walks children in **ascending z order** (stable sort). Nodes
    with matching ``z`` paint in declaration order — later siblings paint
    over earlier ones, exactly like the pre-``z`` behavior. Nodes with
    ``visible=False`` are skipped entirely: neither they nor their descendants
    are laid out, painted, or considered for cursor placement or effect-area
    tracking. A hidden subtree still occupies the layout slot the parent
    reserved for it (matching CSS ``visibility: hidden`` semantics rather
    than ``display: none``); if the framework needs true collapse it should
    omit the node from the tree entirely.

    ``z`` is **sibling-local**: it orders paint among children of the same
    parent only. To promote content above unrelated subtrees, place it under
    a shared absolute-geometry ancestor (see :meth:`stack`). This mirrors
    CSS stacking contexts and keeps ``z`` from fighting containment.

    Attributes:
        __module__: Always ``"xnano_core.rust.engine"``.
    """

    def __init__(
        self,
        *,
        x: Optional[int] = None,
        y: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        direction: Optional[Direction] = None,
        gap: int = 0,
        constraints: Optional[Sequence[Constraint]] = None,
        margin: Optional[Margin] = None,
        content: Optional[CoreRenderContent] = None,
        cursor_hint: Optional[tuple[int, int]] = None,
        effect_key: Optional[str] = None,
        z: int = 0,
        visible: bool = True,
        children: Optional[Sequence[CoreRenderNode]] = None,
    ) -> None:
        """Construct a render node.

        All arguments are keyword-only.

        Args:
            x: Absolute X of the node's top-left in cells. If all four of
                ``x``/``y``/``width``/``height`` are supplied the node has
                absolute geometry and is treated as a stacking-context anchor;
                otherwise the parent's layout allocates its rect.
            y: Absolute Y of the node's top-left in cells.
            width: Absolute width in cells.
            height: Absolute height in cells.
            direction: How this node's children should flow when laid out by
                constraint. ``None`` defaults to ``Direction.Vertical``.
            gap: Cells of spacing inserted between adjacent children by the
                layout solver. Ignored if all children have absolute geometry.
            constraints: Layout constraints applied to children in
                declaration order. Length should match ``len(children)``.
            margin: Inner margin applied to this node's rect before it is
                subdivided for children. Does not affect this node's own
                paint region.
            content: What this node paints into its own rect. Defaults to
                :meth:`CoreRenderContent.empty`.
            cursor_hint: If set, the terminal cursor is positioned at
                ``(rect.x + dx, rect.y + dy)`` after this subtree renders,
                subject to the cursor being visible. Later cursor hints
                encountered during traversal override earlier ones.
            effect_key: If set, the resolved rect for this node is recorded
                under this key so :meth:`CoreSession.effect_area_for` can
                look it up after the frame.
            z: Sibling-local paint order. Higher values paint later
                (on top). Defaults to ``0``. Sibling ties break in
                declaration order.
            visible: If ``False``, this node and its entire subtree are
                skipped during traversal — no layout, no paint, no cursor
                or effect-area contributions. The layout slot the parent
                reserved is still consumed by the (invisible) node.
                Defaults to ``True``.
            children: Child nodes. Each child's rect is derived from the
                parent's direction+constraints+gap unless the child itself
                has absolute geometry.
        """
        ...

    @staticmethod
    def leaf(content: CoreRenderContent) -> CoreRenderNode:
        """Construct a leaf node with no children and default styling.

        Args:
            content: The content painted into this node's rect.

        Returns:
            A node with ``z=0``, ``visible=True``, no children, no absolute
            geometry, and the given ``content``.
        """
        ...

    @staticmethod
    def row(
        children: Sequence[CoreRenderNode],
        *,
        constraints: Optional[Sequence[Constraint]] = None,
        gap: int = 0,
        margin: Optional[Margin] = None,
    ) -> CoreRenderNode:
        """Construct a horizontal container.

        Args:
            children: Child nodes laid out left-to-right.
            constraints: Layout constraints per child.
            gap: Cells of horizontal spacing between children.
            margin: Inner margin applied to the parent rect before children
                are laid out.

        Returns:
            A container node with ``direction=Direction.Horizontal``,
            ``z=0``, ``visible=True``.
        """
        ...

    @staticmethod
    def column(
        children: Sequence[CoreRenderNode],
        *,
        constraints: Optional[Sequence[Constraint]] = None,
        gap: int = 0,
        margin: Optional[Margin] = None,
    ) -> CoreRenderNode:
        """Construct a vertical container.

        Args:
            children: Child nodes laid out top-to-bottom.
            constraints: Layout constraints per child.
            gap: Cells of vertical spacing between children.
            margin: Inner margin applied to the parent rect before children
                are laid out.

        Returns:
            A container node with ``direction=Direction.Vertical``,
            ``z=0``, ``visible=True``.
        """
        ...

    @staticmethod
    def stack(
        x: int,
        y: int,
        width: int,
        height: int,
        children: Sequence[CoreRenderNode],
    ) -> CoreRenderNode:
        """Construct an absolute-geometry stacking context.

        Every child inherits this anchor's rect unless it has its own
        absolute geometry. Children paint in ascending ``z`` order, so
        modals, dropdowns, and overlays should live under a ``stack``
        parent to escape their surrounding container's clip.

        Args:
            x: Absolute X of the stack's top-left in cells.
            y: Absolute Y of the stack's top-left in cells.
            width: Absolute width in cells.
            height: Absolute height in cells.
            children: Child nodes that share the stack's rect.

        Returns:
            A node with all four geometry fields set, ``z=0``,
            ``visible=True``, and the given children.
        """
        ...

    def get_children(self) -> list[CoreRenderNode]:
        """Return a shallow copy of this node's children.

        The returned list may be freely mutated; the underlying node's
        children are not affected.

        Returns:
            A new list of the child nodes in declaration order.
        """
        ...

    def get_content(self) -> CoreRenderContent:
        """Return a clone of this node's content.

        Returns:
            The :class:`CoreRenderContent` variant carried by this node.
        """
        ...

    def get_effect_key(self) -> Optional[str]:
        """Return this node's effect-area key, if any.

        Returns:
            The string key registered via the ``effect_key`` constructor
            argument, or ``None`` if the node has no key.
        """
        ...

    def get_z(self) -> int:
        """Return this node's paint-order hint.

        Returns:
            The ``z`` value passed at construction time, or ``0`` if none
            was supplied.
        """
        ...

    def is_visible(self) -> bool:
        """Return this node's visibility flag.

        Returns:
            ``True`` if the node participates in rendering, ``False`` if
            the engine will skip its subtree entirely.
        """
        ...

    def has_absolute_geometry(self) -> bool:
        """Whether all four geometry fields are set.

        A node with absolute geometry ignores the parent-supplied rect and
        uses its own ``x``/``y``/``width``/``height`` instead.

        Returns:
            ``True`` if all of ``x``, ``y``, ``width``, and ``height`` are
            set, ``False`` otherwise.
        """
        ...


class CoreTerminalRef:
    """Scope-guarded handle to the live ratatui ``DefaultTerminal``.

    Yielded by :meth:`CoreSession.get_terminal`. The reference is valid only
    while the parent :class:`CoreSession` is alive and has not been restored.
    Calling any method after the parent session has been restored raises
    ``RuntimeError``.

    Attributes:
        __module__: Always ``"xnano_core.rust.engine"``.
    """

    def draw(self, callback: Callable[[Any], Any]) -> None:
        """Run a direct-draw callback against a fresh terminal frame.

        The callback receives a native ``Frame`` handle. Errors raised inside
        the callback are printed but not propagated (matching ratatui's
        ``Terminal::draw`` contract).

        Args:
            callback: A callable receiving a ``Frame``. Its return value is
                discarded.
        """
        ...

    def try_draw(self, callback: Callable[[Any], Any]) -> CompletedFrame:
        """Run a direct-draw callback and return frame metadata on success.

        Errors raised inside the callback are propagated as Python
        exceptions after the draw is aborted.

        Args:
            callback: A callable receiving a ``Frame``. Its return value is
                discarded.

        Returns:
            A :class:`~xnano_core.rust.native.CompletedFrame` describing the
            frame that was written.
        """
        ...

    def flush(self) -> None:
        """Flush pending output to the underlying terminal."""
        ...

    def clear(self) -> None:
        """Clear the terminal's back buffer."""
        ...

    def size(self) -> Size:
        """Return the current terminal size in cells.

        Returns:
            A :class:`~xnano_core.rust.native.Size`.
        """
        ...


class CoreSession:
    """Owner of the terminal, event loop, effects, and device state.

    A ``CoreSession`` is the singleton runtime handle for one live xnano
    application. It is the only type in ``xnano_core`` allowed to call
    ``ratatui::init`` / ``ratatui::restore`` — every other primitive is
    stateless or state-owning-but-scoped.

    A session can be constructed in one of two modes:

    * **Live** (:meth:`init`): claims the real terminal, installs a panic
      hook that restores the terminal on abnormal exit, and drives the
      full event loop.
    * **Offscreen** (:meth:`offscreen`): allocates an in-memory buffer of
      fixed size and skips all crossterm I/O. Used for tests, snapshot
      rendering, and running effects without a terminal.

    Sessions are context managers: ``with CoreSession.init() as session:``
    guarantees the terminal is restored on both normal exit and exception
    propagation. Dropping the session without calling ``restore`` /
    ``__exit__`` also restores the terminal via a ``Drop`` implementation,
    but relying on that is discouraged.

    Attributes:
        __module__: Always ``"xnano_core.rust.engine"``.
    """

    @staticmethod
    def init(*, tick_rate_ms: Optional[int] = None) -> CoreSession:
        """Claim the terminal and construct a live session.

        Installs a panic hook that restores the terminal on abnormal exit.
        Enters the alternate screen and enables raw mode.

        Args:
            tick_rate_ms: If set, the session's event loop emits
                :class:`CoreTerminalEventKind.Tick` events at this cadence.
                If ``None`` or ``0``, ticks are disabled and
                :meth:`poll_event` / :meth:`read_event` never yield ``Tick``.

        Returns:
            A live ``CoreSession``.
        """
        ...

    @staticmethod
    def offscreen(width: int, height: int) -> CoreSession:
        """Construct an offscreen session backed by an in-memory buffer.

        No terminal is claimed. No panic hook is installed. No crossterm
        I/O is performed. :meth:`poll_event` and :meth:`read_event` are
        still callable but will never yield real terminal events; use the
        offscreen mode only for tests and snapshot rendering.

        Args:
            width: Buffer width in cells.
            height: Buffer height in cells.

        Returns:
            An offscreen ``CoreSession``.
        """
        ...

    def render(self, node: CoreRenderNode) -> None:
        """Render one frame from a render tree.

        Walks ``node``, laying out children under each node's direction and
        constraints, painting content in ascending ``z`` order per sibling
        group, skipping subtrees with ``visible=False``, running any
        registered effects over the resulting buffer, and finally
        positioning the cursor (or hiding it) according to the last-seen
        cursor hint.

        On a live session this writes to the real terminal via
        ``Terminal::draw``. On an offscreen session it writes to the
        internal buffer, which can be read back via
        :meth:`buffer_snapshot`.

        Args:
            node: The root of the render tree for this frame.
        """
        ...

    def poll_event(self, timeout_ms: int = 16) -> Optional[CoreEvent]:
        """Wait up to ``timeout_ms`` for the next event, then return.

        Blocks releasing the GIL so Python threads run during the wait.
        Checks Python signals on wake so ``Ctrl+C`` interrupts cleanly.

        Args:
            timeout_ms: Maximum milliseconds to block. Capped internally by
                the session's tick budget when ticks are enabled.

        Returns:
            The next :class:`CoreEvent`, or ``None`` if the poll timed out
            with no event and no tick was due.
        """
        ...

    def read_event(self) -> CoreEvent:
        """Block until the next event arrives.

        Equivalent to calling :meth:`poll_event` in a loop with a large
        timeout. Releases the GIL while blocking and checks signals on
        each iteration so ``Ctrl+C`` interrupts cleanly.

        Returns:
            The next :class:`CoreEvent`.
        """
        ...

    def buffer_snapshot(self) -> Buffer:
        """Clone the current frame buffer.

        Works in both live and offscreen modes. On a live session this
        clones the terminal's current frame buffer; on an offscreen
        session it clones the internal buffer.

        Returns:
            A fresh :class:`~xnano_core.rust.native.Buffer`.
        """
        ...

    def add_effect(self, effect: Effect) -> None:
        """Register a non-keyed effect on the session's effect manager.

        The effect runs on every subsequent :meth:`render` until it
        finishes on its own timeline.

        Args:
            effect: A :class:`~xnano_core.rust.native.Effect` to run.
        """
        ...

    def add_unique_effect(self, key: str, effect: Effect) -> None:
        """Register or replace a keyed effect.

        Any prior effect with the same key is cancelled first, so a hot
        path can call this every frame without piling up duplicates.

        Args:
            key: Identifier for this effect. Also usable with
                :meth:`effect_area_for` when a render node ties its
                ``effect_key`` to the same string.
            effect: A :class:`~xnano_core.rust.native.Effect` to run.
        """
        ...

    def cancel_effect(self, key: str) -> None:
        """Cancel a previously added keyed effect.

        No-op if the key is not registered.

        Args:
            key: The identifier passed to :meth:`add_unique_effect`.
        """
        ...

    def is_animating(self) -> bool:
        """Whether at least one effect is still running.

        Returns:
            ``True`` if any registered effect is unfinished, ``False``
            otherwise.
        """
        ...

    def effect_area_for(self, key: str) -> Optional[Rect]:
        """Look up the last-frame rect for a render node's ``effect_key``.

        A node's ``effect_key`` is recorded during traversal even for nodes
        that don't have absolute geometry, so effects can target a rect
        that was resolved by the layout solver.

        Args:
            key: The string set on a :class:`CoreRenderNode`'s
                ``effect_key``.

        Returns:
            The rect recorded on the most recent frame, or ``None`` if
            no node with that key rendered.
        """
        ...

    def get_terminal(self) -> CoreTerminalRef:
        """Yield a scope-guarded reference to the live terminal.

        Returns:
            A :class:`CoreTerminalRef` valid while this session is alive.

        Raises:
            RuntimeError: If this is an offscreen session.
        """
        ...

    def enable_raw_mode(self) -> None:
        """Enable crossterm raw mode."""
        ...

    def disable_raw_mode(self) -> None:
        """Disable crossterm raw mode."""
        ...

    def enable_mouse_capture(self) -> None:
        """Enable mouse event capture."""
        ...

    def disable_mouse_capture(self) -> None:
        """Disable mouse event capture."""
        ...

    def enable_bracketed_paste(self) -> None:
        """Enable bracketed-paste event delivery."""
        ...

    def disable_bracketed_paste(self) -> None:
        """Disable bracketed-paste event delivery."""
        ...

    def enable_focus_change(self) -> None:
        """Enable focus-gained/focus-lost event delivery."""
        ...

    def disable_focus_change(self) -> None:
        """Disable focus-gained/focus-lost event delivery."""
        ...

    def enter_alternate_screen(self) -> None:
        """Switch the terminal to its alternate screen buffer."""
        ...

    def leave_alternate_screen(self) -> None:
        """Return the terminal to its primary screen buffer."""
        ...

    def push_keyboard_enhancement_flags(
        self, flags: KeyboardEnhancementFlags
    ) -> None:
        """Push kitty-protocol keyboard enhancement flags on the stack.

        Args:
            flags: Enhancement flags to enable while pushed.
        """
        ...

    def pop_keyboard_enhancement_flags(self) -> None:
        """Pop the most recent keyboard enhancement flag frame."""
        ...

    def show_cursor(self) -> None:
        """Show the terminal cursor."""
        ...

    def hide_cursor(self) -> None:
        """Hide the terminal cursor."""
        ...

    def set_cursor_style(self, style: CursorStyle) -> None:
        """Set the terminal cursor shape.

        Args:
            style: The cursor shape to apply.
        """
        ...

    def get_cursor_style(self) -> CursorStyle:
        """Return the currently applied cursor style.

        Returns:
            The last :class:`~xnano_core.rust.native.CursorStyle` set via
            :meth:`set_cursor_style`, or the default shape if none was set.
        """
        ...

    def move_cursor_to(self, x: int, y: int) -> None:
        """Move the terminal cursor to absolute coordinates.

        Args:
            x: Column, in cells.
            y: Row, in cells.
        """
        ...

    def save_cursor_position(self) -> None:
        """Save the cursor position on the terminal's cursor stack."""
        ...

    def restore_cursor_position(self) -> None:
        """Restore the previously saved cursor position."""
        ...

    def get_cursor_position(self) -> Position:
        """Return the current cursor position.

        Returns:
            A :class:`~xnano_core.rust.native.Position`.
        """
        ...

    def get_size(self) -> Size:
        """Return the terminal's cell size.

        Returns:
            A :class:`~xnano_core.rust.native.Size`.
        """
        ...

    def get_window_size(self) -> Size:
        """Return the terminal's pixel window size.

        Returns:
            A :class:`~xnano_core.rust.native.Size` giving the terminal
            window in pixels, not cells.
        """
        ...

    def get_last_frame_area(self) -> Optional[Rect]:
        """Return the rect of the most recently rendered frame.

        Returns:
            The :class:`~xnano_core.rust.native.Rect` used on the last
            :meth:`render` call, or ``None`` if no frame has rendered yet.
        """
        ...

    def is_raw_mode_enabled(self) -> bool:
        """Return the session's mirror of raw-mode state.

        Returns:
            ``True`` if raw mode is enabled.
        """
        ...

    def is_mouse_capture_enabled(self) -> bool:
        """Return the session's mirror of mouse-capture state.

        Returns:
            ``True`` if mouse capture is enabled.
        """
        ...

    def is_bracketed_paste_enabled(self) -> bool:
        """Return the session's mirror of bracketed-paste state.

        Returns:
            ``True`` if bracketed paste is enabled.
        """
        ...

    def is_focus_change_enabled(self) -> bool:
        """Return the session's mirror of focus-change state.

        Returns:
            ``True`` if focus-change events are enabled.
        """
        ...

    def is_alternate_screen_enabled(self) -> bool:
        """Return the session's mirror of alternate-screen state.

        Returns:
            ``True`` if the alternate screen is active.
        """
        ...

    def is_cursor_visible(self) -> bool:
        """Return the session's mirror of cursor visibility.

        Returns:
            ``True`` if the cursor is currently shown.
        """
        ...

    def clear(self, clear_type: ClearType) -> None:
        """Clear part or all of the terminal.

        Args:
            clear_type: What portion of the terminal to clear.
        """
        ...

    def set_title(self, title: str) -> None:
        """Set the terminal window title.

        Args:
            title: The title to apply.
        """
        ...

    def get_title(self) -> Optional[str]:
        """Return the last title set via :meth:`set_title`.

        Returns:
            The title string, or ``None`` if none was set.
        """
        ...

    def scroll_up(self, count: int = 1) -> None:
        """Scroll the terminal viewport up.

        Args:
            count: Number of rows to scroll.
        """
        ...

    def scroll_down(self, count: int = 1) -> None:
        """Scroll the terminal viewport down.

        Args:
            count: Number of rows to scroll.
        """
        ...

    def begin_synchronized_update(self) -> None:
        """Begin a terminal synchronized-output region."""
        ...

    def end_synchronized_update(self) -> None:
        """End a terminal synchronized-output region."""
        ...

    def restore(self) -> None:
        """Restore the terminal and release engine resources.

        Idempotent: safe to call multiple times. Called automatically by
        :meth:`__exit__` and by the ``Drop`` implementation on the
        underlying Rust type.
        """
        ...

    def __enter__(self) -> CoreSession:
        """Context-manager entry.

        Returns:
            This session.
        """
        ...

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> bool:
        """Context-manager exit; always calls :meth:`restore`.

        Args:
            exc_type: The exception type, if propagating.
            exc_value: The exception instance, if propagating.
            traceback: The exception traceback, if propagating.

        Returns:
            ``False`` so any in-flight exception continues to propagate.
        """
        ...


__all__ = (
    "CoreSession",
    "CoreRenderNode",
    "CoreRenderContent",
    "CoreEvent",
    "CoreTickEvent",
    "CoreTerminalEventKind",
    "CoreTerminalRef",
)