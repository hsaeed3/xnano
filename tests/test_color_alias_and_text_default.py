"""tests.test_color_alias_and_text_default

---

Covers the ``color`` -> ``foreground`` deprecation alias on components and
``Field``, plus coercing a plain ``str`` default on a ``Text`` field into a
``Text`` component so it renders as that text.
"""

from __future__ import annotations

import warnings

import pytest

from xnano.colors import (
    Color,
    get_native_color,
    pydantic_color,
    tailwind_color,
)
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


def test_color_forms_flow_through_field_component_and_terminal() -> None:
    class App(BaseGrid):
        label: Text = Field(
            default_factory=lambda: Text(
                "status",
                foreground="#22c55e",
            ),
            background="slate-900",
            border="rounded",
        )

    terminal = Terminal.offscreen(cols=24, rows=4)
    try:
        terminal.attach_grid(App())
        frame = terminal.render()
        ansi = terminal.get_output_as_ansi()

        assert frame.contains("status")
        assert "38;2;34;197;94" in ansi
        assert "48;2;15;23;42" in ansi
    finally:
        terminal.close()


def test_grid_set_field_color_alias_warns_and_sets_foreground() -> None:
    class App(BaseGrid):
        label: str = Field(default="hi")

    grid = App()
    with pytest.warns(DeprecationWarning):
        grid.grid_set_field(
            "label",
            color="cyan",
        )
    overrides = grid._grid_field_overrides  # ty: ignore[unresolved-attribute]
    assert overrides["label"].foreground == "cyan"


def test_grid_update_field_foreground_wins_over_color() -> None:
    class App(BaseGrid):
        label: str = Field(default="hi")

    grid = App()
    with pytest.warns(DeprecationWarning):
        grid.grid_update_field(
            "label",
            foreground="red",
            color="blue",
        )
    overrides = grid._grid_field_overrides  # ty: ignore[unresolved-attribute]
    assert overrides["label"].foreground == "red"


def test_grid_settings_color_class_kwarg_maps_to_foreground() -> None:
    with pytest.warns(DeprecationWarning):

        class Aliased(BaseGrid, color="red"):
            pass

    assert Aliased.grid_settings["foreground"] == "red"

    with warnings.catch_warnings():
        warnings.simplefilter("error")

        class Canonical(BaseGrid, foreground="blue"):
            pass

    assert Canonical.grid_settings["foreground"] == "blue"


def test_content_primitive_color_alias_round_trips() -> None:
    from xnano.core.content import Run, TextBlock

    with pytest.warns(DeprecationWarning):
        run = Run(
            text="x",
            color="cyan",  # ty: ignore[unknown-argument]
        )
    assert run.foreground == "cyan"
    assert run.color == "cyan"  # ty: ignore[unresolved-attribute]

    # Classmethod constructors carry the alias too — the dataclass
    # decorator only wraps ``__init__``.
    with pytest.warns(DeprecationWarning):
        block = TextBlock.from_plain(
            "x",
            color="lime",
        )
    assert block.foreground == "lime"

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert (
            TextBlock.from_plain("x", foreground="lime").foreground == "lime"
        )


def test_paint_cell_color_alias_maps_to_foreground() -> None:
    from xnano.core.stage import Stage

    stage = Stage()
    with pytest.warns(DeprecationWarning):
        stage.paint_cell(
            0,
            0,
            "!",
            color="yellow",
        )
    assert stage._commands[0]["foreground"] == "yellow"


def test_link_foreground_is_not_shadowed_by_color() -> None:
    """``Link`` redeclared ``color``, shadowing ``Text``'s alias property.

    That made ``Link(foreground=...)`` silently render the default blue.
    """
    from xnano.components.link import Link

    assert Link(content="x").foreground == "blue"
    assert Link(content="x", foreground="red").foreground == "red"
    with pytest.warns(DeprecationWarning):
        aliased = Link(
            content="x",
            color="green",  # ty: ignore[unknown-argument]
        )
    assert aliased.foreground == "green"


def test_effect_surfaces_keep_color_without_warning() -> None:
    """Effects intentionally keep ``color``/``background`` — no rename."""
    from xnano.effects import Effect, FadeEffect

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert FadeEffect(color="violet").color == "violet"
        assert Effect("fade", color="violet", duration_ms=10) is not None


def test_color_inputs_share_one_conversion_contract() -> None:
    assert Color.parse("red").as_rgb_tuple() == (255, 0, 0)
    assert Color.parse("#0f08").as_hex(include_alpha=True) == "#00ff0088"
    assert (
        Color.parse((34, 197, 94, 128)).as_hex(include_alpha=True)
        == "#22c55e80"
    )

    accent = tailwind_color("violet", 600)
    assert Color.parse("violet-600") is accent
    assert Color.parse(accent) is accent
    assert accent.as_rgb_tuple(include_alpha=True) == (
        accent.r,
        accent.g,
        accent.b,
        accent.a,
    )
    assert pydantic_color("red") == Color(255, 0, 0)
    assert get_native_color(None) is None
    assert get_native_color("#22c55e") is get_native_color("#22c55e")


@pytest.mark.parametrize(
    "value",
    (
        "#12",
        "not-a-color",
        (1, 2),
        42,
    ),
)
def test_invalid_user_colors_fail_at_the_boundary(value: object) -> None:
    with pytest.raises(ValueError):
        Color.parse(value)  # ty: ignore[invalid-argument-type]
