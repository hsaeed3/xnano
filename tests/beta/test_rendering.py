"""tests.beta.test_rendering"""

from __future__ import annotations

import inspect
import io

from xnano.beta.rendering import (
    clear_stream,
    get_stream_content,
    render,
)


def test_render_has_concrete_public_signature() -> None:
    parameters = inspect.signature(render).parameters
    assert "color" in parameters
    assert "padding" in parameters
    assert "stream" in parameters
    assert all(
        parameter.kind is not inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )


def test_render_writes_and_updates_named_streams() -> None:
    output = io.StringIO()
    clear_stream("status")
    render("waiting", file=output, stream="status")
    render("ready", file=output, stream="status", update=True)
    assert "waiting" in output.getvalue()
    assert get_stream_content("status").rstrip() == "ready"


def test_render_applies_frame_style_at_content_size() -> None:
    output = io.StringIO()
    render("hello", border="rounded", padding=1, file=output)
    rendered = output.getvalue()
    assert "hello" in rendered
    assert rendered.splitlines()[0].startswith("╭───────╮")
