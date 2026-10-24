"""
xnano._runtime._flow

Positions that flow: where a write whose ``x`` or ``y`` is ``'next'`` goes, and how it keeps
following what was written before it.

Every placement written into a container (a canvas, a slot of a stacking canvas or a placement)
joins that container's flow: the placements in the order they were written.

* ``y='next'`` starts a line of the flow on the first row below the lines written before it,
  at column ``0`` when ``x`` is ``'next'`` too. A placement given a ``y`` of its own (a status
  line at ``y='bottom'``) stays out of the lines, so the lines never move below it.
* ``x='next'`` with a ``y`` that was given continues on that row, right after the placement
  written just before, when that placement is on the row and there is room after it, and
  starts at column ``0`` otherwise. A placement that continues a line of the flow this way
  is part of that line, so the next line starts below the tallest part of it.

Only the placements that take part (the lines, what continues a row, and the placement each
continuation follows) are looked at when the flow settles, in the order they were written, so
one pass moves every line to where it belongs. The flow remembers where the lines stood after
each participant, so a placement written at the end is placed on its own, and a participant
that changes position or size from Python moves only itself and what was written after it. The
whole flow settles when the canvas is resized, and in the canvas's frame pass while that runs
for something else (an image that follows the canvas's size changes size there without Python).
A canvas whose content stands still makes no call before its frames for the flow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, TypeAlias

import xnano_core as _core

if TYPE_CHECKING:
    from xnano.canvas import Canvas
    from xnano.layout._placement import Placement

__all__ = ['FLOW_POSITION', 'Flow', 'flow_of', 'is_flow_position']

FLOW_POSITION: Final = 'next'
"""The position word that places something after what was written before it."""


_LineState: TypeAlias = 'tuple[int, frozenset[int]]'
"""Where the lines of a flow stand after a participant: the first row below them, and the
placements (by ``id``) that make up the last line."""

_NO_LINES: Final[_LineState] = (0, frozenset())


def is_flow_position(value: object) -> bool:
    """Whether an ``x`` or ``y`` value asks to follow the flow (``'next'``, or left out)."""
    return value is None or (isinstance(value, str) and value == FLOW_POSITION)


class Flow:
    """
    The placements written into one container, in the order they were written.

    Attributes:
        canvas: The root canvas the container is on.
        container: The buffer the placements are attached to.
        first: The first placement written that is still there.
        last: The last placement written that is still there.
        participants: The placements that follow, and those written just before one, in
            the order they were written.
        link_count: How many placements follow one written before them.
    """

    __slots__ = (
        '_has_line',
        '_is_dissolved',
        '_is_settling',
        '_states',
        'canvas',
        'container',
        'first',
        'last',
        'link_count',
        'participants',
    )

    def __init__(self, canvas: Canvas[object, object], container: _core.Buffer) -> None:
        """
        Start an empty flow. Use [`flow_of`][xnano._runtime._flow.flow_of] instead.

        Args:
            canvas: The root canvas the container is on.
            container: The buffer the placements of the flow are attached to.
        """
        self.canvas = canvas
        self.container = container
        self.first: Placement[object, object] | None = None
        self.last: Placement[object, object] | None = None
        self.participants: list[Placement[object, object]] = []
        self.link_count = 0
        self._has_line = False
        self._is_dissolved = False
        self._is_settling = False
        # The line state after each of the first participants, as the last settle left them.
        self._states: list[_LineState] = []

    # -- membership ----------------------------------------------------------------------

    def add(
        self, placement: Placement[object, object], *, follows_x: bool, follows_y: bool
    ) -> None:
        """Append a placement that was just written, following the flow on the axes given."""
        with self.canvas._lock:
            previous = self.last
            # Set only what differs from the class defaults a new placement reads.
            placement._flow = self
            if placement._flow_previous is not previous:
                placement._flow_previous = previous
            if placement._flow_next is not None:
                placement._flow_next = None
            if placement._follows_x is not follows_x:
                placement._follows_x = follows_x
            if placement._follows_y is not follows_y:
                placement._follows_y = follows_y
            if previous is None:
                self.first = placement
            else:
                previous._flow_next = placement
            self.last = placement
            if not (follows_x or follows_y):
                # It stays where it was put: the flow only remembers it was written here.
                return
            if follows_x and not follows_y and previous is not None:
                self._take_part(previous)
            self._take_part(placement)
            self._count_link(placement)
        # Everything before it is where it belongs, so only the new participants move.
        self._settle_from(len(self._states))

    def dissolve(self) -> None:
        """
        End the flow because everything in it is removed at once, so nothing in it moves.

        A canvas that closes, or a placement removed with what was written into it, dissolves
        the flow first: removing the placements one by one would move every line after each.
        """
        canvas = self.canvas
        with canvas._lock:
            self._is_dissolved = True
            self.participants.clear()
            self._states.clear()
            if canvas._flows.get(id(self.container)) is self:
                del canvas._flows[id(self.container)]

    def remove(self, placement: Placement[object, object]) -> None:
        """Take a placement out of the flow; what followed it follows what came before it."""
        canvas = self.canvas
        with canvas._lock:
            if placement._flow is not self or self._is_dissolved:
                return
            previous = placement._flow_previous
            following = placement._flow_next
            if previous is None:
                self.first = following
            else:
                previous._flow_next = following
            if following is None:
                self.last = previous
            else:
                following._flow_previous = previous
            placement._flow = None
            if previous is not None:
                placement._flow_previous = None
            if following is not None:
                placement._flow_next = None
            if placement._is_flow_participant:
                placement._is_flow_participant = False
                participants = self.participants
                # The placement written last is the one most often removed.
                if participants[-1] is placement:
                    index = len(participants) - 1
                    participants.pop()
                else:
                    index = participants.index(placement)
                    del participants[index]
                self._forget_states_from(index)
            if previous is not None:
                if following is not None and _continues_row(following):
                    self._take_part(previous, before=following)
                else:
                    self._release_if_unneeded(previous)
            self._count_links()
            is_empty = self.first is None
            if is_empty:
                canvas._flows.pop(id(self.container), None)
        if not is_empty:
            # Only what was written after the removed placement can have moved.
            self._settle_from(len(self._states))

    def follow(
        self, placement: Placement[object, object], axis: str, *, is_following: bool
    ) -> None:
        """Start or stop following the flow on one axis of a placement already in it."""
        with self.canvas._lock:
            if axis == 'x':
                placement._follows_x = is_following
            else:
                placement._follows_y = is_following
            previous = placement._flow_previous
            if _follows(placement):
                self._take_part(placement)
            else:
                self._release_if_unneeded(placement)
            if previous is not None:
                if _continues_row(placement):
                    self._take_part(previous, before=placement)
                else:
                    self._release_if_unneeded(previous)
            self._count_links()
            # Following or not changes where the lines stand from the placement on.
            self._states.clear()
        self.settle()

    def _take_part(
        self,
        placement: Placement[object, object],
        *,
        before: Placement[object, object] | None = None,
    ) -> None:
        """Make a placement one of the participants, keeping them in the order written."""
        if placement._is_flow_participant:
            return
        placement._is_flow_participant = True
        participants = self.participants
        if before is not None and before._is_flow_participant:
            index = participants.index(before)
            self._forget_states_from(index)
            participants.insert(index, placement)
            return
        following = placement._flow_next
        while following is not None and not following._is_flow_participant:
            following = following._flow_next
        if following is None:
            participants.append(placement)
        else:
            index = participants.index(following)
            self._forget_states_from(index)
            participants.insert(index, placement)

    def _release_if_unneeded(self, placement: Placement[object, object]) -> None:
        """Stop looking at a placement that neither follows nor is followed any more."""
        following = placement._flow_next
        if (
            placement._is_flow_participant
            and not _follows(placement)
            and not (following is not None and _continues_row(following))
        ):
            placement._is_flow_participant = False
            index = self.participants.index(placement)
            self._forget_states_from(index)
            del self.participants[index]

    def _forget_states_from(self, index: int) -> None:
        """Forget the line states from a participant on, after the participants changed there."""
        del self._states[index:]

    def _count_links(self) -> None:
        """Count the lines after the first, and the continuations that follow something."""
        self.link_count = 0
        self._has_line = False
        for placement in self.participants:
            self._count_link(placement)

    def _count_link(self, placement: Placement[object, object]) -> None:
        """Count a participant appended at the end into ``link_count``."""
        if placement._follows_y:
            self.link_count += self._has_line
            self._has_line = True
        elif placement._follows_x and placement._flow_previous is not None:
            self.link_count += 1

    # -- settling ------------------------------------------------------------------------

    def settle(self) -> None:
        """
        Move every placement that follows the flow to where the flow puts it now.

        The participants are looked at in the order they were written, so every line before a
        placement is already in place when the placement is worked out, and one pass settles
        the whole flow. A call made while the flow settles (by a move it makes) does nothing.
        """
        self._settle_from(0)

    def changed(self, placement: Placement[object, object]) -> None:
        """Move what follows a participant that moved or changed size, and the participant."""
        if self._is_settling:
            return
        with self.canvas._lock:
            participants = self.participants
            if participants and participants[-1] is placement:
                index = len(participants) - 1
            else:
                try:
                    index = participants.index(placement)
                except ValueError:
                    return
        self._settle_from(index)

    def _settle_from(self, start: int) -> None:
        """Settle the participants from ``start`` on, from the line state before it."""
        if self._is_settling or self._is_dissolved:
            return
        self._is_settling = True
        try:
            with self.canvas._lock:
                states = self._states
                start = min(start, len(states))
                participants = self.participants[start:]
                del states[start:]
            if not participants:
                return
            state = states[start - 1] if start else _NO_LINES
            container_width = self.container.width
            for placement in participants:
                state = _place(placement, state, container_width)
                states.append(state)
        finally:
            self._is_settling = False


def _place(
    placement: Placement[object, object], state: _LineState, container_width: int
) -> _LineState:
    """Move one participant to where the flow puts it after ``state``; return the state after."""
    if placement._removed:
        return state
    line_bottom, line_parts = state
    buffer = placement._buffer
    if placement._follows_y:
        if buffer.y != line_bottom:
            placement._assign_within_limits('y', line_bottom)
        if placement._follows_x and buffer.x != 0:
            placement._assign_within_limits('x', 0)
        return (buffer.y + buffer.height, frozenset((id(placement),)))
    if not placement._follows_x:
        return state
    previous = placement._flow_previous
    column = 0
    if previous is not None and not previous._removed:
        before = previous._buffer
        after = before.x + before.width
        if before.y == buffer.y and after + buffer.width <= container_width:
            column = after
    if buffer.x != column:
        placement._assign_within_limits('x', column)
    if column and previous is not None and id(previous) in line_parts:
        # It continues the last line, which now ends below it too.
        return (max(line_bottom, buffer.y + buffer.height), line_parts | {id(placement)})
    return state


def _follows(placement: Placement[object, object]) -> bool:
    """Whether a placement follows the flow on either axis."""
    return placement._follows_x or placement._follows_y


def _continues_row(placement: Placement[object, object]) -> bool:
    """Whether a placement continues a row after the placement written before it."""
    return placement._follows_x and not placement._follows_y


def flow_of(canvas: Canvas[object, object], container: _core.Buffer) -> Flow:
    """The flow of a container on a canvas, started when the first placement joins it."""
    root = canvas._canvas
    key = id(container)
    flow = root._flows.get(key)
    if flow is not None:
        return flow
    with root._lock:
        flow = root._flows.get(key)
        if flow is None:
            flow = Flow(root, container)
            root._flows[key] = flow
    return flow
