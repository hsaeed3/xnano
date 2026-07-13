"""Tests for ``Terminal._render_buffer_backed`` — the wasm/Pyodide path.

Pyodide (and any other build of ``xnano-core`` without the ``terminal``
cargo feature) never has a live terminal to attach to, so a one-shot
``render()`` call goes through ``Terminal._render_buffer_backed``: it sizes
an offscreen ``CoreSession`` buffer and paints one frame into it, with no
event loop. This module can't build an actual wasm wheel, so it forces the
same code path locally by monkeypatching ``Terminal._supports_live_terminal``
to ``False`` and going through the public ``render()`` entry point — the
same one a ``xnano.render(...)`` call inside a ``pyodide`` fence hits.

Passing ``file=`` to ``render()`` is deliberately avoided here: it routes to
a completely different renderer (``xnano._renderable.render``, the plain
ANSI-fallback path already covered by ``test_render_fallback.py``) and never
reaches ``_render_buffer_backed`` at all. Only the default-stdout call shape
(no ``file``/``stream``/``update``) takes the buffer-backed path, so these
tests capture real stdout via ``capsys`` instead.

Regression coverage in here guards two distinct bugs found while writing the
``core-concepts/grids.md`` interactive example:

1. A lone ``BaseGrid`` renderable was never routed through ``root=`` into
   ``_dispatch.render_frame``, so ``isinstance(root, BaseGrid)`` was always
   ``False`` and the grid's fields never got laid out — only whatever the
   inline/text path happened to paint (effectively one line).
2. Multiple plain (non-grid) renderables were measured with
   ``measure_renderable`` instead of ``measure_renderable_in_field``,
   dropping border/padding overhead from the offscreen buffer's height.
"""

from __future__ import annotations

from typing import Any

import pytest

from xnano.fields import Field
from xnano.grid import BaseGrid
from xnano.tui import Terminal


@pytest.fixture(autouse=True)
def _force_headless(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every ``Terminal`` in this module think it's a wasm build.

    Without this, ``Terminal.render()`` on a real desktop build takes the
    live-terminal branch instead of ``_render_buffer_backed`` — the one
    Pyodide actually uses.
    """
    monkeypatch.setattr(
        Terminal, "_supports_live_terminal", staticmethod(lambda: False)
    )


def _render(
    *renderables: Any,
    capsys: pytest.CaptureFixture[str],
    width: Any = None,
    height: Any = None,
    **render_kwargs: Any,
) -> str:
    Terminal(width=width, height=height).render(*renderables, **render_kwargs)
    return capsys.readouterr().out


# ---------------------------------------------------------------------------
# Regression: a lone BaseGrid root must drive the real layout engine
# ---------------------------------------------------------------------------


def test_grid_root_renders_every_field_not_just_first_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    class App(BaseGrid, direction="vertical"):
        title: str = Field(default="My App", border="rounded")
        body: str = Field(default="Hello, world!")

    out = _render(App(), capsys=capsys)
    lines = out.splitlines()
    assert lines[0].startswith("╭")
    assert any("My App" in line for line in lines)
    assert any(line.startswith("╰") for line in lines)
    assert any("Hello, world!" in line for line in lines)


def test_grid_root_with_explicit_height_still_lays_out_fields(
    capsys: pytest.CaptureFixture[str],
) -> None:
    class App(BaseGrid, direction="vertical"):
        title: str = Field(default="My App", border="rounded")
        body: str = Field(default="Hello, world!")

    out = _render(App(), capsys=capsys, height=4)
    lines = out.splitlines()
    assert len(lines) == 4
    assert lines[0].startswith("╭")
    assert "My App" in lines[1]
    assert lines[2].startswith("╰")
    assert "Hello, world!" in lines[3]


def test_grid_root_default_sizing_is_not_one_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # No explicit height/width: falls back to the 80x24 default viewport,
    # same as a live terminal would, rather than a bogus str()-based guess.
    class App(BaseGrid, direction="vertical"):
        title: str = Field(default="My App", border="rounded")
        body: str = Field(default="Hello, world!")

    out = _render(App(), capsys=capsys)
    lines = out.splitlines()
    assert len(lines) > 1
    assert any("Hello, world!" in line for line in lines)


def test_grid_root_state_field_is_never_painted(
    capsys: pytest.CaptureFixture[str],
) -> None:
    class App(BaseGrid, direction="vertical"):
        title: str = Field(default="My App", border="rounded")
        body: str = Field(default="")
        name: str = Field(default="Hammad", state=True)

        def __post_init__(self) -> None:
            self.body = f"Hello, {self.name}!"

    out = _render(App(), capsys=capsys, height=4)
    assert "Hammad" not in out.split("Hello,", 1)[0]
    assert "Hello, Hammad!" in out


def test_nested_grid_root_still_lays_out_through_buffer_backed_path(
    capsys: pytest.CaptureFixture[str],
) -> None:
    class Inner(BaseGrid, direction="vertical"):
        label: str = Field(default="inner", border="rounded")

    class Outer(BaseGrid, direction="vertical"):
        inner: Inner = Field(default_factory=Inner)
        footer: str = Field(default="footer text")

    out = _render(Outer(), capsys=capsys, height=6)
    lines = out.splitlines()
    assert any("inner" in line for line in lines)
    assert any("footer text" in line for line in lines)


def test_grid_mixed_with_other_renderables_is_a_known_gap(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # KNOWN LIMITATION, not asserted as desired behavior: the BaseGrid
    # routing fix only applies when the grid is the *sole* renderable.
    # Mixed in with anything else, its own field content is lost entirely —
    # only the group's shared border/footer text paints. Pinned here so a
    # future fix for this case is a deliberate change, not a silent one, and
    # so nobody mistakes this for already being covered by the routing fix.
    class App(BaseGrid, direction="vertical"):
        title: str = Field(default="My App", border="rounded")

    out = _render(App(), "footer", capsys=capsys)
    assert "footer" in out
    assert "My App" not in out


# ---------------------------------------------------------------------------
# Regression: multiple plain (non-grid) renderables keep border overhead
# ---------------------------------------------------------------------------


def test_multiple_bordered_renderables_each_keep_full_border(
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = _render("line one", "line two", capsys=capsys, border="rounded")
    assert out.count("╭") == 2
    assert out.count("╰") == 2
    assert "line one" in out
    assert "line two" in out


def test_multiple_renderables_height_matches_bordered_row_count(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Two bordered single-line renderables: 3 rows each (top/content/bottom).
    out = _render("a", "b", capsys=capsys, border="rounded")
    assert len(out.splitlines()) == 6


def test_single_non_grid_renderable_with_border_unaffected_by_grid_fix(
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = _render("solo", capsys=capsys, border="rounded")
    lines = out.splitlines()
    assert lines[0].startswith("╭")
    assert "solo" in lines[1]
    assert lines[2].startswith("╰")


# ---------------------------------------------------------------------------
# Sizing overrides on the buffer-backed path
#
# Explicit ``width=``/``height=`` on ``Terminal`` control the *offscreen
# buffer* allocation, not necessarily how much of it fit-width/fit-height
# inline content stretches to fill — so these assert on the ``cols=``/
# ``rows=`` actually handed to ``CoreSession.offscreen`` rather than on
# rendered text width, which auto-fit content wouldn't reflect anyway.
# ---------------------------------------------------------------------------


def _offscreen_dims(
    *renderables: Any,
    monkeypatch: pytest.MonkeyPatch,
    width: Any = None,
    height: Any = None,
    **render_kwargs: Any,
) -> tuple[int, int]:
    calls: list[tuple[int, int]] = []
    real_offscreen = Terminal.offscreen.__func__

    def _spy(cls: type[Terminal[Any]], *, cols: int, rows: int, **kwargs: Any) -> Terminal[Any]:
        calls.append((cols, rows))
        return real_offscreen(cls, cols=cols, rows=rows, **kwargs)

    monkeypatch.setattr(Terminal, "offscreen", classmethod(_spy))
    Terminal(width=width, height=height).render(*renderables, **render_kwargs)
    assert calls, "offscreen() was never called"
    return calls[0]


def test_explicit_width_overrides_measured_width(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cols, _ = _offscreen_dims(
        "hi", monkeypatch=monkeypatch, width=30, border="plain"
    )
    assert cols == 30


def test_explicit_height_overrides_measured_height(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, rows = _offscreen_dims("hi", monkeypatch=monkeypatch, height=12)
    assert rows == 12


def test_default_width_and_height_when_nothing_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cols, rows = _offscreen_dims("hi", monkeypatch=monkeypatch)
    assert (cols, rows) == (2, 1)


def test_explicit_height_smaller_than_content_truncates(
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = _render("a\nb\nc\nd\ne", capsys=capsys, height=2)
    assert out.splitlines() == ["a", "b"]


# ---------------------------------------------------------------------------
# print()-compatible kwargs still work through the buffer-backed path
# ---------------------------------------------------------------------------


def test_end_kwarg_is_respected(capsys: pytest.CaptureFixture[str]) -> None:
    out = _render("no-newline", capsys=capsys, end="")
    assert out == "no-newline"


def test_flush_does_not_raise(capsys: pytest.CaptureFixture[str]) -> None:
    # flush=True on a headless render just needs to not blow up — there's no
    # custom file object here to assert flush-call-count against, since that
    # would require passing file= (which skips this code path entirely).
    _render("x", capsys=capsys, flush=True, end="")
