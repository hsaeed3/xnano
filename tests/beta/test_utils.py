"""tests.beta.test_utils

---

Direct coverage for the decoupled ``xnano.beta.utils`` modules and the
``State`` container built on them.
"""

from __future__ import annotations

from typing import Any

import pytest

from xnano.beta.core.exceptions import Exit
from xnano.beta.state import State
from xnano.beta.utils import introspection, validation
from xnano.beta.utils.dispatch import invoke_hook, run_awaitable
from xnano.beta.utils.markup import (
    highlight_lines,
    markdown_blocks,
    markdown_lines,
    parse_ansi_lines,
    strip_ansi_escapes,
)

# ── markup ──────────────────────────────────────────────────────────────


def test_strip_ansi_escapes() -> None:
    assert strip_ansi_escapes("\x1b[31mred\x1b[0m") == "red"


def test_parse_ansi_lines_carries_color() -> None:
    lines = parse_ansi_lines("\x1b[31mred\x1b[0m plain")
    runs = lines[0]
    assert runs[0].text == "red"
    assert runs[0].color is not None
    assert "".join(run.text for run in runs) == "red plain"


def test_parse_ansi_lines_splits_on_newlines() -> None:
    lines = parse_ansi_lines("one\ntwo")
    assert len(lines) == 2
    assert lines[0][0].text == "one"
    assert lines[1][0].text == "two"


def test_highlight_lines_unknown_language_is_plain() -> None:
    lines = highlight_lines("value = 1", "not-a-language")
    assert "".join(run.text for run in lines[0]) == "value = 1"


def test_highlight_lines_python_tokenizes() -> None:
    lines = highlight_lines("def f():\n    return 1", "python")
    text = "\n".join("".join(run.text for run in line) for line in lines)
    assert "def" in text
    assert "return" in text


def test_markdown_lines_heading_and_code() -> None:
    lines = markdown_lines("# Title\n\n```\ncode\n```")
    flat = ["".join(run.text for run in line) for line in lines]
    assert any("Title" in line for line in flat)
    assert any("code" in line for line in flat)


@pytest.mark.parametrize(
    "kind", ("NOTE", "TIP", "IMPORTANT", "WARNING", "CAUTION")
)
def test_markdown_lines_github_admonition(kind: str) -> None:
    lines = markdown_lines(f"> [!{kind}]\n> Useful information.")
    text = "".join(run.text for run in lines[0])
    assert kind.title() in text
    assert "[!" not in text
    assert "Useful information." in text


def test_markdown_blocks_splits_images() -> None:
    blocks = markdown_blocks("text\n\n![alt](pic.png)\n\nmore")
    kinds = [block[0] for block in blocks]
    assert kinds == ["text", "image", "text"]
    assert blocks[1] == ("image", "pic.png", "alt")


def test_markdown_blocks_plain_text_is_single_block() -> None:
    blocks = markdown_blocks("just prose here")
    assert len(blocks) == 1
    assert blocks[0][0] == "text"


# ── introspection ───────────────────────────────────────────────────────


def test_extra_parameter_count_ignores_self() -> None:
    def zero(self) -> None: ...

    def one(self, ctx) -> None: ...

    assert introspection.get_function_extra_parameter_count(zero) == 0
    assert introspection.get_function_extra_parameter_count(one) == 1


def test_first_parameter_type() -> None:
    def handler(self, ctx) -> None: ...

    # Set a real type object (the module uses ``from __future__ import
    # annotations``, which would otherwise stringize the hint).
    handler.__annotations__ = {"ctx": int}
    assert introspection.get_first_function_parameter_type(handler) is int


def test_evaluate_state_expression() -> None:
    class Model:
        def __init__(self) -> None:
            self.count = 5

    model = Model()
    assert introspection.evaluate_state_expression("count > 3", model) is True
    assert introspection.evaluate_state_expression("count > 9", model) is False


def test_evaluate_state_expression_is_safe_on_error() -> None:
    class Model:
        pass

    assert (
        introspection.evaluate_state_expression("missing > 1", Model())
        is False
    )
    assert introspection.evaluate_state_expression("x", None) is False


def test_compiled_expression_caches_bad_source_as_none() -> None:
    assert introspection.get_compiled_state_expression("a ==") is None


def test_evaluate_state_expression_supports_common_forms() -> None:
    class Model:
        def __init__(self) -> None:
            self.count = 5
            self.loading = True
            self.config = {"name": "john"}
            self.items = [1, 2, 3]

    ev = introspection.evaluate_state_expression
    model = Model()
    assert ev("count >= 5 and count <= 10", model) is True
    assert ev("count > 9 or loading", model) is True
    assert ev("not loading", model) is False
    assert ev("config['name'] == 'john'", model) is True
    assert ev("len(items) == 3", model) is True
    assert ev("count + 1 == 6", model) is True
    assert ev("items[0] == 1", model) is True


def test_evaluate_state_expression_refuses_code_execution() -> None:
    """The evaluator never executes code: dunder access and any call
    outside the safe-builtin whitelist evaluate to ``False`` rather than
    reaching the interpreter."""

    class Model:
        def __init__(self) -> None:
            self.value = 1

    ev = introspection.evaluate_state_expression
    model = Model()
    # Attribute access to dunder names is refused.
    assert ev("state.__class__.__name__ == 'Model'", model) is False
    # Calls to anything not in the safe-builtin whitelist are refused.
    assert ev("open('x')", model) is False
    assert ev("__import__('os')", model) is False


# ── dispatch ────────────────────────────────────────────────────────────

# A stand-in context; hooks under test never read it.
_CTX: Any = object()


def test_invoke_hook_calls_zero_and_one_arg_forms() -> None:
    calls: list[str] = []

    class Grid:
        def zero(self) -> None:
            calls.append("zero")

        def one(self, ctx) -> str:
            calls.append("one")
            return "value"

    grid = Grid()
    invoke_hook(Grid.zero, grid, _CTX)
    assert invoke_hook(Grid.one, grid, _CTX) == "value"
    assert calls == ["zero", "one"]


def test_invoke_hook_awaits_async_result() -> None:
    class Grid:
        async def handler(self, ctx) -> int:
            return 21

    grid = Grid()
    assert invoke_hook(Grid.handler, grid, _CTX) == 21


def test_invoke_hook_propagates_exit() -> None:
    class Grid:
        def handler(self) -> None:
            raise Exit()

    with pytest.raises(Exit):
        invoke_hook(Grid.handler, Grid(), _CTX)


def test_run_awaitable_drives_coroutine() -> None:
    async def value() -> str:
        return "done"

    assert run_awaitable(value()) == "done"


# ── validation ──────────────────────────────────────────────────────────


def test_validate_type_coerces_and_checks() -> None:
    assert validation.validate_type(3, int) == 3
    assert validation.validate_type("x", str) == "x"


def test_validate_type_rejects_bad_value() -> None:
    with pytest.raises(Exception):
        validation.validate_type("not-an-int", int)


def test_validate_type_accepts_beta_component() -> None:
    from xnano.beta.components.text import Text

    text = Text("hi")
    assert validation.validate_type(text, Text) is text


def test_validate_type_accepts_beta_grid() -> None:
    from xnano.beta.grids import BaseGrid

    class App(BaseGrid):
        pass

    app = App()
    assert validation.validate_type(app, App) is app


def test_validate_type_containers_and_unions() -> None:
    from typing import Optional, Union

    assert validation.validate_type([1, 2], list[int]) == [1, 2]
    assert validation.validate_type({"a": 1}, dict[str, int]) == {"a": 1}
    assert validation.validate_type((1, "x"), tuple[int, str]) == (1, "x")
    assert validation.validate_type(5, Union[int, str]) == 5
    assert validation.validate_type(None, Optional[int]) is None


def test_validate_type_literal_and_enum() -> None:
    import enum
    from typing import Literal

    assert validation.validate_type("go", Literal["go", "stop"]) == "go"

    class Color(enum.Enum):
        RED = "red"

    assert validation.validate_type(Color.RED, Color) is Color.RED


def test_validate_type_dataclass() -> None:
    import dataclasses

    @dataclasses.dataclass
    class Point:
        x: int
        y: int

    result = validation.validate_type({"x": 1, "y": 2}, Point)
    assert (result.x, result.y) == (1, 2)


def test_layout_field_annotation_is_renderable() -> None:
    assert validation.layout_field_annotation() is not None


# ── state ───────────────────────────────────────────────────────────────


def test_state_stores_dynamic_attributes() -> None:
    state = State(name="John", age=30)
    assert state.name == "John"
    assert state.age == 30
    state.city = "NYC"
    assert state.city == "NYC"


def test_state_validates_declared_annotations() -> None:
    class AppState(State):
        count: int

    state = AppState(count=1)
    assert state.count == 1
    with pytest.raises(Exception):
        state.count = "not-an-int"  # ty: ignore[invalid-assignment]


def test_state_unknown_attribute_raises() -> None:
    state = State()
    with pytest.raises(AttributeError):
        _ = state.missing
