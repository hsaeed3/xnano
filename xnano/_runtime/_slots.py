"""
xnano._runtime._slots

The slots of a canvas with a column or row layout, and the layout solved once before
the next frame.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

import xnano_core as _core

if TYPE_CHECKING:
    from xnano._schema._axes import Axis
    from xnano.canvas import Canvas
    from xnano.layout._placement import Placement

from xnano._internal._axes import size_share
from xnano._schema._generics import WrittenDepsT, WrittenStateT
from xnano.errors import TerminalError


def slot_rule(size: Axis | None, axis_name: str) -> _core.SizeRule:
    """The size of a slot on a stacking canvas: cells, a percentage, or a share of the rest."""
    if size is None:
        return _core.SizeRule.fill()
    if isinstance(size, int) and not isinstance(size, bool) and size >= 0:
        return _core.SizeRule.cells(size)
    if isinstance(size, str):
        share = size_share(size)
        if share is not None and 0.0 <= share <= 1.0:
            return _core.SizeRule.percent(round(share * 100))
    raise TerminalError(
        f'On a canvas with a column or row layout, the {axis_name} of what is written is the '
        f'size of its slot, so it must be a number of cells or a percentage, but got '
        f"{size!r}. Pass {axis_name}=3 or {axis_name}='50%', or leave it out to share the "
        f'space that is left.',
        code='validation.value',
        location=axis_name,
        input_value=size,
    )


def open_slot(
    canvas: Canvas[object, object],
    written_canvas: Canvas[WrittenDepsT, WrittenStateT] | None,
    width: Axis | None,
    height: Axis | None,
) -> tuple[_core.Buffer, Axis | None, Axis | None]:
    """
    Attach the next slot of a stacking canvas, sized from the written size on its axis.

    When no size was written, the written canvas's requested size on that axis is used.

    Args:
        canvas: The stacking canvas to attach the slot to.
        written_canvas: The canvas being written, whose requested size sizes the slot, or
            ``None`` when what is written is not a canvas.
        width: The width the content was written with.
        height: The height the content was written with.

    Returns:
        The slot, and the width and height to write the content with inside it: a size
        on the stacking axis becomes the slot's size, and the content fills the slot.
    """
    is_column = canvas._layout == 'column'
    size = height if is_column else width
    if size is None and written_canvas is not None:
        size = (
            written_canvas._requested_height
            if is_column
            else written_canvas._requested_width
        )
    rule = slot_rule(size, 'height' if is_column else 'width')
    if size is not None:
        if is_column:
            height = '100%'
        else:
            width = '100%'
    slot = _core.Buffer()
    mark_layout_pending(canvas)
    canvas._content.attach(slot, geometry='inherit', mode='transparent')
    with canvas._lock:
        canvas._slots.append((None, slot, rule))
    # The loop may have laid the canvas out between the mark and the attach.
    mark_layout_pending(canvas)
    return slot, width, height


def close_slot(canvas: Canvas[object, object], slot: _core.Buffer) -> None:
    """Detach a slot and give its space to the slots that are left."""
    with canvas._lock:
        canvas._slots[:] = [entry for entry in canvas._slots if entry[1] is not slot]
    mark_layout_pending(canvas)
    try:
        canvas._content.detach(slot)
    except ValueError:
        pass
    mark_layout_pending(canvas)


def slot_of(
    canvas: Canvas[object, object], placement: Placement[object, object]
) -> _core.Buffer | None:
    """The slot a placement written on this canvas stacks in, or ``None``."""
    with canvas._lock:
        for owner, slot, _ in canvas._slots:
            if owner is placement:
                return slot
    return None


def mark_layout_pending(canvas: Canvas[object, object]) -> None:
    """
    Split the canvas among its slots once, before the next frame.

    Solving a layout gets slow as slots are added, so writes and removals in a row are
    laid out together. Until then the slots overlap, which attaches and detaches cheaply.
    """
    root = canvas._canvas
    with root._lock:
        if canvas._is_layout_pending:
            return
        canvas._is_layout_pending = True
        root._pending_layouts[id(canvas)] = canvas
    canvas._content.update(_core.Layout('overlay'))
    root._demand_frames()
    if not root._is_closed:
        root._host.post(lambda: root._runtime.request_frame())


def apply_pending_layouts(root: Canvas[object, object]) -> None:
    """Lay out every canvas that was written to or removed from since the last frame."""
    with root._lock:
        pending = list(root._pending_layouts.values())
        root._pending_layouts.clear()
        for canvas in pending:
            canvas._is_layout_pending = False
    for canvas in pending:
        if not canvas._is_closed:
            apply_layout(canvas)
        root._release_frames()


def apply_layout(canvas: Canvas[object, object]) -> None:
    """Split the canvas among its slots, in the order they were written."""
    with canvas._lock:
        rules = [rule for _, _, rule in canvas._slots]
    canvas._content.update(
        _core.Layout(cast('Literal["row", "column"]', canvas._layout), sizes=rules)
    )
