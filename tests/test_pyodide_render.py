"""Tests for the wasm/Pyodide render path and its feature-reduced native.

Pyodide loads ``xnano-core`` built with ``--no-default-features`` (no
``terminal`` cargo feature), and drives a one-shot ``Terminal.offscreen``
buffer — no live terminal, no event loop. This module pins two things that
have broken that path before:

1. **Import under a feature-reduced native.** The ``terminal`` feature is
   what registers ``native.ClearType`` (and ``CursorStyle``,
   ``KeyboardEnhancementFlags``, …). ``xnano.device`` builds its clear-type
   map at *module scope*, so if it touches ``native.ClearType`` eagerly the
   whole framework becomes unimportable in the browser. Reproduced here by
   deleting ``ClearType`` from the real native module and re-executing
   ``device.py`` in isolation — exactly what dyld hands Pyodide.

2. **Buffer-backed layout and styling.** Regressions found writing the docs
   sandbox: a lone ``BaseGrid`` root must drive the real layout engine (not
   collapse to one line), bordered renderables must keep their border rows,
   and cell colors must survive to ANSI. In v1.2 the buffer-backed path is
   just ``Terminal.offscreen(...).render(...)`` returning a ``Frame`` — no
   monkeypatched ``_supports_live_terminal`` needed anymore.
"""

from __future__ import annotations

import importlib.util
from typing import Any

import pytest
import xnano_core.rust.native as native

import xnano.device as device
from xnano.fields import Field
from xnano.grids import BaseGrid
from xnano.terminal import Terminal

# ---------------------------------------------------------------------------
# Regression: import must survive a native wheel without the terminal feature
# ---------------------------------------------------------------------------


def _reload_device_isolated() -> Any:
    """Re-execute ``device.py`` under a throwaway module name.

    Runs the module top-to-bottom against whatever ``xnano_core.rust.native``
    currently exposes, without clobbering the canonical ``xnano.device`` other
    tests import.
    """
    spec = importlib.util.spec_from_file_location(
        "xnano._device_probe", device.__file__
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_device_imports_without_terminal_feature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # native.ClearType is registered only by the `terminal` cargo feature,
    # which the wasm wheel is built without. Deleting it mimics that build.
    monkeypatch.delattr(native, "ClearType")
    module = _reload_device_isolated()
    assert module._NATIVE_CLEAR_TYPES == {}


def test_device_clear_type_map_is_full_with_terminal_feature() -> None:
    # Positive control: the normal (feature-complete) build maps every value.
    assert set(device._NATIVE_CLEAR_TYPES) == {
        "all",
        "purge",
        "from_cursor_down",
        "from_cursor_up",
        "current_line",
        "until_new_line",
    }


# ---------------------------------------------------------------------------
# Regression: a lone BaseGrid root must drive the real layout engine
# ---------------------------------------------------------------------------


def test_grid_root_renders_every_field_not_just_first_line() -> None:
    class App(BaseGrid, direction="vertical"):
        title: str = Field(default="My App", border="rounded")
        body: str = Field(default="Hello, world!")

    with Terminal.offscreen(cols=40, rows=6) as terminal:
        lines = terminal.render(App()).text.splitlines()

    assert lines[0].startswith("╭")
    assert any("My App" in line for line in lines)
    assert any(line.startswith("╰") for line in lines)
    assert any("Hello, world!" in line for line in lines)


def test_grid_root_with_explicit_height_still_lays_out_fields() -> None:
    class App(BaseGrid, direction="vertical"):
        title: str = Field(default="My App", border="rounded")
        body: str = Field(default="Hello, world!")

    with Terminal.offscreen(cols=40, rows=4) as terminal:
        lines = terminal.render(App()).text.splitlines()

    assert len(lines) == 4
    assert lines[0].startswith("╭")
    assert "My App" in lines[1]
    assert lines[2].startswith("╰")
    assert "Hello, world!" in lines[3]


def test_grid_root_state_field_is_never_painted() -> None:
    class App(BaseGrid, direction="vertical"):
        title: str = Field(default="My App", border="rounded")
        body: str = Field(default="")
        name: str = Field(default="Hammad", state=True)

        def __post_init__(self) -> None:
            self.body = f"Hello, {self.name}!"

    with Terminal.offscreen(cols=40, rows=4) as terminal:
        text = terminal.render(App()).text

    assert "Hammad" not in text.split("Hello,", 1)[0]
    assert "Hello, Hammad!" in text


def test_nested_grid_root_still_lays_out_through_buffer_backed_path() -> None:
    class Inner(BaseGrid, direction="vertical"):
        label: str = Field(default="inner", border="rounded")

    class Outer(BaseGrid, direction="vertical"):
        inner: Inner = Field(default_factory=Inner)
        footer: str = Field(default="footer text")

    with Terminal.offscreen(cols=40, rows=6) as terminal:
        lines = terminal.render(Outer()).text.splitlines()

    assert any("inner" in line for line in lines)
    assert any("footer text" in line for line in lines)


# ---------------------------------------------------------------------------
# Regression: bordered renderables keep their chrome on the buffer path
# ---------------------------------------------------------------------------


def test_multiple_bordered_renderables_share_one_box_with_all_text() -> None:
    # In v1.2 multiple renderables under a single `border` render as one
    # grouped box (not one border each) — both must still paint inside it.
    with Terminal.offscreen(cols=20, rows=8) as terminal:
        text = terminal.render("line one", "line two", border="rounded").text

    assert text.count("╭") == 1
    assert text.count("╰") == 1
    assert "line one" in text
    assert "line two" in text


def test_single_non_grid_renderable_with_border() -> None:
    with Terminal.offscreen(cols=20, rows=3) as terminal:
        lines = terminal.render("solo", border="rounded").text.splitlines()

    assert lines[0].startswith("╭")
    assert "solo" in lines[1]
    assert lines[-1].startswith("╰")


# ---------------------------------------------------------------------------
# Regression: cell colors and modifiers survive to ANSI on the buffer path
# ---------------------------------------------------------------------------


def test_cell_styles_are_preserved_as_ansi() -> None:
    with Terminal.offscreen(cols=12, rows=1) as terminal:
        ansi = terminal.render(
            "painted", foreground="violet", modifiers=["bold"]
        ).ansi

    assert "\x1b[38;2;238;130;238m" in ansi  # violet foreground
    assert "\x1b[1m" in ansi  # bold
    assert "painted" in ansi
