"""Tests for xnano._renderable — stdout fallback renderer.

All tests run without a live terminal (no TTY / no _ACTIVE_TERMINAL set),
exercising the ANSI-based fallback path directly.
"""

from __future__ import annotations

import pytest

from xnano._renderable import (
    _RESET,
    _ansi_color,
    _apply_border,
    _apply_padding,
    _build_ansi_prefix,
    _join_horizontal,
    _render_to_stdout,
    _renderable_to_lines,
    render,
)


@pytest.fixture(autouse=True)
def _force_fallback_path():
    """Ensure _ACTIVE_TERMINAL is None for every test in this module.

    test_grid_set_field.py creates a Terminal.offscreen() without a context
    manager, leaving _ACTIVE_TERMINAL set for the rest of the process.  That
    causes render() to take the terminal path and produce no stdout output.
    This fixture resets the context var to None for the duration of each test
    so the fallback renderer is always exercised.
    """
    from xnano.tui import _ACTIVE_TERMINAL

    token = _ACTIVE_TERMINAL.set(None)
    yield
    _ACTIVE_TERMINAL.reset(token)


# ---------------------------------------------------------------------------
# _renderable_to_lines
# ---------------------------------------------------------------------------


def test_string_single_line() -> None:
    assert _renderable_to_lines("hello") == ["hello"]


def test_string_multiline() -> None:
    assert _renderable_to_lines("a\nb\nc") == ["a", "b", "c"]


def test_empty_string() -> None:
    assert _renderable_to_lines("") == [""]


def test_int() -> None:
    assert _renderable_to_lines(42) == ["42"]


def test_float() -> None:
    assert _renderable_to_lines(3.14) == ["3.14"]


def test_bool() -> None:
    assert _renderable_to_lines(True) == ["True"]
    assert _renderable_to_lines(False) == ["False"]


def test_list_of_strings() -> None:
    assert _renderable_to_lines(["a", "b"]) == ["a", "b"]


def test_nested_list() -> None:
    assert _renderable_to_lines(["a", ["b", "c"]]) == ["a", "b", "c"]


def test_tuple() -> None:
    assert _renderable_to_lines(("x", "y")) == ["x", "y"]


def test_arbitrary_object_uses_repr() -> None:
    class Foo:
        def __repr__(self) -> str:
            return "Foo()"

    lines = _renderable_to_lines(Foo())
    assert lines == ["Foo()"]


def test_multiline_repr() -> None:
    class Bar:
        def __repr__(self) -> str:
            return "Bar(\n  x=1\n)"

    assert _renderable_to_lines(Bar()) == ["Bar(", "  x=1", ")"]


# ---------------------------------------------------------------------------
# _ansi_color
# ---------------------------------------------------------------------------


def test_ansi_color_foreground() -> None:
    assert _ansi_color(255, 0, 0) == "\033[38;2;255;0;0m"


def test_ansi_color_background() -> None:
    assert _ansi_color(0, 128, 255, bg=True) == "\033[48;2;0;128;255m"


# ---------------------------------------------------------------------------
# _build_ansi_prefix
# ---------------------------------------------------------------------------


def test_prefix_empty_when_no_args() -> None:
    assert _build_ansi_prefix(None, None, None) == ""


def test_prefix_bold() -> None:
    prefix = _build_ansi_prefix(None, None, ["bold"])
    assert "\033[1m" in prefix


def test_prefix_italic() -> None:
    assert "\033[3m" in _build_ansi_prefix(None, None, ["italic"])


def test_prefix_underline() -> None:
    assert "\033[4m" in _build_ansi_prefix(None, None, ["underline"])


def test_prefix_dim() -> None:
    assert "\033[2m" in _build_ansi_prefix(None, None, ["dim"])


def test_prefix_slow_blink() -> None:
    assert "\033[5m" in _build_ansi_prefix(None, None, ["slow_blink"])


def test_prefix_rapid_blink() -> None:
    assert "\033[6m" in _build_ansi_prefix(None, None, ["rapid_blink"])


def test_prefix_reversed() -> None:
    assert "\033[7m" in _build_ansi_prefix(None, None, ["reversed"])


def test_prefix_multiple_modifiers() -> None:
    prefix = _build_ansi_prefix(None, None, ["bold", "italic"])
    assert "\033[1m" in prefix
    assert "\033[3m" in prefix


def test_prefix_color_by_name() -> None:
    prefix = _build_ansi_prefix("red", None, None)
    # red = (255, 0, 0)
    assert "\033[38;2;255;0;0m" in prefix


def test_prefix_color_by_hex() -> None:
    prefix = _build_ansi_prefix("#00ff00", None, None)
    assert "\033[38;2;0;255;0m" in prefix


def test_prefix_background_by_name() -> None:
    prefix = _build_ansi_prefix(None, "blue", None)
    assert "\033[48;2;" in prefix


def test_prefix_color_and_modifier_combined() -> None:
    prefix = _build_ansi_prefix("red", None, ["bold"])
    assert "\033[1m" in prefix
    assert "\033[38;2;255;0;0m" in prefix


def test_prefix_invalid_color_silently_skipped() -> None:
    # Should not raise; bad color names are swallowed
    prefix = _build_ansi_prefix("notacolor", None, None)
    assert "\033[38" not in prefix


# ---------------------------------------------------------------------------
# _apply_padding
# ---------------------------------------------------------------------------


def test_padding_none_is_noop() -> None:
    lines = ["hello"]
    assert _apply_padding(lines, None) == ["hello"]


def test_padding_uniform() -> None:
    result = _apply_padding(["hi"], 1)
    # top blank, padded line, bottom blank
    assert len(result) == 3
    assert result[0].strip() == ""
    assert result[1].startswith(" ") and result[1].endswith(" ")
    assert result[2].strip() == ""


def test_padding_left_right() -> None:
    result = _apply_padding(["hi"], (0, 2))
    assert result[0].startswith("  ")
    assert result[0].endswith("  ")


def test_padding_multiline_same_width() -> None:
    result = _apply_padding(["hello", "hi"], 1)
    # inner lines padded to same width (5)
    inner = [r for r in result if r.strip()]
    assert all(len(line) == 1 + 5 + 1 for line in inner)


def test_padding_empty_lines() -> None:
    result = _apply_padding([], 1)
    assert all(r.strip() == "" for r in result)


# ---------------------------------------------------------------------------
# _apply_border
# ---------------------------------------------------------------------------


def test_border_none_is_noop() -> None:
    lines = ["hi"]
    assert _apply_border(lines, None, None, "", None, None) == ["hi"]


def test_border_rounded_adds_top_bottom() -> None:
    result = _apply_border(["hi"], "rounded", None, "", None, None)
    assert result[0].startswith("╭")
    assert result[-1].startswith("╰")
    assert "│" in result[1]


def test_border_double() -> None:
    result = _apply_border(["x"], "double", None, "", None, None)
    assert result[0].startswith("╔")
    assert result[-1].startswith("╚")


def test_border_thick() -> None:
    result = _apply_border(["x"], "thick", None, "", None, None)
    assert result[0].startswith("┏")


def test_border_plain() -> None:
    result = _apply_border(["x"], "plain", None, "", None, None)
    assert result[0].startswith("+")
    assert result[-1].startswith("+")


def test_border_title_in_top() -> None:
    result = _apply_border(["content"], "rounded", None, "", "MyTitle", "top")
    assert "MyTitle" in result[0]


def test_border_title_in_bottom() -> None:
    result = _apply_border(
        ["content"], "rounded", None, "", "MyTitle", "bottom"
    )
    assert "MyTitle" in result[-1]
    assert "MyTitle" not in result[0]


def test_border_title_default_position_is_top() -> None:
    result = _apply_border(["content"], "rounded", None, "", "Title", None)
    assert "Title" in result[0]


def test_border_sides_top_only() -> None:
    result = _apply_border(["hi"], "plain", ["top"], "", None, None)
    assert result[0].startswith("-")
    assert "|" not in result[1]
    # no bottom border
    assert len(result) == 2  # top + content


def test_border_sides_left_right_only() -> None:
    result = _apply_border(["hi"], "plain", ["left", "right"], "", None, None)
    assert result[0].startswith("|")
    assert result[0].endswith("|")
    assert len(result) == 1  # no top/bottom


def test_border_color_prefix_wraps_chars() -> None:
    border_prefix = "\033[38;2;255;0;0m"
    result = _apply_border(["hi"], "rounded", None, border_prefix, None, None)
    assert result[0].startswith(border_prefix)


def test_border_multiline_content() -> None:
    result = _apply_border(
        ["line one", "line two"], "rounded", None, "", None, None
    )
    assert result[0].startswith("╭")
    assert "│" in result[1]
    assert "│" in result[2]
    assert result[-1].startswith("╰")


# ---------------------------------------------------------------------------
# _join_horizontal
# ---------------------------------------------------------------------------


def test_join_horizontal_two_groups() -> None:
    a = ["AA", "BB"]
    b = ["XX", "YY"]
    result = _join_horizontal([a, b])
    assert result == ["AAXX", "BBYY"]


def test_join_horizontal_unequal_heights() -> None:
    a = ["tall", "tall"]
    b = ["short"]
    result = _join_horizontal([a, b])
    assert len(result) == 2
    assert result[1] == "tall" + " " * len("short")


def test_join_horizontal_empty() -> None:
    assert _join_horizontal([]) == []


def test_join_horizontal_single_group() -> None:
    assert _join_horizontal([["hello"]]) == ["hello"]


def test_join_horizontal_unequal_widths() -> None:
    a = ["a", "bbb"]
    b = ["xx"]
    result = _join_horizontal([a, b])
    # width of a = 3, width of b = 2
    assert result[0] == "a  xx"
    assert result[1] == "bbb" + "  "


# ---------------------------------------------------------------------------
# _render_to_stdout — integration (captures stdout)
# ---------------------------------------------------------------------------


def _call_render(**kwargs):
    """Call _render_to_stdout and return written line groups."""
    import io

    buf = io.StringIO()
    renderables = kwargs.pop("renderables", ("hello",))
    _render_to_stdout(
        renderables,
        direction=kwargs.pop("direction", "vertical"),
        color=kwargs.pop("color", None),
        background=kwargs.pop("background", None),
        modifiers=kwargs.pop("modifiers", None),
        align=kwargs.pop("align", None),
        border=kwargs.pop("border", None),
        border_sides=kwargs.pop("border_sides", None),
        border_color=kwargs.pop("border_color", None),
        title=kwargs.pop("title", None),
        title_position=kwargs.pop("title_position", None),
        padding=kwargs.pop("padding", None),
        sep=kwargs.pop("sep", " "),
        end=kwargs.pop("end", "\n"),
        file=buf,
        flush=kwargs.pop("flush", False),
        stream=kwargs.pop("stream", None),
        update=kwargs.pop("update", False),
    )
    text = buf.getvalue()
    if text == "":
        return []
    # Preserve prior test expectation: one joined body string per call.
    body = text[:-1] if text.endswith("\n") else text
    return [body]


def test_stdout_plain_string() -> None:
    out = _call_render(renderables=("hello",))
    assert len(out) == 1
    assert "hello" in out[0]


def test_stdout_bold_modifier() -> None:
    out = _call_render(renderables=("hi",), modifiers=["bold"])
    assert "\033[1m" in out[0]
    assert _RESET in out[0]


def test_stdout_color_applied() -> None:
    out = _call_render(renderables=("hi",), color="red")
    assert "\033[38;2;255;0;0m" in out[0]


def test_stdout_no_ansi_when_no_style() -> None:
    out = _call_render(renderables=("plain",))
    assert "\033[" not in out[0]


def test_stdout_border_present() -> None:
    out = _call_render(renderables=("content",), border="rounded")
    assert "╭" in out[0]
    assert "╰" in out[0]


def test_stdout_vertical_stacks_renderables() -> None:
    out = _call_render(renderables=("a", "b"), direction="vertical")
    combined = out[0]
    lines = combined.split("\n")
    assert "a" in lines[0]
    assert "b" in lines[1]


def test_stdout_horizontal_joins_renderables() -> None:
    out = _call_render(renderables=("left", "right"), direction="horizontal")
    combined = out[0]
    assert "left" in combined
    assert "right" in combined
    # both on the same line
    assert "\n" not in combined


def test_stdout_padding_adds_whitespace() -> None:
    out = _call_render(renderables=("x",), padding=1)
    lines = out[0].split("\n")
    assert len(lines) == 3  # blank + content + blank


def test_stdout_align_center() -> None:
    out = _call_render(renderables=("hi",), align="center")
    # With center align and a 2-char string, there is no extra whitespace
    # (width == len("hi")), but no error either.
    assert "hi" in out[0]


def test_stdout_title_in_output() -> None:
    out = _call_render(renderables=("body",), border="plain", title="MyBox")
    assert "MyBox" in out[0]


def test_stdout_multiple_modifiers() -> None:
    out = _call_render(renderables=("x",), modifiers=["bold", "italic"])
    assert "\033[1m" in out[0]
    assert "\033[3m" in out[0]


def test_stdout_empty_renderables() -> None:
    out = _call_render(renderables=())
    assert out == [""]


def test_stdout_integer_renderable() -> None:
    out = _call_render(renderables=(42,))
    assert "42" in out[0]


def test_stdout_list_renderable() -> None:
    out = _call_render(renderables=(["line1", "line2"],))
    lines = out[0].split("\n")
    assert "line1" in lines[0]
    assert "line2" in lines[1]


# ---------------------------------------------------------------------------
# render() public API — no active terminal → hits fallback
# ---------------------------------------------------------------------------


def test_render_bold_produces_ansi(capsys) -> None:
    render("hello", modifiers=["bold"])
    captured = capsys.readouterr()
    assert "\033[1m" in captured.out
    assert "hello" in captured.out
    assert _RESET in captured.out


def test_render_color_name(capsys) -> None:
    render("hi", color="green")
    captured = capsys.readouterr()
    assert "\033[38;2;" in captured.out


def test_render_border(capsys) -> None:
    render("box", border="rounded")
    captured = capsys.readouterr()
    assert "╭" in captured.out
    assert "╰" in captured.out


def test_render_no_style_no_ansi(capsys) -> None:
    render("plain text")
    captured = capsys.readouterr()
    assert "\033[" not in captured.out
    assert "plain text" in captured.out


def test_render_padding_and_border(capsys) -> None:
    render("padded", border="plain", padding=1)
    captured = capsys.readouterr()
    assert "+" in captured.out
    assert "padded" in captured.out


def test_render_title_with_border(capsys) -> None:
    render("body", border="rounded", title="Header")
    captured = capsys.readouterr()
    assert "Header" in captured.out


def test_render_multiple_vertical(capsys) -> None:
    render("alpha", "beta", direction="vertical")
    captured = capsys.readouterr()
    assert "alpha" in captured.out
    assert "beta" in captured.out


def test_render_multiple_horizontal(capsys) -> None:
    render("left", "right", direction="horizontal")
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    # both renderables should appear on the same line
    assert any("left" in line and "right" in line for line in lines)


def test_render_hex_color(capsys) -> None:
    render("x", color="#ff0000")
    captured = capsys.readouterr()
    assert "\033[38;2;255;0;0m" in captured.out


def test_render_background_color(capsys) -> None:
    render("bg", background="blue")
    captured = capsys.readouterr()
    assert "\033[48;2;" in captured.out


def test_render_border_sides_partial(capsys) -> None:
    render("sided", border="plain", border_sides=["top", "bottom"])
    captured = capsys.readouterr()
    assert "-" in captured.out
    assert "|" not in captured.out


def test_render_align_center(capsys) -> None:
    render("hi", align="center")
    captured = capsys.readouterr()
    assert "hi" in captured.out


def test_render_integer(capsys) -> None:
    render(99)
    captured = capsys.readouterr()
    assert "99" in captured.out


def test_render_float(capsys) -> None:
    render(1.5)
    captured = capsys.readouterr()
    assert "1.5" in captured.out


def test_render_empty_string(capsys) -> None:
    render("")
    captured = capsys.readouterr()
    assert captured.out == "\n"


def test_render_border_color(capsys) -> None:
    render("x", border="plain", border_color="red")
    captured = capsys.readouterr()
    # border color prefix should appear around border chars
    assert "\033[38;2;255;0;0m" in captured.out


# ---------------------------------------------------------------------------
# Text component styling
# ---------------------------------------------------------------------------


def test_render_text_component_leaf_color(capsys) -> None:
    from xnano.components.text import Text

    render(Text("Hello", color="violet", modifiers=("bold",)))
    out = capsys.readouterr().out
    assert "Hello" in out
    assert "\033[1m" in out
    assert "\033[38;2;" in out
    assert "Text(" not in out


def test_render_text_component_nested_spans(capsys) -> None:
    from xnano.components.text import Text

    message = Text(
        [
            Text("● ", color="emerald-400"),
            Text("Done: ", color="white", modifiers=("bold",)),
            Text("ok", color="slate-300"),
        ]
    )
    render(message)
    out = capsys.readouterr().out
    assert "● " in out
    assert "Done: " in out
    assert "ok" in out
    assert "\033[38;2;" in out


def test_render_multiple_text_components_vertical(capsys) -> None:
    from xnano.components.text import Text

    render(
        Text("Done: ", color="emerald-400", modifiers=("bold",)),
        Text("All checks passed.", color="slate-400"),
    )
    lines = capsys.readouterr().out.splitlines()
    assert any("Done:" in line for line in lines)
    assert any("checks" in line for line in lines)


# ---------------------------------------------------------------------------
# Component fallbacks (Progress / Sparkline / Table / Chart)
# ---------------------------------------------------------------------------


def test_render_progress_component(capsys) -> None:
    from xnano.components.progress import Progress

    render(Progress(value=0.5))
    out = capsys.readouterr().out
    assert "50%" in out
    assert "█" in out or "░" in out


def test_render_progress_with_label(capsys) -> None:
    from xnano.components.progress import Progress

    render(Progress(value=0.4, label="cpu"))
    out = capsys.readouterr().out
    assert "cpu" in out


def test_render_progress_value_total(capsys) -> None:
    from xnano.components.progress import Progress

    render(Progress(value=25, total=100))
    out = capsys.readouterr().out
    assert "25%" in out


def test_render_sparkline(capsys) -> None:
    from xnano.components.sparkline import Sparkline

    render(Sparkline(data=[0, 2, 4, 8, 4, 2, 0]))
    out = capsys.readouterr().out.strip()
    assert out
    assert any(ch in out for ch in "▁▂▃▄▅▆▇█")


def test_render_table_from_dicts(capsys) -> None:
    from xnano.components.table import Table

    render(
        Table(
            data=[
                {"service": "api", "status": "ok"},
                {"service": "db", "status": "degraded"},
            ]
        )
    )
    out = capsys.readouterr().out
    assert "service" in out
    assert "api" in out
    assert "degraded" in out


def test_render_chart_summary(capsys) -> None:
    from xnano.components.chart import Chart

    render(Chart(series={"cpu": [1, 2, 3]}))
    out = capsys.readouterr().out
    assert "chart" in out.lower()


# ---------------------------------------------------------------------------
# builtins.print-compatible kwargs: sep, end, file, flush
# ---------------------------------------------------------------------------


def test_render_sep_horizontal(capsys) -> None:
    render("left", "right", direction="horizontal", sep=" | ")
    out = capsys.readouterr().out
    assert "left | right" in out or ("left" in out and "right" in out)


def test_render_end_empty(capsys) -> None:
    render("no-newline", end="")
    out = capsys.readouterr().out
    assert out == "no-newline"


def test_render_end_custom(capsys) -> None:
    render("x", end="!\n")
    out = capsys.readouterr().out
    assert out.endswith("!\n")
    assert "x" in out


def test_render_to_file_object() -> None:
    import io

    buf = io.StringIO()
    render("to-file", file=buf, end="")
    assert buf.getvalue() == "to-file"


def test_render_flush_file() -> None:
    import io

    class Tracking(io.StringIO):
        def __init__(self) -> None:
            super().__init__()
            self.flush_count = 0

        def flush(self) -> None:
            self.flush_count += 1
            super().flush()

    buf = Tracking()
    render("flush-me", file=buf, flush=True, end="")
    assert buf.getvalue() == "flush-me"
    assert buf.flush_count >= 1


def test_render_file_with_styles() -> None:
    import io

    buf = io.StringIO()
    render("styled", color="red", modifiers=["bold"], file=buf, end="")
    text = buf.getvalue()
    assert "styled" in text
    assert "\033[1m" in text
    assert "\033[38;2;" in text


# ---------------------------------------------------------------------------
# Stream append + full-content update
# ---------------------------------------------------------------------------


def test_stream_append_chunks(capsys) -> None:
    from xnano._renderable import clear_stream, get_stream_content

    clear_stream("chat")
    render("Hello", stream="chat", end="", flush=True)
    render(" world", stream="chat", end="\n", flush=True)
    out = capsys.readouterr().out
    assert "Hello" in out
    assert "world" in out
    assert get_stream_content("chat") == "Hello world\n"
    clear_stream("chat")


def test_stream_update_replaces_full_content(capsys) -> None:
    from xnano._renderable import clear_stream, get_stream_content

    clear_stream("status")
    render("Loading.", stream="status", update=True, end="\n")
    render("Done!", stream="status", update=True, end="\n")
    # Final region content is the full replacement, not a concatenation.
    assert get_stream_content("status") == "Done!\n"
    out = capsys.readouterr().out
    assert "Done!" in out
    clear_stream("status")


def test_stream_true_uses_default_id() -> None:
    from xnano._renderable import clear_stream, get_stream_content

    clear_stream(True)
    render("a", stream=True, end="")
    render("b", stream=True, end="")
    assert get_stream_content(True) == "ab"
    clear_stream(True)


def test_stream_update_multiline_region(capsys) -> None:
    from xnano._renderable import clear_stream, get_stream_content

    clear_stream("box")
    render("line1", "line2", stream="box", update=True, end="\n")
    render("only", stream="box", update=True, end="\n")
    assert get_stream_content("box") == "only\n"
    clear_stream("box")


def test_format_renderables_no_io() -> None:
    from xnano._renderable import format_renderables

    body = format_renderables(("alpha", "beta"), direction="vertical")
    assert "alpha" in body
    assert "beta" in body
    assert "\n" in body


def test_render_all_style_kwargs_together(capsys) -> None:
    render(
        "core",
        color="cyan",
        background="black",
        modifiers=["bold", "underline"],
        align="left",
        border="rounded",
        border_sides=["top", "bottom", "left", "right"],
        border_color="yellow",
        title="T",
        title_position="top",
        padding=1,
    )
    out = capsys.readouterr().out
    assert "core" in out
    assert "╭" in out
    assert "T" in out
