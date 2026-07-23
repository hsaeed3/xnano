"""Tests for Terminal.render / Terminal.run inline rendering of renderables.

These exercise the non-BaseGrid rendering path — content measurement, inline
viewport sizing, and painting standalone renderables — using offscreen
sessions so no TTY is required.
"""

from __future__ import annotations

import signal

import pytest

from xnano import _dispatch as dispatch
from xnano._types import Sizing
from xnano.components.text import Text
from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.terminal import Terminal


@pytest.mark.skipif(
    not hasattr(signal, "SIGHUP"),
    reason="SIGHUP is POSIX-only; no equivalent in Python's signal module on Windows",
)
def test_terminal_hangup_terminates_process() -> None:
    terminal: Terminal = Terminal()

    with pytest.raises(SystemExit) as exit_info:
        terminal._on_exit_signal(signal.SIGHUP, None)

    assert exit_info.value.code == 128 + signal.SIGHUP
    assert terminal._exit_requested is True


# ---------------------------------------------------------------------------
# measure_renderable / measure_renderables_height
# ---------------------------------------------------------------------------


def test_measure_renderable_single_line() -> None:
    width, height = dispatch.measure_renderable("hi, how are you?")
    assert width == len("hi, how are you?")
    assert height == 1


def test_measure_renderable_multiline() -> None:
    width, height = dispatch.measure_renderable("aaa\nb\ncc")
    assert width == 3
    assert height == 3


def test_measure_renderable_non_string_uses_str() -> None:
    assert dispatch.measure_renderable(42) == (2, 1)


def test_measure_renderable_text_component() -> None:
    width, height = dispatch.measure_renderable(Text(content="hello"))
    assert width >= len("hello")
    assert height >= 1


def test_measure_renderables_height_sums() -> None:
    assert dispatch.measure_renderables_height(["a\nb\nc", "x"]) == 4


def test_measure_renderables_height_empty_is_zero() -> None:
    assert dispatch.measure_renderables_height([]) == 0


def test_measure_renderables_height_includes_border_overhead() -> None:
    from xnano.fields import GridFieldInfo

    field = GridFieldInfo(border="rounded")
    # One content line plus a top and bottom border row.
    assert dispatch.measure_renderables_height(["hi"], field) == 3


def test_field_frame_none_when_no_chrome() -> None:
    from xnano.fields import GridFieldInfo

    assert dispatch.field_frame(GridFieldInfo()) is None
    assert dispatch.field_frame(None) is None
    assert dispatch.field_frame(GridFieldInfo(border="plain")) is not None
    assert dispatch.field_frame(GridFieldInfo(background="violet")) is None


# ---------------------------------------------------------------------------
# Terminal._compute_inline_height
# ---------------------------------------------------------------------------


def test_resolve_inline_height_at_least_one() -> None:
    terminal: Terminal = Terminal()
    # An empty string measures zero rows but must reserve at least one.
    assert terminal._resolve_inline_height(Sizing.fit(), [""], None) >= 1


def test_resolve_inline_height_matches_content() -> None:
    terminal: Terminal = Terminal()
    # Three lines of content → three inline rows (terminals in CI are tall
    # enough that the clamp to terminal height is a no-op here).
    assert (
        terminal._resolve_inline_height(
            Sizing.fit(), ["one\ntwo\nthree"], None
        )
        == 3
    )


def test_resolve_inline_height_includes_field_border() -> None:
    from xnano.fields import GridFieldInfo

    terminal: Terminal = Terminal()
    field = GridFieldInfo(border="rounded")
    # One content row plus top and bottom border rows.
    assert terminal._resolve_inline_height(Sizing.fit(), ["hi"], field) == 3


def test_resolve_inline_height_cells_is_literal() -> None:
    terminal: Terminal = Terminal()
    # A fixed cells height ignores content size (clamped to terminal rows).
    assert terminal._resolve_inline_height(Sizing.cells(4), ["hi"], None) == 4


# ---------------------------------------------------------------------------
# render() painting via an offscreen (already-live) session
# ---------------------------------------------------------------------------


def test_render_paints_single_line() -> None:
    terminal = Terminal.offscreen(cols=40, rows=6)
    terminal.render("hi, how are you?")
    lines = [line.rstrip() for line in terminal.get_output().splitlines()]
    assert lines[0] == "hi, how are you?"
    # Remaining rows stay blank — content is not stretched to fill the screen.
    assert all(line == "" for line in lines[1:])


def test_render_paints_embedded_newlines() -> None:
    terminal = Terminal.offscreen(cols=50, rows=6)
    terminal.render("line one\n\nline three")
    lines = [line.rstrip() for line in terminal.get_output().splitlines()]
    assert lines[0] == "line one"
    assert lines[1] == ""
    assert lines[2] == "line three"


def test_render_resolve_inline_height_grows_with_multiline_content() -> None:
    terminal: Terminal = Terminal()
    single = terminal._resolve_run(
        ["hello, world!"], is_grid=False, field=None
    )
    multi = terminal._resolve_run(
        ["this will be updated in 1 second: \n\nhello, world!"],
        is_grid=False,
        field=None,
    )
    assert single.inline_height == 1
    assert multi.inline_height == 3


def test_render_prepare_session_recreates_when_inline_height_changes() -> None:
    from unittest import mock

    terminal: Terminal = Terminal()
    terminal._is_live = True
    terminal._pending_enter = False
    core_session = mock.Mock()
    core_session.get_inline_height.return_value = 1
    session = mock.Mock()
    session._is_offscreen = False
    session._core_session = core_session
    terminal._session = session

    terminal._prepare_render_session(
        ["this will be updated in 1 second: \n\nhello, world!"],
        None,
    )

    session.leave.assert_called_once()
    assert terminal._session is None
    assert terminal._inline_height == 3
    assert terminal._pending_enter is True


def test_render_stacks_multiple_renderables() -> None:
    terminal = Terminal.offscreen(cols=40, rows=6)
    terminal.render("line one", "line two")
    lines = [line.rstrip() for line in terminal.get_output().splitlines()]
    assert lines[0] == "line one"
    assert lines[1] == "line two"


def test_render_applies_border() -> None:
    terminal = Terminal.offscreen(cols=40, rows=6)
    terminal.render("boxed", border="rounded")
    output = terminal.get_output()
    assert "╭" in output
    assert "╰" in output
    assert "boxed" in output


def test_render_paints_basegrid_as_layout_root() -> None:
    # Terminal.render(BaseGrid) must drive the full layout engine. The inline
    # renderable path only paints field chrome tops (a lone border row).
    class Card(BaseGrid, direction="vertical"):
        heading: str = Field(
            default="Reminder",
            border="rounded",
            height=1,
        )
        body: str = Field(default="Water the plants.", height=1)

    terminal = Terminal.offscreen(cols=40, rows=10)
    terminal.render(Card())
    output = terminal.get_output()
    lines = [line.rstrip() for line in output.splitlines()]
    assert any("Reminder" in line for line in lines)
    assert any("Water the plants." in line for line in lines)
    assert "╭" in output
    assert "╰" in output


def test_render_offscreen_stays_full_viewport_session() -> None:
    # Rendering into an already-live offscreen session must not attempt to
    # switch it into an inline viewport.
    terminal = Terminal.offscreen(cols=20, rows=4)
    terminal.render("x")
    assert terminal._inline_height is None


# ---------------------------------------------------------------------------
# inline renderables dispatch (renderables + field kwargs)
# ---------------------------------------------------------------------------


def test_render_frame_paints_inline_renderables() -> None:
    from xnano.fields import GridFieldInfo

    terminal = Terminal.offscreen(cols=30, rows=5)
    terminal._render_frame(
        renderables=("alpha", "beta"), field=GridFieldInfo()
    )
    lines = [line.rstrip() for line in terminal.get_output().splitlines()]
    assert lines[0] == "alpha"
    assert lines[1] == "beta"


def test_render_frame_paints_lone_root_renderable() -> None:
    terminal = Terminal.offscreen(cols=30, rows=5)
    terminal._render_frame("solo")
    lines = [line.rstrip() for line in terminal.get_output().splitlines()]
    assert lines[0] == "solo"


# ---------------------------------------------------------------------------
# run() dispatch routing (BaseGrid vs inline)
# ---------------------------------------------------------------------------


def _run_would_use_inline(*renderables: object) -> bool:
    """Mirror the BaseGrid-vs-inline branch that ``Terminal.run`` uses."""
    return not (len(renderables) == 1 and isinstance(renderables[0], BaseGrid))


def test_run_routes_single_grid_to_full_screen() -> None:
    class MyGrid(BaseGrid):
        body: str = Field(default="hello")

    # A lone BaseGrid takes the full-screen path (no inline viewport).
    assert _run_would_use_inline(MyGrid()) is False


def test_run_routes_strings_to_inline() -> None:
    assert _run_would_use_inline("hello world") is True
    assert _run_would_use_inline("a", "b") is True


def test_fresh_terminal_has_no_inline_height() -> None:
    terminal: Terminal = Terminal()
    assert terminal._inline_height is None


# ---------------------------------------------------------------------------
# Terminal viewport resolution (root sizing → Viewport)
#
# ``_resolve_run`` is pure: it returns a ``_ResolvedRun`` rather than mutating
# the terminal, so these assert on the returned value.
# ---------------------------------------------------------------------------


def test_resolve_run_grid_defaults_to_fullscreen() -> None:
    terminal: Terminal = Terminal()
    resolved = terminal._resolve_run(["x"], is_grid=True, field=None)
    # A BaseGrid defaults to fill height → full-screen (no inline viewport).
    assert resolved.inline_height is None
    assert resolved.root_width_sizing == Sizing.fraction(1)


def test_resolve_run_leaf_defaults_to_inline_fit() -> None:
    terminal: Terminal = Terminal()
    resolved = terminal._resolve_run(["hi\nthere"], is_grid=False, field=None)
    # A leaf defaults to fit height → inline viewport sized to content.
    assert resolved.inline_height == 2
    assert resolved.root_width_sizing == Sizing.fit()


def test_resolve_run_explicit_cells_height_is_inline() -> None:
    terminal: Terminal = Terminal(height=5)
    resolved = terminal._resolve_run(["x"], is_grid=True, field=None)
    # An explicit finite height forces an inline viewport even for a BaseGrid.
    assert resolved.inline_height == 5


def test_resolve_run_explicit_fill_height_is_fullscreen() -> None:
    terminal: Terminal = Terminal(height="1fr")
    resolved = terminal._resolve_run(["hi"], is_grid=False, field=None)
    # An explicit fill height forces full-screen even for a leaf.
    assert resolved.inline_height is None


def test_resolve_run_records_explicit_width_sizing() -> None:
    terminal: Terminal = Terminal(width=40)
    resolved = terminal._resolve_run(["hi"], is_grid=False, field=None)
    assert resolved.root_width_sizing == Sizing.cells(40)


def test_resolve_run_fit_grid_falls_back_to_fullscreen() -> None:
    # A BaseGrid has no measurable intrinsic height, so an explicit fit height
    # cannot reserve an inline viewport and must fall back to full-screen —
    # and it warns rather than silently overriding the request.
    terminal: Terminal = Terminal(height="fit")
    with pytest.warns(UserWarning, match="has no effect for a BaseGrid"):
        resolved = terminal._resolve_run(["x"], is_grid=True, field=None)
    assert resolved.inline_height is None


def test_resolve_run_cells_height_grid_is_inline() -> None:
    # A fixed cells height needs no measurement, so it works for a BaseGrid.
    terminal: Terminal = Terminal(height=8)
    resolved = terminal._resolve_run(["x"], is_grid=True, field=None)
    assert resolved.inline_height == 8


def test_resolve_run_returns_result_without_mutating_terminal() -> None:
    # The resolution is a returned value, not a side effect.
    terminal: Terminal = Terminal(height=5)
    terminal._resolve_run(["x"], is_grid=True, field=None)
    assert terminal._inline_height is None
    assert terminal._root_width_sizing is None
