"""
xnano.terminal._screen

Claiming the one screen of a program, the live runtime that draws on it, and moving a canvas
onto and off it.
"""

from __future__ import annotations

import os
import sys
import threading
import warnings
from collections.abc import Generator, Mapping, Sequence
from typing import TYPE_CHECKING, Final, cast

import xnano_core as _core
from xnano._runtime._host import _InlineHost, _ThreadHost
from xnano._schema._generics import DepsT, StateT
from xnano._schema._layout import EdgeBehavior
from xnano.canvas import (
    Canvas,
    _canvas_size,
    _check_size,
    _check_title,
    _is_whole_window,
    _plain_appearance,
    _size_in_cells,
)
from xnano.effects._properties import EffectParameters
from xnano.errors import TerminalAlreadyOpenError, TerminalError
from xnano.state import _prepare_state, _replaced_state, _state_field_types
from xnano.terminal._settings import gates_for_screen, parse_open_settings
from xnano_core import JSONValue

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

_screen_lock: Final = threading.Lock()

is_screen_claimed: bool = False
"""Whether a canvas is on the screen. Read it through this module, never copy it."""


def window_size() -> os.terminal_size:
    """
    The size of the terminal this program runs in, or 80 by 24 when it has none.

    The terminal itself is asked first, through standard output, input or error, so a
    ``COLUMNS`` or ``LINES`` variable left over in the environment does not change it.
    """
    for stream in (sys.__stdout__, sys.__stdin__, sys.__stderr__):
        try:
            size = os.get_terminal_size(stream.fileno())  # type: ignore[union-attr]
        except (AttributeError, OSError, ValueError):
            continue
        if size.columns > 0 and size.lines > 0:
            return size
    import shutil  # only reached when no standard stream is a terminal

    return shutil.get_terminal_size((80, 24))


def warn_if_output_is_not_held_back(*, requested: bool, is_held_back: bool) -> None:
    """Say so when ``capture`` could not be honored on this platform."""
    if requested and not is_held_back:
        warnings.warn(
            'This platform cannot hold back what a program prints while a canvas is on the '
            'screen, so a print or a log record can land in the middle of a frame and '
            'corrupt the screen. Log to a file instead, or pass capture=False to silence '
            'this warning.',
            RuntimeWarning,
            stacklevel=2,
        )


def claim_screen() -> None:
    """Take the one screen of the program, or say that another canvas has it."""
    global is_screen_claimed
    with _screen_lock:
        if is_screen_claimed:
            raise TerminalAlreadyOpenError(
                'A canvas is already on the screen, and a program has only one screen. Close '
                'it first, or draw into xnano.new() and show that instead.'
            )
        is_screen_claimed = True


def release_screen() -> None:
    """Give the one screen of the program back."""
    global is_screen_claimed
    with _screen_lock:
        is_screen_claimed = False


def create_live_runtime(
    *,
    fps: float,
    width: int | None,
    height: int | None,
    gates: Mapping[str, object],
    title: str | None,
    clock: _core.Clock,
) -> _core.Runtime:
    """Create the runtime that draws on the screen, with the input the terminal settings ask for."""
    mouse = gates['mouse']
    keyboard = gates['keyboard']
    uses_alternate_screen = bool(gates['alternate_screen']) and height is None
    options = _core.TerminalOptions(
        input=_core.InputOptions(
            mouse='buttons' if mouse is True else 'off' if mouse is False else 'motion',
            scroll=bool(gates['scroll']),
            bracketed_paste=bool(gates['paste']),
            focus_reporting=bool(gates['focus']),
            interrupt='stop' if gates['interrupt'] else 'event',
            keyboard='basic'
            if keyboard is True
            else 'off'
            if keyboard is False
            else 'disambiguated'
            if keyboard == 'disambiguated'
            else 'release_events',
        ),
        alternate_screen=uses_alternate_screen,
        should_capture_output=bool(gates['capture']),
        should_clear_on_close=bool(gates['clear']) and not uses_alternate_screen,
    )
    runtime = _core.Runtime.live(
        frame_interval_milliseconds=max(1, round(1000.0 / fps)),
        inline_height=height,
        inline_width=width,
        options=options,
        clock=clock,
    )
    if title is not None:
        runtime.title = title
    return runtime


def attach_screen(
    canvas: Canvas[DepsT, StateT],
    *,
    title: str | None,
    width: int | str | None,
    height: int | str | None,
    settings: Mapping[str, object],
) -> None:
    """Move the canvas onto a live runtime that draws on the screen."""
    steps = _attach_screen_steps(
        canvas, title=title, width=width, height=height, settings=settings
    )
    host = next(steps)
    try:
        host.wait_until_ready()
    except BaseException as error:
        steps.throw(error)
        raise
    next(steps, None)


async def attach_screen_async(
    canvas: Canvas[DepsT, StateT],
    *,
    title: str | None,
    width: int | str | None,
    height: int | str | None,
    settings: Mapping[str, object],
) -> None:
    """Move the canvas onto the screen, awaiting the terminal instead of blocking the loop."""
    steps = _attach_screen_steps(
        canvas, title=title, width=width, height=height, settings=settings
    )
    host = next(steps)
    try:
        await host.wait_until_ready_async()
    except BaseException as error:
        steps.throw(error)
        raise
    next(steps, None)


def _attach_screen_steps(
    canvas: Canvas[DepsT, StateT],
    *,
    title: str | None,
    width: int | str | None,
    height: int | str | None,
    settings: Mapping[str, object],
) -> Generator[_ThreadHost, None, None]:
    """
    The steps of putting a canvas on the screen, paused once while the terminal answers.

    The generator yields the new loop while its thread creates the live runtime; the caller
    waits for it (``wait_until_ready`` or ``wait_until_ready_async``) and resumes the
    generator, or throws the error that interrupted the waiting into it.
    """
    from xnano.terminal import Terminal

    canvas._require_open()
    _check_title(title)
    if canvas._is_live:
        raise TerminalError(
            'This canvas is already on the screen, and a program has one screen. Keep '
            'drawing on it, or create another canvas with xnano.new() to draw off the '
            'screen.',
            code='screen.already_open',
        )
    if canvas._canvas is not canvas:
        raise TerminalError(
            'This canvas was written into another canvas, so it draws inside that one. '
            'Open the outer canvas instead.',
            code='canvas.composition',
        )
    canvas._host.require_retirable()
    parsed = parse_open_settings(canvas, settings)
    checked_width = _check_size('width', width)
    checked_height = _check_size('height', height)
    if checked_width is None and checked_height is None:
        checked_width, checked_height = canvas._requested_width, canvas._requested_height
    fits_width = checked_width == 'fit'
    fits_height = checked_height == 'fit'
    if (fits_width or fits_height) and canvas._layout != 'overlay':
        raise ValueError(
            f'A {canvas._layout} canvas shares its size among the pieces written on it, so '
            f'it cannot take the size of them. Give it a size such as height=12 instead of '
            f"'fit'."
        )
    if (
        not fits_width
        and not fits_height
        and (_is_whole_window(checked_width) and _is_whole_window(checked_height))
    ):
        # Neither size, or '100%' for both: the whole window, following its size.
        width = height = None
    else:
        if checked_height is None:
            raise ValueError(
                'A canvas on the screen with a width needs a height too, because it draws '
                'in a region of that size. Add height=... (cells, a percentage such as '
                "'50%', or 'fit' for the height of the content), or remove width."
            )
        canvas._fits_width = fits_width
        canvas._fits_height = fits_height
        canvas._root.should_fit_width = fits_width
        canvas._root.should_fit_height = fits_height
        content = canvas.screen.size if fits_width or fits_height else None
        if fits_width:
            assert content is not None
            width = max(1, content.width)
        else:
            width = (
                None
                if _is_whole_window(checked_width)
                else _size_in_cells(checked_width, 'columns')
            )
        if fits_height:
            assert content is not None
            height = max(1, content.height)
        else:
            height = _size_in_cells(checked_height, 'lines')
    gates = {**canvas._gates, **cast('dict[str, object]', parsed['gates'])}
    resolved = gates_for_screen(canvas, gates)
    replacement: _core.TerminalStateStore | None = None
    replaced: _core.TerminalStateSnapshot | None = None
    if parsed.get('state') is not None:
        earlier = canvas._state_store
        replaced = None if earlier is None else earlier.snapshot()
        replacement = _prepare_state(
            cast('DataclassInstance', parsed['state']),
            None
            if earlier is None
            else cast('dict[str, JSONValue]', earlier.snapshot().to_value()),
        )
    claim_screen()
    old_host = canvas._host
    clock = canvas._time_source
    carried: dict[str, object] = {
        'elapsed_seconds': clock.elapsed_seconds,
        'frame': clock.frame,
        'is_stopped': clock.is_stopped,
    }
    fps = cast('float', parsed.get('fps', canvas._fps))
    window_title = canvas._title if title is None else title
    cursor = canvas._cursor
    if cursor is not None:
        carried['cursor'] = (
            cursor.position,
            cursor.shape,
            cursor.is_blinking,
            cursor.is_visible,
            canvas._cursor_follow,
        )

    def create_live() -> _core.Runtime:
        continued = _core.Clock.monotonic(
            elapsed_seconds=cast('float', carried['elapsed_seconds']),
            frame=cast('int', carried['frame']),
        )
        if carried['is_stopped']:
            continued.stop()
        return create_live_runtime(
            fps=fps,
            width=width,
            height=height,
            gates=resolved,
            title=window_title,
            clock=continued,
        )

    try:
        new_host = _ThreadHost(
            cast('Canvas[object, object]', canvas),
            create_live,
            defer_bind=True,
            should_wait=False,
        )
        try:
            yield new_host
        except BaseException:
            # The waiting was interrupted while the loop's thread may still be creating its
            # runtime, so that thread is stopped before the screen is given back.
            new_host.shutdown()
            raise
        new_host.raise_startup_error()
    except TerminalError:
        release_screen()
        raise
    except RuntimeError as error:
        release_screen()
        detail = str(error).split('. Run the program', 1)[0]
        raise TerminalError(
            f'The canvas could not be put on the screen: {detail}. Run the program in a '
            f'terminal, or draw into a canvas from xnano.new() and read it with '
            f'canvas.screen.render().',
            code='screen.unavailable',
        ) from error
    except BaseException:
        release_screen()
        raise
    try:
        old_host.call(canvas._unbind_runtime)
        old_host.retire()
    except BaseException:
        new_host.shutdown()
        release_screen()
        raise
    # The old runtime may only be dropped on the thread that created it, which is this
    # one for a canvas with a manual clock.
    canvas._forget_runtime()
    canvas._host = new_host
    object.__setattr__(canvas, '__class__', Terminal)
    canvas._is_realtime = True
    canvas._gates = gates
    canvas._resolved_gates = resolved
    canvas._carried = carried
    canvas._title = window_title
    canvas._fps = fps
    if 'bpm' in parsed:
        canvas._bpm = cast('float', parsed['bpm'])
    if 'edges' in parsed:
        canvas._edges = cast('EdgeBehavior', parsed['edges'])
    if 'deps' in parsed:
        canvas._deps = cast('DepsT', parsed['deps'])
        canvas._deps_given = True
    was_stopped = canvas._stop_requested.is_set()
    canvas._stop_requested.clear()
    try:
        if replacement is not None:
            if canvas._state_subscription is not None:
                canvas._state_subscription.cancel()
                canvas._state_subscription = replacement.subscribe(
                    [()], canvas._on_state_change
                )
            canvas._internal_revisions.clear()
            canvas._state_store = replacement
            canvas._state_fields = _state_field_types(
                cast('DataclassInstance', parsed['state'])
            )
            canvas._state_namespace = None
            canvas._state_given = True
        appearance = cast('dict[str, object]', parsed['appearance'])
        if appearance:
            look = canvas._ensure_look()
            for name, value in _plain_appearance(appearance).items():
                setattr(look, name, value)
        new_host.bind_now()
    except BaseException:
        restore_screenless(canvas, carried)
        if was_stopped:
            canvas._stop_requested.set()
        raise
    if replacement is not None and replaced is not None:
        change = _replaced_state(replaced, replacement)
        if change is not None:
            new_host.post(lambda: canvas._tell_followers(change))
    for effect in cast('Sequence[EffectParameters]', parsed.get('effects', ())):
        effect.apply_to(cast('Canvas[object, object]', canvas))


def restore_carried(
    canvas: Canvas[DepsT, StateT], runtime: _core.Runtime, carried: Mapping[str, object]
) -> None:
    """Give a new runtime the cursor and title the previous one had. Runs on its loop."""
    if canvas._title is not None:
        runtime.title = canvas._title
    cursor_state = carried.get('cursor')
    if cursor_state is None:
        return
    position, shape, is_blinking, is_visible, follow = cast(
        'tuple[_core.Point | None, _core.CursorShape | None, bool, bool, tuple[_core.Buffer, int, int] | None]',
        cursor_state,
    )
    cursor = runtime.cursor
    if follow is not None:
        buffer, column, row = follow
        cursor.follow(buffer, x=column, y=row)
    elif position is not None:
        cursor.position = position
    cursor.shape = shape
    cursor.is_blinking = is_blinking
    cursor.is_visible = is_visible


def restore_screenless(
    canvas: Canvas[DepsT, StateT], carried: Mapping[str, object]
) -> None:
    """After a failed attach, give the canvas a screenless runtime again."""
    failed_host = canvas._host
    object.__setattr__(canvas, '__class__', Canvas)
    canvas._is_realtime = False
    canvas._carried = dict(carried)
    elapsed = cast('float', carried['elapsed_seconds'])
    columns, rows = _canvas_size(
        canvas._requested_width, canvas._requested_height, canvas._enclosing_size
    )
    interval_milliseconds = max(1, round(1000.0 / canvas._fps))

    def create_runtime() -> _core.Runtime:
        clock = _core.Clock.manual(elapsed_seconds=elapsed)
        if carried['is_stopped']:
            clock.stop()
        return _core.Runtime.offscreen(
            width=columns,
            height=rows,
            frame_interval_milliseconds=interval_milliseconds,
            clock=clock,
        )

    try:
        failed_host.shutdown()
    finally:
        release_screen()
        _InlineHost(cast('Canvas[object, object]', canvas), create_runtime)
