"""tests.test_color_alias_and_text_default

---

Covers the ``color`` -> ``foreground`` deprecation alias on components and
``Field``, plus coercing a plain ``str`` default on a ``Text`` field into a
``Text`` component so it renders as that text.
"""

from __future__ import annotations

import warnings

import pytest

from xnano.components.text import Text
from xnano.fields import Field
from xnano.grids import BaseGrid
from xnano.terminal import Terminal


def test_color_alias_sets_foreground_and_warns() -> None:
    with pytest.warns(DeprecationWarning):
        # Deprecated ``color`` alias, exercised on purpose.
        text = Text(
            "hello",
            color="cyan",  # ty: ignore[unknown-argument]
        )
    assert text.foreground == "cyan"
    # Deprecated ``color`` property still reads back the foreground.
    assert text.color == "cyan"  # ty: ignore[unresolved-attribute]


def test_foreground_is_canonical_without_warning() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        text = Text("hello", foreground="magenta")
    assert text.foreground == "magenta"


def test_foreground_wins_when_both_passed() -> None:
    with pytest.warns(DeprecationWarning):
        text = Text(
            "hello",
            foreground="red",
            color="blue",  # ty: ignore[unknown-argument]
        )
    assert text.foreground == "red"


def test_field_color_alias_warns_and_sets_foreground() -> None:
    with pytest.warns(DeprecationWarning):
        field = Field(default="", color="green")
    # ``Field`` is typed to return its default for class-attr use, so the
    # static type here is ``str``; the alias resolves at runtime.
    assert field.color == "green"  # ty: ignore[unresolved-attribute]


def test_str_default_on_text_field_renders() -> None:
    class App(BaseGrid):
        # Task 3: a plain str default is coerced to ``Text`` at runtime;
        # the static type is intentionally left unmodeled.
        label: Text = Field(  # ty: ignore[invalid-assignment]
            default="hello world"
        )

    grid = App()
    assert isinstance(grid.label, Text)

    terminal = Terminal.offscreen(cols=40, rows=4)
    terminal.attach_grid(grid)
    frame = terminal.render()
    terminal.close()

    assert "hello world" in frame.text
